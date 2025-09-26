class SouthAmericaDataCenter:
    def __init__(self):
        self.name = "South America Data Center"
        self.location = "South America"
        self.capacity_tb = 5000  # Capacity in Terabytes
        self.utc_offset = "-03:00"  # UTC offset for the location
        self.servers = []
        self.is_operational = True

    def get_status(self):
        return {
            "name": self.name,
            "location": self.location,
            "capacity_tb": self.capacity_tb,
            "is_operational": self.is_operational,
            "utc_offset": self.utc_offset,
            "server_count": len(self.servers)
        }
    def upgrade_capacity(self, additional_tb):
        if additional_tb > 0:
            self.capacity_tb += additional_tb
            return f"Capacity upgraded by {additional_tb} TB. New capacity is {self.capacity_tb} TB."
        else:
            return "Invalid capacity upgrade amount."
    def messagePassing(self, message):
        # Simulate message passing to another data center
        return f"Message '{message}' sent from {self.name}."

south_america_dc = SouthAmericaDataCenter()
print(south_america_dc.get_status())
print(south_america_dc.messagePassing("Hello, North America Data Center!"))
def add_server(server_name):
    south_america_dc.servers.append(server_name)
    return f"Server '{server_name}' added. Total servers: {len(south_america_dc.servers)}."

def server_count():
    return len(south_america_dc.servers)