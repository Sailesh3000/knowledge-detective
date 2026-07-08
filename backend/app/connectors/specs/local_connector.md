# Local Folder Connector Specification

The **Local Folder Connector** is responsible for scanning directories on the local file system, extracting text content and system metadata from supported files, and converting them into a standardized `Document` format for our pipeline.

---

## Supported File Types
1. **Markdown (`.md`)**: Read as UTF-8 text. Useful for ingestion plan, build plan, personal notes, READMEs, etc.
2. **Text Files (`.txt`)**: Read as UTF-8 text.
3. **PDF Files (`.pdf`)**: Parsed using the `pypdf` library to extract raw text content page-by-page.
4. **JSON Files (`.json`)**: Loaded and parsed. If it's structured data (like synthetic email files or export files), it can be formatted into clean string representations or parsed dynamically.

---

## Metadata Mapping
Each file processed by the connector maps to the unified `Document` Pydantic model as follows:

| Document Field | Mapping Description | Example Value |
|----------------|---------------------|---------------|
| `id` | MD5 hash of the absolute file path (provides stability) | `a3f901c8...` |
| `source` | Set to `SourceType.LOCAL` | `SourceType.LOCAL` |
| `title` | File name (including extension) | `implementation-plan.md` |
| `content` | Full extracted text content of the file | `"# Knowledge Detective..."` |
| `url` | Local file path formatted as `file://` scheme | `file:///C:/knowledge-detective/plan.md` |
| `timestamp` | Modification time of the file (`mtime`) | `2026-07-08T18:41:46+05:30` |
| `author` | System file owner or a fallback default | `Sailesh` (or "Local User") |
| `metadata` | Dictionary containing: `file_path`, `file_size`, `file_type`, `folder_depth` | `{"file_size": 2048, "file_type": ".md"}` |

---

## Code Implementation Design
The class `LocalConnector` will inherit from a base connector interface and implement:
- `fetch_documents(directory_path: str) -> List[Document]`: Recursively crawls the target directory and processes matches.
- `_extract_pdf_text(file_path: str) -> str`: Helper function to extract text using `pypdf`.
- `_get_file_owner(file_path: str) -> str`: Helper to resolve local Windows file owner using system utilities or default to a configured developer name.
