-- =============================================================================
-- Reading the panel vocabulary
-- =============================================================================
-- Two questions this answers: what panels do we know about, and what is in one
-- of them.
--
-- ONE THING TO KNOW FIRST, OR QUERY 2 WILL MISLEAD YOU
--   There are two different "core" flags in this schema and they mean unrelated
--   things.
--
--     lab.panels.is_core   is this panel one of the ten high-frequency groups
--                          worth having a template for. A property of the PANEL.
--
--     core / optional      per the review screen's "Req" column: is this
--     on an ANALYTE         analyte worth flagging when the report does not
--                          print it. This is NOT A STORED COLUMN. It is derived
--                          as NOT lab.analytes.is_derived by
--                          scripts/export_templates.py:149 - Karthik's call of
--                          2026-09-24, chosen for being reproducible from the
--                          database with no editorial opinion in the loop.
--
--   So query 2 recomputes that rule rather than reading it. Two consequences:
--
--   1. If anyone hand-edits a template JSON in
--      api/app/services/ocr/templates/, this query will disagree with what the
--      review screen shows. The JSON wins there; this is the generator's rule.
--   2. The rule has a known hole, documented where it is defined: LDL and VLDL
--      are computed from the other lipids, so is_derived is true and they come
--      out "optional" - even though every lipid report in the world prints
--      them. A lipid panel whose coverage looks too forgiving is this.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Every panel we know, and how much is in it
-- -----------------------------------------------------------------------------
-- The core panels first, because those are the ones a template exists for and
-- therefore the only ones coverage can report on.
SELECT p.code,
       p.display_name,
       p.is_core                                   AS core_panel,
       count(a.id)                                 AS analytes,
       count(a.id) FILTER (WHERE NOT a.is_derived) AS core,
       count(a.id) FILTER (WHERE a.is_derived)     AS optional,
       (SELECT count(*)
          FROM lab.panel_aliases pa
         WHERE pa.panel_id = p.id
           AND pa.is_deleted = FALSE)              AS titles_it_arrives_under
FROM       lab.panels   p
LEFT JOIN  lab.analytes a ON a.panel_id = p.id
                         AND a.is_deleted = FALSE
                         AND a.is_active = TRUE
WHERE  p.is_deleted = FALSE
GROUP  BY p.id, p.code, p.display_name, p.is_core, p.sort_order
ORDER  BY p.is_core DESC, p.sort_order, p.code;


-- -----------------------------------------------------------------------------
-- 2. One panel, core and optional
-- -----------------------------------------------------------------------------
-- Change the code on the WHERE line. Codes come from query 1: CBC, LIPID,
-- DIABETES, LFT, KFT, THYROID, URINE_ROUTINE, ELECTROLYTES, IRON, VITAMIN, ...
SELECT CASE WHEN a.is_derived THEN 'optional' ELSE 'core' END AS req,
       a.code,
       a.display_name,
       a.default_unit,
       a.value_type,
       a.derivation_note                                      AS computed_from
FROM       lab.analytes a
INNER JOIN lab.panels   p ON p.id = a.panel_id
WHERE  p.code = 'URINE_ROUTINE'          -- <<< the panel you want
  AND  a.is_deleted = FALSE
  AND  a.is_active  = TRUE
  AND  p.is_deleted = FALSE
-- is_derived sorts FALSE first, so core comes before optional without a CASE
ORDER  BY a.is_derived, a.sort_order, a.code;


-- -----------------------------------------------------------------------------
-- 3. Every panel and its members in one result, if you want one scroll
-- -----------------------------------------------------------------------------
-- Same facts as 1 and 2 together. Useful for eyeballing the whole vocabulary,
-- poor for anything that needs one row per analyte.
SELECT p.code,
       p.display_name,
       string_agg(a.code, ', ' ORDER BY a.sort_order, a.code)
         FILTER (WHERE NOT a.is_derived) AS core,
       string_agg(a.code, ', ' ORDER BY a.sort_order, a.code)
         FILTER (WHERE a.is_derived)     AS optional
FROM       lab.panels   p
LEFT JOIN  lab.analytes a ON a.panel_id = p.id
                         AND a.is_deleted = FALSE
                         AND a.is_active = TRUE
WHERE  p.is_deleted = FALSE
GROUP  BY p.id, p.code, p.display_name, p.is_core, p.sort_order
ORDER  BY p.is_core DESC, p.sort_order, p.code;


-- -----------------------------------------------------------------------------
-- 4. Analytes belonging to no panel
-- -----------------------------------------------------------------------------
-- Worth running once. An analyte with a NULL panel_id resolves fine on a row
-- but can never count towards any panel's coverage, so it is invisible to the
-- n/m fraction on the review screen. If query 1's analyte counts do not add up
-- to the 108 in /health, this is where the difference is.
SELECT a.code, a.display_name, a.default_unit
FROM   lab.analytes a
WHERE  a.panel_id IS NULL
  AND  a.is_deleted = FALSE
  AND  a.is_active  = TRUE
ORDER  BY a.sort_order, a.code;
