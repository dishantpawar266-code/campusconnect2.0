"""
CampusConnect 2.0 - Render PostgreSQL Persistent Storage Module
Manages persistent file uploads stored directly inside Render PostgreSQL as binary objects.
Falls back to local static directory if needed.
"""

import io
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import send_file, send_from_directory, current_app, abort, redirect
from database import db
from models import UploadedFile

def upload_file_to_storage(file_obj, prefix="file"):
    """
    Uploads a Werkzeug FileStorage object to Render PostgreSQL database as persistent binary data.
    Returns the unique stored filename string.
    """
    if not file_obj or not file_obj.filename:
        return None

    orig_filename = secure_filename(file_obj.filename)
    unique_filename = f"{prefix}_{int(datetime.utcnow().timestamp())}_{orig_filename}"

    file_bytes = file_obj.read()
    mimetype = file_obj.mimetype or 'application/octet-stream'

    # Save to PostgreSQL Database
    try:
        existing = UploadedFile.query.filter_by(filename=unique_filename).first()
        if not existing:
            file_record = UploadedFile(
                filename=unique_filename,
                original_filename=orig_filename,
                mimetype=mimetype,
                file_data=file_bytes
            )
            db.session.add(file_record)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"PostgreSQL file storage notice: {e}")

    # Local fallback copy
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'static', 'uploads'))
        os.makedirs(upload_folder, exist_ok=True)
        local_path = os.path.join(upload_folder, unique_filename)
        with open(local_path, 'wb') as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"Local file system notice: {e}")
    finally:
        file_obj.seek(0)

    return unique_filename

def get_file_download_response(filename):
    """
    Returns a Flask response for downloading/viewing a file.
    Fetches binary content from Render PostgreSQL database or falls back to local static folder.
    """
    if not filename:
        abort(404)

    if filename.startswith('http://') or filename.startswith('https://'):
        return redirect(filename)

    # 1. Primary: Fetch persistent file binary content from Render PostgreSQL
    try:
        file_record = UploadedFile.query.filter_by(filename=filename).first()
        if file_record and file_record.file_data:
            return send_file(
                io.BytesIO(file_record.file_data),
                mimetype=file_record.mimetype or 'application/octet-stream',
                as_attachment=True,
                download_name=file_record.original_filename or filename
            )
    except Exception as e:
        print(f"PostgreSQL file download notice: {e}")

    # 2. Fallback: Serve from local UPLOAD_FOLDER
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'static', 'uploads'))
    local_path = os.path.join(upload_folder, filename)
    if os.path.exists(local_path):
        return send_from_directory(upload_folder, filename, as_attachment=True)

    abort(404)
