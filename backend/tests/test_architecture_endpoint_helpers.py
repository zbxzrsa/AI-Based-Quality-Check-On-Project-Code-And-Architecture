import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import architecture as architecture_endpoint


class ArchitectureEndpointHelperTests(unittest.IsolatedAsyncioTestCase):
    def test_health_status_from_violation_count_uses_shared_thresholds(self):
        self.assertEqual(
            architecture_endpoint._health_status_from_violation_count(0),
            "healthy",
        )
        self.assertEqual(
            architecture_endpoint._health_status_from_violation_count(3),
            "warning",
        )
        self.assertEqual(
            architecture_endpoint._health_status_from_violation_count(5),
            "critical",
        )

    async def test_count_violations_for_pull_requests_short_circuits_empty_input(self):
        db = SimpleNamespace(execute=AsyncMock())

        result = await architecture_endpoint._count_violations_for_pull_requests(db, [])

        self.assertEqual(result, 0)
        db.execute.assert_not_awaited()

    async def test_get_analysis_violations_returns_list_shape(self):
        expected = [SimpleNamespace(id="v1"), SimpleNamespace(id="v2")]
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    scalars=lambda: SimpleNamespace(all=lambda: expected)
                )
            )
        )

        result = await architecture_endpoint._get_analysis_violations(db, "analysis-1")

        self.assertEqual(result, expected)
        db.execute.assert_awaited_once()

    async def test_count_analysis_violations_defaults_none_to_zero(self):
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar=lambda: None))
        )

        result = await architecture_endpoint._count_analysis_violations(db, "analysis-1")

        self.assertEqual(result, 0)
        db.execute.assert_awaited_once()

    async def test_get_latest_analysis_for_pull_request_returns_scalar_row(self):
        expected = SimpleNamespace(id="analysis-1")
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(scalar_one_or_none=lambda: expected)
            )
        )

        result = await architecture_endpoint._get_latest_analysis_for_pull_request(
            db,
            "pr-1",
        )

        self.assertIs(result, expected)
        db.execute.assert_awaited_once()

    def test_get_violation_components_preserves_or_sorts_component_order(self):
        violations = [
            SimpleNamespace(component="service", related_component="db"),
            SimpleNamespace(component="api", related_component="service"),
        ]

        self.assertEqual(
            architecture_endpoint._get_violation_components(violations),
            ["service", "db", "api"],
        )
        self.assertEqual(
            architecture_endpoint._get_violation_components(
                violations,
                sort_components=True,
            ),
            ["api", "db", "service"],
        )

    def test_build_graph_from_violations_maps_nodes_and_circular_edges(self):
        violations = [
            SimpleNamespace(
                component="service",
                related_component="db",
                severity="critical",
                type="circular_dependency",
            ),
            SimpleNamespace(
                component="api",
                related_component="service",
                severity="medium",
                type="dependency",
            ),
        ]

        nodes, edges = architecture_endpoint._build_graph_from_violations(
            violations,
            edge_type="dependency",
            sort_components=True,
        )

        self.assertEqual([node.label for node in nodes], ["api", "db", "service"])
        self.assertEqual(nodes[-1].health, "critical")
        self.assertEqual(len(edges), 2)
        self.assertTrue(edges[0].is_circular)
        self.assertEqual(edges[0].type, "dependency")

    def test_build_architecture_graph_from_summary_supports_branch_shape(self):
        summary = {
            "components": [
                {"name": "API", "type": "service", "health": "warning", "complexity": 7},
            ],
            "dependencies": [
                {"source": 10, "target": 20, "is_circular": True, "type": "ignored"},
            ],
            "circular_dependency_chains": [["API", "DB"]],
        }

        nodes, edges, chains = architecture_endpoint._build_architecture_graph_from_summary(
            summary,
            include_extended_fields=False,
        )

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].id, "1")
        self.assertEqual(nodes[0].label, "API")
        self.assertEqual(nodes[0].position, {"x": 100, "y": 100})
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].id, "e1")
        self.assertEqual(edges[0].source, "10")
        self.assertEqual(edges[0].target, "20")
        self.assertEqual(edges[0].type, "default")
        self.assertTrue(edges[0].is_circular)
        self.assertEqual(chains, [])

    def test_build_architecture_graph_from_summary_supports_analysis_shape(self):
        summary = {
            "components": [
                {
                    "id": "component-1",
                    "name": "Worker",
                    "type": "job",
                    "health": "critical",
                    "complexity": 9,
                    "position": {"x": 10, "y": 20},
                    "properties": {"owner": "platform"},
                    "metrics": {"fanin": 3},
                },
            ],
            "dependencies": [
                {
                    "id": "edge-1",
                    "source": "component-1",
                    "target": "component-2",
                    "type": "async",
                    "is_circular": False,
                    "properties": {"weight": 2},
                },
            ],
            "circular_dependency_chains": [["Worker", "Queue"]],
        }

        nodes, edges, chains = architecture_endpoint._build_architecture_graph_from_summary(
            summary,
            include_extended_fields=True,
        )

        self.assertEqual(nodes[0].id, "component-1")
        self.assertEqual(nodes[0].position, {"x": 10, "y": 20})
        self.assertEqual(nodes[0].properties, {"owner": "platform"})
        self.assertEqual(nodes[0].metrics, {"fanin": 3})
        self.assertEqual(edges[0].id, "edge-1")
        self.assertEqual(edges[0].type, "async")
        self.assertEqual(edges[0].properties, {"weight": 2})
        self.assertEqual(chains, [["Worker", "Queue"]])

    def test_map_analysis_status_keeps_legacy_processing_contract(self):
        self.assertEqual(
            architecture_endpoint._map_analysis_status("in_progress"),
            "processing",
        )
        self.assertEqual(
            architecture_endpoint._map_analysis_status("completed"),
            "completed",
        )
        self.assertEqual(
            architecture_endpoint._map_analysis_status("unknown"),
            "pending",
        )

    def test_build_dependency_graph_from_summary_maps_summary_fields(self):
        summary = {
            "components": [
                {
                    "id": "node-1",
                    "name": "worker",
                    "type": "job",
                    "file_path": "src/worker.ts",
                    "lines_of_code": 120,
                    "complexity": 8,
                    "properties": {"layer": "application"},
                },
            ],
            "dependencies": [
                {
                    "id": "dep-1",
                    "source": "node-1",
                    "target": "node-2",
                    "type": "call",
                    "weight": 2.5,
                    "is_circular": True,
                    "properties": {"frequency": "high"},
                },
            ],
            "circular_dependency_chains": [["worker", "queue"]],
        }

        nodes, edges, chains = architecture_endpoint._build_dependency_graph_from_summary(
            summary
        )

        self.assertEqual(nodes[0].id, "node-1")
        self.assertEqual(nodes[0].name, "worker")
        self.assertEqual(nodes[0].file_path, "src/worker.ts")
        self.assertEqual(nodes[0].properties, {"layer": "application"})
        self.assertEqual(edges[0].id, "dep-1")
        self.assertEqual(edges[0].type, "call")
        self.assertEqual(edges[0].weight, 2.5)
        self.assertTrue(edges[0].is_circular)
        self.assertEqual(chains, [["worker", "queue"]])

    def test_build_dependency_graph_from_summary_returns_empty_shapes_for_non_dict(self):
        nodes, edges, chains = architecture_endpoint._build_dependency_graph_from_summary(None)

        self.assertEqual(nodes, [])
        self.assertEqual(edges, [])
        self.assertEqual(chains, [])


class ArchitectureEndpointContractTests(unittest.TestCase):
    def _build_app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(architecture_endpoint.router, prefix="/architecture")
        return app

    def _override_dependency(self, app: FastAPI, path: str, dependency_name: str, override):
        route = next(
            route for route in app.routes
            if getattr(route, "path", None) == path
        )
        dependency = next(
            dependency for dependency in route.dependant.dependencies
            if dependency.name == dependency_name
        )
        app.dependency_overrides[dependency.call] = override

    def test_get_dependency_graph_returns_stable_response_contract(self):
        app = self._build_app()
        project_id = str(uuid4())
        analysis_id = uuid4()
        started_at = datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc)

        analysis = SimpleNamespace(
            id=analysis_id,
            pull_request_id="pr-1",
            summary={
                "components": [
                    {
                        "id": "node-1",
                        "name": "worker",
                        "type": "job",
                        "file_path": "src/worker.ts",
                        "lines_of_code": 120,
                        "complexity": 8,
                        "properties": {"layer": "application"},
                    },
                ],
                "dependencies": [
                    {
                        "id": "dep-1",
                        "source": "node-1",
                        "target": "node-2",
                        "type": "call",
                        "weight": 2.5,
                        "is_circular": True,
                        "properties": {"frequency": "high"},
                    },
                ],
                "circular_dependency_chains": [["worker", "queue"]],
                "max_depth": 4,
            },
            status=SimpleNamespace(value="in_progress"),
            started_at=started_at,
            completed_at=None,
        )
        pull_request = SimpleNamespace(
            id="pr-1",
            project_id=project_id,
            branch_name="feature/stream-unification",
        )
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    scalar_one_or_none=lambda: pull_request
                )
            )
        )
        user = SimpleNamespace(user_id="user-1", username="tester", role="admin")

        async def override_db():
            return db

        async def override_current_user():
            return user

        self._override_dependency(
            app,
            "/architecture/dependencies/{project_id}",
            "current_user",
            override_current_user,
        )
        self._override_dependency(
            app,
            "/architecture/dependencies/{project_id}",
            "db",
            override_db,
        )

        with patch.object(
            architecture_endpoint,
            "_get_latest_project_analysis",
            AsyncMock(return_value=analysis),
        ):
            with TestClient(app) as client:
                response = client.get(f"/architecture/dependencies/{project_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": str(analysis_id),
                "project_id": project_id,
                "branch_id": "feature/stream-unification",
                "status": "processing",
                "nodes": [
                    {
                        "id": "node-1",
                        "name": "worker",
                        "type": "job",
                        "file_path": "src/worker.ts",
                        "lines_of_code": 120,
                        "complexity": 8,
                        "properties": {"layer": "application"},
                    }
                ],
                "edges": [
                    {
                        "id": "dep-1",
                        "source": "node-1",
                        "target": "node-2",
                        "type": "call",
                        "weight": 2.5,
                        "is_circular": True,
                        "properties": {"frequency": "high"},
                    }
                ],
                "metrics": {
                    "total_nodes": 1,
                    "total_edges": 1,
                    "circular_dependencies": 1,
                    "max_depth": 4,
                    "avg_dependencies_per_node": 1.0,
                },
                "circular_dependency_chains": [["worker", "queue"]],
                "created_at": started_at.isoformat(),
                "updated_at": started_at.isoformat(),
                "api_version": architecture_endpoint.API_VERSION,
            },
        )

    def test_get_architecture_analysis_returns_stable_response_contract(self):
        app = self._build_app()
        analysis_id = uuid4()
        project_id = str(uuid4())
        started_at = datetime(2026, 3, 25, 15, 30, tzinfo=timezone.utc)
        completed_at = datetime(2026, 3, 25, 15, 35, tzinfo=timezone.utc)

        analysis = SimpleNamespace(
            id=analysis_id,
            pull_request_id="pr-2",
            summary={
                "components": [
                    {
                        "id": "component-1",
                        "name": "Worker",
                        "type": "job",
                        "health": "critical",
                        "complexity": 9,
                        "position": {"x": 10, "y": 20},
                        "properties": {"owner": "platform"},
                        "metrics": {"fanin": 3},
                    },
                ],
                "dependencies": [
                    {
                        "id": "edge-1",
                        "source": "component-1",
                        "target": "component-2",
                        "type": "async",
                        "is_circular": False,
                        "properties": {"weight": 2},
                    },
                ],
                "circular_dependency_chains": [["Worker", "Queue"]],
                "max_depth": 6,
            },
            status=SimpleNamespace(value="completed"),
            started_at=started_at,
            completed_at=completed_at,
        )
        pull_request = SimpleNamespace(
            id="pr-2",
            project_id=project_id,
            branch_name="feature/graph-contract",
        )
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    SimpleNamespace(scalar_one_or_none=lambda: analysis),
                    SimpleNamespace(scalar_one_or_none=lambda: pull_request),
                ]
            )
        )
        user = SimpleNamespace(user_id="user-1", username="tester", role="admin")

        async def override_db():
            return db

        async def override_current_user():
            return user

        self._override_dependency(
            app,
            "/architecture/architecture/{analysis_id}",
            "current_user",
            override_current_user,
        )
        self._override_dependency(
            app,
            "/architecture/architecture/{analysis_id}",
            "db",
            override_db,
        )

        with patch.object(
            architecture_endpoint,
            "_get_analysis_violations",
            AsyncMock(return_value=[]),
        ):
            with TestClient(app) as client:
                response = client.get(f"/architecture/architecture/{analysis_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": str(analysis_id),
                "project_id": project_id,
                "branch_id": "feature/graph-contract",
                "status": "completed",
                "nodes": [
                    {
                        "id": "component-1",
                        "label": "Worker",
                        "type": "job",
                        "health": "critical",
                        "complexity": 9,
                        "position": {"x": 10, "y": 20},
                        "properties": {"owner": "platform"},
                        "metrics": {"fanin": 3.0},
                    }
                ],
                "edges": [
                    {
                        "id": "edge-1",
                        "source": "component-1",
                        "target": "component-2",
                        "type": "async",
                        "is_circular": False,
                        "properties": {"weight": 2},
                    }
                ],
                "metrics": {
                    "total_nodes": 1,
                    "total_edges": 1,
                    "circular_dependencies": 0,
                    "max_depth": 6,
                    "avg_complexity": 9.0,
                },
                "circular_dependency_chains": [["Worker", "Queue"]],
                "created_at": started_at.isoformat(),
                "updated_at": completed_at.isoformat(),
                "api_version": architecture_endpoint.API_VERSION,
            },
        )


if __name__ == "__main__":
    unittest.main()
