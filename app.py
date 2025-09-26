from flask import Flask, render_template, request, jsonify
from ring import Ring
from paxos import Paxos

app = Flask(__name__)
ring = Ring([10, 20, 30, 40])
paxos = Paxos()

# ---------- UI ----------
@app.route("/")
def index():
    return render_template("index.html")

# ---------- Ring API ----------
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
    return jsonify({"ok": ok, **ring.state()})

@app.route("/api/ring/recover/<int:nid>", methods=["POST"])
def ring_recover(nid):
    ok = ring.recover(nid)
    return jsonify({"ok": ok, **ring.state()})

# ---------- Paxos API ----------
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
