CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nodes (
    node_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location_desc VARCHAR(255),
    latitude FLOAT NOT NULL DEFAULT 21.0075,
    longitude FLOAT NOT NULL DEFAULT 105.8394,
    is_virtual BOOLEAN NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'offline',
    mode VARCHAR(16) NOT NULL DEFAULT 'AUTO',
    water_level_cm FLOAT NOT NULL DEFAULT 0.0,
    flow_rate_lpm FLOAT NOT NULL DEFAULT 0.0,
    pump_active BOOLEAN NOT NULL DEFAULT 0,
    alert_level VARCHAR(16) NOT NULL DEFAULT 'NORMAL',
    last_seen DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS node_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    node_id VARCHAR(32) NOT NULL,
    notify_alert BOOLEAN NOT NULL DEFAULT 1,
    notify_pump BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, node_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES nodes(node_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS telemetry_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id VARCHAR(32) NOT NULL,
    water_level_cm FLOAT NOT NULL,
    flow_rate_lpm FLOAT NOT NULL,
    pump_active BOOLEAN NOT NULL,
    alert_level VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES nodes(node_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_telemetry_node_time
    ON telemetry_logs (node_id, created_at);

CREATE TABLE IF NOT EXISTS alert_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id VARCHAR(32) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    message TEXT NOT NULL,
    water_level_cm FLOAT,
    pump_active BOOLEAN,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES nodes(node_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alert_node_time
    ON alert_logs (node_id, created_at);

CREATE TABLE IF NOT EXISTS fcm_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    token VARCHAR(255) NOT NULL UNIQUE,
    device_name VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
