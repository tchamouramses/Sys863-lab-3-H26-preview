from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .models import PredictionRequest, Subscription, db

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


@dashboard_bp.post("/history/<int:pred_id>/feedback")
@login_required
def set_feedback(pred_id):
    pred = PredictionRequest.query.filter_by(
        id=pred_id, user_id=current_user.id
    ).first_or_404()
    value = request.form.get("feedback", "").strip()
    if value not in ("parfait", "moyen", "mauvais"):
        flash("Retour invalide.", "error")
        return redirect(url_for("dashboard.history"))
    pred.feedback = value
    db.session.commit()
    flash("Retour enregistré.", "success")
    return redirect(url_for("dashboard.history"))


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
