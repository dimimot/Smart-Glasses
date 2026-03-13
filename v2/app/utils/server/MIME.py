"""
MIME type validation utility for image uploads.
"""

from __future__ import annotations

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
ALLOWED_MIME_TYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/webp'}

def is_allowed_file(filename: str, mimetype: str | None = None) -> bool:
    """Check if the filename extension and mimetype are allowed."""
    ext_ok = '.' in filename and \
             filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    if mimetype:
        return ext_ok and mimetype in ALLOWED_MIME_TYPES
    return ext_ok
