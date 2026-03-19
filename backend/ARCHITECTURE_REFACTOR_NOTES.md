# Architecture Refactor Notes

## Scope (2026-03-19)

This refactor establishes a cleaner boundary for library-management workflows without breaking API behavior.

## What Changed

1. `LibraryManager` was reorganized into small workflow-focused methods:
- context resolution (`_resolve_validation_context`)
- installation persistence (`_persist_installation`)
- public operations remain unchanged (`validate_library`, `install_library`, `search_libraries`, `get_installed_libraries`)

2. Introduced a repository contract:
- `app/domain/repositories/library_repository.py`
- `ILibraryRepository` protocol enables dependency inversion and makes the application workflow independent of specific DB implementations.

3. Removed naming ambiguity in search errors:
- service-level search exception is imported as `SearchServiceError`
- manager-level `SearchError` remains the public API error for callers.

## Architectural Impact

- Higher cohesion: each private method now handles one responsibility.
- Lower coupling: manager logic targets a repository protocol, not a concrete class.
- Better testability: workflow methods can be unit-tested with mocked protocol implementations.
- Better evolvability: storage implementation can be swapped with minimal changes.

## Additional API Decoupling (Round 2)

1. Unified security service dependency providers in `app/api/dependencies.py`:
- `get_security_audit_service()`
- `get_security_compliance_service()`

2. Reduced endpoint-level infrastructure coupling:
- `security_audit.py` now uses DI-provided services instead of directly constructing service objects per endpoint.
- Reused a shared Neo4j query helper (`_execute_neo4j_query`) to avoid duplicated connection/session boilerplate.

3. Fixed invalid dependency imports:
- Replaced `app.core.dependencies` imports with `app.api.dependencies` in security endpoints.

## Additional Service-Centric Refactor (Round 3)

1. Moved query-heavy endpoint logic into service use-cases:
- Added `get_recent_scan_summary()` to `SecurityAuditService`.
- Added `get_used_scan_tools()` to `SecurityAuditService`.

2. Endpoint simplification:
- `security_audit.py` now delegates scan-summary and tools retrieval to service methods.
- API layer now focuses on request/response orchestration only.

3. Reduced duplication:
- Added shared internal Neo4j execution helper in `SecurityAuditService` for read-query data access.

## Additional Endpoint Consolidation (Round 4)

1. Refactored `github.py` endpoint internals:
- Added shared helpers for project lookup, PR lookup, access enforcement, and analysis queueing.
- Replaced repeated endpoint code with helper calls.

2. Fixed maintainability bug in `sync_project`:
- Corrected control flow so GitHub `repo_info` is always initialized before use.

3. Reduced boilerplate and drift risk:
- Centralized PR analysis enqueue payload creation.

## Additional Analytics Refactor (Round 5)

1. Refactored shared endpoint logic in `project_analytics.py`:
- Added `_default_project_analytics()` fallback builder.
- Added `_get_project_prs()` reusable PR retrieval helper.
- Added `_parse_time_range()` centralized time-range parsing/validation helper.
- Added `_utcnow_iso()` helper for consistent timestamps.

2. Reduced duplicated query and validation code:
- `issues`, `architecture`, `metrics`, and `architecture-analysis` endpoints now reuse helper functions.

3. Improved safety in architecture-analysis query flow:
- Replaced generator-based `IN` filter input with explicit PR id list handling and empty-list guard.

## Additional Auth Refactor (Round 6)

1. Consolidated auth endpoint workflow helpers in `auth.py`:
- `_get_user_by_email()`
- `_get_user_by_id()`
- `_log_auth_failure()`
- `_store_refresh_metadata()`

2. Reduced endpoint coupling and duplication:
- Reused one cache instance in login flow instead of repeated service retrieval.
- Unified audit failure logging call structure.
- Centralized refresh token metadata persistence logic.

3. Improved resilience:
- Login now consistently uses safe client IP extraction helper (`get_client_ip`).

## Additional Code Review Endpoint Refactor (Round 7)

1. Consolidated repeated endpoint logic in `code_review.py`:
- Added `_parse_uuid_or_422()` for centralized UUID parsing/validation.
- Added `_to_comment_model()` for unified comment response mapping.

2. Reduced local import and drift issues:
- Moved repeated function-local imports to module scope.
- Removed duplicate logger definition at file end.

3. Maintained API behavior while reducing complexity:
- Trigger/status/detail/comments endpoints now share validation and serialization helpers.

## Additional Pull Request Endpoint Refactor (Round 8)

1. Added endpoint-level reusable helpers in `pull_request.py`:
- `_get_project_pr_or_404()`
- `_build_task_status_response()`

2. Reduced duplicate query and response mapping logic:
- Reused shared PR lookup in both analyze/reanalyze paths.
- Centralized Celery task status response shaping.

## RBAC Simplification and Compatibility Hardening (Round 9-11)

1. Unified effective RBAC model to `ADMIN/USER`:
- Updated role defaults and endpoint policy checks to align with two effective roles.
- Replaced scattered role assumptions in API dependencies with explicit `require_admin` and `require_user`.

2. Preserved backward compatibility for historical role data:
- Retained legacy role values in shared enums (`PROGRAMMER`, `VISITOR`, `REVIEWER`, etc.).
- Added normalization utilities:
  - Python: `Role.effective()` and `RBACService.normalize_role()`
  - TypeScript: `toEffectiveRole(...)`
- This avoids runtime breaks when old JWT payloads or persisted DB rows still use legacy role strings.

3. Reduced RBAC endpoint duplication and drift:
- Refactored `rbac_projects.py` and `rbac_users.py` to reuse helper functions for:
  - client IP extraction
  - response model mapping
  - project lookup
- Updated RBAC docs/OpenAPI descriptions to consistently describe `ADMIN/USER` behavior.

4. Test and script alignment:
- Replaced legacy enum references in tests/scripts (`UserRole.user`, `Role.DEVELOPER`) with effective roles.
- Verified modified modules with `py_compile` to ensure syntax-level stability after refactor.
