import os
import time
import threading
from flask import Flask, render_template, request, jsonify
from DS.DataCenter.Datacenter import DataCenter
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

# Connect neighbors in a ring
for i, dc in enumerate(datacenters):
    successor = datacenters[(i + 1) % len(datacenters)]
    dc.neighbors = [f"http://127.0.0.1:{ports[successor.name]}"]


for dc in datacenters:
    port = ports[dc.name]
    t = threading.Thread(target=dc.add_new_server, kwargs={"port": port}, daemon=True)
    t.start()
    time.sleep(0.3)  # prevent port conflicts

print("[+] All datacenters are running in a ring topology.")

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

# --- Flask Dashboard ---
@app.route("/implementation")
def index():
    return render_template("indexer.html")


@app.route("/api/ring/state")
def ring_state():
    return jsonify(ring.state())


@app.route("/api/ring/start", methods=["POST"])
def ring_start():
    ok = ring.start_election()
    return jsonify({"ok": ok, **ring.state()})


@app.route("/api/ring/crash/<int:nid>", methods=["POST"])
def ring_crash(nid):
    ok = ring.crash(nid)
    ring._next_alive(nid)
    index_cherry = Datacenters.index(nid)
    data = Datacenters_eq[index_cherry]
    data.is_operational = False
    return jsonify({"ok": ok, **ring.state()})


@app.route("/api/ring/recover/<int:nid>", methods=["POST"])
def ring_recover(nid):
    ok = ring.recover(nid)
    index_cherry = Datacenters.index(nid)
    data_center = Datacenters_eq[index_cherry]
    data_center.is_operational = True
    if data_center not in Datacenters_eq:
        Datacenters_eq.insert(index_cherry, data_center)
    return jsonify({"ok": ok, **ring.state()})


@app.route("/api/paxos/state")
def paxos_state():
    return jsonify(paxos.snapshot())


@app.route("/api/paxos/propose", methods=["POST"])
def paxos_propose():
    body = request.get_json(silent=True) or {}
    cmd = body.get("command", "UPDATE P123 OUT_FOR_DELIVERY")
    idx = body.get("index")
    res = paxos.propose(cmd, index=idx)
    return jsonify(res)


@app.route("/api/paxos/crash/<name>", methods=["POST"])
def paxos_crash(name):
    ok = paxos.crash(name)
    return jsonify({"ok": ok, **paxos.snapshot()})


@app.route("/api/paxos/recover/<name>", methods=["POST"])
def paxos_recover(name):
    ok = paxos.recover(name)
    return jsonify({"ok": ok, **paxos.snapshot()})


# --- Run Flask Dashboard ---
if __name__ == "__main__":
    # Dashboard runs on port 5010
    app.run(debug=True, host="localhost", port=5010)
