"""Draw the workflow graph: python -m scripts.draw_graph

Writes two files to docs/:
- workflow_graph.md: the graph as a Mermaid diagram. GitHub shows it as a picture, and you can paste the
  code block into https://mermaid.live to see it or download a PNG.
- workflow_graph.png: the same graph as a picture, drawn by the mermaid.ink web service.
  Only the graph's shape (its node names) is sent there, never any patient data.

Solid arrows always happen; dotted arrows are choices made while the request runs.
"""

from pathlib import Path

from app.graph.builder import GRAPH

DOCS = Path(__file__).parent.parent / "docs"


def main() -> None:
    graph = GRAPH.get_graph()

    markdown_file = DOCS / "workflow_graph.md"
    markdown_file.write_text(
        "# Workflow graph\n\nMade by `python -m scripts.draw_graph` from app/graph/builder.py.\n\n"
        f"```mermaid\n{graph.draw_mermaid()}```\n",
        encoding="utf-8",
    )
    print(f"Wrote {markdown_file}")

    png_file = DOCS / "workflow_graph.png"
    try:
        graph.draw_mermaid_png(output_file_path=str(png_file))
    except ValueError as error:  # mermaid.ink could not be reached
        reason = type(error.__cause__).__name__ if error.__cause__ else error
        print(f"Could not draw {png_file.name}: mermaid.ink could not be reached ({reason}).")
        print("The Mermaid diagram above has the same graph.")
        return
    print(f"Wrote {png_file}")


if __name__ == "__main__":
    main()
