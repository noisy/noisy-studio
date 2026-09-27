const test = require("node:test");
const assert = require("node:assert/strict");
const { installExternalLinks } = require("./external-links");
test("external browser receives only HTTP(S) targets and no child windows", () => {
  let handler;
  const opened = [];
  installExternalLinks({ setWindowOpenHandler: value => handler = value }, { openExternal: async url => opened.push(url) });
  for (const url of ["http://localhost:6038/", "https://example.com/review", "javascript:alert(1)", "file:///tmp/review", "https://user:password@example.com/"]) {
    assert.deepEqual(handler({ url }), { action: "deny" });
  }
  assert.deepEqual(opened, ["http://localhost:6038/", "https://example.com/review"]);
});
