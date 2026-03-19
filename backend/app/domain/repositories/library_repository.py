"""Library repository domain contract.

Application services depend on this protocol instead of concrete persistence
implementations to keep business workflows decoupled from storage details.
"""

from typing import Protocol

from app.models.library import ProjectContext
from app.schemas.library import InstalledLibrary


class ILibraryRepository(Protocol):
    async def save_library(self, library: InstalledLibrary) -> int: ...

    async def save_dependencies(self, library_id: int, dependencies: list) -> None: ...

    async def get_libraries_by_project(self, project_id: str, context: ProjectContext | None = None) -> list[InstalledLibrary]: ...

    async def get_library_by_name(
        self,
        project_id: str,
        name: str,
        context: ProjectContext,
    ) -> InstalledLibrary | None: ...

    async def update_library_version(self, library_id: int, new_version: str) -> None: ...
