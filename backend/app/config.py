import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///flood_system.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
    MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "flood_system/nodes")

    FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "")
    TELEMETRY_RETENTION_HOURS = int(os.getenv("TELEMETRY_RETENTION_HOURS", "24"))
    TOKEN_MAX_AGE_SECONDS = int(os.getenv("TOKEN_MAX_AGE_SECONDS", "604800"))
