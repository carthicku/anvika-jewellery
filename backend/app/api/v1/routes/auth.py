"""Authentication routes. Phase 1 provides the CSRF token; sign-in flows arrive in Phase 4."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.core.cookies import issue_csrf_cookie
from app.core.middleware import CSRF_COOKIE

router = APIRouter(prefix="/auth", tags=["auth"])


class CsrfOut(BaseModel):
    csrf_token: str


@router.get("/csrf", response_model=CsrfOut)
def get_csrf_token(
    request: Request, response: Response, settings: Settings = Depends(get_app_settings)
) -> CsrfOut:
    """Return the CSRF token, issuing a new cookie only if the browser doesn't have one yet."""
    existing = request.cookies.get(CSRF_COOKIE)
    token = existing if existing else issue_csrf_cookie(response, settings)
    response.headers["Cache-Control"] = "no-store"
    return CsrfOut(csrf_token=token)
