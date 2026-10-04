from database import db
from models import Department, Division, ExternalResource

def seed_database():
    # Check if departments are already seeded
    if Department.query.first():
        print("Departments & Divisions already initialized. Skipping systemic seeding.")
        return

    print("Initializing official RCPIT departments, divisions, and external resources directory...")

    # Official RCPIT Department & Division Structure (5 Departments, 9 Divisions)
    depts_structure = [
        (
            "Artificial Intelligence and Machine Learning",
            "AIML",
            "Advanced study of AI models, Machine Learning, Deep Learning, and NLP.",
            ["A"] # 1 Division
        ),
        (
            "Computer Science Engineering (Data Science)",
            "CSE-DS",
            "Core software engineering, data analytics, and big data systems.",
            ["A", "B"] # 2 Divisions
        ),
        (
            "Artificial Intelligence and Data Science",
            "AIDS",
            "Statistical modeling, data science, and neural network pipelines.",
            ["A", "B"] # 2 Divisions
        ),
        (
            "Electronics and Telecommunications",
            "ENTC",
            "Embedded systems, IoT, signal processing, and communication networks.",
            ["A", "B"] # 2 Divisions
        ),
        (
            "Information Technology",
            "IT",
            "Web applications, cloud computing, cybersecurity, and database systems.",
            ["A", "B"] # 2 Divisions
        )
    ]

    for dept_name, dept_code, desc, divisions_list in depts_structure:
        dept = Department(name=dept_name, code=dept_code, description=desc)
        db.session.add(dept)
        db.session.flush()

        for div_name in divisions_list:
            div = Division(department_id=dept.id, name=div_name)
            db.session.add(div)

    # External Platform Directory
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
    print("Official RCPIT Department & 9 Division structure initialized cleanly!")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        db.create_all()
        seed_database()
