import requests
import json

BASE_URL = "https://case-review-web.onrender.com"
AUTH = ('admin', 'admin123')

print("1. POST /api/cases/ (Create Case)")
res = requests.post(f"{BASE_URL}/api/cases/", json={"title": "Live Render Test Case", "description": "Testing the deployed API", "priority": "high"}, auth=AUTH)
case_data = res.json()
print(json.dumps(case_data, indent=2))
case_id = case_data['case_id']
admin_id = case_data['created_by']['id']

print("\n2. GET /api/cases/ (List Cases)")
res = requests.get(f"{BASE_URL}/api/cases/", auth=AUTH)
print(json.dumps(res.json(), indent=2))

print(f"\n3. GET /api/cases/{case_id}/ (Get Case)")
res = requests.get(f"{BASE_URL}/api/cases/{case_id}/", auth=AUTH)
print(json.dumps(res.json(), indent=2))

print(f"\n4. PATCH /api/cases/{case_id}/ (Update Case)")
res = requests.patch(f"{BASE_URL}/api/cases/{case_id}/", json={"priority": "critical"}, auth=AUTH)
print(json.dumps(res.json(), indent=2))

print(f"\n5. POST /api/cases/{case_id}/transition/ (Transition to pending_review)")
res = requests.post(f"{BASE_URL}/api/cases/{case_id}/transition/", json={"status": "pending_review"}, auth=AUTH)
print(json.dumps(res.json(), indent=2))

print(f"\n6. POST /api/cases/{case_id}/assign/ (Fails intentionally - Admin ID is not a reviewer)")
res = requests.post(f"{BASE_URL}/api/cases/{case_id}/assign/", json={"assigned_to": admin_id}, auth=AUTH)
print(f"Status Code: {res.status_code}")
print(json.dumps(res.json(), indent=2))

print(f"\n7. POST /api/cases/{case_id}/comments/ (Add Comment)")
res = requests.post(f"{BASE_URL}/api/cases/{case_id}/comments/", json={"content": "This API is deployed and works perfectly!", "is_internal": True}, auth=AUTH)
print(json.dumps(res.json(), indent=2))

print(f"\n8. GET /api/cases/{case_id}/comments/ (List Comments)")
res = requests.get(f"{BASE_URL}/api/cases/{case_id}/comments/", auth=AUTH)
print(json.dumps(res.json(), indent=2))

print(f"\n9. GET /api/cases/{case_id}/audit-logs/ (List Audit Logs)")
res = requests.get(f"{BASE_URL}/api/cases/{case_id}/audit-logs/", auth=AUTH)
print(json.dumps(res.json(), indent=2))

