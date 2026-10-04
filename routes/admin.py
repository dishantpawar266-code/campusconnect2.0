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
        if not session.get('admin_logged_in') or session.get('role') != 'admin':
            flash('Admin access required. Please authenticate as Developer Admin.', 'danger')
            return redirect(url_for('admin.login'))
        
        # 2. Server-side DB verification if user_id is in session
        user_id = session.get('user_id')
        if user_id:
            user = db.session.get(User, user_id)
            if user and user.role != 'admin':
                session.clear()
                flash('Unauthorized access: Developer Admin privileges required.', 'danger')
                return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
def index():
    if session.get('admin_logged_in') and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('admin.login'))


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in') and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        env_admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin@Campus2026!')
        env_admin_email = os.environ.get('ADMIN_EMAIL', 'admin@rcpit.ac.in').lower().strip()

        user = User.query.filter_by(email=email).first() if email else None
        if not user:
            user = User.query.filter_by(role='admin').first()

        is_authenticated = False
        if password and password == env_admin_password:
            is_authenticated = True
        elif user and user.check_password(password) and user.role == 'admin':
            is_authenticated = True

        if is_authenticated:
            if not user:
                user = User.query.filter_by(role='admin').first()

            session.permanent = True
            session['user_id'] = user.id if user else 1
            session['role'] = 'admin'
            session['admin_logged_in'] = True
            session['user_name'] = user.full_name if user else 'Developer Admin'
            session['admin_email'] = email or (user.email if user else env_admin_email)
            flash('Welcome back to Developer Admin Console!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid Developer Admin credentials. Access Denied.', 'danger')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    session.pop('admin_logged_in', None)
    session.pop('user_name', None)
    session.pop('admin_email', None)
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
    total_quizzes = Quiz.query.count()

    departments = Department.query.all()
    dept_stats = []
    for dept in departments:
        st_count = Student.query.filter_by(department_id=dept.id).count()
        fac_count = Faculty.query.filter_by(department_id=dept.id).count()
        club_count = Club.query.filter_by(department_id=dept.id).count()
        dept_stats.append({
            'dept': dept,
            'students_count': st_count,
            'faculty_count': fac_count,
            'clubs_count': club_count,
            'total_dept_users': st_count + fac_count + club_count
        })

    recent_users = User.query.order_by(User.created_at.desc()).limit(8).all()

    # Create activity feed
    recent_activity = []
    for u in recent_users:
        recent_activity.append({
            'timestamp': u.created_at,
            'type': 'User Registered',
            'details': f"{u.full_name} ({u.role.title()}) registered with email {u.email}",
            'badge_class': f"role-{u.role}"
        })
    
    recent_notes = Note.query.order_by(Note.created_at.desc()).limit(5).all()
    for n in recent_notes:
        recent_activity.append({
            'timestamp': n.created_at,
            'type': 'Note Uploaded',
            'details': f"Note '{n.title}' in {n.subject} uploaded by {n.uploader.full_name if n.uploader else 'User'}",
            'badge_class': 'role-student' if n.uploader_role == 'student' else 'role-faculty'
        })

    recent_activity.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min, reverse=True)
    recent_activity = recent_activity[:10]

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
        total_quizzes=total_quizzes,
        dept_stats=dept_stats,
        recent_users=recent_users,
        recent_activity=recent_activity
    )


@admin_bp.route('/users')
@admin_required
def users():
    search_q = request.args.get('q', '').strip()
    role_filter = request.args.get('role', 'all').strip()
    dept_filter = request.args.get('department_id', 'all').strip()
    status_filter = request.args.get('status', 'all').strip()
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

    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)

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
        status_filter=status_filter,
        sort_by=sort_by,
        departments=departments
    )


@admin_bp.route('/students')
@admin_required
def students():
    search_q = request.args.get('q', '').strip()
    dept_filter = request.args.get('department_id', 'all').strip()
    year_filter = request.args.get('academic_year', 'all').strip()
    sort_by = request.args.get('sort', 'newest').strip()
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

    if year_filter and year_filter != 'all':
        query = query.filter(Student.academic_year.ilike(f'%{year_filter}%'))

    if sort_by == 'oldest':
        query = query.order_by(User.created_at.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(User.full_name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(User.full_name.desc())
    elif sort_by == 'roll_asc':
        query = query.order_by(Student.roll_number.asc())
    else:
        query = query.order_by(User.created_at.desc())

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    students_list = pagination.items
    total_students_count = Student.query.count()
    departments = Department.query.all()

    return render_template(
        'admin/students.html',
        students=students_list,
        pagination=pagination,
        search_q=search_q,
        dept_filter=dept_filter,
        year_filter=year_filter,
        sort_by=sort_by,
        total_students_count=total_students_count,
        departments=departments
    )


@admin_bp.route('/faculty')
@admin_required
def faculty():
    search_q = request.args.get('q', '').strip()
    dept_filter = request.args.get('department_id', 'all').strip()
    sort_by = request.args.get('sort', 'newest').strip()
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

    if sort_by == 'oldest':
        query = query.order_by(User.created_at.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(User.full_name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(User.full_name.desc())
    else:
        query = query.order_by(User.created_at.desc())

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    faculty_list = pagination.items
    total_faculty_count = Faculty.query.count()
    departments = Department.query.all()

    return render_template(
        'admin/faculty.html',
        faculty_list=faculty_list,
        pagination=pagination,
        search_q=search_q,
        dept_filter=dept_filter,
        sort_by=sort_by,
        total_faculty_count=total_faculty_count,
        departments=departments
    )


@admin_bp.route('/clubs')
@admin_required
def clubs():
    search_q = request.args.get('q', '').strip()
    category_filter = request.args.get('category', 'all').strip()
    sort_by = request.args.get('sort', 'newest').strip()
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

    if sort_by == 'oldest':
        query = query.order_by(User.created_at.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Club.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Club.name.desc())
    else:
        query = query.order_by(User.created_at.desc())

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    clubs_list = pagination.items
    total_clubs_count = Club.query.count()

    return render_template(
        'admin/clubs.html',
        clubs=clubs_list,
        pagination=pagination,
        search_q=search_q,
        category_filter=category_filter,
        sort_by=sort_by,
        total_clubs_count=total_clubs_count
    )


@admin_bp.route('/departments')
@admin_bp.route('/department-statistics')
@admin_required
def departments():
    depts = Department.query.order_by(Department.id.asc()).all()
    dept_details = []

    total_all_students = Student.query.count()

    for d in depts:
        st_count = Student.query.filter_by(department_id=d.id).count()
        fac_count = Faculty.query.filter_by(department_id=d.id).count()
        club_count = Club.query.filter_by(department_id=d.id).count()
        notes_count = Note.query.filter_by(department_id=d.id).count()
        asgn_count = Assignment.query.filter_by(department_id=d.id).count()
        notice_count = Notice.query.filter_by(department_id=d.id).count()

        percentage = round((st_count / total_all_students * 100), 1) if total_all_students > 0 else 0.0

        dept_details.append({
            'department': d,
            'students_count': st_count,
            'faculty_count': fac_count,
            'clubs_count': club_count,
            'notes_count': notes_count,
            'assignments_count': asgn_count,
            'notices_count': notice_count,
            'student_percentage': percentage,
            'total_users': st_count + fac_count + club_count
        })

    return render_template('admin/departments.html', dept_details=dept_details, total_all_students=total_all_students)


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


@admin_bp.route('/notes/<int:note_id>/delete', methods=['POST'])
@admin_required
def delete_note(note_id):
    note = db.session.get(Note, note_id)
    if note:
        db.session.delete(note)
        db.session.commit()
        flash('Note deleted successfully from production database.', 'success')
    else:
        flash('Note not found.', 'danger')
    return redirect(request.referrer or url_for('admin.notes'))


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


@admin_bp.route('/assignments/<int:asgn_id>/delete', methods=['POST'])
@admin_required
def delete_assignment(asgn_id):
    asgn = db.session.get(Assignment, asgn_id)
    if asgn:
        db.session.delete(asgn)
        db.session.commit()
        flash('Assignment deleted successfully from production database.', 'success')
    else:
        flash('Assignment not found.', 'danger')
    return redirect(request.referrer or url_for('admin.assignments'))


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


@admin_bp.route('/notices/<int:notice_id>/delete', methods=['POST'])
@admin_required
def delete_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if notice:
        db.session.delete(notice)
        db.session.commit()
        flash('Notice deleted successfully from production database.', 'success')
    else:
        flash('Notice not found.', 'danger')
    return redirect(request.referrer or url_for('admin.notices'))


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


@admin_bp.route('/doubts/<int:doubt_id>/delete', methods=['POST'])
@admin_required
def delete_doubt(doubt_id):
    doubt = db.session.get(Doubt, doubt_id)
    if doubt:
        db.session.delete(doubt)
        db.session.commit()
        flash('Doubt deleted successfully from production database.', 'success')
    else:
        flash('Doubt not found.', 'danger')
    return redirect(request.referrer or url_for('admin.doubts'))


@admin_bp.route('/database')
@admin_bp.route('/system')
@admin_required
def database_overview():
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

    recent_activity = []
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    for u in recent_users:
        recent_activity.append({
            'timestamp': u.created_at,
            'type': 'User Registration',
            'details': f"{u.full_name} ({u.role.title()}) registered with email {u.email}",
            'icon': 'fa-user-plus',
            'color': '#0284c7'
        })

    recent_notes = Note.query.order_by(Note.created_at.desc()).limit(5).all()
    for n in recent_notes:
        recent_activity.append({
            'timestamp': n.created_at,
            'type': 'Note Upload',
            'details': f"Note '{n.title}' uploaded by {n.uploader.full_name if n.uploader else 'User'}",
            'icon': 'fa-file-pdf',
            'color': '#10b981'
        })

    recent_notices = Notice.query.order_by(Notice.created_at.desc()).limit(5).all()
    for nt in recent_notices:
        recent_activity.append({
            'timestamp': nt.created_at,
            'type': 'Notice Created',
            'details': f"Notice '{nt.title}' published ({nt.notice_type.title()})",
            'icon': 'fa-bullhorn',
            'color': '#f59e0b'
        })

    recent_activity.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min, reverse=True)
    recent_activity = recent_activity[:10]

    env_info = {
        'Python Version': sys.version.split(' ')[0],
        'Database Engine': str(db.engine.url.drivername),
        'Server Time (UTC)': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'Upload Directory': current_app.config['UPLOAD_FOLDER'],
        'Environment': 'Production Live Database',
        'Database Sync': 'Real-time Automatic'
    }

    return render_template('admin/system.html', table_counts=table_counts, env_info=env_info, recent_activity=recent_activity)


@admin_bp.route('/settings')
@admin_required
def settings():
    session_info = {
        'admin_logged_in': session.get('admin_logged_in'),
        'admin_email': session.get('admin_email', 'admin@rcpit.ac.in'),
        'user_name': session.get('user_name', 'Developer Admin'),
        'role': session.get('role', 'admin'),
        'has_env_password': 'ADMIN_PASSWORD' in os.environ,
        'session_permanent': True
    }
    return render_template('admin/settings.html', session_info=session_info)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User record not found in database.', 'danger')
        return redirect(url_for('admin.users'))

    if user.role == 'admin':
        flash('Developer Admin account status cannot be toggled.', 'warning')
        return redirect(url_for('admin.users'))

    user.is_active = not getattr(user, 'is_active', True)
    db.session.commit()
    status_str = "activated" if user.is_active else "deactivated"
    flash(f'User account {user.full_name} ({user.email}) has been {status_str}.', 'success')

    ref = request.referrer or url_for('admin.users')
    return redirect(ref)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User record not found in database.', 'danger')
        return redirect(url_for('admin.users'))

    if user.role == 'admin':
        flash('Developer Admin account cannot be deleted.', 'danger')
        return redirect(url_for('admin.users'))

    confirm_text = request.form.get('confirm_text', '').strip()
    if confirm_text != 'DELETE' and confirm_text.lower() != user.email.lower():
        flash('Confirmation failed. You must type DELETE to confirm account deletion.', 'warning')
        ref = request.referrer or url_for('admin.users')
        return redirect(ref)

    email_bak = user.email
    name_bak = user.full_name
    db.session.delete(user)
    db.session.commit()
    flash(f'User account {name_bak} ({email_bak}) and all associated records were permanently deleted.', 'success')

    ref = request.referrer or url_for('admin.users')
    return redirect(ref)
