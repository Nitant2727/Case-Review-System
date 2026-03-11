# cURL Testing Guide for Live Endpoints

If you want to manually test the API endpoints using `curl` from your terminal, you can run the commands below.

### Environment Setup
Export these variables in your terminal to make copy-pasting the commands easier:
```bash
export BASE_URL="https://case-review-web.onrender.com"
export ADMIN_AUTH="admin:admin123"
export OP_AUTH="operator:operator123"
export REV_AUTH="reviewer:reviewer123"
export REV_UUID="3a25aae4-84fa-46f6-b871-6b4e159e407b"
```

---

### 1. Create a Case (Operator)
```bash
curl -s -u $OP_AUTH -X POST "$BASE_URL/api/cases/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "cURL Manual Test",
    "description": "Testing from terminal",
    "priority": "high"
  }'
```
*Note: Copy the `case_id` from the JSON response and export it:*
```bash
export CASE_ID="<paste-case-id-here>"
```

### 2. List All Cases (Admin)
```bash
curl -s -u $ADMIN_AUTH "$BASE_URL/api/cases/"
```

### 3. Get Specific Case
```bash
curl -s -u $ADMIN_AUTH "$BASE_URL/api/cases/$CASE_ID/"
```

### 4. Update Case Priority (Operator)
```bash
curl -s -u $OP_AUTH -X PATCH "$BASE_URL/api/cases/$CASE_ID/" \
  -H "Content-Type: application/json" \
  -d '{"priority": "critical"}'
```

### 5. Assign Case to Reviewer (Admin Only)
```bash
curl -s -u $ADMIN_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/assign/" \
  -H "Content-Type: application/json" \
  -d "{\"assigned_to\": \"$REV_UUID\"}"
```

### 6. Transition Status to Pending Review (Operator/Admin)
```bash
curl -s -u $OP_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/transition/" \
  -H "Content-Type: application/json" \
  -d '{"status": "pending_review"}'
```

### 7. Transition Status to In Review (Assigned Reviewer Only)
```bash
curl -s -u $REV_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/transition/" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_review"}'
```

### 8. Add an Internal Comment (Reviewer/Admin)
```bash
curl -s -u $REV_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/comments/" \
  -H "Content-Type: application/json" \
  -d '{"content": "This is an internal note.", "is_internal": true}'
```

### 9. Add a Public Comment (Operator)
```bash
curl -s -u $OP_AUTH -X POST "$BASE_URL/api/cases/$CASE_ID/comments/" \
  -H "Content-Type: application/json" \
  -d '{"content": "This is a public update.", "is_internal": false}'
```

### 10. List Comments (Role-Based Visibility)
**Run as Operator (Will only see the public comment):**
```bash
curl -s -u $OP_AUTH "$BASE_URL/api/cases/$CASE_ID/comments/"
```

**Run as Admin (Will see both comments):**
```bash
curl -s -u $ADMIN_AUTH "$BASE_URL/api/cases/$CASE_ID/comments/"
```

### 11. Fetch Audit Logs
```bash
curl -s -u $ADMIN_AUTH "$BASE_URL/api/cases/$CASE_ID/audit-logs/"
```