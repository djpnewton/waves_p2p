import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail_sendgrid import MailSendGrid

import config
cfg = config.read_cfg()

# Create Flask application
app = Flask(__name__)
app.config.from_pyfile("flask_config.py")
app.config.from_pyfile("flask_config_secret.py")
if os.getenv("DEBUG"):
    app.config["DEBUG"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = cfg.db_filename
if os.getenv("SESSION_KEY"):
    app.config["SECRET_KEY"] = os.getenv("SESSION_KEY")
if os.getenv("PASSWORD_SALT"):
    app.config["SECURITY_PASSWORD_SALT"] = os.getenv("PASSWORD_SALT")
if os.getenv("SENDGRID_API_KEY"):
    app.config["MAIL_SENDGRID_API_KEY"] = os.getenv("SENDGRID_API_KEY")
if os.getenv("SERVER_NAME"):
    app.config["SERVER_NAME"] = os.getenv("SERVER_NAME")
app.config["ASSET_ID"] = "CgUrFtinLXEbJwJVjwwcppk4Vpz1nMmR3H5cQaDcUcfe"
if os.getenv("PRODUCTION"):
    app.config["TESTNET"] = False
    app.config["ASSET_ID"] = "9R3iLi4qGLVWKc16Tg98gmRvgg1usGEYd7SgC1W5D6HB"
if os.getenv("SERVER_NAME"):
    app.config["SERVER_NAME"] = os.getenv("SERVER_NAME")
if os.getenv("URL_SCHEME"):
    app.config["URL_SCHEME"] = os.getenv("URL_SCHEME")
db = SQLAlchemy(app)
mail = MailSendGrid(app)
