import os
import time
import threading
from tkinter.font import names
from flask import Flask, render_template, request, jsonify, Response
from DS.DataCenter.Datacenter import DataCenter
import json
from ring import Ring
from paxos import PaxosCluster

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# --- Initialize Data Centers ---
asia_dc = DataCenter("Asia Data Center", "Asia", 5000, "+03:00", 1)
australia_dc = DataCenter("Australia Data Center", "Australia", 5000, "+10:00", 7)
europe_dc = DataCenter("Europe Data Center", "Europe", 5000, "+01:00", 2)
africa_dc = DataCenter("Africa Data Center", "Africa", 5000, "+02:00", 3)
north_america_dc = DataCenter("North America Data Center", "North America", 5000, "-05:00", 4)
south_america_dc = DataCenter("South America Data Center", "South America", 5000, "-03:00", 5)
atlantic_dc = DataCenter("Atlantic Data Center", "Atlantic", 5000, "+00:00", 6)

# --- Ring ⇄ Paxos name/ID mapping (keep these in this exact order) ---
ID_TO_NAME = {
    1: "Asia Data Center",
    2: "Europe Data Center",
    3: "Africa Data Center",
    4: "North America Data Center",
    5: "South America Data Center",
    6: "Atlantic Data Center",
    7: "Australia Data Center",
}
NAME_BY_ID = ID_TO_NAME  # alias for clarity


ports = {
    "Asia Data Center": 5001,
    "Australia Data Center": 5002,
    "Europe Data Center": 5003,
    "Africa Data Center": 5004,
    "North America Data Center": 5005,
    "South America Data Center": 5006,
    "Atlantic Data Center": 5007
}

datacenters = [
    asia_dc,
    australia_dc,
    europe_dc,
    africa_dc,
    north_america_dc,
    south_america_dc,
    atlantic_dc
]

# --- Ring and Paxos setup ---
Datacenters_eq = [asia_dc, europe_dc, africa_dc, north_america_dc, south_america_dc, atlantic_dc, australia_dc]
Datacenters = [
    asia_dc.datacenter_id,
    europe_dc.datacenter_id,
    africa_dc.datacenter_id,
    north_america_dc.datacenter_id,
    south_america_dc.datacenter_id,
    atlantic_dc.datacenter_id,
    australia_dc.datacenter_id
]

ring = Ring(Datacenters)

# ✅ FIX: use PaxosCluster (there is no class named 'Paxos')
paxos_dc_names = [dc.name for dc in Datacenters_eq]
paxos = PaxosCluster(paxos_dc_names)

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, separators=(',',':'))}\n\n"

# ------------ UI ------------
@app.route("/")
def index():
    return render_template("indexer2.html")  # make sure templates/indexer2.html exists

# ------------ Ring APIs ------------
@app.route("/api/ring/state")
def ring_state():
    return jsonify(ring.state())

@app.route("/api/ring/reset", methods=["POST"])
def ring_reset():
    ring.reset_flags()
    return jsonify({"ok": True, **ring.state()})

@app.post("/api/ring/crash/<int:nid>")
def ring_crash(nid):
    ok = ring.crash(nid)
    name = {1:"Asia Data Center",2:"Europe Data Center",3:"Africa Data Center",
            4:"North America Data Center",5:"South America Data Center",
            6:"Atlantic Data Center",7:"Australia Data Center"}[nid]
    paxos.crash(name)
    return jsonify({"ok": ok, **ring.state(), "paxos": paxos.state()})

@app.route("/api/ring/recover/<int:nid>", methods=["POST"])
def ring_recover(nid: int):
    ok = ring.recover(nid)
    # reflect the same DC recovery in Paxos
    name = NAME_BY_ID.get(nid)
    if name:
        paxos.recover(name)
    return jsonify({"ok": ok, **ring.state(), "paxos": paxos.state()})

@app.route("/api/ring/fast", methods=["POST"])
def ring_fast():
    initiator = (request.get_json(silent=True) or {}).get("initiator")
    res = ring.start_fast(initiator)
    return jsonify(res | ring.state())

@app.route("/api/ring/trace")
def ring_trace_json():
    initiator = request.args.get("initiator", type=int)
    return jsonify(ring.election_trace(initiator))

@app.route("/stream/ring/election")
def ring_election_sse():
    initiator = request.args.get("initiator", type=int)
    delay = request.args.get("delay", default=400, type=int)
    trace = ring.election_trace(initiator)

    def gen():
        if not trace.get("ok"):
            yield _sse({"type": "error", "reason": trace.get("reason", "unknown")})
            return
        for step in trace["steps"]:
            yield _sse(step)
            if step["type"] in ("hop", "coord"):
                time.sleep(max(0, delay) / 1000)
        # commit final state
        leader = trace["leaderId"]
        ring.leader_id = leader
        for nd in ring.nodes.values():
            nd.elected = leader
            nd.participant = False

    resp = Response(gen(), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Connection"] = "keep-alive"
    return resp

# ------------ Paxos APIs ------------
@app.route("/api/paxos/state")
def paxos_state():
    return jsonify(paxos.state())

@app.route("/api/paxos/propose", methods=["POST"])
def paxos_propose():
    cmd = (request.get_json(silent=True) or {}).get("command")
    cmd = (cmd or "").strip() or "NOOP"

    # 1) Require a live ring leader; auto-elect if needed
    lid = ring.leader_id
    if lid is None or not ring.nodes[lid].alive:
        tr = ring.start_fast()         # quick non-animated election
        if not tr.get("ok"):
            return jsonify({"ok": False, "reason": "ring-election-failed"}), 503
        lid = ring.leader_id

    proposer_name = {
        1:"Asia Data Center", 2:"Europe Data Center", 3:"Africa Data Center",
        4:"North America Data Center", 5:"South America Data Center",
        6:"Atlantic Data Center", 7:"Australia Data Center",
    }.get(lid, f"node-{lid}")

    # 2) Run Paxos; result depends on majority of alive acceptors
    res = paxos.propose(cmd)

    return jsonify({
        "proposerId": lid,
        "proposerName": proposer_name,
        **res,
        **paxos.state()
    })


@app.route("/api/paxos/crash/<name>", methods=["POST"])
def paxos_crash(name: str):
    return jsonify({"ok": paxos.crash(name)} | paxos.state())

@app.route("/api/paxos/recover/<name>", methods=["POST"])
def paxos_recover(name: str):
    return jsonify({"ok": paxos.recover(name)} | paxos.state())

if __name__ == "__main__":
    app.run(debug=False, threaded=True, use_reloader=False)
