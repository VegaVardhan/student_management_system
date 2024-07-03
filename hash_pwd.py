import mysql.connector
from werkzeug.security import generate_password_hash

# Connect to the database
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="vegamysql24",
    database='sms')
cursor = connection.cursor()

# Fetch all users
cursor.execute("SELECT email, password FROM users")
users = cursor.fetchall()

# Hash the passwords and update the users table
for email, plain_password in users:
    hashed_password = generate_password_hash(plain_password)
    cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))

# Commit the changes
connection.commit()

# Close the connection
cursor.close()
connection.close()
