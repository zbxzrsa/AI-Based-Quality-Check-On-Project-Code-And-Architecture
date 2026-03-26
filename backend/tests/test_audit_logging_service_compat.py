import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.audit_logging_service import AuditService


class AuditLoggingServiceCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_audit_service_log_action_delegates_to_unified_audit_service(self):
        with patch("app.core.audit_service.UnifiedAuditService.log_action", new_callable=AsyncMock) as log_action:
            log_action.return_value = "logged"
            result = await AuditService.log_action("db-session", user_id="user-1", action="export")

        self.assertEqual(result, "logged")
        log_action.assert_awaited_once_with("db-session", user_id="user-1", action="export")


if __name__ == "__main__":
    unittest.main()
