class AtlanticDataCenter:
    def __init__(self):
        self.name = "Atlantic Data Center"
        self.location = "Atlantic Ocean"
        self.capacity_tb = 5000  # Capacity in Terabytes
        self.utc_offset = "-03:00"  # UTC offset for the location
        self.servers = []
        self.datacenter_id = 3
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
atlantic_dc = AtlanticDataCenter()
print(atlantic_dc.get_status())