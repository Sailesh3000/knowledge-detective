import logging
from datetime import datetime, timezone
from typing import List, Optional
from github import Github, GithubException
from app.connectors.base import BaseConnector
from app.models.document import Document, SourceType
from app.config import settings

logger = logging.getLogger(__name__)

class GitHubConnector(BaseConnector):
    """
    Ingests repository issues, pull requests, and commits using PyGithub.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        if self.token:
            self.github_client = Github(self.token)
            logger.info("GitHub client initialized with personal access token.")
        else:
            self.github_client = Github()
            logger.warning("GitHub client initialized without credentials (rate limits will apply).")

    def fetch_documents(self, repo_name: str, limit: int = 30) -> List[Document]:
        """
        Fetch issues, PRs, and commits from the specified repository.
        repo_name format: "owner/repo" (e.g. "Sailesh3000/knowledge-detective")
        """
        documents = []
        try:
            repo = self.github_client.get_repo(repo_name)
            logger.info(f"Connected to repository: {repo_name}")
            
            # 1. Fetch Issues (ignoring pull requests)
            logger.info("Fetching issues...")
            issues_count = 0
            for issue in repo.get_issues(state="all"):
                if issues_count >= limit:
                    break
                # PyGithub issues include PRs; filter out PRs
                if issue.pull_request:
                    continue
                
                doc = self._process_issue(issue)
                if doc:
                    documents.append(doc)
                    issues_count += 1
            logger.info(f"Processed {issues_count} issues.")

            # 2. Fetch Pull Requests
            logger.info("Fetching pull requests...")
            prs_count = 0
            for pr in repo.get_pulls(state="all"):
                if prs_count >= limit:
                    break
                
                doc = self._process_pr(pr)
                if doc:
                    documents.append(doc)
                    prs_count += 1
            logger.info(f"Processed {prs_count} pull requests.")

            # 3. Fetch Commits
            logger.info("Fetching commits...")
            commits_count = 0
            for commit in repo.get_commits():
                if commits_count >= limit:
                    break
                
                doc = self._process_commit(commit, repo_name)
                if doc:
                    documents.append(doc)
                    commits_count += 1
            logger.info(f"Processed {commits_count} commits.")

        except GithubException as ge:
            logger.error(f"GitHub API Error: {ge.status} - {ge.data.get('message', str(ge))}")
        except Exception as e:
            logger.error(f"Failed to fetch data from GitHub repo {repo_name}: {str(e)}")
            
        return documents

    def _process_issue(self, issue) -> Optional[Document]:
        try:
            # Build content with description and comments
            content_parts = [
                f"# Issue Description\n{issue.body or 'No description provided.'}"
            ]
            
            # Fetch comments
            comments = issue.get_comments()
            if comments.totalCount > 0:
                content_parts.append("\n## Discussion Thread")
                for comment in comments:
                    created_at_str = comment.created_at.replace(tzinfo=timezone.utc).isoformat()
                    content_parts.append(
                        f"### Comment by @{comment.user.login} ({created_at_str})\n{comment.body}"
                    )
            
            content = "\n\n".join(content_parts)
            created_at = issue.created_at.replace(tzinfo=timezone.utc)

            metadata = {
                "issue_number": issue.number,
                "state": issue.state,
                "labels": [label.name for label in issue.labels],
                "html_url": issue.html_url,
                "type": "issue",
                "comments_count": comments.totalCount
            }

            return Document(
                id=f"github_issue_{issue.id}",
                source=SourceType.GITHUB,
                title=f"[Issue #{issue.number}] {issue.title}",
                content=content,
                url=issue.html_url,
                timestamp=created_at,
                author=issue.user.login,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error processing issue #{issue.number}: {str(e)}")
            return None

    def _process_pr(self, pr) -> Optional[Document]:
        try:
            # Build content with PR details
            content_parts = [
                f"# Pull Request Description\n{pr.body or 'No description provided.'}"
            ]
            
            # Fetch list of changed files
            files = pr.get_files()
            if files.totalCount > 0:
                content_parts.append("\n## Files Changed")
                for f in files:
                    content_parts.append(f"- {f.filename} (+{f.additions}, -{f.deletions})")

            # Fetch issue comments (general discussion comments)
            issue_comments = pr.get_issue_comments()
            # Fetch review comments (inline code comments)
            review_comments = pr.get_review_comments()
            
            if issue_comments.totalCount > 0 or review_comments.totalCount > 0:
                content_parts.append("\n## Discussion & Reviews")
                
                for comment in issue_comments:
                    created_at_str = comment.created_at.replace(tzinfo=timezone.utc).isoformat()
                    content_parts.append(
                        f"### Comment by @{comment.user.login} ({created_at_str})\n{comment.body}"
                    )
                
                for comment in review_comments:
                    created_at_str = comment.created_at.replace(tzinfo=timezone.utc).isoformat()
                    content_parts.append(
                        f"### Review Comment by @{comment.user.login} on `{comment.path}` ({created_at_str})\n{comment.body}"
                    )
                    
            content = "\n\n".join(content_parts)
            created_at = pr.created_at.replace(tzinfo=timezone.utc)
            
            state = "merged" if pr.merged else pr.state

            metadata = {
                "pr_number": pr.number,
                "state": state,
                "html_url": pr.html_url,
                "type": "pull_request",
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files_count": pr.changed_files
            }

            return Document(
                id=f"github_pr_{pr.id}",
                source=SourceType.GITHUB,
                title=f"[PR #{pr.number}] {pr.title}",
                content=content,
                url=pr.html_url,
                timestamp=created_at,
                author=pr.user.login,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error processing PR #{pr.number}: {str(e)}")
            return None

    def _process_commit(self, commit, repo_name: str) -> Optional[Document]:
        try:
            # Gather commit message
            message = commit.commit.message
            first_line = message.split("\n")[0]
            
            # Commit files
            changed_files = [f.filename for f in commit.files]
            files_str = "\n".join([f"- {f}" for f in changed_files])
            
            content_parts = [
                f"# Commit Message\n{message}",
                f"\n## Files Modified\n{files_str}" if changed_files else ""
            ]
            content = "\n\n".join(content_parts)
            
            # Author information
            author_login = "unknown"
            author_email = ""
            if commit.author:
                author_login = commit.author.login
            elif commit.commit.author:
                author_login = commit.commit.author.name
                author_email = commit.commit.author.email
            
            # Timestamp (commit date)
            commit_date = commit.commit.author.date.replace(tzinfo=timezone.utc)
            html_url = f"https://github.com/{repo_name}/commit/{commit.sha}"

            metadata = {
                "sha": commit.sha,
                "html_url": html_url,
                "type": "commit",
                "author_email": author_email,
                "changed_files": changed_files
            }

            return Document(
                id=f"github_commit_{commit.sha}",
                source=SourceType.GITHUB,
                title=f"[Commit {commit.sha[:7]}] {first_line}",
                content=content,
                url=html_url,
                timestamp=commit_date,
                author=author_login,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error processing commit {commit.sha[:7]}: {str(e)}")
            return None
