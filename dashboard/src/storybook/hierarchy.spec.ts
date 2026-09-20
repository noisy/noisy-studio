/* The Storybook hierarchy is a rule, not a convention people remember.
 *
 * It drifted once already: 43 stories grew four naming styles, proposals
 * sitting beside finished components, and two entries loose at the root
 * (#116). A rule that is only written down decays at exactly the speed
 * people stop reading it, so it is asserted here instead.
 */
import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SECTIONS = ["Dashboard", "Widget", "Website", "Lab"];
const SRC = dirname(dirname(fileURLToPath(import.meta.url)));

function storyFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return storyFiles(path);
    return /\.stories\.(ts|js)$/.test(entry) ? [path] : [];
  });
}

const stories = storyFiles(SRC).map((path) => {
  const title = readFileSync(path, "utf8").match(/title:\s*['"]([^'"]+)['"]/)?.[1];
  return { path, title, file: path.split("/").pop()!.replace(/\.stories\.(ts|js)$/, "") };
});

describe("Storybook hierarchy (#116)", () => {
  it("finds every story file", () => {
    expect(stories.length).toBeGreaterThan(40);
  });

  it("gives every story a title", () => {
    expect(stories.filter((s) => !s.title).map((s) => s.path)).toEqual([]);
  });

  it("puts every story in one of the four sections, none at the root", () => {
    const wrong = stories
      .filter((s) => !SECTIONS.includes(s.title!.split("/")[0]))
      .map((s) => s.title);
    expect(wrong).toEqual([]);
  });

  it("names the component after its file, so the sidebar and the filesystem agree", () => {
    const mismatched = stories
      .filter((s) => s.title!.split("/").slice(-1)[0] !== s.file)
      .map((s) => `${s.title} <- ${s.file}.stories.ts`);
    expect(mismatched).toEqual([]);
  });

  it("keeps annotations out of titles - the section already says it", () => {
    const annotated = stories
      .filter((s) => /—|\(proposal\)|Concepts|\bLab\b(?!\/)/.test(s.title!))
      .map((s) => s.title);
    expect(annotated).toEqual([]);
  });
});
