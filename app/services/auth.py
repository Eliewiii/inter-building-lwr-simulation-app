"""Secured authentication mechanics providing identity verification for application endpoints."""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract, decode, and validate the user identity from an active HTTP Bearer token.

    Decodes an incoming JSON Web Token utilizing the configured cryptographic
    signature validation constraints, verifies payload structure completeness, and Isolates
    malformed authentication states by enforcing immediate unauthorized exceptions.

    Args:
        credentials (HTTPAuthorizationCredentials): Cryptographic token payload
            extracted from the incoming HTTP Authorization header. Defaults to Depends(security).

    Raises:
        HTTPException: Raised with status 401 if the token signature is missing the
            sub identification claim.
        HTTPException: Raised with status 401 if the cryptographic token payload signature
            evaluation fails against the signature key.

    Returns:
        str: The fully verified unique user identifier mapped from the token payload.
    """
    token = credentials.credentials
    try:
        # 1. Parse token parameters using central settings definitions
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")

        # 2. Defense by Construction: Guard parameter extraction
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
        )
