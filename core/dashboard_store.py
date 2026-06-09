"""Save and load named dashboard configurations to/from disk."""
import json
import os
from datetime import datetime
from typing import Optional

SAVED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_dashboards')


def _ensure_dir():
    os.makedirs(SAVED_DIR, exist_ok=True)


def save(name: str, kpi_selections: list, filter_selections: list,
         confirmed_dtypes: dict, ai_suggestions: dict = None) -> str:
    """Save dashboard config under `name`. Returns the file path."""
    _ensure_dir()
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip()
    if not safe_name:
        safe_name = "dashboard"
    filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = os.path.join(SAVED_DIR, filename)
    payload = {
        'name': name,
        'saved_at': datetime.now().isoformat(),
        'kpi_selections': kpi_selections or [],
        'filter_selections': filter_selections or [],
        'confirmed_dtypes': confirmed_dtypes or {},
        'ai_suggestions': ai_suggestions or {},
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, default=str)
    return path


def list_saved() -> list:
    """Return list of saved dashboards sorted newest first."""
    _ensure_dir()
    result = []
    for fname in os.listdir(SAVED_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(SAVED_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result.append({
                'filename': fname,
                'path': path,
                'name': data.get('name', fname),
                'saved_at': data.get('saved_at', ''),
            })
        except Exception:
            pass
    return sorted(result, key=lambda x: x['saved_at'], reverse=True)


def load(path: str) -> Optional[dict]:
    """Load a saved dashboard config. Returns None on error."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] load dashboard '{path}': {e}")
        return None


def delete(path: str) -> bool:
    """Delete a saved dashboard file."""
    try:
        os.remove(path)
        return True
    except Exception:
        return False
