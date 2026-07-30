import json
import os
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path.home() / ".locallm" / "sessions"

def _ensure_dir():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

def generate_session_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    import uuid
    suffix = uuid.uuid4().hex[:4]
    return f"{timestamp}-{suffix}"

def save_session(session_id: str, model: str, messages: list) -> None:
    _ensure_dir()
    path = SESSIONS_DIR / f"{session_id}.json"
    
    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except Exception:
            pass

    data = {
        "session_id": session_id,
        "created_at": existing.get("created_at", datetime.now(timezone.utc).isoformat()),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "messages": messages,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def load_session(session_id: str) -> dict | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None

def list_sessions() -> list[dict]:
    _ensure_dir()
    sessions = []
    for path in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text())
            sessions.append({
                "session_id": data.get("session_id"),
                "created_at": data.get("created_at"),
                "last_updated": data.get("last_updated"),
                "model": data.get("model"),
                "turns": len([m for m in data.get("messages", []) if m["role"] == "user"]),
            })
        except Exception:
            continue
    return sessions

def delete_session(session_id: str) -> bool:
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
