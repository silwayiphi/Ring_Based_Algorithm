/* app.js - per-user package tracker
   - no datacenter ops shown
   - users only see their packages
   - package logs persist in localStorage
*/

(function () {
  // -----------------------------
  // CONFIG
  // -----------------------------
  const USERS = {
    alice: { password: "pass123", packages: ["PKG-A-1001", "PKG-A-1002"] },
    bob: { password: "hunter2", packages: ["PKG-B-2001", "PKG-B-2002"] },
    charlie: { password: "charlie123", packages: ["PKG-C-3001"] }
  };

  const STATUS_FLOW = ["in_transit", "out_for_delivery", "delivered"];
  const STATUS_COLORS = {
    in_transit: "#3b82f6",
    out_for_delivery: "#f97316",
    delivered: "#10b981"
  };

  const BASE_DURATIONS = {
    in_transit_min: 300, in_transit_max: 900,
    out_for_delivery_min: 1200, out_for_delivery_max: 2400
  };

  let speedFactor = 0.05;
  let currentUser = null;

  // logs and states will load from localStorage
  let PACKAGE_LOGS = {};
  let PACKAGE_STATE = {};

  // -----------------------------
  // DOM HELPERS
  // -----------------------------
  function $(sel) { return document.querySelector(sel); }

  function ensureDOM() {
    if (!$("#app-root")) {
      document.body.innerHTML = `
        <div id="app-root" class="container">
          <header style="display:flex;justify-content:space-between;align-items:center">
            <h1>My Packages</h1>
            <div id="auth-area"></div>
          </header>
          <section><h2>Packages</h2><div id="package-cards"></div></section>
          <section><h2>Timeline</h2><ul id="events"></ul></section>
          <section><h2>Lookup</h2>
            <input id="lookup-id" placeholder="Package ID"/><button id="lookup">Lookup</button>
            <div id="lookup-result"></div>
          </section>
        </div>
        <style>
          body { font-family: sans-serif; background:#f9fafb; margin:0; }
          .container { max-width:800px; margin:auto; padding:20px; }
          .package-card, .timeline-entry {
            background:#fff; border-radius:12px; padding:12px; margin:8px 0;
            box-shadow:0 2px 6px rgba(0,0,0,0.08);
          }
          .status-label { padding:4px 8px; border-radius:6px; color:#fff; font-size:12px; }
        </style>
      `;
    }
  }

  function renderAuth() {
    const area = $("#auth-area");
    area.innerHTML = "";
    if (!currentUser) {
      const btn = document.createElement("button");
      btn.textContent = "Login";
      btn.onclick = loginPrompt;
      area.appendChild(btn);
    } else {
      area.innerHTML = `<span>Logged in as <b>${currentUser}</b></span>
                        <button id="logout">Logout</button>`;
      $("#logout").onclick = logout;
    }
  }

  function renderPackageCards() {
    const wrap = $("#package-cards");
    wrap.innerHTML = "";
    if (!currentUser) {
      wrap.innerHTML = "<p>Login to see packages</p>";
      return;
    }
    USERS[currentUser].packages.forEach(pkg => {
      const events = PACKAGE_LOGS[pkg] || [];
      const latest = events[events.length - 1];
      wrap.innerHTML += `<div class="package-card">
        <h4>${pkg}</h4>
        <p>Status: ${latest ? latest.status : "pending"}</p>
      </div>`;
    });
  }

  // -----------------------------
  // AUTH
  // -----------------------------
  function loginPrompt() {
    const u = prompt("Username:");
    const p = prompt("Password:");
    if (USERS[u] && USERS[u].password === p) {
      currentUser = u;
      localStorage.setItem("loggedUser", u);
      loadUserLogs();
      renderAuth(); renderPackageCards(); renderTimeline();
    } else {
      alert("Invalid credentials");
    }
  }

  function logout() {
    saveUserLogs();
    currentUser = null;
    localStorage.removeItem("loggedUser");
    renderAuth(); renderPackageCards();
    $("#events").innerHTML = "";
    $("#lookup-result").innerHTML = "";
  }

  function restoreLogin() {
    const saved = localStorage.getItem("loggedUser");
    if (saved && USERS[saved]) {
      currentUser = saved;
      loadUserLogs();
    }
  }

  // -----------------------------
  // STORAGE HELPERS
  // -----------------------------
  function saveUserLogs() {
    if (!currentUser) return;
    localStorage.setItem(`logs_${currentUser}`, JSON.stringify(PACKAGE_LOGS));
    localStorage.setItem(`state_${currentUser}`, JSON.stringify(PACKAGE_STATE));
  }

  function loadUserLogs() {
    if (!currentUser) return;
    PACKAGE_LOGS = JSON.parse(localStorage.getItem(`logs_${currentUser}`) || "{}");
    PACKAGE_STATE = JSON.parse(localStorage.getItem(`state_${currentUser}`) || "{}");

    // init if empty
    USERS[currentUser].packages.forEach(pkg => {
      if (!PACKAGE_LOGS[pkg]) PACKAGE_LOGS[pkg] = [];
      if (!PACKAGE_STATE[pkg]) PACKAGE_STATE[pkg] = { index: 0, delivered: false };
    });
  }

  // -----------------------------
  // SIMULATION
  // -----------------------------
  function emitEvent(pkgId, status) {
    const ev = { status, ts: Date.now()/1000 };
    PACKAGE_LOGS[pkgId].push(ev);
    saveUserLogs();

    if (currentUser && USERS[currentUser].packages.includes(pkgId)) {
      const li = document.createElement("li");
      li.className = "timeline-entry";
      li.innerHTML = `<span class="status-label" style="background:${STATUS_COLORS[status]}">${status}</span>
                      <span>${pkgId} • ${new Date(ev.ts*1000).toLocaleString()}</span>`;
      $("#events").prepend(li);
      renderPackageCards();
    }
  }

  function scheduleStep(pkgId) {
    const state = PACKAGE_STATE[pkgId];
    if (!state || state.delivered) return;

    const idx = state.index;
    const status = STATUS_FLOW[idx];
    emitEvent(pkgId, status);

    if (status === "delivered") {
      state.delivered = true;
      saveUserLogs();
      return;
    }

    state.index++;
    let dur = 0;
    if (status === "in_transit") dur = randDur(BASE_DURATIONS.in_transit_min, BASE_DURATIONS.in_transit_max);
    else if (status === "out_for_delivery") dur = randDur(BASE_DURATIONS.out_for_delivery_min, BASE_DURATIONS.out_for_delivery_max);

    setTimeout(() => scheduleStep(pkgId), dur*1000);
  }

  function randDur(min,max){ return (min + Math.random()*(max-min))*speedFactor; }

  function startSim() {
    if (!currentUser) return;
    USERS[currentUser].packages.forEach((pkg,i) => {
      const state = PACKAGE_STATE[pkg];
      if (!state.delivered) {
        setTimeout(() => scheduleStep(pkg), 2000 + i*1500);
      }
    });
  }

  // -----------------------------
  // LOOKUP
  // -----------------------------
 // -----------------------------
// LOOKUP
// -----------------------------
function wireLookup() {
  $("#lookup").onclick = () => {
    if (!currentUser) return alert("Login first");

    const pkg = $("#lookup-id").value.trim();
    if (!USERS[currentUser].packages.includes(pkg)) {
      $("#lookup-result").innerHTML = `<p style="color:#ef4444">🚫 Not your package</p>`;
      return;
    }

    const logs = PACKAGE_LOGS[pkg];
    if (!logs || logs.length === 0) {
      $("#lookup-result").innerHTML = `<p style="color:#6b7280">No events yet for ${pkg}</p>`;
      return;
    }

    $("#lookup-result").innerHTML = `
      <h3>Tracking history for <span style="color:#3b82f6">${pkg}</span></h3>
      <div class="lookup-timeline">
        ${logs.map(e => `
          <div class="history-entry">
            <span class="status-label" style="background:${STATUS_COLORS[e.status]}">${e.status}</span>
            <span class="timestamp">${new Date(e.ts*1000).toLocaleString()}</span>
          </div>
        `).join("")}
      </div>
    `;
  };
}

  function renderTimeline() {
    if (!currentUser) return;
    $("#events").innerHTML = "";
    USERS[currentUser].packages.forEach(pkg => {
      PACKAGE_LOGS[pkg].forEach(e => {
        const li = document.createElement("li");
        li.className = "timeline-entry";
        li.innerHTML = `<span class="status-label" style="background:${STATUS_COLORS[e.status]}">${e.status}</span>
                        <span>${pkg} • ${new Date(e.ts*1000).toLocaleString()}</span>`;
        $("#events").prepend(li);
      });
    });
  }

  // -----------------------------
  // INIT
  // -----------------------------
  document.addEventListener("DOMContentLoaded", () => {
    ensureDOM();
    restoreLogin();
    renderAuth();
    renderPackageCards();
    renderTimeline();
    wireLookup();
    startSim();
  });

})();
