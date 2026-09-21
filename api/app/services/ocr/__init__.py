"""OCR engines, copied verbatim from the idp workspace.

Source: ../VectorDB_Analysis/idp/code/src/idp/engines/
Only the intra-package import lines were changed (idp.engines.X -> .X);
nothing else was touched, so these stay diffable against the originals and
against the 18 test files that live beside them there.

paddle_vl is imported for one function, normalise_page_result. It does not
pull paddlepaddle at import time - the 2 GB dependency is deferred - so
importing this package is cheap.
"""
