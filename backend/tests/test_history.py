import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.session import SessionLocal, init_db
from app.models.match import Match
from app.api.routers.history import get_match_history, get_match_history_detail
from app.match.match_service import MatchService


class TestMatchHistoryPersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_match_history_query(self):
        response = get_match_history(page=1, page_size=5, db=self.db)
        self.assertIsNotNone(response)
        self.assertGreater(response.total, 0)
        self.assertGreater(len(response.items), 0)

        first = response.items[0]
        self.assertIsNotNone(first.id)
        self.assertIsNotNone(first.team1_name)
        self.assertIsNotNone(first.team2_name)
        self.assertIn(first.status.upper(), ["COMPLETED", "TIED", "FINISHED"])
        print(f"\n[TEST PASS] Loaded {response.total} matches. First match: {first.team1_name} vs {first.team2_name} -> {first.result_margin}")

    def test_match_history_detail(self):
        # Fetch first completed match
        m = self.db.query(Match).filter(Match.status == "COMPLETED").first()
        self.assertIsNotNone(m)

        detail_res = get_match_history_detail(match_id=m.id, db=self.db)
        self.assertTrue(detail_res.success)
        self.assertIsNotNone(detail_res.data)
        self.assertEqual(detail_res.data.match_id, m.id)
        print(f"[TEST PASS] Match Detail for ID {m.id} retrieved. Scorecard present: {detail_res.data.scorecard is not None}")


if __name__ == "__main__":
    unittest.main()
