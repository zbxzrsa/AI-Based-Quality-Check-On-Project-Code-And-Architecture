"""
Load testing script using Locust
"""
from locust import HttpUser, task, between
import json
import random
import os
from dotenv import load_dotenv

load_dotenv()

# Load test credentials from environment variables
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "TestPassword123!")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "AdminPassword123!")


class AICodeReviewUser(HttpUser):
    """Simulated user for load testing"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Login when user starts"""
        self.login()
    
    def login(self):
        """Authenticate user"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": f"test.user.{random.randint(1, 1000)}@example.com",
            "password": TEST_USER_PASSWORD
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        else:
            # Register if login fails
            self.client.post("/api/v1/auth/register", json={
                "email": f"test.user.{random.randint(1, 10000)}@example.com",
                "password": TEST_USER_PASSWORD,
                "full_name": "Test User"
            })
            self.login()
    
    @task(10)
    def list_projects(self):
        """List projects (most common operation)"""
        self.client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(5)
    def get_project(self):
        """Get single project details"""
        # Assume projects with IDs 1-100 exist
        project_id = random.randint(1, 100)
        self.client.get(
            f"/api/v1/projects/{project_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(8)
    def list_pull_requests(self):
        """List pull requests for a project"""
        project_id = random.randint(1, 100)
        self.client.get(
            f"/api/v1/projects/{project_id}/pulls",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(3)
    def get_pr_analysis(self):
        """Get PR analysis results"""
        pr_id = random.randint(1, 1000)
        self.client.get(
            f"/api/v1/pulls/{pr_id}/review-results",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(2)
    def create_project(self):
        """Create new project (less common)"""
        self.client.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "name": f"test-project-{random.randint(1, 10000)}",
                "description": "Test project for load testing",
                "github_repo_url": "https://github.com/test/repo",
                "language": "Python"
            }
        )
    
    @task(1)
    def sync_project(self):
        """Sync project with GitHub (rare operation)"""
        project_id = random.randint(1, 100)
        self.client.post(
            f"/api/v1/projects/{project_id}/sync",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(4)
    def health_check(self):
        """Health check endpoint"""
        self.client.get("/api/v1/health")


class AdminUser(HttpUser):
    """Admin user with different usage patterns"""
    
    wait_time = between(5, 15)
    weight = 1  # 10% of users are admins
    
    def on_start(self):
        """Login as admin"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "admin@example.com",
            "password": TEST_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
    
    @task(5)
    def view_audit_logs(self):
        """View audit logs"""
        self.client.get(
            "/api/v1/audit/logs?limit=50",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(3)
    def list_users(self):
        """List all users"""
        self.client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(2)
    def get_system_metrics(self):
        """Get system metrics"""
        self.client.get(
            "/metrics",
            headers={"Authorization": f"Bearer {self.token}"}
        )


# Run with:
# locust -f load_test.py --host=http://localhost:8000 --users=1000 --spawn-rate=50
