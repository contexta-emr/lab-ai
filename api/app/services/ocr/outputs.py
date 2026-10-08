"""Write an extraction to disk, named the same way whoever ran it.

The CLI and the UI both save here, so a file read in the browser can be replayed with the
same tools as one read from the command line.
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import RawBlock, RawDocument, RawPage
from .contracts import Extraction

__all__ = ["read_raw", "write_extraction", "write_raw"]


def write_raw(raw: RawDocument, out_dir: Path, source: Path) -> Path:
    """Write the engine's blocks verbatim, before any interpretation.

    When a column role comes out wrong, the question is always the same: did the engine
    see the grid we think it saw? This answers it without re-running a model that takes
    minutes per page. It is also what lets a pipeline fix be replayed against a real
    document in milliseconds.

    Returns:
        ``out_dir/<source stem>.<ENGINE>.raw.json``.
    """
    destination = out_dir / f"{source.stem}.{raw.engine}.raw.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "engine": raw.engine,
        "engine_version": raw.engine_version,
        "source": raw.source_path.name,
        "pages": [
            {
                "page_number": p.page_number,
                "width": p.width,
                "height": p.height,
                "blocks": [
                    {
                        "label": b.label,
                        "order": b.order,
                        "score": b.score,
                        "bbox": list(b.bbox) if b.bbox else None,
                        "content": b.content,
                    }
                    for b in p.blocks
                ],
            }
            for p in raw.pages
        ],
    }
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return destination


def write_extraction(
    extraction: Extraction, out_dir: Path, source: Path, *, engine: str, indent: int = 2
) -> Path:
    """Write the extraction JSON.

    The engine is in the name because comparing two engines on one document is the whole
    point of having a swappable engine - without it the second run silently destroys the
    first, which is exactly what happened once.

    Returns:
        ``out_dir/<source stem>.<ENGINE>.extraction.json``.
    """
    destination = out_dir / f"{source.stem}.{engine}.extraction.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(extraction.to_json(indent=indent), encoding="utf-8")
    return destination


def read_raw(path: Path) -> RawDocument:
    """Rebuild a RawDocument from a dump write_raw produced.

    The other half of the trade write_raw describes. Once the engine's blocks
    are on disk, every later pipeline change is measured against the real 300
    documents in seconds instead of forty minutes and the cost of reading them
    again - so a change can be tried, measured and thrown away, which is not
    true when each measurement is billed per page.

    Taken from tools/score_corpus.py:from_raw_dump in the idp workspace, which
    is where this round trip was first used.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return RawDocument(
        source_path=Path(data.get("source") or path.name),
        engine=data.get("engine", ""),
        engine_version=data.get("engine_version", ""),
        pages=[
            RawPage(
                page_number=page["page_number"],
                width=page["width"],
                height=page["height"],
                blocks=[
                    RawBlock(
                        label=block["label"],
                        content=block["content"],
                        bbox=tuple(block["bbox"]) if block.get("bbox") else None,
                        order=block["order"],
                        score=block["score"],
                    )
                    for block in page["blocks"]
                ],
            )
            for page in data.get("pages", [])
        ],
    )
