import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from googleapiclient.discovery import build
from app.connectors.base import BaseConnector
from app.connectors.google_auth import get_google_credentials
from app.models.document import Document, SourceType

logger = logging.getLogger(__name__)

class CalendarConnector(BaseConnector):
    """
    Ingests meeting events from Google Calendar using Google Calendar API.
    """

    def __init__(self):
        self.creds = get_google_credentials()
        if self.creds:
            self.service = build("calendar", "v3", credentials=self.creds)
            logger.info("Google Calendar API service initialized successfully.")
        else:
            self.service = None
            logger.error("Google Calendar API service failed to initialize due to missing/invalid credentials.")

    def fetch_documents(self, time_min: Optional[datetime] = None, limit: int = 30) -> List[Document]:
        """
        Fetch calendar events from the primary calendar.
        By default, fetches events starting from 30 days ago up to the limit.
        """
        documents = []
        if not self.service:
            logger.error("Google Calendar service is not initialized. Skipping fetch.")
            return documents

        # Default timeMin to 30 days ago if not provided
        if not time_min:
            time_min = datetime.now(timezone.utc) - timedelta(days=30)
            
        time_min_str = time_min.isoformat()

        try:
            logger.info(f"Listing primary calendar events starting from {time_min_str}")
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=time_min_str,
                maxResults=limit,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get("items", [])

            if not events:
                logger.info("No calendar events found.")
                return documents

            logger.info(f"Found {len(events)} events. Processing details...")
            for event in events:
                doc = self._process_event(event)
                if doc:
                    documents.append(doc)

            logger.info(f"Successfully processed {len(documents)} calendar events.")

        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {str(e)}")

        return documents

    def _process_event(self, event) -> Optional[Document]:
        try:
            summary = event.get("summary", "(No Title)")
            description = event.get("description", "No description provided.")
            location = event.get("location", "No location specified")
            html_link = event.get("htmlLink", "")
            event_id = event.get("id", "")

            # Start and end times (could be date only for all-day events)
            start = event.get("start", {})
            end = event.get("end", {})
            
            start_time_str = start.get("dateTime") or start.get("date", "")
            end_time_str = end.get("dateTime") or end.get("date", "")

            # Parse start time to timezone-aware datetime for document timestamp
            # Google dates are ISO 8601 strings
            try:
                if "T" in start_time_str:
                    timestamp = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                else:
                    # All day event, parse date only and set to UTC
                    timestamp = datetime.strptime(start_time_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception as time_err:
                logger.warning(f"Could not parse event time '{start_time_str}': {str(time_err)}. Using current time.")
                timestamp = datetime.now(timezone.utc)

            # Organizer
            organizer = event.get("organizer", {})
            organizer_email = organizer.get("email") or organizer.get("displayName") or "unknown@calendar.google.com"

            # Process attendees
            attendees_list = event.get("attendees", [])
            attendee_lines = []
            attendee_emails = []
            
            for att in attendees_list:
                email_addr = att.get("email", "")
                name = att.get("displayName", "")
                status = att.get("responseStatus", "needsAction")
                
                name_display = f"{name} " if name else ""
                attendee_lines.append(f"- {name_display}<{email_addr}> ({status.capitalize()})")
                if email_addr:
                    attendee_emails.append(email_addr)

            attendees_str = "\n".join(attendee_lines) if attendee_lines else "- No other attendees listed"

            # Format full content structure
            content = (
                f"Event: {summary}\n"
                f"Organizer: {organizer_email}\n"
                f"Time: {start_time_str} to {end_time_str} (UTC)\n"
                f"Location: {location}\n\n"
                f"## Attendees\n{attendees_str}\n\n"
                f"## Description\n{description}"
            )

            metadata = {
                "event_id": event_id,
                "location": location,
                "status": event.get("status", ""),
                "html_link": html_link,
                "attendees": attendee_emails,
                "type": "meeting"
            }

            return Document(
                id=f"calendar_{event_id}",
                source=SourceType.CALENDAR,
                title=summary,
                content=content,
                url=html_link or None,
                timestamp=timestamp,
                author=organizer_email,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error processing calendar event {event.get('id', 'unknown')}: {str(e)}")
            return None
