"""BrickLink API credentials, read only from environment variables (feature 011, FR-006, R8).

The four OAuth 1.0 values are never committed, logged, printed or written: ``repr`` and ``str``
are redacted, the object refuses to be pickled, and a missing variable is reported by name only.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Mapping, Optional, Tuple

ENV_VARS = ("BRICKLINK_CONSUMER_KEY", "BRICKLINK_CONSUMER_SECRET", "BRICKLINK_TOKEN_VALUE",
            "BRICKLINK_TOKEN_SECRET")
_FIELDS = ("consumer_key", "consumer_secret", "token_value", "token_secret")
REDACTED = "Credentials(<redacted>)"


class MissingCredentialsError(ValueError):
    """One or more ``BRICKLINK_*`` variables are missing or empty (exit 1, before any request)."""

    def __init__(self, names: Tuple[str, ...]):
        self.names = tuple(names)
        super().__init__(f"missing environment variable(s): {', '.join(self.names)}")


@dataclass(frozen=True, repr=False, eq=False)
class Credentials:
    consumer_key: str
    consumer_secret: str
    token_value: str
    token_secret: str

    def __post_init__(self) -> None:
        for f in fields(self):
            v = getattr(self, f.name)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"credential {f.name} must be a non-empty string")

    def __repr__(self) -> str:
        return REDACTED

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("Credentials are never serialized")


def credentials_from_env(env: Optional[Mapping[str, str]] = None) -> Credentials:
    """The four values from ``BRICKLINK_*``; ``MissingCredentialsError`` names any missing one."""
    env = os.environ if env is None else env
    values = {name: (env.get(name) or "").strip() for name in ENV_VARS}
    missing = tuple(name for name in ENV_VARS if not values[name])
    if missing:
        raise MissingCredentialsError(missing)
    return Credentials(**{f: values[n] for f, n in zip(_FIELDS, ENV_VARS)})


__all__ = ["ENV_VARS", "Credentials", "MissingCredentialsError", "credentials_from_env"]
