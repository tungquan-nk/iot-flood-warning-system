# Data Contract Toàn Hệ Thống: Firmware ↔ Backend ↔ Mobile Web

## 1. Quy ước chung
- **Định dạng dữ liệu:** JSON (UTF-8)
- **Chuẩn thời gian:** ISO-8601 UTC (`"2026-11-25T13:45:02Z"`). Backend tự gắn timestamp khi nhận bản tin; Mobile Web tự quy đổi sang múi giờ địa phương (`UTC+7`).
- **Tần suất cập nhật:** 2 giây / lần cho dữ liệu cảm biến; đẩy tức thì (Event-driven) khi trạng thái bơm, cảnh báo, hoặc kết nối Node thay đổi.

---

## 2. Giao tiếp Firmware (ESP32) ↔ MQTT Broker ↔ Backend

### 2.1. Dữ liệu cảm biến & trạng thái Node (`ESP32 -> Backend`)
- **Topic:** `flood_system/nodes/{node_id}/telemetry`
- **QoS:** `0` | **Tần suất:** 2 giây / lần (và gửi ngay khi `pump_active` hoặc `alert_level` đổi trạng thái)
- **Payload:**
```json
{
  "node_id": "node_01",
  "water_level_cm": 14.5,
  "flow_rate_lpm": 1.25,
  "pump_active": true,
  "alert_level": "WARNING"
}
```

### 2.2. Trạng thái Sống / Chết LWT (`ESP32 -> Backend`)
- **Topic:** `flood_system/nodes/{node_id}/status`
- **QoS:** `1` | **Retain:** `true`
- **Payload:** `{"status": "online"}` hoặc `{"status": "offline"}` (Broker tự phát LWT khi ESP32 mất điện/mất Wi-Fi).

### 2.3. Lệnh điều khiển bơm (`Backend -> ESP32`)
- **Topic:** `flood_system/nodes/{node_id}/command`
- **QoS:** `1` | **Retain:** `false`
- **Payload:**
```json
{
  "mode": "MANUAL",
  "pump_command": true
}
```

---

## 3. Giao tiếp Backend ↔ Mobile Web Dashboard (REST API + Socket.IO)

### 3.1. REST API Endpoints (`Frontend -> Backend`)

| Method | Endpoint | Mô tả | Request / Query | Response mẫu (`200 OK`) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Kiểm tra trạng thái Server & MQTT | Không | `{"status": "ok", "mqtt_connected": true}` |
| `GET` | `/api/nodes` | Lấy danh sách điểm đo & thông số hiện tại | Không | `{"nodes": [{"node_id": "node_01", "name": "Hầm chui Kim Liên", "status": "online", "mode": "AUTO", "water_level_cm": 14.5, "flow_rate_lpm": 1.25, "pump_active": true, "alert_level": "WARNING", "last_seen": "2026-11-25T13:45:02Z"}]}` |
| `POST` | `/api/nodes` | Thêm điểm đo thật hoặc Node ảo demo | `{"node_id": "node_02", "name": "Cống Nguyễn Trãi", "is_virtual": true}` | `{"node": {...}}` (`201 Created`) |
| `GET` | `/api/nodes/<node_id>/telemetry` | Lấy lịch sử vẽ biểu đồ Chart.js | `?limit=30` (tối đa `500`) | `{"node_id": "node_01", "count": 30, "telemetry": [{"water_level_cm": 14.5, "flow_rate_lpm": 1.25, "pump_active": true, "alert_level": "WARNING", "timestamp": "2026-11-25T13:45:02Z"}]}` |
| `POST` | `/api/nodes/<node_id>/command` | Chuyển chế độ AUTO/MANUAL hoặc bật/tắt bơm | `{"mode": "MANUAL", "pump_command": true}` | `{"node_id": "node_01", "mode": "MANUAL", "pump_command": true, "mqtt_delivered": true}` |
| `GET` | `/api/alerts` | Lấy danh sách nhật ký sự kiện ngập | `?limit=20&node_id=node_01` | `{"unread_count": 2, "alerts": [{"id": 12, "node_id": "node_01", "event_type": "LEVEL_DANGER", "message": "...", "water_level_cm": 16.8, "is_read": false, "created_at": "..."}]}` |
| `PATCH` | `/api/alerts/read-all` | Đánh dấu toàn bộ cảnh báo đã đọc | Không | `{"status": "ok"}` |
| `POST` | `/api/devices/fcm-token` | Đăng ký FCM token nhận Push Notification | `{"token": "fcm_token_xyz", "device_name": "Samsung A53"}` | `{"status": "registered"}` (`201 Created`) |

### 3.2. Socket.IO Real-time Events (`Backend -> Frontend`)

| Tên Event | Thời điểm kích hoạt | Payload JSON | Hành động phía Mobile Web |
| :--- | :--- | :--- | :--- |
| `telemetry_update` | Ngay khi nhận gói tin cảm biến mới (2s/lần) | `{"node_id": "node_01", "water_level_cm": 14.5, "flow_rate_lpm": 1.25, "pump_active": true, "alert_level": "WARNING", "timestamp": "2026-11-25T13:45:02Z"}` | Đẩy điểm mới vào cuối Chart.js (`push` + `shift` + `update('none')`) và cập nhật số liệu trên thẻ Node. |
| `node_status` | Khi ESP32 kết nối hoặc mất kết nối (LWT) | `{"node_id": "node_01", "status": "offline", "last_seen": "2026-11-25T13:46:10Z"}` | Đổi huy hiệu trạng thái Online (xanh) / Offline (xám) ngay lập tức. |
| `new_alert` | Khi phát sinh sự kiện chuyển mức cảnh báo / bật bơm / mất kết nối | `{"id": 12, "node_id": "node_01", "event_type": "LEVEL_DANGER", "message": "...", "water_level_cm": 16.8, "is_read": false, "created_at": "..."}` | Hiển thị Toast/Banner cảnh báo khẩn cấp và tăng badge số thông báo chưa đọc. |
| `command_ack` | Sau khi Backend publish lệnh bơm xuống Broker | `{"node_id": "node_01", "mode": "MANUAL", "pump_command": true, "mqtt_delivered": true}` | Đồng bộ trạng thái nút gạt giữa nhiều thiết bị đang mở Dashboard cùng lúc. |

### 3.3. Quy tắc đồng bộ vòng đời Mobile Web (Bắt buộc)
1. **Khởi tạo màn hình:** Gọi `GET /api/nodes`, `GET /api/nodes/<active_id>/telemetry?limit=30` và `GET /api/alerts?limit=20` song song (`Promise.all`) trước khi lắng nghe Socket.IO.
2. **Khôi phục từ chế độ nền (`visibilitychange` / Socket `connect` lại):** Khi người dùng mở khóa màn hình điện thoại hoặc chuyển từ 4G sang Wi-Fi, Frontend tự động gọi lại `GET /api/nodes` và `GET /api/nodes/<active_id>/telemetry?limit=30` để bù dữ liệu bị thiếu trong lúc trình duyệt ngắt WebSocket.
