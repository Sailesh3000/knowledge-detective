# GitHub Connector Specification

The **GitHub Connector** connects to the GitHub REST API using `PyGithub` and ingests repository data, converting issues, pull requests, and commits into standardized `Document` models.

---

## Configuration & Credentials
The connector retrieves the personal access token from:
- `settings.GITHUB_TOKEN` or `GITHUB_TOKEN` env var.
- If no token is provided, the connector can fall back to public/unauthenticated requests (which are heavily rate-limited by GitHub to 60 requests/hour, compared to 5,000/hour for authenticated requests).

---

## Ingested Entities & Mapping

The connector fetches three types of entities from a target repository (`owner/name`):

### 1. GitHub Issues
* **Title**: `[Issue #<number>] <title>`
* **Content**: The main body of the issue, followed by an appended thread of all comments:
  ```markdown
  # Issue Description
  <issue body>
  
  ## Comment by @<username> (2026-07-09T10:00:00Z)
  <comment body>
  ```
* **Timestamp**: Issue creation time.
* **Author**: The GitHub username of the creator.
* **Metadata**:
  * `issue_number`: e.g. `42`
  * `state`: `"open"` or `"closed"`
  * `labels`: List of label names
  * `html_url`: Link to the issue on GitHub
  * `type`: `"issue"`

### 2. GitHub Pull Requests (PRs)
* **Title**: `[PR #<number>] <title>`
* **Content**: The main PR description, followed by comments, review comments, and lists of changed file names:
  ```markdown
  # Pull Request Description
  <pr body>
  
  ## Files Changed
  - path/to/file1.py
  - path/to/file2.py
  
  ## Review Comment by @<reviewer>
  <comment body>
  ```
* **Timestamp**: PR creation time.
* **Author**: GitHub username of the PR author.
* **Metadata**:
  * `pr_number`: e.g. `43`
  * `state`: `"open"`, `"closed"`, or `"merged"`
  * `html_url`: Link to the PR on GitHub
  * `type`: `"pull_request"`

### 3. Commits
* **Title**: `[Commit <sha>] <message first line>`
* **Content**: Full commit message, SHA, and list of changed files.
* **Timestamp**: Commit authoring date.
* **Author**: GitHub username of the committer (or email if username is unavailable).
* **Metadata**:
  * `sha`: Full git SHA
  * `html_url`: Link to the commit on GitHub
  * `type`: `"commit"`
  * `changed_files`: List of changed filenames

---

## Identity Resolution Data
To support the Knowledge Graph's identity resolution, the metadata for each document retains the raw email address and username of the author whenever available (e.g. git commit author email vs. GitHub issue username). This allows the Graph Builder later to link `user@example.com` and GitHub username `@user` to the same `Person` node.
