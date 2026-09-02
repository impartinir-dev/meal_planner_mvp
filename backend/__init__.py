import os

from flask import Flask, jsonify, send_from_directory

from backend.config import Config
from backend.extensions import db, login_manager


def create_app(test_config=None):
    package_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(package_dir)
    instance_path = os.path.join(package_dir, "instance")
    os.makedirs(instance_path, exist_ok=True)

    app = Flask(
        __name__,
        instance_path=instance_path,
        static_folder=None,
    )
    app.config.from_object(Config)
    db_path = os.path.join(instance_path, "nutrimatch.db")
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{db_path}")
    if test_config:
        app.config.update(test_config)
    if not app.config.get("DEBUG"):
        app.config["DEBUG"] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.session_protection = "basic"

    from backend.models import CupboardItem, User, ensure_schema  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "unauthorized"}), 401

    from backend.auth import auth_bp
    from backend.api import api_bp
    from backend.admin_api import admin_bp
    from backend.cupboard_api import cupboard_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(cupboard_bp, url_prefix="/api/cupboard")

    with app.app_context():
        db.create_all()
        ensure_schema()

    dist = os.path.join(project_root, "frontend", "dist")

    @app.get("/")
    def root():
        index = os.path.join(dist, "index.html")
        if os.path.isfile(index):
            return send_from_directory(dist, "index.html")
        return jsonify({"status": "ok", "app": "NutriMatch API"}), 200

    @app.errorhandler(404)
    def spa_or_404(err):
        from flask import request

        if request.path.startswith("/api"):
            return jsonify({"error": "not_found"}), 404
        if request.path.startswith("/assets/") or "." in request.path.split("/")[-1]:
            file_path = os.path.join(dist, request.path.lstrip("/"))
            if os.path.isfile(file_path):
                return send_from_directory(dist, request.path.lstrip("/"))
        index = os.path.join(dist, "index.html")
        if os.path.isfile(index):
            return send_from_directory(dist, "index.html")
        return jsonify({"error": "not_found"}), 404

    return app
