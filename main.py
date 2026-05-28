import sys
import os
import logging
import tkinter as tk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("main")


def check_config():
    import config
    if config.BOT_ID == "your_bot_id_here" or config.ACCESS_TOKEN == "your_access_token_here":
        logger.warning("=" * 60)
        logger.warning("请先配置 BOT_ID 和 ACCESS_TOKEN！")
        logger.warning("")
        logger.warning("方式一：设置环境变量")
        logger.warning("  Windows PowerShell:")
        logger.warning('    $env:COZE_BOT_ID="your_bot_id"')
        logger.warning('    $env:COZE_ACCESS_TOKEN="your_token"')
        logger.warning("")
        logger.warning("方式二：直接修改 config.py 文件")
        logger.warning("=" * 60)
        return False
    return True


def check_dependencies():
    missing = []
    try:
        import websocket
    except ImportError:
        missing.append("websocket-client")
    try:
        import pyaudio
    except ImportError:
        missing.append("pyaudio")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    try:
        import PIL
    except ImportError:
        missing.append("Pillow")

    if missing:
        logger.error("缺少以下依赖: %s", ", ".join(missing))
        logger.error("请运行: pip install -r requirements.txt")
        return False
    return True


def main():
    if not check_dependencies():
        sys.exit(1)

    check_config()

    from gui import CozeVoiceDemo

    root = tk.Tk()
    app = CozeVoiceDemo(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_close()


if __name__ == "__main__":
    main()