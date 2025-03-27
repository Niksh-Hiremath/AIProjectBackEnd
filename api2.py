from fastapi import APIRouter, Header, HTTPException
from typing import Annotated
from dotenv import load_dotenv
import os
from uuid import uuid4
from pydantic import BaseModel, Field
from pymongo import MongoClient


load_dotenv()


AUTHORIZATION_KEY = os.getenv("AUTHORIZATION_KEY")

router = APIRouter()

mongo = MongoClient(os.getenv("MONGO"))
db = mongo.data.images
db2 = mongo.data.questions

sessions = {}


class StartRequest(BaseModel):
    name: str = Field(..., description="Name for the session")
    key: str = Field(..., description="Key for the text")


@router.put("/start", description="Starts processor")
async def start(
    authorization: Annotated[str, Header(alias="Authorization")],
    request: StartRequest,
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")

    session_id = str(uuid4())
    sessions[session_id] = {"count": 0, "name": request.name, "key": request.key}

    return_dict = {"SessionId": session_id}

    print(return_dict)
    return return_dict


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

    print(results)
    return 200


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

    sessions[session_id]["count"] += 1

    db.insert_one(
        {
            "session_id": session_id,
            "count": sessions[session_id]["count"],
            "name": sessions[session_id]["name"],
            "key": sessions[session_id]["key"],
            "image": image_data,
        }
    )

    return 200


class SubmissionRequest(BaseModel):
    name: str
    key: str
    answers: dict


@router.post("/submit")
async def submit_answers(
    authorization: Annotated[str, Header(alias="Authorization")],
    session_id: Annotated[str, Header(alias="SessionId")],
    request: SubmissionRequest,
):
    if authorization != AUTHORIZATION_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        submission_data = {
            "name": request.name,
            "session_id": session_id,
            "key": request.key,
            "answers": request.answers,
        }
        db2.insert_one(submission_data)
        return {"message": "Submission saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
