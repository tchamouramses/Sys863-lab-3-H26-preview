from datetime import datetime, timedelta

import stripe
import requests as http
from flask import (
    Blueprint, current_app, flash, jsonify, redirect,
    render_template, request, session, url_for,
)
from flask_login import current_user, login_required

from .models import Payment, PredictionRequest, Subscription, User, db

payments_bp = Blueprint("payments", __name__)

_API_URL = "https://smart-farming.calme2me.com/predict"


def _configure_stripe():
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]


def _require_stripe(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        _configure_stripe()
        if not stripe.api_key:
            flash("Le service de paiement n'est pas encore configuré.", "error")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)
    return decorated


# ── Checkout: 1 CAD per request ─────────────────────────────────────────────

@payments_bp.post("/checkout/request")
@login_required
@_require_stripe
def checkout_request():
    domain = current_app.config["DOMAIN"]
    try:
        cs = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "cad",
                    "product_data": {"name": "Smart Farming — Prédiction"},
                    "unit_amount": 100,          # 1.00 CAD in cents
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{domain}/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain}/",
            metadata={"user_id": str(current_user.id), "type": "per_request"},
        )
        return redirect(cs.url, code=303)
    except stripe.error.StripeError as exc:
        flash(f"Erreur Stripe: {exc.user_message or str(exc)}", "error")
        return redirect(url_for("main.home"))


# ── Checkout: 10 CAD/month subscription ─────────────────────────────────────

@payments_bp.post("/checkout/subscribe")
@login_required
@_require_stripe
def checkout_subscribe():
    price_id = current_app.config.get("STRIPE_PRICE_ID_SUBSCRIPTION", "")
    if not price_id:
        flash("L'abonnement mensuel n'est pas encore configuré. Contactez l'admin.", "error")
        return redirect(url_for("main.home"))

    domain = current_app.config["DOMAIN"]
    try:
        params = dict(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{domain}/payments/subscription-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain}/",
            metadata={"user_id": str(current_user.id), "type": "subscription"},
        )
        if current_user.stripe_customer_id:
            params["customer"] = current_user.stripe_customer_id
        else:
            params["customer_email"] = current_user.email

        cs = stripe.checkout.Session.create(**params)
        return redirect(cs.url, code=303)
    except stripe.error.StripeError as exc:
        flash(f"Erreur Stripe: {exc.user_message or str(exc)}", "error")
        return redirect(url_for("main.home"))


# ── Success: per-request payment ─────────────────────────────────────────────

@payments_bp.get("/success")
@login_required
@_require_stripe
def payment_success():
    session_id = request.args.get("session_id", "")
    if not session_id:
        return redirect(url_for("main.home"))

    # Idempotency — avoid double-processing
    existing = Payment.query.filter_by(stripe_session_id=session_id).first()
    if existing and existing.status == "completed":
        flash("Paiement déjà traité.", "info")
        return redirect(url_for("dashboard.history"))

    try:
        cs = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as exc:
        flash(f"Impossible de vérifier le paiement: {exc.user_message or str(exc)}", "error")
        return redirect(url_for("main.home"))

    if cs.payment_status != "paid":
        flash("Le paiement n'a pas été complété.", "error")
        return redirect(url_for("main.home"))

    # Record payment
    payment = Payment(
        user_id=current_user.id,
        stripe_session_id=session_id,
        stripe_payment_intent_id=getattr(cs, "payment_intent", None),
        amount=1.0,
        currency="cad",
        payment_type="per_request",
        status="completed",
    )
    db.session.add(payment)
    db.session.flush()

    # Link Stripe customer
    if not current_user.stripe_customer_id and getattr(cs, "customer", None):
        current_user.stripe_customer_id = cs.customer

    # Execute pending prediction (payload saved in Flask session before payment)
    pending = session.pop("pending_payload", None)
    if pending:
        try:
            resp = http.post(_API_URL, json=pending, timeout=30)
            result = resp.json()
            pred = PredictionRequest(
                user_id=current_user.id,
                payload=pending,
                result=result if resp.ok else {"error": "API error"},
                is_free=False,
                payment_id=payment.id,
            )
            db.session.add(pred)
            flash("✓ Paiement réussi ! Votre prédiction a été enregistrée.", "success")
        except Exception:
            flash("Paiement réussi, mais la prédiction a échoué. Réessayez.", "warning")
    else:
        flash("Paiement réussi ! Vous pouvez faire votre prédiction.", "success")

    db.session.commit()
    return redirect(url_for("dashboard.history"))


# ── Success: subscription ────────────────────────────────────────────────────

@payments_bp.get("/subscription-success")
@login_required
@_require_stripe
def subscription_success():
    session_id = request.args.get("session_id", "")
    if not session_id:
        return redirect(url_for("main.home"))

    existing = Subscription.query.filter_by(stripe_session_id=session_id).first()
    if existing:
        flash("Abonnement déjà activé.", "info")
        return redirect(url_for("dashboard.subscriptions"))

    try:
        cs = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
    except stripe.error.StripeError as exc:
        flash(f"Impossible de vérifier l'abonnement: {exc.user_message or str(exc)}", "error")
        return redirect(url_for("main.home"))

    stripe_sub = getattr(cs, "subscription", None)
    now = datetime.utcnow()

    if stripe_sub and hasattr(stripe_sub, "current_period_end"):
        end_date = datetime.utcfromtimestamp(stripe_sub.current_period_end)
    else:
        end_date = now + timedelta(days=30)

    sub = Subscription(
        user_id=current_user.id,
        stripe_subscription_id=stripe_sub.id if stripe_sub else None,
        stripe_session_id=session_id,
        status="active",
        amount=10.0,
        currency="cad",
        start_date=now,
        end_date=end_date,
    )
    db.session.add(sub)

    if not current_user.stripe_customer_id and getattr(cs, "customer", None):
        current_user.stripe_customer_id = cs.customer

    db.session.commit()
    flash("✓ Abonnement mensuel activé ! Prédictions illimitées jusqu'au " +
          end_date.strftime("%d/%m/%Y") + ".", "success")
    return redirect(url_for("dashboard.subscriptions"))


# ── Webhook (optional — Stripe CLI in dev) ──────────────────────────────────

@payments_bp.post("/webhook")
def webhook():
    _configure_stripe()
    payload      = request.get_data(as_text=True)
    sig_header   = request.headers.get("Stripe-Signature", "")
    secret       = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")

    if not secret:
        return jsonify({"status": "webhook_not_configured"}), 200

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify({"error": "invalid_signature"}), 400

    etype = event["type"]
    obj   = event["data"]["object"]

    if etype == "customer.subscription.deleted":
        sub = Subscription.query.filter_by(stripe_subscription_id=obj["id"]).first()
        if sub:
            sub.status = "canceled"
            db.session.commit()

    elif etype == "customer.subscription.updated":
        sub = Subscription.query.filter_by(stripe_subscription_id=obj["id"]).first()
        if sub:
            sub.status = obj.get("status", sub.status)
            if obj.get("current_period_end"):
                sub.end_date = datetime.utcfromtimestamp(obj["current_period_end"])
            db.session.commit()

    return jsonify({"status": "ok"}), 200
