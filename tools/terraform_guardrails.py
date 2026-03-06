#!/usr/bin/env python3
import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Finding:
    severity: str  # ERROR | WARN | INFO
    rule_id: str
    message: str
    path: str | None = None


def add(findings: list[Finding], severity: str, rule_id: str, message: str, path: Path | None = None) -> None:
    findings.append(
        Finding(
            severity=severity,
            rule_id=rule_id,
            message=message,
            path=str(path.relative_to(REPO_ROOT)) if path else None,
        )
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def summarize(findings: list[Finding]) -> dict:
    return {
        "errors": sum(1 for f in findings if f.severity == "ERROR"),
        "warnings": sum(1 for f in findings if f.severity == "WARN"),
        "info": sum(1 for f in findings if f.severity == "INFO"),
    }


def check_gitignore_job_files(findings: list[Finding]) -> None:
    ignore = REPO_ROOT / ".gitignore"
    if not ignore.exists():
        add(findings, "WARN", "gitignore.missing", ".gitignore is missing; add rules for artifacts and private inputs.")
        return
    if ".[0-9][0-9]_*.txt" not in read_text(ignore):
        add(findings, "WARN", "gitignore.job_descriptions", "Add a .gitignore rule to prevent committing job description .txt files.", ignore)


def check_required_docs(findings: list[Finding]) -> None:
    required = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "architecture" / "ADR-0001-repo-goal.md",
        REPO_ROOT / "docs" / "security" / "threat-model.md",
        REPO_ROOT / "docs" / "ops" / "slo.md",
    ]
    for p in required:
        if not p.exists():
            add(findings, "ERROR", "docs.required", "Required documentation file is missing.", p)


def tf_files() -> list[Path]:
    return sorted(REPO_ROOT.rglob("*.tf"))


def check_terraform_blocks(findings: list[Finding]) -> None:
    files = tf_files()
    if not files:
        add(findings, "ERROR", "tf.none", "No Terraform (*.tf) files found in the repo.")
        return

    combined = "\n".join(read_text(p) for p in files)
    if "terraform {" not in combined:
        add(findings, "ERROR", "tf.terraform_block", "Terraform files found but no terraform{} blocks detected.")

    if "required_version" not in combined:
        add(findings, "WARN", "tf.required_version", "Define terraform.required_version to reduce drift.")

    if "required_providers" not in combined:
        add(findings, "WARN", "tf.required_providers", "Define terraform.required_providers with pinned provider versions.")

    for p in files:
        text = read_text(p)
        if re.search(r'(?i)\\b(password|secret|token|private_key)\\b\\s*=\\s*\"[^\"]+\"', text):
            add(findings, "ERROR", "tf.hardcoded_secret", "Possible hardcoded secret detected; use variables/secret managers.", p)


def check_provider_version_pinning(findings: list[Finding]) -> None:
    files = tf_files()
    combined = "\n".join(read_text(p) for p in files)
    for m in re.finditer(r'required_providers\\s*\\{([\\s\\S]*?)\\n\\s*\\}', combined):
        block = m.group(1)
        providers = re.findall(r'(?m)^\\s*([a-zA-Z0-9_]+)\\s*=\\s*\\{([\\s\\S]*?)\\n\\s*\\}', block)
        for name, body in providers:
            if re.search(r'(?m)^\\s*version\\s*=\\s*\"', body) is None:
                add(findings, "WARN", "tf.provider_version", f"Provider '{name}' should pin a version constraint.", None)


def check_examples_are_safe(findings: list[Finding]) -> None:
    example = REPO_ROOT / "infra" / "examples" / "dev" / "main.tf"
    if not example.exists():
        add(findings, "WARN", "tf.example_missing", "Expected Terraform example missing at infra/examples/dev/main.tf.", example)
        return
    text = read_text(example)
    if "owner" not in text:
        add(findings, "WARN", "tf.owner", "Terraform examples should include an owner attribution variable/tag.", example)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline, deterministic Terraform/IaC guardrails for this repo.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--out", default="", help="Write output to a file (optional).")
    args = parser.parse_args()

    findings: list[Finding] = []
    check_required_docs(findings)
    check_gitignore_job_files(findings)
    check_terraform_blocks(findings)
    check_provider_version_pinning(findings)
    check_examples_are_safe(findings)

    report = {"summary": summarize(findings), "findings": [asdict(f) for f in findings]}

    if args.format == "json":
        output = json.dumps(report, indent=2, sort_keys=True)
    else:
        lines = []
        for f in findings:
            where = f" ({f.path})" if f.path else ""
            lines.append(f"{f.severity} {f.rule_id}{where}: {f.message}")
        lines.append("")
        lines.append(f"Summary: {report['summary']}")
        output = "\n".join(lines)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

