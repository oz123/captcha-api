import os

from celery import Celery
from flask import Blueprint, Flask, redirect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .db import db, migrate
from .log_utils import configure_logging
from .rest import api

index_bp = Blueprint("index", __name__)

celery = Celery()


@index_bp.route("/")
def index():
    return redirect("/swagger-ui")


def _read_env_config(app: Flask):
    try:
        app.config.from_envvar("CAPTCHA_API_CONFIG")
    except Exception as e:
        app.logger.error(e)


def _setup_api(app: Flask):
    api.version = app.config["API_VERSION"]
    api.prefix = f"/api/{api.version}"
    api.init_app(app)


def _setup_celery(app):
    """Sets up Celery as a background task runner for the application."""
    if app.config.get("USE_CELERY", False):
        celery.conf.broker_url = app.config["CELERY_BROKER_URL"]
        celery.conf.result_backend = app.config["CELERY_RESULT_BACKEND"]
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
    else:
        app.logger.warning("Celery is disabled!")


def _setup_db(app):
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///db.sqlite3")

    db.init_app(app)

    app.logger.warning(f"Creating database... {app.config['SQLALCHEMY_DATABASE_URI']}")
    try:
        with app.app_context():
            db.create_all()
            app.logger.warning("Database created successfully.")

            app.logger.warning("Committing session...")
            db.session.commit()
            app.logger.warning("Session committed successfully.")

            migrate.init_app(app, directory=os.path.join(app.root_path, "migrations"))
            app.logger.warning("Migration initialized successfully.")
    except Exception as e:
        app.logger.error(f"Error during database setup: {str(e)}")
        raise

    app.logger.info("Database setup completed.")


def _configure_app(app, from_env=True):
    app.config.from_pyfile("captcha.cfg.example")
    if from_env:
        _read_env_config(app)


def create_app(config_override=None, use_env_config=True) -> Flask:
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.logger = configure_logging()

    if config_override:
        app.config.update(config_override)
    _configure_app(app, use_env_config)

    app.wsgi_app = ProxyFix(app.wsgi_app)
    CORS(app,
         resource={
           r"/*": {"origins": "*"}
    })
    _setup_db(app)
    _setup_api(app)

    # Create a Celery connection
    _setup_celery(app)

    # Blueprints
    app.register_blueprint(index_bp)

    return app
