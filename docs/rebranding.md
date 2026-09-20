# Noisy Studio rebrand

Noisy Studio is the new product name. This first change covers the dashboard,
website, Demo Studio, desktop window/menu text, packaged app and download names,
mobile view, setup greetings, plugin display text, and current documentation.

The macOS app builds as **Noisy Studio.app**, with **Noisy Studio Dev.app** for
the development distribution. Electron Builder derives executable and download
artifact names from these product names. The existing bundle IDs remain stable.
The shell explicitly preserves the former Electron user-data directory before
startup, including the separate packaged development profile. Backend settings,
history, and credentials continue to use their existing configured directories.
The former app bundle may remain installed alongside the renamed bundle; quit
and replace the old application when installing the renamed build.

## Compatibility names retained for the next change

| Area | Existing identifier | Why it remains |
| --- | --- | --- |
| Local checkout | `noisy-coding/` | Existing directory names remain valid; the repository is now `noisy/noisy-studio`. |
| Website URLs | Current domain and `/noisy-coding/` Pages base | Avoid broken links and deployment paths. |
| Python and CLI | `noisy-coding`, `noisy_coding`, `noisy-coding-*` | Imports, entry points, metadata lookup, installers, and release scripts must move together. |
| Plugins and MCP | `noisy-coding`, `mcp__noisy-coding__*` | Existing registrations, hook matchers, ownership markers, and update commands depend on them. |
| Configuration | `NOISY_CODING_*`, `.config/noisy-coding*` | Renaming without fallback could disconnect integrations or hide saved state. |
| Browser preferences | `noisy-coding.*` | Preserve accent, avatar, and audio settings. |
| Desktop identity | `pl.noisy.coding.companion*`, old Electron profile names | Preserve application identity and existing profiles; OS upgrade/permission behavior still needs a packaged-app check. |
| Internal build names | npm package names, `noisy-coding-daemon` | These are technical identities, separate from the visible app and download names. |

A later technical rename needs agreed aliases/fallbacks, collision handling when
both old and new settings exist, and rollback behavior. Do not replace these
identifiers in installation examples until the corresponding implementation
supports the new names. Existing ticket contents remain unchanged; historical design documents use
the current brand in prose while retaining their original technical examples.

## Recorded media

The two scripted demo lines that name the product use new clip keys,
`studio-greet` and `studio-script-1`, so the existing browser speech fallback
reads the updated text instead of playing old-brand audio. Replacement recordings
can be added under those keys without another driver change. The existing hero and crew recording transcripts contain no old product name;
sampled video frames and their posters also produced no old-name OCR matches.
This is a spot check, not a frame-by-frame or audio transcription audit.

The unreferenced `docs/img/desktop-dashboard.png` and
`docs/img/companion-desktop-dock.png` retain the old name in historical captures.
The generated website/dashboard screenshots are rebuilt from the new UI.
