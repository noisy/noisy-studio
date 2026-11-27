/* Frozen helper for the Lab "before" and "sections" copies, which still use
 * the old positional key menu. Production dropped it for per-conversation
 * talk keys (01e49dd); keep it here so the comparison stays as it was. */
import { orderAgents, type AgentMetaLike } from "../../components/agentOrder";

/** "Give this conversation the Tab N key": the daemon numbers its visible
 *  conversations in position order, so the key moves by swapping positions
 *  with whoever holds it now. Returns the FULL new order for the daemon, or
 *  null when nobody holds that key or it is already this conversation's. */
export function assignShortcut(
  names: string[],
  meta: Record<string, AgentMetaLike & { shortcut?: number | null }>,
  name: string,
  slot: number,
): string[] | null {
  const holder = names.find((n) => meta[n]?.shortcut === slot);
  if (!holder || holder === name) return null;
  const all = orderAgents(names, meta);
  const [a, b] = [all.indexOf(name), all.indexOf(holder)];
  if (a === -1 || b === -1) return null;
  [all[a], all[b]] = [all[b], all[a]];
  return all;
}
