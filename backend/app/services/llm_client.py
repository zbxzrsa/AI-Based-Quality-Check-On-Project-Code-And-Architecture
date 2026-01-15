"""
LLM client service for AI code review
Supports OpenAI GPT-4 and Anthropic Claude
"""
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import openai
import anthropic
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import settings


class LLMProvider(str, Enum):
    """LLM provider enum"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient:
    """
    Universal LLM client supporting multiple providers
    """
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENAI,
        model: Optional[str] = None
    ):
        self.provider = provider
        
        if provider == LLMProvider.OPENAI:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = model or "gpt-4-turbo-preview"
        elif provider == LLMProvider.ANTHROPIC:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = model or "claude-3-opus-20240229"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        self.total_tokens = 0
        self.total_cost = 0.0
    
    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        json_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Generate completion from LLM
        
        Args:
            system_prompt: System instruction
            user_prompt: User message
            temperature: Randomness (0-1)
            max_tokens: Maximum response tokens
            json_mode: Force JSON output
            
        Returns:
            Response with content and metadata
        """
        if self.provider == LLMProvider.OPENAI:
            return await self._openai_completion(
                system_prompt,
                user_prompt,
                temperature,
                max_tokens,
                json_mode
            )
        else:
            return await self._anthropic_completion(
                system_prompt,
                user_prompt,
                temperature,
                max_tokens,
                json_mode
            )
    
    async def _openai_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> Dict[str, Any]:
        """OpenAI completion"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if json_mode and "gpt-4" in self.model:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            
            # Track usage
            usage = response.usage
            self.total_tokens += usage.total_tokens
            self.total_cost += self._calculate_openai_cost(
                usage.prompt_tokens,
                usage.completion_tokens
            )
            
            return {
                "content": content,
                "provider": "openai",
                "model": self.model,
                "tokens": {
                    "prompt": usage.prompt_tokens,
                    "completion": usage.completion_tokens,
                    "total": usage.total_tokens
                },
                "cost": self._calculate_openai_cost(
                    usage.prompt_tokens,
                    usage.completion_tokens
                )
            }
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def _anthropic_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> Dict[str, Any]:
        """Anthropic completion"""
        try:
            if json_mode:
                user_prompt += "\n\nPlease respond with valid JSON only."
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.content[0].text
            
            # Track usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            self.total_tokens += total_tokens
            self.total_cost += self._calculate_anthropic_cost(
                input_tokens,
                output_tokens
            )
            
            return {
                "content": content,
                "provider": "anthropic",
                "model": self.model,
                "tokens": {
                    "prompt": input_tokens,
                    "completion": output_tokens,
                    "total": total_tokens
                },
                "cost": self._calculate_anthropic_cost(
                    input_tokens,
                    output_tokens
                )
            }
            
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    def _calculate_openai_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate OpenAI API cost"""
        # GPT-4 Turbo pricing (as of 2024)
        prompt_cost_per_1k = 0.01  # $0.01 per 1K tokens
        completion_cost_per_1k = 0.03  # $0.03 per 1K tokens
        
        prompt_cost = (prompt_tokens / 1000) * prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000) * completion_cost_per_1k
        
        return prompt_cost + completion_cost
    
    def _calculate_anthropic_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate Anthropic API cost"""
        # Claude 3 Opus pricing (as of 2024)
        input_cost_per_1k = 0.015  # $0.015 per 1K tokens
        output_cost_per_1k = 0.075  # $0.075 per 1K tokens
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        
        return input_cost + output_cost
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "provider": self.provider.value,
            "model": self.model
        }
    
    def reset_usage(self):
        """Reset usage tracking"""
        self.total_tokens = 0
        self.total_cost = 0.0


# Singleton instances
_openai_client: Optional[LLMClient] = None
_anthropic_client: Optional[LLMClient] = None


def get_llm_client(provider: LLMProvider = LLMProvider.OPENAI) -> LLMClient:
    """Get LLM client instance"""
    global _openai_client, _anthropic_client
    
    if provider == LLMProvider.OPENAI:
        if _openai_client is None:
            _openai_client = LLMClient(LLMProvider.OPENAI)
        return _openai_client
    else:
        if _anthropic_client is None:
            _anthropic_client = LLMClient(LLMProvider.ANTHROPIC)
        return _anthropic_client
