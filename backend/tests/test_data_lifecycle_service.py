import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.data_lifecycle_service import DataLifecycleService


class DataLifecycleServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cleanup_old_analysis_results_skips_when_table_missing(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=SimpleNamespace(scalar=lambda: False))

        service = DataLifecycleService(db)

        result = await service.cleanup_old_analysis_results()

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "analysis_results_table_not_found")
        self.assertEqual(result["deleted_count"], 0)
        db.commit.assert_not_awaited()

    async def test_get_cleanup_statistics_includes_sessions_and_missing_audit_table(self):
        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                SimpleNamespace(scalar=lambda: True),
                SimpleNamespace(
                    fetchone=lambda: SimpleNamespace(
                        total=8,
                        expired=3,
                        oldest=None,
                        newest=None,
                    )
                ),
                SimpleNamespace(scalar=lambda: True),
                SimpleNamespace(
                    fetchone=lambda: SimpleNamespace(
                        total=4,
                        expired=1,
                        oldest=None,
                        newest=None,
                    )
                ),
                SimpleNamespace(scalar=lambda: True),
                SimpleNamespace(
                    fetchone=lambda: SimpleNamespace(
                        total=6,
                        expired=2,
                        oldest=None,
                        newest=None,
                    )
                ),
                SimpleNamespace(scalar=lambda: False),
            ]
        )

        service = DataLifecycleService(db)

        stats = await service.get_cleanup_statistics()

        self.assertEqual(stats["analysis_results"]["expired"], 3)
        self.assertEqual(stats["architectural_baselines"]["expired"], 1)
        self.assertEqual(stats["expired_sessions"]["expired"], 2)
        self.assertEqual(stats["audit_logs"]["status"], "skipped")
        self.assertEqual(stats["audit_logs"]["reason"], "audit_log_entries_table_not_found")


if __name__ == "__main__":
    unittest.main()
