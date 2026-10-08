import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url

db = SQLAlchemy()


def ensure_mysql_database(database_url):
    url = make_url(database_url)
    if url.get_backend_name() != "mysql":
        return
    if not url.database:
        raise ValueError("DATABASE_URL must include a MySQL database name")

    server_url = URL.create(
        url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        query=url.query,
    )
    server_engine = create_engine(server_url)
    try:
        database_name = server_engine.dialect.identifier_preparer.quote_identifier(url.database)
        with server_engine.begin() as connection:
            connection.exec_driver_sql(f"CREATE DATABASE IF NOT EXISTS {database_name}")
    finally:
        server_engine.dispose()


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/certificates"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["CERTIFICATE_DIR"] = os.getenv("CERTIFICATE_DIR", "generated")
    app.config["MAX_RECIPIENTS"] = 500
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        from app import models  # noqa: F401
        ensure_mysql_database(app.config["SQLALCHEMY_DATABASE_URI"])
        db.create_all()

    from app.routes import api
    app.register_blueprint(api, url_prefix="/api")
    return app
