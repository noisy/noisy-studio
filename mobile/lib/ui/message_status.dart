// Generated from desktop machines/chat.ts and components/bubbleStatus.ts.
const userStatusPrefixes = <(String, String)>[
  ("recording", "recording"),
  ("transcribing", "transcribing"),
  ("ready", "ready"),
  ("delivered", "delivered"),
  ("empty", "empty"),
  ("dropped", "dropped"),
  ("undelivered", "undelivered"),
  ("transcription error", "error"),
  ("cancelled", "cancelled"),
  ("delivery unknown", "unknown"),
  ("sent", "sent"),
  ("delivery uncertain", "uncertain"),
  ("unavailable", "unavailable"),
  ("delivery rejected", "rejected"),
  ("accepted", "accepted"),
  ("delivery confirmed", "confirmed"),
];
const userStatusChips = <String, (String, String)>{
  "recording": ("rec", "● RECORDING"),
  "transcribing": ("work", "◌ TRANSCRIBING"),
  "ready": ("work", "◌ AWAITING AGENT"),
  "delivered": ("done", "✓ DELIVERED"),
  "sent": ("off", "◌ SENT · UNCONFIRMED"),
  "unknown": ("off", "? DELIVERY UNKNOWN"),
  "uncertain": ("fail", "! UNCERTAIN · NOT RETRIED"),
  "unavailable": ("warn", "ACTION NEEDED"),
  "rejected": ("fail", "✕ REJECTED"),
  "accepted": ("off", "◌ ACCEPTED · UNCONFIRMED"),
  "confirmed": ("done", "✓ CONFIRMED"),
  "empty": ("fail", "✕ NO SPEECH"),
  "dropped": ("fail", "✕ DROPPED"),
  "error": ("fail", "✕ ERROR"),
  "cancelled": ("off", "✕ CANCELLED"),
  "undelivered": ("fail", "✕ NO LISTENER"),
};
const agentStatusPrefixes = <(String, String)>[
  ("queued \u2014 waiting", "holding"),
  ("queued", "queued"),
  ("synthesizing", "synthesizing"),
  ("ready", "ready"),
  ("playing", "playing"),
  ("played", "played"),
  ("unheard", "unheard"),
  ("skipped", "skipped"),
  ("error", "error"),
];
const agentStatusChips = <String, (String, String)>{
  "queued": ("work", "◌ QUEUED"),
  "holding": ("work", "◌ HOLDING"),
  "synthesizing": ("work", "◌ SYNTHESIZING"),
  "ready": ("work", "✓ READY"),
  "playing": ("spoken", "▶ PLAYING"),
  "played": ("done", "✓ PLAYED"),
  "unheard": ("off", "◌ UNHEARD"),
  "skipped": ("off", "⏭ SKIPPED"),
  "error": ("fail", "✕ ERROR"),
};

String? messageState(String role, String status) {
  final prefixes = role == 'user' ? userStatusPrefixes : agentStatusPrefixes;
  for (final entry in prefixes) {
    if (status.toLowerCase().startsWith(entry.$1)) return entry.$2;
  }
  return null;
}

(String, String) messageChip(String role, String status) {
  final chips = role == 'user' ? userStatusChips : agentStatusChips;
  return chips[messageState(role, status)] ?? ('work', status.toUpperCase());
}
