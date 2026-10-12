from backend.app.services.forecasting import train_forecasting_model


def main():
    for target in ["solar", "wind"]:
        print(f"\nTraining {target.upper()} forecasting model...")

        result = train_forecasting_model(target)

        print(f"Target: {result['target']}")
        print(f"Training records: {result['training_records']}")
        print(f"Testing records: {result['testing_records']}")
        print(f"MAE: {result['mae_mw']} MW")
        print(f"RMSE: {result['rmse_mw']} MW")
        print(f"Model saved at: {result['model_path']}")

    print("\nSUCCESS: Both forecasting models trained successfully.")


if __name__ == "__main__":
    main()