# Data Contract: Firmware - Backend

## 1. Cấu hình MQTT chung
- **Protocol:** MQTT 3.1.1
- **Format:** JSON (UTF-8)
- **Tần suất publish:** 2 giây / lần (và publish ngay lập tức khi trạng thái bơm hoặc cảnh báo thay đổi)
- **QoS:** `0` cho dữ liệu cảm biến định kỳ, `1` cho trạng thái Online/Offline.

---

## 2. Danh sách Topics

### A. Dữ liệu cảm biến & trạng thái Node (ESP32 -> Backend)
- **Topic:** `flood_system/nodes/{node_id}/telemetry`
  *(Ví dụ: `flood_system/nodes/node_01/telemetry`)*

- **Payload mẫu:**
```json
{
  "node_id": "node_01",
  "water_level_cm": 14.5,
  "flow_rate_lpm": 1.25,
  "pump_active": true,
  "alert_level": "WARNING"
}
```

- **Quy định chi tiết từng trường:**

| Key | Kiểu dữ liệu | Đơn vị / Giá trị | Mô tả |
| :--- | :--- | :--- | :--- |
| `node_id` | `string` | Ví dụ: `"node_01"` | Mã định danh của từng Node trên sa bàn |
| `water_level_cm` | `float` | `cm` (làm tròn 2 chữ số) | Chiều cao mực nước tính từ đáy khay (đã lọc nhiễu) |
| `flow_rate_lpm` | `float` | `L/phút` (Liters per min) | Tốc độ thoát nước đo từ cảm biến lưu lượng |
| `pump_active` | `boolean` | `true` / `false` | `true`: máy bơm đang chạy, `false`: đang tắt |
| `alert_level` | `string` | `"NORMAL"`, `"WARNING"`, `"DANGER"` | Mức cảnh báo (tương ứng trạng thái LED trên sa bàn) |

*(Lưu ý: Backend tự sinh `timestamp` theo giờ server ngay khi nhận được bản tin để lưu vào Database Logs).*

---

### B. Trạng thái Sống / Chết của Node (ESP32 -> Backend)
Dùng cơ chế **LWT (Last Will and Testament)** của MQTT với cờ `retain = true` để Dashboard luôn biết Node đang sống hay sập nguồn.
- **Topic:** `flood_system/nodes/{node_id}/status`
- **Payload:**
  - Khi ESP32 vừa kết nối MQTT: gửi `{"status": "online"}`
  - Khi ESP32 mất điện / rớt mạng (Broker tự gửi hộ qua LWT): `{"status": "offline"}`

---

### C. Điều khiển từ Dashboard xuống ESP32 (Backend -> ESP32)
Phòng trường hợp sau này nhóm mày muốn có nút bật/tắt bơm thủ công trên web lúc demo:
- **Topic:** `flood_system/nodes/{node_id}/command`
- **Payload mẫu:**
```json
{
  "mode": "MANUAL",
  "pump_command": true
}
```
*(Giá trị `mode`: `"AUTO"` hoặc `"MANUAL"`).*