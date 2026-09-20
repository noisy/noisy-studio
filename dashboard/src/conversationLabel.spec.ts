import { expect, it } from "vitest";
import { conversationLabel } from "./conversationLabel";

it.each([
  "/private/example/session-1", "~/projects/session-1", "../projects/session-1",
  "projects/session-1", "C:\\projects\\session-1", "\\\\server\\share",
  "C:session-1", "Investigate /projects/session-1 today", "", "   ",
])("uses a neutral label for unsafe or absent title %j", (title) => {
  expect(conversationLabel(title)).toBe("New conversation");
});

it("preserves a human title", () => {
  expect(conversationLabel("  Release review  ")).toBe("Release review");
});
