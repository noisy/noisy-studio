import { describe, expect, it } from "vitest";
import type { DaemonStatus, Utterance } from "../types";
import { dictationView } from "./dictationOverlay";

const status = (dictation: DaemonStatus["dictation"]) => ({ dictation }) as DaemonStatus;
const said = (id: number, text: string, extra: Partial<Utterance> = {}) =>
  ({ id, text, status: "transcribing (live)…", role: "user", agent: "", dictation: 2, ...extra }) as Utterance;

describe("dictationView", () => {
  it("joins the current session's segments in order and ignores everything else", () => {
    const view = dictationView(status({ permission: "granted", active: true, session: 2 }), [
      said(9, "second part"),
      said(4, "first part"),
      said(3, "an older dictation", { dictation: 1 }),
      said(5, "said to an agent", { dictation: undefined, agent: "tab-a" }),
    ]);
    expect(view).toEqual({ text: "first part second part", phase: "listening" });
  });

  it("follows the words into the app: inserting, then inserted or failed", () => {
    const stopped = (pending: boolean) => status({ permission: "granted", active: false, session: 2, pending });
    expect([
      dictationView(stopped(true), [said(1, "hi")]).phase,
      dictationView(stopped(false), [said(1, "hi", { status: "dictation — inserted into iTerm2" })]).phase,
      dictationView(stopped(false), [said(1, "hi", { status: "dictation — not inserted: Accessibility permission missing" })]).phase,
    ]).toEqual(["inserting", "inserted", "failed"]);
  });

  it("shows nothing before the first session", () => {
    expect(dictationView(null, [said(1, "x")])).toEqual({ text: "", phase: "inserted" });
  });
});
