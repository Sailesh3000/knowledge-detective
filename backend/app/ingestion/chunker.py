import re
from typing import List
from app.models.document import Document, DocumentChunk

def split_text_recursive(text: str, chunk_size: int = 1500, chunk_overlap: int = 150) -> List[str]:
    """
    Recursively splits text into chunks of at most chunk_size characters,
    attempting to split on paragraph, sentence, and space boundaries first.
    """
    if len(text) <= chunk_size:
        return [text]

    # Split characters/separators to try in order:
    # 1. Double newlines (paragraphs)
    # 2. Single newlines
    # 3. Sentence boundaries (. ? !)
    # 4. Spaces
    separators = ["\n\n", "\n", r"(?<=[.!?])\s+", " "]
    
    # Try to find a split point
    split_str = None
    for sep in separators:
        if sep == r"(?<=[.!?])\s+":
            splits = re.split(sep, text)
        else:
            splits = text.split(sep)
            
        if len(splits) > 1:
            # Check if splits help reduce chunk size
            # If every split item is as long as the original, it doesn't help
            split_str = sep
            break
            
    if split_str is None:
        # Hard split at chunk_size if no separator worked
        return [text[:chunk_size]] + split_text_recursive(text[chunk_size - chunk_overlap:], chunk_size, chunk_overlap)

    # Reconstruct chunks with overlap
    chunks = []
    current_chunk = []
    current_length = 0
    
    # We need to compile the regex for sentence boundary split if used
    is_regex = (split_str == r"(?<=[.!?])\s+")
    
    for part in (re.split(split_str, text) if is_regex else text.split(split_str)):
        part_len = len(part)
        
        # If a single part is larger than the chunk size, split it recursively
        if part_len > chunk_size:
            if current_chunk:
                join_sep = " " if is_regex or split_str == " " else (split_str if isinstance(split_str, str) else "\n")
                chunks.append(join_sep.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            sub_chunks = split_text_recursive(part, chunk_size, chunk_overlap)
            chunks.extend(sub_chunks[:-1])
            if sub_chunks:
                current_chunk = [sub_chunks[-1]]
                current_length = len(sub_chunks[-1])
            continue
            
        join_sep_len = 1 if is_regex or split_str == " " or split_str == "\n" else len(str(split_str))
        if current_length + part_len + (join_sep_len if current_chunk else 0) > chunk_size:
            # Emit current chunk
            join_sep = " " if is_regex or split_str == " " else (split_str if isinstance(split_str, str) else "\n")
            chunks.append(join_sep.join(current_chunk))
            
            # Start new chunk, incorporating overlap
            # Find the overlap from the end of the emitted chunk
            emitted_text = join_sep.join(current_chunk)
            overlap_text = emitted_text[-(chunk_overlap):] if len(emitted_text) > chunk_overlap else emitted_text
            
            current_chunk = [overlap_text, part] if overlap_text else [part]
            current_length = len(overlap_text) + part_len + (join_sep_len if overlap_text else 0)
        else:
            current_chunk.append(part)
            current_length += part_len + (join_sep_len if len(current_chunk) > 1 else 0)
            
    if current_chunk:
        join_sep = " " if is_regex or split_str == " " else (split_str if isinstance(split_str, str) else "\n")
        chunks.append(join_sep.join(current_chunk))
        
    return chunks

class Chunker:
    """
    Splits documents into overlapping chunks with unified metadata.
    """
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_document(self, doc: Document) -> List[DocumentChunk]:
        """
        Splits a Document into a list of DocumentChunks.
        """
        raw_chunks = split_text_recursive(doc.content, self.chunk_size, self.chunk_overlap)
        
        chunks = []
        for i, text in enumerate(raw_chunks):
            # Clean/strip text
            clean_text = text.strip()
            if not clean_text:
                continue
                
            chunk_id = f"{doc.id}_chunk_{i}"
            
            # Combine document metadata with chunk specific info
            chunk_metadata = doc.metadata.copy()
            chunk_metadata.update({
                "source": doc.source.value,
                "title": doc.title,
                "author": doc.author,
                "timestamp": doc.timestamp.isoformat(),
                "url": doc.url,
            })
            
            chunk = DocumentChunk(
                id=chunk_id,
                document_id=doc.id,
                content=clean_text,
                chunk_index=i,
                embedding=None,
                metadata=chunk_metadata
            )
            chunks.append(chunk)
            
        return chunks
