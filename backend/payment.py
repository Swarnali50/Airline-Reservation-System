from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from .db import get_db_connection
import oracledb

# Blueprint
payment_bp = Blueprint("payment", __name__, url_prefix="/pay")

# ====================================
# 1️⃣ SHOW PAYMENT PAGE
# ====================================
@payment_bp.post("/payment")
def payment_page():
    """Display payment confirmation page after booking form"""
    name = request.form.get("passenger_name")
    contact = request.form.get("contact")
    email = request.form.get("email")
    flight_id = request.form.get("flight_id")
    seat_no = request.form.get("seat_no")
    amount = request.form.get("amount")

    # Store booking info temporarily
    session["pending_booking"] = {
        "name": name, "contact": contact, "email": email,
        "flight_id": flight_id, "seat_no": seat_no, "amount": amount
    }

    # Temporary placeholder for booking_id (will be generated after payment confirm)
    booking_id = session.get("temp_booking_id") or 1  

    return render_template("payment_page.html",
                           booking_id=booking_id,
                           name=name,
                           flight_id=flight_id,
                           seat_no=seat_no,
                           amount=amount)


# ====================================
# 2️⃣ CONFIRM PAYMENT (Practice Mode: does NOTHING)
# ====================================
@payment_bp.post("/confirm_payment")
def confirm_payment():
    return redirect(url_for("bookings.book_form"))




# ====================================
# 3️⃣ PAYMENT SUCCESS PAGE
# ====================================
@payment_bp.get("/success")
def payment_success():
    booking_id = request.args.get("booking_id")
    amount = request.args.get("amount")

    # ✅ Payment Success Page — auto redirect after 3 seconds
    return render_template(
        "payment_success.html",
        booking_id=booking_id,
        amount=amount
    )


        
