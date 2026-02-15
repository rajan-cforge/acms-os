"""FastAPI authentication middleware.

Provides:
- Bearer token extraction from Authorization header
- User context injection via FastAPI dependencies
- Role-based access control decorators
- Audit logging for authenticated requests

Part of Sprint 1 Security Foundation (Days 4-5).
"""

import logging
from typing import Optional, List, Callable
from functools import wraps

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.auth.simple_auth import SimpleAuth, UserContext, AuthError, get_auth_service
from src.gateway.tracing import get_trace_id, set_trace_id, generate_trace_id

logger = logging.getLogger(__name__)

# FastAPI security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: SimpleAuth = Depends(get_auth_service)
) -> Optional[UserContext]:
    """Extract and validate user from Authorization header.

    This dependency can be used in FastAPI endpoints:

        @app.get("/protected")
        async def protected_route(user: UserContext = Depends(get_current_user)):
            if not user:
                raise HTTPException(401, "Authentication required")
            return {"user_id": user.user_id, "role": user.role}

    Args:
        request: FastAPI request
        credentials: Extracted bearer token
        auth_service: Auth service instance

    Returns:
        UserContext if authenticated, None otherwise
    """
    # Ensure trace_id is set for this request
    if not get_trace_id():
        trace_id = generate_trace_id()
        set_trace_id(trace_id)

    if not credentials:
        # Check for token in cookie as fallback
        token = request.cookies.get("access_token")
        if not token:
            return None
    else:
        token = credentials.credentials

    try:
        user_ctx = auth_service.validate_token(token)

        # Log authentication for audit
        logger.info(
            f"[{get_trace_id()}] Auth: user={user_ctx.user_id} "
            f"role={user_ctx.role} tenant={user_ctx.tenant_id}"
        )

        return user_ctx

    except AuthError as e:
        logger.warning(f"[{get_trace_id()}] Auth failed: {e.code} - {e.message}")
        return None


async def require_auth(
    user: Optional[UserContext] = Depends(get_current_user)
) -> UserContext:
    """Require authentication for an endpoint.

    Usage:
        @app.get("/protected")
        async def protected_route(user: UserContext = Depends(require_auth)):
            return {"user_id": user.user_id}

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_role(allowed_roles: List[str]):
    """Create a dependency that requires specific roles.

    Usage:
        @app.get("/admin")
        async def admin_only(user: UserContext = Depends(require_role(["admin"]))):
            return {"admin": True}

    Args:
        allowed_roles: List of role names that can access this endpoint

    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        user: UserContext = Depends(require_auth)
    ) -> UserContext:
        if user.role not in allowed_roles:
            logger.warning(
                f"[{get_trace_id()}] Access denied: user={user.user_id} "
                f"role={user.role} required={allowed_roles}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {' or '.join(allowed_roles)}"
            )
        return user

    return role_checker


def require_admin(user: UserContext = Depends(require_auth)) -> UserContext:
    """Shortcut dependency for admin-only endpoints.

    Usage:
        @app.get("/admin")
        async def admin_only(user: UserContext = Depends(require_admin)):
            return {"admin": True}
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return user


def require_member(user: UserContext = Depends(require_auth)) -> UserContext:
    """Shortcut dependency for member+ endpoints.

    Allows both member and admin roles.
    """
    if user.role not in ["member", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Member access required"
        )
    return user


def optional_auth(
    user: Optional[UserContext] = Depends(get_current_user)
) -> Optional[UserContext]:
    """Optional authentication - returns user if authenticated, None otherwise.

    Use this for endpoints that work for both authenticated and anonymous users,
    but provide enhanced functionality for authenticated users.

    Usage:
        @app.get("/content")
        async def get_content(user: Optional[UserContext] = Depends(optional_auth)):
            if user:
                return {"content": "personalized", "user_id": user.user_id}
            return {"content": "generic"}
    """
    return user


def audit_log(action: str):
    """Decorator to add audit logging to endpoints.

    Usage:
        @app.post("/sensitive")
        @audit_log("sensitive_action")
        async def sensitive_action(user: UserContext = Depends(require_auth)):
            return {"success": True}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user")
            trace_id = get_trace_id()

            logger.info(
                f"[{trace_id}] AUDIT: action={action} "
                f"user={user.user_id if user else 'anonymous'} "
                f"role={user.role if user else 'none'}"
            )

            result = await func(*args, **kwargs)

            logger.info(
                f"[{trace_id}] AUDIT: action={action} completed"
            )

            return result
        return wrapper
    return decorator


class AuthMiddleware:
    """Middleware for request-level authentication processing.

    Adds user context to request.state for access in other middleware.
    """

    def __init__(self, app, auth_service: Optional[SimpleAuth] = None):
        self.app = app
        self.auth_service = auth_service or get_auth_service()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract authorization header
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()

            user_ctx = None
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                try:
                    user_ctx = self.auth_service.validate_token(token)
                except AuthError:
                    pass

            # Store in scope for access by the app
            scope["user"] = user_ctx

        await self.app(scope, receive, send)
