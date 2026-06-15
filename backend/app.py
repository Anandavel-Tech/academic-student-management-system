from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, send_from_directory, Response
from pymongo import MongoClient
import bcrypt
import os
from datetime import datetime, date
import csv
import io
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from bson.objectid import ObjectId
import traceback

# Create Flask app instance
app = Flask(__name__, 
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['SESSION_TYPE'] = 'filesystem'

# Avatar upload configuration
AVATAR_FOLDER = os.path.join(app.static_folder, 'avatars')
os.makedirs(AVATAR_FOLDER, exist_ok=True)
ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# MongoDB connection handling
def get_db():
    if 'db' not in g:
        try:
            print("Connecting to MongoDB...")
            client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
            g.db = client.academic_tracker
            # Test connection
            client.server_info()
            print("MongoDB connected successfully")
            
            # Initialize collections if they don't exist
            collections = g.db.list_collection_names()
            if 'users' not in collections:
                print("Creating users collection...")
                g.db.create_collection('users')
            if 'students' not in collections:
                print("Creating students collection...")
                g.db.create_collection('students')
            if 'courses' not in collections:
                print("Creating courses collection...")
                g.db.create_collection('courses')
            if 'marks' not in collections:
                print("Creating marks collection...")
                g.db.create_collection('marks')
            if 'notifications' not in collections:
                print("Creating notifications collection...")
                g.db.create_collection('notifications')

            # Ensure default admin user exists
            ensure_admin_user(g.db)
                
        except Exception as e:
            print(f"Database connection error: {e}")
            # Create a mock database structure to prevent crashes
            class MockDB:
                def __init__(self):
                    self.users = MockCollection()
                    self.students = MockCollection()
                    self.courses = MockCollection()
                    self.marks = MockCollection()
            
            class MockCollection:
                def find(self, *args, **kwargs):
                    return []
                def find_one(self, *args, **kwargs):
                    return None
                def insert_one(self, document):
                    class Result:
                        def __init__(self):
                            self.inserted_id = ObjectId()
                    return Result()
                def update_one(self, *args, **kwargs):
                    class Result:
                        modified_count = 1
                    return Result()
                def delete_one(self, *args, **kwargs):
                    class Result:
                        deleted_count = 1
                    return Result()
                def count_documents(self, *args, **kwargs):
                    return 0
            
            g.db = MockDB()
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if hasattr(db, 'client'):
        db.client.close()

@app.before_request
def before_request():
    g.db = get_db()


@app.context_processor
def inject_notifications():
    """Make notification info available in all templates for the current user."""
    notif_unread_count = 0
    notif_recent = []
    try:
        username = session.get('username')
        if username and hasattr(g, 'db'):
            # Unread count
            notif_unread_count = g.db.notifications.count_documents({
                'student_id': username,
                'read': False,
            })
            # Last 5 notifications (read or unread)
            notif_recent = list(
                g.db.notifications.find({'student_id': username})
                .sort('created_at', -1)
                .limit(5)
            )
    except Exception as e:
        print(f"Error loading notifications for navbar: {e}")
    return dict(notif_unread_count=notif_unread_count, notif_recent=notif_recent)


# Helper functions

def ensure_admin_user(db):
    """Create a default admin user if it does not exist."""
    try:
        existing = db.users.find_one({'username': 'admin'})
        if not existing:
            print("Creating default admin user (username=admin)...")
            hashed = bcrypt.hashpw('12345678'.encode('utf-8'), bcrypt.gensalt())
            db.users.insert_one({'username': 'admin', 'password': hashed, 'role': 'admin'})
    except Exception as e:
        print(f"Error ensuring admin user: {e}")


def calculate_grade(marks):
    """Calculate grade based on marks percentage"""
    if isinstance(marks, str):
        try:
            marks = float(marks)
        except ValueError:
            return 'N/A'
            
    try:
        marks = float(marks)
        if not (0 <= marks <= 100):
            return 'N/A'
    except (TypeError, ValueError):
        return 'N/A'
    
    if marks >= 90:
        return 'A+'
    elif marks >= 80:
        return 'A'
    elif marks >= 70:
        return 'B'
    elif marks >= 60:
        return 'C'
    elif marks >= 50:
        return 'D'
    else:
        return 'F'

def generate_performance_chart(marks_data):
    """Generate a performance distribution chart"""
    try:
        static_dir = os.path.join(app.static_folder)
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
        
        grades = []
        for mark in marks_data:
            if 'grade' in mark:
                grades.append(mark['grade'])
        
        grade_counts = {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0, 'N/A': 0}
        
        for grade in grades:
            if grade in grade_counts:
                grade_counts[grade] += 1
        
        plt.figure(figsize=(10, 6))
        plt.bar(grade_counts.keys(), grade_counts.values(), color='skyblue')
        plt.title('Grade Distribution')
        plt.xlabel('Grades')
        plt.ylabel('Number of Students')
        plt.tight_layout()
        
        chart_path = os.path.join(static_dir, 'chart.png')
        plt.savefig(chart_path)
        plt.close()
        
        return True
    except Exception as e:
        print(f"Error generating chart: {e}")
        return False


def create_notification(student_roll_no, message):
    """Create a notification for a student.

    Stored in the 'notifications' collection as unread (read=False).
    """
    try:
        g.db.notifications.insert_one({
            'student_id': student_roll_no,
            'message': message,
            'read': False,
            'created_at': datetime.now(),
        })
    except Exception as e:
        # Don't break the main flow if notifications fail
        print(f"Error creating notification: {e}")


def allowed_avatar_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


# Login required decorator
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Routes
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password')
            return render_template('login.html')
        
        try:
            user = g.db.users.find_one({'username': username})
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
                session['username'] = username
                session['role'] = user.get('role', 'student')
                flash('Login successful!')
                return redirect(url_for('dashboard'))
            
            flash('Invalid username or password')
        except Exception as e:
            print(f"Login error: {e}")
            flash('Login error. Please try again.')
    
    return render_template('login.html')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page for viewing info and uploading avatar."""
    username = session.get('username')
    role = session.get('role')
    if not username:
        return redirect(url_for('login'))

    student_doc = None
    if role == 'student':
        student_doc = g.db.students.find_one({'roll_no': username})

    avatar_url = None
    if student_doc and student_doc.get('avatar_path'):
        avatar_url = url_for('static', filename=student_doc['avatar_path'])

    if request.method == 'POST' and role == 'student':
        file = request.files.get('avatar')
        if file and file.filename and allowed_avatar_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{username}_avatar.{ext}")
            save_path = os.path.join(AVATAR_FOLDER, filename)
            file.save(save_path)
            rel_path = os.path.join('avatars', filename).replace('\\', '/')
            g.db.students.update_one({'roll_no': username}, {'$set': {'avatar_path': rel_path}})
            avatar_url = url_for('static', filename=rel_path)
            flash('Avatar updated successfully')
        else:
            flash('Please upload a valid image (png, jpg, jpeg, gif)', 'error')

    return render_template('profile.html', username=username, role=role, student=student_doc, avatar_url=avatar_url)


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_pw = request.form.get('current_password') or ''
        new_pw = request.form.get('new_password') or ''
        confirm_pw = request.form.get('confirm_password') or ''

        if not current_pw or not new_pw or not confirm_pw:
            flash('Please fill all password fields', 'error')
            return redirect(url_for('change_password'))

        if new_pw != confirm_pw:
            flash('New passwords do not match', 'error')
            return redirect(url_for('change_password'))

        user = g.db.users.find_one({'username': username})
        if not user or not bcrypt.checkpw(current_pw.encode('utf-8'), user['password']):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('change_password'))

        hashed = bcrypt.hashpw(new_pw.encode('utf-8'), bcrypt.gensalt())
        g.db.users.update_one({'_id': user['_id']}, {'$set': {'password': hashed}})
        flash('Password updated successfully')
        return redirect(url_for('profile'))

    return render_template('change_password.html', username=username)


@app.route('/dashboard')
@login_required
def dashboard():
    # Admin users see a separate dashboard
    if session.get('role') == 'admin':
        try:
            student_count = g.db.students.count_documents({})
            course_count = g.db.courses.count_documents({})
            marks_count = g.db.marks.count_documents({})

            # Build eligibility & grade data for widgets
            from collections import defaultdict
            per_student = defaultdict(lambda: {
                'total_internal': 0.0,
                'count': 0,
                'name': '',
                'roll_no': '',
                'eligible': True,
            })

            marks_cursor = g.db.marks.find({})
            for mark in marks_cursor:
                roll_no = mark.get('student_id')
                if not roll_no:
                    continue
                info = per_student[roll_no]
                info['total_internal'] += float(mark.get('marks', 0) or 0)
                info['count'] += 1
                if not info['name']:
                    stu = g.db.students.find_one({'roll_no': roll_no}, {'name': 1}) or {}
                    info['name'] = stu.get('name', 'Unknown')
                    info['roll_no'] = roll_no
                if mark.get('eligibility') == 'ineligible':
                    info['eligible'] = False

            eligible_students = 0
            ineligible_students = 0
            grade_counts = {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0, 'N/A': 0}
            top_students = []

            for roll_no, info in per_student.items():
                if info['count'] == 0:
                    continue
                avg_internal = info['total_internal'] / info['count']  # 0-50
                pct = (avg_internal / 50.0) * 100.0
                grade = calculate_grade(pct)
                if grade not in grade_counts:
                    grade_counts['N/A'] += 1
                else:
                    grade_counts[grade] += 1

                if info['eligible']:
                    eligible_students += 1
                else:
                    ineligible_students += 1

                top_students.append({
                    'student_name': info['name'],
                    'roll_no': roll_no,
                    'average': round(pct, 2),
                })

            top_students.sort(key=lambda x: x['average'], reverse=True)
            top_students = top_students[:5]
        except Exception as e:
            print(f"Error loading admin dashboard stats: {e}")
            student_count = course_count = marks_count = 0
            eligible_students = ineligible_students = 0
            grade_counts = {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0, 'N/A': 0}
            top_students = []

        return render_template(
            'admin_dashboard.html',
            username=session.get('username'),
            student_count=student_count,
            course_count=course_count,
            marks_count=marks_count,
            eligible_students=eligible_students,
            ineligible_students=ineligible_students,
            grade_counts=grade_counts,
            top_students=top_students,
        )

    # Simple in-code timetable matching time_table.html for students
    timetable = {
        'Monday': [
            'Professional Competency Development',
            'Professional Competency Development',
            'BREAK',
            'Design and Analysis of Algorithm',
            'Web Technology',
            'LUNCH BREAK',
            'Mathematics - III',
            'Computer Organization & Architecture',
            'BREAK',
            'Web Technology Lab',
        ],
        'Tuesday': [
            'Design and Analysis of Algorithm Lab',
            'Design and Analysis of Algorithm Lab',
            'BREAK',
            'Professional Coding Practice',
            'Professional Coding Practice',
            'LUNCH BREAK',
            'Hands on Python Lab',
            'Hands on Python Lab',
            'BREAK',
            'Mathematics - III',
        ],
        'Wednesday': [
            'Professional Coding Practice',
            'Professional Coding Practice',
            'BREAK',
            'Mathematics - III',
            'Club Activity',
            'LUNCH BREAK',
            'Mathematics - III',
            'Computer Organization & Architecture',
            'BREAK',
            'Web Technology Lab',
        ],
        'Thursday': [
            'Computer Organization & Architecture',
            'Mentor Mentee Meeting',
            'BREAK',
            'Hands on C++ Lab',
            'Hands on C++ Lab',
            'LUNCH BREAK',
            'Hands on Python Lab',
            'Hands on Python Lab',
            'BREAK',
            'Design and Analysis of Algorithm',
        ],
        'Friday': [
            'Web Technology',
            'Web Technology',
            'BREAK',
            'Computer Organization & Architecture',
            'Design and Analysis of Algorithm',
            'LUNCH BREAK',
            'NOSQL Database with MangoDB',
            'NOSQL Database with MangoDB',
            'BREAK',
            'Professional Competency Development',
        ],
    }

    time_slots = [
        '08:00 - 08:55',
        '08:55 - 09:50',
        '09:50 - 10:10 BREAK',
        '10:10 - 11:05',
        '11:05 - 12:00',
        '12:00 - 01:00 LUNCH BREAK',
        '01:00 - 01:50',
        '01:50 - 02:40',
        '02:40 - 02:55 BREAK',
        '02:55 - 03:45',
    ]

    today_name = date.today().strftime('%A')
    today_schedule = timetable.get(today_name)
    schedule_rows = []
    if today_schedule:
        schedule_rows = list(zip(time_slots, today_schedule))

    try:
        student_count = g.db.students.count_documents({})
        course_count = g.db.courses.count_documents({})

        # Fetch recent notifications for this student (read and unread)
        notifications = list(
            g.db.notifications.find({'student_id': session.get('username')})
            .sort('created_at', -1)
            .limit(10)
        )
        
        return render_template(
            'dashboard.html',
            username=session.get('username'),
            student_count=student_count,
            course_count=course_count,
            today_name=today_name,
            time_slots=time_slots,
            today_schedule=today_schedule,
            schedule_rows=schedule_rows,
            notifications=notifications,
        )
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template(
            'dashboard.html',
            username=session.get('username'),
            student_count=0,
            course_count=0,
            today_name=today_name,
            time_slots=time_slots,
            today_schedule=today_schedule,
            schedule_rows=schedule_rows,
            notifications=[],
        )

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.')
    return redirect(url_for('login'))

@app.route('/students')
@login_required
def students():
    try:
        students_list = list(g.db.students.find({}))
        # Convert ObjectId to string for JSON serialization
        for student in students_list:
            student['_id'] = str(student['_id'])
        return render_template('students.html', students=students_list)
    except Exception as e:
        print(f"Error fetching students: {e}")
        flash('Error loading students')
        return render_template('students.html', students=[])

@app.route('/view-students')
@login_required
def view_students():
    try:
        students_list = list(g.db.students.find({}))
        for student in students_list:
            student['_id'] = str(student['_id'])
            # Get marks for this student
            student_marks = list(g.db.marks.find({'student_id': student.get('roll_no')}))
            # Initialize marks array
            student['marks'] = []
            student['total'] = 0
            student['percentage'] = 0
            student['grade'] = 'N/A'
            student['cgpa'] = 0.0
            
            # Sort marks by course code for consistent display
            student_marks.sort(key=lambda x: x.get('course_code', ''))
            
            # Calculate totals and averages if marks exist
            if student_marks:
                total_marks = sum(mark.get('marks', 0) for mark in student_marks)
                avg_marks = total_marks / len(student_marks) if len(student_marks) > 0 else 0
                # Only show the first 3 course marks in the table (CA1, CA2, CA3)
                student['marks'] = [mark.get('marks', 0) for mark in student_marks[:3]]
                student['total'] = total_marks
                student['percentage'] = avg_marks
                student['grade'] = calculate_grade(avg_marks)
                # CGPA calculation (assuming 10-point scale)
                student['cgpa'] = avg_marks / 10.0
                
            # Pad marks array to match SUBJECTS count (3 subjects only)
            while len(student['marks']) < 3:
                student['marks'].append(0)
                
        return render_template('view_students.html', students=students_list, SUBJECTS=3)
    except Exception as e:
        print(f"Error fetching students: {e}")
        flash('Error loading students')
        return render_template('view_students.html', students=[], SUBJECTS=3)


@app.route('/admin/reports')
@login_required
def admin_reports():
    """Admin reports dashboard: exports and per-student report links."""
    if session.get('role') != 'admin':
        flash('Reports are available only for admin users')
        return redirect(url_for('dashboard'))

    try:
        students_list = list(g.db.students.find({}))
        for student in students_list:
            student['_id'] = str(student['_id'])

        courses_list = list(g.db.courses.find({}))
        for course in courses_list:
            course['_id'] = str(course['_id'])

        return render_template('admin_reports.html', students=students_list, courses=courses_list)
    except Exception as e:
        print(f"Error loading admin reports: {e}")
        flash('Error loading reports page')
        return render_template('admin_reports.html', students=[], courses=[])


@app.route('/admin/export/students.csv')
@login_required
def export_students_csv():
    """Export aggregated student performance to CSV (admin only)."""
    if session.get('role') != 'admin':
        flash('Export is available only for admin users')
        return redirect(url_for('dashboard'))

    dept = request.args.get('department')
    query = {}
    if dept:
        query['department'] = dept

    try:
        students_cursor = g.db.students.find(query)
        output = io.StringIO()
        writer = csv.writer(output)
        header = ['Roll No', 'Name', 'Email', 'Department', 'Total Internal (all courses)', 'Average (0-50)', 'Grade', 'CGPA']
        writer.writerow(header)

        for student in students_cursor:
            roll_no = student.get('roll_no')
            student_marks = list(g.db.marks.find({'student_id': roll_no}))
            total_marks = sum(m.get('marks', 0) for m in student_marks) if student_marks else 0.0
            avg_marks = (total_marks / len(student_marks)) if student_marks else 0.0
            grade = calculate_grade(avg_marks)
            cgpa = avg_marks / 10.0

            writer.writerow([
                roll_no,
                student.get('name', ''),
                student.get('email', ''),
                student.get('department', ''),
                round(total_marks, 2),
                round(avg_marks, 2),
                grade,
                f"{cgpa:.2f}",
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-Disposition": "attachment; filename=students_report.csv"},
        )
    except Exception as e:
        print(f"Error exporting students CSV: {e}")
        flash('Error exporting students CSV')
        return redirect(url_for('admin_reports'))


@app.route('/admin/export/marks.csv')
@login_required
def export_marks_csv():
    """Export marks (optionally filtered by course_code) to CSV."""
    if session.get('role') != 'admin':
        flash('Export is available only for admin users')
        return redirect(url_for('dashboard'))

    course_code = request.args.get('course_code')
    query = {}
    if course_code:
        query['course_code'] = course_code

    try:
        marks_cursor = g.db.marks.find(query)
        output = io.StringIO()
        writer = csv.writer(output)
        header = ['Roll No', 'Course Code', 'CA1', 'CA2', 'CA3', 'Internal Total (0-50)', 'Eligibility', 'Updated At']
        writer.writerow(header)

        for mark in marks_cursor:
            writer.writerow([
                mark.get('student_id', ''),
                mark.get('course_code', ''),
                mark.get('ca1', 0),
                mark.get('ca2', 0),
                mark.get('ca3', 0),
                round(mark.get('marks', 0), 2),
                mark.get('eligibility', ''),
                mark.get('updated_at', '').isoformat() if isinstance(mark.get('updated_at'), datetime) else '',
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-Disposition": "attachment; filename=marks_report.csv"},
        )
    except Exception as e:
        print(f"Error exporting marks CSV: {e}")
        flash('Error exporting marks CSV')
        return redirect(url_for('admin_reports'))


@app.route('/admin/student-report/<roll_no>')
@login_required
def admin_student_report(roll_no):
    """Detailed printable report for a single student (admin only)."""
    if session.get('role') != 'admin':
        flash('Reports are available only for admin users')
        return redirect(url_for('dashboard'))

    try:
        student = g.db.students.find_one({'roll_no': roll_no})
        if not student:
            flash('Student not found')
            return redirect(url_for('admin_reports'))

        # Fetch marks for this student
        marks_cursor = list(g.db.marks.find({'student_id': roll_no}))
        marks_rows = []
        total_internal_all = 0.0

        for mark in marks_cursor:
            course = g.db.courses.find_one({'course_code': mark.get('course_code')})
            course_name = course.get('course_name', mark.get('course_code', 'Unknown')) if course else mark.get('course_code', 'Unknown')

            raw_ca1 = mark.get('ca1', 0)
            raw_ca2 = mark.get('ca2', 0)
            raw_ca3 = mark.get('ca3', 0)

            ca1_internal = (raw_ca1 / 50.0) * 15.0
            ca2_internal = (raw_ca2 / 50.0) * 15.0
            ca3_internal = float(raw_ca3)
            total_internal = ca1_internal + ca2_internal + ca3_internal
            total_internal_all += total_internal

            eligibility = mark.get('eligibility', '')

            marks_rows.append({
                'course_code': mark.get('course_code', ''),
                'course_name': course_name,
                'ca1_raw': raw_ca1,
                'ca2_raw': raw_ca2,
                'ca3_raw': raw_ca3,
                'ca1_internal': round(ca1_internal, 2),
                'ca2_internal': round(ca2_internal, 2),
                'ca3_internal': round(ca3_internal, 2),
                'total_internal': round(total_internal, 2),
                'eligibility': eligibility,
            })

        if marks_rows:
            avg_internal = total_internal_all / len(marks_rows)
        else:
            avg_internal = 0.0

        overall_grade = calculate_grade(avg_internal)
        cgpa = avg_internal / 10.0

        # Attendance percentage placeholder (no real data stored yet)
        attendance_percent = None

        return render_template(
            'admin_student_report.html',
            student=student,
            marks=marks_rows,
            avg_internal=avg_internal,
            overall_grade=overall_grade,
            cgpa=cgpa,
            attendance_percent=attendance_percent,
        )
    except Exception as e:
        print(f"Error building student report: {e}")
        flash('Error loading student report')
        return redirect(url_for('admin_reports'))


@app.route('/notifications')
@login_required
def student_notifications():
    """Show full notifications list for the logged-in student."""
    if session.get('role') != 'student':
        return redirect(url_for('dashboard'))

    try:
        username = session.get('username')
        notifications = list(
            g.db.notifications.find({'student_id': username})
            .sort('created_at', -1)
        )

        # Mark all as read when visiting the notifications page
        g.db.notifications.update_many(
            {'student_id': username, 'read': False},
            {'$set': {'read': True}}
        )

        return render_template('student_notifications.html', notifications=notifications)
    except Exception as e:
        print(f"Error loading student notifications: {e}")
        flash('Error loading notifications')
        return render_template('student_notifications.html', notifications=[])


@app.route('/admin/notifications', methods=['GET', 'POST'])
@login_required
def admin_notifications():
    """Simple admin UI to send notifications to students."""
    if session.get('role') != 'admin':
        flash('Notifications admin is available only for admin users')
        return redirect(url_for('dashboard'))

    try:
        if request.method == 'POST':
            audience = request.form.get('audience')  # all, roll_no, department
            message = (request.form.get('message') or '').strip()
            roll_no = (request.form.get('roll_no') or '').strip()
            department = (request.form.get('department') or '').strip()

            if not message:
                flash('Message is required', 'error')
                return redirect(url_for('admin_notifications'))

            query = {}
            if audience == 'roll_no' and roll_no:
                query['roll_no'] = roll_no
            elif audience == 'department' and department:
                query['department'] = department
            elif audience == 'all':
                query = {}
            else:
                flash('Please choose a valid audience and value', 'error')
                return redirect(url_for('admin_notifications'))

            students_cursor = g.db.students.find(query)
            count = 0
            for student in students_cursor:
                sid = student.get('roll_no')
                if not sid:
                    continue
                create_notification(sid, message)
                count += 1

            flash(f'Notification sent to {count} student(s)')
            return redirect(url_for('admin_notifications'))

        # GET: build departments list and recent notifications
        departments = sorted({
            s.get('department') for s in g.db.students.find({}, {'department': 1}) if s.get('department')
        })
        recent_notifications = list(
            g.db.notifications.find({}).sort('created_at', -1).limit(20)
        )
        return render_template(
            'admin_notifications.html',
            departments=departments,
            notifications=recent_notifications,
        )
    except Exception as e:
        print(f"Error in admin_notifications: {e}")
        flash('Error loading notifications admin')
        return render_template('admin_notifications.html', departments=[], notifications=[])

@app.route('/search-student', methods=['GET', 'POST'])
@login_required
def search_student():
    if request.method == 'POST':
        search_term = request.form.get('search', '').strip()
        try:
            students = list(g.db.students.find({
                '$or': [
                    {'name': {'$regex': search_term, '$options': 'i'}},
                    {'roll_no': {'$regex': search_term, '$options': 'i'}},
                    {'email': {'$regex': search_term, '$options': 'i'}}
                ]
            }))
            for student in students:
                student['_id'] = str(student['_id'])
            return render_template('search_student.html', students=students, search_term=search_term)
        except Exception as e:
            print(f"Error searching students: {e}")
            flash('Error searching students')
            return render_template('search_student.html', students=[], search_term=search_term)
    return render_template('search_student.html', students=None)

@app.route('/delete-student/<roll_no>', methods=['POST', 'GET'])
@login_required
def delete_student(roll_no):
    try:
        # Find student first to verify existence
        student = g.db.students.find_one({'roll_no': roll_no})
        if not student:
            flash('Student not found')
            return redirect(url_for('view_students'))

        # Delete student
        g.db.students.delete_one({'roll_no': roll_no})
        
        # Delete associated marks
        g.db.marks.delete_many({'student_id': roll_no})
        
        flash('Student and associated marks deleted successfully')
    except Exception as e:
        print(f"Error deleting student: {e}")
        flash('Error deleting student')
    return redirect(url_for('view_students'))

@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    # Only admin can add students
    if session.get('role') != 'admin':
        flash('Only admin can add students')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            student_data = {
                'name': request.form.get('name', '').strip(),
                'email': request.form.get('email', '').strip(),
                'roll_no': request.form.get('roll_no', '').strip(),
                'department': request.form.get('department', '').strip()
            }
            
            if not all([student_data['name'], student_data['email'], student_data['roll_no']]):
                flash('Please fill all required fields')
                return render_template('add_student.html')
            
            existing_student = g.db.students.find_one({'roll_no': student_data['roll_no']})
            if existing_student:
                flash('Roll no already exists!')
                return render_template('add_student.html')
            
            existing_email = g.db.students.find_one({'email': student_data['email']})
            if existing_email:
                flash('Email already exists!')
                return render_template('add_student.html')
            
            # Insert student document
            g.db.students.insert_one(student_data)

            # Also create/login user for this student if not existing
            existing_user = g.db.users.find_one({'username': student_data['roll_no']})
            if not existing_user:
                # Default student password (same for all students initially)
                default_pw = 'password123'
                hashed_pw = bcrypt.hashpw(default_pw.encode('utf-8'), bcrypt.gensalt())
                g.db.users.insert_one({
                    'username': student_data['roll_no'],
                    'password': hashed_pw,
                    'role': 'student'
                })

            flash('Student added successfully! Login username = roll number, password = "password123"')
            return redirect(url_for('students'))
        except Exception as e:
            print(f"Error adding student: {e}")
            flash('Error adding student')
    
    return render_template('add_student.html')

@app.route('/courses')
@login_required
def courses():
    try:
        courses_list = list(g.db.courses.find({}))
        for course in courses_list:
            course['_id'] = str(course['_id'])
        return render_template('courses.html', courses=courses_list)
    except Exception as e:
        print(f"Error fetching courses: {e}")
        flash('Error loading courses')
        return render_template('courses.html', courses=[])

@app.route('/add-course', methods=['GET', 'POST'])
@login_required
def add_course():
    if request.method == 'POST':
        try:
            course_data = {
                'course_code': request.form.get('course_code', '').strip(),
                'course_name': request.form.get('course_name', '').strip(),
                'credits': request.form.get('credits', '0').strip(),
                'department': request.form.get('department', '').strip()
            }
            
            if not all([course_data['course_code'], course_data['course_name']]):
                flash('Please fill all required fields')
                return render_template('add_course.html')
            
            try:
                course_data['credits'] = int(course_data['credits'])
            except ValueError:
                course_data['credits'] = 0
            
            existing_course = g.db.courses.find_one({'course_code': course_data['course_code']})
            if existing_course:
                flash('Course code already exists!')
                return render_template('add_course.html')
            
            g.db.courses.insert_one(course_data)
            flash('Course added successfully!')
            return redirect(url_for('courses'))
        except Exception as e:
            print(f"Error adding course: {e}")
            flash('Error adding course')
    
    return render_template('add_course.html')

@app.route('/delete-course/<course_code>', methods=['POST'])
@login_required
def delete_course(course_code):
    try:
        result = g.db.courses.delete_one({'course_code': course_code})
        if result.deleted_count:
            return jsonify({'success': True, 'message': 'Course deleted successfully'})
        return jsonify({'success': False, 'message': 'Course not found'}), 404
    except Exception as e:
        print(f"Error deleting course: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# MARKS ROUTES
def _build_marks_context(student_roll_no=None):
    """Helper to compute marks_data and top_students for marks/visualization views.

    If student_roll_no is provided, only that student's marks are loaded; otherwise all marks.
    """
    # Build query: restrict to a single student if roll number is given
    marks_query = {}
    if student_roll_no:
        marks_query['student_id'] = student_roll_no

    marks_data_raw = list(g.db.marks.find(marks_query))
    marks_data = []

    for mark in marks_data_raw:
        mark['_id'] = str(mark['_id'])
        student = g.db.students.find_one({'roll_no': mark.get('student_id')})
        course = g.db.courses.find_one({'course_code': mark.get('course_code')})
        # Raw CA scores (CA1 & CA2: 0-50, CA3: 0-20)
        raw_ca1 = mark.get('ca1', 0)
        raw_ca2 = mark.get('ca2', 0)
        raw_ca3 = mark.get('ca3', 0)
        subjects = {
            'ca1': raw_ca1,
            'ca2': raw_ca2,
            'ca3': raw_ca3
        }
        # Scale to internal marks: CA1, CA2 out of 15 each, CA3 out of 20 (total 50)
        ca1_internal = (raw_ca1 / 50.0) * 15.0
        ca2_internal = (raw_ca2 / 50.0) * 15.0
        ca3_internal = float(raw_ca3)              # already out of 20
        total_internal = ca1_internal + ca2_internal + ca3_internal  # 0-50
        percentage = (total_internal / 50.0 * 100.0) if total_internal else 0.0
        grade = calculate_grade(percentage)
        eligibility = 'eligible' if total_internal >= 25.0 else 'ineligible'
        marks_data.append({
            'student_name': student.get('name', 'Unknown') if student else 'Unknown',
            'roll_no': mark.get('student_id', 'Unknown'),
            'course_name': course.get('course_name', 'Unknown') if course else 'Unknown',
            'course_code': mark.get('course_code', 'Unknown'),
            'marks': round(total_internal, 2),      # total out of 50
            'subjects': subjects,                   # raw CA scores
            'average': round(percentage, 2),        # percentage out of 100
            'grade': grade,
            'eligibility': eligibility
        })

    # Generate performance chart
    try:
        generate_performance_chart(marks_data)
    except Exception as e:
        print(f"Error generating chart: {e}")

    # Compute top students by average (overall, across all courses)
    top_students = []
    try:
        # aggregate by student_id (roll_no)
        from collections import defaultdict
        agg = defaultdict(lambda: {'total_avg': 0.0, 'count': 0, 'name': '', 'roll_no': ''})
        for m in marks_data:
            key = m.get('roll_no')
            if not key:
                continue
            agg[key]['total_avg'] += m.get('average', 0.0)
            agg[key]['count'] += 1
            agg[key]['name'] = m.get('student_name', 'Unknown')
            agg[key]['roll_no'] = key

        for roll_no, info in agg.items():
            if info['count'] > 0:
                avg = info['total_avg'] / info['count']
                top_students.append({
                    'student_name': info['name'],
                    'roll_no': roll_no,
                    'average': round(avg, 2)
                })

        # sort descending by average and keep top 5
        top_students.sort(key=lambda x: x['average'], reverse=True)
        top_students = top_students[:5]
    except Exception as e:
        print(f"Error computing top students: {e}")

    return marks_data, top_students


@app.route('/marks')
@login_required
def marks():
    """Render the marks page with student performance data.

    - Admin accounts see all marks.
    - Student accounts see only marks for their own roll number (username).
    """
    try:
        username = session.get('username')
        student_roll_no = None

        if session.get('role') == 'student' and username:
            # For students, assume username is their roll number
            student_roll_no = username

        marks_data, top_students = _build_marks_context(student_roll_no=student_roll_no)
        return render_template('marks.html', marks=marks_data, top_students=top_students)
    except Exception as e:
        print(f"Error fetching marks: {e}")
        flash('Error loading marks data')
        return render_template('marks.html', marks=[], top_students=[])


@app.route('/visualization')
@login_required
def visualization():
    """Render only the visualization (top students + chart).

    Same visibility rules as /marks.
    """
    try:
        username = session.get('username')
        student_roll_no = None
        if session.get('role') == 'student' and username:
            student_roll_no = username

        marks_data, top_students = _build_marks_context(student_roll_no=student_roll_no)
        return render_template('visualization.html', top_students=top_students)
    except Exception as e:
        print(f"Error fetching data for visualization: {e}")
        flash('Error loading visualization data')
        return render_template('visualization.html', top_students=[])


@app.route('/my-performance')
@login_required
def my_performance():
    """Per-student performance analytics page.

    Only student accounts should access this; it shows their own marks,
    internal calculations and simple eligibility hints per subject.
    """
    if session.get('role') != 'student':
        # Non-students are redirected to the generic marks page
        return redirect(url_for('marks'))

    try:
        roll_no = session.get('username')
        if not roll_no:
            flash('Session expired. Please log in again.')
            return redirect(url_for('login'))

        # Fetch this student's marks
        raw_marks = list(g.db.marks.find({'student_id': roll_no}))
        subjects_data = []

        labels = []
        ca1_raw_list = []
        ca2_raw_list = []
        ca3_raw_list = []

        ELIGIBILITY_TOTAL = 25.0  # internal marks out of 50
        CA3_MAX_INTERNAL = 20.0

        for mark in raw_marks:
            course = g.db.courses.find_one({'course_code': mark.get('course_code')})
            course_name = course.get('course_name', mark.get('course_code', 'Unknown')) if course else mark.get('course_code', 'Unknown')

            raw_ca1 = mark.get('ca1', 0)
            raw_ca2 = mark.get('ca2', 0)
            raw_ca3 = mark.get('ca3', 0)

            ca1_internal = (raw_ca1 / 50.0) * 15.0
            ca2_internal = (raw_ca2 / 50.0) * 15.0
            ca3_internal = float(raw_ca3)
            total_internal = ca1_internal + ca2_internal + ca3_internal

            eligibility = mark.get('eligibility')
            if eligibility not in ('eligible', 'ineligible'):
                eligibility = 'eligible' if total_internal >= ELIGIBILITY_TOTAL else 'ineligible'

            needed_ca3_internal = ELIGIBILITY_TOTAL - (ca1_internal + ca2_internal)
            needed_ca3_internal = max(0.0, min(CA3_MAX_INTERNAL, needed_ca3_internal))

            subjects_data.append({
                'course_name': course_name,
                'course_code': mark.get('course_code', ''),
                'ca1_raw': raw_ca1,
                'ca2_raw': raw_ca2,
                'ca3_raw': raw_ca3,
                'ca1_internal': round(ca1_internal, 2),
                'ca2_internal': round(ca2_internal, 2),
                'ca3_internal': round(ca3_internal, 2),
                'total_internal': round(total_internal, 2),
                'eligibility': eligibility,
                'needed_ca3_internal': round(needed_ca3_internal, 2),
            })

            labels.append(course_name)
            ca1_raw_list.append(raw_ca1)
            ca2_raw_list.append(raw_ca2)
            ca3_raw_list.append(raw_ca3)

        return render_template(
            'my_performance.html',
            subjects=subjects_data,
            chart_labels=labels,
            chart_ca1=ca1_raw_list,
            chart_ca2=ca2_raw_list,
            chart_ca3=ca3_raw_list,
        )
    except Exception as e:
        print(f"Error loading my performance page: {e}")
        flash('Error loading performance data')
        return render_template('my_performance.html', subjects=[], chart_labels=[], chart_ca1=[], chart_ca2=[], chart_ca3=[])


@app.route('/add-marks', methods=['GET', 'POST'])
@login_required
def add_marks():
    """Add or update marks for a student"""
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                roll_no = data.get('roll_no')
                course_code = data.get('course_code')
                ca1 = int(data.get('ca1', 0))
                ca2 = int(data.get('ca2', 0))
                ca3 = int(data.get('ca3', 0))
            else:
                roll_no = request.form.get('roll_no')
                course_code = request.form.get('course_code')
                ca1 = int(request.form.get('ca1', 0))
                ca2 = int(request.form.get('ca2', 0))
                ca3 = int(request.form.get('ca3', 0))

            # Raw totals (CA1 & CA2: 0-50, CA3: 0-20)
            # We'll store scaled internal total separately

            if not all([roll_no, course_code]):
                if request.is_json:
                    return {'success': False, 'message': 'Please fill all required fields'}, 400
                flash('Please fill all required fields')
                return redirect(url_for('add_marks'))

            # Validate student exists
            student = g.db.students.find_one({'roll_no': roll_no})
            if not student:
                if request.is_json:
                    return {'success': False, 'message': 'Student not found'}, 400
                flash('Student not found')
                return redirect(url_for('add_marks'))

            # Validate course exists
            course = g.db.courses.find_one({'course_code': course_code})
            if not course:
                if request.is_json:
                    return {'success': False, 'message': 'Course not found'}, 400
                flash('Course not found')
                return redirect(url_for('add_marks'))

            # Validate CA marks: CA1 & CA2 in [0,50], CA3 in [0,20]
            try:
                ca1 = int(ca1)
                ca2 = int(ca2)
                ca3 = int(ca3)
            except ValueError:
                if request.is_json:
                    return {'success': False, 'message': 'Invalid marks value'}, 400
                flash('Invalid marks value')
                return redirect(url_for('add_marks'))

            if not (0 <= ca1 <= 50):
                msg = 'CA1 marks must be between 0 and 50'
                if request.is_json:
                    return {'success': False, 'message': msg}, 400
                flash(msg)
                return redirect(url_for('add_marks'))

            if not (0 <= ca2 <= 50):
                msg = 'CA2 marks must be between 0 and 50'
                if request.is_json:
                    return {'success': False, 'message': msg}, 400
                flash(msg)
                return redirect(url_for('add_marks'))

            if not (0 <= ca3 <= 20):
                msg = 'CA3 marks must be between 0 and 20'
                if request.is_json:
                    return {'success': False, 'message': msg}, 400
                flash(msg)
                return redirect(url_for('add_marks'))

            # Scale CA scores to internal total out of 50
            ca1_internal = (ca1 / 50.0) * 15.0
            ca2_internal = (ca2 / 50.0) * 15.0
            ca3_internal = float(ca3)              # out of 20
            total_internal = ca1_internal + ca2_internal + ca3_internal  # 0-50

            # Calculate grade based on percentage (0-100 scale)
            percentage = (total_internal / 50.0 * 100.0) if total_internal else 0.0
            grade = calculate_grade(percentage)
            eligibility = 'eligible' if total_internal >= 25.0 else 'ineligible'

            # Check if marks already exist for this student and course
            existing_marks = g.db.marks.find_one({
                'student_id': roll_no,
                'course_code': course_code
            })

            if existing_marks:
                # Update existing marks
                g.db.marks.update_one(
                    {'_id': existing_marks['_id']},
                    {'$set': {
                        'marks': total_internal,
                        'ca1': ca1,
                        'ca2': ca2,
                        'ca3': ca3,
                        'grade': grade,
                        'eligibility': eligibility,
                        'updated_at': datetime.now()
                    }}
                )
                # Notification for updated marks
                create_notification(roll_no, f"Your marks for {course_code} have been updated.")
                if request.is_json:
                    return {'success': True, 'message': 'Marks updated successfully!'}
                flash('Marks updated successfully!')
            else:
                # Insert new marks
                marks_data = {
                    'student_id': roll_no,  # Using roll_no as student identifier
                    'course_code': course_code,
                    'marks': total_internal,
                    'ca1': ca1,
                    'ca2': ca2,
                    'ca3': ca3,
                    'grade': grade,
                    'eligibility': eligibility,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                g.db.marks.insert_one(marks_data)
                # Notification for new marks
                create_notification(roll_no, f"New marks have been added for {course_code}.")
                if request.is_json:
                    return {'success': True, 'message': 'Marks added successfully!'}
                flash('Marks added successfully!')

            if request.is_json:
                return {'success': True, 'message': 'Marks processed successfully!'}
            return redirect(url_for('marks'))

        except Exception as e:
            print(f"Error adding marks: {e}")
            if request.is_json:
                return {'success': False, 'message': 'Error adding marks'}, 500
            flash('Error adding marks')
    
    # For GET request, get students and courses for dropdown
    try:
        students = list(g.db.students.find({}, {'name': 1, 'roll_no': 1}))
        courses = list(g.db.courses.find({}, {'course_name': 1, 'course_code': 1}))
        
        for student in students:
            student['_id'] = str(student['_id'])
        for course in courses:
            course['_id'] = str(course['_id'])
            
        return render_template('add_marks.html', students=students, courses=courses)
    except Exception as e:
        print(f"Error loading add marks page: {e}")
        flash('Error loading page')
        return render_template('add_marks.html', students=[], courses=[])

@app.route('/api/students-min')
@login_required
def api_students_min():
    """Return minimal student list (roll_no + name) for dropdowns."""
    try:
        students = list(g.db.students.find({}, {'_id': 0, 'roll_no': 1, 'name': 1}))
        return jsonify({'success': True, 'data': students})
    except Exception as e:
        print(f"Error in students-min API: {e}")
        return jsonify({'success': False, 'message': 'Error loading students'}), 500


@app.route('/api/courses-min')
@login_required
def api_courses_min():
    """Return minimal courses list (course_code + course_name) for dropdowns."""
    try:
        courses = list(g.db.courses.find({}, {'_id': 0, 'course_code': 1, 'course_name': 1}))
        return jsonify({'success': True, 'data': courses})
    except Exception as e:
        print(f"Error in courses-min API: {e}")
        return jsonify({'success': False, 'message': 'Error loading courses'}), 500


@app.route('/api/marks', methods=['GET', 'POST'])
@login_required
def handle_marks_api():
    """API endpoint for marks operations"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            required_fields = ['roll_no', 'course_code', 'marks']
            if not all(field in data for field in required_fields):
                return jsonify({
                    'success': False,
                    'message': f'Missing required fields: {required_fields}'
                }), 400
            
            # Validate student and course
            student = g.db.students.find_one({'roll_no': data['roll_no']})
            if not student:
                return jsonify({'success': False, 'message': 'Student not found'}), 404
                
            course = g.db.courses.find_one({'course_code': data['course_code']})
            if not course:
                return jsonify({'success': False, 'message': 'Course not found'}), 404
            
            # Validate marks
            try:
                marks = float(data['marks'])
                if not (0 <= marks <= 100):
                    return jsonify({'success': False, 'message': 'Marks must be between 0 and 100'}), 400
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid marks value'}), 400
            
            # Prepare marks data
            marks_data = {
                'student_id': data['roll_no'],  # Using roll_no as student identifier
                'course_code': data['course_code'],
                'marks': marks,
                'grade': calculate_grade(marks),
                'updated_at': datetime.now()
            }
            
            # Check for existing record
            existing = g.db.marks.find_one({
                'student_id': data['roll_no'],
                'course_code': data['course_code']
            })
            
            if existing:
                # Update existing
                g.db.marks.update_one(
                    {'_id': existing['_id']},
                    {'$set': marks_data}
                )
                message = 'Marks updated successfully'
            else:
                # Insert new
                marks_data['created_at'] = marks_data['updated_at']
                g.db.marks.insert_one(marks_data)
                message = 'Marks added successfully'
            
            return jsonify({'success': True, 'message': message})
            
        else:  # GET request
            roll_no = request.args.get('roll_no')
            course_code = request.args.get('course_code')
            
            query = {}
            if roll_no:
                query['student_id'] = roll_no
            if course_code:
                query['course_code'] = course_code
            
            marks_data = list(g.db.marks.find(query))
            for mark in marks_data:
                mark['_id'] = str(mark['_id'])
            
            return jsonify({
                'success': True,
                'data': marks_data,
                'count': len(marks_data)
            })
    
    except Exception as e:
        print(f"Error in marks API: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/chart')
@login_required
def chart():
    """Serve the performance chart"""
    try:
        return send_from_directory(app.static_folder, 'chart.png')
    except Exception as e:
        print(f"Error serving chart: {e}")
        return jsonify({'error': 'Chart not found'}), 404

@app.route('/achievement-image')
@login_required
def achievement_image():
    """Serve the Hackathon achievement image from project root"""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_name = 'Hackathon X.jpg'
    if os.path.exists(os.path.join(root_dir, image_name)):
        return send_from_directory(root_dir, image_name)

    placeholder = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
      <rect width="1200" height="675" fill="#eef2ff"/>
      <circle cx="600" cy="260" r="100" fill="#2563eb"/>
      <path d="M550 260l35 35 70-80" fill="none" stroke="#fff" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="600" y="430" text-anchor="middle" font-family="Arial, sans-serif" font-size="48" fill="#1e293b">Hackathon Achievement</text>
      <text x="600" y="490" text-anchor="middle" font-family="Arial, sans-serif" font-size="26" fill="#64748b">Add Hackathon X.jpg to the project root to replace this placeholder.</text>
    </svg>"""
    return Response(placeholder, mimetype='image/svg+xml')

@app.route('/advanced-todo')
@login_required
def advanced_todo():
    """Advanced per-user to-do list page.

    Tasks are stored client-side (localStorage) but namespaced by the logged-in
    username so that different users do not see each other's tasks on
    the same device.
    """
    return render_template('advanced_todo.html', username=session.get('username'))

@app.route('/exam-timetable')
@login_required
def exam_timetable():
    """Show the third semester exam timetable image"""
    return render_template('exam_timetable.html')

@app.route('/student-achievements')
@login_required
def student_achievements():
    return render_template('student_achievements.html')

@app.route('/sports-meet')
@login_required
def sports_meet():
    """Detailed page for the Annual Sports Meet event."""
    return render_template('sports_meet.html')

@app.route('/guest-lecture')
@login_required
def guest_lecture():
    """Detailed page for the AI & Data Analytics guest lecture."""
    return render_template('guest_lecture.html')

# Other routes
@app.route('/time-table')
@login_required
def time_table():
    return render_template('time_table.html')

@app.route('/attendance-percentage')
@login_required
def attendance_percentage():
    return render_template('attendance percentage.html')

@app.route('/student-report-card')
@login_required
def student_report_card():
    return render_template('student_report_card.html')
# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    tb = traceback.format_exc()
    print(f"Internal server error: {error}\n{tb}")
    # Pass traceback to template for debugging (development only)
    return render_template('500.html', error=str(error), traceback=tb), 500

@app.errorhandler(Exception)
def handle_error(error):
    tb = traceback.format_exc()
    print(f"Unexpected error: {error}\n{tb}")
    return render_template('500.html', error=str(error), traceback=tb), 500

if __name__ == "__main__":
    # Print registered routes for debugging
    print("\nRegistered Routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    print("\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
