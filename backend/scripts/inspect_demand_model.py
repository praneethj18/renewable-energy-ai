from pathlib import Path

import joblib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "demand_forecast_model.joblib"


def main():
    print("Inspecting demand forecasting model...")

    if not MODEL_PATH.exists():
        print(f"Model not found: {MODEL_PATH}")
        return

    artifact = joblib.load(MODEL_PATH)

    print("\nModel path:", MODEL_PATH)
    print("Artifact type:", type(artifact).__name__)

    if isinstance(artifact, dict):
        print("\nAvailable artifact fields:")

        for key, value in artifact.items():
            if key == "model":
                print("model:", type(value).__name__)
            else:
                print(f"{key}: {value}")
    else:
        print("\nThe saved artifact is a model object.")
        print("Model type:", type(artifact).__name__)


if __name__ == "__main__":
    main()