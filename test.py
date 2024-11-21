from ai import DeepFace

file_path = "test.jpeg"
result = DeepFace.analyze(img_path=file_path, actions=["emotion"])
emotion = result[0]["emotion"]

print(emotion)