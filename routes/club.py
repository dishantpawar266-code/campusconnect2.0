import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from database import db
from models import User, Club, Department, Notice, Doubt, DoubtReply
from routes.auth import login_required, role_required
from storage import upload_file_to_storage

club_bp = Blueprint('club', __name__, url_prefix='/club')

def allowed_file(filename):
    allowed_extensions = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@club_bp.route('/dashboard')
@login_required
@role_required('club')
def dashboard():
    user = db.session.get(User, session['user_id'])
    club = user.club_profile

    # Notices published by this club
    notices = Notice.query.filter_by(club_id=club.id).order_by(Notice.created_at.desc()).all()

    # Doubts sent to this club
    doubts = Doubt.query.filter_by(club_id=club.id).order_by(Doubt.created_at.desc()).all()

    departments = Department.query.all()

    return render_template(
        'club_dashboard.html',
        user=user,
        club=club,
        notices=notices,
        doubts=doubts,
        departments=departments
    )

@club_bp.route('/notice/create', methods=['POST'])
@login_required
@role_required('club')
def create_notice():
    user = db.session.get(User, session['user_id'])
    club = user.club_profile

    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    department_id = request.form.get('department_id')
    event_date_str = request.form.get('event_date')

    department_id = int(department_id) if department_id and department_id != 'all' else None

    event_date = None
    if event_date_str:
        try:
            event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
        except ValueError:
            pass

    file = request.files.get('file')
    filename = None
    if file and allowed_file(file.filename):
        filename = upload_file_to_storage(file, prefix=f"club_notice_{club.id}")

    if title and content:
        notice = Notice(
            author_id=user.id,
            notice_type='club',
            department_id=department_id,
            club_id=club.id,
            title=title,
            content=content,
            attachment_path=filename,
            event_date=event_date
        )
        db.session.add(notice)
        db.session.commit()
        flash('Club event/notice published successfully!', 'success')
    else:
        flash('Title and Content are required.', 'danger')

    return redirect(url_for('club.dashboard'))

@club_bp.route('/doubt/reply/<int:doubt_id>', methods=['POST'])
@login_required
@role_required('club')
def reply_doubt(doubt_id):
    user = db.session.get(User, session['user_id'])
    doubt = db.session.get(Doubt, doubt_id)
    if not doubt:
        flash('Doubt query not found.', 'danger')
        return redirect(url_for('club.dashboard'))

    reply_text = request.form.get('reply_text', '').strip()

    file = request.files.get('file')
    filename = None
    if file and allowed_file(file.filename):
        filename = upload_file_to_storage(file, prefix=f"club_ans_{user.id}")

    if reply_text:
        reply = DoubtReply(doubt_id=doubt.id, responder_id=user.id, reply_text=reply_text, file_path=filename)
        db.session.add(reply)
        doubt.status = 'answered'
        db.session.commit()
        flash('Reply posted to student query!', 'success')
    else:
        flash('Reply text cannot be empty.', 'danger')

    return redirect(url_for('club.dashboard'))

@club_bp.route('/profile/update', methods=['POST'])
@login_required
@role_required('club')
def update_profile():
    user = db.session.get(User, session['user_id'])
    club = user.club_profile

    leader_name = request.form.get('leader_name', '').strip()
    description = request.form.get('description', '').strip()
    passcode = request.form.get('passcode', '').strip()

    if leader_name:
        club.leader_name = leader_name
    if description:
        club.description = description
    if passcode:
        club.passcode = passcode
        user.set_password(passcode)

    db.session.commit()
    flash('Club profile updated successfully!', 'success')
    return redirect(url_for('club.dashboard'))
