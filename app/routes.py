from functools import wraps

import requests as http
from flask import Blueprint, jsonify, render_template, request, session
from flask_login import current_user

from .models import PredictionRequest, db

main_bp = Blueprint("main", __name__)

_API_URL = "https://smart-farming.calme2me.com/predict"

def _api_login_required(f):
    """Return JSON 401 for AJAX calls instead of HTML redirect."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "authentication_required"}), 401
        return f(*args, **kwargs)
    return decorated


@main_bp.get("/")
def home():
    from flask_login import login_required
    from flask import redirect, url_for
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    return render_template("index.html")


@main_bp.get("/health")
def healthcheck():
    return jsonify({"message": "Flask app running", "python": "3.10+"})


@main_bp.post("/api/predict")
@_api_login_required
def predict():
    payload = request.get_json(silent=True) or {}

    if not current_user.has_access:
        # Save payload so payments blueprint can replay it after checkout
        session["pending_payload"] = payload
        return jsonify({
            "payment_required": True,
            "free_remaining": 0,
            "total_predictions": current_user.total_predictions,
        }), 402

    is_free    = current_user.can_use_free
    active_sub = current_user.active_subscription

    try:
        resp = http.post(_API_URL, json=payload, timeout=30)
    except http.exceptions.Timeout:
        return jsonify({"error": "L'API de prédiction n'a pas répondu à temps."}), 504
    except http.exceptions.RequestException as exc:
        return jsonify({"error": f"Erreur de connexion : {exc}"}), 502

    result = resp.json()
    if not resp.ok:
        return jsonify(result), resp.status_code

    # Persist prediction
    pred = PredictionRequest(
        user_id=current_user.id,
        payload=payload,
        result=result,
        is_free=is_free,
        subscription_id=active_sub.id if active_sub else None,
    )
    db.session.add(pred)
    db.session.commit()

    result["_meta"] = {
        "free_remaining":    current_user.free_requests_remaining,
        "total_predictions": current_user.total_predictions,
        "has_subscription":  active_sub is not None,
    }
    return jsonify(result), resp.status_code
