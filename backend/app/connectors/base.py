from abc import ABC, abstractmethod
from typing import List
from app.models.document import Document

class BaseConnector(ABC):
    """
    Abstract Base Class for all data source connectors.
    Every connector must implement the fetch_documents method to ingest data.
    """

    @abstractmethod
    def fetch_documents(self, *args, **kwargs) -> List[Document]:
        """
        Fetch data from the source and convert it into unified Document models.
        """
        pass
