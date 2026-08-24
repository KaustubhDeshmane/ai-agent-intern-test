import re
from pathlib import Path
from typing import Tuple, Dict, Any
from src.models import DocumentMetadata


def parse_front_matter(content: str) -> Tuple[DocumentMetadata, str]:
    """
    Parses YAML front matter from markdown document content.
    Returns (DocumentMetadata, body_text).
    """
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.search(pattern, content, re.DOTALL)
    
    metadata_dict: Dict[str, Any] = {
        "status": "active",
        "audience": "customer",
        "policy_authority": "official",
        "customer_answering": True,
    }
    
    body = content
    if match:
        yaml_text = match.group(1)
        body = match.group(2)
        
        for line in yaml_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            
            if val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
                
            metadata_dict[key] = val

    # Ensure required fields
    if "document_id" not in metadata_dict:
        metadata_dict["document_id"] = "UNKNOWN"
    if "title" not in metadata_dict:
        # Fallback title from H1 in body if present
        h1_match = re.search(r"^#\s+(.*)$", body, re.MULTILINE)
        metadata_dict["title"] = h1_match.group(1).strip() if h1_match else "Untitled"

    metadata = DocumentMetadata(**metadata_dict)
    return metadata, body.strip()


def parse_document_file(filepath: Path) -> Tuple[DocumentMetadata, str]:
    """Reads a file and parses its front-matter and content."""
    content = filepath.read_text(encoding="utf-8")
    return parse_front_matter(content)
