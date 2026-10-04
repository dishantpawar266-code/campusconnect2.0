from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    students = db.relationship('Student', backref='department', lazy=True)
    faculty_members = db.relationship('Faculty', backref='department', lazy=True)
    clubs = db.relationship('Club', backref='department', lazy=True)
    notes = db.relationship('Note', backref='department', lazy=True)
    assignments = db.relationship('Assignment', backref='department', lazy=True)
    notices = db.relationship('Notice', backref='department', lazy=True)
    quizzes = db.relationship('Quiz', backref='department', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'student', 'faculty', 'club'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student_profile = db.relationship('Student', backref='user', uselist=False, cascade="all, delete-orphan")
    faculty_profile = db.relationship('Faculty', backref='user', uselist=False, cascade="all, delete-orphan")
    club_profile = db.relationship('Club', backref='user', uselist=False, cascade="all, delete-orphan")
    notes_uploaded = db.relationship('Note', backref='uploader', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    academic_year = db.Column(db.String(30), nullable=False) # FE, SE, TE, BE
    roll_number = db.Column(db.String(30), nullable=True)

    tasks = db.relationship('Task', backref='student', lazy=True, cascade="all, delete-orphan")
    doubts = db.relationship('Doubt', backref='student', lazy=True)
    submissions = db.relationship('AssignmentSubmission', backref='student', lazy=True)
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy=True)

class Faculty(db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    designation = db.Column(db.String(100), nullable=False) # Assistant Professor, HOD, etc.
    specialization = db.Column(db.String(150), nullable=True)

    assignments = db.relationship('Assignment', backref='faculty', lazy=True)
    quizzes = db.relationship('Quiz', backref='faculty', lazy=True)
    doubts_received = db.relationship('Doubt', backref='faculty', lazy=True)

class Club(db.Model):
    __tablename__ = 'clubs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False) # Technical, Cultural, Sports, etc.
    leader_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    passcode = db.Column(db.String(100), nullable=True)

    notices = db.relationship('Notice', backref='club', lazy=True)
    doubts = db.relationship('Doubt', backref='club', lazy=True)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), default='General') # Homework, Exam, Project, Personal
    due_date = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploader_role = db.Column(db.String(20), nullable=False) # 'student' or 'faculty'
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    academic_year = db.Column(db.String(30), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    is_faculty_note = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shares = db.relationship('NoteShare', backref='note', lazy=True, cascade="all, delete-orphan")

class NoteShare(db.Model):
    __tablename__ = 'note_shares'
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('notes.id'), nullable=False)
    shared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[shared_by_id])
    recipient = db.relationship('User', foreign_keys=[shared_with_id])

class Friendship(db.Model):
    __tablename__ = 'friendships'
    id = db.Column(db.Integer, primary_key=True)
    user_id_1 = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_id_2 = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='accepted') # 'pending', 'accepted'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user1 = db.relationship('User', foreign_keys=[user_id_1])
    user2 = db.relationship('User', foreign_keys=[user_id_2])

class Doubt(db.Model):
    __tablename__ = 'doubts'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=True)
    target_type = db.Column(db.String(20), nullable=False, default='faculty') # 'faculty' or 'club'
    subject = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    question = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending') # 'pending', 'answered'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    replies = db.relationship('DoubtReply', backref='doubt', lazy=True, cascade="all, delete-orphan")

class DoubtReply(db.Model):
    __tablename__ = 'doubt_replies'
    id = db.Column(db.Integer, primary_key=True)
    doubt_id = db.Column(db.Integer, db.ForeignKey('doubts.id'), nullable=False)
    responder_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reply_text = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    responder = db.relationship('User', foreign_keys=[responder_id])

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    academic_year = db.Column(db.String(30), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    deadline = db.Column(db.DateTime, nullable=False)
    max_marks = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy=True, cascade="all, delete-orphan")

class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    submission_text = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    marks_obtained = db.Column(db.Integer, nullable=True)
    feedback = db.Column(db.Text, nullable=True)

class Notice(db.Model):
    __tablename__ = 'notices'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notice_type = db.Column(db.String(20), nullable=False) # 'academic' or 'club'
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True) # None = all depts
    academic_year = db.Column(db.String(30), nullable=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    event_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', foreign_keys=[author_id])

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    academic_year = db.Column(db.String(30), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    time_limit_minutes = db.Column(db.Integer, default=15)
    total_marks = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship('QuizQuestion', backref='quiz', lazy=True, cascade="all, delete-orphan")
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True, cascade="all, delete-orphan")

class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False) # 'A', 'B', 'C', 'D'
    marks = db.Column(db.Integer, default=1)

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_possible = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    details_json = db.Column(db.Text, nullable=True) # store user answers string/json

class ExternalResource(db.Model):
    __tablename__ = 'external_resources'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False) # Competitive, Hackathons, Practice, Learning, Careers
    description = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(255), nullable=False)
    icon_name = db.Column(db.String(50), default='code')
    badge_tag = db.Column(db.String(50), default='Popular')
    is_api_supported = db.Column(db.Boolean, default=False)
