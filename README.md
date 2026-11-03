# API Inspector

API Inspector is a developer-focused platform for understanding API contracts and, eventually, comparing documented specifications with real API behavior.

The project contains a Django REST API backend and a React-based web frontend. The current implementation focuses on account management, authentication, and the frontend workspace foundation. OpenAPI import and live API inspection are planned next steps and are not implemented yet.

## Project Overview

API Inspector is split into two applications:

- **Backend:** A Django REST Framework API that handles user accounts, authentication, and account security.
- **Frontend:** A React single-page application that provides the user interface for authentication and the API Inspector workspace.

The frontend interface was developed with assistance from AI tools. AI was used as a development aid for implementation and UI work; the code is included in the repository and can be reviewed, tested, and maintained like the backend.

## Current Features

### Backend

- Custom user model with email-based authentication
- User registration with email verification
- JWT access and refresh tokens
- Refresh-token rotation and blacklisting
- Logout
- User profile endpoint
- Change-password flow
- Password-reset flow
- Rate limiting for public authentication endpoints
- Automated tests for account and authentication behavior

### Frontend

- React single-page application built with Vite and TypeScript
- Registration, login, and logout flows
- Email verification and password recovery screens
- Protected application workspace
- Account settings and password change
- Responsive dashboard layout with Specifications and Inspections sections
- API request handling with JWT authentication and access-token refresh
- Tailwind CSS tooling and Lucide icons

> **Development status:** The workspace UI is in place, but specification import, endpoint discovery, and contract-vs-response inspection are not functional yet. Those are planned product features.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Backend | Python, Django 6.1, Django REST Framework |
| Authentication | Simple JWT |
| Frontend | React 18, TypeScript, Vite |
| Routing | React Router |
| Styling and icons | Tailwind CSS, Lucide React |
| Database | SQLite (local development) |
| Configuration | python-dotenv |

## Project Structure

```text
api-inspector/
├── accounts/              # User model, authentication, serializers, views, tests
├── config/                # Django settings and URL configuration
├── frontend/
│   ├── src/
│   │   ├── App.tsx        # Application routes, pages, and UI
│   │   └── styles.css     # Application styles
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
├── .env.example           # Backend environment template
├── manage.py
└── requirements.txt
```

## Getting Started

Run the backend and frontend in separate terminals.

### 1. Clone the repository

```bash
git clone https://github.com/Kian-kianmehr/api-inspector.git
cd api-inspector
```

### 2. Set up the backend

**Requirements:** Python 3.14+ (as currently specified by the project).

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create the backend environment file:

```bash
cp .env.example .env
```

Set your own `DJANGO_SECRET_KEY`, `EMAIL_HOST_USER`, and `EMAIL_HOST_PASSWORD` values in `.env`. Never commit the real `.env` file or share its secrets.

Generate a Django secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Apply migrations and start Django on port **8008**:

```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8008
```

The frontend's Vite development proxy is configured to forward `/api` requests to `http://127.0.0.1:8008`.

### 3. Set up the frontend

**Requirements:** Node.js and npm.

Open a second terminal from the repository root:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Vite runs at:

```text
http://127.0.0.1:5173
```

The frontend uses `VITE_API_BASE_URL=/api` by default. The Vite proxy forwards those requests to the Django backend.

To create a production build:

```bash
npm run build
```

## Account API

All account endpoints use the `/api/accounts/` prefix.

| Method | Endpoint | Authentication | Purpose |
| --- | --- | --- | --- |
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

For protected endpoints, send the access token in the request header:

```http
Authorization: Bearer <access_token>
```

Newly registered accounts remain inactive until their email address is verified.

## Running Tests

Run the backend test suite:

```bash
python manage.py test accounts
```

Run Django's system checks:

```bash
python manage.py check
```

Build the frontend and run its TypeScript checks:

```bash
cd frontend
npm run build
```

## Environment Variables

- Backend: see [`.env.example`](.env.example).
- Frontend: see [`frontend/.env.example`](frontend/.env.example).

Keep real secrets in local environment files and never commit them.

## Security Notes

- Keep `.env` files out of version control.
- Use a unique, randomly generated `DJANGO_SECRET_KEY`.
- Use an app-specific SMTP password for Gmail.
- Set `DJANGO_DEBUG=False` and configure `DJANGO_ALLOWED_HOSTS` before deployment.
- The current SQLite configuration is intended for local development. Configure a production database before deployment.
- The frontend stores authentication tokens in session storage; use HTTPS in production.

## Roadmap

- [ ] OpenAPI 3.0 and 3.1 specification import
- [ ] Endpoint and schema discovery
- [ ] API response inspection
- [ ] Contract-versus-response comparison
- [ ] Inspection history and issue reporting

## Contributing

Contributions, bug reports, and suggestions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

## License

No license has been added yet. Until a license is selected and included in this repository, the project should not be treated as having an open-source reuse license.
