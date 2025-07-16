import secrets

import aiohttp
from aiohttp import web

from src.web.config.settings import (
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    TOKEN_URL,
    USER_URL,
)

# Store OAuth states for CSRF protection
oauth_states = {}


routes = web.RouteTableDef()


@routes.get("/auth/login")
async def auth_login(request):
    """Handle login page and OAuth redirect"""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True

    # Build OAuth URL
    oauth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={state}"
    )

    return web.HTTPFound(oauth_url)


@routes.get("/auth/callback")
async def auth_callback(request):
    """Handle OAuth callback from Discord"""
    # Get the authorization code from the callback
    code = request.query.get("code")
    state = request.query.get("state")

    # Validate state to prevent CSRF
    if not state or state not in oauth_states:
        return web.Response(text="Invalid state parameter", status=400)

    # Remove used state
    del oauth_states[state]

    if not code:
        return web.Response(text="No authorization code provided", status=400)

    try:
        # Exchange code for access token
        async with aiohttp.ClientSession() as session:
            token_data = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            }

            async with session.post(TOKEN_URL, data=token_data) as response:
                if response.status != 200:
                    return web.Response(text="Failed to get access token", status=400)

                token_response = await response.json()
                access_token = token_response.get("access_token")

                if not access_token:
                    return web.Response(text="No access token received", status=400)

                # Get user information
                headers = {"Authorization": f"Bearer {access_token}"}
                async with session.get(USER_URL, headers=headers) as user_response:
                    if user_response.status != 200:
                        return web.Response(text="Failed to get user info", status=400)

                    user_data = await user_response.json()

                    # Create session
                    session_id = secrets.token_urlsafe(32)
                    request.app["sessions"][session_id] = {
                        "user_id": user_data["id"],
                        "username": user_data["username"],
                        "discriminator": user_data.get("discriminator", "0"),
                        "avatar": user_data.get("avatar"),
                    }

                    # Redirect to dashboard with session cookie
                    response = web.HTTPFound("/")
                    response.set_cookie("session_id", session_id, max_age=3600, httponly=True)
                    return response

    except Exception as e:
        return web.Response(text=f"Authentication error: {str(e)}", status=500)


@routes.get("/auth/logout")
async def auth_logout(request):
    """Handle user logout"""
    # Clear session
    session_id = request.cookies.get("session_id")
    if session_id and session_id in request.app["sessions"]:
        del request.app["sessions"][session_id]

    # Redirect to login with cleared cookie
    response = web.HTTPFound("/auth/login")
    response.del_cookie("session_id")
    return response
