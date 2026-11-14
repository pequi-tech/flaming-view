"""Período consultado dentro do arquivo."""
import unittest
from app.domain.errors import YearsOutOfRange
from app.domain.years import year_range


class TestYears(unittest.TestCase):
    def test_padrao_e_todo_o_arquivo(self):
        self.assertEqual(year_range([2003, 2025]), range(2003, 2026))

    def test_recorte(self):
        self.assertEqual(year_range([2003, 2025], 2010, 2012), range(2010, 2013))

    def test_fora_do_arquivo(self):
        for a, b in [(1990, 2000), (2020, 2030), (2015, 2010)]:
            with self.subTest(a=a, b=b), self.assertRaises(YearsOutOfRange):
                year_range([2003, 2025], a, b)


if __name__ == '__main__':
    unittest.main()
