from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
# db = SQLAlchemy(app)


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'bad_access'

# User model
class User(UserMixin):
    pass

# Dummy user database (replace with your own user storage)
users = {
    'admin': {'password': 'admin'}
}

@login_manager.user_loader
def load_user(user_id):
    user = User()
    user.id = user_id
    return user

@app.route('/')
def home():
    return render_template('homepage.html')


if __name__ == '__main__':
    app.run(debug=True)