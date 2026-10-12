from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.forecasting import train_forecasting_model


def main():
    results = {}

    for target in ("solar", "wind"):
        print(f"\nTraining {target} generation model...")

        result = train_forecasting_model(target)
        results[target] = result

        print(json.dumps(result, indent=2))

    output_path = PROJECT_ROOT / "models" / "training_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print(f"\nTraining report saved to: {output_path}")


if __name__ == "__main__":
    main()