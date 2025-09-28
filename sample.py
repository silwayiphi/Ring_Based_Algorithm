import threading

for t in threading.enumerate():
    print(f"Thread: {t.name}, Alive: {t.is_alive()}")