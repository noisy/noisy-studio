# Noisy Studio

Talk to your coding agent while it works. Noisy Studio is a native desktop app
with speech recognition, spoken replies, per-conversation voice and character
settings, and a dashboard for the conversations you are following.

## Install

Download the macOS Apple Silicon app from [Releases](https://github.com/noisy/noisy-studio/releases),
move **Noisy Studio.app** to Applications, and open it. Complete provider and
audio setup in the app. The app includes its own Python engine; ordinary Claude
installation needs neither Python nor a separate service manager.

For Claude Code, install the companion plugin:

```sh
claude plugin marketplace add noisy/noisy-studio
claude plugin install noisy-studio@noisy
```

Restart Claude Code and ask it to set up Noisy Studio voice. Keep the app and
plugin versions together: the plugin launches the engine bundled with the app.
The internal plugin name remains `noisy-coding` for compatibility.

[Installation and troubleshooting](docs/INSTALL.md) covers permissions,
providers, updates, and a spoken round trip. The [Codex preview](docs/codex.md)
uses the same app and currently requires `uv` for its integration processes.
macOS is the validated release platform; other platforms are source development.

## Development

Use [local development](docs/local-development.md) for the isolated daemon on
7765 and dashboard hot reload. The installed app owns 9765 and has separate
settings. See [desktop packaging](docs/desktop-app.md) for signed app builds.

- [Agent hooks](docs/hooks.md)
- [Ports](docs/ports.md)
- [Product naming](docs/rebranding.md)
- [Storybook](https://noisystudio.ai/storybook/) - how the dashboard and the
  widget are meant to look, published from `main`. Run it locally with
  `cd dashboard && npm run storybook`. Its title shows the commit it was
  built from, so a story can be cited by URL and version.

API credentials belong in the app's provider settings, never in chat or source.
Offline providers download their models on first use and then run locally.
