"""Request and response shapes.

BigInt ids cross the wire as strings. PostgreSQL BIGINT goes to 2^63; JavaScript
loses integer precision above 2^53. A patient id of 9007199254740993 would arrive
in the browser as 9007199254740992, silently, and attach a lab report to the
wrong person. So ids are serialised as strings and parsed back with a check.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

ID_PATTERN = re.compile(r"^\d+$")


def parse_id(value: str | int, field: str = "id") -> int:
    """The /^\\d+$/ check the EMR conventions require before casting to BigInt."""
    text = str(value)
    if not ID_PATTERN.match(text):
        raise ValueError(f"{field} must be a positive integer, got {value!r}")
    return int(text)


class Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ------------------------------------------------------------------------ auth
class LoginRequest(Base):
    email: str
    password: str


class TokenResponse(Base):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - the OAuth token type, not a credential
    expires_in_minutes: int
    user_id: str
    practice_id: str
    email: str
    role: str


# -------------------------------------------------------------------- documents
class DocumentSummary(Base):
    id: str
    status: str
    source: str
    detected_uhid: str | None = None
    detected_uhid_label: str | None = None
    detected_patient_name: str | None = None
    patient_id: str | None = None
    patient_name: str | None = None
    patient_uhid: str | None = None
    patient_match_method: str | None = None
    patient_match_confidence: float | None = None
    page_count: int | None = None
    ocr_engine: str | None = None
    extraction_confidence: float | None = None
    result_count: int = 0
    unmatched_count: int = 0
    lab_name: str | None = None
    collected_at: datetime | None = None
    received_at: datetime | None = None
    is_synthetic: bool = False
    # Which page you are looking at. Obvious on paper, invisible in a queue.
    file_name: str | None = None

    @field_serializer("patient_match_confidence", "extraction_confidence")
    def _decimal(self, value: Decimal | float | None) -> float | None:
        return float(value) if value is not None else None


class ResultOut(Base):
    id: str
    printed_label: str
    analyte_code: str | None = None
    analyte_name: str | None = None
    panel_code: str | None = None
    match_method: str | None = None
    match_confidence: float | None = None
    value_text: str
    value_numeric: float | None = None
    value_operator: str | None = None
    unit: str | None = None
    reference_printed: str | None = None
    flag: str | None = None
    is_text_result: bool = False
    is_derived: bool = False

    @field_serializer("match_confidence", "value_numeric")
    def _decimal(self, value: Decimal | float | None) -> float | None:
        return float(value) if value is not None else None


class SectionOut(Base):
    id: str
    heading_printed: str | None = None
    panel_code: str | None = None
    panel_match_method: str | None = None
    results: list[ResultOut] = Field(default_factory=list)


class ReportOut(Base):
    id: str
    lab_name: str | None = None
    accession_no: str | None = None
    uhid_printed: str | None = None
    patient_name_printed: str | None = None
    age_printed: str | None = None
    sex_printed: str | None = None
    collected_at: datetime | None = None
    reported_at: datetime | None = None
    referring_doctor: str | None = None
    layout_hint: str | None = None
    sections: list[SectionOut] = Field(default_factory=list)
    notes: list[dict] = Field(default_factory=list)


class DocumentDetail(DocumentSummary):
    reports: list[ReportOut] = Field(default_factory=list)
    candidates: list[PatientCandidate] = Field(default_factory=list)


class PatientCandidate(Base):
    """A possible patient for a quarantined document, best first."""

    patient_id: str
    uhid: str
    full_name: str
    dob: date | None = None
    match_method: str
    confidence: float
    #: What the match was made on, for a demographic candidate. A reviewer
    #: choosing between two people needs the reason, not just a score.
    evidence: dict | None = None

    @field_serializer("confidence")
    def _decimal(self, value: Decimal | float) -> float:
        return float(value)


# ----------------------------------------------------------------------- review
class ReviewRequest(Base):
    patient_id: str | None = None
    decision: str = "verify"
    note: str | None = None

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: str) -> str:
        if v not in ("verify", "reject"):
            raise ValueError("decision must be 'verify' or 'reject'")
        return v

    @field_validator("patient_id")
    @classmethod
    def _patient(cls, v: str | None) -> str | None:
        if v is not None:
            parse_id(v, "patient_id")
        return v


class ReviewResponse(Base):
    document_id: str
    status: str
    patient_id: str | None = None


# --------------------------------------------------------------------- patients
class PatientOut(Base):
    id: str
    uhid: str
    full_name: str
    dob: date | None = None
    gender: str | None = None
    city: str | None = None
    document_count: int = 0
    result_count: int = 0
    last_report_at: datetime | None = None


class PatientCreate(Base):
    """What a reviewer types to register a patient a report arrived for.

    Only the identifier and a given name are required. Indian reports frequently print
    one name and nothing else, and refusing the record because a surname is missing
    would leave the document with nowhere to go.
    """

    uhid: str
    first_name: str
    last_name: str = ""
    dob: date | None = None
    gender: str | None = None
    city: str | None = None


class TrendPoint(Base):
    # Optional, because a report whose date could not be read still has real
    # readings on it. Returning them with a null date lets the table show them
    # and the chart skip them; making the field required threw away the whole
    # trend over one unparsed date.
    collected_at: datetime | None = None
    value_numeric: float | None = None
    value_text: str
    value_operator: str | None = None
    unit: str | None = None
    reference_printed: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    flag: str | None = None
    lab_name: str | None = None
    printed_label: str
    document_id: str

    @field_serializer("value_numeric", "ref_low", "ref_high")
    def _decimal(self, value: Decimal | float | None) -> float | None:
        return float(value) if value is not None else None


class TrendResponse(Base):
    patient_id: str
    analyte_code: str
    analyte_name: str | None = None
    unit: str | None = None
    point_count: int
    points: list[TrendPoint]


# ----------------------------------------------------------------------- master
class AnalyteOut(Base):
    id: str
    code: str
    display_name: str
    panel_code: str | None = None
    default_unit: str | None = None
    value_type: str
    is_derived: bool
    alias_count: int = 0


class PanelOut(Base):
    id: str
    code: str
    display_name: str
    description: str | None = None
    is_core: bool
    analyte_count: int = 0


class UnmatchedLabelOut(Base):
    id: str
    printed_label: str
    occurrence_count: int
    sample_unit: str | None = None
    sample_value: str | None = None
    last_seen_at: datetime


class ResolveManyIn(Base):
    """A checklist as typed, before anything has been made of it.

    Free text on purpose: codes, printed labels and panel names all arrive
    here, and deciding which is which is the resolver's job, not the caller's.
    """

    labels: list[str] = Field(default_factory=list, max_length=500)


DocumentDetail.model_rebuild()
