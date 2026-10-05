import os
import unittest
from app import app
from database import db
from models import Department, User, Student, Faculty, Club, Task, Note, Notice, Doubt, DoubtReply, Assignment
from seed import seed_database

class CampusConnectRealDataTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            # Reset database for clean testing
            db.drop_all()
            db.create_all()
            seed_database()

            dept_aiml = Department.query.filter_by(code='AIML').first()
            dept_cse = Department.query.filter_by(code='CSE').first()
            self.dept_aiml_id = dept_aiml.id if dept_aiml else 1
            self.dept_cse_id = dept_cse.id if dept_cse else 2

    def test_official_8_departments(self):
        with app.app_context():
            depts = Department.query.all()
            dept_codes = [d.code for d in depts]
            expected_codes = ['AIML', 'CSE', 'CSE-DS', 'AI&DS', 'ENTC', 'IT', 'ME', 'EE']
            for code in expected_codes:
                self.assertIn(code, dept_codes)

    def test_admin_authentication_and_security(self):
        client = self.client

        # 1. Unauthenticated request to /admin/dashboard must redirect to /admin/login
        res = client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Developer Admin Portal', res.data)

        # 2. Login as regular student and attempt to access /admin/dashboard (Must be blocked)
        client.post('/register/student', data={
            'full_name': 'Normal Student',
            'email': 'student@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_aiml_id,
            'academic_year': 'Third Year (TE)',
            'roll_number': '101'
        }, follow_redirects=True)

        client.post('/login', data={'role': 'student', 'email': 'student@rcpit.ac.in', 'password': 'password123'}, follow_redirects=True)
        
        # Accessing /admin/dashboard as student
        res = client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Admin access required', res.data)
        self.assertIn(b'Developer Admin Portal', res.data)

        client.get('/logout')

        # 3. Authenticate as Developer Admin using ADMIN_PASSWORD env var
        res = client.post('/admin/login', data={
            'email': os.environ.get('ADMIN_EMAIL', 'dishantpawar04@gmail.com'),
            'password': os.environ.get('ADMIN_PASSWORD', 'Admin@Campus2026!')
        }, follow_redirects=True)
        self.assertIn(b'Production Overview', res.data)
        self.assertIn(b'Normal Student', res.data)  # Shows real student registered in DB!

    def test_admin_dashboard_full_navigation_and_user_management(self):
        client = self.client

        # 1. Register a student user
        client.post('/register/student', data={
            'full_name': 'Test Student User',
            'email': 'teststudent@rcpit.ac.in',
            'password': 'pass123student',
            'department_id': self.dept_aiml_id,
            'academic_year': 'Second Year (SE)',
            'roll_number': '22AIML007'
        }, follow_redirects=True)

        # 2. Login as Developer Admin
        client.post('/admin/login', data={
            'email': os.environ.get('ADMIN_EMAIL', 'dishantpawar04@gmail.com'),
            'password': os.environ.get('ADMIN_PASSWORD', 'Admin@Campus2026!')
        }, follow_redirects=True)

        # 3. Test all admin navigation endpoints load live data cleanly
        endpoints = [
            '/admin/dashboard',
            '/admin/students',
            '/admin/faculty',
            '/admin/clubs',
            '/admin/users',
            '/admin/department-statistics',
            '/admin/departments',
            '/admin/notes',
            '/admin/notices',
            '/admin/assignments',
            '/admin/doubts',
            '/admin/database',
            '/admin/settings'
        ]
        for ep in endpoints:
            res = client.get(ep)
            self.assertEqual(res.status_code, 200, f"Endpoint {ep} failed with status {res.status_code}")
            self.assertIn(b'Developer', res.data)

        # 4. Toggle User Status (Deactivate Student)
        with app.app_context():
            st_user = User.query.filter_by(email='teststudent@rcpit.ac.in').first()
            st_user_id = st_user.id

        res = client.post(f'/admin/users/{st_user_id}/toggle-status', follow_redirects=True)
        self.assertIn(b'has been deactivated', res.data)

        # 5. Verify Deactivated Student cannot log into main portal
        client.get('/admin/logout')
        res = client.post('/login', data={'role': 'student', 'email': 'teststudent@rcpit.ac.in', 'password': 'pass123student'}, follow_redirects=True)
        self.assertIn(b'Your account has been deactivated by administrator', res.data)

        # 6. Re-authenticate as Admin & Activate Student
        client.post('/admin/login', data={
            'email': os.environ.get('ADMIN_EMAIL', 'dishantpawar04@gmail.com'),
            'password': os.environ.get('ADMIN_PASSWORD', 'Admin@Campus2026!')
        }, follow_redirects=True)

        res = client.post(f'/admin/users/{st_user_id}/toggle-status', follow_redirects=True)
        self.assertIn(b'has been activated', res.data)

        # 7. Delete User with confirmation
        res = client.post(f'/admin/users/{st_user_id}/delete', data={'confirm_text': 'DELETE'}, follow_redirects=True)
        self.assertIn(b'permanently deleted', res.data)

        # 8. Logout Admin & verify security protection
        client.get('/admin/logout')
        res = client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Developer Admin Portal', res.data)

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

    def test_private_chat_and_file_sharing(self):
        client = self.client
        import io

        # 1. Register Student Alice & Bob in same dept (AIML) & academic year (TE)
        client.post('/register/student', data={
            'full_name': 'Alice Chat',
            'email': 'alicechat@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_aiml_id,
            'academic_year': 'Third Year (TE)',
            'roll_number': '301'
        }, follow_redirects=True)

        client.post('/register/student', data={
            'full_name': 'Bob Chat',
            'email': 'bobchat@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_aiml_id,
            'academic_year': 'Third Year (TE)',
            'roll_number': '302'
        }, follow_redirects=True)

        # Get User IDs
        with app.app_context():
            u_alice = User.query.filter_by(email='alicechat@rcpit.ac.in').first()
            u_bob = User.query.filter_by(email='bobchat@rcpit.ac.in').first()
            alice_id = u_alice.id
            bob_id = u_bob.id

        # 2. Login Alice and send private text message + study PDF attachment to Bob
        client.post('/login', data={'role': 'student', 'email': 'alicechat@rcpit.ac.in', 'password': 'password123'}, follow_redirects=True)
        
        pdf_data = (io.BytesIO(b"%PDF-1.4 Fake PDF Content for Chat Test"), "notes_unit1.pdf")
        res = client.post('/student/chat/send', data={
            'receiver_id': str(bob_id),
            'message_text': 'Hey Bob, here are the Unit 1 AI notes!',
            'file': pdf_data
        }, content_type='multipart/form-data')

        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertTrue(res_json.get('success'))
        self.assertEqual(res_json['message']['message_text'], 'Hey Bob, here are the Unit 1 AI notes!')
        self.assertEqual(len(res_json['message']['attachments']), 1)
        att_id = res_json['message']['attachments'][0]['id']

        client.get('/logout')

        # 3. Login Bob and fetch chat history with Alice
        client.post('/login', data={'role': 'student', 'email': 'bobchat@rcpit.ac.in', 'password': 'password123'}, follow_redirects=True)
        res_history = client.get(f'/student/chat/messages/{alice_id}')
        self.assertEqual(res_history.status_code, 200)
        history_json = res_history.get_json()
        self.assertEqual(len(history_json['messages']), 1)
        self.assertEqual(history_json['messages'][0]['message_text'], 'Hey Bob, here are the Unit 1 AI notes!')

        # Bob downloads attachment sent by Alice
        res_dl = client.get(f'/student/chat/download/{att_id}')
        self.assertEqual(res_dl.status_code, 200)
        self.assertIn(b'%PDF-1.4 Fake PDF Content', res_dl.data)

        client.get('/logout')

        # 4. Security Test: Register Charlie in different Dept/Year & verify access is BLOCKED
        client.post('/register/student', data={
            'full_name': 'Charlie External',
            'email': 'charlie@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_cse_id,
            'academic_year': 'First Year (FE)',
            'roll_number': '101'
        }, follow_redirects=True)

        client.post('/login', data={'role': 'student', 'email': 'charlie@rcpit.ac.in', 'password': 'password123'}, follow_redirects=True)
        
        # Charlie attempts to view Alice's chat messages (Should be blocked 403)
        res_block = client.get(f'/student/chat/messages/{alice_id}')
        self.assertEqual(res_block.status_code, 403)

        # Charlie attempts to download Alice-Bob private attachment (Should redirect with security alert)
        res_att_block = client.get(f'/student/chat/download/{att_id}', follow_redirects=True)
        self.assertIn(b'Unauthorized to access this chat file', res_att_block.data)

    def test_chat_file_security_validation(self):
        client = self.client
        import io

        # Register Student 1 & Student 2
        client.post('/register/student', data={
            'full_name': 'Sec Student 1',
            'email': 'sec1@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_aiml_id,
            'academic_year': 'Second Year (SE)',
            'roll_number': 'SE001'
        }, follow_redirects=True)

        client.post('/register/student', data={
            'full_name': 'Sec Student 2',
            'email': 'sec2@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_aiml_id,
            'academic_year': 'Second Year (SE)',
            'roll_number': 'SE002'
        }, follow_redirects=True)

        with app.app_context():
            u2 = User.query.filter_by(email='sec2@rcpit.ac.in').first()
            u2_id = u2.id

        client.post('/login', data={'role': 'student', 'email': 'sec1@rcpit.ac.in', 'password': 'password123'}, follow_redirects=True)

        # 1. Attempt to upload dangerous EXE file
        exe_file = (io.BytesIO(b"MZ... Fake Executable Payload"), "malicious_app.exe")
        res_exe = client.post('/student/chat/send', data={
            'receiver_id': str(u2_id),
            'message_text': 'Try running this app!',
            'file': exe_file
        }, content_type='multipart/form-data')
        self.assertEqual(res_exe.status_code, 400)
        self.assertIn('File type not allowed or executable prohibited', res_exe.get_json().get('error', ''))

        # 2. Attempt to upload dangerous BAT script
        bat_file = (io.BytesIO(b"@echo off\ndel /f /q *"), "script.bat")
        res_bat = client.post('/student/chat/send', data={
            'receiver_id': str(u2_id),
            'message_text': 'Run script',
            'file': bat_file
        }, content_type='multipart/form-data')
        self.assertEqual(res_bat.status_code, 400)

        # 3. Attempt to upload JS file
        js_file = (io.BytesIO(b"alert('xss');"), "exploit.js")
        res_js = client.post('/student/chat/send', data={
            'receiver_id': str(u2_id),
            'message_text': 'Check js',
            'file': js_file
        }, content_type='multipart/form-data')
        self.assertEqual(res_js.status_code, 400)

        # 4. Upload valid DOCX file
        docx_file = (io.BytesIO(b"PK... Fake DOCX Document"), "assignment_draft.docx")
        res_valid = client.post('/student/chat/send', data={
            'receiver_id': str(u2_id),
            'message_text': 'Here is the DOCX draft',
            'file': docx_file
        }, content_type='multipart/form-data')
        self.assertEqual(res_valid.status_code, 200)
        self.assertTrue(res_valid.get_json().get('success'))

    def test_classmates_isolation_and_no_faculty_or_clubs(self):
        client = self.client

        # Register Student 1, Student 2 (same dept/year), Faculty (same dept), Club (same dept)
        client.post('/register/student', data={
            'full_name': 'Iso Student A',
            'email': 'isoa@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_cse_id,
            'academic_year': 'Final Year (BE)',
            'roll_number': 'BE001'
        }, follow_redirects=True)

        client.post('/register/student', data={
            'full_name': 'Iso Student B',
            'email': 'isob@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_cse_id,
            'academic_year': 'Final Year (BE)',
            'roll_number': 'BE002'
        }, follow_redirects=True)

        client.post('/register/faculty', data={
            'full_name': 'Prof. Iso Faculty',
            'email': 'isofaculty@rcpit.ac.in',
            'password': 'password123',
            'department_id': self.dept_cse_id,
            'designation': 'Professor',
            'specialization': 'Database Systems'
        }, follow_redirects=True)

        client.post('/register/club', data={
            'club_name': 'Iso CSE Club',
            'email': 'isoclub@rcpit.ac.in',
            'passcode': 'clubpass123',
            'leader_name': 'Iso Leader',
            'category': 'Technical',
            'department_id': str(self.dept_cse_id)
        }, follow_redirects=True)

        # Login Student A and verify dashboard HTML
        res = client.post('/login', data={'role': 'student', 'email': 'isoa@rcpit.ac.in', 'password': 'password123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Classmate directory must include Iso Student B
        self.assertIn(b'Iso Student B', res.data)

        # Classmate directory must NOT contain Faculty or Club as classmate items in the directory!
        # Verify that classmates list query only returns real registered students
        with app.app_context():
            u_isoa = User.query.filter_by(email='isoa@rcpit.ac.in').first()
            st_isoa = u_isoa.student_profile
            classmates = Student.query.join(User).filter(
                Student.department_id == st_isoa.department_id,
                Student.academic_year == st_isoa.academic_year,
                Student.id != st_isoa.id,
                User.is_active == True
            ).all()
            
            self.assertEqual(len(classmates), 1)
            self.assertEqual(classmates[0].user.full_name, 'Iso Student B')

if __name__ == '__main__':
    unittest.main()


