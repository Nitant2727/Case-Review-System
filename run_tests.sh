#!/bin/bash
BASE_URL="https://case-review-web.onrender.com"
AUTH="admin:admin123"

echo "1. POST /api/cases/ (Create Case)"
CREATE_RES=$(curl -s -u $AUTH -X POST "$BASE_URL/api/cases/" -H "Content-Type: application/json" -d '{"title": "Live Render Test Case", "description": "Testing the deployed API", "priority": "high"}')
echo "$CREATE_RES" | jq .
CASE_ID=$(echo "$CREATE_RES" | jq -r .case_id)
ADMIN_ID=$(echo "$CREATE_RES" | jq -r .created_by.id)

echo -e "\n2. GET /api/cases/ (List Cases)"
curl -s -u $AUTH "$BASE_URL/api/cases/" | jq .

echo -e "\n3. GET /api/cases/{id}/ (Get Case)"
curl -s -u $AUTH "$BASE_URL/api/cases/$CASE_ID/" | jq .

echo -e "\n4. PATCH /api/cases/{id}/ (Update Case)"
curl -s -u $AUTH -X PATCH "$BASE_URL/api/cases/$CASE_ID/" -H "Content-Type: application/json" -d '{"priority": "critical"}' | jq .

echo -e "\n5. POST /api/cases/{id}/transition/ (Transition to pending_review)"
curl -s -u $AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/transition/" -H "Content-Type: application/json" -d '{"status": "pending_review"}' | jq .

echo -e "\n6. POST /api/cases/{id}/assign/ (Fails intentionally - Admin ID is not a reviewer)"
curl -s -u $AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/assign/" -H "Content-Type: application/json" -d "{\"assigned_to\": \"$ADMIN_ID\"}" | jq .

echo -e "\n7. POST /api/cases/{id}/comments/ (Add Comment)"
curl -s -u $AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/comments/" -H "Content-Type: application/json" -d '{"content": "This API is super fast!", "is_internal": true}' | jq .

echo -e "\n8. GET /api/cases/{id}/comments/ (List Comments)"
curl -s -u $AUTH "$BASE_URL/api/cases/$CASE_ID/comments/" | jq .

echo -e "\n9. GET /api/cases/{id}/audit-logs/ (List Audit Logs)"
curl -s -u $AUTH "$BASE_URL/api/cases/$CASE_ID/audit-logs/" | jq .

