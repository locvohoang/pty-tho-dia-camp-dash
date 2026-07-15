"""
Fetch Meta (Facebook) Ads insights directly via Graph API — no Supermetrics/Cowork needed.

Requires env vars:
  META_ACCESS_TOKEN   — System User access token with ads_read permission
  META_AD_ACCOUNT_ID  — numeric ad account id (no "act_" prefix), e.g. 697690298835029

Docs: https://developers.facebook.com/docs/marketing-api/insights
"""
import os
import requests

GRAPH_VERSION = "v20.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

# Campaign name substrings to include — mirrors META_NAME_FILTERS in the Cowork dashboard.
# Since Graph API doesn't support "name contains" filtering server-side the same way,
# we fetch ALL campaigns in the account (paginated) and filter client-side by name.
NAME_FILTERS = ["thodiacamp", "brand_eng_sale_pty_b2c_0726"]


def _get(url, params):
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def list_campaigns(access_token, ad_account_id):
    """Return all campaigns in the account with id/name/status/objective."""
    url = f"{GRAPH_BASE}/act_{ad_account_id}/campaigns"
    params = {
        "access_token": access_token,
        "fields": "id,name,status,objective",
        "limit": 200,
    }
    campaigns = []
    while True:
        data = _get(url, params)
        campaigns.extend(data.get("data", []))
        paging = data.get("paging", {})
        next_url = paging.get("next")
        if not next_url:
            break
        url, params = next_url, {}  # `next` already has all query params baked in
    return campaigns


def campaign_insights(access_token, campaign_id, since, until, time_increment=None):
    """Impressions/reach/frequency/spend for one campaign over a date range.
    If time_increment is set (e.g. 1), returns one row per day."""
    url = f"{GRAPH_BASE}/{campaign_id}/insights"
    params = {
        "access_token": access_token,
        "fields": "campaign_name,impressions,reach,frequency,spend",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
    }
    if time_increment:
        params["time_increment"] = str(time_increment)
    data = _get(url, params)
    return data.get("data", [])


def fetch_all(access_token, ad_account_id, since, until, time_increment=None):
    """Fetch insights for every campaign whose name matches NAME_FILTERS."""
    campaigns = list_campaigns(access_token, ad_account_id)
    matched = [c for c in campaigns if any(f in c["name"] for f in NAME_FILTERS)]

    rows = []
    for c in matched:
        insights = campaign_insights(access_token, c["id"], since, until, time_increment)
        for row in insights:
            rows.append({
                "campaign_id": c["id"],
                "campaign_name": c["name"],
                "status": c.get("status"),
                "objective": c.get("objective"),
                "date_start": row.get("date_start"),
                "date_stop": row.get("date_stop"),
                "impressions": int(row.get("impressions", 0) or 0),
                "reach": int(row.get("reach", 0) or 0),
                "frequency": float(row.get("frequency", 0) or 0),
                "spend_sgd": float(row.get("spend", 0) or 0),  # ad account currency = SGD
            })
    return rows


if __name__ == "__main__":
    token = os.environ["META_ACCESS_TOKEN"]
    account_id = os.environ.get("META_AD_ACCOUNT_ID", "697690298835029")
    import datetime
    today = datetime.date.today().isoformat()
    result = fetch_all(token, account_id, "2026-07-01", today)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
