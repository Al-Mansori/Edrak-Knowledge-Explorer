# main.py
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Your index utilities (from the file you shared)
from index import (
    build_or_load_index,
    build_or_load_kg_index_from_markdown,
    build_or_load_kg_index_from_markdown_file,
    get_query_engine,        # used only if you want to restrict by file on the vector side
)

load_dotenv()  # picks up GOOGLE_API_KEY, etc.


def print_response(resp):
    """Pretty-print a LlamaIndex response object or plain string."""
    print("\n=== Answer ===")
    # Some query engines return a Response object, others a string
    if hasattr(resp, "response"):
        print(resp.response)
    else:
        print(str(resp))

    # If the hybrid/vector side produced retriever sources, show them
    if hasattr(resp, "source_nodes") and resp.source_nodes:
        print("\n=== Sources (Vector) ===")
        for s in resp.source_nodes:
            preview = s.node.get_content()[:160].replace("\n", " ")
            score = getattr(s, "score", 0.0)
            meta = s.metadata or {}
            print(
                f"- {meta.get('content_list_file','?')} | {meta.get('source_type')} "
                f"| p{meta.get('page_idx')} | score={score:.2f}"
            )
            print(f"  {preview}…")


def build_hybrid_engine(args):
    """Build/load vector + KG, return a hybrid query engine."""
    # Build/load vector
    # vec_index = build_or_load_index(
    #     content_list_dir=args.content_list_dir,
    #     persist_dir=args.persist_dir,
    #     rebuild=args.rebuild,
    # )

    # engine = get_query_engine(
    #     index=vec_index,
    #     top_k=5,
    #     response_mode="compact",
    # )
    
    kg_index = build_or_load_kg_index_from_markdown(
        summary_dir="publications_dataset/summary",
        persist_dir="./.kg_from_summary",
        rebuild=False,
        max_triplets_per_chunk=10,
    )
    
    # kg_engine = kg_index.get_networkx_graph()
    
    # print(kg_engine)

    # List all markdown files in the summary directory
    summary_dir = "publications_dataset/summary"
    md_files = [str(f) for f in Path(summary_dir).glob("*.md")]

    # Build a KG index for all markdown files
    kg_index = build_or_load_kg_index_from_markdown(
        summary_dir=summary_dir,
        persist_dir="./.kg_from_summary",
        rebuild=False,
        max_triplets_per_chunk=10,
    )
    kg_engine = kg_index.get_networkx_graph()
    print(kg_engine)
    for f in md_files:
        
        kg_index = build_or_load_kg_index_from_markdown_file(
            md_path=f,
            rebuild=False,
            max_triplets_per_chunk=10,
        )
        print (f"{f}: {kg_index.get_networkx_graph()}")
    
    # Hybrid engine (Vector + KG)
    return None, None
    return engine, vec_index  # return vec_index too, in case we want file-level filters later


def run_example(engine, example_query: str):
    """Run one example query before the loop (optional but handy)."""
    if not example_query:
        return
    print(f"\n>> Example query:\n{example_query}")
    resp = engine.query(example_query)
    print_response(resp)


def repl(engine, vec_index, only_file: str = ""):
    """
    Simple Q&A loop.
    Tips shown:
      - type ':q' or ':exit' to quit
      - type ':only <file.json>' to restrict (vector-side) retrieval to a single content_list file
      - type ':clear' to remove the restriction
    """
    current_only = only_file or None
    print("\nEnter questions (':q' to quit).")
    if current_only:
        print(f"[Filter] Only retrieving from file: {current_only}")

    while True:
        try:
            q = input("\n>>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            return

        if not q:
            continue
        if q in (":q", ":quit", ":exit"):
            print("Bye!")
            return
        if q.startswith(":only "):
            current_only = q.split(" ", 1)[1].strip() or None
            if current_only:
                print(f"[Filter] Now restricting to: {current_only}")
            else:
                print("[Filter] Cleared (no restriction).")
            continue
        if q == ":clear":
            current_only = None
            print("[Filter] Cleared (no restriction).")
            continue

        # If we have an active file restriction, re-make a vector-only engine with filters
        # and still query the hybrid afterward. This pattern gives you a second pass of
        # vector-filtered grounding if you want. Most folks just use hybrid directly.
        if current_only:
            vec_only_engine = get_query_engine(
                vec_index,
                top_k=5,
                response_mode="compact",
                include_sources=True,
                only_file=current_only,
            )
            # Ask both: filtered vector first (quick peek), then the hybrid as the main answer
            print("\n[Vector-only preview (restricted)]")
            vec_resp = vec_only_engine.query(q)
            print_response(vec_resp)

        # Hybrid is our main answerer
        resp = engine.query(q)
        print_response(resp)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Hybrid (Vector + KG) Q&A over content_list JSON datasets."
    )
    parser.add_argument(
        "--content_list_dir",
        type=str,
        default='publications_dataset/content_list/',
        help="Path to dataset/content_list directory",
    )
    parser.add_argument(
        "--persist_dir",
        type=str,
        default="./.llamaindex_store",
        help="Directory to persist indexes",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild of the vector index",
    )
    parser.add_argument(
        "--rebuild_kg",
        action="store_true",
        help="Force rebuild of the KG index",
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=5,
        help="Top-K for vector retrieval in the hybrid engine",
    )
    parser.add_argument(
        "--max_triplets_per_chunk",
        type=int,
        default=5,
        help="KG: max number of triplets to extract per chunk",
    )
    parser.add_argument(
        "--example",
        type=str,
        default="Give a concise overview of the key entities and how they relate.",
        help="An example query to run once before entering the loop",
    )
    parser.add_argument(
        "--only_file",
        type=str,
        default="",
        help="(Optional) Start the REPL with a retrieval restriction to this content_list file",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Sanity check
    if not Path(args.content_list_dir).exists():
        print(f"[ERROR] content_list path not found: {args.content_list_dir}")
        sys.exit(1)

    # Build hybrid engine
    engine, vec_index = build_hybrid_engine(args)

    
    # One example query (optional but nice for smoke testing)
    # run_example(engine, args.example)

    # Interactive loop
    # repl(engine, vec_index, only_file=args.only_file)


if __name__ == "__main__":
    main()
