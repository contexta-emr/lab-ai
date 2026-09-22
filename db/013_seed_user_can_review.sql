-- =============================================================================
-- Contexta - Lab extraction store
-- 013  The seeded user can actually review
-- =============================================================================
-- Run after 012.
--
-- THE BUG, AS SEEN IN THE CONSOLE
--   Clicking Confirm on a document returned
--
--       This action needs a reviewer or clinician role
--
--   db/005 seeds idp.seed@contexta.local with role 'service'. app/auth.py
--   grants review to 'admin', 'reviewer' and 'clinician' only, and quite
--   right too - a service account exists to move data, not to decide that a
--   lab result belongs to a patient. But it left the only account anyone can
--   log in with unable to do the one thing the console is for.
--
--   So the fix is a second account, not a wider service account. The service
--   user keeps the role it should have.
--
-- NO PASSWORD HERE
--   password_hash stays NULL, exactly as 005 leaves it, and
--   scripts/set_password.py sets one. A migration is committed to the
--   repository and applied to every database it ever touches; a credential
--   in one is the incident contexta-emr already has on record.
--
--       python scripts/set_password.py reviewer@contexta.local
-- =============================================================================

INSERT INTO core.users (practice_id, email, full_name, role)
SELECT p.id, 'reviewer@contexta.local', 'Demo Reviewer', 'reviewer'
FROM   core.practices p
WHERE  p.name = 'Contexta Demo Clinic'
  AND  NOT EXISTS (SELECT 1 FROM core.users u
                   WHERE u.email = 'reviewer@contexta.local');

COMMENT ON TABLE core.users IS
  'Local POC accounts. idp.seed@contexta.local is the service account used by '
  'the loaders and has role service, which deliberately cannot verify a '
  'document. reviewer@contexta.local exists so a human can. Both ship without '
  'a password; scripts/set_password.py sets one per database.';
