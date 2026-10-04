from database import db
from models import Department, ExternalResource

def seed_database():
    print("Syncing official 5 departments and external resources directory...")

    # Official Department Structure (ONLY these 5 departments, NO divisions)
    depts_structure = [
        (
            "Artificial Intelligence & Machine Learning",
            "AIML",
            "Advanced study of AI models, Machine Learning, Deep Learning, and NLP."
        ),
        (
            "Computer Science Engineering",
            "CSE",
            "Core software engineering, algorithms, system architecture, and computing foundations."
        ),
        (
            "Computer Science Engineering - Data Science",
            "CSE-DS",
            "Core software engineering, data analytics, and big data systems."
        ),
        (
            "Artificial Intelligence & Data Science",
            "AI&DS",
            "Statistical modeling, data science, and neural network pipelines."
        ),
        (
            "Electronics & Telecommunication Engineering",
            "ENTC",
            "Embedded systems, IoT, signal processing, and communication networks."
        )
    ]

    valid_codes = [code for _, code, _ in depts_structure]

    # Delete any deprecated departments
    deprecated = Department.query.filter(Department.code.notin_(valid_codes)).all()
    for d in deprecated:
        db.session.delete(d)

    # Upsert the official 5 departments
    for dept_name, dept_code, desc in depts_structure:
        dept = Department.query.filter_by(code=dept_code).first()
        if not dept:
            dept = Department(name=dept_name, code=dept_code, description=desc)
            db.session.add(dept)
        else:
            dept.name = dept_name
            dept.description = desc

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
    print("Official 5 Department structure initialized cleanly!")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        db.create_all()
        seed_database()
