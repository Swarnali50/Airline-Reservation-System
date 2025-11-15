from datetime import datetime

def parse_date_yyyy_mm_dd(s: str):
    return datetime.strptime(s, "%Y-%m-%d")
