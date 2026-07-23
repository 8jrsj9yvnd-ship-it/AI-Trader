import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone

GIST_ID = "4518b5abd44289f1104c63aac5e5d0ee"
GH_EXE = r"C:\Program Files\GitHub CLI\gh.exe"


def write_heartbeat(engine_alive, discord_alive):
    """Push a live status snapshot to the shared GitHub Gist so the
    Streamlit Cloud dashboard (which has no access to local lock files)
    can show real engine/bot status instead of always reporting offline."""

    payload = {
        "engine_alive": engine_alive,
        "discord_alive": discord_alive,
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        temp_path = f.name

    try:
        subprocess.run(
            [GH_EXE, "gist", "edit", GIST_ID, "--filename", "status.json", temp_path],
            capture_output=True,
            timeout=15,
        )
    except Exception as e:
        print(f"[heartbeat] failed to publish: {e}")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
