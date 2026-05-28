import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import time
import logging
import json

import config
from ws_client import CozeWSClient
from audio_io import AudioRecorder, AudioPlayer
from event_handlers import EventHandlers
from media_utils import build_image_message

logger = logging.getLogger(__name__)


class CozeVoiceDemo:
    def __init__(self, root):
        self.root = root
        self.root.title("Coze 流式语音对话 Demo")
        self.root.geometry("700x650")
        self.root.minsize(550, 500)

        self.client = CozeWSClient()
        self.recorder = AudioRecorder()
        self.player = AudioPlayer()
        self.handlers = EventHandlers()

        self._bind_events()
        self.handlers.set_gui_callback(self._on_gui_event)
        self.handlers.set_audio_player(self.player)

        self.vad_active = False
        self.vad_thread = None
        self.push_to_talk_pressed = False
        self.push_to_talk_thread = None

        self._build_ui()

    def _bind_events(self):
        self.client.on_chat_created = self.handlers.on_chat_created
        self.client.on_chat_updated = self.handlers.on_chat_updated
        self.client.on_conversation_chat_created = self.handlers.on_conversation_chat_created
        self.client.on_message_delta = self.handlers.on_message_delta
        self.client.on_audio_sentence_start = self.handlers.on_audio_sentence_start
        self.client.on_audio_delta = self.handlers.on_audio_delta
        self.client.on_message_completed = self.handlers.on_message_completed
        self.client.on_error = self.handlers.on_error
        self.client.on_connection_closed = self.handlers.on_connection_closed
        self.client.on_input_audio_buffer_completed = lambda d: logger.info("音频提交完成")
        self.client.on_conversation_chat_canceled = lambda d: logger.info("对话已取消")
        self.client.on_speech_started = self.handlers.on_speech_started
        self.client.on_speech_stopped = self.handlers.on_speech_stopped
        self.client.on_transcript_update = self.handlers.on_transcript_update
        self.client.on_transcript_completed = self.handlers.on_transcript_completed
        self.client.on_chat_in_progress = self.handlers.on_chat_in_progress
        self.client.on_audio_completed = self.handlers.on_audio_completed
        self.client.on_chat_completed = self.handlers.on_chat_completed
        self.client.on_chat_failed = self.handlers.on_chat_failed

    def _on_gui_event(self, event_type, data):
        self.root.after(0, self._handle_gui_event, event_type, data)

    def _handle_gui_event(self, event_type, data):
        if event_type == "status":
            self.status_var.set(data)
        elif event_type == "text_delta":
            self.conversation_text.insert(tk.END, data)
            self.conversation_text.see(tk.END)
        elif event_type == "sentence_start":
            self.conversation_text.insert(tk.END, "\n[AI]: ")
            self.conversation_text.see(tk.END)
        elif event_type == "text_complete":
            if data and not data.startswith("\n[AI]:"):
                current = self.conversation_text.get("end-2l", "end-1c")
                if "[AI]:" in current:
                    self.conversation_text.insert(tk.END, "\n")
            self.conversation_text.see(tk.END)
        elif event_type == "user_text":
            self.conversation_text.insert(tk.END, f"\n[你]: {data}")
            self.conversation_text.see(tk.END)
        elif event_type == "transcript":
            pass

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.push_talk_frame = ttk.Frame(notebook)
        self.vad_frame = ttk.Frame(notebook)
        self.image_frame = ttk.Frame(notebook)

        notebook.add(self.push_talk_frame, text="🎤 按键对话")
        notebook.add(self.vad_frame, text="🔊 VAD 自由对话")
        notebook.add(self.image_frame, text="🖼️ 上传图片")

        self._build_status_bar()
        self._build_push_talk_tab()
        self._build_vad_tab()
        self._build_image_tab()
        self._build_conversation_log()

    def _build_status_bar(self):
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=8, pady=(0, 4))

        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT, padx=(0, 4))
        self.status_var = tk.StringVar(value="未连接")
        ttk.Label(status_frame, textvariable=self.status_var, foreground="gray").pack(side=tk.LEFT)

        ttk.Button(status_frame, text="连接服务", command=self._connect).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(status_frame, text="断开连接", command=self._disconnect).pack(side=tk.RIGHT, padx=(4, 0))

    def _build_conversation_log(self):
        log_frame = ttk.LabelFrame(self.root, text="对话记录")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.conversation_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, height=10, font=("Microsoft YaHei", 10)
        )
        self.conversation_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.conversation_text.insert(tk.END, "=== Coze 流式语音对话 Demo ===\n")
        self.conversation_text.insert(tk.END, "请先点击「连接服务」按钮建立 WebSocket 连接\n")

        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.text_input_var = tk.StringVar()
        self.text_input = ttk.Entry(input_frame, textvariable=self.text_input_var, font=("Microsoft YaHei", 10), width=50)
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.text_input.bind("<Return>", self._on_send_text)

        ttk.Button(input_frame, text="发送", command=self._on_send_text).pack(side=tk.RIGHT)

    def _on_send_text(self, event=None):
        text = self.text_input_var.get().strip()
        if not text:
            return
        if not self.client.connected:
            self.status_var.set("请先建立 WebSocket 连接")
            return

        self.client.send_text_message(text)
        self.conversation_text.insert(tk.END, f"\n[你]: {text}\n")
        self.conversation_text.see(tk.END)
        self.text_input_var.set("")
        self.status_var.set("正在发送文字...")

    def _build_push_talk_tab(self):
        pad = {"padx": 16, "pady": 8}

        info_label = ttk.Label(
            self.push_talk_frame,
            text="长按下方按钮开始录音，松开按钮结束录音并发送\n服务端将识别语音并返回回复",
            justify=tk.CENTER,
        )
        info_label.pack(fill=tk.X, **pad)

        self.ptt_button = tk.Button(
            self.push_talk_frame,
            text="按住说话",
            font=("Microsoft YaHei", 16, "bold"),
            bg="#4CAF50",
            fg="white",
            relief=tk.RAISED,
            bd=4,
            padx=40,
            pady=30,
            cursor="hand2",
        )
        self.ptt_button.pack(pady=20)
        self.ptt_button.bind("<ButtonPress-1>", self._on_push_talk_press)
        self.ptt_button.bind("<ButtonRelease-1>", self._on_push_talk_release)

        ptt_status_var = tk.StringVar(value="松开按钮后自动发送语音")
        ttk.Label(self.push_talk_frame, textvariable=ptt_status_var, foreground="gray").pack(**pad)

        config_frame = ttk.LabelFrame(self.push_talk_frame, text="设置")
        config_frame.pack(fill=tk.X, **pad)

        ttk.Label(config_frame, text="音色 ID:").pack(side=tk.LEFT, padx=(4, 2))
        self.voice_id_var = tk.StringVar(value="")
        ttk.Entry(config_frame, textvariable=self.voice_id_var, width=24).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(config_frame, text="语速:").pack(side=tk.LEFT, padx=(4, 2))
        self.speech_rate_var = tk.IntVar(value=0)
        ttk.Scale(config_frame, from_=-50, to=100, variable=self.speech_rate_var, length=100).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(config_frame, textvariable=self.speech_rate_var, width=4).pack(side=tk.LEFT)

    def _on_push_talk_press(self, event):
        self.push_to_talk_pressed = True
        self.ptt_button.config(bg="#F44336", text="正在录音... 松开发送")
        self.recorder.clear_buffer()
        self.recorder.resume()
        self.status_var.set("正在录音...")
        self.conversation_text.insert(tk.END, "\n[你]: (录音中...)")
        self.conversation_text.see(tk.END)

        self.push_to_talk_thread = threading.Thread(target=self._ptt_audio_loop, daemon=True)
        self.push_to_talk_thread.start()

    def _on_push_talk_release(self, event):
        self.push_to_talk_pressed = False
        self.ptt_button.config(bg="#4CAF50", text="按住说话")
        self.recorder.pause()

        for _ in range(50):
            chunk = self.recorder.read_chunk(timeout=0.05)
            if chunk:
                try:
                    self.client.send_audio_chunk(chunk)
                except Exception as e:
                    logger.error("发送尾块失败: %s", e)
            else:
                break

        self.status_var.set("正在发送语音...")
        self.client.send_audio_complete()

    def _ptt_audio_loop(self):
        while self.push_to_talk_pressed and self.client.connected:
            chunk = self.recorder.read_chunk(timeout=0.1)
            if chunk:
                try:
                    self.client.send_audio_chunk(chunk)
                except Exception as e:
                    logger.error("发送音频块失败: %s", e)

    def _build_vad_tab(self):
        pad = {"padx": 16, "pady": 8}

        info_label = ttk.Label(
            self.vad_frame,
            text="VAD 模式：服务端自动检测说话起止\n点击开始按钮后，自由说话即可，无需手动控制",
            justify=tk.CENTER,
        )
        info_label.pack(fill=tk.X, **pad)

        btn_frame = ttk.Frame(self.vad_frame)
        btn_frame.pack(pady=16)

        self.vad_start_btn = tk.Button(
            btn_frame,
            text="▶ 开始对话",
            font=("Microsoft YaHei", 13, "bold"),
            bg="#2196F3",
            fg="white",
            relief=tk.RAISED,
            bd=3,
            padx=24,
            pady=12,
            cursor="hand2",
            command=self._on_vad_start,
        )
        self.vad_start_btn.pack(side=tk.LEFT, padx=8)

        self.vad_stop_btn = tk.Button(
            btn_frame,
            text="⏹ 停止对话",
            font=("Microsoft YaHei", 13, "bold"),
            bg="#F44336",
            fg="white",
            relief=tk.RAISED,
            bd=3,
            padx=24,
            pady=12,
            cursor="hand2",
            command=self._on_vad_stop,
            state=tk.DISABLED,
        )
        self.vad_stop_btn.pack(side=tk.LEFT, padx=8)

        self.vad_cancel_btn = tk.Button(
            btn_frame,
            text="⏸ 打断回复",
            font=("Microsoft YaHei", 13, "bold"),
            bg="#FF9800",
            fg="white",
            relief=tk.RAISED,
            bd=3,
            padx=24,
            pady=12,
            cursor="hand2",
            command=self._on_vad_cancel,
            state=tk.DISABLED,
        )
        self.vad_cancel_btn.pack(side=tk.LEFT, padx=8)

        vad_status_var = tk.StringVar(value="点击「开始对话」进入 VAD 模式")
        ttk.Label(self.vad_frame, textvariable=vad_status_var, foreground="gray").pack(**pad)

        self.vad_indicator = tk.Canvas(self.vad_frame, width=60, height=60, highlightthickness=0)
        self.vad_indicator.pack(pady=8)
        self._vad_dot = self.vad_indicator.create_oval(15, 15, 45, 45, fill="gray", outline="")

        config_frame = ttk.LabelFrame(self.vad_frame, text="VAD 设置")
        config_frame.pack(fill=tk.X, **pad)

        ttk.Label(config_frame, text="静音检测(ms):").pack(side=tk.LEFT, padx=(4, 2))
        self.vad_silence_var = tk.IntVar(value=500)
        ttk.Entry(config_frame, textvariable=self.vad_silence_var, width=6).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(config_frame, text="前缀填充(ms):").pack(side=tk.LEFT, padx=(4, 2))
        self.vad_prefix_var = tk.IntVar(value=600)
        ttk.Entry(config_frame, textvariable=self.vad_prefix_var, width=6).pack(side=tk.LEFT)

    def _build_image_tab(self):
        pad = {"padx": 16, "pady": 8}

        info_label = ttk.Label(
            self.image_frame,
            text="选择一张图片，输入可选的文本描述，发送给智能体进行识别分析",
            justify=tk.CENTER,
        )
        info_label.pack(fill=tk.X, **pad)

        select_frame = ttk.Frame(self.image_frame)
        select_frame.pack(pady=12)

        self.image_path_var = tk.StringVar()
        ttk.Entry(select_frame, textvariable=self.image_path_var, width=40).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(select_frame, text="选择图片", command=self._on_select_image).pack(side=tk.LEFT)

        prompt_frame = ttk.Frame(self.image_frame)
        prompt_frame.pack(fill=tk.X, pady=4)

        ttk.Label(prompt_frame, text="提示文字 (可选):").pack(side=tk.LEFT, padx=(16, 4))
        self.image_prompt_var = tk.StringVar()
        ttk.Entry(prompt_frame, textvariable=self.image_prompt_var, width=50).pack(side=tk.LEFT)

        self.send_image_btn = tk.Button(
            self.image_frame,
            text="发送图片给智能体",
            font=("Microsoft YaHei", 12, "bold"),
            bg="#9C27B0",
            fg="white",
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=10,
            cursor="hand2",
            command=self._on_send_image,
        )
        self.send_image_btn.pack(pady=16)

        self.image_preview_label = ttk.Label(self.image_frame, text="尚未选择图片")
        self.image_preview_label.pack(**pad)

    def _on_select_image(self):
        filepath = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
                ("所有文件", "*.*"),
            ],
        )
        if filepath:
            self.image_path_var.set(filepath)
            self.image_preview_label.config(text=f"已选择: {filepath}")

    def _on_send_image(self):
        image_path = self.image_path_var.get().strip()
        if not image_path:
            self.status_var.set("请先选择一张图片")
            return

        if not self.client.connected:
            self.status_var.set("请先建立 WebSocket 连接")
            return

        try:
            prompt = self.image_prompt_var.get().strip()
            objects = build_image_message(image_path, prompt_text=prompt)
            
            import json
            msg_str = json.dumps(objects, ensure_ascii=False)
            logger.info(f"发送图片消息: {len(msg_str)} 字符，对象数量: {len(objects)}")
            for i, obj in enumerate(objects):
                logger.info(f"  对象 {i}: type={obj.get('type')}, size={len(str(obj))}")

            self.client.send_audio_clear()

            self.client.send_object_string_message(objects)

            self.conversation_text.insert(tk.END, f"\n[你]: [发送图片] {image_path}\n")
            if prompt:
                self.conversation_text.insert(tk.END, f"[你]: {prompt}\n")
            self.conversation_text.see(tk.END)
            self.status_var.set("图片已发送，等待智能体回复...")

        except Exception as e:
            self.status_var.set(f"图片处理失败: {e}")
            logger.error("图片处理失败: %s", e)

    def _connect(self):
        if self.client.connected:
            self.status_var.set("已连接，无需重复连接")
            return

        self.status_var.set("正在连接...")
        self.client.connect()
        self.player.start()

        def wait_connect():
            time.sleep(0.5)
            self.root.after(0, self._on_connected)

        threading.Thread(target=wait_connect, daemon=True).start()

    def _on_connected(self):
        if not self.client.connected:
            self.root.after(500, self._on_connected)
            return

        self.client.send_chat_update(turn_detection_type="client_interrupt")
        self.recorder.start()
        self.recorder.pause()
        self.status_var.set("已连接，按键模式就绪")

    def _disconnect(self):
        if not self.client.connected:
            return

        self.push_to_talk_pressed = False
        self._stop_vad()
        self.vad_start_btn.config(state=tk.NORMAL)
        self.vad_stop_btn.config(state=tk.DISABLED)
        self.vad_cancel_btn.config(state=tk.DISABLED)
        self.vad_indicator.itemconfig(self._vad_dot, fill="gray")
        self.client.disconnect()
        self.recorder.stop()
        self.player.stop()
        self.status_var.set("已断开连接")

    def _on_vad_start(self):
        if not self.client.connected:
            self.status_var.set("请先建立 WebSocket 连接")
            return

        self.vad_start_btn.config(state=tk.DISABLED)
        self.vad_stop_btn.config(state=tk.NORMAL)
        self.vad_cancel_btn.config(state=tk.NORMAL)

        config.VAD_SILENCE_DURATION_MS = self.vad_silence_var.get()
        config.VAD_PREFIX_PADDING_MS = self.vad_prefix_var.get()

        self.client.send_chat_update(turn_detection_type="server_vad")
        self.recorder.clear_buffer()
        self.recorder.resume()

        self.vad_active = True
        self.vad_indicator.itemconfig(self._vad_dot, fill="#4CAF50")

        self.vad_thread = threading.Thread(target=self._vad_audio_loop, daemon=True)
        self.vad_thread.start()

        self.status_var.set("VAD 模式已启动，可以自由说话...")

    def _vad_audio_loop(self):
        while self.vad_active and self.client.connected:
            chunk = self.recorder.read_chunk(timeout=0.1)
            if chunk:
                try:
                    self.client.send_audio_chunk(chunk)
                except Exception as e:
                    logger.error("发送音频块失败: %s", e)
        logger.info("VAD 音频循环结束")

    def _on_vad_stop(self):
        self._stop_vad()
        self.vad_start_btn.config(state=tk.NORMAL)
        self.vad_stop_btn.config(state=tk.DISABLED)
        self.vad_cancel_btn.config(state=tk.DISABLED)
        self.vad_indicator.itemconfig(self._vad_dot, fill="gray")
        self.recorder.pause()
        self.client.send_audio_complete()
        self.client.send_audio_clear()
        self.status_var.set("VAD 模式已停止")

    def _on_vad_cancel(self):
        if self.client.connected:
            self.client.send_cancel()
            self.status_var.set("已发送打断请求")

    def _stop_vad(self):
        self.vad_active = False

    def on_close(self):
        self.push_to_talk_pressed = False
        self._stop_vad()
        self.recorder.stop()
        self.player.stop()
        self.client.disconnect()
        self.root.destroy()