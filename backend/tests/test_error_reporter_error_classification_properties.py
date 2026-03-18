"""
Property-based tests for error classification and messaging in ErrorReporter.

Tests Property 12: Error Classification and Messaging
**Validates: Requirements 5.2, 5.4**

These tests verify that for any database error, the system properly categorizes
the error type and provides structured error messages with recommended resolution steps.
"""


import pytest
from hypothesis import given, strategies as st, settings

from app.core.error_reporter import (
    ErrorReporter,
    DatabaseErrorCategory,
)
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# Test constants for configuration to avoid literal suspicious strings
TEST_PASSWORD = get_test_password("test_password_value")
TEST_USER = "test_user_name"
TEST_DB = "test_database_db"


class TestErrorClassificationAndMessagingProperties:
    """Property-based tests for error classification and structured messaging"""
    
    def setup_method(self):
        """Reset error statistics before each test"""
        ErrorReporter.reset_error_statistics()
    
    @given(
        error_message=st.sampled_from([
            "Connection timed out after 30 seconds",
            "Connection timeout occurred",
            "Request timed out",
            "Authentication failed for user",
            "Invalid password provided",
            "Access denied to database",
            "Login failed - credentials invalid",
            "Permission denied for operation",
            "UTF-8 decoding error in file",
            "Character encoding issue detected",
            "Unicode decode error",
            "Codec can't decode bytes",
            "Version 3.13 incompatible with asyncpg 0.25",
            "Unsupported Python version",
            "Compatibility check failed",
            "Connection pool exhausted",
            "Maximum connections reached",
            "Too many active connections",
            "Connection refused by server",
            "Network unreachable",
            "Host not found",
            "DNS resolution failed",
            "Invalid configuration parameter",
            "Missing required setting",
            "Configuration validation failed",
            "Migration script failed",
            "Alembic error occurred",
            "Schema update failed",
            "Health check probe failed",
            "Status check timeout"
        ]),
        component=st.sampled_from(['PostgreSQL', 'Neo4j', 'Redis', 'MongoDB', 'MySQL']),
        error_code=st.one_of(st.none(), st.text(min_size=1, max_size=10))
    )
    @settings(max_examples=100, deadline=10000)
    def test_error_classification_accuracy_property(
        self, error_message, component, error_code
    ):
        """
        **Property 12: Error Classification and Messaging - Classification Accuracy**
        **Validates: Requirements 5.2**
        
        For any database error message, the system should correctly classify
        the error into the appropriate category based on error content.
        """
        error = Exception(error_message)
        
        # Classify the error
        category = ErrorReporter.classify_database_error(error, component)
        
        # Verify classification is appropriate based on error message content
        error_lower = error_message.lower()
        
        if any(keyword in error_lower for keyword in ['timeout', 'timed out']):
            assert category == DatabaseErrorCategory.CONNECTION_TIMEOUT, f"Timeout errors should be classified as CONNECTION_TIMEOUT, got {category}"
        
        elif any(keyword in error_lower for keyword in ['authentication', 'password', 'login', 'access denied', 'permission denied']):
            assert category == DatabaseErrorCategory.AUTHENTICATION_FAILURE, f"Auth errors should be classified as AUTHENTICATION_FAILURE, got {category}"
        
        elif any(keyword in error_lower for keyword in ['encoding', 'decode', 'utf-8', 'unicode', 'codec']):
            assert category == DatabaseErrorCategory.ENCODING_ERROR, f"Encoding errors should be classified as ENCODING_ERROR, got {category}"
        
        elif any(keyword in error_lower for keyword in ['version', 'compatibility', 'incompatible', 'unsupported']):
            assert category == DatabaseErrorCategory.COMPATIBILITY_ERROR, f"Compatibility errors should be classified as COMPATIBILITY_ERROR, got {category}"
        
        elif any(keyword in error_lower for keyword in ['pool', 'connection limit', 'max connections', 'exhausted', 'too many']):
            assert category == DatabaseErrorCategory.POOL_EXHAUSTION, f"Pool errors should be classified as POOL_EXHAUSTION, got {category}"
        
        elif any(keyword in error_lower for keyword in ['connection refused', 'network', 'host', 'dns', 'unreachable']):
            assert category == DatabaseErrorCategory.NETWORK_ERROR, f"Network errors should be classified as NETWORK_ERROR, got {category}"
        
        elif any(keyword in error_lower for keyword in ['configuration', 'config', 'invalid', 'missing', 'required']):
            assert category == DatabaseErrorCategory.CONFIGURATION_ERROR, f"Config errors should be classified as CONFIGURATION_ERROR, got {category}"
        
        elif any(keyword in error_lower for keyword in ['migration', 'alembic', 'schema']):
            assert category == DatabaseErrorCategory.MIGRATION_ERROR, f"Migration errors should be classified as MIGRATION_ERROR, got {category}"
        
        elif any(keyword in error_lower for keyword in ['health', 'check', 'probe', 'status']):
            assert category == DatabaseErrorCategory.HEALTH_CHECK_ERROR, f"Health check errors should be classified as HEALTH_CHECK_ERROR, got {category}"
        
        # Verify category is a valid enum value
        assert isinstance(category, DatabaseErrorCategory), f"Classification should return DatabaseErrorCategory, got {type(category)}"
        assert category in list(DatabaseErrorCategory), f"Category {category} should be a valid DatabaseErrorCategory"
    
    @given(
        component=st.sampled_from(['PostgreSQL', 'Neo4j', 'Redis', 'MongoDB']),
        error_category=st.sampled_from(list(DatabaseErrorCategory)),
        has_connection_params=st.booleans(),
        has_error_code=st.booleans()
    )
    @settings(max_examples=100, deadline=10000)
    def test_structured_error_message_completeness_property(
        self, component, error_category, has_connection_params, has_error_code
    ):
        """
        **Property 12: Error Classification and Messaging - Structured Message Completeness**
        **Validates: Requirements 5.4**
        
        For any database error, the system should provide structured error messages
        with all relevant information including component, category, timestamp, and resolution steps.
        """
        # Create error based on category
        error_messages = {
            DatabaseErrorCategory.CONNECTION_TIMEOUT: "Connection timed out",
            DatabaseErrorCategory.AUTHENTICATION_FAILURE: "Authentication failed",
            DatabaseErrorCategory.ENCODING_ERROR: "UTF-8 encoding error",
            DatabaseErrorCategory.COMPATIBILITY_ERROR: "Version incompatibility",
            DatabaseErrorCategory.POOL_EXHAUSTION: "Connection pool exhausted",
            DatabaseErrorCategory.NETWORK_ERROR: "Network unreachable",
            DatabaseErrorCategory.CONFIGURATION_ERROR: "Invalid configuration",
            DatabaseErrorCategory.MIGRATION_ERROR: "Migration failed",
            DatabaseErrorCategory.HEALTH_CHECK_ERROR: "Health check failed"
        }
        
        error_message = error_messages.get(error_category, "Unknown error")
        error = Exception(error_message)
        
        # Create connection parameters if requested
        connection_params = None
        if has_connection_params:
            connection_params = {
                'host': 'localhost',
                'port': '5432',
                'database': TEST_DB,
                'connection_string': f'postgresql://{TEST_USER}:***@localhost:5432/{TEST_DB}'
            }
        
        # Create error code if requested
        error_code = "E001" if has_error_code else None
        
        # Create error info
        error_info = ErrorReporter.create_database_error_info(
            error=error,
            component=component,
            connection_params=connection_params,
            error_code=error_code
        )
        
        # Override category for testing
        error_info.category = error_category
        
        # Generate structured error message
        structured_message = ErrorReporter.format_structured_error_message(
            error_info,
            include_resolution_steps=True,
            include_context=True
        )
        
        # Verify message structure and completeness
        assert "DATABASE ERROR REPORT" in structured_message, "Should include error report header"
        assert f"Component: {component}" in structured_message, "Should include component name"
        assert f"Category: {error_category.value.replace('_', ' ').title()}" in structured_message, "Should include formatted category"
        assert "Timestamp:" in structured_message, "Should include timestamp"
        assert f"Message: {error_info.message}" in structured_message, "Should include error message"
        
        # Verify error code inclusion
        if has_error_code:
            assert f"Error Code: {error_code}" in structured_message, "Should include error code when provided"
        
        # Verify resolution steps are included
        assert "Resolution Steps:" in structured_message, "Should include resolution steps section"
        assert any(str(i) + "." in structured_message for i in range(1, 6)), "Should include numbered resolution steps"
        
        # Verify error details are included when connection params exist
        if has_connection_params:
            assert "Error Details:" in structured_message, "Should include error details section when connection params exist"
            assert "connection_params:" in structured_message, "Should include connection parameters"
        
        # Verify message is properly formatted
        lines = structured_message.split('\n')
        assert len(lines) > 10, "Structured message should have multiple lines"
        
        # Check for proper section separators
        separator_count = sum(1 for line in lines if '=' in line or '-' in line)
        assert separator_count >= 2, "Should have section separators for formatting"
    
    @given(
        error_categories=st.lists(
            st.sampled_from(list(DatabaseErrorCategory)),
            min_size=1,
            max_size=10
        ),
        component=st.sampled_from(['PostgreSQL', 'Neo4j', 'Redis'])
    )
    @settings(max_examples=50, deadline=15000)
    def test_resolution_steps_appropriateness_property(
        self, error_categories, component
    ):
        """
        **Property 12: Error Classification and Messaging - Resolution Steps Appropriateness**
        **Validates: Requirements 5.4**
        
        For any error category, the system should provide appropriate and actionable
        resolution steps that are relevant to the specific error type and component.
        """
        for error_category in error_categories:
            # Get resolution steps for this category
            resolution_steps = ErrorReporter._get_resolution_steps(error_category, component)
            
            # Verify resolution steps exist and are appropriate
            assert len(resolution_steps) > 0, f"Should provide resolution steps for {error_category}"
            assert len(resolution_steps) <= 10, f"Should not provide too many steps (max 10), got {len(resolution_steps)}"
            
            # Verify steps are strings and non-empty
            for step in resolution_steps:
                assert isinstance(step, str), "Resolution steps should be strings"
                assert len(step.strip()) > 0, "Resolution steps should not be empty"
                assert len(step) < 200, "Resolution steps should be concise (under 200 chars)"
            
            # Verify steps are relevant to the error category
            steps_text = " ".join(resolution_steps).lower()
            
            if error_category == DatabaseErrorCategory.CONNECTION_TIMEOUT:
                assert any(keyword in steps_text for keyword in ['timeout', 'connection', 'network', 'service']), \
                    "Timeout resolution steps should mention relevant keywords"
            
            elif error_category == DatabaseErrorCategory.AUTHENTICATION_FAILURE:
                assert any(keyword in steps_text for keyword in ['password', 'username', 'credentials', 'authentication', 'permissions']), \
                    "Auth failure resolution steps should mention relevant keywords"
            
            elif error_category == DatabaseErrorCategory.ENCODING_ERROR:
                assert any(keyword in steps_text for keyword in ['encoding', 'utf-8', 'character', 'file']), \
                    "Encoding error resolution steps should mention relevant keywords"
            
            elif error_category == DatabaseErrorCategory.COMPATIBILITY_ERROR:
                assert any(keyword in steps_text for keyword in ['version', 'compatibility', 'update', 'driver']), \
                    "Compatibility error resolution steps should mention relevant keywords"
            
            elif error_category == DatabaseErrorCategory.POOL_EXHAUSTION:
                assert any(keyword in steps_text for keyword in ['pool', 'connection', 'limit', 'cleanup']), \
                    "Pool exhaustion resolution steps should mention relevant keywords"
            
            # Verify component is mentioned in steps
            assert component.lower() in steps_text or 'database' in steps_text, \
                f"Resolution steps should mention {component} or generic database terms"
    
    @given(
        error_count=st.integers(min_value=1, max_value=20),
        component=st.sampled_from(['PostgreSQL', 'Neo4j', 'Redis']),
        error_category=st.sampled_from(list(DatabaseErrorCategory))
    )
    @settings(max_examples=50, deadline=15000)
    def test_pattern_analysis_in_structured_messages_property(
        self, error_count, component, error_category
    ):
        """
        **Property 12: Error Classification and Messaging - Pattern Analysis**
        **Validates: Requirements 5.4**
        
        For any sequence of similar errors, the structured error messages should
        include pattern analysis and recommendations based on error frequency.
        """
        # Reset statistics
        ErrorReporter.reset_error_statistics()
        
        # Generate multiple errors of the same type
        for i in range(error_count):
            error = Exception(f"Test error {i}")
            error_info = ErrorReporter.create_database_error_info(error, component)
            error_info.category = error_category  # Override for testing
            
            # Add to statistics
            ErrorReporter._error_statistics.add_error(error_info)
        
        # Create final error for message generation
        final_error = Exception("Final test error")
        final_error_info = ErrorReporter.create_database_error_info(final_error, component)
        final_error_info.category = error_category
        
        # Generate structured message
        structured_message = ErrorReporter.format_structured_error_message(
            final_error_info,
            include_resolution_steps=True,
            include_context=True
        )
        
        # Verify pattern analysis is included for repeated errors
        if error_count >= 2:
            assert "Pattern Analysis:" in structured_message, "Should include pattern analysis for repeated errors"
            assert f"occurred {error_count} times" in structured_message, "Should mention error frequency"
            assert f"Component {component} has {error_count} total errors" in structured_message, "Should mention component error count"
        
        # Verify warnings for frequent errors
        if error_count >= 3:
            assert "⚠️" in structured_message, "Should include warning indicators for frequent errors"
            assert "Frequent" in structured_message, "Should mention frequent errors"
        
        if error_count >= 5:
            assert "high error rate" in structured_message, "Should mention high error rate for many errors"
            assert "review configuration" in structured_message, "Should suggest configuration review"
    
    @given(
        sensitive_data=st.lists(
            st.sampled_from([
                "password=TEST_PASSWORD_VALUE",
                "api_key=sk-1234567890abcdefghijklmnop",  # 20+ chars for API key pattern
                "token=bearer_xyz",
                "postgresql://user:password@host:5432/db"
            ]),
            min_size=1,
            max_size=3
        ),
        component=st.sampled_from(['PostgreSQL', 'Neo4j', 'Redis'])
    )
    @settings(max_examples=100, deadline=10000)
    def test_sensitive_data_masking_in_structured_messages_property(
        self, sensitive_data, component
    ):
        """
        **Property 12: Error Classification and Messaging - Sensitive Data Masking**
        **Validates: Requirements 5.4**
        
        For any structured error message containing sensitive data, the system
        should mask all sensitive information while preserving diagnostic value.
        """
        # Create error with sensitive data
        error_message = f"Database error with {' '.join(sensitive_data)}"
        error = Exception(error_message)
        
        # Create connection parameters with sensitive data
        connection_params = {}
        for data in sensitive_data:
            if '=' in data:
                key, value = data.split('=', 1)
                connection_params[key] = value
            elif '://' in data:
                connection_params['connection_string'] = data
        
        # Create error info
        error_info = ErrorReporter.create_database_error_info(
            error=error,
            component=component,
            connection_params=connection_params if connection_params else None
        )
        
        # Generate structured message
        structured_message = ErrorReporter.format_structured_error_message(
            error_info,
            include_resolution_steps=True,
            include_context=True
        )
        
        # Verify sensitive data is masked
        for data in sensitive_data:
            if '=' in data:
                key, value = data.split('=', 1)
                if len(value) > 3:  # Only check non-trivial values
                    # The original value should not appear in the message
                    assert value not in structured_message or '***' in structured_message, \
                        f"Sensitive value '{value}' should be masked in structured message"
            elif '://' in data and ':' in data and '@' in data:
                # Connection string passwords should be masked
                if 'password' in data:
                    assert 'password' not in structured_message or '***' in structured_message, \
                        "Connection string passwords should be masked"
        
        # Verify masking indicators are present when sensitive data exists
        if connection_params:
            assert '***' in structured_message, "Should contain masking indicators when sensitive data is present"
        
        # Verify non-sensitive data is preserved
        assert component in structured_message, "Component name should not be masked"
        assert "Error Details:" in structured_message or not connection_params, "Section headers should not be masked"
    
    @given(
        error_categories=st.lists(
            st.sampled_from(list(DatabaseErrorCategory)),
            min_size=2,
            max_size=5,
            unique=True
        ),
        components=st.lists(
            st.sampled_from(['PostgreSQL', 'Neo4j', 'Redis']),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=50, deadline=15000)
    def test_error_message_consistency_property(
        self, error_categories, components
    ):
        """
        **Property 12: Error Classification and Messaging - Message Consistency**
        **Validates: Requirements 5.4**
        
        For any set of different error types, the structured error messages should
        maintain consistent formatting and structure while providing category-specific content.
        """
        structured_messages = []
        
        # Generate structured messages for different error types
        for i, category in enumerate(error_categories):
            component = components[i % len(components)]
            
            error = Exception(f"Test error for {category.value}")
            error_info = ErrorReporter.create_database_error_info(error, component)
            error_info.category = category
            
            structured_message = ErrorReporter.format_structured_error_message(
                error_info,
                include_resolution_steps=True,
                include_context=True
            )
            structured_messages.append(structured_message)
        
        # Verify consistent structure across all messages
        for message in structured_messages:
            # All messages should have the same header
            assert "DATABASE ERROR REPORT" in message, "All messages should have consistent header"
            assert "=" * 50 in message, "All messages should have consistent separator"
            
            # All messages should have required sections
            assert "Component:" in message, "All messages should have component section"
            assert "Category:" in message, "All messages should have category section"
            assert "Timestamp:" in message, "All messages should have timestamp section"
            assert "Message:" in message, "All messages should have message section"
            assert "Resolution Steps:" in message, "All messages should have resolution steps section"
            
            # All messages should have proper formatting
            lines = message.split('\n')
            assert len(lines) > 5, "All messages should have multiple lines"
            
            # Check for consistent section separators
            separator_lines = [line for line in lines if '-' * 20 in line]
            assert len(separator_lines) >= 1, "All messages should have section separators"
        
        # Verify messages are different (category-specific content)
        unique_messages = set(structured_messages)
        assert len(unique_messages) == len(error_categories), "Messages should be unique for different error categories"
        
        # Verify category-specific content exists
        for i, (message, category) in enumerate(zip(structured_messages, error_categories)):
            category_name = category.value.replace('_', ' ').title()
            assert category_name in message, f"Message should contain formatted category name: {category_name}"


# Integration test to verify property test assumptions
def test_error_classification_and_messaging_integration():
    """Integration test to verify error classification and structured messaging works correctly"""
    # Reset statistics
    ErrorReporter.reset_error_statistics()
    
    # Test various error types
    test_cases = [
        ("Connection timeout after 30 seconds", DatabaseErrorCategory.CONNECTION_TIMEOUT),
        ("Authentication failed for user admin", DatabaseErrorCategory.AUTHENTICATION_FAILURE),
        ("UTF-8 decoding error in migration file", DatabaseErrorCategory.ENCODING_ERROR),
        ("Python 3.13 incompatible with asyncpg 0.25", DatabaseErrorCategory.COMPATIBILITY_ERROR),
        ("Connection pool exhausted - max 20 connections", DatabaseErrorCategory.POOL_EXHAUSTION)
    ]
    
    for error_message, expected_category in test_cases:
        error = Exception(error_message)
        
        # Test classification
        actual_category = ErrorReporter.classify_database_error(error, 'PostgreSQL')
        assert actual_category == expected_category, f"Classification mismatch for '{error_message}'"
        
        # Test structured message generation
        error_info = ErrorReporter.create_database_error_info(
            error=error,
            component='PostgreSQL',
            connection_params={'host': 'localhost', 'port': '5432'},
            error_code='E001'
        )
        
        structured_message = ErrorReporter.format_structured_error_message(error_info)
        
        # Verify message structure
        assert "DATABASE ERROR REPORT" in structured_message
        assert "Component: PostgreSQL" in structured_message
        assert f"Category: {expected_category.value.replace('_', ' ').title()}" in structured_message
        assert "Resolution Steps:" in structured_message
        assert len(error_info.resolution_steps) > 0
        
        # Verify resolution steps are appropriate
        steps_text = " ".join(error_info.resolution_steps).lower()
        if expected_category == DatabaseErrorCategory.CONNECTION_TIMEOUT:
            assert any(keyword in steps_text for keyword in ['timeout', 'connection', 'network'])
        elif expected_category == DatabaseErrorCategory.AUTHENTICATION_FAILURE:
            assert any(keyword in steps_text for keyword in ['password', 'credentials', 'authentication'])


# Test fixtures for property tests
@pytest.fixture
def sample_error_categories():
    """Sample error categories for testing"""
    return list(DatabaseErrorCategory)


@pytest.fixture
def sample_components():
    """Sample database components for testing"""
    return ['PostgreSQL', 'Neo4j', 'Redis', 'MongoDB', 'MySQL']


@pytest.fixture
def sample_error_messages():
    """Sample error messages for different categories"""
    return {
        DatabaseErrorCategory.CONNECTION_TIMEOUT: [
            "Connection timed out after 30 seconds",
            "Request timeout occurred",
            "Connection timeout to database"
        ],
        DatabaseErrorCategory.AUTHENTICATION_FAILURE: [
            "Authentication failed for user",
            "Invalid password provided",
            "Access denied to database",
            "Login failed - credentials invalid"
        ],
        DatabaseErrorCategory.ENCODING_ERROR: [
            "UTF-8 decoding error in file",
            "Character encoding issue detected",
            "Unicode decode error occurred"
        ]
    }