import requests

BASE_URL = "https://case-review-web.onrender.com"
AUTH = ('admin', 'admin123')

# We can query a case created by an operator or assign to a reviewer if we know their UUID.
# But since we don't have a public "list users" endpoint, we need a clever way to find it.

# Let's hit an endpoint that returns cases and extract user IDs from the 'created_by' and 'assigned_to' fields
res = requests.get(f"{BASE_URL}/api/cases/", auth=AUTH)
cases = res.json().get('results', [])

users = {}

# Scrape users from existing data
for case in cases:
    creator = case.get('created_by')
    if creator:
        users[creator['username']] = creator['id']
    
    assignee = case.get('assigned_to')
    if assignee:
        users[assignee['username']] = assignee['id']

print("Discovered Users from API Data:")
for username, uid in users.items():
    print(f"{username}: {uid}")

