import os
import time
import logging
import hashlib
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.connectors.local_connector import LocalConnector
from app.ingestion.pipeline import IngestionPipeline

logger = logging.getLogger(__name__)

class DocumentFileHandler(FileSystemEventHandler):
    """
    Event handler that triggers ingestion on creation/modification of files,
    and deletion of vector/graph nodes on file removal.
    """

    def __init__(self, pipeline: IngestionPipeline, connector: LocalConnector):
        super().__init__()
        self.pipeline = pipeline
        self.connector = connector

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_file_event(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_file_event(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        
        # Calculate the document ID matching LocalConnector's hashing format
        abs_path = os.path.abspath(event.src_path)
        doc_id = f"local_{hashlib.md5(abs_path.encode('utf-8')).hexdigest()}"
        logger.info(f"File watcher detected deletion of: {abs_path}. Triggering removal of doc '{doc_id}'...")
        
        try:
            self.pipeline.delete_document(doc_id)
        except Exception as e:
            logger.error(f"File watcher failed to process deletion for {abs_path}: {str(e)}")

    def _handle_file_event(self, file_path: str):
        abs_path = os.path.abspath(file_path)
        _, ext = os.path.splitext(abs_path)
        if ext.lower() not in [".md", ".txt", ".pdf"]:
            return

        logger.info(f"File watcher detected change/creation of: {abs_path}. Processing...")
        
        # Prevent double trigger by verifying the file actually exists and is readable
        # sometimes modifications trigger during file-write operations
        time.sleep(0.5)
        if not os.path.exists(abs_path):
            return

        try:
            doc = self.connector._process_file(abs_path)
            if doc:
                self.pipeline.ingest_document(doc)
            else:
                logger.debug(f"File watcher: file {abs_path} returned empty document. Skipping ingestion.")
        except Exception as e:
            logger.error(f"File watcher failed to process file {abs_path}: {str(e)}")


class LocalFolderWatcher:
    """
    Background observer that monitors a local folder for real-time document additions/modifications.
    """

    def __init__(self):
        self.pipeline = IngestionPipeline()
        self.connector = LocalConnector()
        self.observer = None

    def start(self, path: str):
        """
        Starts watching the specified folder in a background thread.
        """
        if self.observer is not None:
            logger.warning("Watcher observer is already running.")
            return

        abs_watch_path = os.path.abspath(path)
        if not os.path.exists(abs_watch_path):
            logger.error(f"Cannot start watcher: Watch directory path '{abs_watch_path}' does not exist.")
            return

        logger.info(f"Initializing local directory watchdog observer for: '{abs_watch_path}'...")
        event_handler = DocumentFileHandler(self.pipeline, self.connector)
        
        self.observer = Observer()
        self.observer.schedule(event_handler, abs_watch_path, recursive=True)
        self.observer.start()
        logger.info("Local folder watcher started successfully in a background thread.")

    def stop(self):
        """
        Stops the observer background thread.
        """
        if self.observer:
            logger.info("Stopping local folder watcher...")
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Local folder watcher stopped.")
            self.pipeline.close()
