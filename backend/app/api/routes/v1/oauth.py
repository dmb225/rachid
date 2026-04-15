"""OAuth2 authentication routes."""

from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.deps import UserSvc
from app.core.oauth import oauth
from app.core.security import create_access_token, create_refresh_token

router = APIRouter()

from app.core.config import settings

FRONTEND_URL = settings.FRONTEND_URL


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google OAuth2 login page."""
    from app.core.config import settings

    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, user_service: UserSvc):
    """Handle Google OAuth2 callback.

    Creates a new user if one doesn't exist with the Google email,
    or returns tokens for existing user. Redirects to frontend with tokens.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            params = urlencode({"error": "Failed to get user info from Google"})
            return RedirectResponse(url=f"{FRONTEND_URL}/login?{params}")

        email = user_info.get("email")
        google_id = user_info.get("sub")
        full_name = user_info.get("name")

        # Try to find existing user by OAuth ID
        user = await user_service.get_by_oauth("google", google_id)

        if not user:
            # Try to find by email (link existing account)
            user = await user_service.get_by_email(email)
            if user:
                # Link OAuth to existing account
                user = await user_service.link_oauth(user.id, "google", google_id)
            else:
                # Create new user
                user = await user_service.create_oauth_user(
                    email=email,
                    full_name=full_name,
                    oauth_provider="google",
                    oauth_id=google_id,
                )

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        # Redirect to frontend with tokens
        params = urlencode(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        )
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?{params}")

    except Exception as e:
        params = urlencode({"error": str(e)})
        return RedirectResponse(url=f"{FRONTEND_URL}/login?{params}")
