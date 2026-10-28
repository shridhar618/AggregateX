from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..schemas import LoginRequest, RegisterRequest
from ..services import auth_service
from ..services.auth_service import SESSION_COOKIE, SESSION_DAYS

router = APIRouter(tags=["auth"])


def require_user(request: Request) -> dict:
    """Dependency for every route that reads or changes saved data."""
    user = auth_service.user_for_token(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="Log in to continue.")
    return user


AUTH = [Depends(require_user)]


def _start_session(response: Response, user: dict) -> dict:
    token = auth_service.create_session(user["id"])
    # HttpOnly: unreadable from page scripts. SameSite=Strict: never sent on cross-site requests.
    # Not marked Secure because the engine serves plain HTTP on 127.0.0.1.
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True,
                        samesite="strict", path="/")
    return {"user": user}


@router.post("/auth/register", status_code=201)
def register(req: RegisterRequest, response: Response):
    try:
        user = auth_service.register(req.name, req.email, req.password)
    except auth_service.EmailTaken as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return _start_session(response, user)


@router.post("/auth/login")
def login(req: LoginRequest, response: Response):
    try:
        user = auth_service.authenticate(req.email, req.password)
    except auth_service.TooManyAttempts as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": str(exc.retry_after)}) from None
    if user is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return _start_session(response, user)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    auth_service.delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    response.status_code = 204
    return None


@router.get("/auth/me")
def me(user: dict = Depends(require_user)):
    return {"user": user}
