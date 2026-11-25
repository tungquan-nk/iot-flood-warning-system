# Backend - Hệ thống Giám sát & Cảnh báo Ngập lụt IoT (Nhóm 5)

# APIs: 
- **Xem được bản đồ các nút** (`GET /api/nodes` kèm `latitude`, `longitude`, trạng thái ngập)
- **Xem chi tiết một nút** (`GET /api/nodes/<node_id>` + Socket.IO room `node:<node_id>`): mực nước, tốc độ thoát nước, thông tin máy bơm và cảnh báo của nút
- **Tạo tài khoản** (`POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`)
- **Đăng ký theo dõi 1 nút** (`POST /api/nodes/<node_id>/subscribe`, `DELETE .../subscribe`, `GET /api/subscriptions`) + lọc Push Notification FCM theo nút đăng ký

## Khởi chạy nhanh
```bash
cp .env.example .env
pip install -r requirements.txt
python run.py
```
Chạy giả lập ESP32 trong terminal thứ 2:
```bash
python scripts/mock_esp32.py
```
