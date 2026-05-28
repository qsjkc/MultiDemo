import base64
import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)


def image_to_base64(image_path, max_size=(1024, 1024), quality=85):
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode("ascii")


def build_image_message(image_path, prompt_text=""):
    b64_data = image_to_base64(image_path, max_size=(1280, 1280), quality=95)

    objects = []

    objects.append({
        "type": "image",
        "file_url": f"data:image/jpeg;base64,{b64_data}",
    })

    if prompt_text:
        objects.append({"type": "text", "text": prompt_text})
    else:
        objects.append({"type": "text", "text": "请详细描述这张图片中的内容。"})

    return objects


def build_file_message(file_url, prompt_text=""):
    objects = []

    if prompt_text:
        objects.append({"type": "text", "text": prompt_text})

    objects.append({"type": "file", "file_url": file_url})

    return objects


def pcm_to_numpy(pcm_bytes, dtype="int16"):
    import numpy as np
    return np.frombuffer(pcm_bytes, dtype=np.dtype(dtype))


def numpy_to_pcm(samples, dtype="int16"):
    import numpy as np
    return np.array(samples, dtype=np.dtype(dtype)).tobytes()