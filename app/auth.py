import re
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .models import User, db

auth_bp = Blueprint("auth", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USER_RE  = re.compile(r"^[A-Za-z0-9_]{3,50}$")


@auth_bp.get("/register")
@auth_bp.post("/register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not email or not username or not password:
            flash("Tous les champs sont requis.", "error")
        elif not _EMAIL_RE.match(email):
            flash("Adresse email invalide.", "error")
        elif not _USER_RE.match(username):
            flash("Le nom d'utilisateur doit faire 3-50 caractères alphanumériques.", "error")
        elif len(password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères.", "error")
        elif password != confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Cette adresse email est déjà utilisée.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Ce nom d'utilisateur est déjà pris.", "error")
        else:
            user = User(email=email, username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash(f"Bienvenue {username}! Vous avez {5} prédictions gratuites.", "success")
            return redirect(url_for("main.home"))

    return render_template("auth/register.html")


@auth_bp.get("/login")
@auth_bp.post("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Identifiants incorrects.", "error")
        else:
            login_user(user, remember=remember)
            next_page = request.args.get("next") or url_for("main.home")
            return redirect(next_page)

    return render_template("auth/login.html")


@auth_bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
