from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
import json
import logging
import uuid
import time
import threading
import os

from config import (
    VOLCANO_AK, VOLCANO_SK, RTC_APP_ID, RTC_APP_KEY,
    ASR_APP_ID, TTS_APP_ID, AGENT_SERVER_URL, AGENT_API_KEY,
    BOT_USER_ID, CLIENT_PORT, CLIENT_HOST,
)
from volcano_rtc import generate_rtc_token, start_voice_chat, stop_voice_chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)
CORS(app)

active_tasks = {}


@app.route("/")
def index():
    return render_template("index.html",
                           room_id=f"room_{int(time.time())}",
                           user_id=f"user_{uuid.uuid4().hex[:8]}")


@app.route("/api/token", methods=["POST"])
def get_token():
    data = request.get_json() or {}
    room_id = data.get("room_id", f"room_{int(time.time())}")
    user_id = data.get("user_id", f"user_{uuid.uuid4().hex[:8]}")

    try:
        token_info = json.loads(
            generate_rtc_token(RTC_APP_ID, RTC_APP_KEY, room_id, user_id)
        )
        return jsonify({
            "code": 0,
            "data": {
                "app_id": RTC_APP_ID,
                "token": token_info["token"],
                "room_id": room_id,
                "user_id": user_id,
            }
        })
    except Exception as e:
        logger.error("Token 生成失败: %s", e)
        return jsonify({"code": -1, "msg": str(e)}), 500


@app.route("/api/agent/start", methods=["POST"])
def agent_start():
    data = request.get_json() or {}
    room_id = data.get("room_id", "")
    agent_url = data.get("agent_url", AGENT_SERVER_URL)
    agent_api_key = data.get("agent_api_key", AGENT_API_KEY)
    voice_type = data.get("voice_type", "zh_female_shuangkuaisisi_moon_bigtts")
    speaker = data.get("speaker", "")
    bot_audience = data.get("bot_audience", False)

    if not room_id:
        return jsonify({"code": -1, "msg": "缺少 room_id"}), 400

    try:
        task_id = f"agent_{int(time.time())}"
        result = start_voice_chat(
            ak=VOLCANO_AK, sk=VOLCANO_SK,
            app_id=RTC_APP_ID, room_id=room_id,
            agent_url=agent_url, agent_api_key=agent_api_key,
            task_id=task_id, asr_app_id=ASR_APP_ID, tts_app_id=TTS_APP_ID,
            voice_type=voice_type, speaker=speaker,
            bot_audience=bot_audience,
        )

        active_tasks[room_id] = task_id
        logger.info("智能体已启动: RoomId=%s, TaskId=%s", room_id, task_id)

        return jsonify({
            "code": 0,
            "data": {
                "task_id": task_id,
                "room_id": room_id,
                "status": "started",
            }
        })
    except Exception as e:
        logger.error("启动智能体失败: %s", e)
        return jsonify({"code": -1, "msg": str(e)}), 500


@app.route("/api/agent/stop", methods=["POST"])
def agent_stop():
    data = request.get_json() or {}
    room_id = data.get("room_id", "")
    task_id = data.get("task_id", active_tasks.get(room_id, ""))

    if not room_id or not task_id:
        return jsonify({"code": -1, "msg": "缺少 room_id 或 task_id"}), 400

    try:
        stop_voice_chat(VOLCANO_AK, VOLCANO_SK, RTC_APP_ID, room_id, task_id)
        active_tasks.pop(room_id, None)
        logger.info("智能体已停止: RoomId=%s, TaskId=%s", room_id, task_id)
        return jsonify({"code": 0, "data": {"status": "stopped"}})
    except Exception as e:
        logger.error("停止智能体失败: %s", e)
        return jsonify({"code": -1, "msg": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify({
        "code": 0,
        "data": {
            "active_tasks": active_tasks,
            "agent_url": AGENT_SERVER_URL,
        }
    })


if __name__ == "__main__":
    logger.info("客户端后端启动: http://%s:%s", CLIENT_HOST, CLIENT_PORT)
    app.run(host=CLIENT_HOST, port=CLIENT_PORT, debug=True, use_reloader=False)