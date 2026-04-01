from fastapi import HTTPException, status

from app.core.security import create_access_token, verify_password
from app.core.storage import get_admin_accounts, get_client_accounts


def _find_account(accounts: list[dict[str, str]], username: str) -> dict[str, str] | None:
    for account in accounts:
        if account.get("username") == username:
            return account
    return None


def _authenticate(accounts: list[dict[str, str]], username: str, password: str) -> dict[str, str]:
    account = _find_account(accounts, username)
    if not account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    stored_password = str(account.get("password", ""))
    if not verify_password(password, stored_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return account


def login_admin(username: str, password: str) -> dict[str, str]:
    account = _authenticate(get_admin_accounts(), username, password)
    token = create_access_token(username=str(account["username"]), role="admin")

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "admin",
        "username": str(account["username"]),
        "display_name": str(account.get("display_name") or account["username"]),
    }


def login_client(username: str, password: str) -> dict[str, str]:
    account = _authenticate(get_client_accounts(), username, password)
    token = create_access_token(username=str(account["username"]), role="client")

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "client",
        "username": str(account["username"]),
        "display_name": str(account.get("display_name") or account["username"]),
    }
