from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import Config
from utils.db import db

# Blueprints
from routes.students import students_bp
from routes.professors import professors_bp
from routes.auth import auth_bp
from routes.arduino import arduino_bp
from routes.access import access_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Extensions
    CORS(app, resources={r"/*": {"origins": "*"}})
    db.init_app(app)
    JWTManager(app)

    # Register Blueprints
    app.register_blueprint(students_bp, url_prefix="/students")
    app.register_blueprint(professors_bp, url_prefix="/professors")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(arduino_bp, url_prefix="/arduino")
    app.register_blueprint(access_bp, url_prefix="/access")

    # Health check
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    # Create tables if they don't exist
    with app.app_context():
        from models import Student, Professor, User  # noqa: F401 - ensure models are registered
        db.create_all()

    return app

print("Starting the Flask application...")
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
