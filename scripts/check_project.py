"""Dependency-free structural checks for the IISAT QR source tree."""

from __future__ import annotations

import compileall
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "presenceqr"


def check_python_syntax() -> None:
    if not compileall.compile_dir(str(PACKAGE), quiet=1):
        raise SystemExit("Python syntax check failed.")
    if not compileall.compile_file(str(ROOT / "run.py"), quiet=1):
        raise SystemExit("run.py syntax check failed.")
    if not compileall.compile_file(str(ROOT / "wsgi.py"), quiet=1):
        raise SystemExit("wsgi.py syntax check failed.")


def route_function_names() -> set[str]:
    route_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((PACKAGE / "routes").glob("*.py"))
    )
    return set(re.findall(r"^def\s+(\w+)\(", route_source, re.MULTILINE))


def check_template_endpoints() -> None:
    functions = route_function_names()
    missing: list[tuple[str, str]] = []

    for template in sorted((PACKAGE / "templates").glob("*.html")):
        text = template.read_text(encoding="utf-8")
        for match in re.finditer(
            r"url_for\(\s*['\"]main\.([\w_]+)['\"]",
            text,
        ):
            endpoint = match.group(1)
            if endpoint not in functions:
                missing.append((template.name, endpoint))

    if missing:
        details = ", ".join(f"{file}: main.{endpoint}" for file, endpoint in missing)
        raise SystemExit(f"Missing template endpoint(s): {details}")


def main() -> None:
    check_python_syntax()
    check_template_endpoints()
    print("IISAT QR structural checks passed.")


if __name__ == "__main__":
    main()
