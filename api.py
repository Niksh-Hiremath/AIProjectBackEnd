from fastapi import APIRouter, Header, HTTPException, Body
from typing import Annotated
from dotenv import load_dotenv
import os
from uuid import uuid4
from collections import defaultdict
from pathlib import Path
import base64
import numpy as np
import cv2

from ai import process_image

load_dotenv()

AUTHORIZATION_KEY = os.getenv("AUTHORIZATION_KEY")

UPLOAD_DIR = Path("./uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter()

sessions: dict[str, dict[str, int]] = {}


@router.put("/start", description="Starts processor")
async def start(
    authorization: Annotated[str, Header("Authorization")],
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")

    session_id = str(uuid4())
    sessions[session_id] = defaultdict(int)
    return {"session_id": session_id}


@router.delete("/stop", description="Stops processor and returns the result")
async def stop(
    authorization: Annotated[str, Header("Authorization")],
    session_id: Annotated[str, Header("SessionId")],
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")
    if session_id not in sessions:
        return HTTPException(status_code=404, detail="Session not found")

    results = sessions[session_id]
    del sessions[session_id]

    emotion: str = max(results, key=results.get)

    return {
        "emotion": emotion,
        "confidence": results[emotion] / sum(results.values()),
    }


@router.post("/process", description="Processes the image and saves the result")
async def process(
    authorization: Annotated[str, Header(alias="Authorization")],
    session_id: Annotated[str, Header(alias="SessionId")],
    image_data: Annotated[str, Body(alias="imageData")],
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")
    if session_id not in sessions:
        return HTTPException(status_code=404, detail="Session not found")

    if not image_data.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid image data format")

    header, base64_str = image_data.split(",", 1)
    image_bytes = base64.b64decode(base64_str)

    # file_extension = header.split(";")[0].split("/")[1]
    # filename = f"{session_id}-{uuid4()}.{file_extension}"
    # file_path = UPLOAD_DIR / filename

    # with open(file_path, "wb") as f:
    #     f.write(image_bytes)

    nparr = np.frombuffer(image_bytes, np.uint8)
    im = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if im is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    emotion = process_image(im)

    if emotion is None:
        raise HTTPException(
            status_code=400, detail="No face detected or could not process image"
        )

    sessions[session_id][emotion] += 1

    return {"emotion": emotion}
