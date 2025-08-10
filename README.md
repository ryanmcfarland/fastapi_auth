# FastAPI Auth Framework

Personal boilerplate for future projects. Includes an implementation of an authentication framework.

## TODO

- Improve logging
- Add More tests
- Auth headers - defaults to session
- gunicorn logging on startup

## Walkthroughs

### Migrations

Uses `Go-Migrate` : See [migrations.md](migrations.md)

### Endpoints : Auth

> auth/register

> auth/login

> auth/logout (mocked : TODO)

> auth/refresh

Follows simple auth flow: register -> login. `Login` will return an access_token AND return a refresh_token via cookie. Once user's access_token has expired, `auth/refresh` can be called to return a new short-lived access token.

Each refresh_token is decoded & checked against a database. This allows a auto logout for everyone.

### Models

TODO - Should be optimised and better structured.

### Utils

Token & Password Check. `TokenUtils` contains logic to decode JWT's and is used within `UserService`

### Services

`UserService` & `PermissionService` contain logic to manage / check users / check user roles for protected endpoints.

### Dependancies

- `get_refresh_token` : grab refresh token from header / token from the API request. Is used in the `auth/request` route.
- `get_oauth2_scheme` : dependancy that runs for `OAuth2PasswordBearerWithCookie` to check for header `session`. TODO : put into settings?
- `get_current_user` : dependancy that returns the `UserService` object with the AsyncDatabase object.
- `require_admin` : dependancy that checks that current_user has role `admin`. Checked via DB call.

## Tests [pytest]

```bash
pytest --collect-only
```

```bash
pytest -v -m auth
```

# Run : Gunicorn

```bash
gunicorn app.main:app -c gunicorn.conf.py
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 -c gunicorn.conf.py
```

# Pyenv Commands

```bash
pyenv install 3.12.4

pyenv virtualenv 3.12.4 fastapi_auth

pyenv activate fastapi_auth

pyenv local fastapi_auth

pyenv virtualenv-delete test_env
```
