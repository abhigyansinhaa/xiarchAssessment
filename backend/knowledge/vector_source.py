import os
import re
import math
from typing import List, Dict, Any, Optional
from pathlib import Path
from backend.config import DOCS_DIR, CHROMA_DIR, OPENAI_API_KEY


class DocumentChunk:
    def __init__(self, doc_name: str, title: str, section: str, content: str):
        self.doc_name = doc_name
        self.title = title
        self.section = section
        self.content = content.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_name": self.doc_name,
            "title": self.title,
            "section": self.section,
            "content": self.content
        }


class VectorKnowledgeSource:
    """
    Vector search engine for HR documents.
    Supports ChromaDB vector indexing and includes an intelligent TF-IDF / vector
    similarity fallback engine so tests and offline runs never fail.
    """

    def __init__(self):
        self.source_name = "ChromaDB Vector Store (Policy & Guidelines Docs)"
        self.chunks: List[DocumentChunk] = []
        self._load_and_chunk_documents()
        self._init_chroma()

    def _load_and_chunk_documents(self):
        if not DOCS_DIR.exists():
            return

        for filepath in DOCS_DIR.glob("*.md"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()

                doc_title = filepath.stem.replace("_", " ").title()
                # Split by markdown headers ##
                sections = re.split(r'\n(?=##?\s)', text)
                for sec in sections:
                    lines = sec.strip().split("\n")
                    if not lines:
                        continue
                    first_line = lines[0].strip()
                    sec_title = re.sub(r'^#+\s*', '', first_line) if first_line.startswith("#") else doc_title
                    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else first_line

                    if body:
                        self.chunks.append(
                            DocumentChunk(
                                doc_name=filepath.name,
                                title=doc_title,
                                section=sec_title,
                                content=f"[{doc_title} - {sec_title}]\n{body}"
                            )
                        )
            except Exception as e:
                print(f"[VectorKnowledgeSource] Error reading {filepath}: {e}")

    def _init_chroma(self):
        self.chroma_client = None
        self.collection = None
        try:
            import chromadb
            from chromadb.config import Settings
            os.makedirs(CHROMA_DIR, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            self.collection = self.chroma_client.get_or_create_collection(
                name="xiarch_hr_policies",
                metadata={"hnsw:space": "cosine"}
            )
            # Index if empty
            if self.collection.count() == 0 and self.chunks:
                ids = [f"chunk_{i}" for i in range(len(self.chunks))]
                documents = [c.content for c in self.chunks]
                metadatas = [{"doc_name": c.doc_name, "section": c.section} for c in self.chunks]
                self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
                print(f"[VectorKnowledgeSource] ChromaDB indexed {len(self.chunks)} chunks.")
        except Exception as e:
            print(f"[VectorKnowledgeSource] ChromaDB initialization notice: {e}. Using fallback vector engine.")

    def _tfidf_vector_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Fast fallback TF-IDF cosine similarity search across chunks."""
        q_tokens = set(re.findall(r'\b[a-zA-Z0-9_]{3,}\b', query.lower()))
        if not q_tokens:
            return [c.to_dict() for c in self.chunks[:top_k]]

        scored = []
        for chunk in self.chunks:
            c_text = (chunk.title + " " + chunk.section + " " + chunk.content).lower()
            tokens = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', c_text)
            if not tokens:
                continue

            matches = sum(1 for t in tokens if t in q_tokens)
            # Give boost to title/section matches
            title_matches = sum(3 for t in q_tokens if t in chunk.title.lower() or t in chunk.section.lower())
            score = (matches + title_matches) / (math.sqrt(len(tokens)) + 1)

            if score > 0:
                res = chunk.to_dict()
                res["similarity_score"] = round(float(score), 4)
                scored.append((score, res))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def search_documents(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        # If ChromaDB collection exists and works, try it
        if self.collection is not None:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(top_k, len(self.chunks))
                )
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0] if "distances" in results else []

                formatted = []
                for i, doc in enumerate(docs):
                    meta = metas[i] if i < len(metas) else {}
                    score = 1.0 - (distances[i] if i < len(distances) else 0.5)
                    formatted.append({
                        "doc_name": meta.get("doc_name", "Policy Document"),
                        "section": meta.get("section", "General"),
                        "content": doc,
                        "similarity_score": round(float(score), 4)
                    })
                if formatted:
                    return formatted
            except Exception as e:
                print(f"[VectorKnowledgeSource] Chroma search query fallback: {e}")

        # Fallback to local vector/TF-IDF search
        return self._tfidf_vector_search(query, top_k=top_k)
