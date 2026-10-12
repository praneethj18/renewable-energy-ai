from pathlib import Path

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_dataset(file_path: str | Path) -> pd.DataFrame:
    """
    Load a CSV or Excel file into a Pandas DataFrame.

    Args:
        file_path: Path to the input dataset.

    Returns:
        A Pandas DataFrame containing the loaded data.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file format is unsupported or the file is empty.
        RuntimeError: If the file cannot be read.
    """

    path = Path(file_path)

    # Check whether the file exists.
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"The provided path is not a file: {path}"
        )

    # Check the file extension.
    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}. "
            "Supported formats are CSV, XLSX, and XLS."
        )

    try:
        # Load the file according to its format.
        if extension == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

    except pd.errors.EmptyDataError as exc:
        raise ValueError(
            f"The dataset is empty: {path}"
        ) from exc

    except (OSError, ValueError, ImportError) as exc:
        raise RuntimeError(
            f"Unable to read dataset: {path}. Reason: {exc}"
        ) from exc

    # Reject files that contain no records or no columns.
    if df.empty:
        raise ValueError(
            f"The dataset contains no records: {path}"
        )

    if len(df.columns) == 0:
        raise ValueError(
            f"The dataset contains no columns: {path}"
        )

    return df