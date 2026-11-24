import requests
import time

API_URL = "http://localhost:8000/api"

print("Starting run...")
resp = requests.post(f"{API_URL}/run", json={
    "user_id": "test_user",
    "request_text": "Generate my business travel expense report for June 2026 from the uploaded CSV"
})
run_data = resp.json()
print("Run started:", run_data)
run_id = run_data["run_id"]

for i in range(10):
    time.sleep(1)
    status_resp = requests.get(f"{API_URL}/run/{run_id}")
    status_data = status_resp.json()
    print(f"\nPoll {i+1} - Status: {status_data.get('status')}")
    print(f"Agent Status: {status_data.get('agent_status')}")
    if status_data.get("status") in ["completed", "failed"]:
        break

print("\nFinal Totals:", status_data.get("totals"))
