// ---------- tiny fetch helpers ----------
async function jget(u){ const r = await fetch(u); return r.json(); }
async function jpost(u,b={}){ const r = await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}); return r.json(); }

// ---------- elements ----------
const ringDiv = document.getElementById("ring");
const traceDiv = document.getElementById("trace");
const ringLeaderEl = document.getElementById("ringLeader");
let ringES = null;

// ---------- ring visualization ----------
function layoutRing(nodes, leaderId){
  if (!ringDiv) return;
  ringDiv.innerHTML = "";
  const cx = 260, cy = 140, R = 105;
  nodes.forEach((n, i)=>{
    const angle = (2*Math.PI*i)/nodes.length - Math.PI/2;
    const x = cx + R*Math.cos(angle), y = cy + R*Math.sin(angle);
    const el = document.createElement("div");
    el.className = `node ${n.alive?"":"dead"} ${n.participant?"participant":""} ${(n.elected!=null)?"elected":""} ${n.id===leaderId?"leader":""}`;
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
function logTrace(text){
  if (!traceDiv) return;
  const d = document.createElement("div");
  d.textContent = text;
  traceDiv.prepend(d);
  while (traceDiv.children.length > 160) traceDiv.removeChild(traceDiv.lastChild);
}

// ---------- refresh ----------
async function refresh(){
  const st = await jget("/api/ring/state");
  layoutRing(st.nodes, st.leaderId);
  ringLeaderEl.textContent = `Leader: ${st.leaderId ?? "—"}`;
}

// ---------- animated: JSON fallback ----------
async function animateFromTraceJSON(init, delay){
  const url = init ? `/api/ring/trace?initiator=${encodeURIComponent(init)}` : `/api/ring/trace`;
  const tr = await jget(url);
  if (!tr.ok){ logTrace(`ERROR: ${tr.reason||"trace failed"}`); return; }

  traceDiv.innerHTML = "";
  ringDiv.querySelectorAll(".node").forEach(n=> n.classList.remove("active"));

  for (const s of tr.steps){
    if (s.type === "start"){
      highlightNode(s.who, true);
      logTrace(`START: P${s.who} marks participant and sends ELECTION(j=${s.who})`);
    }
    if (s.type === "hop"){
      highlightNode(s.frm, false); highlightNode(s.to, true);
      if (s.compare.startsWith("j<me & non-participant")){
        logTrace(`RECV at P${s.to}: j=${s.j_in} < own ⇒ replace with ${s.action.split('-with-')[1]} & forward`);
      } else if (s.compare === "j>me"){
        logTrace(`RECV at P${s.to}: j=${s.j_in} > own ⇒ forward unchanged`);
      } else {
        logTrace(`RECV at P${s.to}: j=${s.j_in} < own (already participant) ⇒ forward unchanged`);
      }
      await new Promise(r=> setTimeout(r, Math.max(0, delay)));
    }
    if (s.type === "winner"){
      highlightNode(s.who, true);
      ringLeaderEl.textContent = `Leader: ${s.who}`;
      logTrace(`WINNER: P${s.who} (saw its own id)`);
    }
    if (s.type === "coord"){
      logTrace(`COORDINATOR(k=${s.leader}) flows: P${s.frm} → P${s.to}; P${s.to} sets elected=${s.leader} & non-participant`);
      await new Promise(r=> setTimeout(r, Math.max(0, delay)));
    }
    if (s.type === "end"){
      logTrace(`ELECTION COMPLETE (leader=${s.leader})`);
    }
  }
  refresh();
}

// ---------- wire ----------
function wire(){
  document.getElementById("animate").onclick = ()=>{
    const init = document.getElementById("initiator").value.trim();
    const delay = Number(document.getElementById("delay").value || "400");
    // prefer SSE; fall back to JSON if SSE errors
    const url = init
      ? `/stream/ring/election?initiator=${encodeURIComponent(init)}&delay=${delay}`
      : `/stream/ring/election?delay=${delay}`;

    traceDiv.innerHTML = "";
    ringDiv.querySelectorAll(".node").forEach(n=> n.classList.remove("active"));

    try { if (ringES) ringES.close(); } catch {}
    let fellBack = false;
    ringES = new EventSource(url);

    ringES.onmessage = (ev)=>{
      try{
        const m = JSON.parse(ev.data);
        if (m.type === "start"){
          highlightNode(m.who, true);
          logTrace(`START: P${m.who} marks participant and sends ELECTION(j=${m.who})`);
        } else if (m.type === "hop"){
          highlightNode(m.frm, false); highlightNode(m.to, true);
          if (m.compare.startsWith("j<me & non-participant")){
            logTrace(`RECV at P${m.to}: j=${m.j_in} < own ⇒ replace with ${m.action.split('-with-')[1]} & forward`);
          } else if (m.compare === "j>me"){
            logTrace(`RECV at P${m.to}: j=${m.j_in} > own ⇒ forward unchanged`);
          } else {
            logTrace(`RECV at P${m.to}: j=${m.j_in} < own (already participant) ⇒ forward unchanged`);
          }
        } else if (m.type === "winner"){
          highlightNode(m.who, true);
          ringLeaderEl.textContent = `Leader: ${m.who}`;
          logTrace(`WINNER: P${m.who} (saw its own id)`);
        } else if (m.type === "coord"){
          logTrace(`COORDINATOR(k=${m.leader}) flows: P${m.frm} → P${m.to}; P${m.to} sets elected=${m.leader} & non-participant`);
        } else if (m.type === "end"){
          logTrace("ELECTION COMPLETE");
          try { ringES.close(); } catch {}
          refresh();
        } else if (m.type === "error"){
          throw new Error(m.reason||"SSE error");
        }
      }catch(e){
        if (!fellBack){
          fellBack = true;
          try { ringES.close(); } catch {}
          animateFromTraceJSON(init, delay);
        }
      }
    };
    ringES.onerror = ()=>{
      if (!fellBack){
        try { ringES.close(); } catch {}
        animateFromTraceJSON(init, delay);
      }
    };
  };

  document.getElementById("fast").onclick = async ()=>{
    const init = document.getElementById("initiator").value.trim();
    await jpost("/api/ring/fast", init ? {initiator: Number(init)} : {});
    logTrace("FAST election executed");
    refresh();
  };

  document.getElementById("reset").onclick = async ()=>{
    await jpost("/api/ring/reset");
    traceDiv.innerHTML = "";
    logTrace("Reset: participant=false, elected cleared, leader cleared");
    refresh();
  };

  document.querySelectorAll("[data-crash]").forEach(b=>{
    b.onclick = ()=> jpost(`/api/ring/crash/${b.dataset.crash}`)
      .then(()=>{ logTrace(`Crashed ${b.dataset.crash}`); refresh(); });
  });
  document.querySelectorAll("[data-recover]").forEach(b=>{
    b.onclick = ()=> jpost(`/api/ring/recover/${b.dataset.recover}`)
      .then(()=>{ logTrace(`Recovered ${b.dataset.recover}`); refresh(); });
  });
}

// ---------- init ----------
wire();
refresh();
setInterval(refresh, 2000);
