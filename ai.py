from deepface import DeepFace


def process_image(img_path: str):
    result = DeepFace.analyze(img_path=img_path, actions=["emotion"])
    return result[0]["emotion"]
