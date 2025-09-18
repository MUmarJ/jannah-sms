# app/core/templates.py
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

def format_datetime(dt, format_str="%B %d, %Y at %I:%M %p"):
    if dt:
        return dt.strftime(format_str)
    return "Not available"

def format_phone(phone):
    if phone:
        cleaned = ''.join(filter(str.isdigit, phone))
        if len(cleaned) == 10:
            return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        elif len(cleaned) == 11 and cleaned[0] == '1':
            return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
    return phone

templates.env.filters['format_datetime'] = format_datetime
templates.env.filters['format_phone'] = format_phone