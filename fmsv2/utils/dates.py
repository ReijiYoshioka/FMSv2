import calendar
from datetime import datetime


def current_month_str():
    return datetime.now().strftime("%Y-%m")


def month_range(month_str):
    """'YYYY-MM' → (start, end) の半開区間。end は翌月1日。"""
    year, month = map(int, month_str.split("-"))
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year + 1:04d}-01-01" if month == 12 else f"{year:04d}-{month + 1:02d}-01"
    return start, end


def year_range(year_str):
    year = int(year_str)
    return f"{year:04d}-01-01", f"{year + 1:04d}-01-01"


def last_day_of_month(year, month):
    return calendar.monthrange(year, month)[1]


def shift_month(month_str, delta):
    """'YYYY-MM'をdeltaヶ月分ずらした文字列を返す(delta=-1で前月)。"""
    year, month = map(int, month_str.split("-"))
    total = year * 12 + (month - 1) + delta
    new_year, new_month = divmod(total, 12)
    return f"{new_year:04d}-{new_month + 1:02d}"


def is_valid_month_str(month_str):
    try:
        year, month = month_str.split("-")
        year_i, month_i = int(year), int(month)
        return len(year) == 4 and len(month) == 2 and 1 <= month_i <= 12 and year_i > 0
    except (ValueError, AttributeError):
        return False


def is_valid_year_str(year_str):
    try:
        return len(year_str) == 4 and int(year_str) > 0
    except (ValueError, TypeError):
        return False
