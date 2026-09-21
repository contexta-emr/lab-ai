# Open question for RK — PyMuPDF is AGPL-3.0

**Raised:** 2026-09-21 · **Owner:** RK (licensing) · **Status:** open, not blocking today

---

## The question

`contexta-lab-idp` reads every uploaded lab report with **PyMuPDF**
(`api/pyproject.toml`, `pymupdf>=1.24`). PyMuPDF is dual-licensed: **AGPL-3.0**, or a
commercial licence from Artifex.

The AGPL's section 13 network clause is the part that matters. It extends the
copyleft obligation to users who interact with the software **over a network**, not
only to those who receive a copy of it. This service is intended to be hosted — a
doctor's browser calls it over HTTPS — which is exactly the shape that clause was
written for.

I am not qualified to give a legal opinion and am not offering one. I am flagging it
because the decision needs someone who can make it.

## Why it is being raised now

The engineers on `../VectorDB_Analysis/idp/` already faced this and went the other
way. Their `pyproject.toml`:

```toml
# Experimental fast path for digital PDFs. pdfplumber is MIT, unlike PyMuPDF's AGPL.
textlayer = ["pdfplumber>=0.11"]
```

and `src/idp/engines/textlayer.py`:

> *"Built on pdfplumber: MIT licensed, geometry-based, and it exposes every character
> with its coordinates — which is what its table finder reconstructs rows and columns
> from. The licence matters as much as the accuracy: PyMuPDF is AGPL-3.0, whose
> network clause is triggered by hosted SaaS."*

So two engineers on this project have already concluded PyMuPDF should not be in a
hosted product, and this service has it in the request path. That disagreement should
be resolved deliberately rather than by whichever repo ships first.

## What we use it for

One thing: reading the text and word coordinates out of a PDF that already has a text
layer. `api/app/services/extract.py`, via `page.get_text("words")`. No rendering, no
image extraction, no writing.

## The options

| | |
|---|---|
| **Buy the commercial licence** | Keep the code as it is. Cost unknown; Artifex quotes per-product. |
| **Swap to pdfplumber (MIT)** | Same capability — it exposes every character with coordinates, which is all we use. Already the choice made next door, and `pdfplumber` is now a dependency here because `app/services/ocr/textlayer.py` uses it. |
| **Accept AGPL** | Only viable if the service is never offered over a network to anyone outside the licence holder, which contradicts the plan. |
| **Confirm it does not apply** | Possible — but it needs someone qualified to say so, in writing, not an assumption. |

## What it would cost to swap

Not free, and this is the honest part. `pdfplumber` is **already wired up and
measured** in this repo, because `app/services/ocr/` was brought in from the idp
workspace on 2026-09-21. Scored over the full 300-report corpus:

| reader | recall | precision | code | value |
|---|---|---|---|---|
| ours, PyMuPDF word geometry | **86.3%** | 88.8% | 99.8% | 99.7% |
| idp pipeline on pdfplumber | **27.0%** | 46.3% | 99.2% | 80.9% |

That gap is not evidence that pdfplumber is worse. The idp pipeline was built and
tested against thirteen real vendor documents, and our corpus is twenty-six synthetic
layouts it has never seen; pdfplumber's own `has_text_layer` also rejected 116 of our
PDFs where PyMuPDF accepted 239, which alone accounts for much of it. The number says
"a swap is not a drop-in", not "pdfplumber cannot do this".

**So the realistic cost of swapping is engineering time to port our reader onto
pdfplumber's character geometry and get back to 86%, not a permanent loss of accuracy.**
Better to know that before the answer is needed than after.

## What is needed

A decision on which of the four options applies, and if it is the swap, whether it
happens before or after the first production deployment.
