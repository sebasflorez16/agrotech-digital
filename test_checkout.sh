#!/bin/bash
# Test checkout endpoint
echo "=== Testing create-checkout endpoint ==="
curl -s -X POST http://127.0.0.1:8000/billing/api/create-checkout/ \
  -H 'Content-Type: application/json' \
  -d '{"plan_tier":"basic","billing_cycle":"monthly","payer_email":"test@agrotech.com.co"}' | python3 -m json.tool
echo ""
echo "=== Done ==="
