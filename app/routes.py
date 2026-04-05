from flask import Blueprint, jsonify, render_template, request
import requests as http


main_bp = Blueprint("main", __name__)

_API_URL = "https://smart-farming.calme2me.com/predict"


@main_bp.get("/")
def home():
    return render_template("index.html")


@main_bp.get("/health")
def healthcheck():
    return jsonify({"message": "Flask app running", "python": "3.10+"})


@main_bp.post("/api/predict")
def predict():
    payload = request.get_json(silent=True) or {}
    try:
        resp = http.post(_API_URL, json=payload, timeout=30)
        return jsonify(resp.json()), resp.status_code
    except http.exceptions.Timeout:
        return jsonify({"error": "L'API de prediction n'a pas repondu a temps."}), 504
    except http.exceptions.RequestException as exc:
        return jsonify({"error": f"Erreur de connexion : {exc}"}), 502
