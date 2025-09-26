import socket
import threading
import json
import time

class DataCenterNode:
    def __init__(self, datacenter_id, port, successor_port):
        self.datacenter_id = datacenter_id
        self.port = port
        self.successor_port = successor_port
        self.packages = {}
        self.running = True

    def start(self):
        threading.Thread(target=self.tcp_server, daemon=True).start()

    # TCP server to receive messages
    def tcp_server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow quick restart of the socket on Windows
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", self.port))
        except OSError as e:
            print(f"{self.datacenter_id}: Port {self.port} is already in use! {e}")
            return
        s.listen()
        print(f"{self.datacenter_id} listening on port {self.port}")
        while self.running:
            try:
                conn, _ = s.accept()
                data = conn.recv(4096).decode()
                if data:
                    try:
                        self.handle_message(json.loads(data))
                    except json.JSONDecodeError:
                        print(f"{self.datacenter_id}: Received invalid JSON")
                conn.close()
            except Exception as e:
                # Print exception instead of silent pass
                print(f"{self.datacenter_id}: Server error {e}")
                continue

    # Handle incoming messages
    def handle_message(self, msg):
        print(f"{self.datacenter_id} received: {msg}")
        # Forward the message to successor if it is not the origin
        if msg.get("origin") != self.datacenter_id:
            self.send_to_successor(msg)

    # Send a message to the successor
    def send_to_successor(self, msg):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", self.successor_port))
            s.send(json.dumps(msg).encode())
            s.close()
        except Exception as e:
            print(f"{self.datacenter_id}: Failed to send to successor ({e})")

    # Simulate failure
    def stop(self):
        self.running = False
        print(f"{self.datacenter_id} stopped")
