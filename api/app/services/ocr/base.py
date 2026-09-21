"""The engine seam.

Engines produce **geometry and text**. They do not produce meaning. An engine hands back
blocks - some of which are tables - and the pipeline decides what the columns mean and
what the rows say.

That split is the whole reason a 0.9B model can be swapped for a text-layer reader, or
for whatever wins the next benchmark, without touching the JSON contract, the vocabulary
layer, or any of the three storage layers. It is what the ``engine`` and
``engine_version`` columns on ``core.attachment_extractions`` exist to record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["ExtractionEngine", "RawBlock", "RawDocument", "RawPage"]


@dataclass(slots=True)
class RawBlock:
    """One layout block as the engine saw it.

    Attributes:
        label: The engine's own block type - ``table``, ``text``, ``title``, ``image``.
            Engine vocabulary, deliberately not normalised here.
        content: Recognised content. HTML for tables, plain text otherwise.
        bbox: ``(x0, y0, x1, y1)`` in the engine's own coordinate space, which is why
            :class:`RawPage` carries the page size needed to normalise it.
        order: Reading order within the page, when the engine reports one.
        score: Engine confidence for this block, when reported.
    """

    label: str
    content: str
    bbox: tuple[float, float, float, float] | None = None
    order: int | None = None
    score: float | None = None


@dataclass(slots=True)
class RawPage:
    """One page of blocks, plus the page size its coordinates are expressed in.

    ``width`` and ``height`` are what make normalised bounding boxes possible, and so
    what makes click-to-highlight on the verification screen work regardless of the zoom
    the viewer renders at.
    """

    page_number: int
    width: float
    height: float
    blocks: list[RawBlock] = field(default_factory=list)


@dataclass(slots=True)
class RawDocument:
    """Everything one engine extracted from one file, before any interpretation."""

    source_path: Path
    engine: str
    engine_version: str
    pages: list[RawPage] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        """Number of pages the engine returned."""
        return len(self.pages)


@runtime_checkable
class ExtractionEngine(Protocol):
    """What the pipeline requires of any engine.

    Implementations must be safe to construct without loading a model, so that importing
    the package does not pull in heavyweight dependencies. Load lazily inside
    :meth:`extract`.
    """

    name: str
    version: str

    def extract(self, path: Path) -> RawDocument:
        """Read one document.

        Args:
            path: The file to read. PDFs and images.

        Returns:
            Blocks and geometry, uninterpreted.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            RuntimeError: If the engine's backend is unavailable.
        """
        ...
