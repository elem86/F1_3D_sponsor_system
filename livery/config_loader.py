from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_json(path: str | Path) -> Dict[str, Any]:
    """
    Load a JSON file and return it as a Python dictionary.

    Parameters
    ----------
    path : str | Path
        Path to the JSON file.

    Returns
    -------
    dict
        Parsed JSON content.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
