# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from datetime import date, timedelta
import json
import re

SOURCE = "https://www.gov.uk/bank-holidays.json"
REGIONS = ("england-and-wales", "scotland", "northern-ireland")


def pack(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Date must be YYYY-MM-DD")
    return date.fromisoformat(value)


def observe(region, start, end):
    response = gl.nondet.web.get(SOURCE)
    if response.status != 200:
        raise gl.vm.UserError("HOLIDAY_SOURCE_UNAVAILABLE")
    try:
        section = json.loads(response.body)[region]
        if section["division"] != region or not isinstance(section["events"], list):
            raise ValueError("Unexpected holiday division")
        days = {parse_date(item["date"]) for item in section["events"]}
    except (KeyError, TypeError, ValueError):
        raise gl.vm.UserError("INVALID_HOLIDAY_FEED")
    years = {day.year for day in days}
    if any(year not in years for year in range(start.year, end.year + 1)):
        raise gl.vm.UserError("OUTSIDE_PUBLISHED_YEARS")
    return pack(sorted(day.isoformat() for day in days if start < day <= end))


def calculate(start, holidays, count):
    remaining = count
    trace = []
    for step in range(1, 46):
        day = start + timedelta(days=step)
        label = day.isoformat()
        reason = "bank_holiday" if label in holidays else "weekend" if day.weekday() >= 5 else "workday"
        trace.append({"date": label, "kind": reason})
        if reason == "workday":
            remaining -= 1
            if remaining == 0:
                return label, trace
    raise gl.vm.UserError("INSUFFICIENT_WORKDAYS")


@allow_storage
class CalendarCutoff(gl.Contract):
    certificates: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.view
    def read_certificate(self, owner: str, key: str) -> str:
        return self.certificates.get(owner.lower() + "/" + key, "")

    @gl.public.write
    def certify(self, key: str, region: str, start_date: str, working_days: u32) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,39}", key):
            raise gl.vm.UserError("INVALID_CERTIFICATE_KEY")
        if region not in REGIONS or not 1 <= working_days <= 20:
            raise gl.vm.UserError("INVALID_CALENDAR_POLICY")
        try:
            start = parse_date(start_date)
            end = start + timedelta(days=45)
        except (ValueError, OverflowError):
            raise gl.vm.UserError("INVALID_START_DATE")
        owner = str(gl.message.sender_address).lower()
        record_key = owner + "/" + key
        if record_key in self.certificates:
            raise gl.vm.UserError("CERTIFICATE_ALREADY_EXISTS")
        holidays = json.loads(gl.eq_principle.strict_eq(lambda: observe(region, start, end)))
        deadline, trace = calculate(start, set(holidays), working_days)
        self.certificates[record_key] = pack({
            "owner": owner, "key": key, "region": region, "start": start_date,
            "working_days": int(working_days), "deadline": deadline,
            "observed_through": end.isoformat(), "holidays": holidays, "trace": trace,
        })
