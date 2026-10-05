import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

db_path = os.path.join(BASE_DIR, 'campus_connect.db')
upload_folder = os.path.join(BASE_DIR, 'static', 'uploads')

raw_db_url = os.environ.get('DATABASE_URL', '').strip()
if raw_db_url:
    # Convert legacy 'postgres://' URLs from cloud providers to 'postgresql://' required by SQLAlchemy 1.4+
    if raw_db_url.startswith("postgres://"):
        database_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    else:
        database_url = raw_db_url
else:
    database_url = f'sqlite:///{db_path}'

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'campus_connect_secret_key_2026_rcpit')
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    } if database_url and database_url.startswith("postgresql") else {}
    UPLOAD_FOLDER = upload_folder
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file upload size



