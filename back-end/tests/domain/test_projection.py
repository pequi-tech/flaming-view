"""Projeção do mês corrente."""
import unittest
from app.domain.projection import project


class TestProjecao(unittest.TestCase):
    def test_mes_corrente(self):
            self.assertEqual(project(100, day=10, days_in_month=30), 300)
            self.assertEqual(project(100, day=30, days_in_month=30), 100)


if __name__ == '__main__':
    unittest.main()
