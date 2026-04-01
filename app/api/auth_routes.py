from fastapi import APIRouter

from app.schemas.auth import LoginRequest, LoginResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/admin/login", response_model=LoginResponse)
def admin_login(payload: LoginRequest):
    """Authenticate admin users from storage/admin.json."""
    return LoginResponse(**auth_service.login_admin(payload.username, payload.password))


@router.post("/client/login", response_model=LoginResponse)
def client_login(payload: LoginRequest):
    """Authenticate client users from storage/clients.json."""
    return LoginResponse(**auth_service.login_client(payload.username, payload.password))
