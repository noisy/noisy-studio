import { expect, it } from 'vitest';
import take from './recorded-hero/hero-recording.json';
import { activityAt, presentationTake, validatePresentation } from './presentationTiming';
import { recordedCrewAt } from './recordedCrewTimeline';
it('ends listening earlier while preserving transcript arrivals, media and reply times', () => {
  const edits = [{utterance: 'u1', userEndMs: 10500, status: 'thinking' as const}];
  const adjusted = presentationTake(take, edits);
  expect(adjusted.events.filter(event => event.type !== 'user-end')).toEqual(take.events.filter(event => event.type !== 'user-end'));
  expect(recordedCrewAt(adjusted, 11000).mode).toBe('idle');
  expect(recordedCrewAt(adjusted, 13000).feed[0].text).toContain('part of a name gives me nothing');
  expect([activityAt(take, edits, 10499), activityAt(take, edits, 11000), activityAt(take, edits, 13000)]).toEqual([null, 'Thinking…', null]);
  expect(take.events.find(event => event.type === 'user-end')!.atMs).toBeGreaterThan(10500);
});
it('rejects timing from another source or outside the selected user turn', () => {
  const document = {version: 1, kind: 'demo-presentation-edits', sourceSha256: 'source1', turns: [{utterance: 'u1', userEndMs: 10500, status: 'console'}]};
  expect(validatePresentation(document, take, 'source1')).toBe(document);
  expect(() => validatePresentation(document, take, 'source2')).toThrow();
  expect(() => validatePresentation({...document, turns: [{utterance: 'u1', userEndMs: 14000, status: 'thinking'}]}, take, 'source1')).toThrow();
});

it('opens a working pause after Lux by delaying the next user speaking window', () => {
  const edits = [{utterance: 'u2', userStartMs: 21000, userEndMs: 32709, status: 'none' as const}];
  const activities = [{id: 'activity1', startMs: 17500, endMs: 21000, status: 'console' as const, consoleTask: 'u2'}];
  const document = {version: 1, kind: 'demo-presentation-edits', sourceSha256: 'source1', turns: edits, activities};
  expect(validatePresentation(document, take, 'source1')).toBe(document);
  const adjusted = presentationTake(take, edits);
  expect(recordedCrewAt(adjusted, 20000).mode).toBe('idle');
  expect(recordedCrewAt(adjusted, 22000).mode).toBe('user');
  expect([activityAt(take, edits, 18000, activities), activityAt(take, edits, 21000, activities)]).toEqual(['Editing src/search.ts', null]);
  expect(adjusted.events.filter(event => event.type.startsWith('agent-') || event.type === 'transcript')).toEqual(take.events.filter(event => event.type.startsWith('agent-') || event.type === 'transcript'));
  expect(() => validatePresentation({...document, activities: [{...activities[0], endMs: 22000}]}, take, 'source1')).toThrow(/fit a pause/);
});

// Protect the approved recording plan at the same boundary as imported editor JSON.
import savedPresentation from '../../../../tools/demo-recorder/takes/hero-v1/presentation-edits.json';
import manifest from '../../../../tools/demo-recorder/takes/hero-v1/manifest.json';
it('loads the approved hero timing without moving media events', () => {
  const plan = validatePresentation(savedPresentation, take, manifest.files['original.webm']);
  const adjusted = presentationTake(take, plan.turns);
  expect(adjusted.events.filter(event => event.type.startsWith('agent-') || event.type === 'transcript')).toEqual(take.events.filter(event => event.type.startsWith('agent-') || event.type === 'transcript'));
  expect([activityAt(take, plan.turns, 18000, plan.activities), activityAt(take, plan.turns, 62000, plan.activities)]).toEqual(['Editing src/search.ts', 'Deploying to production']);
});

import toddTake from '../../../../website/src/assets/todd/hero.json';
import toddPresentation from '../../../../website/src/assets/todd/hero-presentation-edits.json';
it('keeps Todd speaking through the last partial caption before showing thinking', () => {
  const plan = validatePresentation(toddPresentation, toddTake, toddPresentation.sourceSha256);
  expect(recordedCrewAt(toddTake, 12000).mode).toBe('user');
  expect([activityAt(toddTake, plan.turns, 12000, plan.activities), activityAt(toddTake, plan.turns, 13000, plan.activities)]).toEqual([null, 'Thinking…']);
});
