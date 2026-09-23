/** Render the real Vue hero into a shareable MP4; see UPDATE-VIDEOS.md for approved openings and the full rebuild recipe. */
import { createRequire } from 'node:module';
import { mkdir, writeFile, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const require = createRequire(resolve(process.env.RENDER_NODE_MODULES || '/tmp/noisy-video-renderer', 'package.json'));
const { chromium } = require('playwright');
const output = resolve(process.argv[2] || join(tmpdir(), 'noisy-studio-hero.mp4'));
const url = process.argv[3] || 'http://127.0.0.1:5214/hero-export.html';
const readme = new URL(url).searchParams.has('readme');
const framesDir = await mkdtemp(join(tmpdir(), 'noisy-hero-frames-'));
await mkdir(resolve(output, '..'), { recursive: true });
const browser = await chromium.launch({
  channel: 'chrome', headless: true,
  args: ['--autoplay-policy=no-user-gesture-required'],
});
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  page.on('pageerror', error => console.error(error.message));
  await page.goto(url);
  await page.waitForFunction(() => document.body.dataset.exportReady === 'true');
  const session = await page.context().newCDPSession(page);
  const frames = [];
  const pending = [];
  session.on('Page.screencastFrame', event => {
    const path = join(framesDir, `${String(frames.length).padStart(6, '0')}.jpg`);
    frames.push({ path, timestamp: event.metadata.timestamp });
    pending.push(writeFile(path, Buffer.from(event.data, 'base64')));
    void session.send('Page.screencastFrameAck', { sessionId: event.sessionId }).catch(() => {});
  });
  await session.send('Page.startScreencast', { format: 'jpeg', quality: 95, maxWidth: 1600, maxHeight: 900, everyNthFrame: 1 });
  console.log('Capturing the complete hero animation (about 73 seconds)…');
  await page.waitForFunction(() => document.body.dataset.exportEnded === 'true', null, { timeout: 100000 });
  await session.send('Page.stopScreencast');
  await Promise.all(pending);
  const mediaStart = Number(await page.getAttribute('body', 'data-media-start'));
  const audioDelay = mediaStart - frames[0].timestamp;
  if (!(audioDelay > 0 && audioDelay < 5)) throw new Error(`Unexpected media offset: ${audioDelay}`);
  const lines = ['ffconcat version 1.0'];
  frames.forEach((frame, index) => {
    lines.push(`file '${frame.path}'`);
    lines.push(`duration ${Math.max(0.001, (frames[index + 1]?.timestamp ?? frame.timestamp + 1/30) - frame.timestamp)}`);
  });
  lines.push(`file '${frames.at(-1).path}'`);
  const concat = join(framesDir, 'frames.ffconcat');
  await writeFile(concat, lines.join('\n'));
  console.log(`Encoding ${frames.length} captured frames; intro/audio offset ${audioDelay.toFixed(3)}s`);
  const result = spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', concat,
    '-i', join(root, 'website/src/assets/todd/hero.mp4'),
    '-filter_complex', `[0:v]${readme ? `trim=start=${audioDelay},setpts=PTS-STARTPTS,` : ''}fps=30,format=yuv420p[v];[1:a]adelay=${(readme ? 0 : audioDelay*1000).toFixed(3)}:all=1,apad[a]`,
    '-map', '[v]', '-map', '[a]', '-shortest', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
    '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', output], { stdio: 'inherit' });
  if (result.status !== 0) throw new Error('FFmpeg export failed');
  await writeFile(output + '.json', JSON.stringify({ url, output, frames: frames.length, audioDelaySeconds: audioDelay, width: 1600, height: 900, framesDir }, null, 2));
  console.log(`Export ready: ${output}`);
} finally {
  await browser.close();
}
