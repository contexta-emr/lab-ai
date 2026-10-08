"""PaddleOCR-VL 1.6 engine.

The production engine, chosen for Apache-2.0 licensing, fine-grained coordinates, and
the fact that it runs entirely inside our own boundary - nothing about a patient's lab
report leaves the machine.

Installation is an optional extra, because ``paddlepaddle`` is roughly 2 GB::

    uv pip install -e ".[paddle]"

Without a GPU it runs at roughly 30-120 seconds per page. Extraction is asynchronous by
design, so that is acceptable for testing; it is not acceptable on a request path.

See `paddleocr-vl-architecture.md`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import RawBlock, RawDocument, RawPage

__all__ = ["PaddleVLEngine", "normalise_page_result"]

_MISSING = (
    "PaddleOCR-VL is not installed. Install the optional extra:\n"
    '    uv pip install -e ".[paddle]"\n'
    "First run also downloads roughly 2 GB of model weights."
)


def _as_floats(value: Any) -> tuple[float, float, float, float] | None:
    """Coerce a bbox of unknown provenance into four floats.

    PaddleOCR returns ``block_bbox`` as a numpy array and ``coordinate`` as a list, so
    this accepts anything with four numeric elements and rejects everything else rather
    than letting a malformed box reach the contract.
    """
    if value is None:
        return None
    try:
        parts = [float(v) for v in list(value)[:4]]
    except (TypeError, ValueError):
        return None
    if len(parts) != 4:
        return None
    x0, y0, x1, y1 = parts
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def normalise_page_result(payload: dict[str, Any], *, fallback_page: int) -> RawPage:
    """Turn one PaddleOCR-VL page result into a :class:`RawPage`.

    Kept as a free function, separate from the engine class, so it can be unit-tested
    against recorded fixtures without paddlepaddle installed. That matters: the engine
    itself needs a 2 GB dependency and minutes of CPU, while this mapping is where the
    bugs actually live.

    Args:
        payload: The ``result.json`` dict, or its inner ``res`` object.
        fallback_page: Page number to use when the payload does not carry one.

    Returns:
        The page with its blocks and the size its coordinates are expressed in.
    """
    res = payload.get("res", payload) if isinstance(payload.get("res"), dict) else payload

    width = float(res.get("width") or 0) or 1.0
    height = float(res.get("height") or 0) or 1.0
    index = res.get("page_index")
    page_number = (int(index) + 1) if isinstance(index, int) else fallback_page

    blocks: list[RawBlock] = []
    for item in res.get("parsing_res_list") or []:
        content = item.get("block_content") or ""
        if not str(content).strip():
            continue
        blocks.append(
            RawBlock(
                label=str(item.get("block_label") or "text"),
                content=str(content),
                bbox=_as_floats(item.get("block_bbox")),
                order=item.get("block_order")
                if isinstance(item.get("block_order"), int)
                else None,
                score=None,
            )
        )

    # Layout detection carries per-region confidence that parsing_res_list omits. Match
    # them up by geometry so a low-confidence region can be flagged downstream.
    for box in (res.get("layout_det_res") or {}).get("boxes") or []:
        coord = _as_floats(box.get("coordinate"))
        score = box.get("score")
        if coord is None or not isinstance(score, (int, float)):
            continue
        for block in blocks:
            if block.bbox is not None and block.score is None and _overlaps(block.bbox, coord):
                block.score = float(score)
                break

    return RawPage(page_number=page_number, width=width, height=height, blocks=blocks)


def _overlaps(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    """True when two boxes share more than half of the smaller one's area."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter <= 0:
        return False
    area_a = max(1e-9, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1e-9, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / min(area_a, area_b) > 0.5


class PaddleVLEngine:
    """Adapter over the ``PaddleOCRVL`` pipeline.

    The model is loaded on first use, not at construction, so importing this module - and
    therefore the package - costs nothing when paddle is absent.
    """

    name = "PADDLEOCR_VL"

    def __init__(
        self,
        *,
        pipeline_version: str = "v1.6",
        device: str = "cpu",
        use_layout_detection: bool = True,
        layout_threshold: float = 0.5,
        orientation_and_unwarp: bool = False,
        max_concurrency: int | None = None,
    ) -> None:
        """Configure the engine without loading anything.

        Args:
            pipeline_version: PaddleOCR-VL pipeline version. Pin it - a version bump is a
                behaviour change that requires re-benchmarking, not a patch.
            device: ``cpu``, ``gpu:0``, and so on.
            use_layout_detection: Keep enabled; it supplies the region confidences.
            layout_threshold: Minimum layout detection score.
            orientation_and_unwarp: Page-rotation detection and de-warping of curved
                paper. **The pipeline config turns both on by default**, and each is an
                extra model run per page. A digital PDF is upright and flat, so both are
                wasted work - hence off here. Turn it back on for phone photographs of
                curved or rotated pages, where they earn their cost.
            max_concurrency: How many page regions PaddleOCR reads at once. ``None``
                leaves the pipeline default. Raising it is the documented throughput
                knob; the useful value depends on core count, so measure rather than
                guess.
        """
        self.version = pipeline_version
        self._device = device
        self._use_layout_detection = use_layout_detection
        self._layout_threshold = layout_threshold
        self._orientation_and_unwarp = orientation_and_unwarp
        self._max_concurrency = max_concurrency
        self._pipeline: Any = None

    def _load(self) -> Any:
        """Load the pipeline once, raising a useful error when paddle is missing."""
        if self._pipeline is not None:
            return self._pipeline
        try:
            from paddleocr import PaddleOCRVL
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(_MISSING) from exc
        options: dict[str, Any] = {
            "pipeline_version": self.version,
            "device": self._device,
            "use_layout_detection": self._use_layout_detection,
            "layout_threshold": self._layout_threshold,
            "use_doc_orientation_classify": self._orientation_and_unwarp,
            "use_doc_unwarping": self._orientation_and_unwarp,
            "use_chart_recognition": False,
            "use_seal_recognition": False,
        }
        if self._max_concurrency is not None:
            options["vl_rec_max_concurrency"] = self._max_concurrency
        self._pipeline = PaddleOCRVL(**options)
        return self._pipeline

    def extract(self, path: Path) -> RawDocument:
        """Run PaddleOCR-VL over one file.

        Args:
            path: PDF or image to read.

        Returns:
            One :class:`RawPage` per page, in document order.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            RuntimeError: If paddleocr is not installed.
        """
        if not path.exists():
            raise FileNotFoundError(path)
        pipeline = self._load()
        pages = [
            normalise_page_result(_result_json(result), fallback_page=i)
            for i, result in enumerate(pipeline.predict(input=str(path)), start=1)
        ]
        return RawDocument(
            source_path=path, engine=self.name, engine_version=self.version, pages=pages
        )


def _result_json(result: Any) -> dict[str, Any]:
    """Pull the dict out of a paddle result object, whatever shape it arrives in."""
    payload = getattr(result, "json", result)
    return payload if isinstance(payload, dict) else {}
