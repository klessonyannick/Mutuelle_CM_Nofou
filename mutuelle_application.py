from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secret123"
app.permanent_session_lifetime = timedelta(minutes=30)

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user',
        member_id INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        amount REAL DEFAULT 0,
        deleted INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        amount REAL,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

# ---------------- ADMIN ----------------
def create_admin():
    conn = get_db()

    existing = conn.execute(
        "SELECT * FROM users WHERE username='admin'"
    ).fetchone()

    if not existing:
        password = generate_password_hash("1234")

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO members (name, phone) VALUES (?, ?)",
            ("Admin", "00000000")
        )

        member_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO users (username, password, role, member_id) VALUES (?, ?, ?, ?)",
            ("admin", password, "admin", member_id)
        )

        conn.commit()

    conn.close()

# ---------------- PROTECTION ----------------
@app.before_request
def protect():
    allowed = ["login", "static"]

    if request.endpoint not in allowed and "user" not in session:
        return redirect("/")

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            session["role"] = user["role"]
            session["member_id"] = user["member_id"]
            session.permanent = True
            return redirect("/dashboard")

        flash("Identifiants incorrects ❌")
        return redirect("/")

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    conn = get_db()

    if session["role"] == "admin":
        members = conn.execute(
            "SELECT * FROM members WHERE deleted=0"
        ).fetchall()
    else:
        members = conn.execute(
            "SELECT * FROM members WHERE id=?",
            (session["member_id"],)
        ).fetchall()

    total = conn.execute(
        "SELECT SUM(amount) as total FROM payments"
    ).fetchone()["total"] or 0

    conn.close()

    return render_template("dashboard.html", members=members, total=total)

# ---------------- ADD ----------------
@app.route("/add", methods=["POST"])
def add():
    if session.get("role") != "admin":
        return redirect("/dashboard")

    name = request.form["name"]
    phone = request.form["phone"]

    conn = get_db()
    conn.execute(
        "INSERT INTO members (name, phone) VALUES (?, ?)",
        (name, phone)
    )
    conn.commit()
    conn.close()

    flash("Membre ajouté ✅")
    return redirect("/dashboard")

# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    if session.get("role") != "admin":
        return redirect("/dashboard")

    conn = get_db()
    conn.execute("UPDATE members SET deleted=1 WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Membre supprimé ❌")
    return redirect("/dashboard")

# ---------------- PAY ----------------
@app.route("/pay/<int:id>", methods=["GET", "POST"])
def pay(id):
    conn = get_db()

    member = conn.execute(
        "SELECT * FROM members WHERE id=?", (id,)
    ).fetchone()

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            if amount <= 0:
                raise ValueError
        except:
            return render_template("pay.html", member=member, error="Montant invalide ❌")

        date = datetime.now().strftime("%Y-%m-%d")

        conn.execute(
            "INSERT INTO payments (member_id, amount, date) VALUES (?, ?, ?)",
            (id, amount, date)
        )

        conn.execute(
            "UPDATE members SET amount = amount + ? WHERE id=?",
            (amount, id)
        )

        conn.commit()

        flash("Paiement effectué 💰")
        conn.close()
        return redirect("/dashboard")

    conn.close()
    return render_template("pay.html", member=member)

# ---------------- HISTORY ----------------
@app.route("/history/<int:id>")
def history(id):
    conn = get_db()

    payments = conn.execute(
        "SELECT * FROM payments WHERE member_id=?",
        (id,)
    ).fetchall()

    conn.close()

    return render_template("history.html", payments=payments)

# ---------------- CREATE USER ----------------
@app.route("/create_user", methods=["GET", "POST"])
def create_user():
    if session.get("role") != "admin":
        return redirect("/dashboard")

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = get_db()

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO members (name, phone) VALUES (?, ?)",
            (name, phone)
        )

        member_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO users (username, password, role, member_id) VALUES (?, ?, ?, ?)",
            (username, password, "user", member_id)
        )

        conn.commit()
        conn.close()

        flash("Utilisateur créé ✅")
        return redirect("/dashboard")

    return render_template("create_user.html")

# ---------------- CHANGE PASSWORD ----------------
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        old = request.form["old_password"]
        new = request.form["new_password"]
        confirm = request.form["confirm_password"]

        if new != confirm:
            return render_template("change_password.html", error="Mot de passe incorrect ❌")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (session["user"],)
        ).fetchone()

        if not check_password_hash(user["password"], old):
            conn.close()
            return render_template("change_password.html", error="Ancien mot de passe faux ❌")

        conn.execute(
            "UPDATE users SET password=? WHERE username=?",
            (generate_password_hash(new), session["user"])
        )

        conn.commit()
        conn.close()

        flash("Mot de passe modifié ✅")
        return redirect("/dashboard")

    return render_template("change_password.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    create_admin()
    app.run(host="0.0.0.0", port=10000)