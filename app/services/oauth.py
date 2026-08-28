"""Google OAuth client registration.

`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` come from the Google Cloud Console
OAuth credentials for this app; unset in an env that doesn't need Google
login. The redirect URI configured there must match the `/api/auth/google/callback`
route this app serves.
"""

import os

from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    client_kwargs={"scope": "openid email profile"},
)


def google_login_enabled() -> bool:
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))
