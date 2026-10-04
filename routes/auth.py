from functools import wraps
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, g
from database import db
from models import User, Student, Faculty, Club, Department

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('role') not in roles:
                flash('Unauthorized access for your role.', 'danger')
                return redirect(url_for('auth.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = db.session.get(User, user_id)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('auth.dashboard'))

    departments = Department.query.all()
    clubs = Club.query.all()

    if request.method == 'POST':
        role = request.form.get('role')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if role == 'club_leader':
            club_id = request.form.get('club_id')
            passcode = request.form.get('passcode')
            club = db.session.get(Club, int(club_id)) if club_id else None
            if club and (club.passcode == passcode or club.user.check_password(passcode)):
                session['user_id'] = club.user.id
                session['role'] = 'club'
                session['user_name'] = club.name
                flash(f'Welcome Club Leader of {club.name}!', 'success')
                return redirect(url_for('club.dashboard'))
            else:
                flash('Invalid Club selection or passcode.', 'danger')
                return render_template('login.html', departments=departments, clubs=clubs)

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if role and user.role != role:
                flash(f'Role mismatch. You registered as a {user.role.title()}.', 'danger')
                return render_template('login.html', departments=departments, clubs=clubs)

            session['user_id'] = user.id
            session['role'] = user.role
            session['user_name'] = user.full_name
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('auth.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', departments=departments, clubs=clubs)

@auth_bp.route('/register/student', methods=['POST'])
def register_student():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    department_id = request.form.get('department_id')
    academic_year = request.form.get('academic_year')
    roll_number = request.form.get('roll_number', '').strip()

    if not full_name or not email or not password or not department_id:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('auth.login'))

    existing = User.query.filter_by(email=email).first()
    if existing:
        flash('Email address is already registered.', 'warning')
        return redirect(url_for('auth.login'))

    user = User(email=email, full_name=full_name, role='student')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    student = Student(
        user_id=user.id,
        department_id=int(department_id),
        academic_year=academic_year,
        roll_number=roll_number
    )
    db.session.add(student)
    db.session.commit()

    flash('Student account registered successfully! Please log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register/faculty', methods=['POST'])
def register_faculty():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    department_id = request.form.get('department_id')
    designation = request.form.get('designation')
    specialization = request.form.get('specialization', '').strip()

    if not full_name or not email or not password or not department_id:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('auth.login'))

    existing = User.query.filter_by(email=email).first()
    if existing:
        flash('Email address is already registered.', 'warning')
        return redirect(url_for('auth.login'))

    user = User(email=email, full_name=full_name, role='faculty')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    faculty = Faculty(user_id=user.id, department_id=int(department_id), designation=designation, specialization=specialization)
    db.session.add(faculty)
    db.session.commit()

    flash('Faculty account registered successfully! Please log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register/club', methods=['POST'])
def register_club():
    club_name = request.form.get('club_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    passcode = request.form.get('passcode', '').strip()
    category = request.form.get('category', 'Technical')
    department_id = request.form.get('department_id')
    leader_name = request.form.get('leader_name', '').strip()
    description = request.form.get('description', '').strip()

    department_id = int(department_id) if department_id and department_id != 'all' else None

    if not club_name or not email or not passcode or not leader_name:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('auth.login'))

    existing = User.query.filter_by(email=email).first()
    if existing:
        flash('Club email address is already registered.', 'warning')
        return redirect(url_for('auth.login'))

    user = User(email=email, full_name=club_name, role='club')
    user.set_password(passcode)
    db.session.add(user)
    db.session.flush()

    club = Club(user_id=user.id, department_id=department_id, name=club_name, category=category, leader_name=leader_name, description=description, passcode=passcode)
    db.session.add(club)
    db.session.commit()

    flash('Campus Club registered successfully! Please log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'student':
        return redirect(url_for('student.dashboard'))
    elif role == 'faculty':
        return redirect(url_for('faculty.dashboard'))
    elif role == 'club':
        return redirect(url_for('club.dashboard'))
    else:
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
