import re
from pathlib import Path
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import KNOWLEDGE_BASE_DIR
from src.models import Chunk
from src.rag.chunker import load_and_chunk_all
from src.rag.precedence import filter_authoritative_chunks


# General domain paraphrase mapping for standard e-commerce customer support vocabulary.
DOMAIN_PARAPHRASE_MAP = [
    (r"\b(?:send|take|give|ship)\s+(?:it\s+)?back\b", "return policy standard return window calendar days"),
    (r"\b(?:how long|how much time|return window|time frame|days to return|return window)\b", "return policy standard return window calendar days 30 days"),
    (r"\b(?:toronto|vancouver|montreal|calgary|ottawa|quebec|ontario|alberta|bc)\b", "canada international shipping supported destinations"),
    (r"\b(?:london|berlin|paris|tokyo|sydney|germany|uk|france|australia|japan)\b", "international shipping unsupported destination"),
    (r"\b(?:damaged|broken|defective|faulty|ripped|torn|wrong item|wrong size)\b", "damaged wrong items replacement claim"),
    (r"\b(?:dishwasher|hand\s*wash|wash|clean|tumbler care)\b", "breeze tumbler product care cleaning instructions"),
]


def expand_paraphrased_query(query: str) -> str:
    """
    Expands natural paraphrases to canonical domain terminology for improved retrieval.
    """
    query_lower = query.lower()
    expanded_terms = [query]
    
    for pattern, canonical_terms in DOMAIN_PARAPHRASE_MAP:
        if re.search(pattern, query_lower):
            expanded_terms.append(canonical_terms)
            
    return " ".join(expanded_terms)


class KnowledgeBaseRetriever:
    """
    Metadata-aware, TF-IDF + Cosine similarity retriever for Aster & Row Knowledge Base.
    Supports natural language query paraphrase expansion and domain boosting.
    """
    def __init__(self, kb_dir: Path = KNOWLEDGE_BASE_DIR):
        self.kb_dir = kb_dir
        self.all_chunks: List[Chunk] = load_and_chunk_all(kb_dir)
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 3),
            sublinear_tf=True,
            strip_accents="unicode"
        )
        
        # Prepare text representations for indexing
        self.corpus = [
            f"{c.title} {c.heading} {c.content}" for c in self.all_chunks
        ]
        if self.corpus:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        else:
            self.tfidf_matrix = None

    def retrieve(
        self, query: str, top_k: int = 5, allow_legacy: bool = False
    ) -> List[Chunk]:
        """
        Retrieves top_k chunks matching the query, respecting metadata precedence rules.
        """
        if not self.all_chunks or self.tfidf_matrix is None:
            return []

        # Expand natural paraphrases to canonical concepts
        expanded_query = expand_paraphrased_query(query)
        
        # Transform query
        query_vec = self.vectorizer.transform([expanded_query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Score and rank chunks
        scored_chunks: List[Chunk] = []
        query_lower = query.lower()

        for idx, chunk in enumerate(self.all_chunks):
            base_score = float(similarities[idx])
            
            # Additional domain topic matching boost
            boost = 0.0
            content_lower = chunk.content.lower()
            title_lower = chunk.title.lower()
            heading_lower = chunk.heading.lower()
            
            if "trailplus" in query_lower and "trailplus" in (title_lower + heading_lower + content_lower):
                boost += 0.3
            if "tumbler" in query_lower or "breeze" in query_lower:
                if "breeze" in title_lower or "tumbler" in content_lower:
                    boost += 0.3
            if "warranty" in query_lower and "warranty" in title_lower:
                boost += 0.3
            if "60 days" in query_lower or "migration" in query_lower:
                if "migration" in title_lower or "scratchpad" in content_lower:
                    boost += 0.4

            final_score = base_score + boost
            c_copy = chunk.model_copy()
            c_copy.score = round(final_score, 4)
            scored_chunks.append(c_copy)

        # Sort by final score descending
        scored_chunks.sort(key=lambda x: x.score, reverse=True)

        # Filter by metadata authority unless allow_legacy is True
        if not allow_legacy and not ("legacy" in query_lower or "2024" in query_lower or "before april" in query_lower):
            authoritative_chunks = filter_authoritative_chunks(scored_chunks, allow_legacy=False)
        else:
            authoritative_chunks = scored_chunks

        # Return top_k with score > 0.05
        results = [c for c in authoritative_chunks if c.score > 0.05][:top_k]
        return results
