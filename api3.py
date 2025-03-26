from fastapi import APIRouter, Request
import os
from fastapi.templating import Jinja2Templates
import random


router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


TEXTS = {
    0: "Welcome to your record!",
    1: "Thank you for visiting this page.",
    2: "Here's some random text for you.",
    3: "Have a wonderful day!",
    4: "This is a randomly selected message.",
}


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/record")
async def get_record(request: Request, name: str):
    random_key = random.choice(list(TEXTS.keys()))
    random_text = TEXTS[random_key]
    return templates.TemplateResponse(
        "record.html",
        {"request": request, "name": name, "text": random_text, "key": random_key},
    )
