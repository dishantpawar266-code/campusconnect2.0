import os
import shutil

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

IS_SERVERLESS = 'NETLIFY' in os.environ or 'AWS_LAMBDA_FUNCTION_NAME' in os.environ or 'LAMBDA_TASK_ROOT' in os.environ

if IS_SERVERLESS:
    db_path = '/tmp/campus_connect.db'
    original_db = os.path.join(BASE_DIR, 'campus_connect.db')
    if not os.path.exists(db_path) and os.path.exists(original_db):
        try:
            shutil.copy2(original_db, db_path)
        except Exception as e:
            print(f"Error copying DB to /tmp: {e}")
    upload_folder = '/tmp/uploads'
    os.makedirs(upload_folder, exist_ok=True)
else:
    db_path = os.path.join(BASE_DIR, 'campus_connect.db')
    upload_folder = os.path.join(BASE_DIR, 'static', 'uploads')

database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Fix legacy 'postgres://' URLs from cloud providers to 'postgresql://' required by SQLAlchemy 1.4+
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
else:
    database_url = f'sqlite:///{db_path}'

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'campus_connect_secret_key_2026_rcpit')
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = upload_folder
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file upload size


