async function jget(u){ const r = await fetch(u); return r.json(); }
async function jpost(u,b={}){ const r = await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}); return r.json(); }

const ringDiv = document.getElementById("ring");
const commitIdx = document.getElementById("commitIdx");
const consistency = document.getElementById("consistency");
const ringLeader = document.getElementById("ringLeader");

function layoutRing(nodes, leaderId){
  ringDiv.innerHTML = "";
  const cx=180, cy=90, R=70;
  nodes.forEach((n, i)=>{
    const angle = (2*Math.PI*i)/nodes.length - Math.PI/2;
    const x = cx + R*Math.cos(angle), y = cy + R*Math.sin(angle);
    const el = document.createElement("div");
    el.className = "node " + (n.alive?"alive":"dead") + (n.id===leaderId?" leader":"");
    el.style.left = (x-24)+"px"; el.style.top = (y-24)+"px";
    el.textContent = n.id;
    ringDiv.appendChild(el);
  });
}

async function refresh(){
  const rs = await jget("/api/ring/state");
  layoutRing(rs.nodes, rs.leaderId);
  ringLeader.textContent = "Leader: " + (rs.leaderId ?? "—");

  const ps = await jget("/api/paxos/state");
  commitIdx.textContent = "commitIndex: " + ps.commitIndex;
  consistency.textContent = "CONSISTENCY: " + (ps.consistent ? "OK" : "WARN");
  consistency.className = "badge " + (ps.consistent ? "ok" : "warn");
  for (const name of ["EU","US","APAC"]){
    const card = document.getElementById("acc-"+name);
    const acc = ps.acceptors.find(a=>a.name===name);
    card.classList.toggle("down", !acc.alive);
    card.innerHTML = `<strong>${name}</strong><br>alive=${acc.alive}<br>accepted=${JSON.stringify(acc.accepted)}`;
  }
}

function wire(){
  document.getElementById("ringStart").onclick = ()=> jpost("/api/ring/start").then(refresh);
  document.querySelectorAll("[data-crash]").forEach(b=> b.onclick = ()=> jpost(`/api/ring/crash/${b.dataset.crash}`).then(refresh));
  document.querySelectorAll("[data-recover]").forEach(b=> b.onclick = ()=> jpost(`/api/ring/recover/${b.dataset.recover}`).then(refresh));
  const cmd = document.getElementById("cmd");
  document.getElementById("propose").onclick = ()=> jpost("/api/paxos/propose",{command:cmd.value}).then(refresh);
  document.querySelectorAll("[data-pcrash]").forEach(b=> b.onclick = ()=> jpost(`/api/paxos/crash/${b.dataset.pcrash}`).then(refresh));
  document.querySelectorAll("[data-precover]").forEach(b=> b.onclick = ()=> jpost(`/api/paxos/recover/${b.dataset.precover}`).then(refresh));
}

wire();
refresh();
setInterval(refresh, 2000);
