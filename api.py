from fastapi import APIRouter, Header, HTTPException
from typing import Annotated
from dotenv import load_dotenv
import os
from uuid import uuid4
from collections import defaultdict

from ai import process_image

load_dotenv()

AUTHORIZATION_KEY = os.getenv("AUTHORIZATION_KEY")

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
    authorization: Annotated[str, Header("Authorization")],
    session_id: Annotated[str, Header("SessionId")],
    image: str,
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")
    if session_id not in sessions:
        return HTTPException(status_code=404, detail="Session not found")

    emotion = process_image(image)
    sessions[session_id][emotion] += 1

    return {"emotion": emotion}
