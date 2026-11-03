# API Inspector

API Inspector is an open-source project for inspecting APIs and identifying differences between an API's documented contract and its actual behavior.

> **Current status:** Backend foundation and account authentication are implemented. The OpenAPI import and inspection workflows are planned; they are not implemented yet.

## Current Features

- Custom user model with email-based authentication
- User registration with email verification
- JWT access and refresh tokens
- Logout and refresh-token blacklisting
- User profile endpoint
- Change-password and password-reset flows
- Rate limiting for public authentication endpoints
- Automated tests for account and authentication behavior

## Tech Stack

- Python 3.14+
- Django 6.1
- Django REST Framework
- Django REST Framework Simple JWT
- SQLite for local development

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Kian-kianmehr/api-inspector.git
cd api-inspector
```

### 2. Create and activate a virtual environment

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file:

Linux / macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set your own Django secret key and email credentials. Never commit the real `.env` file or share its secrets.

Generate a Django secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

For Gmail SMTP, use a Google App Password. Do not use your normal Google account password.

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Run the development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/accounts/`.

## Account API

All endpoints use the `/api/accounts/` prefix.

| Method | Endpoint | Authentication | Purpose |
|---|---|---|---|
| POST | `register/` | Public | Create an account and send a verification email |
| POST | `verify-email/` | Public | Verify an email using the UID and token |
| POST | `resend-verification/` | Public | Request another verification email |
| POST | `login/` | Public | Obtain JWT access and refresh tokens |
| POST | `token/refresh/` | Refresh token | Obtain a new access token |
| POST | `logout/` | Access token | Blacklist the supplied refresh token |
| GET | `me/` | Access token | Retrieve the current user's profile |
| POST | `change-password/` | Access token | Change the current user's password |
| POST | `password-reset/` | Public | Request a password reset email |
| POST | `password-reset/confirm/` | Public | Set a new password using the reset UID and token |

### Authentication

For protected endpoints, send the access token in the request header:

```http
Authorization: Bearer <access_token>
```

### Registration example

```json
{
  "email": "user@example.com",
  "display_name": "Example User",
  "password": "Use-A-Strong-Password-Here",
  "confirm_password": "Use-A-Strong-Password-Here"
}
```

Newly registered accounts remain inactive until their email address is verified.

### Login example

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

The login endpoint returns JWT tokens. Use the access token for authenticated API requests and the refresh token to obtain a new access token.

## Running Tests

Run the complete test suite:

```bash
python manage.py test accounts
```

Run Django's system checks:

```bash
python manage.py check
```

## Environment Variables

See [\.env.example](.env.example) for the complete list of required and optional settings.

## Security Notes

- Keep `.env` out of version control.
- Use a unique, randomly generated `DJANGO_SECRET_KEY`.
- Use an app-specific SMTP password for Gmail.
- Set `DJANGO_DEBUG=False` and configure `DJANGO_ALLOWED_HOSTS` appropriately before deployment.
- The current SQLite configuration is intended for local development. Choose and configure a production database before deployment.

## Contributing

Contributions, bug reports, and suggestions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

## License

No license has been added yet. Until a license is selected and included in this repository, the project should not be treated as having an open-source reuse license.
