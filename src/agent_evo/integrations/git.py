"""Git 集成 / Git integration"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from agent_evo.models.config import GitConfig


class GitIntegration:
    """Git 操作封装 / Git operations wrapper"""
    
    def __init__(self, config: GitConfig, project_dir: Path):
        self.config = config
        self.project_dir = project_dir
        self._repo = None
    
    def _get_repo(self):
        """延迟初始化 Git 仓库 / Lazy-initialize Git repository"""
        if self._repo is None:
            try:
                import git
                self._repo = git.Repo(self.project_dir)
            except Exception as e:
                raise RuntimeError(f"无法初始化 Git 仓库 / Cannot initialize Git repo: {e}")
        return self._repo
    
    def create_branch(self, name: Optional[str] = None) -> str:
        """创建新分支 / Create new branch"""
        repo = self._get_repo()
        
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name = f"{self.config.pr_branch_prefix}-{timestamp}"
        
        # 创建并切换到新分支 / Create and checkout new branch
        new_branch = repo.create_head(name)
        new_branch.checkout()
        
        return name
    
    def commit(self, message: str, files: Optional[list[str]] = None) -> str:
        """提交更改 / Commit changes"""
        repo = self._get_repo()
        
        if files:
            repo.index.add(files)
        else:
            repo.index.add("*")
        
        commit = repo.index.commit(message)
        return commit.hexsha
    
    def push(self, branch: Optional[str] = None) -> None:
        """推送到远程 / Push to remote"""
        repo = self._get_repo()
        
        if branch is None:
            branch = repo.active_branch.name
        
        origin = repo.remote("origin")
        origin.push(branch)
    
    async def create_pr(
        self,
        title: str,
        body: str,
        changes: list[tuple[str, str]]  # [(文件路径, 新内容) / (file path, new content)]
    ) -> Optional[str]:
        """
        创建 PR / Create pull request
        
        Args:
            title: PR 标题 / PR title
            body: PR 描述 / PR description
            changes: 文件变更列表 / File change list
            
        Returns:
            PR URL（如果成功）/ PR URL (if successful)
        """
        try:
            # 1. 创建分支 / Create branch
            branch_name = self.create_branch()
            
            # 2. 应用变更 / Apply changes
            for file_path, content in changes:
                full_path = self.project_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
            
            # 3. 提交 / Commit
            files = [str(self.project_dir / f[0]) for f in changes]
            self.commit(f"[AgentEvo] {title}", files)
            
            # 4. 推送 / Push
            self.push(branch_name)
            
            # 5. 创建 PR（需要 GitHub API）/ Create PR (requires GitHub API)
            pr_url = await self._create_github_pr(title, body, branch_name)
            
            return pr_url
            
        except Exception as e:
            # 回滚到原分支 / Rollback to original branch
            repo = self._get_repo()
            repo.heads[self.config.pr_base_branch].checkout()
            raise RuntimeError(f"创建 PR 失败 / Failed to create PR: {e}")
    
    async def _create_github_pr(
        self,
        title: str,
        body: str,
        head_branch: str
    ) -> Optional[str]:
        """使用 GitHub API 创建 PR / Create PR using GitHub API"""
        import httpx
        
        # 获取仓库信息 / Get repository info
        repo = self._get_repo()
        remote_url = repo.remote("origin").url
        
        # 解析 owner/repo / Parse owner/repo
        if "github.com" in remote_url:
            # 支持 https 和 ssh 格式 / Support https and ssh formats
            if remote_url.startswith("git@"):
                # git@github.com:owner/repo.git
                parts = remote_url.split(":")[-1].replace(".git", "").split("/")
            else:
                # https://github.com/owner/repo.git
                parts = remote_url.replace(".git", "").split("/")[-2:]
            
            owner, repo_name = parts[0], parts[1]
        else:
            return None  # 非 GitHub 仓库 / Not a GitHub repository
        
        # GitHub Token
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            print("⚠ 未设置 GITHUB_TOKEN，无法自动创建 PR / GITHUB_TOKEN not set, cannot auto-create PR")
            print(f"  请手动创建 PR / Please create PR manually: {head_branch} -> {self.config.pr_base_branch}")
            return None
        
        # 创建 PR / Create PR
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={
                    "title": title,
                    "body": body,
                    "head": head_branch,
                    "base": self.config.pr_base_branch
                }
            )
            
            if response.status_code == 201:
                return response.json()["html_url"]
            else:
                raise RuntimeError(f"GitHub API 错误 / GitHub API error: {response.text}")
