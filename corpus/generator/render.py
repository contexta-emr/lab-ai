"""Turn a composed report into one self-contained A4 HTML page.

Look lives in ``layouts/<layout_style>.css`` - one hand-authored stylesheet per layout
in the corpus spec. This module only decides *structure*: which header block, which
columns, where a trap changes the shape of the table. Nothing external is loaded: no
web fonts, no images, no scripts, so the page prints identically offline.

A new layout that is still a letterheaded report needs only a stylesheet - ``_css()``
picks it up by name and nothing here changes. Only a layout that reshapes the markup
needs a branch in ``render()``, which is why there are so few of them.
"""

from __future__ import annotations

import random
from pathlib import Path

LAYOUT_DIR = Path(__file__).parent / "layouts"

# Layouts whose values are written by hand, and those where only an addendum is.
HAND_VALUES = {"handwritten_values", "handwritten_full"}

BASE_CSS = """
@page { size: A4; margin: 14mm 13mm; }
* { box-sizing: border-box; }
body { margin: 0; color: #111; font-family: "Segoe UI", Calibri, Arial, sans-serif;
       font-size: 9.2pt; line-height: 1.35; }
.sheet { position: relative; }
h1, h2, h3 { margin: 0; font-weight: 600; }
table { width: 100%; border-collapse: collapse; }
td, th { vertical-align: top; }
.lab-name { font-size: 15pt; letter-spacing: .2px; }
.lab-sub { font-size: 7.6pt; color: #444; }
.rule { border-bottom: 1.6px solid #1c3f6e; margin: 5px 0 7px; }
.meta td { padding: 1.2px 4px 1.2px 0; font-size: 8.6pt; }
.meta .k { color: #555; white-space: nowrap; }
.meta .v { font-weight: 600; }
.sec-title { margin: 9px 0 3px; font-size: 10pt; text-transform: uppercase;
             letter-spacing: .4px; color: #10375f; }
.res th { font-size: 8.2pt; text-transform: uppercase; letter-spacing: .3px;
          text-align: left; padding: 3px 5px; }
.res td { padding: 2.4px 5px; font-size: 9pt; }
.res td.val { font-weight: 600; white-space: nowrap; }
.res td.num, .res th.num { text-align: right; }
.flag { font-weight: 700; padding-left: 4px; }
.flag.H { color: #a8122a; }
.flag.L { color: #1d5fa8; }
.method { display: block; font-size: 7.2pt; color: #666; font-style: italic; }
.legend { margin-top: 7px; font-size: 7.6pt; }
.legend th, .legend td { border: .6px solid #999; padding: 1.6px 5px; }
.legend caption { text-align: left; font-weight: 600; font-size: 7.8pt;
                  padding-bottom: 2px; }
.note { margin-top: 7px; font-size: 7.8pt; color: #333; }
.footnotes { margin-top: 5px; font-size: 7.2pt; color: #444; }
.sample-row td { background: #f2f2f2; font-size: 8pt; font-style: italic; }
.sign { margin-top: 16px; display: flex; justify-content: space-between;
        font-size: 8pt; }
.sign .who { text-align: right; }
.sign .nm { font-weight: 600; }
.scribble { font-family: "Segoe Script", "Ink Free", cursive; font-size: 12pt;
            color: #16233f; }
.pfoot { margin-top: 10px; border-top: .6px solid #aaa; padding-top: 3px;
         font-size: 7pt; color: #666; display: flex; justify-content: space-between; }
.hand { font-family: "Ink Free", "Segoe Script", cursive; color: #1a3a8f;
        font-size: 11.5pt; }
.addendum { margin-top: 10px; border: 1px dashed #98a; padding: 6px 8px; }
.addendum .ah { font-size: 8pt; letter-spacing: .3px; color: #555;
                text-transform: uppercase; }
.qr { width: 46px; height: 46px; }
.stamp { position: absolute; top: 46mm; right: 4mm; border: 2.5px solid #7a1f2b; color: #7a1f2b;
         padding: 5px 10px; font-size: 9pt; font-weight: 700; letter-spacing: 1px;
         opacity: .48; transform: rotate(-14deg); text-align: center;
         border-radius: 4px; line-height: 1.1; }
.logo { width: 34px; height: 34px; border-radius: 50%; background: #10375f;
        color: #fff; font-weight: 700; font-size: 13pt; text-align: center;
        line-height: 34px; }
.deptblock { background: #10375f; color: #fff; padding: 4px 8px; font-size: 8.4pt;
             letter-spacing: .6px; text-transform: uppercase; }
.hdr-logo { display: flex; gap: 9px; align-items: center; }
.hdr-centre { text-align: center; }
.hdr-banner { display: flex; justify-content: space-between; align-items: center; }
.hdr-min { border-bottom: 1px solid #333; padding-bottom: 2px; font-size: 8.4pt; }
.hdr-stampsig { text-align: center; }
.sec-sub { font-size: 7.8pt; color: #555; margin-bottom: 2px; font-style: italic; }
.cols { display: flex; gap: 9mm; align-items: flex-start; }
.cols .sec { flex: 1 1 0; min-width: 0; }
.pagebreak { break-after: page; page-break-after: always; height: 0; }
.contd { font-size: 7.6pt; color: #555; text-align: right; margin-top: 4px; }
.p2head { font-size: 7.8pt; color: #333; border-bottom: 1px solid #888;
          padding-bottom: 3px; margin-bottom: 6px; }
.hdr-barcode { display: flex; gap: 12px; align-items: flex-start;
               justify-content: space-between; }
.barcode { width: 58mm; height: 11mm; display: block; }
.bcnum { font-family: Consolas, "Courier New", monospace; font-size: 7.4pt;
         letter-spacing: 2px; text-align: center; }
.bcname { text-align: right; }
.hdr-bilingual { text-align: center; }
.lab-local { font-family: "Nirmala UI", "Segoe UI", sans-serif; font-size: 13pt;
             color: #10375f; }
.lab-local-sm { font-family: "Nirmala UI", "Segoe UI", sans-serif; font-size: 8pt; }
.res td.fw { font-size: 7.6pt; letter-spacing: .6px; font-weight: 700; color: #777; }
.res td.fw.H { color: #a8122a; }
.res td.fw.L { color: #1d5fa8; }
.res tr.abn td { background: #fdf0f0; font-weight: 600; }
.interp { margin-top: 8px; padding: 6px 9px; font-size: 8pt; background: #f4f6f8;
          border-left: 3px solid #10375f; line-height: 1.4; }
.hdr-ribbon { margin-bottom: 7px; }
.ribbon { background: #10375f; color: #fff; padding: 5px 10px; font-size: 13pt;
          letter-spacing: .6px; }
.ribbon-sub { background: #dde5ee; color: #24374d; padding: 2.5px 10px; font-size: 7.4pt; }
.res td.labcode { font-family: Consolas, "Courier New", monospace; font-size: 7.6pt;
                  color: #667; white-space: nowrap; }
.res td.reflow, .res td.refhigh { font-size: 8.2pt; color: #555; text-align: right; }
"""


def _css(layout: str) -> str:
    path = LAYOUT_DIR / f"{layout}.css"
    return path.read_text(encoding="utf-8") if path.exists() else ""


DAMAGE_CSS = (LAYOUT_DIR / "_damage.css").read_text(encoding="utf-8")


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _barcode_svg(text: str) -> str:
    """A Code-128-looking barcode. The bars are decorative; the number under them is not."""
    rng = random.Random(text)
    x, bars = 0, []
    while x < 240:
        w = rng.choice((1, 1, 2, 2, 3))
        if rng.random() < 0.55:
            bars.append(f'<rect x="{x}" y="0" width="{w}" height="34"/>')
        x += w + rng.choice((1, 1, 2))
    return (f'<svg class="barcode" viewBox="0 0 {x} 34" preserveAspectRatio="none" '
            f'fill="#111">{"".join(bars)}</svg>')


def _qr_svg() -> str:
    """A QR-shaped block of inline SVG - no image file, just squares."""
    rng = random.Random(7)
    cells = []
    for y in range(11):
        for x in range(11):
            corner = (x < 3 and y < 3) or (x > 7 and y < 3) or (x < 3 and y > 7)
            if corner or rng.random() < 0.45:
                cells.append(f'<rect x="{x}" y="{y}" width="1" height="1"/>')
    return ('<svg class="qr" viewBox="0 0 11 11" fill="#111">' + "".join(cells) + "</svg>")


# --------------------------------------------------------------------------- header


def _header(rep: dict) -> str:
    lab = rep["lab"]
    style = rep["header_style"]
    initials = "".join(w[0] for w in lab["name"].split()[:2]).upper()
    addr = f'{lab["addr"]} &nbsp;|&nbsp; Ph: {lab["phone"]}'

    if style == "letterhead_logo_left":
        return f"""<div class="hdr hdr-logo">
  <div class="logo">{initials[:1]}</div>
  <div>
    <div class="lab-name">{_esc(lab["name"])}</div>
    <div class="lab-sub">{addr}</div>
    <div class="lab-sub">{_esc(lab["accred"])}</div>
  </div>
</div><div class="rule"></div>"""

    if style == "centred_title_only":
        return f"""<div class="hdr hdr-centre">
  <div class="lab-name">{_esc(lab["name"])}</div>
  <div class="lab-sub">{_esc(lab["addr"])}</div>
  <div class="lab-sub">LABORATORY INVESTIGATION REPORT</div>
</div><div class="rule"></div>"""

    if style == "banner_with_qr":
        return f"""<div class="hdr hdr-banner">
  <div>
    <div class="lab-name">{_esc(lab["name"])}</div>
    <div class="lab-sub">{addr}</div>
  </div>
  {_qr_svg()}
</div><div class="rule"></div>"""

    if style == "stamp_and_signature":
        return f"""<div class="hdr hdr-stampsig">
  <div class="lab-name">{_esc(lab["name"])}</div>
  <div class="lab-sub">{_esc(lab["addr"])} &nbsp;&nbsp; {_esc(lab["accred"])}</div>
</div><div class="rule"></div>"""

    if style == "minimal_text_top":
        return f"""<div class="hdr hdr-min">
  <div><b>{_esc(lab["name"])}</b> &nbsp; {_esc(lab["city"])} &nbsp; {_esc(lab["phone"])}</div>
</div>"""

    if style == "barcode_header":
        return f"""<div class="hdr hdr-barcode">
  <div class="bc">{_barcode_svg(rep["accession"])}
    <div class="bcnum">{_esc(rep["accession"])}</div></div>
  <div class="bcname">
    <div class="lab-name">{_esc(lab["name"])}</div>
    <div class="lab-sub">{addr}</div>
  </div>
</div><div class="rule"></div>"""

    if style == "two_line_ribbon":
        return f"""<div class="hdr hdr-ribbon">
  <div class="ribbon">{_esc(lab["name"])}</div>
  <div class="ribbon-sub">{addr} &nbsp;&middot;&nbsp; {_esc(lab["accred"])}</div>
</div>"""

    if style == "bilingual_header":
        local = lab.get("name_local", lab["name"])
        local_addr = lab.get("addr_local", "")
        return f"""<div class="hdr hdr-bilingual">
  <div class="lab-name">{_esc(lab["name"])}</div>
  <div class="lab-local">{_esc(local)}</div>
  <div class="lab-sub">{addr}</div>
  <div class="lab-sub lab-local-sm">{_esc(local_addr)}</div>
</div><div class="rule"></div>"""

    # hospital_department_block
    return f"""<div class="hdr hdr-dept">
  <div class="lab-name">{_esc(lab["name"])}</div>
  <div class="lab-sub">{_esc(lab["addr"])}</div>
  <div class="deptblock">Department of Laboratory Medicine &nbsp;&middot;&nbsp; {_esc(rep["department"])}</div>
</div>"""


def _demographics(rep: dict, kv_box: bool) -> str:
    left = [
        ("Patient Name", rep["patient_name"]),
        (rep["uhid_label"], rep["uhid"]),
        ("Age / Sex", f'{rep["age_printed"]} Y / {rep["sex"]}'),
        ("Referred By", rep["referring_doctor"]),
    ]
    right = [
        ("Accession No.", rep["accession"]),
        ("Sample Collected", rep["collected_printed"]),
        ("Report Released", rep["reported_printed"]),
        ("Specimen", rep["specimen"]),
    ]
    rows = "".join(
        f'<tr><td class="k">{_esc(a)}</td><td class="v">{_esc(b)}</td>'
        f'<td class="k">{_esc(c)}</td><td class="v">{_esc(d)}</td></tr>'
        for (a, b), (c, d) in zip(left, right)
    )
    cls = "meta kvbox" if kv_box else "meta"
    return f'<table class="{cls}">{rows}</table>'


# ---------------------------------------------------------------------------- table


def _columns(rep: dict) -> list[str]:
    cols = []
    if "sno_column" in rep["traps"]:
        cols.append("sno")
    if "test_code_column" in rep["traps"]:
        cols.append("labcode")
    cols.append("label")
    cols.append("value")
    if not {"unit_in_value_cell", "unit_in_label"} & set(rep["traps"]):
        cols.append("unit")
    if "range_split_columns" in rep["traps"]:
        cols += ["reflow", "refhigh"]
    elif "no_reference_column" not in rep["traps"]:
        cols.append("ref")
    if rep["layout_style"] == "range_bar":
        cols.append("bar")
    if "flag_as_words" in rep["traps"]:
        cols.append("flagcol")
    if "prev_value_column" in rep["traps"]:
        cols.insert(cols.index("value") + 1, "prev")
    return cols


HEAD_TEXT = {
    "sno": "S.No",
    "label": "Investigation",
    "value": "Result",
    "unit": "Units",
    "ref": "Biological Reference Interval",
    "flagcol": "Status",
    "prev": "Previous",
    "labcode": "Test Code",
    "reflow": "Range Low",
    "refhigh": "Range High",
    "bar": "Low / Normal / High",
}

FLAG_WORDS = {"H": "HIGH", "L": "LOW", "": "NORMAL"}


def _cell(row: dict, col: str, rep: dict, n: int, jitter) -> str:
    hand = rep["layout_style"] in HAND_VALUES
    if col == "sno":
        return f'<td class="num sno">{n}</td>'
    if col == "label":
        lbl = _esc(row["printed_label"])
        if "unit_in_label" in rep["traps"] and row["unit"]:
            lbl += f' ({_esc(row["unit"])})' 
        if row.get("marker"):
            lbl += f'<sup>{row["marker"]}</sup>'
        meth = (f'<span class="method">Method: {_esc(row["method"])}</span>'
                if row.get("method") else "")
        return f'<td class="lbl">{lbl}{meth}</td>'
    if col == "value":
        txt = _esc(row["value"])
        if "unit_in_value_cell" in rep["traps"] and row["unit"]:
            txt = f'{txt} {_esc(row["unit"])}'
        if "flag_as_words" in rep["traps"] or "abnormal_shaded" in rep["traps"]:
            flag = ""  # carried by its own column, or by the shading alone
        else:
            flag = (f'<span class="flag {row["flag"]}">{row["flag"]}</span>'
                    if row.get("flag") else "")
        if hand or row.get("hand"):
            deg, dy = jitter()
            txt = (f'<span class="hand" style="display:inline-block;'
                   f'transform:rotate({deg}deg) translateY({dy}px)">{txt}</span>')
        return f'<td class="val num">{txt}{flag}</td>'
    if col == "bar":
        return _range_bar(row)
    if col == "labcode":
        return f'<td class="labcode">{_esc(row.get("lab_code", ""))}</td>'
    if col in ("reflow", "refhigh"):
        band = row.get("reference", "")
        low, high = "", ""
        if " - " in band:
            low, high = band.split(" - ", 1)
        elif band.startswith("<"):
            high = band.lstrip("< ")
        elif band.startswith(">"):
            low = band.lstrip("> ")
        else:
            low = band
        return f'<td class="{col}">{_esc(low if col == "reflow" else high)}</td>'
    if col == "prev":
        return f'<td class="prev">{_esc(row.get("prev", ""))}</td>'
    if col == "flagcol":
        word = FLAG_WORDS.get(row.get("flag", ""), "")
        return f'<td class="fw {row.get("flag", "")}">{word}</td>'
    if col == "unit":
        return f'<td class="unit">{_esc(row["unit"])}</td>'
    ref = _esc(row["reference"])
    if "range_with_unit" in rep["traps"] and row["unit"] and row["reference"]:
        ref = f'{ref} {_esc(row["unit"])}'
    return f'<td class="ref">{ref}</td>'


def _slip_section(sec: dict, rep: dict) -> str:
    """A till-roll has no columns: name, then the value right-aligned under it."""
    items = []
    for row in sec["rows"]:
        unit = f' {_esc(row["unit"])}' if row["unit"] else ""
        flag = f' {row["flag"]}' if row.get("flag") else ""
        ref = (f'<span class="rf">Ref: {_esc(row["reference"])}</span>'
               if row.get("reference") and "no_reference_column" not in rep["traps"] else "")
        items.append(f'<div class="slip-row"><span class="nm">{_esc(row["printed_label"])}'
                     f'</span><span class="vl">{_esc(row["value"])}{unit}{flag}</span>'
                     f'{ref}</div>')
    title = (f'<div class="sec-title">{_esc(sec["heading"])}</div>'
             if sec.get("heading") else "")
    return f'<div class="sec">{title}{"".join(items)}</div>'


def _section_table(sec: dict, rep: dict, start_n: int) -> tuple[str, int]:
    cols = _columns(rep)
    rng = random.Random(f'{rep["report_id"]}-{sec["heading"]}')

    def jitter():
        return round(rng.uniform(-1.5, 1.5), 2), round(rng.uniform(-1.6, 1.6), 1)

    head = ""
    if "no_header_row" not in rep["traps"]:
        ths = "".join(
            f'<th class="{"num" if c in ("sno", "value") else ""}">{HEAD_TEXT[c]}</th>'
            for c in cols
        )
        head = f"<thead><tr>{ths}</tr></thead>"

    body, n = [], start_n
    if "sample_type_row" in rep["traps"] and sec.get("sample_row"):
        body.append(f'<tr class="sample-row"><td colspan="{len(cols)}">'
                    f'Sample Type : {_esc(sec["sample_row"])}</td></tr>')
    shade = "abnormal_shaded" in rep["traps"]
    for row in sec["rows"]:
        tds = "".join(_cell(row, c, rep, n, jitter) for c in cols)
        cls = ' class="abn"' if shade and row.get("flag") else ""
        body.append(f"<tr{cls}>{tds}</tr>")
        n += 1

    title = (f'<div class="sec-title">{_esc(sec["heading"])}</div>'
             if sec.get("heading") else "")
    if sec.get("sub"):
        title += f'<div class="sec-sub">{_esc(sec["sub"])}</div>'
    table = f'<table class="res">{head}<tbody>{"".join(body)}</tbody></table>'
    legend = _legend(sec) if sec.get("legend") else ""
    return f'<div class="sec">{title}{table}{legend}</div>', n


def _legend(sec: dict) -> str:
    rows = "".join(f"<tr><td>{_esc(a)}</td><td>{_esc(b)}</td></tr>" for a, b in sec["legend"][1:])
    return (f'<table class="legend"><caption>{_esc(sec["legend"][0][0])}</caption>'
            f'<tr><th>{_esc(sec["legend"][0][1])}</th><th>Interpretation</th></tr>'
            f"{rows}</table>")


def _addendum(sec: dict, rep: dict) -> str:
    rng = random.Random(f'{rep["report_id"]}-add')
    items = []
    for row in sec["rows"]:
        deg = round(rng.uniform(-1.5, 1.5), 2)
        dy = round(rng.uniform(-1.6, 1.6), 1)
        unit = f' {_esc(row["unit"])}' if row["unit"] else ""
        items.append(
            f'<div class="hand" style="transform:rotate({deg}deg) translateY({dy}px)">'
            f'{_esc(row["printed_label"])} &nbsp;&mdash;&nbsp; {_esc(row["value"])}{unit}</div>'
        )
    return (f'<div class="addendum"><div class="ah">{_esc(sec["heading"])}</div>'
            + "".join(items) + "</div>")


# ------------------------------------------------------- other document kinds
#
# The four below are not skins on the same table. A chat screenshot, a register
# page and a discharge summary are different *kinds* of document that happen to
# carry lab values, which is what a real clinic actually receives.


def _range_bar(row: dict) -> str:
    """Where this value sits inside its range, drawn as a bar."""
    band, raw = row.get("reference", ""), row.get("value", "")
    try:
        val = float(str(raw).lstrip("<> "))
    except ValueError:
        return '<td class="bar"></td>'
    if " - " in band:
        lo, hi = (float(x) for x in band.split(" - "))
    elif band.startswith("<"):
        lo, hi = 0.0, float(band.lstrip("< "))
    elif band.startswith(">"):
        lo = float(band.lstrip("> "))
        hi = lo * 2
    else:
        return '<td class="bar"></td>'
    span = (hi - lo) or 1.0
    left, right = lo - span * 0.6, hi + span * 0.6
    width = (right - left) or 1.0
    pos = max(0.0, min(1.0, (val - left) / width)) * 100
    lo_x = (lo - left) / width * 100
    hi_x = (hi - left) / width * 100
    colour = "#c0392b" if val > hi else ("#2471a3" if val < lo else "#1e8449")
    return (
        '<td class="bar"><svg class="rangebar" viewBox="0 0 100 13" '
        'preserveAspectRatio="none">'
        '<rect x="0" y="5" width="100" height="3" fill="#e6ebef"/>'
        f'<rect x="{lo_x:.1f}" y="5" width="{hi_x - lo_x:.1f}" height="3" fill="#bfe3cb"/>'
        f'<circle cx="{pos:.1f}" cy="6.5" r="3.1" fill="{colour}"/>'
        "</svg></td>"
    )


def _chat(rep: dict) -> str:
    """The lab typed the results into a chat and the patient screenshotted it."""
    lab = rep["lab"]
    when = rep["reported_printed"]
    day, clock = when.split(" ", 1)
    bubbles = []
    for sec in rep["sections"]:
        lines = []
        for row in sec["rows"]:
            unit = f' {_esc(row["unit"])}' if row["unit"] else ""
            mark = {"H": " (H)", "L": " (L)"}.get(row.get("flag", ""), "")
            lines.append(f'<div class="ln">{_esc(row["printed_label"])} - '
                         f'<b>{_esc(row["value"])}{unit}</b>{mark}</div>')
        title = (f'<div class="ttl">{_esc(sec["heading"])}</div>'
                 if sec.get("heading") else "")
        bubbles.append(f'<div class="bub">{title}{"".join(lines)}'
                       f'<div class="tm">{_esc(clock)}</div></div>')
    reply = ('<div class="bub me"><div class="ln">Thank you sir, I will show this to the '
             'doctor tomorrow</div>'
             f'<div class="tm">{_esc(clock)} &#10003;&#10003;</div></div>')
    note = (f'<div class="chatfoot">{_esc(rep["note"])}</div>' if rep.get("note") else "")
    return (
        f'<div class="statusbar"><span>{_esc(day)}</span><span>4G &#9679;&#9679;&#9679; 78%</span></div>'
        f'<div class="chatbar"><div class="av">{_esc(lab["name"][0].upper())}</div>'
        f'<div><div class="nm">{_esc(lab["name"])}</div>'
        f'<div class="st">online</div></div></div>'
        f'<div class="chatwrap"><div class="daychip"><span>{_esc(day)}</span></div>'
        f'{"".join(bubbles)}{reply}</div>{note}'
    )


# Other people whose results share the register page. Invented, like everyone here,
# and deliberately absent from the answer key: picking our patient out is the test.
DECOYS = [
    ("Sunil Marathe", "44 / M", "Blood Sugar F", "108 mg/dL"),
    ("Farida Sheikh", "29 / F", "Haemoglobin", "10.9 g/dL"),
    ("T. Ramakrishnan", "67 / M", "Creatinine", "1.42 mg/dL"),
    ("Bhavna Solanki", "35 / F", "TSH", "3.62 uIU/mL"),
    ("Imran Qadri", "52 / M", "Uric Acid", "7.8 mg/dL"),
    ("Lalita Barman", "61 / F", "Haemoglobin", "11.4 g/dL"),
    ("Nitin Wagh", "23 / M", "Widal", "Non Reactive"),
]


def _register(rep: dict) -> str:
    """A page of the lab's ruled register: several patients, ours among them."""
    rng = random.Random(rep["report_id"])
    ours = [(rep["patient_name"], f'{rep["age_printed"]} / {rep["sex"]}',
             row["printed_label"], f'{row["value"]} {row["unit"]}'.strip())
            for sec in rep["sections"] for row in sec["rows"]]
    entries = [(n, a, t, v, False) for n, a, t, v in rng.sample(DECOYS, 5)]
    at = rng.randrange(1, 5)
    for k, entry in enumerate(ours):
        entries.insert(at + k, (*entry, True))

    date = rep["collected_printed"].split(" ")[0]
    abbr = rep["lab"].get("abbr", "LAB")
    rows = []
    for i, (name, age, test, val, mine) in enumerate(entries, start=1):
        acc = rep["accession"] if mine else f"{abbr}/{rng.randrange(1000, 9999)}"
        rows.append(
            f"<tr><td><div>{i}</div></td><td><div>{_esc(date)}</div></td>"
            f"<td><div>{_esc(acc)}</div></td><td><div>{_esc(name)}</div></td>"
            f"<td><div>{_esc(age)}</div></td><td><div>{_esc(test)}</div></td>"
            f"<td><div>{_esc(val)}</div></td></tr>"
        )
    return (
        f'<div class="reg-head"><div>'
        f'<div class="reg-title">{_esc(rep["lab"]["name"])}</div>'
        f'<div class="reg-sub">{_esc(rep["lab"]["addr"])}</div></div>'
        f'<div class="reg-sub">DAILY RESULT REGISTER &middot; {_esc(date)}</div></div>'
        '<table class="regtab"><thead><tr><th>Sl</th><th>Date</th><th>Lab No</th>'
        '<th>Patient Name</th><th>Age / Sex</th><th>Investigation</th><th>Result</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        '<div class="reg-note">Register page photographed for the patient file. Entries '
        'for other patients on this page are not part of this record.</div>'
        f'<div class="reg-sign"><span>Entered by: {_esc(rep["technician"])}</span>'
        f'<span class="scribble">{_esc(rep["pathologist"]["scrawl"])}</span></div>'
    )


def _discharge(rep: dict, blocks: list[str]) -> str:
    """Labs as one section inside a discharge summary, not as the document itself."""
    ds = rep.get("discharge", {})
    parts = [
        f'<div class="ds-head"><div class="lab-name">{_esc(rep["lab"]["name"])}</div>'
        f'<div class="lab-sub">{_esc(rep["lab"]["addr"])} &nbsp;|&nbsp; Ph: '
        f'{_esc(rep["lab"]["phone"])}</div></div>'
        '<div class="ds-title">Discharge Summary</div>',
        _demographics(rep, False),
    ]
    for label in ("diagnosis", "history", "examination", "course"):
        if ds.get(label):
            parts.append(f'<div class="ds-sec">{label}</div>'
                         f'<div class="ds-body">{_esc(ds[label])}</div>')
    parts.append('<div class="ds-sec">Investigations</div>')
    parts.append("".join(blocks))
    for label in ("treatment", "advice"):
        if ds.get(label):
            parts.append(f'<div class="ds-sec">{label}</div>'
                         f'<div class="ds-body">{_esc(ds[label])}</div>')
    return "".join(parts)


# ----------------------------------------------------------------------- assembling


def _pfoot(rep: dict, pages: str) -> str:
    return (f'<div class="pfoot"><span>{_esc(rep["report_id"])} &middot; '
            f'{_esc(rep["lab"]["name"])}</span><span>{_esc(rep["accession"])}'
            f'</span><span>{pages}</span></div>')


def render(rep: dict) -> str:
    """Compose the whole page. ``rep`` is a composed report from build.compose()."""
    layout = rep["layout_style"]

    # document kinds that are not a letterheaded report at all
    if layout == "chat_screenshot":
        return _page(rep, layout, _chat(rep))
    if layout == "register_page":
        return _page(rep, layout, _register(rep))

    kv_box = layout == "kv_header_table"
    parts = [_header(rep), _demographics(rep, kv_box)]

    n = 1
    blocks = []
    for sec in rep["sections"]:
        if sec.get("hand_addendum"):
            blocks.append(_addendum(sec, rep))
            continue
        if layout == "thermal_slip":
            blocks.append(_slip_section(sec, rep))
            continue
        html, n = _section_table(sec, rep, n)
        blocks.append(html)

    if layout == "discharge_summary":
        parts = [_discharge(rep, blocks)]
    elif layout == "two_column":
        parts.append('<div class="cols">' + "".join(blocks) + "</div>")
    elif layout == "newsprint_cols":
        # CSS columns need one element to flow through; the header must stay outside it
        parts.append('<div class="colwrap">' + "".join(blocks) + "</div>")
    elif layout == "continuation":
        half = rep.get("page_break_after", max(1, len(blocks) - 1))
        parts.append("".join(blocks[:half]))
        parts.append('<div class="contd">Continued on page 2 &rarr;</div>')
        parts.append(_pfoot(rep, "Page 1 of 2"))
        parts.append('<div class="pagebreak"></div>')
        parts.append(f'<div class="p2head">{_esc(rep["lab"]["name"])} &middot; '
                     f'{_esc(rep["patient_name"])} &middot; {_esc(rep["uhid_label"])} '
                     f'{_esc(rep["uhid"])} &middot; Page 2 of 2</div>')
        parts.append('<div class="contd">&hellip; continued from page 1</div>')
        parts.append("".join(blocks[half:]))
    else:
        parts.append("".join(blocks))

    if rep.get("footnotes"):
        parts.append('<div class="footnotes">'
                     + "<br>".join(f'<sup>{m}</sup> {_esc(t)}' for m, t in rep["footnotes"])
                     + "</div>")
    if rep.get("interpretation"):
        parts.append(f'<div class="interp"><b>Interpretation</b><br>'
                     f'{_esc(rep["interpretation"])}</div>')
    if rep.get("note"):
        parts.append(f'<div class="note">{_esc(rep["note"])}</div>')

    signed = rep["pathologist"]
    hand_sig = "scribble" if layout not in HAND_VALUES else "scribble"
    parts.append(f"""<div class="sign">
  <div class="tech">Tested by: {_esc(rep["technician"])}<br>
    <span class="lab-sub">Results released electronically. Verified before release.</span></div>
  <div class="who"><span class="{hand_sig}">{_esc(signed["scrawl"])}</span><br>
    <span class="nm">{_esc(signed["name"])}</span><br>{_esc(signed["qual"])}<br>
    Regn. No. {_esc(signed["regn"])}</div>
</div>""")
    parts.append(_pfoot(rep, "Page 2 of 2" if layout == "continuation" else "Page 1 of 1"))

    if "stamp" in rep:
        parts.append(f'<div class="stamp">{rep["stamp"]}</div>')

    return _page(rep, layout, "".join(parts))


def _page(rep: dict, layout: str, body: str) -> str:
    """Wrap a finished body in the page skeleton, with any handling damage over it."""
    if layout == "poor_scan":
        body = f'<div class="scanwrap"><div class="speckle"></div>{body}</div>'
    elif layout == "mobile_photo":
        body = f'<div class="photowrap">{body}</div>'
    elif layout == "fax_header":
        body = f'<div class="faxwrap">{body}</div>'

    if rep.get("damage"):
        damage = list(rep["damage"])
        if rep.get("illegible"):
            damage.append("illegible")
        # one wrapper per effect, nested: CSS filters do not stack on a single element,
        # so a blurred AND badly lit photograph needs two boxes, not two class names
        for d in reversed(damage):
            body = f'<div class="dmg dmg-{d}">{body}</div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{_esc(rep["report_id"])} {_esc(rep["lab"]["name"])}</title>
<style>{BASE_CSS}
{_css(layout)}
{DAMAGE_CSS if rep.get("damage") else ""}</style></head>
<body><div class="sheet">{body}</div></body></html>
"""
