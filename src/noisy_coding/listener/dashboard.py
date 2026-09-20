"""Self-contained live dashboard served by the listener daemon at GET /."""

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Noisy Studio — live view</title>
<style>
  :root {
    --paper: #FBFAF6; --surface: #FFFFFF; --ink: #23262B; --muted: #6E6A61;
    --line: #E4E1D7; --teal: #0E9F87; --teal-soft: #E0F2EE; --amber: #C2760A;
    --amber-soft: #F8ECDC; --violet: #7C5CBF; --violet-soft: #EEE9F8;
    --red: #C2483B; --red-soft: #F8E3E0; --code-bg: #F1EFE8;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --paper: #15171B; --surface: #1D2026; --ink: #E9E7E1; --muted: #9A968C;
      --line: #2D3038; --teal: #2FC4A7; --teal-soft: #16332E; --amber: #E5963C;
      --amber-soft: #35281A; --violet: #A88BE0; --violet-soft: #2A2438;
      --red: #E06A5D; --red-soft: #3A2320; --code-bg: #24272E;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 28px 18px 60px;
  }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.3rem; letter-spacing: -0.01em; margin: 0 0 4px; }
  .sub { color: var(--muted); font-size: 0.85rem; margin: 0 0 20px; }

  .card.speaking { animation: speaking 1.1s ease-in-out infinite; }
  @keyframes speaking {
    0%,100% { border-color: var(--violet); box-shadow: 0 0 0 0 transparent; }
    50% { border-color: var(--violet); box-shadow: 0 0 0 3px var(--violet-soft); }
  }
  @media (prefers-reduced-motion: reduce) { .card.speaking { animation: none; } }

  .statusbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 20px; }
  .tabs { display: flex; gap: 8px; margin: 12px 0 0; flex-wrap: wrap; }
  .tabs button {
    font: inherit; cursor: pointer; color: var(--muted);
    font-weight: 650; font-size: 0.95rem;
    /* Whole pill is clickable — border + generous padding, not just the text. */
    border: 1.5px solid var(--line); background: var(--surface);
    border-radius: 12px; padding: 11px 20px;
    display: inline-flex; align-items: center; gap: 9px;
    transition: border-color .12s, color .12s, background .12s;
  }
  .tabs button:hover { color: var(--ink); border-color: var(--muted); }
  .tabs button.viewing {
    color: var(--ink); border-color: var(--teal);
    background: var(--teal-soft); box-shadow: inset 0 0 0 1px var(--teal);
  }
  .tabs button:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }
  /* A dot shows which agent is LIVE (listening), independent of which tab you view. */
  .tabs button .live-dot { width: 8px; height: 8px; border-radius: 50%;
    background: var(--line); flex: none; }
  .tabs button.live .live-dot { background: var(--teal); animation: pulse 2s infinite; }
  .tabs button.is-speaking { border-color: var(--violet); }
  .tabs button .tab-speaking { animation: blink-speak 0.8s infinite; }
  @keyframes blink-speak { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }
  @media (prefers-reduced-motion: reduce) { .tabs button .tab-speaking { animation: none; } }
  .chip {
    display: inline-flex; align-items: center; gap: 8px;
    border: 1px solid var(--line); background: var(--surface);
    border-radius: 999px; padding: 7px 15px; font-size: 0.88rem; font-weight: 600;
  }
  .chip .num { font-variant-numeric: tabular-nums; }
  .chip small { color: var(--muted); font-weight: 500; }
  button.chip { cursor: pointer; font: inherit; color: inherit; }
  button.chip:hover { border-color: var(--teal); }
  button.chip:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }
  #mode-label { font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
  #mode-label.live, #tts-label.live { color: var(--amber); }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--muted); }
  .chip.listening .dot { background: var(--teal); animation: pulse 2s infinite; }
  .chip.recording .dot { background: var(--amber); animation: pulse 0.7s infinite; }
  .chip.muted .dot { background: var(--violet); }
  .chip.offline .dot { background: var(--red); }
  @keyframes pulse { 50% { opacity: 0.35; } }
  @media (prefers-reduced-motion: reduce) { .dot, .card.live { animation: none !important; } }

  details.rules {
    background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
    padding: 10px 18px; margin-bottom: 22px; font-size: 0.85rem;
  }
  details.rules summary { cursor: pointer; font-size: 0.75rem; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted); font-weight: 600; }
  .rules table { border-collapse: collapse; width: 100%; margin-top: 10px; }
  .rules td { padding: 4px 12px 4px 0; vertical-align: top; }
  .rules td:first-child {
    font-family: ui-monospace, Menlo, monospace; font-weight: 600;
    white-space: nowrap; color: var(--amber);
  }
  .rules td:last-child { color: var(--muted); }

  .sliders { display: grid; gap: 10px; margin-top: 12px; }
  .sliders label {
    display: grid; grid-template-columns: 168px 1fr 42px; gap: 10px;
    align-items: center; font-size: 0.85rem; font-weight: 600;
  }
  .sliders .name small { display: block; color: var(--muted); font-weight: 400; font-size: 0.72rem; }
  .sliders select {
    font: inherit; color: inherit; background: var(--paper);
    border: 1px solid var(--line); border-radius: 8px; padding: 5px 8px;
  }
  .sliders input[type="range"] { width: 100%; accent-color: var(--teal); }
  .sliders .val { font-family: ui-monospace, Menlo, monospace; font-size: 0.8rem;
    color: var(--teal); text-align: right; font-variant-numeric: tabular-nums; }

  #cards { display: flex; flex-direction: column; gap: 12px; }
  .card {
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
    padding: 13px 16px; max-width: 88%;
  }
  .card.user { align-self: flex-end; border-right: 4px solid var(--amber); }
  .card.claude { align-self: flex-start; border-left: 4px solid var(--violet); }
  .card.live { animation: breathe 1.2s infinite; }
  @keyframes breathe { 50% { border-color: var(--amber); } }

  .card .head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; flex-wrap: wrap; }
  .card .who {
    font-family: ui-monospace, Menlo, monospace; font-size: 0.68rem; font-weight: 700;
    letter-spacing: 0.09em;
  }
  .card.user .who { color: var(--amber); }
  .card.claude .who { color: var(--violet); }
  .card .status {
    font-size: 0.72rem; font-weight: 650; padding: 2px 10px; border-radius: 999px;
    background: var(--code-bg); color: var(--muted); white-space: nowrap;
  }
  .card .status.phase-rec { background: var(--amber-soft); color: var(--amber); }
  .card .status.phase-work { background: var(--code-bg); color: var(--muted); }
  .card .status.phase-ready { background: var(--amber-soft); color: var(--amber); }
  .card .status.phase-done { background: var(--teal-soft); color: var(--teal); }
  .card .status.phase-spoken { background: var(--violet-soft); color: var(--violet); }
  .card .status.phase-spoken-done { background: var(--violet-soft); color: var(--violet); }
  .card .status.phase-bad { background: var(--red-soft); color: var(--red); }
  .card .t { font-family: ui-monospace, Menlo, monospace; font-size: 0.72rem; color: var(--muted); margin-left: auto; }
  .card .text { font-size: 0.97rem; line-height: 1.45; overflow-wrap: anywhere; }
  .card .text.pending { color: var(--muted); font-style: italic; }
  .card .foot { display: flex; gap: 12px; margin-top: 5px; font-size: 0.76rem;
    color: var(--muted); font-family: ui-monospace, Menlo, monospace; }
  .card .cost { margin-left: auto; font-variant-numeric: tabular-nums; }
  .empty { color: var(--muted); font-size: 0.9rem; padding: 24px 4px; }
</style>
</head>
<body>
<main>
  <h1>Noisy Studio — live view</h1>
  <p class="sub">Every utterance is a card with a live status: recording → transcription → text → delivery.</p>

  <div class="statusbar">
    <span class="chip" id="state"><span class="dot"></span><span id="state-label">connecting…</span></span>
    <span class="chip"><span class="num" id="queued">0</span>&nbsp;<small>queued</small></span>
    <span class="chip"><small>session</small>&nbsp;<span class="num" id="cost">$0.0000</span></span>
    <span class="chip" id="credits-chip" hidden><small>credits left</small>&nbsp;<span class="num" id="credits"></span></span>
    <button class="chip" id="mode-toggle" type="button" title="Speech-to-text. Batch: transcribe after you stop talking ($0.10/h). Live: stream while you talk ($0.20/h).">
      <small>STT</small>&nbsp;<span id="mode-label">…</span>
    </button>
    <button class="chip" id="tts-toggle" type="button" title="Text-to-speech. Batch: wait for the whole clip, then play. Live: stream audio as Claude generates it, so playback starts sooner on long replies.">
      <small>TTS</small>&nbsp;<span id="tts-label">…</span>
    </button>
    <button class="chip" id="mute-toggle" type="button" title="Stop transcribing the mic (e.g. while talking to someone else). Claude keeps working; nothing you say reaches him until you unmute.">
      🎤&nbsp;<span id="mute-label">…</span>
    </button>
  </div>

  <details class="rules">
    <summary>Settings <small>(shared across agents)</small></summary>
    <div class="sliders">
      <label><span class="name">Speed <small>0.7× ↔ 1.5×</small></span>
        <input type="range" id="ch-speed" min="0.7" max="1.5" step="0.05"><span class="val" id="ch-speed-val"></span></label>
      <label><span class="name">Pause split <small>silence that ends an utterance</small></span>
        <input type="range" id="ch-silence" min="500" max="4000" step="100"><span class="val" id="ch-silence-val"></span></label>
      <label><span class="name">Smart turn <small>live only · 0 = off, higher = wait for a complete thought</small></span>
        <input type="range" id="ch-smart" min="0" max="0.9" step="0.1"><span class="val" id="ch-smart-val"></span></label>
      <label><span class="name">Turn mode <small>soft = smart turn may end early · hard = pause split rules</small></span>
        <button class="chip" id="smart-mode-toggle" type="button"><span id="smart-mode-label">…</span></button><span class="val"></span></label>
      <label><span class="name">Language <small>speech recognition &amp; voice</small></span>
        <select id="ch-language"></select><span class="val"></span></label>
    </div>
  </details>

  <details class="rules">
    <summary>Timing rules</summary>
    <table>
      <tr><td>&lt; 0.8s</td><td>a pause while speaking — nothing happens, still one utterance</td></tr>
      <tr><td>0.8s silence</td><td>VAD closes the utterance and sends it for transcription (~1s)</td></tr>
      <tr><td>2s silence</td><td>after a transcript: the grace period ends and Claude wakes with everything; speaking again extends the wait (max 20s)</td></tr>
      <tr><td>5 min</td><td>how long the background hook keeps listening after a turn ends</td></tr>
    </table>
  </details>

  <div id="tabs" class="tabs" hidden></div>

  <details class="rules" open id="character-box">
    <summary>Character <small id="character-for"></small></summary>
    <div class="sliders">
      <label><span class="name">Humor <small>dry ↔ playful</small></span>
        <input type="range" id="ch-humor" min="0" max="100" step="5"><span class="val" id="ch-humor-val"></span></label>
      <label><span class="name">Honesty <small>diplomatic ↔ blunt</small></span>
        <input type="range" id="ch-honesty" min="0" max="100" step="5"><span class="val" id="ch-honesty-val"></span></label>
      <label><span class="name">Verbosity <small>radio clicks ↔ lecture</small></span>
        <input type="range" id="ch-verbosity" min="0" max="100" step="5"><span class="val" id="ch-verbosity-val"></span></label>
      <label><span class="name">Talkative <small>milestones only ↔ frequent updates</small></span>
        <input type="range" id="ch-talkative" min="0" max="100" step="5"><span class="val" id="ch-talkative-val"></span></label>
      <label><span class="name">Voice <small>who speaks to you</small></span>
        <select id="ch-voice"></select><span class="val"></span></label>
    </div>
  </details>

  <div id="cards"><div class="empty" id="empty">Say something — the first card will appear here.</div></div>
</main>
<script>
  const PHASE = s =>
    s.startsWith("recording") ? "rec" :
    s.startsWith("transcribing") || s.startsWith("synthesizing") ? "work" :
    s.startsWith("ready") ? "ready" :
    s.startsWith("delivered") ? "done" :
    s.startsWith("playing") ? "spoken" :       // playing → pulsing card frame
    s === "played" ? "spoken-done" :           // finished → reveal text
    // empty / dropped / error — an utterance that never became text
    (s.startsWith("empty") || s.startsWith("dropped") || s.indexOf("error") >= 0) ? "dead" :
    "bad";

  const cards = document.getElementById("cards");
  const seen = new Map();

  const fmtTime = ts => new Date(ts * 1000).toLocaleTimeString();
  const fmtCost = usd => usd >= 0.01 ? "$" + usd.toFixed(2) : "$" + usd.toFixed(4);
  const escapeHtml = s => s.replace(/[&<>"']/g,
    c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const renderBold = s => escapeHtml(s).replace(/\\*\\*(.+?)\\*\\*/g, "<b>$1</b>");

  // Restart-safe key: utterance ids reset to 1 when the daemon restarts, so
  // pair the id with the start time to keep old and new cards distinct.
  const cardKey = (u) => u.started_at + ":" + u.id;

  function dropCard(key) {
    const el = seen.get(key);
    if (el) { el.remove(); seen.delete(key); }
  }

  function upsert(u) {
    const key = cardKey(u);
    // An utterance that never became text (cough, noise, silence) must not
    // linger — drop it. But keep it if STT actually captured words, even
    // when the clip was flagged too-short/dropped: real speech is not noise.
    if (PHASE(u.status) === "dead" && !u.text) { dropCard(key); return; }
    document.getElementById("empty")?.remove();
    let el = seen.get(key);
    if (!el) {
      el = document.createElement("div");
      el.innerHTML =
        '<div class="head"><span class="who"></span><span class="status"></span>' +
        '<span class="t"></span></div><div class="text"></div>' +
        '<div class="foot"><span class="detail"></span><span class="cost"></span></div>';
      el.querySelector(".who").textContent = u.role === "user" ? "YOU" : "CLAUDE";
      el.querySelector(".t").textContent = fmtTime(u.started_at);
      el.dataset.ts = u.started_at;
      // Insert newest-first by timestamp, not by arrival order — so a daemon
      // restart (utterance ids reset to 1) doesn't push new cards to the
      // bottom, and the whole history stays in true chronological order.
      const after = [...cards.children].find(
        (c) => Number(c.dataset.ts) < u.started_at
      );
      cards.insertBefore(el, after || null);
      seen.set(key, el);
      while (cards.children.length > 200) {
        const last = cards.lastChild;
        for (const [k, node] of seen) if (node === last) seen.delete(k);
        last.remove();
      }
    }
    const phase = PHASE(u.status);
    el.className = "card " + u.role + (phase === "rec" ? " live" : "");
    const st = el.querySelector(".status");
    st.textContent = u.status;
    st.className = "status phase-" + phase;
    // A Claude card that is still playing gets a pulsing frame so the user
    // can see Claude has "the mic" — while the text is already readable.
    if (u.role === "claude" && phase === "spoken") el.classList.add("speaking");
    const txt = el.querySelector(".text");
    // Show text the moment it exists — reading is faster than listening.
    if (u.text) {
      txt.innerHTML = renderBold(u.text); txt.className = "text";
    } else {
      txt.className = "text pending";
      txt.textContent = phase === "rec" ? "listening, keep talking…" : "…";
    }
    el.querySelector(".detail").textContent = u.detail || "";
    el.querySelector(".cost").textContent = u.cost_usd ? fmtCost(u.cost_usd) : "";
  }

  function setState(cls, label) {
    const chip = document.getElementById("state");
    chip.className = "chip " + cls;
    document.getElementById("state-label").textContent = label;
  }

  const TRAITS = ["humor", "honesty", "verbosity", "talkative"];
  const VOICES = {
    altair:"male", ara:"female", atlas:"male", carina:"female", castor:"male",
    celeste:"female", cosmo:"male", eve:"female", helios:"male", helix:"male",
    iris:"female", kepler:"male", leo:"male", lumen:"male", luna:"female",
    lux:"male", naksh:"male", orion:"male", perseus:"male", rex:"male",
    rigel:"male", sal:"male", sirius:"male", ursa:"female", zagan:"male",
    zenith:"male"
  };
  async function postCharacter() {
    // Character (voice + traits) is per viewed agent; speed lives in Settings.
    const body = {
      voice: document.getElementById("ch-voice").value,
      speed: Number(document.getElementById("ch-speed").value),
    };
    for (const t of TRAITS) body[t] = Number(document.getElementById("ch-" + t).value);
    if (viewedAgent) body.agent = viewedAgent;
    await fetch("/character", { method: "POST", body: JSON.stringify(body) });
  }
  function bindSliders() {
    for (const trait of TRAITS) {
      const input = document.getElementById("ch-" + trait);
      const val = document.getElementById("ch-" + trait + "-val");
      input.addEventListener("input", () => { val.textContent = input.value; });
      input.addEventListener("change", postCharacter);
    }
    const speed = document.getElementById("ch-speed");
    speed.addEventListener("input", () => {
      document.getElementById("ch-speed-val").textContent = Number(speed.value).toFixed(2) + "×";
    });
    speed.addEventListener("change", postCharacter);
    const silence = document.getElementById("ch-silence");
    silence.addEventListener("input", () => {
      document.getElementById("ch-silence-val").textContent = (silence.value / 1000).toFixed(1) + "s";
    });
    silence.addEventListener("change", async () => {
      await fetch("/settings", { method: "POST",
        body: JSON.stringify({ end_silence_ms: Number(silence.value) }) });
    });
    const smart = document.getElementById("ch-smart");
    smart.addEventListener("input", () => {
      const v = Number(smart.value);
      document.getElementById("ch-smart-val").textContent = v === 0 ? "off" : v.toFixed(1);
    });
    smart.addEventListener("change", async () => {
      await fetch("/settings", { method: "POST",
        body: JSON.stringify({ smart_turn: Number(smart.value) }) });
    });
    document.getElementById("smart-mode-toggle").addEventListener("click", async () => {
      const next = currentSmartMode === "hard" ? "soft" : "hard";
      await fetch("/settings", { method: "POST",
        body: JSON.stringify({ smart_turn_mode: next }) });
    });
    const select = document.getElementById("ch-voice");
    for (const [v, gender] of Object.entries(VOICES)) {
      const option = document.createElement("option");
      option.value = v;
      option.textContent = v[0].toUpperCase() + v.slice(1) + " (" + gender + ")";
      select.appendChild(option);
    }
    select.addEventListener("change", postCharacter);

    const langSelect = document.getElementById("ch-language");
    const LANGS = { "": "Auto-detect", en: "English", pl: "Polski", de: "Deutsch",
      es: "Español", fr: "Français", "pt-BR": "Português (BR)", it: "Italiano",
      ja: "日本語", zh: "中文" };
    for (const [code, name] of Object.entries(LANGS)) {
      const option = document.createElement("option");
      option.value = code;
      option.textContent = name;
      langSelect.appendChild(option);
    }
    langSelect.addEventListener("change", async () => {
      await fetch("/settings", { method: "POST",
        body: JSON.stringify({ language: langSelect.value }) });
    });
  }
  async function loadCharacter() {
    try {
      // Load the VIEWED agent's character, so switching tabs shows its sliders.
      if (document.activeElement &&
          document.activeElement.closest &&
          document.activeElement.closest("#character-box")) return;  // don't yank a slider mid-drag
      const q = viewedAgent ? "?agent=" + encodeURIComponent(viewedAgent) : "";
      const data = await (await fetch("/character" + q)).json();
      for (const trait of TRAITS) {
        const input = document.getElementById("ch-" + trait);
        input.value = data.character[trait];
        document.getElementById("ch-" + trait + "-val").textContent = input.value;
      }
      document.getElementById("ch-voice").value = data.character.voice || "carina";
      const speedInput = document.getElementById("ch-speed");
      speedInput.value = data.character.speed || 1.0;
      document.getElementById("ch-speed-val").textContent =
        Number(speedInput.value).toFixed(2) + "×";
    } catch {}
  }
  bindSliders();
  loadCharacter();

  let currentMode = null;
  document.getElementById("mode-toggle").addEventListener("click", async () => {
    const next = currentMode === "live" ? "batch" : "live";
    await fetch("/mode", { method: "POST", body: JSON.stringify({ mode: next }) });
  });

  // Which agent's tab you're VIEWING (history + character). May differ from
  // the LIVE agent (the one currently listening). null = follow the live one.
  let viewedAgent = null;
  // Once you click a tab it's PINNED: the view stops auto-following the active
  // agent. Without this, two live sessions flipping active make the view jump
  // and briefly show both agents' cards at once.
  let pinnedView = false;
  let speakingSet = [];  // agents currently playing audio (may be a background tab)
  let agentLabels = {};  // agent id -> human label (session /rename title)

  function renderTabs(agents, active) {
    const names = Object.keys(agents).sort();
    const tabs = document.getElementById("tabs");
    tabs.hidden = names.length < 1;
    if (tabs.hidden) { viewedAgent = null; pinnedView = false; return; }
    // Follow the active agent only until the user pins a tab by clicking.
    if (!pinnedView) viewedAgent = active;
    if (!names.includes(viewedAgent)) { viewedAgent = active; pinnedView = false; }
    tabs.innerHTML = "";
    for (const name of names) {
      const b = document.createElement("button");
      const speaking = speakingSet.includes(name);
      const label = agentLabels[name] || name;
      // Speaker icon (flashing) when THIS agent is talking — even if you're on
      // another tab, so you see e.g. personal replying while viewing work.
      b.innerHTML = '<span class="live-dot"></span>' + label +
        (speaking ? '<span class="tab-speaking">🔊</span>' : "");
      if (name === viewedAgent) b.classList.add("viewing");
      if (name === active) b.classList.add("live");
      if (speaking) b.classList.add("is-speaking");
      b.addEventListener("click", () => {
        if (viewedAgent === name) return;
        viewedAgent = name;
        pinnedView = true;  // stop auto-following active from now on
        // Respond instantly: clear the old agent's cards and repaint tabs now,
        // don't wait for the round-trip (that's what felt laggy).
        for (const [k, node] of seen) { node.remove(); seen.delete(k); }
        renderTabs(agents, active);
        loadCharacter();  // show this agent's own sliders
        tick();
        // Clicking a tab both views it AND makes it the live (listening) agent.
        fetch("/active-agent", { method: "POST", body: JSON.stringify({ name }) });
      });
      tabs.appendChild(b);
    }
    document.getElementById("character-for").textContent =
      names.length > 1 ? "· " + viewedAgent : "";
  }

  let currentSmartMode = null;
  function setSmartMode(mode) {
    currentSmartMode = mode;
    const label = document.getElementById("smart-mode-label");
    label.textContent = mode === "hard" ? "hard (pause split)" : "soft (smart turn)";
  }

  let currentTtsMode = null;
  document.getElementById("tts-toggle").addEventListener("click", async () => {
    const next = currentTtsMode === "live" ? "batch" : "live";
    await fetch("/settings", { method: "POST", body: JSON.stringify({ tts_mode: next }) });
  });
  function setTtsMode(mode) {
    currentTtsMode = mode;
    const label = document.getElementById("tts-label");
    label.textContent = mode;
    label.className = mode === "live" ? "live" : "";
  }

  let currentMuted = false;
  document.getElementById("mute-toggle").addEventListener("click", async () => {
    await fetch("/mute", { method: "POST", body: JSON.stringify({ muted: !currentMuted }) });
  });
  function setMuted(muted) {
    currentMuted = muted;
    const label = document.getElementById("mute-label");
    label.textContent = muted ? "muted" : "listening";
    label.style.color = muted ? "var(--red)" : "";
  }
  function setMode(mode) {
    currentMode = mode;
    const label = document.getElementById("mode-label");
    label.textContent = mode;
    label.className = mode === "live" ? "live" : "";
  }

  async function tick() {
    try {
      const s = await (await fetch("/status")).json();
      document.getElementById("queued").textContent = s.queued;
      const costs = s.session_cost_usd || {};
      const total = (costs.user || 0) + (costs.claude || 0);
      document.getElementById("cost").textContent = fmtCost(total);
      document.getElementById("cost").title =
        "you " + fmtCost(costs.user || 0) + " · Claude " + fmtCost(costs.claude || 0);
      const creditsChip = document.getElementById("credits-chip");
      if (s.credits_usd != null) {
        creditsChip.hidden = false;
        document.getElementById("credits").textContent = "$" + s.credits_usd.toFixed(2);
      }
      speakingSet = s.speaking_agents || [];
      agentLabels = s.agent_labels || {};
      renderTabs(s.agents || {}, s.active_agent);
      setMode(s.mode || "batch");
      setTtsMode(s.tts_mode || "batch");
      setSmartMode(s.smart_turn_mode || "soft");
      setMuted(!!s.muted);
      const silence = document.getElementById("ch-silence");
      if (s.end_silence_ms && document.activeElement !== silence) {
        silence.value = s.end_silence_ms;
        document.getElementById("ch-silence-val").textContent =
          (s.end_silence_ms / 1000).toFixed(1) + "s";
      }
      const smart = document.getElementById("ch-smart");
      if (s.smart_turn != null && document.activeElement !== smart) {
        smart.value = s.smart_turn;
        document.getElementById("ch-smart-val").textContent =
          s.smart_turn === 0 ? "off" : Number(s.smart_turn).toFixed(1);
      }
      const lang = document.getElementById("ch-language");
      if (s.language != null && document.activeElement !== lang) {
        lang.value = s.language;
      }
      if (s.muted) setState("offline", "muted by you — mic ignored");
      else if (!s.listening) setState("muted", "muted — Claude is speaking");
      else if (s.recording) setState("recording", "recording your utterance");
      else setState("listening", "listening");
      // The daemon owns the character (Claude can change_voice at any time)
      // — keep the panel mirroring it. loadCharacter skips itself while a
      // slider is mid-drag, so this never fights the user's hand.
      await loadCharacter();
      // Show only the viewed agent's history (or everything in single-agent mode).
      const q = viewedAgent ? "?agent=" + encodeURIComponent(viewedAgent) : "";
      const data = await (await fetch("/utterances" + q)).json();
      const live = new Set(data.utterances.map((u) => cardKey(u)));
      // Drop cards that don't belong to the viewed agent (e.g. after switching tabs).
      for (const [key, node] of seen) {
        if (!live.has(key)) { node.remove(); seen.delete(key); }
      }
      for (const u of data.utterances) upsert(u);
    } catch {
      setState("offline", "daemon not responding");
    }
  }
  tick();
  setInterval(tick, 400);
</script>
</body>
</html>
"""
