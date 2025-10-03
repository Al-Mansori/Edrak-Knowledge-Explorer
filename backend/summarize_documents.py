#!/usr/bin/env python3
"""
Summarize Markdown publications with LlamaIndex + Google GenAI.

- Reads:  publications_dataset/markdown/ (recursively, .md only)
- Writes: publications_dataset/summary/ (mirrors structure, .md summaries)

Env:
  GOOGLE_API_KEY         (required)
  LLAMAINDEX_DEBUG=1     (optional)
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# LlamaIndex core
from llama_index.core import (
    Settings,
    Document,
    SummaryIndex,
    SimpleDirectoryReader,
)

# Google GenAI LLM for LlamaIndex
from llama_index.llms.google_genai import GoogleGenAI


# ----------------------------
# Defaults
# ----------------------------
DEFAULT_INPUT_DIR = "publications_dataset/markdown"
DEFAULT_OUTPUT_DIR = "publications_dataset/summary"
DEFAULT_MODEL = "models/gemini-2.5-flash"   # fast & cheap; use "models/gemini-1.5-pro" for higher quality
SYSTEM_PROMPT = """You are an expert scientific summarizer. 
Write concise, faithful, and useful summaries for researchers.
Prefer plain language, but keep important technical detail accurate.
If the text is not a research paper, still summarize clearly."""

USER_SUMMARY_INSTRUCTIONS = """Summarize the document for a technical audience.

Include (when present):
- TL;DR (2–4 sentences)
- Research question / objective
- Methods / data
- Key findings (bullet points)
- Limitations / uncertainties
- Notable figures/tables (describe briefly; do not invent)
- Practical implications
- 1–2 follow-up questions

Keep to ~1000 words. Use Markdown. Do not fabricate citations.
"""


# ----------------------------
# Helpers
# ----------------------------
def ensure_model(model_name: str):
    """Configure LlamaIndex to use Google GenAI."""
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("Missing GOOGLE_API_KEY in environment.")
    Settings.llm = GoogleGenAI(model=model_name)
    # You can also adjust global parsing/embedding here if you want:
    # from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
    # Settings.embed_model = GoogleGenAIEmbedding(model="models/text-embedding-004")


def load_markdown(input_dir: Path):
    """Load only .md files, recursively, as LlamaIndex Documents."""
    reader = SimpleDirectoryReader(
        input_dir=str(input_dir),
        recursive=True,
        required_exts=[".md"],
        filename_as_id=True,
    )
    return reader.load_data()


def summarize_document(doc: Document) -> str:
    """Summarize a single Document using SummaryIndex + tree summarize."""
    # Create a tiny index for this single document
    index = SummaryIndex.from_documents([doc])
    qe = index.as_query_engine(response_mode="tree_summarize", use_async=False)
    # The 'query' is our instruction to synthesize a high-quality summary.
    response = qe.query(USER_SUMMARY_INSTRUCTIONS)
    return str(response)


def write_summary(base_in: Path, base_out: Path, doc: Document, summary_md: str):
    """Mirror the input structure and write .md file with '-summary' suffix."""
    # Document.id_ is the filename if filename_as_id=True
    rel_path = Path(doc.doc_id) if doc.doc_id else Path(doc.metadata.get("file_name", "document.md"))
    # If doc_id is absolute, make it relative to input dir
    try:
        rel_path = rel_path.relative_to(base_in)
    except Exception:
        # fall back to relative name only
        rel_path = rel_path.name if rel_path.is_absolute() else rel_path

    # Ensure .md extension and add -summary suffix
    rel_path = Path(rel_path)
    stem = rel_path.stem
    out_rel = rel_path.with_name(f"{stem}-summary.md")

    out_path = base_out / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)

    header = f"# Summary: {stem}\n\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + summary_md.strip() + "\n")

    return out_path


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Summarize Markdown publications with LlamaIndex + Google GenAI.")
    parser.add_argument("--input", "-i", default=DEFAULT_INPUT_DIR, help="Input directory with Markdown files.")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory for summaries.")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help="Google GenAI model, e.g. models/gemini-1.5-pro")
    args = parser.parse_args()

    in_dir = Path(args.input).resolve()
    out_dir = Path(args.output).resolve()

    if not in_dir.exists():
        print(f"Input directory not found: {in_dir}", file=sys.stderr)
        sys.exit(1)

    ensure_model(args.model)

    docs: List[Document] = load_markdown(in_dir)
    if not docs:
        print(f"No Markdown files found under {in_dir}")
        return

    print(f"Found {len(docs)} file(s). Writing summaries to: {out_dir}\n")

    for i, doc in enumerate(docs, 1):
        name = doc.metadata.get("file_name", doc.doc_id) or f"doc_{i}"
        print(f"[{i}/{len(docs)}] Summarizing: {name} ...", end="", flush=True)
        try:
            summary_md = summarize_document(doc)
            out_path = write_summary(in_dir, out_dir, doc, summary_md)
            print(f" done -> {out_path}")
        except Exception as e:
            print(f"\n  ERROR on {name}: {e}", file=sys.stderr)

    print("\nAll set.")


if __name__ == "__main__":
    main()
