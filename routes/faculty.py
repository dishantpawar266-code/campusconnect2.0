import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Faculty, Student, Department, Note, Doubt, DoubtReply,
    Assignment, AssignmentSubmission, Notice, Quiz, QuizQuestion, QuizAttempt
)
from routes.auth import login_required, role_required

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

def allowed_file(filename):
    allowed_extensions = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@faculty_bp.route('/dashboard')
@login_required
@role_required('faculty')
def dashboard():
    user = db.session.get(User, session['user_id'])
    faculty = user.faculty_profile
    department = faculty.department

    # Data queries
    notes = Note.query.filter_by(uploader_id=user.id).order_by(Note.created_at.desc()).all()
    assignments = Assignment.query.filter_by(faculty_id=faculty.id).order_by(Assignment.created_at.desc()).all()
    notices = Notice.query.filter_by(author_id=user.id).order_by(Notice.created_at.desc()).all()
    doubts = Doubt.query.filter_by(faculty_id=faculty.id).order_by(Doubt.created_at.desc()).all()
    quizzes = Quiz.query.filter_by(faculty_id=faculty.id).order_by(Quiz.created_at.desc()).all()
    dept_students = Student.query.filter_by(department_id=department.id).all()

    departments = Department.query.all()

    return render_template(
        'faculty_dashboard.html',
        user=user,
        faculty=faculty,
        department=department,
        notes=notes,
        assignments=assignments,
        notices=notices,
        doubts=doubts,
        quizzes=quizzes,
        dept_students=dept_students,
        departments=departments
    )

# --- 1. FACULTY NOTES ---
@faculty_bp.route('/note/upload', methods=['POST'])
@login_required
@role_required('faculty')
def upload_note():
    user = db.session.get(User, session['user_id'])
    faculty = user.faculty_profile

    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()
    target_dept_id = request.form.get('department_id', faculty.department_id)
    academic_year = request.form.get('academic_year')

    year = academic_year if academic_year and academic_year != 'all' else None

    file = request.files.get('file')
    filename = None
    if file and allowed_file(file.filename):
        sec_filename = secure_filename(file.filename)
        filename = f"fac_note_{user.id}_{int(datetime.utcnow().timestamp())}_{sec_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

    if title and subject:
        note = Note(
            uploader_id=user.id,
            uploader_role='faculty',
            department_id=int(target_dept_id),
            academic_year=year,
            title=title,
            subject=subject,
            description=description,
            file_path=filename,
            is_faculty_note=True
        )
        db.session.add(note)
        db.session.commit()
        flash('Faculty study material published for targeted students!', 'success')
    else:
        flash('Title and Subject are required.', 'danger')

    return redirect(url_for('faculty.dashboard'))

# --- 2. ASSIGNMENTS MANAGEMENT ---
@faculty_bp.route('/assignment/create', methods=['POST'])
@login_required
@role_required('faculty')
def create_assignment():
    user = db.session.get(User, session['user_id'])
    faculty = user.faculty_profile

    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()
    deadline_str = request.form.get('deadline')
    max_marks = request.form.get('max_marks', 100)
    target_dept_id = request.form.get('department_id', faculty.department_id)
    academic_year = request.form.get('academic_year')

    year = academic_year if academic_year and academic_year != 'all' else None

    file = request.files.get('file')
    filename = None
    if file and allowed_file(file.filename):
        sec_filename = secure_filename(file.filename)
        filename = f"fac_asgn_{faculty.id}_{int(datetime.utcnow().timestamp())}_{sec_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

    try:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M') if 'T' in deadline_str else datetime.strptime(deadline_str, '%Y-%m-%d')
    except Exception:
        deadline = datetime.utcnow()

    if title and subject and description:
        asgn = Assignment(
            faculty_id=faculty.id,
            department_id=int(target_dept_id),
            academic_year=year,
            title=title,
            subject=subject,
            description=description,
            file_path=filename,
            deadline=deadline,
            max_marks=int(max_marks)
        )
        db.session.add(asgn)
        db.session.commit()
        flash('Assignment published for targeted students!', 'success')
    else:
        flash('Title, subject, and description are required.', 'danger')

    return redirect(url_for('faculty.dashboard'))

@faculty_bp.route('/assignment/evaluate/<int:submission_id>', methods=['POST'])
@login_required
@role_required('faculty')
def evaluate_submission(submission_id):
    submission = db.session.get(AssignmentSubmission, submission_id)
    if not submission:
        flash('Submission not found.', 'danger')
        return redirect(url_for('faculty.dashboard'))

    marks = request.form.get('marks')
    feedback = request.form.get('feedback', '').strip()

    if marks:
        submission.marks_obtained = int(marks)
    submission.feedback = feedback
    db.session.commit()

    flash('Submission evaluated successfully!', 'success')
    return redirect(url_for('faculty.dashboard'))

# --- 3. ACADEMIC NOTICES ---
@faculty_bp.route('/notice/create', methods=['POST'])
@login_required
@role_required('faculty')
def create_notice():
    user = db.session.get(User, session['user_id'])
    faculty = user.faculty_profile

    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    department_id = request.form.get('department_id')
    academic_year = request.form.get('academic_year')
    event_date_str = request.form.get('event_date')

    dept_id = int(department_id) if department_id and department_id != 'all' else None
    year = academic_year if academic_year and academic_year != 'all' else None

    event_date = None
    if event_date_str:
        try:
            event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
        except ValueError:
            pass

    file = request.files.get('file')
    filename = None
    if file and allowed_file(file.filename):
        sec_filename = secure_filename(file.filename)
        filename = f"notice_{user.id}_{int(datetime.utcnow().timestamp())}_{sec_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

    if title and content:
        notice = Notice(
            author_id=user.id,
            notice_type='academic',
            department_id=dept_id,
            academic_year=year,
            title=title,
            content=content,
            attachment_path=filename,
            event_date=event_date
        )
        db.session.add(notice)
        db.session.commit()
        flash('Official Academic Notice published!', 'success')
    else:
        flash('Title and Notice Content are required.', 'danger')

    return redirect(url_for('faculty.dashboard'))

# --- 4. STUDENT DOUBTS REPLY ---
@faculty_bp.route('/doubt/reply/<int:doubt_id>', methods=['POST'])
@login_required
@role_required('faculty')
def reply_doubt(doubt_id):
    user = db.session.get(User, session['user_id'])
    doubt = db.session.get(Doubt, doubt_id)
    if not doubt:
        flash('Doubt not found.', 'danger')
        return redirect(url_for('faculty.dashboard'))

    reply_text = request.form.get('reply_text', '').strip()

    file = request.files.get('file')
    filename = None
    if file and allowed_file(file.filename):
        sec_filename = secure_filename(file.filename)
        filename = f"doubt_ans_{user.id}_{int(datetime.utcnow().timestamp())}_{sec_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

    if reply_text:
        reply = DoubtReply(doubt_id=doubt.id, responder_id=user.id, reply_text=reply_text, file_path=filename)
        db.session.add(reply)
        doubt.status = 'answered'
        db.session.commit()
        flash('Doubt answer posted to student!', 'success')
    else:
        flash('Reply text cannot be empty.', 'danger')

    return redirect(url_for('faculty.dashboard'))

# --- 5. QUIZ CREATION & MANAGEMENT ---
@faculty_bp.route('/quiz/create', methods=['POST'])
@login_required
@role_required('faculty')
def create_quiz():
    user = db.session.get(User, session['user_id'])
    faculty = user.faculty_profile

    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    time_limit = request.form.get('time_limit_minutes', 15)
    target_dept_id = request.form.get('department_id', faculty.department_id)
    academic_year = request.form.get('academic_year')

    year = academic_year if academic_year and academic_year != 'all' else None

    q_texts = request.form.getlist('q_text[]')
    q_opts_a = request.form.getlist('q_opt_a[]')
    q_opts_b = request.form.getlist('q_opt_b[]')
    q_opts_c = request.form.getlist('q_opt_c[]')
    q_opts_d = request.form.getlist('q_opt_d[]')
    q_corrects = request.form.getlist('q_correct[]')

    if title and subject and len(q_texts) > 0:
        total_marks = len(q_texts)
        quiz = Quiz(
            faculty_id=faculty.id,
            department_id=int(target_dept_id),
            academic_year=year,
            title=title,
            subject=subject,
            time_limit_minutes=int(time_limit),
            total_marks=total_marks,
            is_active=True
        )
        db.session.add(quiz)
        db.session.flush()

        for i in range(len(q_texts)):
            if q_texts[i].strip():
                question = QuizQuestion(
                    quiz_id=quiz.id,
                    question_text=q_texts[i].strip(),
                    option_a=q_opts_a[i].strip() if i < len(q_opts_a) else '',
                    option_b=q_opts_b[i].strip() if i < len(q_opts_b) else '',
                    option_c=q_opts_c[i].strip() if i < len(q_opts_c) else '',
                    option_d=q_opts_d[i].strip() if i < len(q_opts_d) else '',
                    correct_option=q_corrects[i].strip().upper() if i < len(q_corrects) else 'A',
                    marks=1
                )
                db.session.add(question)

        db.session.commit()
        flash('Quiz created and activated for targeted students!', 'success')
    else:
        flash('Title, subject, and at least one question are required.', 'danger')

    return redirect(url_for('faculty.dashboard'))

@faculty_bp.route('/quiz/toggle/<int:quiz_id>', methods=['POST'])
@login_required
@role_required('faculty')
def toggle_quiz(quiz_id):
    user = db.session.get(User, session['user_id'])
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('faculty.dashboard'))

    if quiz.faculty_id != user.faculty_profile.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('faculty.dashboard'))

    quiz.is_active = not quiz.is_active
    db.session.commit()
    status_str = "activated" if quiz.is_active else "deactivated"
    flash(f'Quiz has been {status_str}.', 'info')
    return redirect(url_for('faculty.dashboard'))
