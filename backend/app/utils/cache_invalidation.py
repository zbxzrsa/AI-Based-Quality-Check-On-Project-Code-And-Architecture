"""
Cache invalidation strategies
"""
from typing import List
from app.services.redis_cache_service import RedisCacheService


class CacheInvalidation:
    """
    Cache invalidation logic for different scenarios
    """
    
    def __init__(self, cache_service: RedisCacheService):
        self.cache = cache_service
    
    async def on_pull_request_update(self, pr_id: str):
        """
        Invalidate caches when PR is updated
        """
        # Invalidate analysis results
        await self.cache.invalidate_analysis(pr_id)
    
    async def on_project_update(self, project_id: str):
        """
        Invalidate caches when project structure changes
        """
        # Invalidate all graph query caches for this project
        await self.cache.invalidate_project_cache(project_id)
    
    async def on_baseline_update(self, project_id: str):
        """
        Invalidate caches when architectural baseline is updated
        """
        # Invalidate project graph caches
        await self.cache.invalidate_project_cache(project_id)
    
    async def on_user_logout(self, user_id: str):
        """
        Clear user session on logout
        """
        await self.cache.delete_session(user_id)
    
    async def bulk_invalidate_analyses(self, pr_ids: List[str]):
        """
        Invalidate multiple analysis results at once
        """
        for pr_id in pr_ids:
            await self.cache.invalidate_analysis(pr_id)
