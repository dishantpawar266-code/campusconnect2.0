"""
CampusConnect 2.0 - Supabase Storage Helper Module
Manages persistent file uploads to Supabase Storage buckets.
Falls back to local/tmp filesystem storage if Supabase credentials are not provided.
"""

import os
import requests
from werkzeug.utils import secure_filename
from datetime import datetime

SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '').strip()
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'campusconnect-files').strip()

def is_supabase_storage_enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)

def upload_file_to_storage(file_obj, prefix="file"):
    """
    Uploads a Werkzeug FileStorage object to Supabase Storage if configured.
    Falls back to local/tmp filesystem upload.
    Returns the stored unique filename.
    """
    if not file_obj or not file_obj.filename:
        return None

    orig_filename = secure_filename(file_obj.filename)
    unique_filename = f"{prefix}_{int(datetime.utcnow().timestamp())}_{orig_filename}"

    if is_supabase_storage_enabled():
        try:
            file_bytes = file_obj.read()
            content_type = file_obj.mimetype or 'application/octet-stream'

            endpoint = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{unique_filename}"
            headers = {
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "apiKey": SUPABASE_KEY,
                "Content-Type": content_type,
                "x-upsert": "true"
            }

            res = requests.post(endpoint, data=file_bytes, headers=headers, timeout=10)

            if res.status_code in (200, 201):
                return unique_filename
            else:
                # Attempt to create public bucket if it does not exist
                create_bucket_endpoint = f"{SUPABASE_URL}/storage/v1/bucket"
                bucket_payload = {"id": SUPABASE_STORAGE_BUCKET, "name": SUPABASE_STORAGE_BUCKET, "public": True}
                requests.post(create_bucket_endpoint, json=bucket_payload, headers=headers, timeout=5)

                # Retry upload
                res_retry = requests.post(endpoint, data=file_bytes, headers=headers, timeout=10)
                if res_retry.status_code in (200, 201):
                    return unique_filename
                else:
                    print(f"Supabase Storage Upload Warning ({res_retry.status_code}): {res_retry.text}")
        except Exception as e:
            print(f"Supabase Storage Upload Exception: {e}")
        finally:
            file_obj.seek(0)

    # Local / Tmp Filesystem Fallback
    from flask import current_app
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp/uploads')
    os.makedirs(upload_folder, exist_ok=True)
    local_path = os.path.join(upload_folder, unique_filename)
    file_obj.save(local_path)
    return unique_filename

def get_file_download_response(filename):
    """
    Returns a Flask response for downloading/viewing a file.
    Redirects to Supabase Storage public URL if enabled, or serves from local UPLOAD_FOLDER.
    """
    from flask import redirect, send_from_directory, current_app, abort

    if not filename:
        abort(404)

    if filename.startswith('http://') or filename.startswith('https://'):
        return redirect(filename)

    if is_supabase_storage_enabled():
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{filename}"
        return redirect(public_url)

    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp/uploads')
    local_path = os.path.join(upload_folder, filename)
    if os.path.exists(local_path):
        return send_from_directory(upload_folder, filename, as_attachment=True)

    abort(404)
