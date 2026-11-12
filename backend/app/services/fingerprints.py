import hashlib
import re

_VOLATILE = re.compile(r"0x[0-9a-fA-F]+|\b[0-9a-f]{8}-[0-9a-f-]{27,}\b|\b\d+\b")


def fingerprint_for(project_id: str, exception_type: str, message: str, stacktrace: str = "") -> str:
    first_frame = ""
    for line in (stacktrace or "").splitlines():
        line = line.strip()
        if line and (" at " in line or line.startswith("File \"")):
            first_frame = line[:240]
            break
    normalized = _VOLATILE.sub("#", (message or "").lower()).strip()
    raw = "|".join((project_id, exception_type.lower().strip(), normalized, first_frame))
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()
