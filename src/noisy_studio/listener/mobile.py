"""Standalone mobile dashboard: big touch buttons to switch the active agent.

Served by a tiny separate process (see mobile_server), NOT by the listener
daemon — so it can be built and restarted without touching the daemon (which
would force the running agents to reconnect). It talks to the daemon's HTTP
API on localhost for state and switching.
"""

MOBILE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Noisy Studio — switch agent</title>
<style>
  :root {
    --bg: #15171B; --surface: #1D2026; --ink: #E9E7E1; --muted: #9A968C;
    --line: #2D3038; --teal: #2FC4A7; --teal-soft: #16332E; --violet: #A88BE0;
    --violet-soft: #2A2438; --red: #E06A5D;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: system-ui, -apple-system, sans-serif;
    min-height: 100dvh; display: flex; flex-direction: column;
    padding: env(safe-area-inset-top) 16px env(safe-area-inset-bottom);
  }
  header { text-align: center; padding: 18px 0 10px; }
  header h1 { margin: 0; font-size: 1.1rem; font-weight: 650; }
  header .status { color: var(--muted); font-size: 0.82rem; margin-top: 4px; }
  header .status .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--muted); margin-right: 5px; vertical-align: middle; }
  header .status.listening .dot { background: var(--teal); }
  header .status.recording .dot { background: var(--violet); animation: pulse 0.7s infinite; }
  header .status.offline .dot { background: var(--red); }
  @keyframes pulse { 50% { opacity: 0.3; } }

  #agents { flex: 1; display: flex; flex-direction: column; gap: 14px; padding: 10px 0 20px; }
  button.agent {
    flex: 1; min-height: 96px; border-radius: 20px; border: 2px solid var(--line);
    background: var(--surface); color: var(--ink); font: inherit;
    font-size: 1.6rem; font-weight: 700; cursor: pointer;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
    transition: border-color .1s, background .1s;
  }
  button.agent .sub { font-size: 0.8rem; font-weight: 500; color: var(--muted); }
  button.agent.active { border-color: var(--teal); background: var(--teal-soft); }
  button.agent.active .sub { color: var(--teal); }
  button.agent .speaking { font-size: 0.85rem; color: var(--violet); }
  button.agent:active { transform: scale(0.98); }
  .empty { color: var(--muted); text-align: center; margin: auto; font-size: 0.95rem; }
</style>
</head>
<body>
  <header>
    <h1>Noisy Studio</h1>
    <div class="status" id="status"><span class="dot"></span><span id="status-label">connecting…</span></div>
  </header>
  <div id="agents"><div class="empty" id="empty">Waiting for agents to register…</div></div>
<script>
  async function switchTo(name) {
    try { await fetch("/api/active-agent", { method: "POST", body: JSON.stringify({ name }) }); }
    catch {}
    tick();
  }
  function setStatus(cls, label) {
    const s = document.getElementById("status");
    s.className = "status " + cls;
    document.getElementById("status-label").textContent = label;
  }
  const seen = {};
  async function tick() {
    let s;
    try { s = await (await fetch("/api/status")).json(); }
    catch { setStatus("offline", "daemon offline"); return; }
    if (s.muted) setStatus("offline", "muted");
    else if (s.recording) setStatus("recording", "recording you");
    else if (s.listening) setStatus("listening", "listening · " + (s.active_agent || "—"));
    else setStatus("", "idle");
    const names = Object.keys(s.agents || {}).sort();
    const box = document.getElementById("agents");
    if (!names.length) { box.innerHTML = '<div class="empty">Waiting for agents to register…</div>'; return; }
    if (box.querySelector(".empty")) box.innerHTML = "";
    // Rebuild only if the set of agents changed; else just update classes.
    const key = names.join(",");
    if (box.dataset.key !== key) {
      box.dataset.key = key; box.innerHTML = "";
      const labels = s.agent_labels || {};
      for (const name of names) {
        const b = document.createElement("button");
        b.className = "agent"; b.dataset.name = name;
        b.innerHTML = (labels[name] || name) +
          '<span class="sub"></span><span class="speaking"></span>';
        b.addEventListener("click", () => switchTo(name));
        box.appendChild(b);
      }
    }
    const speaking = s.speaking_agents || [];
    for (const b of box.querySelectorAll("button.agent")) {
      const name = b.dataset.name;
      b.classList.toggle("active", name === s.active_agent);
      b.querySelector(".sub").textContent = name === s.active_agent ? "listening to you" : "tap to switch";
      b.querySelector(".speaking").textContent = speaking.includes(name) ? "🔊 speaking…" : "";
    }
  }
  tick();
  setInterval(tick, 500);
</script>
</body>
</html>
"""
