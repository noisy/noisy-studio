// Approved CSS-only framing shared by both Todd recordings. Preserve the
// source's top 20% and left 19.43% crop; keep original media untouched.
const zoom = 1.75 * 1.05 * 1.05;
export const toddCamera = {
  cameraZoom: zoom,
  cameraOffsetX: 100 * (1 - 2 * (3 / 14 - 0.02) * zoom / (zoom - 1)),
  cameraOffsetY: 100 * (1 - 2 * 0.20 * zoom / (zoom - 1)),
};

// Opt-in comparison; the normal website keeps the approved inset layout.
export const cornerCameraPreview = typeof window !== 'undefined'
  && new URLSearchParams(window.location.search).get('cameraLayout') === 'corner';

export const inwardCameraPreview = typeof window !== 'undefined'
  && new URLSearchParams(window.location.search).get('cameraLayout') === 'inward';
