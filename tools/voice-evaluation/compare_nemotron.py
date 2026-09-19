"""Evaluate the pinned viewer-suggested ONNX export without installing it in the app."""
import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
TAKE = ROOT / 'tools/demo-recorder/takes/hero-v1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', type=Path, required=True)
    args = parser.parse_args()
    p = args.models
    started = time.perf_counter()
    recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(tokens=str(p/'tokens.txt'), encoder=str(p/'encoder.int8.onnx'), decoder=str(p/'decoder.int8.onnx'), joiner=str(p/'joiner.int8.onnx'), num_threads=4, feature_dim=128)
    result = {'export_revision':'3f1f6020667b151d0b6820cc4b8ae4f42b6d35fc', 'runtime':sherpa_onnx.__version__, 'threads':4, 'load_ms':round((time.perf_counter()-started)*1000), 'note':'Unpaced replay in 100ms chunks; processing time is not conversational latency.', 'clips':[]}
    events=json.loads((TAKE/'timeline.json').read_text())['events']
    with tempfile.TemporaryDirectory() as directory:
        for event in events:
            if event['type'] != 'user-start': continue
            end=next(e for e in events if e['type']=='user-end' and e['utterance']==event['utterance'])
            path=Path(directory)/'clip.wav'
            duration=(end['atMs']-event['atMs'])/1000
            subprocess.run(['ffmpeg','-v','error','-y','-ss',str(event['atMs']/1000),'-i',str(TAKE/'original.webm'),'-t',str(duration),'-ar','16000','-ac','1',str(path)],check=True)
            audio,rate=sf.read(path,dtype='float32')
            stream=recognizer.create_stream()
            started=time.perf_counter(); first_partial=None
            for offset in range(0,len(audio),1600):
                stream.accept_waveform(rate,audio[offset:offset+1600])
                while recognizer.is_ready(stream): recognizer.decode_stream(stream)
                if first_partial is None and recognizer.get_result(stream): first_partial=(offset+1600)/rate
            stream.accept_waveform(rate,np.zeros(rate,dtype=np.float32));stream.input_finished()
            while recognizer.is_ready(stream):recognizer.decode_stream(stream)
            result['clips'].append({'clip':event['utterance'],'script_reference':event['prompt'],'duration_s':duration,'transcript':recognizer.get_result(stream),'inference_ms':round((time.perf_counter()-started)*1000),'first_partial_after_audio_s':first_partial})
            print(event['utterance'],'completed',flush=True)
    (ROOT/'tools/voice-evaluation/nemotron-results.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
