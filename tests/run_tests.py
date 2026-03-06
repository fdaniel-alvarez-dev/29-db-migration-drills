#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def fail(message: str, *, output: str | None = None, code: int = 1) -> None:
    print(f"FAIL: {message}")
    if output:
        print(output.rstrip())
    raise SystemExit(code)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {path}", output=str(exc))
    return {}


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        fail(f"Missing {description}: {path}")


def demo_mode() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ARTIFACTS_DIR / "terraform_guardrails.json"

    guardrails = run([sys.executable, "tools/terraform_guardrails.py", "--format", "json", "--out", str(report_path)])
    if guardrails.returncode != 0:
        fail("Terraform guardrails failed (demo mode must be offline).", output=guardrails.stdout)

    report = load_json(report_path)
    if report.get("summary", {}).get("errors", 0) != 0:
        fail("Terraform guardrails reported errors.", output=json.dumps(report.get("findings", []), indent=2))

    require_file(REPO_ROOT / "NOTICE.md", "NOTICE.md")
    require_file(REPO_ROOT / "COMMERCIAL_LICENSE.md", "COMMERCIAL_LICENSE.md")
    require_file(REPO_ROOT / "GOVERNANCE.md", "GOVERNANCE.md")

    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8", errors="replace")
    if "it.freddy.alvarez@gmail.com" not in license_text:
        fail("LICENSE must include the commercial licensing contact email.")

    print("OK: demo-mode tests passed (offline).")


def production_mode() -> None:
    if os.environ.get("PRODUCTION_TESTS_CONFIRM") != "1":
        fail(
            "Production-mode tests require an explicit opt-in.",
            output=(
                "Set `PRODUCTION_TESTS_CONFIRM=1` and rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    if shutil.which("terraform") is None:
        fail(
            "terraform is required for production-mode tests.",
            output="Install Terraform and rerun production mode.",
            code=2,
        )

    ran_external_integration = False

    example_dir = REPO_ROOT / "infra" / "examples" / "dev"
    if not example_dir.exists():
        fail("Terraform example directory missing.", output=str(example_dir))

    init = run(["terraform", "init", "-backend=false"], cwd=example_dir)
    if init.returncode != 0:
        fail(
            "terraform init failed (provider download is a real external dependency).",
            output=(
                "Ensure you have network access to download providers, or configure a provider mirror.\n\n"
                + init.stdout
            ),
            code=2,
        )
    ran_external_integration = True

    fmt = run(["terraform", "fmt", "-check", "-recursive"], cwd=REPO_ROOT)
    if fmt.returncode != 0:
        fail("terraform fmt -check failed.", output=fmt.stdout)

    validate = run(["terraform", "validate"], cwd=example_dir)
    if validate.returncode != 0:
        fail("terraform validate failed.", output=validate.stdout)

    if not ran_external_integration:
        fail("No external integration checks were executed in production mode.", code=2)

    print("OK: production-mode tests passed (Terraform integration executed).")


def main() -> None:
    mode = os.environ.get("TEST_MODE", "demo").strip().lower()
    if mode not in {"demo", "production"}:
        fail("Invalid TEST_MODE. Expected 'demo' or 'production'.", code=2)

    if mode == "demo":
        demo_mode()
        return

    production_mode()


if __name__ == "__main__":
    main()

