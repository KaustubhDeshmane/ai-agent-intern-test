import re
from pathlib import Path
from typing import List
from src.models import DocumentMetadata, Chunk
from src.rag.document_parser import parse_document_file


def chunk_document(filepath: Path) -> List[Chunk]:
    """
    Chunks a Markdown document by headings (H1, H2, H3), preserving metadata.
    """
    metadata, body = parse_document_file(filepath)
    filename = filepath.name
    
    # Split by headings starting with #, ##, or ###
    lines = body.splitlines()
    chunks: List[Chunk] = []
    
    current_heading = f"# {metadata.title}"
    current_lines: List[str] = []
    chunk_index = 0
    
    def save_chunk(heading: str, lines_list: List[str]):
        nonlocal chunk_index
        text = "\n".join(lines_list).strip()
        if text:
            chunk_id = f"{metadata.document_id}_{chunk_index}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=metadata.document_id,
                    filename=filename,
                    title=metadata.title,
                    heading=heading,
                    content=text,
                    metadata=metadata,
                )
            )
            chunk_index += 1

    for line in lines:
        if line.startswith("#"):
            # If we already accumulated lines, save existing chunk
            if current_lines:
                save_chunk(current_heading, current_lines)
                current_lines = []
            current_heading = line.strip()
        else:
            current_lines.append(line)
            
    if current_lines:
        save_chunk(current_heading, current_lines)

    return chunks


def load_and_chunk_all(knowledge_base_dir: Path) -> List[Chunk]:
    """Loads and chunks all markdown files in the given directory."""
    all_chunks: List[Chunk] = []
    for filepath in sorted(knowledge_base_dir.glob("*.md")):
        all_chunks.extend(chunk_document(filepath))
    return all_chunks
