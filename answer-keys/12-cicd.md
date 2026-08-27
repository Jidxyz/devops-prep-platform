# CI/CD, Release & Deployment — Answer Key

Companion to Domain 12 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: this domain is **deliberately tool-agnostic** — GitHub Actions and Jenkins are separate implementation domains. **Terraform pipelines are TF9** and **database migration sequencing is DB7**; where a topic overlaps, the answer covers the delivery-practice half and points there for the mechanics.

Three notes on how this domain is interviewed:

- **This is the most "opinions with reasons" domain in the matrix.** Very little of it is factual recall — almost every item is a design or judgement question, and the answers that score well are the ones that name a tradeoff and take a position. Reciting definitions of blue/green and canary is a mid-level answer; explaining when each is wrong is a senior one.
- **C7, C9, and C12 carry the most weight for a senior or lead role.** Deployment strategy selection, rollback under pressure, and the organisational reasons delivery improvements fail are where the interview goes once the basics are established.
- **C11 is worth rehearsing with numbers.** DORA metrics come up constantly, and the strong answer is not the four names but the argument in C11.2 — that frequency and stability move together — plus a case made in business terms (C11.7).

---

## C1. Fundamentals

**C1.1 — Continuous integration as a practice**

**CI is the practice of every developer integrating their work into a shared mainline frequently — at least daily — with each integration verified by an automated build and test.**

**The tool is not the practice.** A team running Jenkins on a repository where feature branches live for three weeks is not doing CI; they're doing automated builds on branches. **The defining behaviour is the frequency of integration into the shared trunk**, and the automation exists to make that frequent integration safe.

**What the practice actually requires:**

- **A shared mainline everyone integrates into**, at least daily (C1.3).
- **An automated build and test suite** that runs on every integration and gives a clear pass/fail.
- **A fast enough build** that people don't avoid it (C1.5).
- **A broken build is the top priority** — the team stops and fixes it, because a broken mainline blocks everyone.
- **Everyone can see the state** of the build.

**Why it matters — the problem it solves**: integration is where conflicts, incompatible assumptions, and interface mismatches surface. **Deferring integration doesn't avoid that work, it concentrates it** into a painful, unpredictable merge at the end (C1.4, C1.9). Integrating continuously means conflicts are small, discovered immediately, and cheap to resolve.

**The tell in an interview**: someone who says "we have CI, we use GitLab CI" has described a tool. Someone who says "we merge to trunk at least daily behind flags, and a red build stops the line" has described the practice.

**C1.2 — Continuous delivery vs continuous deployment**

- **Continuous delivery** — **every change that passes the pipeline is *deployable* to production.** The artefact is built, tested, and ready; **the decision to release is a business one, and it's a button someone presses.**
- **Continuous deployment** — **every change that passes the pipeline *is* deployed to production, automatically, with no human gate.**

**The difference is one manual step**, and the technical requirements are almost identical — which is the point worth making. **If you have genuine continuous delivery, continuous deployment is a configuration change.** If you can't deploy on demand within minutes, you don't have continuous delivery either, regardless of what the pipeline does.

**Why the distinction matters practically:**

- **Continuous delivery is achievable almost everywhere**, including regulated environments (C6.6, C10.8), because the approval gate is preserved.
- **Continuous deployment requires very high confidence in the automated verification** — the tests, the progressive rollout, and the automated rollback are the only things between a commit and production (C8.5, C9.5).
- **The gate has a cost** (C10.2): batching changes behind a manual approval increases batch size (C1.9), which increases risk per deployment — **so the gate intended to reduce risk can increase it** if it causes changes to accumulate.

**The position to hold**: **continuous delivery is the goal for essentially every team.** Continuous deployment is appropriate where the blast radius is manageable and the automated verification is genuinely trusted, and inappropriate in the cases in C12.1.

**C1.3 — Trunk-based development and its relationship to CI**

**Trunk-based development**: all developers work from a single shared branch (`main`), committing directly or through **very short-lived branches — hours to a day, not weeks.** Releases are cut from trunk, or from short-lived release branches.

**The relationship to CI is definitional**: **CI means integrating continuously, and you cannot integrate continuously if your work lives on a branch for two weeks.** Trunk-based development is what makes CI possible; **CI is what makes trunk-based development safe.** They're the same practice viewed from two angles, and a team claiming CI with long-lived feature branches has one without the other.

**What it requires to work:**

- **Feature flags** (C8.1) — so incomplete work can be merged to trunk without being active. **This is the enabling mechanism**, and without it the argument for long branches becomes hard to answer.
- **A comprehensive, fast automated test suite** — trunk must always be releasable.
- **Small changes** (C1.9).
- **Branch by abstraction** for larger refactors — introduce an abstraction layer, migrate behind it incrementally, remove the old path.
- **A culture where breaking trunk is taken seriously.**

**The comparison to GitFlow, since it's the usual counterpoint**: GitFlow's long-lived `develop`, `release`, and feature branches were designed for versioned software with scheduled releases and multiple supported versions. **For a continuously-deployed service it introduces merge overhead and delays integration for no benefit** — and the DORA research consistently associates trunk-based development with higher performance on all four metrics (C11.1).

**C1.4 — Why long-lived branches undermine integration**

**The mechanism:**

- **Divergence compounds.** Every day a branch lives, trunk moves and the branch moves, and the distance between them grows non-linearly — **merge difficulty grows faster than branch age**, because changes interact.
- **Conflicts are discovered late**, all at once, at the worst time — when the feature is "finished" and there's pressure to ship. **The integration work is the same work; it's just concentrated into an unpredictable block.**
- **Semantic conflicts don't show as merge conflicts.** Two branches can merge cleanly and be logically incompatible — one renames a concept, the other adds a caller of the old behaviour. **Git cannot detect this**, so it surfaces as a runtime bug after a clean merge.
- **CI on the branch is testing a fiction** — the branch plus its own tests, not the branch integrated with everything else that has landed since.
- **Large batches** (C1.9) — a three-week branch is a large, high-risk change with many possible causes when it breaks.
- **Refactoring is discouraged**, because a large refactor conflicts with every open branch, so the team stops improving the codebase.

**The counter-argument to address**: "we need branches for code review." **Review is not the problem — branch lifetime is.** A branch open for four hours gets the same review as one open for three weeks; **small, frequent PRs get better review**, because a 2,000-line PR is not genuinely reviewed by anyone.

**The resolution: small PRs merged daily, incomplete work behind flags** (C8.1). That preserves review and removes the divergence cost.

**C1.5 — Fast feedback, with a number**

**The number that matters: 10 minutes** for the commit-to-feedback loop. That's the widely-cited target, and the reasoning behind it is more useful than the figure.

**Why the number matters:**

- **Under about 10 minutes, a developer waits for the result.** They stay in context, and if it fails they fix it immediately with the change fresh.
- **Beyond that, they context-switch** to something else. **The cost is not the wait — it's the switch back**, which research puts at 15–25 minutes to regain full context. **So a 20-minute build costs far more than 20 minutes.**
- **Beyond about 30 minutes, people batch changes** to avoid the wait, which increases batch size and risk (C1.9) — **the slow pipeline actively degrades the practice it exists to support.**
- **Beyond an hour, people stop running it before pushing**, work around it, and treat failures as noise.

**The arithmetic to have ready** (C2.11): 20 engineers, 5 pipeline runs a day each, 15 minutes of avoidable wait per run = **25 engineer-hours per day**. At a loaded cost that's a straightforward business case for optimisation work.

**The refinement**: not all feedback needs to be in 10 minutes. **Structure it in tiers** (C2.2): lint and unit tests in 2 minutes, integration in 10, the full end-to-end suite asynchronously after merge. **The 10-minute target applies to the feedback that gates a merge**, not to everything.

**C1.6 — Build once, promote everywhere**

**The principle: the pipeline produces one immutable artefact, and that exact artefact is promoted through every environment to production** (C3.4, D8.8).

**Why rebuilding per environment is wrong:**

- **A rebuild can produce a different artefact.** A floating base image tag updated (D2.15), a dependency resolved differently (S7.2), a different builder or toolchain version, a transient network failure changing what was fetched. **So the thing you tested in staging is provably not the thing running in production** — which invalidates the testing, which was the entire point of having staging.
- **Traceability is lost** — several artefacts for one commit, and "what's running" becomes ambiguous (C3.8).
- **Signatures and attestations are per-artefact** (S7.7) — a rebuild invalidates them, so admission-time verification fails or has to be redone per environment.
- **It's slower**, and it multiplies the surface for a build-time supply chain attack (S7.1).

**The corollary that makes it work: configuration must be injected at runtime** (C5.3, D4.10). **If you have to rebuild to change an endpoint or a feature flag, you cannot promote** — so the artefact must be environment-agnostic, and that's a design constraint on the application, not just on the pipeline.

**The practical test to offer**: **take the digest of what's in production and confirm it's byte-identical to what passed staging.** If you can't, you're rebuilding somewhere, possibly without realising it.

**C1.7 — Reproducible builds and what breaks them**

**The goal: the same source at the same commit produces a functionally identical artefact, whenever and wherever it's built.**

**What breaks it:**

- **Floating dependency versions** — `^4.2.0`, `latest`, unpinned `apt-get install` (S7.2, D2.15). **The most common cause.**
- **Unpinned base images** — `FROM node:20` resolves differently over time (D2.15).
- **Network fetches at build time** — `curl | sh` gets whatever is there now.
- **Build environment differences** — a different compiler version, OS, or locale between a developer's machine and CI (D10.11).
- **Timestamps and build metadata** embedded in the output, which break bit-for-bit reproducibility though not functional equivalence.
- **Non-deterministic ordering** — file system iteration order, map iteration, parallel compilation producing different link order.
- **Build cache differences** (D3.3).

**The fixes**: lockfiles committed and installed from exactly (`npm ci`, `--require-hashes`); base images pinned by digest with automated update PRs (D2.15, S7.2); checksums on anything fetched; **build in CI as the source of truth**, not locally; and `SOURCE_DATE_EPOCH` if bit-for-bit matters.

**The distinction worth drawing**: **functional reproducibility** (behaves identically) is the practical target and is achievable with discipline. **Bit-for-bit reproducibility** is a much higher bar, relevant for high-assurance supply chain work (S7.12) and rarely necessary otherwise. **Claiming the second when you mean the first is a common overstatement.**

**C1.8 — What "done" means when delivery is continuous**

**With scheduled releases, "done" could mean "merged" and the release was a separate later event.** With continuous delivery, that definition breaks — a merged change is minutes from production.

**A workable definition of done:**

- **Merged to trunk** and the pipeline is green.
- **Deployed to production** — because if it isn't, it's inventory, not value, and the risk is still outstanding.
- **Released to at least some users** (which with flags may be a subset, C8.7), or explicitly deferred as a business decision.
- **Verified in production** — the metrics show it working, not just deployed (C4.8).
- **Observable** — logs, metrics, and alerts exist for the new behaviour (O1.6).
- **Documented** where it affects others, and the **feature flag removed** if it was a release flag (C8.3).

**The shift in thinking**: **"done" moves from "the code is written" to "it is delivering value in production and we can see that it is."** That's a genuinely different bar, and it's what makes the DORA lead time metric measurable (C11.3).

**The organisational consequence to name**: this changes what a team commits to and how work is tracked. **A ticket closed at merge hides the remaining risk**; one closed at verified-in-production makes the whole path visible, which is what surfaces the delivery bottleneck (C11.6).

**C1.9 — Batch size and deployment risk**

**The relationship: risk per deployment scales super-linearly with batch size, and total risk over time scales with batch size too.**

**Why:**

- **More changes means more possible causes.** A deployment with one change that breaks has one suspect; one with fifty has fifty, and the interactions between them. **Diagnosis time grows disproportionately.**
- **Rollback is coarser.** Rolling back fifty changes to fix one reverts forty-nine good ones, which the business may refuse — **so you end up fixing forward under pressure** (C9.1).
- **Review quality degrades** with size — a 2,000-line PR is not genuinely reviewed.
- **Interactions between changes** are untested in combination.
- **Confidence is lower**, so the deployment gets more ceremony, which makes it rarer, which makes batches bigger. **A reinforcing loop, and it's the core dynamic to describe.**

**The counterintuitive conclusion that's worth stating explicitly**: **deploying more frequently is safer, not riskier.** Each deployment is smaller, so the blast radius per deployment is smaller and diagnosis is faster. **This is what the DORA research found** and it's the substance of C11.2.

**The practical levers**: trunk-based development (C1.3), feature flags to decouple merge from release (C8.1), small PRs, and **removing the friction that makes people batch** — a slow pipeline (C1.5), a heavy approval process (C10.2), or a deployment that requires a maintenance window.

---

## C2. Pipeline design

**C2.1 — Designing a pipeline's stages and justifying the ordering**

A representative pipeline, with the reason for each position:

```
On pull request:
  1. Lint + format check          ~30s    cheapest, catches the most trivial failures
  2. Unit tests                   ~3min   fast, isolated, high signal
  3. Build artefact               ~4min   must succeed before anything downstream
  4. SAST + dependency scan       ~2min   parallel with build where possible
  5. Integration tests            ~8min   needs the artefact and real dependencies
  6. Publish artefact (PR tag)    ~1min
  7. Deploy to ephemeral env      ~3min   optional, per-PR (C5.5)
  8. Smoke / contract tests       ~2min

On merge to main:
  9. Promote artefact             instant  same artefact, retagged (C1.6)
 10. Deploy to staging
 11. Post-deploy verification              (C4.8)
 12. [approval gate for prod]              (C10.2)
 13. Progressive deploy to prod            (C7.4)
 14. Automated canary analysis             (C8.5)
```

**The ordering principles:**

- **Cheapest and fastest first** (C2.2) — fail in 30 seconds rather than 15 minutes.
- **Highest-signal-per-second first** — unit tests catch most defects per minute spent.
- **Build once, early**, and everything downstream uses that artefact (C1.6, C3.1).
- **Dependencies dictate some ordering** — you can't test an artefact before building it.
- **Anything independent runs in parallel** (C2.3).
- **The expensive, slow, or flaky moves after merge** where it doesn't block a developer.
- **Gates where a human decision genuinely adds value** (C10.2), not everywhere.

**The justification to give**: **the pipeline's job is to reject a bad change as early and as cheaply as possible, and to make a good change's path to production frictionless.** Every stage should be defensible in those terms — and a stage that has never caught anything is a stage to remove (C4.5).

**C2.2 — Fail fast**

**Order stages by cost-to-run ascending and by probability-of-catching descending.** A lint failure found in 30 seconds costs 30 seconds; the same failure found after a 20-minute integration suite costs 20 minutes, plus the queue time, plus the developer's context switch (C1.5).

**The practices:**

- **Cheap static checks first** — formatting, linting, type checking, a config syntax check. Seconds, and they catch a real share of failures.
- **Unit tests before integration**, integration before end-to-end (C4.1).
- **Fail the whole pipeline on the first failing stage**, rather than running everything and reporting at the end — **unless** you deliberately want the full picture (see below).
- **Run the fast checks locally too** — a pre-commit hook catching lint failures means CI never sees them.
- **Order tests within a suite** so previously-failing and recently-changed tests run first, which surfaces failures sooner.

**The deliberate exception worth naming**: **sometimes you want all the results, not the first failure** — running lint, tests, and scans in parallel and reporting all outcomes means a developer fixes everything in one pass rather than discovering the next failure after each fix. **That's a better experience and costs more compute**, and it's a legitimate trade. **Fail-fast on the sequential dependency chain, run-all on the independent checks in parallel** is the usual resolution (C2.3).

**C2.3 — Parallelising stages, and what actually blocks**

**What can genuinely run in parallel**: independent test suites, linting alongside building, security scans alongside tests, multi-platform builds (D3.6), and per-service builds in a monorepo.

**What actually blocks:**

- **True dependencies** — you cannot test an artefact before it exists.
- **Shared mutable resources** — several jobs against one test database, or one Kubernetes namespace, will interfere. **This is the most common hidden serialisation**, and it usually manifests as flakiness rather than as an obvious block (C2.8).
- **Runner capacity.** Twenty parallel jobs on a pool of five runners is five at a time plus queueing. **Parallelism you don't have capacity for is queue time**, and pipeline queue time is the metric people forget to measure (C2.10).
- **Concurrency limits and locks** — a deployment lock, a state lock (TF9.4), a shared environment.
- **Licence or quota limits** on a tool.
- **The critical path.** Parallelising a 2-minute job alongside a 15-minute one saves nothing — **only shortening the longest path shortens the pipeline** (O14.5's Amdahl argument applied here).

**Test splitting** is the highest-value parallelisation for most pipelines: shard a long suite across N runners, ideally **balanced by historical duration** rather than by count, since a naive split leaves one shard dominating.

**The diagnostic to state**: **measure the critical path, not the total job time.** A pipeline of ten jobs totalling 40 minutes of compute might complete in 12 if the dependency graph allows — or in 40 if they're accidentally serialised.

**C2.4 — Caching without stale results**

**What's worth caching**: dependency downloads (npm, Maven, pip, Go modules), compiled intermediates, Docker layers (D3.5), and test fixtures.

**The design that avoids staleness:**

- **Key the cache on a hash of the dependency manifest** — `cache-key: deps-${{ hashFiles('package-lock.json') }}`. **A change to dependencies produces a different key, so a stale cache is impossible by construction.** This is the essential technique.
- **Restore-keys for partial hits** — fall back to a prefix match so a dependency change reuses most of the previous cache rather than starting empty.
- **Never cache build output keyed on something that doesn't capture all its inputs** — that's where genuinely wrong results come from.
- **Scope caches** — per branch with a fallback to main, so a poisoned or unusual branch cache doesn't affect everyone.
- **Expire caches** with a TTL, and give yourself a way to bust them manually (a version prefix in the key).

**The failure modes to name:**

- **A stale cache producing a passing build that shouldn't pass** — the dangerous one, because it's silent. Content-hash keys prevent it.
- **Cache restore taking longer than the work it saves** — genuinely common for small dependency sets. **Measure it.**
- **Cache poisoning as a security issue** (S7.10) — a cache shared between a fork PR and the base branch is an attack path. **Don't share caches across trust boundaries.**
- **Unbounded cache growth** consuming storage and cost.

**C2.5 — Pipeline as code, living with the application**

**The pipeline definition is a file in the application's repository, versioned with the code it builds.**

**Why it lives with the application:**

- **It changes with the code.** A new dependency, a new test command, a new deployment target — **the pipeline change and the code change are one atomic commit**, reviewed together and merged together.
- **A branch can have a different pipeline** — so you can change the build process in a PR and see it run before merging. **With a centrally-configured pipeline you cannot test a pipeline change without affecting everyone.**
- **History and review** — pipeline changes go through the same review as code, which matters because **the pipeline holds deployment credentials** (C10.4).
- **Reproducibility** — checking out an old commit gets you the pipeline that built it.
- **Self-service** — teams change their own pipeline without a ticket to a platform team (C12.3).

**The contrast with UI-configured pipelines**: Jenkins jobs configured through the web interface have no version control, no review, no history, and **no way to know who changed what or to roll back** — the same argument as dashboards-as-code (O7.6) and infrastructure-as-code (TF1.5).

**The tension to acknowledge** (C2.6): pipeline-as-code per repository means **duplication across many repositories**, and a change to a shared practice means editing N files. That's what reusable workflows and shared libraries solve — and the balance between the two is C2.6.

**C2.6 — Reusing pipeline logic without a monolith**

**The mechanisms** (tool-specific, same shape): GitHub reusable workflows and composite actions, GitLab `include` and templates, Jenkins shared libraries, Azure DevOps templates.

**The design that works:**

- **A shared repository of versioned, reusable workflows**, called by application repositories with parameters.
- **Version the shared workflows** and let consumers pin (`uses: acme/workflows/.github/workflows/build.yml@v3`) — **so a change to the shared logic doesn't break every repository simultaneously** (TF4.3's module versioning argument, applied identically).
- **Parameterise what genuinely varies**, not everything (TF4.5's over-abstraction warning).
- **Compose small pieces** rather than one giant configurable workflow (TF4.6).

**How it becomes a monolith, which is the failure to avoid:**

- **One workflow with forty inputs and nested conditionals** serving every team's special case. **Unreadable, untestable, and every change risks everyone.**
- **The platform team becomes the bottleneck** — every pipeline change needs their approval (C12.3, TF8.8).
- **No versioning**, so a change is instantly global.
- **Teams fork it** to escape, and now you have five divergent copies and no shared practice at all.

**The balance to articulate**: **share the parts that encode organisational decisions** — how to authenticate to the cloud (C10.3), how to publish an artefact, how to deploy, the security scanning baseline. **Leave the parts that are genuinely application-specific in the application's repository.** And **make contribution easy** — a team needing something the shared workflow doesn't do should be able to raise a PR, not wait in a queue (TF8.8).

**C2.7 — Ephemeral vs persistent build agents**

- **Ephemeral** — a fresh runner per job, destroyed afterwards. GitHub-hosted runners, Kubernetes-based runners, an autoscaled pool with single-use instances.
- **Persistent** — long-lived runners reused across jobs.

| | Ephemeral | Persistent |
|---|---|---|
| Isolation | **Strong** — no state carries between jobs | Weak — state, files, and processes persist |
| Reproducibility | **High** — every job starts identically | Lower — accumulated drift |
| Security | **Strong** — a compromised job doesn't affect the next (S7.10) | **A poisoned runner affects every subsequent job** |
| Speed | Slower — cold caches, image pulls each time | **Faster** — warm caches, warm Docker layers |
| Cost | Higher per job, zero when idle | Cheaper at high utilisation, paid when idle |
| Operational burden | Lower | Patching, disk, drift (D6.7) |

**The security argument is the decisive one for most organisations**: **a persistent runner is a shared trust boundary.** A malicious or compromised job can leave credentials, modify tooling, poison caches, or install a backdoor that affects every subsequent job — including jobs from other teams and other repositories (S7.9, S7.10).

**The resolution most people land on**: **ephemeral by default; persistent only where the warm-cache benefit is large and the trust boundary is controlled** — for example a dedicated persistent pool for one team's builds with no untrusted input, while everything touching fork PRs runs ephemeral. **Ephemeral plus a shared remote cache** (C2.4, D3.5) recovers most of the speed benefit without the shared state.

**C2.8 — What makes a pipeline flaky, and stabilising it**

**The causes:**

- **Test flakiness** — timing assumptions, race conditions, tests depending on execution order, unmocked external calls, and **shared mutable state between parallel tests** (C2.3).
- **Shared environments** — several pipeline runs against one test database or namespace, interfering with each other. **The most common infrastructure cause.**
- **External dependencies** — a third-party API, a package registry (rate limits, D8.7), a container registry.
- **Resource contention** — a runner short on memory or CPU causing timeouts under load, which makes failures load-dependent and therefore intermittent.
- **Network** — transient failures pulling dependencies or images.
- **Time and date** — tests that fail at month boundaries, in a different timezone, or on a leap day.
- **Cleanup failures** leaving residue that affects the next run.

**Stabilising it:**

1. **Measure it.** Track the failure rate per job and per test. **You cannot fix what you haven't quantified**, and the distribution is usually concentrated — a handful of tests cause most of it.
2. **Quarantine, don't ignore.** Move a known-flaky test to a non-blocking suite **with a ticket and an owner and a deadline** — because an unquarantined flaky test poisons trust in the whole suite (C4.4), and a quarantined one with no owner never comes back.
3. **Fix the root cause** — the usual answers are isolation (a fresh database per run, ephemeral environments), removing timing assumptions (poll for a condition rather than sleeping), and mocking external calls.
4. **Retry deliberately and visibly** — retrying an infrastructure step is reasonable; **retrying a test until it passes is hiding a bug**, and it must at minimum be recorded so the flakiness is visible.
5. **Isolate**: ephemeral environments (C5.5), ephemeral runners (C2.7), unique test data per run.

**The framing**: **flakiness is a trust problem** (C4.4). A pipeline that fails 10% of the time for no reason teaches people to re-run rather than investigate, **and then a real failure is re-run too.**

**C2.9 — Timeouts and concurrency controls**

**Timeouts** at every level:

```yaml
jobs:
  test:
    timeout-minutes: 15        # job level — always set one
    steps:
      - run: ./run-tests.sh
        timeout-minutes: 10    # step level for the risky step
```

**Why they matter**: without a timeout, a hung job **holds a runner indefinitely**, blocking the queue and consuming cost. **And in a Terraform or deployment context it holds a lock**, blocking everyone else (TF3.5, TF9.4). **Set a job timeout modestly above the p99 duration** — long enough not to kill legitimate slow runs, short enough that a hang is caught quickly.

**Concurrency controls:**

```yaml
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false     # deployments must not be cancelled
```

- **Cancel superseded PR runs** — a new push makes the previous run's result irrelevant, so cancelling saves capacity and time. `cancel-in-progress: true` for build and test.
- **Never cancel a deployment mid-flight** — that's how you get a partially-applied change (C9.7, TF9.4). `cancel-in-progress: false` for anything that mutates.
- **Serialise deployments per environment** — a concurrency group keyed on the environment prevents two deployments racing.
- **Serialise anything holding a lock** — Terraform state (TF9.4), a shared test environment.

**The related control**: **limits on total concurrent jobs** to avoid exhausting runner capacity or hitting a downstream rate limit — a hundred parallel jobs all pulling from Docker Hub will be rate-limited (D8.7).

**C2.10 — A pipeline's own observability**

**The pipeline is production infrastructure for the engineering team, and it should be monitored as such.**

**The metrics that matter:**

- **Duration**, as a distribution not a mean — p50 and p95 per job and for the whole pipeline. **The p95 is what people experience as "the build is slow."**
- **Queue time** — how long a job waited for a runner. **Frequently a larger share of total time than execution**, and it's the metric people forget to measure. Rising queue time means insufficient runner capacity (C2.3).
- **Failure rate per job**, and **the flaky rate** — failures that pass on re-run with no code change (C2.8).
- **Success rate on main** — a red mainline blocks everyone (C1.1).
- **Time to recover a red build.**
- **Frequency** — runs per day, which relates to batch size (C1.9).
- **Cost** — runner minutes, by team and by repository, which makes optimisation a fundable conversation (C2.11).
- **Cache hit rate** (C2.4).

**What to do with them:**

- **Alert on the mainline being red** for longer than a threshold.
- **Alert on rising queue time** — a leading indicator of capacity exhaustion.
- **Review the slowest and flakiest jobs** on a cadence, and act on the top offenders. **Flakiness and duration are both heavily concentrated**, so the 80/20 applies strongly.
- **Track the trend**, because pipelines degrade gradually — a test added here, a step added there — and nobody notices until it's 40 minutes.

**The framing to give**: **treat pipeline duration as an SLO** with an owner (O16.3's platform contract argument). Without measurement it degrades continuously, and the degradation is invisible because each increment is small.

**C2.11 — The cost of a slow pipeline in engineer-hours**

**The arithmetic, which is the point of the item:**

```
20 engineers × 5 pipeline runs/day × 15 minutes of avoidable wait
  = 25 engineer-hours per day
  = ~125 hours/week
  ≈ 3 full-time engineers' worth of time
```

**And that undercounts**, because:

- **Context switching** (C1.5) — a 20-minute wait doesn't cost 20 minutes, it costs the wait plus 15–25 minutes to regain context. **The real multiplier is closer to 2×.**
- **Batching behaviour** — slow pipelines cause people to batch changes (C1.9), which increases risk and makes failures harder to diagnose. **That cost is real and doesn't appear in the arithmetic.**
- **Reduced deployment frequency**, with the downstream effects on lead time and change failure rate (C11.1).
- **Morale and attrition** — waiting on a slow build is one of the most consistently cited engineering frustrations.

**How to use it**: **this is the business case for delivery investment** (C11.7). "We should optimise the pipeline" is a preference; "the pipeline costs us the equivalent of three engineers and two weeks of work would halve it" is a decision.

**The counterweight to be honest about**: runner cost is real, and buying more parallelism to reduce wall-clock time is a direct trade of infrastructure spend for engineer time. **At most organisations engineer time is the far more expensive resource**, and making that comparison explicit is usually enough to fund the runners.

---

## C3. Build & artifacts

**C3.1 — Immutable artefacts and why they're central**

**An immutable artefact is a build output that cannot change after creation and is identified by its content** — a container image referenced by digest (D8.2), a versioned JAR, a signed package.

**Why it's central to the whole model:**

- **It's what makes promotion meaningful** (C1.6, C3.4). Promoting a mutable thing promotes nothing — you can't be sure what you're promoting.
- **It's what makes rollback possible.** Rolling back means deploying a previous artefact, and that artefact must still exist and still be exactly what it was (C9.1).
- **It's what makes testing meaningful.** Tests passed against artefact X, and artefact X is what runs.
- **It's the unit of traceability** (C3.8) — from a running process back to a digest back to a commit.
- **It's the unit of signing and attestation** (S7.7) — a signature is over specific bytes.
- **It makes deployments idempotent and comparable** — "is production running the same thing as staging" is a digest comparison.

**What breaks immutability in practice**: mutable tags (D2.11, D8.2) — `myapp:latest` or even `myapp:v1.2` if the tag can be moved; artefacts assembled at deploy time; and configuration baked in at build so a "rebuild for prod" is required (C5.3).

**The enforcement**: **tag immutability in the registry** (A5.1), deployment by digest, and signature verification at admission (S7.7). Convention alone erodes.

**C3.2 — Versioning artefacts so deployment traces to a commit**

**The requirement: from a running instance, determine the exact commit that produced it — and from a commit, determine what artefact it produced.** Both directions.

**The mechanisms, used together:**

- **A tag containing the commit SHA** — `myapp:sha-a3f9c2b` (D8.4).
- **OCI labels** in the image recording the revision, source repository, version, and build time (D2.12) — **so the artefact is self-describing** and `docker inspect` answers the question without any external system.
- **A build-info endpoint** in the application exposing version, commit, and build time — **so a running instance answers for itself**, which is the most direct route during an incident.
- **A deployment record** — in GitOps, the manifest in git records the digest deployed (K10.7); otherwise the deployment system's history.
- **Provenance attestation** (C3.7, S7.12) recording the build inputs cryptographically.

**The version format for internal services**: a monotonic build number plus a commit SHA is often more useful than semantic versioning (C3.3) — `2026.08.22-a3f9c2b` or `1.4.2+a3f9c2b`. **The commit is the thing that matters for traceability; the human-readable part is for communication.**

**The test to apply**: **pick a running pod in production and, in under two minutes, produce the commit, the PR, and the person who approved it.** If you can't, the traceability chain is broken somewhere, and the gap is usually between the deployment and the artefact rather than between the artefact and the commit.

**C3.3 — Semantic versioning and its limits for internal services**

**SemVer** — `MAJOR.MINOR.PATCH`: major for breaking changes, minor for backwards-compatible additions, patch for fixes.

**Where it works well**: **published libraries and public APIs** with many unknown consumers who need to reason about upgrade safety from the version alone. **That's what it was designed for**, and it does it well.

**Its limits for internal services:**

- **A continuously-deployed service has no meaningful "release" to version.** Fifteen deployments a day producing 1.0.1 through 1.0.15 is a build counter with extra ceremony.
- **"Breaking" is ambiguous** for a service. Breaking for whom? An internal service with three known consumers has a different upgrade story from a public library — **you can just talk to them** (C6.8).
- **Consumers don't choose a version.** Nobody upgrades to your service's 2.0; they call your endpoint and get whatever is deployed. **The version communicates nothing to them.**
- **Determining the correct bump requires judgement**, and it's frequently done wrong or automated by commit message convention (C6.3), which is a proxy for the actual semantics.

**The alternatives for internal services:**

- **Commit SHA plus a build number** (C3.2) — traceable, monotonic, and no judgement required.
- **CalVer** — `2026.08.22.3`. Communicates recency, which for a continuously deployed service is more useful than compatibility.
- **SemVer at the API level rather than the artefact level** (C6.10) — **which is the resolution**: version the contract, not the deployment. `/v1/` and `/v2/` endpoints are what consumers care about; the artefact version is an internal detail.

**C3.4 — Artefact promotion between environments**

**Promotion is moving the same artefact through environments without rebuilding** (C1.6, D8.8).

**The mechanics**:

- **Retag the same digest** — `imagetools create` adds a tag to an existing manifest server-side (D8.8), or copy blobs between registries with `crane`/`skopeo`.
- **Or don't retag at all** — reference the digest in the deployment manifest, and promotion is updating that reference in the environment's config (K10.10).
- **Promote the record, not the bytes** — in GitOps, promotion is a commit changing the digest in the production overlay.

**The gates between stages** (C5.7): automated verification passing in the lower environment, a soak period, and where required a human approval (C10.2).

**The design points:**

- **The artefact must be environment-agnostic** (C5.3) — otherwise you can't promote it.
- **Promotion should be a recorded event** — who promoted what, when, from where (C10.7).
- **The lower environment's verification is the evidence** justifying promotion, so it must be meaningful (C5.8).
- **Registry retention must not delete an artefact that's still deployed or that you might roll back to** (C3.5, D8.5).

**The anti-pattern**: **a "staging build" and a "production build" from the same commit.** Two artefacts, different bits, and staging proved nothing about production.

**C3.5 — Artefact repositories and retention**

**The repository**: a container registry (ECR, GHCR, Harbor), a package repository (Artifactory, Nexus), or a language-specific one. **It's the system of record for what can be deployed** and is therefore production infrastructure — its availability gates deployments and, on a cold node, gates scaling (D11.7).

**Retention policy** (D8.5):

| Artefact class | Retention | Reason |
|---|---|---|
| Untagged / superseded | Days | Almost always garbage, and usually the bulk of storage |
| PR and branch builds | 1–2 weeks, capped by count | Short-lived by nature |
| Main-branch builds | 30–90 days | Rollback and investigation window |
| Released versions | **Long — months to years** | **Rollback target, audit, and reproduction** |
| Anything currently deployed | **Never delete** | Deleting it is an outage on the next node pull |

**The rules that matter:**

- **Never expire an artefact that is deployed or that you might roll back to.** An over-aggressive rule is a genuine outage cause, and it's the one to be careful about.
- **Retention interacts with rollback depth** (C9.1) — if you retain 30 days and need to roll back 45, you can't.
- **Compliance may require retaining what was deployed** for years (C10.8) — usually satisfied by retaining the release artefacts and the provenance, not every build.
- **Cost** — image size (D3.8) × build frequency × retention. A reliable finding in a cost review (A12.3).

**C3.6 — Dependency caching vs vendoring**

- **Caching** — dependencies are fetched from an upstream registry and cached locally to speed subsequent builds (C2.4). **The source of truth remains upstream.**
- **Vendoring** — dependencies are committed into your repository. **You own the copy.**

| | Caching | Vendoring |
|---|---|---|
| Build speed | Fast after first fetch | Fast, no fetch at all |
| Upstream outage | **Build fails** (unless cached) | **Unaffected** |
| Upstream deletion / yanked package | **Build fails** | Unaffected |
| Repository size | Small | **Large** |
| Review of dependency changes | A lockfile diff | **The actual code diff** — you see what changed |
| Supply chain | Verified by hash (S7.2) | Auditable directly, and you must review it |
| Updating | Change the lockfile | Re-vendor, large diff |

**The middle ground most organisations use: an internal proxy or mirror** (D8.7, S7.3) — an Artifactory or Nexus remote repository, or a registry pull-through cache. **You get upstream-outage resilience and control over what's available, without repository bloat**, and it's the answer to dependency confusion too (S7.3).

**When vendoring is genuinely right**: air-gapped environments; a critical dependency you cannot risk disappearing (the `left-pad` scenario); Go, where vendoring is idiomatic and well-supported; and anywhere the ability to build with no network access is a requirement.

**The point to make**: **caching is an optimisation; vendoring and mirroring are availability and supply chain controls.** Conflating them means people cache for speed and believe they're protected against an upstream outage, which they aren't — **a cache miss falls through to upstream.**

**C3.7 — Build provenance**

**Provenance is a signed, machine-readable record of how an artefact was built** — which source commit, which builder, which build definition, which inputs, and when.

```json
{
  "buildDefinition": {
    "buildType": "https://github.com/actions/workflow@v1",
    "externalParameters": { "workflow": { "repository": "acme/api", "ref": "refs/heads/main" } },
    "resolvedDependencies": [{ "uri": "git+https://github.com/acme/api@a3f9c2b" }]
  },
  "runDetails": { "builder": { "id": "https://github.com/actions/runner" } }
}
```

**Why you'd want it:**

- **Signing proves who built it; provenance proves how** (S1.3, S7.7). **SolarWinds was validly signed** — the build was the attack. Provenance lets verification assert "built by our pipeline, from our repository, from commit X" rather than merely "signed by someone we trust."
- **It's verifiable at admission** — a policy can reject an image without provenance from the expected builder and repository (K8.9, S7.7).
- **It answers "where did this come from"** for an artefact found running, which is C3.8's question with cryptographic backing.
- **SLSA levels are defined in terms of it** (S7.12) — L1 is provenance existing, L2 is it being signed by a hosted builder, L3 is it being unforgeable.

**Generating it**: GitHub Actions' `attest-build-provenance`, the `slsa-github-generator`, or `cosign attest`. **Attached to the artefact as an OCI attestation** (D8.3) so it travels with it.

**The point that makes it worth the effort**: **verification must be enforced** — provenance generated and never checked is documentation. The value is in the admission policy that rejects artefacts without it.

**C3.8 — Proving what code is running in production right now**

**The chain, and every link must hold:**

1. **The running instance reports its identity** — a `/version` endpoint returning the commit SHA and build time, or the image digest visible from the orchestrator (`kubectl get pod -o jsonpath='{..imageID}'`).
2. **The digest maps to an artefact** in the registry, which is immutable (C3.1).
3. **The artefact carries labels and provenance** recording the source commit (C3.2, C3.7).
4. **The commit is in the repository**, with its PR, review, and approval (C10.7).
5. **The deployment is recorded** — the GitOps commit that set that digest (K10.7), or the pipeline run.

**The strongest form**: **GitOps, where the git repository *is* the record of what should be running**, and drift detection confirms that it is (K10.9). "What's in production" is answered by reading a file, and "who approved it" is answered by `git log`.

**Where the chain breaks in practice — and these are the things to check:**

- **A mutable tag** deployed, so the digest running may not be the digest the tag now points at (D8.2).
- **A manual `kubectl set image`** or hotfix that isn't in git (TF1.5's drift argument).
- **No version endpoint and no labels**, so the running instance can't be identified without the orchestrator.
- **Rebuilding per environment** (C1.6), so several artefacts map to one commit.

**The exercise worth proposing**: **pick a production service and produce the commit, the PR, the approver, and the deployment time — with a stopwatch.** Under two minutes means the chain works. Anything longer identifies exactly which link is missing, and it's a good audit rehearsal too (C10.7).

---

## C4. Testing in the pipeline

**C4.1 — The test pyramid and the cost of inverting it**

**The pyramid**: many fast unit tests at the base, fewer integration tests in the middle, very few end-to-end tests at the top.

**The reasoning, per level:**

| Level | Speed | Scope | Failure diagnosis | Flakiness |
|---|---|---|---|---|
| Unit | Milliseconds | One function or class | **Precise — the failing test names the defect** | Very low |
| Integration | Seconds | A few components, real dependencies | Moderate | Moderate |
| End-to-end | Minutes | The whole system | **Poor — "checkout failed" could be anything** | **High** |

**The cost of inverting it** (the "ice cream cone"), which is the substance:

- **Slow feedback** — a suite dominated by end-to-end tests takes 45 minutes, which destroys the loop (C1.5) and causes batching (C1.9).
- **Flakiness** — end-to-end tests touch networks, timing, browsers, and shared state, so they fail intermittently. **At scale this is fatal to trust** (C4.4): a suite that fails 20% of the time for no reason gets re-run reflexively, and real failures are re-run too.
- **Poor diagnosis** — a failure tells you the system is broken, not what is broken. **Debugging time per failure is an order of magnitude higher.**
- **Expensive to maintain** — end-to-end tests break on any UI or interface change, so a large suite becomes a maintenance burden that outweighs its value.
- **Expensive to run** — full environments, real data, browsers.

**The nuance to add, because the pyramid is sometimes over-applied**: **the shape should follow where your risk actually is.** A system whose complexity is in the integration between services genuinely needs more integration testing than the classic pyramid suggests — which is what **contract testing** addresses (C4.3), and what the "testing trophy" argument is about. **The pyramid's real point is that fast, precise, reliable tests should dominate**, not that a specific ratio is sacred.

**C4.2 — Which tests belong at which stage**

| Stage | Tests | Why here |
|---|---|---|
| **Pre-commit hook** | Lint, format, fast unit subset | Seconds; catches trivia before CI |
| **On PR — fast lane** | Lint, type check, full unit suite | Under 5 min; gates the merge |
| **On PR** | Integration tests against real dependencies in containers | Needs the artefact; still fast enough to gate |
| **On PR** | Contract tests (C4.3) | Cheap, and catches cross-service breakage |
| **On PR** | SAST, dependency scan (C10.5) | Fast, and the fix is cheapest here |
| **On merge** | Full end-to-end suite | Too slow to gate a PR; runs against staging |
| **On merge** | DAST, deeper scanning | Needs a running deployment |
| **Post-deploy** | Smoke tests (C4.8) | Verifies the deployment itself |
| **Post-deploy, continuous** | Synthetic monitoring | Ongoing verification (O1.5) |
| **Scheduled** | Performance and load (C4.9), chaos (T7.9), soak | Slow, resource-heavy, not per-change |

**The principles:**

- **Gate on what's fast and reliable; run the slow and flaky asynchronously.** A flaky end-to-end suite blocking every merge is worse than no suite (C4.4).
- **Test at the lowest level that gives the signal.** If a unit test can catch it, don't write an end-to-end test for it.
- **The cost of a failure found later is higher** — in the pipeline, at deploy, in production — so shift left where the test is cheap and reliable (C2.2).
- **Post-merge failures need an owner and a fast response**, or an asynchronous suite becomes a permanently-red dashboard nobody reads.

**C4.3 — Contract testing and when it beats end-to-end**

**The problem end-to-end testing has at scale**: to test that service A works with service B, you deploy both — and their dependencies, and the databases, and the message broker. **The environment is expensive, slow, and shared, so tests are slow and flaky** (C4.1). **And with fifteen services, you need all fifteen deployed and correct to test any one of them.**

**Contract testing** breaks that coupling:

- **The consumer defines its expectations** of the provider — "when I GET /orders/123, I expect a 200 with these fields of these types." That expectation is a **contract**.
- **The consumer's tests run against a mock** built from the contract — fast, isolated, no provider needed.
- **The provider's tests verify it satisfies every consumer's contract** — replaying them against the real provider, again with no consumer needed.
- **Both sides are tested independently, and the contract guarantees they compose** (Pact is the common tool; a broker shares contracts between the repositories).

**When it beats end-to-end:**

- **Many services**, where the combinatorial cost of end-to-end is prohibitive.
- **Independent deployment** — the provider can verify it hasn't broken any consumer **before deploying**, which is exactly the question C6.8 is about.
- **Speed** — contract tests run in seconds, in each service's own pipeline.
- **Precise failure** — "you broke consumer X's expectation of field Y", not "checkout is broken."

**What it doesn't cover, and must be said**: **it verifies the interface, not the behaviour of the whole system.** It won't catch a workflow that's individually correct at every hop and wrong end to end, and it won't catch performance or infrastructure problems. **So you keep a small end-to-end suite for critical user journeys** — a handful, not hundreds — and contract testing removes the need for the rest.

**C4.4 — Flaky tests as a trust problem**

**The mechanism, and the framing is the point of the item:**

1. A test fails intermittently for no code-related reason.
2. Developers learn that re-running usually works.
3. **Re-running becomes the reflex** for any failure.
4. **A real failure gets re-run too** — and if it passes on the second attempt for an unrelated reason, it's merged.
5. **The test suite has stopped being a signal.** It's a ritual.

**So the cost isn't the wasted minutes — it's that the suite no longer means anything.** A suite with 5% flakiness across 200 tests fails most runs for no reason, and at that point **the team is deploying without effective testing while believing they aren't** — which is worse than having no tests, because of the false confidence.

**The management:**

- **Measure it** — failure rate per test, and specifically failures that pass on re-run with no change (C2.10). **The distribution is heavily concentrated**, so a handful of tests are usually most of it.
- **Set a threshold and treat breaching it as a blocking issue**, not a background annoyance.
- **Quarantine with an owner and a deadline** (C2.8) — out of the blocking suite, into a tracked backlog. **A quarantine with no owner is deletion with extra steps.**
- **Delete tests that are flaky and low-value.** A test that has never caught a real defect and fails weekly is a net negative — **and being willing to delete tests is a mature position** that people resist.
- **Fix the causes**: isolation (ephemeral environments and databases, C5.5), removing timing assumptions, mocking external calls.
- **Make re-running visible** — if a run required a retry, record it, so the flakiness is measurable rather than absorbed.

**C4.5 — Quality gates that aren't theatre**

**A quality gate is a pipeline check that blocks progression.** The question is which ones genuinely reduce risk.

**Gates that earn their place:**

- **The test suite passing** — if it's reliable (C4.4).
- **Build succeeding.**
- **Critical or high severity, reachable, internet-facing vulnerabilities** (C10.5, S8.2) — filtered, not raw scanner output.
- **Secret detection** (S6.3) — near-zero false positives and a catastrophic miss cost.
- **Policy checks** on infrastructure changes (TF7.6) — a plan that would destroy a database.
- **Coverage not *decreasing*** — a delta gate rather than an absolute threshold.

**Gates that are theatre:**

- **An absolute coverage threshold** — 80% is arbitrary, gameable (C4.6), and it blocks a legitimate change while permitting badly-tested code that happens to be above the line.
- **Raw scanner output as a blocker** — thousands of unfiltered findings means either everything is blocked or the gate is bypassed routinely (S8.7).
- **A manual approval where the approver has no basis to judge** and always approves (C10.2).
- **A checklist someone ticks** without performing the checks.
- **A gate that is routinely bypassed** — its existence is documentation of a process nobody follows.

**The tests to apply to any proposed gate:**

1. **What does it catch that nothing else does?**
2. **What's the false positive rate?** A gate with high false positives trains people to bypass it, **which degrades every gate's authority.**
3. **Has it ever caught anything real?** If not in a year, remove it.
4. **Is there an exception path?** If not, people will find an unofficial one (S10.7).

**The framing**: **a gate's value is `(risk it prevents) − (cost of friction) − (cost of erosion when it's bypassed)`.** The third term is the one people omit and it's often the largest.

**C4.6 — Coverage as a signal and its failure as a target**

**As a signal, coverage is useful**: it identifies **untested code** — a module at 5% coverage is a legitimate concern, and a **drop** in coverage on a PR flags new untested code. **The delta is a much better signal than the absolute.**

**As a target it fails**, and it's a clean illustration of Goodhart's law:

- **It measures execution, not assertion.** A test that calls every function and asserts nothing gives 100% coverage and tests nothing. **This is trivially achievable and does happen** when a threshold is enforced.
- **It's easily gamed** — testing trivial getters, generated code, and error branches that don't matter, while the complex conditional logic that actually carries risk stays untested.
- **100% is a bad target** — the last 10% is usually error handling and defensive branches whose tests cost more than they're worth, and chasing it produces low-value tests that then need maintaining.
- **It says nothing about test quality** — whether the assertions are meaningful, whether edge cases are covered, whether the tests would catch a regression.
- **A hard threshold blocks legitimate changes** — a bug fix with no new coverage fails an 80% gate, so people add a token test to pass it.

**The better use:**

- **Track the trend and the delta**, not the absolute (C4.5).
- **Look at coverage of changed lines** in a PR — that's actionable and specific.
- **Use it to find untested areas** for investment, as an input to a conversation.
- **Mutation testing** is the better quality signal where you can afford it — it changes the code and checks whether tests fail, which measures whether assertions are meaningful.

**The position to hold**: **report coverage, don't gate on an absolute number** — and if you must have a gate, make it "coverage must not decrease."

**C4.7 — Test data and environments not dependent on production data**

**Why production data in lower environments is a serious risk** (DB13.10, S10.4): identical sensitivity with weaker controls, far broader access, GDPR obligations including erasure that nobody applies to staging, and the risk of sending real emails or notifications from a test environment.

**The approaches, best to worst:**

1. **Synthetic generation** — data created by a generator (Faker, factory patterns) or by the application's own APIs. **Safest, and it takes real effort to make representative** — the failure mode is uniform, unrealistic data that hides the problems real data would surface (DB2.9).
2. **Masked or anonymised production copies** — a restore with transformation applied **before the data becomes accessible** (DB13.9). Substitution with realistic fakes, preserving referential integrity and distribution. **Must be automated in the restore pipeline**, or it gets skipped.
3. **Subsetting** — a referentially-consistent slice, smaller and faster to refresh, still requiring masking.

**What makes test data good, regardless of source:**

- **Representative distributions**, including the outliers — the customer with 400,000 orders is where the performance problems live (DB2.9).
- **Deterministic and reproducible**, so a failing test can be re-run.
- **Isolated per test run** — shared mutable test data is a top cause of flakiness (C2.8).
- **Seeded automatically**, not maintained by hand.
- **Includes edge cases** — empty states, unicode, boundary values, deliberately malformed records.

**The environment half**: **ephemeral environments per PR** (C5.5) with freshly-seeded data give isolation, which removes an entire class of flakiness — and containers make that practical (D7.1).

**C4.8 — Smoke tests and post-deployment verification**

**A smoke test is a small, fast check run immediately after deployment to confirm the deployment itself worked** — not to test the application's functionality comprehensively.

**What it should check:**

- **The service is up and responding** — a health endpoint returning 200.
- **The version is what you deployed** (C3.8) — surprisingly often it isn't, because of a caching or tag issue (D10.11).
- **Critical dependencies are reachable** — the database connects, the message broker is available.
- **One or two critical paths work end to end** — a login, a read of a real record, a write to a scratch record.
- **No error spike** in the first minutes (C8.5).

**What it should not be**: the full regression suite. **It must complete in seconds to a couple of minutes**, because it's gating the rollout's progression (C7.11) and a slow smoke test extends every deployment.

**How it's used:**

- **Gate progression** — smoke tests failing on the canary stops the rollout before it reaches everyone (C7.4, C8.6).
- **Trigger automated rollback** (C9.5).
- **Run against each environment** after promotion (C3.4).

**The wider point about post-deployment verification** (C11.4): **"the deployment succeeded" and "the change works" are different claims.** A deployment that completes and breaks the service is a successful deployment by the pipeline's measure. **Verification against real signals — error rate, latency, business metrics — is what closes that gap**, and automated canary analysis is the systematic form (C8.5).

**C4.9 — Performance and load testing placement**

**The problem**: performance tests are slow, resource-intensive, and need a realistic environment and realistic data (O13.6) — so they can't run on every commit.

**The placement:**

- **Micro-benchmarks in CI** for performance-critical code paths, with a regression threshold. Fast, and narrow (O13.5).
- **Automated load test on merge to main**, against a staging environment, with the result compared against a baseline. **Nightly if the run is long.**
- **Before a major release** or a change known to affect performance.
- **On a schedule** to catch gradual degradation, which is otherwise invisible until it's an incident.
- **In production, carefully** (C4.10, O13.9) — the only environment that's genuinely representative.

**The design points:**

- **Compare against a baseline, not an absolute threshold** — absolute numbers depend on the environment and drift; **a 20% regression against the previous run is the actionable signal.**
- **Account for environment variance** — a shared CI runner gives noisy results (O13.5), so a single run's difference may be noise. **Run several and compare distributions.**
- **Realistic traffic shape** (O13.6) — request mix, arrival pattern, data distribution, cache state. An unrealistic test gives confident wrong answers.
- **Use open-loop load generation** to avoid coordinated omission (O12.5), which otherwise makes the results systematically optimistic.
- **Test the failure mode too** — a stress test finding where it breaks and *how* is more valuable than confirming it handles expected load (O13.7).

**The honest position**: **staging performance tests predict production poorly** — different data volumes, different cache states, different neighbours (DB2.9). They catch gross regressions, which is worth having, and they don't substitute for production observability (O2.9).

**C4.10 — Testing in production, responsibly**

**The argument for**: **production is the only environment that is production.** Real data volumes, real cache states, real traffic patterns, real dependencies, real infrastructure. **Staging is a model, and models are wrong in ways you discover during incidents** (C5.8).

**The techniques, from safest:**

- **Synthetic monitoring** — scripted user journeys running continuously against production (O1.5). Uncontroversial and already standard.
- **Canary deployments** — a small traffic percentage on the new version, with automated analysis (C7.4, C8.5). **This is testing in production**, and it's the mainstream form.
- **Shadow / dark traffic** — duplicating real requests to the new version and discarding responses (C7.5). Realistic load with no user impact.
- **Feature flags with a small user segment** (C8.7) — the new path exercised by 1% of real users, with a kill switch (C8.8).
- **Load testing against production** (O13.9) — with tagged synthetic traffic, an abort condition tied to real-user SLIs, and careful handling of side effects.
- **Chaos experiments** (T7.9) — controlled failure injection with a defined blast radius and stop condition.

**What makes it responsible:**

- **A blast radius that's bounded and known** — a percentage, a segment, a single region.
- **An abort condition defined in advance and automated** (C8.6) — tied to real user impact, not to someone watching a dashboard.
- **A kill switch that works instantly** (C8.8).
- **Observability good enough to detect harm quickly** (O16.7), because the whole approach depends on noticing fast.
- **No irreversible side effects** — synthetic transactions routed to test doubles, tagged so they're excluded from analytics and billing.
- **Communicated** — the on-call knows, and there's a rollback plan.

**The framing**: **every deployment is a test in production; the question is whether it's a controlled one.** Progressive delivery is the discipline of making it controlled rather than pretending it isn't happening.

---

## C5. Environments

**C5.1 — What each environment is actually for**

| Environment | Purpose | The question it answers |
|---|---|---|
| **Local / dev** | Fast iteration | "Does my change work at all?" |
| **Ephemeral / preview** | Review a change in isolation (C5.5) | "Does this PR work, and can a reviewer see it?" |
| **Integration / test** | Automated testing against real dependencies | "Do the components work together?" |
| **Staging** | Final verification before production (C5.8) | "Would this work in production?" |
| **Production** | Serving users | — |

**Environments to challenge:**

- **A "UAT" environment that duplicates staging** — used by nobody, maintained by everybody, and diverged from both neighbours.
- **A "pre-prod" that exists because staging isn't trusted** — the honest answer is to fix staging rather than add another layer (C5.8).
- **Long-lived per-team environments** that drift and become snowflakes — ephemeral environments (C5.5) serve the same purpose better.
- **A "hotfix" environment.**
- **Any environment nobody deployed to in the last month** — it is not being used and is providing no signal, while costing money and maintenance.

**The questions to ask of each environment:**

1. **What decision does this environment inform?** If nobody makes a decision based on it, it's inventory.
2. **Who owns it, and who deploys to it?** (C5.10)
3. **What breaks if it's deleted?**
4. **How does it differ from production, and does that difference invalidate what we learn from it?** (C5.2)

**The senior framing**: **every environment has a cost — infrastructure, maintenance, and the delay it adds to the path to production.** More environments means longer lead time (C11.3), so each one must justify itself. **Fewer, better environments beat more, neglected ones**, and proposing to delete one is a legitimate and often welcome contribution.

**C5.2 — Environment parity, and which differences matter**

**The differences that genuinely invalidate what you learn:**

- **Data volume and distribution** — the biggest one (DB2.9). A query fast against 10,000 rows and catastrophic against 50 million; a customer with 400,000 orders that staging doesn't have.
- **Traffic volume and concurrency** — contention, connection pool exhaustion (DB8.4), and queueing effects (O12.1) appear only under real load.
- **Scale** — one replica versus fifty changes behaviour: connection counts, cache hit rates, and coordination overhead.
- **Configuration** — timeouts, pool sizes, feature flags, log levels. **A staging environment with debug logging and a 60-second timeout is not testing production behaviour.**
- **Dependencies** — mocks or shared sandboxes instead of the real third party, with different latency and failure modes.
- **Infrastructure topology** — single-AZ staging versus multi-AZ production means you never test cross-AZ latency or failover.

**The differences that usually don't matter:**

- **Instance sizes**, for functional testing (they matter enormously for performance testing, C4.9).
- **Replica counts**, for functional testing.
- **Domain names and certificates** — as long as TLS is actually enabled somewhere.
- **Cost optimisations** — spot instances, smaller storage tiers.

**The principle**: **parity matters where it affects the signal you're taking from the environment.** Making staging identical to production is expensive and usually unnecessary; **making it identical in the dimensions that affect your conclusions is the actual requirement.** And the differences that remain should be **documented and known**, so when staging says something works you know what that claim covers (C5.8).

**C5.3 — Config, not artefacts, differing between environments**

**The rule: the artefact is identical everywhere; configuration is injected at runtime** (C1.6, D4.10).

**What must be configuration:**

- Endpoints and connection strings.
- Credentials (C5.11).
- Feature flags.
- Resource limits and scaling parameters.
- Log levels.
- Timeouts and retry policies.
- Environment identifiers for telemetry.

**Why it matters beyond the promotion argument:**

- **It's what makes promotion possible at all** (C3.4) — if the artefact differs, there's nothing to promote.
- **A config change doesn't require a rebuild**, so changing a timeout in production is a config deployment, not a build-and-test cycle.
- **It makes the environment differences explicit and reviewable** — a diff between the staging and production config files is a precise statement of how they differ (C5.2).

**The failures:**

- **Compile-time environment selection** — a build flag producing a "prod build". **You cannot promote it.**
- **Config baked into the image** — the same problem.
- **Environment detection in code** — `if (env === 'production')` scattered through the codebase means behaviour differs in ways nobody has enumerated, **and staging is running different code paths from production.** This is the subtle one and it's very common.

**The test**: **can you take the artefact that's in staging and run it in production by changing only configuration?** If not, find out why — the answer is usually one of the three failures above.

**C5.4 — Environment-specific configuration without duplication**

**The approaches:**

- **A base plus per-environment overlays** — Kustomize overlays (K10.5), Helm values files (K10.2), Compose override files (D7.4). **The overlay contains only the differences**, which is the property that matters.
- **A hierarchical config system** — defaults, then environment, then instance, merged at load.
- **A parameter store per environment** — same key paths, different values, resolved at runtime (A10.20).
- **Templating with per-environment variable files.**

**The principle to state**: **duplication is not the enemy — divergence is.** Three copied config files that stay identical are harmless; the problem is that they *don't* stay identical, so production quietly acquires settings staging doesn't have and the testing stops predicting.

**The test to apply**: **can a reviewer see, in one place, exactly how production differs from staging?** An overlay containing only the deltas passes; three full copies do not. **That's the criterion**, and it's more useful than any specific tool choice.

**The related disciplines:**

- **Keep the differences small and deliberate** — replica counts, sizes, endpoints, and flags. If they differ structurally, you're testing something different (C5.2).
- **Validate configuration** in the pipeline — a schema check catches a typo before deployment, and a missing required value should fail fast (D7.3's `${VAR:?}` pattern).
- **Secrets by reference, not by value** (C5.11, K10.11).
- **Version the config with the environment**, so a config change is a reviewed commit like any other (C10.7).

**C5.5 — Ephemeral / preview environments per PR**

**A full deployment of the change, created when the PR opens and destroyed when it closes.**

**What it enables:**

- **A reviewer clicks a link and uses the change** rather than reading a diff and imagining it. **For anything user-facing this transforms review quality**, and it's the strongest argument.
- **Isolated testing** — no shared staging contention, no interference between concurrent PRs, no queueing for the environment (C2.8's flakiness cause).
- **Realistic integration testing** against real dependencies.
- **Product and design review** before merge.
- **Confidence that the deployment mechanism works** for this change, before it reaches a shared environment.

**The implementation shape**: a pipeline job on PR open that provisions a namespace or a stack, deploys the PR's artefact, seeds test data (C4.7), and comments the URL on the PR. Kubernetes namespaces (K13.3), a Terraform workspace (TF3.7's legitimate use), or a platform feature (Vercel, Heroku review apps, Argo CD ApplicationSets).

**What to get right:**

- **Fast creation** — if it takes fifteen minutes, people won't wait for it.
- **Cheap** — share heavyweight dependencies (one database server with a schema per PR) rather than duplicating everything.
- **Seeded automatically** with synthetic data (C4.7).
- **Teardown discipline** (C5.6) — the part that fails.

**Where it's hard**: applications with heavy stateful dependencies, expensive third-party integrations (a sandbox account per PR may not exist), and very large monoliths where a full deployment is slow and costly.

**C5.6 — The cost and teardown discipline ephemeral environments require**

**The costs:**

- **Infrastructure per environment** × number of concurrent PRs. **With 30 open PRs that's 30 environments**, and if each includes a database instance the arithmetic gets uncomfortable quickly.
- **Creation time** on every PR, and on every push if it redeploys.
- **Third-party quota and cost** — sandbox accounts, licences, API rate limits.
- **Maintenance** of the provisioning mechanism itself.

**Teardown discipline — where it actually fails:**

- **Destroy on PR close and on merge**, and handle the case where a PR is closed without merging.
- **A scheduled reaper that destroys environments older than N days regardless of PR state.** **This is the essential backstop** — the close hook will fail sometimes (a cancelled job, a deleted branch, a CI outage), and without a reaper those environments live forever. **This is the control people skip and then discover months later in a cost review** (TF9.9, A12.3).
- **Tag everything with the PR number and a TTL**, so orphans are identifiable and attributable.
- **A budget alert on the ephemeral environment account** (A12.6).
- **A separate account or cluster** for ephemeral environments, so an over-aggressive reaper can't touch anything real and quota exhaustion is contained (A11.9).

**The design constraint that follows**: **ephemeral environments must be cheap and fast**, which means they can't include heavyweight stateful resources. Share a database server with a schema per environment; use a lightweight seeded dataset; mock expensive third parties. **And `prevent_destroy`-style protections must not be set** on anything in them, or teardown fails (TF2.9).

**C5.7 — Environment promotion and the gates between stages**

**The promotion path**: `PR env → staging → production`, or with more stages in a regulated or multi-region context.

**The gates, and what each should actually verify:**

| Gate | Verifies | Automated? |
|---|---|---|
| PR → merge | Tests pass, scans clean, review approved | Mostly automated |
| Merge → staging | Artefact built and published | Automated |
| Staging verification | Smoke tests, integration suite, no error spike | **Automated** |
| Staging → production | Soak time elapsed, verification green, **approval where required** | Automated + optional human |
| Production canary → full | Canary analysis passing (C8.5) | **Automated** |

**The principles:**

- **Each gate should verify something the previous one couldn't** — otherwise it's delay without signal (C4.5).
- **Automate the verification; reserve human judgement for genuine decisions** (C10.2). A human approving because the tests passed adds nothing; a human deciding whether now is the right moment to release adds something.
- **Soak time is a real gate** — a period in staging under load catches issues that immediate tests don't, and it's cheap.
- **The same artefact throughout** (C3.4) — a gate that triggers a rebuild breaks the chain.
- **Promotion should be recorded** — who, what, when, from where (C10.7).

**The failure to name**: **gates that accumulate.** Each incident adds an approval step, and nobody removes them, so the path to production grows from two gates to seven over a couple of years — with lead time growing accordingly (C11.3) and batch size growing with it (C1.9). **Reviewing and removing gates should be as routine as adding them** (C4.5).

**C5.8 — Why staging is often misleading, and what to do**

**Why it misleads** (C5.2):

- **Different data** — volume, distribution, and the awkward real records that break things (DB2.9).
- **Different traffic** — no concurrency, no contention, no queueing (O12.1).
- **Different scale** — one replica versus fifty.
- **Different configuration** — timeouts, pool sizes, log levels.
- **Mocked or sandboxed dependencies** with different latency and failure behaviour.
- **Drift** — staging is deployed to constantly and reconfigured ad hoc, so it diverges from production and from its own IaC (TF1.4).
- **Nobody uses it** — so problems that only appear with real usage don't appear.

**The consequence**: **"it worked in staging" carries far less information than people assume**, and treating it as a guarantee produces confident bad deployments.

**What to do:**

1. **Be explicit about what staging does and doesn't verify** (C5.2). It's good for functional correctness and integration; it's poor for performance, scale, and data-dependent behaviour. **Knowing the limits is more useful than trying to eliminate them.**
2. **Reduce the differences that matter** — a production-scale anonymised data copy (C4.7) is the single highest-value improvement.
3. **Shift verification into production** — canary (C7.4), automated analysis (C8.5), feature flags with a small segment (C8.7). **This is the real answer**: rather than making staging more like production, verify in production with a bounded blast radius.
4. **Manage staging with the same IaC and pipeline as production**, so it can't drift.
5. **Consider whether you need it at all** — some organisations with strong progressive delivery run PR environments plus production canaries and no staging. **That's a defensible position** and worth being able to argue.

**C5.9 — Production-like data in lower environments, safely**

Covered from the database side in DB13.9 and DB13.10. The delivery-side summary:

**The risk**: identical data sensitivity with weaker controls and far broader access; GDPR applies including erasure requests nobody processes for staging; and real notifications sent to real customers from a test environment.

**The approaches:**

1. **Synthetic data** (C4.7) — safest, and it must be representative to be useful.
2. **Masked production copies** — **masked as part of the restore pipeline, before the data is accessible**, so an unmasked copy never exists outside production. **Automate it**, because a manual masking step gets skipped.
3. **Subsetting** — a referentially-consistent slice, still masked.

**The masking techniques**: substitution with realistic fakes (best for usability), deterministic hashing (preserves joins), shuffling within a column, generalisation. **Referential integrity must survive** or the data is useless.

**The delivery-specific controls:**

- **Restrict who can restore production backups** — that permission is effectively production data access.
- **Block outbound side effects in lower environments** — mail catchers rather than a real SMTP relay, sandbox payment endpoints, disabled webhooks. **Sending a real email from staging is a recurring embarrassment** and is entirely preventable at the platform level.
- **Detect it** — periodic scanning of lower environments for patterns that look like real PII.
- **Treat it as in-scope for compliance if you do use it** (S10.5) — the honest position, and usually the argument that funds the masking work.

**C5.10 — Environment ownership and who can deploy where**

**The model:**

| Environment | Who can deploy | Mechanism |
|---|---|---|
| Local / ephemeral | Anyone on the team | Automated on PR |
| Integration / test | Automated only | Pipeline on merge |
| Staging | Automated only | Pipeline on merge |
| **Production** | **The pipeline, with an approval from a defined group** | Protected environment + IAM (C10.1) |

**The principles:**

- **Nobody deploys by hand.** All deployments go through the pipeline, so they're recorded, reviewed, and repeatable (C10.7). **A human with `kubectl apply` access to production is drift waiting to happen** (TF1.5).
- **Separation of duties** — the author should not be the sole approver (C10.1).
- **Enforced by the platform, not by convention** — protected environments with required reviewers, backed by IAM so the deploy credential is only assumable from the protected context (S7.9). **Otherwise anyone who can edit the workflow can bypass the gate** (TF7.9).
- **Each environment has a named owning team** responsible for its state and its cost.
- **Break-glass exists and is audited** (C10.6).

**The point that connects it to security**: **deploy access is production write access.** In many organisations the group who can merge to main is much larger than the group with direct production console access — **so the pipeline is a privilege escalation path around the IAM model** unless the approval gate and the credential scoping are done properly (C10.3, C10.4).

**C5.11 — How secrets differ per environment and how they're injected**

**Secrets are per-environment by definition** — production credentials must not exist in staging, or a staging compromise is a production compromise.

**The injection mechanisms** (S6.2):

- **Workload identity** — the pod or instance assumes a role and fetches from the secret store at runtime (A2.7, A10.21). **No secret is stored anywhere; access is scoped by environment because the role is.** The strongest option.
- **Secrets Store CSI Driver** — mounted as files, never becoming a Kubernetes Secret (K3.6).
- **External Secrets Operator** — synced from the external store into native Secrets (K3.6).
- **CI injection at deploy time** — the pipeline fetches and passes them, which means the pipeline holds the credential to fetch them (C10.3).

**The per-environment structure**: the same secret *paths* across environments with different values — `/prod/payments/db` and `/staging/payments/db` — so the application's configuration is identical and only the resolved value differs (C5.3). **The access control is on the path prefix**, scoped to the environment's role.

**What must not happen:**

- **Production secrets in a non-production secret store** or in a shared one without path-level access control.
- **Secrets in git**, even encrypted, without a deliberate decision (K10.11, S6.3).
- **The same secret across environments** — a shared API key means a staging leak is a production incident.
- **Secrets in the pipeline configuration** rather than fetched at runtime.

**The rotation dimension** (S6.5): secrets rotate independently per environment, and the application must re-fetch rather than caching at startup — otherwise rotation breaks the deployment.

---

## C6. Release management

**C6.1 — Deploy vs release, and why decoupling matters**

- **Deploy** — putting the code on the infrastructure. A technical event.
- **Release** — making the behaviour available to users. A business event.

**Coupled, they are the same moment**: the code ships and users get it. **Decoupled, code is deployed dark and activated separately** — by a feature flag (C8.1), a configuration change, or a traffic rule.

**Why decoupling matters — the consequences are substantial:**

- **Deployment risk and release risk are separated.** A deployment that goes wrong is a technical rollback; a release that goes wrong is a flag flip. **Different failure modes, different recovery, different owners.**
- **Release becomes reversible in seconds** (C8.8). Rolling back a deployment takes minutes and reverts everything in it; turning off a flag takes seconds and reverts one thing.
- **Trunk-based development becomes practical** (C1.3) — incomplete work merges to trunk behind a flag, so no long-lived branches (C1.4).
- **The business controls timing.** Marketing wants the feature live on Tuesday morning; engineering deployed it last week and verified it. **These no longer have to coincide**, which removes a whole category of deployment-under-pressure.
- **Progressive exposure** becomes possible — 1% of users, then 10% (C8.7).
- **Deployment frequency rises** because deploying is low-risk, which improves everything else (C11.2).

**The cost to acknowledge** (C8.3, C8.4): flags are code, they accumulate, they create untested combinations, and they need a lifecycle. **The decoupling is not free**, and the discipline of removing flags is the price.

**C6.2 — Release versioning and tagging strategy**

**Two things are being versioned and they should not be conflated:**

- **The artefact** (C3.2) — identified by digest and traceable to a commit. **Machine-oriented.**
- **The release** — a human-meaningful label for a set of changes. `v2.4.0`, `2026.08.22`, or a sprint name.

**A workable strategy:**

```
git tag v2.4.0                          # annotated, signed, on the released commit
ghcr.io/acme/api:v2.4.0                 # the artefact tag
ghcr.io/acme/api:sha-a3f9c2b            # traceability tag (C3.2)
ghcr.io/acme/api@sha256:...             # what production actually references (D8.2)
```

**The decisions:**

- **SemVer for anything with external consumers** (C3.3); **CalVer or a build number for internal continuously-deployed services**, because a version conveys nothing useful to a consumer who doesn't choose it.
- **Tag the commit in git**, signed where provenance matters (S7.7), so the release is anchored to source.
- **Immutable tags in the registry** (D8.2) — a release tag that can be moved isn't a release.
- **Automate the version bump** from commit conventions (C6.3) rather than doing it by hand, or it drifts.

**The point worth making**: **for a continuously deployed service, a "release version" is often ceremony.** If you deploy fifteen times a day, `v2.4.127` communicates nothing. **What matters is the commit and the deployment record** (C3.8). **Version the API contract instead** (C6.10) — that's what consumers actually depend on.

**C6.3 — Changelogs and release notes from commits**

**The mechanism**: structured commit messages, parsed to generate the changelog.

```
feat(payments): add support for SEPA instant transfers
fix(auth): correct token expiry calculation
feat!: remove deprecated /v1/charges endpoint

BREAKING CHANGE: /v1/charges removed; use /v2/payments
```

**Conventional Commits** is the common standard: `type(scope): description`, with `!` or a `BREAKING CHANGE` footer marking incompatibility. **Tools**: `semantic-release`, `release-please`, `git-cliff`, `changesets`.

**What it enables:**

- **Automated version bumping** — `feat` bumps minor, `fix` bumps patch, `BREAKING CHANGE` bumps major (C3.3). **Removes the judgement call and the human error.**
- **A generated changelog** that's actually complete, because it's derived from what was merged rather than from what someone remembered.
- **Release notes** grouped by type, with links to PRs and issues.
- **A trigger for release automation** — a `feat` on main can automatically cut a release.

**The caveats worth stating:**

- **Commit messages are written for other engineers; release notes are often for users.** **A generated changelog is a good engineering artefact and a poor user-facing announcement** — the honest answer is generate the technical changelog automatically and write the user-facing notes by hand for anything significant.
- **It requires discipline**, enforced by a commit-message linter in CI, or it degrades to `fix: stuff`.
- **Squash-merge policy interacts with it** — the squashed commit message becomes the record, so the PR title needs to follow the convention.
- **For an internal continuously-deployed service, the changelog may have no audience** (C6.2) — in which case it's ceremony, and worth saying so.

**C6.4 — Release trains vs on-demand**

- **Release train** — releases go out on a fixed schedule. Whatever is ready by the cutoff ships; whatever isn't waits for the next one.
- **On-demand** — each change releases when it's ready.

| | Release train | On-demand |
|---|---|---|
| Batch size | **Large** (C1.9) | Small |
| Coordination | Easier across teams — one known date | Harder |
| Predictability for stakeholders | **High** | Lower per-change |
| Risk per release | **Higher** — more changes | Lower |
| Time from merge to production | **Up to the full cycle** | Minutes |
| Pressure at the cutoff | **High — rushed merges to catch the train** | None |

**Where trains genuinely fit**: **software shipped to customers who must install it** (mobile apps subject to app store review, on-premises software, embedded firmware); **regulated releases requiring coordinated approval**; and **coordinated multi-team releases** with genuine interdependencies — though C6.8 argues most of those can be decoupled.

**Where they don't**: a continuously-deployed service. **The train imposes batch size** (C1.9), delays value, and creates the cutoff rush — where changes are merged hastily to avoid waiting a fortnight, which is precisely when defects are introduced.

**The middle ground**: **deploy continuously, release on a schedule** (C6.1) — the code is in production and verified; the flag flips on the announced date. **This gets the coordination benefit without the batch size cost**, and it's the answer worth giving because it dissolves the apparent tradeoff.

**C6.5 — Freeze periods: rationale and cost**

**The rationale**: during a high-risk or high-traffic period — Black Friday, quarter end, a regulatory deadline, the Christmas holidays with reduced staffing — **avoid change so as not to introduce an incident when the cost is highest and the ability to respond is lowest.**

**That's a legitimate argument**, and it should be acknowledged rather than dismissed.

**The costs:**

- **Batch accumulation.** A two-week freeze means two weeks of changes released at once, and **the first deployment after the freeze is the largest and riskiest of the year** (C1.9) — often at exactly the moment when staffing is still thin.
- **Urgent changes still happen**, through an exception process that's less well-rehearsed than the normal path (C10.6). **So the freeze doesn't stop change; it stops *practised* change.**
- **Deployment capability atrophies** — a pipeline unused for a month is a pipeline whose first use reveals a broken credential or an expired certificate.
- **It signals that deployment is dangerous**, which is a self-fulfilling belief that undermines investment in making it safe.

**The constructive position** (S10.7's framing): **the intent is to reduce risk during a critical period. Ask whether a freeze is the best mechanism for that intent.**

The alternatives: **freeze risky changes, not all changes** — a config change or a small fix behind a flag is not the same risk as a schema migration; **require progressive rollout with automated analysis** during the period rather than blocking (C8.5); **increase the approval bar** rather than setting it to infinity; and **rehearse** — a team deploying safely fifty times a week is far better placed to handle a Black Friday incident than one that hasn't deployed in three weeks.

**C6.6 — Change management and CAB in a regulated context**

**Don't pretend it doesn't exist** — that's the framing the item asks for, and it's the right one. In a regulated environment, change control is a genuine obligation, and dismissing it as bureaucracy loses the argument and the relationship.

**What the control is actually for**: an auditable record that changes to production are authorised, assessed for risk, and reversible — with someone accountable.

**The productive approach:**

- **Map the pipeline's automatic artefacts to the control requirements** (S10.2, C10.7). The PR is the change record; the review is the assessment; the approval gate is the authorisation; the plan or diff is the impact analysis; the pipeline log is the implementation record. **All captured automatically, with better fidelity than a manually-filled ticket.**
- **Agree the mapping with compliance and audit in advance**, and document it. **Unilaterally deciding your pipeline satisfies the control produces a finding** (S10.1).
- **Standard/pre-approved changes** — most frameworks (ITIL included) have a category for low-risk, well-understood, repeatable changes that don't need per-instance CAB approval. **Getting your routine deployments classified as standard changes is the single highest-value negotiation available here**, and it's a well-trodden path.
- **Reserve CAB for genuinely novel or high-risk changes** — a schema migration, a new integration, an infrastructure change with a broad blast radius.
- **Emergency change process** for incidents, with retrospective approval (C10.6).

**The argument to make** (S10.6): **an automated pipeline with enforced review, automated policy checks, progressive rollout, and complete audit trails provides better control than a weekly meeting approving a list of changes nobody in the room can meaningfully assess.** Made with evidence, that argument usually succeeds — because compliance functions are generally as frustrated by ineffective controls as engineers are.

**C6.7 — Satisfying an auditor about who approved what**

**What the auditor wants**: for a given production change, **who requested it, who reviewed it, who approved it, when, what was deployed, and evidence the process was followed consistently** — over a period, not at a moment (S10.2).

**Producing it from systems:**

| Question | Source |
|---|---|
| What changed? | The PR diff, and the artefact digest deployed (C3.8) |
| Who wrote it? | Git commit author, signed if required |
| Who reviewed it? | PR review record, with the required-reviewers policy enforced |
| Who approved deployment? | The protected environment's approval record (C10.1) |
| When was it deployed? | Pipeline run record, or the GitOps commit |
| Was separation of duties maintained? | **Enforced by the platform** — author ≠ approver, configured in branch protection |
| Was it tested? | Pipeline logs showing the gates that passed |
| Could an unauthorised change occur? | Branch protection, IAM scoping (C10.3), audit logs (C10.7) |

**The properties that make it good evidence** (S10.2): **continuous** (covers the whole period, not a sampled screenshot), **tamper-evident** (the audit log is off-system and immutable, S9.7), **complete** (every change went through the path — no manual deployments, C5.10), and **reproducible** (the auditor could run the same query).

**The gaps that cause findings:**

- **Manual deployments outside the pipeline** — one `kubectl apply` and the "all changes go through the pipeline" claim is false.
- **The approver could bypass the gate** — if anyone who can approve can also edit the workflow, separation of duties isn't enforced (C10.1).
- **Break-glass with no record** (C10.6).
- **Retention too short** to cover the audit period.

**C6.8 — Coordinating a release across services with dependencies**

**The default position to argue for: don't.** A coordinated multi-service release is a large batch (C1.9) with a complex rollback, and **the need for it usually indicates a design problem** — services that must deploy together are coupled and arguably shouldn't be separate services.

**How to avoid it — the techniques, in preference order:**

1. **Backwards and forwards compatible changes** (C6.9) — if every change is compatible with the previous version of its neighbours, ordering doesn't matter and each service deploys independently. **This is the real answer.**
2. **Expand-contract** (DB7.3, applied to APIs) — add the new field or endpoint, migrate consumers, remove the old. Three independent releases instead of one coordinated one.
3. **Feature flags** (C8.1) — deploy everything dark, flip a coordinated flag. **The flag flip is the coordinated event, and it's instant and reversible** (C8.8), which is a vastly better coordination point than a deployment.
4. **Contract testing** (C4.3) — the provider verifies it hasn't broken any consumer before deploying, so the coordination becomes a check rather than a schedule.
5. **API versioning** (C6.10) — run both versions concurrently and migrate consumers at their own pace.

**When coordination is genuinely unavoidable** — a protocol change, a shared data format change that can't be made compatible:

- **Define the order explicitly** and which service must go first.
- **Verify compatibility at each step**, not just at the end.
- **Have a rollback plan for the whole sequence**, and know which steps are irreversible (C9.3).
- **Do it in a low-traffic window**, with everyone available.
- **Rehearse it** in a lower environment.

**C6.9 — Backwards and forwards compatibility as a release requirement**

**The requirement, and stating it this way is the key insight**: during any rolling deployment (C7.2), **both versions run simultaneously**. So:

- **The new version must work with data and messages written by the old** — **backwards compatible.**
- **The old version must tolerate data and messages written by the new** — **forwards compatible.**

**Both are required**, and the second is the one people forget.

**Where it applies:**

- **APIs** — a new required field breaks old clients; a removed field breaks new ones reading old responses.
- **Database schemas** (DB7.5) — a dropped column breaks the old version still running; a new `NOT NULL` column breaks the old version writing.
- **Message formats** (M7.3) — a producer and consumer deploying at different times.
- **Serialised state** — cache entries, session data, and persisted objects written by one version and read by another.

**The rollback consequence, which is the sharpest argument**: **if a change is not backwards compatible, you cannot roll back** (C9.4). The new version wrote data the old version can't read. **So compatibility isn't just about the rolling window — it's what preserves rollback as an option**, and losing that removes your primary incident response.

**The practices**: **additive changes only** in a single release; **expand-contract** for anything else (DB7.3); **tolerant readers** — ignore unknown fields rather than erroring, which makes forwards compatibility largely free; **schema registries with compatibility enforcement** (M7.2) for message formats; and **contract tests** (C4.3) to verify it.

**C6.10 — API versioning and deprecation as a release concern**

**The versioning approaches:**

- **URI path** — `/v1/orders`, `/v2/orders`. Explicit, visible, cacheable, and it clutters the URL space. **The most common and the most operationally straightforward.**
- **Header** — `Accept: application/vnd.acme.v2+json`. Cleaner URLs, harder to test by hand, and easy for a client to get wrong.
- **Query parameter** — `?version=2`. Simple and a bit informal.
- **No versioning, compatible evolution only** (C6.9) — **viable and underrated** for an internal API with known consumers: only additive changes, ever, with tolerant readers.

**Deprecation as a release process, which is the part that matters:**

1. **Announce**, with a date, through a channel consumers actually read.
2. **Instrument** — **log and meter usage of the deprecated version, per consumer.** **This is essential and frequently missing**: you cannot deprecate what you can't measure, and "who is still calling v1" must be answerable.
3. **Signal in the response** — a `Deprecation` header (RFC 8594), a `Sunset` header with the date, and a warning in the payload where the format allows.
4. **Contact remaining consumers** individually as the date approaches — the metering makes this possible.
5. **Brownout** — deliberately fail or delay a small percentage of requests to the deprecated version for short windows before the cutoff. **The most effective technique**: it surfaces remaining consumers who ignored every notice, while the impact is still recoverable.
6. **Remove**, and keep the ability to restore it briefly.

**The release-concern framing**: **an API version is a contract with a lifecycle** — introduction, support, deprecation, removal — and each stage is a release event with its own communication and verification. **For an internal API with known consumers, this is a conversation; for a public one it's a programme measured in quarters.**

---

## C7. Deployment strategies

**C7.1 — Recreate, and when downtime is acceptable**

**Recreate**: stop all instances of the old version, then start the new. **Downtime for the duration.**

**When it's acceptable or necessary:**

- **The two versions genuinely cannot coexist** — an exclusive lock, a schema change that isn't backwards compatible (C6.9), a singleton process, or a licence permitting one instance.
- **A batch or internal system** with a maintenance window nobody notices.
- **A development environment.**
- **The application is stateful in a way that makes mixed versions unsafe** (C7.8).
- **It's genuinely simpler and the downtime is acceptable to the business** — **and that's a legitimate answer.** A brief outage on an internal tool at 2am is cheaper than the engineering to avoid it.

**The honest framing**: **recreate is the simplest strategy and it's chosen too rarely and too often.** Too rarely, because teams build elaborate zero-downtime machinery for services where a 30-second window would be fine. Too often, because it's the default when nobody has thought about it.

**The question to ask**: **what does the downtime actually cost, and what does avoiding it cost?** For a customer-facing payments API, any downtime is unacceptable and the engineering is justified. For an internal reporting job, a maintenance window is the right answer and building blue/green for it is waste.

**The mitigation if you must**: schedule it, announce it, put up a maintenance page rather than serving errors, and **make it fast** — the shorter the window, the more acceptable.

**C7.2 — Rolling deployment and the mixed-version state**

**Rolling**: replace instances incrementally — start a new one, wait for it to be healthy, remove an old one, repeat.

**The controls**: `maxSurge` (how many extra above the desired count) and `maxUnavailable` (how many below), which together determine capacity during the rollout (K2.6).

**The mixed-version state is the defining property**, and it's what the item is asking about:

- **Both versions serve production traffic simultaneously**, for the duration of the rollout — which can be minutes, or much longer with a large fleet or a slow readiness check.
- **A user's consecutive requests may hit different versions.** So a change to a response format or a session structure must tolerate that.
- **Both versions read and write the same database** — which is why schema changes must be compatible (C6.9, DB7.5), and it's the single most common way rolling deployments break.
- **Both consume the same message queues** (M7.3).
- **Rollback also produces a mixed state**, in the other direction.

**The requirements that follow**: backwards and forwards compatibility (C6.9); graceful shutdown so terminating instances drain (C7.10); and health checks that gate progression accurately (C7.11).

**The properties**: **no extra infrastructure cost** (unlike blue/green), **no downtime**, **gradual** so a problem affects a fraction initially — **and rollback is another rolling deployment**, which takes as long as the original and is therefore slow under pressure (C9.1). That last point is the main argument for blue/green.

**C7.3 — Blue/green: mechanics, cutover, and cost**

**Mechanics**: two complete environments. **Blue** is live; **green** is the new version, deployed and verified while receiving no production traffic. **Cutover switches all traffic to green** — a load balancer target group change, a DNS change, or a Kubernetes Service selector flip.

**The cutover:**

- **Atomic and instant** — all traffic moves at once, so **there is no mixed-version state** (unlike rolling, C7.2). That's the main functional advantage.
- **Rollback is switching back**, which is **the fastest rollback available** — seconds, and the old environment is still warm and known-good (C9.1).
- **Verification happens before any user traffic** — the full test suite against green, in the production environment, with production configuration.

**The costs:**

- **Double the infrastructure** during the transition, and if you keep blue warm for a rollback window, for longer. **For a large fleet that's substantial**, though with autoscaling and short windows it's less than it sounds.
- **The database is shared** (C7.9) — **this is the constraint that limits the whole strategy**, and it's the item that follows.
- **Stateful components don't switch cleanly** — in-flight sessions, WebSocket connections, in-memory caches (C7.8).
- **A DNS-based cutover isn't atomic** — TTLs and client caching mean it's gradual and unpredictable (A8.5), which undermines the main benefit. **Use a load balancer switch, not DNS.**
- **All-at-once means a problem affecting all users at once** — no gradual exposure, unlike canary (C7.4). **The blast radius on failure is total**, mitigated only by how fast you switch back.

**C7.4 — Canary: traffic percentage, bake time, promotion criteria**

**Canary**: route a small percentage of traffic to the new version, observe, and progressively increase if the signals are good.

```
1% → observe 10 min → 5% → observe 15 min → 25% → observe 30 min → 50% → 100%
```

**The three parameters:**

- **Traffic percentage** — start small enough that a failure affects few users, and large enough to produce statistically meaningful data. **1% of a high-volume service is plenty; 1% of a service handling 100 requests an hour is one request an hour and tells you nothing** — so the starting percentage must be derived from volume.
- **Bake time** — long enough to surface the problems you're looking for. **Immediate errors show in seconds; a memory leak takes hours; a problem that only appears at a daily peak takes a day.** Bake time is a judgement about which failure classes you're screening for.
- **Promotion criteria** (C8.6) — **defined before the rollout starts**, automated where possible: error rate not elevated versus the baseline, latency percentiles within bounds, no increase in specific business metrics failing.

**The mechanics**: an ingress controller with weighted routing, a service mesh (K4.13), a load balancer with weighted target groups, or **Argo Rollouts / Flagger** which automate the progression and the analysis.

**What makes it valuable rather than ceremony**: **the automated analysis** (C8.5). A canary a human watches for ten minutes and approves is barely better than a rolling deployment; **one that automatically aborts on an SLO regression catches what a human wouldn't**. If you describe canary in an interview, describe the analysis and the abort criteria — that's the part that's actually hard.

**The comparison to the alternative**: canary gives **gradual exposure** (unlike blue/green's all-at-once) at the cost of a **mixed-version state** (like rolling, C7.2) and a longer rollout.

**C7.5 — Shadow / dark traffic, and what it can and can't validate**

**Shadow traffic**: real production requests are **duplicated** to the new version, which processes them normally — **but its responses are discarded.** Users are served entirely by the current version.

**What it validates:**

- **Performance under real traffic** — real request mix, real distribution, real concurrency (C4.9's realism problem, solved).
- **Correctness by comparison** — run both versions on the same input and diff the responses. **The strongest form**, and it catches subtle behavioural changes that tests wouldn't.
- **Resource consumption** at realistic load, informing sizing (D11.4).
- **Stability** — does it crash, leak, or degrade under real conditions?
- **All of this with zero user impact**, which is the point.

**What it can't validate:**

- **Write side effects.** **The critical limitation.** A shadowed request that writes to the database writes twice; one that charges a card charges twice; one that sends an email sends two. **So shadowing requires either a read-only path, or a parallel datastore, or write suppression** — and setting that up is most of the work.
- **The user experience** — responses are discarded, so nothing verifies what users would have seen.
- **Anything requiring a response cycle** — multi-step flows, sessions, anything stateful across requests.
- **Downstream effects on third parties**, unless they're stubbed.
- **Capacity interaction** — shadowing adds real load to shared downstream dependencies, so it can affect production even though users aren't served by it.

**When it's worth the effort**: a **major rewrite or migration** where behavioural equivalence must be proven (C12.5, DB14.5) — the comparison mode is genuinely powerful there. **For an ordinary release it's disproportionate**, and canary (C7.4) gives most of the value for a fraction of the setup.

**C7.6 — A/B deployment vs canary**

**Frequently confused, and they have different goals:**

| | Canary | A/B test |
|---|---|---|
| **Goal** | **Is the new version safe?** | **Which variant performs better?** |
| Question | Technical — errors, latency, stability | **Business — conversion, engagement, revenue** |
| Duration | Minutes to hours | **Days to weeks** — needs statistical power |
| Traffic split | Small, increasing to 100% | **Fixed, often 50/50, held for the duration** |
| Assignment | Usually random per request | **Sticky per user** — a user must see one variant consistently |
| Outcome | Promote or roll back | **Choose a winner**, then ship it to everyone |
| Measured by | Engineering metrics (C8.5) | Business metrics, with significance testing |
| Owner | Engineering | Product |

**The key differences to articulate:**

- **Canary asks "did we break anything"; A/B asks "which is better."** Different questions, different metrics, different durations.
- **A/B requires sticky assignment** — a user flipping between variants invalidates the experiment and produces a confusing experience. Canary doesn't care.
- **A/B requires statistical rigour** — sample size, significance, and not peeking at results early. **Canary is a safety check, not an experiment.**
- **A/B is usually implemented with feature flags** (C8.2's experiment flags), not with deployment infrastructure — **because you want both variants in one deployed artefact**, so the experiment outlives any deployment.

**The point that resolves the confusion**: **they're often used together.** Deploy the new version via canary (safety), then run an A/B experiment behind a flag on top of it (value). Conflating them means either running a safety check for two weeks or making a business decision on ten minutes of data.

**C7.7 — Choosing a strategy for a stated system**

The shape of a good answer — take a concrete context and reason from it:

> "For the payments API — customer-facing, high volume, strict availability requirement, and a shared relational database:
>
> **Rolling with a canary stage** is what I'd choose. Rolling because the database is shared, so blue/green's environment duplication doesn't extend to the data layer (C7.9) and the value is limited. A canary stage because the blast radius matters — 1% for ten minutes with automated analysis on error rate and p99 latency (C8.5), then progressive promotion.
>
> **The requirements that follow**: every schema change must be expand-contract so both versions coexist (C6.9, DB7.3); the application must handle SIGTERM and drain (C7.10); readiness probes must be accurate or the rollout gates on nothing (C7.11); and rollback must be tested (C9.2).
>
> **I'd rule out blue/green** because the database is the constraint and the infrastructure cost isn't repaid, and **recreate** because any downtime is unacceptable here.
>
> **For the nightly reconciliation batch job in the same system, recreate is the right answer** — nobody is watching at 2am, it can't run two versions concurrently, and building anything more elaborate would be waste."

**The elements that make it strong**: **a specific context**, **a choice with a reason**, **the alternatives ruled out with reasons**, **the requirements the choice imposes**, and — the part that most distinguishes it — **a different answer for a different workload in the same system**, showing that the choice is per-workload rather than an organisational default.

**C7.8 — How each strategy handles a stateful workload**

**The general problem**: state makes instances non-interchangeable, so the assumptions behind every strategy weaken.

| Strategy | With stateful workloads |
|---|---|
| **Recreate** | **Often the only safe option** — no mixed versions, no concurrent access to the same state |
| **Rolling** | Ordered replacement (StatefulSet, K2.8); **each instance's state must survive replacement** (persistent volumes, K5.5); mixed versions must tolerate the same on-disk or in-cluster format |
| **Blue/green** | **The database can't be duplicated** (C7.9); in-memory state and sessions don't move; **clustered systems can't have two clusters** |
| **Canary** | Works if the state is external and shared; **fails if instances hold user-specific state**, because a user's requests must reach the same instance |

**The specific state types and their handling:**

- **The database** (C7.9) — shared, not duplicated. Compatibility is the answer (C6.9).
- **In-memory session state** — **the fix is to externalise it** (Redis, a signed cookie), after which the workload is effectively stateless and every strategy works. **This is usually the right move** and is worth naming as the structural answer.
- **Local caches** — a new instance starts cold, so a rollout can cause a latency spike and a load spike on the backend (DB11.4). Warm gradually, or accept it.
- **Long-lived connections** — WebSockets, gRPC streams, database connections. **They don't drain quickly**, so a rollout either waits a long time or disconnects clients. Needs client-side reconnection.
- **Clustered systems** (Kafka, Elasticsearch, a database cluster) — rolling with quorum awareness, one node at a time, waiting for full recovery between (M9.3).

**The framing**: **the strategy question for stateful workloads is usually a state-architecture question in disguise.** Externalise what you can; for what you can't, ordered rolling with health gating and careful compatibility is the answer, and a managed service is frequently better than doing it yourself (DB14.3).

**C7.9 — The database constraint that limits blue/green**

**The constraint, stated plainly: you can duplicate the application tier; you cannot duplicate the database.**

Blue/green's premise is two complete environments, with an atomic switch. **But both environments share one database** — because:

- **Duplicating it means the data diverges** the moment both are live, and reconciling two databases is not tractable.
- **Duplicating it means a data migration** for every deployment, which is slow and risky.
- **So blue and green both point at the same database**, which means **the schema must work with both versions simultaneously** — which is exactly the constraint blue/green was supposed to avoid (C6.9, DB7.5).

**The consequences:**

- **Schema changes must still be expand-contract** (DB7.3). The atomic application cutover doesn't help.
- **Rollback is constrained by the schema.** If green ran a migration, switching back to blue means blue runs against the migrated schema — **which only works if the migration was backwards compatible.** If it wasn't, **you cannot roll back**, and blue/green's headline benefit evaporates (C9.4).
- **So blue/green's fast rollback is only fast for application changes**, not for changes involving the data layer — which is a significant qualification.

**The mitigations:**

- **Always expand-contract** (DB7.3), which restores rollback as an option.
- **Separate the schema change from the application change** across releases (DB7.4) — deploy the compatible schema first, deploy the application later, so neither deployment is coupled to the other.
- **Database blue/green** (RDS's feature, A7.5) exists for the database's own version upgrades, and it's a different problem from application deployment.

**The point to make**: **this is why blue/green is less useful in practice than in diagrams.** Its main benefit is instant rollback, and the database constraint removes that benefit for exactly the changes that most need it.

**C7.10 — Connection draining and graceful shutdown**

**The sequence when an instance is being removed** (D11.2, K9.10):

1. **The instance is marked unhealthy / removed from the load balancer's rotation** — so no *new* connections are routed to it.
2. **Existing connections continue to be served** — this is the draining period.
3. **The instance receives SIGTERM** and begins its own shutdown: stops accepting new work, finishes in-flight requests.
4. **After the drain timeout / grace period**, remaining connections are closed and the process is killed (D4.3).

**What must align:**

- **The load balancer's deregistration delay** must be long enough for in-flight requests to complete.
- **The application's shutdown timeout** must be shorter than the orchestrator's grace period, or it's SIGKILLed mid-drain (D4.4).
- **The order matters**: **fail readiness first, then shut down.** In Kubernetes, SIGTERM and endpoint removal happen concurrently, so **a brief `preStop` sleep lets the endpoint removal propagate before the application stops accepting** — without it, every deployment produces a small number of connection errors (K9.10, D11.2).

**Why it matters for deployment specifically**: **without it, every rolling deployment, every scale-in, and every node replacement drops requests.** On a service deploying several times a day, that's a continuous background error rate attributed to "flakiness" — self-inflicted and entirely fixable (C11.4's change failure rate).

**The cases that are hard**: **long-lived connections** — WebSockets and streaming — where draining means either waiting a long time or disconnecting clients. **The answer is client-side reconnection with backoff and jitter** (O15.10), because the server cannot solve it alone.

**C7.11 — How health checks gate a deployment's progress**

**The mechanism**: the deployment controller starts a new instance and **waits for it to report healthy before proceeding** to the next. An instance that never becomes healthy stops the rollout.

**What that buys**: **a broken version stops after affecting one instance rather than all of them.** The rollout stalls with the old version still serving, which is a safe failure — and combined with a progress deadline and automatic rollback (K2.5), it's the primary automated safety mechanism in a rolling deployment.

**The requirements for it to actually work:**

- **The readiness check must reflect genuine readiness** — the application can serve requests, dependencies are connected, caches are warm enough. **A check that returns 200 as soon as the process starts gates on nothing**, and the rollout proceeds through a fleet of broken instances.
- **A grace period long enough for startup** — too short and healthy instances are killed during initialisation, producing an infinite replacement loop (A4.4, K9.10).
- **Readiness and liveness must be distinguished** (K9.10) — readiness gates traffic and the rollout; liveness restarts. **Conflating them means a slow-starting instance gets killed rather than waited for.**
- **A progress deadline** so a stalled rollout fails visibly rather than hanging indefinitely.
- **Don't check deep dependencies in the readiness of every instance** (O15.8) — if the database blips, every instance fails readiness simultaneously and the rollout stalls or, worse, existing instances are pulled from rotation.

**The gap it doesn't cover**: **health checks verify the instance is up, not that the change is correct.** A version that starts perfectly and returns wrong answers passes every health check. **That's what canary analysis is for** (C8.5) — and stating that boundary is what completes the answer.

**C7.12 — The cost of each strategy**

| Strategy | Infrastructure | Complexity | Rollback speed | Blast radius on failure |
|---|---|---|---|---|
| **Recreate** | None extra | **Lowest** | Redeploy old (minutes) | Total, plus downtime |
| **Rolling** | None extra (or +`maxSurge`) | Low | **Slow — another rolling deploy** | Gradual, but reaches everyone |
| **Blue/green** | **~2× during transition** | Medium | **Fastest — switch back** | **Total at cutover** |
| **Canary** | Small extra | **Higher — routing, analysis, automation** | Fast — shift traffic back | **Smallest — bounded by percentage** |
| **Shadow** | ~2× compute, plus write-suppression work | **Highest** | N/A (no user traffic) | None |

**The complexity costs that are easy to underestimate:**

- **Canary needs traffic-splitting infrastructure** (an ingress controller, a mesh, or a load balancer that supports weights) **and automated analysis** (C8.5) to be worth more than a rolling deployment. **Without the analysis, you've added complexity for a slower rollout.**
- **Blue/green needs the routing switch, environment provisioning, and the discipline to actually verify green before cutting over** — a blue/green where nobody tests green is just a slower recreate.
- **Shadow needs write suppression** (C7.5), which is application work.
- **All of them need graceful shutdown, health checks, and compatible changes** (C7.10, C7.11, C6.9) — **which are the actual prerequisites**, and a team that hasn't got those right will not get value from a sophisticated strategy.

**The judgement to express**: **strategy sophistication should follow blast radius and the maturity of the fundamentals.** Rolling with good health checks and compatible changes covers most services well. **Canary with automated analysis is worth it for high-blast-radius services**, and the cost is real. **Adopting canary before you've got graceful shutdown right is optimising the wrong thing.**

---

## C8. Progressive delivery

**C8.1 — Feature flags and decoupling deploy from release**

**A feature flag is a conditional that determines whether a code path is active, controlled at runtime rather than at build or deploy time.**

```python
if flags.enabled("new-pricing-engine", user=user, default=False):
    return new_pricing(order)
return legacy_pricing(order)
```

**What it enables** (C6.1):

- **Deploy dark** — the code is in production, inactive, verified as deployable, and not affecting anyone.
- **Release independently of deployment** — flip the flag when the business is ready, with no deployment.
- **Instant reversal** — turning a flag off takes seconds and reverts one thing (C8.8), rather than minutes reverting everything in a release (C9.1).
- **Progressive exposure** — 1%, then 10%, then a segment (C8.7).
- **Trunk-based development** — incomplete work merges to trunk behind an off flag, so no long-lived branches (C1.3, C1.4). **This is arguably the most important enabler.**
- **Experimentation** (C7.6).
- **Operational control** — disabling an expensive feature under load (C8.2).

**The implementation options**: a managed service (LaunchDarkly, Flagsmith, Unleash), a self-hosted open-source one, or a simple config-driven approach for a small number of flags. **The requirements**: runtime evaluation without a deploy, targeting by user or segment, an audit trail of who changed what, and a fast propagation time.

**The cost, which must be acknowledged** (C8.3, C8.4): flags are code, they accumulate, they multiply the code paths under test, and they need a lifecycle. **The discipline of removal is the price of the capability.**

**C8.2 — Flag types**

**The types have different lifecycles, and conflating them is the source of flag debt** (C8.3):

- **Release flags** — hide incomplete work; enable progressive rollout. **Short-lived: days to weeks.** **Removed once fully rolled out** — this is the type that must be cleaned up.
- **Experiment flags** — A/B testing (C7.6). **Lifetime is the experiment's duration**, then removed and the winner made permanent.
- **Ops flags (kill switches)** — disable a feature or degrade functionality under load or during an incident (C8.8, O15.7). **Long-lived and deliberately permanent** — they're operational controls, not debt.
- **Permission flags (entitlements)** — enable functionality for specific customers, plans, or tiers. **Permanent by design** — this is product functionality, not a flag in the temporary sense, and it arguably shouldn't be in a flag system at all but in the entitlement model.

**Why the distinction matters:**

- **It determines the expected lifetime**, which determines whether an old flag is debt or working as intended.
- **It determines ownership** — release flags belong to the engineer who added them; ops flags to the operations team; permission flags to product.
- **It determines the cleanup policy** (C8.3) — **you can only enforce "remove flags after 30 days" if you can distinguish a release flag from a kill switch.**
- **It determines the testing requirement** — a permanent flag's combinations need testing; a release flag's don't for long (C8.4).

**The practice**: **tag flags by type at creation, with an owner and an expected removal date for the temporary ones.** That metadata is what makes the cleanup process possible rather than aspirational.

**C8.3 — Flag debt and the discipline of removing them**

**Flag debt**: flags that have served their purpose and remain in the code, with both branches still present.

**The costs:**

- **Code complexity** — every flag is a conditional, and they nest and interact. A codebase with 200 flags is genuinely harder to read and change.
- **Untested combinations** (C8.4) — the combinatorial space grows exponentially.
- **Dead code** that nobody dares delete because they're not sure the flag is off everywhere.
- **Cognitive load** — a developer must reason about which paths are live.
- **Risk** — an old flag flipped accidentally, or defaulting differently in a new environment, activates code nobody has thought about for a year.

**The discipline:**

- **An expected removal date at creation** (C8.2), with an owner.
- **Automated staleness detection** — a flag fully on or fully off for N days, or with no evaluation for N days, is flagged for removal. **Most flag platforms report this**, and it's the mechanism that makes it systematic rather than aspirational.
- **A removal ticket created automatically** when a flag goes stale.
- **Make it part of the definition of done** (C1.8) — the feature isn't done until the flag is removed.
- **Periodic review** — a quarterly sweep of flags older than the threshold, with the owning team deciding.
- **Budget it** — a team with a flag limit must remove one to add one, which is crude and effective.

**The framing**: **flags are borrowed complexity — useful, and it must be repaid.** A team that adds flags and never removes them has traded one form of technical debt (long-lived branches) for another, and the second form is harder to see.

**C8.4 — The risk of untested code path combinations**

**The combinatorial problem: N independent boolean flags produce 2^N possible states.** Ten flags is 1,024 combinations; twenty is over a million. **You cannot test them all**, and production will exhibit combinations that were never exercised anywhere.

**Where it bites:**

- **Interacting flags** — flag A changes the data format and flag B reads it, and the combination A-on-B-off was never tried.
- **Environment divergence** — staging has a different flag state from production, **so what you tested is not what runs** (C5.2). **This is the most common and most damaging version.**
- **Per-user targeting** (C8.7) means different users experience different combinations, so a bug affects an unpredictable subset and is hard to reproduce.
- **Default values** — a new environment or a flag-service outage falls back to defaults, activating a combination nobody planned.

**The mitigations:**

- **Keep the number of concurrent flags small** — the discipline in C8.3 directly reduces the exponent.
- **Test the combinations that matter**: current production state, the target state, and the transitional states of the rollout in progress. **Not all 2^N — the handful that will actually occur.**
- **Avoid interacting flags.** If two flags must be coordinated, **make them one flag**.
- **Test with production's flag configuration** in staging, refreshed automatically — which removes the environment divergence case.
- **Sensible, safe defaults** — a flag-service failure should degrade to the known-good path, not to an untested one.
- **Short flag lifetimes** (C8.3), which bounds how long any combination can persist.

**C8.5 — Automated canary analysis**

**The mechanism**: during a canary rollout (C7.4), **automatically compare metrics from the canary against the baseline** and promote, pause, or roll back based on the result.

```yaml
# Argo Rollouts AnalysisTemplate (illustrative)
metrics:
  - name: error-rate
    interval: 1m
    count: 10
    successCondition: result < 0.01
    failureLimit: 2
    provider:
      prometheus:
        query: |
          sum(rate(http_requests_total{version="canary",status=~"5.."}[2m]))
            / sum(rate(http_requests_total{version="canary"}[2m]))
  - name: latency-p99
    successCondition: result < 0.5
    provider:
      prometheus:
        query: histogram_quantile(0.99, ...)
```

**What makes it work:**

- **Compare canary against baseline, not against an absolute threshold.** **This is the essential design point**: an absolute threshold fails during an unrelated incident or a traffic pattern change. **Comparing the canary to the concurrently-running stable version controls for everything environmental** — same time, same traffic, same dependencies.
- **Metrics that reflect user impact** — error rate, latency percentiles, and where possible a business metric (checkout completion, payment success).
- **Statistical sensitivity appropriate to the traffic volume** — at 1% of a low-volume service the sample is too small to conclude anything (C7.4).
- **Multiple metrics with a failure limit**, so one noisy datapoint doesn't abort.
- **Automatic rollback on failure**, not a notification.

**Why it's the thing that makes canary valuable** (C7.4): **a human watching a dashboard for ten minutes catches obvious failures and misses subtle ones**, and won't be watching at 3am. Automated analysis catches a 0.3% error rate increase that no human would notice, and it does so consistently.

**The tools**: Argo Rollouts, Flagger, Spinnaker's Kayenta.

**C8.6 — Promotion and rollback criteria defined before starting**

**The principle: decide the criteria before the rollout, when you're calm, not during it when you're anxious and invested.**

**A rollout plan should state, in advance:**

| | Defined before starting |
|---|---|
| **Stages** | 1% → 5% → 25% → 50% → 100% |
| **Bake time per stage** | 10 / 15 / 30 / 30 minutes |
| **Promotion criteria** | Error rate within 0.1% of baseline; p99 latency within 10%; no increase in 5xx by endpoint |
| **Rollback criteria** | Error rate > 0.5% above baseline for 2 consecutive minutes; p99 > 1.5× baseline; any spike in a named business metric |
| **Who decides** | Automated (C8.5); the on-call may abort at any point without approval |
| **Rollback mechanism** | Shift traffic to stable; flag off if applicable |
| **Communication** | Where the rollout status is visible; who is notified on abort |

**Why defining it in advance matters, specifically:**

- **In the moment, you are invested in the change succeeding.** A 0.3% error rate increase looks like noise when you want to promote and like a disaster when you're neutral. **Pre-defined criteria remove the motivated reasoning**, and that's the psychological argument that makes this more than process.
- **It makes automation possible** (C8.5) — you cannot automate a judgement you haven't specified.
- **It removes hesitation** — the on-call doesn't need to decide whether to abort; the criteria already decided.
- **It surfaces missing observability** — if you can't state a criterion because you don't measure the thing, that's a finding before the rollout rather than during it (O1.6).

**C8.7 — Ring-based or percentage-based rollout**

- **Percentage-based** — a random percentage of requests or users. Simple, statistically clean for analysis (C8.5), and **you can't control who's affected.**
- **Ring-based** — concentric groups of increasing size and decreasing tolerance for breakage:

```
Ring 0: internal / dogfooding (employees)
Ring 1: beta / opt-in customers
Ring 2: low-risk customer segment, or one region
Ring 3: general availability
```

**The comparison:**

| | Percentage | Rings |
|---|---|---|
| Who's exposed first | Random | **Chosen — most tolerant first** |
| Statistical analysis | **Clean** — random assignment | Biased by ring composition |
| Consistency for a user | Needs sticky assignment | **Inherent** |
| Feedback quality | Anonymous | **Named users who will report problems** |
| Fit | Technical safety verification | **Product changes and UX** |

**Ring-based is better when the failure mode is qualitative** — a confusing UI, a workflow that doesn't fit — because **internal users and beta customers will tell you**, where a random 1% will silently churn. **Percentage-based is better for technical verification**, because random assignment makes the metrics comparable.

**The practicalities**: **sticky assignment is essential for anything user-facing** — a user flipping between versions is a bad experience and invalidates measurement. Hash the user ID to assign consistently. **Segment by tenant rather than user in a B2B context**, because a tenant's users seeing different behaviour is confusing.

**Combined with geography or infrastructure**: rolling out one region or one cluster at a time gives both blast radius control and a natural rollback boundary.

**C8.8 — Kill switches, and why they differ from rollback**

**A kill switch is a pre-built, always-present control that disables a feature or degrades functionality instantly, without a deployment.**

**How it differs from a rollback:**

| | Rollback | Kill switch |
|---|---|---|
| Mechanism | Deploy a previous artefact | **Flip a flag / change config** |
| Time to effect | **Minutes** (a full deployment cycle) | **Seconds** |
| Scope | **Everything in that release** | **One specific behaviour** |
| Prerequisites | The old artefact exists, and is compatible (C9.4) | The switch was built in advance |
| Risk | Another deployment, with its own risk | Very low — a known, tested path |
| Available when? | If rollback is possible at all (C9.3) | **Always, by design** |
| Who can use it | Whoever can deploy | **Often the on-call, without a deploy** |

**The operational difference that matters most**: **a rollback reverts everything in the release, including changes that are fine.** A kill switch disables precisely the problematic behaviour and leaves the rest. **During an incident that precision is worth a great deal** — you stop the bleeding without reverting a day's work and without a second deployment under pressure.

**What to build them for:**

- **Any new feature with meaningful risk** (a release flag doubles as one, C8.2).
- **Expensive operations** that can be shed under load (O15.3) — recommendations, personalisation, non-essential enrichment.
- **Third-party integrations** that may fail (O15.7's graceful degradation).
- **Anything that touches money or data at scale.**

**The requirements**: **it must be tested** — a kill switch never exercised probably doesn't work (C9.2); **it must be fast to reach** and usable by the on-call without a deployment; **and the degraded path must be a real, working path** (O15.7), not an untested error handler.

---

## C9. Rollback & recovery

**C9.1 — Rollback vs fix-forward, choosing under pressure**

- **Rollback** — return to the previous known-good version.
- **Fix forward** — deploy a new version containing the fix.

**Choose rollback when:**

- **The previous version is known-good and reachable**, and rollback is genuinely possible (C9.3, C9.4).
- **The cause is unclear.** **This is the key case**: rollback doesn't require understanding the problem, only knowing that it started with this release. **Diagnosis can happen afterwards, with the pressure off.**
- **Impact is significant and ongoing.**
- **Rollback is fast and well-tested** (C9.2).

**Choose fix-forward when:**

- **Rollback is impossible** — an incompatible migration (C9.4), an irreversible side effect (C9.3).
- **The fix is small, obvious, and confidently understood** — a one-line config value, an obviously-wrong constant.
- **The previous version has its own serious problem** — you're rolling back into a different incident.
- **Rolling back would revert other changes the business needs**, and the batch is large (C1.9) — which is itself an argument for smaller batches.
- **The problem is data or environmental**, not code, so a different artefact changes nothing.

**The default position to state: prefer rollback, because it's the option that doesn't require you to be right.** Fix-forward under pressure means writing, reviewing, and deploying code during an incident, with degraded judgement and no time to test — **and the fix frequently makes things worse.**

**The organisational point**: **the choice should be made in advance where possible.** A runbook stating "if error rate exceeds X after a deploy, roll back first and diagnose after" removes the decision from the moment (C8.6). **The pressure to fix forward comes from investment in the change** — the same motivated reasoning as C8.6, and pre-committing is the defence.

**C9.2 — Ensuring rollback is tested rather than assumed**

**An untested rollback is a plan, not a capability** — the same argument as untested backups (DB6.5) and untested DR (A11.8).

**What breaks in practice:**

- **The previous artefact was deleted** by a retention policy (C3.5).
- **The rollback deploys, and the schema has moved on** so the old version can't read it (C9.4).
- **Configuration has changed** since — a new required environment variable the old version doesn't set, or a removed one it needs.
- **A dependency has moved on** — another service deployed a change the old version can't talk to (C6.9).
- **The rollback path itself is broken** — a pipeline job nobody has run in months, with an expired credential.
- **Nobody knows how**, because the person who set it up has left.

**How to test it:**

- **Roll back in staging routinely**, as part of the deployment pipeline — deploy, verify, roll back, verify. **Cheap, and it exercises the mechanism.**
- **Roll back in production deliberately** on a low-risk change, occasionally. **The only real test.**
- **Automated rollback triggers** (C9.5) mean the path is exercised whenever they fire, which is the best case — it's tested by use.
- **Include rollback in game days** (A11.8, T7.9).
- **Measure the time it takes** — that number is your recovery time (C9.6), and without measuring you're guessing.

**The related discipline**: **every deployment should state its rollback plan**, and for anything unusual, the plan should have been rehearsed. "We'll roll back if it goes wrong" is not a plan unless someone has done it.

**C9.3 — What makes a change irreversible**

**The categories:**

- **Destroyed data.** A dropped column, a deleted table, a purged record (DB6.6). **The code can be reverted; the data cannot.** The most common and most serious.
- **A lossy data transformation** — truncating a field, merging records, normalising a value. **The old value is gone.**
- **External side effects** — an email sent, a payment taken, a webhook delivered, a partner notified, a message published to a topic other systems have consumed (M2.10). **You cannot un-send.**
- **Third-party state changes** — an order placed with a supplier, a record created in an external system.
- **Schema changes the old version can't read** (C9.4).
- **Anything consumed downstream** — an event published in a new format that consumers have already processed.
- **Cryptographic operations** — a key rotated and old material destroyed (A10.7).
- **Time** — a scheduled job that ran, a rate limit consumed, a certificate revoked.

**The practices that preserve reversibility:**

- **Expand-contract** (DB7.3) — the destructive step happens long after the point at which you'd want to roll back.
- **Soft delete first** — rename rather than drop, mark rather than delete, and remove later (DB7.6).
- **Separate the irreversible step into its own release**, so the reversible changes can be rolled back independently.
- **Order the irreversible steps last** in a sequence, so a failure earlier leaves everything reversible (M2.11's saga ordering argument).
- **Idempotency and an outbox** for external effects, so a retry doesn't duplicate (M2.3).
- **Feature flags** to gate the irreversible action, so it can be disabled before it's taken (C8.8).

**The framing**: **identify the irreversible step in any change, and treat it as a distinct decision point.** Everything before it is a normal deployment; everything after it needs a different plan (C9.8).

**C9.4 — How a database migration constrains rollback**

**The constraint**: the application version and the schema version must be compatible. **A rollback changes the application; it does not change the schema** (and shouldn't — reversing a migration is usually worse, C9.3).

**The cases:**

| Migration | Roll back the app? |
|---|---|
| Added a nullable column | **Yes** — the old version ignores it |
| Added a table | **Yes** |
| Dropped a column the old version reads | **No** — the old version breaks |
| Renamed a column | **No** — the old version reads a name that's gone |
| Changed a type incompatibly | **No** |
| Added a `NOT NULL` column the old version doesn't write | **No** — the old version's inserts fail |
| Data transformed to a new format | **No** — the old version can't read it |

**The rule that follows: a migration must be backwards compatible with the currently-deployed application version, and remain so for as long as you might want to roll back to it** (C6.9, DB7.5).

**Which means expand-contract** (DB7.3), sequenced across releases:

1. **Release N**: add the new column, nullable. **Both versions work.** Rollback safe.
2. **Release N+1**: application writes both old and new. Rollback to N safe.
3. **Release N+2**: application reads the new. Rollback to N+1 safe.
4. **Release N+3**: stop writing the old. **Rollback to N+2 safe, to N+1 not.**
5. **Release N+4**: drop the old column. **By now, rolling back that far isn't a live option anyway.**

**The point that makes this land**: **the destructive step happens several releases after the change it supports, by which time the rollback window has closed naturally.** That's what makes expand-contract safe rather than merely tedious — **the irreversibility arrives when you no longer need reversibility.**

**C9.5 — Automated rollback triggers and false-positive risk**

**The mechanism**: define conditions that automatically revert a deployment — error rate above a threshold, latency regression, failed health checks, a business metric dropping (C8.5, C8.6).

**Why automate it**: **speed.** Automated rollback happens in seconds to minutes; a human noticing, diagnosing, deciding, and acting takes much longer — and at 3am, much longer again. **It directly reduces time-to-restore** (C9.6, C11.1).

**The false-positive risk, which is the substance:**

- **An unrelated incident** — a downstream dependency degrades during your rollout, error rate rises, and the rollback triggers on a change that was fine. **You've now added a deployment to an ongoing incident.**
- **Noisy metrics** on low-traffic services, where a handful of requests moves the percentage dramatically (C7.4).
- **A traffic pattern change** coinciding with the rollout.
- **A metric that legitimately changes** — the new version is *supposed* to alter the behaviour being measured.

**Mitigating false positives:**

- **Compare canary to baseline, not to an absolute threshold** (C8.5) — **the single most effective mitigation**, because it controls for everything environmental.
- **Require sustained breach** — N consecutive intervals, not a single datapoint.
- **Require sufficient sample size** before concluding.
- **Multiple metrics with a failure limit**, so one noisy signal doesn't trigger alone.
- **Make rollback cheap and safe** — if a false rollback costs little, a slightly trigger-happy threshold is the right trade. **That's the key judgement: the cost of a false positive versus the cost of a slow response to a true one**, and for most services the second is much larger.

**The safeguard**: **an automated rollback should notify loudly and be reviewable.** A rollback that happens silently and repeatedly, masking a real problem, is its own failure mode.

**C9.6 — Measuring and reducing time to restore**

**Time to restore (MTTR)** — one of the four DORA metrics (C11.1) — is the time from a failure being detected to service being restored.

**Measuring it honestly:**

- **Start the clock at impact, not at detection.** If users were affected for 20 minutes before anyone noticed, that's part of it — **otherwise poor detection makes the metric look better**, which is exactly backwards.
- **Stop at restored, not at root-caused.** Restoring service and understanding the cause are different milestones.
- **Report the distribution**, not the mean — the p90 is what matters, and a single bad incident dominates an average.
- **Capture it from systems** — the incident record's start and end, correlated to the deployment record (C10.7).

**Reducing it:**

| Phase | Reduction |
|---|---|
| **Detect** | Better alerting on symptoms and SLOs (O8.4, T7.3); synthetic monitoring (O1.5) |
| **Diagnose** | Observability with correlation (O1.7); **and rollback removes this phase entirely** (C9.1) |
| **Decide** | Pre-defined criteria (C8.6); a clear runbook (T4) |
| **Act** | **Fast, tested rollback** (C9.2); kill switches (C8.8); automation (C9.5) |
| **Verify** | Post-deploy verification (C4.8) |

**The largest lever, and it's worth stating explicitly: rollback removes the diagnosis phase from the critical path.** You don't need to understand the problem to restore service — which is why C9.1's default matters so much for this metric.

**The second largest**: **small batches** (C1.9). A deployment with one change has one suspect; the diagnosis is faster and the rollback reverts less.

**C9.7 — Handling a partially completed deployment**

**A deployment can fail midway**: some instances updated and some not; a database migration partially applied (DB7.10); a multi-service release with two of four services deployed (C6.8).

**The approach:**

1. **Stop the deployment.** Don't let it continue while you decide — pause the rollout, which most controllers support.
2. **Establish the actual state.** Which instances are on which version? Did the migration complete? **`kubectl get pods` and the deployment's revision history, or the equivalent** — don't assume.
3. **Determine whether the mixed state is safe.** **If the change was backwards and forwards compatible** (C6.9), a mixed state is exactly what a rolling deployment produces normally and is fine — **so you have time to think.** If it isn't compatible, you're in a degraded state and need to resolve it quickly in one direction or the other.
4. **Decide: complete or revert.** Completing is right if the failure was transient (a node with no capacity, a transient registry failure). Reverting is right if the new version is the problem.
5. **For a partially-applied migration** (DB7.10): **forward is usually safer** — a corrective migration to a known state — because a down migration on a partial state may itself fail.
6. **Verify the end state explicitly** rather than assuming the controller sorted it out.

**Why it's more likely with some strategies**: **rolling deployments have a mixed state by design** (C7.2), so a partial failure is a longer-lived version of normal. **Blue/green's cutover is atomic**, so it either happened or didn't — which is one of its genuine advantages (C7.3).

**The prevention**: health gating so a bad version stops after one instance (C7.11); progress deadlines with automatic rollback (K2.5); compatible changes so any intermediate state is safe (C6.9); and **not deploying several services simultaneously** (C6.8).

**C9.8 — Deploying safely when rollback isn't possible**

**When the change is irreversible** (C9.3) — a destructive migration, an external side effect, a one-way data transformation — **the entire safety model changes**, because your primary recovery option is gone.

**What to do instead:**

- **Isolate the irreversible step.** Separate it into its own release, so everything around it remains reversible (C9.3). **Then only that one step carries the elevated risk.**
- **Delay irreversibility.** Expand-contract (DB7.3) means the destructive step happens weeks later, after confidence has been established — **and this is the single most effective technique.**
- **Gate it behind a flag** (C8.8), so the behaviour can be disabled even if the underlying change can't be undone.
- **Make it recoverable rather than reversible.** **A verified, tested backup taken immediately before** (DB6.4) converts "irreversible" into "recoverable with an RTO" — different, and much better than nothing.
- **Dry-run it.** Run the migration against a restored production-sized copy (DB7.7) and verify the result before doing it for real.
- **Do it progressively** where possible — migrate 1% of records, verify, continue (DB7.8). **A bad transformation caught at 1% is a very different incident from one caught at 100%.**
- **Increase the verification bar** — more testing, more review, more approval (C10.2), and a second person present.
- **Choose the timing deliberately** — low traffic, full staffing, not before a weekend.
- **Write the recovery plan explicitly**, including the restore procedure and its measured RTO, and have it reviewed before starting.

**The framing to give**: **when you can't roll back, you buy safety with verification and blast radius instead.** More testing before, smaller increments during, and a tested recovery path after — because the cheap safety net is gone and the expensive ones have to substitute.

---

## C10. Security & governance in delivery

**C10.1 — Separation of duties in an automated pipeline**

**The control's intent** (S10.1): **no single person can unilaterally put arbitrary code into production.**

**How it's satisfied in an automated pipeline:**

- **The author cannot approve their own change** — branch protection requiring a review from someone else, with the author excluded.
- **The approver cannot bypass the pipeline** — the deploy credential is only assumable from the protected context (C10.3), so approval is necessary and merging is the only path.
- **The pipeline configuration is itself reviewed** — **this is the gap people miss**: if anyone who can merge can also edit the workflow, they can grant themselves anything. **Protect the workflow files with a CODEOWNERS rule requiring platform-team review** (S7.9).
- **Production approval is a distinct permission** from merge permission (C5.10) — a protected environment with a named reviewer group.
- **Everything is recorded** (C10.7).

**The failure modes to check for:**

- **A solo approver** — in a small team, a two-person requirement may be impractical, in which case say so explicitly and compensate (automated policy checks, post-hoc review).
- **Admin bypass** — repository admins who can override branch protection. **Restrict and alarm on it.**
- **The pipeline's own credentials** being usable outside the pipeline (C10.3).
- **A break-glass path** with no controls (C10.6).

**The argument to make to an auditor** (C6.6): **an automated pipeline enforces separation of duties more reliably than a manual process**, because it cannot be skipped, it applies uniformly, and it produces a complete record. **A manual sign-off can be given without looking; a required review that blocks the merge cannot be skipped.**

**C10.2 — Approval gates that add safety rather than delay**

**A gate adds safety only if the approver has both the information and the ability to say no.**

**Gates that add safety:**

- **The approver has meaningful context** — the plan or diff (TF9.2), the canary results, the test outcomes. **Approving a change described only as "deploy v2.4.1" adds nothing.**
- **The decision is genuinely a judgement** — is now the right time, given a marketing campaign, an ongoing incident, or a freeze (C6.5)? **That's a decision a human is well-placed to make and automation is not.**
- **The change is high-risk or irreversible** (C9.8) — where extra scrutiny is proportionate.
- **The approver is accountable and competent** to assess it.

**Gates that add only delay:**

- **Approval by someone with no context**, who always approves.
- **A gate on every change regardless of risk** — which trains the approver to rubber-stamp and **erodes the authority of every gate** (C4.5).
- **A gate duplicating an automated check** — approving because the tests passed adds nothing the pipeline didn't already assert.
- **A gate whose real function is to slow deployment**, addressing a fear rather than a specific risk.

**The design guidance:**

- **Risk-proportionate gating** (TF11.3's approval-policy argument): gate the changes that destroy resources, touch IAM, or hit production data; **let routine changes flow.**
- **Automate the assessment and reserve the human for the decision.**
- **Measure the gate** — approval time, and how often it results in a rejection. **A gate that has never rejected anything in a year is not a control; it's a delay** (C4.5).

**The cost to name** (C1.2): **a gate increases batch size** by making deployment less frequent, which increases risk per deployment (C1.9). **So a badly-designed gate makes things less safe**, and that inversion is the argument to make when pushing back (S10.7).

**C10.3 — Least privilege for deployment credentials**

**The principles:**

- **OIDC federation instead of static credentials** (A2.8, S7.9) — **the highest-value single change.** The pipeline exchanges a short-lived token for cloud credentials; **no long-lived secret exists in the CI system**, so there's nothing to leak or rotate.
- **The trust policy's `sub` condition is the security boundary** — scoped to a specific repository and, for the deploy role, a specific branch or protected environment. **A wildcard there is the critical misconfiguration**, and it's common.
- **Separate roles per stage** — a plan/build role with read access, a deploy role with write, scoped so **a PR job cannot assume the deploy role** (TF9.1). This is what makes running CI on fork PRs safe (S7.10).
- **Separate roles per environment** — the staging deploy role cannot touch production.
- **Scope the permissions to what the deployment actually needs** — updating a specific Deployment, not cluster-admin (K8.11); updating a specific ECS service, not `ecs:*`.
- **Time-bound** — the credential lives for the job's duration.

**The question that exposes most problems**: **what could a malicious commit merged to main do with the pipeline's credentials?** In many organisations the answer is "anything", because the deploy role is broad and the pipeline runs on merge. **That's the risk in C10.4**, and narrowing the role is the mitigation.

**The GitOps alternative** (K10.7): **the cluster pulls rather than CI pushing**, so **no external system holds cluster credentials at all.** For a regulated environment that's a materially stronger position and is often the strongest argument for adopting it.

**C10.4 — Why the pipeline is a high-value attack target**

**The pipeline has, by design, everything an attacker wants:**

- **Production deployment credentials** (C10.3) — the ability to put code into production.
- **Access to source code**, including private repositories.
- **Registry write access** — the ability to publish a malicious artefact that will be deployed and trusted.
- **Signing keys**, if artefacts are signed there (S7.7).
- **Secrets** for every environment it deploys to (C5.11).
- **A trusted position** — its output is deployed without further scrutiny, which is the crux: **compromising the pipeline means your malicious code is deployed through the legitimate, audited process.**

**And it executes untrusted-ish code by design** (S7.10): dependencies with install scripts, third-party actions, and — with fork PRs — arbitrary contributor code.

**The real incidents that demonstrate it**: **SolarWinds** (build system compromised; malicious code inserted into a legitimately signed artefact — **signing didn't help because the build was the attack**); **Codecov** (a modified uploader exfiltrating CI environment variables from thousands of pipelines); **`tj-actions/changed-files` (2025)** (tags repointed at code dumping runner memory into logs, S7.11).

**The controls** (S7.9): OIDC over static credentials; least-privilege, environment-scoped roles; **ephemeral runners** (C2.7); **pinned actions by digest** (S7.11); **no secrets in PR workflows**; egress restrictions on runners; **protecting the pipeline configuration itself** with required review (C10.1); and audit logging of pipeline changes and runs.

**The framing that lands**: **the pipeline is production infrastructure with production credentials, and it is usually secured like a developer tool.** Treating it with the same rigour as a production system — access control, change review, audit, monitoring — is the correction.

**C10.5 — Security scanning without blocking on noise**

**The tension**: scanning finds real problems, and unfiltered output is overwhelming (S8.7). **Block on everything and the pipeline is permanently red; block on nothing and the scanning is decorative.**

**The design:**

| Finding | Action |
|---|---|
| **Secret detected** | **Block.** Near-zero false positives, catastrophic miss cost (S6.3) |
| Critical/high, **reachable**, internet-facing (S8.2) | **Block** |
| Critical/high, not reachable | Ticket with an SLA (S8.3) |
| Medium/low | Backlog, reviewed periodically |
| New finding introduced by this PR | **Block** — the delta, not the absolute |
| Pre-existing finding | Don't block this PR on someone else's debt |

**The techniques that make it workable:**

- **Gate on the delta, not the absolute.** **A PR is blocked for what it introduces, not for the accumulated backlog** — otherwise every PR is blocked by a finding from two years ago, which is the most common way scanning gates get disabled.
- **Reachability analysis** (S8.2) — `govulncheck` and equivalents eliminate most findings as unexploitable.
- **KEV and EPSS** rather than CVSS alone (S8.1) — actively-exploited vulnerabilities are a different category.
- **A baseline** — accept the current state, block regressions, and burn the backlog down separately.
- **VEX** to record determinations so a triaged finding doesn't reappear every run (S7.4).
- **Fast scans** — a scan adding ten minutes to every PR is a tax on every developer (C1.5).
- **Actionable output** — which dependency, which version fixes it, and ideally an automated PR.

**The principle**: **a gate people bypass is worse than no gate** (C4.5), because it trains bypassing as a habit and erodes every other gate's authority.

**C10.6 — Break-glass deployment and its audit requirements**

**The need**: during a severe incident, the normal path may be too slow or unavailable — the pipeline is down, a required approver is unreachable, or minutes matter.

**A well-designed break-glass path** (S9.2, TF13.6):

1. **A named, pre-existing mechanism** — a separate emergency workflow, or an elevated role — **not improvised during the incident.**
2. **Requires a deliberate act** with a justification and an incident reference.
3. **Still produces an artefact and a record** — even in an emergency, the deployment should be traceable to something (C3.8).
4. **Alarmed in real time**, not merely logged — **a break-glass deployment that isn't an incident is itself an incident.**
5. **Time-bounded** — the elevated access expires.
6. **Fully audited**: who, what, when, why, which artefact, correlated to the incident (C10.7).
7. **Mandatory retrospective reconciliation** — the change must be brought back through the normal path, with code review and tests, within a defined window. **This is the step that's always skipped**, and skipping it means the emergency change becomes permanent undocumented drift.
8. **A post-incident review** asking **why the normal path was insufficient** — because if the answer is "the pipeline takes 40 minutes", that's the actual finding (C12.7).

**The argument for having one**: **an organisation with no break-glass path doesn't have fewer emergency changes — it has the same number, made with someone's personal credentials, unrecorded.** Designing it makes it visible, bounded, and auditable, which is a strictly better outcome and is the argument that gets it approved in a regulated environment.

**C10.7 — A deployment audit trail from systems, not spreadsheets**

**What the trail must answer** (C6.7): what changed, who wrote it, who reviewed it, who approved it, when it was deployed, what artefact was deployed, and whether the process was followed — **over a period, continuously.**

**The sources, all generated automatically:**

| Question | System of record |
|---|---|
| What changed | The PR diff; the artefact digest (C3.1) |
| Who wrote it | Git commit, signed if required |
| Who reviewed it | PR review record, with required-reviewers enforced |
| Who approved deployment | Protected environment approval record |
| When deployed | Pipeline run, or the GitOps commit (K10.7) |
| What was deployed | The digest, with provenance (C3.7) |
| To where | The deployment target in the manifest |
| Was the process followed | Branch protection config + the absence of manual deployments |

**Why systems beat spreadsheets** (S10.2): **a spreadsheet or a change ticket records what someone said happened; the systems record what happened.** The pipeline's record is complete (every change went through it), continuous (covers the period, not a sample), tamper-evident (S9.7), and free (generated as a by-product).

**The requirements to make it hold:**

- **No deployments outside the pipeline** (C5.10) — one manual `kubectl apply` and the completeness claim is false.
- **Audit logs shipped off-system** and immutable (S9.7), so a compromised actor can't edit the record.
- **Retention covering the audit period** (S10.5).
- **The mapping to control requirements agreed in advance** with compliance (C6.6).

**The exercise worth doing**: **pick a random production deployment from three months ago and produce the whole chain in under five minutes.** That's what an auditor will ask, and rehearsing it finds the broken link before they do.

**C10.8 — How compliance requirements change pipeline design**

**The changes that actually apply:**

- **Separation of duties enforced structurally** (C10.1) — branch protection, environment approvals, and workflow files protected.
- **Every change traceable to an authorised request** (C10.7).
- **Approval gates on production**, with a defined approver group (C10.2).
- **Evidence generated continuously** rather than assembled (S10.2).
- **Retention** of pipeline logs, artefacts, and approvals for the required period (C3.5).
- **Vulnerability management with SLAs** enforced in the pipeline (C10.5, S8.3).
- **Access reviews** of who can deploy where (C5.10).
- **A documented, audited break-glass path** (C10.6).
- **Data residency** possibly constraining where builds run and where artefacts are stored (S10.4).
- **Change categorisation** — pre-approved standard changes versus those needing CAB (C6.6).

**What compliance does *not* require, and this is the important half:**

- **Manual deployments.** Nothing in SOC 2, ISO 27001, or PCI DSS requires a human to run the deploy command.
- **Infrequent releases.** The controls are about authorisation and traceability, not cadence.
- **A weekly CAB for routine changes** — standard change categories exist precisely for this.
- **Screenshots as evidence** (S10.2).

**The argument to make** (S10.6, S10.7): **an automated pipeline provides better control and better evidence than a manual process** — it's consistent, it cannot be skipped, and it produces a complete record. **Work with compliance early, map the pipeline's artefacts to the control objectives, and get the mapping agreed.** The outcome is usually that you can deploy frequently *and* be more compliant, and demonstrating that is one of the more valuable things a platform lead does in a regulated firm.

---

## C11. Metrics & improvement

**C11.1 — The four DORA metrics and what each reveals**

| Metric | Definition | Reveals |
|---|---|---|
| **Deployment frequency** | How often you deploy to production | **Batch size and process friction** (C1.9) |
| **Lead time for changes** | Commit to running in production | **End-to-end delivery efficiency** (C11.3) |
| **Change failure rate** | % of deployments causing a degradation requiring remediation | **Quality of the delivery process** (C11.4) |
| **Time to restore** | How long to recover from a failure | **Operational resilience** (C9.6) |

**What each actually tells you:**

- **Deployment frequency is a proxy for batch size.** Low frequency means large batches, which means higher risk per deployment and slower feedback. **It's a measure of process friction, not of effort.**
- **Lead time exposes where the time goes** — and it's usually not in coding. Measured honestly (C11.3), it surfaces queueing: waiting for review, waiting for a gate, waiting for a release window.
- **Change failure rate measures whether speed is costing quality.** It's the counterweight that stops frequency being gamed.
- **Time to restore measures whether you can recover** — and it's the one most improved by rollback capability (C9.1) and small batches.

**The pairing to explain**: **frequency and lead time are throughput; change failure rate and time to restore are stability.** DORA's central finding is that **high performers do well on both** — they're not in tension (C11.2).

**The caveats worth adding**: they measure the delivery process, not business value — a team can deploy fifty times a day and ship nothing useful. **And they're gameable** (C11.5). They're a diagnostic, not a target.

**C11.2 — Why frequency and stability are not in tension**

**The intuition says they are**: deploy more often, break things more often. **The DORA research consistently found the opposite** — high performers are better on all four metrics simultaneously.

**The mechanism, which is the substance of the item:**

- **Frequent deployment forces small batches** (C1.9). A small change is easier to review, easier to test, easier to diagnose when it breaks, and easier to roll back. **Risk per deployment falls.**
- **Frequent deployment means the deployment path is exercised constantly**, so it works. **A team deploying fifty times a week has a reliable, rehearsed deployment; one deploying monthly has a risky, unfamiliar event** — and the monthly one is where things go wrong.
- **The capabilities that enable frequency are the same ones that produce stability**: comprehensive automated testing, trunk-based development, small changes, fast rollback, good observability. **You cannot deploy safely at high frequency without them, and having them makes you stable at any frequency.**
- **Fast feedback catches problems earlier**, when they're small.
- **Fast recovery** (C9.6) means a failure is a brief degradation rather than an outage, which lowers the cost of failing.

**The causal claim to state carefully**: **it's not that deploying more often makes you stable.** It's that **the practices required to deploy frequently and safely also produce stability** — and an organisation that responds to instability by deploying less often is treating a symptom and making the underlying problem worse (C6.5's freeze argument).

**The rhetorical version**: **if deploying is risky, the answer is to deploy more often until it isn't** — because the risk comes from batch size and unfamiliarity, both of which frequency reduces.

**C11.3 — Measuring lead time honestly**

**The definition**: **from commit to running in production.** Not from ticket creation, not from start of work, and not from merge — those are easier to measure and they hide the delivery bottleneck.

**Measuring it:**

```
commit timestamp → first deployment to production containing that commit
```

**Derived from**: git commit times, and the deployment record's artefact digest mapped back to the commits it contains (C3.8). **With GitOps this is straightforward** — the deployment commit references the digest, and the digest maps to the source commit.

**The dishonest measurements to avoid:**

- **From merge rather than commit** — hides review and CI queue time, which is frequently the largest component.
- **To "deployed to staging"** — the whole point is production.
- **Mean rather than distribution** — one long-running change dominates, and **the p50 and p90 tell you far more than the mean.**
- **Excluding changes that took a long time** as outliers — **the outliers are where the process problem lives.**
- **Measuring only successful deployments.**

**What the breakdown reveals** (C11.6) — decompose the total into: commit → PR open, PR open → approved, approved → merged, merged → deployed to staging, staging → production. **The largest segment is your bottleneck**, and it's very often waiting for review or waiting for a release window rather than anything technical.

**The typical finding**: teams assume the pipeline is the bottleneck and measure it to discover that **the median change spends four hours in the pipeline and three days waiting for a human** — which redirects the improvement effort entirely.

**C11.4 — Change failure rate and defining failure**

**The definition: the percentage of deployments to production that result in degraded service requiring remediation** — a rollback, a hotfix, a patch, or an incident.

**Defining "failure" is the hard part, and it must be defined explicitly or the metric is meaningless:**

**Counts as a failure:**

- A rollback was required.
- A hotfix was deployed to correct it.
- An incident was declared.
- An SLO was breached as a result.
- Users were affected.

**Doesn't count:**

- A deployment that failed in the pipeline and never reached production — **that's the pipeline working**, and counting it discourages the gates from being strict.
- A pre-existing bug discovered after deployment but not caused by it.
- An unrelated incident coinciding with a deployment.
- A canary aborted automatically before reaching users — **that's a success of the process**, and counting it as a failure discourages canary use (C11.5).

**The definitional edge cases to decide in advance**: a change that caused a minor degradation nobody noticed; a deployment requiring a follow-up config tweak; a feature flagged off after release (C8.8) — **is that a failure or the mechanism working as intended?** **Arguably the latter**, and deciding consistently matters more than which way you decide.

**The measurement**: correlate the deployment record (C10.7) with the incident record, ideally automatically. **Manual classification drifts** and is subject to the pressure in C11.5.

**The benchmark**: DORA's high performers sit around 0–15%. **A rate of 0% is suspicious** — it usually means the definition is too narrow, or the team is deploying so cautiously that throughput has suffered.

**C11.5 — How metrics get gamed, and guarding against it**

**The gaming, per metric:**

- **Deployment frequency** — deploy trivial no-op changes to inflate the count. Split one change into five deployments.
- **Lead time** — measure from merge rather than commit (C11.3); start the clock late; classify slow changes as out of scope.
- **Change failure rate** — **redefine failure narrowly**; classify incidents as "not caused by a deployment"; fix forward quietly rather than declaring a rollback; **avoid canary because an aborted canary looks like a failure** (C11.4).
- **Time to restore** — start the clock at declaration rather than at impact, so slow detection improves the number (C9.6); declare "restored" early.

**Guarding against it:**

- **Derive metrics from systems automatically**, not from self-reporting (C10.7). A metric a team enters by hand is a metric they can shape.
- **Define the terms precisely and in writing**, especially "failure" (C11.4).
- **Look at all four together.** **This is the strongest guard**: gaming one usually degrades another. Inflating frequency with trivial deployments doesn't improve lead time for real changes; narrowing the failure definition doesn't reduce actual incidents, which show up in time-to-restore.
- **Never use them for individual or team performance evaluation.** **This is the essential point** — the moment they're used to compare teams or rate people, they will be gamed, and you lose the diagnostic entirely. **They're for the team to understand its own system**, not for management to rank.
- **Pair them with outcome measures** — SLO attainment, incident count, and actual user impact.
- **Ask what the trend means rather than what the number is.**

**The framing**: **Goodhart's law applies** — a measure that becomes a target ceases to be a good measure. **The defence is to treat them as a diagnostic that prompts questions, not a scoreboard** (C4.6's coverage argument, generalised).

**C11.6 — Identifying the delivery bottleneck with evidence**

**The method: measure the end-to-end path, decompose it, and find the largest segment.**

**Decompose lead time** (C11.3):

```
commit → PR opened          : 4h   (batching work before opening)
PR opened → first review    : 18h  ← the bottleneck
first review → approved     : 6h
approved → merged           : 0.5h
merged → staging            : 25m
staging → production        : 48h  (waiting for the twice-weekly release window)
```

**Two bottlenecks visible immediately**: review latency and the release window. **Neither is the pipeline**, which is where everyone assumed the problem was — and that's the typical finding.

**The evidence sources**: git and PR timestamps; pipeline run records (C2.10); deployment records; incident records; **and queue time specifically**, which is the most commonly missed (C2.3).

**The common bottlenecks, and they're rarely technical:**

- **Waiting for review** — the largest in many organisations. Fixed by smaller PRs, review SLAs, and rotation.
- **A release window or approval gate** (C10.2, C6.4).
- **Manual testing or a QA handoff.**
- **Environment contention** — waiting for staging (C5.5's ephemeral environments fix this).
- **Pipeline duration and queueing** (C2.11).
- **Coordination across teams** (C6.8).

**The discipline**: **fix the largest segment, then re-measure** — because removing one bottleneck reveals the next (O13.8's iterative argument). **And don't optimise what isn't the constraint** (O14.5) — halving a 25-minute pipeline when the median change waits 48 hours for a release window improves lead time by 1%.

**C11.7 — Making the case for delivery investment in business terms**

**The translation from engineering to business language, which is the skill being assessed:**

| Engineering framing | Business framing |
|---|---|
| "The pipeline is slow" | **"We lose the equivalent of three engineers to build waits"** (C2.11) |
| "We deploy fortnightly" | **"A customer-requested fix takes two weeks to reach them"** |
| "Rollback isn't tested" | **"Our worst-case recovery is unknown and we'd find out during an outage"** |
| "Change failure rate is 25%" | **"One in four releases causes a customer-visible problem"** |
| "We need feature flags" | **"Marketing could control launch timing without an engineering release"** |
| "Lead time is 5 days" | **"Five days between deciding and delivering — competitors ship in hours"** |

**A worked case:**

> "Median lead time from commit to production is 5.2 days. The breakdown shows 18 hours waiting for review and 48 hours waiting for the twice-weekly release window — so 66 of those 125 hours are queueing, not work.
>
> Moving to on-demand releases behind feature flags removes the release window entirely. The investment is roughly six weeks of one engineer to build the flag infrastructure and adopt it in the top three services.
>
> The return: lead time falls to under a day, so a customer-requested change ships the same week rather than the next fortnight. Batch size falls, which the DORA research associates with a lower change failure rate — and our current rate is 22%, so each release causing a problem costs an average of four engineer-hours plus the customer impact. And marketing gains control of launch timing, which they've asked for twice this year."

**The elements**: **a measured baseline**, **a decomposition showing where the time goes**, **a specific investment with a cost**, **a quantified return in terms the business cares about**, and **a secondary benefit for another function**. Without the baseline it's an opinion; with it, it's a decision.

---

## C12. Judgement

**C12.1 — When continuous deployment is inappropriate**

**The cases:**

- **The blast radius of a bad change is catastrophic and unrecoverable** — a payments ledger, a medical device, a trading system, industrial control. **Where an automated bad deployment could cause irreversible harm**, a human gate is proportionate.
- **Regulatory requirements mandating pre-deployment approval** — some regimes genuinely require it (C10.8). **Though check the intent** (S10.1): most require authorisation and traceability, not a manual deploy button.
- **The automated verification isn't trusted.** **This is the honest common case**: if the test suite is flaky (C4.4) or the coverage of critical paths is poor, the pipeline isn't a sufficient gate — **and the answer is to fix that, not to add a human who can't assess it better** (C10.2).
- **No progressive rollout or automated rollback** (C8.5, C9.5) — without them, a bad deployment reaches everyone with no automatic recovery, and continuous deployment amplifies rather than mitigates.
- **Software shipped to customers** — mobile apps, on-premises, embedded. **You cannot continuously deploy to someone else's device** (C6.4).
- **Deployment has an inherent cost** — a maintenance window, a customer notification, a partner coordination step.
- **A very small team with no on-call coverage** — deploying automatically at 6pm on Friday with nobody available is a choice, not an accident.

**The framing to give**: **continuous delivery is the goal everywhere; continuous deployment is a further step justified by blast radius and confidence in the automation.** And most objections to it are actually objections to inadequate automated verification — **which is a fixable problem and the right thing to invest in**, rather than a permanent reason for a gate.

**C12.2 — Designing delivery for a monolith vs many services**

**Monolith:**

- **One pipeline, one artefact, one deployment.** Simpler in every respect — no cross-service coordination (C6.8), no version compatibility matrix, no distributed tracing needed to debug a deploy.
- **The problems**: **the build is slow** because everything is built and tested every time; **any change deploys everything**, so batch size is inherently large (C1.9); **one team's failure blocks everyone's release**; and **the blast radius of a deployment is the whole system.**
- **The techniques**: **build and test only what changed** (affected-target detection — Bazel, Nx, Turborepo); **parallelise the test suite aggressively** (C2.3); **modular monolith boundaries** so changes are localised; **feature flags** so deployment doesn't mean release (C6.1) — **which recovers most of the independent-release benefit without splitting the system.**

**Many services:**

- **Independent pipelines, independent deployment**, small blast radius per deployment, teams deploy at their own pace.
- **The problems**: **cross-service compatibility** becomes a first-class concern (C6.9); **coordinated changes are hard** (C6.8); **end-to-end testing is expensive** (C4.3's contract testing is the answer); **pipeline duplication** across repositories (C2.6); and **observability must span services** (O5.8).
- **The techniques**: contract testing, compatible-change discipline, shared pipeline templates, and distributed tracing.

**The judgement to express**: **the delivery difficulty of a monolith is build time and batch size; the delivery difficulty of many services is coordination and compatibility.** Neither is universally easier. **A well-run modular monolith with feature flags and affected-target builds delivers faster than a poorly-coordinated set of services** — and saying that is a stronger answer than assuming microservices are the mature end state (K13.1's parallel argument).

**C12.3 — The platform team's contract with delivery teams**

**The platform team provides:**

- **A paved road** — templates and reusable workflows that take a service from commit to production with security scanning, artefact publishing, and progressive deployment built in (C2.6, C12.4).
- **The pipeline infrastructure** — runners, capacity, availability, with a stated SLO (C2.10).
- **Deployment mechanisms** — the tooling for rolling, canary, and rollback (C7), so teams don't each build it.
- **Environment provisioning** — ephemeral environments, staging, production access (C5.5).
- **Secrets and credentials infrastructure** — OIDC, secret injection, per-environment scoping (C5.11, C10.3).
- **Guardrails** — policy checks, required scanning, approval gates (C10.5).
- **Observability of the delivery process** — DORA metrics, pipeline duration, failure rates (C11.1).
- **Documentation, and support when things break.**

**Delivery teams provide:**

- **Their own tests**, and keeping them fast and reliable (C4.4).
- **Their own pipeline configuration**, within the provided templates.
- **Compatible changes** (C6.9) and safe migrations (DB7).
- **Their own deployment decisions and rollback readiness** (C9.2).
- **Responding to their own deployment failures** — the platform team is not on call for application errors.
- **Flag hygiene** (C8.3).

**The boundary that must be explicit**: **the platform team owns the delivery mechanism; teams own what they deliver.** A pipeline that's broken is the platform's; a test that's failing is the team's.

**The failure mode to name** (TF8.8, K13.4): **the platform team becoming a bottleneck** — every pipeline change requiring their approval, every deployment requiring their involvement. **The measure of a healthy contract is how much teams can do without asking**, and contribution to the shared templates should be open.

**C12.4 — Golden paths and why they beat mandates**

**A golden path is a well-supported, documented, opinionated route from idea to production** — a service template, a pipeline, deployment tooling, observability wired in — **that is genuinely the easiest way to do the thing.**

**A mandate is a policy requiring teams to do something.**

**Why golden paths win:**

- **They work through incentive rather than enforcement.** A team uses the path because it's faster, not because they're required to. **Compliance is a by-product of convenience**, which is far more durable than compliance through policing.
- **Mandates create resentment and workarounds.** A team required to use a tool that's worse than their alternative will comply minimally, work around it, or fork it — and you lose the standardisation you were mandating.
- **Golden paths are testable** — if teams aren't using it, you have a product problem to solve, and **that's actionable feedback**. A mandate with low compliance produces enforcement conversations instead.
- **They scale.** One well-maintained path serves fifty teams; enforcing a policy across fifty teams is a permanent cost.
- **Security and compliance come free** — a team on the golden path gets scanning, secret management, approval gates, and audit trails without asking (S9.4's secure-defaults argument).

**What makes a path golden rather than merely available:**

- **It must be genuinely faster** than the alternative. **If going around it is quicker, it isn't golden** (TF13.5).
- **It must cover the common case beautifully** and permit the unusual case somehow — **an escape hatch, with a documented process** (S10.7). Without one, teams fork it.
- **It must be maintained** — a stale template is worse than none.
- **Contribution must be open** (C12.3).

**The honest caveat**: **some things do need mandating** — the security baseline, the audit trail. **The technique is to put the mandate inside the golden path**, so following the easy route satisfies it automatically.

**C12.5 — Migrating a team from manual releases to automated delivery**

**The sequence, and the ordering is deliberate:**

1. **Understand the current process, by watching it.** What actually happens on release day, including the undocumented steps. **The gap between the documented process and the real one is where the migration risk is.**
2. **Start with something they want.** Don't begin by taking away control — begin by removing a pain point. **Automate the most tedious, error-prone step first** and let them keep the rest.
3. **Automate the build and produce a versioned artefact** (C3.1) — even if deployment stays manual. **This alone gives traceability and reproducibility**, and it's low-risk.
4. **Automate deployment to a lower environment**, so the mechanism is exercised safely and repeatedly.
5. **Build confidence with tests** — if the suite is weak, automation just ships bugs faster. **This is often the real work**, and it's where the time goes.
6. **Automate production deployment with a manual trigger** — continuous delivery, not deployment (C1.2). **The team keeps the decision; the mechanism becomes reliable.**
7. **Add progressive rollout and rollback** (C7.4, C9.1), and demonstrate a rollback working.
8. **Increase frequency gradually**, and let the improved metrics make the argument (C11.1).
9. **Remove manual access** last, once the automated path is genuinely better.

**The principles that make it work:**

- **Never remove the old path before the new one is trusted.**
- **Demonstrate rollback early** — the fear is "we won't be able to recover", and showing recovery working addresses it directly.
- **Measure before and after** (C11.7), so the improvement is visible rather than asserted.
- **Pair with the team** — a migration done to a team fails; one done with them sticks.
- **Expect the first automated production deployment to be a significant event** for them, and treat it as one.

**C12.6 — Introducing change safely into a low-trust environment**

**A low-trust environment**: previous changes caused incidents, the team has been blamed, management is risk-averse, and any proposal is met with resistance. **The technical work is the easy part.**

**The approach:**

1. **Understand why the trust is low.** There is usually a specific incident. **Learn it in detail** — it tells you what people are actually afraid of, and addressing that fear specifically is far more effective than general reassurance.
2. **Start where failure is cheap.** An internal tool, a non-critical service, a lower environment. **Build a track record before touching anything that matters.**
3. **Make the change reversible and demonstrate the reversal.** **Showing a rollback working is worth more than any argument** (C9.2) — it directly addresses "what if it goes wrong".
4. **Reduce blast radius visibly** — canary, flags, a single region. **Being seen to limit exposure builds more confidence than promising it will work.**
5. **Over-communicate.** Announce before, report during, summarise after — including when nothing went wrong. **Predictability builds trust faster than success does.**
6. **Deliver a small, visible win quickly**, and attribute it to the change.
7. **Bring the sceptics in early.** The person most opposed usually has a specific concern; **addressing it makes them an advocate**, and ignoring them makes them a permanent blocker.
8. **Never claim it's risk-free.** Overclaiming and being wrong once destroys everything. **Say what could go wrong and what you'll do about it** — that's what earns credibility.
9. **Let the metrics accumulate** (C11.1) and present the trend, not a single result.

**The framing**: **trust is rebuilt through a sequence of small, visible, reversible successes**, not through a persuasive argument. The technical plan should be designed to produce that sequence.

**C12.7 — The organisational reasons delivery improvements fail**

**The reasons, and they're rarely technical:**

- **It's treated as a tooling project.** A new CI system is installed and the practices don't change — long-lived branches, manual testing, fortnightly releases (C1.1). **The tool was never the constraint.**
- **The bottleneck wasn't measured** (C11.6). Effort goes into the pipeline while the median change waits three days for review.
- **No executive sponsorship**, so it's squeezed out by feature work every quarter.
- **The platform team builds what it finds interesting** rather than what teams need, and adoption is low (C12.4).
- **It's mandated rather than made attractive** (C12.4) — teams comply minimally and work around it.
- **Conway's law** — the delivery process mirrors the org structure, and a handoff between development, QA, and operations produces queues no amount of automation removes. **Changing the delivery process requires changing the structure**, and that's outside the platform team's authority.
- **Incentives conflict** — an operations team measured on stability and a development team measured on feature velocity will not agree on deployment frequency. **This is the deepest one**, and DevOps as a movement was largely a response to it.
- **Fear from a past incident**, unaddressed (C12.6), expressing itself as process.
- **The improvement is made and then decays** — gates accumulate (C5.7), the pipeline slows (C2.10), flags pile up (C8.3). **Nobody owns the ongoing health**, so it regresses to where it started.
- **Success isn't measured**, so the investment can't be justified and isn't repeated (C11.7).

**The framing that makes this a lead-level answer**: **delivery improvement is an organisational change programme with a technical component, not the reverse.** The technical work is usually well understood; **the failure is in sponsorship, incentives, measurement, and ownership** — and a platform lead who only brings the technical plan will watch it decay.

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 109 items this is a large domain, and unusually little of it is factual recall — most items are positions to hold rather than facts to know.
- **C7, C9, and C12 carry the most weight for a senior or lead role.** Strategy selection defended for a stated system (C7.7), rollback under pressure (C9.1), and why delivery improvements fail organisationally (C12.7) are where the interview goes once the basics are covered.
- **C11.2 is worth being able to argue cold.** "Frequency and stability aren't in tension, because the practices that enable frequency are the same ones that produce stability" is the single most useful claim in the domain, and it reframes a great many objections — including freeze periods (C6.5) and approval gates (C10.2).
- **The items where a considered "no" is the strong answer**: when continuous deployment is inappropriate (C12.1), when recreate is the right strategy (C7.1), when a quality gate is theatre (C4.5), and when staging is misleading enough to be worth challenging (C5.8).
- **The mechanisms that read as experience**: the database constraint that undermines blue/green's rollback benefit (C7.9); expand-contract meaning the irreversible step arrives after the rollback window closes (C9.4); comparing canary against a concurrent baseline rather than an absolute threshold (C8.5); and the ephemeral environment reaper nobody builds (C5.6).
- **Cross-references are dense into Terraform, Kubernetes, and Security** — TF9 for the IaC pipeline specifics, K2.6 and K2.11 for the deployment mechanics, DB7 for migration sequencing, and S7.9–S7.11 for pipeline security. This domain is the practice; those are the implementations.
