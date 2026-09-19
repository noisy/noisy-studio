import { afterEach, expect, it, vi } from 'vitest';
import { getSpeechSettings, updateSpeechSettings } from './client';
afterEach(()=>vi.unstubAllGlobals());

it('preserves the server recovery explanation for speech settings errors',async()=>{
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({error:'Restore saved speech settings, then retry.'}),{status:409})));
  await expect(getSpeechSettings()).rejects.toThrow('Restore saved speech settings, then retry.');
});

it('offers a readable fallback when a failed speech request has no JSON response',async()=>{
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('Service unavailable',{status:503})));
  await expect(updateSpeechSettings({operation:'apply',choice:'example:tts',revision:'1',bindings:{}})).rejects.toThrow('Check the connection and retry.');
});
