
import time
from Datacenter import DataCenter

asia_dc = DataCenter("Asia Data Center", "Asia", 5000, "+03:00", 1)
australia_dc = DataCenter("Australia Data Center", "Australia", 5000, "+10:00", 7)
europe_dc = DataCenter("Europe Data Center", "Europe", 5000, "+01:00", 2)
africa_dc = DataCenter("Africa Data Center", "Africa", 5000, "+02:00", 3)
north_america_dc = DataCenter("North America Data Center", "North America", 5000, "-05:00", 4)
south_america_dc = DataCenter("South America Data Center", "South America", 5000, "-03:00", 5)
atlantic_dc = DataCenter("Atlantic Data Center", "Atlantic", 5000, "+00:00", 6)

# Assign ports for each datacenter
ports = {
    "Asia Data Center": 5001,
    "Australia Data Center": 5002,
    "Europe Data Center": 5003,
    "Africa Data Center": 5004,
    "North America Data Center": 5005,
    "South America Data Center": 5006,
    "Atlantic Data Center": 5007
}

# List of datacenters in ring order
datacenters = [
    asia_dc,
    australia_dc,
    europe_dc,
    africa_dc,
    north_america_dc,
    south_america_dc,
    atlantic_dc
]

# Connect neighbors in a ring (successor)
for i, dc in enumerate(datacenters):
    successor = datacenters[(i + 1) % len(datacenters)]  # next in ring, wraps around
    dc.neighbors = [f"http://127.0.0.1:{ports[successor.name]}"]

# Start each datacenter server
for dc in datacenters:
    port = ports[dc.name]
    dc.add_new_server(port=port)
    time.sleep(0.3)  # slight delay to prevent conflicts

print("[+] All datacenters are running in a ring topology.")

# Keep main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down datacenters...")
