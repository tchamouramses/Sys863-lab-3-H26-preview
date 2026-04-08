from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

FREE_REQUEST_LIMIT = 5


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id                 = db.Column(db.Integer, primary_key=True)
    email              = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username           = db.Column(db.String(100), unique=True, nullable=False)
    password_hash      = db.Column(db.String(255), nullable=False)
    stripe_customer_id = db.Column(db.String(100))
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)

    predictions   = db.relationship("PredictionRequest", back_populates="user", lazy="dynamic")
    subscriptions = db.relationship("Subscription",       back_populates="user", lazy="dynamic")
    payments      = db.relationship("Payment",            back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def total_predictions(self) -> int:
        return self.predictions.count()

    @property
    def active_subscription(self):
        now = datetime.utcnow()
        return (
            self.subscriptions
            .filter_by(status="active")
            .filter(Subscription.end_date > now)
            .first()
        )

    @property
    def free_requests_remaining(self) -> int:
        return max(0, FREE_REQUEST_LIMIT - self.total_predictions)

    @property
    def can_use_free(self) -> bool:
        return self.total_predictions < FREE_REQUEST_LIMIT

    @property
    def has_access(self) -> bool:
        return self.can_use_free or (self.active_subscription is not None)


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id                     = db.Column(db.Integer, primary_key=True)
    user_id                = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    stripe_subscription_id = db.Column(db.String(300))
    stripe_session_id      = db.Column(db.String(300), unique=True)
    status                 = db.Column(db.String(50), default="pending")  # active | canceled | past_due | pending
    amount                 = db.Column(db.Float, default=10.0)
    currency               = db.Column(db.String(10), default="cad")
    start_date             = db.Column(db.DateTime)
    end_date               = db.Column(db.DateTime)
    created_at             = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="subscriptions")


class Payment(db.Model):
    __tablename__ = "payments"

    id                       = db.Column(db.Integer, primary_key=True)
    user_id                  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    stripe_session_id        = db.Column(db.String(300), unique=True)
    stripe_payment_intent_id = db.Column(db.String(300))
    amount                   = db.Column(db.Float)
    currency                 = db.Column(db.String(10), default="cad")
    payment_type             = db.Column(db.String(50))   # per_request
    status                   = db.Column(db.String(50), default="pending")  # pending | completed | failed
    created_at               = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="payments")


class PredictionRequest(db.Model):
    __tablename__ = "prediction_requests"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    payload         = db.Column(db.JSON)
    result          = db.Column(db.JSON)
    is_free         = db.Column(db.Boolean, default=False)
    payment_id      = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    feedback       = db.Column(db.String(20), nullable=True)  # parfait | moyen | mauvais

    user = db.relationship("User", back_populates="predictions")
