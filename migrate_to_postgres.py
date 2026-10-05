"""
Database Migration Script for CampusConnect 2.0
Migrates existing user data and application records from local SQLite (campus_connect.db)
to production PostgreSQL database.
"""

import os
import sqlite3
from app import create_app
from database import db
from models import (
    Department, User, Student, Faculty, Club, Task, Note, NoteShare,
    Friendship, Doubt, DoubtReply, Assignment, AssignmentSubmission,
    Notice, Quiz, QuizQuestion, QuizAttempt, ExternalResource
)

def migrate_data():
    sqlite_db_path = os.path.join(os.path.dirname(__file__), 'campus_connect.db')
    if not os.path.exists(sqlite_db_path):
        print("No local campus_connect.db found to migrate.")
        return

    app = create_app()
    with app.app_context():
        # Ensure target database tables exist
        db.create_all()

        print(f"Connecting to source SQLite database: {sqlite_db_path}...")
        conn = sqlite3.connect(sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Check departments table
        try:
            cur.execute("SELECT * FROM departments")
            dept_rows = cur.fetchall()
            dept_id_map = {} # old_id -> new_id
            for r in dept_rows:
                dept = Department.query.filter_by(code=r['code']).first()
                if not dept:
                    dept = Department(
                        name=r['name'],
                        code=r['code'],
                        description=r['description'] if 'description' in r.keys() else None
                    )
                    db.session.add(dept)
                    db.session.flush()
                dept_id_map[r['id']] = dept.id
            db.session.commit()
            print(f"Departments synced. Mapped {len(dept_id_map)} departments.")
        except Exception as e:
            db.session.rollback()
            print(f"Department migration note: {e}")

        # 2. Sync Users & Profiles
        try:
            cur.execute("SELECT * FROM users")
            user_rows = cur.fetchall()
            user_id_map = {} # old_id -> new_id
            migrated_users_count = 0

            for u_row in user_rows:
                email = u_row['email'].strip().lower()
                user = User.query.filter_by(email=email).first()

                if not user:
                    user = User(
                        email=email,
                        password_hash=u_row['password_hash'],
                        full_name=u_row['full_name'],
                        role=u_row['role'],
                        is_active=bool(u_row['is_active']) if 'is_active' in u_row.keys() and u_row['is_active'] is not None else True
                    )
                    db.session.add(user)
                    db.session.flush()
                    migrated_users_count += 1
                
                user_id_map[u_row['id']] = user.id

                # Migrate associated profile if not existing
                if u_row['role'] == 'student' and not user.student_profile:
                    cur.execute("SELECT * FROM students WHERE user_id = ?", (u_row['id'],))
                    st_row = cur.fetchone()
                    if st_row:
                        dept_id = dept_id_map.get(st_row['department_id'], st_row['department_id'])
                        student = Student(
                            user_id=user.id,
                            department_id=dept_id,
                            academic_year=st_row['academic_year'],
                            roll_number=st_row['roll_number'] if 'roll_number' in st_row.keys() else None
                        )
                        db.session.add(student)

                elif u_row['role'] == 'faculty' and not user.faculty_profile:
                    cur.execute("SELECT * FROM faculty WHERE user_id = ?", (u_row['id'],))
                    fac_row = cur.fetchone()
                    if fac_row:
                        dept_id = dept_id_map.get(fac_row['department_id'], fac_row['department_id'])
                        faculty = Faculty(
                            user_id=user.id,
                            department_id=dept_id,
                            designation=fac_row['designation'],
                            specialization=fac_row['specialization'] if 'specialization' in fac_row.keys() else None
                        )
                        db.session.add(faculty)

                elif u_row['role'] == 'club' and not user.club_profile:
                    cur.execute("SELECT * FROM clubs WHERE user_id = ?", (u_row['id'],))
                    cl_row = cur.fetchone()
                    if cl_row:
                        dept_id = dept_id_map.get(cl_row['department_id']) if cl_row['department_id'] else None
                        club = Club(
                            user_id=user.id,
                            department_id=dept_id,
                            name=cl_row['name'],
                            category=cl_row['category'],
                            leader_name=cl_row['leader_name'],
                            description=cl_row['description'] if 'description' in cl_row.keys() else None,
                            passcode=cl_row['passcode'] if 'passcode' in cl_row.keys() else None
                        )
                        db.session.add(club)

            db.session.commit()
            print(f"Users & Profiles synced successfully. New users inserted: {migrated_users_count}.")
        except Exception as e:
            db.session.rollback()
            print(f"User migration error: {e}")

        conn.close()
        print("Data migration routine finished.")

if __name__ == '__main__':
    migrate_data()
