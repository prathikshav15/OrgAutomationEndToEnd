"""
test_datastream.py — standalone script to create an Opportunity datastream on cr-test.
Uses same approach as d360-mcp-server d360_datastream_create_sfdc:
  - datastreamType: "SFDC"
  - No field list — API auto-discovers fields from CRM object schema
  - Only connector info + DLO category/dataspace needed

Run: python test_datastream.py
"""
import json
import subprocess
import sys

import requests


# ── 1. Get a live token via sf CLI ────────────────────────────────────────────
print("Step 1 — fetching token for cr-test...")
result = subprocess.run(
    ["sf", "org", "display", "--target-org", "cr-test", "--json"],
    capture_output=True, text=True
)
org_data = json.loads(result.stdout)["result"]
TOKEN    = org_data["accessToken"]
BASE_URL = org_data["instanceUrl"]
print(f"  ✓ instance : {BASE_URL}")
print(f"  ✓ token    : {TOKEN[:20]}...")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type":  "application/json",
}

# ── 2. Check if stream already exists ────────────────────────────────────────
print("\nStep 2 — checking if Opportunity_Stream already exists...")
resp = requests.get(
    f"{BASE_URL}/services/data/v66.0/ssot/data-streams/Opportunity_Stream",
    headers=HEADERS, timeout=15
)
if resp.status_code == 200:
    existing = resp.json()
    print(f"  ~ Already exists: {existing.get('name')} (DLO: {existing.get('dataLakeObjectInfo',{}).get('name')})")
    print("  Skipping creation.")
    sys.exit(0)
print("  ✓ Does not exist — will create.")

# ── 3. Create the datastream ──────────────────────────────────────────────────
# Mirrors d360_datastream_create_sfdc from d360-mcp-server:
#   SalesforceCrmDataStreamTools.java — does NOT send field list.
#   API auto-discovers fields from CRM object schema.
#   datastreamType: "SFDC" is required for SalesforceDotCom connector.
print("\nStep 3 — creating Opportunity_Stream datastream...")

payload = {
    "name":           "Opportunity_Stream",
    "label":          "Opportunity_Stream",
    "datastreamType": "SFDC",
    "connectorInfo": {
        "connectorType": "SalesforceDotCom",
        "connectorDetails": {
            "name":         "SalesforceDotCom_Home",
            "sourceObject": "Opportunity"
        }
    },
    "dataLakeObjectInfo": {
        "name":         "Opportunity_Stream",
        "category":     "Profile",
        "dataspaceInfo": [{"name": "default"}]
    }
}

print(f"  Payload:\n{json.dumps(payload, indent=4)}")

resp = requests.post(
    f"{BASE_URL}/services/data/v66.0/ssot/data-streams",
    headers=HEADERS, json=payload, timeout=90
)

print(f"\n  HTTP {resp.status_code}")

if resp.status_code in (200, 201):
    result = resp.json()
    dlo = result.get("dataLakeObjectInfo", {})
    print(f"\n  ✓ Datastream created!")
    print(f"    name      : {result.get('name')}")
    print(f"    status    : {result.get('status')}")
    print(f"    recordId  : {result.get('recordId')}")
    print(f"    DLO name  : {dlo.get('name')}")
    print(f"    DLO id    : {dlo.get('id')}")
    print(f"\n  ✓ DLO fields (auto-discovered by API):")
    for f in dlo.get("dataLakeFieldInfoRepresentation", []):
        pk = " (PK)" if f.get("isPrimaryKey") else ""
        print(f"    {f['name']:40} {f['dataType']}{pk}")
else:
    print(f"\n  ✗ Failed: {resp.text[:500]}")
    sys.exit(1)
