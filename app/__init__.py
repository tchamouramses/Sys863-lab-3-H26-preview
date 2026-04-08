import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app() -> Flask:
    app = Flask(__name__)

    # ── Core config ──────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-prod")

    # ── Database ──────────────────────────────────────────────────────────────
    data_dir = os.path.join(os.path.dirname(app.root_path), "data")
    os.makedirs(data_dir, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(data_dir, 'app.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ── Stripe ────────────────────────────────────────────────────────────────
    app.config["STRIPE_SECRET_KEY"]           = os.environ.get("STRIPE_SECRET_KEY", "")
    app.config["STRIPE_PUBLISHABLE_KEY"]      = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    app.config["STRIPE_PRICE_ID_SUBSCRIPTION"]= os.environ.get("STRIPE_PRICE_ID_SUBSCRIPTION", "")
    app.config["STRIPE_WEBHOOK_SECRET"]       = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    app.config["DOMAIN"]                      = os.environ.get("DOMAIN", "http://localhost:5000")

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "warning"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # ── Blueprints ────────────────────────────────────────────────────────────
    from .auth      import auth_bp
    from .dashboard import dashboard_bp
    from .payments  import payments_bp
    from .routes    import main_bp
    from .api       import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,      url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(payments_bp,  url_prefix="/payments")
    app.register_blueprint(api_bp)

    # ── Template filters ────────────────────────────────────────────────────
    @app.template_filter("without_key")
    def without_key(d, key):
        if not isinstance(d, dict):
            return d
        return {k: v for k, v in d.items() if k != key}

    # ── Create tables ─────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()

    # ── Load .env if present (local dev) ─────────────────────────────────────
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return app
