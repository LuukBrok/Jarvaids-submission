"""Conservative date resolution against a recorded instant and an IANA time zone."""
from datetime import date, datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .validation import require, text

MONTHS = {name: i for i, name in enumerate(('january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december'), 1)}
WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')


def zone_name(value):
    text(value, 'timezone', 100)
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        require(False, 'calendar_timezone', 'Choose a recognised IANA time zone, such as Europe/Amsterdam.')
    return value


def local_day(instant, zone):
    return datetime.fromtimestamp(instant, ZoneInfo(zone)).date()


def source_instant(data):
    return data.get('captured_at_utc_ms', data['created_at'] * 1000) / 1000


def iso_day(value, empty=True):
    text(value, 'date', 10, empty=empty)
    if not value and empty:
        return ''
    try:
        parsed = date.fromisoformat(value)
        require(parsed.isoformat() == value, 'calendar_date', 'Use an exact YYYY-MM-DD date.')
    except ValueError:
        require(False, 'calendar_date', 'Use a valid YYYY-MM-DD date.')
    return value


def resolve_date(phrase, instant, zone, *, period=False):
    """Return (ISO date, clarification). Unknown/ambiguous phrases stay undated."""
    if not phrase.strip():
        return '', ''
    today = local_day(instant, zone)
    value = re.sub(r'^(?:due |by |on |for )+', '', phrase.casefold().strip()).rstrip('.')
    offsets = {'today': 0, 'tomorrow': 1, 'the day after tomorrow': 2, 'day after tomorrow': 2, 'yesterday': -1}
    if value in offsets:
        return (today + timedelta(days=offsets[value])).isoformat(), ''
    if value in ('this week', 'next week', 'last week'):
        if period:
            return (today-timedelta(days=today.weekday())+timedelta(days={'this week': 0, 'next week': 7, 'last week': -7}[value])).isoformat(), ''
        return '', 'Which day '+value+'?'
    if value in ('this month', 'next month', 'last month') and period:
        index = today.year*12+today.month-1+{'this month': 0, 'next month': 1, 'last month': -1}[value]
        return date(index//12, index % 12+1, 1).isoformat(), ''
    if value in ('this year', 'next year', 'last year') and period:
        return date(today.year+{'this year': 0, 'next year': 1, 'last year': -1}[value], 1, 1).isoformat(), ''
    match = re.fullmatch(r'(?:in )?(\d+) days?', value)
    if match and int(match[1]) <= 3660:
        return (today+timedelta(days=int(match[1]))).isoformat(), ''
    match = re.fullmatch(r'(this |next )?('+'|'.join(WEEKDAYS)+r')(?: (this|next) week)?', value)
    if match:
        prefix, name, week = match.groups(); weekday = WEEKDAYS.index(name)
        if prefix == 'next ' and not week:
            return '', 'Does next '+name+' mean the upcoming '+name+' or the one in the following week?'
        if prefix == 'this ' or week:
            resolved = today-timedelta(days=today.weekday())+timedelta(days=weekday+(7 if week == 'next' else 0))
        else:
            resolved = today+timedelta(days=(weekday-today.weekday()) % 7)
        return resolved.isoformat(), ''
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return date.fromisoformat(value).isoformat(), ''
        month_names = '|'.join(MONTHS)
        match = re.fullmatch(r'(?:the )?(\d{1,2})(?:st|nd|rd|th)?(?: of)? ('+month_names+r')(?:,? (\d{4}))?', value)
        if match:
            day, month, year = int(match[1]), MONTHS[match[2]], int(match[3] or today.year)
        else:
            match = re.fullmatch(r'('+month_names+r') (\d{1,2})(?:st|nd|rd|th)?(?:,? (\d{4}))?', value)
            if not match:
                if period:
                    month = re.fullmatch(r'('+month_names+r')(?: (\d{4}))?', value)
                    if month:
                        return date(int(month[2] or today.year), MONTHS[month[1]], 1).isoformat(), ''
                    if re.fullmatch(r'\d{4}', value):
                        return date(int(value), 1, 1).isoformat(), ''
                return '', 'Please give an exact date for “'+phrase+'”, such as 2026-10-23.'
            month, day, year = MONTHS[match[1]], int(match[2]), int(match[3] or today.year)
        resolved = date(year, month, day)
        if not match[3] and resolved < today:
            return '', 'Which year do you mean for “'+phrase+'”?'
        return resolved.isoformat(), ''
    except (ValueError, OverflowError):
        return '', 'Please check the date “'+phrase+'”.'


def resolve_time(phrase):
    if not phrase:
        return '', ''
    value = re.sub(r'^at ', '', phrase.casefold().strip()).replace('.', '').replace(' ', '')
    match = re.fullmatch(r'(\d{1,2})(?::(\d{2}))?(am|pm)', value)
    if match and 1 <= int(match[1]) <= 12:
        hour, minute = int(match[1]) % 12+(12 if match[3] == 'pm' else 0), int(match[2] or 0)
    else:
        match = re.fullmatch(r'(\d{1,2}):(\d{2})', value)
        if not match:
            return '', 'Please give a clear time, such as 14:00 or 2 pm.'
        hour, minute = int(match[1]), int(match[2])
    if hour < 24 and minute < 60:
        return f'{hour:02d}:{minute:02d}', ''
    return '', 'Please check the event time.'
