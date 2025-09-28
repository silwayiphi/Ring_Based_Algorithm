// ---------- tiny fetch helpers ----------
async function jget(u){ const r = await fetch(u); return r.json(); }
async function jpost(u,b={}){ const r = await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}); return r.json(); }

// ---------- elements ----------
const ringDiv = document.getElementById("ring");
const ringLeaderEl = document.getElementById("ringLeader");
const traceDiv = document.getElementById("trace");

const commitIdxEl = document.getElementById("commitIdx");
const paxosLogEl = document.getElementById("paxosLog");
const acceptorsEl = document.getElementById("acceptors");
const paxosTraceEl = document.getElementById("paxosTrace");

let ringES = null;

// ---------- ring visualization ----------
function layoutRing(nodes, leaderId){
  if (!ringDiv) return;
  ringDiv.innerHTML = "";
  const cx = 270, cy = 150, R = 110;
  nodes.forEach((n,i)=>{
    const a = (2*Math.PI*i)/nodes.length - Math.PI/2;
    const x = cx + R*Math.cos(a), y = cy + R*Math.sin(a);
    const el = document.createElement("div");
    // include .dead if node is not alive (crashed)
    el.className = `node ${n.alive ? "" : "dead"} ${n.participant?"participant":""} ${(n.elected!=null)?"elected":""} ${n.id===leaderId?"leader":""}`;
    el.style.left = (x-32)+"px"; el.style.top = (y-32)+"px";
    el.textContent = n.id;
    ringDiv.append(el);
  });
}
function highlightNode(id, on=true){
  ringDiv?.querySelectorAll(".node").forEach(n=>{
    if (Number(n.textContent.trim()) === id) n.classList.toggle("active", on);
  });
}
function ringLog(line){
  if (!traceDiv) return;
  const d = document.createElement("div");
  d.textContent = line;
  traceDiv.prepend(d);
  while (traceDiv.children.length > 180) traceDiv.removeChild(traceDiv.lastChild);
}

// ---------- paxos rendering ----------
function paxosLog(line){
  if (!paxosTraceEl) return;
  const d = document.createElement("div");
  d.textContent = line;
  paxosTraceEl.prepend(d);
  while (paxosTraceEl.children.length > 180) paxosTraceEl.removeChild(paxosTraceEl.lastChild);
}
function renderPaxos(state){
  // commit index
  if (commitIdxEl) commitIdxEl.textContent = `commitIndex: ${state.commitIndex}`;

  // acceptors list
  if (acceptorsEl){
    acceptorsEl.innerHTML = "";
    (state.acceptors || []).forEach(a=>{
      const card = document.createElement("div");
      card.className = "card" + (a.alive ? "" : " down");
      card.innerHTML = `
        <h4>${a.name} ${a.alive ? "" : "(down)"}</h4>
        <div class="kv">promised=${a.promised}</div>
        <div class="kv">accepted=${a.accepted===null?"—":JSON.stringify(a.accepted)}</div>
        <div class="btns">
          <button data-pcrash="${a.name}">Crash</button>
          <button data-precover="${a.name}">Recover</button>
        </div>
      `;
      acceptorsEl.append(card);
    });
  }

  // chosen log
  if (paxosLogEl){
    paxosLogEl.innerHTML = "";
    const entries = Object.entries(state.log || {}).map(([k,v])=>[Number(k),v]).sort((a,b)=>a[0]-b[0]);
    for (const [idx, val] of entries){
      const li = document.createElement("li");
      li.textContent = `#${idx}: ${val}`;
      paxosLogEl.append(li);
    }
  }
}

// ---------- refresh both panels ----------
async function refresh(){
  try{
    const rs = await jget("/api/ring/state");
    layoutRing(rs.nodes, rs.leaderId);
    if (ringLeaderEl) ringLeaderEl.textContent = `Leader: ${rs.leaderId ?? "—"}`;
  }catch{}
  try{
    const ps = await jget("/api/paxos/state");
    renderPaxos(ps);
  }catch{}
}

// ---------- animated ring: JSON fallback ----------
async function animateFromTraceJSON(init, delay){
  try{
    const url = init ? `/api/ring/trace?initiator=${encodeURIComponent(init)}` : `/api/ring/trace`;
    const tr = await jget(url);
    if (!tr.ok){ ringLog(`ERROR: ${tr.reason||"trace failed"}`); return; }

    traceDiv.innerHTML = "";
    ringDiv.querySelectorAll(".node").forEach(n=> n.classList.remove("active"));

    for (const s of tr.steps){
      if (s.type === "start"){
        highlightNode(s.who, true);
        ringLog(`START: P${s.who} marks participant and sends ELECTION(j=${s.who})`);
      }
      if (s.type === "hop"){
        highlightNode(s.frm, false); highlightNode(s.to, true);
        if (s.compare.startsWith("j<me & non-participant")){
          ringLog(`RECV at P${s.to}: j=${s.j_in} < own ⇒ replace with ${s.action.split('-with-')[1]} & forward`);
        } else if (s.compare === "j>me"){
          ringLog(`RECV at P${s.to}: j=${s.j_in} > own ⇒ forward unchanged`);
        } else {
          ringLog(`RECV at P${s.to}: j=${s.j_in} < own (already participant) ⇒ forward unchanged`);
        }
        await new Promise(r=> setTimeout(r, Math.max(0, delay)));
      }
      if (s.type === "winner"){
        highlightNode(s.who, true);
        if (ringLeaderEl) ringLeaderEl.textContent = `Leader: ${s.who}`;
        ringLog(`WINNER: P${s.who} (saw its own id)`);
      }
      if (s.type === "coord"){
        ringLog(`COORDINATOR(k=${s.leader}) flows: P${s.frm} → P${s.to}; P${s.to} sets elected=${s.leader} & non-participant`);
        await new Promise(r=> setTimeout(r, Math.max(0, delay)));
      }
      if (s.type === "end"){
        ringLog(`ELECTION COMPLETE (leader=${s.leader})`);
      }
    }
    refresh();
  }catch(e){ ringLog(`ERROR: ${e.message||e}`); }
}

// ---------- wire events ----------
function wire(){
  // RING buttons
  document.getElementById("animate").onclick = ()=>{
    const init = document.getElementById("initiator").value.trim();
    const delay = Number(document.getElementById("delay").value || "400");
    const url = init
      ? `/stream/ring/election?initiator=${encodeURIComponent(init)}&delay=${delay}`
      : `/stream/ring/election?delay=${delay}`;

    traceDiv.innerHTML = "";
    ringDiv.querySelectorAll(".node").forEach(n=> n.classList.remove("active"));

    try{ if (ringES) ringES.close(); }catch{}
    let fellBack = false;
    ringES = new EventSource(url);
    ringES.onmessage = ev=>{
      try{
        const m = JSON.parse(ev.data);
        if (m.type === "start"){
          highlightNode(m.who, true);
          ringLog(`START: P${m.who} marks participant and sends ELECTION(j=${m.who})`);
        } else if (m.type === "hop"){
          highlightNode(m.frm, false); highlightNode(m.to, true);
          if (m.compare.startsWith("j<me & non-participant")){
            ringLog(`RECV at P${m.to}: j=${m.j_in} < own ⇒ replace with ${m.action.split('-with-')[1]} & forward`);
          } else if (m.compare === "j>me"){
            ringLog(`RECV at P${m.to}: j=${m.j_in} > own ⇒ forward unchanged`);
          } else {
            ringLog(`RECV at P${m.to}: j=${m.j_in} < own (already participant) ⇒ forward unchanged`);
          }
        } else if (m.type === "winner"){
          highlightNode(m.who, true);
          if (ringLeaderEl) ringLeaderEl.textContent = `Leader: ${m.who}`;
          ringLog(`WINNER: P${m.who} (saw its own id)`);
        } else if (m.type === "coord"){
          ringLog(`COORDINATOR(k=${m.leader}) flows: P${m.frm} → P${m.to}; P${m.to} sets elected=${m.leader} & non-participant`);
        } else if (m.type === "end"){
          ringLog("ELECTION COMPLETE");
          try{ ringES.close(); }catch{}
          refresh();
        } else if (m.type === "error"){
          throw new Error(m.reason||"SSE error");
        }
      }catch(e){
        if (!fellBack){
          fellBack = true;
          try{ ringES.close(); }catch{}
          const initVal = document.getElementById("initiator").value.trim();
          const delayVal = Number(document.getElementById("delay").value || "400");
          animateFromTraceJSON(initVal, delayVal);
        }
      }
    };
    ringES.onerror = ()=>{
      if (!fellBack){
        try{ ringES.close(); }catch{}
        const initVal = document.getElementById("initiator").value.trim();
        const delayVal = Number(document.getElementById("delay").value || "400");
        animateFromTraceJSON(initVal, delayVal);
      }
    };
  };

  document.getElementById("fast").onclick = async ()=>{
    const init = document.getElementById("initiator").value.trim();
    await jpost("/api/ring/fast", init ? {initiator:Number(init)} : {});
    ringLog("FAST election executed");
    refresh();
  };

  document.getElementById("reset").onclick = async ()=>{
    await jpost("/api/ring/reset");
    traceDiv.innerHTML = "";
    ringLog("Reset: participant=false, elected cleared, leader cleared");
    refresh();
  };

  document.querySelectorAll("[data-crash]").forEach(b=>{
    b.onclick = ()=> jpost(`/api/ring/crash/${b.dataset.crash}`).then(()=>{ ringLog(`Crashed ${b.dataset.crash}`); refresh(); });
  });
  document.querySelectorAll("[data-recover]").forEach(b=>{
    b.onclick = ()=> jpost(`/api/ring/recover/${b.dataset.recover}`).then(()=>{ ringLog(`Recovered ${b.dataset.recover}`); refresh(); });
  });

  // PAXOS propose
  document.getElementById("propose").onclick = async () => {
    const cmd = (document.getElementById("cmd").value || "").trim() || "NOOP";

    // backend will also auto-elect, but this gives a smoother UX
    const st = await jget("/api/ring/state");
    const lid = st.leaderId;
    const aliveLeader = lid && st.nodes.find(n => n.id === lid && n.alive);
    if (!aliveLeader) {
      await jpost("/api/ring/fast", {}); // quick election
    }

    const res = await jpost("/api/paxos/propose", { command: cmd });
    if (!res.ok) {
      logPaxos(`PROPOSE failed: ${res.reason || "unknown"}`);
      return;
    }
    logPaxos(`PROPOSED by ${res.proposerName} → chosen="${res.chosen}" at slot #${res.slot}`);
    refreshPaxos(); // your existing refresh
  };


  // PAXOS crash/recover via event delegation
  acceptorsEl.addEventListener("click", async (e)=>{
    const t = e.target;
    if (!(t instanceof HTMLElement)) return;
    if (t.dataset.pcrash){
      const res = await jpost(`/api/paxos/crash/${t.dataset.pcrash}`);
      paxosLog(`CRASH: ${t.dataset.pcrash}`);
      renderPaxos(res);
    }
    if (t.dataset.precover){
      const res = await jpost(`/api/paxos/recover/${t.dataset.precover}`);
      paxosLog(`RECOVER: ${t.dataset.precover}`);
      renderPaxos(res);
    }
  });
}

wire();
refresh();
setInterval(refresh, 2000);
