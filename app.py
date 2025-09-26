from flask import Flask, render_template, request, jsonify
from DS.DataCenter.Africa import AfricaDataCenter
from DS.DataCenter.Africa import AfricaDataCenter
from DS.DataCenter.Asia import AsiaDataCenter
from DS.DataCenter.Europe import EuropeDataCenter
from Datacenter import DataCenterNode
from DS.DataCenter.North_America import NorthAmericaDataCenter
from DS.DataCenter.South_America import SouthAmericaDataCenter
from DS.DataCenter.Atantica import AtlanticDataCenter

from ring import Ring
from paxos import Paxos

app = Flask(__name__)

asia_dc = AsiaDataCenter()
europe_dc = EuropeDataCenter()
africa_dc = AfricaDataCenter()
north_america_dc = NorthAmericaDataCenter()
south_america_dc = SouthAmericaDataCenter()
atlantic_dc = AtlanticDataCenter()
# Define ports for each datacenter
datacenters_info = [
    (africa_dc.name, 5001),
    (europe_dc.name, 5002),
    (asia_dc.name, 5003),
    (north_america_dc.name, 5004),
    (south_america_dc.name, 5005),
    (atlantic_dc.name, 5006)
]

# Create nodes
nodes = []
for i, (name, port) in enumerate(datacenters_info):
    successor_port = datacenters_info[(i + 1) % len(datacenters_info)][1]
    node = DataCenterNode(name, port, successor_port)
    node.start()
    nodes.append(node)

# Test sending a message around the ring
Datacenters_eq= [asia_dc, europe_dc, africa_dc, north_america_dc, south_america_dc, atlantic_dc]
Datacenters =[asia_dc.datacenter_id, europe_dc.datacenter_id, africa_dc.datacenter_id, north_america_dc.datacenter_id, south_america_dc.datacenter_id, atlantic_dc.datacenter_id]
ring= Ring(Datacenters)
paxos = Paxos()

@app.route("/")
def index():
    return render_template("index.html")


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
    print(ring.state())
    ring._next_alive(nid)
    index_cherry = Datacenters.index(nid)
    data=Datacenters_eq[index_cherry]
    data.is_operational = False
    print(data.get_status())
    return jsonify({"ok": ok, **ring.state()})

@app.route("/api/ring/recover/<int:nid>", methods=["POST"])
def ring_recover(nid):
    ok = ring.recover(nid)
    index_cherry = Datacenters.index(nid)

    # Get the corresponding data center object
    data_center = Datacenters_eq[index_cherry]

    # Mark it as operational
    data_center.is_operational = True

    # Ensure it's back in Datacenters_eq at the correct position
    if data_center not in Datacenters_eq:
        Datacenters_eq.insert(index_cherry, data_center)

    # Optionally, reassign users if needed
    # redirected_users = ring.reassign_users_to_node(nid)  # implement if desired

    print(f"Recovered Data Center {nid}: {data_center.get_status()}")

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

if __name__ == "__main__":
    app.run(debug=True)
