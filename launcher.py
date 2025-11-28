# launcher.py
  from src.ops import run_preflight
  
  # ops_health_service.py
  from src.ops import send_ops, send_health, send_crack, guard_engine
  
  # Possibly in src/__init__.py
  from .ops_notify import ...
```
- **ROOT_CAUSE**: Import paths don't match actual module structure. If `ops_notify` is a separate module from `ops`, imports need to reflect that. Mixing `src.ops` and `.ops_notify` suggests confusion about module organization.
- **IMPACT**: **BLOCKER**. ImportError on module load.
- **PRIMARY FIX**: Standardize on one import pattern and ensure module structure matches. If using package structure (`src/ops/`), all imports should use either `from src.ops import X` or `from .ops import X` (for relative imports within `src/`).
- **RISK LEVEL**: **BLOCKER**

### CRACK_004_REVISED
- **CRACK_ID**: AIRTABLE_EXCEPTION_CLASSES_MISSING
- **TYPE**: IMPORT
- **LOCATION**: `src/__init__.py` and `main.py`
- **SYMPTOMS**:
```
  ImportError: cannot import name 'AirtableSchemaError' from 'src.common.airtable_client'
