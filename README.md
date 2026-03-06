# 29-aws-reliability-security-terraform

A portfolio-grade repository focused on **Terraform hygiene for reliable infrastructure delivery**:
deterministic guardrails, CI-friendly checks, and production-safe validation flows.

This repository is intentionally generic (no employer branding). It demonstrates practical DevSecOps habits for IaC.

## The 3 core problems this repo solves
1) **IaC correctness and drift control:** clear version pinning and deterministic formatting/validation steps.
2) **Security-minded IaC hygiene:** guardrails that catch common secret and configuration mistakes early.
3) **Production-safe validation:** explicit test modes separating offline checks from real Terraform integration runs.

## Tests (two explicit modes)

This repo supports exactly two test modes via `TEST_MODE`:

- `TEST_MODE=demo` (default): offline-only guardrails (no Terraform binary required)
- `TEST_MODE=production`: real Terraform integration checks (requires Terraform + provider downloads)

Run demo mode:

```bash
make test-demo
```

Run production mode:

```bash
make test-production
```

If provider download fails, production mode prints explicit guidance (network access or provider mirrors).

## Terraform guardrails

The file `tools/terraform_guardrails.py` runs deterministic checks over `*.tf` files:
- `required_version` presence
- `required_providers` and provider version pinning
- basic secret-pattern detection (hardcoded `password`, `token`, etc.)

Generate a JSON evidence artifact:

```bash
python3 tools/terraform_guardrails.py --format json --out artifacts/terraform_guardrails.json
```

## Sponsorship and contact

Sponsored by:
CloudForgeLabs  
https://cloudforgelabs.ainextstudios.com/  
support@ainextstudios.com

Built by:
Freddy D. Alvarez  
https://www.linkedin.com/in/freddy-daniel-alvarez/

For job opportunities, contact:
it.freddy.alvarez@gmail.com

## License

Personal, educational, and non-commercial use is free. Commercial use requires paid permission.
See `LICENSE` and `COMMERCIAL_LICENSE.md`.
