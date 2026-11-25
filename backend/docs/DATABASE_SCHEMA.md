# Thiết kế Cơ sở dữ liệu (6 Bảng) - Theo Use Case Dashboard

1. **`users`**: Lưu tài khoản người dùng (`id`, `username`, `email`, `password_hash`, `full_name`, `created_at`) phục vụ Use Case *Tạo tài khoản*.
2. **`nodes`**: Lưu thông tin điểm đo kèm tọa độ địa lý (`latitude`, `longitude`) phục vụ Use Case *Xem được bản đồ các nút* và cache chỉ số mới nhất (`water_level_cm`, `flow_rate_lpm`, `pump_active`, `alert_level`) phục vụ Use Case *Xem chi tiết một nút*.
3. **`node_subscriptions`**: Bảng trung gian N-N giữa `users` và `nodes` (`user_id`, `node_id`, `notify_alert`, `notify_pump`) phục vụ Use Case *Đăng ký theo dõi 1 nút*.
4. **`fcm_tokens`**: Lưu token thiết bị di động gắn với `user_id` để bắn thông báo đẩy (Push Notification) đúng tới người dùng đã đăng ký theo dõi nút.
5. **`telemetry_logs`**: Chuỗi thời gian 2s/lần lưu `water_level_cm`, `flow_rate_lpm`, `pump_active`, `alert_level` phục vụ biểu đồ *Xem mực nước hiện tại* và *Xem tốc độ thoát nước hiện tại*.
6. **`alert_logs`**: Lưu lịch sử chuyển trạng thái cảnh báo (`LEVEL_WARNING`, `LEVEL_DANGER`, `LEVEL_NORMAL`) và trạng thái máy bơm (`PUMP_ON`, `PUMP_OFF`) phục vụ *Nhận thông báo cảnh báo* và *Nhận thông tin máy bơm*.
