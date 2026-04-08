import os
from functools import wraps
from flask import Blueprint, jsonify, request
from .models import User, Subscription, Payment, PredictionRequest

api_bp = Blueprint("api", __name__, url_prefix="/api")


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("Authorization", "")
        expected = os.environ.get("POWERBI_API_KEY", "")
        if not expected or api_key != f"Bearer {expected}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@api_bp.route("/stats/users")
@require_api_key
def users_stats():
    users = User.query.all()
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "total_predictions": u.total_predictions,
            "has_active_subscription": u.active_subscription is not None,
        }
        for u in users
    ])

@api_bp.route("/stats/subscriptions")
@require_api_key
def subscriptions_stats():
    subs = Subscription.query.all()
    return jsonify([
        {
            "id": s.id,
            "user_id": s.user_id,
            "status": s.status,
            "amount": s.amount,
            "currency": s.currency,
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in subs
    ])


@api_bp.route("/stats/predictions")
@require_api_key
def predictions_stats():
    predictions = PredictionRequest.query.all()
    return jsonify([
        {
            "id": p.id,
            "user_id": p.user_id,
            "payload": p.payload,
            "result": p.result,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in predictions
    ])


@api_bp.route("/stats/overview")
@require_api_key
def overview():
    from sqlalchemy import func
    from . import db

    total_users = User.query.count()
    total_predictions = PredictionRequest.query.count()
    free_predictions = PredictionRequest.query.filter_by(is_free=True).count()
    paid_predictions = PredictionRequest.query.filter_by(is_free=False).count()

    total_revenue = db.session.query(func.sum(Payment.amount)).filter_by(status="completed").scalar() or 0.0
    active_subscriptions = Subscription.query.filter_by(status="active").count()
    completed_payments = Payment.query.filter_by(status="completed").count()
    pending_payments = Payment.query.filter_by(status="pending").count()

    return jsonify({
        "total_users": total_users,
        "total_predictions": total_predictions,
        "free_predictions": free_predictions,
        "paid_predictions": paid_predictions,
        "total_revenue_cad": round(total_revenue, 2),
        "active_subscriptions": active_subscriptions,
        "completed_payments": completed_payments,
        "pending_payments": pending_payments,
    })
