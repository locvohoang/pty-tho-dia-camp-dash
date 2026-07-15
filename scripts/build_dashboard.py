"""
Main entrypoint — run by GitHub Actions (or locally) to refresh docs/data.json.

Usage:
  python scripts/build_dashboard.py

Reads:
  data/manual_data.json          (budget plan, OOH, targets, Paid link snapshot — edited by hand)
Writes:
  docs/data.json                 (everything the static index.html needs to render)

Meta / TikTok calls fail gracefully: if a token/secret is missing or the API errors out,
that section is marked {"available": false, "error": "..."} instead of crashing the whole run,
so the site still updates with whatever data IS available.
"""
import os
import sys
import json
import datetime
import traceback

sys.path.insert(0, os.path.dirname(__file__))
import fetch_meta
import fetch_tiktok

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL_DATA_PATH = os.path.join(ROOT, "data", "manual_data.json")
OUTPUT_PATH = os.path.join(ROOT, "docs", "data.json")

CAMPAIGN_START = "2026-07-01"
CAMPAIGN_END = "2026-08-31"


def today():
    return datetime.date.today().isoformat()


def safe_call(label, fn, *args, **kwargs):
    try:
        return {"available": True, "data": fn(*args, **kwargs)}
    except Exception as e:
        print(f"[WARN] {label} failed: {e}", file=sys.stderr)
        traceback.print_exc()
        return {"available": False, "error": str(e)}


def build_meta_section():
    token = os.environ.get("META_ACCESS_TOKEN")
    account_id = os.environ.get("META_AD_ACCOUNT_ID", "697690298835029")
    if not token:
        unavailable = {"available": False, "error": "META_ACCESS_TOKEN not set"}
        return {"summary": unavailable, "daily": unavailable}
    until = min(today(), CAMPAIGN_END)
    summary = safe_call("meta summary", fetch_meta.fetch_all, token, account_id, CAMPAIGN_START, until)
    daily = safe_call("meta daily", fetch_meta.fetch_all, token, account_id, CAMPAIGN_START, until, time_increment=1)
    return {"summary": summary, "daily": daily}


def build_tiktok_section():
    token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    advertiser_id = os.environ.get("TIKTOK_ADVERTISER_ID", "6966879607479894018")
    if not token:
        return {"available": False, "error": "TIKTOK_ACCESS_TOKEN not set"}
    until = min(today(), CAMPAIGN_END)
    report = safe_call("tiktok report", fetch_tiktok.fetch_campaign_report, token, advertiser_id, CAMPAIGN_START, until)
    return report


def compute_paid_link_totals(posts):
    def buzz(p):
        return p["post"] + p["repost"] + p["comment"] + p["share"]

    def engagement(p):
        return p["repost"] + p["comment"] + p["share"] + p["react"] + p["save"]

    total_buzz = sum(buzz(p) for p in posts)
    total_engagement = sum(engagement(p) for p in posts)

    by_channel = {}
    for p in posts:
        key = f'{p["platform"]} Owned'
        c = by_channel.setdefault(key, {"name": key, "post": 0, "comment": 0, "share": 0, "repost": 0, "react": 0, "save": 0, "buzz": 0, "engagement": 0})
        c["post"] += p["post"]; c["comment"] += p["comment"]; c["share"] += p["share"]
        c["repost"] += p["repost"]; c["react"] += p["react"]; c["save"] += p["save"]
        c["buzz"] += buzz(p); c["engagement"] += engagement(p)

    top5 = sorted(posts, key=buzz, reverse=True)[:5]
    top5_out = [{**p, "buzz": buzz(p), "engagement": engagement(p)} for p in top5]

    return {
        "totalBuzz": total_buzz,
        "totalEngagement": total_engagement,
        "byChannel": list(by_channel.values()),
        "top5": top5_out,
    }


def main():
    with open(MANUAL_DATA_PATH, encoding="utf-8") as f:
        manual = json.load(f)

    meta_section = build_meta_section()
    tiktok_section = build_tiktok_section()
    paid_link = compute_paid_link_totals(manual["paidLinkPosts"])

    output = {
        "generatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "campaignStart": CAMPAIGN_START,
        "campaignEnd": CAMPAIGN_END,
        "manual": manual,
        "meta": meta_section,
        "tiktok": tiktok_section,
        "paidLink": paid_link,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
