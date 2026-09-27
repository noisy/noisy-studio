export type LimitWindow = { name: string; used?: number; reset: string; state: 'fresh' | 'stale' | 'unknown' | 'unsupported'; note: string };
export type Account = { name: string; badge: string; account: string; windows: LimitWindow[] };
export const accounts: Account[] = [
  { name: 'Claude Code', badge: 'C', account: 'Main account', windows: [
    { name: '5-hour', used: 76, reset: '42m', state: 'fresh', note: 'Updated 20s ago' },
    { name: 'Weekly · all models', used: 48, reset: '3d 8h', state: 'fresh', note: 'Updated 20s ago' },
    { name: 'Weekly · Opus', used: 92, reset: '1d 4h', state: 'fresh', note: 'Updated 20s ago' },
  ] },
  { name: 'Codex', badge: '✳', account: 'Main account', windows: [
    { name: 'Weekly', used: 36, reset: '5d 2h', state: 'fresh', note: 'Updated 8s ago' },
  ] },
];
export const mixedAccounts: Account[] = [
  { ...accounts[0]!, windows: [
    { name: '5-hour', used: 76, reset: '12m', state: 'stale', note: 'Last sample 31m ago' },
    { name: 'Weekly · all models', used: 48, reset: '3d 8h', state: 'fresh', note: 'Updated 20s ago' },
    { name: 'Weekly · Opus', reset: 'Unknown', state: 'unknown', note: 'Waiting for a sample' },
  ] },
  { ...accounts[1]!, windows: [
    { name: '5-hour', used: 95, reset: '18m', state: 'fresh', note: 'Updated 8s ago' },
    { name: 'Weekly', reset: 'Unavailable', state: 'unsupported', note: 'Not exposed by this connection' },
  ] },
];
