from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

users_bp = Blueprint("users", __name__, url_prefix="")

# ======================
# SIGNUP
# ======================
@users_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # Already logged in? Redirect to welcome
    if "user_name" in session:
        return redirect(url_for("users.welcome"))

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Check if email already exists
            cur.execute("SELECT user_id FROM app_user WHERE email = :1", (email,))
            if cur.fetchone():
                flash("⚠️ Email already registered. Please log in.", "warning")
                return redirect(url_for("users.login"))

            # Insert new user
            hashed_pw = generate_password_hash(password)
            cur.execute("""
                INSERT INTO app_user (name, email, password_hash)
                VALUES (:1, :2, :3)
            """, (name, email, hashed_pw))
            conn.commit()

            # Auto login after signup
            session["user_name"] = name
            session["user_email"] = email.strip().lower()
            flash(f"Welcome to Airline Reservation System, {name}!", "success")
            return redirect(url_for("users.welcome"))

        except Exception as e:
            conn.rollback()
            flash(f"Database error: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()

    return render_template("signup.html")

# ======================
# LOGIN
# ======================
@users_bp.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in? Go to welcome
    if "user_name" in session:
        return redirect(url_for("users.welcome"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT user_id, name, password_hash FROM app_user WHERE email = :1", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row and check_password_hash(row[2], password):
            session["user_id"] = row[0]
            session["user_name"] = row[1]
            session["user_email"] = email.strip().lower()
            flash(f"Welcome to Airline Reservation System, {row[1]}!", "success")
            return redirect(url_for("users.welcome"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")

# ======================
# WELCOME PAGE
# ======================
@users_bp.route("/welcome")
def welcome():
    if "user_name" not in session:
        flash("Please log in to continue.", "warning")
        return redirect(url_for("users.login"))

    # Show a proper welcome page after login
    return render_template("welcome.html", user=session["user_name"])

# ======================
# LOGOUT
# ======================
@users_bp.route("/logout")
def logout():
    session.clear()
    flash("You’ve been logged out successfully.", "info")
    return redirect(url_for("users.login"))


