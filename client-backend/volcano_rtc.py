import hashlib
import hmac
import json
import time
import logging
import random
import string

import requests

logger = logging.getLogger(__name__)

RTC_HOST = "https://rtc.volcengineapi.com"
SERVICE = "rtc"
REGION = "cn-north-1"


def _sign(ak, sk, method, uri, query, payload, timestamp):
    """火山引擎 API Signature V4 签名"""
    content_type = "application/json"
    body = json.dumps(payload) if payload else ""

    x_content_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()

    x_date = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(timestamp))
    x_date_short = x_date[:8]

    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_headers = "\n".join([
        f"content-type:{content_type}",
        f"host:{RTC_HOST.replace('https://', '')}",
        f"x-content-sha256:{x_content_sha256}",
        f"x-date:{x_date}",
    ])

    canonical_query = "&".join(sorted([f"{k}={v}" for k, v in sorted(query.items())]))

    canonical_request = "\n".join([
        method.upper(),
        uri,
        canonical_query,
        canonical_headers + "\n",
        signed_headers,
        x_content_sha256,
    ])

    credential_scope = f"{x_date_short}/{REGION}/{SERVICE}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256",
        x_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    k_date = hmac.new(ak.encode("utf-8"), x_date_short.encode("utf-8"), hashlib.sha256).digest()
    k_region = hmac.new(k_date, REGION.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, SERVICE.encode("utf-8"), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, "request".encode("utf-8"), hashlib.sha256).digest()

    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    return {
        "Content-Type": content_type,
        "X-Date": x_date,
        "X-Content-Sha256": x_content_sha256,
        "Authorization": authorization,
    }


def _call_api(ak, sk, action, version, body):
    method = "POST"
    uri = "/"
    query = {"Action": action, "Version": version}

    timestamp = int(time.time())
    headers = _sign(ak, sk, method, uri, query, body, timestamp)
    headers["Host"] = RTC_HOST.replace("https://", "")

    url = f"{RTC_HOST}/?Action={action}&Version={version}"
    resp = requests.post(url, headers=headers, json=body, timeout=15)

    result = resp.json()
    if "ResponseMetadata" in result:
        error = result["ResponseMetadata"].get("Error")
        if error:
            logger.error("API %s 错误: %s - %s", action, error.get("Code"), error.get("Message"))
            raise RuntimeError(f"{error.get('Code')}: {error.get('Message')}")
    return result


def generate_rtc_token(app_id: str, app_key: str, room_id: str, user_id: str,
                        expire_seconds: int = 86400) -> str:
    """生成 RTC 进房 Token"""
    token_version = "001"
    prefix = hashlib.md5(room_id.encode()).hexdigest()
    cur_time = int(time.time())
    expire_time = cur_time + expire_seconds

    content = {
        "app_id": app_id,
        "room_id": room_id,
        "user_id": user_id,
        "cur_time": cur_time,
        "expire_time": expire_time,
        "nonce": ''.join(random.choices(string.ascii_letters + string.digits, k=8)),
    }
    payload = json.dumps(content)

    sign_raw = token_version + app_key + payload
    signature = hmac.new(app_key.encode(), sign_raw.encode(), hashlib.sha256).hexdigest()

    token = token_version + signature + payload
    return json.dumps({
        "token": token,
        "app_id": app_id,
        "room_id": room_id,
        "user_id": user_id,
        "expire_time": expire_time,
    })


def start_voice_chat(ak: str, sk: str, app_id: str, room_id: str,
                     agent_url: str, agent_api_key: str = "",
                     bot_user_id: str = "ai_bot_001",
                     task_id: str = None,
                     asr_app_id: str = "", tts_app_id: str = "",
                     voice_type: str = "zh_female_shuangkuaisisi_moon_bigtts",
                     speaker: str = "",
                     bot_audience: bool = False) -> dict:
    """启动实时对话智能体

    主要参数：
    - ak/sk: 火山引擎 API 密钥
    - app_id: RTC 应用 ID
    - room_id: RTC 房间 ID
    - agent_url: 第三方 Agent 服务器的 URL
    - agent_api_key: Agent 服务器的 API Key
    - asr_app_id: ASR 应用 ID
    - tts_app_id: TTS 应用 ID
    - voice_type: TTS 音色类型
    - speaker: 自定义音色 speaker id
    - bot_audience: 智能体是否仅聆听不回应
    """
    if task_id is None:
        task_id = f"agent_{int(time.time())}_{random.randint(1000, 9999)}"

    config = {
        "BotName": bot_user_id,
        "UserId": bot_user_id,

        "ASRConfig": {
            "Vad": {
                "VadLevel": 1,
                "StartSilenceTimeMs": 800,
                "EndSilenceTimeMs": 600,
            },
        },
        "TTSConfig": {
            "SpeedRatio": 1.0,
            "VolumeRatio": 1.0,
            "PitchRatio": 1.0,
            "Emotion": "",
            "VoiceType": voice_type,
            "WithTimestamp": True,
            "AudioChannel": 1,
            "SampleRate": 24000,
            "Encoding": "raw",
            "EnableCallBack": True,
        },

        "LLMConfig": {
            "Mode": "CustomLLM",
            "Url": agent_url,
            "APIKey": agent_api_key,
            "HistoryLength": 10,
            "ThinkingMode": "auto",
        },

        "AgentConfig": {
            "UserId": bot_user_id,
            "InterruptSpeechDuration": 500,
            "InterruptResponseDuration": 2000,
            "WelcomeMessage": "你好！我是智能语音助手，可以帮你查天气、算数学题，有什么需要吗？",
            "EnableNoiseDetection": True,
            "BotAudience": bot_audience,
        },
    }

    if asr_app_id:
        config["ASRConfig"]["AppId"] = asr_app_id
    if tts_app_id:
        config["TTSConfig"]["AppId"] = tts_app_id
    if speaker:
        config["TTSConfig"]["Speaker"] = speaker

    body = {
        "AppId": app_id,
        "RoomId": room_id,
        "TaskId": task_id,
        "Config": config,
    }

    logger.info("StartVoiceChat 请求: RoomId=%s, TaskId=%s, AgentUrl=%s",
                room_id, task_id, agent_url)
    return _call_api(ak, sk, "StartVoiceChat", "2024-12-01", body)


def stop_voice_chat(ak: str, sk: str, app_id: str, room_id: str, task_id: str) -> dict:
    """停止实时对话智能体"""
    body = {
        "AppId": app_id,
        "RoomId": room_id,
        "TaskId": task_id,
    }
    logger.info("StopVoiceChat 请求: RoomId=%s, TaskId=%s", room_id, task_id)
    return _call_api(ak, sk, "StopVoiceChat", "2024-12-01", body)


def update_voice_chat_url(ak: str, sk: str, app_id: str, room_id: str,
                           task_id: str, new_url: str, new_api_key: str = "") -> dict:
    """更新智能体的 Agent 服务器地址"""
    body = {
        "AppId": app_id,
        "RoomId": room_id,
        "TaskId": task_id,
        "LLMConfig": {
            "Mode": "CustomLLM",
            "Url": new_url,
            "APIKey": new_api_key,
        },
    }
    return _call_api(ak, sk, "UpdateVoiceChat", "2024-12-01", body)