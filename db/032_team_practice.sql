-- =============================================================================
-- Contexta - Lab extraction store
-- 032  A practice for the team, empty, beside the test data
-- =============================================================================
-- Run after 031.
--
-- WHY
--   The team console has no sign-in. It runs every visitor as one account,
--   named in OPEN_ACCESS_TEAM (app/auth.py). That account must not belong to
--   practice 1, which holds the 20 synthetic patients and their reports.
--   Every query is scoped by the caller's practice_id, so a second practice
--   starts empty and cannot see the first.
--
--   Nothing is copied. The vocabulary - analytes, panels, aliases - is
--   shared, so reading works from the first upload.
--
-- NO PASSWORD
--   Open access needs none, and a migration must never carry one (see 013).
-- =============================================================================

INSERT INTO core.practices (name)
SELECT 'Contexta Team'
WHERE  NOT EXISTS (SELECT 1 FROM core.practices WHERE name = 'Contexta Team');

INSERT INTO core.users (practice_id, email, full_name, role)
SELECT p.id, 'team@contexta.local', 'Contexta Team', 'reviewer'
FROM   core.practices p
WHERE  p.name = 'Contexta Team'
  AND  NOT EXISTS (SELECT 1 FROM core.users u WHERE u.email = 'team@contexta.local');
