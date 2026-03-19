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
