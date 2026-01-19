"""
LLM Fine-Tuning Pipeline for AI Code Review
"""
from typing import List, Dict, Any, Optional, BinaryIO
import asyncio
import json
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import List, Dict, Any, Optional, TypeVar, Callable, Type, cast
from pathlib import Path

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState,
)
from pydantic import BaseModel

from app.core.config import settings
from app.models.pull_request import PullRequest
from app.models.review_result import ReviewResult
from app.schemas.training import TrainingExample, TrainingExampleCreate

logger = logging.getLogger(__name__)

# Type variables for generic typing
T = TypeVar('T')
P = TypeVar('P', bound=BaseModel)

class TrainingConfig(BaseModel):
    """Configuration for training data collection."""
    min_confidence: float = Field(0.8, ge=0.0, le=1.0, description="Minimum confidence score for inclusion")
    min_feedback_score: float = Field(4.0, ge=0.0, le=5.0, description="Minimum human feedback score")
    batch_size: int = Field(100, gt=0, description="Number of examples to process in a batch")
    max_examples: int = Field(10000, gt=0, description="Maximum number of examples to collect")
    include_metadata: bool = Field(True, description="Whether to include metadata in the output")


def async_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator for retrying async functions with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    wait_time = min(min_wait * (2 ** attempt), max_wait)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
            logger.error(f"All {max_attempts} attempts failed")
            raise last_exception if last_exception else Exception("Unknown error occurred")
        return wrapper
    return decorator

class FineTuningDataset:
    """Service for collecting and processing training data for LLM fine-tuning."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config = TrainingConfig()

    @async_retry(max_attempts=3, min_wait=1.0)
    async def _get_pr_diff(self, pr_id: str) -> str:
        """Get PR diff from database with retry logic."""
        try:
            result = await self.db.execute(
                select(PullRequest.diff)
                .where(PullRequest.id == pr_id)
            )
            pr = result.scalar_one_or_none()
            if not pr or not hasattr(pr, 'diff'):
                logger.warning(f"No diff found for PR {pr_id}")
                return ""
            return pr.diff
        except Exception as e:
            logger.error(f"Error fetching PR {pr_id} diff: {str(e)}", exc_info=True)
            raise

    @async_retry(max_attempts=3, min_wait=1.0)
    async def collect_training_data(
        self,
        config: Optional[TrainingConfig] = None
    ) -> List[TrainingExample]:
        """
        Collect high-quality training examples from the database.
        
        Args:
            config: Configuration for data collection. If None, uses default config.
            
        Returns:
            List of training examples ready for fine-tuning.
                    ReviewComment.severity.in_(["high", "critical"])
                )
            )
            .order_by(PullRequest.updated_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        examples = []
        processed_prs = set()
        
        # Group comments by PR and review
        pr_reviews = {}
        for pr, review, comment in result.all():
            if pr.id not in pr_reviews:
                pr_reviews[pr.id] = {
                    "pr": pr,
                    "reviews": {}
                }
            
            if review.id not in pr_reviews[pr.id]["reviews"]:
                pr_reviews[pr.id]["reviews"][review.id] = {
                    "review": review,
                    "comments": []
                }
            
            pr_reviews[pr.id]["reviews"][review.id]["comments"].append(comment)
        
        # Process each PR and its reviews
        for pr_id, pr_data in pr_reviews.items():
            pr = pr_data["pr"]
            
            try:
                # Get PR diff
                diff = await self._get_pr_diff(pr.id)
                if not diff:
                    continue
                
                # Process each review for this PR
                for review_id, review_data in pr_data["reviews"].items():
                    review = review_data["review"]
                    comments = review_data["comments"]
                    
                    # Format comments as markdown
                    formatted_comments = []
                    for comment in sorted(comments, key=lambda c: (c.file_path or "", c.line_number or 0)):
                        comment_text = f"**{comment.severity.upper()}**"
                        if comment.file_path:
                            comment_text += f" in `{comment.file_path}`"
                            if comment.line_number:
                                comment_text += f" at line {comment.line_number}"
                        comment_text += f": {comment.message}"
                        
                        if comment.suggested_fix:
                            comment_text += f"\n\`\`\`suggestion\n{comment.suggested_fix}\n\`\`\`"
                        
                        formatted_comments.append(comment_text)
                    
                    if not formatted_comments:
                        continue
                        
                    # Create training example
                    example = {
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are an expert code reviewer. Analyze the following code changes "
                                    "and provide a detailed review focusing on code quality, security, "
                                    "performance, and maintainability. Be specific and provide actionable "
                                    "suggestions when possible."
                                )
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Review the following code changes for PR #{pr.github_pr_number}: {pr.title}\n\n"
                                    f"```diff\n{diff}\n```"
                                )
                            },
                            {
                                "role": "assistant",
                                "content": "\n\n".join(formatted_comments)
                            }
                        ]
                    }
                    
                    examples.append(example)
                    
            except Exception as e:
                # Log error but continue with other PRs
                print(f"Error processing PR {pr.id}: {str(e)}")
                continue
            
            if len(examples) >= limit:
                break
        
        return examples
    
    def _format_review_prompt(self, pr, diff: str) -> str:
        """Format PR data as review prompt"""
        return f"""
Analyze this pull request:

Title: {pr.title}
Description: {pr.description}
Files Changed: {pr.files_changed}
Language: {pr.language}

Diff:
```
{diff}
```

Provide a comprehensive code review with security, logic, architecture, performance, and quality issues.
"""
    
    async def _get_pr_diff(self, pr_id: str) -> str:
        """Get PR diff from database"""
        # Would fetch from database
        return "diff content"
    
    async def export_jsonl(self, examples: List[Dict[str, Any]], output_file: str):
        """Export to JSONL format for OpenAI fine-tuning"""
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            for example in examples:
                await f.write(json.dumps(example) + '\n')


class LLMFineTuner:
    """Fine-tune LLM models for code review"""
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        
        if provider == "openai":
            self.client = openai.OpenAI()
        elif provider == "anthropic":
            self.client = Anthropic()
    
    async def create_fine_tuning_job(
        self,
        training_file: str,
        validation_file: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        suffix: str = "code-review",
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create fine-tuning job
        
        Args:
            training_file: Path to training JSONL
            validation_file: Path to validation JSONL
            model: Base model to fine-tune
            suffix: Model name suffix
            hyperparameters: Training hyperparameters
            
        Returns:
            Fine-tuning job ID
        """
        async def _upload_file(self, file_path: str) -> str:
            """Upload a file for fine-tuning"""
            async with aiofiles.open(file_path, 'rb') as f:
                file = await self.client.files.create(
                    file=await f.read(),
                    purpose='fine-tune'
                )
            return file.id
        
        # Upload training file
        train_file_id = await _upload_file(training_file)
        
        # Upload validation file if provided
        val_file_id = None
        if validation_file:
            val_file_id = await _upload_file(validation_file)
        
        # Create fine-tuning job
        job = await self.client.fine_tuning.jobs.create(
            training_file=train_file_id,
            validation_file=val_file_id,
            model=model,
            suffix=suffix,
            hyperparameters=hyperparameters or {
                "n_epochs": 3,
                "batch_size": 4,
                "learning_rate_multiplier": 0.1
            }
        )
        
        return job.id
    
    async def monitor_job(self, job_id: str):
        """
        Monitor fine-tuning job status
        
        Args:
            job_id: Fine-tuning job ID
            
        Returns:
            Job status and metrics
        """
        if self.provider == "openai":
            job = await self.client.fine_tuning.jobs.retrieve(job_id)
            
            return {
                "status": job.status,
                "model": job.fine_tuned_model,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "metrics": job.metrics
            }
    
    async def evaluate_model(
        self,
        model_id: str,
        test_set: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate fine-tuned model
        
        Args:
            model_id: Fine-tuned model ID
            test_set: Test examples
            
        Returns:
            Evaluation metrics
        """
        correct = 0
        total = len(test_set)
        confidence_scores = []
        
        for example in test_set:
            # Get model prediction
            response = await self._get_prediction(model_id, example["messages"][:-1])
            
            # Parse response
            try:
                predicted = json.loads(response)
                actual = json.loads(example["messages"][-1]["content"])
                
                # Simple accuracy check
                if predicted.get("risk_score") == actual.get("risk_score"):
                    correct += 1
                
                # Track confidence
                if "confidence" in predicted:
                    confidence_scores.append(predicted["confidence"])
                    
            except:
                continue
        
        return {
            "accuracy": correct / total if total > 0 else 0,
            "total_examples": total,
            "correct_predictions": correct,
            "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
        }
    
    async def _get_prediction(self, model_id: str, messages: List[Dict]):
        """Get model prediction"""
        try:
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    temperature=0.2
                )
                return response.choices[0].message.content
            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=1000
                )
                return response.content[0].text
        except:
            return ""


class RLHFTrainer:
    """Reinforcement Learning from Human Feedback"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def collect_feedback(
        self,
        pr_id: str,
        review_id: str,
        feedback_type: str,
        rating: float,
        comments: str
    ):
        """
        Collect human feedback on AI review
        
        Args:
            pr_id: Pull request ID
            review_id: Review result ID
            feedback_type: Type of feedback (helpful, accurate, etc.)
            rating: Rating score (1-5)
            comments: Feedback comments
        """
        # Store feedback in database
        feedback = {
            "pr_id": pr_id,
            "review_id": review_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "comments": comments,
            "timestamp": datetime.now()
        }
        
        # Would insert into feedback table
        return feedback
    
    def create_preference_dataset(self) -> List[Dict[str, Any]]:
        """
        Create preference dataset from human feedback
        
        Format for RLHF:
        - Chosen response (high rating)
        - Rejected response (low rating)
        """
        # Query feedback data
        # Compare similar PRs with different ratings
        # Create preference pairs
        
        preference_pairs = []
        
        # Example format:
        preference_pairs.append({
            "prompt": "Review this PR...",
            "chosen": "High-quality review with rating 5",
            "rejected": "Low-quality review with rating 2"
        })
        
        return preference_pairs
    
    def train_reward_model(
        self,
        preference_data: List[Dict[str, Any]]
    ) -> str:
        """
        Train reward model from human preferences
        
        Args:
            preference_data: Preference pairs
            
        Returns:
            Reward model ID
        """
        # Would implement reward model training
        # Using frameworks like TRL (Transformer Reinforcement Learning)
        pass
    
    def run_ppo_training(
        self,
        base_model: str,
        reward_model: str,
        num_steps: int = 10000
    ) -> str:
        """
        Run PPO (Proximal Policy Optimization) training
        
        Args:
            base_model: Base language model
            reward_model: Trained reward model
            num_steps: Training steps
            
        Returns:
            Fine-tuned model ID
        """
        # Would implement PPO training
        # Using libraries like trl, peft
        pass


class FineTuningPipeline:
    """Complete fine-tuning pipeline orchestration"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.dataset = FineTuningDataset(db_session)
        self.tuner = LLMFineTuner()
        self.rlhf = RLHFTrainer(db_session)
    
    def run_full_pipeline(
        self,
        domain: str = "general",
        use_rlhf: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete fine-tuning pipeline
        
        Args:
            domain: Domain-specific dataset (finance, healthcare, etc.)
            use_rlhf: Whether to use RLHF
            
        Returns:
            Pipeline results with model IDs
        """
        results = {}
        
        # Step 1: Collect training data
        print("Collecting training data...")
        examples = self.dataset.collect_training_data(
            limit=10000
        )
        
        # Filter by domain if specified
        if domain != "general":
            examples = [e for e in examples if domain in e.get("metadata", {}).get("tags", [])]
        
        # Split into train/validation
        split_idx = int(len(examples) * 0.9)
        train_data = examples[:split_idx]
        val_data = examples[split_idx:]
        
        # Step 2: Export to JSONL
        print(f"Exporting {len(train_data)} training examples...")
        self.dataset.export_jsonl(train_data, f"train_{domain}.jsonl")
        self.dataset.export_jsonl(val_data, f"val_{domain}.jsonl")
        
        results["training_examples"] = len(train_data)
        results["validation_examples"] = len(val_data)
        
        # Step 3: Create fine-tuning job
        print("Starting fine-tuning job...")
        job_id = self.tuner.create_fine_tuning_job(
            training_file=f"train_{domain}.jsonl",
            validation_file=f"val_{domain}.jsonl",
            suffix=f"{domain}-review"
        )
        
        results["job_id"] = job_id
        
        # Step 4: Monitor until completion
        print(f"Monitoring job {job_id}...")
        # Would poll job status
        
        # Step 5: Evaluate model
        # Would run evaluation
        
        # Step 6: RLHF (optional)
        if use_rlhf:
            print("Running RLHF training...")
            preference_data = self.rlhf.create_preference_dataset()
            # Would run RLHF
        
        return results
