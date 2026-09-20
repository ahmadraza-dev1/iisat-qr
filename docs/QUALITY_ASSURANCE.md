# Quality assurance

The professional reorganization was performed with the rule that application
features and endpoint behavior must remain unchanged.

## Checks completed during handoff

- All Python source files compile successfully.
- The reorganized route package exposes the same 40 HTTP route definitions as
  the supplied final project.
- Template `main.*` endpoint references were checked against route functions;
  no missing endpoint references were found.
- `render.yaml` parses as valid YAML locally.
- Cache/build artifacts (`__pycache__`, `.pyc`, pytest cache) were removed.
- Database model table/column/constraint names were preserved for compatibility.
- Existing default development credentials were preserved.
- Existing QR, roster, correction, audit, analytics, report, term, teacher, and
  course workflows were retained.

## Quick structural check

Run without installing extra developer tools:

```bash
python scripts/check_project.py
```

## Full runtime regression tests

After installing project dependencies:

```bash
pip install -r requirements.txt
pytest -q
```

The delivery environment used for the reorganization did not have internet
package access, so Flask/Werkzeug could not be installed there for a full
runtime pytest execution. The dependency-free structural checks above were run
successfully. Run `pytest -q` once in your VS Code virtual environment before
publishing a live university deployment.
