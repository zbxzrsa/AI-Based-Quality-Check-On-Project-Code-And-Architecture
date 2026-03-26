import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.repository import (
    AddRepositoryRequest,
    DependencyInfo,
    RepositoryInfo,
)
from app.services.repository_service import RepositoryService
from common.shared.enums import RepositoryStatus, RepositoryURLFormat


class RepositoryServiceCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    def test_parse_repository_url_delegates_to_refactored_service(self):
        db = AsyncMock()
        parsed = RepositoryInfo(
            owner="octocat",
            name="hello-world",
            url_format=RepositoryURLFormat.HTTPS,
            full_url="https://github.com/octocat/hello-world",
            clone_url="https://github.com/octocat/hello-world.git",
        )
        inner = SimpleNamespace(parse_repository_url=lambda url: parsed)

        with patch("app.services.repository_service.create_repository_service", return_value=inner) as factory:
            service = RepositoryService(db)
            result = service.parse_repository_url("https://github.com/octocat/hello-world")

        self.assertIs(result, parsed)
        factory.assert_called_once_with(db, None)

    async def test_validate_repository_wraps_legacy_response_model(self):
        db = AsyncMock()
        repo_info = RepositoryInfo(
            owner="octocat",
            name="hello-world",
            url_format=RepositoryURLFormat.HTTPS,
            full_url="https://github.com/octocat/hello-world",
            clone_url="https://github.com/octocat/hello-world.git",
        )
        inner = SimpleNamespace(
            validate_repository_access=AsyncMock(
                return_value={
                    "is_valid": True,
                    "is_accessible": True,
                    "exists": True,
                    "default_branch": "main",
                    "available_branches": ["main", "develop"],
                    "available_tags": ["v1.0.0"],
                    "error_message": None,
                }
            )
        )

        with patch("app.services.repository_service.create_repository_service", return_value=inner):
            service = RepositoryService(db, github_token="secret-token")
            result = await service.validate_repository(repo_info, branch="develop")

        self.assertTrue(result.is_valid)
        self.assertEqual(result.default_branch, "main")
        self.assertEqual(result.available_branches, ["main", "develop"])
        inner.validate_repository_access.assert_awaited_once_with(repo_info, "develop")

    async def test_fetch_dependencies_returns_dependency_info(self):
        db = AsyncMock()
        repo_info = RepositoryInfo(
            owner="octocat",
            name="hello-world",
            url_format=RepositoryURLFormat.HTTPS,
            full_url="https://github.com/octocat/hello-world",
            clone_url="https://github.com/octocat/hello-world.git",
        )
        dependency_info = DependencyInfo(
            package_manager="npm",
            dependencies={"react": "^19.0.0"},
            dev_dependencies={"typescript": "^5.0.0"},
            peer_dependencies={},
        )
        inner = SimpleNamespace(fetch_dependencies=AsyncMock(return_value=dependency_info))

        with patch("app.services.repository_service.create_repository_service", return_value=inner):
            service = RepositoryService(db)
            result = await service.fetch_dependencies(repo_info, branch="main")

        self.assertIs(result, dependency_info)
        inner.fetch_dependencies.assert_awaited_once_with(repo_info, "main")

    async def test_add_repository_preserves_legacy_response_shape(self):
        db = AsyncMock()
        request = AddRepositoryRequest(repository_url="https://github.com/octocat/hello-world.git")
        created_at = datetime.now(timezone.utc)
        response = {
            "id": "repo-1",
            "repository_url": request.repository_url,
            "owner": "octocat",
            "name": "hello-world",
            "branch": "main",
            "version": None,
            "status": RepositoryStatus.COMPLETED,
            "description": None,
            "auto_update": False,
            "last_synced": None,
            "created_at": created_at,
            "updated_at": created_at,
            "metadata": {"source": "test"},
        }
        inner = SimpleNamespace(create_entity=AsyncMock(return_value=response))

        with patch("app.services.repository_service.create_repository_service", return_value=inner):
            service = RepositoryService(db)
            result = await service.add_repository(request, user_id="user-1")

        self.assertEqual(result.id, "repo-1")
        self.assertEqual(result.status, RepositoryStatus.COMPLETED)
        self.assertEqual(result.metadata["source"], "test")
        inner.create_entity.assert_awaited_once_with(request, "user-1")


if __name__ == "__main__":
    unittest.main()
