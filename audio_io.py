import logging
import threading
import queue
import numpy as np
import pyaudio

import config

logger = logging.getLogger(__name__)


class AudioRecorder:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self._recording = False
        self._running = False
        self._thread = None
        self._chunk_buffer = queue.Queue()

    @property
    def is_recording(self):
        return self._recording

    def start(self):
        if self._running:
            return
        self._running = True
        self._recording = True
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=config.INPUT_CHANNELS,
            rate=config.INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=config.FRAMES_PER_BUFFER,
            stream_callback=self._audio_callback,
        )
        self.stream.start_stream()
        logger.info("录音已启动: rate=%d, channels=%d, frames_per_buffer=%d",
                    config.INPUT_SAMPLE_RATE, config.INPUT_CHANNELS, config.FRAMES_PER_BUFFER)

    def _audio_callback(self, in_data, frame_count, time_info, status):
        if self._recording:
            self._chunk_buffer.put(in_data)
        return (None, pyaudio.paContinue)

    def pause(self):
        self._recording = False

    def resume(self):
        self._recording = True

    def read_chunk(self, timeout=0.1):
        try:
            return self._chunk_buffer.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear_buffer(self):
        while not self._chunk_buffer.empty():
            try:
                self._chunk_buffer.get_nowait()
            except queue.Empty:
                break

    def stop(self):
        self._running = False
        self._recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.pa.terminate()
        logger.info("录音已停止")


class AudioPlayer:
    def __init__(self):
        import pyaudio
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self._playing = False
        self._queue = queue.Queue()
        self._thread = None
        self._running = False

    @property
    def is_playing(self):
        return self._playing

    def start(self):
        import pyaudio
        if self._running:
            return
        self._running = True
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=config.OUTPUT_CHANNELS,
            rate=config.OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=config.FRAMES_PER_BUFFER,
        )
        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()
        logger.info("播放器已启动: rate=%d, channels=%d",
                    config.OUTPUT_SAMPLE_RATE, config.OUTPUT_CHANNELS)

    def _play_loop(self):
        while self._running:
            try:
                pcm_data = self._queue.get(timeout=0.1)
                if pcm_data is None:
                    break
                self._playing = True
                logger.debug("播放音频块: %d bytes", len(pcm_data))
                self.stream.write(pcm_data)
                self._playing = False
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("播放异常: %s", e)

    def enqueue(self, pcm_data):
        self._queue.put(pcm_data)

    def clear_queue(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def stop(self):
        self._running = False
        self._queue.put(None)
        if self._thread:
            self._thread.join(timeout=1)
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.pa.terminate()
        logger.info("播放器已停止")