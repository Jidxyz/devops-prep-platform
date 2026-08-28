# DevOps Interview Preparation

A self-assessment capability matrix for senior platform and DevOps engineering
interviews, with a full answer key for every item.

**1705 capabilities across 15 domains.** Every matrix item has a corresponding
answer covering what a strong response includes — the reasoning, the tradeoffs,
and the failure modes that signal real experience.

## How to use it

1. **Score yourself against the matrix first.** Each item is 0–2:
   - **0** — couldn't answer it
   - **1** — could answer roughly, not confidently
   - **2** — could answer under interview pressure
2. **Read only the items you scored 0 or 1.** The keys are long; reading them
   end to end produces recognition rather than recall.
3. **Re-score after reading.** The scoring summary at the end of each matrix
   domain gives you a total to track.

Each answer key ends with a **"Using this key"** section naming which of its
items carry the most weight for a platform role, and which failure modes are the
ones that read as genuine experience.

## Contents

| # | Domain | Items | Answer key |
|---|---|---|---|
| 1 | Git | 152 | [`01-git.md`](./answer-keys/01-git.md) |
| 2 | Linux | 98 | [`02-linux.md`](./answer-keys/02-linux.md) |
| 3 | Networking | 86 | [`03-networking.md`](./answer-keys/03-networking.md) |
| 4 | AWS | 166 | [`04-aws.md`](./answer-keys/04-aws.md) |
| 5 | Troubleshooting & Incident Response | 65 | [`05-troubleshooting-incident-response.md`](./answer-keys/05-troubleshooting-incident-response.md) |
| 6 | Security, PKI & Certificates | 97 | [`06-security-pki.md`](./answer-keys/06-security-pki.md) |
| 7 | Docker & Containers | 103 | [`07-docker.md`](./answer-keys/07-docker.md) |
| 8 | Kubernetes | 136 | [`08-kubernetes.md`](./answer-keys/08-kubernetes.md) |
| 9 | Databases | 129 | [`09-databases.md`](./answer-keys/09-databases.md) |
| 10 | Messaging, Queues & Streaming | 113 | [`10-messaging.md`](./answer-keys/10-messaging.md) |
| 11 | Terraform & Infrastructure as Code | 137 | [`11-terraform.md`](./answer-keys/11-terraform.md) |
| 12 | CI/CD, Release & Deployment | 109 | [`12-cicd.md`](./answer-keys/12-cicd.md) |
| 13 | GitHub Actions | 88 | [`13-github-actions.md`](./answer-keys/13-github-actions.md) |
| 14 | Jenkins | 81 | [`14-jenkins.md`](./answer-keys/14-jenkins.md) |
| 15 | Observability, Performance & Reliability | 145 | [`15-observability.md`](./answer-keys/15-observability.md) |
| | **Total** | **1705** | |

- [`devops-interview-skills-question-matrix.md`](./devops-interview-skills-question-matrix.md) — the matrix itself: all 1,705 questions with blank score and notes columns, plus a scoring summary per domain.
- [`web/`](./web) — three browser-based drill apps over the same data. Single HTML files, no build step. See [`web/README.md`](./web/README.md).

## Conventions

- Items are prefixed per domain (`A1.1` AWS, `K9.4` Kubernetes, `TF3.6` Terraform,
  and so on). Git uses unprefixed numbering (`1.1`).
- Cross-references between domains use those prefixes, so `(DB7.3)` in the CI/CD
  key points at expand-contract migrations in the Databases key. They are dense
  and deliberate — interviewers move between domains constantly.
- Answers describe *what a good response covers*, not a script to recite.
- Where an item is judgement rather than fact, the answer gives the reasoning
  and the tradeoff, because that is what is being assessed.

## Scope notes

Some topics deliberately live in one domain and are referenced from others
rather than duplicated:

- TLS debugging is in Networking; PKI as a system is in Security.
- Image scanning and artifact signing are in Security, not Docker.
- Terraform pipelines are in Terraform; delivery practice is in CI/CD.
- AWS-managed database configuration is in AWS; engine internals are in Databases.
