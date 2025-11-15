# backend/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from .db import get_db_connection
from werkzeug.security import check_password_hash, generate_password_hash
import os

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# -----------------------
# helper: admin_required
# -----------------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.", "warning")
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated

# -----------------------
# Admin login / logout
# -----------------------
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT admin_id, username, password_hash, full_name FROM admin_user WHERE username = :u", {"u": username})
            row = cur.fetchone()
            if row and check_password_hash(row[2], password):
                session["is_admin"] = True
                session["admin_id"] = int(row[0])
                session["admin_name"] = row[3] or row[1]
                flash(f"Welcome, {session['admin_name']}!", "success")
                return redirect(url_for("admin.dashboard"))
            else:
                flash("Invalid admin credentials.", "danger")
        finally:
            cur.close()
            conn.close()
    return render_template("admin_login.html")

@admin_bp.route("/logout")
@admin_required
def logout():
    session.pop("is_admin", None)
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    flash("Logged out.", "info")
    return redirect(url_for("admin.login"))

# -----------------------
# Dashboard
# -----------------------
@admin_bp.route("/")
@admin_required
def dashboard():
    return render_template("admin_dashboard.html")

# -----------------------
# Flights CRUD
# -----------------------
@admin_bp.route("/flights")
@admin_required
def flights_list():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT flight_id, airplane_id, origin_airport_id, destination_airport_id,
               TO_CHAR(departure_utc,'YYYY-MM-DD HH24:MI TZH:TZM') departure,
               TO_CHAR(arrival_utc,'YYYY-MM-DD HH24:MI TZH:TZM') arrival,
               price, seats_total, seats_available
        FROM flight
        ORDER BY departure_utc
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_flights.html", rows=rows)

@admin_bp.route("/flights/new", methods=["GET","POST"])
@admin_required
def flight_new():
    if request.method == "POST":
        fid = request.form.get("flight_id").strip()
        airplane_id = request.form.get("airplane_id")
        origin = request.form.get("origin_airport_id").strip().upper()
        dest = request.form.get("destination_airport_id").strip().upper()
        dep = request.form.get("departure_utc").strip()
        arr = request.form.get("arrival_utc").strip()
        price = request.form.get("price")
        seats_total = request.form.get("seats_total")

        conn = get_db_connection(); cur = conn.cursor()
        try:
            cur.execute("""
              INSERT INTO flight (flight_id, airplane_id, origin_airport_id, destination_airport_id, departure_utc, arrival_utc, price, seats_total, seats_available)
              VALUES (:1,:2,:3,:4,TO_TIMESTAMP_TZ(:5,'YYYY-MM-DD HH24:MI TZH:TZM'),TO_TIMESTAMP_TZ(:6,'YYYY-MM-DD HH24:MI TZH:TZM'),:7,:8,:8)
            """, (fid, airplane_id, origin, dest, dep, arr, price, seats_total))
            conn.commit()
            flash("Flight created.", "success")
            return redirect(url_for("admin.flights_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error creating flight: {e}", "danger")
        finally:
            cur.close(); conn.close()
    return render_template("admin_flight_form.html", mode="new")

@admin_bp.route("/flights/<flight_id>/edit", methods=["GET","POST"])
@admin_required
def flight_edit(flight_id):
    conn = get_db_connection(); cur = conn.cursor()
    if request.method == "POST":
        airplane_id = request.form.get("airplane_id")
        origin = request.form.get("origin_airport_id").strip().upper()
        dest = request.form.get("destination_airport_id").strip().upper()
        dep = request.form.get("departure_utc").strip()
        arr = request.form.get("arrival_utc").strip()
        price = request.form.get("price")
        seats_total = request.form.get("seats_total")
        try:
            cur.execute("""
              UPDATE flight SET airplane_id=:2, origin_airport_id=:3, destination_airport_id=:4,
                  departure_utc = TO_TIMESTAMP_TZ(:5,'YYYY-MM-DD HH24:MI TZH:TZM'),
                  arrival_utc   = TO_TIMESTAMP_TZ(:6,'YYYY-MM-DD HH24:MI TZH:TZM'),
                  price=:7, seats_total=:8, seats_available=:8
              WHERE flight_id = :1
            """, (flight_id, airplane_id, origin, dest, dep, arr, price, seats_total))
            conn.commit()
            flash("Flight updated.", "success")
            return redirect(url_for("admin.flights_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating flight: {e}", "danger")
        finally:
            cur.close(); conn.close()
    else:
        cur.execute("SELECT flight_id, airplane_id, origin_airport_id, destination_airport_id, TO_CHAR(departure_utc,'YYYY-MM-DD HH24:MI TZH:TZM'), TO_CHAR(arrival_utc,'YYYY-MM-DD HH24:MI TZH:TZM'), price, seats_total FROM flight WHERE flight_id = :1", (flight_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            flash("Flight not found.", "warning")
            return redirect(url_for("admin.flights_list"))
        return render_template("admin_flight_form.html", mode="edit", flight=row)

@admin_bp.route("/flights/<flight_id>/delete", methods=["POST"])
@admin_required
def flight_delete(flight_id):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM flight WHERE flight_id = :1", (flight_id,))
        conn.commit()
        flash("Flight deleted.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting flight: {e}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("admin.flights_list"))

# -----------------------
# View bookings
# -----------------------
@admin_bp.route("/bookings")
@admin_required
def bookings_view():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
      SELECT b.booking_id, p.name, p.email, b.flight_id, b.seat_no, b.status, NVL(pay.status,'N/A') as pay_status, TO_CHAR(b.booking_date,'YYYY-MM-DD HH24:MI') created_at
      FROM booking b
      JOIN passenger p ON p.passenger_id = b.passenger_id
      LEFT JOIN payment pay ON pay.booking_id = b.booking_id
      ORDER BY b.booking_date DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_bookings.html", rows=rows)

# -----------------------
# View passengers
# -----------------------
@admin_bp.route("/passengers")
@admin_required
def passengers_view():
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("SELECT passenger_id, name, contact, email FROM passenger ORDER BY passenger_id DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_passengers.html", rows=rows)
