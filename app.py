from flask import Flask, render_template, redirect, url_for, session
from backend.flights import flights_bp
from backend.passengers import passengers_bp
from backend.bookings import bookings_bp
from backend.payment import payment_bp  
from backend.users import users_bp
from backend.admin import admin_bp

import os


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")

    # ✅ Register all blueprints
    app.register_blueprint(flights_bp)
    app.register_blueprint(passengers_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(admin_bp)

    # ✅ Home route: decides where to go based on login status
    @app.route("/")
    def home():
        # If user logged in → go to welcome dashboard
        if "user_name" in session:
            return redirect(url_for("users.welcome"))
        # Otherwise → show index with login/signup
        return render_template("index.html")

    # ✅ Optional: nice route to reset session manually
    @app.route("/reset")
    def reset_session():
        session.clear()
        return redirect(url_for("home"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
