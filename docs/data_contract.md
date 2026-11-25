# Data Contract Toàn Hệ Thống: Firmware ↔ Backend ↔ Mobile Web (Theo Use Case)

## 1. Bảng ánh xạ Use Case Dashboard ↔ API & Socket.IO

| Use Case trên Dashboard | Giao thức | Endpoint / Event | Mô tả dữ liệu trả về |
| :--- | :--- | :--- | :--- |
| **Xem được bản đồ các nút** | REST + WS | `GET /api/nodes` + `map_node_update` | Danh sách nút kèm `latitude`, `longitude`, `alert_level`, `status`, `is_subscribed` để ghim marker trên bản đồ. |
| **Xem chi tiết một nút** | REST + WS | `GET /api/nodes/<node_id>` + room `node:<node_id>` | Gom đủ 4 thông tin con: mực nước (`water_level_cm`), tốc độ thoát nước (`flow_rate_lpm`), máy bơm (`pump_active`, `mode`), và `recent_alerts`. |
| **Xem mực nước hiện tại** | REST + WS | `GET /api/nodes/<node_id>/telemetry` + `telemetry_update` | Giá trị `water_level_cm` hiện tại & chuỗi 30 điểm gần nhất vẽ biểu đồ Chart.js. |
| **Xem tốc độ thoát nước hiện tại** | REST + WS | `GET /api/nodes/<node_id>/telemetry` + `telemetry_update` | Giá trị `flow_rate_lpm` (L/phút) hiện tại & chuỗi lịch sử thoát nước. |
| **Nhận thông báo cảnh báo** | REST + WS + FCM | `GET /api/alerts?category=alert` + `new_alert` + FCM | Phát sinh khi `alert_level` chuyển sang `WARNING`/`DANGER`/`NORMAL`; gửi Push FCM tới các user đã đăng ký theo dõi nút. |
| **Nhận thông tin máy bơm** | REST + WS + FCM | `GET /api/alerts?category=pump` + `pump_status_update` + FCM | Phát sinh khi `pump_active` đổi từ `false <-> true`; thông báo trạng thái bật/tắt bơm và lưu lượng thoát nước. |
| **Tạo tài khoản** | REST | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` | Tạo tài khoản (`username`, `email`, `password`, `full_name`) và cấp Bearer Token. |
| **Đăng ký theo dõi 1 nút** | REST | `POST /api/nodes/<node_id>/subscribe`, `DELETE .../subscribe`, `GET /api/subscriptions` | Gắn `user_id` với `node_id` (`notify_alert`, `notify_pump`) để nhận thông báo cá nhân hóa. |

---

## 2. Giao tiếp Firmware (ESP32) ↔ MQTT Broker ↔ Backend
- **Telemetry (`ESP32 -> Backend`):** Topic `flood_system/nodes/{node_id}/telemetry` (`QoS 0`, 2s/lần)
  ```json
  {
    "node_id": "node_01",
    "water_level_cm": 14.5,
    "flow_rate_lpm": 1.25,
    "pump_active": true,
    "alert_level": "WARNING"
  }
  ```
- **LWT Status (`ESP32 -> Backend`):** Topic `flood_system/nodes/{node_id}/status` (`QoS 1`, `retain=true`) -> `{"status": "online"}` / `{"status": "offline"}`.
- **Command (`Backend -> ESP32`):** Topic `flood_system/nodes/{node_id}/command` (`QoS 1`) -> `{"mode": "MANUAL", "pump_command": true}`.

---

## 3. Chi tiết REST API Endpoints (`Backend <-> Mobile Web`)

### 3.1. Tài khoản (`auth_api.py`)
- `POST /api/auth/register`
  - Body: `{"username": "hungpm", "email": "hung@example.com", "password": "secret123", "full_name": "Phạm Mạnh Hùng"}`
  - Response `201`: `{"token": "<bearer_token>", "user": {"id": 1, "username": "hungpm", "email": "hung@example.com", "full_name": "Phạm Mạnh Hùng", "subscribed_node_ids": []}}`
- `POST /api/auth/login`
  - Body: `{"username": "hungpm", "password": "secret123"}`
  - Response `200`: `{"token": "<bearer_token>", "user": {...}}`
- `GET /api/auth/me` (Header `Authorization: Bearer <token>`) -> trả về thông tin user & danh sách `subscribed_node_ids`.

### 3.2. Bản đồ, Chi tiết Nút & Đăng ký theo dõi (`nodes_api.py`)
- `GET /api/nodes` *(Hỗ trợ optional Header `Authorization: Bearer <token>` để đánh dấu `is_subscribed`)*
  - Response `200`:
    ```json
    {
      "nodes": [
        {
          "node_id": "node_01",
          "name": "Hầm chui Kim Liên",
          "location_desc": "Nút giao Xã Đàn - Giải Phóng, Đống Đa, Hà Nội",
          "latitude": 21.0075,
          "longitude": 105.8394,
          "is_virtual": false,
          "status": "online",
          "mode": "AUTO",
          "water_level_cm": 14.5,
          "flow_rate_lpm": 1.25,
          "pump_active": true,
          "alert_level": "WARNING",
          "is_subscribed": true,
          "subscriber_count": 3,
          "last_seen": "2026-11-25T14:20:00Z"
        }
      ]
    }
    ```
- `GET /api/nodes/<node_id>?limit=30` -> Trả về đồng thời `node`, `telemetry` (30 điểm gần nhất), và `recent_alerts` (10 sự kiện gần nhất của nút) khi người dùng bấm vào 1 marker trên bản đồ.
- `POST /api/nodes/<node_id>/subscribe` *(Yêu cầu `Bearer <token>`)*
  - Body: `{"notify_alert": true, "notify_pump": true}`
  - Response `200`: `{"status": "subscribed", "subscription": {...}, "node": {...}}`
- `DELETE /api/nodes/<node_id>/subscribe` *(Yêu cầu `Bearer <token>`)* -> Hủy theo dõi nút.
- `GET /api/subscriptions` *(Yêu cầu `Bearer <token>`)* -> Lấy danh sách các nút user đang theo dõi.
- `POST /api/devices/fcm-token` -> Body `{"token": "...", "device_name": "..."}` (tự liên kết với `user_id` nếu kèm `Bearer <token>`).

### 3.3. Thông báo cảnh báo & Thông tin máy bơm (`alerts_api.py`)
- `GET /api/alerts?node_id=node_01&category=alert&only_subscribed=true&limit=20`
  - `category`: `"alert"` (mức ngập), `"pump"` (bật/tắt máy bơm), hoặc bỏ trống để lấy tất cả.
  - `only_subscribed=true`: Chỉ lọc thông báo từ các nút user đã đăng ký theo dõi.

---

## 4. Socket.IO Events (`Backend <-> Mobile Web`)
- **Client gửi lên Server:**
  - `join_node`: `{"node_id": "node_01"}` (gọi khi mở màn hình *Xem chi tiết một nút*).
  - `leave_node`: `{"node_id": "node_01"}` (gọi khi quay lại màn hình *Bản đồ các nút*).
- **Server đẩy xuống Client:**
  - `map_node_update`: Cập nhật nhanh trạng thái marker trên bản đồ.
  - `telemetry_update` (gửi tới room `node:<node_id>`): Cập nhật real-time mực nước, tốc độ thoát nước, máy bơm cho màn hình chi tiết.
  - `pump_status_update` (gửi tới room `node:<node_id>`): Phát ngay khi máy bơm chuyển trạng thái `ON <-> OFF`.
  - `new_alert`: Phát ngay khi có cảnh báo mực nước hoặc sự kiện máy bơm mới.
