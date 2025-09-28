import threading
import time
from DS.DataCenter.Datacenter import DataCenter

# --- Data Center configuration ---
datacenters_info = [
    ("Asia Data Center", "Asia", "+03:00", 1, 5001),
    ("Australia Data Center", "Australia", "+10:00", 2, 5002),
    ("Europe Data Center", "Europe", "+01:00", 3, 5003),
    ("Africa Data Center", "Africa", "+02:00", 4, 5004),
    ("North America Data Center", "North America", "-05:00", 5, 5005),
    ("South America Data Center", "South America", "-03:00", 6, 5006),
    ("Atlantic Data Center", "Atlantic", "+00:00", 7, 5007)
]

datacenters = []
ports = {}

for name, location, utc, dcid, port in datacenters_info:
    dc = DataCenter(name, location, 5000, utc, dcid)
    datacenters.append(dc)
    ports[name] = port


for i, dc in enumerate(datacenters):
    successor = datacenters[(i + 1) % len(datacenters)]
    dc.neighbors = [f"http://127.0.0.1:{ports[successor.name]}"]
    print(f"{dc.name} neighbor -> {successor.name}")


for dc in datacenters:
    port = ports[dc.name]
    t = threading.Thread(target=dc.add_new_server, kwargs={"port": port})
    t.start()
    time.sleep(0.3)  # stagger startup

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down all data centers...")
