import os
import sys
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, abort, current_app
from database import db
from models import (
    User, Student, Faculty, Club, Department, Task, Note, NoteShare,
    Friendship, Doubt, DoubtReply, Assignment, AssignmentSubmission,
    Notice, Quiz, QuizQuestion, QuizAttempt, ExternalResource
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Backend session check
        if not session.get('user_id') or session.get('role') != 'admin' or not session.get('admin_logged_in'):
            flash('Admin access required. Please authenticate as Admin.', 'danger')
            return redirect(url_for('admin.login'))
        
        # 2. Server-side DB verification to prevent tampering
        user = db.session.get(User, session['user_id'])
        if not user or user.role != 'admin':
            session.clear()
            flash('Unauthorized access: Developer Admin privileges required.', 'danger')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
def index():
    if session.get('user_id') and session.get('role') == 'admin' and session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.login'))


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id') and session.get('role') == 'admin' and session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.role != 'admin':
                flash('Access Denied: Account is not an authorized administrator.', 'danger')
                return render_template('admin/login.html')

            session['user_id'] = user.id
            session['role'] = 'admin'
            session['admin_logged_in'] = True
            session['user_name'] = user.full_name
            flash(f'Welcome back, Developer Admin ({user.full_name})!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials. Access Denied.', 'danger')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    session.pop('admin_logged_in', None)
    session.pop('user_name', None)
    flash('Developer Admin logged out safely.', 'info')
    return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_users = User.query.count()
    total_students = Student.query.count()
    total_faculty = Faculty.query.count()
    total_clubs = Club.query.count()
    total_admins = User.query.filter_by(role='admin').count()

    total_notes = Note.query.count()
    total_assignments = Assignment.query.count()
    total_notices = Notice.query.count()
    total_doubts = Doubt.query.count()
    total_tasks = Task.query.count()

    departments = Department.query.all()
    dept_stats = []
    for dept in departments:
        st_count = Student.query.filter_by(department_id=dept.id).count()
        fac_count = Faculty.query.filter_by(department_id=dept.id).count()
        dept_stats.append({
            'dept': dept,
            'students_count': st_count,
            'faculty_count': fac_count,
            'total_dept_users': st_count + fac_count
        })

    recent_users = User.query.order_by(User.created_at.desc()).limit(8).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_students=total_students,
        total_faculty=total_faculty,
        total_clubs=total_clubs,
        total_admins=total_admins,
        total_notes=total_notes,
        total_assignments=total_assignments,
        total_notices=total_notices,
        total_doubts=total_doubts,
        total_tasks=total_tasks,
        dept_stats=dept_stats,
        recent_users=recent_users
    )


@admin_bp.route('/users')
@admin_required
def users():
    search_q = request.args.get('q', '').strip()
    role_filter = request.args.get('role', 'all').strip()
    dept_filter = request.args.get('department_id', 'all').strip()
    sort_by = request.args.get('sort', 'newest').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 15

    query = User.query

    if search_q:
        query = query.filter(
            (User.full_name.ilike(f'%{search_q}%')) |
            (User.email.ilike(f'%{search_q}%'))
        )

    if role_filter and role_filter != 'all':
        query = query.filter(User.role == role_filter)

    if dept_filter and dept_filter != 'all':
        dept_id = int(dept_filter)
        student_user_ids = [s.user_id for s in Student.query.filter_by(department_id=dept_id).all()]
        faculty_user_ids = [f.user_id for f in Faculty.query.filter_by(department_id=dept_id).all()]
        club_user_ids = [c.user_id for c in Club.query.filter_by(department_id=dept_id).all()]
        all_target_ids = list(set(student_user_ids + faculty_user_ids + club_user_ids))
        query = query.filter(User.id.in_(all_target_ids))

    if sort_by == 'oldest':
        query = query.order_by(User.created_at.asc())
    else:
        query = query.order_by(User.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users_list = pagination.items

    departments = Department.query.all()

    return render_template(
        'admin/users.html',
        users=users_list,
        pagination=pagination,
        search_q=search_q,
        role_filter=role_filter,
        dept_filter=dept_filter,
        sort_by=sort_by,
        departments=departments
    )


@admin_bp.route('/students')
@admin_required
def students():
    search_q = request.args.get('q', '').strip()
    dept_filter = request.args.get('department_id', 'all').strip()
    page = request.args.get('page', 1, type=int)

    query = Student.query.join(User)

    if search_q:
        query = query.filter(
            (User.full_name.ilike(f'%{search_q}%')) |
            (User.email.ilike(f'%{search_q}%')) |
            (Student.roll_number.ilike(f'%{search_q}%'))
        )

    if dept_filter and dept_filter != 'all':
        query = query.filter(Student.department_id == int(dept_filter))

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    students_list = pagination.items
    departments = Department.query.all()

    return render_template(
        'admin/students.html',
        students=students_list,
        pagination=pagination,
        search_q=search_q,
        dept_filter=dept_filter,
        departments=departments
    )


@admin_bp.route('/faculty')
@admin_required
def faculty():
    search_q = request.args.get('q', '').strip()
    dept_filter = request.args.get('department_id', 'all').strip()
    page = request.args.get('page', 1, type=int)

    query = Faculty.query.join(User)

    if search_q:
        query = query.filter(
            (User.full_name.ilike(f'%{search_q}%')) |
            (User.email.ilike(f'%{search_q}%')) |
            (Faculty.designation.ilike(f'%{search_q}%')) |
            (Faculty.specialization.ilike(f'%{search_q}%'))
        )

    if dept_filter and dept_filter != 'all':
        query = query.filter(Faculty.department_id == int(dept_filter))

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    faculty_list = pagination.items
    departments = Department.query.all()

    return render_template(
        'admin/faculty.html',
        faculty_list=faculty_list,
        pagination=pagination,
        search_q=search_q,
        dept_filter=dept_filter,
        departments=departments
    )


@admin_bp.route('/clubs')
@admin_required
def clubs():
    search_q = request.args.get('q', '').strip()
    category_filter = request.args.get('category', 'all').strip()
    page = request.args.get('page', 1, type=int)

    query = Club.query.join(User)

    if search_q:
        query = query.filter(
            (Club.name.ilike(f'%{search_q}%')) |
            (User.email.ilike(f'%{search_q}%')) |
            (Club.leader_name.ilike(f'%{search_q}%'))
        )

    if category_filter and category_filter != 'all':
        query = query.filter(Club.category == category_filter)

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    clubs_list = pagination.items

    return render_template(
        'admin/clubs.html',
        clubs=clubs_list,
        pagination=pagination,
        search_q=search_q,
        category_filter=category_filter
    )


@admin_bp.route('/departments')
@admin_required
def departments():
    depts = Department.query.order_by(Department.id.asc()).all()
    dept_details = []

    for d in depts:
        st_count = Student.query.filter_by(department_id=d.id).count()
        fac_count = Faculty.query.filter_by(department_id=d.id).count()
        club_count = Club.query.filter_by(department_id=d.id).count()
        notes_count = Note.query.filter_by(department_id=d.id).count()
        asgn_count = Assignment.query.filter_by(department_id=d.id).count()
        notice_count = Notice.query.filter_by(department_id=d.id).count()

        dept_details.append({
            'department': d,
            'students_count': st_count,
            'faculty_count': fac_count,
            'clubs_count': club_count,
            'notes_count': notes_count,
            'assignments_count': asgn_count,
            'notices_count': notice_count,
            'total_users': st_count + fac_count
        })

    return render_template('admin/departments.html', dept_details=dept_details)


@admin_bp.route('/notes')
@admin_required
def notes():
    search_q = request.args.get('q', '').strip()
    dept_filter = request.args.get('department_id', 'all').strip()
    role_filter = request.args.get('role', 'all').strip()
    page = request.args.get('page', 1, type=int)

    query = Note.query

    if search_q:
        query = query.filter(
            (Note.title.ilike(f'%{search_q}%')) |
            (Note.subject.ilike(f'%{search_q}%'))
        )

    if dept_filter and dept_filter != 'all':
        query = query.filter(Note.department_id == int(dept_filter))

    if role_filter and role_filter != 'all':
        query = query.filter(Note.uploader_role == role_filter)

    pagination = query.order_by(Note.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    notes_list = pagination.items
    departments = Department.query.all()

    return render_template(
        'admin/notes.html',
        notes=notes_list,
        pagination=pagination,
        search_q=search_q,
        dept_filter=dept_filter,
        role_filter=role_filter,
        departments=departments
    )


@admin_bp.route('/assignments')
@admin_required
def assignments():
    search_q = request.args.get('q', '').strip()
    dept_filter = request.args.get('department_id', 'all').strip()
    page = request.args.get('page', 1, type=int)

    query = Assignment.query

    if search_q:
        query = query.filter(
            (Assignment.title.ilike(f'%{search_q}%')) |
            (Assignment.subject.ilike(f'%{search_q}%'))
        )

    if dept_filter and dept_filter != 'all':
        query = query.filter(Assignment.department_id == int(dept_filter))

    pagination = query.order_by(Assignment.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    assignments_list = pagination.items
    departments = Department.query.all()

    return render_template(
        'admin/assignments.html',
        assignments=assignments_list,
        pagination=pagination,
        search_q=search_q,
        dept_filter=dept_filter,
        departments=departments
    )


@admin_bp.route('/notices')
@admin_required
def notices():
    search_q = request.args.get('q', '').strip()
    type_filter = request.args.get('type', 'all').strip()
    page = request.args.get('page', 1, type=int)

    query = Notice.query

    if search_q:
        query = query.filter(
            (Notice.title.ilike(f'%{search_q}%')) |
            (Notice.content.ilike(f'%{search_q}%'))
        )

    if type_filter and type_filter != 'all':
        query = query.filter(Notice.notice_type == type_filter)

    pagination = query.order_by(Notice.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    notices_list = pagination.items

    return render_template(
        'admin/notices.html',
        notices=notices_list,
        pagination=pagination,
        search_q=search_q,
        type_filter=type_filter
    )


@admin_bp.route('/doubts')
@admin_required
def doubts():
    search_q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all').strip()
    page = request.args.get('page', 1, type=int)

    query = Doubt.query

    if search_q:
        query = query.filter(
            (Doubt.title.ilike(f'%{search_q}%')) |
            (Doubt.question.ilike(f'%{search_q}%')) |
            (Doubt.subject.ilike(f'%{search_q}%'))
        )

    if status_filter and status_filter != 'all':
        query = query.filter(Doubt.status == status_filter)

    pagination = query.order_by(Doubt.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    doubts_list = pagination.items

    return render_template(
        'admin/doubts.html',
        doubts=doubts_list,
        pagination=pagination,
        search_q=search_q,
        status_filter=status_filter
    )


@admin_bp.route('/system')
@admin_required
def system():
    table_counts = {
        'Users': User.query.count(),
        'Students': Student.query.count(),
        'Faculty': Faculty.query.count(),
        'Clubs': Club.query.count(),
        'Departments': Department.query.count(),
        'Tasks': Task.query.count(),
        'Notes': Note.query.count(),
        'NoteShares': NoteShare.query.count(),
        'Friendships': Friendship.query.count(),
        'Doubts': Doubt.query.count(),
        'DoubtReplies': DoubtReply.query.count(),
        'Assignments': Assignment.query.count(),
        'AssignmentSubmissions': AssignmentSubmission.query.count(),
        'Notices': Notice.query.count(),
        'Quizzes': Quiz.query.count(),
        'QuizQuestions': QuizQuestion.query.count(),
        'QuizAttempts': QuizAttempt.query.count(),
        'ExternalResources': ExternalResource.query.count()
    }

    env_info = {
        'Python Version': sys.version.split(' ')[0],
        'Database Engine': str(db.engine.url.drivername),
        'Server Time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'Upload Folder': current_app.config['UPLOAD_FOLDER']
    }

    return render_template('admin/system.html', table_counts=table_counts, env_info=env_info)
