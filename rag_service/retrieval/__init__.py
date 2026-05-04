"""
Retrieval exports for rag_service.
"""

from .retrieve import retrieve_candidate_chunks
from .neighbor_expand import expand_context_with_neighbors

__all__ = ["retrieve_candidate_chunks",
           "expand_context_with_neighbors"]