import requests
import time

BASE = "http://localhost:8000"

call_id = "call-demo"

chunks = [
    "Hello",
    "I have an issue",
    "I was charged twice on my invoice",
]

for i, text in enumerate(chunks):
    r = requests.post(
        f"{BASE}/calls/{call_id}/chunks",
        json={"seq": i, "text": text},
    )
    print("POST:", r.json())
    time.sleep(1)

    view = requests.get(f"{BASE}/calls/{call_id}/agent_view")
    print("VIEW:", view.json())
    print("------")