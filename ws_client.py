import json
import time
import logging
import threading
from websocket import WebSocketApp, WebSocketException

import config

logger = logging.getLogger(__name__)


class CozeWSClient:
    def __init__(self):
        self.ws = None
        self.ws_thread = None
        self.connected = False
        self.event_counter = 0
        self._lock = threading.Lock()

        self.on_chat_created = None
        self.on_chat_updated = None
        self.on_conversation_chat_created = None
        self.on_message_delta = None
        self.on_audio_sentence_start = None
        self.on_audio_delta = None
        self.on_message_completed = None
        self.on_error = None
        self.on_connection_closed = None
        self.on_input_audio_buffer_completed = None
        self.on_conversation_chat_canceled = None
        self.on_speech_started = None
        self.on_speech_stopped = None
        self.on_transcript_update = None
        self.on_transcript_completed = None
        self.on_chat_in_progress = None
        self.on_audio_completed = None
        self.on_chat_completed = None
        self.on_chat_failed = None

    def _next_event_id(self):
        with self._lock:
            self.event_counter += 1
            return f"evt_{self.event_counter}"

    def connect(self):
        headers = {"Authorization": f"Bearer {config.ACCESS_TOKEN}"}
        self.ws = WebSocketApp(
            config.WS_URL,
            header=headers,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.ws_thread.start()

    def disconnect(self):
        if self.ws:
            self.ws.close()

    def _on_open(self, ws):
        logger.info("WebSocket 连接已建立")
        self.connected = True

    def _on_message(self, ws, raw_message):
        try:
            msg = json.loads(raw_message)
            event_type = msg.get("event_type", "")
            logger.debug("收到事件: %s", event_type)

            if event_type == "chat.created":
                self._trigger(self.on_chat_created, msg)
            elif event_type == "chat.updated":
                self._trigger(self.on_chat_updated, msg)
            elif event_type == "conversation.chat.created":
                self._trigger(self.on_conversation_chat_created, msg)
            elif event_type == "conversation.message.delta":
                self._trigger(self.on_message_delta, msg)
            elif event_type == "conversation.audio.sentence_start":
                self._trigger(self.on_audio_sentence_start, msg)
            elif event_type == "conversation.audio.delta":
                self._trigger(self.on_audio_delta, msg)
            elif event_type == "conversation.message.completed":
                self._trigger(self.on_message_completed, msg)
            elif event_type == "input_audio_buffer.completed":
                self._trigger(self.on_input_audio_buffer_completed, msg)
            elif event_type == "conversation.chat.canceled":
                self._trigger(self.on_conversation_chat_canceled, msg)
            elif event_type == "input_audio_buffer.speech_started":
                self._trigger(self.on_speech_started, msg)
            elif event_type == "input_audio_buffer.speech_stopped":
                self._trigger(self.on_speech_stopped, msg)
            elif event_type == "conversation.audio_transcript.update":
                self._trigger(self.on_transcript_update, msg)
            elif event_type == "conversation.audio_transcript.completed":
                self._trigger(self.on_transcript_completed, msg)
            elif event_type == "conversation.chat.in_progress":
                self._trigger(self.on_chat_in_progress, msg)
            elif event_type == "conversation.audio.completed":
                self._trigger(self.on_audio_completed, msg)
            elif event_type == "conversation.chat.completed":
                self._trigger(self.on_chat_completed, msg)
            elif event_type == "conversation.chat.failed":
                self._trigger(self.on_chat_failed, msg)
            elif event_type == "error":
                logger.error("服务端错误: %s", json.dumps(msg, ensure_ascii=False))
                self._trigger(self.on_error, msg)
            else:
                logger.debug("未处理的事件: %s", event_type)
        except json.JSONDecodeError as e:
            logger.error("消息解析失败: %s", e)

    def _on_error(self, ws, error):
        logger.error("WebSocket 错误: %s", error)
        self._trigger(self.on_error, {"error": str(error)})

    def _on_close(self, ws, close_status, close_msg):
        logger.info("WebSocket 连接关闭: %s - %s", close_status, close_msg)
        self.connected = False
        self._trigger(self.on_connection_closed, {"status": close_status, "msg": close_msg})

    def _trigger(self, handler, data):
        if handler:
            try:
                handler(data)
            except Exception as e:
                logger.error("事件处理器异常: %s", e)

    def _send(self, event):
        if not self.ws or not self.connected:
            logger.warning("WebSocket 未连接，无法发送事件")
            return
        raw = json.dumps(event, ensure_ascii=False)
        self.ws.send(raw)
        logger.debug("发送事件: %s", event.get("event_type"))

    def send_chat_update(self, turn_detection_type="client_interrupt"):
        event = {
            "id": self._next_event_id(),
            "event_type": "chat.update",
            "data": {
                "chat_config": {
                    "auto_save_history": True,
                    "user_id": "demo_user",
                },
                "input_audio": {
                    "format": config.INPUT_AUDIO_FORMAT,
                    "codec": config.INPUT_AUDIO_CODEC,
                    "sample_rate": config.INPUT_SAMPLE_RATE,
                    "channel": config.INPUT_CHANNELS,
                    "bit_depth": config.INPUT_BIT_DEPTH,
                },
                "output_audio": {
                    "codec": config.OUTPUT_AUDIO_CODEC,
                    "speech_rate": 0,
                },
                "turn_detection": {
                    "type": turn_detection_type,
                },
            },
        }

        if turn_detection_type == "server_vad":
            event["data"]["turn_detection"]["prefix_padding_ms"] = config.VAD_PREFIX_PADDING_MS
            event["data"]["turn_detection"]["silence_duration_ms"] = config.VAD_SILENCE_DURATION_MS

        self._send(event)

    def send_audio_chunk(self, pcm_bytes):
        import base64
        event = {
            "id": self._next_event_id(),
            "event_type": "input_audio_buffer.append",
            "data": {
                "delta": base64.b64encode(pcm_bytes).decode("ascii"),
            },
        }
        self._send(event)

    def send_audio_complete(self):
        event = {
            "id": self._next_event_id(),
            "event_type": "input_audio_buffer.complete",
        }
        self._send(event)

    def send_audio_clear(self):
        event = {
            "id": self._next_event_id(),
            "event_type": "input_audio_buffer.clear",
        }
        self._send(event)

    def send_message(self, content, content_type="text"):
        event = {
            "id": self._next_event_id(),
            "event_type": "conversation.message.create",
            "data": {
                "role": "user",
                "content_type": content_type,
                "content": content,
            },
        }
        self._send(event)

    def send_text_message(self, text):
        self.send_message(text, content_type="text")

    def send_object_string_message(self, objects):
        self.send_message(json.dumps(objects, ensure_ascii=False), content_type="object_string")

    def send_cancel(self):
        event = {
            "id": self._next_event_id(),
            "event_type": "conversation.chat.cancel",
        }
        self._send(event)

    def send_clear_context(self):
        event = {
            "id": self._next_event_id(),
            "event_type": "conversation.clear",
        }
        self._send(event)