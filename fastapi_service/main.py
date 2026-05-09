from fastapi import FastAPI
import joblib
import numpy as np
import os

app = FastAPI()

models = {}

# -----------------------------
# Load models safely on startup
# -----------------------------
@app.on_event("startup")
def load_models():
    global models
    models = {}

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    model_folder = os.path.join(BASE_DIR, "models")

    if not os.path.exists(model_folder):
        print(f"Model folder not found: {model_folder}")
        return

    for file in os.listdir(model_folder):
        if file.endswith(".pkl"):
            try:
                key = file.replace(".pkl", "").lower().replace(" ", "_")
                path = os.path.join(model_folder, file)

                models[key] = joblib.load(path)

            except Exception as e:
                print(f"Failed to load {file}: {e}")

    print("Loaded models:", list(models.keys()))
    print("Working directory:", os.getcwd())


# -----------------------------
# Prediction endpoint
# -----------------------------
@app.post("/predict")
def predict(data: dict):
    try:
        # Validate input
        if "crop" not in data or "model" not in data or "features" not in data:
            return {"error": "Missing required fields: crop, model, features"}

        crop = data["crop"].lower().replace(" ", "_")
        model_name = data["model"].lower().replace(" ", "_")

        key = f"{crop}_{model_name}"

        print("REQUESTED KEY:", key)
        print("AVAILABLE MODELS:", list(models.keys()))

        # Check model existence
        if key not in models:
            return {
                "error": f"Model '{key}' not found",
                "available_models": list(models.keys())
            }

        # Prepare features
        features = np.array(data["features"]).reshape(1, -1)

        model = models[key]
        prediction = model.predict(features)

        return {
            "model_used": key,
            "prediction": float(prediction[0])
        }

    except Exception as e:
        return {
            "error": str(e)
        }