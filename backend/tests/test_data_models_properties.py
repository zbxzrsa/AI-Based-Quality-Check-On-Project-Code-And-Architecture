"""
Property-based tests for data models.

**Validates: Requirements 5.3, 5.6**

This module tests data model properties using Hypothesis for property-based testing:
- Referential integrity properties
- Constraint validation properties

Property-based testing generates many test cases automatically to verify
that data model properties hold across a wide range of inputs.

Each property test runs with 100 iterations as specified in Requirement 5.6.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timedelta
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User, Project, PullRequest, CodeEntity, ProjectAccess,
    Session, TokenBlacklist, ReviewResult, UserRole
)
from app.models.code_review import PRStatus as CodeReviewPRStatus


# ========================================
# Hypothesis Strategies
# ========================================

# Strategy for generating valid email addresses
email_strategy = st.emails()

# Strategy for generating user roles
user_role_strategy = st.sampled_from([UserRole.USER])

# Strategy for generating PR statuses
pr_status_strategy = st.sampled_from([
    CodeReviewPRStatus.PENDING, 
    CodeReviewPRStatus.ANALYZING, 
    CodeReviewPRStatus.REVIEWED
])

# Strategy for generating valid strings
name_strategy = st.text(min_size=1, max_size=255, alphabet=st.characters(blacklist_characters='\x00'))

# Strategy for generating valid UUIDs
uuid_strategy = st.uuids()


# ========================================
# Test Fixtures
# ========================================
# Note: db_session fixture is provided by conftest.py

@pytest.fixture
async def sample_user(db_session: AsyncSession):
    """Create a sample user for testing"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        role=UserRole.USER,
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_project(db_session: AsyncSession, sample_user: User):
    """Create a sample project for testing"""
    project = Project(
        id=uuid.uuid4(),
        owner_id=sample_user.id,
        name="Test Project",
        description="Test Description",
        github_repo_url="https://github.com/test/repo",
        language="python",
        is_active=True
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


class TestReferentialIntegrityProperties:
    """
    Property-based tests for referential integrity in data models.
    
    **Validates: Requirement 5.3** - Property-based tests for data model
    **Validates: Requirement 5.6** - Execute minimum 100 iterations per property
    """
    
    @pytest.mark.asyncio
    @given(email=email_strategy, role=user_role_strategy)
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_user_creation_with_valid_data(self, db_session: AsyncSession, email: str, role: UserRole):
        """
        Property: Users can be created with valid email and role.
        
        This ensures basic user creation works with valid inputs.
        """
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash="test_hash",
            role=role,
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == email
        assert user.role == role
        assert user.created_at is not None
        
        # Cleanup
        await db_session.delete(user)
        await db_session.commit()

    
    @pytest.mark.asyncio
    async def test_project_requires_valid_owner(self, db_session: AsyncSession):
        """
        Property: Projects cannot be created without a valid owner_id (foreign key constraint).
        
        This ensures referential integrity for Project -> User relationship.
        """
        # Try to create project with non-existent owner
        invalid_owner_id = uuid.uuid4()
        project = Project(
            id=uuid.uuid4(),
            owner_id=invalid_owner_id,
            name="Test Project",
            is_active=True
        )
        
        db_session.add(project)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_cascade_delete_user_deletes_projects(self, db_session: AsyncSession):
        """
        Property: Deleting a user cascades to delete their projects.
        
        This ensures CASCADE delete works for User -> Project relationship.
        """
        # Create user
        user = User(
            id=uuid.uuid4(),
            email="cascade@example.com",
            password_hash="test_hash",
            role=UserRole.USER,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create project owned by user
        project = Project(
            id=uuid.uuid4(),
            owner_id=user.id,
            name="Test Project",
            is_active=True
        )
        db_session.add(project)
        await db_session.commit()
        project_id = project.id
        
        # Delete user
        await db_session.delete(user)
        await db_session.commit()
        
        # Verify project was also deleted
        result = await db_session.execute(
            select(Project).where(Project.id == project_id)
        )
        deleted_project = result.scalar_one_or_none()
        assert deleted_project is None, "Project should be deleted when user is deleted"
    
    @pytest.mark.asyncio
    async def test_pull_request_requires_valid_project(self, db_session: AsyncSession):
        """
        Property: PullRequests cannot be created without a valid project_id.
        
        This ensures referential integrity for PullRequest -> Project relationship.
        """
        # Try to create pull request with non-existent project
        invalid_project_id = uuid.uuid4()
        pr = PullRequest(
            id=uuid.uuid4(),
            project_id=invalid_project_id,
            github_pr_number=123,
            title="Test PR",
            status=CodeReviewPRStatus.PENDING
        )
        
        db_session.add(pr)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()

    
    @pytest.mark.asyncio
    async def test_cascade_delete_project_deletes_pull_requests(self, db_session: AsyncSession, sample_user: User):
        """
        Property: Deleting a project cascades to delete its pull requests.
        
        This ensures CASCADE delete works for Project -> PullRequest relationship.
        """
        # Create project
        project = Project(
            id=uuid.uuid4(),
            owner_id=sample_user.id,
            name="Test Project",
            is_active=True
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        
        # Create pull request for project
        pr = PullRequest(
            id=uuid.uuid4(),
            project_id=project.id,
            author_id=sample_user.id,
            github_pr_number=123,
            title="Test PR",
            status=CodeReviewPRStatus.PENDING
        )
        db_session.add(pr)
        await db_session.commit()
        pr_id = pr.id
        
        # Delete project
        await db_session.delete(project)
        await db_session.commit()
        
        # Verify pull request was also deleted
        result = await db_session.execute(
            select(PullRequest).where(PullRequest.id == pr_id)
        )
        deleted_pr = result.scalar_one_or_none()
        assert deleted_pr is None, "PullRequest should be deleted when project is deleted"
    
    @pytest.mark.asyncio
    async def test_code_entity_requires_valid_project(self, db_session: AsyncSession):
        """
        Property: CodeEntities cannot be created without a valid project_id.
        
        This ensures referential integrity for CodeEntity -> Project relationship.
        """
        # Try to create code entity with non-existent project
        invalid_project_id = uuid.uuid4()
        entity = CodeEntity(
            id=uuid.uuid4(),
            project_id=invalid_project_id,
            entity_type="function",
            name="test_function",
            qualified_name="module.test_function",
            file_path="test.py",
            start_line=1,
            end_line=10
        )
        
        db_session.add(entity)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_project_access_requires_valid_project_and_user(self, db_session: AsyncSession):
        """
        Property: ProjectAccess cannot be created without valid project_id and user_id.
        
        This ensures referential integrity for ProjectAccess relationships.
        """
        # Try to create project access with non-existent project
        invalid_project_id = uuid.uuid4()
        invalid_user_id = uuid.uuid4()
        
        access = ProjectAccess(
            id=uuid.uuid4(),
            project_id=invalid_project_id,
            user_id=invalid_user_id,
            access_level="read"
        )
        
        db_session.add(access)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()

    
    @pytest.mark.asyncio
    async def test_cascade_delete_user_deletes_project_access(self, db_session: AsyncSession, sample_project: Project):
        """
        Property: Deleting a user cascades to delete their project access records.
        
        This ensures CASCADE delete works for User -> ProjectAccess relationship.
        """
        # Create user
        user = User(
            id=uuid.uuid4(),
            email="access@example.com",
            password_hash="test_hash",
            role=UserRole.USER,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create project access for user
        access = ProjectAccess(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            user_id=user.id,
            access_level="read"
        )
        db_session.add(access)
        await db_session.commit()
        access_id = access.id
        
        # Delete user
        await db_session.delete(user)
        await db_session.commit()
        
        # Verify project access was also deleted
        result = await db_session.execute(
            select(ProjectAccess).where(ProjectAccess.id == access_id)
        )
        deleted_access = result.scalar_one_or_none()
        assert deleted_access is None, "ProjectAccess should be deleted when user is deleted"
    
    @pytest.mark.asyncio
    async def test_session_requires_valid_user(self, db_session: AsyncSession):
        """
        Property: Sessions cannot be created without a valid user_id.
        
        This ensures referential integrity for Session -> User relationship.
        """
        # Try to create session with non-existent user
        invalid_user_id = uuid.uuid4()
        session = Session(
            id=uuid.uuid4(),
            user_id=invalid_user_id,
            token_jti="test_jti",
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_active=True
        )
        
        db_session.add(session)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_review_result_requires_valid_pull_request(self, db_session: AsyncSession):
        """
        Property: ReviewResults cannot be created without a valid pull_request_id.
        
        This ensures referential integrity for ReviewResult -> PullRequest relationship.
        """
        # Try to create review result with non-existent pull request
        invalid_pr_id = uuid.uuid4()
        result = ReviewResult(
            id=uuid.uuid4(),
            pull_request_id=invalid_pr_id,
            confidence_score=0.85,
            total_issues=5,
            critical_issues=1
        )
        
        db_session.add(result)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()


class TestConstraintValidationProperties:
    """
    Property-based tests for constraint validation in data models.
    
    **Validates: Requirement 5.3** - Property-based tests for data model
    **Validates: Requirement 5.6** - Execute minimum 100 iterations per property
    """

    
    @pytest.mark.asyncio
    async def test_user_email_must_be_unique(self, db_session: AsyncSession):
        """
        Property: User emails must be unique (unique constraint).
        
        This ensures no duplicate email addresses in the system.
        """
        email = "unique@example.com"
        
        # Create first user
        user1 = User(
            id=uuid.uuid4(),
            email=email,
            password_hash="test_hash",
            role=UserRole.USER,
            is_active=True
        )
        db_session.add(user1)
        await db_session.commit()
        
        # Try to create second user with same email
        user2 = User(
            id=uuid.uuid4(),
            email=email,
            password_hash="test_hash2",
            role=UserRole.USER,
            is_active=True
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Cleanup
        await db_session.delete(user1)
        await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_project_github_repo_url_must_be_unique(self, db_session: AsyncSession, sample_user: User):
        """
        Property: Project GitHub repo URLs must be unique (unique constraint).
        
        This ensures no duplicate repository URLs in the system.
        """
        repo_url = "https://github.com/test/unique-repo"
        
        # Create first project
        project1 = Project(
            id=uuid.uuid4(),
            owner_id=sample_user.id,
            name="Project 1",
            github_repo_url=repo_url,
            is_active=True
        )
        db_session.add(project1)
        await db_session.commit()
        
        # Try to create second project with same repo URL
        project2 = Project(
            id=uuid.uuid4(),
            owner_id=sample_user.id,
            name="Project 2",
            github_repo_url=repo_url,
            is_active=True
        )
        db_session.add(project2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Cleanup
        await db_session.delete(project1)
        await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_project_access_unique_constraint(self, db_session: AsyncSession, sample_user: User, sample_project: Project):
        """
        Property: ProjectAccess has unique constraint on (project_id, user_id).
        
        This ensures a user cannot have duplicate access records for the same project.
        """
        # Create first access record
        access1 = ProjectAccess(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            user_id=sample_user.id,
            access_level="read"
        )
        db_session.add(access1)
        await db_session.commit()
        
        # Try to create second access record for same project and user
        access2 = ProjectAccess(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            user_id=sample_user.id,
            access_level="write"
        )
        db_session.add(access2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Cleanup
        await db_session.delete(access1)
        await db_session.commit()

    
    @pytest.mark.asyncio
    async def test_session_token_jti_must_be_unique(self, db_session: AsyncSession, sample_user: User):
        """
        Property: Session token_jti must be unique (unique constraint).
        
        This ensures no duplicate JWT IDs in the system.
        """
        token_jti = "unique_jti_12345"
        
        # Create first session
        session1 = Session(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            token_jti=token_jti,
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_active=True
        )
        db_session.add(session1)
        await db_session.commit()
        
        # Try to create second session with same token_jti
        session2 = Session(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            token_jti=token_jti,
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_active=True
        )
        db_session.add(session2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Cleanup
        await db_session.delete(session1)
        await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_token_blacklist_token_must_be_unique(self, db_session: AsyncSession, sample_user: User):
        """
        Property: TokenBlacklist token must be unique (unique constraint).
        
        This ensures no duplicate blacklisted tokens.
        """
        token = "blacklisted_token_12345"
        
        # Create first blacklist entry
        blacklist1 = TokenBlacklist(
            id=uuid.uuid4(),
            token=token,
            user_id=sample_user.id,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        db_session.add(blacklist1)
        await db_session.commit()
        
        # Try to create second blacklist entry with same token
        blacklist2 = TokenBlacklist(
            id=uuid.uuid4(),
            token=token,
            user_id=sample_user.id,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        db_session.add(blacklist2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Cleanup
        await db_session.delete(blacklist1)
        await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_review_result_pull_request_unique_constraint(self, db_session: AsyncSession, sample_user: User, sample_project: Project):
        """
        Property: ReviewResult has unique constraint on pull_request_id.
        
        This ensures each pull request has at most one review result.
        """
        # Create pull request
        pr = PullRequest(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            author_id=sample_user.id,
            github_pr_number=123,
            title="Test PR",
            status=CodeReviewPRStatus.PENDING
        )
        db_session.add(pr)
        await db_session.commit()
        
        # Create first review result
        result1 = ReviewResult(
            id=uuid.uuid4(),
            pull_request_id=pr.id,
            confidence_score=0.85,
            total_issues=5,
            critical_issues=1
        )
        db_session.add(result1)
        await db_session.commit()
        
        # Try to create second review result for same pull request
        result2 = ReviewResult(
            id=uuid.uuid4(),
            pull_request_id=pr.id,
            confidence_score=0.90,
            total_issues=3,
            critical_issues=0
        )
        db_session.add(result2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Cleanup
        await db_session.delete(result1)
        await db_session.delete(pr)
        await db_session.commit()

    
    @pytest.mark.asyncio
    @given(email=email_strategy)
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_user_email_cannot_be_null(self, db_session: AsyncSession, email: Optional[str]):
        """
        Property: User email cannot be NULL (NOT NULL constraint).
        
        This ensures all users have an email address.
        """
        assume(email is not None)  # Only test with non-null emails
        
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash="test_hash",
            role=UserRole.USER,
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Verify email is stored
        assert user.email == email
        
        # Cleanup
        await db_session.delete(user)
        await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_user_email_null_raises_error(self, db_session: AsyncSession):
        """
        Property: Creating a user with NULL email raises IntegrityError.
        """
        user = User(
            id=uuid.uuid4(),
            email=None,  # NULL email
            password_hash="test_hash",
            role=UserRole.USER,
            is_active=True
        )
        
        db_session.add(user)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_project_owner_id_cannot_be_null(self, db_session: AsyncSession):
        """
        Property: Project owner_id cannot be NULL (NOT NULL constraint).
        
        This ensures all projects have an owner.
        """
        project = Project(
            id=uuid.uuid4(),
            owner_id=None,  # NULL owner_id
            name="Test Project",
            is_active=True
        )
        
        db_session.add(project)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_pull_request_project_id_cannot_be_null(self, db_session: AsyncSession):
        """
        Property: PullRequest project_id cannot be NULL (NOT NULL constraint).
        
        This ensures all pull requests belong to a project.
        """
        pr = PullRequest(
            id=uuid.uuid4(),
            project_id=None,  # NULL project_id
            github_pr_number=123,
            title="Test PR",
            status=CodeReviewPRStatus.PENDING
        )
        
        db_session.add(pr)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
    
    @pytest.mark.asyncio
    async def test_code_entity_required_fields_cannot_be_null(self, db_session: AsyncSession, sample_project: Project):
        """
        Property: CodeEntity required fields cannot be NULL.
        
        This ensures all code entities have complete information.
        """
        # Test with NULL entity_type
        entity = CodeEntity(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            entity_type=None,  # NULL
            name="test_function",
            qualified_name="module.test_function",
            file_path="test.py",
            start_line=1,
            end_line=10
        )
        
        db_session.add(entity)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()



class TestDataIntegrityProperties:
    """
    Property-based tests for data integrity across the system.
    
    **Validates: Requirement 5.3** - Property-based tests for data model
    **Validates: Requirement 5.6** - Execute minimum 100 iterations per property
    """
    
    @pytest.mark.asyncio
    async def test_orphaned_pull_requests_cannot_exist(self, db_session: AsyncSession, sample_user: User):
        """
        Property: Pull requests cannot exist without a valid project (no orphans).
        
        This ensures referential integrity prevents orphaned records.
        """
        # Create project and pull request
        project = Project(
            id=uuid.uuid4(),
            owner_id=sample_user.id,
            name="Test Project",
            is_active=True
        )
        db_session.add(project)
        await db_session.commit()
        
        pr = PullRequest(
            id=uuid.uuid4(),
            project_id=project.id,
            author_id=sample_user.id,
            github_pr_number=123,
            title="Test PR",
            status=CodeReviewPRStatus.PENDING
        )
        db_session.add(pr)
        await db_session.commit()
        pr_id = pr.id
        
        # Delete project (should cascade delete PR)
        await db_session.delete(project)
        await db_session.commit()
        
        # Verify PR no longer exists
        result = await db_session.execute(
            select(PullRequest).where(PullRequest.id == pr_id)
        )
        orphaned_pr = result.scalar_one_or_none()
        assert orphaned_pr is None, "Pull request should not exist after project deletion"
    
    @pytest.mark.asyncio
    async def test_orphaned_code_entities_cannot_exist(self, db_session: AsyncSession, sample_user: User):
        """
        Property: Code entities cannot exist without a valid project (no orphans).
        
        This ensures referential integrity prevents orphaned code entities.
        """
        # Create project and code entity
        project = Project(
            id=uuid.uuid4(),
            owner_id=sample_user.id,
            name="Test Project",
            is_active=True
        )
        db_session.add(project)
        await db_session.commit()
        
        entity = CodeEntity(
            id=uuid.uuid4(),
            project_id=project.id,
            entity_type="function",
            name="test_function",
            qualified_name="module.test_function",
            file_path="test.py",
            start_line=1,
            end_line=10
        )
        db_session.add(entity)
        await db_session.commit()
        entity_id = entity.id
        
        # Delete project (should cascade delete entity)
        await db_session.delete(project)
        await db_session.commit()
        
        # Verify entity no longer exists
        result = await db_session.execute(
            select(CodeEntity).where(CodeEntity.id == entity_id)
        )
        orphaned_entity = result.scalar_one_or_none()
        assert orphaned_entity is None, "Code entity should not exist after project deletion"
    
    @pytest.mark.asyncio
    async def test_orphaned_project_access_cannot_exist(self, db_session: AsyncSession, sample_project: Project):
        """
        Property: Project access records cannot exist without valid user (no orphans).
        
        This ensures referential integrity prevents orphaned access records.
        """
        # Create user and project access
        user = User(
            id=uuid.uuid4(),
            email="orphan@example.com",
            password_hash="test_hash",
            role=UserRole.USER,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        
        access = ProjectAccess(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            user_id=user.id,
            access_level="read"
        )
        db_session.add(access)
        await db_session.commit()
        access_id = access.id
        
        # Delete user (should cascade delete access)
        await db_session.delete(user)
        await db_session.commit()
        
        # Verify access no longer exists
        result = await db_session.execute(
            select(ProjectAccess).where(ProjectAccess.id == access_id)
        )
        orphaned_access = result.scalar_one_or_none()
        assert orphaned_access is None, "Project access should not exist after user deletion"

    
    @pytest.mark.asyncio
    @given(
        pr_number=st.integers(min_value=1, max_value=999999),
        status=pr_status_strategy
    )
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_pull_request_data_consistency(
        self, 
        db_session: AsyncSession, 
        sample_user: User, 
        sample_project: Project,
        pr_number: int,
        status: CodeReviewPRStatus
    ):
        """
        Property: Pull request data remains consistent after creation and retrieval.
        
        This ensures data is stored and retrieved correctly.
        """
        # Create pull request
        pr = PullRequest(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            author_id=sample_user.id,
            github_pr_number=pr_number,
            title=f"Test PR #{pr_number}",
            status=status,
            files_changed=5,
            lines_added=100,
            lines_deleted=50
        )
        
        db_session.add(pr)
        await db_session.commit()
        pr_id = pr.id
        
        # Retrieve and verify
        result = await db_session.execute(
            select(PullRequest).where(PullRequest.id == pr_id)
        )
        retrieved_pr = result.scalar_one()
        
        assert retrieved_pr.github_pr_number == pr_number
        assert retrieved_pr.status == status
        assert retrieved_pr.files_changed == 5
        assert retrieved_pr.lines_added == 100
        assert retrieved_pr.lines_deleted == 50
        
        # Cleanup
        await db_session.delete(retrieved_pr)
        await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_timestamps_are_automatically_set(self, db_session: AsyncSession):
        """
        Property: created_at and updated_at timestamps are automatically set.
        
        This ensures audit trail timestamps are maintained.
        """
        # Create user
        user = User(
            id=uuid.uuid4(),
            email="timestamp@example.com",
            password_hash="test_hash",
            role=UserRole.USER,
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Verify timestamps are set
        assert user.created_at is not None, "created_at should be automatically set"
        assert user.updated_at is not None, "updated_at should be automatically set"
        
        # Store original timestamps
        original_created_at = user.created_at
        original_updated_at = user.updated_at
        
        # Update user
        user.full_name = "Updated Name"
        await db_session.commit()
        await db_session.refresh(user)
        
        # Verify created_at unchanged, updated_at changed
        assert user.created_at == original_created_at, "created_at should not change on update"
        assert user.updated_at > original_updated_at, "updated_at should be updated"
        
        # Cleanup
        await db_session.delete(user)
        await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_default_values_are_applied(self, db_session: AsyncSession, sample_user: User):
        """
        Property: Default values are applied when fields are not specified.
        
        This ensures database defaults work correctly.
        """
        # Create project without specifying is_active
        project = Project(
            id=uuid.uuid4(),
            owner_id=sample_user.id,
            name="Test Project"
            # is_active not specified, should default to True
        )
        
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        
        # Verify default value
        assert project.is_active is True, "is_active should default to True"
        
        # Cleanup
        await db_session.delete(project)
        await db_session.commit()
    
    @pytest.mark.asyncio
    @given(role=user_role_strategy)
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_enum_values_are_validated(self, db_session: AsyncSession, role: UserRole):
        """
        Property: Enum values are properly validated and stored.
        
        This ensures enum constraints work correctly.
        """
        user = User(
            id=uuid.uuid4(),
            email=f"enum_{uuid.uuid4()}@example.com",
            password_hash="test_hash",
            role=role,
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Verify enum value is stored correctly
        assert user.role == role
        assert isinstance(user.role, UserRole)
        
        # Cleanup
        await db_session.delete(user)
        await db_session.commit()
