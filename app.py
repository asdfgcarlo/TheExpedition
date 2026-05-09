from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib
import random

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------------- DB CONFIG ----------------
app.config['MYSQL_HOST'] = 'sql12.freesqldatabase.com'
app.config['MYSQL_USER'] = 'sql12825863'
app.config['MYSQL_PASSWORD'] = 'HAFcXalj6m'
app.config['MYSQL_DB'] = 'sql12825863'

mysql = MySQL(app)


# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()

        if user:
            # ---------------- STORE SESSION ----------------
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            # ---------------- NORMALIZE ROLE ----------------
            role = user['role'].strip().lower()

            # ---------------- ROLE-BASED REDIRECT ----------------
            if role == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('dashboard'))

        else:
            error = "Invalid email or password"

    return render_template('index.html', error=error)


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (%s,%s,%s,%s)",
            (username, email, password, "user")
        )
        mysql.connection.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('dashboard.html', user=session.get('username'))


# ---------------- ADMIN (FIXED + RELIABLE) ----------------
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ---------------- GET USER FROM DB (SECURE ROLE CHECK) ----------------
    cursor.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()

    if not user:
        return redirect(url_for('login'))

    role = user['role'].strip().lower()

    if role != 'admin':
        return redirect(url_for('dashboard'))

    # ---------------- USERS LIST ----------------
    cursor.execute("SELECT id, username, email, role FROM users")
    users = cursor.fetchall()

    # ---------------- TOTAL USERS ----------------
    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cursor.fetchone()['total']
    # ---------------- BOOKINGS LIST ----------------
    cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
    bookings = cursor.fetchall()

    # ---------------- TOTAL BOOKINGS ----------------
    cursor.execute("SELECT COUNT(*) AS total FROM bookings")
    total_bookings = cursor.fetchone()['total']

    # ---------------- TOTAL INCOME ----------------
    cursor.execute("SELECT SUM(total) AS income FROM bookings")
    income_result = cursor.fetchone()
    total_income = income_result['income'] if income_result['income'] else 0

    # ---------------- RENDER ADMIN PAGE ----------------
    return render_template(
        'admin.html',
        users=users,
        bookings = bookings,
        total_users=total_users,
        total_bookings=total_bookings,
        total_income=total_income
    )
# ---------------- BOOK PAGE ----------------
@app.route('/book')
def book():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('book_now.html')


# ---------------- FILL UP + BOOKING ----------------
@app.route('/fillup/<flight>/<int:price>', methods=['GET', 'POST'])
def fillup(flight, price):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        contact = request.form['contact']
        pax = int(request.form['pax'])
        total = pax * price

        booking_ref = "FL" + str(random.randint(100000, 999999))

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO bookings 
            (user_id, flight, contact, pax, price, total, booking_ref)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            flight,
            contact,
            pax,
            price,
            total,
            booking_ref
        ))

        mysql.connection.commit()

        session['booking_ref'] = booking_ref

        return redirect(url_for('receipt'))

    return render_template('fillup.html', flight=flight, price=price)


# ---------------- RECEIPT (SECURE) ----------------
@app.route('/receipt')
def receipt():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    booking_ref = session.get('booking_ref')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT * FROM bookings 
        WHERE booking_ref=%s AND user_id=%s
    """, (booking_ref, session['user_id']))

    data = cursor.fetchone()

    if not data:
        return redirect(url_for('dashboard'))

    return render_template('receipt.html', data=data)


# ---------------- ABOUT ----------------
@app.route('/about_us')
def about():
    return render_template("about.html")


# ---------------- CONTACT ----------------
@app.route('/contact_us')
def contact():
    return render_template("contact.html")


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



@app.route('/booking_details')
def booking_details():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
    bookings = cursor.fetchall()

    cursor.close()

    return render_template('booking_details.html', bookings=bookings)
# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app.run(debug=True)