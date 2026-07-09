# Google Calendar Connector Specification

The **Google Calendar Connector** integrates with the Google Calendar API using Google client libraries (`google-api-python-client`, `google-auth-oauthlib`) to fetch scheduled meetings, discussions, and details (description, attendees) and format them into unified `Document` models.

---

## Configuration & OAuth Scopes
The connector reuses the shared Google credentials from `backend/token.json` (authenticated in `google_auth.py` with the `https://www.googleapis.com/auth/calendar.readonly` scope). No separate login flow is needed if Gmail OAuth has already run.

---

## Ingested Entities & Mapping

The connector retrieves events from the user's `'primary'` calendar (typically filtered by time or text keyword search):

### Calendar Event mapping to Document:
* **Title**: The event's `summary` (e.g., "Sprint Planning" or "Architecture Review").
* **Content**: Formatted representation of meeting metadata and notes:
  ```markdown
  Event: <summary>
  Organizer: <organizer email>
  Time: <start_time> to <end_time> (UTC)
  Location: <location / Google Meet link>
  
  ## Attendees
  - John Doe <john@example.com> (Accepted)
  - Alice Smith <alice@example.com> (Needs Action)
  
  ## Description
  <meeting description / agenda / Google Meet transcript notes>
  ```
* **Timestamp**: The event's **Start Time** (parsed as a timezone-aware UTC datetime). This is crucial for temporal alignment since decisions occur during the meeting.
* **Author**: The event organizer's email address.
* **Metadata**:
  * `event_id`: Google Calendar event identifier.
  * `attendees`: List of attendee emails and their RSVP response status.
  * `location`: Venue or web conference link.
  * `status`: e.g. `"confirmed"`, `"tentative"`, `"cancelled"`.
  * `html_link`: Direct link to open the event in the Google Calendar web UI.
  * `type`: `"meeting"`

---

## Identity Resolution Data
The connector gathers the email addresses of the organizer and all attendees. When the Graph Builder runs, it creates `Person` nodes for these emails and links them with `ATTENDED` relationships to the meeting. It resolves these emails against Gmail senders and GitHub authors to compile a holistic view of team collaboration.
