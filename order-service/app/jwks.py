import base64
import os
import time

import httpx
from jose import JWTError, jwt

JWKS_URI = os.environ["JWKS_URI"]
_SSL_VERIFY = os.environ.get("IS_SSL_VERIFY", "true").lower() == "true"
_CACHE_TTL = 300.0

_jwks_cache: dict = {}
_jwks_cache_time: float = 0.0


async def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_cache_time
    now = time.monotonic()
    if _jwks_cache and (now - _jwks_cache_time) < _CACHE_TTL:
        return _jwks_cache
    async with httpx.AsyncClient(verify=_SSL_VERIFY) as client:
        resp = await client.get(JWKS_URI, timeout=5.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = now
    return _jwks_cache


async def get_claims_from_assertion(assertion_header: str) -> dict:
    # WSO2 APIM base64-encodes the JWT before injecting it as X-JWT-Assertion
    try:
        padding = "=" * (4 - len(assertion_header) % 4)
        token = base64.b64decode(assertion_header + padding).decode("utf-8")
    except Exception:
        token = assertion_header  # already a raw JWT string

    jwks = await _fetch_jwks()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise ValueError(f"Could not parse JWT header: {e}")

    kid = unverified_header.get("kid")
    key = _find_key(jwks, kid)
    if key is None:
        # Force refresh on kid mismatch (key rotation)
        global _jwks_cache_time
        _jwks_cache_time = 0.0
        jwks = await _fetch_jwks()
        key = _find_key(jwks, kid)
    if key is None:
        raise ValueError(f"No JWKS key found for kid={kid}")

    try:
        return jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})
    except JWTError as e:
        raise ValueError(f"JWT validation failed: {e}")


def _find_key(jwks: dict, kid: str | None):
    for key_data in jwks.get("keys", []):
        if kid is None or key_data.get("kid") == kid:
            return key_data
    return None
