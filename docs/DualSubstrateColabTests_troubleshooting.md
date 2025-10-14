# DualSubstrateColabTests Notebook Import Error

## Symptom
Running the `DualSubstrateColabTests.ipynb` notebook fails in the cell that imports `DualSubstrateGenerator` from `dual_substrate_adapter.py`. The stack trace ends with:

```
ModuleNotFoundError: No module named 'p_adic_memory'
```

## Root cause
The adapter script (`dual_substrate_adapter.py`) imports `DualSubstrateMemory` from the `p_adic_memory` package. Although the notebook previously installs the package in editable mode and exports `PYTHONPATH` inside a notebook cell, that environment configuration does **not** persist to the separate Python process that executes `dual_substrate_adapter.py` during the import. As a result, the interpreter that runs the adapter script cannot resolve the `p_adic_memory` package that lives under `/content/p-adic-memory/src`, and the import fails.

## Fix
Ensure the adapter script extends `sys.path` itself before attempting to import `p_adic_memory`. Adding the following snippet at the top of `/content/dual_substrate_adapter.py` (before importing `p_adic_memory`) makes the module discovery explicit and reliable across notebook cells:

```python
import os
import sys

SRC_PATH = "/content/p-adic-memory/src"
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)
```

Alternatively, you can insert the same logic in any notebook cell *before* importing `DualSubstrateGenerator`. What matters is that the process that runs the adapter code updates its `sys.path` to include the package's `src` directory.

After making this change, rerun the cell that imports `DualSubstrateGenerator` and the import should succeed.
