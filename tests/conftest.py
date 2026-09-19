"""Make the tests import the code the way Lambda does.

`template.yaml` sets `CodeUri: backend/` for both functions, so in the deployed
package `shared`, `router` and `agent_runner` are all top-level — which is why
the Lambdas say `from shared import scheduler` rather than anything relative.
Putting `backend/` on the path reproduces that layout exactly, so a patch
target in a test names the same module object the deployed code imports.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
