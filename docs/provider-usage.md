# Agent provider plan limits

The dashboard reads `provider_usage` from this daemon's `/status`. Only providers with a visible, non-ended conversation registered in this instance appear. Installed tools and speech-engine catalog entries do not count. Unknown or unsupported reports have no invented percentage. The compact panel has no Details view or historical statistics.

Quota samples expire after five minutes and independently when their reset timestamp passes. Stale values remain visibly historical; missing windows in a new report are removed rather than interpreted as zero. Reports are memory-only, so a restarted daemon waits for fresh readings.

Connection scopes are opaque hashes of each harness profile location. Sessions with the same scope share a sample. Distinct profiles remain separate: this registration contract does not expose a trustworthy account ID, so it cannot prove that two profiles share an account. No paths, credentials, or account identifiers are sent to the dashboard.

## Codex

Successful Codex hooks schedule a background read at most once per minute per profile and daemon endpoint. The helper inherits that hook's CODEX_HOME, starts the installed `codex app-server`, performs initialize/initialized and `account/rateLimits/read`, and shuts down. It never starts a turn, logs in, or reads auth files. If the CLI is absent, unsupported, not authenticated, or times out, the panel stays unknown/stale. Collection resumes on later hooks; an idle session does not continuously spawn processes.

## Claude Code

`hooks/claude_statusline.py` accepts official statusline JSON and forwards only session_id plus rate_limits to the selected daemon. It requires an already registered session. Configure it explicitly with the same `NOISY_STUDIO_LISTENER_PORT` as that session's hooks. This change does NOT overwrite any Claude configuration.

If a statusline already exists, preserve it as arguments after `--`; its original JSON stdin and output pass through. For example, the command structure is `python3 /absolute/path/hooks/claude_statusline.py -- /absolute/path/existing-statusline`. Shell-based commands can be preserved with an explicit `sh -c` argument when configuring them. Do not replace an existing statusline without preserving its command. There is no fallback to private OAuth endpoints or credential files.

## Grok

A shared weekly plan pool is documented, but a supported quota collector has not been verified. Grok conversations registered with explicit `provider: "grok"` metadata display Usage unavailable. Legacy registrations without provider metadata are not guessed from labels; their client must supply this optional field to `/register`. Grok API RPS/TPM limits are not substituted for subscription allowance.

Sources: https://code.claude.com/docs/en/statusline ; https://learn.chatgpt.com/docs/app-server ; https://docs.x.ai/grok/faq .
