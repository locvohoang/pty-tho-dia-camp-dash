"""
Gửi tóm tắt report Thổ Địa Campaign vào 1 kênh Slack qua Incoming Webhook.
Chạy SAU khi build_dashboard.py đã ghi xong docs/data.json.

Requires env vars:
  SLACK_WEBHOOK_URL   — Incoming Webhook URL của kênh Slack muốn gửi report vào
                        (xem README mục "Tạo Slack Incoming Webhook" để lấy URL này)
Optional:
  DASHBOARD_URL       — link GitHub Pages nếu dùng custom domain; nếu bỏ trống,
                        script tự suy ra từ GITHUB_REPOSITORY (owner.github.io/repo)
"""
import os
import sys
import json
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "docs", "data.json")

FX_SGD_VND = 20000
FX_USD_VND = 26260


def fmt(n):
    try:
        return f"{n:,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def pct(actual, target):
    if not target:
        return "N/A"
    return f"{actual / target * 100:.1f}%"


def dashboard_url():
    override = os.environ.get("DASHBOARD_URL")
    if override:
        return override
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"
    return "(chưa cấu hình DASHBOARD_URL)"


def sum_rows(rows, *keys):
    return {k: sum(r.get(k, 0) or 0 for r in rows) for k in keys}


def main():
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("[WARN] SLACK_WEBHOOK_URL chưa được set — bỏ qua bước gửi Slack.", file=sys.stderr)
        return

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    manual = data["manual"]
    kpi = manual["kpiTargets"]
    paid_link = data["paidLink"]

    meta = data.get("meta", {}).get("summary", {})
    meta_rows = meta.get("data", []) if meta.get("available") else []
    meta_totals = sum_rows(meta_rows, "impressions", "reach", "spend_sgd")

    tiktok = data.get("tiktok", {})
    tiktok_rows = tiktok.get("data", []) if tiktok.get("available") else []
    tiktok_totals = sum_rows(tiktok_rows, "impressions", "reach", "spend_usd")

    total_impression = meta_totals.get("impressions", 0) + tiktok_totals.get("impressions", 0)
    media_spend_vnd = meta_totals.get("spend_sgd", 0) * FX_SGD_VND + tiktok_totals.get("spend_usd", 0) * FX_USD_VND

    manual_budget_vnd = sum(
        (b.get("actual") or 0) for b in manual["budgetPlan"]
        if b.get("includeInTotal") and b.get("source", "").startswith("Manual")
    )
    total_budget_plan = sum(b.get("plan", 0) for b in manual["budgetPlan"] if b.get("includeInTotal"))
    total_spend_actual = manual_budget_vnd + media_spend_vnd

    meta_status = "✅" if meta.get("available") else "⚠️ chưa có data"
    tiktok_status = "✅" if tiktok.get("available") else "⚠️ chưa có data"

    lines = [
        f"📊 *Thổ Địa Campaign — Update {data.get('generatedAt', '')[:10]}*",
        f"Xem chi tiết đầy đủ: {dashboard_url()}",
        "",
        f"*Awareness*  (Meta {meta_status} · TikTok {tiktok_status})",
        f"• Impression: {fmt(total_impression)}",
        f"• Reach — Meta: {fmt(meta_totals.get('reach', 0))}  |  TikTok: {fmt(tiktok_totals.get('reach', 0))}",
        "",
        "*Social buzz & engagement*  (nguồn: Paid link sheet)",
        f"• Buzz: {fmt(paid_link['totalBuzz'])} / {fmt(kpi['socialBuzz'])} target  ({pct(paid_link['totalBuzz'], kpi['socialBuzz'])})",
        f"• Engagement: {fmt(paid_link['totalEngagement'])} / {fmt(kpi['socialEngagement'])} target  ({pct(paid_link['totalEngagement'], kpi['socialEngagement'])})",
        "",
        "*Budget*",
        f"• Đã chi (ước tính): {fmt(total_spend_actual)}đ / kế hoạch {fmt(total_budget_plan)}đ  ({pct(total_spend_actual, total_budget_plan)})",
    ]
    text = "\n".join(lines)

    payload = {"text": text, "unfurl_links": False}
    r = requests.post(webhook, json=payload, timeout=30)
    r.raise_for_status()
    print("Đã gửi report vào Slack.")


if __name__ == "__main__":
    main()
