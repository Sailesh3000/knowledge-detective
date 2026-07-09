import base64
import email.utils
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from app.connectors.base import BaseConnector
from app.connectors.google_auth import get_google_credentials
from app.models.document import Document, SourceType

logger = logging.getLogger(__name__)

class GmailConnector(BaseConnector):
    """
    Ingests email messages from Gmail using Google Gmail API.
    """

    def __init__(self):
        self.creds = get_google_credentials()
        if self.creds:
            self.service = build("gmail", "v1", credentials=self.creds)
            logger.info("Gmail API service initialized successfully.")
        else:
            self.service = None
            logger.error("Gmail API service failed to initialize due to missing/invalid credentials.")

    def fetch_documents(self, query: str = "", limit: int = 30) -> List[Document]:
        """
        Fetch emails matching a Gmail query (e.g., 'subject:"Knowledge Detective"' or empty for recent).
        """
        documents = []
        if not self.service:
            logger.error("Gmail service is not initialized. Skipping fetch.")
            return documents

        try:
            logger.info(f"Listing messages with query: '{query}'")
            # List messages
            result = self.service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
            messages = result.get("messages", [])

            if not messages:
                logger.info("No Gmail messages found matching the query.")
                return documents

            logger.info(f"Found {len(messages)} messages. Fetching contents...")
            for msg_summary in messages:
                msg_id = msg_summary["id"]
                doc = self._fetch_message_detail(msg_id)
                if doc:
                    documents.append(doc)

            logger.info(f"Successfully processed {len(documents)} emails.")

        except Exception as e:
            logger.error(f"Failed to fetch emails from Gmail: {str(e)}")

        return documents

    def _fetch_message_detail(self, message_id: str) -> Optional[Document]:
        try:
            # Fetch message full payload
            message = self.service.users().messages().get(userId="me", id=message_id, format="full").execute()
            payload = message.get("payload", {})
            headers = payload.get("headers", [])

            # Parse headers
            headers_dict = {h["name"].lower(): h["value"] for h in headers}
            
            subject = headers_dict.get("subject", "(No Subject)")
            from_header = headers_dict.get("from", "")
            to_header = headers_dict.get("to", "")
            date_header = headers_dict.get("date", "")

            # Parse sender's email
            _, author_email = email.utils.parseaddr(from_header)
            if not author_email:
                author_email = from_header or "unknown@gmail.com"

            # Parse date to timezone-aware datetime
            try:
                timestamp = email.utils.parsedate_to_datetime(date_header)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except Exception as date_err:
                logger.warning(f"Could not parse date header '{date_header}': {str(date_err)}. Using current time.")
                timestamp = datetime.now(timezone.utc)

            # Extract body
            body = self._parse_body(payload)
            if not body:
                body = message.get("snippet", "(No content)")

            # Format full content structure
            content = (
                f"From: {from_header}\n"
                f"To: {to_header}\n"
                f"Date: {date_header}\n"
                f"Subject: {subject}\n\n"
                f"{body}"
            )

            # Web url link for threads
            thread_id = message.get("threadId", "")
            html_url = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}" if thread_id else None

            metadata = {
                "message_id": message_id,
                "thread_id": thread_id,
                "snippet": message.get("snippet", ""),
                "labels": message.get("labelIds", []),
                "type": "email"
            }

            return Document(
                id=f"gmail_{message_id}",
                source=SourceType.GMAIL,
                title=subject,
                content=content,
                url=html_url,
                timestamp=timestamp,
                author=author_email,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error fetching detail for message {message_id}: {str(e)}")
            return None

    def _parse_body(self, payload: Dict[str, Any]) -> str:
        """
        Recursively traverse email parts to find plain text body. Falls back to HTML if plain text isn't found.
        """
        body = ""
        mime_type = payload.get("mimeType", "")
        
        # Base64 decode utility
        def decode_part(part_data):
            try:
                # Base64url encoding uses - and _ instead of + and /
                decoded_bytes = base64.urlsafe_b64decode(part_data.encode("utf-8"))
                return decoded_bytes.decode("utf-8", errors="ignore")
            except Exception as e:
                logger.error(f"Failed to decode base64 email body: {str(e)}")
                return ""

        if mime_type.startswith("text/plain"):
            data = payload.get("body", {}).get("data", "")
            if data:
                return decode_part(data)
        
        # If multipart, traverse recursively
        parts = payload.get("parts", [])
        html_body = ""
        for part in parts:
            part_mime = part.get("mimeType", "")
            if part_mime.startswith("text/plain"):
                data = part.get("body", {}).get("data", "")
                if data:
                    return decode_part(data)
            elif part_mime.startswith("text/html"):
                data = part.get("body", {}).get("data", "")
                if data:
                    html_body = decode_part(data)
            elif part.get("parts"):
                # Nested parts
                sub_body = self._parse_body(part)
                if sub_body:
                    return sub_body

        # Fallback to HTML body (and strip basic tags if we can, or just keep it)
        if html_body:
            # Basic HTML tags stripping (to avoid bloated context)
            import re
            clean_text = re.sub(r"<[^>]+>", "", html_body)
            # Normalize whitespace
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            return clean_text

        return body
