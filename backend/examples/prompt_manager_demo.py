"""
Prompt Manager Demo

Demonstrates how to use the prompt manager for code analysis.

This example shows:
1. Generating code quality review prompts
2. Generating architectural analysis prompts
3. Generating security vulnerability detection prompts
4. Using prompts with the LLM orchestrator

Validates Requirements: 1.4
"""
import logging
logger = logging.getLogger(__name__)


import asyncio
from app.services.llm import (
    get_prompt_manager,
    AnalysisType,
    create_orchestrator,
    LLMProviderType,
    LLMRequest
)


# Sample code for analysis
SAMPLE_CODE_QUALITY = """
def authenticate_user(username, password):
    # NOTE: This is intentionally vulnerable code for demonstration purposes
    # In production, use parameterized queries and input validation
    user = db.query("SELECT * FROM users WHERE username='" + username + "'")
    if user and user.password == password:
        return user
    return None
"""

SAMPLE_CODE_ARCHITECTURE = """
class UserService:
    def __init__(self):
        self.db = Database()
        self.cache = Cache()
        self.email = EmailService()
        self.sms = SMSService()
        self.payment = PaymentService()
    
    def create_user(self, data):
        user = self.db.create_user(data)
        self.cache.set(user.id, user)
        self.email.send_welcome(user)
        self.sms.send_verification(user)
        self.payment.create_account(user)
        return user
"""

SAMPLE_CODE_SECURITY = """
@app.route('/api/user/<user_id>')
def get_user(user_id):
    # SECURE: Use parameterized query to prevent SQL injection
    query = "SELECT * FROM users WHERE id = ?"
    result = db.execute(query, (user_id,))
    return jsonify(result)
"""


def demo_code_quality_prompt():
    """Demonstrate code quality review prompt generation"""
    logger.info("=" * 80)
    logger.info("CODE QUALITY REVIEW PROMPT")
    logger.info("=" * 80)
    
    manager = get_prompt_manager()
    
    prompt = manager.generate_code_quality_prompt(
        file_path="src/auth.py",
        language="python",
        code_diff=SAMPLE_CODE_QUALITY,
        context="Authentication module review - checking for security issues and code quality"
    )
    
    logger.info("\n--- SYSTEM PROMPT ---")
    logger.info(str(prompt["system_prompt"][:500] + "...\n"))
    
    logger.info("--- USER PROMPT ---")
    logger.info(str(prompt["user_prompt"]))
    logger.info()


def demo_architecture_prompt():
    """Demonstrate architectural analysis prompt generation"""
    logger.info("=" * 80)
    logger.info("ARCHITECTURAL ANALYSIS PROMPT")
    logger.info("=" * 80)
    
    manager = get_prompt_manager()
    
    prompt = manager.generate_architecture_prompt(
        file_path="src/services/user_service.py",
        language="python",
        code_diff=SAMPLE_CODE_ARCHITECTURE,
        dependencies="Database, Cache, EmailService, SMSService, PaymentService",
        context="Service layer review - checking for proper separation of concerns and dependency management"
    )
    
    logger.info("\n--- SYSTEM PROMPT ---")
    logger.info(str(prompt["system_prompt"][:500] + "...\n"))
    
    logger.info("--- USER PROMPT ---")
    logger.info(str(prompt["user_prompt"]))
    logger.info()


def demo_security_prompt():
    """Demonstrate security vulnerability detection prompt generation"""
    logger.info("=" * 80)
    logger.info("SECURITY VULNERABILITY DETECTION PROMPT")
    logger.info("=" * 80)
    
    manager = get_prompt_manager()
    
    prompt = manager.generate_security_prompt(
        file_path="src/api/user_api.py",
        language="python",
        code_diff=SAMPLE_CODE_SECURITY,
        context="API endpoint security review - checking for OWASP Top 10 vulnerabilities",
        exposure_level="public-facing"
    )
    
    logger.info("\n--- SYSTEM PROMPT ---")
    logger.info(str(prompt["system_prompt"][:500] + "...\n"))
    
    logger.info("--- USER PROMPT ---")
    logger.info(str(prompt["user_prompt"]))
    logger.info()


def demo_prompt_by_type():
    """Demonstrate generating prompts by analysis type"""
    logger.info("=" * 80)
    logger.info("GENERATING PROMPTS BY TYPE")
    logger.info("=" * 80)
    
    manager = get_prompt_manager()
    
    # Get available analysis types
    types = manager.get_available_analysis_types()
    logger.info("\nAvailable analysis types: {types}\n")
    
    # Generate prompt for each type
    for analysis_type in [AnalysisType.CODE_QUALITY, AnalysisType.ARCHITECTURE, AnalysisType.SECURITY]:
        prompt = manager.generate_prompt(
            analysis_type=analysis_type,
            file_path="src/example.py",
            language="python",
            code_diff="def example(): pass",
            context=f"{analysis_type.value} analysis"
        )
        
        logger.info("--- {analysis_type.value.upper()} ---")
        logger.info("System prompt length: {len(prompt['system_prompt'])} chars")
        logger.info("User prompt length: {len(prompt['user_prompt'])} chars")
        logger.info()


async def demo_with_llm_orchestrator():
    """Demonstrate using prompts with LLM orchestrator"""
    logger.info("=" * 80)
    logger.info("USING PROMPTS WITH LLM ORCHESTRATOR")
    logger.info("=" * 80)
    logger.info("\nNOTE: This demo requires valid API keys to run.\n")
    
    try:
        # Create prompt manager and orchestrator
        manager = get_prompt_manager()
        orchestrator = create_orchestrator(
            primary_provider=LLMProviderType.OPENAI,
            fallback_provider=LLMProviderType.ANTHROPIC,
            timeout=30
        )
        
        # Generate security analysis prompt
        prompt = manager.generate_security_prompt(
            file_path="src/api.py",
            language="python",
            code_diff=SAMPLE_CODE_SECURITY,
            context="Security review of API endpoint",
            exposure_level="public-facing"
        )
        
        logger.info("Generated security analysis prompt")
        logger.info("System prompt: {len(prompt['system_prompt'])} chars")
        logger.info("User prompt: {len(prompt['user_prompt'])} chars")
        
        # Create LLM request
        request = LLMRequest(
            prompt=prompt["user_prompt"],
            system_prompt=prompt["system_prompt"],
            temperature=0.3,
            max_tokens=2000
        )
        
        logger.info("\nSending request to LLM orchestrator...")
        
        # Generate analysis (this will fail without valid API keys)
        response = await orchestrator.generate(request)
        
        logger.info("\n--- LLM ANALYSIS RESPONSE ---")
        logger.info(str(response.content))
        logger.info("\nTokens used: {response.tokens['total']}")
        logger.info("Cost: ${response.cost:.4f}")
        logger.info("Provider: {response.provider}")
        
    except Exception as e:
        logger.info("Error: {e}")
        logger.info("\nThis is expected if API keys are not configured.")
        logger.info("To run this demo with actual LLM calls:")
        logger.info("1. Set OPENAI_API_KEY environment variable")
        logger.info("2. Set ANTHROPIC_API_KEY environment variable")
        logger.info("3. Run this script again")


def demo_custom_prompt_template():
    """Demonstrate creating custom prompt templates"""
    logger.info("=" * 80)
    logger.info("CUSTOM PROMPT TEMPLATE")
    logger.info("=" * 80)
    
    from app.services.llm.prompts import PromptTemplate
    
    # Create a custom template
    template = PromptTemplate(
        system_prompt="You are a performance optimization expert.",
        user_prompt_template="""Analyze the following code for performance issues:

File: {file_path}
Language: {language}

Code:
```{language}
{code}
```

Focus on:
- Time complexity
- Space complexity
- Database query optimization
- Caching opportunities

Provide specific optimization recommendations.""",
        analysis_type=AnalysisType.CODE_QUALITY
    )
    
    # Format the template
    prompt = template.format(
        file_path="src/data_processor.py",
        language="python",
        code="""
def process_data(items):
    results = []
    for item in items:
        if item.is_valid():
            processed = expensive_operation(item)
            results.append(processed)
    return results
"""
    )
    
    logger.info("\n--- CUSTOM SYSTEM PROMPT ---")
    logger.info(str(prompt["system_prompt"]))
    
    logger.info("\n--- CUSTOM USER PROMPT ---")
    logger.info(str(prompt["user_prompt"]))
    logger.info()


def main():
    """Run all demos"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "PROMPT MANAGER DEMONSTRATION" + " " * 30 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info()
    
    # Run synchronous demos
    demo_code_quality_prompt()
    demo_architecture_prompt()
    demo_security_prompt()
    demo_prompt_by_type()
    demo_custom_prompt_template()
    
    # Run async demo
    logger.info("\n--- ASYNC DEMO ---")
    asyncio.run(demo_with_llm_orchestrator())
    
    logger.info("\n" + "=" * 80)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 80)
    logger.info("\nKey Takeaways:")
    logger.info("1. Use get_prompt_manager() to get a prompt manager instance")
    logger.info("2. Generate prompts using convenience methods or generate_prompt()")
    logger.info("3. Prompts include both system and user prompts")
    logger.info("4. All prompts support variable substitution")
    logger.info("5. Integrate with LLM orchestrator for actual analysis")
    logger.info()


if __name__ == "__main__":
    main()
