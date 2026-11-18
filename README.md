# IST Nexus

A responsive campus events frontend backed by Flask and the Supabase `users`, `events`, and `registrations` tables.

## Run locally

1. Activate the virtual environment in `backend`.
2. Install the root runtime dependencies with `python -m pip install -r requirements.txt`.
3. Put `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `backend/.env` (see `.env.example`).
4. From the project root, run `python app.py` and open `http://127.0.0.1:5000`.

The frontend reads `/api/users`; the endpoint returns public `id` and `email` fields from `users`.

## API

All routes below are public and include permissive CORS headers (`Access-Control-Allow-Origin: *`). IDs are UUIDs.

| Method | Endpoint | Behavior |
| --- | --- | --- |
| `GET` | `/api/events` | List events; optional `?status=...` filter. |
| `GET` | `/api/events/<id>` | Fetch one event or return `404`. |
| `POST` | `/api/registrations` | JSON `{ "user_id": "...", "event_id": "..." }`; returns `201`, or `409` for duplicate/capacity conflict. |
| `GET` | `/api/me/registrations?user_id=<uuid>` | List registrations for the supplied user. `user_id` is required because there is no login. |
| `GET` | `/api/events/<id>/registrations` | List attendee registration IDs and timestamps for an event. |
| `GET` | `/api/users` | List public user IDs and emails. |
| `GET` | `/api/health` | Health check. |

The API follows the tables in `backend/database.png`: `events`, `registrations`, and `users`. The images show only a small set of event fields, so the events API returns the columns present in the actual Supabase table. The "my registrations" and organizer-only concepts in the endpoint reference cannot be secured without authentication; these routes are public as requested. The attendee list omits email addresses.

## Deploy to Vercel

Import this project with its root directory set to the repository root. Vercel detects the root `app.py` Flask entry point and installs dependencies from `requirements.txt`. Add `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` under Project Settings > Environment Variables for every environment you deploy, then deploy.

Do not upload or commit `backend/.env`. CORS allows any website to read the public API, but CORS does not itself grant database access: Supabase still applies the permissions and Row Level Security (RLS) policies for the configured publishable key. Configure RLS to permit exactly the public operations you intend. Because there is no authentication, anyone can choose a `user_id` in registration requests or query another user's registrations. `/api/users` also returns email addresses. Use only data that is intended to be public, and never use a service-role key here.

The frontend event cards are illustrative sample content; the API reads live event rows and accepts registration requests. For capacity limits to remain correct under simultaneous requests, enforce the capacity rule in the database with a transaction or database function. Confirm the `events` and `registrations` tables and their Row Level Security policies exist before using the write endpoint.
