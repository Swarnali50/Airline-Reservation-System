-- =======================
-- PROCEDURES FOR BOOKING & CANCELLATION
-- =======================

-- BOOK SEAT PROCEDURE
CREATE OR REPLACE PROCEDURE proc_book_seat (
  p_passenger_id IN NUMBER,
  p_flight_id IN VARCHAR2,
  p_seat_no IN VARCHAR2,
  p_amount IN NUMBER,
  p_out_booking_id OUT NUMBER,
  p_out_status OUT VARCHAR2
) AS
  v_seats NUMBER;
BEGIN
  -- Check seat availability
  SELECT seats_available INTO v_seats
  FROM flight
  WHERE flight_id = p_flight_id
  FOR UPDATE;

  IF v_seats <= 0 THEN
    p_out_booking_id := NULL;
    p_out_status := 'NO_SEATS';
    RETURN;
  END IF;

  -- Reduce seat count
  UPDATE flight
     SET seats_available = seats_available - 1
   WHERE flight_id = p_flight_id;

  -- Create booking (payment will be completed later)
  INSERT INTO booking (passenger_id, flight_id, seat_no, fare_paid, status)
  VALUES (p_passenger_id, p_flight_id, p_seat_no, p_amount, 'PENDING')
  RETURNING booking_id INTO p_out_booking_id;

  COMMIT;
  p_out_status := 'SUCCESS';

EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    p_out_booking_id := NULL;
    p_out_status := 'ERROR:' || SUBSTR(SQLERRM,1,200);
END;
/


-- CANCEL BOOKING PROCEDURE
CREATE OR REPLACE PROCEDURE proc_cancel_booking (
  p_booking_id IN NUMBER,
  p_out_status OUT VARCHAR2
) AS
  v_flight_id VARCHAR2(20);
  v_status VARCHAR2(20);
BEGIN
  SELECT flight_id, status INTO v_flight_id, v_status
  FROM booking
  WHERE booking_id = p_booking_id
  FOR UPDATE;

  IF v_status = 'CANCELLED' THEN
    p_out_status := 'ALREADY_CANCELLED';
    RETURN;
  END IF;

  -- Cancel booking
  UPDATE booking
     SET status = 'CANCELLED'
   WHERE booking_id = p_booking_id;

  -- Restore seat
  UPDATE flight
     SET seats_available = seats_available + 1
   WHERE flight_id = v_flight_id;

  -- Cancel payment if exists
  UPDATE payment
     SET status = 'CANCELLED'
   WHERE booking_id = p_booking_id;

  COMMIT;
  p_out_status := 'CANCELLED';

EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    p_out_status := 'ERROR:' || SUBSTR(SQLERRM,1,200);
END;
/

