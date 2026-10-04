import os
from database import db
from models import Department, ExternalResource, User

def seed_database():
    print("Syncing official 8 departments, admin user, and external resources...")

    # Ensure is_active column exists in users table
    try:
        db.session.execute(db.text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Official Department Structure (ONLY these 8 departments, NO divisions)
    depts_structure = [
        (
            "Artificial Intelligence and Machine Learning",
            "AIML",
            "Advanced study of AI models, Machine Learning, Deep Learning, and NLP."
        ),
        (
            "Computer Science Engineering",
            "CSE",
            "Core software engineering, algorithms, system architecture, and computing foundations."
        ),
        (
            "Computer Science Engineering (Data Science)",
            "CSE-DS",
            "Core software engineering, data analytics, and big data systems."
        ),
        (
            "Artificial Intelligence and Data Science",
            "AI&DS",
            "Statistical modeling, data science, and neural network pipelines."
        ),
        (
            "Electronics and Telecommunication Engineering",
            "ENTC",
            "Embedded systems, IoT, signal processing, and communication networks."
        ),
        (
            "Information Technology",
            "IT",
            "Information technology, software engineering, web technologies, and systems."
        ),
        (
            "Mechanical Engineering",
            "ME",
            "Thermal engineering, mechanical design, CAD/CAM, and robotics."
        ),
        (
            "Electrical Engineering",
            "EE",
            "Electrical power systems, control systems, energy engineering, and electronics."
        )
    ]

    valid_codes = [code for _, code, _ in depts_structure]

    # Delete any deprecated departments that are NOT referenced by existing data
    from models import Student, Faculty, Club, Note, Assignment, Notice, Quiz
    deprecated = Department.query.filter(Department.code.notin_(valid_codes)).all()
    for d in deprecated:
        has_students = Student.query.filter_by(department_id=d.id).first()
        has_faculty = Faculty.query.filter_by(department_id=d.id).first()
        has_clubs = Club.query.filter_by(department_id=d.id).first()
        has_notes = Note.query.filter_by(department_id=d.id).first()
        has_assignments = Assignment.query.filter_by(department_id=d.id).first()
        has_notices = Notice.query.filter_by(department_id=d.id).first()
        has_quizzes = Quiz.query.filter_by(department_id=d.id).first()

        if not (has_students or has_faculty or has_clubs or has_notes or has_assignments or has_notices or has_quizzes):
            db.session.delete(d)

    # Upsert the official 8 departments
    for dept_name, dept_code, desc in depts_structure:
        dept = Department.query.filter_by(code=dept_code).first()
        if not dept:
            dept = Department(name=dept_name, code=dept_code, description=desc)
            db.session.add(dept)
        else:
            dept.name = dept_name
            dept.description = desc

    # Seed Developer / Owner Admin Account if not exists
    admin_email = os.environ.get('ADMIN_EMAIL', 'dishantpawar04@gmail.com').lower().strip()
    admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin@Campus2026!')

    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        admin_user = User.query.filter_by(email=admin_email).first()

    if not admin_user:
        admin_user = User(
            email=admin_email,
            full_name='Developer Admin',
            role='admin'
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
    else:
        if admin_user.role != 'admin':
            admin_user.role = 'admin'

    # External Platform Directory
    if not ExternalResource.query.first():
        resources = [
            ExternalResource(
                title="CodeChef", category="Competitive Programming",
                description="Practice coding contests, weekly starters, and benchmark your rank globally against top student coders.",
                url="https://www.codechef.com", icon_name="code", badge_tag="Coding", is_api_supported=True
            ),
            ExternalResource(
                title="Unstop (Formerly Dare2Compete)", category="Hackathons & Opportunities",
                description="Explore national level hackathons, case competitions, engineering challenges, and campus recruitment drives.",
                url="https://unstop.com", icon_name="award", badge_tag="Hackathons", is_api_supported=True
            ),
            ExternalResource(
                title="LeetCode", category="Data Structures & Algorithms",
                description="Master technical interview questions, algorithm problem sets, and company-wise curated problem tags.",
                url="https://leetcode.com", icon_name="terminal", badge_tag="Interviews", is_api_supported=True
            ),
            ExternalResource(
                title="GeeksforGeeks", category="Computer Science Tutorials",
                description="Comprehensive reference for algorithms, core CS subjects (OS, DBMS, CN), and syntax guides.",
                url="https://www.geeksforgeeks.org", icon_name="book-open", badge_tag="Tutorials", is_api_supported=False
            ),
            ExternalResource(
                title="NPTEL / SWAYAM", category="Academic Certification",
                description="IIT & IISc certified online semester courses, video lectures, and official academic credit transfers.",
                url="https://nptel.ac.in", icon_name="globe", badge_tag="Certification", is_api_supported=False
            ),
            ExternalResource(
                title="GitHub Student Developer Pack", category="Developer Tools",
                description="Free access to premium developer tools, cloud credits (AWS, Azure), domain names, and GitHub Copilot.",
                url="https://education.github.com/pack", icon_name="git-branch", badge_tag="Free Credits", is_api_supported=True
            ),
            ExternalResource(
                title="Kaggle", category="AI & Data Science",
                description="Access real-world datasets, compete in machine learning benchmarks, and run GPU-powered Jupyter notebooks online.",
                url="https://www.kaggle.com", icon_name="cpu", badge_tag="Machine Learning", is_api_supported=True
            )
        ]
        db.session.add_all(resources)

    db.session.commit()
    print("Official 8 Department structure & Admin account initialized cleanly!")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        db.create_all()
        seed_database()

