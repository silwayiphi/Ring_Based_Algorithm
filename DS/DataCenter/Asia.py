class AsiaDataCenter:
    def __init__(self):
        self.name = "Asia Data Center"
        self.location = "Asia"
        self.capacity_tb = 10000  # Capacity in terabytes
        self.is_operational = True
        self.utc_offset = "+08:00"  # UTC offset for the location
        self.servers = []
        self.datacenter_id = 2
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
asia_dc = AsiaDataCenter()
print(asia_dc.get_status())