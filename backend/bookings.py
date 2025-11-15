from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from .db import get_db_connection
import oracledb

bookings_bp = Blueprint("bookings", __name__, url_prefix="")

# ------------------------------------------------------------
# Helper to safely extract Oracle OUT parameter values
# ------------------------------------------------------------
def extract_value(v):
    if v is None:
        return None
    value = v.getvalue()
    if isinstance(value, list):
        return value[0]
    return value


# ------------------------------------------------------------
# 1️⃣ SHOW BOOKING FORM
# ------------------------------------------------------------
@bookings_bp.get("/book")
def book_form():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT flight_id,
               origin_airport_id,
               destination_airport_id,
               TO_CHAR(departure_utc, 'YYYY-MM-DD HH24:MI') dep,
               price,
               seats_available
        FROM flight
        ORDER BY departure_utc
    """)
    flights = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("booking_form.html", flights=flights)


# ------------------------------------------------------------
# 2️⃣ SUBMIT BOOKING FORM → Create booking
# ------------------------------------------------------------
@bookings_bp.post("/book")
def book_submit():
    name = request.form.get("passenger_name")
    contact = request.form.get("contact")
    email = (request.form.get("email") or session.get("user_email") or "").strip().lower()
    flight_id = request.form.get("flight_id")
    seat_no = request.form.get("seat_no")
    amount = request.form.get("amount")

    if not all([name, email, flight_id, seat_no, amount]):
        flash("All fields are required!", "warning")
        return redirect(url_for("bookings.book_form"))

    try:
        amount = float(amount)
    except:
        flash("Invalid amount.", "warning")
        return redirect(url_for("bookings.book_form"))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check passenger exists
        cur.execute("SELECT passenger_id FROM passenger WHERE email = :1", (email,))
        row = cur.fetchone()

        if row:
            pid = row[0]
        else:
            out_id = cur.var(oracledb.NUMBER)
            cur.execute("""
                INSERT INTO passenger (name, contact, email)
                VALUES (:1, :2, :3)
                RETURNING passenger_id INTO :4
            """, (name, contact, email, out_id))

            pid = int(extract_value(out_id))

        # Call booking procedure
        out_bid = cur.var(oracledb.NUMBER)
        out_status = cur.var(oracledb.STRING)

        cur.callproc("proc_book_seat", [
            pid,
            flight_id,
            seat_no,
            amount,
            out_bid,
            out_status
        ])

        booking_id = extract_value(out_bid)
        status = out_status.getvalue()

        if status == "SUCCESS":
            cur.execute("""
                UPDATE booking
                SET status = 'CONFIRMED'
                WHERE booking_id = :1
            """, (booking_id,))
            conn.commit()

            return redirect(url_for(
                "bookings.payment_page",
                booking_id=booking_id,
                name=name,
                flight_id=flight_id,
                amount=amount
            ))

        flash("Booking failed: " + status, "danger")
        return redirect(url_for("bookings.book_form"))

    except oracledb.DatabaseError as e:
        (err,) = e.args
        flash("DB Error: " + err.message, "danger")
        conn.rollback()
        return redirect(url_for("bookings.book_form"))

    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------
# 3️⃣ PAYMENT PAGE
# ------------------------------------------------------------
@bookings_bp.get("/payment")
def payment_page():
    return render_template(
        "payment_page.html",
        booking_id=request.args.get("booking_id"),
        amount=request.args.get("amount"),
        flight_id=request.args.get("flight_id"),
        name=request.args.get("name")
    )


# ------------------------------------------------------------
# 4️⃣ CANCEL PAYMENT
# ------------------------------------------------------------
@bookings_bp.get("/cancel_payment")
def cancel_payment():
    booking_id = request.args.get("booking_id")

    if not booking_id:
        flash("Missing booking ID.", "warning")
        return redirect(url_for("bookings.my_bookings"))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Cancel booking
        out_status = cur.var(oracledb.STRING)
        cur.callproc("proc_cancel_booking", [int(booking_id), out_status])

        # Mark payment cancelled
        cur.execute("""
            UPDATE payment
            SET status = 'CANCELLED'
            WHERE booking_id = :1
        """, (booking_id,))

        conn.commit()
        flash("Payment cancelled. Booking cancelled.", "info")
        return redirect(url_for("bookings.my_bookings"))

    except oracledb.DatabaseError as e:
        (err,) = e.args
        flash("DB Error: " + err.message, "danger")
        conn.rollback()
        return redirect(url_for("bookings.my_bookings"))

    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------
# 5️⃣ VIEW ALL BOOKINGS (ADMIN)
# ------------------------------------------------------------
@bookings_bp.get("/bookings")
def view_bookings():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT b.booking_id, p.name, b.flight_id, b.seat_no,
               TO_CHAR(b.booking_date,'YYYY-MM-DD HH24:MI'),
               b.status,
               NVL(pay.status, 'N/A')
        FROM booking b
        JOIN passenger p ON p.passenger_id = b.passenger_id
        LEFT JOIN payment pay ON pay.booking_id = b.booking_id
        ORDER BY b.booking_date DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("bookings_list.html", rows=rows)


# ------------------------------------------------------------
# 6️⃣ USER BOOKINGS PAGE
# ------------------------------------------------------------
@bookings_bp.get("/mybookings")
def my_bookings():
    email = session.get("user_email", "").strip().lower()
    if not email:
        flash("Please log in.", "warning")
        return redirect(url_for("users.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            p.name,
            f.flight_id,
            b.seat_no,
            b.status AS booking_status,
            NVL(pay.status, 'NOT PAID') AS payment_status
        FROM booking b
        JOIN passenger p ON p.passenger_id = b.passenger_id
        JOIN flight f ON f.flight_id = b.flight_id
        LEFT JOIN payment pay ON pay.booking_id = b.booking_id
        WHERE LOWER(p.email) = :email
        ORDER BY b.booking_date DESC
    """, {"email": email})

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("my_bookings.html", rows=rows)



