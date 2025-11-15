from flask import Blueprint, request, jsonify
from .db import get_db_connection


passengers_bp = Blueprint("passengers", __name__, url_prefix="")

@passengers_bp.post("/passengers")
def create_passenger():
    data = request.get_json(force=True)
    name = data.get("name"); contact = data.get("contact"); email = data.get("email")
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO passenger (name, contact, email)
        VALUES (:1, :2, :3)
        RETURNING passenger_id INTO :id
    """, (name, contact, email, cur.var(int)))
    pid = cur.getimplicitresults()[0][0]
    conn.commit(); cur.close(); conn.close()
    return jsonify({"passenger_id": pid}), 201
