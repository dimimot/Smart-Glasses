"""
SSL helper αποκλειστικά για FastAPI/uvicorn (απλή μορφή).

Χρήση:
    uvicorn.run(app, host="0.0.0.0", port=5050, **get_ssl_args_for_uvicorn())

Λογική paths (σειρά προτεραιότητας):
1) Περιβαλλοντικές μεταβλητές: SSL_CERT_FILE, SSL_KEY_FILE
2) Fallback στον φάκελο DATA_DIR/certs/ (π.χ. cert.pem, key.pem)
"""

from __future__ import annotations

import os
from pathlib import Path

from v2.app.config import DATA_DIR

def _resolve_cert_paths(cert_file: str = "cert.pem", key_file: str = "key.pem") -> tuple[Path, Path]:
    """Επιστρέφει απόλυτα paths για cert/key.

    Προτεραιότητα:
    1) ENV: SSL_CERT_FILE / SSL_KEY_FILE
    2) DATA_DIR/certs/<cert|key>.pem
    """
    env_cert = os.environ.get("SSL_CERT_FILE")
    env_key = os.environ.get("SSL_KEY_FILE")

    if env_cert and env_key:
        return Path(env_cert), Path(env_key)

    certs_dir = Path(DATA_DIR) / "certs"
    cert_path = certs_dir / cert_file
    key_path = certs_dir / key_file
    return cert_path, key_path
def get_ssl_args_for_uvicorn(cert_file: str = "cert.pem", key_file: str = "key.pem") -> dict:
    """
    Επιστρέφει dict με `ssl_certfile` και `ssl_keyfile` για uvicorn.
    Αν κάποιο από τα δύο δεν υπάρχει, επιστρέφει κενό dict (χωρίς SSL).

    Παράδειγμα:
        uvicorn.run(app, host="0.0.0.0", port=5050, **get_ssl_args_for_uvicorn())
    """
    cert_path, key_path = _resolve_cert_paths(cert_file, key_file)

    if cert_path.exists() and key_path.exists():
        return {"ssl_certfile": str(cert_path), "ssl_keyfile": str(key_path)}
    return {}
