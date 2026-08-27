# Docker & Containers — Answer Key

Companion to Domain 7 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **ECR specifics are A5.1**, **image scanning and artifact signing are S7.5–S7.7**, **ECS is A5.2–A5.4**, and **orchestration is the Kubernetes domain**. This domain is containers themselves — what they are, how images are built, and how they behave and fail at runtime.

Three notes on how this domain is interviewed:

- **D1 is asked more often than its size suggests.** "What is a container, actually?" is a standard opener, and the answer separates people who understand namespaces and cgroups from people who think of it as a lightweight VM. D1.6 and D9.11 are the same insight applied to isolation.
- **D10 is where practical experience is unmistakable.** Exit code 137, a container that exits immediately, and an image pull failure by architecture are everyday realities, and the answers can't be reconstructed from documentation under pressure.
- **D2 and D3 carry the most items and the most day-to-day value.** Layer caching, multi-stage builds, and base image choice are what you'll actually be doing, and D2.9/D2.10 (build args are not secrets) is the one people most often get wrong in a way that matters.

---

## D1. Fundamentals & internals

**D1.1 — What a container actually is**

**A container is a normal Linux process, with kernel features applied to constrain what it can see and use.** There is no container object in the kernel — the word describes a combination of:

- **Namespaces** (D1.3) — control **what the process can see**: its own process tree, network stack, filesystem mounts, hostname, and users.
- **cgroups** (D1.4) — control **what the process can use**: CPU, memory, I/O, and PIDs.
- **A root filesystem** from an image (D1.5), applied with `chroot`/`pivot_root`.
- **Capabilities, seccomp, and LSMs** (D9.4, D9.7) — restricting what it may do.

**The framing that lands: run `ps aux` on the host and you see the containerised process listed among all the others**, with a normal PID, scheduled by the same kernel scheduler. **It is not running "inside" anything.** From the host's perspective it's just a process; from its own perspective it appears to be alone on a machine, because the namespaces lie to it convincingly.

The consequences that follow, and which the rest of the domain depends on:

- **Startup is process startup** — milliseconds, not the seconds a VM needs to boot a kernel.
- **Overhead is essentially zero** — no hypervisor, no guest kernel.
- **They share the host kernel** (D1.6), which is the source of both the efficiency and the security limitation (D9.11).
- **"It's not a VM" is the single most useful correction** to make, because almost every misconception in this domain follows from that mental model.

**D1.2 — Container vs VM, and the isolation tradeoff**

| | Virtual machine | Container |
|---|---|---|
| Isolation boundary | Hypervisor, hardware-assisted | Kernel features |
| Kernel | **Its own** | **Shared with the host** |
| Boot time | Seconds to minutes | Milliseconds |
| Overhead per instance | Hundreds of MB, a full OS | Megabytes, just the process |
| Density per host | Tens | Hundreds or thousands |
| OS flexibility | Any OS | **Same kernel — Linux containers need a Linux kernel** |
| Attack surface to escape | The hypervisor (small, hardened) | **The entire kernel syscall interface (large)** |

**The isolation tradeoff, stated precisely**: a VM escape requires exploiting the hypervisor, which presents a deliberately narrow interface. **A container escape requires exploiting the kernel, which presents hundreds of syscalls and is a vastly larger attack surface** — and a successful escape lands you on the host with access to every other container on it.

**So VMs give stronger isolation; containers give better density and speed.** That's the whole trade, and it's why the answer to "can I run untrusted tenants' code in containers on shared hosts" is no (D9.11).

**The middle ground worth naming**: **Firecracker microVMs** (what AWS Lambda and Fargate use), **Kata Containers**, and **gVisor** (a user-space kernel intercepting syscalls). These give VM-grade isolation with container-like startup, and they exist precisely because the tradeoff above is uncomfortable for multi-tenant workloads.

**D1.3 — Which namespaces do what**

- **PID** — the process tree. The container's first process is **PID 1** inside, while being some other PID on the host. It cannot see or signal host processes. **This is where the PID 1 problem comes from** (D4.5).
- **NET** — the network stack: interfaces, routes, iptables rules, and the port space. **Each container gets its own**, which is why two containers can both listen on port 8080 without conflict, and why port publishing is needed to reach them (D5.2).
- **MNT** — the mount table. The container sees its image's filesystem as `/` and cannot see the host's mounts unless they're deliberately shared (D6.1).
- **UTS** — hostname and domain name. Why a container has its own hostname.
- **IPC** — System V IPC and POSIX message queues; isolates shared memory between containers.
- **USER** — maps UIDs inside to different UIDs outside. **Root inside can be an unprivileged user outside**, which is the basis of rootless containers and user namespace remapping (D9.6). **Not enabled by default in standard Docker**, which is why root in a container is root on the host if it escapes (D9.1).
- **CGROUP** — hides the host's cgroup hierarchy from the container.
- **TIME** (newer) — allows a different system clock offset.

The practical points: **namespaces can be shared deliberately** — Kubernetes pods share the network and IPC namespaces so containers reach each other on `localhost` (K2.1); `--pid=host` or `--net=host` opts out for a specific namespace, and each such opt-out is a meaningful reduction in isolation (D5.1, D9.3).

**D1.4 — What cgroups control and how limits are enforced**

**cgroups (control groups) limit and account for resource usage.** The controllers that matter:

- **memory** — a hard limit. **Exceeding it triggers the cgroup OOM killer, which kills a process in the group** (D4.2, D10.6). Memory is **incompressible**: you cannot give a process less than it has already allocated, so the only options are refuse or kill.
- **cpu** — a quota per period (`cpu.max`: e.g. 50000µs per 100000µs = 0.5 CPU). **Exceeding it throttles: the process is descheduled until the next period.** CPU is **compressible** — you can simply give less, so nothing dies.
- **pids** — a maximum process count, which is the defence against a fork bomb.
- **io** — block I/O weight and throughput limits.
- **cpuset** — pinning to specific cores and NUMA nodes.

**The asymmetry between memory and CPU is the important point** and it explains the runtime behaviour in D4.2: **over-limit on memory is fatal and immediate; over-limit on CPU is a slowdown.** That difference should drive how you set each (D11.4).

**cgroups v2** is the current unified hierarchy (all controllers in one tree, rather than v1's separate hierarchies per controller) and is the default on modern distributions — worth knowing because file paths and some semantics differ, and some older tooling assumes v1.

The connection to make: **CPU throttling is invisible in utilisation metrics** — a container throttled 70% of each period can show 30% average CPU while its latency is terrible (O9.4). `cpu.stat`'s `nr_throttled` and `throttled_time` are where you see it.

**D1.5 — Layers, the union filesystem, and the writable layer**

**An image is an ordered stack of read-only layers.** Each layer is a filesystem diff produced by one instruction in the build (D2.2). A **union filesystem** (OverlayFS is the modern default) presents the stack as a single merged view.

**When a container runs, a thin writable layer is added on top.** All writes go there; the image layers are untouched.

**Copy-on-write** is the mechanism: reading a file finds it in whichever layer holds the topmost version. **Writing to a file that lives in a read-only layer copies the whole file up into the writable layer first**, then modifies the copy.

The consequences that matter:

- **Layers are shared between containers and images.** Ten containers from one image share one copy of the read-only layers on disk — which is why container density is cheap.
- **The writable layer is ephemeral** (D6.2) — destroyed with the container. **Anything written there is lost.**
- **Deleting a file in a later layer doesn't remove it from the image.** OverlayFS writes a "whiteout" marker; the data is still present in the earlier layer and extractable. **This is why a secret used in one `RUN` and deleted in the next is still in the image** (D9.8) — the single most important consequence of the layer model.
- **Copy-on-write has a cost**: modifying a large file in a read-only layer copies it entirely first, so write-heavy workloads on the container layer perform poorly. **Use a volume** (D6.1).
- **Layer count and ordering drive caching** (D2.6) and image size (D3.7).

**D1.6 — Sharing the host kernel, and what that rules out**

**Every container on a host runs on that host's kernel.** There is no per-container kernel.

**What that rules out:**

- **Different operating systems.** A Linux container needs a Linux kernel. **Docker Desktop on macOS and Windows runs a Linux VM** — the containers are in that VM, not on the host OS, which explains the filesystem performance characteristics in D6.5.
- **Different kernel versions.** A container needing a kernel feature the host lacks won't work, regardless of what the image contains.
- **Kernel modules.** A container cannot load one (without privileged access, D9.3) — and if it does, **it's loaded into the host kernel, affecting everything.**
- **Kernel parameter changes.** `sysctl` settings are largely host-wide; only a few are namespaced. **Changing `net.core.somaxconn` inside a container affects the host** unless it's one of the namespaced ones.
- **Independent kernel patching.** Patching the kernel means restarting the host, affecting every container on it.

**The security consequence, which is the item's real point**: **a kernel vulnerability is a vulnerability for every container on the host simultaneously.** There is no per-container isolation from it. That's the mechanism behind D9.10 and D9.11, and it's why untrusted multi-tenancy needs a VM boundary (D1.2).

**D1.7 — The OCI specs**

The Open Container Initiative maintains three specifications, and the separation is the useful part:

- **Image spec** — the format of an image: the layer archives, the config JSON (entrypoint, env, working directory), and the manifest tying them together. **This is why an image built by Docker runs under containerd, CRI-O, or Podman** — the format is standard, not Docker's.
- **Runtime spec** — how to run a container from an unpacked filesystem bundle plus a `config.json` describing namespaces, cgroups, mounts, and capabilities. **runc implements this** (D1.8).
- **Distribution spec** — the registry HTTP API: how images are pushed and pulled, how manifests and blobs are addressed. **This is why any registry works with any client.**

**Why it matters practically:**

- **The dockershim removal in Kubernetes 1.24 changed nothing about your images**, because they're OCI images and containerd runs them natively (K1.7). **This is a favourite interview question and the correct answer is "nothing broke, because Docker's image format is the OCI format".**
- **You're not locked into Docker** — buildah, kaniko, BuildKit standalone, and Podman all produce OCI images.
- **The distribution spec is why artifact types beyond images** — Helm charts, SBOMs (S7.8), signatures (S7.7) — can live in a container registry, which is increasingly how the ecosystem works.

**D1.8 — Docker, containerd, and runc**

The layers, top to bottom:

- **Docker (the CLI and daemon)** — the user-facing tool. Builds images, manages networks and volumes, and provides the developer experience. **It does not run containers itself.**
- **containerd** — a container runtime daemon: manages image pull, storage, and container lifecycle. Speaks CRI, so **Kubernetes talks to it directly** without Docker. Donated to the CNCF.
- **containerd-shim** — one per container, holding the container's process so **containerd can be restarted without killing running containers.**
- **runc** — the low-level OCI runtime. **This is the thing that actually creates namespaces and cgroups and executes the process** (D1.1), then exits.

```
docker CLI → dockerd → containerd → shim → runc → your process
kubelet    → CRI     → containerd → shim → runc → your process
```

**The points that matter:**

- **Kubernetes removing dockershim** (1.24) meant the kubelet talks to containerd directly rather than through Docker. **Docker was an unnecessary layer in that path**, and removing it changed nothing about images (D1.7).
- **Alternative low-level runtimes** slot in where runc sits: **gVisor** (`runsc`) and **Kata Containers** provide stronger isolation (D1.2), configured as a RuntimeClass in Kubernetes.
- **`crictl` and `nerdctl`** are the containerd-level CLIs, which is what you use to debug on a node with no Docker (K9.1).

**D1.9 — Architecture and multi-arch images**

**A container image contains compiled binaries for a specific CPU architecture.** An `amd64` image will not run on an `arm64` host, and vice versa.

**Why it's now a daily concern**: Apple Silicon laptops are arm64, AWS Graviton instances are arm64 (A4.2), and most cloud production is still amd64. **So building on a laptop and deploying to production crosses an architecture boundary**, which is the source of D10.11's "works on my machine".

**Multi-arch images** solve it with a **manifest list** (or OCI image index): a manifest that points at several per-architecture manifests. **The client requests the image by name, and the registry serves the manifest matching the client's platform** (D8.3). One tag, many architectures, transparent to the user.

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t acme/api:1.4.2 --push .
docker buildx imagetools inspect acme/api:1.4.2      # see what architectures are present
```

**The failure modes to name:**

- **`exec format error`** — the image ran and the binary is for the wrong architecture. **The classic symptom** (D10.7, D10.11).
- **Silent emulation** — Docker Desktop runs amd64 images on arm64 via QEMU, which **works and is very slow**, so people don't notice until production.
- **Building single-arch by accident** — a plain `docker build` on an M-series Mac produces an arm64-only image, which then fails on amd64 nodes.

The practicalities: **buildx with QEMU emulation is simple and slow**; **native builders per architecture** (a build farm, or GitHub's arm64 runners) are much faster for real pipelines (D3.6).

---

## D2. Images & Dockerfiles

**D2.1 — Writing a Dockerfile for a real application**

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-slim@sha256:abc123... AS base
WORKDIR /app

FROM base AS deps
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --omit=dev

FROM base AS build
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build

FROM gcr.io/distroless/nodejs20-debian12:nonroot AS runtime
WORKDIR /app
COPY --from=deps  /app/node_modules ./node_modules
COPY --from=build /app/dist          ./dist
USER nonroot
EXPOSE 3000
ENV NODE_ENV=production
ENTRYPOINT ["/nodejs/bin/node", "dist/server.js"]
```

The decisions this demonstrates, each of which is an item in its own right:

- **Multi-stage** so build tooling doesn't ship (D3.1).
- **Dependencies copied and installed before the source**, so a code change doesn't invalidate the dependency layer (D2.6).
- **`npm ci` not `npm install`** — installs exactly from the lockfile and fails if it disagrees (S7.2).
- **Cache mounts** for the package manager (D3.4).
- **A digest-pinned base** (D2.15).
- **Distroless runtime, non-root** (D2.13, D9.1).
- **`ENTRYPOINT` in exec form** so signals reach the process (D2.3, D4.4).
- **`.dockerignore`** alongside it (D2.5).

**D2.2 — Instructions and which create layers**

**Create a layer** (they modify the filesystem): `RUN`, `COPY`, `ADD`.

**Do not create a layer** (metadata only, though each still creates an image config change): `FROM` (starts from the base's layers), `ENV`, `ARG`, `LABEL`, `EXPOSE`, `WORKDIR`, `USER`, `CMD`, `ENTRYPOINT`, `VOLUME`, `HEALTHCHECK`, `STOPSIGNAL`, `SHELL`, `ONBUILD`.

The per-instruction notes worth knowing:

- **`WORKDIR`** creates the directory if absent, and **is preferable to `RUN cd`**, which doesn't persist between instructions since each `RUN` is a fresh shell.
- **`EXPOSE` publishes nothing.** It's documentation plus a hint for `-P` (D5.2) — a very common misunderstanding.
- **`VOLUME`** declares a mount point, and **it has a surprising effect: any subsequent write to that path in the build is discarded**, and it forces an anonymous volume at runtime, which accumulates (D6.6). Generally better omitted and specified at run time.
- **`ARG` vs `ENV`** — D2.8.
- **`ONBUILD`** triggers instructions in a downstream build; rare and confusing enough to avoid.

**The historical framing**: layer count used to matter a great deal (there was a hard limit, and every layer added overhead). **With BuildKit and modern storage drivers it matters much less**, so the advice to chain everything into one giant `RUN` is dated — **splitting instructions for better cache granularity is usually the better trade now** (D2.6). What still matters is *what ends up in* a layer (D9.8) and total size (D3.7).

**D2.3 — CMD vs ENTRYPOINT, shell vs exec form**

- **`ENTRYPOINT`** — the executable. Arguments passed to `docker run` are **appended** to it.
- **`CMD`** — either the whole command (if no `ENTRYPOINT`) or **default arguments to the `ENTRYPOINT`**. Arguments to `docker run` **replace** it.

**How they combine:**

```dockerfile
ENTRYPOINT ["/app/server"]
CMD ["--port", "8080"]
```
- `docker run img` → `/app/server --port 8080`
- `docker run img --port 9090` → `/app/server --port 9090`
- `docker run --entrypoint /bin/sh img` → overrides the entrypoint entirely

**Shell vs exec form is the more consequential distinction:**

- **Exec form** `["executable", "arg"]` — **executes directly, so the process is PID 1** and receives signals (D4.3, D4.4).
- **Shell form** `executable arg` — runs as `/bin/sh -c "executable arg"`, so **the shell is PID 1 and the application is a child.** `sh` does not forward `SIGTERM` to children, **so `docker stop` waits the full grace period and then SIGKILLs your application** — no graceful shutdown, dropped connections, and an unclean exit.

**Always use exec form for `ENTRYPOINT` and `CMD`.** This is one of the highest-value single facts in the domain, because the failure is silent — the container works fine and shutdown is always ungraceful.

The exception: shell form is needed for variable expansion (`CMD echo $HOME`), and the correct answer there is an entrypoint script, `ENTRYPOINT ["/bin/sh", "-c", "exec myapp $ARGS"]` with `exec` so the shell is replaced.

**D2.4 — COPY vs ADD**

**`COPY`** copies files and directories from the build context into the image. That's all it does.

**`ADD`** does the same, plus two extras: **it auto-extracts local tar archives**, and **it can fetch a remote URL.**

**Why `COPY` is the default choice:**

- **Predictability.** `ADD ./thing.tar.gz /app/` **silently extracts it**, which is surprising if you wanted the archive. `COPY` does exactly what it says.
- **Remote fetching in `ADD` is a poor mechanism**: no verification of the download by default, it doesn't use the layer cache well, and it can't be cleaned up in the same layer. **`RUN curl` with a checksum check** is more explicit and lets you validate.
- **Security** — `ADD` with a URL fetches arbitrary remote content into your image, which is a supply chain concern (S7.1).

**Use `ADD` when** you genuinely want tar auto-extraction, which is essentially the only justified case.

The modern additions worth naming: **`ADD` with a git repository URL** and **`ADD --checksum=sha256:...`** for remote fetches, which addresses the verification objection. Also **`COPY --from=stage`** for multi-stage (D3.1), **`COPY --chown=user:group`** to avoid a separate `RUN chown` layer (D6.4), and **`COPY --link`** which improves cache behaviour by making the layer independent of its parents.

**D2.5 — `.dockerignore` and build context**

**The build context is everything in the directory sent to the builder before the build starts.** With `docker build .`, the entire directory tree is packaged and transferred to the daemon.

```
.git
node_modules
dist
*.log
.env
.terraform
**/__pycache__
Dockerfile
.dockerignore
```

**The effects:**

- **Build time.** A context containing `.git` (often hundreds of MB), `node_modules`, and build artefacts takes seconds or minutes just to transfer before anything happens (D3.9). **On a remote builder, that's a network transfer.**
- **Cache invalidation.** Without ignores, `COPY . .` includes files that change constantly — local logs, editor files, `node_modules` timestamps — **so the layer cache is invalidated on every build even when nothing relevant changed** (D3.3).
- **Image size and correctness** — copying local `node_modules` built for macOS into a Linux image produces a broken image with native modules for the wrong platform. **A very common "works on my machine" failure.**
- **Security** — **`.env`, `.aws/credentials`, private keys, and `.git` (which contains full history, including secrets that were deleted, S6.3) all end up in the image** if `COPY . .` picks them up. **This is a genuine and frequent leak path** (D9.8).

The practical guidance: **write it before the Dockerfile**, treat it like `.gitignore` with more consequence, and **verify with `docker build --progress=plain`** which shows the context transfer size.

**D2.6 — Ordering instructions for cache hits**

**The rule: least-frequently-changing first.** A cache hit requires every preceding layer to be identical; **once one layer's cache is invalidated, every layer after it rebuilds.**

```dockerfile
# BAD — source copied before dependencies installed
COPY . .
RUN npm ci                    # re-runs on every code change

# GOOD — dependency manifest first
COPY package.json package-lock.json ./
RUN npm ci                    # cached unless dependencies change
COPY . .                      # only this rebuilds on a code change
```

**The ordering that generalises:**

1. `FROM` and base setup.
2. System packages (`apt-get`) — change rarely.
3. **Dependency manifests only** (`package.json`, `requirements.txt`, `go.mod`, `pom.xml`, `Gemfile`).
4. **Dependency installation** — the expensive step, now cached.
5. Application source.
6. Build.

**The invalidation rules**: for `RUN`, the cache key is the instruction text; for `COPY` and `ADD`, it's a **checksum of the file contents** (not timestamps, which is worth knowing — touching a file doesn't invalidate). **`ARG` values that are used invalidate from that point.**

**The payoff is large**: a Node or Java application where dependency installation is 90% of the build time goes from three minutes to twenty seconds on a code-only change. **Combined with cache mounts** (D3.4), even a dependency change is much cheaper.

**D2.7 — Why `apt-get update` and `install` must be in the same RUN**

```dockerfile
# BROKEN
RUN apt-get update
RUN apt-get install -y curl        # ← may use a cached, stale package index

# CORRECT
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
```

**The mechanism**: `apt-get update` downloads the package index into its own layer. If a later build changes only the `install` line, **Docker's cache serves the old `update` layer** — which may be months old. **The package index then references package versions that no longer exist in the repository**, and the install fails with a 404. Or worse, it succeeds and installs a stale version.

**This is "cache busting"**, and the failure is confusing because it appears intermittently and depends on cache state — a fresh build works, a cached one fails, and the Dockerfile is unchanged.

**Chaining them into one `RUN` means they share a cache key**, so they're always invalidated together.

The additional practices in that snippet, each worth its own point: **`--no-install-recommends`** avoids pulling in a large tree of suggested packages, often halving the added size; **`rm -rf /var/lib/apt/lists/*` in the same `RUN`** removes the index — **and it must be the same `RUN`, because deleting it in a later layer doesn't remove it from the image** (D1.5, D9.8); and pinning package versions where reproducibility matters (D11.3).

**D2.8 — Build args vs environment variables**

- **`ARG`** — available **only during the build**. Not present in the running container. Scoped to the stage it's declared in, and must be re-declared after `FROM` to be used in a later stage.
- **`ENV`** — set during the build **and persisted into the image**, so it's in the container's environment at runtime.

```dockerfile
ARG NODE_VERSION=20
FROM node:${NODE_VERSION}-slim

ARG BUILD_VERSION                 # passed with --build-arg
ENV APP_VERSION=${BUILD_VERSION}  # promoted to runtime
ENV NODE_ENV=production           # runtime config with a default
```

**Choosing:**

- **`ARG` for build-time parameters** — a base image version, a build target, a feature flag affecting compilation.
- **`ENV` for runtime configuration** with sensible defaults, overridable at `docker run` (D4.10).
- **Neither for secrets** (D2.9, D2.10).

The details: **`ARG` before the first `FROM` is global** and usable in `FROM` lines, but not inside stages without re-declaration — a frequent source of "my build arg is empty". **`ENV` overrides `ARG`** of the same name at runtime. And **`ENV` values are visible in `docker inspect`** and in the image config, so anything sensitive there is exposed (D9.9).

**D2.9 — Why build args are not a safe way to pass secrets**

```dockerfile
ARG NPM_TOKEN
RUN npm config set //registry.npmjs.org/:_authToken=${NPM_TOKEN} && npm ci
```

**This leaks the token, in several places:**

1. **`docker history` shows the build arg's value** for the layers where it was used. Anyone who can pull the image can read it:
   ```bash
   docker history --no-trunc myimage | grep -i token
   ```
2. **The value may be written into files in a layer** — in the example, `npm config set` writes it to `.npmrc`, which is in the layer permanently. **Deleting it in a later `RUN` does not remove it** (D1.5).
3. **The image config records the ARG**, visible via `docker inspect` (D9.9).
4. **CI logs** may echo the `--build-arg` on the command line (S6.7).
5. **The build cache** retains it, and a shared cache (D3.5) shares it.

**The consequence: a token passed as a build arg must be treated as leaked** and rotated (S6.4).

**The workarounds people try, and why they fail**: `RUN ... && rm .npmrc` in the same layer removes the file but the ARG is still in history; multi-stage helps only if the secret never touches the final stage *and* you don't publish intermediate stages.

**The correct answer is BuildKit secret mounts** (D2.10).

**D2.10 — BuildKit secret mounts**

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc,required=true \
    npm ci --omit=dev
```

```bash
docker build --secret id=npmrc,src=$HOME/.npmrc -t myapp .
# or from an environment variable
docker build --secret id=npmrc,env=NPM_CONFIG -t myapp .
```

**How it works**: the secret is mounted into the build step's filesystem **as a tmpfs, for the duration of that `RUN` only.** It is **never written to a layer**, never appears in `docker history`, and is not in the image config or the build cache.

The related mount types worth knowing:

- **`--mount=type=ssh`** — forwards the SSH agent for `git clone` of a private repository, without the key entering the image.
- **`--mount=type=cache`** — persistent build cache (D3.4).
- **`--mount=type=bind`** — read a file from another stage or the context without copying it into a layer.

**The requirement**: BuildKit must be the builder — the default in modern Docker, and enabled with `DOCKER_BUILDKIT=1` or `docker buildx build` otherwise. **The `# syntax=docker/dockerfile:1` directive** ensures a recent frontend that supports the syntax.

**The broader point**: the correct answer to "how do I use a credential during a build" is **never to have it in a layer** — secret mounts, or restructuring so the credential isn't needed (a pre-authenticated proxy, a vendored dependency, or an artefact fetched in CI and copied in).

**D2.11 — Tagging deliberately, and why `latest` is not a version**

**`latest` is just a default tag name.** It carries no semantics — it is **not** automatically the most recent image, it's whatever was last pushed with that tag, and **it's mutable** (D8.2).

**Why depending on it is a problem:**

- **It's not reproducible.** `FROM node:latest` today and tomorrow are different images. A build that worked yesterday fails today with no change from you (S7.2).
- **You cannot tell what's running.** Every environment says `latest`, so "which version is in production" is unanswerable.
- **Rollback is impossible** — there's no previous tag to roll back to.
- **`imagePullPolicy: Always` is implied** for `:latest` in Kubernetes, so it re-pulls constantly.
- **Deployments may not update** — with a mutable tag and a cached image, a node may keep running the old one (D10.11).

**A deliberate tagging strategy** (D8.4):

```
acme/api:1.4.2                  # semantic version — immutable, the release
acme/api:1.4                    # minor — moves with patches
acme/api:sha-a3f9c2b            # git commit — exact traceability
acme/api:2026-08-22-a3f9c2b     # timestamped build
acme/api@sha256:abc123...       # digest — the only truly immutable reference
```

**Deploy by digest or by an immutable version tag; never by `latest` or a floating tag.** And **enable tag immutability in the registry** (A5.1) so a tag cannot be moved, which turns the convention into an enforced property.

**D2.12 — Labels for metadata and traceability**

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/acme/api" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.title="payments-api" \
      org.opencontainers.image.licenses="Proprietary" \
      com.acme.team="payments" \
      com.acme.cost-centre="CC-4471"
```

**The OCI standard label set** (`org.opencontainers.image.*`) is the one to use, because tooling recognises it — GitHub links packages back to their source repository via `image.source`, and scanners and SBOM tools read them (S7.8).

**Why it matters:**

- **Traceability back to a commit.** **"What code is running in production?" answered from the image itself**, via `docker inspect`, without needing a separate registry of builds. **This is the primary value**, and it's what you want during an incident.
- **Ownership** — which team, which cost centre, who to page (A12.2's tagging argument applied to images).
- **Automation** — retention policies (D8.5), promotion rules, and compliance checks can key off labels.

The practicalities: **labels are metadata, not layers**, so they're free. **Populate from CI** with build args (D2.8) — `--build-arg GIT_SHA=$(git rev-parse HEAD)`. **`--label` on `docker build`** sets them without a Dockerfile change. And **`docker inspect --format '{{json .Config.Labels}}'`** reads them back.

**D2.13 — Base image choice**

| Base | Size | Contents | Use when |
|---|---|---|---|
| `ubuntu` / `debian` | ~70–120MB | Full distro, package manager, shell | You need a full userland; debugging matters more than size |
| `-slim` | ~30–80MB | Minimal distro, package manager, shell | **The pragmatic default** — apt available, much smaller |
| `alpine` | ~5–15MB | musl libc, busybox, apk | Size is critical and you've verified musl compatibility (D2.14) |
| `distroless` | ~2–20MB | Runtime only — **no shell, no package manager** | Production, security-sensitive (S7.6) |
| `scratch` | 0 | Nothing | A static binary with no dependencies (Go, Rust) |

**The tradeoffs:**

- **Distroless is the strongest security position** — no shell means an attacker with code execution has no tooling (S7.6), and CVE counts drop by an order of magnitude because there are almost no OS packages to have CVEs (S7.5). **The cost is debuggability**, and the answer is ephemeral debug containers (D10.3, K9.12), which fully addresses it.
- **Alpine's size advantage is real and its compatibility cost is underestimated** (D2.14).
- **Slim is the sensible middle** for most applications — small enough, and `apt` is there when you need it.
- **Scratch works only for fully static binaries**, and you'll still need `ca-certificates` for outbound TLS (S2.4) and `tzdata` if you handle timezones — **both of which are non-obvious and produce baffling failures.**

**The recommendation to give**: **build with a full base in a build stage, ship on distroless or slim** (D3.1). That's the multi-stage answer and it gets you the toolchain where you need it and the minimal surface where it matters.

**D2.14 — The musl vs glibc problem with alpine**

**Alpine uses musl libc; almost everything else uses glibc.** They're both C standard libraries and they are not identical.

**The consequences:**

- **Precompiled binaries built against glibc do not run on Alpine.** The failure is `not found` when running an executable that obviously exists — **because the dynamic loader path differs**, which is a genuinely confusing error message.
- **Python wheels.** PyPI's `manylinux` wheels are glibc-built. **On Alpine, pip cannot use them and falls back to compiling from source**, which requires a full build toolchain, takes many minutes, and often fails on packages like `numpy`, `pandas`, `cryptography`, or `psycopg2`. **This is the single most common Alpine problem** and it turns a 30-second install into a 10-minute build — frequently making the Alpine image *larger* than the slim one once the toolchain is added.
- **Performance differences.** musl's malloc is markedly slower for some allocation-heavy workloads, and its default thread stack size is smaller, which has caused stack overflows in JVM and Go applications.
- **DNS resolution differences** — musl historically didn't support `search` domains the same way and queries A and AAAA in parallel, which has caused real resolution failures in Kubernetes (K4.6).
- **Node native modules** and any language with compiled extensions face the same recompilation issue.

**The guidance**: **for compiled-static languages (Go with `CGO_ENABLED=0`, Rust) Alpine is fine** — there's no libc dependency to mismatch. **For Python, Node with native modules, and the JVM, use `-slim` instead** — the size difference after adding a toolchain is usually negligible, and you avoid the whole class of problem.

**D2.15 — Pinning base images by digest**

```dockerfile
FROM node:20-slim@sha256:5f7e9a2c4b8d...
```

**A tag is a mutable pointer** (D8.2). `node:20-slim` is rebuilt regularly — with security patches, and occasionally with breaking changes. **Your build's base changes without any change from you**, which means:

- **Builds are not reproducible** — the same commit produces different images on different days (D11.3).
- **A breaking change arrives unannounced.**
- **A compromised base image is pulled automatically** (S7.1).

**A digest is content-addressed and immutable.** `@sha256:...` always refers to exactly those bytes, verified on pull.

**What it buys**: reproducibility, supply chain integrity, and the ability to say precisely what went into a build.

**The tension, and it must be acknowledged**: **a pinned base does not receive security patches.** A digest pinned in January is missing every base image update since. **The resolution is automated update PRs** — Renovate and Dependabot both understand digest pinning and will raise a PR updating the digest with the new tag in a comment. **You get the patches as reviewed changes, on your schedule** (S7.2, S8.6).

**Pinning without an update process is worse than not pinning**, because you get stale bases and believe you're being rigorous. The pairing of digest pinning plus automated updates plus a scheduled rebuild cadence (S8.6) is the complete answer.

---

## D3. Build optimisation

**D3.1 — Writing a multi-stage build**

```dockerfile
# syntax=docker/dockerfile:1

FROM golang:1.23 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/api ./cmd/api

FROM gcr.io/distroless/static-debian12:nonroot AS runtime
COPY --from=build /out/api /api
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/api"]
```

**The mechanism**: each `FROM` starts a new stage with its own filesystem. **`COPY --from=<stage>` pulls specific artefacts across.** Only the final stage becomes the image; everything else is discarded.

The patterns worth knowing:

- **Named stages** (`AS build`) for readability and for `--from`.
- **`--target`** to build a specific stage — `docker build --target build` for a debug image with the toolchain, or a `test` stage run in CI.
- **A shared `base` stage** that several stages derive from, avoiding repetition.
- **Copying from an external image**: `COPY --from=alpine:3.20 /etc/ssl/certs /etc/ssl/certs` — the standard way to get CA certificates into a `scratch` image (D2.13).
- **Stages build in parallel** with BuildKit where they don't depend on each other, which is a real speed benefit.

**D3.2 — Why multi-stage matters for size and attack surface**

**Size**: the build stage contains the compiler, the package manager, source code, intermediate objects, test fixtures, and the full dependency tree. **A Go build image is ~800MB; the resulting binary is ~15MB.** Multi-stage ships the second number. For Java, Node, and Python the ratio is less dramatic and still substantial.

**Attack surface — the more important half:**

- **Build tools are attacker tools.** A compiler, `curl`, `git`, `make`, and a package manager in a production image are exactly what someone with code execution wants (S7.6). **Multi-stage removes them because they were never in the final stage.**
- **Source code doesn't ship.** Your application source, config templates, and test files aren't in the running image — which matters for both IP and for what an attacker learns.
- **Build-time credentials never reach the final image.** A registry token used in the build stage is not in the runtime stage's layers **provided it was never copied across** — though the safer answer remains secret mounts (D2.10), because an intermediate stage can still be pushed or cached.
- **Fewer packages means fewer CVEs** (S7.5), and the reduction is often an order of magnitude — which also makes the remaining findings triageable rather than noise (S8.7).

**The quantification worth having**: "our API image went from 1.1GB to 45MB and from 180 CVEs to 3" is the shape of a credible claim (D3.8).

**D3.3 — Diagnosing a missing layer cache**

```bash
docker build --progress=plain .        # shows CACHED vs running for each step
```

**The rule: a cache hit requires the instruction and all preceding layers to be identical.** Once one misses, everything after it rebuilds.

**The causes, in order of frequency:**

1. **A `COPY` earlier than it needs to be** (D2.6) — `COPY . .` before dependency installation means any code change invalidates the install.
2. **A file in the context changing that you didn't expect** — a log file, an editor swap file, a `.git` update, or a build artefact. **`.dockerignore` is the fix** (D2.5).
3. **A changing `ARG`** — a build arg like a timestamp or a git SHA passed early invalidates everything after it. **Pass volatile args as late as possible.**
4. **A fresh builder** — in CI, every run may start with an empty cache (D3.5).
5. **`--no-cache` or `--pull`** in the build command.
6. **Base image changed** — a floating tag was updated (D2.15).
7. **File metadata**: `COPY` keys on **content checksum**, so `touch` doesn't invalidate — but **permissions and ownership changes do**, which catches people whose CI checks out files with different modes.
8. **Multi-platform builds** have per-platform caches, so building for two architectures doesn't share.

**The diagnostic**: `--progress=plain` and find the first step that isn't `CACHED` — **that's the invalidation point**, and everything after it is a consequence rather than a separate problem.

**D3.4 — Cache mounts for package managers**

```dockerfile
RUN --mount=type=cache,target=/root/.npm \
    npm ci

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends curl

RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go build ./...
```

**The distinction from layer caching**: a layer cache is all-or-nothing — change one dependency and the whole `npm ci` re-runs, re-downloading everything. **A cache mount persists the package manager's own download cache across builds**, so a re-run only fetches what actually changed.

**The properties**: the mount exists **only during that `RUN`** and is **not part of any layer** — so it doesn't affect image size, and it's not in `docker history`. It persists in the builder's cache between builds.

The details: **`sharing=locked`** serialises concurrent access, which apt needs; `sharing=shared` (the default) allows concurrent, and `private` gives each build its own. **`id=`** to share a cache between different Dockerfiles. And note that with apt you must **not** `rm -rf /var/lib/apt/lists/*` when using a cache mount there — the mount handles it.

**The payoff**: adding one dependency to a large `requirements.txt` goes from a full re-download to fetching one package. On a big Java or Node project this is minutes per build.

**D3.5 — Sharing a build cache in CI**

**The problem**: CI runners are ephemeral (S7.9), so **every build starts with an empty local cache** and every layer rebuilds — losing everything D2.6 and D3.4 bought you.

**The mechanisms:**

```bash
# registry-backed cache — portable, works anywhere
docker buildx build \
  --cache-from type=registry,ref=ghcr.io/acme/api:buildcache \
  --cache-to   type=registry,ref=ghcr.io/acme/api:buildcache,mode=max \
  --push -t ghcr.io/acme/api:1.4.2 .
```

- **`type=registry`** — the cache is stored in a registry, so any runner can pull it. **The most portable option**, and `mode=max` exports intermediate layers too (larger cache, better hit rate) versus `mode=min` which only exports the final layers.
- **`type=gha`** — GitHub Actions cache backend, integrated with the platform's cache and free within quota.
- **`type=local`** with a CI cache directory — simple, and depends on the CI's cache restore.
- **`type=s3` / `type=azblob`** — object storage backed.
- **A persistent builder** — a long-lived buildx builder (a remote BuildKit instance, or a self-hosted runner with a durable daemon) keeps the cache natively. **The fastest option, and it reintroduces the shared-state concerns of persistent runners** (S7.10).

**The considerations**: cache pull time can exceed the build time it saves for small images — **measure rather than assume**. `mode=max` caches are large and need lifecycle management (D8.5). And **a shared cache is a shared trust boundary** — a poisoned cache entry from an untrusted build could affect others (S7.10), so don't share a cache between trust levels.

**D3.6 — Multi-arch builds with buildx**

```bash
# one-off, using QEMU emulation
docker run --privileged --rm tonistiigi/binfmt --install all
docker buildx create --name multi --use --bootstrap
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/acme/api:1.4.2 --push .

docker buildx imagetools inspect ghcr.io/acme/api:1.4.2
```

**`--push` is required for multi-arch** — a manifest list can't be loaded into the local daemon's single-architecture store, which is a common first stumble (`--load` fails).

**The two approaches and their tradeoff:**

- **QEMU emulation** — one builder, transparent, and **very slow** for compilation-heavy builds. Fine for a Go build (fast anyway) or an interpreted language; painful for a large C++ or Rust build, where it can be 5–10× slower.
- **Native builders per architecture** — a buildx builder node per platform (a native arm64 runner, or a remote BuildKit on an arm64 instance), with buildx assembling the manifest list. **Much faster and more setup.** GitHub now offers native arm64 runners, which makes this straightforward.

**The CI pattern for the native approach**: build each architecture in a parallel job on its native runner, push by digest, then a final job creates the manifest list with `docker buildx imagetools create`.

The related points: **`TARGETPLATFORM`, `TARGETARCH`, and `BUILDPLATFORM`** are automatic build args letting a Dockerfile cross-compile rather than emulate — `GOARCH=${TARGETARCH} go build` on a native builder is the fast pattern for Go. And **test each architecture**, because "it built" isn't "it runs" (D10.11).

**D3.7 — Inspecting image size layer by layer**

```bash
docker history --no-trunc --human myimage:1.4.2
docker image inspect myimage:1.4.2 --format '{{.Size}}'

# dive — the best tool for this
dive myimage:1.4.2
```

**`docker history`** shows each layer with its size and the instruction that created it — **so the culprit is usually obvious immediately**: one `RUN` that added 800MB.

**`dive`** is the better tool: it shows the layers *and* lets you browse the filesystem at each one, highlighting what each layer added, and reports an "efficiency" score identifying files that are added and later removed (wasted space, D1.5).

**The usual culprits:**

- **Build tooling in the final image** — the fix is multi-stage (D3.1).
- **Package manager caches not cleaned in the same layer** — `/var/lib/apt/lists`, `~/.npm`, `~/.cache/pip` (D2.7).
- **Files deleted in a later layer** — **still present in the image**, so the delete adds a whiteout and saves nothing (D1.5). `dive` flags this specifically.
- **The build context copied wholesale** — `.git`, `node_modules`, test fixtures (D2.5).
- **Dev dependencies installed** — `npm ci` without `--omit=dev`.
- **A large base image** (D2.13).
- **Multiple copies of the same data** across stages.

The reading tip: **`docker history` shows layer sizes, and shared base layers count toward the total but are shared on disk** — so a 1GB image on a host that already has 900MB of that base costs 100MB more. **Total size matters for pull time on a cold node** (D11.7), which is the case that actually affects you.

**D3.8 — Reducing an oversized image and quantifying it**

The method:

1. **Measure the baseline** — total size, and per-layer (D3.7).
2. **Identify the largest contributors** with `dive`.
3. **Apply the fixes in order of impact:**
   - **Multi-stage** to drop build tooling (D3.1) — usually the largest single win.
   - **A smaller base** — `slim` or distroless (D2.13).
   - **Clean package caches in the same `RUN`** (D2.7).
   - **`--no-install-recommends`.**
   - **Production dependencies only.**
   - **`.dockerignore`** to stop copying junk (D2.5).
   - **Combine or reorder** where a file is added and removed.
4. **Re-measure and verify it still works** — including at runtime, not just that it builds.
5. **Check the second-order effects** — pull time, node disk usage, and scaling responsiveness (D11.7).

A credible report:

> "The API image was 1.24GB. `dive` showed 780MB from the Maven build stage — the JDK, the dependency cache, and the source — and 220MB from apt lists never cleaned. Moving to a multi-stage build with a JRE-only runtime on `eclipse-temurin:21-jre-alpine`, and cleaning apt in the same layer, brought it to 187MB. Cold-start pull time on a new node went from 42s to 7s, which cut our p99 scale-out latency during traffic spikes from about 90s to 55s. CVE count from the base dropped from 94 to 11."

**The elements**: a baseline, the mechanism (what `dive` showed), the specific changes, the result, **and the second-order benefit that makes it matter** — because "the image is smaller" is not by itself a business outcome, and pull time affecting autoscaling is.

**D3.9 — How build context size affects build time**

**Before any instruction runs, the entire build context is packaged and sent to the builder.** With a local daemon that's a local copy; **with a remote builder or in CI it's a network transfer.**

**The effects:**

- **A fixed delay before the build starts**, proportional to context size. A 2GB context (typically `.git` plus `node_modules` plus build artefacts) is tens of seconds before anything happens, on every build.
- **In CI with a remote BuildKit or a Docker-in-Docker setup**, it's a network transfer over the wire.
- **Cache invalidation** — a larger context means more files that might change, and `COPY . .` hashes all of them (D3.3).

```bash
docker build --progress=plain . 2>&1 | head    # shows "transferring context: X MB"
du -sh .git node_modules dist                  # the usual suspects
```

**The fix is `.dockerignore`** (D2.5), and the improvement is frequently dramatic — a context going from 1.8GB to 4MB.

The additional techniques: **BuildKit only transfers files that are actually needed** in some cases (it can do lazy context transfer with certain frontends), which mitigates but doesn't eliminate it; **`docker build -f Dockerfile <specific-dir>`** to scope the context to a subdirectory in a monorepo; and **`--build-context`** for named additional contexts, which is the clean way to pull in a sibling directory without rooting the context at the repository top level.

---

## D4. Running containers

**D4.1 — The flags that matter**

```bash
docker run -d --name api \
  --restart unless-stopped \
  -p 127.0.0.1:8080:8080 \
  -e NODE_ENV=production \
  --env-file ./app.env \
  -v api-data:/var/lib/app \
  -v "$PWD/config.yaml:/etc/app/config.yaml:ro" \
  --memory 512m --cpus 1.5 \
  --read-only --tmpfs /tmp \
  --user 10001:10001 \
  --health-cmd 'curl -f http://localhost:8080/healthz || exit 1' \
  --init \
  acme/api:1.4.2
```

- **`-d`** — detached. Without it the container holds your terminal, and `Ctrl-C` sends SIGINT to it.
- **`-p host:container`** — publish a port (D5.2). **`-p 127.0.0.1:8080:8080` binds to loopback only** — worth knowing, because plain `-p 8080:8080` binds all interfaces and **bypasses the host firewall** (D5.7).
- **`-v`** — a named volume (`name:/path`) or a bind mount (`/host/path:/path`), with `:ro` for read-only (D6.1).
- **`-e` / `--env-file`** — environment configuration (D4.10).
- **`--rm`** — remove the container on exit. **Essential for one-off runs**, or stopped containers accumulate (D6.7).
- **`--name`** — a stable name for `docker logs`, `exec`, and DNS on a user-defined network (D5.3).
- **`--memory` / `--cpus`** — limits (D4.2).
- **`--init`** — a minimal init as PID 1 (D4.5).
- **`--user`** — run as a non-root UID (D9.1).

**D4.2 — Memory and CPU limits, and what happens when exceeded**

```bash
docker run --memory 512m --memory-swap 512m --cpus 1.5 myapp
```

**Memory (`--memory`) — incompressible:**

**Exceeding it means the cgroup OOM killer terminates a process in the container** — usually the main one, so the container dies with **exit code 137** (D10.5). Not throttled, not slowed: killed, immediately.

- **`--memory-swap` equal to `--memory` disables swap** for the container, which is usually what you want — swapping to disk is catastrophically slow (O10.3) and hides the problem.
- **Page cache counts toward the limit**, so heavy file I/O can trigger an OOM in a process whose heap is fine (O10.2) — a genuinely confusing failure.
- **`--memory-reservation`** is a soft limit applied under host pressure.

**CPU (`--cpus`) — compressible:**

**Exceeding it means throttling: the process is descheduled until the next period.** Nothing dies; it just goes slower — **and the slowdown is bursty and hurts latency disproportionately** (O9.4, K6.2). A container throttled for 70ms of every 100ms period shows moderate average CPU and terrible p99.

- **`--cpus 1.5`** sets the quota (`cpu.max`); **`--cpu-shares`** sets a relative weight under contention rather than a hard cap.
- **`--cpuset-cpus`** pins to specific cores.

**The asymmetry is the point of the item**: **memory over-limit is fatal and immediate; CPU over-limit is a slowdown.** That drives how you set them (D11.4) — memory with real headroom because being wrong kills the process, CPU more tolerantly because being wrong just costs performance.

**D4.3 — The signal on stop and the grace period**

```bash
docker stop --time 30 api     # SIGTERM, wait 30s, then SIGKILL
docker kill api               # SIGKILL immediately
docker kill --signal HUP api  # arbitrary signal
```

**`docker stop` sends `SIGTERM` to PID 1 in the container, waits for the grace period (default 10 seconds), then sends `SIGKILL`.**

The points that matter:

- **SIGKILL cannot be caught.** If your process hasn't exited within the grace period, it is killed abruptly — **in-flight requests are dropped, buffers are unflushed, and connections are severed** (D11.2).
- **The signal goes to PID 1 only.** If PID 1 is a shell (shell form, D2.3), **the shell does not forward it to your application** — so your application never sees SIGTERM and is always SIGKILLed. **This is the single most common cause of ungraceful shutdown.**
- **`STOPSIGNAL`** in the Dockerfile changes which signal is sent, for applications expecting `SIGQUIT` (nginx) or `SIGINT`.
- **The default 10 seconds is often too short** for a service draining connections — set it to exceed your longest expected request plus drain time.
- **In Kubernetes the equivalent is `terminationGracePeriodSeconds`** (K11.4), and the same mechanics apply.

**D4.4 — Handling signals correctly for graceful shutdown**

**The Dockerfile side:**

```dockerfile
ENTRYPOINT ["/app/server"]        # exec form — the process IS PID 1 (D2.3)
STOPSIGNAL SIGTERM
```

**If you need a wrapper script**, `exec` replaces the shell so the application becomes PID 1:

```bash
#!/bin/sh
set -e
# setup...
exec /app/server "$@"             # ← exec is essential
```

**The application side:**

```go
srv := &http.Server{Addr: ":8080", Handler: mux}
go func() { srv.ListenAndServe() }()

stop := make(chan os.Signal, 1)
signal.Notify(stop, syscall.SIGTERM, syscall.SIGINT)
<-stop

ctx, cancel := context.WithTimeout(context.Background(), 25*time.Second)
defer cancel()
srv.Shutdown(ctx)                 // stop accepting, finish in-flight
db.Close()
```

**What a correct shutdown does, in order:**

1. **Stop accepting new work** — and in an orchestrator, **fail readiness first** so traffic is withdrawn before you stop accepting (K9.10), otherwise you refuse requests that were still being routed to you.
2. **Finish in-flight requests**, within a bounded time.
3. **Close resources cleanly** — flush buffers, close database connections, commit or abandon in-flight messages (M2.2).
4. **Exit 0.**

**The detail that catches people**: in Kubernetes, **SIGTERM and endpoint removal happen concurrently**, not in sequence — so a short sleep in a `preStop` hook before shutting down lets the endpoint removal propagate first. Without it you get a small number of connection errors on every deploy.

**D4.5 — The PID 1 problem and zombie reaping**

**PID 1 has two special responsibilities in Linux**, and a normal application process does neither:

1. **It must reap zombies.** When a child process exits, it becomes a zombie until its parent calls `wait()`. **If the parent dies, orphaned children are re-parented to PID 1**, which must reap them. **An application that doesn't accumulates zombie processes**, eventually exhausting the PID limit (D1.4).
2. **It has different signal semantics.** **The kernel does not install default signal handlers for PID 1** — so a process that would normally be terminated by SIGTERM's default action **simply ignores it** if it hasn't registered a handler. **This is why `docker stop` on some containers always takes the full grace period and then SIGKILLs.**

**When it matters**: applications that spawn child processes (shelling out, running subprocesses, a supervisor pattern), and any application without explicit signal handling.

**The fixes:**

```bash
docker run --init myapp           # Docker injects tini as PID 1
```

```dockerfile
ENTRYPOINT ["/usr/bin/tini", "--", "/app/server"]
```

**`--init`** runs a minimal init (tini) as PID 1, which reaps zombies and forwards signals to your process. **In Kubernetes, `shareProcessNamespace` provides a similar reaper**, and most runtimes handle it, but the cleanest answer is either `--init` or an application that handles signals and reaps properly.

**The judgement**: for a single-process application with correct signal handling (D4.4), you don't need an init. **For anything spawning children, or any language runtime you're unsure about, add `--init` — it costs nothing.**

**D4.6 — Restart policies and their limits**

```bash
--restart no                      # default
--restart on-failure:5            # only non-zero exit, max 5 attempts
--restart always                  # always, including on daemon restart
--restart unless-stopped          # always, except if manually stopped
```

- **`no`** — never restart.
- **`on-failure[:max]`** — restart only on a non-zero exit code, optionally capped. **The right choice for batch-like workloads.**
- **`always`** — restart regardless of exit code, **and start on daemon restart** — so it survives a host reboot.
- **`unless-stopped`** — like `always`, but **a container you stopped manually stays stopped across a daemon restart**. Usually what you want for a service.

**The limits, which is the substance:**

- **Restarting doesn't fix the cause.** A container failing because its database is down restarts into the same failure — **an exponential backoff is applied** (starting at 100ms, doubling), which is why a crash-looping container's restarts slow down (K9.4's `CrashLoopBackOff`).
- **It's per-host and per-daemon.** **If the host dies, nothing restarts anywhere** — which is the fundamental limitation and the reason orchestrators exist. Docker restart policies give you process supervision, not availability.
- **No health-based restart** — a container that is running but wedged is not restarted by the policy. That needs a healthcheck plus something acting on it (D4.7), which standalone Docker doesn't provide.
- **No rescheduling, no capacity awareness, no rollout control.**

**The framing**: restart policies are appropriate for a single-host deployment or a development machine. **For production, the orchestrator owns restart, rescheduling, and health** (K2.1), and the Docker-level policy is irrelevant because the orchestrator manages the container's lifecycle.

**D4.7 — Healthchecks and what they should test**

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:8080/healthz || exit 1
```

**What it should actually test** — the design question:

- **That this process can serve requests.** An endpoint that returns 200 by exercising the request path — not a static file, which proves only that a web server is up.
- **Not its dependencies**, generally. **A healthcheck that verifies the database means every container becomes unhealthy simultaneously when the database blips** — and if something acts on that by restarting them, **a transient dependency problem becomes a total outage** (K9.11, O15.8). **This is the most important point in the item.**
- **Cheap.** It runs every interval on every container; an expensive check is a self-inflicted load source.

**The parameters**: **`--start-period`** is the one people miss — it gives a slow-starting application time before failures count, without lengthening the interval. **`--retries`** requires consecutive failures, damping transient blips.

**What Docker does with the result: nothing.** It sets the status to `healthy`/`unhealthy`, visible in `docker ps`. **Standalone Docker does not restart an unhealthy container.** Compose can use it for `depends_on` conditions (D7.2), Swarm acts on it, and **Kubernetes ignores the Dockerfile `HEALTHCHECK` entirely** — it uses its own liveness and readiness probes (K9.10).

**The distinction Kubernetes makes explicit and Docker doesn't**: **liveness** ("is this wedged, restart it") should be shallow; **readiness** ("should it get traffic") can be deeper. Docker has one concept, which is why the "don't check dependencies" rule matters more here.

**D4.8 — Logging drivers, and why apps should log to stdout**

```bash
docker run --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 myapp
docker run --log-driver awslogs --log-opt awslogs-group=/app/api myapp
```

**Drivers**: `json-file` (default), `local`, `journald`, `syslog`, `awslogs`, `gcplogs`, `fluentd`, `splunk`, `none`.

**Why applications should log to stdout/stderr:**

- **The application doesn't need to know about the logging infrastructure.** No file paths, no rotation config, no shipping library, no backend credentials. **The runtime captures it and the platform routes it** — that's the separation of concerns (O4.6).
- **`docker logs` and `kubectl logs` work**, which is the first thing anyone reaches for (D10.1).
- **Uniform across languages and frameworks**, so one collector configuration serves everything.
- **Writing to a file inside the container means the logs vanish with it**, or need a volume and a sidecar.

**The critical operational detail**: **`json-file` has no rotation by default.** A chatty container fills the host disk (D6.7) — **this is a real and common outage cause.** Always set `max-size` and `max-file`, ideally in the daemon's `daemon.json` so it applies to everything rather than per-container.

The other points: **`local` driver is more efficient** than `json-file` (compressed, better format) and isn't readable by `docker logs` on older versions; **blocking vs non-blocking mode** (`--log-opt mode=non-blocking`) matters because **a slow logging backend can block the application's writes**, which is a surprising source of latency (O4.6); and **log structured JSON to stdout** so fields are queryable downstream (O4.1).

**D4.9 — One process per container, and when it bends**

**The convention and its reasons:**

- **Lifecycle clarity** — the container's lifetime is the process's lifetime. If it exits, the container exits, and the orchestrator acts.
- **Independent scaling** — components that scale differently should be separate.
- **Signal handling and PID 1** are straightforward with one process (D4.5).
- **Logs go to stdout unambiguously** (D4.8) — two processes interleaving on stdout is a mess.
- **Resource limits apply to the whole container** (D4.2), so two processes share one budget and one OOM kill takes both.
- **Health means something** — one process, one health state (D4.7).

**When it bends legitimately:**

- **A process that genuinely spawns children** — nginx with workers, Gunicorn with workers, a JVM with threads. **This is one logical process with a supervisor**, not a violation.
- **A sidecar-style helper that must share the filesystem or a namespace** — though **in Kubernetes that's a second container in a pod** (K2.4), which is the right answer and preserves the convention.
- **Legacy applications** that genuinely require a co-located agent and can't be changed.
- **Development images** where convenience outweighs discipline.

**The anti-pattern**: `supervisord` running nginx, an application, and a cron daemon in one container. **You've built a small, badly-managed VM** — a crash of one is invisible, resource limits are shared, logs are interleaved, and updating one means rebuilding all.

**The framing**: the convention is really **one *concern* per container**. If you find yourself needing a process supervisor inside a container, that's usually a signal to split it — and in Kubernetes, into separate containers in a pod (K2.4) or separate deployments.

**D4.10 — Configuration without rebuilding**

**The principle** (twelve-factor, D11.5): **configuration varies by environment; the image should not.** The same image artefact runs in dev, staging, and production, with configuration injected at runtime — which is what makes image promotion possible (D8.8).

The mechanisms:

- **Environment variables** — `-e`, `--env-file`, or the orchestrator's equivalent. The most common, with the leak caveats in S6.1.
- **Mounted config files** — a bind mount or, in Kubernetes, a ConfigMap volume (K3.1). **Better for structured or large config**, and it can update in place (K3.2).
- **A config service or parameter store** fetched at startup (A10.20) — no local file, and it adds a startup dependency.
- **Command arguments** — appended to `ENTRYPOINT` (D2.3).

**What must not be in the image**: environment-specific endpoints, credentials (D9.8, S6.2), feature flags that vary by environment, and anything that would require a rebuild to change.

**What legitimately can be baked in**: sensible defaults, the application's own structure, and configuration genuinely invariant across environments.

**The connected point**: **if you must rebuild to deploy to a different environment, you cannot promote an artefact** (D8.8) — so what you test in staging is not what runs in production, which defeats a large part of the value of containers. **That's the argument to make**, because it connects a configuration practice to a deployment guarantee.

---

## D5. Networking

**D5.1 — Network drivers**

- **`bridge`** — the default. A virtual bridge on the host (`docker0` for the default network); each container gets a veth pair and an IP in a private subnet. **Isolated from the host network; reachable via published ports** (D5.2).
- **`host`** — **no network namespace** (D1.3). The container shares the host's network stack directly: its ports *are* host ports, no NAT, no publishing. **Fastest** (no NAT overhead) and **least isolated** — the container can bind any host port and see all host interfaces.
- **`none`** — a network namespace with only loopback. Fully isolated. For batch jobs needing no network.
- **`overlay`** — a multi-host network using VXLAN encapsulation, for Swarm or a multi-host setup. Containers on different hosts communicate as if on one L2 network.
- **`macvlan` / `ipvlan`** — the container gets an IP directly on the physical network, appearing as a distinct device to the LAN. For legacy applications expecting to be on the physical network.

**Choosing**: **bridge for essentially everything**; **host** for performance-critical networking or when a container needs to bind many ports dynamically, **accepting the isolation loss**; **none** for isolation; **overlay** in Swarm.

**In Kubernetes this is all replaced by CNI** (K4.2) — the pod's network is set up by a plugin, and `hostNetwork: true` is the equivalent of `--network host`, with the same tradeoff.

**D5.2 — How port publishing works**

```bash
docker run -p 8080:80 nginx           # host:container, all interfaces
docker run -p 127.0.0.1:8080:80 nginx # loopback only
docker run -P nginx                   # publish all EXPOSEd ports to random high ports
```

**What it does on the host:**

1. **An iptables DNAT rule** is added in the `DOCKER` chain of the `nat` table, rewriting the destination of packets arriving on host port 8080 to the container's IP and port 80.
2. **`docker-proxy`** — a userspace process is also started per published port, handling cases iptables can't (notably loopback and where the kernel's hairpin NAT doesn't apply). It's a fallback path, not the main one.
3. **A forwarding rule** in the `FORWARD` chain permits the traffic.

```bash
sudo iptables -t nat -L DOCKER -n
```

**The points that matter:**

- **`EXPOSE` in the Dockerfile publishes nothing** (D2.2) — it's metadata and a hint for `-P`. **A very common misunderstanding.**
- **The bind address matters.** `-p 8080:80` binds `0.0.0.0` — **reachable from anywhere the host is reachable.** `-p 127.0.0.1:8080:80` restricts to loopback, and it's what you want for anything not deliberately public.
- **It bypasses the host firewall** (D5.7) — the security consequence and the item that follows.
- **In Kubernetes, publishing is replaced by Services** (K4.3), and `hostPort` is the direct analogue, rarely used.

**D5.3 — Container-to-container communication and embedded DNS**

```bash
docker network create appnet
docker run -d --name db  --network appnet postgres:16
docker run -d --name api --network appnet acme/api:1.4.2
# api reaches the database at  postgres://db:5432/
```

**On a user-defined network, Docker runs an embedded DNS server at `127.0.0.11`** inside each container. It resolves **container names and network aliases** to their IPs on that network.

**So containers address each other by name**, which is what makes it usable — IPs are assigned dynamically and change on restart, so hardcoding them is impossible.

The details:

- **`--network-alias`** adds additional names, and **several containers can share an alias**, in which case DNS returns all their IPs — a crude round-robin.
- **Containers can be on several networks**, which is how you segment (an application on both a frontend and a backend network, with the database only on backend).
- **Only containers on the same network can reach each other.** Different networks are isolated by default — **which is the segmentation primitive** (D5.4).
- **The container's own name and hostname** resolve too.

**In Compose this is automatic** — services are reachable by service name on the project's default network (D7.1), which is why a Compose file needs no IP configuration at all.

**D5.4 — Default bridge vs user-defined**

| | Default `bridge` | User-defined bridge |
|---|---|---|
| **DNS resolution by name** | **No** | **Yes** (D5.3) |
| Isolation | All containers on it can reach each other | Only containers on the same network |
| Connect/disconnect while running | No | Yes |
| Configurable subnet, gateway, options | No | Yes |
| `--link` | Legacy, deprecated | Not needed |

**The headline difference is DNS.** On the default bridge, containers can reach each other by IP but **there is no name resolution** — which is why the deprecated `--link` flag existed, injecting `/etc/hosts` entries. **On a user-defined network, names just work.**

**The isolation difference matters too**: every container on the default bridge can reach every other one. **User-defined networks are isolated from each other**, so putting the database on a backend network that the public-facing container isn't on is real segmentation (S9.5).

**The recommendation: always create a user-defined network.** The default bridge exists for backward compatibility, and there's no reason to use it deliberately. **Compose creates one per project automatically**, which is why this is invisible to most people until they run containers by hand and find name resolution doesn't work — a common first confusion.

**D5.5 — Reaching a service on the host from inside a container**

The options, and the right one depends on the platform:

- **`host.docker.internal`** — resolves to the host's IP. **Available by default on Docker Desktop (macOS/Windows); on Linux it requires `--add-host=host.docker.internal:host-gateway`.** That platform difference is the thing to know, because a Compose file that works on a colleague's Mac fails on a Linux CI runner.
- **The bridge gateway IP** — typically `172.17.0.1` on the default bridge, or the gateway of the user-defined network. **Reliable on Linux, and the address varies**, so `host-gateway` is better.
- **`--network host`** — the container shares the host's stack, so `localhost` is the host (D5.1). Effective and it discards isolation.
- **The host's LAN IP** — works, and it's environment-specific and awkward.

**The prerequisite people miss**: **the host service must be listening on an interface the container can reach.** A service bound to `127.0.0.1` on the host is **not** reachable from a container, because the container's loopback is its own (D1.3). **It must bind `0.0.0.0` or the bridge interface** — and this is the actual cause of most "I can't reach the host service" reports.

The better answer for anything beyond development: **run the dependency in a container too**, on the same user-defined network (D5.3), so it's addressable by name and the topology matches production.

**D5.6 — "The container is running but I can't reach it"**

The checklist, in order — each step eliminates a layer:

1. **Is the process actually listening, and on which address?**
   ```bash
   docker exec api ss -tlnp    # or netstat -tlnp
   ```
   **Binding to `127.0.0.1` inside the container means it's unreachable from outside** — the container's loopback is its own (D1.3). **This is the single most common cause.** It must bind `0.0.0.0`.
2. **Is the port published, and to the right interface?** `docker ps` shows the mapping. **`EXPOSE` alone publishes nothing** (D2.2).
3. **Is the port mapping correct?** `-p 8080:80` means host 8080 → container 80. Reversing them is a frequent slip.
4. **Test from inside the container first** — `docker exec api curl -v localhost:8080`. **If that fails, it's the application, not the network**, and you've eliminated everything else.
5. **Test from another container on the same network** (D5.3) — this tests container-to-container without the host.
6. **Test from the host** — `curl localhost:8080`.
7. **Check the host firewall** (D5.7) and any cloud security group (A3.2).
8. **Check DNS** if connecting by name — is it resolving, and to what?
9. **Check the container's network** — `docker inspect` (D5.8): is it on the network you think?

**The bisection principle**: **work outward from the process.** Inside the container → another container → the host → outside the host. **Each hop that works eliminates everything below it**, which is the same discipline as K4.12 and O11.9.

**D5.7 — What happens to the host firewall when Docker publishes a port**

**Docker inserts its own iptables rules, and they are evaluated before the rules in `INPUT` where most firewall configuration lives.**

The mechanism: published ports are DNAT'd in the **`nat` table's `PREROUTING`** chain, and the resulting traffic is then evaluated in the **`FORWARD`** chain — **not `INPUT`**. **`ufw` and most simple firewall configurations only manage `INPUT`.**

**The consequence, which is the security point: `ufw deny 8080` does not block a Docker-published port 8080.** The container is reachable from the internet despite the firewall appearing to deny it. **This surprises people badly and has exposed a great many databases** — a `docker run -p 5432:5432 postgres` on a host with a "deny all" firewall is publicly reachable.

**The mitigations:**

- **Bind to loopback**: `-p 127.0.0.1:5432:5432` — **the simplest and most reliable fix**, and it should be the default for anything not deliberately public.
- **`--iptables=false`** in `daemon.json` and manage the rules yourself — full control, and you now own container networking rules entirely, which is a lot of work.
- **Rules in the `DOCKER-USER` chain**, which Docker deliberately leaves for administrators and evaluates before its own rules. **This is the supported extension point.**
- **A cloud security group** (A3.2) — an external control that Docker's iptables manipulation cannot bypass. **The most reliable answer in a cloud environment.**

**The general lesson**: **verify what's actually reachable rather than trusting the firewall's configuration** — `nmap` from another host, or check from outside. This is the same "prove it, don't assume it" discipline as verifying TLS is actually on (DB13.5).

**D5.8 — Inspecting a container's network configuration**

```bash
docker inspect api --format '{{json .NetworkSettings}}' | jq
docker inspect api --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}: {{$v.IPAddress}}{{"\n"}}{{end}}'

docker network ls
docker network inspect appnet          # subnet, gateway, connected containers

# from inside the container
docker exec api ip addr
docker exec api ip route
docker exec api ss -tlnp
docker exec api cat /etc/resolv.conf
docker exec api getent hosts db

# for a distroless container with no tools (D10.3)
docker run --rm -it --network container:api nicolaka/netshoot
```

**That last command is the technique worth knowing**: `--network container:<name>` joins the target container's network namespace, so **netshoot's full toolset (`dig`, `tcpdump`, `curl`, `ss`, `mtr`) operates on the target's network** without needing anything installed in it. It's the Docker equivalent of `kubectl debug` for networking (K9.12).

What to look for: **the networks the container is actually on** (frequently not the one you assumed), **its IP and gateway**, **`/etc/resolv.conf` pointing at `127.0.0.11`** for the embedded DNS (D5.3), and **which ports are actually bound and on what address** (D5.6).

---

## D6. Storage & data

**D6.1 — Named volumes, bind mounts, tmpfs**

```bash
-v pgdata:/var/lib/postgresql/data           # named volume
-v /opt/config:/etc/app:ro                   # bind mount, read-only
--tmpfs /tmp:rw,size=64m,noexec              # tmpfs
--mount type=volume,source=pgdata,target=/var/lib/postgresql/data   # explicit syntax
```

- **Named volume** — managed by Docker, stored under `/var/lib/docker/volumes/`. **Docker owns the lifecycle**; you reference it by name. Can use volume drivers for network or cloud storage. **Permissions are initialised from the image's directory** on first use.
- **Bind mount** — a host path mounted into the container. **You control the location**; the container sees whatever is there. **Permissions come from the host**, which is the source of D6.4.
- **tmpfs** — in-memory, never written to disk, **destroyed with the container.** **Counts against the container's memory limit** (D4.2).

**Choosing:**

| Use | Choice | Why |
|---|---|---|
| Database data, application state | **Named volume** | Managed lifecycle, better performance on Desktop, backup-able as a unit |
| Source code in development | **Bind mount** | Live editing from the host (D7.6) |
| Config file from the host | **Bind mount, `:ro`** | Explicit path, read-only |
| Secrets at runtime | **tmpfs** or a secret mount | Never on disk (S6.1) |
| Scratch space with a read-only rootfs | **tmpfs** | Required when `--read-only` (D9.5) |
| Sharing between containers on one host | Named volume | Both mount the same volume |

**The default to state**: **named volumes for data, bind mounts for development and host config.** A bind mount for production data ties the container to a specific host path and makes the setup non-portable.

**D6.2 — Why data in the container layer is ephemeral**

**Writes that don't go to a volume land in the container's writable layer** (D1.5), which **exists only as long as the container does.** `docker rm` deletes it; a container replaced by a new one from the same image starts with an empty writable layer.

**In an orchestrator this is much more consequential**: containers are replaced routinely — on deploy, on node failure, on rescheduling, on scale-in (K2.12). **Anything in the container layer is lost every time**, which for a database is total data loss.

**The other reasons to avoid writing to it, beyond persistence:**

- **Copy-on-write performance** (D1.5) — modifying a large file in a read-only layer copies it entirely first. Write-heavy workloads on the container layer are slow.
- **It counts toward host disk** and isn't obviously attributable (D6.7).
- **It defeats a read-only root filesystem** (D9.5), which is a hardening control worth having.

**The rule to state**: **containers should be stateless; state goes in a volume, a database, or object storage.** And the corollary that matters architecturally — **if a workload genuinely needs local persistent state, that's a signal to reconsider** (K13.8): use a managed database rather than running one in a container with a volume, unless you've decided deliberately.

**D6.3 — Creating, inspecting, backing up, and restoring a volume**

```bash
docker volume create pgdata
docker volume ls
docker volume inspect pgdata            # shows Mountpoint on the host

# back up: mount the volume into a throwaway container and tar it out
docker run --rm \
  -v pgdata:/data:ro \
  -v "$PWD":/backup \
  alpine tar czf /backup/pgdata-$(date +%F).tar.gz -C /data .

# restore into a fresh volume
docker volume create pgdata-restored
docker run --rm \
  -v pgdata-restored:/data \
  -v "$PWD":/backup \
  alpine sh -c 'tar xzf /backup/pgdata-2026-08-22.tar.gz -C /data'
```

**The pattern to know: mount the volume into a temporary container to operate on it**, because Docker has no `docker volume export`. The `alpine tar` idiom is the standard answer.

**The caveats that matter:**

- **A tar of a running database's data directory is crash-consistent at best** (DB6.10) — and because the files change during the copy, **it may not even be that.** **Stop the container, or use the database's own backup mechanism** (`pg_dump`, DB6.1). **This is the important point** — a naive volume backup of a live database is not a backup you can rely on.
- **`docker volume prune` removes unused volumes** — including ones holding data you needed (D6.6).
- **Named volumes are host-local.** They don't move between hosts without an explicit copy or a volume driver, which is why this approach doesn't scale to a cluster — that's what CSI and persistent volumes are for (K5.1).
- **Test the restore** (DB6.5) — the same argument applies at any scale.

**D6.4 — Diagnosing permission problems on a bind mount**

**The symptom**: `Permission denied` writing to a mounted directory, or files created in the container owned by an unexpected user on the host.

**The mechanism**: **the kernel enforces permissions by numeric UID and GID, and those numbers mean different things inside and outside the container.** A container process running as UID 1000 writing to a host directory owned by UID 501 gets denied — **there is no name resolution involved**, the names in `/etc/passwd` differ between the two and are irrelevant.

```bash
docker exec api id                       # UID/GID inside
ls -ln /host/path                        # numeric owner on the host
```

**The fixes:**

- **Run the container as the host user**: `--user "$(id -u):$(id -g)"`. **The common development answer**, and the container then has no entry in `/etc/passwd`, which some applications dislike.
- **`chown` the host directory** to match the container's UID.
- **Build the image with a UID matching the host's** — brittle, since it varies per developer.
- **`COPY --chown=`** in the Dockerfile for files baked in (D2.4).
- **Use a named volume instead** (D6.1) — **Docker initialises its permissions from the image's directory**, so this class of problem largely disappears. **The best answer where a bind mount isn't specifically needed.**

**The platform difference worth knowing**: **on Docker Desktop for macOS and Windows, the file sharing layer translates ownership**, so permission problems are largely invisible there and appear only on Linux. **That's a classic "works on my machine"** (D10.11) between a Mac developer and a Linux CI runner.

**In Kubernetes** the equivalent is `fsGroup` and `runAsUser` in the securityContext (K8.7), and the same numeric-UID reasoning applies.

**D6.5 — Bind mount performance on macOS/Windows**

**Containers on macOS and Windows run inside a Linux VM** (D1.6). **A bind mount crosses the VM boundary**, so every filesystem operation traverses a translation layer — historically osxfs, then gRPC-FUSE, now **VirtioFS**.

**The consequence: filesystem operations are dramatically slower than native**, and the penalty is worst for **many small operations** rather than bulk throughput. Which is exactly what development workloads do:

- **`node_modules`** — tens of thousands of small files; `npm install` or a webpack build over a bind mount can be an order of magnitude slower.
- **Ruby, PHP, and Python** applications scanning many source files on each request.
- **Compilation and test runs** over mounted source.

**The mitigations:**

- **VirtioFS** (Docker Desktop's current default) is substantially faster than its predecessors — **check it's enabled**, because older installations may not be.
- **Mount consistency flags** — `:delegated` and `:cached` relaxed coherence guarantees; largely superseded by VirtioFS.
- **Keep `node_modules` in a named volume** rather than the bind mount — a very common and effective pattern: bind-mount the source, volume-mount `node_modules`, so the small-file traffic stays inside the VM.
- **Do the heavy work inside the container** without mounting — build in the image, use a dev container.
- **Mount only what changes**, not the whole repository.

**On Linux there is no penalty** — a bind mount is a normal mount, so this is entirely a Desktop concern. **Which means it's also a source of "the build is fast in CI and slow locally"** and is worth naming as such.

**D6.6 — What `docker system prune` removes and the risk**

```bash
docker system prune              # stopped containers, unused networks,
                                 # dangling images, build cache
docker system prune -a           # ...plus ALL images not used by a running container
docker system prune -a --volumes # ...plus ALL unused volumes  ← dangerous
```

**What each level removes:**

| Command | Removes |
|---|---|
| `prune` | Stopped containers, unused networks, **dangling** images (untagged), build cache |
| `prune -a` | **Every image not used by a running container** — including tagged ones you'd have to re-pull |
| `--volumes` | **Every volume not attached to a container** |

**The risks:**

- **`--volumes` is the dangerous one.** A **stopped** database container's volume counts as "unused" — **so pruning deletes the data.** Irrecoverably. **This is the classic disaster**, and it's why `--volumes` was made opt-in.
- **`-a` removes images you'll need**, meaning a re-pull — inconvenient on a good connection, an outage if the registry is unreachable or the tag has been deleted (D8.5).
- **Build cache removal** means the next build is slow (D3.3).
- **On a shared host or CI runner, you're pruning other people's things.**

**Safer alternatives:**

```bash
docker container prune --filter "until=24h"
docker image prune --filter "until=168h"     # dangling only, older than a week
docker builder prune --keep-storage 20GB
docker volume ls -qf dangling=true           # LOOK before removing
```

**The guidance: use targeted prunes with `--filter until=`, never `--volumes` on a host with data, and understand that on a production host `prune` is a change that should be deliberate rather than a reflex when disk fills** (D6.7).

**D6.7 — Diagnosing a host running out of disk**

```bash
docker system df                 # summary by type
docker system df -v              # per-image, per-container, per-volume detail

du -sh /var/lib/docker/*         # where it's actually going
du -sh /var/lib/docker/containers/*/*-json.log | sort -h | tail
```

**The usual culprits, in order:**

1. **Container logs.** `json-file` has **no rotation by default** (D4.8) — a chatty container produces multi-gigabyte log files. **This is the most common cause** and the fix is `max-size` and `max-file` in `daemon.json`, applied globally.
2. **Images** — accumulated tags, especially on a CI host building constantly. `docker system df` shows reclaimable space.
3. **Build cache** — BuildKit's cache grows without bound unless capped (`docker builder prune --keep-storage`).
4. **Stopped containers**, each holding its writable layer (D1.5). Use `--rm` for one-off runs (D4.1).
5. **Volumes**, including anonymous ones created by `VOLUME` in a Dockerfile (D2.2) — these accumulate invisibly, one per container run.
6. **The container writable layer** of a running container writing data that should be in a volume (D6.2).

**The remediation, in order of safety**: rotate and truncate logs; `docker image prune` with a filter; `docker builder prune --keep-storage`; `docker container prune`; and **only then** consider volumes, after inspecting them (D6.6).

**The prevention**: **log rotation in `daemon.json`** (the single highest-value setting), `--rm` on ephemeral runs, a scheduled targeted prune on CI hosts, **disk monitoring with a predicted-full alert** (O3.5, DB12.2), and — the structural answer — **treating hosts as disposable** so accumulated state doesn't matter (A4.6).

---

## D7. Compose & local development

**D7.1 — A compose file for a multi-service application**

```yaml
services:
  api:
    build:
      context: .
      target: dev
    ports: ["8080:8080"]
    environment:
      DATABASE_URL: postgres://app:${DB_PASSWORD}@db:5432/app
      REDIS_URL: redis://cache:6379
    env_file: [.env]
    depends_on:
      db:    { condition: service_healthy }
      cache: { condition: service_started }
    develop:
      watch:
        - { action: sync, path: ./src, target: /app/src }
        - { action: rebuild, path: package.json }

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_USER: app
      POSTGRES_DB: app
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

  cache:
    image: redis:7-alpine
    command: ["redis-server", "--save", ""]

volumes:
  pgdata:
```

The points this demonstrates:

- **Services reach each other by service name** — `db:5432` — via the project's automatic user-defined network and embedded DNS (D5.3). **No IP configuration anywhere**, which is the main ergonomic win.
- **`depends_on` with `condition: service_healthy`** rather than bare ordering (D7.2).
- **A named volume for database data** (D6.1), so `docker compose down` doesn't lose it (that needs `-v`).
- **Variable substitution** from `.env` (D7.3).
- **`build.target`** selecting a multi-stage stage (D3.1).
- **The `version:` key is obsolete** in Compose V2 and should be omitted — a small currency signal.

**D7.2 — `depends_on` with healthchecks**

**Plain `depends_on` only controls start order** — Compose starts `db` before `api`. **It does not wait for the database to be ready to accept connections.** Postgres takes several seconds to initialise, so the API starts, tries to connect, and fails.

**`condition: service_healthy`** waits for the dependency's healthcheck to pass (D4.7), which is the actual readiness signal.

```yaml
depends_on:
  db: { condition: service_healthy }
  migrations: { condition: service_completed_successfully }
```

The conditions: **`service_started`** (default — order only), **`service_healthy`** (waits for the healthcheck), **`service_completed_successfully`** (waits for a one-shot container to exit 0 — the pattern for running migrations before the application, DB7.4).

**Why ordering alone isn't enough, stated generally**: **"started" and "ready" are different**, and the gap can be seconds or minutes. This is the same distinction Kubernetes makes explicit with readiness probes (K9.10), and Compose's `service_healthy` is the equivalent.

**The more important point to make**: **even with healthchecks, the application should tolerate its dependencies being unavailable.** In production there is no startup ordering — a database can fail at any time, and a service that only works because it started in the right order is fragile (O15.1). **Retry with backoff on connection, and fail readiness rather than crashing** (K9.10). `depends_on` makes local development pleasant; it should not be load-bearing for correctness.

**D7.3 — Environment files and variable substitution**

```bash
# .env — read automatically by Compose, for substitution in the YAML
DB_PASSWORD=localdevpassword
API_PORT=8080
TAG=1.4.2
```

```yaml
services:
  api:
    image: acme/api:${TAG:-latest}          # default if unset
    ports: ["${API_PORT:?API_PORT required}:8080"]   # error if unset
    env_file:
      - .env.common
      - .env.local                          # later files win
    environment:
      LOG_LEVEL: ${LOG_LEVEL:-info}
```

**The distinction that confuses people:**

- **`.env` in the project directory is read by Compose itself**, for **substituting `${VAR}` in the YAML**. It does **not** automatically become the container's environment.
- **`env_file:`** specifies files whose contents are **passed into the container's environment.**
- **`environment:`** sets variables explicitly, and **takes precedence over `env_file`.**

The syntax worth knowing: **`${VAR:-default}`** (use default if unset or empty), **`${VAR:?message}`** (fail with a message if unset — good for required values), and **shell environment variables override `.env`**, which is how CI injects values.

**The security point**: **`.env` files hold secrets and must be in `.gitignore` and `.dockerignore`** (D2.5, S6.3). A committed `.env` is a leaked credential requiring rotation (S6.4). **For anything beyond local development, use a real secret store** (S6.2) — Compose `secrets:` (file-based) is a step up but still local files.

**D7.4 — Overriding configuration per environment**

```bash
docker compose up                                              # base + override (automatic)
docker compose -f compose.yaml -f compose.prod.yaml up          # explicit
COMPOSE_FILE=compose.yaml:compose.ci.yaml docker compose up
```

**`compose.override.yaml` is merged automatically** if present, which is the convention for local development settings — so `compose.yaml` holds the shared definition and the override holds developer-specific bind mounts and debug ports.

```yaml
# compose.yaml — shared
services:
  api:
    image: acme/api:${TAG}
    environment: { LOG_LEVEL: info }

# compose.override.yaml — local dev, applied automatically
services:
  api:
    build: { context: ., target: dev }
    volumes: ["./src:/app/src"]
    environment: { LOG_LEVEL: debug }
    ports: ["9229:9229"]
```

**The merge semantics**: scalars are replaced by the later file; **most lists are appended** (ports, volumes, environment as a list) rather than replaced — **which surprises people**, because you can't remove an entry from a list by overriding. Maps are merged key by key.

The related mechanisms: **`extends:`** to inherit a service definition from another file; **YAML anchors** (`&name` / `*name`) for repetition within one file; and **`include:`** (newer) for composing multiple Compose files as modules.

**The judgement**: this works well for **dev/test/CI variation**. **For production, Compose is usually the wrong tool** (D7.7) — the override pattern is for varying a development setup, not for managing production environments.

**D7.5 — Profiles**

```yaml
services:
  api:
    image: acme/api
  db:
    image: postgres:16
  # only started when explicitly requested
  jaeger:
    image: jaegertracing/all-in-one
    profiles: ["observability"]
  mailhog:
    image: mailhog/mailhog
    profiles: ["dev-tools"]
  loadtest:
    image: grafana/k6
    profiles: ["testing"]
```

```bash
docker compose up                                    # api and db only
docker compose --profile observability up            # plus jaeger
docker compose --profile dev-tools --profile testing up
COMPOSE_PROFILES=observability,dev-tools docker compose up
```

**Services without a `profiles` key always start**; services with one start only when that profile is activated.

**Why it's useful**: a Compose file for a real application accumulates optional services — a tracing backend, a mail catcher, a message broker UI, a load testing tool, a database admin interface. **Without profiles, everyone runs all of them**, consuming laptop memory and slowing startup for things most people don't need.

**The alternative it replaces**: multiple Compose files (D7.4) with the optional services split out — which works and is more files to remember. **Profiles keep one file and make the subsets explicit.**

The detail: **a service depended on by an active service is started even if its profile isn't active**, which is sensible and occasionally surprising.

**D7.6 — A live-reload development loop**

**The modern answer is `develop.watch`** (Compose 2.22+), which supersedes the bind-mount-plus-nodemon pattern:

```yaml
services:
  api:
    build: { context: ., target: dev }
    develop:
      watch:
        - action: sync            # copy changed files into the container
          path: ./src
          target: /app/src
          ignore: ["**/*.test.ts"]
        - action: rebuild         # dependency change → rebuild the image
          path: package.json
        - action: sync+restart    # config change → sync and restart the process
          path: ./config
          target: /app/config
```

```bash
docker compose watch
```

**The actions**: **`sync`** copies changed files in (paired with the application's own hot reload); **`rebuild`** rebuilds the image, for dependency changes; **`sync+restart`** syncs and restarts the container, for config the application reads at startup.

**Why it's better than a plain bind mount**: it **avoids the bind mount performance problem on macOS and Windows** (D6.5) by syncing rather than mounting, it **handles the dependency-change case explicitly** rather than requiring you to remember to rebuild, and it keeps `node_modules` inside the container where it belongs.

**The older pattern still worth knowing** (and still common): bind-mount the source, keep `node_modules` in a named volume so it isn't shadowed by the host directory, and run a file watcher (`nodemon`, `air`, `watchexec`, `--reload`) in the container. **The `node_modules` volume trick is the essential detail** — without it, the host's directory shadows the container's and you get platform-mismatched native modules (D2.5).

**D7.7 — Where Compose stops being appropriate**

**Compose is excellent for**: local development, a demo, CI test dependencies (spinning up a real database for integration tests), and a genuinely simple single-host deployment.

**Where it stops:**

- **Multi-host.** Compose is single-host. **No scheduling, no distribution, no failover** — if the host dies, everything dies. That's the fundamental ceiling.
- **No self-healing beyond restart policies** (D4.6), which are per-host and don't survive host loss.
- **No rolling deployments.** `docker compose up` recreates containers with downtime. **No canary, no gradual rollout, no automatic rollback** (K2.11).
- **No horizontal scaling worth the name.** `--scale` exists and there's no load balancing, no service discovery across hosts, and no capacity awareness.
- **No secret management** beyond files (D7.3, S6.2).
- **No resource-aware scheduling** — no bin packing, no node selection.
- **Limited health integration** — healthchecks exist but little acts on them (D4.7).

**The transition point**: **when you need more than one host, or zero-downtime deploys, or automatic recovery from host failure.** That's Kubernetes (or ECS, A5.2), and it's a substantial step (K13.1's cost argument).

**The honest position worth stating**: **Compose in production on a single host is a legitimate choice for a small internal service** where an occasional restart is acceptable — it's simple and comprehensible. **What it isn't is a scaled-down Kubernetes**, and trying to make it one (scripts around it for rolling updates and health-based restarts) is rebuilding an orchestrator badly.

---

## D8. Registries & distribution

**D8.1 — Push, pull, authenticate**

```bash
# Docker Hub
docker login
# GHCR
echo "$GITHUB_TOKEN" | docker login ghcr.io -u USERNAME --password-stdin
# ECR — a short-lived token from IAM (A5.1)
aws ecr get-login-password --region eu-west-1 \
  | docker login --username AWS --password-stdin 111122223333.dkr.ecr.eu-west-1.amazonaws.com

docker tag myapp:1.4.2 ghcr.io/acme/myapp:1.4.2
docker push ghcr.io/acme/myapp:1.4.2
docker pull ghcr.io/acme/myapp@sha256:abc123...
```

**The image reference format**: `[registry[:port]/][namespace/]name[:tag|@digest]`. **With no registry it defaults to Docker Hub**, which is why `nginx` means `docker.io/library/nginx` — worth knowing because it explains rate limits appearing where people didn't expect a Docker Hub dependency (D8.7).

**The authentication points that matter:**

- **`--password-stdin`**, never `-p` on the command line — it lands in shell history and in process listings (S6.7).
- **`docker login` writes credentials to `~/.docker/config.json`**, base64-encoded, not encrypted (S1.2). **On a shared or CI host that's a credential file** — use a credential helper (`docker-credential-ecr-login`, `osxkeychain`) which stores them properly.
- **ECR tokens are short-lived** (12 hours) and derived from IAM, which is the good pattern — **no static registry credential exists** (S6.6).
- **In CI, authenticate via OIDC** (S7.9) rather than storing a registry password.
- **In Kubernetes**, `imagePullSecrets`, or better, node-level IAM (A5.1) so no secret exists.

**D8.2 — Digests vs tags**

- **A tag is a mutable, human-readable pointer** to a manifest. `acme/api:1.4.2` can be moved to a different image at any time by anyone who can push.
- **A digest is the SHA-256 of the manifest content.** `acme/api@sha256:abc123...` **always refers to exactly those bytes** and is verified on pull.

**Why tags are mutable and why that matters:**

- **The same tag on two days can be two different images** — so a build isn't reproducible (D2.15, D11.3), and "what's running in production" is ambiguous.
- **An attacker or a mistake can repoint a tag**, and every subsequent pull gets different content with no signal. **This is the mechanism behind the CI action compromise in S7.11**, applied to images.
- **Caching interacts badly** — a node with a cached image for tag `X` may not re-pull, so different nodes run different code under the same tag (D10.11).

**The practices:**

- **Deploy by digest**, or by an immutable version tag. **Kubernetes manifests referencing a digest are the strongest form** and it's what admission-time signature verification effectively requires (S7.7).
- **Enable tag immutability in the registry** (ECR supports it, A5.1) — this makes the convention an enforced property, and it's a one-setting improvement.
- **Record the digest at deploy time** so you know exactly what ran.
- **A tag is still useful for humans**; the digest is what machines should use. Both, with the tag as a label (D2.12).

**D8.3 — Manifests and manifest lists**

**An image manifest** describes one image for one platform:

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "config":  { "digest": "sha256:...", "size": 7023 },
  "layers": [ { "digest": "sha256:...", "size": 32654 },
              { "digest": "sha256:...", "size": 16724 } ]
}
```

It references **the config blob** (entrypoint, env, architecture, layer ordering — D2.2) and **the layer blobs**. **Everything is content-addressed by digest**, so pulling verifies integrity by construction.

**A manifest list (OCI image index)** references several manifests, one per platform:

```bash
docker buildx imagetools inspect acme/api:1.4.2
# Name: acme/api:1.4.2
# MediaType: application/vnd.oci.image.index.v1+json
# Manifests:
#   linux/amd64  sha256:...
#   linux/arm64  sha256:...
```

**The client sends its platform, and the registry serves the matching manifest** — which is how multi-arch works transparently (D1.9).

**The wider point worth making**: **the index is a general mechanism**, not just for architectures. **SBOMs (S7.8), signatures (S7.7), and provenance attestations (S7.12) are stored as additional manifests referring to the image** — which is why a modern registry holds far more than images, and why the OCI distribution spec (D1.7) matters as a general artefact protocol.

**D8.4 — A tagging strategy supporting rollback and traceability**

```
ghcr.io/acme/api:1.4.2                    # semantic version — the release
ghcr.io/acme/api:1.4                      # minor, moves with patches
ghcr.io/acme/api:sha-a3f9c2b              # git commit — exact traceability
ghcr.io/acme/api:main                     # latest on the main branch
ghcr.io/acme/api:pr-482                   # per-PR, short retention
ghcr.io/acme/api@sha256:...               # digest — what production actually references
```

**What the strategy must support:**

- **Rollback** — an immutable tag or digest for every previously-deployed version, retained long enough to roll back to (D8.5's retention must not delete them).
- **Traceability** — **from a running container back to the exact commit.** The `sha-` tag plus OCI labels (D2.12) gives this both ways.
- **Promotion without rebuild** (D8.8) — the same digest moves through environments.
- **Human readability** — a version tag people can reason about.

**The rules:**

- **Every build gets an immutable, unique tag** (the commit SHA at minimum). **Never rely on a moving tag for deployment.**
- **Moving tags (`main`, `1.4`, `latest`) are conveniences for humans**, never deployment references (D2.11).
- **Tag immutability enabled** in the registry so it's enforced.
- **Record which digest is deployed where** — the deployment manifest in git is that record under GitOps (K10.7).

**The anti-pattern to name**: **rebuilding for each environment** (a `staging` tag and a `prod` tag built separately). **Different bits ran in staging than in production**, so the testing proved nothing (D8.8).

**D8.5 — Retention and lifecycle policies**

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire untagged images after 7 days",
      "selection": { "tagStatus": "untagged", "countType": "sinceImagePushed",
                     "countUnit": "days", "countNumber": 7 },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 2,
      "description": "Keep only 20 PR images",
      "selection": { "tagStatus": "tagged", "tagPrefixList": ["pr-"],
                     "countType": "imageCountMoreThan", "countNumber": 20 },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 3,
      "description": "Keep last 50 release images",
      "selection": { "tagStatus": "tagged", "tagPrefixList": ["v"],
                     "countType": "imageCountMoreThan", "countNumber": 50 },
      "action": { "type": "expire" }
    }
  ]
}
```

**Why it matters**: **without lifecycle rules, a registry grows without bound** — and on a busy CI pipeline, **untagged images (superseded by a re-pushed tag) are the bulk of it.** Registry storage becomes a meaningful line item and is a reliable finding in a cost review (A12.3, A5.1).

**The rules to get right:**

- **Expire untagged aggressively** — they're almost always garbage.
- **Expire PR and branch images quickly**, with a short retention.
- **Keep releases for long enough to roll back to** — and be careful, because **an over-aggressive rule that deletes the image production is running is a genuine outage** if a node needs to pull it. **Never expire an image currently deployed**, which means the rule must be generous relative to your release cadence.
- **Beware digest-referenced images** — a rule keying on tags can delete a manifest that a digest reference still points at.
- **Multi-arch**: deleting a per-platform manifest breaks the index.

**The related cost lever** (A5.1): image size (D3.8) multiplied by retention count is the storage bill, so a smaller image helps twice.

**D8.6 — Cross-account or cross-environment pull access**

**On ECR** (A5.1), it's a two-part requirement and that's where people get stuck:

1. **A repository policy** (resource-based) in the owning account allowing the other account's principals:

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::444455556666:root" },
  "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer",
             "ecr:BatchCheckLayerAvailability"]
}
```

2. **`ecr:GetAuthorizationToken` in the pulling account's IAM policy** — this is account-level, not repository-level, and is the part most often missing.

**Both are required** (A2.1's two-sided cross-account rule).

The other considerations:

- **Registry-level policies** and **`aws:PrincipalOrgID`** conditions (A2.5) to grant to a whole organisation rather than enumerating accounts.
- **Encryption** — if the repository uses a CMK, the pulling account needs `kms:Decrypt` on it too (A10.11). **A frequent cause of "I granted ECR access and it still fails."**
- **Replication** — ECR cross-region and cross-account replication copies images automatically, which is often better than cross-account pull for latency and for surviving a regional issue.
- **A central "artefacts" account** owning production images, with workload accounts having pull-only access, is the common mature pattern (A1.12) — it means a compromised workload account cannot push a malicious image.

**On other registries**: GHCR uses package visibility and org permissions; a self-hosted registry uses its own auth. **The principle is the same** — read-only where possible, and pushes restricted to CI (S7.9).

**D8.7 — Pull-through cache and the rate-limit motivation**

**The motivation**: **Docker Hub rate-limits anonymous pulls** (historically 100 per 6 hours per IP, and tightened since). **In CI, every runner pulling base images shares the NAT gateway's IP** (A3.1) — so an organisation's builds collectively exhaust the limit and **builds start failing with `toomanyrequests`**, intermittently and confusingly, with no change on your side.

**A pull-through cache** sits between your builders and the upstream registry: the first pull fetches and caches; subsequent pulls are served locally.

```bash
# ECR pull-through cache rule
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub \
  --upstream-registry-url registry-1.docker.io

# then reference it
FROM 111122223333.dkr.ecr.eu-west-1.amazonaws.com/docker-hub/library/node:20-slim
```

**The benefits beyond rate limits:**

- **Speed** — pulling from a cache in the same region and VPC is much faster than the public internet, and it avoids NAT data processing charges (A3.3).
- **Availability** — a Docker Hub outage doesn't stop your builds.
- **Control** — you can see and audit what upstream images are being used, and constrain them (S7.3's mirror argument).
- **Resilience against upstream deletion** — a base image tag removed upstream is still in your cache.

**The alternatives**: **authenticate to Docker Hub** (an authenticated pull has a higher limit); **vendor critical base images** into your own registry deliberately; or use registries without aggressive limits (GHCR, ECR Public, Quay).

**D8.8 — Promoting an image between environments without rebuilding**

**The principle: build once, promote the same artefact.**

```bash
# built and pushed once, in CI
DIGEST=$(docker buildx build --push -t ghcr.io/acme/api:sha-a3f9c2b . \
          --metadata-file meta.json && jq -r '."containerimage.digest"' meta.json)

# promote by adding a tag to the SAME digest — no rebuild
docker buildx imagetools create \
  --tag ghcr.io/acme/api:staging \
  ghcr.io/acme/api@${DIGEST}

docker buildx imagetools create \
  --tag ghcr.io/acme/api:prod-1.4.2 \
  ghcr.io/acme/api@${DIGEST}
```

**`imagetools create` retags without pulling or rebuilding** — it creates a new tag pointing at the same manifest, server-side. **Cross-registry promotion** copies the blobs (`crane copy`, `skopeo copy`), still without rebuilding.

**Why rebuilding per environment is wrong:**

- **Different bits.** A rebuild can produce a different image — a floating base tag updated (D2.15), a dependency resolved differently (S7.2), a different builder. **So what you tested in staging is not what runs in production**, which invalidates the testing.
- **It's slow** and wastes CI time.
- **Traceability is lost** — several images for one commit.
- **Signatures and attestations are per-digest** (S7.7) — a rebuild invalidates them, so verification at admission fails or must be redone.

**The corollary that makes it work**: **the image must be environment-agnostic** (D4.10) — all configuration injected at runtime. **If you have to rebuild to change an endpoint, you cannot promote**, which is the practical reason the twelve-factor config rule matters (D11.5).

---

## D9. Security

**D9.1 — Running as non-root**

```dockerfile
RUN useradd --system --uid 10001 --no-create-home appuser
USER 10001:10001
```
```bash
docker run --user 10001:10001 myapp
```

**Why the default is a problem**: **containers run as root unless told otherwise**, and **without user namespace remapping** (D9.6), **root inside the container is UID 0 on the host.** So:

- **A container escape** (D9.10) lands as root on the host, not as an unprivileged user.
- **A vulnerability in the application** gives root within the container — full control of its filesystem, ability to install tools, and ability to bind privileged ports.
- **Bind-mounted host files** are written as root, creating files the host user can't manage (D6.4).
- **Capabilities** are granted by default to root (D9.4), so the process has more privilege than it needs.

**The practices:**

- **`USER` in the Dockerfile with a numeric UID** — numeric matters because **Kubernetes' `runAsNonRoot` check can only verify a numeric UID**; a username requires resolving `/etc/passwd`, which distroless may not have (K8.7).
- **A high UID (10000+)** to avoid collision with host users.
- **Ensure the application can actually run unprivileged** — it can't bind ports below 1024 (listen on 8080 and map it, D5.2), and it needs write access only where you've provided it (D9.5).
- **`--user` at runtime** to override, and **`runAsUser`/`runAsNonRoot` in Kubernetes** to enforce (K8.7).
- **Distroless `:nonroot` variants** do this for you (D2.13).

**The enforcement point**: a Dockerfile `USER` can be overridden at runtime. **Enforce it at admission** — Pod Security Admission `restricted` or a policy engine (K8.6, K8.9) — or it's a convention rather than a control.

**D9.2 — The risk of mounting the Docker socket**

```bash
docker run -v /var/run/docker.sock:/var/run/docker.sock myimage    # ← full host compromise
```

**Mounting the Docker socket grants complete control of the Docker daemon, which runs as root on the host. That is equivalent to root on the host.**

**The escape is trivial** — anyone with socket access can:

```bash
docker run -v /:/host --privileged -it alpine chroot /host
```

**One command, full host filesystem, root.** No exploit required; it's the intended functionality of the API.

**Also available**: read every other container's contents and environment (including their secrets), start privileged containers, and access anything the daemon can.

**Why people do it anyway**: CI runners building images (Docker-in-Docker), monitoring agents enumerating containers, and tools like Watchtower or Traefik reading container metadata.

**The alternatives:**

- **Rootless builders** — **Kaniko, Buildah, or BuildKit in rootless mode** build images without a daemon or a socket. **The right answer for CI image building.**
- **A socket proxy** (`tecnativa/docker-socket-proxy`) exposing only specific read-only API endpoints — much better for monitoring agents that only need to list containers.
- **Podman** — daemonless and rootless by design.
- **In Kubernetes, use the API** rather than the container runtime socket, with RBAC scoping it (K8.2).

**The framing**: **"mount the Docker socket" and "grant root on this host" are the same request**, and treating them as equivalent in review is the correct posture (K12.3's operator-permissions argument).

**D9.3 — What `--privileged` grants**

**`--privileged` grants:**

- **All Linux capabilities** (D9.4) — including `CAP_SYS_ADMIN`, which is close to root itself.
- **Access to all host devices** under `/dev` — including raw block devices, so **the container can read and modify the host's disks directly**, bypassing every filesystem permission.
- **A permissive seccomp profile and AppArmor unconfined** (D9.7).
- **Ability to mount filesystems**, load kernel modules, and modify sysctls.
- **Write access to `/sys` and `/proc`**, including cgroup manipulation — which is one of the documented escape routes.

**It is effectively root on the host with extra steps.** A privileged container is not isolated in any meaningful security sense.

**The rare legitimate cases**: Docker-in-Docker (and rootless alternatives exist, D9.2), some storage and network CNI plugins that genuinely manipulate the host, hardware access needing raw devices, and certain system-level agents.

**The correct approach when someone asks for it**: **find out what specific capability or device is actually needed and grant only that:**

```bash
docker run --cap-add NET_ADMIN myapp                    # not --privileged
docker run --device /dev/ttyUSB0 myapp                  # one device
docker run --security-opt seccomp=custom.json myapp     # a specific profile
```

**Almost every `--privileged` request resolves to one or two capabilities** (D9.4), and asking "which capability do you need" is the productive response. **In Kubernetes, `privileged: true` is blocked by Pod Security Admission `baseline` and above** (K8.6), which is the enforcement.

**D9.4 — Dropping capabilities**

**Linux capabilities split root's privileges into discrete units**, so a process can have some without being root.

```bash
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myapp
```
```yaml
securityContext:
  capabilities:
    drop: ["ALL"]
    add: ["NET_BIND_SERVICE"]
```

**Docker's default grants a set of capabilities** even to non-root containers, including `CHOWN`, `SETUID`, `SETGID`, `NET_RAW`, `KILL`, and `MKNOD`. **Most applications need none of them.**

**The dangerous ones to recognise**: **`SYS_ADMIN`** (very broad — mount, namespace manipulation, close to root); **`SYS_PTRACE`** (inspect and modify other processes); **`SYS_MODULE`** (load kernel modules — a direct host compromise); **`NET_ADMIN`** (reconfigure networking); **`DAC_OVERRIDE`** (bypass file permission checks); **`NET_RAW`** (raw sockets — enables ARP spoofing and is on by default, which is why dropping it matters).

**The ones legitimately needed**: **`NET_BIND_SERVICE`** to bind ports below 1024 — **and the better answer is to listen on a high port and map it** (D5.2), avoiding the capability entirely. **`CHOWN`/`SETUID`/`SETGID`** if an entrypoint drops privileges, which a well-built image shouldn't need.

**The practice: `drop: ALL` and add back nothing**, then add only what fails. **Most applications run fine with no capabilities at all**, and starting from zero rather than trimming the default set is what makes this effective (A2.2's least-privilege method applied here).

**D9.5 — Read-only root filesystem**

```bash
docker run --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --tmpfs /run:rw,noexec,nosuid,size=16m \
  -v app-data:/var/lib/app \
  myapp
```
```yaml
securityContext:
  readOnlyRootFilesystem: true
volumeMounts:
  - { name: tmp, mountPath: /tmp }
volumes:
  - { name: tmp, emptyDir: { medium: Memory } }
```

**What it prevents:**

- **An attacker cannot write tools to disk** — no downloading a payload, no dropping a webshell, no modifying binaries.
- **No persistence** — a compromise doesn't survive a restart.
- **No tampering with the application's own code or config**, which blocks a class of privilege escalation.
- **It forces you to identify what actually needs to be writable**, which is a useful exercise in itself.

**The paths that typically need writing**: `/tmp`, `/run` or `/var/run` (PID files, sockets), application-specific cache and log directories, and language-runtime scratch space (some runtimes write to `/tmp` unconditionally).

**Provide them as tmpfs** (in-memory, ephemeral, and it counts against the memory limit — D4.2) **or as volumes** for anything that must persist (D6.1).

**The practical note**: **enabling it usually breaks something on the first attempt**, and the failure identifies the writable path you missed. Iterate with `--read-only` locally until it runs clean, then enforce.

**In Kubernetes it's part of the `restricted` Pod Security Standard** (K8.6), and it's one of the highest-value hardening settings relative to its cost.

**D9.6 — User namespace remapping and rootless Docker**

**User namespace remapping** maps UIDs inside the container to different UIDs on the host (D1.3). **Root inside (UID 0) becomes an unprivileged high UID outside** (e.g. 231072).

```json
// /etc/docker/daemon.json
{ "userns-remap": "default" }
```

**So a container escape as root lands as an unprivileged user on the host** — which substantially reduces the impact of D9.1's default. **It's not enabled by default** and that's the point of the item.

**The limitations**: it breaks some features — **`--privileged`, host networking, and PID namespace sharing conflict with it**; bind mount permissions become confusing because the host UID differs from what the container sees (D6.4); and it's daemon-wide, so it applies to everything.

**Rootless Docker** goes further: **the daemon itself runs as an unprivileged user**, using user namespaces and slirp4netns for networking. **Nothing in the stack runs as root**, so even a daemon compromise doesn't give host root.

**The limitations of rootless**: **cannot bind ports below 1024** without additional configuration; **networking performance is lower** (userspace networking); some storage drivers and features are unavailable; and cgroup v2 is required for resource limits.

**The current state worth naming**: **Podman is rootless by default** and is the more mature implementation of this model; **Kubernetes has user namespace support** (beta and progressing), which addresses the long-standing gap where a container escape meant host root. **This is a genuinely improving area** and knowing the direction is a good signal.

**D9.7 — seccomp and AppArmor at a working level**

**seccomp** filters **which syscalls** a process may make. **Docker applies a default profile** blocking around 40 of the ~350 syscalls — the obviously dangerous ones (`mount`, `reboot`, `kexec_load`, `ptrace` in some contexts). **This default is a meaningful control that most people don't know is active.**

```bash
docker run --security-opt seccomp=/path/to/profile.json myapp
docker run --security-opt seccomp=unconfined myapp        # ← disables it
```

A custom profile is JSON listing allowed or denied syscalls with a default action. **Writing one from scratch is impractical; generate it by tracing** the application's actual syscalls (`strace`, or `oci-seccomp-bpf-hook`) and allow-listing them.

**AppArmor** (Debian/Ubuntu) and **SELinux** (RHEL) are Linux Security Modules enforcing **mandatory access control** — restricting file paths, capabilities, and network operations per profile. **Docker ships a default AppArmor profile** (`docker-default`) restricting writes to sensitive `/proc` and `/sys` paths.

**The working-level guidance:**

- **Do not disable them.** `--security-opt seccomp=unconfined` and `apparmor=unconfined` appear in Stack Overflow answers as a fix for a permission error — **and they remove a whole layer of defence to solve a problem that usually has a narrower fix.** Recognising that in review is the practical skill.
- **`RuntimeDefault` seccomp is part of the Kubernetes `restricted` standard** (K8.6) and is what you should be enforcing.
- **Custom profiles are for high-value workloads** where the effort is justified, and they need maintenance as the application changes.
- **gVisor** (D1.8) is the heavier alternative — a user-space kernel intercepting syscalls entirely, giving much stronger isolation than a syscall filter.

**D9.8 — Why secrets must not be baked into layers**

**A layer is immutable, and deleting a file in a later layer does not remove it from the image** (D1.5). OverlayFS records a whiteout; **the data is still in the earlier layer and is extractable by anyone who can pull the image.**

```dockerfile
COPY id_rsa /root/.ssh/id_rsa
RUN git clone git@github.com:acme/private.git && rm /root/.ssh/id_rsa
# the key is STILL in the image, in the COPY layer
```

```bash
# trivially recovered
docker save myimage | tar -x -O --wildcards '*/layer.tar' | tar -t | grep id_rsa
docker history --no-trunc myimage
```

**The exposure paths:**

- **Anyone who can pull the image** — which in a shared registry is a broad group, and if the image is ever made public, everyone.
- **`docker history`** shows build args (D2.9) and the commands.
- **`docker inspect`** shows environment variables set with `ENV`.
- **The build cache**, including a shared one (D3.5).
- **Every layer cache on every node** that has pulled it.

**The consequence: a secret in an image must be treated as leaked and rotated** (S6.4). Rebuilding the image without it does not un-leak it.

**The correct approaches**: **BuildKit secret mounts** for build-time credentials (D2.10); **runtime injection** for runtime secrets (D4.10, S6.2); **multi-stage** so build-stage material doesn't reach the final image (D3.2); and **`.dockerignore`** so `.env`, `.git`, and key files aren't in the context at all (D2.5).

**D9.9 — Inspecting an image's history**

```bash
docker history --no-trunc myimage:1.4.2
docker inspect myimage:1.4.2 --format '{{json .Config}}' | jq

# extract and examine the actual layers
docker save myimage:1.4.2 -o img.tar && mkdir x && tar xf img.tar -C x
dive myimage:1.4.2                              # interactive, best for this
```

**What to look for:**

- **Secrets in build args or `ENV`** (D2.9, D9.8) — `docker history | grep -iE 'token|password|secret|key'`.
- **A `COPY . .` that pulled in `.git`, `.env`, or credentials** (D2.5).
- **Unexpected `curl | sh`** — a script fetched and executed from an unverified source (S7.1).
- **Files added and later deleted**, which `dive` flags explicitly — **the space is wasted and the content is still there.**
- **The base image**, and whether it's what you expected and pinned (D2.15).
- **Unexpected packages** — a build toolchain in a runtime image, or `curl`/`wget` that shouldn't be there (S7.6).
- **The user** — `docker inspect` `.Config.User`; **empty means root** (D9.1).
- **Exposed ports, entrypoint, and environment** — comparing intent with what's actually configured (D10.8).

**The use cases**: reviewing a third-party image before adopting it (S7.1's supply chain argument); auditing your own images for leaked secrets; and investigating an incident where you need to know what's actually in the running artefact.

**D9.10 — Container escape, conceptually, and the controls**

**An escape is a container process gaining access to the host or to other containers.**

**The routes:**

1. **Misconfiguration — by far the most common:**
   - **`--privileged`** (D9.3) — barely an escape; it's granted access.
   - **The Docker socket mounted** (D9.2) — one command.
   - **`hostPath` mount of `/` or a sensitive path**, or `/proc`.
   - **Host namespaces shared** (`--pid=host`, `--net=host`).
   - **Dangerous capabilities** — `SYS_ADMIN`, `SYS_MODULE`, `SYS_PTRACE` (D9.4).
2. **Kernel vulnerabilities** — the container and host share a kernel (D1.6), so a local privilege escalation in the kernel is an escape. **Dirty COW, Dirty Pipe** are the well-known examples.
3. **Runtime vulnerabilities** — **CVE-2019-5736 in runc** allowed overwriting the host's runc binary from inside a container; **Leaky Vessels (2024)** was a set of runc and BuildKit escapes.
4. **Symlink and race conditions** in volume handling.

**The controls, mapped to the routes:**

| Control | Blocks |
|---|---|
| Non-root (D9.1), user namespaces (D9.6) | Escape lands unprivileged |
| Drop all capabilities (D9.4) | Capability-based routes |
| No privileged, no socket, no host namespaces (D9.2, D9.3) | The misconfiguration routes |
| seccomp and AppArmor (D9.7) | Narrows the syscall surface for kernel exploits |
| Read-only rootfs (D9.5) | Tooling and persistence |
| Patch the host kernel and runtime (S8.4) | Known CVEs |
| gVisor / Kata (D1.2) | Kernel surface, by not sharing it |
| Admission policy (K8.6, K8.9) | Enforcing all of the above |

**The framing**: **most escapes are configuration, not exploits.** Enforcing the Pod Security `restricted` standard blocks essentially every configuration route, which is why it's the highest-value single control (K8.6).

**D9.11 — Why container isolation isn't a security boundary for untrusted code**

**The argument, and it should be stated directly:**

- **Containers share the host kernel** (D1.6). **The isolation is enforced by kernel features, so a kernel vulnerability defeats it entirely** — and the kernel presents a syscall interface of hundreds of calls, which is a very large attack surface compared with a hypervisor's narrow one (D1.2).
- **Kernel local-privilege-escalation vulnerabilities are found regularly.** Any one of them is potentially a container escape affecting every container on the host simultaneously.
- **The default configuration is weak** — root, default capabilities, writable filesystem (D9.1, D9.4, D9.5) — so an escape lands with privilege unless you've hardened deliberately.
- **The container runtime itself has had escapes** (D9.10).
- **Side channels** — Spectre-class attacks, resource-exhaustion signalling, and shared cache timing cross container boundaries.

**So: containers are a good isolation boundary between *your own* workloads that you trust not to be actively hostile. They are not a sufficient boundary for running code you do not trust** — a customer's arbitrary code, untrusted builds, or a genuinely multi-tenant execution platform.

**What to use instead for untrusted code:**

- **A VM boundary** — **Firecracker** (what Lambda and Fargate use), Kata Containers.
- **gVisor** — a user-space kernel intercepting syscalls, so the host kernel is barely exposed. A middle ground with a performance cost.
- **Separate hosts or separate accounts** per tenant (A1.1).

**The framing that lands**: **AWS runs Lambda on Firecracker microVMs rather than on shared-kernel containers, and that decision is the industry's clearest statement about this exact question.** Kubernetes namespaces are an organisational and RBAC boundary, not a security boundary between hostile parties (K8.10) — and this item is the underlying reason.

---

## D10. Debugging & troubleshooting

**D10.1 — Reading logs and where they're stored**

```bash
docker logs api
docker logs -f --tail 100 api
docker logs --since 10m --timestamps api
docker logs --until 2026-08-22T14:00:00 api
```

**Where they are**: with the default `json-file` driver, at `/var/lib/docker/containers/<container-id>/<container-id>-json.log` on the host — **one JSON object per line**, wrapping stdout and stderr with a stream marker and a timestamp.

**The facts that matter:**

- **`docker logs` reads that file**, so it only works with `json-file` or `local`. **With `awslogs`, `fluentd`, or another shipping driver, `docker logs` returns nothing** — the logs went straight to the backend. **This surprises people** and is worth knowing before you go looking (D4.8).
- **Logs are deleted with the container.** `docker rm` removes them, so **removing a crashed container destroys the evidence** — the same discipline point as K9.3.
- **No rotation by default** (D4.8, D6.7).
- **Only stdout and stderr are captured.** An application logging to a file inside the container produces nothing here (O4.6).

**The interleaving caveat**: stdout and stderr are captured separately and merged by timestamp, so ordering between the two streams can be misleading for tightly-interleaved output.

**For a stopped container**, `docker logs` still works until it's removed — which is why `--rm` (D4.1) is convenient and occasionally costs you the diagnosis.

**D10.2 — Exec into a running container, and when that's the wrong instinct**

```bash
docker exec -it api sh
docker exec -it api ps aux
docker exec api cat /etc/app/config.yaml
docker exec -u root -it api sh          # as root, if the container runs non-root
```

**When it's right**: inspecting configuration as the container actually sees it, checking what's listening (D5.6), reading a file, checking environment variables, and quick network diagnosis.

**When it's the wrong instinct** — and this is the substance:

- **Changing anything.** A fix applied via `exec` **is lost when the container restarts** and is not in any image or manifest. **It's drift with a very short half-life**, and worse, it makes the running container differ from what your code says (TF1.5's argument in miniature).
- **When the container has already exited** — you can't exec into it (D10.4). **Reaching for `exec` on a crash-looping container and finding it unavailable is a common moment of confusion**, and the answer is to override the command with `sleep`.
- **When it indicates missing observability.** **If the answer to every problem is a shell, your logs, metrics, and traces are inadequate** (O16.6). That's the mature framing.
- **When the image is distroless** and there's no shell (D10.3) — which is by design (S7.6).
- **In production, on an orchestrator**, where exec access is effectively production write access and should be audited (K8.13).

**The better instincts**: read the logs first (D10.1); `docker inspect` for configuration (D10.8); reproduce locally; and for a crashed container, examine it rather than trying to enter it.

**D10.3 — Debugging a container with no shell**

**Distroless and scratch images have no shell, no package manager, and no tools** (D2.13) — deliberately, because that's what an attacker would use (S7.6). Which also means `docker exec -it sh` fails.

**The techniques:**

```bash
# 1. join the target's namespaces with a full-featured image
docker run --rm -it \
  --pid=container:api --network=container:api \
  --cap-add SYS_PTRACE \
  nicolaka/netshoot sh
# now ps, netstat, tcpdump, strace, curl all see the target's processes and network

# 2. inspect the filesystem without running anything
docker cp api:/etc/app/config.yaml ./config.yaml
docker export api | tar -t | less

# 3. build a debug variant from the same base
#    FROM myapp AS debug
#    COPY --from=busybox /bin/sh /bin/sh

# 4. Kubernetes
kubectl debug -it <pod> --image=nicolaka/netshoot --target=app
```

**The namespace-joining technique (1) is the key one**: **`--pid=container:X --network=container:X` puts a tools container into the target's process and network namespaces** (D1.3), so you can inspect it fully without adding anything to the image. It's the direct equivalent of `kubectl debug --target` (K9.12).

**`docker cp` works on a stopped container too**, which is how you retrieve evidence from something that crashed.

**The framing worth giving**: **the difficulty of debugging distroless is a feature, not a defect** — and because the tooling exists to work around it for legitimate use (ephemeral debug containers), it's not a real cost. **That pairing is what makes distroless practical**, and offering it pre-empts the usual objection to minimal images.

**D10.4 — Diagnosing a container that exits immediately**

```bash
docker ps -a                                    # see it, and its exit code
docker logs <container>                         # what did it say before dying?
docker inspect <container> --format '{{.State.ExitCode}} {{.State.Error}} {{.State.OOMKilled}}'
```

**The causes, by exit code and symptom:**

- **Exit 0, immediately** — **the process completed and exited.** The most common cause is **no long-running foreground process**: the command was a one-shot, or the process daemonised itself into the background (nginx without `daemon off;`, or a service started with `service X start`). **The container's lifetime is PID 1's lifetime** — if it forks and exits, the container exits.
- **Exit 1 or 2** — an application error. **The logs will say** — a missing environment variable, an unreachable dependency, a config parse failure.
- **Exit 125** — the Docker daemon itself failed (a bad flag).
- **Exit 126** — the command was found but not executable (permissions, or a missing shebang).
- **Exit 127** — **command not found.** Usually a wrong path in `ENTRYPOINT`, or a shell-form command in an image with no shell (D2.13), or a Windows line ending (`\r`) on the entrypoint script — **which produces a baffling "not found" for a file that plainly exists.**
- **Exit 137** — SIGKILL, almost always OOM (D10.5, D10.6).
- **Exit 139** — segfault, frequently an architecture mismatch (D10.7, D1.9).

**The technique for investigating**: **override the entrypoint so it doesn't run the failing command:**

```bash
docker run -it --entrypoint sh myimage
# now poke around: does the binary exist, is it executable, what does it do when run by hand?
```

**And `docker logs` works on a stopped container** until it's removed — so **don't `docker rm` it before reading them** (D10.1).

**D10.5 — Interpreting exit codes**

| Code | Meaning |
|---|---|
| 0 | Clean exit |
| 1 | Generic application error |
| 2 | Shell misuse / builtin error |
| 125 | Docker daemon error — the run itself failed |
| 126 | Command found but not executable |
| 127 | Command not found |
| **137** | **128 + 9 = SIGKILL** — OOM kill, or `docker kill`, or grace period expired |
| **139** | **128 + 11 = SIGSEGV** — segmentation fault |
| 143 | 128 + 15 = SIGTERM — terminated and exited on the signal |
| 255 | Out-of-range or generic failure |

**The convention: a process killed by signal N exits with 128 + N.** Knowing that lets you decode any signal-based exit rather than memorising a table.

**The two that matter most:**

- **137** — **OOM kill** if `.State.OOMKilled` is true (D10.6); otherwise SIGKILL from `docker kill`, or **from `docker stop` when the grace period expired** because the process didn't handle SIGTERM (D4.3, D2.3). **Distinguishing those two is the diagnosis.**
- **139** — segfault. In a container context, **frequently an architecture mismatch** (D1.9) — an amd64 binary on arm64 sometimes segfaults rather than giving a clean `exec format error`. Also a genuine application bug or a musl/glibc incompatibility (D2.14).

**143 is a healthy shutdown** — it means the process received SIGTERM and exited on it, which is what you want to see on a `docker stop` (D4.4).

**D10.6 — Diagnosing an OOM kill vs an application crash**

```bash
docker inspect <container> --format '{{.State.OOMKilled}} {{.State.ExitCode}}'
# true 137  → OOM killed

dmesg -T | grep -i -E 'killed process|out of memory'
docker stats --no-stream
```

**The distinction:**

| | OOM kill | Application crash |
|---|---|---|
| Exit code | **137** | Usually 1, or 139 for a segfault |
| `.State.OOMKilled` | **true** | false |
| Application logs | **Nothing — no stack trace, no shutdown message.** It was SIGKILLed with no warning | Usually an error and possibly a stack trace |
| Host `dmesg` | Kernel OOM message naming the process and cgroup | Nothing |
| Pattern over time | **Sawtooth memory graph, rising to the limit, restart, repeat** | Often correlated with a specific input or event |

**The absence of any log output before the exit is the most useful signal** — **SIGKILL cannot be caught**, so the application had no opportunity to say anything. A crash almost always leaves something.

**Two OOM mechanisms to distinguish** (K6.11):

- **cgroup OOM** — the container exceeded **its own** limit. `.State.OOMKilled` is true and it's contained.
- **Host OOM** — the whole host ran out and the kernel chose a victim by score. **The killed container may be an innocent bystander** with plenty of headroom in its own limit, and `dmesg` shows the full candidate table.

**Then determine which memory problem it is** (O10.4): **memory rising to a plateau above the limit** means under-provisioned — raise it (D11.4). **Unbounded growth with a constant sawtooth period** means a leak — raising the limit only lengthens the interval, and saying so explicitly is the mark of understanding it. **And check the runtime is reading its cgroup limit** (O10.6) — a JVM sizing its heap from host memory in a small container OOMs immediately.

**D10.7 — Diagnosing an image pull failure**

**The four causes have distinct error messages, and reading them is most of the answer:**

1. **Not found** — `manifest unknown`, `manifest for X:tag not found`, `repository does not exist`. A wrong tag, a wrong registry path, or **an image that was never actually pushed** — a common CI failure where the build succeeded and the push didn't.
2. **Authentication** — `unauthorized`, `authentication required`, `denied: requested access to the resource is denied`. Missing or expired credentials, wrong registry, or — on ECR — **the node's IAM role lacking pull permission** (A5.1, D8.6). **Note the pull is done by the node/daemon, not by the workload's identity**, which confuses people on EKS.
3. **Rate limited** — `toomanyrequests: You have reached your pull rate limit`. **Docker Hub, from a shared NAT IP** (D8.7). **Intermittent and confusing** because it depends on what everyone else has been pulling.
4. **Architecture** — `no matching manifest for linux/amd64 in the manifest list entries`, or the image pulls and the container fails with **`exec format error`** (D1.9). **An arm64 image built on a Mac deployed to x86 nodes** is the modern classic.

**Also**: no network path to the registry from a private subnet (needs NAT or a VPC endpoint, A3.3); a TLS failure against a private registry with a self-signed certificate (S2.13); and disk full on the node (D6.7).

**The diagnostic**: **`docker pull` the exact reference by hand** from the affected host — the error message is definitive. In Kubernetes, `kubectl describe pod` shows the pull error in Events (K9.5).

**D10.8 — Inspecting a container's full config**

```bash
docker inspect api | jq
docker inspect api --format '{{.Config.User}}'
docker inspect api --format '{{json .HostConfig.Mounts}}' | jq
docker inspect api --format '{{json .Config.Env}}' | jq
docker inspect api --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}'
docker inspect api --format '{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}}'
docker inspect api --format '{{json .NetworkSettings.Ports}}' | jq
```

**Comparing intent with reality is the point** — the running container's actual configuration frequently differs from what you believe you specified:

- **`.Config.User` empty means it's running as root** (D9.1), despite what you thought the Dockerfile said — commonly because a base image's `USER` was overridden, or the run command specified otherwise.
- **`.HostConfig.Memory` is 0 if no limit was set** — so the container can consume the host (D4.2).
- **`.Config.Env`** shows the merged environment, including what the image baked in — **and it's where secrets are visible** (S6.1).
- **`.NetworkSettings.Ports`** shows the actual published mapping and bind address (D5.2, D5.7).
- **`.Mounts`** shows what's actually mounted and whether it's read-only.
- **`.Config.Image` vs `.Image`** — the tag it was started with versus **the digest actually running**, which is how you catch a stale cached image under a moved tag (D8.2, D10.11).

**The habit**: **when behaviour doesn't match expectation, inspect before theorising.** Compose and orchestrator abstractions mean the effective configuration is the merge of several sources, and `inspect` is the only view of the result.

**D10.9 — Checking resource usage per container**

```bash
docker stats                              # live, all containers
docker stats --no-stream                  # one snapshot, scriptable
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
```

**Reading it:**

- **`MEM USAGE / LIMIT`** — and **`LIMIT` shows the host's total memory if no limit was set** (D4.2), which is how you spot an unlimited container.
- **`MEM %`** is against the limit, so it's meaningful only when a limit exists.
- **`CPU %`** — **can exceed 100%**, because it's relative to a single core: 250% means two and a half cores.
- **`NET I/O` and `BLOCK I/O`** are cumulative since start, not rates — so you need two samples to derive a rate.

**The limitations that matter, and knowing them is the point:**

- **It's a point-in-time view with no history.** You cannot see what happened during last night's incident. **For anything real, use proper metrics** — cAdvisor and Prometheus (O9, K9.13) — and `docker stats` is a quick local check.
- **Memory shown is the working set** (RSS plus cache minus reclaimable), which is what the OOM killer acts on (O10.1) — reasonable, and not the same as heap.
- **It doesn't show CPU throttling** (D4.2, O9.4), which is the most important CPU metric in a limited container and is invisible here. **Read `/sys/fs/cgroup/cpu.stat`** for `nr_throttled` and `throttled_time`.
- **Polling overhead** is non-trivial with many containers.

**D10.10 — Debugging a build failure at an intermediate layer**

```bash
docker build --progress=plain --no-cache .        # full output, no cache hiding
```

**With the classic builder**, a failed build left intermediate images and you could run the last successful one:

```bash
docker run -it <last-successful-layer-id> sh
```

**BuildKit doesn't produce those by default**, so the modern techniques are:

```bash
# 1. build up to the last working stage or instruction
docker build --target build -t debug-build .
docker run -it debug-build sh

# 2. temporarily truncate the Dockerfile after the last successful step, build, and exec in

# 3. buildx debug — drops into a shell at the failure point
docker buildx debug --invoke /bin/sh build .

# 4. export the failed state
BUILDKIT_HOST=... buildctl build ... --output type=local,dest=./out
```

**Technique 3 (`buildx debug --invoke`) is the modern answer** and worth knowing — it drops you into the build container at the point of failure, with the filesystem as it was.

**The practical approach that works everywhere: add a stage boundary before the failing step**, build with `--target`, and exec in to reproduce the command by hand. **Reproducing the failing command interactively is what actually resolves it** — you see the real error, the actual filesystem state, and what's on `PATH`.

**The common build failures**: a file not in the context (D2.5); a cached stale package index (D2.7); a network failure fetching dependencies; **an architecture mismatch during a cross-build** (D3.6); permissions on a copied file; and a missing build dependency that exists on your machine but not in the image.

**D10.11 — "Works on my machine" from architecture or cached layers**

**The two causes named in the item, and they present differently:**

**Architecture** (D1.9):

- **Built on an Apple Silicon Mac (arm64), deployed to amd64 nodes.** The symptom is `exec format error` (D10.7), or a segfault (D10.5), or **silent success under QEMU emulation locally** so the developer never notices.
- **The reverse** — an amd64 image pulled on a Mac, which Docker Desktop emulates. **It works and is very slow**, and people conclude the application is slow.
- **The fix**: build multi-arch (D3.6), or build for the target platform explicitly (`--platform linux/amd64`), and **verify with `docker buildx imagetools inspect`** what architectures the pushed image actually contains.

**Cached layers** (D3.3):

- **A local build uses a cached layer that CI doesn't have** (or vice versa), so the images differ. A `RUN` that fetched a dependency months ago is still cached locally.
- **A mutable tag** means the local `node:20-slim` and CI's are different images (D2.15, D8.2).
- **The fix**: **pin base images by digest** (D2.15), **use lockfiles** (S7.2), and **build in CI as the source of truth** — a local build is for iteration, not for producing the deployed artefact.

**The other frequent causes worth naming:**

- **`.dockerignore` missing**, so local `node_modules` built for macOS is copied in (D2.5) — **native modules for the wrong platform**, and a genuinely confusing failure.
- **Bind-mounted source locally versus copied-in code in CI** (D7.6) — so the image works locally because the mount masks a missing `COPY`.
- **Environment differences** — a local `.env` that isn't in CI (D7.3).
- **Docker Desktop's file sharing translating permissions**, hiding UID problems that appear on Linux (D6.4).

**The structural answer**: **the artefact deployed to production should be the one built in CI, promoted unchanged** (D8.8) — which removes the local build from the path entirely.

---

## D11. Production readiness

**D11.1 — What makes an image production-ready beyond "it runs"**

The checklist, and each item connects to something earlier:

- **Minimal base and minimal contents** — distroless or slim, multi-stage, no build tooling (D2.13, D3.1, S7.6).
- **Non-root, with a numeric UID** (D9.1), and it must actually work unprivileged.
- **Compatible with a read-only root filesystem** (D9.5) — writable paths identified and provided as volumes or tmpfs.
- **Correct signal handling** — exec-form entrypoint, SIGTERM handled, graceful drain (D2.3, D4.4, D11.2).
- **Configuration injected at runtime**, nothing environment-specific baked in (D4.10) — which is what makes promotion possible (D8.8).
- **No secrets in any layer** (D9.8).
- **A health endpoint** the orchestrator can use, checking the right thing (D4.7).
- **Logs to stdout, structured** (D4.8, O4.1).
- **Metrics exposed** if the platform scrapes them (O3.12).
- **Traceability** — OCI labels back to the commit (D2.12), pinned base by digest (D2.15), reproducible from a known commit (D11.3).
- **Scanned and signed** (S7.5, S7.7), with an SBOM (S7.8).
- **Resource requirements known** from measurement (D11.4).
- **Multi-arch if the fleet is mixed** (D3.6).
- **Sized so pull time doesn't hurt scaling** (D11.7).

**The framing**: "it runs" is the first of about fifteen requirements. **The distinguishing question is what happens when it's stopped, scaled, rescheduled, attacked, or investigated** — and production readiness is the set of properties that make those cases uneventful.

**D11.2 — Handling SIGTERM and draining connections**

The correct sequence when SIGTERM arrives (D4.4):

1. **Fail readiness immediately**, so the orchestrator stops routing new requests to this instance (K9.10). **This must happen first**, and it's the step people omit.
2. **Wait briefly** — endpoint removal propagates asynchronously through the load balancer and kube-proxy, so requests may still arrive for a second or two after readiness fails. **A short `preStop` sleep covers this**, and without it every deploy produces a small number of connection errors.
3. **Stop accepting new connections** but continue serving in-flight ones.
4. **Finish in-flight work**, bounded by a timeout shorter than the grace period.
5. **Close resources** — flush buffers, close database connections, commit or nack in-flight messages (M2.2), deregister from service discovery.
6. **Exit 0** — which shows as exit code 143 if it exited on the signal (D10.5).

**The configuration that must align**: `terminationGracePeriodSeconds` (or `--time`) **must exceed** the application's drain timeout, which must exceed the longest expected request. **If the grace period is shorter, you get SIGKILLed mid-drain** and the careful shutdown code never completes.

**Why it matters**: without it, **every deploy, every scale-in, every node replacement drops requests.** On a service deploying several times a day with rolling updates (K2.6), that's a continuous low-level error rate attributed to "flakiness" — and it's entirely self-inflicted and fixable.

**The prerequisite that catches people**: **the process must be PID 1 to receive the signal at all** (D2.3) — shell-form entrypoint means none of this code ever runs.

**D11.3 — Reproducibility from a known commit**

**The goal**: given a commit SHA, rebuild an image that is functionally identical to what was deployed.

**What breaks it:**

- **Floating base image tags** (D2.15) — `node:20-slim` today is not yesterday's. **Pin by digest.**
- **Unpinned dependencies** (S7.2) — `npm install` without a lockfile, `pip install requests` without a version, `apt-get install curl` without a version pin. **Use lockfiles and install from them exactly** (`npm ci`, `--require-hashes`).
- **Network-fetched content at build time** — `curl https://example.com/install.sh | sh` fetches whatever is there now. **Pin a version and verify a checksum.**
- **Timestamps and build metadata** embedded in the artefact — which breaks byte-for-byte reproducibility though not functional equivalence. `SOURCE_DATE_EPOCH` and BuildKit's `--build-arg SOURCE_DATE_EPOCH` address this if you need bit-identical output.
- **Build cache differences** (D10.11).

**The practical target is functional reproducibility**, not bit-for-bit — the same inputs producing an image that behaves identically. **Bit-for-bit is achievable and is a much higher bar**, relevant for high-assurance supply chain work (S7.12).

**The traceability half**: **the image must record which commit produced it** — OCI labels (D2.12) and a commit-SHA tag (D8.4) — so the mapping works in both directions. **"What code is running in production" and "what image did this commit produce" should both be answerable**, and during an incident the first one matters a great deal.

**D11.4 — Resource requests and limits from measurement**

The method (K6.5, O10.9):

1. **Run under realistic load** long enough to reach steady state — including warm-up, cache filling, and at least one full GC cycle for a managed runtime.
2. **Measure actual usage** — `docker stats` for a quick look (D10.9), Prometheus with cAdvisor for real data, or VPA in recommendation mode in Kubernetes (K7.4).
3. **CPU: request at p90–p95 of observed usage.** CPU is compressible, so being slightly under is a slowdown, not a failure (D4.2).
4. **Memory: request and limit at p99 plus 20–30% headroom.** **Memory over-limit is fatal**, so be more conservative here — the asymmetry in D4.2 is what drives the different treatment.
5. **Set requests equal to limits for memory** on anything important (Guaranteed QoS, K6.4).
6. **Consider omitting the CPU limit** for latency-sensitive services (K6.2, O9.4) — with correct requests the scheduler shares CPU proportionally, and a limit forbids bursting into idle capacity for no benefit. **In a multi-tenant cluster the isolation argument goes the other way**, so state it as a tradeoff.
7. **Re-measure after significant changes.**

**The measurement caveats**: **startup uses more than steady state** — JVMs and anything with warm-up — so requests sized for steady state make startup slow and can trip readiness timeouts. **And the runtime must read its cgroup limit** (O10.6) or it sizes itself from the host and OOMs immediately.

**The cost dimension** (K6.5): **cluster spend is driven by requests, not usage**, so over-requesting is directly wasted money at fleet scale — and right-sizing from data is a genuine cost reduction with no reliability regression (A12.7).

**D11.5 — Twelve-factor principles that apply to containerisation**

The factors that map directly, with what each means concretely here:

- **I. Codebase** — one repo, many deploys. **The same image promoted between environments** (D8.8).
- **III. Config** — **config in the environment, not the code.** The single most important one for containers: it's what makes one image work everywhere (D4.10).
- **IV. Backing services** — attached resources addressed by URL, so a database can be swapped without a code change.
- **V. Build, release, run** — **strict separation.** The build produces an immutable image; the release combines it with config; the run executes it. **No building at release time and no changing a running container** (D10.2).
- **VI. Processes** — **stateless and share-nothing.** State goes in a backing service, not the container layer (D6.2). **This is what makes containers disposable and therefore schedulable.**
- **VII. Port binding** — the application binds a port itself rather than relying on an injected web server (D5.2).
- **VIII. Concurrency** — scale out with more processes rather than up with threads (K2.5).
- **IX. Disposability** — **fast startup and graceful shutdown** (D11.2). Directly the container lifecycle.
- **X. Dev/prod parity** — the same image, so the environments genuinely match (D8.8).
- **XI. Logs** — **treat as event streams to stdout** (D4.8, O4.6).

**The ones that matter most for containerisation specifically: III (config), VI (stateless), IX (disposability), and XI (logs)** — those four are what make a container work correctly under an orchestrator, and violating any of them produces a workload that fights the platform.

**The honest caveat**: twelve-factor is opinionated and predates Kubernetes; some of it is dated (the build/release/run separation is now handled differently, and XII's admin processes are Jobs). **The principles hold; the specific prescriptions less so.**

**D11.6 — How config and secrets differ at runtime**

Both are injected at runtime (D4.10), and the handling differs:

| | Configuration | Secrets |
|---|---|---|
| Sensitivity | Low — endpoints, feature flags, log levels | **High — credentials, keys, tokens** |
| Storage | ConfigMap, env vars, files, parameter store | **Secret store with access control and audit** (S6.2) |
| In version control | **Yes** — it's reviewable and belongs in git | **No** — only a reference (K10.11) |
| Visibility | Fine in `docker inspect`, logs, dashboards | **Must not appear** in inspect, logs, crash dumps (S6.7) |
| Rotation | Rare, on deploy | **Regular, ideally without a deploy** (S6.5) |
| Delivery | Env vars are fine | **Prefer mounted files or runtime fetch** (S6.1) |
| Access control | Broad | **Least privilege, per workload** (S9.1) |
| Audit | Not needed | **Who accessed it, and when** |

**The practical consequences:**

- **Secrets should not be environment variables** where avoidable — visible in `docker inspect`, inherited by children, captured by crash reporters (S6.1).
- **Secrets need a rotation story** the application supports — re-fetch on auth failure rather than caching at startup (S6.5).
- **The best secret is one that doesn't exist** — workload identity to a cloud service (A2.7, S6.6) means no credential to manage at all.
- **Configuration in git, secrets by reference** — which is the GitOps resolution (K10.11).

**The point to make**: **treating them identically is the failure.** Putting a database password in the same ConfigMap as the log level means it inherits the ConfigMap's access control, visibility, and version-control treatment — all of which are wrong for a credential.

**D11.7 — Image size, deploy speed, and autoscaling responsiveness**

**The chain: image size → pull time → pod start time → how fast you can scale.**

**Where it bites:**

- **Cold start on a new node.** Autoscaling adds a node (K7.5); it has no layers cached, so it pulls the whole image. **A 2GB image over a constrained pull path is minutes** — during which the traffic spike that triggered the scale-out is unserved. **This is the case that actually matters**, and it turns image size from an aesthetic concern into a latency one (O14.6).
- **Rolling deployments** — every node pulls the new image; a large image extends the rollout window and therefore the period at reduced capacity (K2.6).
- **Spot interruption and node churn** (A4.5, K7.6) — nodes are replaced routinely, so cold pulls are frequent rather than exceptional.
- **Recovery from a node failure** — how fast capacity is restored.
- **CI** — pull and push time on every build.

**The quantification**: a 1.2GB image versus 80MB is roughly 40 seconds versus 5 on a typical path. **Multiply by every scale-out event and every deploy**, and it's a material difference in how responsive the system is.

**The mitigations beyond making it smaller** (D3.8): **layer sharing** — if all your services share a base, the base is pulled once per node; **pre-pulling** images onto nodes (a DaemonSet, or Karpenter's ability to warm); **registry locality** — pull from the same region, and use a VPC endpoint or pull-through cache (D8.7, A3.3); and **lazy-loading snapshotters** (eStargz, SOCI on AWS) which start the container before the whole image has been pulled — a genuinely significant development for large images and worth naming.

**D11.8 — When a container is the wrong answer**

The cases:

- **Workloads needing a different kernel or OS.** Windows applications on Linux hosts, anything needing a specific kernel version or module (D1.6).
- **Kernel-level software** — drivers, some monitoring and security agents, anything loading modules. **It can run privileged, and at that point the container is providing packaging, not isolation** (D9.3).
- **Untrusted multi-tenant code** (D9.11) — needs a VM boundary.
- **Very high performance requirements** where the network or storage abstraction costs matter — though this is narrower than people claim, since the overhead is small and `--network host` and device passthrough exist.
- **Stateful systems with demanding storage requirements** — a database is runnable in a container and the question is whether you want to own the durability (K13.8, DB14.3). **Frequently the answer is a managed service.**
- **Desktop and GUI applications** — possible, awkward, and rarely worth it.
- **Legacy applications that assume a full OS** — multiple daemons, an init system, in-place upgrades. **Containerising them produces a badly-managed VM** (D4.9), and a VM is the honest answer.
- **Extremely short-lived, high-frequency execution** — where container startup, small as it is, dominates. **Firecracker or a function runtime fits better.**
- **A single application on a single server with no scaling need** — the container adds a layer and buys little.

**The framing**: **containers are packaging plus isolation plus a scheduling unit.** If you need none of the three, they're overhead. **If you need the isolation to hold against a determined adversary, they're insufficient** (D9.11). Everything in between is where they're the right answer, which is most things — and being able to name the exceptions is what makes the endorsement credible.

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 103 items this is a mid-sized domain, and much of D1 and D2 will be familiar if you've worked with containers at all.
- **D1 is worth reading even if you scored well.** "What is a container" opens a lot of interviews, and the namespaces-and-cgroups answer, plus D1.6's shared-kernel consequence, is what makes D9.10 and D9.11 coherent rather than memorised.
- **D10 is where practical experience is most visible.** Exit code 137 with `.State.OOMKilled`, a container exiting immediately because the process daemonised, and an `exec format error` from an arm64 build are everyday realities and can't be reconstructed under pressure.
- **The highest-value items for a platform role are D2.9/D2.10 (build args are not secrets), D4.3/D4.4 (signals and graceful shutdown), D5.7 (Docker bypasses the host firewall), D9.2 (the Docker socket is root), and D11.7 (image size affects scaling responsiveness).** Each of those is a specific, consequential fact that people frequently get wrong.
- **The failure modes are the part that reads as experience.** Shell-form `ENTRYPOINT` meaning your application never receives SIGTERM (D2.3); `apt-get update` cached separately from `install` (D2.7); a secret deleted in a later layer still being in the image (D9.8); `ufw deny` not blocking a published port (D5.7); and `docker system prune --volumes` deleting a stopped database's data (D6.6).
- **Cross-references into Kubernetes are dense throughout** — K2.4 for sidecars, K6.2 and K6.11 for limits and eviction, K8.6/K8.7 for enforcing the D9 hardening, and K9.5/K9.12 for the orchestrated versions of D10's debugging. And S7.5–S7.7 owns image scanning and signing, which this domain deliberately points at rather than duplicating.
