"""
test_dmo_mapping.py — create the DMO mapping for Opportunity_Stream__dll → ssot__Opportunity__dlm
Uses standard mappings from d360-mcp-server Opportunity_DMO_Mappings.xml

DLO  : Opportunity_Stream__dll  (created by test_datastream.py)
DMO  : ssot__Opportunity__dlm   (standard Data Cloud Opportunity DMO)

Run: python test_dmo_mapping.py
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

# ── 2. Check if mapping already exists ───────────────────────────────────────
print("\nStep 2 — checking if mapping already exists...")
resp = requests.get(
    f"{BASE_URL}/services/data/v66.0/ssot/data-model-object-mappings"
    f"?sourceObjectName=Opportunity&dataspace=default",
    headers=HEADERS, timeout=15
)
if resp.status_code == 200:
    data = resp.json()
    mappings = data.get("dataModelObjectMappings", [])
    # look for our DLO
    existing = [m for m in mappings if "Opportunity_Stream" in m.get("sourceEntityDeveloperName", "")]
    if existing:
        for m in existing:
            print(f"  ~ Already exists: {m.get('developerName')} "
                  f"({m.get('sourceEntityDeveloperName')} → {m.get('targetEntityDeveloperName')})")
        print("  Skipping creation.")
        sys.exit(0)
print("  ✓ No existing mapping for Opportunity_Stream — will create.")

# ── 3. Create the DMO mapping ─────────────────────────────────────────────────
# Source: Opportunity_DMO_Mappings.xml from d360-mcp-server
# DLO fields have __c suffix  (e.g. Id__c, Name__c)
# DMO fields use standard ssot__ prefix on the DMO name but NOT on field names
#
# Only map fields that actually exist in our DLO (auto-discovered set).
# Skip formula/derived fields (Fmla_*, Has_Opportunity_Line_Item__c) — not in SFDC stream.
print("\nStep 3 — creating DMO mapping: Opportunity_Stream__dll → ssot__Opportunity__dlm...")

payload = {
    "sourceEntityDeveloperName": "Opportunity_Stream__dll",
    "targetEntityDeveloperName": "ssot__Opportunity__dlm",
    "fieldMapping": [
        {"sourceFieldDeveloperName": "Id__c",                   "targetFieldDeveloperName": "Id"},
        {"sourceFieldDeveloperName": "Name__c",                 "targetFieldDeveloperName": "Name"},
        {"sourceFieldDeveloperName": "Name__c",                 "targetFieldDeveloperName": "OpportunityName"},
        {"sourceFieldDeveloperName": "Amount__c",               "targetFieldDeveloperName": "TotalAmount"},
        {"sourceFieldDeveloperName": "StageName__c",            "targetFieldDeveloperName": "OpportunityStageId"},
        {"sourceFieldDeveloperName": "CloseDate__c",            "targetFieldDeveloperName": "CloseDate"},
        {"sourceFieldDeveloperName": "CreatedDate__c",          "targetFieldDeveloperName": "CreatedDate"},
        {"sourceFieldDeveloperName": "LastModifiedDate__c",     "targetFieldDeveloperName": "LastModifiedDate"},
        {"sourceFieldDeveloperName": "OwnerId__c",              "targetFieldDeveloperName": "OwnerUserId"},
        {"sourceFieldDeveloperName": "AccountId__c",            "targetFieldDeveloperName": "CustomerAccountId"},
        {"sourceFieldDeveloperName": "IsClosed__c",             "targetFieldDeveloperName": "IsClosed"},
        {"sourceFieldDeveloperName": "IsWon__c",                "targetFieldDeveloperName": "IsWon"},
        {"sourceFieldDeveloperName": "IsPrivate__c",            "targetFieldDeveloperName": "IsPrivate"},
        {"sourceFieldDeveloperName": "Description__c",          "targetFieldDeveloperName": "Description"},
        {"sourceFieldDeveloperName": "NextStep__c",             "targetFieldDeveloperName": "NextStep"},
        {"sourceFieldDeveloperName": "LeadSource__c",           "targetFieldDeveloperName": "LeadSourceId"},
        {"sourceFieldDeveloperName": "Type__c",                 "targetFieldDeveloperName": "OpportunityTypeId"},
        {"sourceFieldDeveloperName": "ForecastCategory__c",     "targetFieldDeveloperName": "OpportunityForecastCategory"},
        {"sourceFieldDeveloperName": "ForecastCategoryName__c", "targetFieldDeveloperName": "OpportunityForecastCategoryId"},
        {"sourceFieldDeveloperName": "ExpectedRevenue__c",      "targetFieldDeveloperName": "ExpectedRevenueAmount"},
        {"sourceFieldDeveloperName": "Probability__c",          "targetFieldDeveloperName": "Probability"},
        {"sourceFieldDeveloperName": "LastActivityDate__c",     "targetFieldDeveloperName": "LastActivityDate"},
        {"sourceFieldDeveloperName": "LastStageChangeDate__c",  "targetFieldDeveloperName": "LastStageChangeDate"},
        {"sourceFieldDeveloperName": "TotalOpportunityQuantity__c", "targetFieldDeveloperName": "TotalProductQuantity"},
        {"sourceFieldDeveloperName": "CampaignId__c",           "targetFieldDeveloperName": "CampaignId"},
        {"sourceFieldDeveloperName": "ContractId__c",           "targetFieldDeveloperName": "ContractId"},
        {"sourceFieldDeveloperName": "DataSource__c",           "targetFieldDeveloperName": "DataSourceId"},
        {"sourceFieldDeveloperName": "DataSourceObject__c",     "targetFieldDeveloperName": "DataSourceObjectId"},
    ]
}

print(f"  Source DLO : {payload['sourceEntityDeveloperName']}")
print(f"  Target DMO : {payload['targetEntityDeveloperName']}")
print(f"  Field count: {len(payload['fieldMapping'])}")

resp = requests.post(
    f"{BASE_URL}/services/data/v66.0/ssot/data-model-object-mappings?dataspace=default",
    headers=HEADERS, json=payload, timeout=60
)

print(f"\n  HTTP {resp.status_code}")

if resp.status_code in (200, 201):
    result = resp.json()
    print(f"\n  ✓ DMO Mapping created!")
    print(f"    developerName : {result.get('developerName')}")
    print(f"    source        : {result.get('sourceEntityDeveloperName')}")
    print(f"    target        : {result.get('targetEntityDeveloperName')}")
    print(f"    status        : {result.get('status')}")
    fields = result.get("fieldMapping", [])
    print(f"\n  ✓ Field mappings ({len(fields)}):")
    for f in fields:
        print(f"    {f.get('sourceFieldDeveloperName',''):45} → {f.get('targetFieldDeveloperName','')}")
else:
    print(f"\n  ✗ Failed: {resp.text[:800]}")
    sys.exit(1)
