from flask import Flask, render_template, request, redirect, url_for, flash, g, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
from datetime import datetime, timedelta, date
from functools import wraps
import os
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'database.db'

users = {
    'admin': {'password': 'admin'}
}

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'bad_access'

# User model
class User(UserMixin):
    def __init__(self, user_id, username, email, type):
        self.id = user_id
        self.username = username
        self.email = email
        self.type = type

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        user_obj = User(user['id'], user['username'], user['email'], user['type'])
        return user_obj
    return None

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            script = f.read()
            if 'CREATE TABLE users' in script:
                # Check if the users table already exists
                table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
                if not table_exists:
                    db.cursor().executescript(script)
                    # Insert a default user if the users table is empty
                    db.execute('INSERT INTO users (fullname, username, email, password, type) VALUES (?, ?, ?, ?, ?)', ('Admin', 'admin', 'admin@example.com', 'password', 'admin'))
                    db.commit()
            else:
                db.cursor().executescript(script)
                db.commit()

            # Create the profile_pictures table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profile_pictures'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE profile_pictures (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, picture BLOB, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Create the bills table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bills'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE bills (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, cycle_date DATE, amount REAL, paid BOOLEAN DEFAULT 0, paid_date DATE, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Create the usage table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usage'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE usage (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, usage_date DATE, usage_amount REAL, usage_cost REAL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Create the inquiry table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inquiry'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE inquiry (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, inquiry_name VARCHAR NOT NULL, inquiry_date DATE NOT NULL, inquiry_question VARCHAR NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Create the reply table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reply'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE reply (id INTEGER PRIMARY KEY AUTOINCREMENT, inquiry_id INTEGER NOT NULL, admin_id INTEGER NOT NULL, reply_content VARCHAR NOT NULL, reply_date DATE NOT NULL, FOREIGN KEY(inquiry_id) REFERENCES inquiry(id) ON DELETE CASCADE, FOREIGN KEY(admin_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Create the payments table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, payment_date DATE, amount REAL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Create the meters table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meters'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE meters (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, device_type VARCHAR NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Create the admin table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE admin (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Insert admin user into the admin table
            admin_user = db.execute('SELECT id FROM users WHERE type = ?', ('admin',)).fetchone()
            if admin_user:
                admin_id = admin_user['id']
                admin_exists = db.execute('SELECT id FROM admin WHERE user_id = ?', (admin_id,)).fetchone()
                if not admin_exists:
                    db.execute('INSERT INTO admin (user_id) VALUES (?)', (admin_id,))

            # Create the admin_bills table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_bills'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE admin_bills (id INTEGER PRIMARY KEY AUTOINCREMENT, bill_id INTEGER NOT NULL, admin_id INTEGER NOT NULL, FOREIGN KEY(bill_id) REFERENCES bills(id) ON DELETE CASCADE, FOREIGN KEY(admin_id) REFERENCES users(id) ON DELETE CASCADE)")

            # Create the admin_payments table
            table_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_payments'").fetchone()
            if not table_exists:
                db.execute("CREATE TABLE admin_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, payment_id INTEGER NOT NULL, admin_id INTEGER NOT NULL, FOREIGN KEY(payment_id) REFERENCES payments(id) ON DELETE CASCADE, FOREIGN KEY(admin_id) REFERENCES users(id) ON DELETE CASCADE)")

            db.commit()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# @app.route('/')
# def index():
#     db = get_db()
#     cursor = db.execute('SELECT * FROM users')
#     users = cursor.fetchall()
#     return str(users)

@app.route('/add')
def add_user():
    db = get_db()
    db.execute('INSERT INTO users (username, email) VALUES (?, ?)', ('John Doe', 'john@example.com'))
    db.commit()
    return 'User added successfully'

def clear_flashes():
    session.pop('_flashes', None)

@app.route('/')
def home():
    # print(current_user.email)
    return render_template('homepage.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if the passwords match
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('signup'))

        # Check if the username or email already exists in the database
        db = get_db()
        existing_user = db.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()

        if existing_user:
            flash('Username or email already exists')
            return redirect(url_for('signup'))

        # Insert the new user into the database
        db.execute('INSERT INTO users (fullname, username, email, password) VALUES (?, ?, ?, ?)', (fullname, username, email, password))
        db.commit()

        flash('Signup successful. Please login.')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    clear_flashes()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username exists in the database
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user:
            # Check if the password is correct
            if password == user['password']:
                user_obj = User(user['id'], user['username'], user['email'], user['type'])
                login_user(user_obj)
                flash('Login successful')
                return redirect(url_for('home'))
            else:
                flash('Invalid password')
        else:
            flash('Invalid username')

    return render_template('login.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact')
@login_required
def contact():
    db = get_db()
    user_id = current_user.id
    inquiries = db.execute("SELECT i.*, r.reply_content FROM inquiry i LEFT JOIN reply r ON i.id = r.inquiry_id WHERE i.user_id = ? ORDER BY i.id DESC", (user_id,)).fetchall()
    return render_template('contact.html', inquiries=inquiries)

@app.route('/bad_access')
def bad_access():
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/protected')
@login_required
def protected():
    return render_template('login.html')

@app.route('/payBill', methods=['GET', 'POST'])
@login_required
def payBill():
    db = get_db()
    user_id = current_user.id

    if request.method == 'POST':
        bill_id = request.form.get('bill_id')
        custom_amount = float(request.form.get('custom_amount', 0))

        if bill_id:
            # Pay the specific bill
            bill = db.execute('SELECT * FROM bills WHERE id = ? AND user_id = ?', (bill_id, user_id)).fetchone()
            if bill:
                amount = bill['amount']
                db.execute('UPDATE bills SET paid = 1, paid_date = ? WHERE id = ?', (date.today(), bill_id))
                db.execute('INSERT INTO payments (user_id, payment_date, amount) VALUES (?, ?, ?)', (user_id, date.today(), amount))
                db.commit()
                flash('Payment processed successfully', 'success')
        elif custom_amount > 0:
            # Process custom payment
            outstanding_bills = db.execute('SELECT * FROM bills WHERE user_id = ? AND paid = 0 ORDER BY cycle_date', (user_id,)).fetchall()
            remaining_amount = custom_amount
            for bill in outstanding_bills:
                if remaining_amount >= bill['amount']:
                    db.execute('UPDATE bills SET paid = 1, paid_date = ? WHERE id = ?', (date.today(), bill['id']))
                    db.execute('INSERT INTO payments (user_id, payment_date, amount) VALUES (?, ?, ?)', (user_id, date.today(), bill['amount']))
                    remaining_amount -= bill['amount']
                else:
                    break
            if remaining_amount > 0:
                db.execute('INSERT INTO bills (user_id, cycle_date, amount, paid) VALUES (?, ?, ?, ?)', (user_id, date.today(), -remaining_amount, 1))
                db.execute('INSERT INTO payments (user_id, payment_date, amount) VALUES (?, ?, ?)', (user_id, date.today(), remaining_amount))
            db.commit()
            flash('Payment processed successfully', 'success')

        return redirect(url_for('payment_history'))

    bill_id = request.args.get('bill_id')
    if bill_id:
        # Fetch the specific bill details
        bill = db.execute('SELECT * FROM bills WHERE id = ? AND user_id = ?', (bill_id, user_id)).fetchone()
        if bill:
            return render_template('paybill.html', bill=bill)
    else:
        # Get the latest bill for the user
        latest_bill = db.execute('SELECT * FROM bills WHERE user_id = ? ORDER BY cycle_date DESC LIMIT 1', (user_id,)).fetchone()
        return render_template('paybill.html', bill=latest_bill)

@app.route('/usage')
@login_required
def usage():
    user_id = current_user.id

    db = get_db()

    # Get the current date
    current_date = datetime.now().date()

    # Calculate the date ranges for each period
    current_week_start = current_date - timedelta(days=current_date.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    previous_week_start = current_week_start - timedelta(days=7)
    previous_week_end = current_week_start - timedelta(days=1)

    current_month_start = current_date.replace(day=1)
    current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    current_year_start = current_date.replace(month=1, day=1)
    current_year_end = current_date.replace(month=12, day=31)
    previous_year_start = (current_year_start - timedelta(days=365)).replace(month=1, day=1)
    previous_year_end = current_year_start - timedelta(days=1)

    # Fetch usage and cost data for each period
    current_week_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ?', (user_id, current_week_start, current_week_end)).fetchone()
    previous_week_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ?', (user_id, previous_week_start, previous_week_end)).fetchone()

    current_month_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ?', (user_id, current_month_start, current_month_end)).fetchone()
    previous_month_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ?', (user_id, previous_month_start, previous_month_end)).fetchone()

    current_year_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ?', (user_id, current_year_start, current_year_end)).fetchone()
    previous_year_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ?', (user_id, previous_year_start, previous_year_end)).fetchone()

    overall_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ?', (user_id,)).fetchone()

    # Calculate averages for each period
    current_week_avg_usage = current_week_data['total_usage'] / 7 if current_week_data['total_usage'] else 0
    current_week_avg_cost = current_week_data['total_cost'] / 7 if current_week_data['total_cost'] else 0
    previous_week_avg_usage = previous_week_data['total_usage'] / 7 if previous_week_data['total_usage'] else 0
    previous_week_avg_cost = previous_week_data['total_cost'] / 7 if previous_week_data['total_cost'] else 0

    current_month_days = (current_month_end - current_month_start).days + 1
    current_month_avg_usage = current_month_data['total_usage'] / current_month_days if current_month_data['total_usage'] else 0
    current_month_avg_cost = current_month_data['total_cost'] / current_month_days if current_month_data['total_cost'] else 0
    previous_month_days = (previous_month_end - previous_month_start).days + 1
    previous_month_avg_usage = previous_month_data['total_usage'] / previous_month_days if previous_month_data['total_usage'] else 0
    previous_month_avg_cost = previous_month_data['total_cost'] / previous_month_days if previous_month_data['total_cost'] else 0

    current_year_days = (current_year_end - current_year_start).days + 1
    current_year_avg_usage = current_year_data['total_usage'] / current_year_days if current_year_data['total_usage'] else 0
    current_year_avg_cost = current_year_data['total_cost'] / current_year_days if current_year_data['total_cost'] else 0
    previous_year_days = (previous_year_end - previous_year_start).days + 1
    previous_year_avg_usage = previous_year_data['total_usage'] / previous_year_days if previous_year_data['total_usage'] else 0
    previous_year_avg_cost = previous_year_data['total_cost'] / previous_year_days if previous_year_data['total_cost'] else 0

    total_days = db.execute('SELECT COUNT(DISTINCT usage_date) AS total_days FROM usage WHERE user_id = ?', (user_id,)).fetchone()['total_days']
    overall_avg_usage = overall_data['total_usage'] / total_days if overall_data['total_usage'] else 0
    overall_avg_cost = overall_data['total_cost'] / total_days if overall_data['total_cost'] else 0

    return render_template('usage.html',
                           current_week_usage=current_week_data['total_usage'] or 0,
                           current_week_cost=current_week_data['total_cost'] or 0,
                           previous_week_usage=previous_week_data['total_usage'] or 0,
                           previous_week_cost=previous_week_data['total_cost'] or 0,
                           current_week_avg_usage=current_week_avg_usage,
                           current_week_avg_cost=current_week_avg_cost,
                           previous_week_avg_usage=previous_week_avg_usage,
                           previous_week_avg_cost=previous_week_avg_cost,
                           current_month_usage=current_month_data['total_usage'] or 0,
                           current_month_cost=current_month_data['total_cost'] or 0,
                           previous_month_usage=previous_month_data['total_usage'] or 0,
                           previous_month_cost=previous_month_data['total_cost'] or 0,
                           current_month_avg_usage=current_month_avg_usage,
                           current_month_avg_cost=current_month_avg_cost,
                           previous_month_avg_usage=previous_month_avg_usage,
                           previous_month_avg_cost=previous_month_avg_cost,
                           current_year_usage=current_year_data['total_usage'] or 0,
                           current_year_cost=current_year_data['total_cost'] or 0,
                           previous_year_usage=previous_year_data['total_usage'] or 0,
                           previous_year_cost=previous_year_data['total_cost'] or 0,
                           current_year_avg_usage=current_year_avg_usage,
                           current_year_avg_cost=current_year_avg_cost,
                           previous_year_avg_usage=previous_year_avg_usage,
                           previous_year_avg_cost=previous_year_avg_cost,
                           overall_avg_usage=overall_avg_usage,
                           overall_avg_cost=overall_avg_cost)
@app.route('/account')
@login_required
def account():
    return render_template('account.html')

@app.route('/payment-history')
@login_required
def payment_history():
    db = get_db()
    user_id = current_user.id
    payment_history = db.execute('SELECT id, payment_date, amount FROM payments WHERE user_id = ? ORDER BY id DESC', (user_id,)).fetchall()
    return render_template('payment_history.html', payment_history=payment_history)

@app.route('/create_inquiry', methods=['POST'])
@login_required
def create_inquiry():
    inquiry_name = request.form['inquiry_name']
    inquiry_question = request.form['inquiry_question']
    user_id = current_user.id
    inquiry_date = date.today()  # Get the current date

    db = get_db()
    db.execute('INSERT INTO inquiry (user_id, inquiry_name, inquiry_date, inquiry_question) VALUES (?, ?, ?, ?)', (user_id, inquiry_name, inquiry_date, inquiry_question))
    db.commit()

    flash('Inquiry created successfully')
    return redirect(url_for('contact'))

# admin

def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user.type != 'admin':
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return decorated_view

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    db = get_db()
    users = db.execute('SELECT * FROM users').fetchall()
    bills = db.execute('SELECT b.*, u.username FROM bills b JOIN users u ON b.user_id = u.id').fetchall()
    inquiries = db.execute('SELECT i.*, u.username FROM inquiry i JOIN users u ON i.user_id = u.id').fetchall()
    payments = db.execute('SELECT p.*, u.username FROM payments p JOIN users u ON p.user_id = u.id').fetchall()
    replied_inquiry_ids = [row['inquiry_id'] for row in db.execute('SELECT inquiry_id FROM reply').fetchall()]
    # payments = 1
    return render_template('admin.html', users=users , bills=bills, inquiries=inquiries, payments=payments, replied_inquiry_ids=replied_inquiry_ids, clear=clear_flashes)

@app.route('/adminToggle/<int:user_id>')
@login_required
@admin_required
def adminToggle(user_id):
    clear_flashes()
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if user:
        if user['id'] == current_user.id:
            flash("You cannot change your own admin status.", "warning")
        else:
            new_type = 'admin' if user['type'] != 'admin' else 'user'
            db.execute('UPDATE users SET type = ? WHERE id = ?', (new_type, user_id))
            
            if new_type == 'admin':
                # Add user ID to the admin table
                db.execute('INSERT INTO admin (user_id) VALUES (?)', (user_id,))
                flash(f"@{user['username']} has been granted admin privileges.", "success")
            else:
                # Remove user ID from the admin table
                db.execute('DELETE FROM admin WHERE user_id = ?', (user_id,))
                flash(f"@{user['username']} has been revoked of admin privileges.", "info")
            
            db.commit()
    else:
        flash("User not found.", "error")
    
    return redirect(url_for('admin_panel'))

@app.route('/manage-bills')
@login_required
@admin_required
def manage_bills():
    clear_flashes()
    return render_template('manage_bills.html')

@app.route('/generate-bill', methods=['POST'])
@login_required
@admin_required
def generate_bill():
    user_id = request.form['user_id']
    usage_amount = float(request.form['usage_amount'])
    price_per_kwh = float(request.form['price_per_kwh'])

    db = get_db()

    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if user:
        # Calculate the bill amount
        bill_amount = usage_amount * price_per_kwh

        # Insert the generated bill into the database
        cycle_date = date.today()
        db.execute('INSERT INTO bills (user_id, cycle_date, amount) VALUES (?, ?, ?)', (user_id, cycle_date, bill_amount))
        bill_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Insert the usage record into the database
        db.execute('INSERT INTO usage (user_id, usage_date, usage_amount, usage_cost) VALUES (?, ?, ?, ?)',
                   (user_id, cycle_date, usage_amount, bill_amount))

        # Insert into the admin_bills table
        admin_id = current_user.id  # Assuming current_user is the admin user
        db.execute('INSERT INTO admin_bills (bill_id, admin_id) VALUES (?, ?)', (bill_id, admin_id))

        db.commit()

        flash('Bill generated successfully.', 'success')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('admin_panel'))
@app.route('/manage-inquiries')
@login_required
@admin_required
def manage_inquiries():
    
    return render_template('manage_inquiries.html')

@app.route('/answer-inquiry', methods=['POST'])
@app.route('/answer-inquiry', methods=['POST'])
@login_required
@admin_required
def answer_inquiry():
    inquiry_id = request.form['inquiry_id']
    answer = request.form['answer']
    admin_id = current_user.id  # Get the current admin user's ID

    db = get_db()

    # Create a new reply
    db.execute('INSERT INTO reply (inquiry_id, admin_id, reply_content, reply_date) VALUES (?, ?, ?, ?)',
               (inquiry_id, admin_id, answer, datetime.now()))
    db.commit()

    flash('Inquiry answered successfully.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/manage-payments')
@login_required
@admin_required
def manage_payments():
    return render_template('admin.html')

@app.route('/add-payment', methods=['POST'])
@login_required
@admin_required
def add_payment():
    user_id = request.form['user_id']
    amount = float(request.form['amount'])

    db = get_db()

    payment_date = date.today()
    db.execute('INSERT INTO payments (user_id, payment_date, amount) VALUES (?, ?, ?)', (user_id, payment_date, amount))
    payment_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    # Insert into the admin_payments table
    admin_id = current_user.id  # Assuming current_user is the admin user
    db.execute('INSERT INTO admin_payments (payment_id, admin_id) VALUES (?, ?)', (payment_id, admin_id))

    db.commit()

    flash('Payment added successfully.', 'success')
    return redirect(url_for('admin_panel', section='payments'))

@app.route('/account/usage')
@login_required
def account_usage():
    user_id = current_user.id

    db = get_db()

    # Get the current date
    current_date = datetime.now().date()

    # Calculate the date ranges for each period
    current_month_start = current_date.replace(day=1)
    current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    # Fetch usage and cost data for each period
    current_month_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ?', (user_id, current_month_start, current_month_end)).fetchone()
    previous_month_data = db.execute('SELECT SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ?', (user_id, previous_month_start, previous_month_end)).fetchone()

    overall_data = db.execute('SELECT AVG(usage_amount) AS avg_usage, AVG(usage_cost) AS avg_cost FROM usage WHERE user_id = ?', (user_id,)).fetchone()

    # Extract usage and cost values from the fetched data
    current_month_usage = current_month_data['total_usage'] or 0
    current_month_cost = current_month_data['total_cost'] or 0
    previous_month_usage = previous_month_data['total_usage'] or 0
    previous_month_cost = previous_month_data['total_cost'] or 0

    overall_avg_usage = overall_data['avg_usage'] or 0
    overall_avg_cost = overall_data['avg_cost'] or 0

    data = {
        'current_month_usage': round(current_month_usage, 2),
        'previous_month_usage': round(previous_month_usage, 2),
        'average_monthly_usage': round(overall_avg_usage, 2),
        'current_month_expenses': round(current_month_cost, 2),
        'previous_month_expenses': round(previous_month_cost, 2),
        'average_monthly_expenses': round(overall_avg_cost, 2)
    }

    return jsonify(data)

@app.route('/update-personal-info', methods=['POST'])
@login_required
def update_personal_info():
    if request.method == 'POST':
        if 'old_password' in request.form:
            # Modify Password
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            db = get_db()
            user = db.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()

            if user['password'] != old_password:
                flash('old password do not match')
                return render_template('personal_info.html')

            if new_password != confirm_password:
                flash('New passwords do not match')
                return render_template('personal_info.html')

            db.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, current_user.id))
            db.commit()

            flash('Password updated successfully')
            return render_template('personal_info.html')

        elif 'profile_picture' in request.files:
            # Modify Profile Picture
            old_password = request.form['old_password']
            profile_picture = request.files['profile_picture']

            db = get_db()
            user = db.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()

            if user['password'] != old_password:
                flash('Invalid password')
                return render_template('personal_info.html')
                

            picture_data = profile_picture.read()
            db.execute('UPDATE profile_pictures SET picture = ? WHERE user_id = ?', (picture_data, current_user.id))
            if db.execute('SELECT COUNT(*) FROM profile_pictures WHERE user_id = ?', (current_user.id,)).fetchone()[0] == 0:
                db.execute('INSERT INTO profile_pictures (user_id, picture) VALUES (?, ?)', (current_user.id, picture_data))
            db.commit()

            flash('Profile picture updated successfully')
            return render_template('personal_info.html')

    return render_template('personal_info.html')

@app.route('/update-personal-info', methods=['GET'])
@login_required
def update_personal_info_get():
    return render_template('personal_info.html')

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    amount = float(request.form['amount'])
    user_id = current_user.id

    db = get_db()
    payment_date = date.today()
    db.execute('INSERT INTO payments (user_id, payment_date, amount) VALUES (?, ?, ?)', (user_id, payment_date, amount))
    db.commit()

    # Update the paid status of bills based on the payment amount
    outstanding_bills = db.execute('SELECT id, amount FROM bills WHERE user_id = ? AND paid = 0 ORDER BY cycle_date', (user_id,)).fetchall()
    remaining_amount = amount
    for bill in outstanding_bills:
        if remaining_amount >= bill['amount']:
            db.execute('UPDATE bills SET paid = 1, paid_date = ? WHERE id = ?', (payment_date, bill['id']))
            remaining_amount -= bill['amount']
        else:
            break

    db.commit()

    flash('Payment processed successfully', 'success')
    return redirect(url_for('payment_history'))

# ...

@app.route('/manage_billing(user)')
@login_required
def manage_user_billing():
    user_id = current_user.id

    db = get_db()

    # Get the user's current bill
    current_bill = db.execute('SELECT * FROM bills WHERE user_id = ? AND paid = 0 ORDER BY cycle_date DESC LIMIT 1', (user_id,)).fetchone()

    # Get the user's billing history
    billing_history = db.execute('SELECT * FROM bills WHERE user_id = ? ORDER BY cycle_date DESC', (user_id,)).fetchall()

    # Get the user's payment methods
    payment_methods = db.execute('SELECT * FROM payments WHERE user_id = ?', (user_id,)).fetchall()

    return render_template('manage_billing(user).html',
                           user=current_user,
                           current_bill=current_bill,
                           billing_history=billing_history,
                           payment_methods=payment_methods)

# ...
# @app.route('/generate-graphs')
# @login_required
# def generate_graphs():
#     user_id = current_user.id

#     db = get_db()

#     # Get the current date
#     current_date = datetime.now().date()

#     # Calculate the date ranges for each period
#     current_week_start = current_date - timedelta(days=current_date.weekday())
#     current_week_end = current_week_start + timedelta(days=6)
#     previous_week_start = current_week_start - timedelta(days=7)
#     previous_week_end = current_week_start - timedelta(days=1)

#     current_month_start = current_date.replace(day=1)
#     current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
#     previous_month_end = current_month_start - timedelta(days=1)
#     previous_month_start = previous_month_end.replace(day=1)

#     current_year_start = current_date.replace(month=1, day=1)
#     current_year_end = current_date.replace(month=12, day=31)
#     previous_year_start = (current_year_start - timedelta(days=365)).replace(month=1, day=1)
#     previous_year_end = current_year_start - timedelta(days=1)

#     # Fetch usage and cost data for each period
#     current_week_data = db.execute('SELECT usage_date, SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ? GROUP BY usage_date', (user_id, current_week_start, current_week_end)).fetchall()
#     previous_week_data = db.execute('SELECT usage_date, SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ? GROUP BY usage_date', (user_id, previous_week_start, previous_week_end)).fetchall()

#     current_month_data = db.execute('SELECT usage_date, SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ? GROUP BY usage_date', (user_id, current_month_start, current_month_end)).fetchall()
#     previous_month_data = db.execute('SELECT usage_date, SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ? GROUP BY usage_date', (user_id, previous_month_start, previous_month_end)).fetchall()

#     current_year_data = db.execute('SELECT usage_date, SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ? GROUP BY usage_date', (user_id, current_year_start, current_year_end)).fetchall()
#     previous_year_data = db.execute('SELECT usage_date, SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? AND usage_date BETWEEN ? AND ? GROUP BY usage_date', (user_id, previous_year_start, previous_year_end)).fetchall()

#     overall_data = db.execute('SELECT usage_date, SUM(usage_amount) AS total_usage, SUM(usage_cost) AS total_cost FROM usage WHERE user_id = ? GROUP BY usage_date', (user_id,)).fetchall()

#     # Clear the graphs folder
#     graphs_folder = 'static/graphs'
#     if not os.path.exists(graphs_folder):
#         os.makedirs(graphs_folder)
#     for file in os.listdir(graphs_folder):
#         file_path = os.path.join(graphs_folder, file)
#         if os.path.isfile(file_path):
#             os.remove(file_path)

#     # Generate graphs for each period
#     periods = [
#         ('current_week', current_week_data),
#         ('previous_week', previous_week_data),
#         ('current_month', current_month_data),
#         ('previous_month', previous_month_data),
#         ('current_year', current_year_data),
#         ('previous_year', previous_year_data),
#         ('overall', overall_data)
#     ]

#     for period, data in periods:
#         dates = [row['usage_date'] for row in data]
#         usage = [row['total_usage'] for row in data]
#         cost = [row['total_cost'] for row in data]

#         # Generate usage graph
#         plt.figure()
#         plt.plot(dates, usage)
#         plt.xlabel('Date')
#         plt.ylabel('Usage (kWh)')
#         plt.title(f'{period.capitalize()} Usage')
#         plt.xticks(rotation=45)
#         plt.tight_layout()
#         plt.savefig(f'static/graphs/{period}_usage.png')
#         plt.close()

#         # Generate cost graph
#         plt.figure()
#         plt.plot(dates, cost)
#         plt.xlabel('Date')
#         plt.ylabel('Cost ($)')
#         plt.title(f'{period.capitalize()} Cost')
#         plt.xticks(rotation=45)
#         plt.tight_layout()
#         plt.savefig(f'static/graphs/{period}_cost.png')
#         plt.close()

#     return redirect(url_for('usage'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    