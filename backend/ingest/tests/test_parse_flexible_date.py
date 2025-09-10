from datetime import date
from django.test import SimpleTestCase
from ingest.track_processing_helpers import parse_flexible_date, MIN_YEAR


class ParseFlexibleDateTests(SimpleTestCase):
    def test_parse_valid_date(self):
        valid_dates = [
            ("1987-12-03", date(1987, 12, 3)),
            ("2005-07", date(2005, 7, 1)),
            ("2005", date(2005, 1, 1)),
            ("2000.06.21", date(2000, 6, 21)),
            ("23 February 1998", date(1998, 2, 23)),
            ("23 Feb 1998", date(1998, 2, 23)),
            ("2005-07-14T13:45:30", date(2005, 7, 14)),
            ("2005-07-14T13:45:30Z", date(2005, 7, 14)),
            ("2005-07-14 13:45:30", date(2005, 7, 14)),
        ]

        for input, expected in valid_dates:
            self.assertEqual(parse_flexible_date(input), expected)
    
    def test_parse_year_only(self):
        self.assertEqual(parse_flexible_date("1994"), date(1994, 1, 1))
    
    def test_dont_parse_empty(self):
        self.assertEqual(parse_flexible_date(), None)
    
    def test_dont_parse_none(self):
        self.assertEqual(parse_flexible_date(None), None)
    
    def test_dont_parse_empty_string(self):
        self.assertEqual(parse_flexible_date(""), None)

    def test_dont_parse_char_date(self):
        self.assertEqual(parse_flexible_date("YOLO"), None)

    def test_dont_parse_ancient_date(self):
        self.assertEqual(parse_flexible_date(f"{MIN_YEAR-1}"), None)
        self.assertEqual(parse_flexible_date(f"{MIN_YEAR}"), date(MIN_YEAR, 1, 1))
        