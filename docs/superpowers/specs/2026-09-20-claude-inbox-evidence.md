# Claude inbox live evidence

Scope: #119 provider cleanup followed by #120 socket delivery. See the approved
issue descriptions and `docs/claude-inbox-delivery.md` for behavior and limitations.

On 2026-09-20, Claude Code 2.1.278 on macOS was exercised in stream-json print
mode using disposable conversations and a temporary Noisy Studio configuration.
No microphone, production app, inbound-policy setting or messaging token was
changed. Only synthetic messages were used; no endpoint or session ID was printed.

1. A private SessionStart handoff registered the inherited socket and native
   session ID with an independent Python process. After the initial result, the
   process wrote a user frame and observed the randomized marker in the same
   conversation's assistant response. The sender was not Claude's child.
2. The actual Noisy Studio provider, HTTP registration boundary, utterance queue,
   continuation worker and native sender were exercised together. An idle session
   replied to the synthetic speech without a waiting voice hook. Noisy Studio's
   production receipt remained sent/unconfirmed despite the manual marker proof.
3. A valid endpoint with a wrong native target ID produced no reply during the
   observation window. This is a guard probe, not a production rejection receipt.
4. Incoming speech was sent during a Bash sleep tool and a reply arrived in the
   same conversation. A separate interactive terminal checkpoint left an unsent keyboard draft in
   the composer, delivered inbox speech, then submitted that draft. Its marker
   remained intact and appeared in the assistant response. The terminal used
   the same unchanged inbound policy and the updated source hooks.

A synthetic marker reply is test evidence, not a mechanism that production uses
for delivery confirmation. These observations do not establish other operating
systems, all permission modes or remotely hosted Claude sessions.
