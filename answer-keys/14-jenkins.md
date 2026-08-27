# Jenkins — Answer Key

Companion to Domain 14 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **delivery concepts are Domain 12 (the CI/CD key)**, and this domain **assumes you may inherit a legacy Jenkins estate as much as build a new one — which is the realistic case.**

Three notes on how this domain is interviewed:

- **The framing matters more here than in any other domain.** Jenkins in 2026 is mostly a legacy-estate skill. **The strong answer is rarely "here's how I'd build a Jenkins platform" and usually "here's how I'd assess, stabilise, and reduce the risk of an inherited one"** — which is J9.3, and it's the item most worth rehearsing.
- **J2.12, J2.13, J6.6, and J7.11 are the Jenkins-specific traps** — the Groovy sandbox, CPS serialisation, script approval as privilege escalation, and the script console. They're the things that don't transfer from other CI systems, and they're where someone who has actually operated Jenkins is distinguishable from someone who has used it.
- **J9.1 rewards honesty.** "Where does Jenkins still win" asked of someone who has moved to Actions is a test of whether you can argue a position you don't hold — and there are real answers.

---

## J1. Architecture & core concepts

**J1.1 — Controller/agent architecture**

- **The controller** (formerly "master") — the Jenkins server. It holds **all configuration and state** (J1.3), serves the web UI and the API, schedules builds, manages the queue (J1.7), and orchestrates pipeline execution.
- **Agents** (formerly "slaves") — machines that execute build steps. They connect to the controller and run work assigned to them.

**What runs where, and this is the part people get wrong:**

- **The controller runs the *pipeline logic itself*.** A declarative Jenkinsfile's flow control — evaluating `when` conditions, deciding stage order, managing `parallel` — **executes on the controller as CPS-transformed Groovy** (J2.13), even when the `steps` inside run on an agent.
- **`sh`, `bat`, and file operations inside a stage run on the agent**, in a workspace on that agent's disk.
- **Every step boundary is a round trip** to the controller, which is why a pipeline with thousands of small steps is slow and loads the controller disproportionately.

**The consequences:**

- **The controller is a single point of failure and a scaling bottleneck** (J7.9) — it's doing real work for every concurrent build, not just scheduling.
- **A pipeline with heavy Groovy logic loads the controller**, not the agent — so moving work into `sh` scripts on the agent is a genuine performance improvement (J2.11).
- **The controller's memory scales with concurrent builds and pipeline complexity** (J7.5, J8.3).

**J1.2 — Why builds should never run on the controller**

**The controller ships with executors by default** (historically 2), so builds *can* run there. **They should not, and the reasons are cumulative:**

- **Security — the decisive one.** A build running on the controller has **filesystem access to `JENKINS_HOME`** (J1.3): every credential in `credentials.xml`, every job configuration, the secret keys used to encrypt them, and the ability to modify Jenkins itself. **A malicious or compromised build is a full Jenkins compromise**, and from there, everything Jenkins can deploy to.
- **Stability** — a build consuming memory or CPU degrades the controller for everyone; a build that fills the disk stops Jenkins entirely (J8.4).
- **Blast radius** — a build that crashes the JVM takes down the whole instance.
- **Resource contention** — the controller needs its memory for pipeline execution and the object model (J7.5).

**The remediation**: **set the controller's executor count to 0**, and configure agents for all work. **This is one of the first things to check on an inherited estate** (J9.3) and is frequently still at the default.

**The nuance**: some lightweight steps genuinely run on the controller regardless — pipeline flow control (J1.1), `input` (J2.8) — and that's unavoidable and different from running a build there.

**The enforcement**: the **Job Restrictions** or **authorisation** plugins can prevent jobs being assigned to the built-in node, and modern Jenkins labels it `built-in` with a warning.

**J1.3 — `JENKINS_HOME` and what constitutes state**

**`JENKINS_HOME` is Jenkins.** Everything except the installed binary lives there:

```
$JENKINS_HOME/
├── config.xml                  # global configuration
├── credentials.xml             # ← encrypted credentials
├── secrets/                    # ← the keys that decrypt them
│   ├── master.key
│   └── hudson.util.Secret
├── jobs/<name>/
│   ├── config.xml              # job definition
│   └── builds/<n>/             # build history, logs, artifacts
├── plugins/                    # installed plugins (.jpi/.hpi)
├── users/                      # user records
├── nodes/                      # agent configurations
└── workspace/                  # (if builds run on the controller — J1.2)
```

**The points that matter operationally:**

- **`secrets/` and `credentials.xml` together are the credential store.** **Either alone is useless; both together decrypt everything.** So a backup containing both is a full credential dump (J7.1) and must be protected accordingly.
- **`builds/` is the bulk of the size** — build logs and archived artifacts accumulate indefinitely without retention (J7.4), and this is the usual cause of a full disk.
- **It's a filesystem, not a database.** No transactions, and **corruption from an unclean shutdown or a full disk is possible** — job `config.xml` files can be truncated.
- **Backup is a filesystem backup** (J7.1), and the size makes it awkward.
- **The whole of Jenkins' configuration is XML written by the UI**, which is precisely why click-configured Jenkins is unmaintainable (J7.8) and why JCasC exists (J7.6).

**J1.4 — Job types**

- **Freestyle** — the original UI-configured job. A form with build steps, triggers, and post-build actions. **Configuration lives in Jenkins, not in the repository** (J1.5).
- **Pipeline** — a job whose definition is a **Jenkinsfile**, either written in the UI or, correctly, **read from SCM**. The unit of pipeline-as-code.
- **Multibranch Pipeline** — **automatically creates a pipeline job per branch and per PR** that contains a Jenkinsfile, and removes them when the branch is deleted (J4.1). **The standard for a repository.**
- **Organisation Folder** (GitHub Organization / Bitbucket Team) — **scans an entire organisation and creates a multibranch project per repository** containing a Jenkinsfile. **Self-service onboarding** — a team adds a Jenkinsfile and their pipeline appears.
- **Folder** — an organisational container, and importantly **a scope for credentials** (J6.2), **shared libraries** (J3.4), and **permissions** (J6.5).

**The progression to describe**: freestyle → pipeline → multibranch → organisation folder is a progression from **configuration in Jenkins** to **configuration in the repository**, and from **manual job creation** to **automatic discovery**. **A mature Jenkins estate is mostly organisation folders and multibranch projects**, with folders providing the permission and credential boundaries.

**J1.5 — Why freestyle jobs are legacy**

- **The configuration isn't in version control.** It lives in `config.xml` in `JENKINS_HOME` (J1.3), so **there's no history, no review, no diff, and no way to know who changed what or to roll back** — the same argument as UI-configured anything (C2.5, O7.6, TF1.5).
- **It can't vary per branch.** A pipeline change and a code change can't be one atomic commit, and you can't test a build change in a PR before merging.
- **No reusability** — a change to a shared practice means editing every job by hand.
- **Limited expressiveness** — no meaningful conditionals, no parallelism worth the name, no error handling beyond post-build actions.
- **Chained jobs instead of stages** — freestyle "pipelines" are jobs triggering jobs, so **there's no single view of a run**, no shared workspace, and failure handling across the chain is manual.
- **Plugin-dependent** — every capability is a plugin with its own UI, which compounds the plugin sprawl problem (J1.8, J9.6).

**Why they persist anyway** — worth acknowledging, because you'll meet them: **they're easy for people who don't write code**, they work, and **migrating hundreds of them is a real project** (J9.4). **An inherited estate is frequently mostly freestyle**, and the migration is a prioritisation exercise rather than a mandate.

**J1.6 — The executor model**

**An executor is a slot that can run one build at a time.** Each agent is configured with a number of executors, and the total across all online agents is the cluster's concurrency.

**How concurrency is limited:**

- **Executors per agent** — the primary control. **Roughly one per CPU core** is the conventional starting point, adjusted for whether builds are CPU-bound or I/O-bound.
- **Labels** restrict which jobs can use which agents (J5.2), so a job needing a specific capability competes only for those executors.
- **`disableConcurrentBuilds()`** (J2.9) limits one job to one run at a time.
- **The Throttle Concurrent Builds plugin** for cross-job limits on a shared resource.
- **`lock()`** from the Lockable Resources plugin for a named resource.

**The points that matter:**

- **Over-provisioning executors causes contention** — twenty executors on a four-core agent means every build is slow and memory-starved, and it looks like a Jenkins problem rather than an over-subscription one.
- **A build holding an executor while waiting is waste** — which is exactly the `input` problem (J2.8).
- **The controller's executors should be 0** (J1.2).
- **Executor utilisation is a key metric** (J7.10) — persistently at 100% means queue time, persistently low means over-provisioning.

**J1.7 — The build queue and why jobs sit in it**

**A queued build is waiting for an executor that satisfies its requirements.** Hovering over it in the UI gives the reason, and reading that is the whole diagnostic (J8.1).

**The reasons, in order of frequency:**

- **All matching executors are busy** — the ordinary case.
- **No agent has the required label** (J5.2) — **and the build waits indefinitely rather than failing.** The message is "there are no nodes with the label 'X'", and it's the most common cause of a permanently-stuck build.
- **The matching agent is offline** (J5.8) — disconnected, or marked offline manually.
- **`disableConcurrentBuilds()`** and a previous run still going.
- **A lockable resource** held by another build.
- **Quiet period** — a configured delay before starting, often set on SCM triggers to batch rapid pushes.
- **Throttling** from a concurrent-builds plugin.
- **The controller is unresponsive** (J8.3) and not scheduling at all.

**The operational points**: **queue depth over time is a leading indicator** of insufficient capacity (J7.10); **a permanently-queued job blocks nothing else** but consumes queue space and confuses everyone; and **cloud agents** (J5.3, J5.5) turn "waiting for an executor" into "provisioning an agent", which changes the queue's meaning — a queued build may be waiting for a Kubernetes pod to schedule.

**J1.8 — The plugin architecture and its dependency risk**

**Almost all Jenkins functionality is plugins** — Git integration, pipeline itself, credentials, agents, every build step, every UI element. The core is a plugin host. **There are thousands available, and a typical estate has 80–150 installed.**

**The risks this creates, and this is the substance:**

- **Interdependency.** Plugins depend on each other and on a minimum core version. **Upgrading one can require upgrading several, and a version conflict manifests as a broken UI or a `NoSuchMethodError` at build time** (J7.3).
- **Abandonment.** Many plugins are maintained by one volunteer, or nobody. **A plugin that stops being maintained blocks core upgrades** and eventually breaks — and **you may not discover the maintainer left until a CVE needs fixing.**
- **CVE exposure.** **Plugins are the dominant source of Jenkins vulnerabilities**, not the core (J6.8). Jenkins publishes security advisories frequently, and most concern plugins.
- **Arbitrary code with full access.** A plugin runs in the controller's JVM with access to `JENKINS_HOME` (J1.3) — **so installing a plugin is granting complete trust** (S7.1's supply chain argument, applied here).
- **No isolation and no rollback** — downgrading a plugin can leave data in a format the older version can't read.
- **Sprawl.** Plugins accumulate, and nobody removes them because nobody knows what depends on them (J9.6).

**The management**: keep the installed set minimal and inventoried; **upgrade regularly and in small batches** (J7.2); and **test upgrades on a copy** before production.

---

## J2. Pipeline as code

**J2.1 — A declarative Jenkinsfile from scratch**

```groovy
pipeline {
    agent none

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        REGISTRY = 'ghcr.io/acme'
        IMAGE    = "${REGISTRY}/api:${env.GIT_COMMIT.take(7)}"
    }

    stages {
        stage('Build & test') {
            agent { docker { image 'node:20-slim'; label 'linux' } }
            steps {
                sh 'npm ci'
                sh 'npm test -- --ci --reporters=jest-junit'
            }
            post {
                always { junit 'reports/junit.xml' }
            }
        }

        stage('Publish') {
            when { branch 'main' }
            agent { label 'docker' }
            steps {
                withCredentials([usernamePassword(credentialsId: 'ghcr',
                                 usernameVariable: 'U', passwordVariable: 'P')]) {
                    sh '''
                        echo "$P" | docker login ghcr.io -u "$U" --password-stdin
                        docker build -t "$IMAGE" .
                        docker push "$IMAGE"
                    '''
                }
            }
        }

        stage('Deploy to production') {
            when { branch 'main' }
            steps {
                timeout(time: 1, unit: 'HOURS') {
                    input message: "Deploy ${IMAGE} to production?", submitter: 'release-team'
                }
                build job: 'deploy-production', parameters: [string(name: 'IMAGE', value: env.IMAGE)]
            }
        }
    }

    post {
        failure { slackSend channel: '#alerts', message: "Build ${env.BUILD_URL} failed" }
        always  { cleanWs() }
    }
}
```

**The decisions this demonstrates**: `agent none` at the top with per-stage agents (J2.3) so no executor is held during `input`; `options` for the essential hygiene (J2.9); credential binding rather than plain environment variables (J2.10); `when` for branch conditionals (J2.5); `post` blocks for cleanup and reporting (J2.4); `input` wrapped in a `timeout` and outside a node block (J2.8); and no `script` blocks (J2.11).

**J2.2 — Declarative vs scripted, and when scripted is necessary**

- **Declarative** — a structured, validated DSL: `pipeline { agent {} stages {} post {} }`. **Syntax is checked before the build starts**, the structure is enforced, and the Blue Ocean/UI visualisation works properly.
- **Scripted** — Groovy with `node {}` and `stage {}` calls. **Arbitrary imperative code**, full language access, no structural constraints.

**Declarative is the default and should be**, because: **it fails fast on syntax errors** rather than at the point of execution; the structure is comprehensible to someone who doesn't know Groovy; `post`, `when`, `options`, and `environment` are first-class; and **restricting Groovy reduces the sandbox and CPS problems** (J2.12, J2.13).

**When scripted is genuinely necessary:**

- **Dynamic stage generation** — creating stages from a list computed at runtime. **Declarative's stage list is static**, so a matrix of stages derived from a discovered set of services requires scripted (or the `matrix` directive, which covers some cases).
- **Complex control flow** — loops that generate pipeline structure, recursive logic.
- **Building a `parallel` map dynamically** — the most common legitimate reason.
- **Logic that genuinely can't be expressed in `when` and `script` blocks.**

**The middle path, and the one to recommend**: **declarative with `script` blocks for the specific imperative bits** (J2.11), or **push the logic into a shared library** (J3.2) where it's tested and reusable, keeping the Jenkinsfile declarative and readable. **Reaching for a fully scripted pipeline is usually a sign the logic belongs in a library or in a shell script.**

**J2.3 — `agent` directives**

```groovy
pipeline {
    agent none                                   // no global agent

    stages {
        stage('Test') {
            agent { label 'linux && docker' }    // label expression
            steps { sh 'make test' }
        }
        stage('Build') {
            agent {
                docker {
                    image 'golang:1.23'
                    label 'docker'
                    args '-v /var/run/docker.sock:/var/run/docker.sock'   // ← see D9.2
                    reuseNode true               // reuse the outer workspace
                }
            }
            steps { sh 'go build ./...' }
        }
        stage('K8s') {
            agent {
                kubernetes { yamlFile 'pod-template.yaml' }              // J5.3
            }
            steps { container('go') { sh 'go test ./...' } }
        }
    }
}
```

**The forms**: `any`, `none`, `label 'x'`, `docker { }`, `dockerfile { }`, `kubernetes { }`.

**Why `agent none` with per-stage agents is the pattern to prefer:**

- **No executor is held between stages** — so a pipeline that waits for `input` (J2.8) or has a long gap doesn't occupy an agent.
- **Different stages can use different agents** — a build on a Docker-capable agent, a deploy on one with cloud access.
- **Cleaner resource usage** on a busy controller.

**The `docker` agent details**: it runs the stage's steps **inside** that container on the agent, which is how you get a controlled toolchain without maintaining agent images (D2.13's argument). **`reuseNode true`** keeps the same workspace rather than allocating a new one. **And mounting the Docker socket** for image builds is the common pattern and a serious security decision (D9.2) — **rootless alternatives are better.**

**J2.4 — Stages, steps, and post conditions**

```groovy
stages {
    stage('Test') {
        steps {
            sh 'make test'
        }
        post {
            always  { junit 'reports/*.xml' }
            success { echo 'Tests passed' }
            failure { archiveArtifacts artifacts: 'logs/**', allowEmptyArchive: true }
        }
    }
}
post {
    always     { cleanWs() }
    success    { /* ... */ }
    failure    { /* ... */ }
    unstable   { /* ... */ }          // e.g. test failures reported by junit
    changed    { /* ... */ }          // status differs from the previous build
    fixed      { /* ... */ }          // was failing, now passing
    regression { /* ... */ }          // was passing, now failing
    aborted    { /* ... */ }
    unsuccessful { /* ... */ }        // failure, unstable, or aborted
}
```

**The distinctions that matter:**

- **`post` at stage level runs after that stage; at pipeline level after everything.**
- **`always` runs regardless**, including on abort — so it's right for cleanup and for publishing results that exist whether or not the build passed.
- **`unstable` is a Jenkins-specific status** between success and failure — **typically set by `junit` when tests fail** but the build itself completed. **Understanding that a build can be yellow rather than red** is a Jenkins idiosyncrasy worth knowing.
- **`changed`, `fixed`, and `regression`** are genuinely useful for notifications — **notifying only on a change of state** avoids the daily "still broken" spam.
- **`cleanWs()`** in `post { always }` is important on long-lived agents (J5.7).

**J2.5 — `when` conditions**

```groovy
stage('Deploy') {
    when {
        allOf {
            branch 'main'
            not { changeRequest() }
            environment name: 'DEPLOY_ENABLED', value: 'true'
            expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }
        }
        beforeAgent true        // ← evaluate BEFORE allocating an agent
    }
    steps { sh './deploy.sh' }
}
```

**The built-in conditions**: `branch`, `buildingTag`, `tag`, `changeRequest()` (is this a PR), `changelog` / `changeset` (regex on commit messages / changed files), `environment`, `equals`, `expression` (arbitrary Groovy), `triggeredBy`, and the combinators `allOf`, `anyOf`, `not`.

**The options that matter, and `beforeAgent` is the important one:**

- **`beforeAgent true`** — evaluate the condition **before allocating an agent.** **Without it, Jenkins provisions an agent (potentially spinning up a Kubernetes pod or an EC2 instance, J5.3/J5.5), then evaluates the condition, then skips the stage.** **That's wasted provisioning time and cost on every skipped stage**, and it's a common and easily-fixed inefficiency.
- **`beforeInput`** and **`beforeOptions`** similarly control ordering relative to those directives.

**The practical points**: **`branch` matches the branch name, which for a multibranch PR job is `PR-42`, not the source branch** — so `when { branch 'main' }` never fires on a PR, which is usually what you want but surprises people. **`changeRequest()`** is the correct way to test for a PR build.

**J2.6 — `parallel` stages and failure behaviour**

```groovy
stage('Verify') {
    failFast true                       // abort siblings on first failure
    parallel {
        stage('Unit') {
            agent { label 'linux' }
            steps { sh 'make unit' }
        }
        stage('Integration') {
            agent { label 'linux' }
            steps { sh 'make integration' }
        }
        stage('Lint') {
            steps { sh 'make lint' }
        }
    }
}
```

**The failure behaviour, which is the item's focus:**

- **By default, a failing parallel branch does not immediately stop the others** — they run to completion, and the stage fails at the end.
- **`failFast true`** aborts all sibling branches as soon as one fails. **Saves time and executor capacity, and loses information** — you learn that one thing failed rather than which of the three.
- **The choice mirrors GA3.7**: `failFast` when the branches are equivalent and any failure means the same thing; **without it when you want the full picture**, because a developer fixing one failure and discovering the next on a re-run is a worse experience than seeing all three at once.

**The other points:**

- **Each parallel branch needs its own agent** if the steps run on one — **so a parallel stage with five branches consumes five executors simultaneously** (J1.6). On a constrained estate that's a real capacity consideration.
- **A `post` block on the parent stage** runs after all branches complete.
- **Scripted parallelism** takes a map of closures and is how you build a **dynamic** parallel set (J2.2) — the most common reason to drop into `script`.

**J2.7 — Parameters and the first-run problem**

```groovy
parameters {
    string(name: 'VERSION', defaultValue: '', description: 'Version to deploy')
    choice(name: 'ENVIRONMENT', choices: ['staging', 'production'], description: '')
    booleanParam(name: 'DRY_RUN', defaultValue: true, description: '')
    password(name: 'TOKEN', defaultValue: '', description: '')
}
```

Accessed as `params.VERSION`.

**The first-run problem, which is the item:**

**Parameters declared in a Jenkinsfile are not registered with the job until the job has run once and Jenkins has parsed the file.** So:

- **The first build after adding or changing a parameter runs with the *old* parameter set** (or none), **using default values or failing on a missing parameter.**
- **The UI doesn't show the new parameters** until after that first run.
- **On a brand-new multibranch job, the first build of a branch has no parameters at all.**

**The consequences**: a pipeline that requires a parameter fails on its first run after the change; and **a `parameters` block itself resets the job's parameter definitions each run**, so a manually-added parameter disappears.

**The workarounds**: **provide sensible defaults so the first run is harmless**; **guard on the parameter being empty** and fail with a clear message rather than doing something wrong; **run once to register, then use**; and **for a multibranch job, accept that the first branch build is a registration run.** It's a genuine Jenkins wart and knowing it saves confusion.

**J2.8 — `input` and the executor-blocking issue**

```groovy
// WRONG — holds an executor for the whole approval window
stage('Deploy') {
    agent { label 'linux' }
    steps {
        input message: 'Deploy to production?'
        sh './deploy.sh'
    }
}

// RIGHT — approval outside any node, with a timeout
stage('Approval') {
    agent none
    steps {
        timeout(time: 1, unit: 'HOURS') {
            input message: 'Deploy to production?',
                  submitter: 'release-team',
                  submitterParameter: 'APPROVER'
        }
    }
}
stage('Deploy') {
    agent { label 'linux' }
    steps { sh './deploy.sh' }
}
```

**The issue**: **`input` inside a stage that has an agent holds that executor for the entire time it waits** — potentially hours or days. **On a constrained estate, a handful of pipelines awaiting approval can consume every executor and deadlock the whole instance**, with every other build queued (J1.7, J8.1). **This is a classic and genuinely damaging Jenkins mistake.**

**The correct pattern**: **`input` in a stage with `agent none`**, or outside any `node` block in scripted. The pipeline's flow control runs on the controller (J1.1), which costs a lightweight thread rather than an executor.

**The other essentials:**

- **Always wrap in a `timeout`** — an unanswered `input` waits forever, holding pipeline state on the controller and leaving the build in the running list indefinitely.
- **`submitter`** restricts who can approve — **this is the separation-of-duties control** (C10.1), and without it anyone with build permission can approve.
- **`submitterParameter`** captures who approved, which is the audit record (C6.7).
- **An unanswered input on abort** — `post { aborted { } }` handles cleanup.

**J2.9 — `options`**

```groovy
options {
    timeout(time: 45, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '30', daysToKeepStr: '30',
                              artifactNumToKeepStr: '5'))
    disableConcurrentBuilds(abortPrevious: true)
    retry(2)
    timestamps()
    ansiColor('xterm')
    skipDefaultCheckout(true)
    parallelsAlwaysFailFast()
}
```

**The ones that matter, and why:**

- **`timeout`** — **essential.** A hung build without one holds an executor indefinitely (J8.2) and, on a cloud agent, costs money. **Set it modestly above the p95 duration.**
- **`buildDiscarder`** — **the single most important one operationally.** **Without it, build history and artifacts accumulate forever**, and `JENKINS_HOME` fills (J1.3, J7.4, J8.4). **This is the most common cause of a Jenkins disk emergency.** Set `numToKeepStr` and, separately, a much lower `artifactNumToKeepStr` — logs are small, artifacts aren't.
- **`disableConcurrentBuilds()`** — prevents two runs of the same job racing, which matters for deployments (C9.7). **`abortPrevious: true`** cancels the older run instead of queueing, which is the right behaviour for PR builds (GA3.9's equivalent).
- **`retry(n)`** — at pipeline level retries the whole thing, which is usually too coarse. **`retry` as a *step* around a specific flaky operation is better.**
- **`timestamps()`** — adds timestamps to console output. **Trivial to add and disproportionately useful when diagnosing a slow build.**
- **`skipDefaultCheckout(true)`** with explicit `checkout scm` where you want control.

**J2.10 — Environment directives and credential bindings**

```groovy
environment {
    REGISTRY   = 'ghcr.io/acme'
    // credentials() helper — binds by type
    AWS_ROLE   = credentials('aws-deploy-role-arn')       // secret text
    DOCKER_CRED = credentials('ghcr-creds')                // username/password
    // → sets DOCKER_CRED_USR and DOCKER_CRED_PSW
}

stages {
    stage('Deploy') {
        steps {
            withCredentials([
                string(credentialsId: 'api-token', variable: 'API_TOKEN'),
                usernamePassword(credentialsId: 'db', usernameVariable: 'DB_USER',
                                 passwordVariable: 'DB_PASS'),
                file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG'),
                sshUserPrivateKey(credentialsId: 'deploy-key', keyFileVariable: 'SSH_KEY')
            ]) {
                sh './deploy.sh'
            }
        }
    }
}
```

**The two mechanisms:**

- **`environment { X = credentials('id') }`** — binds for the whole pipeline or stage. **Convenient, and the credential is in the environment for every step in scope**, which is a broader exposure than necessary.
- **`withCredentials([...]) { }`** — **binds only within the block.** **Narrower scope, and it supports every credential type explicitly.** **Prefer this** for anything sensitive.

**The details that matter:**

- **The `_USR`/`_PSW` suffix convention** for username/password credentials in `environment` is Jenkins-specific and worth knowing.
- **Bound credentials are masked in the console** — and **masking is defeated by transformation** (J6.3), so this is not sufficient protection.
- **`file` and `sshUserPrivateKey` bindings write a temporary file** and set a variable to its path; **the file is deleted when the block exits** — so a step that copies it elsewhere defeats that.
- **Prefer an external secrets manager** (J6.9) or **OIDC/IAM roles** over storing credentials in Jenkins at all.

**J2.11 — `script` blocks and minimising them**

```groovy
steps {
    script {
        def services = sh(script: 'ls services/', returnStdout: true).trim().split('\n')
        def branches = [:]
        services.each { svc -> branches[svc] = { sh "make build-${svc}" } }
        parallel branches
    }
}
```

**A `script` block drops into scripted (imperative Groovy) inside a declarative pipeline** — the escape hatch for logic declarative can't express (J2.2).

**Why minimising them matters:**

- **You lose declarative's validation.** Errors surface at execution rather than at parse time.
- **CPS serialisation applies** (J2.13) — **arbitrary Groovy in a `script` block hits the CPS restrictions**, and the failures are obscure.
- **Sandbox and script approval** (J2.12) — more Groovy means more approval requests, which is a privilege escalation surface (J6.6).
- **It runs on the controller** (J1.1), so heavy logic loads the controller rather than the agent.
- **It's harder to read** — a Jenkinsfile that's mostly `script` blocks has the readability of scripted with the ceremony of declarative.
- **It's untested.** Logic in a Jenkinsfile has no unit tests; logic in a shared library can (J3.7).

**The alternatives, in preference order:**

1. **A shell script in the repository**, invoked with `sh './script.sh'`. **Testable, runnable locally, no CPS, no sandbox, and it runs on the agent.** **Frequently the right answer** and under-used.
2. **A shared library step** (J3.2) — tested, versioned, reusable.
3. **Declarative features** — `when`, `matrix`, `environment` cover more than people assume.
4. **A `script` block**, small and specific.

**J2.12 — The Groovy sandbox and script approval**

**Pipeline Groovy runs in a sandbox** that permits only an allowlist of methods. **Anything outside it throws `RejectedAccessException`** and creates a pending entry in **Manage Jenkins → In-process Script Approval**, where an administrator approves the specific method signature.

**Why the sandbox exists**: **pipeline code runs on the controller** (J1.1) with **full JVM access** — the filesystem including `JENKINS_HOME` (J1.3), the Jenkins object model, and the ability to execute arbitrary code. **Without a sandbox, anyone who can commit a Jenkinsfile could compromise Jenkins entirely.**

**The operational reality:**

- **The approval list accumulates**, and administrators approve requests to unblock builds without assessing them.
- **Some approvals are effectively "grant full access"** — approving `java.lang.Runtime.exec` or reflection methods (J6.6).
- **A "run without sandbox" option exists** for jobs configured by administrators — **which disables it entirely**, and is frequently used to avoid the friction.
- **Shared libraries can be marked trusted** (J3.4) and then run **outside** the sandbox — **which is the correct pattern**: put the privileged logic in a reviewed, version-controlled library rather than approving individual method signatures.

**The recommendation**: **minimise Groovy** (J2.11), **put necessary privileged logic in a trusted global shared library** where it's reviewed like code, and **treat script approval requests as security decisions** (J6.6) rather than a build-unblocking chore.

**J2.13 — CPS serialisation and why some Groovy fails**

**The mechanism**: Jenkins pipelines must **survive a controller restart mid-build.** To do that, the pipeline's execution state is **serialised to disk at every step boundary**. This is implemented by **CPS (Continuation Passing Style) transformation** — the Groovy is rewritten into a form whose state can be captured.

**The consequences, which are the item:**

- **Every local variable must be `Serializable`.** A non-serializable object (a file handle, a `Matcher` from a regex, a database connection, many library objects) held across a step boundary throws **`java.io.NotSerializableException`** — **and the error names the class, which is the clue.**
  ```groovy
  // FAILS — Matcher is not serializable
  def m = (text =~ /v(\d+)/)
  sh "echo ${m[0][1]}"

  // WORKS — extract the value, discard the Matcher, in a @NonCPS method
  ```
- **`@NonCPS`-annotated methods run as plain Groovy** — not transformed, not serialised. **Use them for pure computation** (regex, collection manipulation). **But you cannot call pipeline steps (`sh`, `echo`) from a `@NonCPS` method** — that's the constraint that catches people.
- **Some Groovy constructs don't work**: closures passed to certain collection methods (`.each` on some types), `Iterator`-based loops in some forms. **The classic workaround is a plain `for (int i = 0; ...)` loop.**
- **The performance cost is real** — CPS-transformed Groovy is much slower than plain Groovy, and **a loop with many iterations in a pipeline is dramatically slower than the same loop in a shell script.**

**The practical guidance**: **this is the strongest argument for J2.11** — **push logic into shell scripts or shared library `@NonCPS` methods**, and keep the pipeline itself to orchestration. **Debugging a `NotSerializableException` is a genuinely Jenkins-specific skill** and recognising it immediately is a good signal.

**J2.14 — Archiving artifacts and publishing test results**

```groovy
post {
    always {
        junit testResults: 'reports/**/*.xml', allowEmptyResults: false,
              skipPublishingChecks: false
        archiveArtifacts artifacts: 'dist/**,build/reports/**',
                         fingerprint: true,
                         onlyIfSuccessful: false,
                         allowEmptyArchive: false
        publishHTML(target: [reportDir: 'coverage', reportFiles: 'index.html',
                             reportName: 'Coverage'])
        recordIssues(tools: [checkStyle(pattern: 'reports/checkstyle.xml')])
    }
}
```

**The points that matter:**

- **`junit` parses JUnit-format XML**, publishes the results, shows trends, and **sets the build to `UNSTABLE` on test failures** rather than `FAILURE` (J2.4) — which is the Jenkins convention and surprises people expecting a red build.
- **`allowEmptyResults: false`** so a missing report fails rather than silently reporting nothing — the same argument as GA9.5's `if-no-files-found`.
- **`archiveArtifacts` stores in `JENKINS_HOME/jobs/.../builds/<n>/`** (J1.3) — **so it consumes controller disk, and without a `buildDiscarder` artifact limit it accumulates indefinitely** (J2.9, J7.4). **This is the main cause of Jenkins disk exhaustion.**
- **`fingerprint: true`** records a hash and tracks the artefact across jobs — useful for traceability (C3.8), and it adds records to `JENKINS_HOME`.
- **Archive selectively.** Archiving a whole build tree on every run is the difference between a manageable and an unmanageable disk footprint.
- **For deployable artefacts, a registry or artifact repository is the right home** (C3.5), not Jenkins — Jenkins archives are for reports and diagnostics.

---

## J3. Shared libraries

**J3.1 — Structure: `vars`, `src`, `resources`**

```
jenkins-shared-library/
├── vars/                          # global variables = custom steps
│   ├── buildAndPush.groovy        # → callable as buildAndPush(...)
│   ├── buildAndPush.txt           # documentation, shown in the UI
│   └── standardPipeline.groovy
├── src/                           # Groovy classes, package structure
│   └── com/acme/jenkins/
│       ├── Docker.groovy
│       └── Notifier.groovy
├── resources/                     # non-Groovy files
│   └── com/acme/templates/pod.yaml
└── test/                          # library tests (J3.7)
```

- **`vars/`** — **each `.groovy` file becomes a globally-available step** named after the file. A file defining `def call(...)` is invoked as `filename(...)`. **This is the main extension point** (J3.2).
- **`src/`** — **standard Groovy classes** in a package hierarchy, imported and instantiated. For anything with real structure — state, multiple methods, inheritance (J3.3).
- **`resources/`** — non-Groovy files, loaded with **`libraryResource 'path'`** which returns the content as a string. **Pod templates, config templates, scripts** — so a shell script can live in the library and be written to the workspace rather than embedded as a heredoc.

**The distinction to state**: **`vars` is the public API of the library — the steps consumers call. `src` is the implementation.** Keeping `vars` thin and delegating to `src` classes gives you testability (J3.7) and a clean interface (TF4.1's module argument).

**J3.2 — Writing a custom step in `vars`**

```groovy
// vars/buildAndPush.groovy
def call(Map config = [:]) {
    def image    = config.image    ?: error('image is required')
    def context  = config.context  ?: '.'
    def registry = config.registry ?: 'ghcr.io/acme'
    def tag      = config.tag      ?: env.GIT_COMMIT.take(7)

    def fullImage = "${registry}/${image}:${tag}"

    withCredentials([usernamePassword(credentialsId: 'ghcr',
                     usernameVariable: 'U', passwordVariable: 'P')]) {
        sh """
            set -euo pipefail
            echo "\$P" | docker login ${registry} -u "\$U" --password-stdin
            docker build -t ${fullImage} ${context}
            docker push ${fullImage}
        """
    }
    return fullImage
}
```

```groovy
// in a Jenkinsfile
def image = buildAndPush(image: 'payments-api', context: './services/api')
```

**The conventions:**

- **`def call(...)` is what makes it invocable as a step.** Other methods in the file are callable as `buildAndPush.otherMethod()`.
- **A Map parameter with named keys** is idiomatic and much more readable than positional arguments — and it's extensible without breaking callers.
- **Validate inputs and `error()` with a clear message** — the library is a product with consumers (J3.8, TF4.1).
- **Return a value** where useful.
- **A matching `.txt` file** provides documentation shown in Jenkins' UI.

**The advanced form**: a `vars` file can also define a **closure-based DSL** (`call(Closure body)` with `body.delegate = this`), which is how `standardPipeline { ... }` style steps work — powerful, and it's where libraries start becoming frameworks nobody understands (J3.8).

**J3.3 — Writing and using a class in `src`**

```groovy
// src/com/acme/jenkins/Notifier.groovy
package com.acme.jenkins

class Notifier implements Serializable {
    private def steps                       // ← the pipeline context

    Notifier(steps) { this.steps = steps }

    void success(String message) {
        steps.slackSend(channel: '#builds', color: 'good', message: message)
    }

    void failure(String message) {
        steps.slackSend(channel: '#alerts', color: 'danger', message: message)
        steps.emailext(subject: 'Build failed', body: message, to: 'team@acme.com')
    }
}
```

```groovy
// vars/notify.groovy
import com.acme.jenkins.Notifier
def call(String status, String message) {
    new Notifier(this).with { status == 'success' ? success(message) : failure(message) }
}
```

**The two things that catch people, and they're the substance:**

1. **`implements Serializable` is required** for anything held across a step boundary (J2.13). **Omitting it produces `NotSerializableException`** at a confusing point.
2. **A `src` class has no access to pipeline steps** — no `sh`, no `echo`, no `env`. **You must pass the pipeline context in** (conventionally `steps` or `script`, passed as `this` from a `vars` file) and call steps through it: `steps.sh(...)`.

**When to use `src` over `vars`**: when there's genuine structure — state across method calls, several related operations, inheritance, or logic complex enough to warrant unit tests (J3.7). **`vars` for the interface, `src` for the implementation** (J3.1).

**J3.4 — Global vs folder-level libraries**

- **Global** (Manage Jenkins → System → Global Pipeline Libraries) — available to **every job on the instance.** Configured by an administrator. **Can be marked "trusted"**, which means **it runs outside the Groovy sandbox** (J2.12).
- **Folder-level** (a folder's configuration) — available only to jobs in that folder (J1.4). **Always runs sandboxed**, regardless of configuration.

**The trust distinction is the important one:**

- **A trusted global library runs with full JVM access** — the same privileges as an administrator's script (J6.6). **So the library's repository is effectively an administrative credential**: anyone who can commit to it can compromise Jenkins.
- **Which means the library repository needs the same protection as Jenkins itself** — restricted write access, required review, and ideally signed commits.
- **The upside**: it's the *correct* place for privileged logic. Rather than approving individual method signatures in script approval (J2.12), **you put the privileged code in a reviewed, version-controlled library** — which is auditable and far better than an approval list nobody assesses.

**Folder-level libraries** are appropriate for a team's own helpers where no elevated privilege is needed, and they let a team version their own library without an administrator.

**The loading forms**: `@Library('my-lib@v2') _` explicitly in the Jenkinsfile, or **implicit loading** (J3.6).

**J3.5 — Versioning a library and pinning consumers**

```groovy
@Library('acme-pipeline@v3.2.0') _          // a tag — pinned
@Library('acme-pipeline@main') _            // a branch — floats
@Library('acme-pipeline@a3f9c2b') _         // a commit — immutable
@Library(['acme-pipeline@v3', 'other-lib@v1']) _
```

**The default version** is configured on the library definition, and **`allowVersionOverride`** controls whether a Jenkinsfile may specify a different one.

**Why pinning matters** (TF4.3, GA5.2's argument):

- **A library on `main` means every consumer's pipeline changes when someone merges** — **with no review of the impact, applied instantly to every job on the instance.** For a trusted global library (J3.4) that's a change to privileged code affecting everything.
- **A broken commit breaks every pipeline simultaneously**, and diagnosing it means correlating the failure with a library commit nobody announced.
- **Pinning to a tag** means consumers adopt changes deliberately.

**The practices:**

- **Semantic version tags** on the library, with a moving major tag if you want consumers to get minors automatically.
- **Consumers pin to a major or an exact version.**
- **Test the library** before tagging (J3.7).
- **Communicate breaking changes** and know who your consumers are.
- **The tension to acknowledge**: pinning means consumers don't get fixes automatically, so a security fix requires updating every consumer. **The resolution is a moving major tag plus semantic discipline** — the same trade as TF4.3.

**J3.6 — Implicit loading and its risk**

**A global library can be marked "Load implicitly"**, which means **it's available in every Jenkinsfile with no `@Library` annotation.**

**The convenience**: consumers write `buildAndPush(...)` with no import ceremony.

**The risks, which is the item:**

- **The library's version is not visible in the Jenkinsfile.** **You cannot tell, by reading a pipeline, which version of the library it's using** — it's whatever the global configuration says. **So a pipeline is not self-describing**, and reproducing an old build requires knowing the library version at that time, which isn't recorded.
- **Consumers cannot pin.** They get the configured default, so a library change is instantly global (J3.5).
- **Implicit dependencies are invisible.** A Jenkinsfile using `notify()` looks like it's calling a built-in step; **there's no indication it comes from a library**, which makes debugging harder and onboarding worse.
- **Name collisions** — an implicitly-loaded step shadowing a plugin's step, or two libraries defining the same name, produces very confusing behaviour.
- **It combines badly with trusted libraries** (J3.4) — privileged code loaded into every pipeline with no declaration.

**The recommendation**: **explicit loading with a pinned version.** The extra line is worth the visibility. **Implicit loading is acceptable for a small, stable, non-privileged utility library** where the coupling is understood, and it should be a deliberate choice rather than the default.

**J3.7 — Testing a shared library**

**The problem**: shared library code is Groovy that runs inside Jenkins, calling pipeline steps that don't exist outside it. **So it's hard to test, and most libraries aren't tested at all** — which matters, because **a broken library breaks every consumer's pipeline simultaneously** (J3.5).

**The approaches:**

- **JenkinsPipelineUnit** — the standard framework. **Mocks the pipeline steps** (`sh`, `echo`, `withCredentials`) and lets you assert that your library called them with the expected arguments. **Runs as a normal JUnit/Spock test in a Gradle or Maven build**, so it's fast and runs in CI.
  ```groovy
  helper.registerAllowedMethod('sh', [Map.class], { m -> return '' })
  def result = loadScript('vars/buildAndPush.groovy').call(image: 'api')
  assertThat(helper.callStack).contains(...)
  ```
- **Unit tests on `src` classes** — plain Groovy classes with the pipeline context injected (J3.3) are **straightforwardly unit-testable** by passing a mock. **This is the strongest argument for putting logic in `src` rather than `vars`.**
- **Integration testing** — a test Jenkins instance (a container) running a pipeline that exercises the library. Slower, higher fidelity, and it's what catches CPS problems (J2.13) that unit tests miss.
- **A canary consumer** — one real pipeline pinned to the library's `main`, so breakage surfaces before a tag is cut.
- **`groovy -c` / static compilation** and **`@CompileStatic`** on `src` classes catches type errors at build time, which is worth doing.

**The point to make**: **an untested shared library used by fifty pipelines is a single point of failure with no safety net** — and testing it is what makes it a product rather than a liability (J3.8).

**J3.8 — Standardising without becoming a framework nobody understands**

**The failure mode**: a library that starts as helper steps grows into a full pipeline framework — `standardPipeline { }` taking forty configuration options, with the actual build logic buried across a dozen `src` classes and a closure-based DSL. **Nobody outside the platform team can read a Jenkinsfile or debug a failure**, and every variation requires a library change (TF4.5's over-abstraction argument, in its Jenkins form).

**The symptoms:**

- **A Jenkinsfile that's three lines** and gives no indication what the build does.
- **A library with more configuration options than the pipelines it replaces had lines.**
- **Debugging requires reading the library**, so the platform team is the bottleneck for every failure (C12.3).
- **"Add a parameter" as the response to every request**, ratcheting the interface wider.
- **Teams forking the library** to escape it — at which point standardisation is lost entirely.

**The design that works:**

- **Share the decisions, not the structure.** **A library step that encodes *how we build and push an image* is valuable** (J3.2) — credentials, tagging, registry, scanning. **A library that encodes *the shape of every pipeline* is a framework.**
- **Keep the Jenkinsfile readable.** A reader should see the stages and roughly what happens. **Composition over a single mega-step.**
- **Thin `vars`, tested `src`** (J3.1, J3.7).
- **Escape hatches** — a consumer needing something the library doesn't do must be able to write plain pipeline code alongside it, not be blocked.
- **Open contribution** — a team raises a PR rather than waiting in a queue (TF8.8).
- **Version and communicate** (J3.5).

**The test to state**: **can a new engineer read a Jenkinsfile and understand what the build does, and debug a failure, without reading the library?** If not, it's gone too far.

---

## J4. Multibranch & SCM

**J4.1 — Configuring a multibranch pipeline with branch discovery**

**A multibranch project scans a repository and creates a job per branch (and per PR) that contains a Jenkinsfile.**

The configuration:

- **Branch Sources** — the SCM (GitHub, Bitbucket, generic Git) plus credentials (J4.7).
- **Behaviours** — the discovery rules:
  - **Discover branches**: all branches / only those that are also PRs / all except those that are PRs.
  - **Discover pull requests from origin** (J4.2).
  - **Discover pull requests from forks** — with a trust strategy (nobody / collaborators / everyone) that determines whether the fork's Jenkinsfile is trusted.
  - **Filter by name** with a regex or wildcard — **essential on a repository with many branches**, or you create hundreds of jobs.
- **Build strategies** — restrict to branches with recent commits, skip branches without changes.
- **Script Path** — `Jenkinsfile` by default, and configurable for a monorepo.
- **Scan triggers** — periodic indexing plus webhooks (J4.4).
- **Orphaned item strategy** (J4.5).

**The properties that make it the standard choice**: **jobs appear and disappear automatically** with branches; **each branch's job uses that branch's Jenkinsfile**, so a pipeline change can be tested in a PR (C2.5); and **`env.BRANCH_NAME`, `env.CHANGE_ID`, and `env.CHANGE_TARGET`** are populated so the pipeline can behave differently per branch (J2.5).

**The caution**: **a repository with hundreds of branches creates hundreds of jobs**, each with its own build history and workspace — a real load and disk consideration (J7.4). **Filter aggressively.**

**J4.2 — PR discovery: merge vs head**

**When discovering pull requests, the strategy determines what gets built:**

- **"Merging the pull request with the current target branch revision"** — Jenkins builds a **merge commit** of the PR into its target. **Tests what the code will be after merge**, which is what you actually care about — a PR that passes in isolation and breaks on merge is caught here.
- **"The current pull request revision"** — builds the PR's **head commit** as-is. **Tests the branch as the author wrote it.**
- **Both** — creates two jobs per PR (`PR-42` and `PR-42-head`).

**The tradeoff:**

- **Merge is more correct** — it catches semantic conflicts with the target branch (C1.4's argument) and reflects what will actually be merged.
- **Merge is less stable** — **the merge commit changes whenever the target branch moves**, so a PR's build result can go stale or a re-run can produce a different result with no change from the author. **And it can fail to build at all if the merge conflicts**, which is a confusing failure mode.
- **Head is reproducible** — the same commit always produces the same build.

**The recommendation: merge**, because the question "will this break main" is the one CI should answer. **And be aware of the staleness** — a PR built against an old target may pass and break after merge, which is why merge queues exist (GA2.2's `merge_group`).

**The fork trust setting is the security decision here** (J6.7's neighbour): **if fork PRs are trusted, a fork's Jenkinsfile executes on your agents with your credentials** — the direct equivalent of `pull_request_target` (GA2.4). **Set trust to "collaborators" or "nobody"** for anything public.

**J4.3 — Branch indexing and why a branch didn't appear**

**Branch indexing is the scan that discovers branches and PRs and creates or removes jobs.** It runs periodically (configurable) and on webhook events (J4.4).

**Why a branch didn't appear — the checklist:**

1. **No Jenkinsfile at the configured Script Path.** **A branch without one is not created as a job** — silently. **The most common answer.**
2. **A filter excludes it** (J4.1) — a name regex or a wildcard that doesn't match.
3. **Indexing hasn't run.** Webhook not configured or not firing (J4.8), and the periodic scan hasn't come round.
4. **Credentials lack access** — the branch exists and Jenkins can't see it (J4.7).
5. **The branch was created before the multibranch project** and indexing hasn't been triggered since — **"Scan Repository Now" is the manual trigger.**
6. **A build strategy excludes it** — "only branches with recent commits" and the branch is old.
7. **API rate limiting** — GitHub's API limits (GA10.6) can cause indexing to fail partway, and **the scan log shows it.**
8. **The orphaned item strategy removed it** and it hasn't been rediscovered (J4.5).

**The diagnostic**: **the "Scan Repository Log"** on the multibranch project shows exactly what indexing found, what it skipped, and why — **including "does not meet the criteria" per branch.** **Reading it answers the question immediately** and it's the first place to look.

**J4.4 — Webhooks vs polling**

- **Webhook** — the SCM pushes an event to Jenkins on a commit or PR, and Jenkins triggers indexing or a build **immediately.**
- **Polling** — Jenkins asks the SCM whether anything changed, on a schedule (`pollSCM` or periodic indexing).

**Why polling is a poor substitute:**

- **Latency.** A poll every 5 minutes means up to 5 minutes' delay before a build starts (C1.5's feedback argument).
- **Load — the significant one.** **Every polled job asks the SCM on every interval, whether or not anything changed.** With hundreds of jobs polling every few minutes, **that's a very large number of API calls**, and it **exhausts GitHub API rate limits** (GA10.6), causing indexing failures and confusing intermittent behaviour (J4.3). **This is a genuine and common cause of Jenkins/GitHub problems at scale.**
- **It scales badly** — the load is proportional to job count × poll frequency, regardless of activity.
- **It's wasteful** — most polls find nothing.

**Why polling persists anyway**: **Jenkins must be reachable from the SCM.** An internal Jenkins behind a firewall cannot receive a webhook from github.com without an inbound path — **and opening one is exactly the risk in J6.7.**

**The resolutions**: a **webhook relay** (a small public endpoint forwarding to internal Jenkins), **GitHub's or Bitbucket's IP allowlist** with a narrow inbound rule, or **an outbound-polling agent architecture**. **And if you must poll, poll infrequently at the multibranch level** rather than per-job, which is dramatically fewer calls.

**J4.5 — Orphaned item retention**

**When a branch is deleted, its multibranch job becomes "orphaned".** The strategy controls what happens:

- **Discard old items** — with **days to keep** and **maximum number to keep.**
- **Or keep forever** (the risky default in some configurations).

**Why it matters:**

- **Orphaned jobs consume `JENKINS_HOME` disk** (J1.3) — their build history, logs, and archived artifacts persist (J7.4). **On a repository with heavy branch churn, this accumulates quickly** and is a common contributor to disk exhaustion (J8.4).
- **They clutter the UI** and confuse people looking for a current job.
- **They keep workspaces on agents** (J5.7) unless cleaned separately.

**The configuration to recommend**: **discard after a short period — 7 days is generous** — because **the value of an orphaned branch's build history drops to near zero once the branch is gone.** Keep a small number for the case where someone needs to look at a recently-deleted branch's last build.

**The related cleanup**: **agent workspaces are not removed** when a job is deleted — they persist on the agent's disk until cleaned (J5.7). **So orphaned item retention handles the controller and not the agents**, and both need attention.

**J4.6 — Reporting build status back to the SCM**

**For GitHub** (and equivalently Bitbucket and GitLab):

- **The GitHub Branch Source plugin reports status automatically** for multibranch jobs — a pending check on build start, success or failure on completion, linked to the run.
- **Explicit control** via `publishChecks` (GitHub Checks API) for richer output — a summary, annotations on specific lines, and a detailed view. **Substantially better than a simple status** and under-used.
- **`githubNotify`** for manual status setting in a pipeline.

```groovy
post {
    always {
        publishChecks name: 'jenkins/build',
                      title: "Build ${currentBuild.result}",
                      summary: "Duration: ${currentBuild.durationString}",
                      detailsURL: env.BUILD_URL
    }
}
```

**Why it matters**: **the status check is what gates the merge** under branch protection — so it's the mechanism by which Jenkins participates in the PR workflow at all. **Without it, Jenkins builds in isolation and nobody sees the result** unless they go looking.

**The requirements**: **credentials with the right scope** — for GitHub, a token or App with `repo:status` at minimum (J4.7); **and the checks must be named consistently**, because branch protection matches on the check name and a rename breaks every protected branch's requirement.

**The point worth making**: **a GitHub App is the better credential** for this than a PAT (GA6.8) — higher rate limits (J4.4's problem), not tied to a person, and scoped to specific repositories.

**J4.7 — Managing SCM credentials securely**

**The options, best to worst:**

1. **A GitHub App** — **the best answer.** Scoped to specific repositories and permissions, **short-lived installation tokens**, higher rate limits (J4.4, GA10.6), not tied to a person, and revocable centrally. The GitHub Branch Source plugin supports App authentication directly.
2. **A machine-user PAT** with minimal scopes, stored as a Jenkins credential, **scoped to a folder** (J6.2) rather than global. **Long-lived**, so it needs rotation (S6.5), and it's tied to an account that must not be deleted.
3. **SSH deploy keys** — per-repository, read-only where possible. **Good for clone-only access** and they don't provide status reporting (J4.6).
4. **A personal PAT** — **never.** It dies when the person leaves or rotates it, it carries their full access, and it attributes automated actions to a human.

**The practices:**

- **Folder-scoped credentials** (J6.2) so a team's jobs use their own credential and can't reach other repositories.
- **Minimal scopes** — `repo` is broad; for a public repository, `public_repo` and `repo:status` may suffice.
- **Rotate**, and know how (S6.5).
- **An external secrets manager** where possible (J6.9), so the credential isn't stored in Jenkins at all.
- **Audit what has access** — the credentials store shows usage, and folder scoping makes the blast radius visible.

---

## J5. Agents & scaling

**J5.1 — SSH vs JNLP agents**

- **SSH (controller-initiated)** — **the controller connects out to the agent** over SSH, copies the agent JAR, and starts it. Requires: the agent reachable from the controller, SSH credentials, and a Java runtime on the agent.
- **JNLP / inbound (agent-initiated)** — **the agent connects in to the controller** over the JNLP/WebSocket port, authenticating with a secret. Requires: the controller reachable from the agent, and an open agent port (or WebSocket over HTTPS).

**The difference that determines which you use is network direction:**

- **SSH when the controller can reach the agent** — a static fleet in the same network.
- **JNLP when the agent can reach the controller but not vice versa** — **agents behind NAT, in a different network, in a container or Kubernetes pod (J5.3), or on a developer's machine.** **This is why containerised and cloud agents are almost always JNLP.**

**The other considerations:**

- **JNLP historically needed a dedicated TCP port** open on the controller, which is a firewall consideration; **WebSocket mode (`-webSocket`) tunnels over the HTTP(S) port**, which removes that and is the modern default.
- **SSH agents don't need an inbound port on the controller**, which is better for an internet-exposed controller (J6.7).
- **The agent secret** in JNLP is a credential — leaking it lets an attacker register an agent and receive builds.

**J5.2 — Labels to route jobs**

```groovy
agent { label 'linux && docker && !gpu' }
agent { label 'arm64' }
```

**Labels are arbitrary tags on agents**, and `label` expressions support `&&`, `||`, `!`, and parentheses.

**The uses**: routing by **OS and architecture** (`linux`, `windows`, `arm64`); by **capability** (`docker`, `gpu`, `terraform`); by **network zone** (`production-network`, for agents with access to a restricted environment); and by **size** (`large`, `xlarge`).

**The practices:**

- **Label by capability, not by identity.** `docker` and `linux`, not `agent-07` — **so agents are interchangeable and can be replaced without editing pipelines.**
- **Every agent should have several labels** describing what it offers.
- **A job requesting a label no agent has waits in the queue forever** (J1.7, J8.1) — **the most common stuck-build cause**, and the message names the missing label.
- **Labels are how you segregate trust** — agents with production credentials labelled distinctly and restricted (via the Job Restrictions plugin or folder-level agent restrictions) so an arbitrary job can't schedule onto them.
- **Cloud agents (J5.3, J5.5) are provisioned by label** — the cloud configuration maps a label to a pod template or an instance type, so requesting `large` provisions a large agent on demand.

**J5.3 — The Kubernetes plugin for ephemeral pod agents**

```groovy
pipeline {
    agent {
        kubernetes {
            yaml '''
              apiVersion: v1
              kind: Pod
              spec:
                serviceAccountName: jenkins-agent      # ← IRSA (J5.9 equivalent)
                containers:
                  - name: jnlp
                    image: jenkins/inbound-agent:latest
                    resources:
                      requests: { cpu: 500m, memory: 512Mi }
                  - name: build
                    image: golang:1.23
                    command: ['sleep']
                    args: ['infinity']
                    resources:
                      requests: { cpu: "2", memory: 4Gi }
            '''
        }
    }
    stages {
        stage('Build') {
            steps {
                container('build') { sh 'go build ./...' }
            }
        }
    }
}
```

**How it works**: the plugin **creates a pod per build**, the `jnlp` container connects back to the controller (J5.1), the build runs, and **the pod is deleted.**

**Why it's the best agent model available for Jenkins:**

- **Ephemeral by construction** (J5.6) — every build gets a clean environment, so no state accumulation and no cross-build contamination.
- **Scales to zero** — no idle agent cost.
- **Per-build resource sizing** via the pod spec, and Kubernetes handles scheduling.
- **Per-build toolchain** — the container image provides the tools, so **you don't maintain agent images with every tool installed** (J5.6's drift problem disappears).
- **Cloud identity via the ServiceAccount** — IRSA or Pod Identity (A2.7), so **no static cloud credentials in Jenkins** (J6.9, J5.9).

**The considerations**: **pod startup latency** (scheduling plus image pull) adds 10–60 seconds per build — mitigated by pre-pulled images and a warm pool; **the controller must be reachable from the pods** (J5.1); and **Docker-in-Docker for image builds** is the usual design problem, with rootless alternatives preferable (D9.2).

**J5.4 — A pod template with multiple containers**

**The pattern**: **one container per tool**, all sharing the pod's workspace volume, with `container('name') { }` selecting which one a step runs in.

```yaml
spec:
  containers:
    - name: jnlp                       # required — the agent
      image: jenkins/inbound-agent:latest
    - name: maven
      image: maven:3.9-eclipse-temurin-21
      command: ['sleep']; args: ['infinity']
    - name: kaniko                     # rootless image build (D9.2)
      image: gcr.io/kaniko-project/executor:debug
      command: ['sleep']; args: ['infinity']
      volumeMounts:
        - name: docker-config
          mountPath: /kaniko/.docker
    - name: kubectl
      image: bitnami/kubectl:latest
      command: ['sleep']; args: ['infinity']
  volumes:
    - name: docker-config
      secret: { secretName: registry-credentials }
```

**The essentials:**

- **`command: ['sleep']` / `args: ['infinity']`** — **required**, because most images have an entrypoint that exits, and **a container that exits kills the pod.** **This is the single most common pod template mistake.**
- **The `jnlp` container is mandatory** (the agent itself); overriding its image is how you customise it.
- **All containers share the workspace volume**, so a build in `maven` produces artefacts the `kaniko` container packages — **which is the whole point of the multi-container pattern.**
- **Resource requests per container** (K6.1) — and **the pod's total is the sum**, so a template with five containers each requesting 2 CPU needs a 10-CPU node.
- **`container('name')`** wraps steps; steps outside any `container` block run in `jnlp`.

**The alternative to weigh**: **one container with all the tools** is simpler and means maintaining a custom image. **Multiple containers means using upstream images unchanged**, which is less maintenance and more pod overhead. **The second is usually better** and it's the idiomatic pattern.

**J5.5 — EC2 or cloud agents with autoscaling**

**The EC2 plugin** (or the EC2 Fleet plugin, which is generally better) provisions instances on demand in response to queued builds (J1.7).

**The configuration**: an AMI (or a launch template / ASG for the Fleet plugin), instance type, labels (J5.2), the number of executors per instance, an idle termination timeout, and a cap on instances.

**The key settings and their reasoning:**

- **Idle termination timeout** — how long an agent stays alive with no work. **Too short means constant provisioning churn** (each new instance costs boot time, ~1–3 minutes); **too long means paying for idle.** 10–30 minutes is a common balance.
- **A cap on instances** — prevents a runaway queue from provisioning unbounded capacity and cost.
- **Spot instances** (A4.5) — **substantially cheaper**, and **an interrupted agent kills its build.** Suits short builds; needs retry handling and it's a poor fit for a long deployment.
- **A pre-baked AMI** (A4.6) with the toolchain — **otherwise every new agent installs everything at boot**, which is slow and non-deterministic.
- **An instance profile for cloud access** (A2.6) rather than credentials in Jenkins (J6.9).

**The comparison to Kubernetes agents** (J5.3): **EC2 agents are heavier** (a VM boot rather than a pod schedule) and **give stronger isolation** (D1.2); **Kubernetes agents start faster and pack better.** **For a Jenkins estate on AWS with an existing EKS cluster, Kubernetes agents are usually the better answer**; EC2 agents suit workloads needing a full VM, specific hardware, or where there's no cluster.

**J5.6 — The risk of long-lived agents accumulating state**

**A persistent agent is not clean between builds** (contrast GA1.4, D1.4):

- **Workspaces persist** — a build's files remain, so a subsequent build may find stale artefacts, a partially-cleaned directory, or a `node_modules` from a different branch. **"It works on a fresh workspace" is the tell.**
- **Installed packages and tools drift** — a build that `apt-get install`s or `npm install -g`s changes the agent for everyone, and **agents diverge from each other**, producing "it fails only on agent 3" (J8.5).
- **Docker images and layers accumulate**, filling the disk (D6.7, J5.7).
- **Credentials leak forward** — a build writing `~/.aws/credentials` or `~/.docker/config.json` leaves them for the next build, **which may belong to a different team.** **This is the security consequence** and it's the serious one (GA8.5's argument).
- **Environment modifications** — a changed `PATH`, a modified global config.
- **Processes left running** hold ports and memory.

**The mitigations:**

- **Ephemeral agents** (J5.3, J5.5) — **the structural answer**, and Kubernetes pod agents give it by default.
- **`cleanWs()`** in `post { always }` (J2.4) — necessary and not sufficient, since it only cleans the workspace.
- **`ws()`** with a unique path, or workspace-per-branch.
- **Periodic agent recycling** — terminate and re-provision on a schedule.
- **Run builds in containers** (J2.3's `docker` agent) even on a persistent agent, so the build's filesystem changes are discarded.

**J5.7 — Agent workspaces and disk consumption**

**Each job gets a workspace directory on each agent it runs on** — `$JENKINS_AGENT_HOME/workspace/<job-name>`. **They persist after the build** (J5.6).

**How disk fills:**

- **Many jobs × many agents** — a multibranch project with 50 branches, each having run on 5 agents, is 250 workspaces.
- **Large checkouts** — a monorepo with full history, multiplied.
- **Build output left in place** — `node_modules`, `target/`, `vendor/`.
- **Docker images and build cache** on agents that build images (D6.7).
- **Orphaned job workspaces** — the job was deleted (J4.5) **and the workspace on the agent was not.**

**The management:**

- **`cleanWs()`** in `post { always }` — the basic hygiene, and it costs a re-clone next time (mitigated by `skipDefaultCheckout` plus a reference repository).
- **The Workspace Cleanup plugin's disk-based policies.**
- **A shallow clone** (`depth: 1`) in the checkout for a large repository — **a large saving on a monorepo.**
- **A git reference repository** — a shared bare clone on the agent that new workspaces reference, so a clone copies almost nothing.
- **Disk monitoring on agents** — Jenkins marks an agent offline when free space drops below a threshold (`Free Disk Space` node monitor), **which is the mechanism by which a disk problem becomes a capacity problem** (J8.1, J8.4).
- **Ephemeral agents** (J5.6) — the problem disappears.

**J5.8 — Diagnosing an agent that won't connect or keeps dropping**

**Won't connect:**

1. **Network path** — can the controller reach the agent (SSH, J5.1), or the agent reach the controller (JNLP)? Firewall, security group (A3.2), routing.
2. **The agent port** — for JNLP, is it open and is the correct port advertised? **WebSocket mode avoids this** entirely.
3. **Credentials** — SSH key or the agent secret.
4. **Java** — the wrong version or missing on the agent. **Jenkins has minimum Java requirements that change with versions**, and a controller upgrade can leave agents on an unsupported Java.
5. **Version mismatch** — the agent JAR must be compatible with the controller; **a controller upgrade requires agents to pick up the new JAR**, which SSH agents do automatically and JNLP agents may not.
6. **The agent's log** — on the agent, or in the UI under the node — states the reason, and **reading it is the fastest route.**

**Keeps dropping:**

1. **Network instability** — a flapping link, a firewall or load balancer with an idle timeout killing the long-lived connection. **An idle timeout on an intermediate proxy is a classic cause** and produces disconnections at a suspiciously regular interval.
2. **Agent OOM** — the JVM or the build exhausting memory, killing the agent process (D10.6).
3. **Disk full** (J5.7) — Jenkins takes the agent offline.
4. **The controller under pressure** (J8.3) — GC pauses long enough to miss the agent's ping, so it's declared dead. **A controller memory problem manifests as agents dropping**, which is a misleading symptom.
5. **`-Dhudson.slaves.ChannelPinger.pingIntervalSeconds`** and the ping timeout — tuning these is the workaround for a slow network.
6. **Spot interruption** (J5.5) for cloud agents.

**J6. Credentials & security follows below.**

---

## J6. Credentials & security

**J6.1 — The credentials store and the correct binding per type**

**Credential types and their bindings:**

| Type | Binding | Produces |
|---|---|---|
| Secret text | `string(credentialsId:, variable:)` | One env var |
| Username/password | `usernamePassword(..., usernameVariable:, passwordVariable:)` | Two env vars |
| Secret file | `file(credentialsId:, variable:)` | A path to a temp file |
| SSH private key | `sshUserPrivateKey(..., keyFileVariable:, passphraseVariable:)` | A path to a key file |
| Certificate | `certificate(..., keystoreVariable:)` | A keystore path |
| AWS credentials (plugin) | `withAWS(credentials:)` or `aws(...)` | AWS env vars |

```groovy
withCredentials([
    string(credentialsId: 'api-token', variable: 'TOKEN'),
    file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')
]) {
    sh 'kubectl --kubeconfig="$KUBECONFIG" apply -f manifests/'
}
```

**The points that matter:**

- **Use the right type.** Storing a private key as "secret text" works and loses the file-based binding, so you end up writing it to disk in the pipeline — **which is worse, because it isn't cleaned up.**
- **`file` and `sshUserPrivateKey` write a temporary file that's deleted when the block exits** — **so don't copy it elsewhere.**
- **`withCredentials` scopes narrowly** (J2.10); `environment { credentials() }` is broader.
- **Never `echo` a credential**, and be aware masking is defeated by transformation (J6.3).
- **Reference by ID**, and **use meaningful IDs** — a credential ID is effectively an API for every pipeline that uses it, so renaming one breaks builds.

**J6.2 — Scoping credentials to folders**

**Credentials have a scope**: **System** (controller only, not available to builds), **Global** (available to all jobs), or **attached to a folder** (available only to jobs in that folder and its children).

**Why folder scoping matters:**

- **A global credential is available to every job on the instance** — so **any team's pipeline can use the production deployment credential**, whether or not they should. **On a shared Jenkins with many teams, that's a serious access control failure**, and it's the default state on most inherited estates.
- **Folder scoping makes the credential's blast radius match the team's** — the payments folder holds the payments credentials, and a job in another folder cannot reference them (the ID simply doesn't resolve).
- **Combined with folder-level authorisation** (J6.5), it gives a coherent tenancy model: a team owns a folder, its jobs, its credentials, and its permissions.

**The practices:**

- **Almost nothing should be a global credential** — the exceptions are genuinely instance-wide things like the SCM organisation credential.
- **A folder per team or per domain** (J1.4), with credentials attached.
- **Audit what's global** on an inherited estate (J9.3) — **it's usually a long list and a quick win.**
- **The strongest version**: **don't store credentials in Jenkins at all** (J6.9) — an external secrets manager with per-folder access, or cloud IAM roles on the agent (J5.3).

**J6.3 — How credentials leak through logs despite masking**

**Jenkins masks bound credential values in the console output** — an exact match is replaced with `****`.

**Why that's insufficient** (the same argument as GA4.7):

- **Transformation defeats it.** A credential that is **base64-encoded, URL-encoded, JSON-escaped, or split** no longer matches the registered string and **prints in full.** `echo $TOKEN | base64` is the canonical leak.
- **Partial output** — printing the first N characters masks nothing.
- **Derived values** — a token exchanged for another, a signed URL, an assembled connection string.
- **`set -x` in a shell step** echoes commands including their arguments — **so a credential passed as a command-line argument is printed.** **This is the most common real leak**, and it's why `--password-stdin` style patterns matter (D8.1).
- **A tool's error message** may include the credential in a transformed form.
- **Archived artifacts and test reports are not masked** (J2.14) — a log file uploaded as an artefact leaks whatever it contains.
- **Environment dumps** — `env` or `printenv` in a debug step.

**The mitigations:**

- **Never echo, encode, or transform a credential.**
- **Pass secrets via stdin or a file**, not as command-line arguments (they're also visible in `ps` on the agent).
- **Avoid `set -x`** in steps handling credentials.
- **Treat a credential that appeared in a log as leaked and rotate it** (S6.4) — Jenkins build logs are retained (J7.4), readable by anyone with job access, and included in backups (J7.1).
- **Prefer credentials that don't exist** — IAM roles on the agent (J5.3), or short-lived tokens from an external manager (J6.9).

**J6.4 — Authentication and authorisation strategies**

**Two separate concerns, and conflating them is common:**

**Authentication (who are you)** — the Security Realm:

- **Jenkins' own user database** — fine for a small instance, and it means separate credentials to manage and offboard (A1.4's argument).
- **LDAP / Active Directory** — enterprise standard.
- **SAML or OIDC** — **the right answer**: SSO with the corporate IdP, so joiners/movers/leavers is handled centrally and MFA is enforced upstream.
- **GitHub / Bitbucket OAuth** — convenient, and it ties Jenkins access to SCM access, which may or may not be the boundary you want.

**Authorisation (what can you do)** — the Authorization Strategy:

- **Anyone can do anything** — **no authorisation.** **Present on far too many inherited instances**, and it's the first thing to fix (J9.3).
- **Logged-in users can do anything** — barely better; any authenticated user is an administrator.
- **Matrix-based security** — a global permission grid (J6.5).
- **Project-based Matrix** — matrix plus per-job and per-folder overrides. **The standard choice.**
- **Role-Based Strategy** (plugin) — named roles assigned to users and groups (J6.5).

**The essential points**: **disable "anyone can do anything" and legacy modes**; **integrate SSO** so access follows employment; and **enable CSRF protection and agent-to-controller access control**, which are on by default in modern versions and disabled on some old instances.

**J6.5 — Matrix or role-based authorisation**

**Matrix-based security**: a grid of permissions (Overall, Credentials, Agent, Job, Run, View, SCM) against users and groups. **Project-based Matrix** adds the same grid at folder and job level, inheriting from above.

**Role-Based Strategy (plugin)**: define **named roles** with permission sets, then assign users and groups to roles — optionally **scoped by a regex on job names** (project roles).

**The comparison**: **matrix is built in and becomes unwieldy** at scale — a grid with 50 groups and 30 permissions is unreadable and unauditable. **Role-based is more maintainable** because the permission set is defined once per role, and it's the usual choice for a large multi-team instance.

**The permission model to aim for:**

| Role | Permissions |
|---|---|
| **Administrator** | Overall/Administer — **very few people** |
| **Team lead** | Full control of their folder (J1.4), including credentials |
| **Developer** | Build, Cancel, Read, Workspace on their folder |
| **Read-only** | Read on everything, for visibility |
| **Anonymous** | **Nothing**, or Read at most |

**The critical points:**

- **`Overall/Administer` is total control** — including the script console (J7.11) and script approval (J6.6), so **it's equivalent to root on the controller and on everything Jenkins can deploy to.** Grant it to as few people as possible and audit it.
- **`Job/Configure` lets someone edit a job**, which for a pipeline job means **changing the Jenkinsfile source or running arbitrary pipeline code** — a significant privilege.
- **Folder-scoped permissions plus folder-scoped credentials** (J6.2) is the coherent tenancy model.
- **Assign to groups from the IdP**, not to individuals (A1.5's argument).

**J6.6 — Why script approval is a privilege escalation path**

**The mechanism**: the Groovy sandbox blocks non-allowlisted methods (J2.12), and an administrator approves specific method signatures in **In-process Script Approval**.

**Why it's an escalation path:**

- **Pipeline Groovy runs on the controller with full JVM access** (J1.1) — the filesystem including `JENKINS_HOME` and `secrets/` (J1.3), the Jenkins object model, and the ability to execute processes.
- **So approving the wrong signature grants that access to anyone who can commit a Jenkinsfile.** Approving `java.lang.Runtime.exec`, `groovy.lang.GroovyShell`, reflection methods, or `jenkins.model.Jenkins.getInstance` **is effectively granting administrator rights to every developer with commit access.**
- **The approval queue creates pressure to approve.** A developer's build is blocked; an administrator approves to unblock; **the assessment doesn't happen.** **This is the practical failure** — it's not that people don't know, it's that the workflow encourages rubber-stamping.
- **Approvals are permanent and global** — an approval granted for one job applies to every job on the instance, forever.

**The controls:**

- **Treat each approval as a security decision.** Ask what the signature permits and who can therefore use it.
- **Minimise Groovy** (J2.11) so the requests are rare.
- **Put privileged logic in a trusted global shared library** (J3.4) — **which runs outside the sandbox and is version-controlled and reviewed.** **This is the correct architectural answer**: review the code in a PR rather than approving a method signature in a UI.
- **Audit the existing approval list** on an inherited estate (J9.3) — **it's usually long and contains things that should never have been approved.**
- **Never enable "run without sandbox"** on a job that anyone can modify.

**J6.7 — The security risk of an internet-exposed Jenkins**

**Jenkins is a very high-value target**: it holds deployment credentials for everything (J1.3), executes arbitrary code by design, and frequently has direct network access to production.

**The risks of exposure:**

- **A history of severe, remotely-exploitable CVEs** — including pre-authentication remote code execution in both the core and plugins (J6.8). **Jenkins instances are actively scanned for and exploited**, and a known-vulnerable exposed instance is compromised in hours, typically for cryptomining first and worse later.
- **Weak or absent authorisation** (J6.4) on many instances — "anyone can do anything" on an internet-facing instance is total compromise by design.
- **The script console** (J7.11) is RCE by design for anyone with admin.
- **Credential theft** — everything in `credentials.xml`, decryptable with `secrets/`.
- **Supply chain** — an attacker who controls Jenkins can inject into any artefact it builds (S7.1, C10.4), and the resulting artefact is validly signed and deployed through the legitimate process.

**The controls, in order:**

1. **Don't expose it.** VPN, private network, or a zero-trust proxy with SSO. **The single most effective control.**
2. **If webhooks require inbound access** (J4.4), expose **only** the webhook endpoint through a relay or a narrow allowlist of the SCM's published IP ranges — **not the whole UI.**
3. **SSO with MFA** (J6.4).
4. **Patch aggressively** (J6.8).
5. **Least privilege** (J6.5), no anonymous access.
6. **Network egress restrictions** from the controller and agents.
7. **Monitor** — failed logins, script console use, credential access (J6.10).

**J6.8 — Patching Jenkins and plugins, and CVE exposure**

**The exposure:**

- **Jenkins publishes security advisories regularly** — typically monthly, frequently covering multiple plugins, and **including high and critical severity issues.**
- **Plugins are the dominant source** (J1.8) — the core is comparatively well-scrutinised; the long tail of plugins is not.
- **Some are pre-authentication RCE.** For an exposed instance (J6.7) that's immediate compromise.
- **Abandoned plugins never get fixed** — the advisory says "no fix available", and the only remedy is removing the plugin (J9.6).

**The practice:**

- **Subscribe to the Jenkins security advisories mailing list** — and actually read them. **The advisory names the affected plugins and versions**, so triage is quick.
- **Patch on a regular cadence** — monthly, in small batches (J7.2), rather than annually in one large risky upgrade.
- **Use the LTS line** for the core, which gets backported fixes and is more stable than weekly releases.
- **Track installed plugin versions against advisories** — the Jenkins UI flags plugins with known vulnerabilities, and **checking that list is the first thing to do on an inherited estate** (J9.3).
- **Remove unused plugins** (J9.6) — the cheapest way to reduce exposure.
- **Test upgrades on a copy** (J7.2) — restore a `JENKINS_HOME` backup to a separate instance and upgrade there first.

**The realistic framing for an inherited estate**: **it will be badly out of date, with known-vulnerable plugins.** The remediation is a prioritised programme (J9.3), starting with anything remotely exploitable on an exposed instance.

**J6.9 — Integrating an external secrets manager**

**The plugins**: **HashiCorp Vault**, **AWS Secrets Manager Credentials Provider**, **Azure Key Vault**, **CyberArk**, and the **Kubernetes Credentials Provider** (reading Kubernetes Secrets).

```groovy
withVault(vaultSecrets: [[path: 'secret/payments', secretValues: [
    [envVar: 'DB_PASSWORD', vaultKey: 'db_password']
]]]) {
    sh './migrate.sh'
}
```

**Why it beats storing secrets in Jenkins:**

- **Rotation happens in the secrets manager**, and Jenkins fetches the current value at build time — **so rotation doesn't require touching Jenkins** (S6.5).
- **Access control is the secrets manager's**, which is generally better than Jenkins' credential scoping (J6.2) and is audited there (A10.16).
- **Jenkins holds no secret material** — so **a Jenkins compromise doesn't yield every credential** (J1.3), which materially reduces the blast radius of the most likely incident.
- **The credential is short-lived** where the manager supports dynamic secrets (S6.6) — Vault's database engine issuing a per-build database user with a one-hour lease.
- **Audit** — the secrets manager records who fetched what.

**The stronger answer where it applies**: **no secret at all.** **An agent with an IAM instance profile (A2.6) or a Kubernetes ServiceAccount with IRSA (J5.3, A2.7) has AWS access with nothing stored in Jenkins** — which is the equivalent of GitHub's OIDC (GA6.5) and is the right pattern for cloud access.

**The bootstrapping consideration**: Jenkins still needs a credential to authenticate to the secrets manager — **ideally the agent's own workload identity**, which closes the loop.

**J6.10 — Audit logging and tracking who changed a job**

**Jenkins' built-in auditing is weak**, and being honest about that is part of the answer.

**What's available:**

- **The Audit Trail plugin** — logs requests to a file or syslog, including job configuration changes, builds triggered, and credential access. **The standard answer**, and it needs configuring.
- **The Job Configuration History plugin** — **keeps a versioned history of `config.xml` changes with diffs and the user who made them.** **Genuinely useful on a click-configured estate** (J7.8) and it's the closest thing to version control for freestyle jobs.
- **`$JENKINS_HOME` in git** — some people version-control the config directory. Crude, and it works.
- **Build logs** record who triggered a build and, with `input` (J2.8), who approved.
- **The system log** for authentication events.

**The gaps to acknowledge:**

- **Nothing is on by default** — a stock Jenkins has essentially no audit trail of configuration changes.
- **Logs are local** to the controller, so **a compromised Jenkins can erase them** (S9.7). **Ship them off-instance.**
- **Script console use** (J7.11) is the highest-risk action and is poorly audited by default — **configure the Audit Trail plugin to capture it specifically.**
- **Credential access** is logged by some providers and not others.

**The structural answer**: **JCasC and pipeline-as-code** (J7.6, J2.1) move configuration into git, **where the audit trail is complete, reviewed, and tamper-evident** (C10.7). **That's a far better answer than auditing UI changes** — and it's the argument for J7.8.

---

## J7. Operations & maintenance

**J7.1 — Backing up and restoring `JENKINS_HOME`**

**What must be backed up** (J1.3):

| Path | Essential? |
|---|---|
| `config.xml`, `*.xml` at root | **Yes** — global configuration |
| `credentials.xml` | **Yes** |
| `secrets/` | **Yes — and without it, credentials are unrecoverable** |
| `jobs/*/config.xml` | **Yes** — job definitions |
| `jobs/*/builds/` | **Optional** — build history and artifacts; **the bulk of the size** |
| `plugins/*.jpi` | **Yes** (or record the versions and reinstall) |
| `users/` | Yes |
| `nodes/` | Yes |
| `workspace/` | **No** — reproducible |

**The method:**

```bash
# stop or quiesce first for consistency
curl -X POST http://jenkins/quietDown --user "$USER:$TOKEN"
tar czf jenkins-home-$(date +%F).tar.gz \
    --exclude='workspace' --exclude='*/builds/*/archive' \
    -C /var/lib/jenkins .
```

**The considerations:**

- **`secrets/` plus `credentials.xml` is a full credential dump** — **the backup must be encrypted and access-controlled as tightly as Jenkins itself** (J6.7). A backup on a share everyone can read is a credential leak.
- **Consistency** — Jenkins writes XML continuously, so a hot filesystem copy can catch a partially-written file. **`quietDown` (stop scheduling new builds) or a filesystem snapshot** gives a consistent point (D6.10's crash-consistency argument).
- **Size** — `builds/` dominates, so **excluding archived artifacts** (which should be in a registry anyway, J2.14) makes the backup practical.
- **Plugin versions matter** — restoring `plugins/` restores exact versions, which is what you want for a rollback (J7.2).

**And the essential point** (DB6.5): **test the restore.** Restore into a separate instance, start it, and confirm jobs and credentials work. **An untested Jenkins backup is very commonly broken** — missing `secrets/`, a plugin version mismatch, or a permissions problem.

**J7.2 — Upgrading with a rollback path**

**The procedure:**

1. **Read the changelogs** — the core upgrade guide and the plugin release notes, particularly for breaking changes.
2. **Take a backup** (J7.1) — **this is the rollback path**, so it must be complete and recent.
3. **Test on a copy** — restore the backup to a separate instance, upgrade there, and **run a representative set of jobs.** **This is the step that catches plugin conflicts** (J7.3) before they affect anyone.
4. **Upgrade in small batches** — the core, or a handful of related plugins, not everything at once. **A batch of forty plugin upgrades that breaks gives you no idea which one did it.**
5. **`quietDown`** so no builds are in flight.
6. **Upgrade and restart.**
7. **Verify** — the UI loads, agents reconnect (J5.8), a canary job runs, and the plugin manager shows no errors.

**The rollback:**

- **Restore `JENKINS_HOME` from the backup** — including `plugins/`, because a downgraded plugin may not read data written by the newer version.
- **Reinstall the previous core version.**
- **Note the asymmetry**: **plugin downgrades are not always safe** — a plugin that migrated its data format on upgrade may leave configuration the old version can't parse. **So the rollback is a full restore, not a selective downgrade**, and that's why the backup matters.

**The cadence argument** (J6.8): **frequent small upgrades are far safer than infrequent large ones** — the same batch-size argument as C1.9. An instance two years behind requires a large, risky, multi-step upgrade; one upgraded monthly is a routine operation.

**J7.3 — Diagnosing a plugin conflict after upgrade**

**The symptoms**: the UI shows errors or blank pages; jobs fail with `NoSuchMethodError`, `NoClassDefFoundError`, or `ClassNotFoundException`; a plugin shows as failed to load in the plugin manager; or a pipeline step suddenly doesn't exist.

**The diagnostic:**

1. **Manage Jenkins → System Information / Manage Plugins** — **failed plugins are listed with the reason**, usually an unsatisfied dependency with the required version.
2. **`$JENKINS_HOME/logs/` and the system log** — **the stack trace names the class and the plugin**, which is the direct answer.
3. **`NoSuchMethodError` means a version mismatch** — plugin A was compiled against a version of plugin B that's no longer installed. **The class name tells you which.**
4. **Check the dependency chain** — the plugin manager shows what each plugin requires.

**The resolution:**

- **Upgrade the dependency** to the required version — usually the answer, and it may cascade.
- **Downgrade the plugin that broke** — with the caveat in J7.2 about data formats.
- **Restore the backup** if the instance is unusable.
- **Remove the plugin** if it's abandoned and blocking (J9.6).

**The prevention, which matters more:**

- **Test on a copy first** (J7.2) — this is exactly what it catches.
- **Small batches**, so the culprit is obvious.
- **Keep the plugin set minimal** (J9.6) — fewer plugins, fewer interactions.
- **Don't skip many versions** — Jenkins' upgrade path assumes incremental steps, and a two-year jump compounds every incompatibility.

**J7.4 — Build retention and disk usage**

**The mechanisms:**

- **`buildDiscarder` in the pipeline** (J2.9) — **the primary control**, and it should be on every job:
  ```groovy
  options { buildDiscarder(logRotator(numToKeepStr: '30', daysToKeepStr: '30',
                                      artifactNumToKeepStr: '5')) }
  ```
- **A global default** via JCasC (J7.6) or the "Discard old builds" defaults, so a job without an explicit policy still gets one.
- **Orphaned item retention** for multibranch (J4.5).
- **Agent workspace cleanup** (J5.7) — separate, and equally necessary.

**The critical distinction**: **`numToKeepStr` keeps build records (small); `artifactNumToKeepStr` keeps archived artifacts (large).** **Keeping 100 builds' logs is cheap; keeping 100 builds' artifacts is not** (J2.14). **Set them separately, with a much lower artifact count** — this is the single most effective retention setting.

**Where the disk goes** (J1.3, J8.4):

```bash
du -sh $JENKINS_HOME/jobs/*/builds | sort -h | tail -20
du -sh $JENKINS_HOME/jobs/*/*/branches/*/builds | sort -h | tail   # multibranch
```

**Usually**: archived artifacts, then build logs, then orphaned multibranch jobs, then plugin and update-centre caches.

**The structural fix**: **deployable artefacts belong in a registry or artifact repository** (C3.5), not archived in Jenkins. **Jenkins archives should be reports and diagnostics only**, which changes the size profile entirely.

**J7.5 — JVM heap tuning and controller memory pressure**

```bash
JAVA_OPTS="-Xmx8g -Xms8g \
           -XX:+UseG1GC \
           -XX:+HeapDumpOnOutOfMemoryError \
           -XX:HeapDumpPath=/var/log/jenkins \
           -Djenkins.model.Jenkins.slaveAgentPort=50000"
```

**What consumes controller memory:**

- **The object model** — every job, every build record, every node is an object. **A large instance with thousands of jobs and long build history uses gigabytes just holding the model.**
- **Concurrent pipeline executions** (J1.1) — **pipeline flow control runs on the controller**, so each running build holds CPS state (J2.13).
- **Build logs being written and read.**
- **Plugins**, some of which are memory-hungry.
- **The UI** — loading a job with thousands of builds.

**Tuning:**

- **`-Xms` equal to `-Xmx`** — avoids heap resizing pauses.
- **G1GC** is the sensible default; **for very large heaps, consider a low-pause collector** (O10.5).
- **Size from measurement**, not guesswork — **and note that the container memory limit must exceed the heap substantially** (O10.6, D10.6), because the JVM's total footprint includes metaspace, thread stacks, and native memory. **A container limit equal to `-Xmx` guarantees an OOM kill.**
- **`-XX:+HeapDumpOnOutOfMemoryError`** so an OOM produces evidence (J8.3).

**Reducing the pressure, which matters more than tuning:**

- **Aggressive build retention** (J7.4) — fewer build records, smaller model.
- **Fewer, simpler pipelines** — move logic to shell scripts on agents (J2.11).
- **No builds on the controller** (J1.2).
- **Split into multiple controllers** (J7.9) if one instance is genuinely too large.

**J7.6 — Configuration as Code (JCasC)**

```yaml
jenkins:
  systemMessage: "Managed by JCasC — do not configure via the UI"
  numExecutors: 0                          # no builds on the controller (J1.2)
  authorizationStrategy:
    roleBased:
      roles:
        global:
          - name: admin
            permissions: [Overall/Administer]
            entries: [{ group: "platform-team" }]
  securityRealm:
    oic:
      clientId: "${OIDC_CLIENT_ID}"
      # ...
  clouds:
    - kubernetes:
        name: k8s
        templates:
          - name: default
            containers: [...]

credentials:
  system:
    domainCredentials:
      - credentials:
          - aws:
              id: "deploy-role"
              # value from an env var or a secrets file — never literal
unclassified:
  location:
    url: https://jenkins.acme.com/
  globalLibraries:
    libraries:
      - name: acme-pipeline
        defaultVersion: v3
        retriever: { modernSCM: { scm: { git: { remote: "..." } } } }
```

**What it gives you** (the same argument as TF1.5 and C2.5):

- **Configuration in version control** — reviewed, diffed, historied, and rollback-able. **Which is the fix for J7.8.**
- **Reproducibility** — a new controller stands up identically from the YAML.
- **Disaster recovery** becomes "deploy the config" rather than "restore a filesystem backup" (J7.1) — **a materially better position.**
- **Consistency across controllers** (J7.9).
- **Auditability** (J6.10) — git log answers who changed what.

**The practicalities:**

- **Secrets come from environment variables or a secrets file** (`${VAR}`), **never literals in the YAML** — so the config can be in git.
- **`configuration-as-code` plugin**, with the config from a file, a directory, or a URL.
- **"Apply new configuration"** reloads without a restart.
- **Not everything is covered** — some plugins have no JCasC support, so there's usually a residue of UI configuration.
- **The export feature** (`/configuration-as-code/viewExport`) generates YAML from a running instance, **which is how you migrate an existing estate** (J9.3).

**J7.7 — Job DSL to generate jobs programmatically**

```groovy
// a seed job runs this
folder('payments') {
    description('Payments team')
}

multibranchPipelineJob('payments/api') {
    branchSources {
        github {
            id('payments-api')
            repoOwner('acme')
            repository('payments-api')
            credentialsId('github-app')
        }
    }
    orphanedItemStrategy { discardOldItems { daysToKeep(7) } }   // J4.5
}

['api', 'worker', 'scheduler'].each { svc ->
    pipelineJob("payments/${svc}-nightly") {
        triggers { cron('H 2 * * *') }
        definition { cpsScm { scm { git { remote { url("...${svc}.git") } } } } }
    }
}
```

**Job DSL generates job configurations from Groovy**, run by a **seed job** that creates or updates them.

**The distinction from JCasC** (J7.6), which is worth being clear about: **JCasC configures Jenkins itself** — security, clouds, global settings, credentials. **Job DSL creates jobs.** **They're complementary**, and a well-managed instance uses both: JCasC for the system, Job DSL (or an organisation folder) for the jobs.

**When Job DSL is worth it**: generating many similar jobs programmatically — a job per service in a monorepo, a standard set per team. **When it isn't**: **an organisation folder (J1.4) discovers repositories automatically** and requires no code at all — **so for the common case of "a pipeline per repository with a Jenkinsfile", the organisation folder is simpler and better**, and Job DSL is for the cases it doesn't cover.

**The caution**: the seed job runs arbitrary Groovy with script approval implications (J6.6), and **a bug in the seed job can delete jobs** — the "removed job action" setting controls whether jobs no longer in the DSL are disabled or deleted, and **defaulting to delete is dangerous.**

**J7.8 — Why click-configured Jenkins becomes unmaintainable**

The reasons, and they compound:

- **No version control.** Configuration lives in `config.xml` files in `JENKINS_HOME` (J1.3). **No history, no diff, no review, no attribution, no rollback** (J1.5, J6.10).
- **No reproducibility.** **You cannot stand up an identical instance** — the only recovery is a filesystem restore (J7.1), and if the backup is incomplete or old, the configuration is simply lost.
- **Undocumented drift.** Settings changed years ago by people who have left, for reasons nobody remembers. **Nobody dares change anything because nobody knows what depends on it.**
- **No review.** A change to global security settings or a shared credential happens with one click, unreviewed.
- **Inconsistency across jobs.** Five hundred freestyle jobs configured individually have five hundred slightly different configurations, and a change to a shared practice means five hundred edits.
- **Knowledge is in the UI, not the repository** — so onboarding means clicking through Jenkins rather than reading code.
- **It scales inversely** — the more jobs and settings, the more unmaintainable it becomes, with no natural correction.

**The remedy** (J9.3, J9.4): **JCasC for the system** (J7.6), **pipeline-as-code for the jobs** (J2.1), **organisation folders or Job DSL for job creation** (J7.7), and **shared libraries for common logic** (J3.1). **The endpoint is that `JENKINS_HOME` holds only state — build history and runtime data — and everything that constitutes configuration is in git.**

**J7.9 — HA options for Jenkins and their limitations**

**The honest headline: Jenkins is not designed for high availability, and open-source Jenkins has no true HA.**

**The options and their limits:**

- **Active/passive with shared storage** — a standby controller with `JENKINS_HOME` on shared storage (EFS, a SAN), failing over on controller loss. **Limits**: **failover is minutes, not seconds**; **running builds are lost**; **shared filesystem performance is a real problem** — `JENKINS_HOME` is latency-sensitive and EFS is notably slow for it; and **split-brain is catastrophic** (two controllers writing to one `JENKINS_HOME` corrupts it), so fencing is essential (DB5.5).
- **Kubernetes with a single replica and a persistent volume** — the pod reschedules on node loss. **Recovery is minutes**, running builds are lost, and it's simple and honest. **This is the pragmatic answer for most.**
- **CloudBees CI (commercial)** — **operations centre with multiple controllers**, and **HA/HS controllers in recent versions.** **The only genuinely supported HA**, and it's a licence cost.
- **Multiple independent controllers** — split by team or domain, so **one controller's failure affects a subset.** **Not HA, and it reduces blast radius**, and it's frequently the right structural answer for a large estate.

**Why true HA is hard**: the controller holds all state on a local filesystem (J1.3), **executes pipeline logic in memory with CPS state** (J2.13), and **has no clustering primitive.** Two controllers cannot share the work.

**The framing to give**: **for most organisations, the right answer is a fast, tested restore rather than HA** (J7.1) — an RTO of 15–30 minutes for a CI system is usually acceptable (A11.1's argument), and **the engineering to do better is disproportionate.** **State the RTO the business needs and derive from it** rather than assuming HA is required.

**J7.10 — Monitoring Jenkins**

**The metrics that matter:**

- **Queue depth and queue time** (J1.7) — **the primary capacity signal.** Rising queue time means insufficient executors (J1.6) or agents that won't connect (J5.8).
- **Executor utilisation** — persistently at 100% means capacity pressure; persistently low means over-provisioning.
- **Online/offline agent count** — **a dropping agent count is the leading indicator** of an infrastructure problem.
- **Build duration**, as a distribution per job — **a trend upward is a degrading pipeline** (C2.10).
- **Build success rate** and **flaky rate** (J8.5, C2.8).
- **Controller JVM**: heap usage, GC pause time and frequency (J7.5, O10.5) — **GC pauses are what cause agents to drop** (J5.8).
- **`JENKINS_HOME` disk free** — with a **predicted-full alert** (O3.5), because this is the most common Jenkins outage (J8.4).
- **Plugin update and security advisory status** (J6.8).

**The tooling**: the **Prometheus Metrics plugin** exposes all of this at `/prometheus`, scraped into your normal stack (O3.1) — **which is the right answer**, because Jenkins should be monitored alongside everything else rather than through its own UI.

**The alerts worth having**: disk predicted-full; queue time above a threshold; agents offline; controller heap sustained high; and **build success rate on main dropping** (C2.10).

**J7.11 — The script console, and why it's dangerous**

**Manage Jenkins → Script Console** executes **arbitrary Groovy on the controller, in the Jenkins JVM, with no sandbox** (J2.12).

```groovy
// legitimate: find jobs using a credential
Jenkins.instance.getAllItems(Job.class).each { j -> /* inspect */ }
```

**Why it's dangerous:**

- **It is unrestricted remote code execution as the Jenkins process user.** Read `secrets/` and decrypt every credential (J1.3), read and modify any file, execute shell commands, and modify Jenkins itself.
- **Anyone with `Overall/Administer` has it** (J6.5) — **so granting that permission is granting RCE on the controller and, transitively, on everything Jenkins can deploy to.**
- **Poorly audited by default** (J6.10) — configure the Audit Trail plugin to capture it explicitly, and **alert on its use.**
- **No undo.** A script that modifies or deletes takes effect immediately with no confirmation.
- **It's the first thing an attacker uses** after compromising an admin account (J6.7).

**Using it safely, when you must:**

- **Read-only first** — write the script to report what it *would* do, run that, inspect, then modify it to act.
- **Test on a non-production instance.**
- **Small, specific scripts** rather than large ones.
- **Record what you ran and why** — treat it as a break-glass action (S9.2, C10.6).
- **Prefer alternatives**: the CLI, the REST API, JCasC (J7.6), or Job DSL (J7.7) for anything repeatable. **If you're using the script console regularly, that's a signal the configuration should be managed as code.**

**The governance point**: **audit who has `Overall/Administer`** on an inherited estate (J9.3) — it's usually far more people than necessary, and each of them has RCE on the controller.

---

## J8. Troubleshooting

**J8.1 — A build stuck in the queue**

**Start with the queue item's tooltip** — Jenkins states the reason, and reading it resolves most cases immediately (J1.7).

**The causes and their checks:**

1. **"There are no nodes with the label 'X'"** — **the most common.** A typo in the label, or the agent providing it is offline or removed (J5.2). Check Manage Nodes for what labels exist.
2. **"Waiting for next available executor"** — genuine capacity. Check executor utilisation (J7.10); the fix is more agents or fewer executors held (J2.8's `input` problem).
3. **"Build #N is already in progress"** — `disableConcurrentBuilds()` (J2.9).
4. **"Waiting for resource"** — a lockable resource held elsewhere.
5. **Quiet period** — a configured start delay.
6. **The agent is offline** (J5.8) — including **automatically taken offline for low disk** (J5.7), which is a frequently-missed cause.
7. **A cloud agent failed to provision** (J5.3, J5.5) — **check the cloud's logs**: a Kubernetes pod that can't schedule (K6.13), an EC2 launch failure, or an exhausted quota (A11.9).
8. **The controller is unresponsive** (J8.3) and not scheduling at all — **the tell is that *everything* is queued.**

**The diagnostic order**: read the reason → check the required label exists → check agents are online → check cloud provisioning → check controller health.

**J8.2 — A hung build, and killing it cleanly**

**The escalation, in order:**

1. **The stop button in the UI** — sends an interrupt to the pipeline. **Often sufficient.**
2. **Wait** — a pipeline in a `sh` step waits for the process; the interrupt propagates when the step checks.
3. **Click stop again** — Jenkins escalates to a harder termination.
4. **"Terminate" / the `X` on the build page** after repeated stops.
5. **The script console** (J7.11) as the last resort:
   ```groovy
   Jenkins.instance.getItemByFullName('folder/job')
       .getBuildByNumber(42).doKill()
   ```
6. **Kill the process on the agent** — for a `sh` step whose child process is ignoring signals, `ps` on the agent and kill the process tree (D4.3's signal semantics).

**Why builds hang:**

- **A process on the agent not responding to termination** — a child that ignores SIGTERM, or a process group not being killed (D4.5's PID 1 issue in a container agent).
- **An unanswered `input`** without a timeout (J2.8) — **not hung, waiting**, and it looks the same.
- **A network operation with no timeout** — a hung `git fetch` or an API call.
- **CPS deadlock** (J2.13) — rare and real.
- **The agent disconnected mid-build** (J5.8) and the controller is waiting for it.
- **The controller is unresponsive** (J8.3).

**The prevention** (J2.9): **`timeout` on every pipeline**, and **a `timeout` step around specific risky operations.** A hung build without one holds an executor indefinitely (J1.6) and, on a cloud agent, costs money.

**J8.3 — A controller running out of memory**

**The symptoms**: the UI is slow or unresponsive; **agents disconnect** (J5.8) because GC pauses exceed the ping timeout; builds queue without starting (J8.1); and eventually `OutOfMemoryError` in the logs or the JVM dies.

**The diagnosis:**

1. **The system log and `$JENKINS_HOME/logs/`** — `OutOfMemoryError`, and **the heap dump** if `-XX:+HeapDumpOnOutOfMemoryError` was set (J7.5).
2. **Monitoring** — heap usage and GC pause time over time (J7.10). **A sawtooth with a rising floor is a leak; a plateau at the limit is under-provisioning** (O10.4).
3. **The Monitoring plugin** (JavaMelody) gives in-instance JVM detail.
4. **Analyse the heap dump** (Eclipse MAT) — **the dominant object types name the cause.**

**The usual causes:**

- **Too many builds retained** (J7.4) — the object model holds every build record. **The most common cause on a large estate**, and the fix is retention.
- **Too many concurrent pipeline executions** (J1.1) — each holds CPS state.
- **A pipeline with heavy Groovy** (J2.11) — large collections in a `script` block, or a loop building a huge string.
- **A leaking plugin.**
- **A very large console log** being held in memory.
- **Heap simply too small** for the instance's size.

**The fixes, in order**: **aggressive build retention** (J7.4) — usually the biggest win; **move logic out of Groovy into shell scripts** (J2.11); **increase the heap** (J7.5), with the container-limit caveat; **remove suspect plugins** (J9.6); and **split into multiple controllers** (J7.9) if the instance is genuinely too large for one JVM.

**J8.4 — A workspace or disk space failure**

**The symptoms**: builds fail with "No space left on device"; **agents go offline automatically** (Jenkins' disk space monitor, J5.7); Jenkins becomes read-only or fails to save configuration; and **in the worst case, `config.xml` files are truncated by a write that ran out of space** — which is genuine corruption.

**The diagnosis:**

```bash
df -h
du -sh $JENKINS_HOME/* | sort -h | tail
du -sh $JENKINS_HOME/jobs/*/builds | sort -h | tail -20
du -sh /var/lib/jenkins-agent/workspace/* | sort -h | tail   # on agents
```

**Where it goes** (J7.4, J5.7): **archived artifacts** (J2.14), **build logs**, **orphaned multibranch jobs** (J4.5), **agent workspaces**, **Docker images and build cache on agents** (D6.7), and the update-centre cache.

**The immediate remediation**: delete old build records for the largest jobs; clean agent workspaces; prune Docker on agents (D6.6, carefully); and clear caches.

**The permanent fix:**

- **`buildDiscarder` on every job**, with a low artifact count (J2.9, J7.4) — **the highest-value change.**
- **`cleanWs()`** in `post { always }` (J5.7).
- **Orphaned item retention** (J4.5).
- **Artifacts to a registry**, not Jenkins (C3.5).
- **Disk monitoring with a predicted-full alert** (J7.10) — **so it's a ticket rather than an outage.**
- **Ephemeral agents** (J5.6), which removes the agent side entirely.

**J8.5 — A pipeline failing only on one agent**

**This is almost always agent drift** (J5.6) — the agents are not identical, and the build depends on something one of them lacks.

**The diagnosis:**

1. **Confirm it's agent-specific** — pin the job to each agent in turn (`agent { label 'agent-03' }`) and reproduce.
2. **Compare the environment** — run a diagnostic step on both: tool versions (`node -v`, `java -version`, `docker version`), `PATH`, `env`, installed packages, and disk space.
3. **Check the workspace** — a stale workspace on that agent with leftover state (J5.7). **`cleanWs()` and retry** — if that fixes it, it was workspace residue.
4. **Check the agent's configuration** — different tool installations, different environment variables set on the node, a different label set.
5. **Check the OS and architecture** — a heterogeneous fleet where one agent is a different distribution or arm64 (D1.9).
6. **Check resources** — a smaller agent hitting a memory or disk limit that others don't.

**The causes**: manually-installed tools that drifted; a build that modified the agent (J5.6); a different base image or AMI; a stale workspace; and a different Docker version or state.

**The structural fix, which is the answer to give**: **stop having pet agents.** **Ephemeral agents from a common image** (J5.3, J5.5) make every build identical by construction, and **running builds in containers** (J2.3's `docker` agent) makes the agent's own state irrelevant. **"It only fails on agent 3" is a symptom of a mutable-infrastructure problem** (A4.6), not a build problem.

**J8.6 — A shared library resolution failure**

**The symptoms**: `No such DSL method 'myStep'`, `Library X is not allowed`, `unable to resolve library`, or a `MissingPropertyException` on a library class.

**The causes:**

1. **The library isn't configured** — not defined globally (J3.4) or in the folder, so `@Library('name')` can't resolve it. **Check the name matches exactly.**
2. **The version doesn't exist** — `@Library('lib@v3.2')` with no such tag or branch (J3.5). **The error names the ref.**
3. **`allowVersionOverride` is disabled** and the Jenkinsfile specifies a version — so it's rejected.
4. **Credentials** — the library's repository isn't readable with the configured credential (J4.7).
5. **The step name doesn't match the filename** — `vars/buildAndPush.groovy` provides `buildAndPush`, and **case matters** (J3.2).
6. **Missing `def call()`** in the `vars` file, so the file loads and provides no invocable step.
7. **A compilation error in the library** — often reported obscurely; **the underlying error is in the log further up.**
8. **Sandbox rejection** (J2.12) for a non-trusted library using a restricted method — **the error is a `RejectedAccessException`, not a resolution failure**, and distinguishing them matters.
9. **`implements Serializable` missing** on a `src` class (J3.3) — a `NotSerializableException` at a later point, which looks unrelated.
10. **Caching** — Jenkins caches library checkouts; a force-refresh or a version change resolves a stale cache.

**The diagnostic**: **the build log's early lines show the library being loaded, from which repository, at which revision.** Reading that confirms whether resolution happened at all and which version was used — **which is the first thing to check** and it's frequently skipped.

**J8.7 — Reading Jenkins logs and thread dumps**

**The logs:**

- **`$JENKINS_HOME/logs/`** and the **system log** (Manage Jenkins → System Log) — the controller's own log, including startup, plugin loading (J7.3), and exceptions.
- **Custom log recorders** — configure a logger for a specific package at FINE/FINER level to debug a plugin without enabling debug globally. **The right way to get targeted detail.**
- **Per-agent logs** on the node's page (J5.8).
- **Build console output** — and `timestamps()` (J2.9) makes it far more useful for a slow build.

**Thread dumps** (`/threadDump`, or `jstack` against the process):

- **What they're for**: a hung or slow controller (J8.3) — **they show what every thread is doing right now.**
- **Reading them** (O9.5's method): **look for many threads in the same stack**, which indicates contention on a lock; **threads `BLOCKED` on a monitor** name the lock and the holder; **threads in a plugin's code** point at the plugin; and **a thread stuck in I/O** points at a network or disk problem.
- **Take several dumps seconds apart** — **a thread appearing in the same place across all of them is stuck; one that moves is just busy.** That comparison is the technique.
- **The Support Core plugin** bundles logs, thread dumps, system info, and configuration into a support bundle — **the right thing to generate before asking for help or filing an issue.**

**The habit**: **enable a targeted log recorder rather than reading everything**, and **take a thread dump before restarting a hung controller** — otherwise the evidence is gone.

**J8.8 — A webhook that isn't triggering builds**

**Work through it from the SCM outward:**

1. **Check the SCM's webhook delivery log.** **GitHub, Bitbucket, and GitLab all record every delivery with the request, the response code, and the body.** **This is the definitive first check** and it immediately tells you whether the problem is delivery or handling.
   - **No delivery attempt** → the webhook isn't configured, or the event type isn't subscribed.
   - **A delivery with a non-2xx response** → the problem is at Jenkins.
   - **A delivery with a 200** → Jenkins received it and chose not to build.
2. **Network path** — can the SCM reach Jenkins? **This is the usual answer for an internal Jenkins** (J4.4, J6.7): a firewall, no public route, or an IP allowlist not including the SCM's ranges.
3. **The URL** — `/github-webhook/` (trailing slash matters), `/bitbucket-hook/`, `/generic-webhook-trigger/invoke`. **A wrong path returns 404** and shows in the delivery log.
4. **Authentication** — some endpoints require a token or a shared secret; a mismatch returns 403.
5. **CSRF protection** — Jenkins' crumb requirement can reject a webhook if the endpoint isn't exempt.
6. **The job's trigger configuration** — for a pipeline, the trigger must be configured (or, for multibranch, indexing must be webhook-driven).
7. **Branch or path filters** (J4.1) excluding the change.
8. **No Jenkinsfile on that branch** (J4.3) — so no job exists to trigger.
9. **Jenkins received it and indexed but found nothing to build** — **the scan log** (J4.3) says why.

**The fallback**: **periodic indexing as a safety net** with a long interval — so a missed webhook delays a build rather than losing it, without the polling load (J4.4).

---

## J9. Judgement & migration

**J9.1 — Where Jenkins still wins over hosted CI**

**The honest answers, and being able to give them matters:**

- **Network access to anything.** **Jenkins runs where you put it** — inside a VPC, on-premises, in an air-gapped environment, behind a firewall with access to a mainframe. **Hosted CI requires either a public endpoint or self-hosted runners**, and at that point you're operating infrastructure anyway. **This is the strongest and most durable advantage.**
- **Flexibility and expressiveness.** **Groovy pipelines and shared libraries can express orchestration that YAML cannot** (GA10.8) — dynamic stage generation, complex conditional flows, genuinely reusable abstractions with real logic. **A large organisation with intricate delivery requirements can build things in Jenkins that would be painful elsewhere.**
- **The plugin ecosystem.** **Thousands of integrations**, including for old and niche systems that hosted CI will never support — a legacy artefact repository, a proprietary test tool, a specific hardware rig.
- **No per-minute cost.** At very high build volume, **self-hosted compute is cheaper than hosted minutes** (GA10.3) — though the operational cost frequently exceeds the saving (J9.2).
- **Full control of the environment** — exact tool versions, custom hardware, specific kernels.
- **Data residency and compliance** (S10.4) — builds run where you control (J9.2's counterweight applies).
- **It already exists.** **Not a technical advantage and a real one** — an estate with 800 jobs represents years of accumulated knowledge, and migration is a multi-quarter project (J9.5).

**The framing**: **Jenkins wins on control and flexibility; hosted CI wins on operational cost and security defaults.** For a greenfield service on GitHub, Actions is the right default (GA10.8). For a heterogeneous, on-premises, or highly-customised estate, Jenkins' flexibility can still be worth its cost — **and that judgement should be made explicitly rather than by inertia.**

**J9.2 — Total cost of ownership of self-hosted Jenkins**

**The costs people count**: controller and agent infrastructure.

**The costs they don't, and this is the item:**

- **Operational engineering time** — patching (J6.8), upgrades (J7.2), plugin management (J9.6), backup and restore testing (J7.1), capacity management (J7.10), and troubleshooting (J8). **Realistically 0.25–1 FTE for a significant estate**, and more during an upgrade or an incident.
- **On-call.** **Jenkins down blocks every team's delivery**, so it needs a response path — which means someone carrying it.
- **The security burden.** Advisories to triage, an internet-exposure decision to defend (J6.7), credential management (J6.9), and access reviews (J6.5). **This is the cost most underestimated**, and it's ongoing.
- **Expertise.** Jenkins-specific knowledge — Groovy, CPS (J2.13), the plugin ecosystem — that is **increasingly scarce and doesn't transfer.** **Hiring for it is genuinely harder than it was**, and that's a real risk.
- **Downtime cost** — every hour Jenkins is down, no team ships (J7.9).
- **The opportunity cost** — the same engineers could be building something that differentiates the business.
- **Migration debt** — the longer you stay, the more accumulated pipeline logic must eventually move (J9.5).

**The comparison to make**: **hosted CI's per-minute cost is visible and its operational cost is near zero; Jenkins' infrastructure cost is visible and its operational cost is large and hidden.** **Compare total cost including engineering time**, and for most organisations the hosted option is cheaper once that's counted — **which is the argument for J9.5, made with numbers** (C11.7).

**J9.3 — Assessing an inherited Jenkins estate**

**This is the most likely real scenario and the most valuable item in the domain.** The assessment, ordered by risk:

**1. Security — first, because the exposure is immediate:**
- **Is it internet-exposed?** (J6.7)
- **What's the authorisation strategy?** "Anyone can do anything" or "logged-in users can do anything" (J6.4)?
- **Who has `Overall/Administer`?** (J6.5, J7.11) — usually far too many.
- **Are there known-vulnerable plugins?** The plugin manager flags them (J6.8).
- **What's in the script approval list?** (J6.6) — usually alarming.
- **Are credentials global rather than folder-scoped?** (J6.2)
- **Do builds run on the controller?** (J1.2)

**2. Continuity:**
- **Is there a backup, and has a restore been tested?** (J7.1) — **usually no.**
- **Could you rebuild this instance if it disappeared?** (J7.8)
- **What's the RTO if it's down?** (J7.9)

**3. Operational health:**
- **Disk headroom and retention policies** (J7.4, J8.4).
- **Version currency** — core and plugins (J6.8).
- **Queue time and executor utilisation** (J7.10).
- **Is anything monitored at all?**

**4. Estate composition:**
- **How many jobs, and what proportion are freestyle** (J1.5) versus pipeline?
- **Which jobs actually run?** — **a large fraction are usually dead**, and deleting them is the cheapest improvement.
- **Plugin count and how many are actually used** (J9.6).
- **Is there a shared library, and is it versioned and tested?** (J3.5, J3.7)

**The prioritisation**: **fix the security exposure and the backup first** — those are the things that turn into an incident. **Then operational stability (disk, retention, patching). Then modernisation** (J9.4). **And resist the urge to start with the interesting work** — migrating freestyle jobs is more appealing than testing a restore, and it's the wrong order.

**J9.4 — Migrating freestyle jobs to pipeline as code**

**The approach:**

1. **Inventory and triage.** **How many jobs, and which actually run?** **Delete the dead ones first** — typically a large fraction, and it's free progress that shrinks the problem.
2. **Group by pattern.** Most estates have a handful of shapes — "build a Java service", "run a script on a schedule", "deploy to environment X" — repeated many times. **Migrate by pattern, not job by job.**
3. **Build the shared library** for the common pattern (J3.2, J3.8), so migrating a job becomes writing a short Jenkinsfile.
4. **Start with a low-risk, representative job.** Prove the pattern, get the library right, learn what's missing.
5. **Run in parallel.** **Keep the freestyle job and add the pipeline job**, comparing results, until confidence is established. **Don't delete the old one first.**
6. **Migrate the common patterns**, which is the bulk of the count.
7. **Leave the long tail.** **There will be strange, one-off jobs where migration costs more than it saves** — and **the honest answer is to leave some of them**, or delete them if they're not genuinely needed.
8. **Prevent regression** — new jobs must be pipelines; disable freestyle job creation where possible.

**The realistic framing to state:**

- **This is a multi-quarter project** for a large estate, and **it competes with feature work** — so it needs a case (C11.7) framed around risk and delivery speed, not tidiness.
- **The value is not "pipelines are nicer"** — it's version control, review, reproducibility, and reusability (J1.5).
- **Migrating 80% and stopping is a legitimate outcome.** The last 20% is often not worth it, and pretending otherwise makes the project fail (J9.5's argument).

**J9.5 — Migrating from Jenkins to another CI incrementally**

**The principle: never a big-bang cutover.** An estate with hundreds of jobs cannot be moved atomically, and attempting it fails.

**The sequence:**

1. **Make the case with numbers** (J9.2, C11.7) — total cost of ownership, security exposure, delivery speed, and the hiring risk. **Without a case, it gets deprioritised every quarter.**
2. **Stand up the target alongside**, and **prove it on a new service first** — greenfield, low risk, and it establishes the patterns without migration complexity.
3. **Build the target's equivalent of your shared library** (C2.6) — reusable workflows and composite actions (GA5.5, GA5.7). **This is the prerequisite for migrating at volume.**
4. **Migrate by team or by domain**, not by job type, so a team's whole world moves together and they have one system to learn.
5. **Run both in parallel** during each team's migration, comparing results.
6. **Freeze the old system** — no new Jenkins jobs, so the problem stops growing.
7. **Handle the hard cases explicitly** — the jobs needing network access Jenkins has and the target doesn't (J9.1). **Self-hosted runners** (GA8.2) usually solve them; **and a residual Jenkins for a handful of genuinely stuck jobs is an acceptable outcome** rather than a failure.
8. **Decommission** only when the last real job has moved, and **keep a read-only Jenkins** for build history until the retention period lapses.

**The realities to name:**

- **It takes longer than planned** — every estate has surprises.
- **The long tail dominates.** 80% moves quickly; the last 20% is where the project stalls, and **planning for a permanent residue is more honest than assuming zero.**
- **You need both operational for a long period**, which is a temporary cost increase.
- **Build history doesn't migrate** — accept it, or export what's needed for compliance (C10.8).

**J9.6 — Reducing plugin sprawl safely**

**Why it matters** (J1.8, J6.8): every plugin is arbitrary code in the controller's JVM, a CVE surface, an upgrade constraint, and a potential conflict (J7.3).

**The method:**

1. **Inventory** — the plugin manager lists installed plugins, versions, and **which are dependencies of others.** Export it.
2. **Identify candidates**: **plugins with no known usage**; **plugins marked deprecated or unmaintained** (Jenkins flags these); **plugins with open security advisories and no fix**; and **duplicates** — two plugins doing the same thing, which accumulates over years.
3. **Determine actual usage** — **this is the hard part.** Options: search job configurations and Jenkinsfiles for the plugin's steps (`grep` across `$JENKINS_HOME/jobs/*/config.xml`); the **Plugin Usage plugin**, which reports which jobs use which; and **the dependency graph**, so you don't remove something another plugin needs.
4. **Remove in small batches**, one category at a time.
5. **Disable before uninstalling** — **Jenkins lets you disable a plugin and restart.** **If nothing breaks over a week, uninstall.** **This is the safe path** and it's the equivalent of soft-delete (DB7.6, A10.7).
6. **Take a backup first** (J7.1), so a mistake is recoverable.
7. **Verify** — run a representative set of jobs after each batch.

**The cautions:**

- **Removing a plugin can orphan configuration** — a job referencing a removed plugin's step fails, and the job's `config.xml` may lose data on save.
- **Dependencies** — removing something another plugin needs breaks it (J7.3).
- **Do it during a quiet period**, not before a release.

**The prevention**: **a policy that adding a plugin requires justification and review** — the same argument as an action allowlist (GA5.9), because it's the same supply chain decision (S7.1).

**J9.7 — Standardising pipelines across many teams**

**The mechanisms, in increasing order of constraint:**

1. **A shared library** with well-designed steps (J3.2, J3.8) — teams call `buildAndPush()` and get the standard behaviour, and they write their own Jenkinsfile around it. **The paved road** (C12.4).
2. **Organisation folders** (J1.4) — automatic onboarding: a team adds a Jenkinsfile and their pipeline appears, with folder-level credentials (J6.2) and permissions (J6.5) already configured.
3. **A template Jenkinsfile** in a service template repository, so new services start correct.
4. **JCasC and Job DSL** (J7.6, J7.7) for the system and job configuration.
5. **A library-provided full pipeline step** (`standardPipeline { }`) — **maximum standardisation, and it's where the framework problem starts** (J3.8).

**What makes it work rather than being resented:**

- **The standard path must be genuinely easier** than doing it yourself (C12.4, TF13.5). **If writing your own pipeline is faster, standardisation fails regardless of policy.**
- **Escape hatches** — a team needing something the library doesn't do writes plain pipeline code alongside it. **Blocking that is what causes forks.**
- **Open contribution** — a PR to the library, not a ticket to the platform team (C12.3, TF8.8).
- **Readable Jenkinsfiles** (J3.8) — a reader should see what the build does.
- **Versioned, so teams adopt changes deliberately** (J3.5).
- **Golden path, not mandate** (C12.4) — compliance as a by-product of convenience.

**What to genuinely mandate**: the security baseline — credential handling (J6.2), no builds on the controller (J1.2), retention policies (J7.4), and required scanning. **Put the mandate inside the golden path** so following the easy route satisfies it automatically (S9.4).

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 81 items this is the smallest domain in the matrix, and if you've operated Jenkins much of J1 and J2 will be familiar.
- **J9.3 is the item most worth rehearsing.** **Jenkins in 2026 is largely a legacy-estate skill**, and the realistic interview question is "you've inherited this — what do you do", not "how would you build it". The ordered assessment — security exposure, then continuity, then operational health, then modernisation — with the explicit note about resisting the interesting work first, is the answer that reads as experience.
- **The Jenkins-specific traps are J2.12, J2.13, J6.6, and J7.11** — the Groovy sandbox, CPS serialisation, script approval as privilege escalation, and the script console. **These don't transfer from other CI systems**, so they're where someone who has actually run Jenkins is distinguishable. **A `NotSerializableException` recognised immediately as CPS is a strong signal.**
- **J9.1 rewards arguing a position you may not hold.** Where Jenkins still wins — network reach, expressiveness, the plugin ecosystem, and the honest "it already exists" — is a test of whether you can be fair to a tool you'd migrate away from.
- **The mechanisms that read as experience**: `input` inside a stage with an agent holding an executor for hours and deadlocking the instance (J2.8); `beforeAgent true` preventing pointless agent provisioning for skipped stages (J2.5); the parameter first-run problem (J2.7); polling exhausting the GitHub API rate limit (J4.4); and `artifactNumToKeepStr` being the setting that actually controls disk (J2.9, J7.4).
- **Cross-references are dense into CI/CD and Security** — C2 for pipeline design, C10 for governance, S6 and S7 for secrets and supply chain, and GA for the direct comparison in J9.1 and J9.5. This domain is the tool; those are the practice.
