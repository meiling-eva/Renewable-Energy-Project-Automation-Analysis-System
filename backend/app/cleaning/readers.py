import io
import json
from typing import List

import pandas as pd

SUPPORTED_EXTENSIONS = (".xlsx", ".xls", ".csv", ".json")


class UnsupportedFileError(ValueError):
    pass


def _json_to_frame(content: bytes) -> pd.DataFrame:
    data = json.loads(content.decode("utf-8-sig"))
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        # {"projects": [...]} style wrappers: use the first list found.
        data = lists[0] if lists else [data]
    if not isinstance(data, list):
        raise UnsupportedFileError("JSON must be an array of objects or an object containing one")
    return pd.json_normalize([row if isinstance(row, dict) else {"value": row} for row in data])


def read_table(filename: str, content: bytes) -> pd.DataFrame:
    """Reads an uploaded Excel/CSV/JSON file into one DataFrame (all Excel sheets are stacked)."""
    name = filename.lower()
    if not name.endswith(SUPPORTED_EXTENSIONS):
        raise UnsupportedFileError(
            f"Unsupported file type. Use one of: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    if name.endswith(".json"):
        return _json_to_frame(content)
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content), dtype=object, keep_default_na=False)

    sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, dtype=object)
    frames: List[pd.DataFrame] = [df for df in sheets.values() if not df.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)
