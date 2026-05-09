from fastapi import FastAPI
import joblib
import numpy as np
import os

app = FastAPI()

models = {}
model_folder = "models"

# Load all models from the specified folder
for file in os.listdir(model_folder):
    if file.endswith(".pkl"):
        key = file.replace(".pkl", "")
        key = file.replace(".pkl", "").lower().replace(" ", "_")
        for model_type in ["random_forest", "linear_regression", "gradient_boosting", "decision_tree"]:
            if key.endswith(model_type) and not key.endswith("_" + model_type):
                key = key[: -len(model_type)] + "_" + model_type
        models[key] = joblib.load(os.path.join(model_folder, file))

print("Loaded models:", models.keys())
print("Working directory:", os.getcwd())


@app.post("/predict")
def predict(data: dict):
    try:
        crop = data["crop"].lower()
        model_name = data["model"].lower().replace(" ", "_")

        features = np.array(data["features"]).reshape(1, -1)

        key = f"{crop}_{model_name}"

        print("KEY REQUESTED:", key)
        print("AVAILABLE:", models.keys())

        if key not in models:
            return {
                "error": f"Model {key} not found",
                "available": list(models.keys())
            }

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