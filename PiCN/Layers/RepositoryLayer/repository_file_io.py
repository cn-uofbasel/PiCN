"""Pure helpers for file-backed repository reads (async executor dispatch)."""

import os.path
from typing import Optional

from PiCN.Packets import Content, Name


def read_file_system_repository_content(
    foldername: str,
    safepath: str,
    prefix_string: str,
    icnname: Name,
) -> Optional[Content]:
    """Read content from a filesystem repo layout (no layer/repo instance)."""
    if not icnname.components_to_string().startswith(prefix_string):
        return None
    try:
        filename = icnname.string_components[-1]
        filename_abs = foldername + "/" + filename
        filepath = os.path.abspath(filename_abs)
        if os.path.commonprefix([filepath, safepath]) != safepath:
            return None
        with open(filename_abs, "r") as content_file:
            payload = content_file.read()
        return Content(icnname, payload)
    except OSError:
        return None
