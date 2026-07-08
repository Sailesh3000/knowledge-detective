import os
import hashlib
import getpass
import logging
from datetime import datetime, timezone
from typing import List, Optional
from app.connectors.base import BaseConnector
from app.models.document import Document, SourceType

# Setup logger
logger = logging.getLogger(__name__)

class LocalConnector(BaseConnector):
    """
    Ingests local documents (.md, .txt, .pdf) from a directory path.
    """

    def __init__(self, default_author: Optional[str] = None):
        # Default author to current OS user or fallback
        self.default_author = default_author or getpass.getuser() or "Local User"

    def fetch_documents(self, directory_path: str) -> List[Document]:
        """
        Recursively scan a directory for supported file types and convert them to Documents.
        """
        documents = []
        if not os.path.exists(directory_path):
            logger.error(f"Directory path does not exist: {directory_path}")
            return documents

        if os.path.isfile(directory_path):
            # Process single file if path points to a file
            doc = self._process_file(directory_path)
            if doc:
                documents.append(doc)
            return documents

        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Ignore hidden files/folders (like .git, .venv)
                if any(part.startswith('.') for part in file_path.split(os.sep)):
                    continue
                
                doc = self._process_file(file_path)
                if doc:
                    documents.append(doc)

        logger.info(f"Successfully processed {len(documents)} files from {directory_path}")
        return documents

    def _process_file(self, file_path: str) -> Optional[Document]:
        abs_path = os.path.abspath(file_path)
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # Check supported file types
        if ext not in [".md", ".txt", ".pdf"]:
            return None

        try:
            # File statistics
            stat = os.stat(abs_path)
            # Create timezone-aware datetime for modification time
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            file_size = stat.st_size

            # Title is the file name
            title = os.path.basename(abs_path)

            # Generate stable ID from absolute path
            doc_id = f"local_{hashlib.md5(abs_path.encode('utf-8')).hexdigest()}"

            # Extract content based on extension
            content = ""
            if ext in [".md", ".txt"]:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            elif ext == ".pdf":
                content = self._extract_pdf_text(abs_path)

            # Format file path as file:// URL for Windows compatibility (replace backslashes)
            normalized_path = abs_path.replace(os.sep, "/")
            url = f"file:///{normalized_path}"

            # If content is empty/whitespace only, skip
            if not content.strip():
                return None

            return Document(
                id=doc_id,
                source=SourceType.LOCAL,
                title=title,
                content=content,
                url=url,
                timestamp=mtime,
                author=self.default_author,
                metadata={
                    "file_path": abs_path,
                    "file_size": file_size,
                    "file_type": ext,
                    "folder_depth": len(abs_path.split(os.sep)) - len(os.getcwd().split(os.sep))
                }
            )

        except Exception as e:
            logger.error(f"Error processing file {abs_path}: {str(e)}")
            return None

    def _extract_pdf_text(self, file_path: str) -> str:
        """
        Extract text from a PDF file using pypdf.
        """
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n--- Page Break ---\n\n".join(text_parts)
        except ImportError:
            logger.warning("pypdf library not installed. PDF parsing skipped.")
            return f"[PDF raw placeholder for {os.path.basename(file_path)}]"
        except Exception as e:
            logger.error(f"Failed to extract PDF text from {file_path}: {str(e)}")
            return ""
