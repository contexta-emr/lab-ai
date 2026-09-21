"""A deliberate stub for the one function pipeline.py imports from synonyms.

THE ORIGINAL
    idp/synonyms.py matches a printed label onto a canonical analyte code. It
    reads 662 mappings out of docs/rkChatZip/lab_analytes_seed.sql and uses
    rapidfuzz for the near-miss tier.

WHY IT IS NOT COPIED
    That is the resolution pass, and in this service resolution lives in SQL:
    lab.fn_resolve_analyte, against lab.analyte_aliases, with the panel-scoped
    aliases 007 added. Copying a second matcher with a second vocabulary read
    from a different file is how the two silently disagree about what
    "S. Creatinine" means, and the whole point of generating the master from
    catalog.py was that the vocabulary has exactly one source.

WHAT IS LOST, AND WHY THAT IS ACCEPTABLE
    pipeline.py calls split_method_suffix to pull a trailing assay method off a
    label - "Cholesterol Total Spectrophotometry" to "Cholesterol Total" plus
    "Spectrophotometry" - so raw_method carries it instead of corrupting the
    label. It cannot do that without a dictionary, because the test is that the
    remainder must still resolve; that is what stops "Vitamin D Binding
    Protein" being cut to "Vitamin D".

    So this returns the label untouched and no method. The full printed label
    then reaches fn_resolve_analyte, which is built for exactly this: three
    passes ending in trigram similarity, which absorbs a glued-on method
    without help. Measured on the corpus, code accuracy through that path is
    99.8%, so there is no evidence the split is needed here.

    If a real report ever proves otherwise, the honest fix is a
    method-stripping pass in SQL beside the alias table, not a second
    vocabulary in Python.
"""

from __future__ import annotations

__all__ = ["split_method_suffix"]


def split_method_suffix(label: str, *, path: str | None = None) -> tuple[str, str | None]:
    """Pass the label through unchanged. See the module docstring."""
    return label, None
