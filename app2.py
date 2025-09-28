import os
import subprocess
import time
import threading
from flask import Flask, render_template, request, jsonify,Response,current_app
from DS.DataCenter.Datacenter import DataCenter
import json
import requests
from ring import Ring
from paxos import Paxos

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
    atlantic_dc.datacenter_id, australia_dc.datacenter_id
]
ring = Ring(Datacenters)
paxos = Paxos()

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, separators=(',',':'))}\n\n"

# ------------ UI ------------
@app.route("/")
def index():
    return render_template("indexer2.html")

# ------------ Ring APIs ------------
@app.route("/api/ring/state")
def ring_state():
    return jsonify(ring.state())

@app.route("/api/ring/reset", methods=["POST"])
def ring_reset():
    ring.reset_flags()
    return jsonify({"ok": True, **ring.state()})

@app.route("/api/ring/crash/<int:nid>", methods=["POST"])
def ring_crash(nid: int):
    ok = ring.crash(nid)
    ring.next_alive(nid)
    current_app.logger.info("needed to crash %s", nid)
    index_cherry = Datacenters.index(nid)
    data = Datacenters_eq[index_cherry]
    data.is_operational = False
    port_to_block = ports[data.name]
    rule_name = f"BlockPort{port_to_block}"

    ok = False
    try:
        subprocess.run([
            "netsh", "advfirewall", "firewall", "delete", "rule",
            f"name={rule_name}"
        ], shell=True, capture_output=True, text=True)
        subprocess.run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            "dir=in",
            "action=block",
            "protocol=TCP",
            f"localport={port_to_block}"
        ], check=True, shell=True, capture_output=True, text=True)
        ok = True
    except subprocess.CalledProcessError as e:
        current_app.logger.error("Failed to block port %s: %s", port_to_block, e.stderr)

    ring.next_alive(nid)
    return jsonify({"ok": ok, **ring.state()})

@app.route("/api/ring/recover/<int:nid>", methods=["POST"])
def ring_recover(nid: int):
    ok = ring.recover(nid)
    index_cherry = Datacenters.index(nid)
    data_center = Datacenters_eq[index_cherry]
    data_center.is_operational = True
    if data_center not in Datacenters_eq:
        Datacenters_eq.insert(index_cherry, data_center)
    return jsonify({"ok": ok, **ring.state()})

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

if __name__ == "__main__":
    app.run(debug=True, threaded=True, use_reloader=False)

