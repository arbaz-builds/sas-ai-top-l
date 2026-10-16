import base64, io
from PIL import Image


def image_data(data):
   image = Image.open(data).convert("RGB")
   buf = io.BytesIO()
   image.save(buf, format="JPEG")
   data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
   return data_url


MAX_SIDE = 1568
MAX_BYTES = 120000   # hosted NVIDIA endpoints limit inline base64 images (~180 KB)
MIN_SIDE = 120       # skip logos / icons smaller than this


def shrink_jpeg(raw, min_side=MIN_SIDE):
    """Any image bytes -> RGB JPEG bytes that fit the API size limit. None if unreadable or too small."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        return None
    if min(img.size) < min_side:
        return None
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, "white")
        bg.paste(rgba, mask=rgba.split()[3])
        img = bg
    else:
        img = img.convert("RGB")
    if max(img.size) > MAX_SIDE:
        s = MAX_SIDE / max(img.size)
        img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
    quality = 85
    while True:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= MAX_BYTES or min(img.size) <= 64:
            return buf.getvalue()
        if quality > 55:
            quality -= 10
        else:
            img = img.resize((int(img.width * 0.85), int(img.height * 0.85)), Image.LANCZOS)


def to_data_url(jpeg):
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
