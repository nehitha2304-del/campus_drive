import os
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from postgrest import APIError
from supabase import Client, create_client


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
load_dotenv(Path(__file__).with_name(".env"))

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    """Allow browser clients on any origin to call the public API."""
    if request.path.startswith("/api/"):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
        response.headers["Access-Control-Max-Age"] = "86400"
    return response


def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.")
    return create_client(url, key)


def valid_uuid(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def database_error(error: APIError):
    app.logger.exception("Supabase request failed")
    # Postgres unique, foreign-key, and check-constraint violations are client conflicts.
    if getattr(error, "code", None) in {"23505", "23503", "23514"}:
        return jsonify({"error": "The request conflicts with the current database state."}), 409
    return jsonify({"error": "The database request failed."}), 502


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:asset_path>")
def frontend_asset(asset_path: str):
    return send_from_directory(FRONTEND_DIR, asset_path)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/users")
def users():
    """Public community list used by the existing frontend."""
    try:
        response = get_supabase().table("users").select("id,email").execute()
        return jsonify({"users": response.data})
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    except APIError as error:
        return database_error(error)


@app.get("/api/events")
def list_events():
    try:
        query = get_supabase().table("events").select("*")
        status = request.args.get("status")
        if status:
            query = query.eq("status", status)
        response = query.execute()
        return jsonify({"events": response.data})
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    except APIError as error:
        return database_error(error)


@app.get("/api/events/<event_id>")
def get_event(event_id):
    event_id = valid_uuid(event_id)
    if not event_id:
        return jsonify({"error": "event_id must be a UUID."}), 400
    try:
        response = get_supabase().table("events").select("*").eq("id", event_id).limit(1).execute()
        if not response.data:
            return jsonify({"error": "Event not found."}), 404
        return jsonify({"event": response.data[0]})
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    except APIError as error:
        return database_error(error)


@app.post("/api/registrations")
def create_registration():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    user_id = valid_uuid(payload.get("user_id"))
    event_id = valid_uuid(payload.get("event_id"))
    if not user_id or not event_id:
        return jsonify({"error": "user_id and event_id are required UUID values."}), 400

    try:
        client = get_supabase()
        event_result = client.table("events").select("id,capacity,status").eq("id", event_id).limit(1).execute()
        if not event_result.data:
            return jsonify({"error": "Event not found."}), 404

        user_result = client.table("users").select("id").eq("id", user_id).limit(1).execute()
        if not user_result.data:
            return jsonify({"error": "User not found."}), 404

        existing = client.table("registrations").select("id").eq("user_id", user_id).eq("event_id", event_id).limit(1).execute()
        if existing.data:
            return jsonify({"error": "This user is already registered for the event."}), 409

        event = event_result.data[0]
        count_result = client.table("registrations").select("id", count="exact").eq("event_id", event_id).execute()
        capacity = event.get("capacity")
        if capacity is not None and (count_result.count or 0) >= capacity:
            return jsonify({"error": "This event is at capacity."}), 409

        inserted = client.table("registrations").insert({"user_id": user_id, "event_id": event_id}).select("*").single().execute()
        return jsonify({"registration": inserted.data}), 201
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    except APIError as error:
        return database_error(error)


@app.get("/api/me/registrations")
def user_registrations():
    # No authentication is configured. The caller supplies the public user UUID.
    user_id = valid_uuid(request.args.get("user_id"))
    if not user_id:
        return jsonify({"error": "Provide a valid user_id UUID query parameter."}), 400
    try:
        response = (
            get_supabase().table("registrations")
            .select("id,user_id,event_id,created_at")
            .eq("user_id", user_id)
            .execute()
        )
        return jsonify({"registrations": response.data})
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    except APIError as error:
        return database_error(error)


@app.get("/api/events/<event_id>/registrations")
def event_registrations(event_id):
    event_id = valid_uuid(event_id)
    if not event_id:
        return jsonify({"error": "event_id must be a UUID."}), 400
    try:
        client = get_supabase()
        event = client.table("events").select("id").eq("id", event_id).limit(1).execute()
        if not event.data:
            return jsonify({"error": "Event not found."}), 404
        response = (
            client.table("registrations")
            .select("id,user_id,event_id,created_at")
            .eq("event_id", event_id)
            .execute()
        )
        return jsonify({"registrations": response.data})
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
    except APIError as error:
        return database_error(error)


if __name__ == "__main__":
    app.run(debug=True)
