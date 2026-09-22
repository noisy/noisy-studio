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

it.each([
  "123456789abc", "12345678-1234-1234-1234-123456789abc",
  "grok:12345678-1234-1234-1234-123456789abc",
])("hides opaque ID titles %j", (title) => {
  expect(conversationLabel(title)).toBe("New conversation");
});

it.each(["abcdefgh-qrstuvwx", "abcdefgh", "qrstuvwx"])("hides known routing IDs and abbreviations %j", (title) => {
  expect(conversationLabel(title, "abcdefgh-qrstuvwx")).toBe("New conversation");
});

it.each(["Grok CLI", "Release 2026", "Review abcdef12", "CI build 12345"])("preserves descriptive titles %j", (title) => {
  expect(conversationLabel(title, "some-other-session")).toBe(title);
});
