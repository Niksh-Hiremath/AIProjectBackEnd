from fastapi import APIRouter, Header, HTTPException
from typing import Annotated
from dotenv import load_dotenv
import os
from uuid import uuid4
from pydantic import BaseModel, Field
from pathlib import Path
import base64
import numpy as np
import cv2
import os
from pymongo import MongoClient

from ai import process_image

load_dotenv()

AUTHORIZATION_KEY = os.getenv("AUTHORIZATION_KEY")

UPLOAD_DIR = Path("./uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter()
mongo = MongoClient(os.getenv("MONGO"))
db = mongo.data.results

sessions = {}


@router.put("/start", description="Starts processor")
async def start(
    authorization: Annotated[str, Header(alias="Authorization")],
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")

    session_id = str(uuid4())
    sessions[session_id] = {"io": [], "emo": {}}
    return {"SessionId": session_id}


@router.delete("/stop", description="Stops processor and returns the result")
async def stop(
    authorization: Annotated[str, Header(alias="Authorization")],
    session_id: Annotated[str, Header(alias="SessionId")],
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")
    if session_id not in sessions:
        return HTTPException(status_code=404, detail="Session not found")

    results = sessions[session_id]
    del sessions[session_id]

    if not results:
        raise HTTPException(status_code=400, detail="No results found")

    del results["emo"]["neutral"]
    emotion, confidence = max(results["emo"].items(), key=lambda x: x[1])

    db.insert_one(
        {
            "session_id": session_id,
            "emotion": emotion,
            "confidence": confidence,
            "io": results["io"],
        }
    )

    return {
        "emotion": emotion,
        "confidence": confidence,
    }


class ProcessImageRequest(BaseModel):
    imageData: str = Field(
        ...,
        description="Base64 encoded image with data URI prefix",
        min_length=1,
    )


@router.post("/process", description="Processes the image and saves the result")
async def process(
    authorization: Annotated[str, Header(alias="Authorization")],
    session_id: Annotated[str, Header(alias="SessionId")],
    request: ProcessImageRequest,
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")
    if session_id not in sessions:
        return HTTPException(status_code=404, detail="Session not found")

    image_data = request.imageData

    if not image_data.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid image data format")

    header, base64_str = image_data.split(",", 1)
    image_bytes = base64.b64decode(base64_str)

    nparr = np.frombuffer(image_bytes, np.uint8)
    im = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if im is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    file_extension = header.split(";")[0].split("/")[1]
    filename = f"{session_id}-{uuid4()}.{file_extension}"
    file_path = UPLOAD_DIR / filename

    cv2.imwrite(str(file_path), im)

    result = process_image(file_path)

    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass

    sessions[session_id]["io"].append(image_data)

    for emotion, confidence in result.items():
        if emotion not in sessions[session_id]["emo"]:
            sessions[session_id]["emo"][emotion] = float(confidence)
        else:
            sessions[session_id]["emo"][emotion] = max(
                sessions[session_id]["emo"][emotion], float(confidence)
            )

    return result
