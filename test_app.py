import unittest
from app import app
from database import db
from models import Department, User, Student, Faculty, Club, Task, Note, Notice, Doubt, DoubtReply, Assignment

class CampusConnectRealDataTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            # Reset database for clean testing
            db.drop_all()
            db.create_all()

            # Seed essential departments
            dept_aiml = Department(name="Artificial Intelligence & Machine Learning", code="AIML", description="AI Department")
            dept_cse = Department(name="Computer Science Engineering", code="CSE", description="CSE Department")
            db.session.add_all([dept_aiml, dept_cse])
            db.session.commit()

            self.dept_aiml_id = dept_aiml.id
            self.dept_cse_id = dept_cse.id

    def test_full_real_user_lifecycle_and_isolation(self):
        client = self.client

        # ----------------------------------------------------
        # 1. Register Student A & Login
        # ----------------------------------------------------
        res = client.post('/register/student', data={
            'full_name': 'Student Alice',
            'email': 'alice@rcpit.ac.in',
            'password': 'pass123',
            'department_id': self.dept_aiml_id,
            'academic_year': 'Third Year (TE)',
            'roll_number': '21AIML001'
        }, follow_redirects=True)
        self.assertIn(b'Student account registered successfully', res.data)

        # Login Student Alice
        res = client.post('/login', data={'role': 'student', 'email': 'alice@rcpit.ac.in', 'password': 'pass123'}, follow_redirects=True)
        self.assertIn(b'Student Command Center', res.data)
        self.assertIn(b'Student Alice', res.data)

        # Alice creates a private task
        res = client.post('/student/task/create', data={
            'title': 'Alice Secret ML Task',
            'category': 'Assignment'
        }, follow_redirects=True)
        self.assertIn(b'Alice Secret ML Task', res.data)

        # Logout Alice
        client.get('/logout')

        # ----------------------------------------------------
        # 2. Register Student B (Bob) & Login
        # ----------------------------------------------------
        client.post('/register/student', data={
            'full_name': 'Student Bob',
            'email': 'bob@rcpit.ac.in',
            'password': 'pass123',
            'department_id': self.dept_aiml_id,
            'academic_year': 'Third Year (TE)',
            'roll_number': '21AIML002'
        }, follow_redirects=True)

        res = client.post('/login', data={'role': 'student', 'email': 'bob@rcpit.ac.in', 'password': 'pass123'}, follow_redirects=True)
        self.assertIn(b'Student Bob', res.data)

        # VERIFY: Bob must NOT see Alice's private task!
        self.assertNotIn(b'Alice Secret ML Task', res.data)
        self.assertIn(b'No tasks yet', res.data)

        # Logout Bob
        client.get('/logout')

        # ----------------------------------------------------
        # 3. Register Faculty A & Post Academic Notice
        # ----------------------------------------------------
        client.post('/register/faculty', data={
            'full_name': 'Dr. Alan Turing',
            'email': 'turing@rcpit.ac.in',
            'password': 'pass123',
            'department_id': self.dept_aiml_id,
            'designation': 'Head of Department (HOD)',
            'specialization': 'AI & Computation'
        }, follow_redirects=True)

        res = client.post('/login', data={'role': 'faculty', 'email': 'turing@rcpit.ac.in', 'password': 'pass123'}, follow_redirects=True)
        self.assertIn(b'Faculty Management Portal', res.data)
        self.assertIn(b'Dr. Alan Turing', res.data)

        # Faculty Turing posts a real academic notice
        res = client.post('/faculty/notice/create', data={
            'title': 'AIML Practical Exam Timetable',
            'department_id': str(self.dept_aiml_id),
            'content': 'Practical exams begin on Monday at 9 AM.'
        }, follow_redirects=True)
        self.assertIn(b'Official Academic Notice published', res.data)

        client.get('/logout')

        # ----------------------------------------------------
        # 4. Student Alice logs in & sees Faculty Turing's notice
        # ----------------------------------------------------
        res = client.post('/login', data={'role': 'student', 'email': 'alice@rcpit.ac.in', 'password': 'pass123'}, follow_redirects=True)
        self.assertIn(b'AIML Practical Exam Timetable', res.data)

        # ----------------------------------------------------
        # 5. Student Alice asks Faculty Turing a doubt
        # ----------------------------------------------------
        with app.app_context():
            fac = Faculty.query.first()
            fac_id = fac.id

        res = client.post('/student/doubt/submit', data={
            'target_type': 'faculty',
            'faculty_id': str(fac_id),
            'title': 'Question about neural backpropagation',
            'subject': 'Deep Learning',
            'question': 'How does chain rule apply in Softmax cross-entropy derivative?'
        }, follow_redirects=True)
        self.assertIn(b'Your doubt has been submitted successfully', res.data)

        client.get('/logout')

        # ----------------------------------------------------
        # 6. Faculty Turing logs in, sees Alice's doubt & replies
        # ----------------------------------------------------
        res = client.post('/login', data={'role': 'faculty', 'email': 'turing@rcpit.ac.in', 'password': 'pass123'}, follow_redirects=True)
        self.assertIn(b'Question about neural backpropagation', res.data)

        with app.app_context():
            doubt = Doubt.query.first()
            doubt_id = doubt.id

        res = client.post(f'/faculty/doubt/reply/{doubt_id}', data={
            'reply_text': 'Apply partial derivative of log-softmax with categorical one-hot target.'
        }, follow_redirects=True)
        self.assertIn(b'Doubt answer posted to student', res.data)

        client.get('/logout')

        # ----------------------------------------------------
        # 7. Student Alice logs in & sees Faculty Turing's reply
        # ----------------------------------------------------
        res = client.post('/login', data={'role': 'student', 'email': 'alice@rcpit.ac.in', 'password': 'pass123'}, follow_redirects=True)
        self.assertIn(b'Apply partial derivative of log-softmax', res.data)

        client.get('/logout')

        # ----------------------------------------------------
        # 8. Register Club A & Post Club Notice
        # ----------------------------------------------------
        client.post('/register/club', data={
            'club_name': 'Robotics Developers Society',
            'email': 'robotics@rcpit.ac.in',
            'passcode': 'clubpass123',
            'leader_name': 'Charlie Club Leader',
            'category': 'Technical',
            'department_id': str(self.dept_aiml_id),
            'description': 'Autonomous drone and bot development club.'
        }, follow_redirects=True)

        with app.app_context():
            club = Club.query.filter_by(name='Robotics Developers Society').first()
            club_id = club.id

        res = client.post('/login', data={'role': 'club_leader', 'club_id': str(club_id), 'passcode': 'clubpass123'}, follow_redirects=True)
        self.assertIn(b'Robotics Developers Society', res.data)

        # Club posts event notice
        res = client.post('/club/notice/create', data={
            'title': 'Autonomous Line Follower Drone Race 2026',
            'department_id': str(self.dept_aiml_id),
            'content': 'Register your teams for the upcoming campus drone race competition!'
        }, follow_redirects=True)
        self.assertIn(b'Club event/notice published successfully', res.data)

        client.get('/logout')

        # ----------------------------------------------------
        # 9. Student Alice logs in & sees Real Club Notice
        # ----------------------------------------------------
        res = client.post('/login', data={'role': 'student', 'email': 'alice@rcpit.ac.in', 'password': 'pass123'}, follow_redirects=True)
        self.assertIn(b'Autonomous Line Follower Drone Race 2026', res.data)

if __name__ == '__main__':
    unittest.main()
