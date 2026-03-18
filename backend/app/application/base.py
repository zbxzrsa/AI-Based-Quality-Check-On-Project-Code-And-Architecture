"""
Application Layer - Use Case Base Classes

Base classes for application use cases following Clean Architecture.
"""

from abc import ABC
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class UseCaseResult:
    """Result of a use case execution"""

    success: bool
    data: Any | None = None
    error: str | None = None

    @staticmethod
    def ok(data: Any = None) -> "UseCaseResult":
        return UseCaseResult(success=True, data=data)

    @staticmethod
    def err(message: str) -> "UseCaseResult":
        return UseCaseResult(success=False, error=message)


class UseCase(ABC):
    """
    Base class for all use cases.

    Use cases orchestrate the flow of data and direct the execution
    of business logic through domain services and repositories.
    """

    async def execute(self, *args, **kwargs) -> UseCaseResult:
        """
        Execute the use case.

        Override this method in subclasses to implement specific logic.
        """
        raise NotImplementedError("Subclasses must implement execute()")

    async def _safe_execute(self, *args, **kwargs) -> UseCaseResult:
        """Execute with error handling"""
        try:
            return await self.execute(*args, **kwargs)
        except Exception as e:
            logger.error(f"Use case error: {e}", exc_info=True)
            return UseCaseResult.err(str(e))


class Command(UseCase):
    """
    Base class for write operations (Commands).

    Commands represent actions that modify state.
    """

    pass


class Query(UseCase):
    """
    Base class for read operations (Queries).

    Queries represent operations that retrieve data without modifying state.
    """

    pass
