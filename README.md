# Thổ Địa Campaign Dashboard — bản GitHub Pages (auto-update)

Dashboard tĩnh chạy trên GitHub Pages, tự động refresh data theo lịch (mặc định 6h sáng mỗi ngày,
giờ Việt Nam) qua GitHub Actions, hoặc bấm nút để refresh ngay bất cứ lúc nào.

⚠️ **Cảnh báo quan trọng trước khi bắt đầu:** GitHub Pages là hosting **công khai** trừ khi bạn có
gói GitHub Pro/Team/Enterprise (mới cho phép Pages chạy trên **private repo**). Nếu repo là public,
BẤT KỲ AI có link cũng xem được toàn bộ số liệu (impression, spend, buzz...) — kể cả người ngoài Chợ
Tốt. Khuyến nghị: tạo **private repo** + nâng cấp GitHub Pro (cá nhân) hoặc dùng GitHub Organization
đã có Team/Enterprise, rồi bật Pages cho private repo. Nếu không chắc, hỏi IT trước khi đẩy số liệu
thật lên.

---

## 1. Cấu trúc project

```
thodia-github-dashboard/
├── README.md                          (file này)
├── requirements.txt
├── data/
│   └── manual_data.json               ← Lox tự sửa tay: OOH actual, ngân sách offline, post mới trong Paid link...
├── scripts/
│   ├── fetch_meta.py                  ← gọi Meta Graph API trực tiếp
│   ├── fetch_tiktok.py                ← gọi TikTok Business API trực tiếp
│   └── build_dashboard.py             ← gộp tất cả lại thành docs/data.json
├── docs/
│   ├── index.html                     ← trang dashboard tĩnh (GitHub Pages sẽ serve từ đây)
│   └── data.json                      ← data được build tự động, ĐỪNG sửa tay file này
└── .github/workflows/
    └── update-dashboard.yml           ← GitHub Action chạy cron + nút bấm thủ công
```

## 2. Setup lần đầu (Lox tự làm — cần quyền admin Meta Business & TikTok Ads)

### Bước 1 — Tạo Meta (Facebook) System User Token

1. Vào **Meta Business Suite** → Business Settings → **System Users** → Add → tạo 1 system user
   (ví dụ "thodia-dashboard-bot"), role = Employee là đủ.
2. Vào **Assign Assets** cho system user đó → chọn Ad Account `697690298835029`
   (Chotot_pty_branding_sgd) → cấp quyền **View performance** (đọc là đủ, không cần Manage).
3. Bấm **Generate New Token** cho system user này → chọn app bất kỳ đã có sẵn (hoặc tạo 1 app mới
   loại "Business" trong developers.facebook.com) → tick quyền `ads_read` → Generate.
4. Copy token này lại — đây chính là `META_ACCESS_TOKEN`. Token loại system user thường **không hết
   hạn** (khác với token cá nhân chỉ sống 60 ngày), nên không cần refresh thủ công.

Docs tham khảo: https://developers.facebook.com/docs/marketing-api/system-users

### Bước 2 — Tạo TikTok Business API access

1. Vào https://business-api.tiktok.com/portal → đăng nhập bằng tài khoản có quyền quản lý
   Advertiser `6966879607479894018` (Chotot_brand).
2. Tạo 1 **App** mới (Developer → My Apps → Create) → xin scope **Reporting** (đọc báo cáo).
3. Sau khi tạo, vào phần **Authorized Advertisers** để authorize App vừa tạo được đọc advertiser
   `6966879607479894018`.
4. Lấy **Access Token** cho app đó (TikTok cấp trực tiếp cho app tự phát triển dùng nội bộ, không
   cần OAuth redirect phức tạp — xem mục "Direct Access Token" trong docs).

Docs tham khảo: https://business-api.tiktok.com/portal/docs?id=1738855099327489

### Bước 3 — Tạo GitHub repo + clone về máy

1. Vào https://github.com/new → đặt tên repo (vd. `thodia-dashboard`) → chọn **Private** (khuyến
   nghị — xem cảnh báo ở đầu file) hoặc Public nếu chấp nhận công khai số liệu → **KHÔNG** tick
   "Add a README file" (để repo trống hoàn toàn) → **Create repository**.
2. Copy URL repo vừa tạo (dạng `https://github.com/<username>/thodia-dashboard.git`).
3. Trên máy Lox, mở Terminal, clone repo về 1 folder cố định (vd. Desktop):
   ```bash
   cd ~/Desktop
   git clone https://github.com/<username>/thodia-dashboard.git
   ```
4. Copy toàn bộ nội dung bên trong folder `thodia-github-dashboard` (đã tải từ Cowork) vào bên
   trong folder `thodia-dashboard` vừa clone (đè lên, giữ nguyên cấu trúc `data/`, `scripts/`,
   `docs/`, `.github/`).
5. Push lên GitHub:
   ```bash
   cd ~/Desktop/thodia-dashboard
   git add .
   git commit -m "Initial commit"
   git push
   ```

Folder `~/Desktop/thodia-dashboard` này chính là folder cần dùng ở **mục 6 — Path B** bên dưới nếu
Lox muốn Claude tự fetch data trực tiếp thay vì chờ Meta/TikTok token.

### Bước 4 — Tạo Slack Incoming Webhook (để tự động gửi report vào group)

1. Vào https://api.slack.com/apps → **Create New App** → **From scratch** → đặt tên (vd.
   "Thổ Địa Dashboard Bot") → chọn đúng workspace Chợ Tốt.
2. Vào menu bên trái **Features → Incoming Webhooks** → bật toggle **Activate Incoming Webhooks**.
3. Kéo xuống dưới → **Add New Webhook to Workspace** → chọn kênh Slack muốn nhận report (vd.
   `#thodia-campaign`) → **Allow**.
4. Copy **Webhook URL** vừa tạo (dạng `https://hooks.slack.com/services/T000/B000/xxxxxxxx`) — đây
   chính là giá trị `SLACK_WEBHOOK_URL` ở bước sau. Không cần app nào duyệt, dùng được ngay.

Docs tham khảo: https://api.slack.com/messaging/webhooks

### Bước 5 — Thêm GitHub Secrets

Vào repo → Settings → Secrets and variables → Actions → **New repository secret**, thêm lần lượt:

| Name                    | Giá trị |
|-------------------------|---------|
| `META_ACCESS_TOKEN`     | Token lấy ở Bước 1 |
| `META_AD_ACCOUNT_ID`    | `697690298835029` |
| `TIKTOK_ACCESS_TOKEN`   | Token lấy ở Bước 2 |
| `TIKTOK_ADVERTISER_ID`  | `6966879607479894018` |
| `SLACK_WEBHOOK_URL`     | Webhook URL lấy ở Bước 4 |

`DASHBOARD_URL` là secret **tùy chọn** — chỉ cần thêm nếu bạn dùng custom domain cho GitHub Pages
(không thêm thì script tự suy ra link dạng `https://<username>.github.io/<repo-name>/`).

### Bước 6 — Bật GitHub Pages

Vào repo → Settings → Pages → Source: chọn branch `main`, folder `/docs` → Save.
GitHub sẽ cấp 1 link dạng `https://<username>.github.io/<repo-name>/` sau ~1 phút.

### Bước 7 — Chạy thử lần đầu

Vào tab **Actions** của repo → chọn workflow "Update Thổ Địa dashboard" → **Run workflow** (nút màu
xanh bên phải) → chờ ~30s-1 phút → kiểm tra 2 chỗ:
- Mở link Pages ở Bước 6 để xem dashboard.
- Kiểm tra kênh Slack đã chọn ở Bước 4 — sẽ có tin nhắn report tự động gửi vào ngay sau khi chạy xong.

---

## 3. Cách hoạt động của "auto update"

- **Theo lịch (daily):** workflow tự chạy mỗi ngày lúc 23:00 UTC = **06:00 sáng giờ VN**. Muốn đổi
  giờ, sửa dòng `cron:` trong `.github/workflows/update-dashboard.yml` (dùng https://crontab.guru để
  tính biểu thức cron).
- **"Real-time" theo yêu cầu:** GitHub Pages không chạy server nên không có real-time đúng nghĩa
  (không tự đẩy data mỗi giây). Cách gần nhất:
  - Bấm **Run workflow** thủ công trong tab Actions bất cứ lúc nào cần số mới ngay.
  - Hoặc đổi cron sang chạy mỗi 15-30 phút (`*/15 * * * *`) nếu muốn gần real-time hơn — lưu ý GitHub
    Actions free tier có giới hạn số phút chạy/tháng, chạy quá dày có thể tốn quota hoặc bị GitHub
    tự giãn lịch nếu server bận (cron trong Actions chỉ đảm bảo "best effort", không tuyệt đối đúng giờ).
- Mỗi lần chạy, script gọi thẳng Meta Graph API + TikTok Business API bằng token trong Secrets, build
  lại `docs/data.json`, gửi 1 tin nhắn tóm tắt report vào kênh Slack (Bước 4), rồi tự commit + push.
  GitHub Pages tự động serve bản mới ngay sau khi có commit.
- Nếu chưa set `SLACK_WEBHOOK_URL`, bước gửi Slack tự bỏ qua (không làm fail cả workflow) — dashboard
  vẫn update bình thường, chỉ là không có tin nhắn Slack.
- Nội dung tin Slack: Impression, Reach (Meta/TikTok), Social buzz & engagement so với target, và
  % ngân sách đã chi so với kế hoạch — kèm link dashboard đầy đủ.

## 4. Cập nhật số liệu thủ công (OOH, ngân sách offline, post Paid link mới)

Sửa trực tiếp file `data/manual_data.json` (có comment `_readme` giải thích rõ), rồi commit + push.
Workflow sẽ tự chạy lại ngay khi phát hiện file này thay đổi (nhờ trigger `push: paths:` trong
workflow) — không cần đợi tới lịch daily.

## 5. Phần còn thiếu so với bản Cowork

- **Traffic / DAU / DWL** (BigQuery `chotot-dwh`): bản GitHub này CHƯA có, vì cần 1 GCP service
  account JSON key riêng (không dùng chung được với Cowork). Nếu sau này xin được quyền, báo lại —
  cấu trúc để thêm 1 script `fetch_bigquery.py` (dùng thư viện `google-cloud-bigquery`) là tương tự
  2 script hiện có, key JSON lưu vào 1 GitHub Secret dạng base64.
- **App Install** (Airbridge/Branch.io): vẫn chưa có nguồn, giữ nguyên "N/A" như bản Cowork.
- Toàn bộ layout/logic tính toán (target, % achieved, funnel...) được giữ giống bản Cowork, chỉ khác
  cách lấy data (gọi thẳng API thay vì qua Cowork connector).

## 6. Path B — Claude tự fetch data + Lox tự push (không cần chờ Meta/TikTok token)

Dùng khi muốn có link xem ngay trong lúc Meta System User token / TikTok Developer app chưa xong.
Claude dùng luôn các connector đã kết nối sẵn trong Cowork (Meta Ads, Supermetrics cho TikTok,
Google Sheet) để tự tạo `docs/data.json` mới — Claude KHÔNG tự push lên GitHub được (không được
phép cầm token/credential thật), nên cần 1 script nhỏ chạy ngay trên máy Lox để làm việc đó.

**Cách hoạt động:** Claude (theo lịch đã chọn — 10h sáng hàng ngày) → ghi đè `docs/data.json` vào
đúng folder repo trên máy Lox → 1 cron job trên máy Lox (không phải Claude) tự chạy
`scripts/local_push.sh` sau đó ít phút → tự commit + push bằng git credential đã đăng nhập sẵn.

### Bước 8 — Kết nối folder repo cho Cowork

Trong Cowork, bấm nút chọn folder (hoặc yêu cầu Claude "kết nối folder") → chọn đúng folder
`~/Desktop/thodia-dashboard` đã clone ở Bước 3. Sau khi kết nối, Claude sẽ set 1 scheduled task tự
fetch data và ghi `docs/data.json` vào đây theo lịch đã chọn.

### Bước 9 — Set cron để tự push trên máy Lox

1. Cấp quyền chạy cho script:
   ```bash
   chmod +x ~/Desktop/thodia-dashboard/scripts/local_push.sh
   ```
2. Mở crontab: `crontab -e`
3. Thêm 1 dòng (chạy SAU giờ Claude fetch ít nhất 5-10 phút — nếu Claude fetch 10:00 sáng thì đặt
   10:10):
   ```
   10 10 * * * /bin/bash /Users/locvohoang/Desktop/thodia-dashboard/scripts/local_push.sh >> /tmp/thodia-dashboard-push.log 2>&1
   ```
4. Lưu lại (`:wq` nếu dùng vim). Kiểm tra log tại `/tmp/thodia-dashboard-push.log` sau lần chạy đầu.

**Lưu ý quan trọng:** cron chỉ chạy khi máy Lox đang bật và đăng nhập đúng giờ — nếu tắt máy/ngủ
đông đúng lúc đó thì lần chạy đó bị bỏ lỡ (sẽ tự chạy lại vào ngày hôm sau). Đây là lý do Path A
(GitHub Actions, mục 1-5) vẫn là hướng ổn định hơn về lâu dài — nên coi Path B là giải pháp tạm
trong lúc chờ hoàn tất Meta/TikTok token, rồi chuyển hẳn sang Path A sau.
