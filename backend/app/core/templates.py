"""
妯℃澘鏂规硶妯″紡瀹炵幇 - 缁熶竴澶勭悊鍏锋湁鍥哄畾娴佺▼浣嗙粏鑺備笉鍚岀殑绠楁硶姝ラ

鍖呭惈浠ヤ笅妯℃澘锛?
1. Repository楠岃瘉妯℃澘
2. Invitation鐘舵€佽浆鎹㈡ā鏉?
3. 浠ｇ爜瀹℃煡娴佺▼妯℃澘
4. 閫氱敤涓氬姟娴佺▼妯℃澘
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Repository楠岃瘉妯℃澘
# ============================================================================


class RepositoryValidationTemplate(ABC):
    """
    Repository楠岃瘉妯℃澘鏂规硶

    鍥哄畾娴佺▼锛?
    1. 璁剧疆API headers
    2. 妫€鏌ヤ粨搴撳瓨鍦ㄦ€?
    3. 鑾峰彇鍒嗘敮鍒楄〃
    4. 鑾峰彇鏍囩鍒楄〃
    5. 楠岃瘉鐗瑰畾鍒嗘敮
    6. 杩斿洖楠岃瘉缁撴灉
    """

    async def validate_repository(self, repo_info: dict[str, Any], branch: str | None = None) -> dict[str, Any]:
        """
        妯℃澘鏂规硶 - 瀹氫箟楠岃瘉娴佺▼

        Args:
            repo_info: 浠撳簱淇℃伅
            branch: 鍙€夌殑鍒嗘敮鍚嶇О

        Returns:
            楠岃瘉缁撴灉
        """
        try:
            logger.info(f"Starting repository validation for {repo_info.get('owner')}/{repo_info.get('name')}")

            # 姝ラ1: 璁剧疆API headers
            headers = await self.setup_api_headers()

            # 姝ラ2: 妫€鏌ヤ粨搴撳瓨鍦ㄦ€?
            repo_exists, repo_data = await self.check_repository_existence(repo_info, headers)
            if not repo_exists:
                return self.create_failure_result("Repository not found or inaccessible")

            # 姝ラ3: 鑾峰彇鍒嗘敮鍒楄〃
            branches = await self.fetch_branches(repo_info, headers)

            # 姝ラ4: 鑾峰彇鏍囩鍒楄〃
            tags = await self.fetch_tags(repo_info, headers)

            # 姝ラ5: 楠岃瘉鐗瑰畾鍒嗘敮锛堝鏋滄彁渚涳級
            branch_validation = self.validate_specific_branch(repo_info, branch, branches, headers)
            if not branch_validation["valid"]:
                return self.create_failure_result(branch_validation["error"])

            # 姝ラ6: 鏋勫缓鎴愬姛缁撴灉
            result = self.build_success_result(repo_data, branches, tags, branch)

            logger.info(
                f"Repository validation completed successfully for {repo_info.get('owner')}/{repo_info.get('name')}"
            )
            return result

        except Exception as e:
            logger.error(f"Repository validation failed: {e}")
            return self.create_failure_result(f"Validation error: {str(e)}")

    # 鎶借薄鏂规硶 - 瀛愮被蹇呴』瀹炵幇
    @abstractmethod
    async def setup_api_headers(self) -> dict[str, str]:
        """璁剧疆API璇锋眰澶?"""
        pass

    @abstractmethod
    async def check_repository_existence(
        self, repo_info: dict[str, Any], headers: dict[str, str]
    ) -> tuple[bool, dict[str, Any] | None]:
        """妫€鏌ヤ粨搴撴槸鍚﹀瓨鍦?"""
        pass

    @abstractmethod
    async def fetch_branches(self, repo_info: dict[str, Any], headers: dict[str, str]) -> list[str]:
        """鑾峰彇鍒嗘敮鍒楄〃"""
        pass

    @abstractmethod
    async def fetch_tags(self, repo_info: dict[str, Any], headers: dict[str, str]) -> list[str]:
        """鑾峰彇鏍囩鍒楄〃"""
        pass

    # 鍙€夌殑閽╁瓙鏂规硶 - 瀛愮被鍙互閲嶅啓
    def validate_specific_branch(
        self, repo_info: dict[str, Any], branch: str | None, branches: list[str], headers: dict[str, str]
    ) -> dict[str, Any]:
        """楠岃瘉鐗瑰畾鍒嗘敮"""
        if branch and branch not in branches:
            return {"valid": False, "error": f"Branch '{branch}' not found"}
        return {"valid": True}

    def build_success_result(
        self, repo_data: dict[str, Any], branches: list[str], tags: list[str], branch: str | None
    ) -> dict[str, Any]:
        """鏋勫缓鎴愬姛缁撴灉"""
        return {
            "is_valid": True,
            "is_accessible": True,
            "exists": True,
            "default_branch": repo_data.get("default_branch", "main"),
            "available_branches": branches[:10],  # 闄愬埗杩斿洖鏁伴噺
            "available_tags": tags[:10],
            "validated_branch": branch,
            "metadata": repo_data,
        }

    def create_failure_result(self, error_message: str) -> dict[str, Any]:
        """鍒涘缓澶辫触缁撴灉"""
        return {"is_valid": False, "is_accessible": False, "exists": False, "error_message": error_message}


class GitHubRepositoryValidator(RepositoryValidationTemplate):
    """GitHub浠撳簱楠岃瘉鍣ㄥ疄鐜?"""

    def __init__(self, github_token: str | None = None):
        self.github_token = github_token
        self.api_base = "https://api.github.com"

    async def setup_api_headers(self) -> dict[str, str]:
        """璁剧疆GitHub API璇锋眰澶?"""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers

    async def check_repository_existence(
        self, repo_info: dict[str, Any], headers: dict[str, str]
    ) -> tuple[bool, dict[str, Any] | None]:
        """妫€鏌itHub浠撳簱鏄惁瀛樺湪"""
        import aiohttp

        owner = repo_info.get("owner")
        name = repo_info.get("name")
        repo_url = f"{self.api_base}/repos/{owner}/{name}"

        async with aiohttp.ClientSession() as session:
            async with session.get(repo_url, headers=headers) as response:
                if response.status == 200:
                    repo_data = await response.json()
                    return True, repo_data
                elif response.status == 404:
                    return False, None
                elif response.status == 403:
                    return False, None  # Access denied
                else:
                    return False, None

    async def fetch_branches(self, repo_info: dict[str, Any], headers: dict[str, str]) -> list[str]:
        """鑾峰彇GitHub浠撳簱鍒嗘敮鍒楄〃"""
        import aiohttp

        owner = repo_info.get("owner")
        name = repo_info.get("name")
        branches_url = f"{self.api_base}/repos/{owner}/{name}/branches"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(branches_url, headers=headers) as response:
                    if response.status == 200:
                        branches_data = await response.json()
                        return [b["name"] for b in branches_data]
        except Exception as e:
            logger.warning(f"Failed to fetch branches: {e}")

        return []

    async def fetch_tags(self, repo_info: dict[str, Any], headers: dict[str, str]) -> list[str]:
        """鑾峰彇GitHub浠撳簱鏍囩鍒楄〃"""
        import aiohttp

        owner = repo_info.get("owner")
        name = repo_info.get("name")
        tags_url = f"{self.api_base}/repos/{owner}/{name}/tags"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(tags_url, headers=headers) as response:
                    if response.status == 200:
                        tags_data = await response.json()
                        return [t["name"] for t in tags_data[:50]]  # 闄愬埗鏍囩鏁伴噺
        except Exception as e:
            logger.warning(f"Failed to fetch tags: {e}")

        return []


# ============================================================================
# Invitation鐘舵€佽浆鎹㈡ā鏉?
# ============================================================================


class InvitationStateTransitionTemplate(ABC):
    """
    Invitation鐘舵€佽浆鎹㈡ā鏉挎柟娉?

    鍥哄畾娴佺▼锛?
    1. 楠岃瘉褰撳墠鐘舵€?
    2. 妫€鏌ヨ浆鎹㈡潯浠?
    3. 鎵ц鍓嶇疆鎿嶄綔
    4. 鏇存柊鐘舵€?
    5. 鎵ц鍚庣疆鎿嶄綔
    6. 璁板綍瀹¤鏃ュ織
    """

    async def transition_state(
        self, db: AsyncSession, invitation_id: str, new_state: str, user_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        妯℃澘鏂规硶 - 瀹氫箟鐘舵€佽浆鎹㈡祦绋?

        Args:
            db: 鏁版嵁搴撲細璇?
            invitation_id: 閭€璇稩D
            new_state: 鏂扮姸鎬?
            user_id: 鎿嶄綔鐢ㄦ埛ID
            context: 棰濆涓婁笅鏂?

        Returns:
            杞崲缁撴灉
        """
        try:
            logger.info(f"Starting invitation state transition to {new_state} for {invitation_id}")

            # 姝ラ1: 楠岃瘉褰撳墠鐘舵€?
            invitation = await self.validate_current_state(db, invitation_id)
            if not invitation:
                return {"success": False, "error": "Invitation not found"}

            # 姝ラ2: 妫€鏌ヨ浆鎹㈡潯浠?
            can_transition, reason = await self.check_transition_conditions(invitation, new_state, user_id, context)
            if not can_transition:
                return {"success": False, "error": reason}

            # 姝ラ3: 鎵ц鍓嶇疆鎿嶄綔
            pre_result = self.execute_pre_transition_actions(db, invitation, new_state, user_id, context)
            if not pre_result["success"]:
                return pre_result

            # 姝ラ4: 鏇存柊鐘舵€?
            old_state = invitation.status
            await self.update_invitation_state(db, invitation, new_state, user_id)

            # 姝ラ5: 鎵ц鍚庣疆鎿嶄綔
            post_result = await self.execute_post_transition_actions(
                db, invitation, old_state, new_state, user_id, context
            )
            if not post_result["success"]:
                # 濡傛灉鍚庣疆鎿嶄綔澶辫触锛屽彲鑳介渶瑕佸洖婊?
                logger.warning(f"Post-transition actions failed: {post_result['error']}")

            # 姝ラ6: 璁板綍瀹¤鏃ュ織
            await self.log_state_transition(db, invitation_id, old_state, new_state, user_id, context)

            logger.info(f"Invitation state transition completed: {old_state} -> {new_state}")
            return {"success": True, "old_state": old_state, "new_state": new_state, "invitation": invitation}

        except Exception as e:
            logger.error(f"Invitation state transition failed: {e}")
            await db.rollback()
            return {"success": False, "error": f"Transition failed: {str(e)}"}

    # 鎶借薄鏂规硶 - 瀛愮被蹇呴』瀹炵幇
    @abstractmethod
    async def validate_current_state(self, db: AsyncSession, invitation_id: str) -> Any | None:
        """楠岃瘉褰撳墠鐘舵€?"""
        pass

    @abstractmethod
    async def check_transition_conditions(
        self, invitation: Any, new_state: str, user_id: str, context: dict[str, Any] | None
    ) -> tuple[bool, str]:
        """妫€鏌ョ姸鎬佽浆鎹㈡潯浠?"""
        pass

    @abstractmethod
    async def update_invitation_state(self, db: AsyncSession, invitation: Any, new_state: str, user_id: str) -> None:
        """鏇存柊閭€璇风姸鎬?"""
        pass

    # 鍙€夌殑閽╁瓙鏂规硶 - 瀛愮被鍙互閲嶅啓
    def execute_pre_transition_actions(
        self, db: AsyncSession, invitation: Any, new_state: str, user_id: str, context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """鎵ц鍓嶇疆鎿嶄綔"""
        return {"success": True}

    async def execute_post_transition_actions(
        self,
        db: AsyncSession,
        invitation: Any,
        old_state: str,
        new_state: str,
        user_id: str,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """鎵ц鍚庣疆鎿嶄綔"""
        await asyncio.sleep(0)
        return {"success": True}

    async def log_state_transition(
        self,
        db: AsyncSession,
        invitation_id: str,
        old_state: str,
        new_state: str,
        user_id: str,
        context: dict[str, Any] | None,
    ) -> None:
        """璁板綍鐘舵€佽浆鎹㈠璁℃棩蹇?"""
        from app.core.audit_service import UnifiedAuditService

        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action="state_transition",
            entity_type="invitation",
            entity_id=invitation_id,
            success=True,
            changes={"old_state": old_state, "new_state": new_state, "context": context or {}},
        )


class ProjectInvitationTransition(InvitationStateTransitionTemplate):
    """椤圭洰閭€璇风姸鎬佽浆鎹㈠疄鐜?"""

    async def validate_current_state(self, db: AsyncSession, invitation_id: str) -> Any | None:
        """楠岃瘉褰撳墠鐘舵€?"""
        from uuid import UUID

        from sqlalchemy import select

        from app.models import ProjectInvitation

        try:
            invitation_uuid = UUID(invitation_id)
            result = await db.execute(select(ProjectInvitation).where(ProjectInvitation.id == invitation_uuid))
            return result.scalar_one_or_none()
        except ValueError:
            return None

    async def check_transition_conditions(
        self, invitation: Any, new_state: str, user_id: str, context: dict[str, Any] | None
    ) -> tuple[bool, str]:
        """妫€鏌ョ姸鎬佽浆鎹㈡潯浠?"""
        from app.models import InvitationStatus

        current_state = invitation.status

        # 瀹氫箟鍏佽鐨勭姸鎬佽浆鎹?
        allowed_transitions = {
            InvitationStatus.pending.value: [
                InvitationStatus.accepted.value,
                InvitationStatus.declined.value,
                InvitationStatus.expired.value,
            ],
            InvitationStatus.accepted.value: [],  # 宸叉帴鍙楃殑閭€璇蜂笉鑳藉啀杞崲
            InvitationStatus.declined.value: [],  # 宸叉嫆缁濈殑閭€璇蜂笉鑳藉啀杞崲
            InvitationStatus.expired.value: [],  # 宸茶繃鏈熺殑閭€璇蜂笉鑳藉啀杞崲
        }

        if new_state not in allowed_transitions.get(current_state, []):
            return False, f"Cannot transition from {current_state} to {new_state}"

        # 妫€鏌ラ個璇锋槸鍚﹁繃鏈?
        if invitation.is_expired() and new_state != InvitationStatus.expired.value:
            return False, "Invitation has expired"

        # 妫€鏌ョ敤鎴锋潈闄?
        if new_state in [InvitationStatus.accepted.value, InvitationStatus.declined.value]:
            # 鍙湁琚個璇蜂汉鍙互鎺ュ彈鎴栨嫆缁?
            user_email = context.get("user_email") if context else None
            if user_email != invitation.invitee_email:
                return False, "Only the invitee can accept or decline the invitation"

        return True, ""

    async def update_invitation_state(self, db: AsyncSession, invitation: Any, new_state: str, user_id: str) -> None:
        """鏇存柊閭€璇风姸鎬?"""
        from app.models import InvitationStatus

        invitation.status = new_state

        # 璁剧疆鐩稿叧鏃堕棿鎴?
        if new_state == InvitationStatus.accepted.value:
            invitation.accepted_at = datetime.now(timezone.utc)
            invitation.invitee_id = user_id

        await db.commit()
        await db.refresh(invitation)

    async def execute_post_transition_actions(
        self,
        db: AsyncSession,
        invitation: Any,
        old_state: str,
        new_state: str,
        user_id: str,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """鎵ц鍚庣疆鎿嶄綔"""
        from app.models import InvitationStatus, ProjectMember

        try:
            # 濡傛灉閭€璇疯鎺ュ彈锛屽垱寤洪」鐩垚鍛樿褰?
            if new_state == InvitationStatus.accepted.value:
                member = ProjectMember(project_id=invitation.project_id, user_id=user_id, role=invitation.role)
                db.add(member)
                await db.commit()

                logger.info(f"Created project membership for user {user_id}")

            return {"success": True}

        except Exception as e:
            logger.error(f"Post-transition action failed: {e}")
            return {"success": False, "error": str(e)}


# ============================================================================
# 浠ｇ爜瀹℃煡娴佺▼妯℃澘
# ============================================================================


class CodeReviewPipelineTemplate(ABC):
    """
    浠ｇ爜瀹℃煡娴佺▼妯℃澘鏂规硶

    鍥哄畾娴佺▼锛?
    1. 瑙ｆ瀽diff鑾峰彇鍙樻洿鏂囦欢
    2. 鍒濆鍖栧鏌ョ粨鏋?
    3. 骞惰鍒嗘瀽姣忎釜鏂囦欢
    4. 鑱氬悎缁撴灉
    5. 鎵ц鏋舵瀯鍒嗘瀽
    6. 杩斿洖瀹℃煡缁撴灉
    """

    async def review_code_changes(self, diff_content: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        妯℃澘鏂规硶 - 瀹氫箟浠ｇ爜瀹℃煡娴佺▼

        Args:
            diff_content: Git diff鍐呭
            context: 瀹℃煡涓婁笅鏂?

        Returns:
            瀹℃煡缁撴灉
        """
        try:
            logger.info("Starting code review pipeline")

            # 姝ラ1: 瑙ｆ瀽diff鑾峰彇鍙樻洿鏂囦欢
            changed_files = await self.parse_diff_files(diff_content)
            if not changed_files:
                return {"success": False, "error": "No changed files found"}

            # 姝ラ2: 鍒濆鍖栧鏌ョ粨鏋?
            review_result = self.initialize_review_result(changed_files, context)

            # 姝ラ3: 骞惰鍒嗘瀽姣忎釜鏂囦欢
            file_analyses = await self.analyze_files_parallel(changed_files, context)

            # 姝ラ4: 鑱氬悎缁撴灉
            aggregated_result = await self.aggregate_file_results(file_analyses, review_result)

            # 姝ラ5: 鎵ц鏋舵瀯鍒嗘瀽
            architecture_analysis = await self.perform_architecture_analysis(changed_files, aggregated_result, context)

            # 姝ラ6: 鏋勫缓鏈€缁堢粨鏋?
            final_result = await self.build_final_result(aggregated_result, architecture_analysis, context)

            logger.info("Code review pipeline completed successfully")
            return final_result

        except Exception as e:
            logger.error(f"Code review pipeline failed: {e}")
            return {"success": False, "error": f"Review failed: {str(e)}"}

    # 鎶借薄鏂规硶 - 瀛愮被蹇呴』瀹炵幇
    @abstractmethod
    async def parse_diff_files(self, diff_content: str) -> list[dict[str, Any]]:
        """瑙ｆ瀽diff鏂囦欢"""
        pass

    @abstractmethod
    async def analyze_single_file(self, file_info: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """鍒嗘瀽鍗曚釜鏂囦欢"""
        pass

    @abstractmethod
    async def perform_architecture_analysis(
        self, changed_files: list[dict[str, Any]], file_results: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """鎵ц鏋舵瀯鍒嗘瀽"""
        pass

    # 鍙€夌殑閽╁瓙鏂规硶 - 瀛愮被鍙互閲嶅啓
    def initialize_review_result(
        self, changed_files: list[dict[str, Any]], context: dict[str, Any]
    ) -> dict[str, Any]:
        """鍒濆鍖栧鏌ョ粨鏋?"""
        return {"total_files": len(changed_files), "files_analyzed": 0, "issues": [], "suggestions": [], "metrics": {}}

    async def analyze_files_parallel(
        self, changed_files: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """骞惰鍒嗘瀽鏂囦欢"""
        tasks = [self.analyze_single_file(file_info, context) for file_info in changed_files]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def aggregate_file_results(
        self, file_analyses: list[dict[str, Any]], review_result: dict[str, Any]
    ) -> dict[str, Any]:
        """鑱氬悎鏂囦欢鍒嗘瀽缁撴灉"""
        all_issues = []
        all_suggestions = []

        for analysis in file_analyses:
            if isinstance(analysis, dict) and not isinstance(analysis, Exception):
                all_issues.extend(analysis.get("issues", []))
                all_suggestions.extend(analysis.get("suggestions", []))

        review_result["issues"] = all_issues
        review_result["suggestions"] = all_suggestions
        review_result["files_analyzed"] = len([a for a in file_analyses if not isinstance(a, Exception)])

        return review_result

    async def build_final_result(
        self, aggregated_result: dict[str, Any], architecture_analysis: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """鏋勫缓鏈€缁堢粨鏋?"""
        return {
            "success": True,
            "summary": {
                "total_files": aggregated_result["total_files"],
                "files_analyzed": aggregated_result["files_analyzed"],
                "total_issues": len(aggregated_result["issues"]),
                "total_suggestions": len(aggregated_result["suggestions"]),
            },
            "file_analysis": aggregated_result,
            "architecture_analysis": architecture_analysis,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ============================================================================
# 閫氱敤涓氬姟娴佺▼妯℃澘
# ============================================================================


class BusinessProcessTemplate(ABC):
    """
    閫氱敤涓氬姟娴佺▼妯℃澘

    鎻愪緵鏍囧噯鐨勪笟鍔℃祦绋嬫鏋讹細
    1. 杈撳叆楠岃瘉
    2. 鏉冮檺妫€鏌?
    3. 涓氬姟閫昏緫鎵ц
    4. 缁撴灉澶勭悊
    5. 瀹¤鏃ュ織璁板綍
    """

    async def execute_process(
        self, db: AsyncSession, input_data: dict[str, Any], user_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        妯℃澘鏂规硶 - 瀹氫箟涓氬姟娴佺▼

        Args:
            db: 鏁版嵁搴撲細璇?
            input_data: 杈撳叆鏁版嵁
            user_id: 鐢ㄦ埛ID
            context: 棰濆涓婁笅鏂?

        Returns:
            澶勭悊缁撴灉
        """
        process_name = self.get_process_name()

        try:
            logger.info(f"Starting business process: {process_name}")

            # 姝ラ1: 杈撳叆楠岃瘉
            validation_result = await self.validate_input(input_data, user_id, context)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}

            # 姝ラ2: 鏉冮檺妫€鏌?
            permission_result = await self.check_permissions(db, input_data, user_id, context)
            if not permission_result["allowed"]:
                return {"success": False, "error": permission_result["reason"]}

            # 姝ラ3: 鎵ц涓氬姟閫昏緫
            business_result = await self.execute_business_logic(db, input_data, user_id, context)
            if not business_result["success"]:
                return business_result

            # 姝ラ4: 澶勭悊缁撴灉
            processed_result = await self.process_result(db, business_result, user_id, context)

            # 姝ラ5: 璁板綍瀹¤鏃ュ織
            await self.log_process_execution(db, process_name, input_data, processed_result, user_id, context)

            logger.info(f"Business process completed: {process_name}")
            return processed_result

        except Exception as e:
            logger.error(f"Business process failed: {process_name} - {e}")
            await db.rollback()

            # 璁板綍澶辫触鐨勫璁℃棩蹇?
            await self.log_process_failure(db, process_name, input_data, str(e), user_id, context)

            return {"success": False, "error": f"Process failed: {str(e)}"}

    # 鎶借薄鏂规硶 - 瀛愮被蹇呴』瀹炵幇
    @abstractmethod
    def get_process_name(self) -> str:
        """鑾峰彇娴佺▼鍚嶇О"""
        pass

    @abstractmethod
    async def validate_input(
        self, input_data: dict[str, Any], user_id: str, context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """楠岃瘉杈撳叆鏁版嵁"""
        pass

    @abstractmethod
    async def check_permissions(
        self, db: AsyncSession, input_data: dict[str, Any], user_id: str, context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """妫€鏌ユ潈闄?"""
        pass

    @abstractmethod
    async def execute_business_logic(
        self, db: AsyncSession, input_data: dict[str, Any], user_id: str, context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """鎵ц涓氬姟閫昏緫"""
        pass

    # 鍙€夌殑閽╁瓙鏂规硶 - 瀛愮被鍙互閲嶅啓
    async def process_result(
        self, db: AsyncSession, business_result: dict[str, Any], user_id: str, context: dict[str, Any] | None
    ) -> dict[str, Any]:
        """澶勭悊缁撴灉"""
        return business_result

    async def log_process_execution(
        self,
        db: AsyncSession,
        process_name: str,
        input_data: dict[str, Any],
        result: dict[str, Any],
        user_id: str,
        context: dict[str, Any] | None,
    ) -> None:
        """璁板綍娴佺▼鎵ц瀹¤鏃ュ織"""
        from app.core.audit_service import UnifiedAuditService

        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action="business_process",
            entity_type=process_name,
            success=result.get("success", False),
            changes={"input": input_data, "result": result, "context": context or {}},
        )

    async def log_process_failure(
        self,
        db: AsyncSession,
        process_name: str,
        input_data: dict[str, Any],
        error: str,
        user_id: str,
        context: dict[str, Any] | None,
    ) -> None:
        """璁板綍娴佺▼澶辫触瀹¤鏃ュ織"""
        from app.core.audit_service import UnifiedAuditService

        await UnifiedAuditService.log_action(
            db=db,
            user_id=user_id,
            action="business_process",
            entity_type=process_name,
            success=False,
            changes={"input": input_data, "error": error, "context": context or {}},
        )


