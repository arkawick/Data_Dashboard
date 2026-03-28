"""
dashboard/auth_views.py
=======================
JWT authentication for the Django dashboard REST API.

Uses PyJWT directly (no Django ORM / simplejwt dependency).
Credentials are stored in MongoDB 'users' collection with bcrypt hashing.

Endpoints (added in config/urls.py):
    POST /api/auth/login/     - returns access + refresh tokens
    POST /api/auth/refresh/   - returns new access token
    POST /api/auth/register/  - create a new user (admin only)
    GET  /api/auth/me/        - returns current user info

Initial setup:
    from dashboard.auth_views import create_user
    create_user("admin", "changeme", role="admin")
"""

import json
import os
from datetime import datetime, timezone, timedelta
from functools import wraps

import jwt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .mongo_utils import get_mongo_collection

# ── Config ────────────────────────────────────────────────────────────────────

JWT_SECRET    = os.environ.get("JWT_SECRET_KEY",          "dev-jwt-secret-replace-in-prod")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM",           "HS256")
ACCESS_HOURS  = int(os.environ.get("JWT_ACCESS_EXPIRE_HOURS",  "8"))
REFRESH_DAYS  = int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS",  "7"))


# ── Token helpers ─────────────────────────────────────────────────────────────

def _make_access_token(username: str, role: str) -> str:
    payload = {
        "sub":  username,
        "role": role,
        "type": "access",
        "exp":  datetime.now(tz=timezone.utc) + timedelta(hours=ACCESS_HOURS),
        "iat":  datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _make_refresh_token(username: str) -> str:
    payload = {
        "sub":  username,
        "type": "refresh",
        "exp":  datetime.now(tz=timezone.utc) + timedelta(days=REFRESH_DAYS),
        "iat":  datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ── Password helpers ──────────────────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    import bcrypt
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _check_password(plain: str, hashed: str) -> bool:
    import bcrypt
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Auth decorator ────────────────────────────────────────────────────────────

def jwt_required(func):
    """Decorator that enforces JWT authentication on a view."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Missing or invalid Authorization header"}, status=401)
        token = auth_header.split(" ", 1)[1]
        try:
            payload = _decode_token(token)
            if payload.get("type") != "access":
                raise ValueError("Not an access token")
            request.jwt_user = payload
        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token expired"}, status=401)
        except Exception:
            return JsonResponse({"error": "Invalid token"}, status=401)
        return func(request, *args, **kwargs)
    return wrapper


def admin_required(func):
    """Decorator that enforces admin role (use after jwt_required)."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if getattr(request, "jwt_user", {}).get("role") != "admin":
            return JsonResponse({"error": "Admin role required"}, status=403)
        return func(request, *args, **kwargs)
    return wrapper


# ── User management ───────────────────────────────────────────────────────────

def create_user(username: str, password: str, role: str = "viewer") -> dict:
    """Create a user in MongoDB. Call this from Django shell for first-time setup."""
    col = get_mongo_collection("users")
    if col.find_one({"username": username}):
        raise ValueError(f"User '{username}' already exists")
    doc = {
        "username":      username,
        "password_hash": _hash_password(password),
        "role":          role,
        "created_at":    datetime.now(tz=timezone.utc).isoformat(),
    }
    col.insert_one(doc)
    return {"username": username, "role": role}


# ── API views ─────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """POST /api/auth/login/ - exchange credentials for JWT tokens."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        return JsonResponse({"error": "username and password required"}, status=400)

    col = get_mongo_collection("users")
    user_doc = col.find_one({"username": username})

    if not user_doc or not _check_password(password, user_doc["password_hash"]):
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    access  = _make_access_token(username, user_doc.get("role", "viewer"))
    refresh = _make_refresh_token(username)

    return JsonResponse({
        "access_token":  access,
        "refresh_token": refresh,
        "token_type":    "Bearer",
        "expires_in":    ACCESS_HOURS * 3600,
        "username":      username,
        "role":          user_doc.get("role", "viewer"),
    })


@csrf_exempt
@require_http_methods(["POST"])
def refresh_view(request):
    """POST /api/auth/refresh/ - get a new access token from a refresh token."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    token = body.get("refresh_token", "")
    if not token:
        return JsonResponse({"error": "refresh_token required"}, status=400)

    try:
        payload = _decode_token(token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Refresh token expired, please log in again"}, status=401)
    except Exception:
        return JsonResponse({"error": "Invalid refresh token"}, status=401)

    col = get_mongo_collection("users")
    user_doc = col.find_one({"username": payload["sub"]})
    if not user_doc:
        return JsonResponse({"error": "User not found"}, status=401)

    access = _make_access_token(payload["sub"], user_doc.get("role", "viewer"))
    return JsonResponse({
        "access_token": access,
        "token_type":   "Bearer",
        "expires_in":   ACCESS_HOURS * 3600,
    })


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def me_view(request):
    """GET /api/auth/me/ - return current user info."""
    user = request.jwt_user
    return JsonResponse({
        "username": user["sub"],
        "role":     user.get("role", "viewer"),
    })


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@admin_required
def register_view(request):
    """POST /api/auth/register/ - create a new user (admin only)."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = body.get("username", "").strip()
    password = body.get("password", "")
    role     = body.get("role", "viewer")

    if not username or not password:
        return JsonResponse({"error": "username and password required"}, status=400)
    if role not in ("admin", "viewer"):
        return JsonResponse({"error": "role must be admin or viewer"}, status=400)

    try:
        result = create_user(username, password, role)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=409)

    return JsonResponse(result, status=201)
