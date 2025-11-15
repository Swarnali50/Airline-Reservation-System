from flask import Blueprint, request, render_template
from .db import get_db_connection


flights_bp = Blueprint("flights", __name__, url_prefix="")

@flights_bp.get("/flights")
def list_flights():
    src = request.args.get("src", "").upper().strip()
    dst = request.args.get("dst", "").upper().strip()
    date = request.args.get("date", "").strip()  # YYYY-MM-DD (optional)

    q = """
    SELECT flight_id, origin_airport_id, destination_airport_id,
           TO_CHAR(departure_utc, 'YYYY-MM-DD HH24:MI ') dep,
           TO_CHAR(arrival_utc,   'YYYY-MM-DD HH24:MI ') arr,
           price, seats_available
      FROM flight
     WHERE 1=1
    """
    params = []
    if src:
        q += " AND origin_airport_id = :src"
        params.append(src)
    if dst:
        q += " AND destination_airport_id = :dst"
        params.append(dst)
    if date:
        q += " AND TRUNC(CAST(departure_utc AT LOCAL AS DATE)) = TO_DATE(:d, 'YYYY-MM-DD')"
        params.append(date)
    q += " ORDER BY departure_utc"

    conn = get_db_connection(); cur = conn.cursor()
    cur.execute(q, params)
    flights = cur.fetchall()
    cur.close(); conn.close()
    return render_template("flights_list.html", flights=flights, src=src, dst=dst, date=date)

