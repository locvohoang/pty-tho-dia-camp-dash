"""
Fetch TikTok Ads insights directly via TikTok Business/Marketing API — no Supermetrics needed.

Requires env vars:
  TIKTOK_ACCESS_TOKEN   — access token from a TikTok "Marketing API" app (Ads Manager > Assets > ... or
                          business-api.tiktok.com developer portal), authorized on the Chotot_brand account.
  TIKTOK_ADVERTISER_ID  — advertiser_id for account "Chotot_brand" (6966879607479894018)

Docs: https://business-api.tiktok.com/portal/docs?id=1740302848100353
  Endpoint used: GET /open_api/v1.3/report/integrated/get/  (campaign-level, daily)
"""
import os
import requests

API_BASE = "https://business-api.tiktok.com/open_api/v1.3"

# Campaign name substring — only campaigns for Thổ Địa
NAME_FILTER = "thodiacamp"


def _get(path, access_token, params):
    headers = {"Access-Token": access_token}
    r = requests.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"TikTok API error: {payload.get('message')} (code {payload.get('code')})")
    return payload["data"]


def fetch_campaign_report(access_token, advertiser_id, since, until):
    """Daily campaign-level report: impressions, reach, frequency, video views, spend."""
    import json as _json
    params = {
        "advertiser_id": advertiser_id,
        "report_type": "BASIC",
        "data_level": "AUCTION_CAMPAIGN",
        "dimensions": _json.dumps(["campaign_id", "stat_time_day"]),
        "metrics": _json.dumps(["campaign_name", "impressions", "reach", "frequency", "spend", "video_play_actions"]),
        "start_date": since,
        "end_date": until,
        "page_size": 1000,
    }
    data = _get("/report/integrated/get/", access_token, params)
    rows = []
    for item in data.get("list", []):
        dims = item.get("dimensions", {})
        metrics = item.get("metrics", {})
        name = metrics.get("campaign_name", "")
        if NAME_FILTER not in name:
            continue
        rows.append({
            "campaign_id": dims.get("campaign_id"),
            "campaign_name": name,
            "date": dims.get("stat_time_day", "")[:10],
            "impressions": int(metrics.get("impressions", 0) or 0),
            "reach": int(metrics.get("reach", 0) or 0),
            "frequency": float(metrics.get("frequency", 0) or 0),
            "video_views": int(metrics.get("video_play_actions", 0) or 0),
            "spend_usd": float(metrics.get("spend", 0) or 0),  # TikTok account currency = USD
        })
    return rows


if __name__ == "__main__":
    token = os.environ["TIKTOK_ACCESS_TOKEN"]
    advertiser_id = os.environ.get("TIKTOK_ADVERTISER_ID", "6966879607479894018")
    import datetime
    today = datetime.date.today().isoformat()
    result = fetch_campaign_report(token, advertiser_id, "2026-07-01", today)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
