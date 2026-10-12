from fastapi import FastAPI
from PIL import Image




app = FastAPI()



image = Image.open("car_damage.jpg")
image.show()



