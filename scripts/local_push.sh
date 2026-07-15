#!/bin/bash
# ============================================================================
# Tự động commit + push docs/data.json lên GitHub — CHẠY TRÊN MÁY LOX (không
# phải trên Cowork/Claude). Dùng cho Path B: Claude ghi data.json mới vào repo
# đã kết nối, script này chỉ có nhiệm vụ đẩy lên GitHub bằng git credential
# đã đăng nhập sẵn trên máy này (không cần nhập token/password gì thêm).
#
# Cách dùng:
#   1. chmod +x scripts/local_push.sh
#   2. Thêm vào crontab (crontab -e), chạy SAU giờ Claude fetch data ít nhất
#      5-10 phút, ví dụ nếu Claude fetch lúc 10:00 thì đặt cron lúc 10:10:
#        10 10 * * * /bin/bash /đường/dẫn/tới/repo/scripts/local_push.sh >> /tmp/thodia-dashboard-push.log 2>&1
#      (Thay "/đường/dẫn/tới/repo" bằng đường dẫn thật của folder đã clone.)
# ============================================================================
set -e
cd "$(dirname "$0")/.."

git add docs/data.json

if git diff --cached --quiet; then
  echo "$(date): Không có thay đổi trong docs/data.json — bỏ qua, không commit."
  exit 0
fi

git commit -m "chore: auto refresh dashboard data $(date +'%Y-%m-%d %H:%M')"
git push

echo "$(date): Đã push docs/data.json mới lên GitHub thành công."
