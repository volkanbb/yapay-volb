"""Risk classification and approval policy.

VOLB never executes free-form commands. Every capability is a registered action with a
pydantic parameter schema and a fixed risk level. Anything above SAFE needs explicit approval.
"""
from __future__ import annotations

from enum import IntEnum
from pathlib import Path


class Risk(IntEnum):
    SAFE = 0          # read-only / opening allowlisted apps & sites
    SENSITIVE = 1     # reads private data or captures the screen
    EXTERNAL = 2      # externally visible (sending, posting, uploading)
    DESTRUCTIVE = 3   # deletes / overwrites data
    ADMIN = 4         # system-level changes, sudo
    FINANCIAL = 5     # money

    @property
    def label(self) -> str:
        return {
            Risk.SAFE: "güvenli", Risk.SENSITIVE: "hassas", Risk.EXTERNAL: "dışa açık",
            Risk.DESTRUCTIVE: "yıkıcı", Risk.ADMIN: "yönetici", Risk.FINANCIAL: "finansal",
        }[self]


# Categories that VOLB never performs, even with approval.
FORBIDDEN_RISKS = {Risk.ADMIN, Risk.FINANCIAL}


def requires_approval(risk: Risk) -> bool:
    return risk >= Risk.SENSITIVE


def is_forbidden(risk: Risk) -> bool:
    return risk in FORBIDDEN_RISKS


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


SENSITIVE_PATH_PARTS = {".ssh", ".gnupg", ".password-store", "keyrings", ".mozilla", ".config/chromium",
                        ".aws", ".kube", ".docker", ".netrc"}


def is_sensitive_path(path: Path) -> bool:
    text = str(path.resolve())
    return any(f"/{part}" in text for part in SENSITIVE_PATH_PARTS) or path.name.startswith(".env")
