"""Person 3: curriculum data, knowledge graph and retrieval (RAG).

Public entry point for the rest of the backend: backend/services/curriculum.py.
Core code here uses only the Python standard library plus pydantic, so it runs
in the Docker image without new dependencies. Semantic search (sentence-
transformers) and PDF reading (pypdf) are optional extras.
"""
