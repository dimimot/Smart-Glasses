from __future__ import annotations

import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from v2.app.receivers.gateway_server import run_server


def main():
    print("=" * 50)
    print("Smart Glasses V2 - Starting")
    print("=" * 50)
    try:
        run_server(host="0.0.0.0", port=5050, ssl=False)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"\nCritical error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Shutdown complete.")


if __name__ == "__main__":
    main()
