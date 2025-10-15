from datetime import date
from django.test import SimpleTestCase
from ingest.track_processing_helpers import parse_flexible_date, MIN_YEAR


class ParseFlexibleDateTests(SimpleTestCase):
    def test_parse_valid_date(self):
        valid_dates = [
            ("1987-12-03", "1987-12-03"),
            ("2005-07", "2005-07-01"),
            ("2005", "2005-01-01"),
            ("2000.06.21", "2000-06-21"),
            ("23 February 1998", "1998-02-23"),
            ("23 Feb 1998", "1998-02-23"),
            ("2005-07-14T13:45:30", "2005-07-14"),
            ("2005-07-14T13:45:30Z", "2005-07-14"),
            ("2005-07-14 13:45:30", "2005-07-14"),
        ]

        for input, expected in valid_dates:
            self.assertEqual(parse_flexible_date(input), expected)
    
    def test_parse_year_only(self):
        self.assertEqual(parse_flexible_date("1994"), "1994-01-01")

    def test_parse_incomplete_date(self):
        self.assertEqual(parse_flexible_date("1984-1"), "1984-01-01")
    
    def test_dont_parse_empty(self):
        self.assertEqual(parse_flexible_date(), None)
    
    def test_dont_parse_none(self):
        self.assertEqual(parse_flexible_date(None), None)
    
    def test_dont_parse_empty_string(self):
        self.assertEqual(parse_flexible_date(""), None)

    def test_dont_parse_char_date(self):
        self.assertEqual(parse_flexible_date("YOLO"), None)

    def test_dont_parse_invalid_date(self):
        self.assertEqual(parse_flexible_date("0000-00-00"), None)
        self.assertEqual(parse_flexible_date("0001"), None)

    def test_dont_parse_ancient_date(self):
        self.assertEqual(parse_flexible_date(f"{MIN_YEAR-1}"), None)
        self.assertEqual(parse_flexible_date(f"{MIN_YEAR}"), f"{MIN_YEAR}-01-01")
        