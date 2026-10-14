"""Authentication endpoints: CSRF token, register, login, refresh, logout, password flows,
email verification and session management. Design: docs/architecture/AUTHENTICATION.md."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import (
    Auth,
    get_app_settings,
    get_auth,
    get_optional_auth,
    get_request_meta,
)
from app.core.config import Settings
from app.core.cookies import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    issue_csrf_cookie,
    set_auth_cookies,
)
from app.core.db import get_db
from app.core.errors import NotAuthenticated, NotFound, error_body
from app.core.middleware import CSRF_COOKIE
from app.core.rate_limit import rate_limit
from app.schemas.account import (
    ChangePasswordIn,
    ForgotPasswordIn,
    LoginIn,
    MeOut,
    RegisterIn,
    ResetPasswordIn,
    SessionOut,
    TokenIn,
)
from app.schemas.common import OkOut
from app.services import account, auth
from app.services import email as email_service
from app.services.auth import RequestMeta

router = APIRouter(prefix="/auth", tags=["auth"])


class CsrfOut(BaseModel):
    csrf_token: str


def send_emails_later(request: Request, tasks: BackgroundTasks) -> None:
    """Dispatch queued emails after the response (the periodic job retries failures)."""
    tasks.add_task(
        email_service.dispatch_pending,
        request.app.state.session_factory,
        request.app.state.settings,
    )


@router.get("/csrf", response_model=CsrfOut)
def get_csrf_token(
    request: Request, response: Response, settings: Settings = Depends(get_app_settings)
) -> CsrfOut:
    """Return the CSRF token, issuing a new cookie only if the browser doesn't have one yet."""
    existing = request.cookies.get(CSRF_COOKIE)
    token = existing if existing else issue_csrf_cookie(response, settings)
    response.headers["Cache-Control"] = "no-store"
    return CsrfOut(csrf_token=token)


@router.get("/me", response_model=MeOut)
def me(response: Response, current: Auth | None = Depends(get_optional_auth)) -> MeOut:
    response.headers["Cache-Control"] = "no-store"
    return MeOut(user=account.user_out(current.user) if current else None)


@router.post(
    "/register",
    response_model=MeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", limit=10, window_seconds=3600))],
)
def register(
    data: RegisterIn,
    request: Request,
    response: Response,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    meta: RequestMeta = Depends(get_request_meta),
) -> MeOut:
    user, issued = auth.register(
        db,
        settings,
        full_name=data.full_name,
        email=data.email,
        password=data.password,
        phone=data.phone,
        meta=meta,
    )
    db.commit()
    set_auth_cookies(
        response, settings, access_token=issued.access_token, refresh_token=issued.refresh_token
    )
    send_emails_later(request, tasks)
    return MeOut(user=account.user_out(user))


@router.post(
    "/login",
    response_model=MeOut,
    dependencies=[Depends(rate_limit("login-ip", limit=30, window_seconds=900))],
)
def login(
    data: LoginIn,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    meta: RequestMeta = Depends(get_request_meta),
) -> MeOut:
    user, issued = auth.login(db, settings, email=data.email, password=data.password, meta=meta)
    db.commit()
    set_auth_cookies(
        response, settings, access_token=issued.access_token, refresh_token=issued.refresh_token
    )
    return MeOut(user=account.user_out(user))


@router.post("/refresh", response_model=OkOut)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> OkOut | JSONResponse:
    token = request.cookies.get(REFRESH_COOKIE)
    try:
        if not token:
            raise NotAuthenticated()
        issued = auth.refresh_session(db, settings, token)
    except NotAuthenticated as exc:
        # Clear the dead cookies so the browser simply continues as a guest.
        failed = JSONResponse(error_body(exc.code, exc.message), status_code=exc.status_code)
        clear_auth_cookies(failed, settings)
        return failed
    db.commit()
    set_auth_cookies(
        response, settings, access_token=issued.access_token, refresh_token=issued.refresh_token
    )
    return OkOut()


@router.post("/logout", response_model=OkOut)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current: Auth | None = Depends(get_optional_auth),
) -> OkOut:
    if current is not None:
        auth.revoke_session(current.session, "logout")
        db.commit()
    clear_auth_cookies(response, settings)
    return OkOut(message="You have been signed out.")


@router.post("/logout-all", response_model=OkOut)
def logout_all(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current: Auth = Depends(get_auth),
) -> OkOut:
    auth.revoke_all_sessions(db, current.user.id, "logout_all")
    db.commit()
    clear_auth_cookies(response, settings)
    return OkOut(message="You have been signed out on all devices.")


@router.post(
    "/verify-email",
    response_model=OkOut,
    dependencies=[Depends(rate_limit("verify-email", limit=20, window_seconds=3600))],
)
def verify_email(data: TokenIn, db: Session = Depends(get_db)) -> OkOut:
    auth.verify_email(db, data.token)
    db.commit()
    return OkOut(message="Thank you — your email address is confirmed.")


@router.post(
    "/resend-verification",
    response_model=OkOut,
    dependencies=[Depends(rate_limit("resend-verification", limit=3, window_seconds=3600))],
)
def resend_verification(
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current: Auth = Depends(get_auth),
) -> OkOut:
    auth.send_verification_email(db, settings, current.user)
    db.commit()
    send_emails_later(request, tasks)
    return OkOut(message="If your email isn't confirmed yet, we've sent a new link.")


@router.post(
    "/forgot-password",
    response_model=OkOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("forgot-ip", limit=10, window_seconds=3600))],
)
def forgot_password(
    data: ForgotPasswordIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> OkOut:
    auth.request_password_reset(db, settings, data.email)
    db.commit()
    send_emails_later(request, tasks)
    # Identical response whether or not the account exists (no account enumeration).
    return OkOut(
        message="If an account exists for that email, we've sent a link to reset the password."
    )


@router.post(
    "/reset-password",
    response_model=OkOut,
    dependencies=[Depends(rate_limit("reset-ip", limit=20, window_seconds=3600))],
)
def reset_password(
    data: ResetPasswordIn,
    request: Request,
    response: Response,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> OkOut:
    auth.reset_password(db, settings, data.token, data.password)
    db.commit()
    clear_auth_cookies(response, settings)
    send_emails_later(request, tasks)
    return OkOut(message="Your password has been changed. Please sign in.")


@router.post(
    "/change-password",
    response_model=OkOut,
    dependencies=[Depends(rate_limit("change-password", limit=10, window_seconds=3600))],
)
def change_password(
    data: ChangePasswordIn,
    request: Request,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current: Auth = Depends(get_auth),
) -> OkOut:
    auth.change_password(
        db, settings, current.user, current.session.id, data.current_password, data.new_password
    )
    db.commit()
    send_emails_later(request, tasks)
    return OkOut(message="Password changed. Other devices have been signed out.")


@router.get("/sessions", response_model=list[SessionOut])
def sessions(db: Session = Depends(get_db), current: Auth = Depends(get_auth)) -> list[SessionOut]:
    return [
        account.session_out(s, current.session.id)
        for s in auth.active_sessions(db, current.user.id)
    ]


@router.delete("/sessions/{session_id}", response_model=OkOut)
def revoke_session(
    session_id: uuid.UUID, db: Session = Depends(get_db), current: Auth = Depends(get_auth)
) -> OkOut:
    target = next(
        (s for s in auth.active_sessions(db, current.user.id) if s.id == session_id), None
    )
    if target is None:
        raise NotFound("We couldn't find that session.")
    auth.revoke_session(target, "revoked_by_user")
    db.commit()
    return OkOut(message="That device has been signed out.")
