import base64
import logging

logger = logging.getLogger(__name__)


class EventHandlers:
    def __init__(self):
        self.gui_callback = None
        self.audio_player = None
        self.text_buffer = ""

    def set_gui_callback(self, callback):
        self.gui_callback = callback

    def set_audio_player(self, player):
        self.audio_player = player

    def on_chat_created(self, data):
        logger.info("对话连接成功: logid=%s", data.get("detail", {}).get("logid", ""))
        if self.gui_callback:
            self.gui_callback("status", "已连接到 Coze 服务")

    def on_chat_updated(self, data):
        config_info = data.get("data", {})
        logger.info("对话配置已更新: %s", config_info)
        if self.gui_callback:
            self.gui_callback("status", "对话就绪，可以开始说话")

    def on_conversation_chat_created(self, data):
        logger.info("对话开始")
        if self.gui_callback:
            self.gui_callback("status", "智能体正在思考...")

    def on_message_delta(self, data):
        data_obj = data.get("data", {})
        content_type = data_obj.get("content_type", "text")
        if content_type == "audio":
            return
        content = data_obj.get("content", "")
        self.text_buffer += content
        if self.gui_callback:
            self.gui_callback("text_delta", content)

    def on_audio_sentence_start(self, data):
        logger.info("新字幕句开始")
        self.text_buffer = ""
        if self.gui_callback:
            self.gui_callback("sentence_start", "")

    def on_audio_delta(self, data):
        data_obj = data.get("data", {})
        content_b64 = data_obj.get("content", "")
        if content_b64 and self.audio_player:
            try:
                pcm_bytes = base64.b64decode(content_b64)
                self.audio_player.enqueue(pcm_bytes)
            except Exception as e:
                logger.error("音频数据解码失败: %s", e)
        elif not self.audio_player:
            logger.warning("音频播放器未就绪，无法播放音频")

    def on_message_completed(self, data):
        logger.info("消息已完成")
        full_text = ""
        msgs = data.get("data", {}).get("messages", [])
        for msg in msgs:
            if msg.get("role") == "assistant" and msg.get("type") == "answer":
                full_text = msg.get("content", "")
                break

        if self.gui_callback:
            self.gui_callback("text_complete", full_text or self.text_buffer)
            self.gui_callback("status", "对话就绪，可以继续说话")

        self.text_buffer = ""

    def on_error(self, data):
        error_msg = data.get("error", data.get("msg", "未知错误"))
        logger.error("对话错误: %s", error_msg)
        if self.gui_callback:
            self.gui_callback("status", f"错误: {error_msg}")

    def on_connection_closed(self, data):
        logger.info("连接关闭")
        if self.gui_callback:
            self.gui_callback("status", "连接已断开")

    def on_speech_started(self, data):
        logger.info("检测到说话开始")
        if self.gui_callback:
            self.gui_callback("status", "正在识别语音...")

    def on_speech_stopped(self, data):
        logger.info("检测到说话停止")
        if self.gui_callback:
            self.gui_callback("status", "正在处理语音...")

    def on_transcript_update(self, data):
        transcript = data.get("data", {}).get("transcript", "")
        if transcript and self.gui_callback:
            self.gui_callback("transcript", transcript)

    def on_transcript_completed(self, data):
        transcript = data.get("data", {}).get("transcript", "")
        logger.info("语音转文字完成: %s", transcript)
        if self.gui_callback and transcript:
            self.gui_callback("user_text", transcript)

    def on_chat_in_progress(self, data):
        logger.info("对话进行中")
        if self.gui_callback:
            self.gui_callback("status", "智能体正在回复...")

    def on_audio_completed(self, data):
        logger.info("音频输出完成")

    def on_chat_completed(self, data):
        logger.info("对话完成")
        if self.gui_callback:
            self.gui_callback("status", "对话完成，可以继续")

    def on_chat_failed(self, data):
        error_msg = data.get("data", {}).get("msg", "对话失败")
        logger.error("对话失败: %s", error_msg)
        if self.gui_callback:
            self.gui_callback("status", f"对话失败: {error_msg}")