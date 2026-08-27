# Kubernetes — Answer Key

Companion to Domain 8 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **EKS-specific configuration is A5.5–A5.8** (managed node groups, the load balancer controller, VPC CNI IP exhaustion, cluster auth), **image and supply-chain security is S7**, **container internals are D1**, and **cert-manager is S4.8**. Where a topic sits on the boundary, the answer points rather than repeats.

Two observations about how this domain is interviewed, worth holding while you read:

- **The debugging section (K9) is where most interviews actually go.** Everyone can describe a Deployment. Far fewer can walk `CrashLoopBackOff` to root cause without guessing, or explain why a Service returns nothing when the pods are healthy. If you're triaging prep time, K9 and K6 repay it fastest.
- **The design-judgement section (K13) is what separates senior from mid.** The distinguishing answer to most K13 items includes the case *against* the thing you're being asked about — and being willing to say "we shouldn't have used Kubernetes for that" is a strong signal rather than a weak one.

---

## K1. Architecture & control plane

**K1.1 — Control plane components**

- **kube-apiserver** — the front door. Validates and authenticates every request, and is the only component that talks to etcd. Everything else, including the other control plane components, goes through it.
- **etcd** — the datastore. Holds all cluster state as the single source of truth (K1.2).
- **kube-scheduler** — assigns pending pods to nodes based on constraints and resources (K1.6).
- **kube-controller-manager** — runs the built-in controllers (Deployment, ReplicaSet, Node, Job, endpoint controllers) as reconciliation loops (K1.4).
- **cloud-controller-manager** — the cloud-specific half: provisioning load balancers, attaching volumes, managing node lifecycle against the provider's API. Split out from the controller manager so cloud logic doesn't live in core.

On each node: **kubelet** and the **container runtime** (K1.7), plus **kube-proxy** (K1.8).

The structural point worth making rather than just listing: **the control plane components don't talk to each other.** The scheduler doesn't call the kubelet; it writes a binding to the API server, and the kubelet notices. All coordination is mediated through the API server and etcd, which is why the API server is the availability-critical component and why the architecture is described as a shared-state, level-triggered system rather than a message-passing one.

**K1.2 — etcd, and why its backup matters most**

etcd is a distributed, consistent key-value store using Raft. It holds **every object in the cluster** — Deployments, Secrets, ConfigMaps, RBAC, CRDs, and the current status of everything.

Why its backup matters more than anything else: **lose etcd and you have lost the cluster, not just its data.** Nodes keep running their existing pods for a while, but nothing can be scheduled, changed, or recovered, and the declarative state describing what should exist is gone. Every other component is stateless and rebuildable from etcd; etcd is rebuildable from nothing.

The operational facts:

- **Raft requires a quorum**, so members are deployed in odd numbers (3 or 5). Losing quorum makes the cluster read-only at best and unrecoverable at worst — a two-member cluster is worse than one, because it can lose quorum from a single failure.
- **Back up with `etcdctl snapshot save`**, on a schedule, stored off-cluster. A backup on the same nodes protects against nothing.
- **Test the restore** (see A11.8 for the general argument). An untested etcd restore is the most consequential untested procedure in a self-managed cluster.
- **etcd is latency-sensitive to disk fsync.** Slow disks are the classic cause of a mysteriously unresponsive control plane — the API server times out, leader elections flap, and everything looks broken with no obvious cause. Fast SSDs are a hard requirement, not an optimisation.
- **Secrets are stored in etcd, base64-encoded not encrypted, by default** (K3.4) — so an etcd snapshot is a full credential dump, and must be treated and encrypted accordingly.

The nuance for managed clusters: **on EKS/GKE/AKS, the provider owns etcd and its backup** (K1.10). That does not mean your cluster state is backed up in a way that helps you — provider backup protects the control plane's availability, not your ability to recover from someone deleting a namespace. Which is the argument for GitOps (K10.7) and for Velero (K11.6).

**K1.3 — The API server as the single point of interaction**

Every interaction — `kubectl`, controllers, the kubelet, operators, the scheduler — goes through the API server. It handles **authentication** (who are you), **authorisation** (RBAC, K8.1), **admission control** (mutating then validating webhooks, K8.8), **validation** against the schema, and then **persistence** to etcd.

Why the design matters:

- **It's the single enforcement point.** RBAC, admission policy, and audit logging (K8.13) are all effective precisely because there's no way around them. A component that talked to etcd directly would bypass every control.
- **It's the single point of *interaction*, and on a managed cluster it's also the availability boundary.** If the API server is down, existing pods keep serving traffic — this is important and often misunderstood — but nothing can be deployed, scaled, rescheduled, or recovered. Degraded rather than dead, but you've lost self-healing at the moment you might need it.
- **It exposes a watch mechanism**, and that's what makes the controller pattern work efficiently: clients watch for changes rather than polling.
- **It's a rate-limited shared resource.** A badly-behaved controller or operator hammering the API server degrades the whole cluster, and API priority and fairness exists to contain that. A cluster that becomes slow after installing a third-party operator is a real and recurring pattern (K12.3).

**K1.4 — The controller pattern and reconciliation**

A controller watches the desired state of some resource, observes the actual state of the world, and takes action to close the gap. Then it does it again. Forever.

```
for {
  desired := getDesiredState()
  actual  := getActualState()
  reconcile(desired, actual)
}
```

The properties that follow, which are what's being probed:

- **It's level-triggered, not edge-triggered.** The controller acts on the *current* difference between desired and actual, not on an event describing a change. So a missed event doesn't cause permanent divergence — the next reconciliation catches it. This is why Kubernetes is resilient to controllers restarting, to network blips, and to lost messages, and it's the single most important architectural idea in the system.
- **Reconciliation must be idempotent.** Running it twice against the same state does nothing the second time.
- **It's eventually consistent.** There's a window where actual and desired differ, and that's normal rather than a fault. "It hasn't happened yet" is a legitimate state.
- **Controllers compose without coordination.** The Deployment controller creates ReplicaSets; the ReplicaSet controller creates Pods; the scheduler binds them; the kubelet runs them. None of them knows about the others — they each watch their own resource and act. That's how the system extends cleanly to CRDs and operators (K12.2).

**K1.5 — Declarative vs imperative, and how it changes operations**

**Imperative** — you issue commands describing actions: `kubectl run`, `kubectl scale`, `docker run`. **Declarative** — you submit a description of the desired end state and a controller works out the actions: `kubectl apply -f`.

What changes operationally, which is the point of the item:

- **The manifest is the source of truth, not the cluster.** Which makes the manifests version-controllable, reviewable, and diffable — and is the precondition for GitOps (K10.7).
- **Self-healing is free.** Kill a pod and it comes back, because desired state still says three replicas. Nobody wrote recovery logic; it's the reconciliation loop (K1.4).
- **Drift is detectable**, because there's a declared state to compare against.
- **You describe outcomes, not sequences**, so operations become idempotent and re-runnable. Re-applying a manifest is safe; re-running a shell script often isn't.

The practical consequences people learn the hard way:

- **Imperative changes get silently reverted** — or worse, persist until something else reconciles and then vanish mysteriously. `kubectl scale` a Deployment that ArgoCD manages and it snaps back, which is correct behaviour that looks like a bug.
- **`kubectl apply` uses a last-applied-configuration annotation** (or, now, server-side apply with field ownership) to work out what to remove. Objects created with `create` and later `apply`d behave surprisingly, and fields you removed from your manifest may not be removed from the object if something else claims ownership.
- **Deleting a field is not the same as setting it to a default**, and this catches people during upgrades.

The mature framing: **the declarative model means your job shifts from performing operations to specifying intent and debugging why reconciliation didn't achieve it.** Most Kubernetes debugging is answering "what is stopping the controller from reaching desired state" (K9.6 and K6.13 are that question in specific forms).

**K1.6 — What the scheduler does and doesn't do**

**Does**: for each pending pod, **filter** nodes to those that could run it (sufficient allocatable resources against the pod's *requests*, node selectors and affinity, taints and tolerations, volume zone constraints, port availability), then **score** the feasible nodes (spread, resource balance, affinity preferences, image locality) and bind the pod to the winner by writing the binding to the API server.

**Doesn't**, and this is the substance of the item:

- **It doesn't start containers.** It writes a binding; the kubelet on the chosen node does the work (K1.7). A pod bound to a node but not running is a kubelet or runtime problem, not a scheduling one — and distinguishing those is a real diagnostic step.
- **It doesn't move running pods.** Scheduling is a one-time decision. If the cluster becomes unbalanced, or a better node appears, nothing rebalances it — the pod stays until something else evicts it. This surprises people constantly. Rebalancing needs the descheduler or a node lifecycle tool like Karpenter's consolidation (K7.6).
- **It doesn't consider actual usage, only requests.** A node whose pods request 4 CPU but use 0.2 is full as far as the scheduler is concerned, and a node whose pods request 0.1 but use 15 is empty. This is why requests are the single most consequential number in a manifest (K6.1, K6.5).
- **It doesn't create nodes.** No capacity means the pod stays Pending until Cluster Autoscaler or Karpenter reacts (K7.5, K7.6).
- **It doesn't guarantee the decision stays valid.** Node conditions change after binding; that's what eviction is for (K6.11).

**K1.7 — kubelet and container runtime**

**kubelet** is the node agent. It watches the API server for pods bound to its node, and then: pulls images via the runtime, creates and starts containers, mounts volumes, runs **probes** (K9.10) and acts on the results, reports node and pod status back to the API server, and enforces eviction when the node is under pressure (K6.11).

**The container runtime** (containerd, CRI-O) does the actual container work via the **CRI** interface: image management, and creating containers via an OCI runtime (runc) using namespaces and cgroups (D1).

The points that matter operationally:

- **The kubelet is the last mile, and it's where "the pod won't start" problems live** — image pull failures, volume mount failures, probe failures. `kubectl describe pod` Events are largely kubelet output (K9.2), which is why that's the first command in nearly every diagnosis.
- **A node whose kubelet stops reporting goes `NotReady`**, and after a grace period the node controller marks its pods for eviction — but **pods on an unreachable node may still be running**, which is the source of split-brain concerns for StatefulSets (K2.8) and why forcibly deleting such a pod is dangerous.
- **Dockershim removal**: Kubernetes talks to runtimes via CRI, and Docker was removed as a directly-supported runtime in 1.24. Practically nothing changed for users — images are OCI images regardless — but it's a favourite interview question, and the correct answer is that Docker-built images run fine because the image format is standard.
- **The kubelet enforces limits via cgroups**, which is why memory limits are fatal and CPU limits are throttling (K6.2, K6.3).

**K1.8 — kube-proxy, and what replaced it**

kube-proxy implements Service networking on each node. It watches Services and EndpointSlices and programs the node's packet-handling rules so that traffic to a Service's ClusterIP is DNAT'd to one of the backing pod IPs.

Modes: **iptables** (the long-standing default — a chain of rules with random selection; correct, but rule evaluation is O(n) and reprogramming the whole table on endpoint churn becomes slow in large clusters), and **IPVS** (kernel load balancing with hash tables, better scaling and real balancing algorithms).

**What replaced it**: **eBPF-based dataplanes** — Cilium's kube-proxy replacement, and Calico's eBPF mode. Instead of iptables rules, service load balancing is done in eBPF programs attached at the socket or driver level. The wins: **O(1) lookup regardless of service count**, lower latency, no iptables rule explosion, better observability, and direct server return options. Cilium can run without kube-proxy entirely.

The framing that shows you understand the *why*: **kube-proxy's problem is scaling, not correctness.** At a few hundred services it's fine and invisible. At thousands of services with high pod churn, iptables reprogramming becomes a measurable source of latency and delayed endpoint updates — traffic goes to pods that are already terminating because the rules haven't caught up. That's the failure mode that drives migration, and it's an argument you make with a service count and a churn rate, not with a preference.

**K1.9 — The full lifecycle of `kubectl apply`**

1. **kubectl** resolves the context and credentials from kubeconfig, converts the YAML to JSON, and POSTs/PATCHes to the API server.
2. **Authentication** — certificate, bearer token, or an exec plugin (`aws eks get-token`, A5.8).
3. **Authorisation** — RBAC evaluates whether this subject may perform this verb on this resource in this namespace (K8.1).
4. **Admission** — **mutating** webhooks first (defaulting, sidecar injection, adding labels), then schema validation, then **validating** webhooks (policy engines, K8.9). Any rejection ends it here.
5. **Persistence** — the object is written to etcd. **At this point `kubectl` returns success.** That's the crucial detail: `configured` means "accepted and stored", not "running".
6. **The Deployment controller** notices a Deployment without a matching ReplicaSet and creates one.
7. **The ReplicaSet controller** notices a ReplicaSet with fewer pods than desired and creates Pod objects — with no node assigned.
8. **The scheduler** watches for unbound pods, filters and scores nodes, and writes a binding (K1.6).
9. **The kubelet** on that node sees a pod bound to it: pulls the image, sets up the network via CNI (K4.2), mounts volumes via CSI (K5.8), and starts containers.
10. **Probes** run; when readiness passes, the endpoint controller adds the pod IP to the Service's EndpointSlice (K4.4), and kube-proxy or the dataplane programs the node so traffic reaches it (K1.8).

Why this is worth being able to walk: **it's a diagnostic map.** A failure at each stage looks different — rejected at admission (immediate error from kubectl), Pending (stage 8, scheduling — K9.6), ImagePullBackOff (stage 9, kubelet — K9.5), CrashLoopBackOff (stage 9, container — K9.4), running but no traffic (stage 10, readiness or Service — K9.9). Being able to say "the pod is Running so we're past scheduling and image pull, which leaves probes and Service wiring" is the shape of a competent answer to almost every Kubernetes debugging question.

**K1.10 — Managed control planes: what the provider owns vs what you own**

**The provider owns**: API server, etcd (including its backup and quorum), scheduler, controller manager — their availability, patching, and scaling. Usually with an SLA on API server availability.

**You own**: nodes (their AMIs, patching, scaling, and lifecycle unless you're on a fully-managed compute option), **all workloads**, networking configuration (CNI choice and its config, NetworkPolicy), storage (CSI drivers and StorageClasses), **RBAC and everything inside the cluster**, add-ons and their compatibility (K11.9), **the upgrade decision and its timing** (K11.1), and observability.

The misconceptions worth correcting explicitly:

- **"Managed" does not mean "backed up".** The provider protects control plane availability; it does not give you a restore point for your cluster's contents. Delete a namespace and the provider cannot help you. That's your problem, solved by GitOps (K10.7) plus Velero (K11.6).
- **Upgrades are still your project.** The provider makes the new version available and eventually forces the issue with end-of-support, but working out whether your workloads and add-ons survive it is entirely yours (K11.3, K11.9).
- **You still need to understand the control plane**, even though you don't run it — API throttling, etcd object size limits, and audit configuration all surface as your problems.
- **The API server's availability is now a dependency you don't control**, which belongs in a resilience review the same way KMS quotas do (A10.15, A11.9).

The honest framing for a build-vs-buy question: managed control planes remove the single hardest and most consequential operational burden (etcd) for a modest per-cluster fee, and self-managing a control plane is very difficult to justify unless you have a specific requirement — air-gapped environments, unusual API server configuration, or regulatory constraints on where state lives.

---

## K2. Workloads

**K2.1 — A Pod spec, and why you rarely create bare pods**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api
spec:
  containers:
    - name: api
      image: registry.example.com/api:1.4.2
      ports:
        - containerPort: 8080
      resources:
        requests: { cpu: 100m, memory: 256Mi }
        limits:   { memory: 512Mi }
```

A pod is one or more containers sharing a network namespace (so they reach each other on `localhost` and share one IP) and able to share volumes. It's the smallest schedulable unit.

**Why you rarely create bare pods**: a bare pod has no controller behind it, so **nothing recreates it.** If the node fails, or it's evicted, or it exits, it's simply gone — there's no reconciliation loop with a desired state saying it should exist (K1.4). You also lose rolling updates, rollback, and scaling, because those are Deployment behaviours.

Legitimate uses of bare pods: a one-off debugging pod, and ephemeral debug containers (K9.12). Everything else gets a controller — Deployment, StatefulSet, DaemonSet, or Job.

The related design point: **multiple containers in one pod is for tightly-coupled helpers, not for co-locating services.** They scale together, they're scheduled together, and they share a lifecycle and a network namespace. If two things could sensibly scale independently, they're two pods.

**K2.2 — Pod lifecycle phases and container states**

**Pod phases**: `Pending` (accepted but not all containers running — includes both waiting to be scheduled and pulling images), `Running` (bound, and at least one container running), `Succeeded` (all containers exited 0 and won't restart), `Failed` (all terminated, at least one non-zero), `Unknown` (state can't be obtained, usually a node communication failure).

**Container states**, which are more diagnostically useful than the phase: `Waiting` (with a **reason** — `ContainerCreating`, `ImagePullBackOff`, `CrashLoopBackOff`), `Running`, `Terminated` (with an **exit code** and reason — `Completed`, `Error`, `OOMKilled`).

**Conditions** on the pod are the third layer and the one people ignore: `PodScheduled`, `Initialized`, `ContainersReady`, `Ready`.

The point to make: **`Pending` is ambiguous and the phase alone tells you almost nothing.** A pod can be Pending because it can't be scheduled (K9.6), because it's pulling a large image, or because a volume won't attach (K5.9). The answer is always in `kubectl describe` Events and in the container state's reason field (K9.2) — the phase is a summary, the reason is the diagnosis.

Also worth knowing: **`Running` does not mean `Ready`.** A pod can be Running and receiving no traffic because readiness fails, which is exactly the K9.9 scenario, and the `READY 0/1` column in `kubectl get pods` is where you see it.

**K2.3 — Init containers**

Init containers run **to completion, in order, before any app container starts**. If one fails, the pod restarts it according to the restart policy; app containers never start until all inits succeed.

Real use cases:

- **Waiting for a dependency** — blocking until a database is reachable or a migration has completed, so the app doesn't start into a failure loop.
- **Running a schema migration** exactly once before the app comes up (with the caveat that this runs per pod, so the migration must be idempotent or gated by a lock).
- **Fetching configuration or secrets** into a shared `emptyDir` — cloning a config repo, pulling a certificate.
- **Setting kernel parameters or file permissions** with elevated privileges, so the app container itself can run unprivileged (K8.7). This is the cleanest use: the privileged work is isolated to a short-lived container with a different securityContext.

The properties that matter: init containers can have **different images and different security contexts** from the app containers, which is the point. They **run on every pod restart**, so they must be idempotent and fast — a slow init container multiplies across every scale-out and every node replacement. And a failing init container shows as `Init:CrashLoopBackOff` or `Init:Error`, with logs retrieved via `kubectl logs pod -c init-container-name`, which people forget and then report "no logs".

**K2.4 — Sidecars, and the native sidecar change**

A sidecar is a helper container alongside the app in the same pod: log shippers, service mesh proxies, metrics exporters, secret refreshers, and cloud SQL proxies.

**The native sidecar change** (stable from 1.29) is the substance of this item. Historically sidecars were just ordinary containers in the pod, which caused two well-known problems:

1. **Startup ordering** — the app container could start before the mesh proxy was ready, so its first outbound calls failed. Everyone worked around this with retry logic or init-container hacks.
2. **Shutdown and Jobs** — regular containers don't terminate until told, so a Job whose main container completed would **hang forever** because the sidecar kept running and the pod never reached `Succeeded`. This was a genuinely notorious problem, worked around by having the app curl the proxy's shutdown endpoint.

Native sidecars are implemented as **init containers with `restartPolicy: Always`**. That gives them: **started before app containers and kept running** for the pod's life, **terminated after the app containers** on shutdown, and **not counted for Job completion**. All three problems solved by the ordering guarantees of the init container sequence.

Naming this change is a good currency signal, because plenty of people's mental model is still the old one, along with the workarounds it required.

**K2.5 — Deployments and the ReplicaSet relationship**

A Deployment manages ReplicaSets; a ReplicaSet manages Pods. **The Deployment doesn't create pods** — that indirection is what makes rolling updates and rollback possible.

On an update to the pod template, the Deployment controller **creates a new ReplicaSet** and gradually scales it up while scaling the old one down (K2.6). The old ReplicaSet is kept at zero replicas rather than deleted, which is what rollback uses (K2.7) — `revisionHistoryLimit` controls how many are retained.

Details that come up:

- **Only changes to the pod template trigger a rollout.** Changing `replicas` scales the existing ReplicaSet; changing an annotation on the Deployment itself does nothing. This is exactly why the checksum-annotation pattern exists for config changes (K3.3) — the change has to land *in the template* to cause a rollout.
- **The selector is immutable** after creation, which means changing labels requires recreating the Deployment. This bites during refactors and is a genuinely annoying constraint.
- **`kubectl rollout status`** blocks until the rollout completes or the progress deadline expires, which is what you use in CI to gate a deploy.
- **A stuck rollout** where the new ReplicaSet can't become ready is the common failure — and the Deployment will sit there indefinitely (subject to `progressDeadlineSeconds`) with old pods still serving. That's correct and safe behaviour, but it means "the deploy succeeded" from the pipeline's perspective can coexist with "nothing new is running".

**K2.6 — Rolling update: maxSurge, maxUnavailable, and consequences**

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 25%          # extra pods allowed above desired
    maxUnavailable: 25%    # pods allowed to be unavailable
```

The consequences, which is what's being asked:

- **`maxUnavailable: 0` with `maxSurge: 1`** — never dips below capacity. New pod comes up and becomes ready before an old one goes. Safest, slowest, and **requires spare cluster capacity** for the extra pod, so it can deadlock on a full cluster.
- **`maxSurge: 0` with `maxUnavailable: 1`** — never exceeds the replica count. Uses no extra capacity but **runs at reduced capacity during the rollout**, which matters if you're already near saturation.
- **Both non-zero** — faster, with a window at reduced capacity.

The practical judgement:

- **Percentages of small replica counts round in ways that surprise people.** 25% of 2 replicas rounds `maxUnavailable` down to 0 and `maxSurge` up to 1, which is usually what you want but is worth verifying rather than assuming.
- **The rollout only proceeds as readiness allows**, so a slow-starting app makes rollouts long. Combined with `maxUnavailable: 0` on a large Deployment, a rollout can take a very long time — and if you're rolling during an incident, that matters.
- **Rolling updates mean two versions run simultaneously.** That's a real constraint on schema changes and API compatibility: the new version must work with the old schema and the old version must tolerate the new one. This is the point most people miss, and it's the reason expand/contract migrations exist (see the Databases domain).
- **`minReadySeconds`** guards against a pod that passes readiness and then immediately falls over, by requiring it to stay ready before counting as available.

**K2.7 — Rollback and revision history**

```bash
kubectl rollout history deployment/api
kubectl rollout history deployment/api --revision=3
kubectl rollout undo deployment/api
kubectl rollout undo deployment/api --to-revision=3
kubectl rollout pause deployment/api      # halt mid-rollout to observe
kubectl rollout resume deployment/api
```

How it works: each revision corresponds to a retained ReplicaSet (K2.5); rollback scales the old one up and the current one down, which is another rolling update in reverse.

The caveats that matter:

- **`revisionHistoryLimit` defaults to 10.** Beyond that, old ReplicaSets are pruned and those revisions are unrecoverable.
- **`kubectl rollout history` shows little useful detail** unless you set `kubernetes.io/change-cause` (via `--record`, now deprecated, or an annotation in your manifests). Revisions listed as `<none>` are hard to choose between under pressure.
- **Rollback only reverts the pod template.** It does not revert ConfigMaps, Secrets, CRDs, or database migrations — so if the deploy included a schema change, rolling back the Deployment may leave a running old version against a new schema. **This is the most important thing to say**: rollback is a Kubernetes operation, not a system-wide undo, and treating it as one is how a rollback makes an incident worse.
- **In a GitOps model, `kubectl rollout undo` is drift** and will be reverted by the sync controller (K10.9). The correct rollback is a git revert, which is slower under pressure — worth having thought about before the incident, because reaching for kubectl during an outage against an auto-syncing ArgoCD produces confusing behaviour.

**K2.8 — When a StatefulSet is required**

StatefulSets provide three things Deployments don't:

1. **Stable network identity** — pods are named ordinally (`db-0`, `db-1`) and keep that name across rescheduling, with a stable DNS record via a headless Service (K4.5).
2. **Stable storage** — each pod gets its own PVC from `volumeClaimTemplates` (K5.5), and the same pod ordinal reattaches to the same volume after rescheduling.
3. **Ordered, graceful deployment and scaling** — pods are created 0, 1, 2 and terminated in reverse, with each waiting for the previous to be Ready.

**When it's required**: clustered systems where members must find each other by stable address and where each member owns specific data — databases with replication, Kafka, Elasticsearch, ZooKeeper, etcd itself. The distinguishing requirement is that **the pods are not interchangeable.**

The honest caveats:

- **A StatefulSet does not make an application stateful-safe.** It provides identity and storage primitives; the clustering, leader election, and replication are the application's problem. Running Postgres in a StatefulSet gives you a pod with a stable volume, not high availability — that needs an operator (K12.2) or a managed service (K13.8).
- **Ordering makes rollouts slow**, and a stuck pod blocks the whole sequence.
- **Scaling down does not delete PVCs** by default, which is a deliberate safety property that surprises people when they scale back up and find old data (and when they see the storage bill).
- **`podManagementPolicy: Parallel`** removes the ordering if you only need identity and storage, which is often the case.
- **Deleting a pod on an unreachable node is dangerous** — the pod may still be running, and forcing deletion can produce two pods with the same identity writing to the same data. Force-deleting StatefulSet pods is genuinely one of the more dangerous routine commands.

**K2.9 — DaemonSets**

Runs one pod on every node (or every node matching a selector), and automatically places one on any new node that joins.

Typical uses: **log collectors** (Fluent Bit), **metrics agents** (node-exporter, the CloudWatch agent), **CNI plugins** and kube-proxy itself, **CSI node drivers**, **security agents**, and node-level tooling like NodeLocal DNSCache (A3.6).

The operational points: DaemonSets usually need **tolerations for all taints** including control-plane taints, or they'll skip exactly the nodes you most want monitored (K6.7) — this is the classic DaemonSet mistake. They consume resources on **every** node, so a DaemonSet requesting 500m CPU costs 500m × node count, which is a significant and easily-overlooked overhead on a large cluster. Their updates use `updateStrategy: RollingUpdate` with `maxUnavailable`, and rolling a DaemonSet across a thousand nodes needs care. And **they don't run on Fargate** (A5.5), which is the main reason Fargate profiles are awkward — no log agent, no metrics agent, so everything must be a sidecar.

**K2.10 — Jobs and CronJobs**

```yaml
apiVersion: batch/v1
kind: Job
spec:
  completions: 10        # total successful pods required
  parallelism: 3         # how many at once
  backoffLimit: 4        # retries before marking Failed
  activeDeadlineSeconds: 3600
  ttlSecondsAfterFinished: 86400
  template:
    spec:
      restartPolicy: OnFailure
```

- **`completions` and `parallelism`** together express the work: `completions: 1` is a single task; `completions: N, parallelism: M` is a work queue processed M at a time. Omitting `completions` with parallelism set means "run until one succeeds", used for queue workers.
- **`backoffLimit`** caps retries; exceeding it marks the Job `Failed`. The retry interval backs off exponentially.
- **`ttlSecondsAfterFinished`** cleans up finished Jobs. Without it, completed Job objects and their pods accumulate indefinitely and eventually become an etcd and API-server problem — a real and common cluster-hygiene issue.
- **`activeDeadlineSeconds`** is a wall-clock cap that overrides `backoffLimit`.

**CronJobs** add a schedule, plus:

- **`concurrencyPolicy`**: `Allow` (default), `Forbid` (skip if the previous run is still going), or `Replace`. **`Allow` on a job that occasionally overruns its schedule is a classic self-inflicted incident** — runs pile up, each consuming resources, and they can conflict on shared state. `Forbid` is the safer default for anything non-idempotent.
- **`startingDeadlineSeconds`** — if the controller was down and missed a scheduled time, this governs whether it runs late. Note the subtlety: if more than 100 schedules are missed, the CronJob stops scheduling entirely and logs an error, which is a genuinely confusing failure.
- **Schedules run in the controller's timezone** unless `timeZone` is set (available in recent versions) — a persistent source of "the job ran an hour early" during DST transitions.
- **Guarantees are at-least-once, not exactly-once**, so jobs must be idempotent.

**K2.11 — Deployment strategies and how you'd implement each**

- **Rolling** (native, K2.6) — gradual replacement in place. Free, built in, and two versions coexist during the rollout.
- **Recreate** (native) — terminate everything, then start the new version. Downtime, but the only option when two versions genuinely can't coexist (an exclusive lock, an incompatible schema).
- **Blue/green** — two full environments; switch traffic at once. **Implementation**: two Deployments with distinct labels and a Service whose selector you flip, or two target groups behind an Ingress. Instant cutover and instant rollback, at the cost of double the resources during the switch. Good when you want a hard, atomic transition and a fast rollback path.
- **Canary** — route a small fraction of traffic to the new version, observe, then progress. **Implementation**: crudely, by running a small number of new-version pods behind the same Service (traffic split ≈ pod ratio, which is imprecise and can't be controlled below 1/N). Properly, with an ingress controller supporting weighted routing, a service mesh (K4.13), or **Argo Rollouts / Flagger**, which automate the progression and — the important part — **analyse metrics at each step and roll back automatically** if error rates or latency degrade.

The judgement to express: **the value of canary is the automated analysis, not the traffic split.** A canary that a human watches for five minutes and approves is barely better than a rolling update; a canary that automatically aborts on an SLO regression catches problems that would otherwise reach everyone. If you're describing canary in an interview, describe the analysis step and the abort criteria, because that's the part that's actually hard.

Also worth naming: all of these are orthogonal to **feature flags**, which decouple deploy from release entirely and are often the better answer for risky changes — you ship the code dark and enable it for 1% of users, which gives finer control than any infrastructure-level split.

**K2.12 — Voluntary vs involuntary disruption**

- **Voluntary** — deliberate actions: `kubectl drain` for node maintenance, cluster upgrades (K11.4), scale-down by the autoscaler (K7.7), node consolidation by Karpenter, deleting a pod, a rolling update.
- **Involuntary** — things you didn't choose: node hardware failure, kernel panic, node OOM, network partition, spot instance reclamation, eviction under node pressure (K6.11), a container exceeding its memory limit (K6.3).

Why the distinction matters, which is the entire point of the item: **PodDisruptionBudgets only protect against voluntary disruption** (K6.9). A PDB saying "at least 2 of 3 must be available" will block a drain, but it cannot stop a node from failing. Expecting a PDB to protect availability generally is a common and consequential misunderstanding.

So the two are handled by different mechanisms:

- **Voluntary** — PDBs, plus graceful termination handling (`preStop` hooks, correct `terminationGracePeriodSeconds`, and the application actually handling SIGTERM by draining connections rather than exiting immediately).
- **Involuntary** — replica count above 1, spreading across nodes and AZs (K6.8), fast rescheduling, and designing the application to tolerate abrupt pod loss.

The senior framing: **on a modern cluster, voluntary disruption is constant.** Karpenter consolidating nodes, spot reclamation, and frequent cluster upgrades mean pods are moved routinely rather than exceptionally. A workload that can't tolerate being rescheduled isn't production-ready on Kubernetes — and the pattern of "we set `do-not-disrupt` on everything" is how you end up with a cluster that can never be upgraded or right-sized.

---

## K3. Configuration & secrets

**K3.1 — ConfigMaps as env vars and as mounted files**

```yaml
# as individual env vars
env:
  - name: LOG_LEVEL
    valueFrom:
      configMapKeyRef: { name: app-config, key: log_level }

# all keys as env vars
envFrom:
  - configMapRef: { name: app-config }

# as files
volumes:
  - name: config
    configMap:
      name: app-config
      items:
        - key: application.yaml
          path: application.yaml
volumeMounts:
  - name: config
    mountPath: /etc/app
    readOnly: true
```

The tradeoff between the two forms, which is what the item is testing:

- **Env vars** are simple and universally supported, but they're **fixed at container start** (K3.2), they leak into crash dumps, child processes, and `kubectl describe`, and there's a practical size limit on the whole environment.
- **Mounted files** support larger content, natural for config file formats, **update in place** without a restart (K3.2), and can be mounted read-only. The downside is the app must read from a path and, if you want live reload, must watch the file.

`envFrom` is convenient and slightly dangerous: it injects every key, so adding a key to the ConfigMap silently adds an environment variable to every consumer, which can collide with something the runtime expects.

**K3.2 — Which mounted config updates live, and which requires a restart**

This is a high-value item because the behaviour is genuinely non-obvious:

- **Environment variables from a ConfigMap or Secret: never update.** They are resolved at container start. Update the ConfigMap and the running container keeps the old value forever. This is the single most common surprise in this area.
- **`subPath` mounts: never update.** A file mounted with `subPath` is copied once and is not a symlink into the managed volume, so it never refreshes. People use `subPath` to mount a single file into a directory that has other content, and then can't work out why updates don't propagate.
- **Whole-volume ConfigMap and Secret mounts: do update**, eventually. The kubelet refreshes them on its sync period (roughly a minute, plus cache TTL), and the update is atomic via a symlink swap so readers never see a partial file.

And the crucial caveat even for the case that does update: **the file changing does not mean the application picked it up.** Most applications read config once at startup. Unless the app watches the file and reloads (or you run a reloader sidecar), a live-updating mount changes the file and nothing else.

So the practical rule: **assume a restart is needed unless the application explicitly supports reload**, and make the restart happen deliberately (K3.3) rather than hoping.

**K3.3 — Triggering a rollout on config change (checksum annotation)**

The problem: changing a ConfigMap doesn't change the Deployment's pod template, so no rollout occurs (K2.5), and the pods keep the old config (K3.2).

The pattern — put a hash of the config into the pod template annotations, so any config change alters the template and triggers a normal rolling update:

```yaml
# Helm
spec:
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
```

Kustomize does this natively and better with **`configMapGenerator`**, which appends a content hash to the ConfigMap's *name* and rewrites all references — so the new ConfigMap is a new object, the pod template changes, and — the extra benefit — **the old ConfigMap still exists, so a rollback to the previous ReplicaSet gets the matching config**. That's a genuine advantage over the annotation approach, where rolling back the Deployment leaves the new ConfigMap in place (K2.7).

Alternatives: **Reloader** or **stakater/Reloader**-style controllers that watch ConfigMaps and Secrets and trigger rollouts automatically, which is convenient but means a config change causes a deploy you didn't explicitly request. And immutable ConfigMaps with generated names (K3.8), which is the same idea as configMapGenerator applied deliberately.

**K3.4 — Secrets are base64-encoded, not encrypted**

`kubectl get secret x -o yaml | base64 -d` returns the plaintext. Base64 is an encoding for binary-safe transport, not a security control, and anyone who can read the Secret object can read the secret.

The consequences that actually matter:

- **Secrets are stored in etcd in plaintext by default** — so an etcd snapshot or disk is a full credential dump (K1.2), and anyone with etcd access has everything.
- **RBAC on Secrets is the real control** (K8.2). `get secrets` in a namespace is equivalent to holding every credential in it, and it's frequently granted casually in a broad Role.
- **Anyone who can create a pod in a namespace can read its Secrets**, by mounting them. So `create pods` is effectively `read secrets` for that namespace — which is a genuinely important RBAC insight (K8.12) and means the two permissions can't be separated.
- **Secrets in manifests are secrets in git.** Which is the whole problem GitOps has to solve (K10.11).

What Secrets *do* give you over ConfigMaps: they're not written to the node's disk in the clear (tmpfs-backed mounts), they're excluded from some logging, they're a distinct RBAC resource so you can grant ConfigMap access without Secret access, and cloud providers and tooling treat them specially. So they're better than ConfigMaps for credentials — just not sufficient on their own.

The correct posture: **encryption at rest (K3.5), tight RBAC, and ideally sourcing secrets externally (K3.6) so they never persist in etcd at all.**

**K3.5 — Encryption at rest for etcd secrets**

Configured on the API server with an `EncryptionConfiguration` specifying providers in order:

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: ["secrets"]
    providers:
      - kms:
          name: aws-kms
          endpoint: unix:///var/run/kmsplugin/socket.sock
      - identity: {}     # fallback: plaintext — must be LAST
```

Points that matter:

- **Provider order is the whole configuration.** The first provider is used for *writes*; all are tried for *reads*. `identity` means no encryption, so **`identity` first means everything is written in plaintext** while appearing configured — a real misconfiguration.
- **Enabling encryption does not encrypt existing Secrets.** They stay as written until rewritten. Force it with `kubectl get secrets -A -o json | kubectl replace -f -`, which rewrites every Secret through the new provider. Forgetting this step is the standard gap.
- **KMS provider (v2) is the right choice** over `aescbc` with a local key, because a local key sitting in a file on the control plane nodes provides limited additional protection — it's protecting against stolen disks, not against anyone with node access. KMS moves the key material out of the cluster entirely (A10.1).
- **On EKS**, this is the "secrets encryption" option using a KMS CMK, and it can now be enabled on existing clusters. Note that **the provider still owns etcd**, so what you're protecting against is a specific and narrower threat than people assume — it's defence in depth and a compliance control, not a defence against the provider.
- Encryption adds a KMS call per Secret write and on cache miss, which is a latency and quota consideration (A10.15).

**K3.6 — External secrets: operators and CSI drivers**

Two approaches with a meaningful difference:

- **External Secrets Operator (ESO)** — a controller reads from AWS Secrets Manager, Vault, or similar and **creates native Kubernetes Secret objects**, keeping them in sync. Pros: works with everything, since consumers just use normal Secrets; supports templating and refresh intervals. Con: **the secret still lands in etcd**, so you've solved the git problem but not the etcd problem (mitigate with K3.5).
- **Secrets Store CSI Driver** — mounts secrets **directly into the pod as files** from the external store at pod start, with no Kubernetes Secret object at all (unless you enable the optional sync). Pros: the secret never touches etcd; rotation can update the mounted file. Cons: only available as a mounted file (so no env vars without the sync feature), and the pod depends on the external store's availability at start.

Both authenticate to the backing store using **workload identity** — IRSA or EKS Pod Identity on AWS (A2.7, K8.4) — so no bootstrap credential is needed, which is the elegant part.

The tradeoffs to state: **ESO for compatibility and ergonomics, CSI driver for the strongest posture.** The availability consideration is real for both: if Secrets Manager or Vault is unreachable, pods can't start — you've added a hard dependency to your pod startup path. Cache and failure behaviour matter, and this belongs in a resilience review.

And the rotation point (A7.8): **a secret updating in the external store doesn't restart your pod.** ESO can trigger a rollout via a reloader; the CSI driver can update the file but the app must re-read it. Rotation only works end to end if the application cooperates.

**K3.7 — The downward API**

Exposes pod and container metadata to the application without hardcoding it:

```yaml
env:
  - name: POD_NAME
    valueFrom: { fieldRef: { fieldPath: metadata.name } }
  - name: POD_NAMESPACE
    valueFrom: { fieldRef: { fieldPath: metadata.namespace } }
  - name: NODE_NAME
    valueFrom: { fieldRef: { fieldPath: spec.nodeName } }
  - name: POD_IP
    valueFrom: { fieldRef: { fieldPath: status.podIP } }
  - name: MEMORY_LIMIT
    valueFrom: { resourceFieldRef: { containerName: app, resource: limits.memory } }
```

Uses: **enriching logs and metrics** with pod, node, and namespace so telemetry is attributable (K9.13); **binding to the correct IP**; **cluster member discovery** for StatefulSets; and — the genuinely valuable one — **sizing runtime memory from the container limit.** Passing `limits.memory` into a JVM's heap settings or a worker-count calculation means the application right-sizes itself to its cgroup rather than to the node, which is what prevents the classic OOMKill where the JVM sizes its heap from the node's total memory and immediately exceeds its own limit (K6.3, K9.8).

Labels and annotations can also be exposed as files via a `downwardAPI` volume, and those *do* update live when the pod's labels change.

**K3.8 — Immutable ConfigMaps and Secrets**

Setting `immutable: true` means the object can't be changed after creation — only deleted and recreated.

Why it helps at scale, and there are two distinct reasons:

1. **Performance.** The kubelet watches every ConfigMap and Secret mounted into its pods so it can propagate updates (K3.2). Marking them immutable lets the kubelet stop watching, which **materially reduces API server and kubelet load** in large clusters with many pods. On a cluster with thousands of pods, this is a real control-plane relief, and it's the reason the feature exists.
2. **Safety.** An accidental edit to a shared ConfigMap can't silently change behaviour across every consumer, with effects appearing minutes later on some pods and not others (K3.2). Immutability forces the change to be a new object, which makes it a deliberate, versioned, rollback-able act.

The pattern it pairs with: **content-hashed names** (`app-config-7f3a9c`), as Kustomize's `configMapGenerator` produces (K3.3). New config means a new object, which means a new pod template, which means a rollout — and the old object still exists for rollback. That combination of immutable plus hashed name plus automatic rollout is the mature way to handle configuration, and describing it as a coherent pattern rather than three separate features is what makes the answer land.

The cost: you must handle cleanup of old objects, or they accumulate.

---

## K4. Networking

Container networking in general is N10.7; the AWS VPC CNI specifics are A5.7.

**K4.1 — The network model and flat addressing**

The model mandates three things:

1. **Every pod gets its own IP address.**
2. **Pods can communicate with all other pods without NAT**, across nodes.
3. **Agents on a node can reach all pods on that node.**

The consequence is a **flat address space**: a pod's IP is the same from its own perspective and from everyone else's. No port mapping, no NAT translation, no "which host port did this land on".

Why this matters rather than being trivia: it means applications behave as they would on a network of VMs. Anything that embeds its own address in a protocol payload works. Service discovery is just DNS returning IPs. And **you can apply network policy and observability per pod**, because the IP identifies a workload.

The costs, which is the interesting half: **IP consumption is enormous.** Every pod consumes an address, and with the AWS VPC CNI those are real VPC addresses, which is precisely the exhaustion problem in A5.7 and the subnet-sizing argument in N2.4. Overlay CNIs solve address consumption by encapsulating, at the cost of MTU overhead (N1.6) and pod IPs that aren't routable outside the cluster.

And the security consequence: **flat means everything can reach everything by default.** There is no built-in segmentation. That's what NetworkPolicy exists to fix, and why a default-deny baseline is a meaningful control rather than a formality (K4.10).

**K4.2 — What a CNI does, and how plugins differ**

The CNI is called by the kubelet when a pod is created: it **allocates an IP, creates the network interface in the pod's namespace, and configures routes** so the pod can reach the rest of the cluster. On deletion it releases the address.

How plugins differ, along the axes that actually matter:

- **Address source**: **native VPC IPs** (AWS VPC CNI, Azure CNI) — pods are first-class citizens of the cloud network, so cloud security groups, flow logs, and direct load balancer targeting work (A5.6), at the cost of address consumption. Versus **overlay** (Calico VXLAN, Flannel) — pods get cluster-private addresses encapsulated over the node network, conserving addresses at the cost of encapsulation overhead and reduced MTU.
- **Routing mode**: encapsulated (VXLAN, IP-in-IP) versus native routing with BGP (Calico can peer with your network so pod IPs are routable directly).
- **Dataplane**: iptables versus **eBPF** (Cilium, Calico eBPF mode), which affects performance, scale, and observability (K1.8).
- **NetworkPolicy support**: not all plugins implement it, and this is the one that catches people (K4.11). Flannel notably does not.
- **Extra capabilities**: Cilium adds identity-based policy, L7-aware policy, Hubble observability, and cluster mesh; Calico adds global network policies and richer policy semantics.

The decision framing: **on a managed cloud cluster, the provider's CNI is the sensible default until you have a specific reason to change** — and the usual specific reasons are IP exhaustion (A5.7), the need for NetworkPolicy the default plugin doesn't support, or scale problems with iptables (K1.8). Changing CNI on a live cluster is disruptive, so it's a decision worth getting right at build time.

**K4.3 — Service types**

- **ClusterIP** (default) — a stable virtual IP reachable only inside the cluster. The building block; everything else is built on it.
- **NodePort** — allocates a port (30000–32767 by default) on **every** node, forwarding to the Service. Mostly a primitive used by LoadBalancer rather than something to use directly: the port range is unfriendly, and you're exposing every node.
- **LoadBalancer** — provisions an external load balancer via the cloud controller manager (A5.6), which targets the NodePort or, better, the pod IPs directly.
- **ExternalName** — no proxying at all; returns a CNAME to an external DNS name. Useful for referring to an external database by an in-cluster name so the application config doesn't change between environments.

Points worth adding: **a LoadBalancer Service per application gets expensive**, which is the argument for an Ingress or Gateway sharing one load balancer across many services (K4.7). **Headless** is a fourth mode rather than a type (K4.5). And **`externalTrafficPolicy: Local`** preserves the client source IP and avoids an extra hop, but only routes to pods on the receiving node — so it needs pods spread across nodes or you get imbalanced traffic and health check failures on nodes with no pods. That tradeoff is a good detail: source IP preservation versus even distribution.

**K4.4 — How a Service selects pods; Endpoints and EndpointSlices**

A Service has a **label selector**. The endpoint controller watches for pods matching it and maintains the list of **ready** pod IPs and ports in EndpointSlice objects. kube-proxy or the dataplane programs each node from those (K1.8).

The two things to be precise about, because they're the basis of most Service debugging (K9.9):

1. **Only pods that pass readiness are included.** A pod that is Running but not Ready is excluded — which is the mechanism behind rolling updates not sending traffic to starting pods, and also the reason a Service with zero endpoints and healthy-looking pods means "readiness is failing".
2. **The selector matches labels, and a typo means zero endpoints** with no error anywhere. Nothing validates that a Service's selector matches anything — an empty Service is a legitimate state.

**EndpointSlices replaced Endpoints** for scale reasons, and the reason is worth knowing: the old `Endpoints` object held *every* backend in a single object, so a Service with 5,000 pods produced a very large object that was rewritten and pushed to every node on every single pod change. EndpointSlices shard that into chunks of ~100, so churn updates one small object instead of one enormous one. This was a genuine control-plane scaling problem, not a cosmetic change.

Diagnostic command: `kubectl get endpointslices -l kubernetes.io/service-name=my-svc`.

**K4.5 — Headless Services**

`clusterIP: None`. No virtual IP is allocated and no proxying happens. Instead, **DNS returns the pod IPs directly** — an A record per ready pod for the Service name, and for StatefulSets, a per-pod DNS name (`db-0.db.default.svc.cluster.local`).

When you need one:

- **StatefulSets** (K2.8) — members must address each other individually for replication and clustering, which a load-balanced VIP actively prevents.
- **Client-side load balancing** — gRPC in particular. gRPC multiplexes over long-lived HTTP/2 connections, so a ClusterIP balances the *connection* once and then every request rides it, producing badly imbalanced load. Resolving all pod IPs and balancing client-side fixes it. **"Why is one of my gRPC pods getting all the traffic" is a classic, and the headless Service is the classic answer** (the alternatives being a proxy or a service mesh, K4.13).
- **Discovering all members** of a set — peer discovery for clustered software.

Note that a headless Service still needs a selector to populate endpoints, and pods appear only when Ready — with `publishNotReadyAddresses: true` as the escape hatch for clustering software that needs to find peers before they're serving.

**K4.6 — Cluster DNS and the FQDN form**

CoreDNS runs in the cluster and serves records for Services and pods. The resolution hierarchy:

```
<service>                                   # same namespace
<service>.<namespace>                       # cross-namespace
<service>.<namespace>.svc.cluster.local     # fully qualified
```

Pods get a `/etc/resolv.conf` with a **search path** (`<ns>.svc.cluster.local svc.cluster.local cluster.local`) and, importantly, **`ndots:5`**.

The `ndots:5` detail is the highest-value thing in this item because it causes a real, widespread performance problem: any name with fewer than five dots is tried against **every search domain first** before being tried as an absolute name. So resolving `api.example.com` (two dots) generates four failed lookups — `api.example.com.default.svc.cluster.local`, `.svc.cluster.local`, `.cluster.local`, then the search-less form — before succeeding. For an application making many external calls, that's a 4× DNS amplification, and it presents as elevated latency and CoreDNS under unexplained load.

Fixes: **use a trailing dot** to make external names absolute (`api.example.com.`), override `dnsConfig` with a lower `ndots`, or run **NodeLocal DNSCache**, which caches on each node and is the standard mitigation at scale — it also relieves the per-ENI DNS query limit on AWS (A3.6).

Other operational points: **CoreDNS is a cluster-wide single point of failure** — if it's unhealthy, everything appears broken in confusing ways, so it needs adequate replicas, resource headroom, and a PDB. And DNS caching in applications means endpoint changes aren't picked up instantly (N4.9), which is the same class of problem as A8.5.

**K4.7 — Ingress, controllers, and why the controller isn't built in**

An **Ingress** is an API object describing HTTP routing: hostnames, paths, TLS, and backend Services. **It does nothing on its own.** An **ingress controller** (NGINX, Traefik, HAProxy, AWS Load Balancer Controller, Istio) watches Ingress objects and configures actual proxy infrastructure to implement them.

**Why the controller isn't built in**: the implementations are genuinely different in kind — a software proxy running as pods in the cluster versus a cloud load balancer provisioned outside it — and the routing features people need vary enormously. Building one in would mean either the lowest common denominator or blessing one implementation. Keeping it as an interface with pluggable implementations is the same pattern as CNI and CSI, and it's a coherent design choice rather than an omission.

The practical consequences: **an Ingress with no controller installed does absolutely nothing, silently.** No error, no event, no traffic. This is a common first-cluster confusion. And **annotations are where the real configuration lives** — timeouts, body size limits, rewrite rules, auth — and they are entirely controller-specific, so an Ingress is not portable between controllers despite being a standard resource. That non-portability is precisely the problem Gateway API solves (K4.9).

On EKS specifically, the subnet-tagging requirement is the classic silent failure (A5.6).

**K4.8 — TLS on an Ingress**

```yaml
spec:
  tls:
    - hosts: [api.example.com]
      secretName: api-tls        # Secret of type kubernetes.io/tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: api, port: { number: 80 } }
```

The Secret must be type `kubernetes.io/tls` with `tls.crt` and `tls.key`. In practice you don't create it by hand — **cert-manager** issues and renews it automatically from Let's Encrypt or an internal CA (S4.8, and A10.18 for ACM Private CA).

The points that matter:

- **TLS terminates at the ingress controller.** Traffic from there to the pod is plaintext by default, which is the same gap as the ALB-to-target leg in A10.31 — architecture diagrams show "HTTPS" and hide it. If end-to-end encryption is required, that's backend TLS annotations or a service mesh (K4.13).
- **The Secret must be in the same namespace as the Ingress**, which is a recurring annoyance for wildcard certificates shared across namespaces (and one of the things Gateway API improves).
- **Certificate expiry is a foreseeable outage** (A8.6) — automate issuance and alert on days-to-expiry regardless.
- SNI means one controller serves many certificates on one IP.

**K4.9 — Gateway API and why it's replacing Ingress**

Gateway API is the successor: a set of resources with **role-oriented separation**:

- **GatewayClass** — the implementation (infrastructure provider).
- **Gateway** — an instance of listening infrastructure: ports, protocols, TLS. Owned by the platform team.
- **HTTPRoute / GRPCRoute / TCPRoute** — routing rules attached to a Gateway. Owned by application teams.

Why it's replacing Ingress, in order of importance:

1. **Ingress's feature set is too small, so everything real lives in controller-specific annotations** (K4.7) — meaning "standard resource, non-portable configuration". Gateway API expresses header matching, traffic splitting by weight, request mirroring, redirects, and rewrites **as typed API fields**, so they're portable and validatable.
2. **Role separation.** The platform team owns the Gateway and its TLS and hostname policy; app teams attach Routes without touching shared infrastructure. Ingress conflates both in one object, which is a real multi-tenancy problem (K13.3).
3. **Cross-namespace references with explicit permission** (ReferenceGrant) — a Route in one namespace can attach to a Gateway in another, only if the Gateway's namespace allows it. Ingress has no such model.
4. **Protocol coverage beyond HTTP**, and **native traffic splitting**, which makes canary deployments (K2.11) a first-class API feature rather than an annotation hack.

The realistic position to hold: Ingress is not deprecated and is still overwhelmingly what's deployed. Gateway API is where new development is going and is the right choice for a new platform, especially where multi-tenancy and canary progression matter. Migration is gradual because both can run side by side.

**K4.10 — NetworkPolicies and a default-deny baseline**

```yaml
# default deny all ingress and egress in a namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny, namespace: payments }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
# then allow what's needed
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: api-from-gateway, namespace: payments }
spec:
  podSelector: { matchLabels: { app: api } }
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector: { matchLabels: { name: ingress } }
          podSelector: { matchLabels: { app: nginx } }
      ports: [{ protocol: TCP, port: 8080 }]
```

The semantics people get wrong:

- **Policies are additive allow-lists with no deny.** If any policy selects a pod for a direction, that direction becomes default-deny for that pod and only explicitly allowed traffic passes. If no policy selects it, everything is allowed. There is no ordering and no priority (unlike Calico's extended policies).
- **A `namespaceSelector` and `podSelector` in the *same* `from` element is an AND** (pods matching X in namespaces matching Y). As **separate list items** it's an OR. This is a subtle YAML distinction that produces policies far more permissive than intended, and it's worth being able to point at.
- **Egress policies must allow DNS** to CoreDNS (UDP/TCP 53 in `kube-system`) or every pod in the namespace loses name resolution. **This is the single most common way a default-deny egress policy breaks a cluster**, and the symptom — everything failing with resolution errors — doesn't obviously point at NetworkPolicy.
- **Policies select by label, not by IP**, which is what makes them work with ephemeral pods.

The rollout advice mirrors A1.11: **start with a default-deny in a non-production namespace, observe what breaks, and build the allow-list from evidence** rather than shipping default-deny to production and discovering the dependency graph the hard way. Cilium's Hubble or flow logs make that observation practical.

**K4.11 — NetworkPolicy requires CNI support**

**A NetworkPolicy object is accepted by the API server whether or not anything implements it.** There is no error, no warning, no status field indicating it isn't enforced. If your CNI doesn't support policy — Flannel being the notable example, and the AWS VPC CNI historically requiring the Calico add-on — you can apply a beautiful default-deny baseline and every packet still flows.

That's the whole item, and it matters because it's a **silent security control failure**: the manifest is in git, the policy is in the cluster, an audit checkbox is ticked, and nothing is enforced. It's exactly the class of false assurance as an unrecorded Config resource type (A10.23) or an unenforced Ingress (K4.7).

How to verify rather than assume: **test it.** Deploy a pod, apply a deny, and try to connect. `kubectl exec` and a `curl`/`nc` between two pods takes a minute and is the only real proof. Beyond that, confirm the CNI's policy feature is enabled (the AWS VPC CNI now has native policy support that must be switched on), and consider a policy engine check (K8.9) that flags namespaces without policies.

**K4.12 — Tracing traffic end to end from client to container port**

The path, and the check at each hop — this is the structural answer that makes K9.9 tractable:

1. **DNS**: does the client's name resolve, and to what? External DNS to the load balancer, or cluster DNS to a ClusterIP (K4.6).
2. **Load balancer / Ingress**: is the LB healthy, are its targets healthy, is the listener and certificate right (K4.8)? Check the controller's logs — a misconfigured Ingress often fails only there.
3. **Ingress rules**: does the host and path match a rule? An unmatched request gets the default backend, typically a 404 from the controller itself — distinguishable from a 404 from your app by the response headers.
4. **Service**: does it exist, does its selector match pods, **does it have endpoints**? `kubectl get endpointslices` is the key check (K4.4).
5. **Port mapping**: `Service.port` → `Service.targetPort` → `containerPort`. **Mismatches here are extremely common** — the Service targets 8080 and the container listens on 3000.
6. **Node dataplane**: kube-proxy/eBPF rules DNAT to a pod IP (K1.8).
7. **NetworkPolicy**: is the traffic allowed at both source egress and destination ingress (K4.10)?
8. **Pod**: is it Ready? Is the process listening, **and on `0.0.0.0` rather than `127.0.0.1`** — a container binding to loopback accepts nothing from outside, which is a classic and confusing one.

The isolating technique: **bypass layers to bisect.** `kubectl port-forward` to the pod tests the pod directly, skipping Service, policy, and Ingress. If that works, the problem is above. `kubectl exec` into another pod and curl the ClusterIP tests the Service without the Ingress. Each test eliminates a layer, which is the same discipline as A3.15 and T1.

**K4.13 — Service mesh: what it adds and what it costs**

A mesh puts a proxy (sidecar, or with Istio ambient mode a per-node component) in the path of all service-to-service traffic, controlled centrally.

**What it adds:**

- **mTLS everywhere, with automatic certificate issuance and rotation** — workload identity without touching application code. This is usually the strongest single justification, especially where a regulator wants encryption in transit between services (A10.31).
- **Fine-grained traffic control** — weighted splitting for canary (K2.11), mirroring, fault injection, retries, timeouts, circuit breaking, all without code changes.
- **Uniform L7 telemetry** — golden signals for every service without instrumenting any of them, which is genuinely valuable in a polyglot estate.
- **Authorisation policy at L7** — beyond NetworkPolicy's L3/L4 (K4.10).

**What it costs**, and an answer that skips this is the incomplete one:

- **Latency**, a small amount per hop, doubled because traffic passes through two proxies.
- **Resource overhead** — a sidecar per pod, which across thousands of pods is a substantial fraction of cluster capacity.
- **Operational complexity, which is the real cost.** The mesh is now a critical component in the request path of everything. Its control plane, its certificates, and its upgrades all become production concerns, and mesh upgrades are notoriously involved. Debugging becomes harder because there's another hop that can fail, and the failure modes are unfamiliar.
- **A steep learning curve** for the whole team, not just whoever installed it.

The judgement: **adopt a mesh when you have a specific requirement it uniquely solves** — most commonly mTLS everywhere for compliance, or traffic management for progressive delivery at a scale where doing it per-service doesn't work. Adopting it because it's the standard answer is how small platforms acquire a large permanent operational burden. Worth naming the lighter alternatives: mTLS via cert-manager and application libraries, retries and timeouts in the client, and Gateway API for north-south traffic (K4.9) — and Istio ambient mode, which removes the per-pod sidecar and materially changes the cost side of this calculation.

---

## K5. Storage

**K5.1 — PersistentVolume, PersistentVolumeClaim, StorageClass**

- **PersistentVolume (PV)** — a piece of storage in the cluster. Cluster-scoped, with a lifecycle independent of any pod.
- **PersistentVolumeClaim (PVC)** — a namespaced request for storage: size, access mode, class. The pod references the PVC, never the PV.
- **StorageClass** — a template describing *how* to provision: which CSI driver, what parameters (volume type, IOPS, encryption, filesystem), what reclaim policy, and whether binding waits for scheduling.

The separation is the point: **the PVC is the application's interface and the PV is the infrastructure's.** An application author asks for "20Gi ReadWriteOnce fast" without knowing whether that's EBS gp3, an in-house SAN, or a local disk — which means the same manifest works in dev and prod against different infrastructure. That abstraction is the reason for the indirection, and it's what the question is checking you understand.

The binding relationship: a PVC binds to exactly one PV, one-to-one and exclusively.

**K5.2 — Static vs dynamic provisioning**

- **Static** — an administrator creates PVs ahead of time; PVCs bind to a matching one. Used when the storage already exists: a pre-existing NFS export, a specific cloud disk you need to attach, a migration where the data is already on a volume.
- **Dynamic** — a PVC referencing a StorageClass causes the CSI driver to **create** the underlying volume on demand. The default and the norm.

Two details worth having:

- **A `default` StorageClass** means PVCs that omit `storageClassName` still provision. Convenient, and occasionally surprising when the default is not what you'd have chosen — a common cause of expensive or wrong-type volumes appearing across a cluster.
- **`storageClassName: ""`** (empty string, explicitly) disables dynamic provisioning for that PVC and forces static binding. Different from omitting the field entirely, which is a genuinely confusing distinction.

**K5.3 — Access modes, and the constraint RWO puts on scheduling**

- **ReadWriteOnce (RWO)** — mountable read-write by a single **node**.
- **ReadOnlyMany (ROX)** — read-only by many nodes.
- **ReadWriteMany (RWX)** — read-write by many nodes.
- **ReadWriteOncePod (RWOP)** — read-write by a single **pod**, strictly.

The critical detail people get wrong: **RWO is per node, not per pod.** Multiple pods on the *same* node can share an RWO volume. It's only when they're on different nodes that it fails. RWOP was added because "one node" was not the guarantee people assumed they had.

**The scheduling constraint** is the substance of the item: an RWO volume is attached to one node, so **every pod using it must be scheduled onto that node.** Consequences:

- **A Deployment with more than one replica and an RWO PVC will not work** — the second pod is stuck `Pending` or `ContainerCreating`, unable to attach. People try it constantly. If you need multiple replicas each with storage, that's a StatefulSet with `volumeClaimTemplates` (K5.5), which gives each pod its *own* volume.
- **Rolling updates deadlock** with RWO: the new pod can't attach until the old one releases, and with default `RollingUpdate` the old one won't terminate until the new one is ready. Use `strategy: Recreate` for single-replica stateful Deployments.
- **The volume's zone pins the pod's zone** (K5.9) — an EBS volume in `eu-west-1a` means the pod can only ever run in `eu-west-1a`, which is a hard constraint on AZ resilience for stateful workloads (K13.8).

**RWX requires a filesystem that supports it** — NFS, EFS (A6.9), FSx, CephFS. Block storage like EBS cannot do RWX, and the fact that a StorageClass accepts the access mode in a PVC doesn't mean the driver can honour it.

**K5.4 — Reclaim policies and the data-loss risk of Delete**

Set on the StorageClass (inherited by dynamically-provisioned PVs) or directly on a PV:

- **`Delete`** — deleting the PVC deletes the PV **and the underlying storage**. The default for most dynamic StorageClasses.
- **`Retain`** — deleting the PVC leaves the PV and the data. The PV goes to `Released` and won't be reused until an administrator manually clears its `claimRef`.
- `Recycle` — deprecated, ignore.

**The risk**: with `Delete`, `kubectl delete pvc` — or deleting the namespace, or a Helm uninstall, or an ArgoCD prune of a resource that fell out of git — **permanently destroys the data**. No confirmation, no recycle bin, no undo. Deleting a namespace to "clean up" and taking the database with it is a real, recurring incident, and it's fast: by the time you realise, the cloud volume is gone.

The mitigations to state:

- **Use `Retain` for anything whose loss would matter**, accepting the manual cleanup burden as the price of the safety net.
- **Snapshot independently** — VolumeSnapshots or provider-level backup (AWS Backup, A11.7) — because reclaim policy protects against deletion, not corruption.
- **`kubernetes.io/pvc-protection` finalizer** already prevents deleting a PVC that's in use by a pod, so the PVC will sit `Terminating` until the pod is gone (K12.4). That protects against the immediate case but not against deleting the workload first.
- **Prevent it in policy** (K8.9) — a Kyverno rule blocking `Delete` reclaim on production StorageClasses, or blocking namespace deletion where PVCs exist.
- In GitOps, **exclude PVCs from automated pruning** (K10.9).

**K5.5 — volumeClaimTemplates in a StatefulSet**

```yaml
apiVersion: apps/v1
kind: StatefulSet
spec:
  serviceName: db          # headless Service (K4.5)
  replicas: 3
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: gp3
        resources: { requests: { storage: 100Gi } }
```

This creates **one PVC per pod**, named deterministically `data-db-0`, `data-db-1`, `data-db-2`. The binding is stable: if `db-1` is rescheduled to a different node, it reattaches to `data-db-1` — which is the property that makes clustered databases workable, since each member keeps its own data.

The behaviours that surprise people:

- **Scaling down does not delete the PVCs.** `db-2`'s volume persists so that scaling back up reattaches the same data. Correct and deliberate, but it means storage cost persists after scale-down and old data reappears on scale-up. `persistentVolumeClaimRetentionPolicy` now lets you control this explicitly.
- **Deleting the StatefulSet does not delete the PVCs** either, by default.
- **`volumeClaimTemplates` is immutable** — you cannot change the size in the template and have it apply. Resizing means editing each PVC individually (K5.6) and recreating the StatefulSet with `--cascade=orphan`. This is one of the genuinely annoying operational realities of StatefulSets and worth mentioning.
- Each PVC inherits the zone constraint of its PV, pinning each pod to an AZ (K5.3).

**K5.6 — Expanding a PVC, and the limits**

Edit `spec.resources.requests.storage` on the PVC to a larger value. Requirements and limits:

- **The StorageClass must have `allowVolumeExpansion: true`.** If not, the edit is rejected. You can add the field to the StorageClass afterwards and it applies to subsequent expansions.
- **Shrinking is not supported at all**, by any driver. Reducing means creating a new smaller volume and copying.
- **Filesystem expansion may need a pod restart.** Modern CSI drivers support online expansion where the driver and kernel allow it; otherwise the volume grows but the filesystem doesn't until the pod restarts. **"I expanded the PVC and `df` still shows the old size"** is that gap — the same distinction as growing an EBS volume without `resize2fs` (A6.8), except CSI normally handles the filesystem step for you.
- **The underlying cloud volume may have its own cooldown** — EBS won't accept another modification for six hours after one, so a mistaken small expansion locks you out of correcting it for the rest of the day. Worth knowing before you type the number.
- **StatefulSet templates can't be edited** (K5.5), so expanding a StatefulSet's storage is a per-PVC operation.

The practical advice: over-provision modestly rather than sizing exactly, because expansion is possible but friction-laden and shrinking is impossible.

**K5.7 — Ephemeral volume types**

- **`emptyDir`** — created empty when the pod is assigned to a node, deleted when the pod leaves it. Survives container restarts within the pod, not pod rescheduling. Uses node disk by default; `medium: Memory` makes it tmpfs (fast, but **counts against the container's memory limit**, so a large tmpfs write can trigger an OOMKill in a way that looks nothing like a memory leak — a good obscure failure mode to know).
- **`configMap` / `secret`** — project the object's keys as files, with update semantics per K3.2.
- **`projected`** — combines several sources (ConfigMaps, Secrets, downward API, service account tokens) into one directory. The mechanism behind **bound service account tokens** (K8.4).
- **`downwardAPI`** — pod metadata as files (K3.7).
- **Generic ephemeral volumes** — a full CSI volume with the pod's lifecycle, for when you need a real provisioned disk as scratch space rather than node disk.

Uses for `emptyDir`: scratch space, caches, and — most commonly — **sharing files between containers in a pod**, which is how an init container hands work to the app container (K2.3) and how a sidecar reads the app's log files.

The trap: **`emptyDir` on node disk consumes node ephemeral storage**, and exceeding it triggers node-pressure eviction of the pod (K6.11). Set `sizeLimit`, and set ephemeral-storage requests and limits, or a runaway log file evicts your pod with an error that points at the node rather than the application.

**K5.8 — CSI and what a driver provides**

CSI is the standard interface between Kubernetes and storage systems, which replaced in-tree provider code so storage vendors ship and version drivers independently of Kubernetes releases.

A driver implements three services:

- **Controller** — provisioning: create/delete volume, attach/detach to a node, snapshot, expand. Runs as a Deployment.
- **Node** — the node-local work: stage/publish the volume onto the node and into the pod's mount namespace, and filesystem expansion. Runs as a DaemonSet.
- **Identity** — capability reporting.

What a driver gives you: **dynamic provisioning** (K5.2), **snapshots** via `VolumeSnapshot` and `VolumeSnapshotClass`, **expansion** (K5.6), **cloning**, and **topology awareness** so the scheduler knows which zones a volume can live in (K5.9).

The operational points worth mentioning: **CSI drivers are cluster add-ons with their own version compatibility** (K11.9), and an upgrade that breaks the driver breaks all storage operations — new pods with PVCs won't start, though existing mounts usually keep working. On EKS the EBS CSI driver is an add-on that **must be installed explicitly** with an IRSA role; a cluster without it has PVCs stuck Pending with no obvious explanation, which catches people on new clusters. And CSI drivers run privileged with node-level mount access, so they're a high-value target and a supply chain consideration (K12.3).

**K5.9 — Diagnosing a pod stuck Pending on volume attachment or zone mismatch**

The two distinct causes and how to tell them apart:

**Zone mismatch.** EBS volumes are zonal (A6.8). If a PV exists in `eu-west-1a` and the scheduler places the pod on a node in `eu-west-1b`, the volume cannot attach. The event says something like `volume node affinity conflict` or the pod simply won't schedule.

The root cause is usually **binding mode**. With `volumeBindingMode: Immediate`, the volume is provisioned as soon as the PVC is created — **before the scheduler has picked a node** — so the zone is chosen arbitrarily and then constrains scheduling. **`volumeBindingMode: WaitForFirstConsumer` is the fix and should be the default**: it delays provisioning until a pod is scheduled, so the volume is created in the right zone. This single setting prevents most zone-mismatch problems, and knowing it is a strong signal.

**Attachment failure.** The volume exists in the right zone but won't attach:

- **Still attached to another node** — the classic case after a node failure, where the old node holds the attachment and the `VolumeAttachment` object lingers. Check `kubectl get volumeattachment`.
- **Node attachment limits** — instance types cap how many EBS volumes can attach, and a busy node hits it.
- **CSI driver problems** — check the driver's controller and node DaemonSet logs; an expired or misconfigured IRSA role is a common cause on EKS.
- **The volume was deleted** out of band, leaving a PV pointing at nothing.

The diagnostic sequence: `kubectl describe pod` for the scheduling event, `kubectl describe pvc` for binding status, `kubectl get pv` for the PV's node affinity and zone, `kubectl get volumeattachment`, then the CSI driver logs. The general Pending method is K9.6.

---

## K6. Scheduling & resources

**K6.1 — Requests vs limits**

- **Requests** — what the scheduler uses to decide placement, and what the container is guaranteed. A node must have enough unallocated request capacity to accept a pod (K1.6).
- **Limits** — the ceiling enforced at runtime by cgroups: CPU is throttled at the limit, memory kills the container at the limit.

The distinction that matters: **requests determine scheduling, limits determine runtime behaviour, and they have completely different failure modes.** Requests too high wastes capacity — pods can't be packed and nodes sit idle while the scheduler says they're full (K1.6). Requests too low means pods land on nodes that can't actually support them, and everything on that node degrades together under contention.

They also determine **QoS class** (K6.4), which determines eviction order under pressure.

The point people miss: **the scheduler never looks at actual usage.** A node whose pods request 8 CPU and use 0.5 is unschedulable; a node whose pods request nothing and use everything is "empty". So requests are a claim on capacity you're paying for whether or not you use it, and setting them from measurement is the highest-leverage cluster-efficiency work there is (K6.5).

**K6.2 — CPU throttling, and why CPU limits are contentious**

CPU is a **compressible** resource: exceeding the limit doesn't kill anything, the kernel just doesn't schedule you. The mechanism is CFS quota — a quota per 100ms period. Exceed it and the container is **stopped until the next period**.

The problem, and this is the crux of the contention: **throttling is bursty and hurts latency disproportionately.** A container with a 1 CPU limit that needs a brief 2-CPU burst to serve a request gets stopped mid-request for the remainder of the period. Average CPU utilisation looks low — maybe 30% — while p99 latency is terrible, because requests are randomly being paused for tens of milliseconds. It's a genuinely confusing symptom: **the dashboard says there's plenty of CPU headroom and the service is slow anyway.** Multi-threaded runtimes make it worse, because parallel threads consume the quota faster.

**The argument against CPU limits**: with requests set correctly, the kernel already shares CPU proportionally under contention, so a container can burst into idle capacity and gives it up when others need it. Limits forbid that burst even when the node is idle — you're throttling for no benefit. So: set requests, omit CPU limits.

**The argument for**: predictability and fairness — a noisy neighbour can't consume all spare capacity and make its neighbours' performance dependent on what else happens to be running. In multi-tenant clusters where one team's behaviour shouldn't affect another's, that's a real requirement. And without limits, performance testing results don't transfer, because the container behaves differently depending on node contention.

**The defensible position** to state: **omit CPU limits for latency-sensitive services on well-managed nodes with correct requests; set them in multi-tenant environments where isolation matters more than burst.** And regardless, **monitor `container_cpu_cfs_throttled_seconds_total`** — throttling is common, invisible on CPU utilisation dashboards, and frequently the answer to an unexplained latency problem.

**K6.3 — Memory limits, and why exceeding them is fatal**

Memory is **incompressible**. You can't give a process less memory than it has already allocated — the only options are to refuse the allocation or kill the process. So the kernel's cgroup OOM killer terminates the container when it exceeds its limit: exit code 137, reason `OOMKilled`.

The asymmetry with CPU is the point: **CPU over-limit degrades, memory over-limit is fatal and immediate.** That drives different practice — memory limits should be set with real headroom, and memory requests should generally equal limits for anything important (making it Guaranteed QoS, K6.4).

The failure modes worth naming:

- **The container is killed, not the pod.** The pod restarts the container and `RESTARTS` increments; repeated kills produce `CrashLoopBackOff` (K9.4). A container being OOMKilled every few hours is easy to miss because the service appears up.
- **Runtimes that don't read their cgroup limit.** Older JVMs sized the heap from the *node's* total memory, immediately exceeding a much smaller container limit. Modern JVMs are container-aware (`MaxRAMPercentage`); Node, Python, and Go each have their own version of this. Passing the limit in via the downward API (K3.7) is the reliable fix.
- **Page cache counts toward the cgroup limit**, so heavy file I/O can trigger an OOM kill in a process whose heap is fine — genuinely confusing when it happens.
- **`emptyDir` with `medium: Memory` counts against the limit** (K5.7).
- **The node itself can OOM**, which is different from a cgroup OOM (K6.11) and much worse, because the kernel picks the victim.

The judgement in K9.8 — raise the limit or fix the app — follows from whether the memory use is legitimate growth or a leak.

**K6.4 — QoS classes and eviction order**

Assigned automatically from requests and limits:

- **Guaranteed** — every container has requests **equal to** limits, for both CPU and memory.
- **Burstable** — requests set, and less than limits (or limits absent) for at least one resource.
- **BestEffort** — no requests or limits at all.

Under **node memory pressure**, the kubelet evicts in order: **BestEffort first, then Burstable (ordered by how far usage exceeds requests), and Guaranteed last.** So QoS is effectively a priority ranking for surviving node pressure.

The practical implications:

- **BestEffort is a bad idea for anything you care about.** It's first to die and the scheduler can pack it anywhere because it claims nothing.
- **Guaranteed for critical workloads** — databases, control-plane-adjacent components, anything whose eviction causes an outage. The cost is efficiency: requests equal to limits means you reserve peak capacity permanently.
- **Burstable for most application workloads** is the sensible middle, but note the ordering detail: eviction ranks by usage *relative to requests*, so a Burstable pod using far more than it requested is evicted before one staying within its request. Which is another argument for accurate requests (K6.5) — under-requesting doesn't just cause bad scheduling, it puts you first in line to be killed.

Distinguish this from **priority and preemption** (K6.10), which governs *scheduling*, and from **cgroup OOM kill** (K6.3), which is the kernel acting on one container rather than the kubelet choosing a pod.

**K6.5 — Setting requests from measurement**

The method:

1. **Observe actual usage** over a representative period covering peak — from Prometheus (`container_memory_working_set_bytes`, `container_cpu_usage_seconds_total` rate), `kubectl top`, or VPA in recommendation-only mode (K7.4), which is the easiest starting point because it produces concrete numbers per workload.
2. **CPU request ≈ p90–p95 of observed usage.** Not the peak — CPU is compressible and burst is fine (K6.2).
3. **Memory request ≈ p95–p99 plus headroom**, because memory over-limit is fatal (K6.3). Be more conservative here.
4. **Memory limit close to the request** for important workloads (Guaranteed, K6.4); CPU limit usually omitted or generous.
5. **Re-measure after changes**, because the numbers drift with traffic and code.

What separates a real answer:

- **The default of "copy whatever the last service used" is the actual state of most clusters**, and it's why utilisation is typically 10–30% of requested capacity. Naming that gap is a good cost story (A12.7) — cluster spend is driven by requests, not usage, so right-sizing requests is directly a cost reduction with no reliability regression if done from data.
- **Startup differs from steady state.** JVMs and anything with a warm-up phase use far more CPU at start. Requests sized for steady state make startup slow, which extends rollouts and can cause readiness timeouts (K9.10). Startup probes exist partly for this.
- **VPA's recommender is the right tool, and running VPA in `Off`/recommendation mode is safe and useful** even if you never let it act (K7.4).
- **Don't tune what doesn't matter.** Right-size the big consumers; a 50m request on a small service isn't worth the meeting.

**K6.6 — Node selectors, node affinity, pod affinity/anti-affinity**

- **`nodeSelector`** — the simple form: schedule only on nodes with these labels. No expressiveness beyond exact match.
- **Node affinity** — the richer form: `requiredDuringSchedulingIgnoredDuringExecution` (a hard constraint) and `preferredDuringSchedulingIgnoredDuringExecution` (weighted soft preference), with operators `In`, `NotIn`, `Exists`, `Gt`, `Lt`.
- **Pod affinity / anti-affinity** — schedule relative to *other pods* rather than node labels, with a `topologyKey` defining the scope (`kubernetes.io/hostname` for per-node, `topology.kubernetes.io/zone` for per-AZ).

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - { key: node.kubernetes.io/instance-type, operator: In, values: [g5.xlarge] }
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector: { matchLabels: { app: api } }
          topologyKey: kubernetes.io/hostname
```

The points that matter:

- **`IgnoredDuringExecution` is in every name for a reason**: these are scheduling-time constraints only. If node labels change afterwards, running pods are unaffected (K1.6 — the scheduler doesn't move things).
- **Pod anti-affinity is expensive at scale.** Evaluating it requires comparing against all other pods, and on large clusters it measurably slows scheduling. **`topologySpreadConstraints` is the modern, cheaper, and more expressive replacement** for the common "spread my replicas out" case (K6.8) — reaching for anti-affinity for that is now dated.
- **`required` anti-affinity with `topologyKey: hostname` caps your replica count at the node count**, and the excess sits Pending forever. A very common self-inflicted Pending (K9.6).
- **Prefer `preferred` unless the constraint is genuinely mandatory**, because hard constraints turn capacity problems into outages.

For GPU and accelerated workloads, node affinity on instance type or accelerator label is how you steer pods onto the right hardware — usually combined with taints so *only* those pods land there (K6.7).

**K6.7 — Taints and tolerations, and how they differ from affinity**

**Taints** are on nodes and **repel** pods. **Tolerations** are on pods and allow them to be scheduled onto tainted nodes anyway.

```bash
kubectl taint nodes gpu-node-1 nvidia.com/gpu=present:NoSchedule
```

```yaml
tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

Effects: **`NoSchedule`** (won't place new pods), **`PreferNoSchedule`** (soft), **`NoExecute`** (won't place, *and evicts existing pods* that don't tolerate it — with `tolerationSeconds` controlling the delay).

**The difference from affinity is the direction of the relationship, and this is the crux:**

- **Affinity is pod-driven attraction** — the pod says where it wants to go. It does *not* stop other pods going there too.
- **Taints are node-driven repulsion** — the node says who's allowed. It excludes everything that doesn't tolerate it.

So they solve different halves of the same problem and are usually used **together**: taint the GPU nodes so ordinary workloads can't land on them and waste expensive capacity, and use node affinity on the GPU workload so it goes there rather than anywhere it merely tolerates. **A toleration alone doesn't attract** — a pod tolerating the GPU taint can still be scheduled onto a cheap CPU node, which is a mistake worth calling out because it silently wastes the reservation.

Kubernetes uses taints internally too: `node.kubernetes.io/not-ready`, `unreachable`, `memory-pressure`, `disk-pressure`, and the control-plane taint. That's the mechanism behind eviction on node failure, and it's why DaemonSets need broad tolerations (K2.9).

**K6.8 — Topology spread constraints**

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway     # or DoNotSchedule
    labelSelector: { matchLabels: { app: api } }
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
    labelSelector: { matchLabels: { app: api } }
```

`maxSkew` is the maximum permitted difference in matching pod count between any two topology domains. With `maxSkew: 1` across three zones and six replicas, you get 2/2/2 rather than 6/0/0.

Why this rather than anti-affinity (K6.6): it's **expressive about degree** rather than binary — "spread evenly" instead of "never co-locate" — it's much cheaper for the scheduler to evaluate, and `whenUnsatisfiable` gives you the crucial choice between "spread if you can" and "fail rather than concentrate".

That choice is the judgement in this item: **`DoNotSchedule` makes the constraint real but turns a capacity shortfall in one zone into Pending pods** (K9.6); **`ScheduleAnyway` keeps you running at the cost of possibly concentrating everything in one zone, which is exactly the resilience property you were trying to buy.** For a critical service where AZ resilience is the point, `DoNotSchedule` on zone is defensible. For most services, `ScheduleAnyway` on zone plus `ScheduleAnyway` on hostname is the pragmatic default.

Two subtleties: **spread is evaluated at scheduling time only**, so a zone outage that reschedules everything into two zones leaves it unbalanced afterwards with no automatic correction. And **`matchLabelKeys`** (newer) lets spread be calculated per Deployment revision, which fixes the annoying behaviour where an old ReplicaSet's pods count toward the new one's skew during a rollout.

This is the direct Kubernetes expression of the multi-AZ design in A11.4, including the N-1 capacity argument.

**K6.9 — PodDisruptionBudgets**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2          # or maxUnavailable: 1
  selector: { matchLabels: { app: api } }
```

A PDB constrains how many pods of a set may be **voluntarily** disrupted at once. `kubectl drain` and the eviction API respect it; if evicting a pod would violate the budget, the eviction is refused and the drain blocks.

**What it protects against**: node drains for maintenance, cluster upgrades (K11.4), autoscaler scale-down (K7.7), Karpenter consolidation. **What it does not protect against**: node failure, OOM kill, spot reclamation, or anything else involuntary (K2.12). This distinction is the item.

The failure modes worth knowing, because they're common and consequential:

- **`minAvailable` equal to the replica count blocks every drain permanently.** A single-replica Deployment with `minAvailable: 1` means that pod can never be voluntarily evicted, so **node drains hang forever and cluster upgrades stall.** This is one of the most common ways an upgrade gets stuck (K11.1), and it's usually written by someone protecting a service without realising they've made the node undrainable.
- **A PDB on a workload that can't reach its target** (pods failing readiness) blocks drains indefinitely, because the budget can never be satisfied.
- **PDBs don't stop the node going away** — a drain that's blocked can be forced, and the underlying instance can be terminated regardless. On spot instances the PDB buys you nothing against reclamation.

The correct pattern: **`maxUnavailable: 1` rather than `minAvailable: N`** for most workloads, because it scales with the replica count and can't accidentally become undrainable. And every workload that matters should have a PDB, because without one the autoscaler and drains treat it as freely disposable.

**K6.10 — Priority classes and preemption**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: { name: critical }
value: 1000000
preemptionPolicy: PreemptLowerPriority
globalDefault: false
```

A pod's `priorityClassName` sets its scheduling priority. Higher-priority pending pods are scheduled first, and if none can fit, the scheduler may **preempt** — evict lower-priority running pods to make room.

Uses: guaranteeing that critical platform components (CNI, CoreDNS, monitoring agents, ingress controllers) can always schedule; letting batch and ML training jobs run at low priority so they're evicted when interactive workloads need capacity, which is the standard pattern for using spare cluster capacity productively.

The cautions:

- **Preemption causes involuntary disruption and ignores PDBs.** The scheduler makes a best effort to respect them but will preempt regardless if it must. So priority can undo the protection you thought a PDB gave.
- **Priority inflation is the predictable organisational failure.** If teams set their own priorities, everything becomes critical and the mechanism is worthless. Priority classes need to be centrally owned and constrained by RBAC or policy (K8.9), with ResourceQuota able to limit which classes a namespace may use.
- **A high-priority pod that can't schedule anywhere will preempt repeatedly and pointlessly**, churning workloads without ever succeeding — a nasty failure mode when the real problem is a constraint no node satisfies (K6.13).
- The built-in `system-cluster-critical` and `system-node-critical` classes exist for the components that must never be evicted.

**K6.11 — Node pressure eviction vs OOM kill**

Two different mechanisms that people conflate:

**Node-pressure eviction** — the **kubelet** monitors node resources (memory, disk, inodes, PIDs) against eviction thresholds. When a soft threshold is crossed for its grace period, or a hard threshold is crossed immediately, the kubelet **selects pods and evicts them** to reclaim resources, ordered by QoS class and usage relative to requests (K6.4). The pod is deleted with reason `Evicted` and a message naming the pressure, and — crucially — **it's a pod-level, graceful action**, and the pod is rescheduled elsewhere.

**cgroup OOM kill** — the **kernel** kills a process because its cgroup exceeded its memory limit (K6.3). Container-level, immediate, ungraceful, exit code 137, reason `OOMKilled`, and the kubelet restarts the container in place per the restart policy.

Telling them apart matters diagnostically:

- **`OOMKilled`** → *this container* exceeded *its own* limit. Look at the application and its limit (K9.8).
- **`Evicted` with a memory-pressure message** → *the node* ran out, and this pod may have been an innocent bystander chosen by QoS ranking. Look at what else is on the node and at whether requests across the node are honest.
- **Disk-pressure eviction** is the underrated one: caused by image accumulation, container logs, or `emptyDir` growth (K5.7). It evicts pods that may be using no disk at all, and the fix is usually log rotation or garbage collection settings, not the workload.

The prevention: accurate requests (K6.5), `--system-reserved` and `--kube-reserved` so system daemons aren't starved by pods, and monitoring node conditions (`MemoryPressure`, `DiskPressure`) rather than only pod-level metrics (K9.14).

**K6.12 — ResourceQuotas and LimitRanges**

**ResourceQuota** — namespace-scoped caps on aggregate consumption: total CPU/memory requests and limits, object counts (pods, Services, PVCs, LoadBalancers), and storage per StorageClass.

```yaml
kind: ResourceQuota
spec:
  hard:
    requests.cpu: "50"
    requests.memory: 100Gi
    limits.memory: 200Gi
    persistentvolumeclaims: "20"
    count/services.loadbalancers: "2"
```

**LimitRange** — per-object defaults and bounds within a namespace: default requests/limits applied to containers that specify none, plus min and max.

They work together, and the interaction is the detail worth knowing: **once a ResourceQuota on `requests.cpu` exists, every pod in the namespace must specify a request or it is rejected.** That would break every existing manifest that omits them — which is exactly what a LimitRange prevents, by injecting defaults. So deploying a quota without a LimitRange is a reliable way to break a namespace's deployments with a confusing admission error.

Uses in multi-tenancy (K13.3): capping a team's total footprint so one namespace can't consume the cluster, limiting expensive object types (LoadBalancers, PVCs), and — with LimitRange — ensuring nothing lands as BestEffort (K6.4).

The limits of the mechanism: quotas constrain *requests*, not usage, so a namespace can be well within quota and still cause node-level problems if requests are under-set. And quota is not isolation — it's a budget, not a boundary (K8.10).

**K6.13 — Diagnosing a pod that won't schedule**

```bash
kubectl describe pod <pod> | tail -20     # Events is where the answer is
kubectl get events --sort-by=.lastTimestamp
```

The scheduler writes a `FailedScheduling` event that **names the reason per node**, which is the single most useful output in this whole area:

```
0/12 nodes are available: 3 Insufficient cpu, 4 node(s) had untolerated taint
{gpu: true}, 5 node(s) didn't match Pod's node affinity/selector.
```

Reading that tally tells you which constraint eliminated which nodes, and the fix follows directly. The checklist, in the order the scheduler applies it:

1. **Insufficient resources** — requests exceed any node's allocatable (K6.1). Note *allocatable*, not capacity: system reservations mean a node with 4 CPU offers less. A pod requesting more than the largest node can ever provide will never schedule, no matter how many nodes you add.
2. **Untolerated taints** (K6.7) — very common with GPU or dedicated node pools.
3. **Node affinity or selector matched nothing** (K6.6) — often a label typo or a node pool that no longer exists.
4. **Pod anti-affinity** — especially `required` with hostname topology and more replicas than nodes (K6.6).
5. **Topology spread with `DoNotSchedule`** and no room in the under-filled domain (K6.8).
6. **Volume constraints** — zone mismatch or an attached volume (K5.9).
7. **Nothing wrong, no capacity** — the autoscaler should react; if it doesn't, that's K7.9.
8. **Quota rejection** — this one fails at *admission*, not scheduling, so there's no pod at all and the error is on the ReplicaSet. `kubectl describe replicaset` is where it shows, which is why "my Deployment created no pods" is a distinct symptom from "my pod is Pending".

The discipline: **read the event tally before forming a hypothesis.** It's one of the few places Kubernetes tells you the answer directly, and people skip it and start guessing.

---

## K7. Autoscaling

Three orthogonal axes, and being clear about which one is which is half the section: **HPA scales replica count**, **VPA scales per-pod resources**, **Cluster Autoscaler and Karpenter scale nodes**.

**K7.1 — HPA on CPU and on custom metrics**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: api }
  minReplicas: 3
  maxReplicas: 30
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 70 }
    - type: Pods
      pods:
        metric: { name: http_requests_per_second }
        target: { type: AverageValue, averageValue: "100" }
    - type: External
      external:
        metric:
          name: sqs_queue_depth
          selector: { matchLabels: { queue: payments } }
        target: { type: AverageValue, averageValue: "30" }
```

The algorithm: `desiredReplicas = ceil(currentReplicas × (currentMetric / targetMetric))`. With multiple metrics, **the HPA computes a replica count for each and takes the highest** — so metrics are a safety union, not a blend.

Requirements: **metrics-server** for `Resource` metrics; **Prometheus Adapter or KEDA** for custom and external metrics. KEDA is worth naming specifically — it provides scalers for dozens of event sources (SQS, Kafka, Redis, Azure queues) and supports scale-to-zero (K7.8), which plain HPA cannot do.

The judgement point mirrors A4.3: **scale on the metric that reflects the bottleneck.** CPU is the default and frequently wrong. For a queue consumer, **queue depth per replica** is correct and CPU is nearly meaningless — a worker blocked on I/O uses no CPU while the backlog grows unboundedly. For a latency-sensitive API, requests-per-second per pod or in-flight concurrency tracks capacity better than CPU. Being able to say "we scaled on SQS depth because the workers were I/O-bound and CPU never moved" is a much stronger answer than reciting the HPA spec.

**K7.2 — Why HPA needs requests set**

`averageUtilization` is a **percentage of the pod's CPU request** — not of the node's capacity, and not of the limit. So:

- **No CPU request → no utilisation figure → the HPA cannot compute anything.** It reports `<unknown>` for the metric and does not scale at all. Silently doing nothing is the failure mode: the HPA object exists, looks configured, and never acts.
- **A wrong request skews the target proportionally.** If a pod requests 100m and typically uses 400m, its utilisation is 400% and the HPA scales out immediately and hits `maxReplicas`. If it requests 2 CPU and uses 200m, utilisation is 10% and it never scales even under load.

So **HPA correctness depends entirely on request accuracy** (K6.5), which is the coupling that makes this item worth asking. It's also the root of the VPA conflict (K7.4): VPA changes requests, which changes the denominator the HPA is dividing by, and the two chase each other.

Using `AverageValue` rather than `Utilization` targets absolute values and sidesteps the request dependency — often the more predictable choice for custom metrics.

**K7.3 — Stabilisation and thrashing**

Thrashing is scaling out, then in, then out again on a metric that oscillates — each cycle costing pod startup time, connection churn, and possibly node churn behind it.

```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300
    policies:
      - type: Percent
        value: 50
        periodSeconds: 60
  scaleUp:
    stabilizationWindowSeconds: 0
    policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 4
        periodSeconds: 30
    selectPolicy: Max
```

The **stabilisation window** makes the HPA use the *highest* recommendation over the window when scaling down (and lowest when scaling up), so a brief dip doesn't trigger a scale-in. Default is 300s down, 0s up.

The asymmetry is the design principle worth articulating: **scale up fast, scale down slowly.** The cost of scaling up too eagerly is some wasted capacity for a few minutes. The cost of scaling down too eagerly is an outage when load returns before the pods do. Those risks are not symmetric, so the response shouldn't be either.

Other causes of thrashing: **a metric that lags the load** — CPU rises only after requests queue, so scaling is always behind, which is an argument for a leading indicator like queue depth or concurrency. And **slow pod startup** relative to the scaling interval means the HPA scales again before the previous pods are serving, over-provisioning badly. That's the same warm-up problem as A4.3, and the mitigation is the same: make the reaction interval longer than the time-to-useful.

**K7.4 — VPA, and why it conflicts with HPA**

VPA observes actual usage and adjusts **requests and limits** — either recommending (`updateMode: Off`), applying on pod recreation (`Initial`), or evicting and recreating pods to apply new values (`Auto`).

**The conflict**: HPA on CPU or memory utilisation divides usage by the *request* (K7.2). VPA *changes the request*. So VPA raises the request → measured utilisation drops → HPA scales in → the remaining pods work harder → VPA raises requests again. The two controllers fight over the same signal with no coordination, and the result is oscillation in both dimensions.

**They can coexist safely when they act on different resources**: VPA managing memory while HPA scales on CPU, or HPA scaling on a custom metric (requests per second, queue depth) that VPA doesn't influence at all. That second case is the clean pattern and worth stating as the resolution rather than just naming the conflict.

The other VPA cautions: **`Auto` mode evicts pods to resize them**, which is voluntary disruption — it respects PDBs (K6.9), but it means unexpected restarts, and for stateful or long-running workloads that's often unacceptable. In-place resize is arriving in newer Kubernetes and changes this materially, which is worth mentioning as current awareness.

**The highest-value use of VPA is `updateMode: Off`** — run it purely as a recommender, and feed its numbers into your manifests through a normal review process (K6.5). You get measurement-driven requests without handing a controller the right to restart your pods.

**K7.5 — Cluster Autoscaler behaviour**

**Scale-up**: watches for pods that are **Pending due to insufficient resources**. It simulates whether adding a node from a configured node group would let the pod schedule, and if so increases that group's size. Note the trigger — **Pending pods**, not high utilisation. A cluster at 95% utilisation with everything scheduled will not scale up.

**Scale-down**: a node is a candidate when its utilisation (sum of requests, not usage) is below a threshold (default 50%) for a period (default 10 minutes), and all its pods could be rescheduled elsewhere. It then drains and terminates the node.

The characteristics that define its behaviour, and the limits that Karpenter addresses:

- **It works through node groups (ASGs).** You predefine the instance types; CA only chooses which group to grow. Getting good instance-type diversity means many node groups, and CA assumes nodes within a group are identical — a mixed-instance ASG with different shapes breaks its simulation.
- **Scale-up is slow**: detect Pending → decide → ASG launches → node boots → joins → kubelet ready → pod schedules. Several minutes, which is a real problem for spiky workloads. **Over-provisioning with low-priority placeholder pods** (K6.10) is the standard trick — pause pods that get preempted by real workloads, so capacity is already warm.
- **It uses requests, not usage**, so a cluster full of over-requested pods never scales down.

**K7.6 — Karpenter's model, and when it's preferable**

Karpenter watches Pending pods and **provisions individual nodes directly from the cloud API**, choosing the instance type from a broad set based on what the pending pods actually require — rather than picking from predefined node groups.

The differences that matter:

- **No node groups to predefine.** You express constraints (instance families, architectures, zones, capacity type) in a NodePool, and Karpenter selects. Adding GPU workloads doesn't require designing a new ASG.
- **Better bin-packing** — it can provision a node sized for the pending pods rather than the nearest predefined shape.
- **Faster** — it goes straight to the cloud API rather than through an ASG.
- **Consolidation** — it actively repacks workloads onto fewer nodes and removes the emptied ones, and it will replace a node with a cheaper one that still fits. This is a continuous cost optimisation rather than a threshold-triggered scale-down, and it's the feature that produces a measurable saving (A12.7).
- **Spot handling is much better** — broad instance-type diversification is natural, which is exactly what makes Spot reliable (A4.5), and it handles interruption notices.

**When it's preferable**: essentially any cluster with varied workload shapes, cost sensitivity, or a need for Spot. It's the current default recommendation on EKS (A5.5).

**The cost, stated honestly**: node lifecycle becomes much more dynamic. Consolidation means pods get moved regularly, so workloads must genuinely tolerate disruption — correct PDBs (K6.9), graceful SIGTERM handling, and no hidden assumptions about node longevity. Karpenter surfaces every workload that quietly assumed it would never be rescheduled. The failure pattern to warn about: teams respond by annotating everything `karpenter.sh/do-not-disrupt`, which disables the consolidation you adopted it for and leaves you with a cluster that can't be right-sized or upgraded (K11.4). Also, `expireAfter` for node rotation is a genuine security and patching benefit — nodes are replaced regularly rather than aging indefinitely.

**K7.7 — What blocks a node from scaling down**

The standard list, and it's a good one to know cold because "why won't my cluster scale down" is a common real question:

- **Pods with no controller** — bare pods (K2.1) can't be safely rescheduled, so the node stays.
- **Pods with local storage** — `emptyDir` or hostPath, whose data would be lost. Overridable with the `safe-to-evict` annotation.
- **PodDisruptionBudgets that would be violated** (K6.9) — including the permanently-blocking single-replica case.
- **DaemonSet pods** are ignored by default (they're expected everywhere), but a misconfiguration can make them count.
- **Pods in `kube-system` without a PDB** — CA is conservative about system components.
- **Pods that can't be rescheduled elsewhere** — no other node satisfies their affinity, taints, or resource requests. Which means a single awkward pod pins an entire expensive node.
- **The `cluster-autoscaler.kubernetes.io/safe-to-evict: "false"` annotation**, which people set and forget.
- **Node utilisation above the threshold** because of *requests*, even when actual usage is near zero (K6.1).
- **Scale-down disabled** on the node group, or `minSize` already reached.

The diagnostic: **Cluster Autoscaler logs state the reason per node**, and the `cluster-autoscaler-status` ConfigMap summarises. Karpenter similarly logs why a node isn't consolidatable. Read those rather than guessing — same discipline as K6.13.

The pattern worth naming: **one long-running pod with local storage or a restrictive PDB, spread randomly across the fleet, prevents any node from emptying**, so the cluster never shrinks and you pay for permanently half-empty nodes. The fix is usually to concentrate such workloads deliberately (affinity to a specific pool) rather than let them scatter.

**K7.8 — Scale-to-zero and the cold-start tradeoff**

Plain HPA cannot scale below 1. The options:

- **KEDA** — scales to zero based on an event source (queue depth, Kafka lag, cron, HTTP via an add-on). When work arrives, it scales to 1 and hands over to a normal HPA. The mainstream answer for event-driven workloads.
- **Knative Serving** — request-driven scale-to-zero for HTTP, with an activator buffering the first request while a pod starts.
- **Karpenter** — scaling the *nodes* to zero when a pool is empty, which is what actually saves money.

The tradeoff: **the first request after scaling from zero pays the full cold-start cost** — node provisioning if none is warm (minutes), image pull if not cached (tens of seconds for a large image), container start, and application warm-up. For an ML inference service with a multi-gigabyte image and model loading, that can be minutes, which is unacceptable for a synchronous API.

Where it's right: **asynchronous and batch work**, where latency on the first item doesn't matter — queue consumers, scheduled processing, dev and preview environments, and internal tools with long idle periods. Where it's wrong: user-facing synchronous APIs, unless you accept a request-buffering layer and the tail latency.

The middle grounds worth naming: **minimum replicas of 1 with aggressive node consolidation**, so you pay for one small pod rather than a warm node pool; **pre-pulled images** and smaller images to shrink cold start; and **scheduled scaling** to zero out of hours rather than continuously, which captures most of the saving with none of the request-path risk. For non-production environments, scheduled scale-down is the highest-value, lowest-risk version of this and a good cost story (A12.3).

**K7.9 — Diagnosing why autoscaling isn't happening**

Work down the chain, because the failure can be at any layer:

**HPA not scaling:**

1. `kubectl describe hpa` — **the metric column showing `<unknown>` is the most common cause**, and it means either metrics-server isn't running or the pods have no CPU request (K7.2).
2. **Is metrics-server healthy?** `kubectl top pods` failing tells you immediately.
3. **For custom metrics**, is the adapter serving them? `kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1` and check the metric name matches exactly.
4. **Already at `maxReplicas`** — the HPA reports this in conditions and people miss it.
5. **Stabilisation window** still holding a previous recommendation (K7.3).
6. **The metric genuinely isn't moving** — the classic being a queue-backed worker scaled on CPU, where the backlog grows and CPU doesn't (K7.1).
7. **Scaled but nothing changed** — pods created and stuck Pending, which is a cluster capacity problem, not an HPA problem.

**Cluster not scaling:**

1. **Are there actually Pending pods?** CA only reacts to those (K7.5). High utilisation with everything scheduled triggers nothing.
2. **`kubectl describe pod`** on the Pending pod — if it's Pending due to a taint, affinity, or volume zone rather than resources (K6.13), no new node will help and CA won't try.
3. **CA logs** — they state whether it considered scaling and why it didn't. Often: no node group can satisfy the pod, or the group is at `maxSize`.
4. **Cloud-side limits** — ASG max, **EC2 vCPU quota** (A11.9), insufficient capacity for the instance type in that AZ, or subnet IP exhaustion (A5.7). These present as CA trying and the node never appearing, which is a different signature from CA not trying.
5. **IAM permissions** on the autoscaler's role.

**Not scaling down**: K7.7.

The habit worth stating: **`kubectl describe hpa` and the autoscaler logs both explain themselves.** Nearly every autoscaling investigation is answered by reading them, and the common error is inferring from dashboards instead.

---

## K8. Security & RBAC

**K8.1 — Role, ClusterRole, RoleBinding, ClusterRoleBinding**

- **Role** — permissions **within one namespace**.
- **ClusterRole** — permissions cluster-wide, and also the way to grant on **cluster-scoped resources** (nodes, PVs, namespaces, CRDs) and on non-resource URLs (`/healthz`).
- **RoleBinding** — grants a Role **or a ClusterRole** to subjects, **scoped to one namespace**.
- **ClusterRoleBinding** — grants a ClusterRole cluster-wide.

The combination people find confusing and that interviewers probe: **a RoleBinding referencing a ClusterRole grants that ClusterRole's permissions only within the binding's namespace.** That's the idiomatic pattern — define `view`, `edit`, and `admin` once as ClusterRoles, then bind them per namespace. It avoids duplicating a Role into every namespace.

Other essentials:

- **RBAC is purely additive. There is no deny.** Permissions are the union of all bindings for a subject; you cannot subtract. This is a real modelling constraint compared with IAM (A2.3) — if you need "everything except X", you enumerate everything else, or you use admission policy (K8.9) to impose the restriction.
- **Subjects** are Users, Groups, and ServiceAccounts. Users and Groups aren't Kubernetes objects — they're assertions from the authenticator (a certificate CN/O, an OIDC claim, or an AWS identity mapping, A5.8), which is why you can't `kubectl get users`.
- **Built-in ClusterRoles** — `view`, `edit`, `admin`, `cluster-admin`. Note that `view` **excludes Secrets** deliberately, and that `edit` includes creating pods, which is effectively secret access (K3.4, K8.12).

**K8.2 — A least-privilege Role for a stated requirement**

Requirement: *a CI service account may deploy to the `payments` namespace and check rollout status, nothing more.*

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: { name: deployer, namespace: payments }
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "patch", "update"]
  - apiGroups: ["apps"]
    resources: ["deployments/status", "replicasets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods", "events"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
```

The method: enumerate the **API group, resource, and verbs** for each operation the workload actually performs. Note `""` is the core group, subresources are their own resource string (`pods/log`, `deployments/status`, `pods/exec`), and `watch` is needed separately from `list` for anything that streams.

Things that demonstrate care:

- **No `create` or `delete` on Deployments** — the CI account patches existing ones, so it can't create arbitrary workloads or delete the app.
- **`pods/log` but not `pods/exec`** — reading logs is diagnostic, exec is a shell into production.
- **Nothing on Secrets**, and no `create pods` — which would be an escalation route (K8.12).
- **Avoid wildcards.** `verbs: ["*"]` or `resources: ["*"]` in a Role is the equivalent of `Action: "*"` in IAM (A2.2), and it silently grants permissions on resources added later by CRDs.
- **Verify with `kubectl auth can-i`** (K8.5) rather than assuming.

**K8.3 — ServiceAccounts and how a pod gets an identity**

Every pod runs as a ServiceAccount — the namespace's `default` if none is specified. The SA is the pod's identity to the API server, and RBAC bindings target it as `system:serviceaccount:<namespace>:<name>`.

The mechanism: a **projected token** is mounted at `/var/run/secrets/kubernetes.io/serviceaccount/token`, along with the CA certificate and namespace. Client libraries read it automatically.

The practices that matter:

- **Never use the `default` ServiceAccount for workloads.** Create one per application. The default is shared by everything in the namespace, so any binding to it grants every pod there — and it's the account that quietly accumulates permissions.
- **Set `automountServiceAccountToken: false`** on pods that don't call the API server, which is most application pods. Without it, every pod carries a valid API token that an attacker can use after compromising the container (K8.12). This is a cheap, high-value hardening step that almost nobody does.
- **The token identifies the pod's SA, not the pod**, so all pods sharing an SA are indistinguishable to RBAC.

**K8.4 — Projected tokens and workload identity federation**

**Legacy** behaviour: creating a ServiceAccount auto-created a Secret containing a **non-expiring, non-audience-bound JWT**. If that token leaked it was valid forever, and it sat in etcd. Removed in recent versions.

**Bound service account tokens** (the current model): tokens are **projected volumes**, and they are:

- **Time-limited**, refreshed automatically by the kubelet.
- **Audience-bound** — a token issued for one audience is rejected elsewhere.
- **Object-bound** — tied to the specific pod, so it's invalid once that pod is gone.

**Workload identity federation** builds on this: the cluster exposes an **OIDC discovery endpoint**, an external system (AWS IAM, GCP, Vault) trusts it as an identity provider, and the pod exchanges its projected token for external credentials. On AWS that's **IRSA**, with the trust policy conditioning on the OIDC issuer plus the `sub` claim (`system:serviceaccount:<ns>:<sa>`) and the audience — the full mechanism, including the wildcard-`sub` mistake, is A2.7. **EKS Pod Identity** is the newer alternative with a different trust model.

Why it matters as a concept rather than an AWS detail: **it eliminates static cloud credentials from the cluster entirely.** No access keys in Secrets, no long-lived tokens, and the identity is per-ServiceAccount so permissions are per-workload rather than per-node. The pattern generalises — Vault's Kubernetes auth method works the same way — and it's the right answer to "how does my pod authenticate to anything outside the cluster".

**K8.5 — `kubectl auth can-i`**

```bash
kubectl auth can-i create deployments --namespace payments
kubectl auth can-i get secrets --all-namespaces

# check on behalf of another subject (needs impersonation rights)
kubectl auth can-i list pods -n payments \
  --as=system:serviceaccount:ci:deployer

kubectl auth can-i --list --as=system:serviceaccount:ci:deployer -n payments
```

Why it's the right tool: it asks the **API server** to evaluate the actual RBAC rules for a subject, rather than you reading YAML and reasoning about the union of bindings. With RBAC being purely additive across potentially many bindings (K8.1), manual reasoning is unreliable — this is the equivalent of the IAM policy simulator (A2.4).

Uses: verifying a Role does what you intended after writing it (K8.2), confirming a service account *cannot* do something as a negative test, and auditing — `--list` for a subject enumerates everything it can do, which is how you check for accidental over-grant.

Two notes: `--as` requires impersonation permission, which is itself a powerful privilege worth restricting. And `can-i` answers **authorisation only** — a request can still be rejected by admission control (K8.8) afterwards, so a `yes` doesn't guarantee the operation succeeds.

**K8.6 — Pod Security Admission and how it replaced PSPs**

**PodSecurityPolicies** were removed in 1.25. They were an admission controller with cluster-scoped policy objects selected via RBAC — and they were genuinely difficult: the selection mechanism was confusing (which policy applies when several match?), they could mutate pods in surprising ways, and getting them working was a well-known source of pain.

**Pod Security Admission** is the built-in replacement, and it's deliberately simpler: three **standards** applied at the **namespace** level via labels.

- **`privileged`** — unrestricted.
- **`baseline`** — blocks known privilege escalations: host namespaces, privileged containers, hostPath, most added capabilities.
- **`restricted`** — hardened: non-root required, `allowPrivilegeEscalation: false`, seccomp profile set, all capabilities dropped except `NET_BIND_SERVICE`, read-only root filesystem encouraged.

Three **modes**, and this is the part that makes rollout practical:

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

`enforce` rejects, `audit` records to the audit log, `warn` returns a warning to the user. So you **enforce baseline while auditing restricted**, see what would break, then promote — the same measure-then-enforce discipline as A1.11 and K4.10.

The limitation to name: **PSA only does the built-in standards.** It cannot express custom rules — required labels, allowed registries, mandatory resource limits. For those you need a policy engine (K8.9), and most real clusters run both: PSA for the pod-hardening baseline, Kyverno or Gatekeeper for organisational policy.

**K8.7 — securityContext**

```yaml
spec:
  securityContext:              # pod level
    runAsNonRoot: true
    runAsUser: 10001
    fsGroup: 10001
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: app
      securityContext:          # container level — overrides pod level
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        privileged: false
        capabilities:
          drop: ["ALL"]
```

What each buys:

- **`runAsNonRoot` / `runAsUser`** — a container escape lands as an unprivileged user rather than root on the node. `runAsNonRoot` is the safer of the two because it fails the pod if the image's user is root, rather than silently relying on the image being built correctly.
- **`readOnlyRootFilesystem`** — the container can't modify its own filesystem, which blocks a large class of attacker tooling and persistence. Requires `emptyDir` mounts for anything genuinely needing to write (`/tmp`, caches), which is the friction people hit.
- **`allowPrivilegeEscalation: false`** — sets `no_new_privs`, blocking setuid binaries from gaining privileges.
- **`capabilities: drop: ["ALL"]`** — start from nothing and add back only what's needed (`NET_BIND_SERVICE` for ports below 1024, though the better answer is to listen on a high port).
- **`seccompProfile: RuntimeDefault`** — restricts available syscalls, reducing kernel attack surface.

The practical points: **these belong in the manifest, but enforcing them requires PSA or policy** (K8.6, K8.9), or people simply omit them. **`fsGroup` matters for volume permissions** — a non-root container often can't write to a mounted volume without it, and that's the most common reason a hardened pod fails. And image build and runtime hardening are two halves of the same job (D-domain and S7): a distroless, non-root image makes `runAsNonRoot` trivial, and a container that insists on root is usually a build problem.

**K8.8 — Admission control: validating vs mutating**

Admission runs **after** authentication and authorisation, **before** persistence (K1.9).

- **Mutating webhooks run first** and can modify the object — injecting sidecars (service mesh, K4.13), adding default labels or annotations, setting default resources, injecting secrets volumes (K3.6).
- **Validating webhooks run second** and can only accept or reject — enforcing policy (K8.9), schema constraints, organisational rules.

Mutating runs first so that validation sees the final object, which is the right ordering and worth being able to explain.

The operational risks, which are the substance of this item:

- **`failurePolicy: Fail` means an unavailable webhook blocks the operations it matches.** If the webhook's own pods are down and its rule matches all pods in all namespaces, **you cannot create any pod anywhere — including the webhook's own replacement pods.** That is a genuine, well-known way to brick a cluster, and recovery means deleting the webhook configuration via the API directly.
- **`failurePolicy: Ignore`** avoids that but means your security control silently stops enforcing during an outage — the same false-assurance shape as K4.11.
- **Mitigations**: scope `namespaceSelector` to exclude `kube-system` and the webhook's own namespace, run the webhook HA with a PDB, set sane `timeoutSeconds`, and monitor webhook latency — because **every matched API call now waits on your webhook**, so a slow webhook slows the whole cluster (K1.3).
- **Validating Admission Policy** (CEL-based, in-tree) is the newer alternative for simple rules and removes the availability dependency entirely, since there's no external webhook to be down. Worth naming as the current direction.

**K8.9 — Policy engines: OPA/Gatekeeper and Kyverno**

Both are admission webhooks that enforce organisational policy.

- **Gatekeeper** — policies in **Rego** via ConstraintTemplates and Constraints. Very expressive; Rego is a real learning curve.
- **Kyverno** — policies as **YAML**, Kubernetes-native. Much lower barrier, and it can **mutate** and **generate** resources as well as validate — for instance, automatically creating a default NetworkPolicy and ResourceQuota in every new namespace (K4.10, K6.12), which is a genuinely useful capability beyond validation.

A representative Kyverno policy:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: { name: require-resources }
spec:
  validationFailureAction: Audit      # then Enforce
  rules:
    - name: check-resources
      match:
        any:
          - resources: { kinds: [Pod] }
      validate:
        message: "CPU and memory requests are required."
        pattern:
          spec:
            containers:
              - resources:
                  requests:
                    memory: "?*"
                    cpu: "?*"
```

Typical policies: require resource requests, require probes, restrict image registries to your own (S7), block `:latest` tags, require specific labels for ownership and cost attribution (A12.2), disallow `hostNetwork` and `hostPath`, require PDBs on production Deployments, block `Delete` reclaim policy on production StorageClasses (K5.4).

The rollout discipline is the same as everywhere else in governance: **`Audit` first, measure what would break, then `Enforce`** (A1.11, K8.6). And the same availability caution as K8.8 applies — a policy engine in the admission path is a cluster-critical component.

The relationship to PSA (K8.6): PSA covers the standard pod-hardening baseline cheaply and without a webhook; a policy engine covers everything organisation-specific. Use both.

**K8.10 — Namespace isolation and its limits**

**What a namespace gives you**: a scope for names, a boundary for RBAC (K8.1), a unit for ResourceQuota and LimitRange (K6.12), a target for NetworkPolicy selectors (K4.10), and a scope for PSA labels (K8.6).

**What it does not give you** — which is the point of the item:

- **No network isolation by default.** Every pod can reach every other pod across namespaces unless NetworkPolicy says otherwise (K4.1), and that requires CNI support (K4.11).
- **No node isolation.** Pods from different namespaces share nodes, so they share a kernel. **A container escape crosses namespaces trivially** because the namespace boundary is an API-server concept with no runtime enforcement.
- **No control plane isolation.** All namespaces share one API server and one etcd, so a noisy tenant can degrade everyone (K1.3), and CRDs, admission webhooks, and the API version are cluster-wide.
- **Not all resources are namespaced.** Nodes, PVs, StorageClasses, ClusterRoles, and CRDs are cluster-scoped, so a tenant with any cluster-scoped permission affects everyone.

The conclusion to state plainly: **namespaces are an organisational and RBAC boundary, not a security boundary between untrusted parties.** They're fine for separating trusted teams within one organisation with policy and quota applied. They are **not** sufficient for hostile multi-tenancy — for that you need separate clusters, or at minimum stronger runtime isolation (gVisor, Kata Containers, dedicated node pools per tenant with taints). That maps directly onto K11.7 and K13.3.

**K8.11 — cluster-admin sprawl and auditing it**

`cluster-admin` is unrestricted: every verb on every resource in every namespace, including reading all Secrets, modifying RBAC, and creating privileged pods. It's the equivalent of AWS `AdministratorAccess` (A2.11), with the same organisational dynamic — granted during an incident or an onboarding, never removed.

**Auditing it:**

```bash
# who holds cluster-admin directly
kubectl get clusterrolebindings -o json \
  | jq -r '.items[] | select(.roleRef.name=="cluster-admin")
           | "\(.metadata.name): \([.subjects[]?|"\(.kind)/\(.name)"]|join(", "))"'

# broader: any ClusterRole with wildcard verbs
kubectl get clusterroles -o json \
  | jq -r '.items[] | select(.rules[]? | (.verbs[]?=="*") and (.resources[]?=="*"))
           | .metadata.name'
```

The subtleties that make a superficial audit miss things:

- **Equivalent-to-admin roles.** A ClusterRole with `["*"]` on `["*"]` isn't named cluster-admin but is identical. And several narrower permissions are effectively admin: `escalate` and `bind` (grant yourself anything), `impersonate` (become anyone), `create` on ClusterRoleBindings, and `get secrets` cluster-wide.
- **ServiceAccounts, not just humans.** Operators and CI accounts routinely hold cluster-admin because it was the fast way to make them work, and they're long-lived, unattended, and rarely reviewed. This is usually where the real sprawl is (K12.3).
- **Group bindings** hide the actual population — a binding to a group that maps to an entire engineering org.
- **On EKS**, access entries and the legacy `aws-auth` mapping are the other half of the picture (A5.8), including the historical implicit cluster-admin for the cluster creator.

The remediation, mirroring A2.11: inventory and attribute, replace standing access with **just-in-time elevation** (a break-glass path that's audited and alarmed), scope operators down from cluster-admin to the resources they actually reconcile, and **alarm on any use of the break-glass role**. And make the audit recurring rather than one-off, because sprawl regrows.

**K8.12 — How an attacker moves from a compromised pod to the cluster**

The escalation chain, which is worth being able to walk because it explains *why* each of the preceding controls exists:

1. **Initial access** — an application vulnerability (RCE, SSRF, deserialisation) gives code execution in the container.
2. **Reconnaissance from inside** — read the mounted **ServiceAccount token** (K8.3), enumerate what it can do (`kubectl auth can-i --list`), read environment variables and mounted Secrets and config, and probe the network — which is flat by default (K4.1), so every other pod and internal service is reachable.
3. **Cloud metadata** — reach `169.254.169.254` for the **node's instance role credentials** (A2.6). If IMDSv2 with a hop limit isn't enforced, this is often the highest-value step, because node roles are typically far more privileged than pod roles.
4. **RBAC escalation** — if the SA can `create pods`, create a privileged pod with `hostPID`, `hostNetwork`, and the host filesystem mounted. If it can `get secrets`, harvest credentials. If it can `create` ClusterRoleBindings or has `escalate`, grant itself cluster-admin directly.
5. **Container escape** — a privileged container, a `hostPath` mount of `/`, a writable Docker socket, or a kernel vulnerability gives root on the **node**.
6. **From node to cluster** — the node's kubelet credentials, every Secret of every pod on that node, and the node's cloud identity. From there, lateral movement to other nodes and to the cloud account (A10.30).

**The controls that break the chain**, mapped to the steps: `automountServiceAccountToken: false` and least-privilege SAs (K8.3, K8.2) break step 2; IMDSv2 with hop limit 1 plus IRSA instead of node roles (A2.7) breaks step 3; tight RBAC with no `create pods` for application SAs breaks step 4; PSA `restricted` and securityContext (K8.6, K8.7) break step 5; NetworkPolicy default-deny (K4.10) constrains lateral movement throughout; and runtime detection (Falco) plus audit logging (K8.13) gives you the chance to notice.

The framing that lands: **the pod is not a security boundary, the node is barely one, and the cluster is only a boundary if you configured it to be.** Defence in depth here is a chain of specific controls, each of which is individually cheap and commonly omitted.

**K8.13 — Audit logging and what to capture**

The API server's audit log records every request, at a configurable level per rule:

- **`None`** — don't log.
- **`Metadata`** — who, what, when, from where, and the outcome. No bodies.
- **`Request`** — plus the request body.
- **`RequestResponse`** — plus the response body.

A sensible policy shape:

```yaml
rules:
  # never log secret contents
  - level: Metadata
    resources: [{ group: "", resources: ["secrets", "configmaps"] }]
  # full detail on RBAC changes
  - level: RequestResponse
    resources: [{ group: "rbac.authorization.k8s.io", resources: ["*"] }]
  # exec and port-forward — always
  - level: Request
    resources: [{ group: "", resources: ["pods/exec", "pods/portforward"] }]
  # drop the noise
  - level: None
    users: ["system:kube-scheduler", "system:kube-controller-manager"]
  - level: Metadata
    omitStages: ["RequestReceived"]
```

What you want captured, and why:

- **`pods/exec` and `pods/portforward`** — someone getting a shell in production. The highest-signal event in the log.
- **Secret reads** — at `Metadata` level only, so you know *who read what* without writing the values into the log (which would make the log itself a credential store).
- **RBAC changes** at full detail — privilege grants are the thing you most need to reconstruct after an incident.
- **Failed authorisation** (`Forbidden`) — reconnaissance signal (K8.12).
- **Workload creation** with privileged securityContext or host mounts.
- **Anything from anonymous or unexpected identities.**

The operational points: **exclude the high-volume system components** or the log is unusable and expensive — the control plane's own controllers generate the overwhelming majority of requests. **Ship it off-cluster** to a store the cluster's own compromise can't reach, which is the same argument as the log archive account (A1.16). On EKS, audit logs go to CloudWatch Logs and need to be enabled explicitly — they're **off by default**, so the answer to "who deleted that" is often "we don't know". And **the reason to configure this before you need it** is that audit logging is retrospective only: you cannot enable it after the incident and learn what happened.

---

## K9. Observability & debugging

The section that matters most in interviews. The general troubleshooting discipline is T1; what follows is that discipline applied to Kubernetes' specific failure signatures.

**K9.1 — kubectl fluency**

```bash
kubectl get pods -o wide                      # node, IP, restarts
kubectl get pods -w                           # watch state changes live
kubectl get pods -A --field-selector status.phase!=Running
kubectl get pods -l app=api -o jsonpath='{.items[*].spec.nodeName}'

kubectl describe pod <pod>                    # Events at the bottom (K9.2)
kubectl logs <pod> -c <container> -f --tail=100
kubectl logs <pod> --previous                 # the crashed instance (K9.3)
kubectl logs -l app=api --max-log-requests=10 # across all matching pods

kubectl exec -it <pod> -c <container> -- sh
kubectl port-forward pod/<pod> 8080:8080      # bypass Service and Ingress
kubectl port-forward svc/<svc> 8080:80        # test through the Service

kubectl top nodes
kubectl top pods --sort-by=memory -A

kubectl get events -A --sort-by=.lastTimestamp | tail -30
kubectl api-resources                          # what exists, and is it namespaced
kubectl explain deployment.spec.strategy       # schema, offline
```

Fluency markers beyond the basics: `-o jsonpath` and `-o custom-columns` for extracting specific fields; `--field-selector` for server-side filtering (the same distinction as A14.1 — `--field-selector` filters at the API server, `-o jsonpath` filters after transferring everything); `-w` to watch a rollout progress; `kubectl explain` for schema without documentation; and `--context` discipline so you know which cluster you're pointed at. That last one is a genuine safety control — the Kubernetes equivalent of `AWS_PROFILE` (A14.2), and running a destructive command against the wrong cluster is a recurring cause of self-inflicted incidents. Tools like `kubectx`/`kubens` and a shell prompt showing the current context are worth mentioning.

**K9.2 — Reading `describe` output and finding the answer in Events**

`kubectl describe pod` has four regions, and they're worth reading in a specific order:

1. **Status and container states** — phase, and per-container `State` with `Reason` and `Exit Code` (K2.2). `Last State` shows the previous run, which is where `OOMKilled` appears.
2. **Conditions** — `PodScheduled`, `Initialized`, `ContainersReady`, `Ready`. The first `False` tells you how far the pod got.
3. **Mounts, volumes, and environment** — for verifying what was actually injected.
4. **Events** — at the bottom, and **almost always where the answer is.**

Events are messages from the scheduler and kubelet about this object: `FailedScheduling` with the per-node tally (K6.13), `Failed` with an image pull error (K9.5), `Unhealthy` with the probe response, `BackOff`, `FailedMount`, `Evicted`.

The practical points:

- **Events expire, by default after one hour.** So a pod that failed overnight may have no events at all, and `describe` looks uninformative. That's a reason to ship events to your logging system (K9.13) rather than relying on the API server's retention — otherwise post-hoc investigation of an overnight failure is impossible.
- **Events are namespaced objects**, so `kubectl get events` works cluster-wide with `-A` and can be sorted and filtered — useful for spotting a pattern affecting many pods rather than one.
- **`describe` on other objects matters too**: `describe node` shows conditions, allocatable versus allocated, and taints; `describe service` shows the selector; `describe replicaset` shows quota rejections that never produced a pod (K6.13).

The habit to state: **describe before logs.** If the container never started, there are no logs, and the reason is an event.

**K9.3 — Logs from a crashed previous container**

```bash
kubectl logs <pod> --previous
kubectl logs <pod> -c <container> --previous
```

The reason this matters: when a container crashes and restarts, `kubectl logs` shows the **current** (possibly just-started, possibly empty) instance. The output that explains the crash belongs to the terminated one, and `--previous` is the only way to get it from the API.

The constraints to know:

- **It holds only one previous instance.** A pod in CrashLoopBackOff cycling repeatedly overwrites it, so you may catch the wrong iteration.
- **It's gone once the pod is deleted.** Delete a CrashLooping pod and its diagnostic evidence goes with it — which is why deleting a broken pod to "try again" destroys the thing you needed. Worth naming as a discipline point.
- **A pod that was evicted or whose node died has no logs available at all** through the API.

Which is the argument for **shipping logs off-cluster** (K9.13): container logs on the node are ephemeral, subject to rotation and garbage collection, and disappear with the pod. Any investigation more than a few minutes after the fact depends on the log pipeline, not on kubectl.

**K9.4 — Diagnosing CrashLoopBackOff systematically**

`CrashLoopBackOff` is not a cause — it's the kubelet saying "this container keeps exiting and I'm backing off before restarting it" (10s, 20s, 40s… capped at 5 minutes). The task is to find out *why* it exits.

The sequence:

1. **`kubectl logs <pod> --previous`** (K9.3). Most of the time the application says exactly what's wrong — a missing environment variable, an unreachable dependency, a config parse error.
2. **`kubectl describe pod`** — check the **exit code** in `Last State`:
   - **`0`** — the process completed successfully and exited. Usually means the container has no long-running foreground process, or the command finished. Correct behaviour for a Job, a bug in a Deployment.
   - **`1` / `2`** — application error; the logs will say.
   - **`137`** — SIGKILL, almost always **OOMKilled** (K6.3, K9.8). Confirm via the reason field.
   - **`139`** — segfault.
   - **`143`** — SIGTERM; something asked it to stop.
3. **Distinguish "crashes on startup" from "crashes after running"**, because the cause sets differ entirely. Startup: config, secrets, permissions, missing dependency. After a period: memory growth, a leaked resource, a dependency failing later.
4. **Check whether it's actually the liveness probe killing it** (K9.11) — the container may be healthy but failing a probe, so the kubelet restarts it forever. The Events show `Unhealthy` with the probe failure, and this is a genuinely common misdiagnosis because the application logs look fine.
5. **Config and secrets** — was the expected env var or file actually there? `kubectl describe` shows mounts and `envFrom` sources; a missing ConfigMap key produces a container that starts and immediately dies.
6. **Permissions** — a hardened securityContext (K8.7) with `readOnlyRootFilesystem` or `runAsNonRoot` against an image that expects to write or expects root. Very common and produces an obscure error.
7. **To inspect without the crash loop**: temporarily override the command with something long-running (`command: ["sleep", "3600"]`) so you can `exec` in and reproduce by hand. Or use a debug container (K9.12).

The framing: **CrashLoopBackOff is the symptom; the exit code plus the previous logs are the diagnosis.** Answering with a method rather than a list of causes is what's being assessed.

**K9.5 — ImagePullBackOff: auth vs tag vs architecture**

The three causes present differently, and distinguishing them is the item:

- **Not found** — `manifest for ...:1.4.2 not found` or `repository does not exist`. A wrong tag, a wrong registry path, or an image that was never actually pushed (a common CI failure where the build succeeded and the push didn't).
- **Authentication** — `unauthorized`, `authentication required`, or `denied`. A missing or wrong `imagePullSecrets`, an expired registry credential, or — on cloud registries — the **node role or IRSA lacking pull permission** (A5.1). Note the pull is done by the kubelet/node, not by the pod's identity, which is the distinction that confuses people on ECS and EKS alike (A5.2).
- **Architecture mismatch** — `no matching manifest for linux/amd64` or, worse, the image pulls and then the container immediately fails with `exec format error`. **An arm64 image built on an Apple Silicon laptop deployed to x86 nodes** is the modern classic. The fix is multi-arch builds (`docker buildx --platform linux/amd64,linux/arm64`), and it's increasingly common with Graviton node pools (A4.2).

Other causes worth knowing: **Docker Hub rate limits** (anonymous pulls are heavily limited — the fix is a pull-through cache or authenticated pulls, A5.1); **no network path to the registry** from private subnets (needs NAT or ECR endpoints, A3.3); and **`imagePullPolicy: Always` with a registry outage** turning a restart into a failure where a cached image would have worked.

The diagnostic: `kubectl describe pod` shows the exact registry error in Events — read it rather than guessing, since the three causes have distinct messages.

**K9.6 — Pending and the blocking constraint**

Fully covered in K6.13 from the scheduling side. The addition here is that **Pending has two distinct families**:

- **Not scheduled** — no node was chosen. `kubectl describe pod` shows a `FailedScheduling` event with the per-node reason tally. This is K6.13.
- **Scheduled but not started** — a node is assigned (`Node:` is populated in describe) but containers aren't running. Now it's a kubelet-stage problem: image pull (K9.5), volume attach (K5.9), or a failing init container (K2.3).

**Checking whether `Node:` is set is the fastest way to bisect**, and it's the step people skip. If there's no node, it's the scheduler; if there is, it's the kubelet, and the entire cause set changes.

**K9.7 — A pod stuck Terminating**

A pod stays `Terminating` when deletion has been requested but something is preventing completion. The causes:

1. **The process ignores SIGTERM** and runs until `terminationGracePeriodSeconds` (default 30) expires, then gets SIGKILL. So a pod terminating for 30 seconds is normal; longer than the grace period is not.
2. **A `preStop` hook that hangs** — the grace period includes it, so a hook waiting on something unavailable consumes the whole window.
3. **Finalizers** (K12.4) — the object has a finalizer and the controller responsible for clearing it is absent, broken, or uninstalled. The pod will stay Terminating **forever**; the grace period is irrelevant because the API object can't be removed.
4. **The node is unreachable** — the kubelet can't confirm the pod is gone, so the API server won't remove it. This is the dangerous one.
5. **A volume that won't unmount** — a stuck NFS mount or a CSI driver problem (K5.9).

Diagnosis: `kubectl get pod -o yaml` and look at `metadata.finalizers` and `deletionTimestamp`. If the node is `NotReady`, that's the cause.

**The force-delete caution is the important part**:

```bash
kubectl delete pod <pod> --grace-period=0 --force
```

This removes the API object **without confirming the container has stopped.** If the node is merely unreachable rather than dead, the container is still running. For a stateless pod that's untidy; **for a StatefulSet member with a ReadWriteOnce volume it can produce two instances writing to the same data** (K2.8). Force-deleting StatefulSet pods on unreachable nodes is genuinely one of the more dangerous routine Kubernetes commands, and knowing why is a strong signal.

Removing a finalizer by patching it away has the same character: you're bypassing a controller's cleanup, which may leave orphaned cloud resources behind (K12.4).

**K9.8 — OOMKilled: raise the limit or fix the app**

Confirm it first: `kubectl describe pod` shows `Last State: Terminated, Reason: OOMKilled, Exit Code: 137`.

**Then determine which of two situations you're in**, which is the actual question:

**Legitimately under-provisioned** — the workload's real working set exceeds the limit. Evidence: memory rises to a plateau and stays there; the plateau is above the limit; usage correlates with load or data volume; it OOMs quickly and consistently rather than after hours. **Raise the limit** (and the request, K6.5), sized from the observed plateau plus headroom.

**A leak** — memory grows without bound. Evidence: a sawtooth on the memory graph — steady climb, OOM kill, restart, climb again — with the period roughly constant regardless of load. **Raising the limit only lengthens the interval between kills**, which is the tell. It buys time; it isn't a fix, and it should be framed that way when you do it during an incident.

The middle cases that matter:

- **A runtime not reading its cgroup limit** (K6.3) — the JVM sizing its heap from node memory. Not a leak and not under-provisioning; it's a configuration bug, fixed with `MaxRAMPercentage` or by passing the limit via the downward API (K3.7).
- **Page cache counting toward the cgroup** — heavy file I/O triggering an OOM in a process whose heap is fine.
- **A single large request** — one oversized payload or query result briefly exceeding the limit. Neither leak nor plateau; the fix is bounding request size or streaming.

The honest answer to give: **raise the limit to stop the bleeding, then investigate, and be explicit that the raise is mitigation not remediation.** Silently raising limits until it stops happening is how a cluster accumulates workloads requesting far more than they need (K6.5) and how a real leak survives to production scale.

**K9.9 — A Service returning nothing**

The single most common Kubernetes networking question, and it has a fixed checklist:

1. **Does the Service have endpoints?**
   ```bash
   kubectl get endpointslices -l kubernetes.io/service-name=api
   ```
   **Empty is the answer most of the time**, and it narrows everything: either the selector matches nothing, or the pods aren't Ready.
2. **Selector mismatch** — compare `kubectl get svc api -o jsonpath='{.spec.selector}'` with the pods' actual labels. A typo or a label changed on the Deployment template. Nothing warns you (K4.4).
3. **Pods not Ready** — `kubectl get pods` showing `0/1 READY` means readiness is failing (K9.10), so they're deliberately excluded. Running ≠ Ready (K2.2).
4. **Port mismatch** — `Service.port` (what clients use) → `targetPort` (the container's port) → `containerPort`. A Service targeting 8080 with a container listening on 3000 has endpoints and still fails. Named ports help avoid this.
5. **The app binds to `127.0.0.1`** rather than `0.0.0.0` — the container accepts nothing from outside its own loopback. Confirm with `kubectl exec` and `netstat`/`ss`.
6. **NetworkPolicy** blocking (K4.10) — check both the caller's egress and the target's ingress.
7. **Above the Service**: Ingress host/path rules, controller logs, TLS (K4.7, K4.8).

**Bisect by bypassing layers**, which is the technique rather than the list:

```bash
kubectl port-forward pod/<pod> 8080:8080     # pod alone — skips Service entirely
kubectl port-forward svc/api 8080:80         # through the Service
kubectl run -it --rm dbg --image=nicolaka/netshoot -- curl http://api.payments:80
```

If the pod works and the Service doesn't, it's selector/ports/readiness. If the Service works and the Ingress doesn't, it's routing or TLS. Each test eliminates a layer (K4.12).

**K9.10 — Liveness, readiness, and startup probes**

- **Readiness** — "should traffic go here?" Failure removes the pod from Service endpoints (K4.4). **Does not restart the container.**
- **Liveness** — "is this container broken beyond recovery?" Failure **restarts the container**.
- **Startup** — "has it finished starting?" While it runs, liveness and readiness are **suspended**. Once it succeeds, it never runs again.

```yaml
startupProbe:                    # allows 5 minutes to start
  httpGet: { path: /healthz, port: 8080 }
  failureThreshold: 30
  periodSeconds: 10
readinessProbe:
  httpGet: { path: /ready, port: 8080 }
  periodSeconds: 5
  failureThreshold: 2
livenessProbe:
  httpGet: { path: /healthz, port: 8080 }
  periodSeconds: 10
  failureThreshold: 3
```

The design rules that matter:

- **Readiness should check dependencies; liveness should not.** This is the crucial asymmetry. If the database is down, readiness failing is correct — stop sending traffic. Liveness failing is wrong — restarting the container doesn't fix the database, and it turns a dependency blip into a cluster-wide restart storm (K9.11). **Liveness should test only "is this process wedged", which for most applications means a trivial endpoint that proves the event loop is alive.**
- **Use a startup probe rather than a long `initialDelaySeconds`.** A fixed delay must be sized for the worst case, so fast starts wait pointlessly and slow starts still fail. The startup probe adapts.
- **Set `failureThreshold` on liveness generously** — restarting is destructive, so require real evidence.
- **Probe timeouts count**: a probe with a 1-second timeout against an endpoint that's slow under load will fail exactly when the system is stressed, which is the worst possible time.
- **`exec` probes fork a process each time** — expensive at high frequency across many pods; prefer `httpGet` or `tcpSocket`.

**K9.11 — How a bad liveness probe causes a self-inflicted outage**

The mechanism, and it's worth telling as a sequence because it's a genuinely instructive failure:

1. The liveness probe checks `/health`, which verifies the database connection.
2. The database has a brief problem — a failover (A7.1), a lock, a slow query.
3. **Every pod's liveness probe fails simultaneously**, because they share the dependency.
4. The kubelet restarts every container, everywhere, at once.
5. The restarted pods all reconnect to the database at the same moment — a **thundering herd** of connection attempts against an already-struggling database.
6. That makes the database worse, so probes fail again, so everything restarts again.
7. Meanwhile all in-flight requests are lost, caches are cold, JVMs are re-warming, and the service is far more broken than the original database blip warranted.

**A transient dependency problem has been converted into a total, self-sustaining outage by the mechanism intended to improve reliability.**

The related failure: **liveness failing under load.** The service is slow because it's saturated, the probe times out, containers restart, capacity drops, the remaining pods get more load, and the cascade accelerates. Restarting is precisely the wrong response to overload.

The rules that follow:

- **Liveness checks the process, not the system.** Dependencies belong in readiness (K9.10).
- **Generous thresholds and timeouts** on liveness — several consecutive failures over a meaningful window.
- **If you're not sure you need a liveness probe, don't set one.** A container with no liveness probe is never restarted by the kubelet, which is often safer than a badly-configured one. Liveness earns its place for processes that genuinely deadlock; for everything else it's a risk with little upside.
- **Alert on restart counts**, because a probe quietly restarting containers is invisible if you only watch availability.

This is one of the best "tell me about a subtle production failure" answers available, because it's specific, mechanistic, and the lesson generalises to health checks everywhere (A4.4).

**K9.12 — Ephemeral debug containers against a distroless pod**

The problem: distroless and scratch images have no shell, no `curl`, no `ps` — deliberately, for supply-chain and attack-surface reasons (S7). So `kubectl exec -- sh` fails, and the hardening that's correct for production makes debugging impossible by conventional means.

```bash
kubectl debug -it <pod> --image=nicolaka/netshoot --target=<container>
```

This injects an **ephemeral container into the running pod**, sharing its network namespace — and with `--target`, its process namespace too, so you can see and inspect the application's processes and its `/proc`. You get a full toolset against the live pod without changing the image, without a restart, and without weakening the production image.

The variants worth knowing:

```bash
# copy the pod with a debug container and a modified command
kubectl debug <pod> -it --copy-to=<pod>-debug --container=app -- sh
# debug a node: privileged pod in the host namespaces
kubectl debug node/<node> -it --image=busybox
```

The `--copy-to` form is the answer for a **CrashLoopBackOff** pod (K9.4), since you can't exec into a container that isn't running — copy it, override the command with `sleep`, and investigate at leisure.

The points to make: ephemeral containers **cannot be removed** once added, and the pod carries them until it's deleted — they're for debugging, not for permanent tooling. They **respect the pod's securityContext and PSA level** (K8.6), so a `restricted` namespace may reject a debug image needing capabilities. And **`kubectl debug` requires RBAC on `pods/ephemeralcontainers`**, which is a permission worth granting deliberately and auditing (K8.13), because it's effectively production shell access.

**K9.13 — How metrics and logs get out of the cluster**

**Logs**: the container writes to stdout/stderr → the container runtime writes to a file on the node (`/var/log/pods/...`) → a **DaemonSet collector** (Fluent Bit, Vector, the OTel Collector) tails those files, enriches them with pod, namespace, and label metadata from the API server, and ships to a backend (CloudWatch Logs, Loki, Elasticsearch, an OTLP endpoint).

The critical properties:

- **Node log files are rotated and garbage-collected**, so anything not shipped is lost — and lost permanently when the pod or node goes (K9.3). The collector isn't an optimisation; it's the only durable path.
- **Enrichment is what makes logs queryable.** Raw lines without pod, namespace, and app labels are almost useless at scale; the collector adding Kubernetes metadata is the step that makes "show me errors for the payments service" possible.
- **Log to stdout as structured JSON.** Applications writing to files inside the container require sidecars or shared volumes and are a persistent annoyance (A9.1).
- **DaemonSet collectors don't work on Fargate** (K2.9, A5.5) — sidecars only.

**Metrics**: applications and components expose Prometheus-format `/metrics` → **Prometheus** (or an agent: the OTel Collector, Grafana Alloy, ADOT) scrapes them via service discovery against the Kubernetes API → stored locally or remote-written to long-term storage (Mimir, Thanos, Amazon Managed Prometheus).

Sources you get for free: **kube-state-metrics** (object state — replicas desired vs available, pod phase, PVC status), **cAdvisor via the kubelet** (container CPU, memory, network), **node-exporter** (node-level), and control-plane metrics.

**metrics-server is a different thing** and confusing people is common: it exists solely to serve the Metrics API for `kubectl top` and HPA (K7.2). It stores nothing and is not a monitoring system.

**Traces**: OTel SDKs in applications → OTel Collector as a DaemonSet or Deployment → backend (Tempo, Jaeger, X-Ray). The instrument-with-OTel-export-anywhere argument is A9.8.

**K9.14 — Cluster-level vs workload-level monitoring**

**Cluster level** — is the platform healthy?

- **Control plane**: API server latency and error rate, etcd latency and database size, scheduler queue depth and scheduling latency, webhook latency (K8.8).
- **Nodes**: `Ready` count, conditions (`MemoryPressure`, `DiskPressure`, `PIDPressure`), allocatable versus allocated, node age and version skew (K11.2).
- **Capacity**: unschedulable pods (the leading indicator for autoscaling problems, K7.9), requests versus usage across the cluster (the cost signal, K6.5), IP address availability (A5.7).
- **Platform components**: CoreDNS latency and error rate, CNI health, ingress controller error rate and latency, CSI driver health, the autoscaler's own status.
- **Certificates and versions**: days-to-expiry, and days-to-end-of-support for the cluster version (K11.1).

**Workload level** — is the application healthy? The **golden signals** — latency, traffic, errors, saturation — measured against SLOs, plus Kubernetes-specific ones: replica availability (desired vs ready), **restart counts** (which is how you spot OOM kills and probe-driven restarts before they become outages, K9.8, K9.11), pod pending duration, deployment rollout status, and CPU throttling (K6.2).

The distinction that matters organisationally: **cluster-level is the platform team's responsibility and its alerts page the platform team; workload-level is the application team's and pages them.** Conflating them is how platform teams end up on call for application errors they can't fix, and how application teams stop reading alerts. That ownership split is part of the platform contract (K13.4).

And the alerting principle carries over from A9.4: **alert on symptoms with user impact, not on every cause.** "Three nodes are NotReady" is worth knowing; it's only worth *paging* if capacity or an SLO is actually threatened. A cluster generates enormous numbers of legitimately-changing conditions, and paging on them is the fastest route to an ignored pager.

---

## K10. Packaging & delivery

**K10.1 — Install, upgrade, roll back, inspect a Helm release**

```bash
helm install api ./chart -n payments --values prod.yaml
helm upgrade api ./chart -n payments --values prod.yaml --atomic --timeout 5m
helm upgrade --install api ./chart -n payments   # idempotent: the CI form
helm history api -n payments
helm rollback api 3 -n payments
helm status api -n payments
helm get values api -n payments                  # what was actually applied
helm get manifest api -n payments                # what was actually rendered
helm uninstall api -n payments
```

The flags that matter in practice:

- **`--atomic`** — roll back automatically if the upgrade fails or times out. Without it a failed upgrade leaves the release in a broken half-applied state (`pending-upgrade`), which then blocks subsequent operations (K10.4).
- **`--timeout`** — how long to wait for resources to become ready; the default 5 minutes is often too short for a slow-starting app, and a timeout is *not* the same as a failure.
- **`--wait`** — block until resources are Ready rather than just applied.
- **`--upgrade --install`** — idempotent, so the same command works for first deploy and every subsequent one.

**`helm get values` and `helm get manifest` are the underused diagnostic pair.** When a release doesn't behave as expected, they tell you what values were actually in effect and what YAML was actually applied — which frequently differs from what you think you passed, because of values-file precedence and chart defaults.

**K10.2 — Writing a chart**

```
chart/
├── Chart.yaml           # name, version, appVersion, dependencies
├── values.yaml          # defaults — and the chart's public interface
├── templates/
│   ├── _helpers.tpl     # named templates: labels, names
│   ├── deployment.yaml
│   ├── service.yaml
│   └── NOTES.txt
└── charts/              # vendored subcharts
```

```yaml
{{- define "app.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
```

```yaml
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    metadata:
      labels: {{- include "app.labels" . | nindent 8 }}
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

Design points that separate a good chart from a working one:

- **`values.yaml` is the chart's public API.** Every field is a contract you'll have to keep supporting. Expose what genuinely varies; don't parameterise everything "just in case" — an over-parameterised chart is unmaintainable and its values file becomes as complex as the manifests it replaced.
- **`_helpers.tpl` for names and labels**, so naming is consistent and the standard `app.kubernetes.io/*` labels are always present (they're what most tooling and dashboards key on).
- **`nindent` versus `indent`** — `nindent` adds a leading newline, which is what you want after a YAML key. Getting this wrong produces invalid YAML and a confusing parse error.
- **`Chart.yaml` `version` is the chart's version, `appVersion` is the application's.** Bumping the wrong one is a common release-hygiene mistake.
- **`required` and schema validation** (`values.schema.json`) to fail fast on missing or malformed values, rather than rendering a broken manifest.
- The checksum annotation for config-driven rollouts (K3.3).

**K10.3 — Debugging a chart**

```bash
helm template api ./chart --values prod.yaml            # render locally, no cluster
helm template api ./chart --values prod.yaml --debug    # includes computed values
helm install api ./chart --dry-run --debug              # render + server-side validate
helm upgrade api ./chart --dry-run
helm lint ./chart
helm diff upgrade api ./chart --values prod.yaml        # plugin: shows the delta
```

The distinction worth being precise about: **`helm template` renders entirely client-side** — fast, needs no cluster, and won't catch anything the API server would reject. **`--dry-run` sends the rendered manifests to the API server for validation**, so it catches schema errors, admission webhook rejections (K8.8), and RBAC problems. Use template for iterating on the Go templating, dry-run before actually applying.

**`helm diff upgrade` is the single most valuable addition** — it shows what would change against the current release, which is the Kubernetes equivalent of `terraform plan` (A14.5) and turns a Helm upgrade from an act of faith into a reviewable change. Worth naming as a standard part of a release process.

Debugging tips: pipe `helm template` output to `kubectl apply --dry-run=server -f -` for the same validation without a release; use `--show-only templates/deployment.yaml` to isolate one file; and remember that **template errors report line numbers in the rendered output, not the source**, so rendering with `--debug` and reading the failed output is usually faster than staring at the template.

**K10.4 — Helm's release state, and what happens when it's out of sync**

Helm stores each release's state as a **Secret in the release's namespace** (`sh.helm.release.v1.<name>.v<revision>`), containing the rendered manifests and values, gzipped and base64-encoded. That's the record it diffs against on upgrade.

**When state and reality diverge** — because someone edited resources with kubectl, or another controller changed them — Helm doesn't know. It computes a three-way merge between the old release, the new release, and the live object, which usually does the sensible thing but can produce surprises: fields you changed manually may be preserved or reverted depending on ownership.

The specific failure states worth knowing:

- **`pending-upgrade` / `pending-install`** — a previous operation was interrupted (a CI job killed, a timeout without `--atomic`). Helm refuses further operations on the release. Fix with `helm rollback` to the last good revision, or in bad cases by deleting the stuck release Secret.
- **Release secret deleted or lost** — Helm no longer knows the release exists and `helm upgrade --install` tries to create resources that already exist, failing on conflict. Recovery is `--force`, or adopting the resources with the right labels and annotations.
- **Too many revisions** — every upgrade creates a Secret; `--history-max` bounds them. Unbounded, they accumulate and contribute to etcd size.
- **Resources deleted out of band** are simply recreated on the next upgrade, which is usually what you want.

The broader point: **Helm's release state is a second source of truth alongside the cluster**, and that's an inherent weakness compared with a purely declarative reconciler. It's precisely why GitOps tools that apply manifests directly (Flux with Kustomize, ArgoCD) avoid a class of problem Helm has — and why ArgoCD, when it renders Helm charts, deliberately uses `helm template` and applies the output rather than using Helm's release mechanism at all.

**K10.5 — Kustomize bases and overlays**

```
base/
├── kustomization.yaml
├── deployment.yaml
└── service.yaml
overlays/
├── dev/
│   ├── kustomization.yaml
│   └── replicas.yaml
└── prod/
    ├── kustomization.yaml
    └── replicas.yaml
```

```yaml
# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: payments-prod
resources:
  - ../../base
patches:
  - path: replicas.yaml
    target: { kind: Deployment, name: api }
images:
  - name: api
    newTag: 1.4.2
configMapGenerator:
  - name: app-config
    files: [application.yaml]
replicas:
  - { name: api, count: 6 }
commonLabels:
  environment: prod
```

The model is **plain YAML plus declarative patches** — no templating language. The base holds valid, applyable manifests; overlays patch them per environment. `kubectl apply -k ./overlays/prod` or `kustomize build`.

The features worth knowing: **`configMapGenerator`/`secretGenerator`** append a content hash to the name and rewrite all references, giving automatic rollout on config change plus rollback-safe config (K3.3); **strategic merge patches** for the common case and **JSON 6902 patches** for surgical list edits; and **`images`** for tag substitution, which is how CI updates the deployed version without touching templates.

**K10.6 — Helm vs Kustomize, and defending the choice**

**Helm** — a package manager. Templating, a values interface, dependencies, a release lifecycle with rollback, and — the decisive practical factor — **an enormous ecosystem of third-party charts.**

**Kustomize** — a patching layer. No templating, built into kubectl, and the output is always plain YAML you can read.

The honest comparison:

- **Helm's templating is powerful and produces unreadable charts at scale.** A heavily-conditioned template with nested `if`/`range` and whitespace control is genuinely hard to reason about, and you can't tell what it produces without rendering it. Kustomize's inputs are always valid YAML, so a reviewer can read them.
- **Kustomize's patching becomes awkward for genuine variability.** If environments differ structurally rather than in a few values, you end up with sprawling overlays that duplicate more than they share. Helm handles conditional inclusion cleanly.
- **Helm has a release state** (K10.4); Kustomize has none, which is simpler and fits GitOps better.
- **You will use Helm regardless**, because third-party components ship as charts. The question is what you use for *your own* applications.

**The defensible position**: **Helm for consuming third-party software, Kustomize for your own applications** — or Helm charts as the base with Kustomize overlays applied on top of `helm template` output, which both ArgoCD and Flux support natively and which is a common mature setup. What matters in the answer is defending it on **who reads and maintains it**: if application teams own their manifests, Kustomize's readability wins; if a platform team maintains one heavily-parameterised chart consumed by many teams, Helm's values interface is the better contract. Also worth naming that the space is moving — Timoni, cdk8s, and Score all exist because both tools have real limitations.

**K10.7 — GitOps vs a push pipeline**

**Push**: CI builds, tests, then runs `kubectl apply` or `helm upgrade` against the cluster. The pipeline holds cluster credentials and initiates the change.

**GitOps**: CI builds and updates a manifest in a git repository. **An agent inside the cluster** (ArgoCD, Flux) watches that repo and continuously reconciles the cluster to match it.

The differences that actually matter:

- **Credential direction.** With push, CI holds cluster-admin-grade credentials, and CI systems are internet-facing and a well-known attack path. With GitOps, **the cluster pulls; no external system has cluster credentials at all.** For a regulated environment this is the strongest single argument, and it's a security answer rather than a workflow preference.
- **Continuous reconciliation, not one-shot apply.** A push pipeline applies and stops; drift afterwards is invisible. A GitOps agent reconciles continuously, so manual changes are detected and (optionally) reverted (K10.9).
- **Git is the audit trail.** Every change to production is a reviewed, signed, attributable commit — which maps directly onto change-management requirements. "Who changed production and who approved it" is answered by `git log` rather than by pipeline logs.
- **Recovery.** Rebuilding a cluster is pointing an agent at the repo, which makes cluster loss much less severe (K11.10).
- **Deployment decouples from CI.** The same manifests deploy to any cluster; CI doesn't need per-cluster configuration.

The costs to acknowledge: **an extra layer of indirection** — a merged PR isn't deployed, it's *going* to be deployed, which confuses people used to a pipeline that reports success. **Feedback is asynchronous**, so failures surface in ArgoCD rather than in the CI job. **Secrets need solving** (K10.11). And **the "rollback under pressure" flow is slower** — a git revert and a sync rather than a command (K2.7).

**K10.8 — Configuring ArgoCD or Flux to sync an application**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: payments-api
  namespace: argocd
spec:
  project: payments
  source:
    repoURL: https://github.com/acme/deploy.git
    targetRevision: main
    path: overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: payments
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff: { duration: 5s, factor: 2, maxDuration: 3m }
```

Key concepts: the **Application** binds a source (repo, revision, path) to a destination (cluster, namespace); **AppProject** constrains which repos, clusters, and resource kinds an Application may use, which is the multi-tenancy control; **sync waves** and hooks order resources (CRDs before the resources that use them, migrations before the app); and **health assessment** determines whether a synced app is actually working, not just applied.

Flux is equivalent with `GitRepository` plus `Kustomization`/`HelmRelease` — more composable and CRD-native, less UI. ArgoCD's UI is a genuine operational advantage for teams debugging deployments; Flux's model is cleaner for platform automation. Either is defensible.

The scaling pattern worth naming: **the app-of-apps pattern, or ArgoCD ApplicationSets**, which generate Applications from a template across clusters, environments, or repo directories — because managing hundreds of Application objects by hand is the thing that stops GitOps scaling.

**K10.9 — Drift, auto-sync, and self-heal**

- **`automated: {}`** — sync automatically when git changes.
- **`selfHeal: true`** — also revert changes made directly in the cluster.
- **`prune: true`** — delete resources removed from git.

When each is appropriate:

- **Auto-sync is right for most environments.** The alternative — manual sync — means git and the cluster routinely diverge, which defeats the purpose.
- **`selfHeal` is right when git is genuinely the source of truth**, and it's what makes drift impossible rather than merely visible. The friction is real though: an engineer debugging by editing a resource watches their change disappear within seconds, which is confusing the first time. That's a training issue rather than a reason to disable it — but it does mean you need a documented break-glass path for genuine emergencies (typically disabling auto-sync on that Application, doing the work, then reconciling git).
- **`prune` is the dangerous one.** A path typo, a bad refactor, or a branch mishap that removes resources from git means **ArgoCD deletes them from the cluster** — and if that includes a PVC with `Delete` reclaim, the data is gone (K5.4). Mitigations: `Prune=false` annotations on stateful resources, `PruneLast`, and ArgoCD's prune-confirmation for resources it considers dangerous.

The nuanced position for production: **auto-sync and self-heal on, prune on but with explicit protection for stateful resources**, and a documented emergency procedure. And note the interaction with other controllers: **HPA-managed replicas will fight a git-declared `replicas` field** unless you exclude it (`ignoreDifferences` on `/spec/replicas`), which is a classic and confusing conflict — the app scales, ArgoCD reverts it, repeatedly.

**K10.10 — Environment config without duplicating manifests**

The options, and the tradeoffs:

- **Kustomize overlays** (K10.5) — one base, per-environment patches. Best when environments differ in a few values; the base stays readable.
- **Helm values files** — one chart, `values-dev.yaml` / `values-prod.yaml`. Best when differences are numerous or structural.
- **ApplicationSets with generators** — one Application template rendered across a list of environments or clusters, with per-environment values from a matrix or a directory generator. This is the answer at scale, because it removes the per-environment Application objects too.
- **Externalised config** — ConfigMaps generated per environment, secrets from an external store (K3.6), so the manifests themselves are environment-agnostic.

The principle to state: **duplication is not the real enemy; divergence is.** Three copied manifests that stay identical are harmless; the problem is that they *don't* stay identical, so prod silently drifts from what was tested in staging. Whatever mechanism you choose, the test is: **can a reviewer see, in one place, exactly how prod differs from staging?** An overlay containing only the deltas passes that test; three full copies do not.

The related discipline: **keep environments as similar as possible and make the differences explicit and small** — replica counts, resource sizes, endpoints, and feature flags. If the manifests differ structurally, you're testing something different from what you ship, and no templating tool fixes that.

**K10.11 — Secrets in a GitOps model**

The tension is direct: GitOps wants everything in git; secrets must not be in git. The options:

- **Sealed Secrets** — encrypt with a controller's public key, commit the ciphertext, the in-cluster controller decrypts. Simple and self-contained. Downsides: **the sealing key is cluster-specific**, so the same SealedSecret doesn't work on another cluster and disaster recovery requires the key backup; and rotation means resealing everything.
- **SOPS** (with age or KMS) + Flux or a plugin — encrypt values in git, decrypt at apply time. Works well, integrates with cloud KMS so key management is delegated (A10.1), and the git diff still shows *which* keys changed.
- **External Secrets Operator / Secrets Store CSI Driver** (K3.6) — **git holds only a reference**, the actual value lives in Secrets Manager or Vault. This is the strongest option and increasingly the default: no ciphertext in git at all, rotation happens in the external store without a commit, and access to secrets is governed by the external store's own IAM.

The comparison to make: **encryption-in-git approaches (Sealed Secrets, SOPS) keep everything self-contained but make rotation a commit and DR dependent on key backup. Reference approaches (ESO, CSI) add a runtime dependency on the external store but solve rotation and access control properly.** For a fintech with an existing Secrets Manager or Vault estate, the reference approach is usually right, and the trade is the availability dependency at pod start.

Whichever you choose, the invariants: **no plaintext secrets in git, ever, including in history** (a leaked commit needs rotation, not a force-push, A10.30); **secret values must not appear in ArgoCD's UI or diffs**; and the decryption identity should be cluster-scoped and auditable.

---

## K11. Cluster operations

**K11.1 — Planning and executing a version upgrade**

The sequence, and the planning is most of it:

1. **Read the changelog and deprecation notices** for every version you're passing through. Kubernetes releases roughly three times a year with about 14 months of support, so **you cannot skip versions on the control plane** — upgrades are one minor version at a time (K11.2).
2. **Find deprecated API usage** before it breaks (K11.3).
3. **Check add-on compatibility** — CNI, CSI, ingress controller, metrics-server, cert-manager, the autoscaler, service mesh, operators. Each has its own support matrix, and **an add-on incompatibility is the most common cause of a failed upgrade** (K11.9).
4. **Upgrade a non-production cluster first**, ideally one that genuinely resembles production. A "dev" cluster running different workloads proves little.
5. **Upgrade the control plane**, then the nodes (K11.5). Never the reverse — the skew policy allows nodes to be older, not newer (K11.2).
6. **Roll nodes** with drains respecting PDBs (K11.4).
7. **Verify**: workloads healthy, add-ons functioning, metrics and logs still flowing, and a deliberate test of something that exercises the CNI and CSI paths.

The realities to name:

- **Control plane upgrades on managed clusters are one-way.** There is no downgrade. That makes the pre-upgrade testing the entire safety mechanism, and it's the reason this is a planned change rather than a routine one.
- **Blocked drains are the most common way an upgrade stalls** — a single-replica workload with a restrictive PDB (K6.9) halts the node roll indefinitely.
- **The upgrade cadence is not optional.** Falling behind end-of-support means running an unpatched control plane and eventually a forced upgrade on the provider's timetable. **Upgrading three times a year as routine is far safer than once every two years as a project**, and making that argument to management is part of the job — the risk of frequent small upgrades is much lower than one large one.
- **Blue/green at the cluster level** is the alternative for high-stakes environments: build a new cluster on the new version, shift traffic, retire the old one. Expensive, and it makes rollback trivial — which for a critical platform can be worth it.

**K11.2 — Version skew policy**

The supported skew:

- **kube-apiserver** — in an HA control plane, instances may differ by one minor version during the upgrade.
- **kubelet** — may be **up to three minor versions older** than the API server, and **never newer**.
- **kube-proxy** — matches the kubelet's constraints.
- **controller-manager, scheduler, cloud-controller-manager** — may be one minor older than the API server, never newer.
- **kubectl** — supported within one minor version either side.

The operationally important consequences:

- **Control plane first, always.** Upgrading nodes ahead of the control plane puts kubelets *newer* than the API server, which is unsupported and does break things.
- **The three-version kubelet allowance is what makes rolling node upgrades practical** — you can take your time rolling a large fleet across several control plane versions. But it's a ceiling, not a target: nodes three versions behind are running old kubelets with old bug fixes, and the further behind they are the more likely something subtly misbehaves.
- **`kubectl get nodes` shows kubelet versions**, and a fleet with mixed versions after an incomplete roll is worth alerting on — nodes that failed to roll and were forgotten are a real pattern (K9.14).

**K11.3 — Finding and fixing deprecated API usage**

Kubernetes removes APIs on a published schedule (`extensions/v1beta1` Ingress, `policy/v1beta1` PDB, and so on). **An upgrade that removes an API you're using means those manifests stop applying** — existing objects are usually migrated by the API server, but your manifests, charts, and controllers break.

Detection:

- **`kubectl deprecations` / `kubent` (kube-no-trouble)** — scans live cluster objects and Helm releases for APIs removed in target versions. The standard tool.
- **Pluto** — scans manifests and charts in your repos, which catches things not currently deployed.
- **The API server's own metrics**: `apiserver_requested_deprecated_apis` tells you what's actually being called and by whom — which is the authoritative answer, because it catches controllers and CI tooling that scanners miss.
- **Audit logs** (K8.13) filtered for deprecated API groups.

The point that's easy to miss: **it's not only your manifests.** Third-party controllers, operators, Helm charts, and CI tooling all call the API, and a controller using a removed API breaks silently after the upgrade — it just stops reconciling. That's why the metrics-based check matters more than the manifest scan, and why the add-on compatibility review (K11.9) is inseparable from this item.

Fixing is usually mechanical (`apiVersion` change, occasionally a field rename), and the important part is doing it **before** the upgrade, on a cluster still running the old version where both APIs are served.

**K11.4 — Cordon, drain, replace a node**

```bash
kubectl cordon <node>                    # mark unschedulable; existing pods stay
kubectl drain <node> \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --grace-period=60 \
  --timeout=10m
# ... replace the node ...
kubectl uncordon <node>                  # only if reusing it
```

What drain does: cordons, then **evicts** pods via the eviction API, which **respects PodDisruptionBudgets** (K6.9). DaemonSet pods can't be evicted meaningfully (they'd be recreated), hence `--ignore-daemonsets`. Pods with `emptyDir` data are refused unless you accept the data loss explicitly.

The operational points:

- **A blocked drain is normal and informative.** If a PDB won't allow the eviction, drain waits. That's the system working — but it means an unattended node roll can hang for hours, which is why `--timeout` matters and why you should check PDBs before starting a fleet roll (K11.1).
- **Graceful termination is the workload's job.** Drain sends SIGTERM and waits `terminationGracePeriodSeconds`; an application that doesn't drain connections on SIGTERM will drop in-flight requests regardless of how carefully you drain.
- **`--force` evicts pods with no controller** (bare pods, K2.1) — meaning they're deleted and never come back. Know what you're forcing.
- **Cordon without drain is useful on its own** — stop new work landing on a suspect node while you investigate, without disrupting what's running.

**K11.5 — In-place vs rolling replacement for node upgrades**

**In-place** — drain, upgrade the kubelet and OS packages on the existing instance, uncordon. Preserves the instance and any local state; used in on-prem and bare-metal environments where instances are expensive to replace.

**Rolling replacement** — launch new nodes from a new image, drain and terminate old ones. The cloud-native default.

Rolling replacement is better in almost every cloud context, for the same reasons as immutable infrastructure generally (A4.6):

- **The new node is a known artefact**, built and tested, rather than an old node mutated by an upgrade script whose outcome depends on its accumulated history.
- **Rollback is launching the previous image**, not un-upgrading packages.
- **It exercises your node provisioning path routinely**, so you find out it's broken during a planned roll rather than during an incident.
- **It resets configuration drift** on every cycle.

The costs: you need spare capacity for the surge, it's slower, and every workload gets rescheduled — which is only a problem if your workloads can't tolerate that, and if they can't, that's a finding rather than an argument against (K2.12).

Worth naming: **Karpenter's `expireAfter`** makes node rotation continuous rather than an event, so nodes are never old and the "upgrade" is just the normal replacement picking up a new AMI (K7.6). That's the mature end state, and it turns node patching from a project into a property of the system.

**K11.6 — Backing up and restoring cluster state, and what backup actually covers**

**Velero** is the standard tool: it backs up Kubernetes API objects (namespaced or cluster-scoped, filtered by label or namespace) to object storage, and can snapshot persistent volumes via CSI or cloud APIs. Restore recreates objects, optionally into a different namespace or cluster.

**What a backup actually covers, and what it doesn't** — the real substance of the item:

- **Covers**: the API objects — Deployments, Services, ConfigMaps, Secrets, CRDs and custom resources, RBAC — and, with volume snapshots configured, the PV data.
- **Does not cover, by default**: **data inside volumes unless you explicitly enable snapshots or file-level backup**. A Velero backup without volume snapshots restores a database Deployment with an empty disk, which is not a database restore.
- **Does not cover**: anything outside the cluster that the workload depends on — cloud load balancers, DNS, RDS instances, IAM roles, external secrets. A restored cluster with no corresponding cloud resources isn't a restored system.
- **Application consistency is your problem.** A volume snapshot of a running database is a crash-consistent image, not a clean backup. Velero hooks can freeze or quiesce the application first, and for real databases the correct answer is **the database's own backup mechanism** (A7.3) rather than a volume snapshot.

The position to state: **for stateless workloads, GitOps is a better recovery mechanism than backup** (K10.7) — the manifests are already in git, so recovery is pointing an agent at the repo. **Velero's real value is for what isn't in git**: resources created by controllers, custom resource state, and namespaces created out of band. **And for stateful data, use the data system's own backup.** Describing backup as three separate problems with three different answers is a much stronger response than "we run Velero".

And the same rule as everywhere: **test the restore** (A11.8), including into a fresh cluster.

**K11.7 — Multi-tenancy: namespaces, virtual clusters, separate clusters**

- **Namespaces** — cheapest. RBAC, quota, network policy, PSA per tenant. **Shared control plane, shared nodes, shared CRDs and API version** (K8.10).
- **Virtual clusters** (vcluster) — a per-tenant API server and controller manager running as pods inside a host cluster, with workloads scheduled onto the host's nodes. Each tenant gets **their own CRDs, their own API versions, and cluster-admin within their virtual cluster** — while sharing the underlying node capacity. Genuinely useful middle ground.
- **Separate clusters** — full isolation of control plane, nodes, and API. Highest isolation, highest cost and operational overhead.

The decision criteria:

- **Trust level.** Namespaces are fine for trusted internal teams. **Hostile or untrusted tenants need separate clusters**, or at minimum separate node pools with strong runtime isolation, because a container escape crosses namespaces (K8.12).
- **Do tenants need cluster-scoped resources?** If teams need their own CRDs, operators, or admission webhooks, namespaces break down immediately — and this is the most common practical driver toward virtual or separate clusters.
- **Blast radius.** One cluster means one control plane outage affects everyone, and one bad upgrade affects everyone.
- **Compliance.** Some regimes require physical or account-level separation for certain data.
- **Cost and operational load.** Every cluster is a control plane fee, a set of add-ons, an upgrade to plan, and a monitoring surface. Fifty clusters is fifty upgrades (K11.9).

The pragmatic answer for most organisations: **namespaces with real guardrails (quota, network policy, PSA, policy engine) for internal teams, separate clusters at the prod/non-prod and per-business-unit boundary, and separate clusters for anything with genuinely different compliance requirements.**

**K11.8 — Cluster sizing, and when to run more clusters**

Arguments for **fewer, larger** clusters: better bin-packing and higher utilisation; fewer control planes to pay for and upgrade; one set of add-ons; shared platform services; simpler service-to-service networking.

Arguments for **more, smaller** clusters:

- **Blast radius.** A cluster is a failure domain — control plane problems, a bad CNI upgrade, an admission webhook misconfiguration (K8.8), or an etcd issue affects everything in it.
- **Upgrade risk.** Smaller clusters can be upgraded independently and progressively, so a bad upgrade affects a fraction of workloads.
- **Scaling limits are real.** Kubernetes' documented limits (around 5,000 nodes, 150,000 pods) are theoretical maxima; **practical limits arrive much earlier** and depend on churn, object count, and controller behaviour — etcd size, API server memory, and endpoint update propagation (K1.8) all degrade before you hit the documented ceilings.
- **Isolation requirements** (K11.7).
- **Regional and locality requirements** — a cluster is regional, so multi-region means multiple clusters regardless.

The framing to give: **the natural boundaries are environment (prod/non-prod), region, and compliance domain** — and beyond that, tenancy is usually better handled with namespaces than with more clusters, because per-cluster operational cost is high and mostly fixed. The failure mode to warn against is **cluster sprawl**: dozens of clusters, each with its own add-on versions and drift, which is far worse operationally than a few well-run large ones. If you're going to run many clusters, **fleet management has to be solved first** — a single GitOps source of truth (K10.8), consistent add-on versioning, and automated provisioning — or you've traded one hard problem for a worse one.

**K11.9 — Add-ons and upgrade coupling**

Every cluster runs components that are not Kubernetes but are essential to it: CNI, CSI drivers, CoreDNS, metrics-server, ingress controller, cert-manager, the autoscaler, service mesh, monitoring agents, policy engine, external-dns, operators.

The coupling problem: **each has its own version support matrix against Kubernetes versions**, and they're independent. Upgrading the cluster may require upgrading several add-ons; upgrading an add-on may require a newer cluster version. This is the dependency graph that makes upgrades a planning exercise rather than a button (K11.1).

Managing it:

- **Maintain an explicit inventory** of every add-on, its version, and its supported Kubernetes range. Without this, upgrade planning is guesswork, and the inventory is usually the missing artefact.
- **Use managed add-ons where available** (EKS add-ons for VPC CNI, CoreDNS, kube-proxy, EBS CSI) — the provider tracks compatibility and can update them as part of the cluster upgrade.
- **Manage the rest through GitOps** (K10.8) so versions are declared, reviewed, and consistent across clusters — add-on version drift between clusters is a major source of "it works on staging" problems.
- **Upgrade add-ons *before* the cluster** where the new version supports both, so each change is isolated. Upgrading everything simultaneously means a failure has many candidate causes.
- **Watch for CRD changes** — add-on upgrades often bring CRD schema changes, and Helm notably **does not upgrade CRDs** on `helm upgrade`, which is a well-known trap that produces subtle failures.

The point worth making about ownership: **add-ons are the platform team's product surface.** Every one is a component you're responsible for patching, monitoring, and upgrading forever, and each one added has a permanent cost. That's the argument for saying no to some of them (K13.5).

**K11.10 — Losing the control plane: what you'd need**

**What happens**: existing pods keep running and serving traffic — the kubelet continues managing what's already scheduled, and kube-proxy/dataplane rules stay programmed. What you lose is **everything requiring the API**: deployments, scaling, rescheduling of failed pods, Service endpoint updates, config changes, and all observability that goes through the API. So the system is **frozen rather than dead**, degrading as individual failures accumulate with no self-healing.

**What you'd need to recover:**

- **Managed cluster**: the provider restores it. Your dependency is on their SLA, and your job is to know what the RTO actually is and whether the failure mode is recoverable or requires rebuilding (K1.10).
- **Self-managed**: **an etcd snapshot** (K1.2) and a procedure to stand up a new control plane and restore into it. This is why etcd backup is the single most important backup in a self-managed cluster.
- **Either way**: the ability to **rebuild the cluster from scratch** — cluster provisioning in IaC (Terraform), add-ons and workloads in git (K10.7), and data restorable from the data systems' own backups (K11.6). If those three exist, control plane loss is a rebuild measured in hours rather than a catastrophe.

The design conclusions to state:

- **Multi-cluster is the real mitigation for control plane loss**, not backup. If your RTO doesn't tolerate a rebuild, you need traffic to fail over to another cluster — which is the same reasoning as A11.2, applied at cluster level.
- **Don't let the cluster be a dependency of its own recovery.** If your CI, your secrets, your container registry, or your monitoring run only in the cluster you're trying to rebuild, you have a circular dependency that surfaces at the worst moment. This is a genuinely common and under-examined finding in a resilience review.
- **Rehearse it** (A11.8). "Rebuild a cluster from git and restore data" is an excellent, contained game day — high learning value, low risk, and it validates several assumptions at once.

---

## K12. Extending Kubernetes

**K12.1 — CRDs and what adding one does to the API**

A CustomResourceDefinition registers a **new resource type with the API server**. Once created, that kind is a first-class API citizen: it gets REST endpoints, works with `kubectl get/describe/apply`, is subject to **RBAC** (K8.1), is validated against the OpenAPI schema in the CRD, is stored in etcd, is watchable, and can be selected by admission webhooks and policy (K8.9).

That's the important insight: **a CRD doesn't add behaviour, it adds a place to store declared intent.** Nothing happens to a custom resource unless a controller is watching it (K12.2). You can create a CRD and thousands of objects of that kind and the cluster will faithfully store them and do nothing.

Practical points:

- **Versioning and conversion**: CRDs support multiple versions with a storage version, and **conversion webhooks** to translate between them. Getting this wrong makes upgrading an operator painful.
- **`spec` and `status` subresources** — separating status lets the controller update status without racing with user edits to spec, and lets RBAC grant one without the other.
- **Printer columns** (`additionalPrinterColumns`) make `kubectl get` output useful, and their absence is a sign of a low-quality CRD.
- **CRDs are cluster-scoped objects**, so installing one affects every namespace — a real multi-tenancy consideration (K11.7).
- **CRDs and etcd**: a controller creating large numbers of large custom resources contributes to etcd size and API server load (K1.3). Operators that store excessive state in status fields are a known cause of control plane strain.

**K12.2 — The operator pattern, and when it's warranted**

An operator is **a CRD plus a controller** that implements the reconciliation loop (K1.4) for that resource — encoding the operational knowledge a human expert would apply. A Postgres operator doesn't just create a StatefulSet; it handles replication setup, failover, backup scheduling, and version upgrades.

**When it's warranted:**

- **The domain has genuine operational complexity that recurs** — clustered stateful systems (databases, Kafka, Elasticsearch) where day-2 operations are the hard part.
- **You'd otherwise be writing runbooks that humans execute repeatedly.** An operator is the automation of a runbook, and the test is whether that runbook exists and is run often.
- **The abstraction is genuinely useful to its consumers** — application teams asking for a `Database` object rather than assembling a StatefulSet, Service, PVC, backup CronJob, and monitoring rules.

**When it isn't:**

- **For simple resources.** An operator wrapping "create a Deployment and a Service" is a Helm chart with extra steps, plus a controller you now maintain forever.
- **When the team can't support it.** An operator is production software with a reconciliation loop that runs continuously against your cluster. Writing one is a real engineering commitment, and an abandoned in-house operator is a serious liability.

The senior framing: **prefer an existing well-maintained operator, then a Helm chart, then writing your own — and prefer a managed service over all three where the workload is stateful** (K13.8). The strongest reason to build one is when you're encoding *your organisation's* specific operational policy, which no third party can provide — a platform team's `PaymentService` CRD that provisions a namespace, roles, network policy, monitoring, and deployment config as one unit is a legitimate and valuable operator, and it's the shape of the platform-as-product argument in K13.4.

**K12.3 — Evaluating a third-party operator before adopting it**

The checklist, and the framing is supply-chain risk plus permanent operational cost:

- **Maintenance health** — commit frequency, release cadence, issue response, and whether it tracks recent Kubernetes versions. **An operator that lags Kubernetes releases will block your cluster upgrades** (K11.9), which is a serious coupling.
- **Permissions it requests.** This is the biggest one. **Many operators ask for cluster-admin**, and installing it means a third-party controller with unrestricted access to every Secret in the cluster (K8.11). Read the ClusterRole it ships and push back — a well-designed operator scopes to the resources it actually reconciles.
- **Admission webhooks** — does it install one, and with what `failurePolicy` and scope? An operator's webhook can take out the cluster if it's badly scoped (K8.8).
- **CRD design and versioning** — is there a conversion strategy, or will upgrading break your resources (K12.1)?
- **What happens if it stops running?** Do existing workloads keep serving, or does the operator sit in the data path? An operator that only reconciles is safe to have down briefly; one whose absence breaks traffic is a critical dependency.
- **Finalizers** — does it use them, and does it clean them up properly on uninstall (K12.4)? A badly-behaved operator's finalizers make its resources undeletable after you remove it.
- **Data safety** — for stateful operators: how does it handle upgrades, and can it delete PVCs (K5.4)?
- **Exit path** — can you migrate off it, or does adopting it mean your data is in a format only it understands?
- **Provenance** — signed images, an SBOM, and a security disclosure process (S7).

The one-line version to give in an interview: **an operator is a privileged, always-running piece of third-party software with API access to your entire cluster, and it should be evaluated with the same rigour as any other production dependency — not installed because the README has a one-line `kubectl apply`.**

**K12.4 — Finalizers and stuck deletions**

A finalizer is a string in `metadata.finalizers`. When an object with finalizers is deleted, the API server **sets `deletionTimestamp` but does not remove the object** — it stays in a terminating state until every finalizer is removed by whichever controller owns it. That's the hook allowing controllers to perform cleanup (delete a cloud load balancer, deregister from an external system, snapshot a volume) before the object disappears.

The failure mode: **the controller responsible for a finalizer is gone, broken, or was uninstalled — so nobody removes it, and the object is stuck forever.** The classic instances:

- **A namespace stuck `Terminating`** — almost always a resource inside it with an unclearable finalizer, very often from an uninstalled operator or an unavailable aggregated API service. `kubectl get namespace <ns> -o yaml` shows what's blocking in `status.conditions`.
- **A PVC stuck terminating** because `pvc-protection` is waiting for a pod that still references it (K5.4) — which is correct behaviour, not a bug.
- **Uninstalling an operator before deleting its custom resources**, leaving objects nobody can clean up.

The escape hatch, and the caution that goes with it:

```bash
kubectl patch <resource> <name> -p '{"metadata":{"finalizers":null}}' --type=merge
```

**This bypasses the cleanup the finalizer existed to perform.** The Kubernetes object goes away; the cloud load balancer, the external DNS record, the IAM role, or the storage bucket it was going to delete **remains, orphaned and billed**. So it's a legitimate last resort, and it should always be followed by manually checking for and cleaning up whatever the controller would have handled.

The prevention: **delete custom resources before uninstalling the operator that manages them**, which is the order people reliably get wrong.

**K12.5 — Owner references and cascading deletion**

`metadata.ownerReferences` records that an object is owned by another. The **garbage collector** deletes objects whose owners are all gone. This is how deleting a Deployment removes its ReplicaSets and their Pods — nobody wrote that logic; it's a generic property of ownership.

Deletion propagation modes:

- **`Background`** (default) — the owner is deleted immediately and dependents are cleaned up asynchronously.
- **`Foreground`** — the owner stays in a terminating state (with a `foregroundDeletion` finalizer, K12.4) until all dependents are gone, then it's removed.
- **`Orphan`** — the owner is deleted and dependents are left, with their owner references stripped. `kubectl delete --cascade=orphan` — used deliberately when recreating a StatefulSet without disturbing its pods (K5.5).

Points that matter:

- **Owner references cannot cross namespaces**, and a namespaced object cannot own a cluster-scoped one. A cross-namespace owner reference is silently treated as invalid and **the garbage collector may delete the dependent**, which is a genuinely nasty trap for operator authors.
- **Setting owner references is how an operator gets cleanup for free** — mark every resource you create as owned by the custom resource, and deleting the CR removes everything. This is the idiomatic pattern and the reason well-written operators don't need their own deletion logic.
- **Orphaned resources** — objects whose owner was force-deleted, or created without owner references — accumulate silently and are a common source of mystery resources and cost.

**K12.6 — The API aggregation layer**

Beyond CRDs, the aggregation layer lets you **register an entire external API server** under a path of the Kubernetes API. An `APIService` object maps an API group/version to a Service, and the main API server **proxies requests for that group to your server**.

The canonical examples: **metrics-server** serving `metrics.k8s.io` (which is why `kubectl top` works but the data isn't in etcd), and **Prometheus Adapter** serving `custom.metrics.k8s.io` for HPA (K7.1).

**CRDs versus aggregation** — the concept to be clear on: **CRDs are declarative objects stored in etcd by the API server**; aggregation is for APIs that need **their own storage, their own semantics, or computed rather than stored responses**. Metrics are the perfect example: they're computed, high-cardinality, and short-lived, so storing every measurement as an etcd object would be absurd. For essentially everything else, CRDs are the right answer, and aggregation is a specialist tool.

The operational implication worth knowing: **an unavailable aggregated API service degrades the whole API server**, because `kubectl get all` and discovery calls try to reach it and time out. A broken metrics-server makes many unrelated commands slow, and a dead APIService is a classic cause of a **namespace stuck terminating** (K12.4), because the namespace controller can't enumerate resources in that group. Check `kubectl get apiservices` for `False` availability when the cluster is behaving strangely — it's an unintuitive diagnostic that resolves genuinely confusing symptoms.

---

## K13. Design judgement

The section that most distinguishes senior from mid-level. For each of these, the strongest answers include the case *against* the thing being asked about.

**K13.1 — When Kubernetes is the wrong choice**

The honest cases:

- **A small number of simple services with a small team.** Kubernetes' operational surface — upgrades, add-ons, networking, RBAC, observability — is a substantial fixed cost regardless of how much you run on it. For three services, ECS Fargate, App Runner, or plain VMs deliver the same outcome with a fraction of the burden.
- **Nobody on the team has run it before, and it's not a strategic investment.** Kubernetes concentrates complexity into a system that fails in unfamiliar ways. Adopting it without the expertise or the time to build it means the first production incident is also the first serious learning experience.
- **A monolith that isn't going to be decomposed.** Containerising a monolith to run one pod gets you a much harder deployment mechanism than the one you had.
- **Genuinely bursty, event-driven, or infrequent workloads** — Lambda or Cloud Run bills per invocation and requires no capacity management; Kubernetes needs nodes running regardless (K7.8).
- **Very small workloads where the control plane and system overhead dominate.** A cluster running three small services still needs CoreDNS, a CNI, monitoring, an ingress controller, and node headroom.
- **Highly specialised infrastructure** — extreme low-latency, unusual hardware, or strict real-time requirements where the abstraction fights you.

The framing that makes this a senior answer: **Kubernetes is a platform for building platforms.** Its value comes from standardising across many teams and services — a common deployment model, a common security posture, a common extension mechanism. If you don't have that multiplicity, you're paying the platform cost without collecting the platform benefit. And being able to say "we chose ECS for this and it was right" demonstrates judgement rather than allegiance.

**K13.2 — EKS vs self-managed vs ECS**

- **ECS** — simplest for pure container orchestration on AWS. Deep AWS integration, no control plane to manage, far smaller conceptual surface, and with Fargate almost no operational load (A5.3). Costs: AWS-only, a much smaller ecosystem, and less expressive scheduling and extensibility. **The right answer more often than people admit**, particularly for a small number of straightforward services.
- **EKS** — managed control plane, the Kubernetes ecosystem, portability of skills and manifests, and the extension model (K12). Costs: the control plane fee, node management, add-on upgrade coupling (K11.9), and a substantially larger learning and operational surface.
- **Self-managed Kubernetes on EC2** — full control including API server flags and etcd placement. Costs: you now own etcd, control plane HA, upgrades, and certificate rotation. **Very hard to justify on a cloud that offers a managed option**, unless you have a specific requirement — air-gapped, unusual API server configuration, or regulatory constraints on control plane data.

The decision framing for a stated context:

> "For a team of six running eight services with no Kubernetes experience and no multi-cloud requirement, ECS on Fargate delivers this faster and with far less to operate. EKS earns its cost once you have enough teams that a shared platform contract is worth building — the ecosystem, the extension model, and portable skills start paying off, and by then you can justify a platform team to own the upgrade and add-on burden. Self-managed I'd only take on for a specific regulatory or configuration requirement that EKS can't meet."

The signals to weigh explicitly: **team size and existing expertise**, **number of teams that would share the platform**, **whether portability across clouds is a real requirement or an aspiration**, **whether you need the ecosystem** (operators, service mesh, Argo, policy engines), and **who is going to run upgrades in eighteen months.**

**K13.3 — Designing a namespace and tenancy model**

A workable model, with the reasoning:

- **Namespace per application per environment** (`payments-api-prod`), or **per team per environment** if teams own several small services. Environments generally belong in **separate clusters** (K11.8) rather than separate namespaces, because environment separation should survive a cluster-level mistake.
- **Platform namespaces** (`ingress`, `monitoring`, `argocd`, `cert-manager`) owned by the platform team, with application teams having no write access.
- **Each namespace gets, automatically at creation**: a RoleBinding for the owning team, a ResourceQuota and LimitRange (K6.12), a default-deny NetworkPolicy plus DNS and egress allowances (K4.10), PSA labels at `restricted` or `baseline` (K8.6), and ownership labels for cost attribution (A12.2). **Generated by policy, not by a runbook** — Kyverno's generate rules or a namespace controller (K8.9), because anything manual is eventually skipped.
- **Namespace creation is a governed, automated request** — a PR to a repo, not a kubectl command.

The judgement to articulate:

- **Namespaces are not a security boundary against untrusted tenants** (K8.10). Say this explicitly, because it's the thing people assume.
- **Design boundaries around policy differences, not the org chart** — the same argument as OU design (A1.12). Teams reorganise; policy requirements are more stable.
- **Avoid namespace-per-microservice-per-team explosion**, because per-namespace overhead is real (quotas, bindings, policies, monitoring config) and hundreds of near-identical namespaces are a maintenance problem.
- **Cluster-scoped resources are the leak** — CRDs, ClusterRoles, webhooks, and StorageClasses are shared by everyone, so any tenant needing their own is a signal to reconsider the model (K11.7).

**K13.4 — The platform team's contract with application teams**

The contract has two halves, and stating both is what makes it a contract rather than a service desk.

**The platform team provides**: a paved road to production (a template or chart that works, a pipeline, an environment); the cluster and its add-ons, kept upgraded and patched; the security baseline (RBAC, network policy, PSA, secrets); observability infrastructure — metrics, logs, traces collected and queryable; guaranteed capacity and autoscaling; documented SLOs **for the platform itself**; and a support path.

**Application teams provide**: correct resource requests (K6.5); working probes (K9.10); PDBs (K6.9); workloads that tolerate disruption — SIGTERM handling, statelessness where possible, no assumption of node longevity (K2.12); their own application-level monitoring and alerting; ownership labels; and **being on call for their own service** (K9.14).

The principles that make it work:

- **The paved road must be genuinely easier than going around it.** If compliance means fighting the platform, teams route around it, and you get shadow infrastructure. Security controls that come free with the standard path are followed; ones that require effort are not.
- **Golden paths, not gates.** The platform team's job is to make the right thing the default, not to review every deployment. A platform team that becomes a bottleneck has failed regardless of how good the platform is.
- **Clear ownership of failure.** When a pod is OOMKilled, that's the application team's; when the ingress controller is down, that's the platform's. Ambiguity here is what produces the "platform team is on call for everything" failure mode.
- **Escape hatches with a process.** Teams will have legitimate exceptions; a documented, time-bounded exception path (A10.28) is better than either a hard no or an undocumented yes.

**K13.5 — The real operational cost of running Kubernetes**

Beyond the infrastructure bill:

- **Upgrades, three times a year, forever** — control plane, nodes, and the whole add-on dependency graph (K11.1, K11.9). This is the single largest recurring cost and the one most often omitted from adoption business cases.
- **Add-on ownership** — every component (CNI, CSI, ingress, cert-manager, monitoring, policy engine, autoscaler) is production software you patch, monitor, and upgrade permanently (K11.9).
- **On-call for a complex distributed system** with unfamiliar failure modes, most of which are in this document.
- **The learning curve, paid by every team**, not just the platform team. Application engineers need to understand requests and limits, probes, and why their pod was evicted — and the ones who don't produce the incidents.
- **Cost management** — clusters default to being expensive: over-requested pods (K6.5), idle nodes (K7.7), cross-AZ traffic (A12.4), and unattributed spend without label discipline.
- **Security surface** — RBAC, admission control, image supply chain, runtime, and network policy are each an ongoing programme (K8).
- **Tooling and glue** — GitOps, CI integration, secrets, templating, and the internal documentation to make it usable.

The honest number to give: **a serious Kubernetes platform needs dedicated people, not a fraction of someone's time** — realistically two to four engineers for a meaningful production estate. Being able to say that clearly is a strong senior signal, because the common failure is adopting Kubernetes with a part-time owner, and what follows is an under-maintained cluster that everyone depends on and nobody can upgrade.

The counterweight to state fairly: **that cost is largely fixed, so it amortises.** The same platform team supports ten services or two hundred. That's exactly why the adoption question is about scale (K13.1) — and why the right answer for a small estate is usually "not yet".

**K13.6 — Designing for HA across AZs, and stating the failure modes it survives**

The design (the AWS-layer version is A11.4):

- **Nodes across three AZs**, with capacity sized so that **losing one AZ still leaves enough to serve peak** — N-1 sizing, not N.
- **Topology spread constraints** on zone and hostname for every meaningful workload (K6.8).
- **PDBs** on everything (K6.9).
- **Control plane** — managed and multi-AZ by the provider; self-managed means etcd members in three AZs (K1.2).
- **Platform components spread and replicated** — CoreDNS, ingress controllers, and the metrics stack are single points of failure if they're not (K4.6).
- **Stateful workloads**: replicated across AZs at the application layer, or accept that a zonal EBS volume pins its pod to one AZ (K5.3).
- **Load balancing across AZs**, with health checks that actually detect failure.

**What it survives**: single-node failure (rescheduling, seconds to minutes); single-AZ failure for stateless workloads (automatic, if capacity exists); rolling upgrades and node replacement (K11.4); individual pod and container failures.

**What it does not survive**, and stating these is the point of the item:

- **A regional failure** — this is a multi-AZ design, not a DR design (A11.2).
- **Control plane loss** — degraded, not dead, but no self-healing (K11.10).
- **A bad config or deploy applied everywhere.** The most common real outage is not infrastructure failure; it's a change. Multi-AZ provides no protection at all, and progressive delivery (K2.11) does.
- **Capacity exhaustion during the failure** — if the surviving AZs can't get instances because everyone else is failing over too, the design is theoretical (A11.9).
- **A cluster-wide dependency failing** — CoreDNS, the CNI, an admission webhook (K8.8), or the container registry.
- **Stateful data loss**, unless the data layer is separately replicated.

The closing point: **the failure modes it doesn't survive are more instructive than the ones it does**, and an answer that volunteers them is far stronger than one that describes a resilient-looking diagram.

**K13.7 — Migrating a workload onto Kubernetes incrementally**

The shape of a low-risk migration:

1. **Pick the right first workload** — stateless, non-critical, with a small blast radius and an owning team that wants to do it. **Do not start with the most important service**, and do not start with the hardest one to prove it can be done.
2. **Containerise and run it in parallel**, serving no production traffic, while the existing deployment continues. Validate startup, config, secrets, logging, and metrics.
3. **Shift traffic gradually at the edge** — DNS weighting (A8.3), a load balancer with targets in both, or an API gateway splitting between old and new. **Keep the old deployment running and capable of taking 100% instantly.**
4. **Observe with real traffic** at 5%, then 25%, then more — comparing error rates and latency between the two, not just checking the new one looks fine.
5. **Cut over fully**, then leave the old path in place for a defined period before decommissioning (A8.5's argument about watching actual traffic rather than trusting TTLs applies directly).
6. **Repeat**, building the paved road as you go so the second service is easier than the first.

The judgement points:

- **Strangler fig for a monolith** — route specific paths to new containerised components while the monolith serves the rest, decomposing incrementally rather than rewriting.
- **Leave state where it is initially.** Keep using RDS, keep using the existing queue. Migrating compute and state simultaneously multiplies the risk for no benefit (K13.8).
- **Networking is usually the hard part**, not the containers — reaching existing databases, firewall rules for new source IPs, service discovery across the boundary, and hybrid DNS (A3.14).
- **The rollback plan is "send traffic back"**, which is why the old deployment stays warm. A migration whose rollback is "redeploy the old thing" isn't a rollback.
- **Migrate the observability first**, so you can actually compare old and new. Migrating blind means you find out from users.

**K13.8 — Running stateful workloads, and whether you should**

**How**, if you do: StatefulSets for identity and per-pod storage (K2.8, K5.5); a **mature operator** rather than hand-rolled manifests, because the hard part is failover, backup, and version upgrades, not the initial deployment (K12.2); anti-affinity or topology spread so replicas aren't in one AZ (K6.8); PDBs sized so quorum survives a drain (K6.9); Guaranteed QoS (K6.4); careful reclaim policy (K5.4); and **backups via the database's own mechanism**, not volume snapshots (K11.6, A7.3).

**Whether you should** — the honest answer:

**Usually not, on a cloud that offers a managed equivalent.** RDS, Aurora, ElastiCache, and MSK give you replication, automated failover, backups, point-in-time recovery, patching, and a support contract. Running Postgres in-cluster means owning all of that yourself, and the failure modes are the ones that end careers — data loss, split brain, a corrupt restore. **The engineering effort to match a managed service's durability guarantees is enormous and almost never justified by the saving.**

**When it is defensible:**

- **No managed equivalent exists** — a specialised database, or software with no hosted offering.
- **A hard requirement the managed service can't meet** — a specific version or extension, data residency, or air-gapped operation.
- **The workload is genuinely stateful-but-recreatable** — caches, search indices rebuildable from a source of truth, ephemeral analytics. Losing the data is an inconvenience, not an incident. This is where in-cluster state is clearly fine.
- **You already run a mature operator with real expertise** behind it, and have tested restore and failover repeatedly.

The framing that lands: **the question isn't whether Kubernetes can run a database — it can, and operators have got genuinely good. The question is whether your team wants to be responsible for the durability of that data at 3am.** For a fintech, that's usually a straightforward no for the systems of record, and a reasonable yes for caches and derived data. Being able to draw that line explicitly, rather than answering with either "Kubernetes can do everything" or "never run databases in Kubernetes", is the senior answer.

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 136 items, reading straight through produces recognition rather than recall.
- **The highest-leverage sections for interview time are K9, K6, and K13.** K9 because live debugging questions are the most common practical assessment; K6 because requests, limits, and scheduling underpin half the other answers; K13 because that's where senior candidates are separated from mid-level ones.
- **K7, K10, and K11 are where platform-role interviews go** once the basics are established — autoscaling economics, GitOps, and the upgrade treadmill are the things a platform team actually spends its time on.
- **The failure modes are the part that reads as experience.** The liveness probe cascade (K9.11), the `ndots:5` DNS amplification (K4.6), the single-replica PDB blocking every upgrade (K6.9), the webhook `failurePolicy: Fail` that bricks a cluster (K8.8), and force-deleting a StatefulSet pod on an unreachable node (K9.7) are all things you only know from having met them or having been told by someone who did.
- **Cross-references into AWS are dense in K5, K7, and K8** — A5.5–A5.8, A2.7, A11.4, and A10.15 all connect directly. Interviewers move between the two domains constantly, and following those links is good preparation for that.
