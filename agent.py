"""Retrieval-augmented childhood cancer information assistant."""

from __future__ import annotations

import math
import os
import re
import argparse
from dataclasses import dataclass
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv(Path(__file__).resolve().with_name(".env"), override=False)


TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)?", re.IGNORECASE)
STOP_WORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "of", "on", "or", "the", "this",
    "to", "was", "what", "when", "where", "which", "who", "why", "with", "would",
}
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
MAX_CHUNK_CHARS = 1400
CHUNK_OVERLAP_CHARS = 180


@dataclass(frozen=True)
class SourceChunk:
    source: str
    text: str


class ChildhoodCancerAgent:
    """Retrieve local source passages and use an API-configured LLM to answer."""

    def __init__(self, data_dir: str | Path = "data", top_k: int = 5):
        self.data_dir = Path(data_dir)
        self.top_k = max(1, min(top_k, 10))
        self.chunks = self._load_chunks()
        self.document_frequency = self._document_frequencies()

    def _load_chunks(self) -> list[SourceChunk]:
        chunks = []
        for path in sorted(self.data_dir.glob("*.txt")):
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            first_line, _, body = text.partition("\n")
            source = first_line.removeprefix("Source: ").strip() if first_line.startswith("Source: ") else path.name
            chunks.extend(self._split_text(source, body or text))

        pdf_path = self.data_dir / "cancer_biomarkers.pdf"
        if pdf_path.is_file():
            try:
                from pypdf import PdfReader
            except ImportError:
                PdfReader = None
            if PdfReader is not None:
                reader = PdfReader(str(pdf_path))
                source = "https://www.cancer.org/content/dam/cancer-org/cancer-control/en/booklets-flyers/cancer-biomarkers.pdf"
                for page_number, page in enumerate(reader.pages, 1):
                    page_text = page.extract_text() or ""
                    chunks.extend(self._split_text(f"{source}#page={page_number}", page_text))
        return chunks

    @staticmethod
    def _split_text(source: str, text: str) -> list[SourceChunk]:
        normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        chunks = []
        start = 0
        while start < len(normalized):
            end = min(start + MAX_CHUNK_CHARS, len(normalized))
            if end < len(normalized):
                boundary = normalized.rfind("\n", start, end)
                if boundary > start + MAX_CHUNK_CHARS // 2:
                    end = boundary
            chunk_text = normalized[start:end].strip()
            if chunk_text:
                chunks.append(SourceChunk(source, chunk_text))
            if end >= len(normalized):
                break
            start = max(start + 1, end - CHUNK_OVERLAP_CHARS)
        return chunks

    def _document_frequencies(self) -> dict[str, int]:
        frequencies: dict[str, int] = {}
        for chunk in self.chunks:
            for token in set(TOKEN_PATTERN.findall(chunk.text.lower())):
                frequencies[token] = frequencies.get(token, 0) + 1
        return frequencies

    def retrieve(self, question: str) -> list[SourceChunk]:
        query_tokens = set(TOKEN_PATTERN.findall(question.lower())) - STOP_WORDS
        if not query_tokens:
            return []

        total_chunks = max(1, len(self.chunks))
        ranked = []
        for chunk in self.chunks:
            tokens = TOKEN_PATTERN.findall(chunk.text.lower())
            token_counts: dict[str, int] = {}
            for token in tokens:
                token_counts[token] = token_counts.get(token, 0) + 1
            score = sum(
                (1 + math.log(token_counts.get(token, 0)))
                * math.log(1 + total_chunks / (1 + self.document_frequency.get(token, 0)))
                for token in query_tokens
                if token in token_counts
            )
            matched_terms = sum(token in token_counts for token in query_tokens)
            if score > 0 and matched_terms / len(query_tokens) > 0.5:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in ranked[: self.top_k]]

    def answer(self, question: str) -> dict:
        question = question.strip()
        if not question:
            raise ValueError("Enter a question first.")
        if not self.chunks:
            raise RuntimeError("No source documents found. Run python ingest.py first.")
        matches = self.retrieve(question)
        if not matches:
            return {
                "answer": "I could not find relevant information in the ingested sources. Try a more specific question or ingest another trusted source.",
                "sources": [],
            }

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured. Set it in the environment before asking the LLM agent.")

        sources = list(dict.fromkeys(chunk.source for chunk in matches))
        source_ids = {source: f"S{index}" for index, source in enumerate(sources, 1)}
        context = "\n\n".join(
            f"[{source_ids[chunk.source]}] Source URL: {chunk.source}\n{chunk.text}"
            for chunk in matches
        )
        system_message = (
            "You are a careful educational assistant about childhood cancer. Answer only from the supplied source excerpts. "
            "Cite factual statements inline using the supplied [S1] style citations. If the excerpts do not answer the question, "
            "say so plainly. Do not diagnose, estimate an individual child's prognosis, or recommend a treatment. Encourage the user "
            "to discuss personal symptoms, test results, and treatment decisions with a qualified pediatric oncology team. Distinguish "
            "population statistics from individual outcomes and preserve dates and population caveats. This is educational information, "
            "not medical advice."
        )
        response = requests.post(
            os.getenv("OPENAI_API_URL", DEFAULT_API_URL),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Question: {question}\n\nSource excerpts:\n{context}"},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        answer_text = payload["choices"][0]["message"]["content"].strip()
        return {
            "answer": answer_text,
            "sources": [{"id": source_ids[source], "url": source} for source in sources],
        }


def main():
    parser = argparse.ArgumentParser(description="Ask the source-grounded childhood cancer assistant.")
    parser.add_argument("question", help="Question about the locally ingested sources")
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()
    result = ChildhoodCancerAgent(args.data_dir).answer(args.question)
    print(result["answer"])
    if result["sources"]:
        print("\nSources:")
        for source in result["sources"]:
            print("[{}] {}".format(source["id"], source["url"]))


if __name__ == "__main__":
    main()