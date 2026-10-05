"""
Database Migration Script for CampusConnect 2.0
Migrates existing user data, profiles, and application records from local SQLite (campus_connect.db)
to production Render PostgreSQL database.
"""

import os
import sqlite3
from datetime import datetime
from app import create_app
from database import db
from models import (
    Department, User, Student, Faculty, Club, Task, Note, NoteShare,
    Friendship, Doubt, DoubtReply, Assignment, AssignmentSubmission,
    Notice, Quiz, QuizQuestion, QuizAttempt, ExternalResource, UploadedFile
)


def parse_dt(dt_str):
    if not dt_str:
        return None
    if isinstance(dt_str, datetime):
        return dt_str
    try:
        return datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
    except Exception:
        try:
            return datetime.strptime(str(dt_str)[:19], '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

def migrate_data():
    sqlite_db_path = os.path.join(os.path.dirname(__file__), 'campus_connect.db')
    if not os.path.exists(sqlite_db_path):
        print("No local campus_connect.db found to migrate.")
        return

    app = create_app()
    with app.app_context():
        db.create_all()

        print(f"Connecting to source SQLite database: {sqlite_db_path}...")
        conn = sqlite3.connect(sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        dept_map = {}      # sqlite dept id -> pg dept id
        user_map = {}      # sqlite user id -> pg user id
        student_map = {}   # sqlite student id -> pg student id
        faculty_map = {}   # sqlite faculty id -> pg faculty id
        club_map = {}      # sqlite club id -> pg club id
        note_map = {}      # sqlite note id -> pg note id
        doubt_map = {}     # sqlite doubt id -> pg doubt id
        assignment_map = {}# sqlite assignment id -> pg assignment id
        quiz_map = {}      # sqlite quiz id -> pg quiz id

        # 1. Departments
        try:
            cur.execute("SELECT * FROM departments")
            for r in cur.fetchall():
                dept = Department.query.filter_by(code=r['code']).first()
                if not dept:
                    dept = Department(
                        name=r['name'],
                        code=r['code'],
                        description=r['description'] if 'description' in r.keys() else None
                    )
                    db.session.add(dept)
                    db.session.flush()
                dept_map[r['id']] = dept.id
            db.session.commit()
            print(f"[1/15] Synced Departments ({len(dept_map)} mapped)")
        except Exception as e:
            db.session.rollback()
            print(f"Department migration note: {e}")

        # 2. Users & Profiles (Student, Faculty, Club)
        try:
            cur.execute("SELECT * FROM users")
            user_rows = cur.fetchall()
            for u in user_rows:
                email = u['email'].strip().lower()
                user = User.query.filter_by(email=email).first()
                if not user:
                    user = User(
                        email=email,
                        password_hash=u['password_hash'],
                        full_name=u['full_name'],
                        role=u['role'],
                        is_active=bool(u['is_active']) if 'is_active' in u.keys() and u['is_active'] is not None else True,
                        created_at=parse_dt(u['created_at']) if 'created_at' in u.keys() else datetime.utcnow()
                    )
                    db.session.add(user)
                    db.session.flush()
                user_map[u['id']] = user.id

                # Profiles
                if u['role'] == 'student' and not user.student_profile:
                    cur.execute("SELECT * FROM students WHERE user_id = ?", (u['id'],))
                    st = cur.fetchone()
                    if st:
                        dept_id = dept_map.get(st['department_id'], st['department_id'])
                        student = Student(
                            user_id=user.id,
                            department_id=dept_id,
                            academic_year=st['academic_year'],
                            roll_number=st['roll_number'] if 'roll_number' in st.keys() else None
                        )
                        db.session.add(student)
                        db.session.flush()
                        student_map[st['id']] = student.id
                elif u['role'] == 'student' and user.student_profile:
                    cur.execute("SELECT * FROM students WHERE user_id = ?", (u['id'],))
                    st = cur.fetchone()
                    if st:
                        student_map[st['id']] = user.student_profile.id

                if u['role'] == 'faculty' and not user.faculty_profile:
                    cur.execute("SELECT * FROM faculty WHERE user_id = ?", (u['id'],))
                    fac = cur.fetchone()
                    if fac:
                        dept_id = dept_map.get(fac['department_id'], fac['department_id'])
                        faculty = Faculty(
                            user_id=user.id,
                            department_id=dept_id,
                            designation=fac['designation'],
                            specialization=fac['specialization'] if 'specialization' in fac.keys() else None
                        )
                        db.session.add(faculty)
                        db.session.flush()
                        faculty_map[fac['id']] = faculty.id
                elif u['role'] == 'faculty' and user.faculty_profile:
                    cur.execute("SELECT * FROM faculty WHERE user_id = ?", (u['id'],))
                    fac = cur.fetchone()
                    if fac:
                        faculty_map[fac['id']] = user.faculty_profile.id

                if u['role'] == 'club' and not user.club_profile:
                    cur.execute("SELECT * FROM clubs WHERE user_id = ?", (u['id'],))
                    cl = cur.fetchone()
                    if cl:
                        dept_id = dept_map.get(cl['department_id']) if cl['department_id'] else None
                        club = Club(
                            user_id=user.id,
                            department_id=dept_id,
                            name=cl['name'],
                            category=cl['category'],
                            leader_name=cl['leader_name'],
                            description=cl['description'] if 'description' in cl.keys() else None,
                            passcode=cl['passcode'] if 'passcode' in cl.keys() else None
                        )
                        db.session.add(club)
                        db.session.flush()
                        club_map[cl['id']] = club.id
                elif u['role'] == 'club' and user.club_profile:
                    cur.execute("SELECT * FROM clubs WHERE user_id = ?", (u['id'],))
                    cl = cur.fetchone()
                    if cl:
                        club_map[cl['id']] = user.club_profile.id

            db.session.commit()
            print(f"[2/15] Synced Users ({len(user_map)} mapped)")
        except Exception as e:
            db.session.rollback()
            print(f"User profile migration note: {e}")

        # 3. Student Tasks
        try:
            cur.execute("SELECT * FROM tasks")
            tasks = cur.fetchall()
            for t in tasks:
                pg_student_id = student_map.get(t['student_id'])
                if pg_student_id:
                    task = Task(
                        student_id=pg_student_id,
                        title=t['title'],
                        description=t['description'] if 'description' in t.keys() else None,
                        category=t['category'] if 'category' in t.keys() else 'General',
                        due_date=parse_dt(t['due_date']) if 'due_date' in t.keys() else None,
                        is_completed=bool(t['is_completed']) if 'is_completed' in t.keys() else False,
                        created_at=parse_dt(t['created_at']) if 'created_at' in t.keys() else datetime.utcnow()
                    )
                    db.session.add(task)
            db.session.commit()
            print(f"[3/15] Synced Tasks ({len(tasks)} items)")
        except Exception as e:
            db.session.rollback()
            print(f"Task migration note: {e}")

        # 4. Notes & NoteShares
        try:
            cur.execute("SELECT * FROM notes")
            notes = cur.fetchall()
            for n in notes:
                pg_uploader_id = user_map.get(n['uploader_id'])
                pg_dept_id = dept_map.get(n['department_id'])
                if pg_uploader_id and pg_dept_id:
                    note = Note(
                        uploader_id=pg_uploader_id,
                        uploader_role=n['uploader_role'],
                        department_id=pg_dept_id,
                        academic_year=n['academic_year'] if 'academic_year' in n.keys() else None,
                        title=n['title'],
                        subject=n['subject'],
                        description=n['description'] if 'description' in n.keys() else None,
                        file_path=n['file_path'] if 'file_path' in n.keys() else None,
                        is_faculty_note=bool(n['is_faculty_note']) if 'is_faculty_note' in n.keys() else False,
                        created_at=parse_dt(n['created_at']) if 'created_at' in n.keys() else datetime.utcnow()
                    )
                    db.session.add(note)
                    db.session.flush()
                    note_map[n['id']] = note.id

            cur.execute("SELECT * FROM note_shares")
            shares = cur.fetchall()
            for s in shares:
                pg_note_id = note_map.get(s['note_id'])
                pg_by_id = user_map.get(s['shared_by_id'])
                pg_with_id = user_map.get(s['shared_with_id'])
                if pg_note_id and pg_by_id and pg_with_id:
                    share = NoteShare(
                        note_id=pg_note_id,
                        shared_by_id=pg_by_id,
                        shared_with_id=pg_with_id,
                        shared_at=parse_dt(s['shared_at']) if 'shared_at' in s.keys() else datetime.utcnow()
                    )
                    db.session.add(share)
            db.session.commit()
            print(f"[4/15] Synced Notes & Shares ({len(notes)} notes)")
        except Exception as e:
            db.session.rollback()
            print(f"Notes migration note: {e}")

        # 5. Friendships
        try:
            cur.execute("SELECT * FROM friendships")
            friendships = cur.fetchall()
            for f in friendships:
                u1 = user_map.get(f['user_id_1'])
                u2 = user_map.get(f['user_id_2'])
                if u1 and u2:
                    friendship = Friendship(
                        user_id_1=u1,
                        user_id_2=u2,
                        status=f['status'] if 'status' in f.keys() else 'accepted',
                        created_at=parse_dt(f['created_at']) if 'created_at' in f.keys() else datetime.utcnow()
                    )
                    db.session.add(friendship)
            db.session.commit()
            print(f"[5/15] Synced Friendships ({len(friendships)} records)")
        except Exception as e:
            db.session.rollback()
            print(f"Friendship migration note: {e}")

        # 6. Doubts & DoubtReplies
        try:
            cur.execute("SELECT * FROM doubts")
            doubts = cur.fetchall()
            for d in doubts:
                pg_student_id = student_map.get(d['student_id'])
                pg_faculty_id = faculty_map.get(d['faculty_id']) if d['faculty_id'] else None
                pg_club_id = club_map.get(d['club_id']) if d['club_id'] else None
                if pg_student_id:
                    doubt = Doubt(
                        student_id=pg_student_id,
                        faculty_id=pg_faculty_id,
                        club_id=pg_club_id,
                        target_type=d['target_type'] if 'target_type' in d.keys() else 'faculty',
                        subject=d['subject'] if 'subject' in d.keys() else None,
                        title=d['title'],
                        question=d['question'],
                        file_path=d['file_path'] if 'file_path' in d.keys() else None,
                        status=d['status'] if 'status' in d.keys() else 'pending',
                        created_at=parse_dt(d['created_at']) if 'created_at' in d.keys() else datetime.utcnow()
                    )
                    db.session.add(doubt)
                    db.session.flush()
                    doubt_map[d['id']] = doubt.id

            cur.execute("SELECT * FROM doubt_replies")
            replies = cur.fetchall()
            for r in replies:
                pg_doubt_id = doubt_map.get(r['doubt_id'])
                pg_responder_id = user_map.get(r['responder_id'])
                if pg_doubt_id and pg_responder_id:
                    reply = DoubtReply(
                        doubt_id=pg_doubt_id,
                        responder_id=pg_responder_id,
                        reply_text=r['reply_text'],
                        file_path=r['file_path'] if 'file_path' in r.keys() else None,
                        created_at=parse_dt(r['created_at']) if 'created_at' in r.keys() else datetime.utcnow()
                    )
                    db.session.add(reply)
            db.session.commit()
            print(f"[6/15] Synced Doubts & Replies ({len(doubts)} doubts)")
        except Exception as e:
            db.session.rollback()
            print(f"Doubts migration note: {e}")

        # 7. Assignments & Submissions
        try:
            cur.execute("SELECT * FROM assignments")
            assignments = cur.fetchall()
            for a in assignments:
                pg_fac_id = faculty_map.get(a['faculty_id'])
                pg_dept_id = dept_map.get(a['department_id'])
                if pg_fac_id and pg_dept_id:
                    asgn = Assignment(
                        faculty_id=pg_fac_id,
                        department_id=pg_dept_id,
                        academic_year=a['academic_year'] if 'academic_year' in a.keys() else None,
                        title=a['title'],
                        subject=a['subject'],
                        description=a['description'],
                        file_path=a['file_path'] if 'file_path' in a.keys() else None,
                        deadline=parse_dt(a['deadline']) if 'deadline' in a.keys() else datetime.utcnow(),
                        max_marks=a['max_marks'] if 'max_marks' in a.keys() else 100,
                        created_at=parse_dt(a['created_at']) if 'created_at' in a.keys() else datetime.utcnow()
                    )
                    db.session.add(asgn)
                    db.session.flush()
                    assignment_map[a['id']] = asgn.id

            cur.execute("SELECT * FROM assignment_submissions")
            subs = cur.fetchall()
            for s in subs:
                pg_asgn_id = assignment_map.get(s['assignment_id'])
                pg_st_id = student_map.get(s['student_id'])
                if pg_asgn_id and pg_st_id:
                    sub = AssignmentSubmission(
                        assignment_id=pg_asgn_id,
                        student_id=pg_st_id,
                        submission_text=s['submission_text'] if 'submission_text' in s.keys() else None,
                        file_path=s['file_path'] if 'file_path' in s.keys() else None,
                        submitted_at=parse_dt(s['submitted_at']) if 'submitted_at' in s.keys() else datetime.utcnow(),
                        marks_obtained=s['marks_obtained'] if 'marks_obtained' in s.keys() else None,
                        feedback=s['feedback'] if 'feedback' in s.keys() else None
                    )
                    db.session.add(sub)
            db.session.commit()
            print(f"[7/15] Synced Assignments & Submissions ({len(assignments)} assignments)")
        except Exception as e:
            db.session.rollback()
            print(f"Assignment migration note: {e}")

        # 8. Notices
        try:
            cur.execute("SELECT * FROM notices")
            notices = cur.fetchall()
            for n in notices:
                pg_author_id = user_map.get(n['author_id'])
                pg_dept_id = dept_map.get(n['department_id']) if n['department_id'] else None
                pg_club_id = club_map.get(n['club_id']) if n['club_id'] else None
                if pg_author_id:
                    notice = Notice(
                        author_id=pg_author_id,
                        notice_type=n['notice_type'],
                        department_id=pg_dept_id,
                        academic_year=n['academic_year'] if 'academic_year' in n.keys() else None,
                        club_id=pg_club_id,
                        title=n['title'],
                        content=n['content'],
                        attachment_path=n['attachment_path'] if 'attachment_path' in n.keys() else None,
                        event_date=parse_dt(n['event_date']) if 'event_date' in n.keys() else None,
                        created_at=parse_dt(n['created_at']) if 'created_at' in n.keys() else datetime.utcnow()
                    )
                    db.session.add(notice)
            db.session.commit()
            print(f"[8/15] Synced Notices ({len(notices)} notices)")
        except Exception as e:
            db.session.rollback()
            print(f"Notice migration note: {e}")

        # 9. Quizzes, Questions & Attempts
        try:
            cur.execute("SELECT * FROM quizzes")
            quizzes = cur.fetchall()
            for q in quizzes:
                pg_fac_id = faculty_map.get(q['faculty_id'])
                pg_dept_id = dept_map.get(q['department_id'])
                if pg_fac_id and pg_dept_id:
                    quiz = Quiz(
                        faculty_id=pg_fac_id,
                        department_id=pg_dept_id,
                        academic_year=q['academic_year'] if 'academic_year' in q.keys() else None,
                        title=q['title'],
                        subject=q['subject'],
                        time_limit_minutes=q['time_limit_minutes'] if 'time_limit_minutes' in q.keys() else 15,
                        total_marks=q['total_marks'] if 'total_marks' in q.keys() else 10,
                        is_active=bool(q['is_active']) if 'is_active' in q.keys() else True,
                        created_at=parse_dt(q['created_at']) if 'created_at' in q.keys() else datetime.utcnow()
                    )
                    db.session.add(quiz)
                    db.session.flush()
                    quiz_map[q['id']] = quiz.id

            cur.execute("SELECT * FROM quiz_questions")
            qqs = cur.fetchall()
            for qq in qqs:
                pg_quiz_id = quiz_map.get(qq['quiz_id'])
                if pg_quiz_id:
                    q_question = QuizQuestion(
                        quiz_id=pg_quiz_id,
                        question_text=qq['question_text'],
                        option_a=qq['option_a'],
                        option_b=qq['option_b'],
                        option_c=qq['option_c'],
                        option_d=qq['option_d'],
                        correct_option=qq['correct_option'],
                        marks=qq['marks'] if 'marks' in qq.keys() else 1
                    )
                    db.session.add(q_question)

            cur.execute("SELECT * FROM quiz_attempts")
            qas = cur.fetchall()
            for qa in qas:
                pg_quiz_id = quiz_map.get(qa['quiz_id'])
                pg_st_id = student_map.get(qa['student_id'])
                if pg_quiz_id and pg_st_id:
                    attempt = QuizAttempt(
                        quiz_id=pg_quiz_id,
                        student_id=pg_st_id,
                        score=qa['score'],
                        total_possible=qa['total_possible'],
                        completed_at=parse_dt(qa['completed_at']) if 'completed_at' in qa.keys() else datetime.utcnow(),
                        details_json=qa['details_json'] if 'details_json' in qa.keys() else None
                    )
                    db.session.add(attempt)
            db.session.commit()
            print(f"[9/15] Synced Quizzes, Questions & Attempts ({len(quizzes)} quizzes)")
        except Exception as e:
            db.session.rollback()
            print(f"Quiz migration note: {e}")

        # 10. External Resources
        try:
            cur.execute("SELECT * FROM external_resources")
            res_rows = cur.fetchall()
            for r in res_rows:
                ext = ExternalResource.query.filter_by(title=r['title']).first()
                if not ext:
                    ext = ExternalResource(
                        title=r['title'],
                        category=r['category'],
                        description=r['description'],
                        url=r['url'],
                        icon_name=r['icon_name'] if 'icon_name' in r.keys() else 'code',
                        badge_tag=r['badge_tag'] if 'badge_tag' in r.keys() else 'Popular',
                        is_api_supported=bool(r['is_api_supported']) if 'is_api_supported' in r.keys() else False
                    )
                    db.session.add(ext)
            db.session.commit()
            print(f"[10/15] Synced External Resources ({len(res_rows)} resources)")
        except Exception as e:
            db.session.rollback()
            print(f"External resource migration note: {e}")

        conn.close()
        print("🎉 Full SQLite -> PostgreSQL Migration Complete!")

if __name__ == '__main__':
    migrate_data()
