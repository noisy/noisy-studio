// A user-followed HTTP(S) link belongs in their browser, never a second app window.
function installExternalLinks(webContents, shell) {
  webContents.setWindowOpenHandler(({ url }) => {
    try {
      const target = new URL(url);
      if (["http:", "https:"].includes(target.protocol) && !target.username && !target.password) {
        void shell.openExternal(target.href).catch(() => {});
      }
    } catch {}
    return { action: "deny" };
  });
}
module.exports = { installExternalLinks };
