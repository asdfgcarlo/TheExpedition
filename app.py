from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib
import random

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------------- FLIGHT PRICES ----------------


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

    total = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    total.execute("SELECT COUNT(*) AS total FROM users")
    total_users = total.fetchone()['total']

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
            flash("Invalid email or password")

    return render_template('index.html', error=error, total_users=total_users)


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        account = cursor.fetchone()

        if account:
            flash("Email already exists!", "error")
        else:
            cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",(username, email, hashed_password))
            mysql.connection.commit()
            flash("Registration successful!", "success")
        return redirect(url_for('register'))

    return render_template('register.html')


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('dashboard.html', user=session.get('username'))


# ---------------- ADMIN ----------------
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ---------------- GET USER FROM DB ----------------
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
        bookings=bookings,
        total_users=total_users,
        total_bookings=total_bookings,
        total_income=total_income
    )
# ---------------- BOOK PAGE ----------------
@app.route('/book')
def book():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('book_now.html', flights=FLIGHTS)


# ---------------- FILL UP + BOOKING ----------------

FLIGHTS = {
        "MNL-CEB": 5073, 
        "MNL-BCD": 6100, 
        "MNL-KLO": 45000, 
        "TAG-CRK": 3500, 
        "LAO-DRP": 9400,
        "MNL-TAC": 3100
           }

@app.route('/fillup/<flight>/<int:price>', methods=['GET', 'POST'])
def fillup(flight, price):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    price = FLIGHTS.get(flight)

    if request.method == 'POST':
        contact = request.form['contact']
        pax = int(request.form['pax'])
        payment = request.form['payment']
        total = pax * price

        booking_ref = "PH" + str(random.randint(100000, 999999))

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO bookings 
            (user_id, flight, contact, pax, price, payment_type, total, booking_ref)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            flight,
            contact,
            pax,
            price,
            payment,
            total,
            booking_ref
        ))

        mysql.connection.commit()

        session['booking_ref'] = booking_ref

        return redirect(url_for('receipt'))

    price = FLIGHTS.get(flight, price)

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

@app.route('/analytics')
def analytics():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    income_p_day = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # price
    cursor.execute('SELECT price AS revenue FROM bookings')
    revenue = cursor.fetchone()['revenue']

    # fetch chart data from database
    cursor.execute('''
        SELECT DATE(created_at) AS date,
               COUNT(*) AS total
        FROM bookings
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    ''')

    chart_data = cursor.fetchall()

    labels = []
    revenue = []

    for row in chart_data:
        labels.append(str(row['date']))
        revenue.append(row['total'])

    # bar chart

    income_p_day.execute('''
        SELECT DATE(created_at) AS date,
               SUM(total) AS income
        FROM bookings
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    ''')
    
    bar = income_p_day.fetchall()
    # for bar
    date = []
    income = []

    for row in bar:
        date.append(str(row['date']))
        income.append(row['income'])


    doughtnut = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    doughtnut.execute(
        'SELECT payment_type as mop, COUNT(payment_type) as count FROM bookings GROUP BY payment_type'
    )

    doughtnut = doughtnut.fetchall()
    mop_label = []
    mop_data = []

    for row in doughtnut:
        mop_label.append(str(row['mop']))
        mop_data.append(row['count'])
    
    return render_template(
        'analytics.html',
        labels=labels,
        revenue=revenue,
        date=date,
        income=income,
        mop_label=mop_label,
        mop_data=mop_data
    )

@app.route('/attraction')
def attraction():
    return render_template('attraction.html')
# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app.run(debug=True)