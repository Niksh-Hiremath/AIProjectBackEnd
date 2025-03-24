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
import shutil

import subprocess
import pandas as pd

from deepface import DeepFace


load_dotenv()


AUTHORIZATION_KEY = os.getenv("AUTHORIZATION_KEY")

UPLOAD_DIR = Path("./uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

# Path to OpenFace FeatureExtraction executable
OPENFACE_EXECUTABLE = os.getenv("OPENFACE_EXECUTABLE")

# Create output directory for OpenFace
OPENFACE_OUTPUT_DIR = Path("./openface_output")
OPENFACE_OUTPUT_DIR.mkdir(exist_ok=True)

router = APIRouter()

mongo = MongoClient(os.getenv("MONGO"))
db = mongo.data.results

sessions = {}


def process_image_deepface(img_path: str):
    result = DeepFace.analyze(img_path=img_path, actions=["emotion"])
    return result[0]["emotion"]


def process_image_facs(img_path: str):
    """
    Process an image using OpenFace to extract FACS Action Units
    """
    if not OPENFACE_EXECUTABLE or not Path(OPENFACE_EXECUTABLE).exists():
        print(f"OpenFace executable not found at: {OPENFACE_EXECUTABLE}")
        return {"error": "OpenFace executable not configured correctly"}

    base_filename = Path(img_path).stem
    os.mkdir(OPENFACE_OUTPUT_DIR / base_filename)
    output_file = (OPENFACE_OUTPUT_DIR / base_filename) / f"{base_filename}.csv"

    # Execute OpenFace
    command = [
        OPENFACE_EXECUTABLE,
        "-f",
        img_path,
        "-out_dir",
        str(OPENFACE_OUTPUT_DIR / base_filename),
        "-au_static",
        "true",
    ]

    try:
        result = subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Read the output CSV file
        if output_file.exists():
            df = pd.read_csv(str(output_file))

            # Extract AU intensity values (AU*_r columns)
            au_columns = [
                col for col in df.columns if col.startswith("AU") and col.endswith("_r")
            ]
            au_values = {
                col.split("_")[0]: float(df[col].iloc[0])
                for col in au_columns
                if not pd.isna(df[col].iloc[0])
            }

            emotion = map_aus_to_emotion(au_values)
            
            try:
                shutil.rmtree(str(OPENFACE_OUTPUT_DIR / base_filename), ignore_errors=True)
            except Exception as e:
                pass

            return {
                "action_units": au_values,
                "emotion": emotion,
                "confidence": max(au_values.values()) if au_values else 0.0,
            }
        else:
            return {"error": "OpenFace processing failed - no output file"}
    except Exception as e:
        return {"error": f"OpenFace processing failed: {str(e)}"}


def map_aus_to_emotion(aus):
    """
    Map Action Units to basic emotions based on FACS coding
    """
    emotions = {
        "happy": 0.0,
        "sad": 0.0,
        "angry": 0.0,
        "fear": 0.0,
        "disgust": 0.0,
        "surprise": 0.0,
        "contempt": 0.0,
    }

    # Happiness: AU6 (cheek raiser) + AU12 (lip corner puller)
    if "AU06" in aus and "AU12" in aus:
        emotions["happy"] = (aus["AU06"] + aus["AU12"]) / 2

    # Sadness: AU1 (inner brow raiser) + AU4 (brow lowerer) + AU15 (lip corner depressor)
    if "AU01" in aus and "AU04" in aus and "AU15" in aus:
        emotions["sad"] = (aus["AU01"] + aus["AU04"] + aus["AU15"]) / 3

    # Anger: AU4 (brow lowerer) + AU5 (upper lid raiser) + AU7 (lid tightener) + AU23 (lip tightener)
    if "AU04" in aus and "AU07" in aus:
        anger_score = 0
        count = 0
        if "AU04" in aus:
            anger_score += aus["AU04"]
            count += 1
        if "AU05" in aus:
            anger_score += aus["AU05"]
            count += 1
        if "AU07" in aus:
            anger_score += aus["AU07"]
            count += 1
        if "AU23" in aus:
            anger_score += aus["AU23"]
            count += 1

        if count > 0:
            emotions["angry"] = anger_score / count

    # Fear: AU1 + AU2 + AU4 + AU5 + AU20 + AU26
    if "AU01" in aus and "AU02" in aus and "AU04" in aus:
        fear_score = 0
        count = 0
        for au in ["AU01", "AU02", "AU04", "AU05", "AU20", "AU26"]:
            if au in aus:
                fear_score += aus[au]
                count += 1

        if count > 0:
            emotions["fear"] = fear_score / count

    # Disgust: AU9 (nose wrinkler) + AU15 + AU17
    if "AU09" in aus:
        disgust_score = aus["AU09"]
        count = 1
        if "AU15" in aus:
            disgust_score += aus["AU15"]
            count += 1
        if "AU17" in aus:
            disgust_score += aus["AU17"]
            count += 1

        emotions["disgust"] = disgust_score / count

    # Surprise: AU1 + AU2 + AU5 + AU26
    if "AU01" in aus and "AU02" in aus:
        surprise_score = 0
        count = 0
        for au in ["AU01", "AU02", "AU05", "AU26"]:
            if au in aus:
                surprise_score += aus[au]
                count += 1

        if count > 0:
            emotions["surprise"] = surprise_score / count

    # Contempt: AU14 (dimpler)
    if "AU14" in aus:
        emotions["contempt"] = aus["AU14"]

    print(emotions, aus)

    # Find the emotion with the highest score
    if any(emotions.values()):
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])
        return dominant_emotion[0]
    else:
        return "neutral"


@router.put("/start", description="Starts processor")
async def start(
    authorization: Annotated[str, Header(alias="Authorization")],
):
    if authorization != AUTHORIZATION_KEY:
        return HTTPException(status_code=401, detail="Unauthorized")

    session_id = str(uuid4())
    sessions[session_id] = {
        "io": [],
        "emo": {},
        "facs": {"action_units": {}, "emotions": {}},
    }

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

    if not results:
        raise HTTPException(status_code=400, detail="No results found")

    # Process emotion results from deepface
    if "neutral" in results["emo"]:
        del results["emo"]["neutral"]

    emotion, confidence = (
        max(results["emo"].items(), key=lambda x: x[1])
        if results["emo"]
        else ("unknown", 0.0)
    )

    # Get FACS results if available
    facs_emotion = None
    facs_confidence = 0.0

    if results["facs"]["emotions"]:
        facs_emotion, facs_confidence = max(
            results["facs"]["emotions"].items(), key=lambda x: x[1]
        )

    # Store results in database
    db.insert_one(
        {
            "session_id": session_id,
            "emotion": emotion,
            "confidence": confidence,
            "facs_emotion": facs_emotion,
            "facs_confidence": facs_confidence,
            # "io": results["io"],
        }
    )

    return_dict = {
        "emotion": emotion,
        "confidence": confidence,
        "facs_emotion": facs_emotion,
        "facs_confidence": facs_confidence,
    }

    print(return_dict)
    return return_dict


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

    # Process with DeepFace for emotion detection
    emotion_result = process_image_deepface(str(file_path))

    # Process with OpenFace for FACS analysis
    facs_result = process_image_facs(str(file_path))

    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass

    # Store image data
    sessions[session_id]["io"].append(image_data)

    # Store emotion results from DeepFace and convert numpy values to Python float
    emotion_result = {k: float(v) for k, v in emotion_result.items()}
    for emotion, confidence in emotion_result.items():
        if emotion not in sessions[session_id]["emo"]:
            sessions[session_id]["emo"][emotion] = confidence
        else:
            sessions[session_id]["emo"][emotion] = max(
                sessions[session_id]["emo"][emotion], confidence
            )

    # Store FACS results
    if "action_units" in facs_result:
        for au, value in facs_result["action_units"].items():
            if au not in sessions[session_id]["facs"]["action_units"]:
                sessions[session_id]["facs"]["action_units"][au] = float(value)
            else:
                sessions[session_id]["facs"]["action_units"][au] = max(
                    sessions[session_id]["facs"]["action_units"][au], float(value)
                )

    if "emotion" in facs_result and facs_result["emotion"] is not None:
        emotion = facs_result["emotion"]
        confidence = facs_result["confidence"]

        if emotion not in sessions[session_id]["facs"]["emotions"]:
            sessions[session_id]["facs"]["emotions"][emotion] = float(confidence)
        else:
            sessions[session_id]["facs"]["emotions"][emotion] = max(
                sessions[session_id]["facs"]["emotions"][emotion], float(confidence)
            )

    facs_aus = facs_result.get("action_units", {})
    facs_aus = {k: float(v) for k, v in facs_aus.items()}
    
    return_dict = {
        "emotion": emotion_result,
        "facs": {
            "action_units": facs_aus,
            "emotion": facs_result.get("emotion", "unknown"),
            "confidence": float(facs_result.get("confidence", 0.0)),
        },
    }

    print(return_dict)
    return return_dict
