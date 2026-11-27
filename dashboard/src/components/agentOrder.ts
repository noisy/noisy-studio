/** ONE ordering rule for conversations, shared by the tabs and the widget.
 *
 * The dashboard grouped by liveness and honoured drag-and-drop; the widget
 * sorted by arrival time alone. Same conversations, different order, in two
 * surfaces the user sees at once - so the third tab and the third avatar
 * were not the same agent, which is exactly the kind of mismatch that makes
 * someone click the wrong one.
 *
 * The rule: online conversations first (in arrival order), then offline
 * (most recently ended first). Within each group, tabs the user has dragged
 * into place come first, in the order they were dragged.
 */
export interface AgentMetaLike {
  online?: boolean;
  activated_at?: number;
  offline_since?: number | null;
  manual_pos?: number | null;
}

export function orderAgents(
  names: string[],
  meta: Record<string, AgentMetaLike> = {},
): string[] {
  const of = (n: string) => meta[n] ?? {};
  const manual = (n: string) => of(n).manual_pos ?? null;

  const group = (subset: string[], natural: (a: string, b: string) => number) =>
    [...subset].sort((a, b) => {
      const [ma, mb] = [manual(a), manual(b)];
      if (ma != null && mb != null) return ma - mb;
      if (ma != null) return -1;
      if (mb != null) return 1;
      return natural(a, b);
    });

  // A daemon without agents_meta yields the legacy flat list: all online.
  const online = names.filter((n) => of(n).online ?? true);
  const offline = names.filter((n) => !(of(n).online ?? true));

  return [
    ...group(online, (a, b) => (of(a).activated_at ?? 0) - (of(b).activated_at ?? 0)),
    ...group(offline, (a, b) => (of(b).offline_since ?? 0) - (of(a).offline_since ?? 0)),
  ];
}

/** The dashboard's conversation list, split T3-style: what needs you stays
 * on top, sessions that are busy or over move down and out of the way.
 *
 * - yourTurn: online and it is your move - speaking, messages waiting, or
 *   idle after finishing its turn.
 * - working: online, working for a while (the caller decides how long, see
 *   useSustainedWork) and nothing waiting for you.
 * - settled: the session ended - unless it still has something for you
 *   (speaking, messages waiting) or it is the conversation you are looking
 *   at or talking to: a collapsed section must never hide those.
 *
 * Each section keeps the orderAgents order, so drag-and-drop and arrival
 * order still hold inside it.
 */
export interface ConversationSections {
  yourTurn: string[];
  working: string[];
  settled: string[];
}

export function sectionAgents(
  names: string[],
  meta: Record<string, AgentMetaLike> = {},
  live: { working?: string[]; speaking?: string[]; queued?: Record<string, number>; keepInSight?: (string | null)[] } = {},
): ConversationSections {
  const working = new Set(live.working ?? []);
  const speaking = new Set(live.speaking ?? []);
  const waitsForYou = (n: string) => speaking.has(n) || (live.queued?.[n] ?? 0) > 0;
  const inSight = new Set(live.keepInSight ?? []);
  const sections: ConversationSections = { yourTurn: [], working: [], settled: [] };
  for (const name of orderAgents(names, meta)) {
    const online = meta[name]?.online ?? true;
    if (!online && !waitsForYou(name) && !inSight.has(name)) sections.settled.push(name);
    else if (online && working.has(name) && !waitsForYou(name)) sections.working.push(name);
    else sections.yourTurn.push(name);
  }
  return sections;
}
