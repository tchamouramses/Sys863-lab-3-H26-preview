from flask import Blueprint, render_template
from flask_login import current_user, login_required

from .models import PredictionRequest, Subscription

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/history")
@login_required
def history():
    predictions = (
        PredictionRequest.query
        .filter_by(user_id=current_user.id)
        .order_by(PredictionRequest.created_at.desc())
        .all()
    )
    return render_template("dashboard/history.html", predictions=predictions)


@dashboard_bp.get("/subscriptions")
@login_required
def subscriptions():
    subs = (
        Subscription.query
        .filter_by(user_id=current_user.id)
        .order_by(Subscription.created_at.desc())
        .all()
    )
    from datetime import datetime
    return render_template("dashboard/subscriptions.html", subscriptions=subs, now=datetime.utcnow())
