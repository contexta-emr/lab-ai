"""The extraction JSON contract.

This is the deliverable of step 1 and the seam the whole pipeline is built around.
It is **open-vocabulary**: there is no ``analyte_code``, no panel enum, and no canonical
vocabulary anywhere in this module. Every field is ``raw_`` and every value is a string.

The extractor does not know what a lab test is. It reads a table and reports what is
printed. Mapping printed labels onto canonical codes is a separate, later pass that is
allowed to fail without losing data - see `attachment-extraction-engine.md` sections 5
and 6.

Coordinates are **normalised fractions of the page** in ``[0, 1]``, origin top-left.
That sidesteps the coordinate-space mismatch between a model's rendered-pixel output and
a PDF crop box entirely: any viewer can multiply by whatever size it renders at.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Self

__all__ = [
    "BBox",
    "DocumentMeta",
    "Extraction",
    "Header",
    "Row",
    "Section",
    "UnparsedBlock",
]


@dataclass(frozen=True, slots=True)
class BBox:
    """A rectangle as fractions of page width and height, origin top-left.

    Attributes:
        x0: Left edge, 0.0 to 1.0.
        y0: Top edge, 0.0 to 1.0.
        x1: Right edge, 0.0 to 1.0.
        y1: Bottom edge, 0.0 to 1.0.
    """

    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_pixels(
        cls, box: tuple[float, float, float, float], width: float, height: float
    ) -> Self:
        """Normalise a pixel-space box against the rendered page size.

        Args:
            box: ``(x0, y0, x1, y1)`` in the coordinate space the engine reported.
            width: Rendered page width in the same space.
            height: Rendered page height in the same space.

        Returns:
            The same rectangle expressed as fractions of the page.

        Raises:
            ValueError: If width or height is not positive.
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"page size must be positive, got {width}x{height}")
        x0, y0, x1, y1 = box
        return cls(x0 / width, y0 / height, x1 / width, y1 / height)

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return the box as a plain tuple."""
        return (self.x0, self.y0, self.x1, self.y1)


@dataclass(slots=True)
class Row:
    """One printed line of a result grid, exactly as it appears on the page.

    Every field is the raw string from the document. Nothing is interpreted, converted,
    or matched against a vocabulary here.
    """

    row_index: int
    raw_label: str
    raw_value: str | None = None
    raw_unit: str | None = None
    raw_reference: str | None = None
    raw_flag: str | None = None
    # Labs print the assay method as a sub-line under the test. It changes what a
    # reference range means - "Creatinine (Jaffe)" and "Creatinine (enzymatic)" do not
    # share one - so it is folded onto the row rather than dropped or left as a row.
    raw_method: str | None = None
    page: int = 1
    bbox: BBox | None = None
    confidence: float | None = None


@dataclass(slots=True)
class Section:
    """A result grid, usually one panel.

    Attributes:
        printed_title: Whatever the lab printed above the grid, verbatim. This is the
            panel *hint* passed to ``fn_resolve_panel`` later - never a panel code.
        rows: The rows of the grid.
        column_roles: Which column index played which role, for auditing the inference.
        page: Page the grid started on.
        bbox: Bounds of the grid on that page.
    """

    printed_title: str | None = None
    rows: list[Row] = field(default_factory=list)
    column_roles: dict[int, str] = field(default_factory=dict)
    page: int = 1
    bbox: BBox | None = None


@dataclass(slots=True)
class Header:
    """Document-level fields printed outside the result grids.

    ``collected_at``, ``tested_at`` and ``reported_at`` are singled out because every
    longitudinal query orders by collection date; they become real columns downstream.
    Everything else the lab prints goes into ``raw_fields`` untouched.
    """

    lab_name: str | None = None
    lab_reference_no: str | None = None
    # Who the report is about. Promoted out of raw_fields because these are what link a
    # document to a patient record, and a lab that prints the name as a bare heading -
    # most of them - would otherwise leave it nowhere at all.
    #
    # Kept exactly as printed. Redaction is the PII layer's job on the way *out*; a step-1
    # extractor that masks on the way in cannot tell you whose report this is, which is
    # the one question it exists to answer.
    patient_name: str | None = None
    patient_age: str | None = None
    patient_sex: str | None = None
    patient_id: str | None = None
    referring_doctor: str | None = None
    collected_at: str | None = None
    tested_at: str | None = None
    reported_at: str | None = None
    # Parsed forms, added beside the printed text rather than replacing it. Absent when
    # the date could not be read unambiguously - a wrong date moves a result on a trend
    # line silently, which is worse than no date at all.
    collected_at_iso: str | None = None
    tested_at_iso: str | None = None
    reported_at_iso: str | None = None
    raw_fields: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class UnparsedBlock:
    """Text the extractor could not fit into the table model.

    The honesty clause. Footnotes, pathologist comments, method notes and column shapes
    nobody anticipated land here with coordinates rather than being discarded. An
    extractor that silently drops what it does not understand is how a report comes out
    looking complete while missing half its content.
    """

    page: int
    text: str
    bbox: BBox | None = None
    block_label: str | None = None


@dataclass(slots=True)
class DocumentMeta:
    """Which engine produced this extraction, and how confident it is overall."""

    engine: str
    engine_version: str
    source_name: str
    page_count: int = 0
    document_type: str | None = None
    confidence: float | None = None


@dataclass(slots=True)
class Extraction:
    """The root object. This is what step 1 emits and what layer 2 stores."""

    document: DocumentMeta
    header: Header = field(default_factory=Header)
    sections: list[Section] = field(default_factory=list)
    unparsed_blocks: list[UnparsedBlock] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        """Total rows across all sections."""
        return sum(len(s.rows) for s in self.sections)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain JSON-compatible types, dropping ``None`` bboxes."""
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Rebuild an ``Extraction`` from :meth:`to_dict` output.

        Args:
            data: A mapping produced by :meth:`to_dict` or parsed from its JSON.

        Returns:
            The reconstructed object.

        Raises:
            KeyError: If the required ``document`` key is absent.
        """

        def _bbox(raw: dict[str, float] | None) -> BBox | None:
            return BBox(**raw) if raw else None

        return cls(
            document=DocumentMeta(**data["document"]),
            header=Header(**data.get("header", {})),
            sections=[
                Section(
                    printed_title=s.get("printed_title"),
                    rows=[
                        Row(**{**r, "bbox": _bbox(r.get("bbox"))}) for r in s.get("rows", [])
                    ],
                    # JSON object keys are strings; column indices are ints.
                    column_roles={int(k): v for k, v in s.get("column_roles", {}).items()},
                    page=s.get("page", 1),
                    bbox=_bbox(s.get("bbox")),
                )
                for s in data.get("sections", [])
            ],
            unparsed_blocks=[
                UnparsedBlock(**{**b, "bbox": _bbox(b.get("bbox"))})
                for b in data.get("unparsed_blocks", [])
            ],
        )

    @classmethod
    def from_json(cls, text: str) -> Self:
        """Rebuild an ``Extraction`` from a JSON string."""
        parsed: dict[str, Any] = json.loads(text)
        return cls.from_dict(parsed)
