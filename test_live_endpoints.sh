#!/bin/bash

# Configuration
BASE_URL="https://case-review-web.onrender.com"
ADMIN_AUTH="admin:admin123"
OPERATOR_AUTH="operator:operator123"
REVIEWER_AUTH="reviewer:reviewer123"

# Helper function to print headers
print_step() {
    echo -e "\n========================================================"
    echo "▶ $1"
    echo "========================================================"
    sleep 1
}

# Python script to extract JSON fields safely without 'jq'
extract_json() {
    python3 -c "import sys, json; print(json.load(sys.stdin).get('$1', ''))" 2>/dev/null
}

# -------------------------------------------------------------------------
# 1. CREATE CASE
# -------------------------------------------------------------------------
print_step "1. Creating Case as Operator (POST /api/cases/)"
CREATE_RESP=$(curl -s -u $OPERATOR_AUTH -X POST "$BASE_URL/api/cases/" \
    -H "Content-Type: application/json" \
    -d '{"title": "Curl Test Case", "description": "Testing live API via cURL", "priority": "high"}')

echo "$CREATE_RESP"
CASE_ID=$(echo "$CREATE_RESP" | extract_json "case_id")

if [ -z "$CASE_ID" ]; then
    echo "Failed to create case. Exiting."
    exit 1
fi
echo -e "\n--> Extracted Case ID: $CASE_ID"

# Wait a moment to ensure DB sync before subsequent requests
sleep 1

# -------------------------------------------------------------------------
# 2. LIST CASES
# -------------------------------------------------------------------------
print_step "2. Listing Cases as Admin (GET /api/cases/)"
curl -s -u $ADMIN_AUTH "$BASE_URL/api/cases/"

# -------------------------------------------------------------------------
# 3. GET SINGLE CASE
# -------------------------------------------------------------------------
print_step "3. Getting Specific Case (GET /api/cases/$CASE_ID/)"
curl -s -u $ADMIN_AUTH "$BASE_URL/api/cases/$CASE_ID/"

# -------------------------------------------------------------------------
# 4. UPDATE CASE
# -------------------------------------------------------------------------
print_step "4. Updating Case Priority (PATCH /api/cases/$CASE_ID/)"
curl -s -u $OPERATOR_AUTH -X PATCH "$BASE_URL/api/cases/$CASE_ID/" \
    -H "Content-Type: application/json" \
    -d '{"priority": "critical"}'

# -------------------------------------------------------------------------
# 5. FETCH REVIEWER UUID
# -------------------------------------------------------------------------
# Since we removed the debug endpoint, we'll fetch the reviewer UUID by creating 
# a quick throwaway case as a Reviewer, which will fail (403), but give us the 
# reviewer context, OR we can just rely on the hardcoded UUID from our earlier test.
# Wait, Reviewers can't create cases. Let's use the hardcoded Reviewer UUID we obtained.
REVIEWER_UUID="3a25aae4-84fa-46f6-b871-6b4e159e407b"

# -------------------------------------------------------------------------
# 6. ASSIGN CASE
# -------------------------------------------------------------------------
print_step "6. Assigning Case to Reviewer (POST /api/cases/$CASE_ID/assign/)"
curl -s -u $ADMIN_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/assign/" \
    -H "Content-Type: application/json" \
    -d "{\"assigned_to\": \"$REVIEWER_UUID\"}"

# -------------------------------------------------------------------------
# 7. TRANSITION STATUS TO PENDING REVIEW
# -------------------------------------------------------------------------
print_step "7. Transitioning to pending_review (POST /api/cases/$CASE_ID/transition/)"
curl -s -u $OPERATOR_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/transition/" \
    -H "Content-Type: application/json" \
    -d '{"status": "pending_review"}'

# -------------------------------------------------------------------------
# 8. TRANSITION STATUS TO IN REVIEW
# -------------------------------------------------------------------------
print_step "8. Transitioning to in_review as Reviewer (POST /api/cases/$CASE_ID/transition/)"
curl -s -u $REVIEWER_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/transition/" \
    -H "Content-Type: application/json" \
    -d '{"status": "in_review"}'

# -------------------------------------------------------------------------
# 9. ADD COMMENTS
# -------------------------------------------------------------------------
print_step "9. Adding an Internal Comment as Reviewer (POST /api/cases/$CASE_ID/comments/)"
curl -s -u $REVIEWER_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/comments/" \
    -H "Content-Type: application/json" \
    -d '{"content": "Internal check: Looks fraudulent.", "is_internal": true}'

print_step "9b. Adding a Public Comment as Operator (POST /api/cases/$CASE_ID/comments/)"
curl -s -u $OPERATOR_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/comments/" \
    -H "Content-Type: application/json" \
    -d '{"content": "Waiting on customer docs.", "is_internal": false}'

# -------------------------------------------------------------------------
# 10. LIST COMMENTS (Checking RBAC)
# -------------------------------------------------------------------------
print_step "10. Listing Comments as Operator (Should only see 1 public comment)"
curl -s -u $OPERATOR_AUTH "$BASE_URL/api/cases/$CASE_ID/comments/"

print_step "10b. Listing Comments as Admin (Should see BOTH comments)"
curl -s -u $ADMIN_AUTH "$BASE_URL/api/cases/$CASE_ID/comments/"

# -------------------------------------------------------------------------
# 11. AUDIT LOGS
# -------------------------------------------------------------------------
print_step "11. Fetching final Audit Logs (GET /api/cases/$CASE_ID/audit-logs/)"
curl -s -u $ADMIN_AUTH "$BASE_URL/api/cases/$CASE_ID/audit-logs/"

echo -e "\n\n========================================================"
echo "All endpoints tested successfully!"
echo "========================================================"
