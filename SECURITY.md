# Security Policy

Tiny Detective AI is a solo-maintained portfolio project, not a project with a formal security team or bug bounty program — but real vulnerability reports are still very welcome and will be taken seriously.

## Reporting a Vulnerability

Please report security issues privately, not via a public GitHub issue: email **thombog.inv@gmail.com** with a description of the issue, steps to reproduce, and (if relevant) which component is affected — `services/api` (backend), `apps/game` (Flutter frontend), or `tools/ai-content` (offline AI content pipeline).

Expect an initial response within a few days. This is a single-maintainer project, not a 24/7 operation — response times will reflect that, but every report will get a real reply.

## Scope

In scope: the code in this repository (`services/api`, `apps/game`, `tools/ai-content`) and its deployment configuration (`.github/workflows/`, `Dockerfile`, `firebase.json`).

Out of scope: vulnerabilities in third-party dependencies themselves (report those upstream — this project runs automated dependency scanning, see `docs/operations.md` and `.github/workflows/ci.yml`'s `dependency-audit` job); the underlying infrastructure providers (Google Cloud, Firebase, OpenAI) — report those directly to the respective provider.

## What This Project Already Does

For context before reporting something that might already be a known, accepted trade-off: this project documents its security posture in depth, including known limitations stated explicitly rather than silently — see `docs/deployment.md`'s "Verified Live" and "Secrets and IAM" sections, `docs/scalability.md`'s "Known Limitations" section, and the architecture-decision records under `docs/architecture-decisions/` (particularly ADR-0006's amendment on rate limiting and X-Forwarded-For handling). If something looks like a gap, it may already be a documented, deliberate MVP-scope trade-off rather than an oversight — worth a quick look there first, though a report is still welcome if you think the trade-off itself is wrong.
