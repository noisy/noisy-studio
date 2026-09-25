"""Generate a reproducible, low-level noise bed from background spectral statistics.

Only a smoothed spectrum is retained; no recorded waveform is reused.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np

RATE = 48000
DURATION_SECONDS = 12
TARGET_DBFS = -80
SEED = 230926
ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('delivery', type=Path)
    args = parser.parse_args()
    # Quiet windows identified inside user-marked non-speech repair regions.
    references = [('Todd - Hero Search.mp4', 46952, 47952), ('Todd - Crew.mp4', 3195, 4195)]
    spectra, sources = [], []
    for name, start, end in references:
        path = args.delivery / name
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', str(RATE), '-f', 'f32le', '-'])
        segment = np.frombuffer(raw, dtype='<f4')[start*48:end*48].astype(float)
        for i in range(0, len(segment)-2048, 1024):
            spectra.append(abs(np.fft.rfft(segment[i:i+2048]*np.hanning(2048)))**2)
        sources.append({'file': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'startMs': start, 'endMs': end})
    log_power = np.log(np.maximum(np.median(spectra, axis=0), 1e-24))
    smooth = np.convolve(np.pad(log_power, (25,25), mode='edge'), np.ones(51)/51, mode='valid')
    n = RATE * DURATION_SECONDS
    frequencies = np.fft.rfftfreq(n, 1/RATE)
    envelope = np.sqrt(np.exp(np.interp(frequencies, np.fft.rfftfreq(2048,1/RATE), smooth)))
    envelope *= frequencies**2/(frequencies**2+100**2) / np.sqrt(1+(frequencies/8000)**8)
    spectrum = np.fft.rfft(np.random.default_rng(SEED).normal(size=n)) * envelope
    noise = np.fft.irfft(spectrum, n)
    noise -= noise.mean()
    noise *= 10**(TARGET_DBFS/20) / np.sqrt(np.mean(noise**2))
    # A periodic FFT bed has no arbitrary splice. Choose an especially small
    # inter-sample step for the saved boundary, without fading to silence.
    seam = np.argmin(abs(noise - np.roll(noise,1)))
    noise = np.roll(noise, -int(seam)).astype('<f4')
    output = ROOT / 'tools/website-media/room-tone'
    output.mkdir(exist_ok=True)
    wav = output / 'todd-clean-room-tone.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(RATE),'-ac','1','-i','-','-c:a','pcm_f32le',str(wav)],input=noise.tobytes(),check=True)
    blocks = np.sqrt(np.mean(noise.reshape(-1,4800).astype(float)**2,axis=1))
    report = {'method':'synthetic noise shaped by smoothed median background spectrum; no original waveform copied','seed':SEED,'sampleRate':RATE,'durationSeconds':DURATION_SECONDS,'rmsDbfs':float(20*np.log10(np.sqrt(np.mean(noise.astype(float)**2)))),'peakDbfs':float(20*np.log10(max(abs(noise)))),'levelVariation100msDb':float(20*np.log10(max(blocks)/min(blocks))),'wrapStep':float(abs(noise[0]-noise[-1])),'sources':sources,'outputSha256':hashlib.sha256(wav.read_bytes()).hexdigest()}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['sources','outputSha256']},indent=2))

if __name__ == '__main__':
    main()
