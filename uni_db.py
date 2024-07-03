from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import re,logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

def get_db_connection():
    mydb_connection=mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="vegamysql24",
    database='sms')
    return mydb_connection

# Configure logging
logging.basicConfig(level=logging.DEBUG)

#app.config['SECRET_KEY'] = 'your_secret_key'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:vegamysql24@localhost/sms'
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#db = SQLAlchemy(app)

@app.route('/',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']

        logging.debug(f"Attempting login for email: {email}")

        connection=get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and check_password_hash(user['password'], password):
            session['email'] = email
            logging.debug(f"Login successful for email: {email}")

            if re.match(r".*\.prof@gmail\.com$",email):
                logging.debug(f"Redirecting {email} to admin_details")
                return redirect(url_for('admin_details'))
            else:
                logging.debug(f"Redirecting {email} to student_details")
                return redirect(url_for('student_details'))
        
        else:
            logging.error("User not found or incorrect password")
            flash('User not found or incorrect password', 'error')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/student-details')
def student_details():
    if 'email' not in session:
        logging.debug("No email in session, redirecting to login")
        return redirect(url_for('login'))
    
    email=session['email']
    logging.debug(f"Fetching student details for email: {email}")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM studnt WHERE email = %s ", (email,))
    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        logging.error(f"Student details not found for email: {email}")
        flash('Student details not found','error')
        return redirect(url_for('login'))
    
    cursor.execute("""
                SELECT c.course_id, c.title 
                FROM course AS c
                JOIN studnt AS s ON c.dept_name = s.dept_name
                WHERE s.email = %s 
                   """,(email,))
    courses=cursor.fetchall()
    cursor.close()
    connection.close()
    
    logging.debug(f"Student details fetched successfully for email: {email}")
    return render_template('student.html',student=student,courses=courses)

@app.route('/enrolled-courses')
def enrolled_courses():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.course_id, c.title 
        FROM course AS c
        JOIN studnt AS s ON c.dept_name = s.dept_name
        WHERE s.email = %s
    """, (email,))
    courses = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(courses)

@app.route('/course-details/<course_id>')
def course_details(course_id):
    if 'email' not in session:
        logging.error("User not authenticated")
        return redirect(url_for('login'))
    
    email = session['email']
    logging.debug(f"Fetching course details for course_id: {course_id}, email: {email}")
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    query = """
    SELECT s.name, e.quiz1, e.midsem, e.quiz2, e.endsem, e.grade, s.email
    FROM studnt AS s
    JOIN takes AS e ON s.email = e.email
    WHERE e.course_id = %s 
    """
    try:
        cursor.execute(query, (course_id,))
        students = cursor.fetchall()
        logging.debug(f"Students data for course_id {course_id}: {students}")
    except mysql.connector.Error as err:
        logging.error(f"Error: {err}")
        cursor.close()
        connection.close()
        return jsonify({'error': 'Error fetching course details'}), 500
    
    cursor.close()
    connection.close()
    
    return jsonify(students)


@app.route('/admin-details')
def admin_details():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    email = session['email']
    return render_template('admin.html',email=email)


@app.route('/admin-data')
def admin_data():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM instructor WHERE email = %s", (email,))
    professor = cursor.fetchone()

    cursor.execute("""
    SELECT c.course_id, c.title 
    FROM course AS c
    JOIN teaches AS t ON c.course_id = t.course_id
    WHERE t.email = %s
    """, (email,))
    courses = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(professor=professor, courses=courses)

@app.route('/submit-marks/<course_id>', methods=['POST'])
def submit_marks(course_id):
    if 'email' not in session:
        return jsonify({'message': 'User not authenticated'}), 403

    data = request.json
    connection = get_db_connection()
    cursor = connection.cursor()

    for key, value in data.items():
        if value:
            exam_type, email = key.split('_')
            try:
                cursor.execute(f"""
                    UPDATE takes
                    SET {exam_type} = %s
                    WHERE email = %s AND course_id = %s
                """, (value, email, course_id))
            except mysql.connector.Error as err:
                logging.error(f"Error: {err}")
                connection.rollback()
                cursor.close()
                connection.close()
                return jsonify({'message': 'Error updating marks'}), 500

    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({'message': 'Marks updated successfully'})

if __name__ == '__main__':
    app.run(debug=True)