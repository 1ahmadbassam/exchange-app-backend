import datetime
import os

from dotenv import load_dotenv
from flask import Flask
from flask_apscheduler import APScheduler
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy

load_dotenv()
try:
    from DB_CONFIG import db_config
except ImportError:
    DB_CONFIG = (f'mysql+pymysql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}'
                 f':{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}')

app = Flask(__name__)
PORT = os.getenv('PORT')
app.config['SQLALCHEMY_DATABASE_URI'] = DB_CONFIG
app.config['APP_NAME'] = "LBP Exchange Tracker"
SECRET_KEY = os.getenv("SECRET_KEY")
SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT")
CORS(app)
db = SQLAlchemy(app)
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)
tz = datetime.timezone.utc
app.config['SCHEDULER_API_ENABLED'] = True
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS')
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

MARKETAUX_KEY = os.getenv('MARKETAUX_KEY')
GEMINI_KEY = os.getenv('GEMINI_KEY')

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN')
