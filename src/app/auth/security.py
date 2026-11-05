from typing import Annotated, Optional

from fastapi import HTTPException, Request
from fastapi.param_functions import Form
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param


# Note: This is a bit of a hack to allow the same endpoint to be used for both authenticated and unauthenticated users
# without forcing the use of the OAuth2PasswordBearerWithCookie dependency which would raise an error if no token is provided.
# By setting auto_error=False, we can handle the case where no token is present and simply return None for the user,
# allowing the service layer to decide how to handle unauthenticated requests.
# This is useful for endpoints that can be accessed by both authenticated and unauthenticated users,
# providing flexibility while still supporting authentication when available.
class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    """Extends the OAuth2PasswordBearer class to retrieve short-lived access token either from headers or cookies"""

    async def __call__(self, request: Request) -> Optional[str]:
        # Try to get auth field from headers (will be None during a redirect)
        authorization = request.headers.get("Authorization")
        if authorization is not None:
            # docs (Authorize) creates header : "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            scheme, param = get_authorization_scheme_param(authorization)
            if not authorization or scheme.lower() != "bearer":
                if self.auto_error:
                    raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
                else:
                    return None
            return param
        # No token in Authorization header. Try using cookie:
        if token := request.cookies.get("access_token", None):
            return token
        elif self.auto_error:
            raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
        else:
            return None


class OAuth2LoginForm:
    """
    Custom OAuth2 Form (Class that we Depends() within /login) that requires either username or email (or both) and password.
    At least one identifier (username or email) must be provided. Email is prioritized as the identifier if both are provided.
    """

    def __init__(
        self,
        *,
        username: Annotated[Optional[str], Form()] = None,
        email: Annotated[Optional[str], Form()] = None,
        password: Annotated[str, Form()],
    ):
        # Validate that at least one identifier is provided
        identifier = email or username
        if identifier is None:
            raise HTTPException(status_code=400, detail="Either username or email must be provided")

        self.username = username
        self.email = email
        self.password = password
        self._identifier = identifier

    @property
    def identifier(self) -> str:
        """
        Returns the identifier to use for authentication.
        Prioritizes email if both are provided, otherwise returns whichever is available.
        """
        return self._identifier
