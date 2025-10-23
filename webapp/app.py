from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, abort, render_template, request
from markupsafe import Markup
from markdown import markdown as md_to_html

from . import config
from .document_index import SimpleSearchIndex, discover_documents, build_tree, Document


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    # Discover documents and build index at startup
    documents: List[Document] = discover_documents()
    search_index = SimpleSearchIndex(documents)
    tree = build_tree(documents)
    relpath_to_doc: Dict[str, Document] = {d.relative_path: d for d in documents}

    @app.context_processor
    def inject_globals():
        return {
            "docs_root": str(config.DOCS_ROOT),
            "total_docs": len(documents),
        }

    @app.route("/")
    def index():
        # Optional: focus on a specific subpath via query param
        focus_path = request.args.get("path", "").strip("/")
        return render_template(
            "index.html",
            tree=tree,
            focus_path=focus_path,
        )

    @app.route("/view/<path:relpath>")
    def view_file(relpath: str):
        normalized = relpath.strip("/")
        doc = relpath_to_doc.get(normalized)
        if not doc:
            abort(404)

        html = md_to_html(
            doc.content,
            extensions=[
                "fenced_code",
                "tables",
                "toc",
                "admonition",
                "codehilite",
                "sane_lists",
                "smarty",
            ],
            extension_configs={
                "codehilite": {
                    "linenums": False,
                    "guess_lang": True,
                    "pygments_style": "default",
                },
                "toc": {"permalink": True},
            },
            output_format="html5",
        )

        return render_template(
            "view.html",
            relpath=normalized,
            title=doc.title,
            tree=tree,
            content=Markup(html),
        )

    @app.route("/search")
    def search():
        query = request.args.get("q", "").strip()
        results = search_index.search(query, limit=100) if query else []
        return render_template("search.html", query=query, results=results)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
