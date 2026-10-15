import base64, io
from PIL import Image


def image_data(data):
   image = Image.open(data).convert("RGB")
   buf = io.BytesIO()
   image.save(buf, format="JPEG")
   data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
   return data_url
