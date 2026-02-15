"""
Git utilities for MCP agents
Handles branch management and commits for parallel development
"""
import subprocess
from typing import List, Optional


class GitManager:
    """Git operations for agent branches"""

    def __init__(self, branch: str, base_branch: str = "v2.0-desktop-build"):
        self.branch = branch
        self.base_branch = base_branch

    def create_branch(self) -> bool:
        """Create and checkout agent branch"""
        try:
            # Check if branch exists
            result = subprocess.run(
                ["git", "branch", "--list", self.branch],
                capture_output=True,
                text=True,
                check=False
            )

            if not result.stdout.strip():
                # Create branch from base
                subprocess.run(
                    ["git", "checkout", "-b", self.branch, self.base_branch],
                    check=True
                )
                return True
            else:
                # Switch to existing branch
                subprocess.run(["git", "checkout", self.branch], check=True)
                return False
        except subprocess.CalledProcessError as e:
            print(f"Error creating/switching branch: {e}")
            return False

    def commit(self, message: str, files: Optional[List[str]] = None) -> bool:
        """Commit changes on agent branch"""
        try:
            if files:
                subprocess.run(["git", "add"] + files, check=True)
            else:
                subprocess.run(["git", "add", "."], check=True)

            subprocess.run(["git", "commit", "-m", message], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error committing: {e}")
            return False

    def push(self) -> bool:
        """Push branch to remote"""
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", self.branch],
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error pushing: {e}")
            return False

    def get_status(self) -> str:
        """Get git status"""
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ""

    def get_current_branch(self) -> str:
        """Get current branch name"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def switch_to_base(self) -> bool:
        """Switch back to base branch"""
        try:
            subprocess.run(["git", "checkout", self.base_branch], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error switching to base branch: {e}")
            return False

    def merge_from(self, source_branch: str, message: str = None) -> bool:
        """Merge another branch into current branch"""
        try:
            if message:
                subprocess.run(
                    ["git", "merge", source_branch, "--no-ff", "-m", message],
                    check=True
                )
            else:
                subprocess.run(["git", "merge", source_branch], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error merging {source_branch}: {e}")
            return False
