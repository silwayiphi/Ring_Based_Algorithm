import threading
import requests
import time
import uuid
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")


# -------------------------------
# USERS CONFIGURATION
# -------------------------------
USERS = {
    "alice": {
        "password": "pass123",
        "packages": ["PKG-A-1001", "PKG-A-1002"]
    },
    "bob": {
        "password": "hunter2",
        "packages": ["PKG-B-2001", "PKG-B-2002"]
    },
    "charlie": {
        "password": "charlie123",
        "packages": ["PKG-C-3001"]
    }
}

# Map each package to a zone (datacenter location)
PACKAGE_ZONE = {
    "PKG-A-1001": "Africa",
    "PKG-A-1002": "Africa",
    "PKG-B-2001": "Europe",
    "PKG-B-2002": "Europe",
    "PKG-C-3001": "Asia"
}


# -------------------------------
# DATACENTER CLASS
# -------------------------------
class DataCenter:
    def __init__(self, name, location, capacity_tb, utc_offset, datacenter_id, neighbors=None):
        self.name = name
        self.location = location
        self.capacity_tb = capacity_tb
        self.utc_offset = utc_offset
        self.datacenter_id = datacenter_id
        self.servers = []  # list of dicts {port, thread}
        self.is_operational = True
        self.neighbors = neighbors or []
        self.packages = {}  # in-memory package store
        self.app = None
        self.socketio = None

    def get_status(self):
        return {
            "name": self.name,
            "location": self.location,
            "capacity_tb": self.capacity_tb,
            "is_operational": self.is_operational,
            "utc_offset": self.utc_offset,
            "server_count": len(self.servers)
        }

    def _record_package_event(self, package_id, event):
        now = time.time()
        zone = PACKAGE_ZONE.get(package_id, "Unknown")
        pkg = self.packages.setdefault(package_id, {
            "package_id": package_id,
            "status": "unknown",
            "current_location": None,
            "zone": zone,
            "history": []
        })
        event_record = {"event_id": str(uuid.uuid4()), "ts": now, "zone": zone, **event}
        pkg["history"].append(event_record)
        if "location" in event:
            pkg["current_location"] = event["location"]
        if "status" in event:
            pkg["status"] = event["status"]
        return event_record

    def add_new_server(self, port=5000):
        app = Flask(self.name, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
        dc = self

        # -------------------
        # ROUTES
        # -------------------
        @app.route("/")
        def home():
            return render_template("index.html", dc=dc.get_status())

        @app.route("/status")
        def status():
            return jsonify(dc.get_status())

        @app.route("/api/package/<package_id>/update", methods=["POST"])
        def package_update(package_id):
            data = request.get_json() or {}
            event = {}
            if "location" in data:
                event["location"] = data["location"]
            if "status" in data:
                event["status"] = data["status"]
            if "agent_id" in data:
                event["agent_id"] = data["agent_id"]

            event_record = dc._record_package_event(package_id, event)

            # Broadcast to connected clients
            socketio.emit("package_event", {"package_id": package_id, "event": event_record}, namespace="/")

            # Replicate to neighbors
            threading.Thread(target=dc._replicate_event_to_neighbors, args=(package_id, event_record), daemon=True).start()

            return jsonify({"ok": True, "event": event_record})

        @app.route("/api/replicate", methods=["POST"])
        def replicate():
            data = request.get_json() or {}
            package_id = data.get("package_id")
            event = data.get("event")
            if not package_id or not event:
                return jsonify({"ok": False, "error": "missing package_id or event"}), 400

            existing = dc.packages.get(package_id, {}).get("history", [])
            if any(e.get("event_id") == event.get("event_id") for e in existing):
                return jsonify({"ok": True, "skipped": True})

            dc.packages.setdefault(package_id, {
                "package_id": package_id,
                "status": "unknown",
                "current_location": None,
                "zone": PACKAGE_ZONE.get(package_id, "Unknown"),
                "history": []
            })
            dc.packages[package_id]["history"].append(event)
            if "location" in event:
                dc.packages[package_id]["current_location"] = event["location"]
            if "status" in event:
                dc.packages[package_id]["status"] = event["status"]

            socketio.emit("package_event", {"package_id": package_id, "event": event}, namespace="/")
            return jsonify({"ok": True})

        @app.route("/api/package/<package_id>")
        def get_package(package_id):
            pkg = dc.packages.get(package_id)
            if not pkg:
                return jsonify({"ok": False, "error": "not found"}), 404
            return jsonify({"ok": True, "package": pkg})

        # -------------------
        # SOCKET EVENTS
        # -------------------
        @socketio.on("connect")
        def on_connect():
            emit("dc_status", dc.get_status())

        self.app = app
        self.socketio = socketio

        def run_server():
            socketio.run(app, host="0.0.0.0", port=port, debug=False)

        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        self.servers.append({"port": port, "thread": t})
        print(f"[+] {self.name} running on port {port} with neighbors: {self.neighbors}")

    def _replicate_event_to_neighbors(self, package_id, event_record):
        payload = {"package_id": package_id, "event": event_record}
        headers = {"Content-Type": "application/json"}
        for n in self.neighbors:
            try:
                url = f"{n}/api/replicate"
                requests.post(url, json=payload, headers=headers, timeout=2)
            except Exception as e:
                print(f"[!] replication to {n} failed: {e}")