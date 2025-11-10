"""
Test script for Git Repository API endpoints
This script tests the CRUD operations for git repositories.
"""
import httpx
import json
import os
from typing import Optional


# Configuration
BASE_URL = "http://localhost:8080"
API_TOKEN = os.getenv("API_TOKEN", "test_token")
REGION = "cn"  # Can be cn, global, or fj


class GitRepositoryAPITester:
    def __init__(self, base_url: str, api_token: str, region: str = "cn"):
        self.base_url = f"{base_url}/{region}/git-repository"
        self.region = region
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        self.test_repo_name = "test-repo-api-test"
    
    def test_create_repository(self) -> Optional[int]:
        """Test creating a new git repository"""
        print("\n=== Testing Create Repository ===")
        
        data = {
            "name": self.test_repo_name,
            "region": self.region,
            "web_url": "https://github.com/test/test-repo",
            "https_url": "https://github.com/test/test-repo.git",
            "ssh_url": "git@github.com:test/test-repo.git",
            "type": "public",
            "token": "test_token_12345",
            "username": "testuser"
        }
        
        try:
            response = httpx.post(
                f"{self.base_url}/create",
                json=data,
                headers=self.headers,
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("retcode") == 0 and result.get("data"):
                    repo_id = result["data"].get("id")
                    print(f"✓ Repository created successfully with ID: {repo_id}")
                    return repo_id
                else:
                    print(f"✗ Failed to create repository: {result.get('message')}")
            else:
                print(f"✗ HTTP Error: {response.status_code}")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        return None
    
    def test_get_all_repositories(self):
        """Test getting all repositories"""
        print("\n=== Testing Get All Repositories ===")
        
        try:
            response = httpx.get(
                f"{self.base_url}/all",
                headers=self.headers,
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            
            if response.status_code == 200 and result.get("retcode") == 0:
                repos = result.get("data", [])
                print(f"✓ Successfully fetched {len(repos)} repositories")
                return True
            else:
                print(f"✗ Failed to get repositories")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        return False
    
    def test_get_repository_by_name(self):
        """Test getting a specific repository by name"""
        print(f"\n=== Testing Get Repository by Name ({self.test_repo_name}) ===")
        
        try:
            response = httpx.get(
                f"{self.base_url}/all?name={self.test_repo_name}",
                headers=self.headers,
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            
            if response.status_code == 200 and result.get("retcode") == 0:
                repos = result.get("data", [])
                if len(repos) == 1 and repos[0].get("name") == self.test_repo_name:
                    print(f"✓ Successfully fetched repository by name")
                    return True
                else:
                    print(f"✗ Expected 1 repository with name '{self.test_repo_name}', got {len(repos)}")
            else:
                print(f"✗ Failed to get repository by name")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        return False
    
    def test_get_nonexistent_repository_by_name(self):
        """Test getting a non-existent repository by name (should return 404)"""
        print(f"\n=== Testing Get Non-existent Repository by Name ===")
        
        try:
            response = httpx.get(
                f"{self.base_url}/all?name=nonexistent-repo-that-does-not-exist",
                headers=self.headers,
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            
            if response.status_code == 404:
                print(f"✓ Correctly returned 404 for non-existent repository")
                return True
            else:
                print(f"✗ Expected 404, got {response.status_code}")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        return False
    
    def test_update_repository_by_id(self, repo_id: int):
        """Test updating a repository by ID"""
        print(f"\n=== Testing Update Repository by ID ({repo_id}) ===")
        
        data = {
            "web_url": "https://github.com/test/updated-repo",
            "type": "private"
        }
        
        try:
            response = httpx.put(
                f"{self.base_url}/update?repo_id={repo_id}",
                json=data,
                headers=self.headers,
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("retcode") == 0:
                    print(f"✓ Repository updated successfully")
                    return True
            print(f"✗ Failed to update repository")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        return False
    
    def test_update_repository_by_name(self):
        """Test updating a repository by name"""
        print(f"\n=== Testing Update Repository by Name ({self.test_repo_name}) ===")
        
        data = {
            "ssh_url": "git@github.com:test/updated-repo.git",
            "token": "updated_token_67890",
            "username": "updateduser"
        }
        
        try:
            response = httpx.put(
                f"{self.base_url}/update?name={self.test_repo_name}",
                json=data,
                headers=self.headers,
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("retcode") == 0:
                    print(f"✓ Repository updated successfully")
                    return True
            print(f"✗ Failed to update repository")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        return False
    
    def test_delete_repository_by_id(self, repo_id: int):
        """Test deleting a repository by ID"""
        print(f"\n=== Testing Delete Repository by ID ({repo_id}) ===")
        
        try:
            response = httpx.delete(
                f"{self.base_url}/delete?repo_id={repo_id}",
                headers=self.headers,
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("retcode") == 0:
                    print(f"✓ Repository deleted successfully")
                    return True
            print(f"✗ Failed to delete repository")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        return False
    
    def test_delete_repository_by_name(self):
        """Test deleting a repository by name"""
        print(f"\n=== Testing Delete Repository by Name ({self.test_repo_name}) ===")
        
        try:
            response = httpx.delete(
                f"{self.base_url}/delete?name={self.test_repo_name}",
                headers=self.headers,
                timeout=10.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("retcode") == 0:
                    print(f"✓ Repository deleted successfully")
                    return True
            print(f"✗ Failed to delete repository")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("=" * 60)
        print("Git Repository API Test Suite")
        print("=" * 60)
        
        # Test 1: Create repository
        repo_id = self.test_create_repository()
        if not repo_id:
            print("\n⚠ Cannot continue tests without a created repository")
            return
        
        # Test 2: Get all repositories
        self.test_get_all_repositories()
        
        # Test 3: Get repository by name (NEW TEST)
        self.test_get_repository_by_name()
        
        # Test 4: Get non-existent repository by name (NEW TEST)
        self.test_get_nonexistent_repository_by_name()
        
        # Test 5: Update by ID
        self.test_update_repository_by_id(repo_id)
        
        # Test 6: Update by name
        self.test_update_repository_by_name()
        
        # Test 7: Get all again to verify updates
        self.test_get_all_repositories()
        
        # Test 8: Delete by ID (or name if you want to test that instead)
        # Uncomment one of the following:
        self.test_delete_repository_by_id(repo_id)
        # self.test_delete_repository_by_name()
        
        # Verify deletion
        self.test_get_all_repositories()
        
        print("\n" + "=" * 60)
        print("Test Suite Complete")
        print("=" * 60)


if __name__ == "__main__":
    tester = GitRepositoryAPITester(BASE_URL, API_TOKEN, REGION)
    tester.run_all_tests()
