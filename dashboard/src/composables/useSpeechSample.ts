import { onUnmounted, ref } from 'vue';
import { resampleTo16k, floatToInt16 } from './pcm';
/** An isolated, bounded microphone sample. Never enters the agent conversation. */
export function useSpeechSample(onSample: (wav: string) => Promise<void>) {
  const recording = ref(false);
  const error = ref('');
  let recorder: MediaRecorder | undefined;
  let stream: MediaStream | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let generation = 0;
  function cancel() { generation++; clearTimeout(timer); if (recorder?.state === 'recording') recorder.stop(); stream?.getTracks().forEach(t=>t.stop()); recording.value=false; }
  async function start() {
    cancel(); error.value=''; const request=generation;
    const input = await navigator.mediaDevices.getUserMedia({audio:true});
    if(request!==generation){input.getTracks().forEach(t=>t.stop());return;}
    stream=input; const parts: Blob[]=[];
    recorder=new MediaRecorder(input);
    recorder.ondataavailable=e=>{if(e.data.size)parts.push(e.data);};
    recorder.onstop=async()=>{
      input.getTracks().forEach(t=>t.stop()); recording.value=false;clearTimeout(timer);
      if(request!==generation)return;
      const context=new AudioContext();
      try {
        const decoded=await context.decodeAudioData(await new Blob(parts).arrayBuffer());
        const pcm=floatToInt16(resampleTo16k(decoded.getChannelData(0),decoded.sampleRate));
        const buffer=new ArrayBuffer(44+pcm.length*2);const view=new DataView(buffer);
        const str=(offset:number,text:string)=>[...text].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
        str(0,'RIFF');view.setUint32(4,36+pcm.length*2,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,pcm.length*2,true);
        pcm.forEach((sample,i)=>view.setInt16(44+i*2,sample,true));
        if(request===generation) await onSample(btoa(Array.from(new Uint8Array(buffer),b=>String.fromCharCode(b)).join('')));
      } catch { if(request===generation) error.value='This browser could not process the recording. Try another microphone or browser.'; } finally {await context.close();}
    };
    recorder.start();recording.value=true;timer=setTimeout(()=>recorder?.stop(),15000);
  }
  function finish(){if(recorder?.state==='recording')recorder.stop();}
  onUnmounted(cancel);
  return {recording,error,start,finish,cancel};
}
