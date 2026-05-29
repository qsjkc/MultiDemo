import os

VOLCANO_AK = os.environ.get("VOLCANO_AK", "your_access_key_id")
VOLCANO_SK = os.environ.get("VOLCANO_SK", "your_secret_access_key")

RTC_APP_ID = os.environ.get("RTC_APP_ID", "your_rtc_app_id")
RTC_APP_KEY = os.environ.get("RTC_APP_KEY", "your_rtc_app_key")

ASR_APP_ID = os.environ.get("ASR_APP_ID", "")
TTS_APP_ID = os.environ.get("TTS_APP_ID", "")

AGENT_SERVER_URL = os.environ.get("AGENT_SERVER_URL", "https://your-server.com/chat")
AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "agent-secret-key")

BOT_USER_ID = os.environ.get("BOT_USER_ID", "ai_bot_001")

CLIENT_PORT = int(os.environ.get("CLIENT_PORT", "5000"))
CLIENT_HOST = os.environ.get("CLIENT_HOST", "0.0.0.0")