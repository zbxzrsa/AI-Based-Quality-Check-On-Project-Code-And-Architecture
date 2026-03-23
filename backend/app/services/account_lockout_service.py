"""
Account lockout service for security
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class AccountLockoutService:
    """
    Service to manage account lockout after failed login attempts
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.max_attempts = 5
        self.lockout_duration_minutes = 30
        self.attempt_window_minutes = 15
    
    def get_lockout_key(self, user_id: int) -> str:
        """Get Redis key for account lockout"""
        return f"account_lockout:{user_id}"
    
    def get_attempts_key(self, user_id: int) -> str:
        """Get Redis key for login attempts"""
        return f"login_attempts:{user_id}"
    
    async def is_account_locked(self, user_id: int) -> tuple[bool, Optional[datetime]]:
        """
        Check if account is currently locked
        
        Returns:
            (is_locked, unlock_time): Tuple indicating lock status and unlock time
        """
        lockout_key = self.get_lockout_key(user_id)
        lockout_data = await self.redis.get(lockout_key)
        
        if lockout_data:
            unlock_time = datetime.fromisoformat(lockout_data.decode())
            if datetime.now(timezone.utc) < unlock_time:
                logger.warning(f"Account {user_id} is locked until {unlock_time}")
                return True, unlock_time
            else:
                # Lockout expired, remove it
                await self.redis.delete(lockout_key)
        
        return False, None
    
    async def record_failed_attempt(self, user_id: int) -> tuple[bool, Optional[datetime]]:
        """
        Record a failed login attempt and lock account if necessary
        
        Returns:
            (should_lock, lockout_end_time): Tuple indicating if account should be locked and until when
        """
        attempts_key = self.get_attempts_key(user_id)
        
        # Get current attempt count
        current_attempts = await self.redis.get(attempts_key)
        attempt_count = int(current_attempts) if current_attempts else 0
        
        # Increment attempts
        attempt_count += 1
        await self.redis.setex(
            attempts_key,
            timedelta(minutes=self.attempt_window_minutes),
            attempt_count
        )
        
        logger.warning(f"Failed login attempt {attempt_count}/{self.max_attempts} for user {user_id}")
        
        # Check if account should be locked
        if attempt_count >= self.max_attempts:
            lockout_time = datetime.now(timezone.utc) + timedelta(minutes=self.lockout_duration_minutes)
            lockout_key = self.get_lockout_key(user_id)
            await self.redis.setex(
                lockout_key,
                timedelta(minutes=self.lockout_duration_minutes),
                lockout_time.isoformat()
            )
            
            # Clear attempts counter after lockout
            await self.redis.delete(attempts_key)
            
            logger.error(f"Account {user_id} locked due to too many failed attempts")
            return True, lockout_time
        
        return False, None
    
    async def reset_attempts(self, user_id: int):
        """Reset failed login attempts after successful login"""
        attempts_key = self.get_attempts_key(user_id)
        await self.redis.delete(attempts_key)
        logger.info(f"Reset login attempts for user {user_id}")
    
    async def unlock_account(self, user_id: int):
        """Manually unlock an account (admin function)"""
        lockout_key = self.get_lockout_key(user_id)
        attempts_key = self.get_attempts_key(user_id)
        
        await self.redis.delete(lockout_key)
        await self.redis.delete(attempts_key)
        
        logger.info(f"Account {user_id} manually unlocked")
    
    async def get_remaining_attempts(self, user_id: int) -> int:
        """Get remaining attempts before lockout"""
        attempts_key = self.get_attempts_key(user_id)
        current_attempts = await self.redis.get(attempts_key)
        attempt_count = int(current_attempts) if current_attempts else 0
        
        return max(0, self.max_attempts - attempt_count)
