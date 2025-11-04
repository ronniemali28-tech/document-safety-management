from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Set up upload folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT DEFAULT 'user'
                    )''')
    conn.commit()
    conn.close()


init_db()


# ---------- ROUTES ----------

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']  # ✅ Get role from dropdown

        conn = sqlite3.connect('users.db')  # ✅ use users.db (not database.db)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "Username already exists. Please choose another."

        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       (username, password, role))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    role = session['role']

    if role == 'admin':
        # Admin can see all uploads
        files = []
        for user_folder in os.listdir(app.config['UPLOAD_FOLDER']):
            user_path = os.path.join(app.config['UPLOAD_FOLDER'], user_folder)
            if os.path.isdir(user_path):
                for f in os.listdir(user_path):
                    files.append(f"{user_folder}/{f}")
    else:
        # Normal user sees only their uploads
        user_path = os.path.join(app.config['UPLOAD_FOLDER'], username)
        os.makedirs(user_path, exist_ok=True)
        files = os.listdir(user_path)

    return render_template('dashboard.html', files=files, role=role, username=username)


@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('dashboard'))

    username = session['username']
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_folder, exist_ok=True)

    file_path = os.path.join(user_folder, file.filename)
    file.save(file_path)

    return redirect(url_for('dashboard'))


@app.route('/delete/<username>/<filename>', methods=['POST'])
def delete_file(username, filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = session['username']
    role = session['role']

    # Only admin can delete anyone's file; user can delete only own file
    if role != 'admin' and current_user != username:
        return "Access denied. You can only delete your own files."

    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    file_path = os.path.join(user_folder, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(url_for('dashboard'))

from flask import send_from_directory

@app.route('/uploads/<username>/<filename>')
def uploaded_file(username, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], username), filename)


if __name__ == '__main__':
    app.run(debug=True)