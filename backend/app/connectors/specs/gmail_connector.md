# Gmail Connector Specification

The **Gmail Connector** integrates with the Google Gmail API using Google client libraries (`google-api-python-client`, `google-auth-oauthlib`) to fetch messages from a user's mailbox, parse email threads, and format them into unified `Document` models.

---

## Google Cloud Project & OAuth Config
To authenticate, the connector requires:
1. An active GCP project with the **Gmail API** enabled.
2. An OAuth 2.0 Client ID of type **Desktop Application**.
3. The downloaded credentials file saved as `backend/credentials.json`.
4. On the first run, the connector launches a local browser window requesting consent. Once granted, it caches access/refresh tokens in `backend/token.json` for silent authentication thereafter.

---

## Ingested Entities & Mapping

The connector retrieves email messages based on a user-specified search query (e.g. `subject:"Knowledge Detective"`, `label:work`, or just recent emails):

### Email Message mapping to Document:
* **Title**: The email's `Subject` header.
* **Content**: The email body (plain text preferred, with HTML tags stripped if only HTML is available), formatted with headers:
  ```markdown
  From: <Sender Name/Email>
  To: <Recipient Emails>
  Date: <Date/Time>
  Subject: <Subject>
  
  <Body plain text>
  ```
* **Timestamp**: The `Date` header parsed as a timezone-aware UTC datetime.
* **Author**: The `From` header email address (e.g. `sailesh@example.com`).
* **Metadata**:
  * `thread_id`: Gmail thread identifier (critical for grouping conversations).
  * `message_id`: Raw RFC 2822 message ID.
  * `labels`: List of Gmail labels applied to this message (e.g., `INBOX`, `SENT`, `UNREAD`).
  * `snippet`: A brief text snippet of the email.
  * `type`: `"email"`
  * `html_url`: Direct link to open the thread in Gmail web UI: `https://mail.google.com/mail/u/0/#inbox/<thread_id>`

---

## Identity Resolution Data
The `author` field holds the raw email address parsed from the `From` header (e.g., `John Doe <john@example.com>` becomes `john@example.com` after sanitization). This email matches the committer/author emails retrieved by the GitHub connector, allowing the Graph Builder to resolve the user's multi-source identities.
