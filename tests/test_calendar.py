import json
from types import SimpleNamespace
import unittest
from host import UserError, load_contract


class CalendarTest(unittest.TestCase):
    def setUp(self):
        self.sender = SimpleNamespace(sender_address="0x" + "1" * 40)
        self.region = "england-and-wales"
        self.data = {self.region:{
            "division":self.region, "events":[{"date":day} for day in
                ["2027-01-01", "2026-12-28", "2026-12-25", "2026-12-25"]],
        }}
        self.status = 200
        self.contract = load_contract("calendar_cutoff.py", "CalendarCutoff", self.fetch, self.sender)

    def fetch(self, url):
        self.assertEqual(url, "https://www.gov.uk/bank-holidays.json")
        return SimpleNamespace(status=self.status, body=json.dumps(self.data))

    def certify(self):
        self.contract.certify("year-end", self.region, "2026-12-24", 2)

    def test_excludes_start_weekend_and_observed_holidays(self):
        self.certify()
        record = json.loads(self.contract.read_certificate(self.sender.sender_address, "year-end"))
        self.assertEqual(record["deadline"], "2026-12-30")
        self.assertEqual(record["holidays"], ["2026-12-25", "2026-12-28", "2027-01-01"])
        self.assertEqual(record["trace"][-2:], [
            {"date":"2026-12-29", "kind":"workday"},
            {"date":"2026-12-30", "kind":"workday"},
        ])

    def test_immutable_but_namespaced(self):
        self.certify()
        original = self.contract.read_certificate(self.sender.sender_address, "year-end")
        self.data[self.region]["events"].pop(1)
        with self.assertRaisesRegex(UserError, "CERTIFICATE_ALREADY_EXISTS"):
            self.certify()
        self.assertEqual(self.contract.read_certificate(self.sender.sender_address, "year-end"), original)
        self.sender.sender_address = "0x" + "2" * 40
        self.certify()
        record = json.loads(self.contract.read_certificate(self.sender.sender_address, "year-end"))
        self.assertEqual(record["deadline"], "2026-12-29")

    def test_unsupported_year_and_bad_source_fail_without_write(self):
        self.data[self.region]["events"].pop(0)
        with self.assertRaisesRegex(UserError, "OUTSIDE_PUBLISHED_YEARS"):
            self.certify()
        self.data[self.region]["events"].append({"date":"not-a-date"})
        with self.assertRaisesRegex(UserError, "INVALID_HOLIDAY_FEED"):
            self.certify()
        self.status = 503
        with self.assertRaisesRegex(UserError, "HOLIDAY_SOURCE_UNAVAILABLE"):
            self.certify()
        self.assertEqual(self.contract.read_certificate(self.sender.sender_address, "year-end"), "")

    def test_invalid_request_bounds(self):
        with self.assertRaisesRegex(UserError, "INVALID_START_DATE"):
            self.contract.certify("year-end", self.region, "2026-02-31", 1)
        with self.assertRaisesRegex(UserError, "INVALID_CALENDAR_POLICY"):
            self.contract.certify("year-end", self.region, "2026-02-01", 21)
