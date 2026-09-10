import os
import json
from typing import Dict, Any

from .sdr_service import STATE_DIR


PRESETS_PATH = os.path.join(STATE_DIR, 'presets.json')


def read_presets() -> Dict[str, Any]:
    try:
        if os.path.exists(PRESETS_PATH):
            with open(PRESETS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    # default structure
    return {'sdr1': [], 'sdr2': []}


def write_presets(data: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(PRESETS_PATH), exist_ok=True)
        with open(PRESETS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False
