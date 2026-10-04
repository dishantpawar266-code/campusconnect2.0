import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Student, Faculty, Club, Department, Task, Note, NoteShare,
    Friendship, Doubt, DoubtReply, Assignment, AssignmentSubmission,
    Notice, Quiz, QuizQuestion, QuizAttempt, ExternalResource
)
from routes.auth import login_required, role_required

student_bp = Blueprint('student', __name__, url_prefix='/student')

def allowed_file(filename):
    allowed_extensions = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@student_bp.route('/dashboard')
@login_required
@role_required('student')
def dashboard():
    user = db.session.get(User, session['user_id'])
    student = user.student_profile
    department = student.department

    # Data queries for Student
    tasks = Task.query.filter_by(student_id=student.id).order_by(Task.is_completed.asc(), Task.due_date.asc()).all()

    # Notes: Targeted to Student's Dept + Year (or All)
    faculty_notes = Note.query.filter_by(department_id=department.id, is_faculty_note=True).filter(
        (Note.academic_year == None) | (Note.academic_year == student.academic_year)
    ).order_by(Note.created_at.desc()).all()

    own_notes = Note.query.filter_by(uploader_id=user.id).order_by(Note.created_at.desc()).all()

    shared_note_ids = [s.note_id for s in NoteShare.query.filter_by(shared_with_id=user.id).all()]
    shared_notes = Note.query.filter(Note.id.in_(shared_note_ids)).all() if shared_note_ids else []

    # Faculty members in student department
    dept_faculty = Faculty.query.filter_by(department_id=department.id).all()

    # Student Doubts
    doubts = Doubt.query.filter_by(student_id=student.id).order_by(Doubt.created_at.desc()).all()

    # Department Assignments
    assignments = Assignment.query.filter_by(department_id=department.id).filter(
        (Assignment.academic_year == None) | (Assignment.academic_year == student.academic_year)
    ).order_by(Assignment.deadline.asc()).all()

    student_submissions = {sub.assignment_id: sub for sub in AssignmentSubmission.query.filter_by(student_id=student.id).all()}

    # Department & Club Notices
    academic_notices = Notice.query.filter_by(notice_type='academic').filter(
        (Notice.department_id == None) | (Notice.department_id == department.id)
    ).filter(
        (Notice.academic_year == None) | (Notice.academic_year == student.academic_year)
    ).order_by(Notice.created_at.desc()).all()

    club_notices = Notice.query.filter_by(notice_type='club').order_by(Notice.created_at.desc()).all()

    # Active Quizzes
    active_quizzes = Quiz.query.filter_by(department_id=department.id, is_active=True).filter(
        (Quiz.academic_year == None) | (Quiz.academic_year == student.academic_year)
    ).order_by(Quiz.created_at.desc()).all()

    quiz_attempts = {att.quiz_id: att for att in QuizAttempt.query.filter_by(student_id=student.id).all()}

    # Clubs
    clubs = Club.query.all()

    # External Resources
    external_resources = ExternalResource.query.all()

    # Classmates in same department
    classmates = Student.query.filter(
        Student.department_id == department.id,
        Student.id != student.id
    ).all()

    return render_template(
        'student_dashboard.html',
        user=user,
        student=student,
        department=department,
        tasks=tasks,
        faculty_notes=faculty_notes,
        own_notes=own_notes,
        shared_notes=shared_notes,
        dept_faculty=dept_faculty,
        doubts=doubts,
        assignments=assignments,
        student_submissions=student_submissions,
        academic_notices=academic_notices,
        club_notices=club_notices,
        active_quizzes=active_quizzes,
        quiz_attempts=quiz_attempts,
        clubs=clubs,
        external_resources=external_resources,
        classmates=classmates
    )

# --- 1. TASK PLANNER ROUTES ---
@student_bp.route('/task/create', methods=['POST'])
@login_required
@role_required('student')
def create_task():
    user = db.session.get(User, session['user_id'])
    student = user.student_profile

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', 'General')
    due_date_str = request.form.get('due_date')

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        except ValueError:
            pass

    if title:
        task = Task(student_id=student.id, title=title, description=description, category=category, due_date=due_date)
        db.session.add(task)
        db.session.commit()
        flash('Task added to your planner!', 'success')
    else:
        flash('Task title is required.', 'danger')

    return redirect(url_for('student.dashboard'))

@student_bp.route('/task/toggle/<int:task_id>', methods=['POST'])
@login_required
@role_required('student')
def toggle_task(task_id):
    user = db.session.get(User, session['user_id'])
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Not found'}), 404

    if task.student_id != user.student_profile.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    task.is_completed = not task.is_completed
    db.session.commit()
    return jsonify({'success': True, 'is_completed': task.is_completed})

@student_bp.route('/task/delete/<int:task_id>', methods=['POST'])
@login_required
@role_required('student')
def delete_task(task_id):
    user = db.session.get(User, session['user_id'])
    task = db.session.get(Task, task_id)
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('student.dashboard'))

    if task.student_id != user.student_profile.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('student.dashboard'))

    db.session.delete(task)
    db.session.commit()
    flash('Task removed.', 'info')
    return redirect(url_for('student.dashboard'))

# --- 2. NOTES ROUTES ---
@student_bp.route('/note/upload', methods=['POST'])
@login_required
@role_required('student')
def upload_note():
    user = db.session.get(User, session['user_id'])
    student = user.student_profile

    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()
    file = request.files.get('file')

    filename = None
    if file and allowed_file(file.filename):
        sec_filename = secure_filename(file.filename)
        filename = f"student_{user.id}_{int(datetime.utcnow().timestamp())}_{sec_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

    if title and subject:
        note = Note(
            uploader_id=user.id,
            uploader_role='student',
            department_id=student.department_id,
            academic_year=student.academic_year,
            title=title,
            subject=subject,
            description=description,
            file_path=filename,
            is_faculty_note=False
        )
        db.session.add(note)
        db.session.commit()
        flash('Note uploaded successfully!', 'success')
    else:
        flash('Title and Subject are required for notes.', 'danger')

    return redirect(url_for('student.dashboard'))

@student_bp.route('/note/share', methods=['POST'])
@login_required
@role_required('student')
def share_note():
    user = db.session.get(User, session['user_id'])
    note_id = request.form.get('note_id')
    recipient_student_id = request.form.get('recipient_student_id')

    note = db.session.get(Note, int(note_id)) if note_id else None
    recipient_student = db.session.get(Student, int(recipient_student_id)) if recipient_student_id else None

    if not note or not recipient_student:
        flash('Invalid note or student selected.', 'danger')
        return redirect(url_for('student.dashboard'))

    if note.uploader_id != user.id:
        flash('You can only share notes you uploaded.', 'danger')
        return redirect(url_for('student.dashboard'))

    existing_share = NoteShare.query.filter_by(note_id=note.id, shared_with_id=recipient_student.user_id).first()
    if not existing_share:
        share = NoteShare(note_id=note.id, shared_by_id=user.id, shared_with_id=recipient_student.user_id)
        db.session.add(share)
        db.session.commit()
        flash(f'Note shared with {recipient_student.user.full_name}!', 'success')
    else:
        flash('Note is already shared with this student.', 'info')

    return redirect(url_for('student.dashboard'))

# --- 3. DOUBT ROUTES ---
@student_bp.route('/doubt/submit', methods=['POST'])
@login_required
@role_required('student')
def submit_doubt():
    user = db.session.get(User, session['user_id'])
    student = user.student_profile

    target_type = request.form.get('target_type', 'faculty')
    title = request.form.get('title', '').strip()
    subject = request.form.get('subject', '').strip()
    question = request.form.get('question', '').strip()

    faculty_id = request.form.get('faculty_id') if target_type == 'faculty' else None
    club_id = request.form.get('club_id') if target_type == 'club' else None

    file = request.files.get('file')
    filename = None
    if file and allowed_file(file.filename):
        sec_filename = secure_filename(file.filename)
        filename = f"doubt_{user.id}_{int(datetime.utcnow().timestamp())}_{sec_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

    if title and question:
        doubt = Doubt(
            student_id=student.id,
            faculty_id=int(faculty_id) if faculty_id else None,
            club_id=int(club_id) if club_id else None,
            target_type=target_type,
            subject=subject,
            title=title,
            question=question,
            file_path=filename
        )
        db.session.add(doubt)
        db.session.commit()
        flash('Your doubt has been submitted successfully!', 'success')
    else:
        flash('Title and Doubt details are required.', 'danger')

    return redirect(url_for('student.dashboard'))

@student_bp.route('/doubt/reply/<int:doubt_id>', methods=['POST'])
@login_required
@role_required('student')
def reply_doubt(doubt_id):
    user = db.session.get(User, session['user_id'])
    doubt = db.session.get(Doubt, doubt_id)
    if not doubt:
        flash('Doubt thread not found.', 'danger')
        return redirect(url_for('student.dashboard'))

    reply_text = request.form.get('reply_text', '').strip()

    if doubt.student_id != user.student_profile.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('student.dashboard'))

    if reply_text:
        reply = DoubtReply(doubt_id=doubt.id, responder_id=user.id, reply_text=reply_text)
        db.session.add(reply)
        db.session.commit()
        flash('Follow-up reply added.', 'success')

    return redirect(url_for('student.dashboard'))

# --- 4. ASSIGNMENT SUBMISSION ---
@student_bp.route('/assignment/submit/<int:assignment_id>', methods=['POST'])
@login_required
@role_required('student')
def submit_assignment(assignment_id):
    user = db.session.get(User, session['user_id'])
    student = user.student_profile
    assignment = db.session.get(Assignment, assignment_id)

    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('student.dashboard'))

    submission_text = request.form.get('submission_text', '').strip()
    file = request.files.get('file')

    filename = None
    if file and allowed_file(file.filename):
        sec_filename = secure_filename(file.filename)
        filename = f"asgn_sub_{student.id}_{assignment_id}_{int(datetime.utcnow().timestamp())}_{sec_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

    existing_sub = AssignmentSubmission.query.filter_by(assignment_id=assignment.id, student_id=student.id).first()
    if existing_sub:
        existing_sub.submission_text = submission_text
        if filename:
            existing_sub.file_path = filename
        existing_sub.submitted_at = datetime.utcnow()
        flash('Assignment submission updated!', 'success')
    else:
        sub = AssignmentSubmission(
            assignment_id=assignment.id,
            student_id=student.id,
            submission_text=submission_text,
            file_path=filename
        )
        db.session.add(sub)
        flash('Assignment submitted successfully!', 'success')

    db.session.commit()
    return redirect(url_for('student.dashboard'))

# --- 5. QUIZ ATTEMPT & RESULTS ---
@student_bp.route('/quiz/attempt/<int:quiz_id>')
@login_required
@role_required('student')
def attempt_quiz(quiz_id):
    user = db.session.get(User, session['user_id'])
    student = user.student_profile
    quiz = db.session.get(Quiz, quiz_id)

    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('student.dashboard'))

    existing_attempt = QuizAttempt.query.filter_by(quiz_id=quiz.id, student_id=student.id).first()
    if existing_attempt:
        flash('You have already submitted this quiz.', 'info')
        return redirect(url_for('student.quiz_results', attempt_id=existing_attempt.id))

    return render_template('quiz_attempt.html', quiz=quiz, user=user, student=student)

@student_bp.route('/quiz/submit/<int:quiz_id>', methods=['POST'])
@login_required
@role_required('student')
def submit_quiz(quiz_id):
    user = db.session.get(User, session['user_id'])
    student = user.student_profile
    quiz = db.session.get(Quiz, quiz_id)

    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('student.dashboard'))

    existing_attempt = QuizAttempt.query.filter_by(quiz_id=quiz.id, student_id=student.id).first()
    if existing_attempt:
        return redirect(url_for('student.quiz_results', attempt_id=existing_attempt.id))

    score = 0
    total_possible = 0
    details = {}

    for question in quiz.questions:
        total_possible += question.marks
        user_answer = request.form.get(f'question_{question.id}')
        details[str(question.id)] = user_answer
        if user_answer and user_answer.upper() == question.correct_option.upper():
            score += question.marks

    import json
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        student_id=student.id,
        score=score,
        total_possible=total_possible,
        details_json=json.dumps(details)
    )
    db.session.add(attempt)
    db.session.commit()

    flash(f'Quiz Submitted! You scored {score}/{total_possible}.', 'success')
    return redirect(url_for('student.quiz_results', attempt_id=attempt.id))

@student_bp.route('/quiz/results/<int:attempt_id>')
@login_required
def quiz_results(attempt_id):
    user = db.session.get(User, session['user_id'])
    attempt = db.session.get(QuizAttempt, attempt_id)
    if not attempt:
        flash('Attempt result not found.', 'danger')
        return redirect(url_for('student.dashboard'))

    quiz = attempt.quiz

    import json
    user_answers = json.loads(attempt.details_json) if attempt.details_json else {}

    return render_template('quiz_results.html', attempt=attempt, quiz=quiz, user_answers=user_answers, user=user)

# --- FILE DOWNLOAD ROUTE ---
@student_bp.route('/download/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
