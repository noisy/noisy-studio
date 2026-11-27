/** ONE ordering rule for conversations, shared by the list and the widget.
 *
 * The dashboard grouped by liveness and honoured drag-and-drop; the widget
 * sorted by arrival time alone. Same conversations, different order, in two
 * surfaces the user sees at once - so the third tab and the third avatar
 * were not the same agent, which is exactly the kind of mismatch that makes
 * someone click the wrong one.
 *
 * The rule: online conversations first, grouped by project (projects in a
 * stable order, see projectOrder), then offline (most recently ended first).
 * Within a project, conversations keep their position: the order the user
 * dragged them into, else arrival order.
 */
export interface AgentMetaLike {
  online?: boolean;
  activated_at?: number;
  offline_since?: number | null;
  manual_pos?: number | null;
  project?: string | null;
}

/** A project is virtual: the conversations whose sessions run in the same
 *  repository (the daemon folds worktrees into it). `null` = unknown. */
export type ProjectKey = string | null;

export function orderAgents(
  names: string[],
  meta: Record<string, AgentMetaLike> = {},
): string[] {
  const of = (n: string) => meta[n] ?? {};
  // A daemon without agents_meta yields the legacy flat list: all online.
  const online = byPosition(names.filter((n) => of(n).online ?? true), meta);
  const offline = byPosition(
    names.filter((n) => !(of(n).online ?? true)),
    meta,
    (a, b) => (of(b).offline_since ?? 0) - (of(a).offline_since ?? 0),
  );
  return [
    ...projectOrder(names, meta).flatMap((project) => online.filter((n) => projectOf(n, meta) === project)),
    ...offline,
  ];
}

/** Projects in the order the list shows them: by their first conversation's
 *  position, counting ended conversations too, so a project never moves
 *  because one of its sessions ended, started working or spoke. Only the
 *  user's own drag (or a new conversation) changes positions. Conversations
 *  without a project come last. */
export function projectOrder(
  names: string[],
  meta: Record<string, AgentMetaLike> = {},
): ProjectKey[] {
  const seen = new Set<ProjectKey>();
  for (const name of byPosition(names, meta)) seen.add(projectOf(name, meta));
  const known = [...seen].filter((project) => project !== null);
  return seen.has(null) ? [...known, null] : known;
}

/** The dashboard's conversation list: one group per project, in
 *  projectOrder, then Settled (ended sessions), folded by the caller.
 *
 * An ended session stays in its project - not in Settled - while it still
 * has something for you (speaking, messages waiting) or it is the
 * conversation you are looking at or talking to: a folded section must
 * never hide those. Working is not a place: projects are always busy, so it
 * is a glyph on the row, and rows never move because an agent started or
 * stopped working.
 */
export interface ProjectGroup {
  project: ProjectKey;
  names: string[];
}
export interface ConversationGroups {
  projects: ProjectGroup[];
  settled: string[];
}

export function groupAgents(
  names: string[],
  meta: Record<string, AgentMetaLike> = {},
  live: { speaking?: string[]; queued?: Record<string, number>; keepInSight?: (string | null)[] } = {},
): ConversationGroups {
  const speaking = new Set(live.speaking ?? []);
  const inSight = new Set(live.keepInSight ?? []);
  const keepsItsPlace = (n: string) =>
    (meta[n]?.online ?? true) || speaking.has(n) || (live.queued?.[n] ?? 0) > 0 || inSight.has(n);
  const ordered = orderAgents(names, meta);
  const listed = ordered.filter(keepsItsPlace);
  const projects = projectOrder(names, meta)
    .map((project) => ({ project, names: listed.filter((n) => projectOf(n, meta) === project) }))
    .filter((group) => group.names.length > 0);
  return { projects, settled: ordered.filter((n) => !keepsItsPlace(n)) };
}

/** Drag-and-drop: `dragged` dropped onto `target`. Returns the FULL new
 *  order to send to the daemon, or null when the two are in different
 *  projects (a project is where the session runs, not a choice).
 *
 * Only the project's own slots are reshuffled; every other conversation
 * keeps its position, so no project moves because of a drag inside another
 * one (the daemon numbers the order it gets from 0). */
export function moveWithinProject(
  names: string[],
  meta: Record<string, AgentMetaLike>,
  dragged: string,
  target: string,
): string[] | null {
  const project = projectOf(dragged, meta);
  if (dragged === target || projectOf(target, meta) !== project) return null;
  const all = byPosition(names, meta);
  const members = all.filter((n) => projectOf(n, meta) === project);
  const from = members.indexOf(dragged);
  const to = members.indexOf(target);
  if (from === -1 || to === -1) return null;
  members.splice(from, 1);
  members.splice(to, 0, dragged);
  let next = 0;
  return all.map((n) => (projectOf(n, meta) === project ? members[next++] : n));
}

function projectOf(name: string, meta: Record<string, AgentMetaLike>): ProjectKey {
  return meta[name]?.project || null;
}

/** Position order: dragged conversations first in their dragged order, the
 *  rest by `natural` (arrival by default). Independent of liveness. */
function byPosition(
  names: string[],
  meta: Record<string, AgentMetaLike>,
  natural: (a: string, b: string) => number = (a, b) => (meta[a]?.activated_at ?? 0) - (meta[b]?.activated_at ?? 0),
): string[] {
  const manual = (n: string) => meta[n]?.manual_pos ?? null;
  return [...names].sort((a, b) => {
    const [ma, mb] = [manual(a), manual(b)];
    if (ma != null && mb != null) return ma - mb;
    if (ma != null) return -1;
    if (mb != null) return 1;
    return natural(a, b);
  });
}
