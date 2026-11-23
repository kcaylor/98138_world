"""OAuth 1.0 request signing with HMAC-SHA1 (RFC 5849), standard library only (feature 011, R2).

Pure functions: the caller supplies the nonce and the timestamp (Unix seconds of the wall clock,
never a monotonic pacing clock). The header carries the consumer key and token value (public
identifiers in OAuth 1.0) and the signature; the two secrets only key the HMAC. Nothing here
logs or stores anything.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, quote, urlsplit

Params = Sequence[Tuple[str, str]]
SIGNATURE_METHOD = "HMAC-SHA1"
_DEFAULT_PORTS = {"http": 80, "https": 443}


def percent_encode(value: str) -> str:
    """RFC 5849 §3.6: UTF-8, then every byte outside ``A-Za-z0-9-._~`` as ``%XX`` (uppercase)."""
    return quote(str(value).encode("utf-8"), safe="-._~")


def base_string_uri(url: str) -> str:
    """§3.4.1.2: scheme and host lowercased, default port dropped, path kept, no query."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host if port is None or port == _DEFAULT_PORTS.get(scheme) else f"{host}:{port}"
    return f"{scheme}://{netloc}{parts.path or '/'}"


def normalize_parameters(params: Iterable[Tuple[str, str]]) -> str:
    """§3.4.1.3.2: encode names and values, sort by name then value, join with ``=`` and ``&``."""
    pairs = sorted((percent_encode(k), percent_encode(v)) for k, v in params if k != "oauth_signature")
    return "&".join(f"{k}={v}" for k, v in pairs)


def base_string(method: str, url: str, params: Params) -> str:
    """§3.4.1: ``METHOD&enc(base URI)&enc(normalized parameters)``.

    ``params`` are decoded name/value pairs (request body and ``oauth_*`` protocol parameters,
    and any query parameters not already in ``url``); a query in ``url`` is included as well.
    """
    query = urlsplit(url).query
    all_params: List[Tuple[str, str]] = parse_qsl(query, keep_blank_values=True) if query else []
    all_params += list(params)
    return "&".join((method.upper(), percent_encode(base_string_uri(url)),
                     percent_encode(normalize_parameters(all_params))))


def hmac_sha1_signature(base: str, consumer_secret: str, token_secret: str) -> str:
    """§3.4.2: key ``enc(consumer secret)&enc(token secret)``; base64 of the HMAC-SHA1 digest."""
    key = f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}".encode("ascii")
    digest = hmac.new(key, base.encode("ascii"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def oauth_parameters(credentials, *, nonce: str, timestamp: int,
                     version: Optional[str] = "1.0") -> List[Tuple[str, str]]:
    """The protocol parameters, without the signature, in header order."""
    if isinstance(timestamp, bool) or not isinstance(timestamp, int):
        raise TypeError("timestamp must be integer Unix seconds")
    out = [("oauth_consumer_key", credentials.consumer_key), ("oauth_token", credentials.token_value),
           ("oauth_signature_method", SIGNATURE_METHOD), ("oauth_timestamp", str(timestamp)),
           ("oauth_nonce", str(nonce))]
    if version is not None:
        out.append(("oauth_version", version))
    return out


def signed_parameters(method: str, url: str, query: Params, credentials, *, nonce: str,
                      timestamp: int, version: Optional[str] = "1.0") -> List[Tuple[str, str]]:
    """Protocol parameters plus ``oauth_signature`` for a request with these query parameters."""
    oauth = oauth_parameters(credentials, nonce=nonce, timestamp=timestamp, version=version)
    base = base_string(method, url, list(query) + oauth)
    return oauth + [("oauth_signature",
                     hmac_sha1_signature(base, credentials.consumer_secret, credentials.token_secret))]


def authorization_header(method: str, url: str, query: Params, credentials, *, nonce: str,
                         timestamp: int, realm: str = "", version: Optional[str] = "1.0") -> str:
    """§3.5.1 ``Authorization`` header value: ``OAuth realm="", oauth_consumer_key="…", …``."""
    params = signed_parameters(method, url, query, credentials, nonce=nonce, timestamp=timestamp,
                               version=version)
    fields = [f'realm="{realm}"'] + [f'{k}="{percent_encode(v)}"' for k, v in params]
    return "OAuth " + ", ".join(fields)


__all__ = ["percent_encode", "base_string_uri", "normalize_parameters", "base_string",
           "hmac_sha1_signature", "oauth_parameters", "signed_parameters", "authorization_header"]
