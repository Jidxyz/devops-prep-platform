# DevOps Interview Skills Question Matrix

**Scoring**

| Score | Meaning |
|---|---|
| 0 | Never done it, or didn't know it existed |
| 1 | Can do it with docs open |
| 2 | Can do it cold, under pressure, and explain why |

Score honestly. A 1 on anything you'd hit in a live exercise is a gap, not a pass.

---

# Domain 1 — Git

## 1. Setup & configuration

| # | Capability | Score | Notes |
|---|---|---|---|
| 1.1 | Configure user, email, editor, and default branch name | | |
| 1.2 | Understand config scopes: system vs global vs local | | |
| 1.3 | Set up and use aliases | | |
| 1.4 | Configure SSH key auth and know how to rotate a key | | |
| 1.5 | Sign commits with GPG or SSH, and verify a signature | | |
| 1.6 | Write a `.gitignore` that actually works (and know why an already-tracked file keeps showing up) | | |
| 1.7 | Use `.gitattributes` for line endings, diff drivers, or LFS | | |
| 1.8 | Set up Git LFS and know when it's warranted | | |

## 2. Core workflow

| # | Capability | Score | Notes |
|---|---|---|---|
| 2.1 | Explain working directory vs index vs HEAD without hand-waving | | |
| 2.2 | Stage selectively with `add -p` | | |
| 2.3 | Unstage without losing work | | |
| 2.4 | Write a clear commit message, and explain what makes one good | | |
| 2.5 | Amend the last commit (message and content) | | |
| 2.6 | Understand what `.git/` contains at a high level | | |
| 2.7 | Explain the object model: blob, tree, commit, tag | | |

## 3. Branching

| # | Capability | Score | Notes |
|---|---|---|---|
| 3.1 | Create, switch, rename, and delete branches | | |
| 3.2 | Understand `switch`/`restore` vs the older `checkout` | | |
| 3.3 | Track a remote branch and set upstream | | |
| 3.4 | List merged vs unmerged branches and prune stale ones | | |
| 3.5 | Explain a branching strategy (trunk-based, GitFlow, release branches) and pick one for a given team | | |
| 3.6 | Recognise a detached HEAD and get out of it safely | | |
| 3.7 | Create and push tags; explain lightweight vs annotated | | |

## 4. Merging & rebasing

| # | Capability | Score | Notes |
|---|---|---|---|
| 4.1 | Merge a branch and read the resulting history | | |
| 4.2 | Explain fast-forward vs no-ff merge and when to force each | | |
| 4.3 | Rebase a feature branch onto an updated main | | |
| 4.4 | Interactive rebase: squash, fixup, reword, reorder, drop | | |
| 4.5 | Explain the golden rule of rebasing (and when it's safe to break it) | | |
| 4.6 | Argue rebase vs merge for a 20-person team, with tradeoffs | | |
| 4.7 | Use `rerere` to stop re-solving the same conflict | | |
| 4.8 | Squash-merge vs merge commit — know what each does to history and to `git bisect` | | |

## 5. Conflict resolution

| # | Capability | Score | Notes |
|---|---|---|---|
| 5.1 | Read conflict markers and understand which side is which | | |
| 5.2 | Resolve a conflict during merge | | |
| 5.3 | Resolve a conflict during rebase (and know why the sides feel inverted) | | |
| 5.4 | Abort cleanly mid-merge or mid-rebase | | |
| 5.5 | Use `checkout --ours` / `--theirs` deliberately | | |
| 5.6 | Use a merge tool or 3-way diff view | | |
| 5.7 | Resolve a conflict in a lockfile or generated file (regenerate, don't hand-merge) | | |

## 6. Undo & recovery

| # | Capability | Score | Notes |
|---|---|---|---|
| 6.1 | Explain `reset --soft` vs `--mixed` vs `--hard` precisely | | |
| 6.2 | Revert a commit on a shared branch and explain why revert, not reset | | |
| 6.3 | Recover a lost commit or branch via reflog | | |
| 6.4 | Recover a deleted file from an earlier commit | | |
| 6.5 | Recover uncommitted work after a bad `reset --hard` (and know when you can't) | | |
| 6.6 | Undo a bad rebase using `ORIG_HEAD` or reflog | | |
| 6.7 | Remove a secret from history and understand the blast radius | | |
| 6.8 | Clean untracked files safely (`clean -n` before `-fd`) | | |

## 7. Inspection & investigation

| # | Capability | Score | Notes |
|---|---|---|---|
| 7.1 | Use `log` with useful flags: `--oneline`, `--graph`, `--since`, `-S` | | |
| 7.2 | Diff working tree vs index vs a given commit | | |
| 7.3 | Use `blame` to trace a line's origin | | |
| 7.4 | Use `bisect` to find a breaking commit | | |
| 7.5 | Automate bisect with a test script (`bisect run`) | | |
| 7.6 | Search history for when a string was added or removed | | |
| 7.7 | Show a file's full history including renames (`log --follow`) | | |
| 7.8 | Inspect an arbitrary object with `cat-file` / `show` | | |

## 8. Remotes & collaboration

| # | Capability | Score | Notes |
|---|---|---|---|
| 8.1 | Add, rename, and inspect remotes | | |
| 8.2 | Explain `fetch` vs `pull`, and why `fetch` first is usually right | | |
| 8.3 | Configure `pull.rebase` and explain the choice | | |
| 8.4 | Force-push safely with `--force-with-lease`, and explain the difference from `--force` | | |
| 8.5 | Recover a branch after someone else force-pushed over your work | | |
| 8.6 | Clone shallow / partial for large repos, and know the tradeoffs | | |
| 8.7 | Work with a fork: add upstream, sync, push to your own remote | | |

## 9. Stash & housekeeping

| # | Capability | Score | Notes |
|---|---|---|---|
| 9.1 | Stash and reapply work | | |
| 9.2 | Stash with a message and apply a specific stash | | |
| 9.3 | Stash including untracked files | | |
| 9.4 | Explain `apply` vs `pop` and when the difference bites | | |
| 9.5 | Understand `gc`, loose vs packed objects, repo size | | |
| 9.6 | Use worktrees to work on two branches at once | | |

## 10. Advanced / situational

| # | Capability | Score | Notes |
|---|---|---|---|
| 10.1 | Cherry-pick a commit, and a range of commits | | |
| 10.2 | Resolve a cherry-pick conflict and know when to abort | | |
| 10.3 | Use submodules: add, clone with, update, and explain the pain | | |
| 10.4 | Use subtree as an alternative, and know when it's better | | |
| 10.5 | Write a client-side hook (pre-commit, commit-msg) | | |
| 10.6 | Set up pre-commit framework hooks across a team | | |
| 10.7 | Explain what a server-side hook can enforce that a client-side one can't | | |
| 10.8 | Enforce conventional commits and drive a changelog from them | | |
| 10.9 | Use `filter-repo` (not `filter-branch`) for history rewriting | | |
| 10.10 | Explain how Git stores history efficiently (packfiles, deltas) | | |

---

## Git — scoring summary

| Section | Items | Score /2 each | Total | % |
|---|---|---|---|---|
| 1. Setup & configuration | 8 | | /16 | |
| 2. Core workflow | 7 | | /14 | |
| 3. Branching | 7 | | /14 | |
| 4. Merging & rebasing | 8 | | /16 | |
| 5. Conflict resolution | 7 | | /14 | |
| 6. Undo & recovery | 8 | | /16 | |
| 7. Inspection & investigation | 8 | | /16 | |
| 8. Remotes & collaboration | 7 | | /14 | |
| 9. Stash & housekeeping | 6 | | /12 | |
| 10. Advanced / situational | 10 | | /20 | |
| **Total** | **76** | | **/152** | |

---

# Domain 2 — Linux

Numbering restarts at L to keep references unambiguous (e.g. "Git 6.7" vs "Linux L4.3").

## L1. Filesystem & navigation

| # | Capability | Score | Notes |
|---|---|---|---|
| L1.1 | Navigate, copy, move, and remove files confidently | | |
| L1.2 | Explain the FHS: what lives in `/etc`, `/var`, `/usr`, `/opt`, `/proc`, `/tmp` | | |
| L1.3 | Absolute vs relative paths; understand `.`, `..`, `~`, `-` | | |
| L1.4 | Symlinks vs hard links — create both and explain the difference | | |
| L1.5 | Find files by name, size, age, type (`find` with `-exec`) | | |
| L1.6 | Search file contents recursively (`grep -r`, `rg`) | | |
| L1.7 | Archive and compress: `tar`, `gzip`, `zip` — and extract safely | | |
| L1.8 | Copy files between hosts: `scp`, `rsync` (and know why rsync usually wins) | | |
| L1.9 | Inspect file type and encoding (`file`, `stat`) | | |

## L2. Permissions, users & access

| # | Capability | Score | Notes |
|---|---|---|---|
| L2.1 | Read and set permissions in octal and symbolic form | | |
| L2.2 | Explain the difference between permissions on a file vs a directory | | |
| L2.3 | Change ownership and group (`chown`, `chgrp`) | | |
| L2.4 | Understand and use setuid, setgid, sticky bit | | |
| L2.5 | Manage users and groups; understand `/etc/passwd`, `/etc/shadow`, `/etc/group` | | |
| L2.6 | Configure sudoers safely (`visudo`) and scope privileges narrowly | | |
| L2.7 | Set up SSH key auth; explain `authorized_keys` vs `known_hosts` | | |
| L2.8 | Harden sshd: disable password auth, disable root login, change defaults | | |
| L2.9 | Understand umask and predict the permissions of a new file | | |
| L2.10 | Diagnose "permission denied" that isn't actually file permissions (SELinux/AppArmor) | | |

## L3. Text processing & the shell

| # | Capability | Score | Notes |
|---|---|---|---|
| L3.1 | Pipes and redirection: stdin, stdout, stderr, `2>&1`, `/dev/null` | | |
| L3.2 | Exit codes; `&&`, `||`, `;` and how they differ | | |
| L3.3 | `grep` with regex, context flags, inverted match | | |
| L3.4 | `sed` for substitution and in-place editing | | |
| L3.5 | `awk` for field extraction and simple aggregation | | |
| L3.6 | `cut`, `sort`, `uniq -c`, `tr`, `wc`, `head`, `tail` | | |
| L3.7 | `jq` for parsing and reshaping JSON | | |
| L3.8 | `yq` for YAML (manifests, pipelines, configs) | | |
| L3.9 | `xargs` — including `-0`, `-n`, `-P` for parallelism | | |
| L3.10 | Build a one-liner that answers a real question from a log file | | |
| L3.11 | Command substitution, quoting rules, and why unquoted variables bite | | |
| L3.12 | Job control: background, `fg`/`bg`, `nohup`, `screen`/`tmux` | | |

## L4. Processes & signals

| # | Capability | Score | Notes |
|---|---|---|---|
| L4.1 | Inspect processes: `ps aux`, `ps -ef`, `pgrep` | | |
| L4.2 | Read `top`/`htop` and interpret each column | | |
| L4.3 | Explain the common signals: TERM, KILL, HUP, INT — and when each is right | | |
| L4.4 | Kill a process by name or pattern; know why `-9` is a last resort | | |
| L4.5 | Explain the process tree, PID 1, orphans and zombies | | |
| L4.6 | Understand nice / renice and process priority | | |
| L4.7 | Find what's holding a file or port open (`lsof`, `fuser`) | | |
| L4.8 | Trace syscalls on a misbehaving process (`strace`, basic use) | | |
| L4.9 | Explain what the OOM killer does and find evidence it fired | | |

## L5. Resources & performance

| # | Capability | Score | Notes |
|---|---|---|---|
| L5.1 | Interpret load average correctly relative to core count | | |
| L5.2 | Read memory usage: `free -h`, and explain buffers/cache vs available | | |
| L5.3 | Distinguish CPU-bound, memory-bound, and IO-bound symptoms | | |
| L5.4 | Check IO pressure: `iostat`, `iotop` | | |
| L5.5 | Check per-process resource usage over time | | |
| L5.6 | Understand swap: when it helps, when it signals a problem | | |
| L5.7 | Read `/proc/<pid>/` for live process detail | | |
| L5.8 | Walk a structured method for "the box is slow" rather than guessing | | |

## L6. Disk & storage

| # | Capability | Score | Notes |
|---|---|---|---|
| L6.1 | Check free space (`df -h`) and find what's consuming it (`du`, `ncdu`) | | |
| L6.2 | Diagnose "disk full" when `df` says there's space (inodes, deleted-but-open files) | | |
| L6.3 | List block devices and partitions (`lsblk`, `fdisk -l`) | | |
| L6.4 | Format, mount, and unmount a filesystem | | |
| L6.5 | Configure a persistent mount in `/etc/fstab` without bricking boot | | |
| L6.6 | Grow a filesystem after expanding an underlying volume (e.g. EBS) | | |
| L6.7 | Understand LVM basics: PV, VG, LV | | |
| L6.8 | Configure and verify log rotation (`logrotate`) | | |

## L7. Services & systemd

| # | Capability | Score | Notes |
|---|---|---|---|
| L7.1 | Start, stop, restart, enable, disable a service | | |
| L7.2 | Read service status and interpret the failure output | | |
| L7.3 | Write a systemd unit file from scratch | | |
| L7.4 | Understand unit types: service, timer, socket, target | | |
| L7.5 | Configure restart policies and understand restart storms | | |
| L7.6 | Override a vendor unit with a drop-in rather than editing it | | |
| L7.7 | Explain the boot sequence at a level useful for debugging | | |
| L7.8 | Diagnose a service that starts then immediately exits | | |

## L8. Scheduling

| # | Capability | Score | Notes |
|---|---|---|---|
| L8.1 | Write a crontab entry and read the five fields correctly | | |
| L8.2 | Debug a cron job that works manually but not on schedule (env, PATH) | | |
| L8.3 | Write a systemd timer and explain why you'd prefer it to cron | | |
| L8.4 | Handle overlapping runs and locking (`flock`) | | |

## L9. Logging & troubleshooting

| # | Capability | Score | Notes |
|---|---|---|---|
| L9.1 | Query `journalctl` by unit, time window, and priority | | |
| L9.2 | Know what lives where in `/var/log` on a given distro | | |
| L9.3 | Follow and filter a live log (`tail -f` piped to grep) | | |
| L9.4 | Read `dmesg` for kernel and hardware-level events | | |
| L9.5 | Correlate a timestamp across multiple logs during an incident | | |
| L9.6 | Explain how logs get off the box and into a central system | | |

## L10. Packages & software

| # | Capability | Score | Notes |
|---|---|---|---|
| L10.1 | Install, update, remove packages with apt and yum/dnf | | |
| L10.2 | Find which package owns a file, and what a package installed | | |
| L10.3 | Pin or hold a version, and explain when that's warranted | | |
| L10.4 | Add a third-party repo and verify its signing key | | |
| L10.5 | Install from source or a tarball when no package exists | | |
| L10.6 | Explain how `$PATH` resolution works and debug a wrong-binary problem | | |

## L11. Shell scripting

| # | Capability | Score | Notes |
|---|---|---|---|
| L11.1 | Write a script with a shebang, made executable, that takes arguments | | |
| L11.2 | Use `set -euo pipefail` and explain what each flag prevents | | |
| L11.3 | Conditionals, loops, and case statements | | |
| L11.4 | Functions, local variables, and return values | | |
| L11.5 | Validate input and fail with a useful message and exit code | | |
| L11.6 | Trap signals for cleanup (`trap ... EXIT`) | | |
| L11.7 | Handle spaces and special characters in filenames safely | | |
| L11.8 | Write to a temp file safely (`mktemp`) | | |
| L11.9 | Parse flags (`getopts`) rather than positional-only | | |
| L11.10 | Lint a script with `shellcheck` and fix what it finds | | |
| L11.11 | Know when the script should have been Python instead | | |

## L12. Host-level networking

> Protocol depth belongs in the Networking domain. These are the host-side skills.

| # | Capability | Score | Notes |
|---|---|---|---|
| L12.1 | Inspect interfaces and addresses (`ip addr`) | | |
| L12.2 | Read the routing table (`ip route`) | | |
| L12.3 | List listening sockets and owning processes (`ss -tulpn`) | | |
| L12.4 | Understand host name resolution order (`/etc/hosts`, `resolv.conf`, nsswitch) | | |
| L12.5 | Configure or inspect a host firewall (`iptables`/`nftables`/`ufw`) | | |
| L12.6 | Use SSH tunnels and port forwarding | | |
| L12.7 | Configure `~/.ssh/config` for jump hosts and bastions | | |

---

## Linux — scoring summary

| Section | Items | Score /2 each | Total | % |
|---|---|---|---|---|
| L1. Filesystem & navigation | 9 | | /18 | |
| L2. Permissions, users & access | 10 | | /20 | |
| L3. Text processing & the shell | 12 | | /24 | |
| L4. Processes & signals | 9 | | /18 | |
| L5. Resources & performance | 8 | | /16 | |
| L6. Disk & storage | 8 | | /16 | |
| L7. Services & systemd | 8 | | /16 | |
| L8. Scheduling | 4 | | /8 | |
| L9. Logging & troubleshooting | 6 | | /12 | |
| L10. Packages & software | 6 | | /12 | |
| L11. Shell scripting | 11 | | /22 | |
| L12. Host-level networking | 7 | | /14 | |
| **Total** | **98** | | **/196** | |

---

# Domain 3 — Networking

Prefixed `N`. Host-side commands (interfaces, routing table, `ss`, host firewall, SSH tunnels) live in Linux L12 — this domain is protocol depth and fault isolation.

## N1. Fundamentals

| # | Capability | Score | Notes |
|---|---|---|---|
| N1.1 | Explain the TCP/IP layers well enough to locate a fault at the right layer | | |
| N1.2 | Walk end-to-end what happens when you type a URL and press enter | | |
| N1.3 | Explain encapsulation: what each layer wraps and unwraps | | |
| N1.4 | Distinguish MAC vs IP addressing and where each is used | | |
| N1.5 | Explain what ARP does and when it matters to you | | |
| N1.6 | Explain MTU and the symptoms of fragmentation / PMTU blackholes | | |

## N2. Addressing & subnetting

| # | Capability | Score | Notes |
|---|---|---|---|
| N2.1 | Read CIDR notation and state the usable host range | | |
| N2.2 | Subnet a range by hand under time pressure, no calculator | | |
| N2.3 | Know the RFC1918 private ranges by heart | | |
| N2.4 | Split a VPC CIDR into public/private subnets across AZs, sized sensibly | | |
| N2.5 | Diagnose an overlapping-CIDR problem between two networks | | |
| N2.6 | Explain why AWS reserves five addresses per subnet | | |
| N2.7 | Basic IPv6 literacy: notation, why it exists, dual-stack implications | | |

## N3. Routing & switching

| # | Capability | Score | Notes |
|---|---|---|---|
| N3.1 | Read a routing table and predict which route wins | | |
| N3.2 | Explain longest-prefix match | | |
| N3.3 | Explain default gateway and what a `0.0.0.0/0` route does | | |
| N3.4 | Explain NAT, and the difference between SNAT and DNAT | | |
| N3.5 | Explain public vs private addressing and how a private host reaches the internet | | |
| N3.6 | Trace a path and interpret the output (`traceroute`, `mtr`) | | |
| N3.7 | Explain why traceroute output has gaps without concluding it's broken | | |
| N3.8 | Know what VLANs and broadcast domains are at a working level | | |
| N3.9 | Explain asymmetric routing and why it breaks stateful firewalls | | |

## N4. DNS

| # | Capability | Score | Notes |
|---|---|---|---|
| N4.1 | Explain resolution end to end: stub resolver, recursive, root, TLD, authoritative | | |
| N4.2 | Use `dig` and read the answer, authority, and additional sections | | |
| N4.3 | Query a specific nameserver and compare answers (`dig @ns`) | | |
| N4.4 | Know the record types and their use: A, AAAA, CNAME, ALIAS, MX, TXT, NS, SRV, CAA | | |
| N4.5 | Explain why a CNAME can't sit at a zone apex, and the cloud workaround | | |
| N4.6 | Reason about TTL and plan a cutover around it | | |
| N4.7 | Diagnose stale DNS: negative caching, resolver cache, application-level caching | | |
| N4.8 | Explain split-horizon / private DNS and when you need it | | |
| N4.9 | Explain how a JVM or app runtime can cache DNS past TTL and cause an outage | | |
| N4.10 | Configure health-check-based failover routing | | |

## N5. Transport layer

| # | Capability | Score | Notes |
|---|---|---|---|
| N5.1 | Explain the TCP three-way handshake and connection teardown | | |
| N5.2 | Distinguish the failure signatures: connection refused vs timeout vs reset | | |
| N5.3 | Explain what each of those tells you about where the fault is | | |
| N5.4 | Explain TCP states, especially TIME_WAIT and CLOSE_WAIT, and what a pile-up means | | |
| N5.5 | Explain keepalives, and why idle connections die behind NAT gateways and LBs | | |
| N5.6 | Explain ephemeral port exhaustion and how to spot it | | |
| N5.7 | Explain when UDP is the right choice and what you give up | | |
| N5.8 | Test a specific port from a host (`nc -zv`, `/dev/tcp`) | | |
| N5.9 | Explain backlog / accept queue and what happens when it fills | | |

## N6. HTTP & the application layer

| # | Capability | Score | Notes |
|---|---|---|---|
| N6.1 | Use `curl -v` and read the full request/response exchange | | |
| N6.2 | Break down request timing (`curl -w`) to isolate DNS vs connect vs TLS vs server | | |
| N6.3 | Interpret status codes precisely — especially 4xx vs 5xx ownership, 502 vs 503 vs 504 | | |
| N6.4 | Explain the headers that matter: Host, Content-Type, Authorization, Cache-Control, X-Forwarded-For | | |
| N6.5 | Explain keep-alive, connection reuse, and connection pooling | | |
| N6.6 | Explain what HTTP/2 changed, and what HTTP/3 / QUIC changes again | | |
| N6.7 | Explain CORS well enough to debug a browser failure | | |
| N6.8 | Explain idempotency and safe retry behaviour per method | | |
| N6.9 | Debug a websocket or long-lived connection through a proxy | | |

## N7. TLS & certificates

| # | Capability | Score | Notes |
|---|---|---|---|
| N7.1 | Explain the TLS handshake at a level useful for debugging | | |
| N7.2 | Inspect a live endpoint's certificate (`openssl s_client`) | | |
| N7.3 | Explain the chain of trust: leaf, intermediate, root | | |
| N7.4 | Diagnose a missing intermediate — works in a browser, fails in curl | | |
| N7.5 | Explain SNI and why it matters for multi-tenant hosts | | |
| N7.6 | Check expiry and set up alerting before it bites | | |
| N7.7 | Explain SAN vs CN and wildcard cert limits | | |
| N7.8 | Explain TLS termination vs passthrough vs re-encryption at a load balancer | | |
| N7.9 | Explain mTLS and where you'd require it | | |
| N7.10 | Explain how ACM / Let's Encrypt validation and renewal actually work | | |

## N8. Load balancing & proxies

| # | Capability | Score | Notes |
|---|---|---|---|
| N8.1 | Explain L4 vs L7 load balancing and choose between them | | |
| N8.2 | Explain forward proxy vs reverse proxy | | |
| N8.3 | Configure health checks and explain the failure modes of a bad one | | |
| N8.4 | Explain connection draining / deregistration delay | | |
| N8.5 | Explain sticky sessions and why you'd rather avoid them | | |
| N8.6 | Trace a client IP through layers of proxying (X-Forwarded-For, PROXY protocol) | | |
| N8.7 | Explain where TLS should terminate in a given architecture, and why | | |
| N8.8 | Explain the common balancing algorithms and when round-robin is wrong | | |

## N9. Diagnostics & fault isolation

| # | Capability | Score | Notes |
|---|---|---|---|
| N9.1 | Work a "can't connect" fault methodically layer by layer rather than guessing | | |
| N9.2 | Distinguish a DNS problem from a routing problem from a firewall problem from an app problem | | |
| N9.3 | Capture traffic with `tcpdump` using a useful filter | | |
| N9.4 | Read a capture: identify SYN with no SYN-ACK, retransmits, resets | | |
| N9.5 | Open a capture in Wireshark and follow a stream | | |
| N9.6 | Explain what `ping` failing does and doesn't prove | | |
| N9.7 | Diagnose intermittent failure — one unhealthy backend behind an LB | | |
| N9.8 | Use flow logs to prove whether traffic arrived and whether it was accepted | | |
| N9.9 | Localise a fault to a specific hop or security control and state your evidence | | |

## N10. Cloud & overlay networking

> AWS-specific service configuration lives in the AWS domain; this is the networking reasoning behind it.

| # | Capability | Score | Notes |
|---|---|---|---|
| N10.1 | Explain security groups vs NACLs: stateful vs stateless, and the debugging implications | | |
| N10.2 | Explain the traffic path from internet to a private instance and back | | |
| N10.3 | Explain NAT gateway vs internet gateway, and the cost profile of each | | |
| N10.4 | Explain VPC endpoints (gateway vs interface) and when they pay for themselves | | |
| N10.5 | Explain VPC peering vs Transit Gateway and the scaling tradeoff | | |
| N10.6 | Explain site-to-site VPN vs Direct Connect at a decision level | | |
| N10.7 | Explain how container networking differs — overlay networks, per-pod IPs, ENI limits | | |
| N10.8 | Explain service discovery in a dynamic environment | | |
| N10.9 | Explain egress control and why it matters for compliance | | |

---

## Networking — scoring summary

| Section | Items | Score /2 each | Total | % |
|---|---|---|---|---|
| N1. Fundamentals | 6 | | /12 | |
| N2. Addressing & subnetting | 7 | | /14 | |
| N3. Routing & switching | 9 | | /18 | |
| N4. DNS | 10 | | /20 | |
| N5. Transport layer | 9 | | /18 | |
| N6. HTTP & application layer | 9 | | /18 | |
| N7. TLS & certificates | 10 | | /20 | |
| N8. Load balancing & proxies | 8 | | /16 | |
| N9. Diagnostics & fault isolation | 9 | | /18 | |
| N10. Cloud & overlay networking | 9 | | /18 | |
| **Total** | **86** | | **/172** | |

---

# Domain 4 — AWS

Prefixed `A`. Networking *reasoning* lives in Domain 3 (N10); this domain is service configuration and operational decisions.

**Tiering.** Not everything needs scoring. Each section is marked:

- **T1** — expected in essentially any DevOps/platform interview. Score every item.
- **T2** — score if it's in your target JD or your day-to-day stack.
- **T3** — awareness only. Know what it is and when you'd reach for it; don't burn prep time going deep.

**Deliberately not assessed:** SageMaker, Redshift, EMR, Glue, AppSync, Amplify, IoT, Connect, Media services, Snow family, Outposts. Add one only if a specific JD names it.

## A1. Account structure & identity — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A1.1 | Explain multi-account strategy and why you'd separate prod/non-prod/security/logging | | |
| A1.2 | Explain AWS Organizations: OUs, root, member accounts | | |
| A1.3 | Write and reason about a Service Control Policy, and explain how it differs from an IAM policy | | |
| A1.4 | Explain IAM Identity Center (SSO) vs IAM users, and why IAM users are a smell | | |
| A1.5 | Design permission sets and map them to groups from an external IdP | | |
| A1.6 | Configure and troubleshoot federation from an external IdP (Okta, Entra, Google) | | |
| A1.7 | Explain cross-account role assumption end to end, including the trust policy | | |
| A1.8 | Explain the External ID and confused-deputy problem for third-party access | | |
| A1.9 | Explain what a landing zone is and the components it must provide | | |
| A1.10 | Explain Control Tower vs a custom landing zone, and the tradeoff | | |
| A1.11 | Explain Control Tower guardrails: preventive vs detective, mandatory vs elective | | |
| A1.12 | Design a baseline OU structure and justify the separation | | |
| A1.13 | Explain account vending / factory and automated account provisioning | | |
| A1.14 | Explain how you'd onboard a new account into an existing org with guardrails intact | | |
| A1.15 | Explain how you'd retrofit governance onto accounts created before the landing zone | | |
| A1.16 | Explain centralised logging and the security/log archive account pattern | | |
| A1.17 | Explain delegated administration for org-level services | | |

## A2. IAM — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A2.1 | Distinguish identity-based, resource-based, and permissions boundaries | | |
| A2.2 | Write a least-privilege policy from scratch for a stated requirement | | |
| A2.3 | Walk the policy evaluation logic: explicit deny, SCP, boundary, session policy, allow | | |
| A2.4 | Debug "access denied" methodically using the error, CloudTrail, and the policy simulator | | |
| A2.5 | Use conditions effectively (`aws:SourceIp`, `aws:PrincipalTag`, `aws:RequestTag`) | | |
| A2.6 | Explain instance profiles and how a workload gets credentials without keys | | |
| A2.7 | Explain IRSA / Pod Identity for EKS workloads | | |
| A2.8 | Configure OIDC federation from GitHub Actions to AWS with no long-lived keys | | |
| A2.9 | Explain the risk of `iam:PassRole` and privilege escalation paths | | |
| A2.10 | Use Access Analyzer and last-accessed data to right-size existing permissions | | |
| A2.11 | Explain how you'd audit and remove unused credentials across an org | | |

## A3. VPC, connectivity & hybrid — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A3.1 | Build a VPC: subnets across AZs, route tables, IGW, NAT | | |
| A3.2 | Configure security groups and NACLs, and know which to reach for | | |
| A3.3 | Configure VPC endpoints and justify them on cost or compliance grounds | | |
| A3.4 | Set up VPC peering or Transit Gateway and explain the choice | | |
| A3.5 | Read VPC flow logs to prove whether traffic was accepted or rejected | | |
| A3.6 | Set up Route53 Resolver / private hosted zones for cross-account name resolution | | |
| A3.7 | Design a bastion-free access pattern (SSM Session Manager) | | |
| A3.8 | Plan VPC CIDR allocation across an org without overlap | | |
| A3.9 | Use VPC IPAM: pools, scopes, allocation rules, and monitoring utilisation | | |
| A3.10 | Explain what IPAM solves that a spreadsheet of CIDRs doesn't | | |
| A3.11 | Configure a site-to-site VPN: customer gateway, tunnels, BGP vs static | | |
| A3.12 | Explain Direct Connect: virtual interfaces, LAG, and why you still want a VPN backup | | |
| A3.13 | Explain Transit Gateway route tables and attachment propagation | | |
| A3.14 | Design hybrid DNS resolution: Route53 Resolver inbound/outbound endpoints and forwarding rules | | |
| A3.15 | Debug on-prem to AWS connectivity across the full path (routing, BGP, SG, NACL, DNS) | | |
| A3.16 | Explain overlapping on-prem and AWS address space and the options for resolving it | | |

## A4. Compute — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A4.1 | Launch and configure EC2: AMIs, instance profiles, user data, EBS | | |
| A4.2 | Choose an instance family for a stated workload and justify it | | |
| A4.3 | Configure Auto Scaling groups, launch templates, and scaling policies | | |
| A4.4 | Explain health checks and instance replacement behaviour in an ASG | | |
| A4.5 | Explain Spot vs On-Demand vs Reserved vs Savings Plans, and where Spot is safe | | |
| A4.6 | Build a golden AMI pipeline and explain why you'd bother | | |
| A4.7 | Write a Lambda and configure its trigger, IAM role, and timeout | | |
| A4.8 | Explain Lambda cold starts, concurrency limits, and VPC-attached tradeoffs | | |
| A4.9 | Use SSM: Session Manager, Run Command, Patch Manager | | |

## A5. Containers — T1 (see also the Containers / Kubernetes domains)

| # | Capability | Score | Notes |
|---|---|---|---|
| A5.1 | Push to and manage ECR: lifecycle policies, scanning, cross-account pull | | |
| A5.2 | Write an ECS task definition and configure a service | | |
| A5.3 | Explain Fargate vs EC2 launch type tradeoffs | | |
| A5.4 | Deploy and roll back an ECS service; debug a task that won't start | | |
| A5.5 | Provision EKS and explain managed node groups vs Fargate vs Karpenter | | |
| A5.6 | Configure the AWS load balancer controller and expose a service | | |
| A5.7 | Explain the VPC CNI and ENI-per-pod IP exhaustion | | |
| A5.8 | Explain how EKS authenticates: aws-auth vs access entries | | |

## A6. Storage — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A6.1 | Configure S3: bucket policies, versioning, lifecycle rules | | |
| A6.2 | Explain the storage classes and pick one for a stated access pattern | | |
| A6.3 | Explain S3 encryption options: SSE-S3, SSE-KMS, SSE-C, and bucket keys | | |
| A6.4 | Block public access correctly and explain how buckets get exposed by accident | | |
| A6.5 | Explain S3 consistency, prefixes, and request-rate scaling | | |
| A6.6 | Use presigned URLs and explain the security tradeoff | | |
| A6.7 | Configure cross-region replication and explain the use case | | |
| A6.8 | Choose between EBS volume types; snapshot, restore, and resize | | |
| A6.9 | Explain when EFS is the right answer and when it's a performance trap | | |

## A7. Databases — T2

| # | Capability | Score | Notes |
|---|---|---|---|
| A7.1 | Provision RDS with multi-AZ; explain failover behaviour and downtime | | |
| A7.2 | Explain read replicas vs multi-AZ — different problems, commonly confused | | |
| A7.3 | Configure backups, retention, and point-in-time recovery; test a restore | | |
| A7.4 | Explain Aurora's architecture difference and when it's worth it | | |
| A7.5 | Explain parameter groups and perform a low-risk engine upgrade | | |
| A7.6 | Explain DynamoDB partition keys, hot partitions, and capacity modes | | |
| A7.7 | Use ElastiCache appropriately and explain the cache invalidation risk | | |
| A7.8 | Rotate database credentials without downtime | | |

## A8. DNS & edge — T1 for Route53, T2 for the rest

| # | Capability | Score | Notes |
|---|---|---|---|
| A8.1 | Manage hosted zones and records; delegate a subdomain | | |
| A8.2 | Use alias records and explain why they beat CNAMEs for AWS targets | | |
| A8.3 | Configure routing policies: weighted, latency, failover, geolocation | | |
| A8.4 | Configure health checks and design a DNS-based failover | | |
| A8.5 | Plan a zero-downtime DNS cutover accounting for TTL and client caching | | |
| A8.6 | Issue and attach ACM certificates; explain validation and auto-renewal failure modes | | |
| A8.7 | Configure CloudFront: origins, behaviours, cache keys, invalidation | | |
| A8.8 | Configure WAF rules and explain what it does and doesn't protect against | | |
| A8.9 | Explain Global Accelerator vs CloudFront | | |

## A9. Observability — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A9.1 | Ship application and system logs to CloudWatch Logs | | |
| A9.2 | Write a CloudWatch Logs Insights query to answer a real incident question | | |
| A9.3 | Create metrics, including custom and metric-filter-derived metrics | | |
| A9.4 | Design an alarm that alerts on symptoms, not noise; explain composite alarms | | |
| A9.5 | Explain CloudTrail: management vs data events, and use it to answer "who did this" | | |
| A9.6 | Set up an organisation trail with a central, tamper-resistant log account | | |
| A9.7 | Use EventBridge to react to an AWS event | | |
| A9.8 | Explain distributed tracing and where X-Ray or OTel fits | | |
| A9.9 | Explain log retention, cost control, and when to route to S3 instead | | |

## A10. Encryption, secrets & security services — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A10.1 | Explain KMS key types: AWS-owned, AWS-managed, customer-managed — and when the extra cost of a CMK is justified | | |
| A10.2 | Explain envelope encryption: data keys, plaintext vs encrypted data key, why it exists | | |
| A10.3 | Explain how a key policy, IAM policy, and grant combine to authorise a KMS operation | | |
| A10.4 | Debug a KMS access denied and identify whether the key policy or the IAM policy is the blocker | | |
| A10.5 | Explain the risk of a key policy that locks out all administrators | | |
| A10.6 | Configure key rotation; explain what rotates, what doesn't, and what happens to old ciphertext | | |
| A10.7 | Explain key deletion: the mandatory waiting period, and why disabling is usually the right first move | | |
| A10.8 | Use aliases and explain why you reference an alias rather than a key ID | | |
| A10.9 | Explain grants and where they're used instead of policy changes | | |
| A10.10 | Explain encryption context and its role in authorisation and auditing | | |
| A10.11 | Explain multi-region keys and cross-account key usage | | |
| A10.12 | Encrypt an existing unencrypted resource (RDS, EBS, S3) and explain the migration path | | |
| A10.13 | Explain cross-region snapshot copy and the re-encryption step it requires | | |
| A10.14 | Explain KMS request costs and how bucket keys or data key caching reduce them | | |
| A10.15 | Explain KMS quotas as an availability risk under high request volume | | |
| A10.16 | Audit key usage via CloudTrail and answer "what decrypted this, and when" | | |
| A10.17 | Explain when CloudHSM or imported key material (BYOK) is actually required | | |
| A10.18 | Explain ACM Private CA and internal certificate issuance at a decision level | | |
| A10.19 | Use Secrets Manager: storage, retrieval, automatic rotation | | |
| A10.20 | Explain Secrets Manager vs Parameter Store and choose on cost and features | | |
| A10.21 | Get secrets into a container or Lambda without baking them into an image | | |
| A10.22 | Explain GuardDuty: what it detects, its data sources, and how you triage a finding | | |
| A10.23 | Explain AWS Config: resource inventory, configuration history, and drift detection | | |
| A10.24 | Write a Config rule or conformance pack to enforce a standard | | |
| A10.25 | Explain Security Hub's role as an aggregator, and its relationship to Config and GuardDuty | | |
| A10.26 | Enable Security Hub org-wide with a delegated admin and aggregated findings | | |
| A10.27 | Explain the standards (CIS, AWS FSBP, PCI) and how you'd act on a low score | | |
| A10.28 | Suppress or accept a finding with a documented justification rather than ignoring it | | |
| A10.29 | Route findings to a ticket or alert rather than a dashboard nobody reads | | |
| A10.30 | Respond to a leaked-credential scenario: revoke, rotate, assess blast radius | | |
| A10.31 | Explain encryption in transit and at rest for a given service, and prove it's on | | |

## A11. Resilience & DR — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A11.1 | Define RTO and RPO and set them from business requirements, not gut feel | | |
| A11.2 | Explain the DR strategies: backup/restore, pilot light, warm standby, active-active | | |
| A11.3 | Cost each strategy and recommend one with the tradeoff stated | | |
| A11.4 | Design multi-AZ HA for a stated workload | | |
| A11.5 | Explain what multi-region actually costs you in complexity, data, and consistency | | |
| A11.6 | Explain how an AZ failure manifests and what fails over automatically vs manually | | |
| A11.7 | Use AWS Backup for centralised, cross-account backup policy | | |
| A11.8 | Explain how you'd actually test DR rather than assume it works | | |
| A11.9 | Explain quotas and limits as an availability risk | | |

## A12. Cost — T2, but disproportionately valued

| # | Capability | Score | Notes |
|---|---|---|---|
| A12.1 | Use Cost Explorer to attribute spend and find an anomaly | | |
| A12.2 | Design a tagging strategy and enforce it | | |
| A12.3 | Name the usual top spend drivers and the usual quick wins | | |
| A12.4 | Explain data transfer charges: cross-AZ, cross-region, NAT, egress | | |
| A12.5 | Explain Savings Plans vs Reserved Instances and recommend a commitment level | | |
| A12.6 | Set up budgets, anomaly detection, and alerting | | |
| A12.7 | Tell a cost-reduction story with a number attached and no reliability regression | | |

## A13. Messaging & integration — T2

| # | Capability | Score | Notes |
|---|---|---|---|
| A13.1 | Explain SQS: visibility timeout, dead-letter queues, standard vs FIFO | | |
| A13.2 | Explain SNS and fan-out patterns | | |
| A13.3 | Explain EventBridge rules, buses, and schema | | |
| A13.4 | Choose between SQS, SNS, EventBridge, and Kinesis for a stated problem | | |
| A13.5 | Explain idempotency and at-least-once delivery implications | | |
| A13.6 | Explain Step Functions and when orchestration beats choreography | | |

## A14. Access & tooling — T1

| # | Capability | Score | Notes |
|---|---|---|---|
| A14.1 | Use the CLI fluently: profiles, SSO login, assume-role, `--query`, pagination | | |
| A14.2 | Configure `~/.aws/config` for multi-account SSO cleanly | | |
| A14.3 | Explain the credential provider chain and debug "which credentials am I using" | | |
| A14.4 | Use the SDK (boto3) for something the CLI can't do neatly | | |
| A14.5 | Explain how CloudFormation / CDK / Terraform differ in state and drift handling | | |
| A14.6 | Explain regional vs global services and the implications for failover | | |

## A15. Awareness only — T3

Know what it is, what problem it solves, and when you'd reach for it. One line each; don't score in depth.

| # | Service | Know it? | Notes |
|---|---|---|---|
| A15.1 | API Gateway | | |
| A15.2 | CloudFormation StackSets | | |
| A15.3 | CodePipeline / CodeBuild / CodeDeploy | | |
| A15.4 | App Runner, Lightsail, Elastic Beanstalk | | |
| A15.5 | Athena | | |
| A15.6 | Kinesis / MSK | | |
| A15.7 | Service Catalog | | |
| A15.8 | Resource Access Manager (RAM) | | |
| A15.9 | Inspector, Macie, Detective | | |
| A15.10 | Fault Injection Service | | |
| A15.11 | Bedrock (T1 if targeting AI platform roles) | | |

---

## AWS — scoring summary

| Section | Tier | Items | Total | % |
|---|---|---|---|---|
| A1. Account structure & identity | T1 | 17 | /34 | |
| A2. IAM | T1 | 11 | /22 | |
| A3. VPC, connectivity & hybrid | T1 | 16 | /32 | |
| A4. Compute | T1 | 9 | /18 | |
| A5. Containers | T1 | 8 | /16 | |
| A6. Storage | T1 | 9 | /18 | |
| A7. Databases | T2 | 8 | /16 | |
| A8. DNS & edge | T1/T2 | 9 | /18 | |
| A9. Observability | T1 | 9 | /18 | |
| A10. Encryption, secrets & security | T1 | 31 | /62 | |
| A11. Resilience & DR | T1 | 9 | /18 | |
| A12. Cost | T2 | 7 | /14 | |
| A13. Messaging & integration | T2 | 6 | /12 | |
| A14. Access & tooling | T1 | 6 | /12 | |
| **Tier 1 subtotal** | | **125** | **/250** | |
| **Full total (excl. T3)** | | **155** | **/310** | |

---

# Domain 5 — Troubleshooting & Incident Response

Prefixed `T`. Cross-cutting. Tool-specific debugging lives in each domain (Networking N9 is the closest sibling); this domain is method, judgement, and the human half of an incident.

## T1. Diagnostic method

| # | Capability | Score | Notes |
|---|---|---|---|
| T1.1 | State the problem precisely before touching anything — what changed, what's the actual symptom, who's affected | | |
| T1.2 | Form a hypothesis and design the cheapest test that would disprove it | | |
| T1.3 | Bisect the problem space rather than checking components in arbitrary order | | |
| T1.4 | Distinguish correlation from causation when a deploy coincides with a failure | | |
| T1.5 | Recognise when you're pattern-matching to a past incident and check the assumption | | |
| T1.6 | Change one thing at a time, and know when the outage is severe enough to break that rule | | |
| T1.7 | Know when to stop debugging and mitigate instead | | |
| T1.8 | Work effectively with incomplete information and state your confidence level | | |
| T1.9 | Recognise when you're stuck and hand off or escalate without ego | | |
| T1.10 | Keep a running log of what you tried and what you observed | | |

## T2. Evidence gathering

| # | Capability | Score | Notes |
|---|---|---|---|
| T2.1 | Establish a timeline: when did it start, what else happened then | | |
| T2.2 | Correlate logs, metrics, and traces across systems on a shared timestamp | | |
| T2.3 | Find the last known-good state and what changed since | | |
| T2.4 | Check deploys, config changes, feature flags, and certificate expiries as first-class suspects | | |
| T2.5 | Determine scope: one user, one AZ, one instance, one region, or everyone | | |
| T2.6 | Distinguish "our problem" from an upstream or cloud-provider problem, with evidence | | |
| T2.7 | Capture evidence before restarting something and destroying it | | |
| T2.8 | Reproduce a failure reliably, or explain why you can't | | |

## T3. Common failure patterns

| # | Capability | Score | Notes |
|---|---|---|---|
| T3.1 | Recognise resource exhaustion: disk, memory, file descriptors, connection pools, ephemeral ports | | |
| T3.2 | Recognise a cascading failure and the role of retries and thundering herds | | |
| T3.3 | Recognise a slow dependency causing upstream queue buildup and timeout | | |
| T3.4 | Recognise DNS and certificate expiry as the boring cause of dramatic outages | | |
| T3.5 | Recognise a partial failure — one bad node behind a load balancer | | |
| T3.6 | Recognise a config or secret change rather than a code change | | |
| T3.7 | Recognise capacity and quota limits being hit | | |
| T3.8 | Recognise a clock, timezone, or leap-related problem | | |
| T3.9 | Recognise a "works in staging" difference: data volume, config, permissions, scale | | |
| T3.10 | Diagnose an intermittent failure without a reliable reproduction | | |

## T4. Incident response

| # | Capability | Score | Notes |
|---|---|---|---|
| T4.1 | Classify severity consistently and justify the call | | |
| T4.2 | Assess blast radius early — who is affected and how badly | | |
| T4.3 | Take incident command: assign roles, keep one person deciding | | |
| T4.4 | Decide mitigate-first vs diagnose-first and articulate why | | |
| T4.5 | Decide rollback vs fix-forward and state the risk of each | | |
| T4.6 | Execute a rollback under pressure, having verified it's actually possible | | |
| T4.7 | Use feature flags, traffic shifting, or scaling as mitigation levers | | |
| T4.8 | Know when to declare an incident rather than quietly fixing it | | |
| T4.9 | Know when to wake someone up, and be willing to | | |
| T4.10 | Manage a long incident: handovers, fatigue, avoiding tunnel vision | | |
| T4.11 | Declare an incident resolved with evidence rather than hope | | |

## T5. Communication during an incident

| # | Capability | Score | Notes |
|---|---|---|---|
| T5.1 | Write a status update that says impact, current understanding, next update time | | |
| T5.2 | Communicate to a non-technical stakeholder without minimising or catastrophising | | |
| T5.3 | Keep updating on a cadence even when there's nothing new | | |
| T5.4 | Separate what you know from what you suspect, out loud | | |
| T5.5 | Manage pressure from stakeholders without letting it drive bad technical decisions | | |
| T5.6 | Run a clean handover to the next responder | | |
| T5.7 | Communicate customer impact honestly, including when you don't yet know the extent | | |

## T6. Post-incident

| # | Capability | Score | Notes |
|---|---|---|---|
| T6.1 | Write a postmortem: timeline, impact, contributing factors, actions | | |
| T6.2 | Run a blameless review and mean it | | |
| T6.3 | Get past the first plausible cause to the contributing conditions | | |
| T6.4 | Distinguish a trigger from a latent cause | | |
| T6.5 | Produce actions that are specific, owned, and prioritised — not a wishlist | | |
| T6.6 | Push back on "add more monitoring" as a default action item | | |
| T6.7 | Track actions to completion and notice when they're quietly dropped | | |
| T6.8 | Spot a repeating pattern across multiple incidents and escalate it as systemic | | |

## T7. Prevention & reliability

| # | Capability | Score | Notes |
|---|---|---|---|
| T7.1 | Define SLIs and SLOs that reflect user experience rather than convenient metrics | | |
| T7.2 | Explain error budgets and how they change deployment decisions | | |
| T7.3 | Design alerts on symptoms rather than causes, and defend the choice | | |
| T7.4 | Audit and reduce alert noise; explain the cost of a noisy pager | | |
| T7.5 | Write a runbook someone else can actually follow at 3am | | |
| T7.6 | Explain graceful degradation, circuit breakers, and bulkheads | | |
| T7.7 | Explain retry strategy: backoff, jitter, and retry budgets | | |
| T7.8 | Explain timeouts as a design decision, and the danger of no timeout | | |
| T7.9 | Run or design a game day / chaos experiment | | |
| T7.10 | Design a healthy on-call rotation and explain what makes one unsustainable | | |
| T7.11 | Explain how you'd measure whether reliability is improving | | |

---

## Troubleshooting & Incident Response — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| T1. Diagnostic method | 10 | /20 | |
| T2. Evidence gathering | 8 | /16 | |
| T3. Common failure patterns | 10 | /20 | |
| T4. Incident response | 11 | /22 | |
| T5. Communication during an incident | 7 | /14 | |
| T6. Post-incident | 8 | /16 | |
| T7. Prevention & reliability | 11 | /22 | |
| **Total** | **65** | **/130** | |

---

# Domain 6 — Security, PKI & Certificates

Prefixed `S`. Deliberate overlaps: TLS *debugging* is N7, AWS KMS and secrets *services* are A10, host hardening is L2, IAM is A2. This domain is PKI as a system, certificate lifecycle operations, and security around the delivery pipeline.

## S1. Cryptography fundamentals

Enough to reason about design choices — not enough to implement anything yourself.

| # | Capability | Score | Notes |
|---|---|---|---|
| S1.1 | Distinguish symmetric and asymmetric encryption and where each is used | | |
| S1.2 | Explain hashing vs encryption vs encoding, and why base64 is not security | | |
| S1.3 | Explain digital signatures: what they prove and what they don't | | |
| S1.4 | Explain why passwords are hashed with bcrypt/argon2 rather than SHA-256 | | |
| S1.5 | Explain salting and why it defeats rainbow tables | | |
| S1.6 | Explain forward secrecy and why it matters if a key leaks later | | |
| S1.7 | Know which algorithms are current and which are deprecated (RSA vs ECDSA, SHA-1) | | |
| S1.8 | Explain the rule about never rolling your own crypto, and where the line actually is | | |

## S2. PKI & the trust model

| # | Capability | Score | Notes |
|---|---|---|---|
| S2.1 | Explain what a Certificate Authority is and why anyone trusts one | | |
| S2.2 | Explain the chain of trust: root, intermediate, leaf | | |
| S2.3 | Explain why roots are kept offline and intermediates do the signing | | |
| S2.4 | Explain the trust store: OS vs browser vs language runtime, and why they disagree | | |
| S2.5 | Explain what a CSR contains and what the CA adds | | |
| S2.6 | Read a certificate and interpret its fields (`openssl x509 -text`) | | |
| S2.7 | Explain SAN vs CN, and why CN alone stopped working | | |
| S2.8 | Explain wildcard certificates and their scope limits | | |
| S2.9 | Explain key usage and extended key usage constraints | | |
| S2.10 | Explain revocation: CRL, OCSP, OCSP stapling — and why revocation is weak in practice | | |
| S2.11 | Explain Certificate Transparency and what it lets you detect | | |
| S2.12 | Explain certificate pinning and why it's a footgun in most deployments | | |
| S2.13 | Explain self-signed vs private CA vs public CA and choose correctly for a scenario | | |

## S3. Certificate lifecycle operations

| # | Capability | Score | Notes |
|---|---|---|---|
| S3.1 | Generate a private key and CSR with the right parameters | | |
| S3.2 | Explain and protect private key material — permissions, storage, never in Git | | |
| S3.3 | Convert between formats: PEM, DER, PKCS#12, JKS | | |
| S3.4 | Assemble a correct chain file and know the required order | | |
| S3.5 | Diagnose a missing intermediate — passes in a browser, fails in curl or a JVM | | |
| S3.6 | Verify a key and certificate actually match | | |
| S3.7 | Install a certificate on a load balancer, reverse proxy, and app server | | |
| S3.8 | Maintain a certificate inventory across an estate | | |
| S3.9 | Monitor and alert on expiry with enough lead time to act | | |
| S3.10 | Plan a renewal or rotation with no downtime | | |
| S3.11 | Handle a key compromise: revoke, reissue, reassess | | |
| S3.12 | Explain how an expired certificate causes an outage and why it keeps happening | | |

## S4. ACME, Let's Encrypt & automation

| # | Capability | Score | Notes |
|---|---|---|---|
| S4.1 | Explain how ACME works: account key, order, challenge, validation, issuance | | |
| S4.2 | Explain HTTP-01 vs DNS-01 vs TLS-ALPN-01 and when each is the only option | | |
| S4.3 | Use DNS-01 to issue a wildcard, and explain why HTTP-01 can't | | |
| S4.4 | Configure certbot or an equivalent client, including renewal hooks | | |
| S4.5 | Explain Let's Encrypt rate limits and how staging avoids burning them | | |
| S4.6 | Explain the 90-day lifetime as a design decision rather than an inconvenience | | |
| S4.7 | Debug a failed renewal: DNS propagation, firewall, webroot, permissions | | |
| S4.8 | Configure cert-manager in Kubernetes: Issuer, ClusterIssuer, Certificate | | |
| S4.9 | Debug a cert-manager certificate stuck pending | | |
| S4.10 | Compare ACME to ACM and to an internal CA, and choose per environment | | |
| S4.11 | Explain what breaks when a CA changes its chain, and how to prepare | | |

## S5. Internal PKI & mTLS

| # | Capability | Score | Notes |
|---|---|---|---|
| S5.1 | Explain when an internal CA is warranted rather than public certificates | | |
| S5.2 | Stand up a private CA and distribute the root to clients | | |
| S5.3 | Explain the operational burden an internal CA creates | | |
| S5.4 | Explain mTLS: what both sides present and verify | | |
| S5.5 | Configure mTLS between two services and debug a rejected client cert | | |
| S5.6 | Explain short-lived certificates and automated rotation as an alternative to revocation | | |
| S5.7 | Explain how a service mesh handles identity and mTLS for you | | |
| S5.8 | Explain SPIFFE/SPIRE-style workload identity at a concept level | | |
| S5.9 | Explain TLS termination vs passthrough vs re-encryption, and the security tradeoff | | |

## S6. Secrets in practice

Services are A10; this is the practice and the failure modes.

| # | Capability | Score | Notes |
|---|---|---|---|
| S6.1 | Explain why secrets in environment variables are still a compromise | | |
| S6.2 | Get a secret to a running workload without it touching an image or repo | | |
| S6.3 | Scan a repo and its history for committed secrets | | |
| S6.4 | Respond to a committed secret: rotate first, then clean history | | |
| S6.5 | Design a rotation strategy for credentials that can't rotate atomically | | |
| S6.6 | Explain dynamic / short-lived credentials and why they beat rotation | | |
| S6.7 | Prevent secrets leaking into logs, error messages, and CI output | | |
| S6.8 | Explain the tradeoffs of Vault vs a cloud-native secrets service | | |
| S6.9 | Explain how secrets are handled in Terraform state and what that implies | | |

## S7. Supply chain & pipeline security

| # | Capability | Score | Notes |
|---|---|---|---|
| S7.1 | Explain the software supply chain attack surface end to end | | |
| S7.2 | Pin dependencies and use lockfiles; explain why floating versions are a risk | | |
| S7.3 | Explain dependency confusion and typosquatting | | |
| S7.4 | Scan dependencies and triage findings by exploitability, not just severity | | |
| S7.5 | Scan container images and explain what a scanner can't see | | |
| S7.6 | Build minimal images (distroless, non-root) and explain the reduction in attack surface | | |
| S7.7 | Sign and verify artifacts (cosign, provenance attestation) | | |
| S7.8 | Generate and use an SBOM for something real | | |
| S7.9 | Secure a CI pipeline: least-privilege runners, OIDC over static keys, protected environments | | |
| S7.10 | Explain the risk of untrusted code running in CI (fork PRs, third-party actions) | | |
| S7.11 | Pin third-party CI actions to a digest and explain why a tag isn't enough | | |
| S7.12 | Explain SLSA levels at a decision level | | |

## S8. Vulnerability & patch management

| # | Capability | Score | Notes |
|---|---|---|---|
| S8.1 | Explain CVE, CVSS, and why CVSS alone is a poor prioritisation signal | | |
| S8.2 | Assess whether a vulnerability is actually reachable in your context | | |
| S8.3 | Define and defend a patching SLA by severity | | |
| S8.4 | Patch at scale without downtime | | |
| S8.5 | Handle a zero-day: assess exposure, mitigate, communicate | | |
| S8.6 | Explain image rebuild cadence as a patching strategy for containers | | |
| S8.7 | Manage the backlog without either ignoring it or drowning in it | | |

## S9. Access, hardening & controls

| # | Capability | Score | Notes |
|---|---|---|---|
| S9.1 | Apply least privilege and explain why it degrades over time | | |
| S9.2 | Design break-glass access with auditing | | |
| S9.3 | Explain defence in depth with a concrete multi-layer example | | |
| S9.4 | Explain the principle of secure defaults and where yours aren't | | |
| S9.5 | Explain network segmentation and blast radius containment | | |
| S9.6 | Explain zero trust beyond the marketing version | | |
| S9.7 | Ensure audit logs exist, are complete, and can't be edited by the audited | | |
| S9.8 | Explain the OWASP Top 10 well enough to spot the common ones in review | | |
| S9.9 | Threat model a system: assets, actors, entry points, mitigations | | |

## S10. Compliance & assurance

| # | Capability | Score | Notes |
|---|---|---|---|
| S10.1 | Explain the intent behind a control rather than reciting the requirement | | |
| S10.2 | Produce evidence for an auditor from systems rather than screenshots | | |
| S10.3 | Explain policy as code and automated compliance checking | | |
| S10.4 | Explain data residency and its architectural consequences | | |
| S10.5 | Explain the relevant frameworks at a working level (SOC 2, ISO 27001, PCI DSS, GDPR) | | |
| S10.6 | Explain how a regulated environment changes deployment practice | | |
| S10.7 | Push back on a control that adds cost without reducing risk, constructively | | |

---

## Security, PKI & Certificates — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| S1. Cryptography fundamentals | 8 | /16 | |
| S2. PKI & the trust model | 13 | /26 | |
| S3. Certificate lifecycle operations | 12 | /24 | |
| S4. ACME, Let's Encrypt & automation | 11 | /22 | |
| S5. Internal PKI & mTLS | 9 | /18 | |
| S6. Secrets in practice | 9 | /18 | |
| S7. Supply chain & pipeline security | 12 | /24 | |
| S8. Vulnerability & patch management | 7 | /14 | |
| S9. Access, hardening & controls | 9 | /18 | |
| S10. Compliance & assurance | 7 | /14 | |
| **Total** | **97** | **/194** | |

---

# Domain 7 — Docker & Containers

Prefixed `D`. Overlaps handled elsewhere: ECR specifics in A5.1, image scanning and artifact signing in S7.5–S7.7, ECS in A5.2–A5.4, orchestration in the Kubernetes domain.

## D1. Fundamentals & internals

| # | Capability | Score | Notes |
|---|---|---|---|
| D1.1 | Explain what a container actually is — namespaces and cgroups, not a VM | | |
| D1.2 | Explain the difference between a container and a VM, including the isolation tradeoff | | |
| D1.3 | Explain which namespaces do what: pid, net, mnt, uts, ipc, user | | |
| D1.4 | Explain what cgroups control and how limits are enforced | | |
| D1.5 | Explain image layers, the union filesystem, and the writable container layer | | |
| D1.6 | Explain that containers share the host kernel and what that rules out | | |
| D1.7 | Explain the OCI spec and the difference between image, runtime, and distribution specs | | |
| D1.8 | Explain the relationship between Docker, containerd, and runc | | |
| D1.9 | Explain why architecture matters (arm64 vs amd64) and how multi-arch images work | | |

## D2. Images & Dockerfiles

| # | Capability | Score | Notes |
|---|---|---|---|
| D2.1 | Write a Dockerfile from scratch for a real application | | |
| D2.2 | Explain every common instruction and when each creates a layer | | |
| D2.3 | Explain CMD vs ENTRYPOINT, shell vs exec form, and how they combine | | |
| D2.4 | Explain COPY vs ADD and why COPY is the default choice | | |
| D2.5 | Use `.dockerignore` and explain its effect on build context size | | |
| D2.6 | Order instructions to maximise layer cache hits | | |
| D2.7 | Explain why `apt-get update` and `install` must be in the same RUN | | |
| D2.8 | Use build args vs environment variables correctly | | |
| D2.9 | Explain why build args are not a safe way to pass secrets | | |
| D2.10 | Use BuildKit secret mounts for build-time credentials | | |
| D2.11 | Tag deliberately — why `latest` is not a version | | |
| D2.12 | Use labels for metadata and traceability back to a commit | | |
| D2.13 | Explain base image choice: distro vs slim vs alpine vs distroless, with tradeoffs | | |
| D2.14 | Explain the musl vs glibc problem with alpine | | |
| D2.15 | Pin base images by digest and explain what that buys you | | |

## D3. Build optimisation

| # | Capability | Score | Notes |
|---|---|---|---|
| D3.1 | Write a multi-stage build separating build-time and runtime dependencies | | |
| D3.2 | Explain why multi-stage matters for both size and attack surface | | |
| D3.3 | Diagnose why a layer cache is missing and fix it | | |
| D3.4 | Use cache mounts for package managers | | |
| D3.5 | Share a build cache in CI where the daemon is ephemeral | | |
| D3.6 | Build multi-arch images with buildx | | |
| D3.7 | Inspect image size layer by layer and identify the culprit | | |
| D3.8 | Reduce an oversized image and quantify the improvement | | |
| D3.9 | Explain how build context size affects build time | | |

## D4. Running containers

| # | Capability | Score | Notes |
|---|---|---|---|
| D4.1 | Run containers with the flags that matter: `-d`, `-p`, `-v`, `-e`, `--rm`, `--name` | | |
| D4.2 | Set memory and CPU limits, and explain what happens when each is exceeded | | |
| D4.3 | Explain the signal a container receives on stop and the grace period | | |
| D4.4 | Handle signals correctly in the entrypoint so shutdown is graceful | | |
| D4.5 | Explain the PID 1 problem and zombie reaping (`--init`, tini) | | |
| D4.6 | Configure restart policies and explain their limits | | |
| D4.7 | Configure a healthcheck and explain what it should actually test | | |
| D4.8 | Configure logging drivers and explain why apps should log to stdout | | |
| D4.9 | Explain why one process per container is the convention and when it bends | | |
| D4.10 | Pass configuration in without rebuilding the image | | |

## D5. Networking

| # | Capability | Score | Notes |
|---|---|---|---|
| D5.1 | Explain the network drivers: bridge, host, none, overlay | | |
| D5.2 | Explain how port publishing works and what it does on the host | | |
| D5.3 | Explain container-to-container communication and embedded DNS on a user-defined network | | |
| D5.4 | Explain why the default bridge behaves differently from a user-defined one | | |
| D5.5 | Reach a service on the host from inside a container | | |
| D5.6 | Diagnose "the container is running but I can't reach it" | | |
| D5.7 | Explain what happens to the host firewall when Docker publishes a port | | |
| D5.8 | Inspect a container's network configuration | | |

## D6. Storage & data

| # | Capability | Score | Notes |
|---|---|---|---|
| D6.1 | Explain named volumes vs bind mounts vs tmpfs, and choose correctly | | |
| D6.2 | Explain why data in the container layer is ephemeral | | |
| D6.3 | Create, inspect, back up, and restore a volume | | |
| D6.4 | Diagnose permission problems on a bind mount (UID/GID mismatch) | | |
| D6.5 | Explain the performance characteristics of bind mounts on macOS/Windows | | |
| D6.6 | Explain what `docker system prune` removes and the risk of running it casually | | |
| D6.7 | Diagnose a host running out of disk from images, volumes, and logs | | |

## D7. Compose & local development

| # | Capability | Score | Notes |
|---|---|---|---|
| D7.1 | Write a compose file for a multi-service application | | |
| D7.2 | Use `depends_on` with healthchecks and explain why ordering alone isn't enough | | |
| D7.3 | Use environment files and variable substitution | | |
| D7.4 | Override configuration per environment with multiple compose files | | |
| D7.5 | Use profiles to run a subset of services | | |
| D7.6 | Set up a live-reload development loop | | |
| D7.7 | Explain where Compose stops being appropriate | | |

## D8. Registries & distribution

| # | Capability | Score | Notes |
|---|---|---|---|
| D8.1 | Push, pull, and authenticate against a registry | | |
| D8.2 | Explain image digests vs tags and why tags are mutable | | |
| D8.3 | Explain what a manifest and manifest list contain | | |
| D8.4 | Design a tagging strategy that supports rollback and traceability | | |
| D8.5 | Configure retention and lifecycle policies to control storage cost | | |
| D8.6 | Configure cross-account or cross-environment pull access | | |
| D8.7 | Use a pull-through cache or mirror, and explain the rate-limit motivation | | |
| D8.8 | Promote an image between environments without rebuilding it | | |

## D9. Security

| # | Capability | Score | Notes |
|---|---|---|---|
| D9.1 | Run as a non-root user and explain why the default is a problem | | |
| D9.2 | Explain the risk of mounting the Docker socket into a container | | |
| D9.3 | Explain what `--privileged` grants and why it's rarely justified | | |
| D9.4 | Drop capabilities and add back only what's needed | | |
| D9.5 | Use a read-only root filesystem with tmpfs for writable paths | | |
| D9.6 | Explain user namespace remapping and rootless Docker | | |
| D9.7 | Explain seccomp and AppArmor profiles at a working level | | |
| D9.8 | Explain why secrets must not be baked into layers, and how they survive deletion | | |
| D9.9 | Inspect an image's history to find something that shouldn't be there | | |
| D9.10 | Explain container escape at a conceptual level and the controls that prevent it | | |
| D9.11 | Explain why container isolation isn't a security boundary for untrusted code | | |

## D10. Debugging & troubleshooting

| # | Capability | Score | Notes |
|---|---|---|---|
| D10.1 | Read logs, follow them, and explain where they're stored | | |
| D10.2 | Exec into a running container and know when that's the wrong instinct | | |
| D10.3 | Debug a container with no shell (distroless) — debug containers, copying tools | | |
| D10.4 | Diagnose a container that exits immediately | | |
| D10.5 | Interpret exit codes, especially 137 and 139 | | |
| D10.6 | Diagnose an OOM kill and distinguish it from an application crash | | |
| D10.7 | Diagnose an image pull failure: auth, rate limit, architecture, tag | | |
| D10.8 | Inspect a container's full config and compare intent with reality | | |
| D10.9 | Check resource usage per container (`docker stats`) | | |
| D10.10 | Debug a build failure at an intermediate layer | | |
| D10.11 | Diagnose "works on my machine" caused by architecture or cached layers | | |

## D11. Production readiness

| # | Capability | Score | Notes |
|---|---|---|---|
| D11.1 | Explain what makes an image production-ready beyond "it runs" | | |
| D11.2 | Ensure the app handles SIGTERM and drains connections | | |
| D11.3 | Ensure the image is reproducible from a known commit | | |
| D11.4 | Set resource requests and limits from measurement rather than guesswork | | |
| D11.5 | Explain the twelve-factor principles that apply to containerisation | | |
| D11.6 | Explain how config and secrets differ in handling at runtime | | |
| D11.7 | Explain the cost of image size on deploy speed and autoscaling responsiveness | | |
| D11.8 | Explain when a container is the wrong answer | | |

---

## Docker & Containers — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| D1. Fundamentals & internals | 9 | /18 | |
| D2. Images & Dockerfiles | 15 | /30 | |
| D3. Build optimisation | 9 | /18 | |
| D4. Running containers | 10 | /20 | |
| D5. Networking | 8 | /16 | |
| D6. Storage & data | 7 | /14 | |
| D7. Compose & local development | 7 | /14 | |
| D8. Registries & distribution | 8 | /16 | |
| D9. Security | 11 | /22 | |
| D10. Debugging & troubleshooting | 11 | /22 | |
| D11. Production readiness | 8 | /16 | |
| **Total** | **103** | **/206** | |

---

# Domain 8 — Kubernetes

Prefixed `K`. Overlaps handled elsewhere: EKS-specific configuration in A5.5–A5.8, image and supply chain security in S7, container internals in D1, cert-manager in S4.8.

## K1. Architecture & control plane

| # | Capability | Score | Notes |
|---|---|---|---|
| K1.1 | Name the control plane components and what each is responsible for | | |
| K1.2 | Explain the role of etcd and why its backup matters more than anything else | | |
| K1.3 | Explain the API server as the single point of interaction | | |
| K1.4 | Explain the controller pattern and the reconciliation loop | | |
| K1.5 | Explain declarative vs imperative and why desired state changes how you operate | | |
| K1.6 | Explain what the scheduler does and what it doesn't do | | |
| K1.7 | Explain kubelet and container runtime responsibilities on a node | | |
| K1.8 | Explain kube-proxy and what replaced it in newer setups | | |
| K1.9 | Walk the full lifecycle of `kubectl apply` through to a running pod | | |
| K1.10 | Explain managed control planes: what the provider owns vs what you own | | |

## K2. Workloads

| # | Capability | Score | Notes |
|---|---|---|---|
| K2.1 | Write a Pod spec and explain why you rarely create bare pods | | |
| K2.2 | Explain the pod lifecycle phases and container states | | |
| K2.3 | Use init containers and explain a real use case | | |
| K2.4 | Use sidecar containers and explain the native sidecar change | | |
| K2.5 | Write a Deployment and explain the ReplicaSet relationship | | |
| K2.6 | Configure a rolling update: maxSurge, maxUnavailable, and the consequences | | |
| K2.7 | Roll back a Deployment and inspect its revision history | | |
| K2.8 | Explain when a StatefulSet is required and how it differs in identity and ordering | | |
| K2.9 | Explain DaemonSets and typical uses | | |
| K2.10 | Write Jobs and CronJobs, including completions, parallelism, and backoff | | |
| K2.11 | Explain deployment strategies: rolling, blue/green, canary — and how you'd implement each | | |
| K2.12 | Explain pod disruption from voluntary vs involuntary causes | | |

## K3. Configuration & secrets

| # | Capability | Score | Notes |
|---|---|---|---|
| K3.1 | Use ConfigMaps as environment variables and as mounted files | | |
| K3.2 | Explain which mounted config updates live and which requires a restart | | |
| K3.3 | Trigger a rollout when config changes (checksum annotation pattern) | | |
| K3.4 | Explain that Secrets are base64-encoded, not encrypted, by default | | |
| K3.5 | Enable and explain encryption at rest for etcd secrets | | |
| K3.6 | Use an external secrets operator or CSI driver to source secrets externally | | |
| K3.7 | Use the downward API to expose pod metadata to the application | | |
| K3.8 | Explain immutable ConfigMaps and Secrets and why they help at scale | | |

## K4. Networking

| # | Capability | Score | Notes |
|---|---|---|---|
| K4.1 | Explain the Kubernetes network model and its flat-addressing assumption | | |
| K4.2 | Explain what a CNI does and how plugins differ | | |
| K4.3 | Explain Service types: ClusterIP, NodePort, LoadBalancer, ExternalName | | |
| K4.4 | Explain how a Service selects pods and what Endpoints/EndpointSlices hold | | |
| K4.5 | Explain headless Services and when you need one | | |
| K4.6 | Explain cluster DNS resolution and the FQDN form for cross-namespace access | | |
| K4.7 | Explain Ingress, ingress controllers, and why the controller is not built in | | |
| K4.8 | Configure TLS on an Ingress | | |
| K4.9 | Explain the Gateway API and why it's replacing Ingress | | |
| K4.10 | Write NetworkPolicies, including a default-deny baseline | | |
| K4.11 | Explain that NetworkPolicy requires CNI support to do anything | | |
| K4.12 | Trace traffic end to end from client to container port | | |
| K4.13 | Explain a service mesh: what it adds and what it costs | | |

## K5. Storage

| # | Capability | Score | Notes |
|---|---|---|---|
| K5.1 | Explain PersistentVolume, PersistentVolumeClaim, and StorageClass roles | | |
| K5.2 | Explain static vs dynamic provisioning | | |
| K5.3 | Explain access modes and the constraint RWO puts on scheduling | | |
| K5.4 | Explain reclaim policies and the data-loss risk of Delete | | |
| K5.5 | Use volumeClaimTemplates in a StatefulSet | | |
| K5.6 | Expand a PVC and explain the limits on doing so | | |
| K5.7 | Explain ephemeral volume types: emptyDir, configMap, secret, projected | | |
| K5.8 | Explain CSI and what a driver provides | | |
| K5.9 | Diagnose a pod stuck pending on volume attachment or zone mismatch | | |

## K6. Scheduling & resources

| # | Capability | Score | Notes |
|---|---|---|---|
| K6.1 | Explain requests vs limits and their different effects | | |
| K6.2 | Explain CPU throttling and why CPU limits are contentious | | |
| K6.3 | Explain memory limits and why exceeding them is fatal rather than throttled | | |
| K6.4 | Explain QoS classes and eviction order | | |
| K6.5 | Set requests from measurement rather than guesswork | | |
| K6.6 | Use node selectors, node affinity, and pod affinity/anti-affinity | | |
| K6.7 | Explain taints and tolerations, and how they differ from affinity | | |
| K6.8 | Use topology spread constraints for AZ distribution | | |
| K6.9 | Use PodDisruptionBudgets and explain what they protect against | | |
| K6.10 | Explain priority classes and preemption | | |
| K6.11 | Explain node pressure eviction and the difference from OOM kill | | |
| K6.12 | Use ResourceQuotas and LimitRanges for multi-tenancy | | |
| K6.13 | Diagnose a pod that won't schedule and identify which constraint blocked it | | |

## K7. Autoscaling

| # | Capability | Score | Notes |
|---|---|---|---|
| K7.1 | Configure an HPA on CPU and on custom metrics | | |
| K7.2 | Explain why HPA needs requests set to work at all | | |
| K7.3 | Explain HPA stabilisation and thrashing | | |
| K7.4 | Explain VPA and why it conflicts with HPA on the same resource | | |
| K7.5 | Explain Cluster Autoscaler behaviour on scale-up and scale-down | | |
| K7.6 | Explain Karpenter's different model and when it's preferable | | |
| K7.7 | Explain what blocks a node from scaling down | | |
| K7.8 | Explain scale-to-zero options and their cold-start tradeoff | | |
| K7.9 | Diagnose why autoscaling isn't happening when you expect it | | |

## K8. Security & RBAC

| # | Capability | Score | Notes |
|---|---|---|---|
| K8.1 | Explain Role, ClusterRole, RoleBinding, ClusterRoleBinding | | |
| K8.2 | Write a least-privilege Role for a stated requirement | | |
| K8.3 | Explain ServiceAccounts and how a pod gets an identity | | |
| K8.4 | Explain projected service account tokens and workload identity federation | | |
| K8.5 | Use `kubectl auth can-i` to verify and debug permissions | | |
| K8.6 | Explain Pod Security Admission levels and how they replaced PSPs | | |
| K8.7 | Set a securityContext: non-root, read-only rootfs, dropped capabilities | | |
| K8.8 | Explain admission control: validating vs mutating webhooks | | |
| K8.9 | Use a policy engine (OPA/Gatekeeper, Kyverno) to enforce a standard | | |
| K8.10 | Explain namespace isolation and its limits as a security boundary | | |
| K8.11 | Explain the risk of cluster-admin sprawl and how you'd audit it | | |
| K8.12 | Explain how an attacker moves from a compromised pod to the cluster | | |
| K8.13 | Explain audit logging and what you'd want captured | | |

## K9. Observability & debugging

| # | Capability | Score | Notes |
|---|---|---|---|
| K9.1 | Use kubectl fluently: get, describe, logs, exec, port-forward, top | | |
| K9.2 | Read `describe` output and find the answer in Events | | |
| K9.3 | Get logs from a crashed previous container (`--previous`) | | |
| K9.4 | Diagnose CrashLoopBackOff systematically | | |
| K9.5 | Diagnose ImagePullBackOff and distinguish auth from tag from architecture | | |
| K9.6 | Diagnose Pending and identify the blocking constraint | | |
| K9.7 | Diagnose a pod stuck Terminating | | |
| K9.8 | Diagnose OOMKilled and decide between raising limits and fixing the app | | |
| K9.9 | Debug a Service returning nothing: selectors, endpoints, ports, probes | | |
| K9.10 | Configure liveness, readiness, and startup probes correctly | | |
| K9.11 | Explain how a bad liveness probe causes a self-inflicted outage | | |
| K9.12 | Use ephemeral debug containers against a distroless pod | | |
| K9.13 | Explain how metrics and logs get out of the cluster | | |
| K9.14 | Explain what to monitor at cluster level vs workload level | | |

## K10. Packaging & delivery

| # | Capability | Score | Notes |
|---|---|---|---|
| K10.1 | Install, upgrade, roll back, and inspect a Helm release | | |
| K10.2 | Write a Helm chart with values, templates, and helpers | | |
| K10.3 | Debug a chart with `template` and `--dry-run` | | |
| K10.4 | Explain Helm's release state and what happens when it's out of sync | | |
| K10.5 | Use Kustomize bases and overlays | | |
| K10.6 | Choose between Helm and Kustomize and defend the choice | | |
| K10.7 | Explain GitOps and how it differs from a push pipeline | | |
| K10.8 | Configure ArgoCD or Flux to sync an application | | |
| K10.9 | Handle drift and explain when auto-sync and self-heal are appropriate | | |
| K10.10 | Manage environment-specific config without duplicating manifests | | |
| K10.11 | Explain how secrets are handled in a GitOps model | | |

## K11. Cluster operations

| # | Capability | Score | Notes |
|---|---|---|---|
| K11.1 | Plan and execute a cluster version upgrade | | |
| K11.2 | Explain version skew policy between control plane and nodes | | |
| K11.3 | Find and fix deprecated API usage before an upgrade breaks it | | |
| K11.4 | Cordon, drain, and replace a node safely | | |
| K11.5 | Explain node upgrade strategies: in-place vs rolling replacement | | |
| K11.6 | Back up and restore cluster state, and explain what backup actually covers | | |
| K11.7 | Explain multi-tenancy options: namespaces vs virtual clusters vs separate clusters | | |
| K11.8 | Explain cluster sizing and when to run more clusters rather than a bigger one | | |
| K11.9 | Manage add-ons and their upgrade coupling to the cluster version | | |
| K11.10 | Explain a disaster scenario: losing the control plane, and what you'd need | | |

## K12. Extending Kubernetes

| # | Capability | Score | Notes |
|---|---|---|---|
| K12.1 | Explain CRDs and what adding one does to the API | | |
| K12.2 | Explain the operator pattern and when it's warranted | | |
| K12.3 | Evaluate a third-party operator before adopting it | | |
| K12.4 | Explain finalizers and how they cause stuck deletions | | |
| K12.5 | Explain owner references and cascading deletion | | |
| K12.6 | Explain the API aggregation layer at a concept level | | |

## K13. Design judgement

| # | Capability | Score | Notes |
|---|---|---|---|
| K13.1 | Explain when Kubernetes is the wrong choice | | |
| K13.2 | Justify EKS vs self-managed vs ECS for a stated context | | |
| K13.3 | Design a namespace and tenancy model for an organisation | | |
| K13.4 | Explain the platform team's contract with application teams | | |
| K13.5 | Explain the real operational cost of running Kubernetes | | |
| K13.6 | Design a cluster for HA across AZs and state the failure modes it survives | | |
| K13.7 | Explain how you'd migrate a workload onto Kubernetes incrementally | | |
| K13.8 | Explain how you'd run stateful workloads, and whether you should | | |

---

## Kubernetes — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| K1. Architecture & control plane | 10 | /20 | |
| K2. Workloads | 12 | /24 | |
| K3. Configuration & secrets | 8 | /16 | |
| K4. Networking | 13 | /26 | |
| K5. Storage | 9 | /18 | |
| K6. Scheduling & resources | 13 | /26 | |
| K7. Autoscaling | 9 | /18 | |
| K8. Security & RBAC | 13 | /26 | |
| K9. Observability & debugging | 14 | /28 | |
| K10. Packaging & delivery | 11 | /22 | |
| K11. Cluster operations | 10 | /20 | |
| K12. Extending Kubernetes | 6 | /12 | |
| K13. Design judgement | 8 | /16 | |
| **Total** | **136** | **/272** | |

---

# Domain 9 — Databases

Prefixed `DB`. AWS-managed service configuration is A7 (RDS, DynamoDB, ElastiCache); this domain is the engine-level and operational knowledge underneath it — what a platform engineer needs to run, scale, and recover a database.

## DB1. Fundamentals

| # | Capability | Score | Notes |
|---|---|---|---|
| DB1.1 | Explain relational vs document vs key-value vs wide-column vs graph, and when each fits | | |
| DB1.2 | Explain normalisation and when denormalising is the right call | | |
| DB1.3 | Explain primary keys, foreign keys, and referential integrity | | |
| DB1.4 | Explain OLTP vs OLAP and why one database rarely serves both well | | |
| DB1.5 | Explain the CAP theorem accurately, including what it doesn't say | | |
| DB1.6 | Explain ACID and what each property actually guarantees | | |
| DB1.7 | Explain eventual consistency and the application consequences | | |
| DB1.8 | Explain how a query gets from client to disk and back | | |
| DB1.9 | Explain the write-ahead log and its role in durability and recovery | | |
| DB1.10 | Explain B-tree vs LSM-tree storage and the read/write tradeoff | | |

## DB2. SQL & query performance

| # | Capability | Score | Notes |
|---|---|---|---|
| DB2.1 | Write joins, aggregations, subqueries, and CTEs confidently | | |
| DB2.2 | Explain the join types and predict row counts | | |
| DB2.3 | Use window functions for a real problem | | |
| DB2.4 | Read an execution plan and identify the expensive step | | |
| DB2.5 | Recognise a sequential scan that should be an index scan | | |
| DB2.6 | Explain how the query planner uses statistics and what happens when they're stale | | |
| DB2.7 | Identify and fix an N+1 query pattern | | |
| DB2.8 | Find the slowest queries on a live system | | |
| DB2.9 | Explain why a query fast in staging is slow in production | | |
| DB2.10 | Rewrite a slow query and prove the improvement with numbers | | |
| DB2.11 | Explain the cost of `SELECT *` beyond aesthetics | | |

## DB3. Indexing

| # | Capability | Score | Notes |
|---|---|---|---|
| DB3.1 | Explain what an index costs on write and in storage | | |
| DB3.2 | Design a composite index and explain why column order matters | | |
| DB3.3 | Explain covering indexes and index-only scans | | |
| DB3.4 | Explain partial and filtered indexes | | |
| DB3.5 | Explain why an index isn't used despite existing | | |
| DB3.6 | Find unused and duplicate indexes and remove them safely | | |
| DB3.7 | Create an index concurrently without locking a live table | | |
| DB3.8 | Explain index bloat and when a rebuild is needed | | |
| DB3.9 | Explain specialised index types and when they apply (GIN, GiST, full-text) | | |

## DB4. Transactions & concurrency

| # | Capability | Score | Notes |
|---|---|---|---|
| DB4.1 | Explain the isolation levels and what anomaly each prevents | | |
| DB4.2 | Explain dirty read, non-repeatable read, phantom read, write skew | | |
| DB4.3 | Explain your engine's default isolation level and its implications | | |
| DB4.4 | Explain MVCC and how readers avoid blocking writers | | |
| DB4.5 | Explain lock types and escalation | | |
| DB4.6 | Diagnose a deadlock from the log and fix the ordering that caused it | | |
| DB4.7 | Diagnose lock contention on a live system | | |
| DB4.8 | Explain optimistic vs pessimistic locking and choose between them | | |
| DB4.9 | Explain long-running transactions as an operational hazard | | |
| DB4.10 | Explain idempotency for operations that may be retried | | |

## DB5. Replication & high availability

| # | Capability | Score | Notes |
|---|---|---|---|
| DB5.1 | Explain synchronous vs asynchronous replication and the durability tradeoff | | |
| DB5.2 | Explain replication lag: causes, measurement, and application impact | | |
| DB5.3 | Explain read-after-write inconsistency when reading from a replica | | |
| DB5.4 | Explain failover: automatic vs manual, and what triggers it | | |
| DB5.5 | Explain split-brain and how quorum prevents it | | |
| DB5.6 | Explain what happens to in-flight connections during failover | | |
| DB5.7 | Explain multi-primary and why it's usually a bad idea | | |
| DB5.8 | Explain logical vs physical replication and when logical is needed | | |
| DB5.9 | Promote a replica and explain the data-loss window | | |
| DB5.10 | Design HA for a stated RTO and RPO | | |

## DB6. Backup, restore & recovery

| # | Capability | Score | Notes |
|---|---|---|---|
| DB6.1 | Explain logical vs physical backups and when each is appropriate | | |
| DB6.2 | Explain full, incremental, and continuous archiving | | |
| DB6.3 | Explain point-in-time recovery and what it requires | | |
| DB6.4 | Perform an actual restore and time it | | |
| DB6.5 | Explain why an untested backup isn't a backup | | |
| DB6.6 | Recover from an accidental DROP or bad UPDATE — the most likely real disaster | | |
| DB6.7 | Explain backup impact on a live primary and how to avoid it | | |
| DB6.8 | Design retention against both DR and compliance requirements | | |
| DB6.9 | Explain cross-region backup and its cost and latency implications | | |
| DB6.10 | Explain what a snapshot does and doesn't guarantee about consistency | | |

## DB7. Schema change & migrations

| # | Capability | Score | Notes |
|---|---|---|---|
| DB7.1 | Explain which DDL operations lock and for how long | | |
| DB7.2 | Add a column to a large live table without an outage | | |
| DB7.3 | Explain the expand-contract pattern for backwards-compatible change | | |
| DB7.4 | Deploy a schema change and an application change safely in sequence | | |
| DB7.5 | Explain why a migration must be backwards compatible during a rolling deploy | | |
| DB7.6 | Write a reversible migration, and explain when reversal is impossible | | |
| DB7.7 | Use a migration tool in a pipeline (Flyway, Liquibase, Alembic) | | |
| DB7.8 | Backfill a large table without saturating the database | | |
| DB7.9 | Explain online schema change tools and why they exist | | |
| DB7.10 | Explain how you'd recover from a migration that fails halfway | | |

## DB8. Connections & pooling

| # | Capability | Score | Notes |
|---|---|---|---|
| DB8.1 | Explain the cost of a database connection | | |
| DB8.2 | Explain connection pooling and where the pool should live | | |
| DB8.3 | Size a pool relative to database max connections and instance count | | |
| DB8.4 | Explain how autoscaling application pods exhausts database connections | | |
| DB8.5 | Explain transaction vs session vs statement pooling modes | | |
| DB8.6 | Use an external pooler (PgBouncer, RDS Proxy) and explain the tradeoffs | | |
| DB8.7 | Diagnose connection exhaustion and identify the leak | | |
| DB8.8 | Explain timeouts: connection, statement, idle-in-transaction | | |

## DB9. Scaling

| # | Capability | Score | Notes |
|---|---|---|---|
| DB9.1 | Explain vertical scaling limits and why it's still often the right first move | | |
| DB9.2 | Scale reads with replicas and explain what it doesn't solve | | |
| DB9.3 | Explain partitioning and choose a partition key | | |
| DB9.4 | Explain sharding and the operational cost it introduces | | |
| DB9.5 | Explain hot partitions and skew | | |
| DB9.6 | Explain why cross-shard joins and transactions are hard | | |
| DB9.7 | Archive or purge old data as a scaling strategy | | |
| DB9.8 | Explain CQRS and read-model separation at a decision level | | |
| DB9.9 | Explain when the answer is a different datastore rather than more scaling | | |

## DB10. NoSQL

| # | Capability | Score | Notes |
|---|---|---|---|
| DB10.1 | Explain single-table design in DynamoDB and access-pattern-first modelling | | |
| DB10.2 | Choose a partition key and sort key for stated access patterns | | |
| DB10.3 | Explain GSIs and LSIs and their constraints | | |
| DB10.4 | Explain provisioned vs on-demand capacity and throttling behaviour | | |
| DB10.5 | Explain strongly vs eventually consistent reads and their cost difference | | |
| DB10.6 | Explain DynamoDB Streams and change data capture uses | | |
| DB10.7 | Explain document stores and when schema flexibility becomes a liability | | |
| DB10.8 | Explain why "NoSQL scales better" is an incomplete claim | | |

## DB11. Caching

| # | Capability | Score | Notes |
|---|---|---|---|
| DB11.1 | Explain caching strategies: cache-aside, read-through, write-through, write-behind | | |
| DB11.2 | Explain TTL choice and the staleness tradeoff | | |
| DB11.3 | Explain cache invalidation approaches and why it's genuinely hard | | |
| DB11.4 | Explain cache stampede and how to prevent it | | |
| DB11.5 | Explain eviction policies and how to spot a badly sized cache | | |
| DB11.6 | Explain Redis persistence options and that a cache can lose data | | |
| DB11.7 | Explain Redis as cache vs datastore vs queue, and the risk of conflating them | | |
| DB11.8 | Explain when a cache is masking a problem you should fix instead | | |

## DB12. Operations & monitoring

| # | Capability | Score | Notes |
|---|---|---|---|
| DB12.1 | Name the metrics that matter: connections, replication lag, cache hit ratio, IOPS, slow queries | | |
| DB12.2 | Set alerts that catch degradation before an outage | | |
| DB12.3 | Explain vacuum/autovacuum and the consequences of it falling behind | | |
| DB12.4 | Explain transaction ID wraparound as an existential risk | | |
| DB12.5 | Explain table and index bloat and how to reclaim space safely | | |
| DB12.6 | Diagnose "the database is slow" methodically | | |
| DB12.7 | Plan and execute a version upgrade with a rollback path | | |
| DB12.8 | Explain storage growth and IOPS as capacity planning inputs | | |
| DB12.9 | Explain maintenance windows and what actually happens in them | | |
| DB12.10 | Explain how to kill a runaway query safely | | |

## DB13. Security

| # | Capability | Score | Notes |
|---|---|---|---|
| DB13.1 | Design least-privilege database roles per application | | |
| DB13.2 | Explain why applications should not connect as a superuser | | |
| DB13.3 | Rotate credentials without downtime | | |
| DB13.4 | Use IAM or certificate-based auth instead of passwords | | |
| DB13.5 | Enforce encryption in transit and verify it's actually on | | |
| DB13.6 | Explain encryption at rest and what it protects against | | |
| DB13.7 | Explain SQL injection and the parameterisation that prevents it | | |
| DB13.8 | Explain audit logging and what should be captured | | |
| DB13.9 | Handle PII: masking, anonymised non-production data, retention | | |
| DB13.10 | Explain why production data in staging is a common serious risk | | |

## DB14. Judgement

| # | Capability | Score | Notes |
|---|---|---|---|
| DB14.1 | Choose a database for a stated workload and defend it | | |
| DB14.2 | Argue for managed vs self-hosted in a given context | | |
| DB14.3 | Explain the risk of running databases on Kubernetes and when operators make it viable | | |
| DB14.4 | Explain the platform team's responsibility boundary with application teams | | |
| DB14.5 | Plan a zero-downtime database migration between engines or versions | | |
| DB14.6 | Explain how you'd approach a database you've inherited and don't understand | | |

---

## Databases — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| DB1. Fundamentals | 10 | /20 | |
| DB2. SQL & query performance | 11 | /22 | |
| DB3. Indexing | 9 | /18 | |
| DB4. Transactions & concurrency | 10 | /20 | |
| DB5. Replication & high availability | 10 | /20 | |
| DB6. Backup, restore & recovery | 10 | /20 | |
| DB7. Schema change & migrations | 10 | /20 | |
| DB8. Connections & pooling | 8 | /16 | |
| DB9. Scaling | 9 | /18 | |
| DB10. NoSQL | 8 | /16 | |
| DB11. Caching | 8 | /16 | |
| DB12. Operations & monitoring | 10 | /20 | |
| DB13. Security | 10 | /20 | |
| DB14. Judgement | 6 | /12 | |
| **Total** | **129** | **/258** | |

---

# Domain 10 — Messaging, Queues & Streaming

Prefixed `M`. AWS service configuration is A13 (SQS, SNS, EventBridge); this domain is the messaging concepts underneath, with Kafka covered in depth.

## M1. Fundamentals & patterns

| # | Capability | Score | Notes |
|---|---|---|---|
| M1.1 | Explain why you'd introduce a broker rather than call a service synchronously | | |
| M1.2 | Explain queue (point-to-point) vs pub/sub (fan-out) | | |
| M1.3 | Explain the log/stream model and how it differs from a queue | | |
| M1.4 | Explain command vs event, and why the distinction shapes the design | | |
| M1.5 | Explain choreography vs orchestration and the tradeoff | | |
| M1.6 | Explain how a broker decouples producer and consumer availability | | |
| M1.7 | Explain backpressure and what happens when consumers can't keep up | | |
| M1.8 | Explain the cost: eventual consistency, debugging difficulty, operational burden | | |
| M1.9 | Explain competing consumers and how throughput scales | | |
| M1.10 | Explain when synchronous request/response is simply the better answer | | |

## M2. Delivery semantics & correctness

| # | Capability | Score | Notes |
|---|---|---|---|
| M2.1 | Explain at-most-once, at-least-once, exactly-once — and why exactly-once is contested | | |
| M2.2 | Explain why at-least-once is the practical default | | |
| M2.3 | Design an idempotent consumer and explain the deduplication mechanism | | |
| M2.4 | Explain ordering guarantees and their scope (per-partition, per-queue, global) | | |
| M2.5 | Explain why global ordering and parallelism are in tension | | |
| M2.6 | Explain the dual-write problem and the transactional outbox pattern | | |
| M2.7 | Explain poison messages and how they block progress | | |
| M2.8 | Design retry with backoff and a retry limit | | |
| M2.9 | Design dead-letter handling, including who looks at the DLQ and when | | |
| M2.10 | Explain message replay and what makes it safe or unsafe | | |
| M2.11 | Explain the saga pattern for distributed transactions | | |

## M3. Queues

| # | Capability | Score | Notes |
|---|---|---|---|
| M3.1 | Explain visibility timeout and what happens when processing outlasts it | | |
| M3.2 | Explain acknowledgement modes and when to ack | | |
| M3.3 | Explain SQS standard vs FIFO: ordering, dedup, throughput limits | | |
| M3.4 | Configure a DLQ with a sensible redrive policy, and redrive from it | | |
| M3.5 | Explain long polling vs short polling | | |
| M3.6 | Explain message groups and how FIFO parallelises | | |
| M3.7 | Explain RabbitMQ's model: exchanges, bindings, routing keys, queues | | |
| M3.8 | Explain when RabbitMQ suits a problem better than Kafka or SQS | | |
| M3.9 | Explain delay queues and scheduled delivery | | |
| M3.10 | Explain message size limits and the claim-check pattern | | |

## M4. Kafka architecture

| # | Capability | Score | Notes |
|---|---|---|---|
| M4.1 | Explain topics, partitions, offsets, and the commit log model | | |
| M4.2 | Explain how partitioning enables parallelism and constrains ordering | | |
| M4.3 | Explain brokers, the cluster, and partition leadership | | |
| M4.4 | Explain replication factor, ISR, and what happens when a replica falls behind | | |
| M4.5 | Explain `min.insync.replicas` and its interaction with producer acks | | |
| M4.6 | Explain leader election and unclean leader election's data-loss tradeoff | | |
| M4.7 | Explain ZooKeeper's former role and what KRaft changed | | |
| M4.8 | Explain retention: time-based, size-based, and log compaction | | |
| M4.9 | Explain when a compacted topic is the right choice | | |
| M4.10 | Explain why Kafka is fast: sequential IO, page cache, zero-copy, batching | | |
| M4.11 | Choose a partition count and explain why changing it later is disruptive | | |

## M5. Kafka producers

| # | Capability | Score | Notes |
|---|---|---|---|
| M5.1 | Explain the acks settings and the durability/latency tradeoff | | |
| M5.2 | Explain how the partitioner works and the effect of a null key | | |
| M5.3 | Choose a partition key and explain the resulting ordering guarantee | | |
| M5.4 | Diagnose partition skew from a poorly chosen key | | |
| M5.5 | Explain batching, linger, and compression as throughput levers | | |
| M5.6 | Explain the idempotent producer and what it actually prevents | | |
| M5.7 | Explain transactional producers and exactly-once semantics end to end | | |
| M5.8 | Explain producer retries and how they can reorder messages | | |
| M5.9 | Explain buffer exhaustion and producer-side backpressure | | |

## M6. Kafka consumers

| # | Capability | Score | Notes |
|---|---|---|---|
| M6.1 | Explain consumer groups and partition assignment | | |
| M6.2 | Explain why consumers beyond the partition count sit idle | | |
| M6.3 | Explain rebalancing, its triggers, and the stop-the-world cost | | |
| M6.4 | Explain cooperative/incremental rebalancing and static membership | | |
| M6.5 | Explain offset commits: auto vs manual, and where duplicates come from | | |
| M6.6 | Explain the consequence of committing before versus after processing | | |
| M6.7 | Diagnose consumer lag and distinguish slow consumer from spike from stuck partition | | |
| M6.8 | Explain `max.poll.interval` and the consumer being kicked from the group | | |
| M6.9 | Reset offsets deliberately and explain the blast radius | | |
| M6.10 | Explain how to scale consumers and what actually limits throughput | | |
| M6.11 | Handle a poison message without an infinite retry loop | | |

## M7. Kafka ecosystem

| # | Capability | Score | Notes |
|---|---|---|---|
| M7.1 | Explain Kafka Connect: source and sink connectors, workers, tasks | | |
| M7.2 | Explain Schema Registry and why schemas matter on a shared bus | | |
| M7.3 | Explain compatibility modes and plan a breaking schema change | | |
| M7.4 | Compare serialisation formats: Avro, Protobuf, JSON | | |
| M7.5 | Explain Kafka Streams and stateful stream processing | | |
| M7.6 | Explain ksqlDB or equivalent at a decision level | | |
| M7.7 | Explain change data capture and Debezium's role | | |
| M7.8 | Explain MirrorMaker and cross-cluster replication | | |
| M7.9 | Compare MSK, Confluent Cloud, and self-managed Kafka | | |

## M8. Streaming concepts

| # | Capability | Score | Notes |
|---|---|---|---|
| M8.1 | Explain event time vs processing time | | |
| M8.2 | Explain windowing: tumbling, hopping, sliding, session | | |
| M8.3 | Explain late-arriving data and watermarks | | |
| M8.4 | Explain stateful processing and where the state lives | | |
| M8.5 | Explain stream-table duality | | |
| M8.6 | Explain joins in a streaming context and their constraints | | |
| M8.7 | Explain event sourcing and its operational implications | | |
| M8.8 | Compare Kafka Streams, Flink, and Spark Streaming at a decision level | | |

## M9. Operations

| # | Capability | Score | Notes |
|---|---|---|---|
| M9.1 | Size a cluster: brokers, partitions, storage, throughput | | |
| M9.2 | Add a broker and rebalance partitions without disrupting traffic | | |
| M9.3 | Perform a rolling broker upgrade safely | | |
| M9.4 | Handle a broker failure and understand what recovers automatically | | |
| M9.5 | Explain and manage disk usage, retention, and running out of space | | |
| M9.6 | Explain quotas and protecting a cluster from a noisy client | | |
| M9.7 | Explain rack awareness and multi-AZ placement | | |
| M9.8 | Explain the cost and risk of cross-region streaming | | |
| M9.9 | Manage topics as code rather than ad hoc | | |
| M9.10 | Explain multi-tenancy: naming conventions, isolation, ownership | | |

## M10. Observability & troubleshooting

| # | Capability | Score | Notes |
|---|---|---|---|
| M10.1 | Name the metrics that matter: lag, under-replicated partitions, ISR shrink, request latency | | |
| M10.2 | Alert on consumer lag in a way that reflects business impact | | |
| M10.3 | Diagnose under-replicated partitions | | |
| M10.4 | Diagnose a consumer group stuck in perpetual rebalance | | |
| M10.5 | Diagnose a producer failing to publish | | |
| M10.6 | Trace a single message end to end across services | | |
| M10.7 | Explain how you'd debug a message that was published but never processed | | |
| M10.8 | Diagnose growing lag and decide between scaling, optimising, or shedding | | |
| M10.9 | Use CLI tooling to inspect topics, groups, and offsets | | |
| M10.10 | Explain what to do when a queue backs up in a live incident | | |

## M11. Security

| # | Capability | Score | Notes |
|---|---|---|---|
| M11.1 | Configure TLS in transit between clients and brokers | | |
| M11.2 | Explain authentication options: mTLS, SASL/SCRAM, IAM | | |
| M11.3 | Configure ACLs for least-privilege topic access | | |
| M11.4 | Explain encryption at rest and its limits | | |
| M11.5 | Explain PII on an event bus and the retention/GDPR problem | | |
| M11.6 | Explain how compaction and tombstones relate to deletion requests | | |
| M11.7 | Explain audit requirements for who published and consumed what | | |

## M12. Judgement

| # | Capability | Score | Notes |
|---|---|---|---|
| M12.1 | Choose between SQS, SNS, EventBridge, Kafka, and Kinesis for a stated problem | | |
| M12.2 | Explain when Kafka is overkill | | |
| M12.3 | Explain the real operational cost of running Kafka yourself | | |
| M12.4 | Explain the risk of the event bus becoming an undocumented integration layer | | |
| M12.5 | Define event ownership and schema governance across teams | | |
| M12.6 | Explain how you'd migrate from one broker technology to another | | |
| M12.7 | Explain the platform team's contract with producing and consuming teams | | |

---

## Messaging, Queues & Streaming — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| M1. Fundamentals & patterns | 10 | /20 | |
| M2. Delivery semantics & correctness | 11 | /22 | |
| M3. Queues | 10 | /20 | |
| M4. Kafka architecture | 11 | /22 | |
| M5. Kafka producers | 9 | /18 | |
| M6. Kafka consumers | 11 | /22 | |
| M7. Kafka ecosystem | 9 | /18 | |
| M8. Streaming concepts | 8 | /16 | |
| M9. Operations | 10 | /20 | |
| M10. Observability & troubleshooting | 10 | /20 | |
| M11. Security | 7 | /14 | |
| M12. Judgement | 7 | /14 | |
| **Total** | **113** | **/226** | |

---

# Domain 11 — Terraform & Infrastructure as Code

Prefixed `TF`. Cloud service knowledge is Domain 4; pipeline mechanics are the CI/CD domain. This is IaC as a discipline, the tool itself, and the platforms that run it at scale.

## TF1. IaC fundamentals

| # | Capability | Score | Notes |
|---|---|---|---|
| TF1.1 | Explain declarative vs imperative IaC and the consequences of each | | |
| TF1.2 | Explain idempotency and why it's the core property | | |
| TF1.3 | Explain immutable vs mutable infrastructure | | |
| TF1.4 | Explain configuration drift, how it happens, and how you detect it | | |
| TF1.5 | Explain why manual console changes undermine the whole model | | |
| TF1.6 | Compare Terraform, CloudFormation, CDK, and Pulumi honestly | | |
| TF1.7 | Explain where Terraform stops and configuration management begins | | |
| TF1.8 | Explain OpenTofu and the licence change that produced it | | |

## TF2. Core language

| # | Capability | Score | Notes |
|---|---|---|---|
| TF2.1 | Write resources, data sources, variables, outputs, and locals fluently | | |
| TF2.2 | Explain the type system and write proper variable types with validation | | |
| TF2.3 | Use `count` and `for_each`, and explain why `for_each` is usually better | | |
| TF2.4 | Explain how `count` index shifting destroys and recreates resources | | |
| TF2.5 | Use dynamic blocks, and know when they hurt readability more than they help | | |
| TF2.6 | Use for expressions, splat, and conditional expressions | | |
| TF2.7 | Use the common functions: try, coalesce, merge, lookup, flatten, templatefile | | |
| TF2.8 | Explain implicit vs explicit dependencies and when `depends_on` is required | | |
| TF2.9 | Use lifecycle meta-arguments: create_before_destroy, prevent_destroy, ignore_changes | | |
| TF2.10 | Explain `replace_triggered_by` and a real use for it | | |
| TF2.11 | Explain provisioners and why they're a last resort | | |
| TF2.12 | Explain the `moved` block and refactoring without destroying resources | | |
| TF2.13 | Explain the `import` block versus the CLI import command | | |
| TF2.14 | Explain `check` blocks and postconditions/preconditions | | |

## TF3. State

| # | Capability | Score | Notes |
|---|---|---|---|
| TF3.1 | Explain what state is and why Terraform can't work without it | | |
| TF3.2 | Explain why state contains secrets and what that implies for storage | | |
| TF3.3 | Configure a remote backend with encryption and versioning | | |
| TF3.4 | Explain state locking and what happens without it | | |
| TF3.5 | Recover from a stuck lock safely | | |
| TF3.6 | Explain how state files should be split and the blast-radius reasoning | | |
| TF3.7 | Use workspaces, and explain why they're a poor fit for environment separation | | |
| TF3.8 | Import an existing resource into state | | |
| TF3.9 | Remove a resource from state without destroying it | | |
| TF3.10 | Move a resource between state files | | |
| TF3.11 | Explain `terraform refresh` behaviour and the refresh-only plan | | |
| TF3.12 | Recover from a corrupted or lost state file | | |
| TF3.13 | Explain the risk of manual state editing and when it's unavoidable | | |
| TF3.14 | Use `terraform_remote_state` and explain why outputs create coupling | | |

## TF4. Modules

| # | Capability | Score | Notes |
|---|---|---|---|
| TF4.1 | Write a reusable module with a clear interface | | |
| TF4.2 | Explain what belongs in a module and what doesn't | | |
| TF4.3 | Version modules and pin them in consumers | | |
| TF4.4 | Source modules from a registry, Git, or local path, and know the tradeoffs | | |
| TF4.5 | Explain the danger of over-abstraction and wrapper-module sprawl | | |
| TF4.6 | Design a module hierarchy that composes rather than nests deeply | | |
| TF4.7 | Document a module so consumers don't read the source | | |
| TF4.8 | Test a module (terraform test, Terratest, or equivalent) | | |
| TF4.9 | Evolve a module's interface without breaking existing consumers | | |
| TF4.10 | Explain when a shared module is worse than duplication | | |

## TF5. Providers & versioning

| # | Capability | Score | Notes |
|---|---|---|---|
| TF5.1 | Configure providers, including multiple aliased instances | | |
| TF5.2 | Handle multi-account and multi-region deployments with provider aliases | | |
| TF5.3 | Explain required_providers and version constraint syntax | | |
| TF5.4 | Explain the lock file and why it belongs in version control | | |
| TF5.5 | Upgrade a provider major version safely | | |
| TF5.6 | Explain how providers map to APIs and what happens when a resource lags | | |
| TF5.7 | Explain Terraform core version constraints and upgrade planning | | |
| TF5.8 | Explain what to do when the provider can't express what you need | | |

## TF6. CLI & workflow

| # | Capability | Score | Notes |
|---|---|---|---|
| TF6.1 | `init` — including `-upgrade`, `-reconfigure`, `-migrate-state`, `-backend-config` | | |
| TF6.2 | `plan` — including `-out`, `-target`, `-var-file`, `-refresh=false`, `-destroy` | | |
| TF6.3 | Read a plan properly: create, update, replace, destroy, and forced replacement reasons | | |
| TF6.4 | Explain why applying a saved plan file is the safe pattern | | |
| TF6.5 | `apply` — including `-auto-approve`, `-parallelism`, and targeted apply | | |
| TF6.6 | Explain why `-target` is a break-glass tool, not a workflow | | |
| TF6.7 | `destroy`, and the safeguards you'd want around it | | |
| TF6.8 | `state` subcommands: list, show, mv, rm, pull, push, replace-provider | | |
| TF6.9 | `taint` / `-replace` and the difference between them | | |
| TF6.10 | `output`, including `-json` for downstream consumption | | |
| TF6.11 | `fmt`, `validate`, and `console` for iterating on expressions | | |
| TF6.12 | `graph` and reasoning about the dependency graph | | |
| TF6.13 | `providers`, `version`, and `show -json` for tooling integration | | |
| TF6.14 | `login` / `logout` against a remote backend or registry | | |
| TF6.15 | `force-unlock` and when it's justified | | |
| TF6.16 | Use `TF_LOG` and debug logs to diagnose a provider problem | | |
| TF6.17 | Explain the environment variables that matter (TF_VAR_, TF_CLI_ARGS, TF_IN_AUTOMATION) | | |

## TF7. Secrets & security

| # | Capability | Score | Notes |
|---|---|---|---|
| TF7.1 | Explain why marking a variable sensitive doesn't remove it from state | | |
| TF7.2 | Source secrets at runtime rather than hardcoding them | | |
| TF7.3 | Secure state access: encryption, IAM, least privilege on the backend | | |
| TF7.4 | Authenticate to a cloud provider without long-lived keys (OIDC) | | |
| TF7.5 | Scan Terraform for misconfiguration (tfsec, Checkov, Trivy) | | |
| TF7.6 | Enforce policy as code (Sentinel, OPA, Conftest) | | |
| TF7.7 | Explain the risk of a compromised provider or module from a public registry | | |
| TF7.8 | Prevent a plan from leaking secrets into CI logs | | |
| TF7.9 | Explain who can approve an apply and why that's a security boundary | | |

## TF8. Structure & scaling

| # | Capability | Score | Notes |
|---|---|---|---|
| TF8.1 | Design a repository layout for many environments and accounts | | |
| TF8.2 | Explain environment separation approaches and defend a choice | | |
| TF8.3 | Explain the tradeoff between monolithic and fragmented state | | |
| TF8.4 | Manage dependencies between separately-stated components | | |
| TF8.5 | Use Terragrunt, and explain what problem it solves and its cost | | |
| TF8.6 | Handle very slow plans on large state | | |
| TF8.7 | Explain how you'd roll a change across many accounts safely | | |
| TF8.8 | Explain the platform team's module ownership model | | |
| TF8.9 | Onboard a team to IaC when they're used to the console | | |

## TF9. Automation & CI/CD

| # | Capability | Score | Notes |
|---|---|---|---|
| TF9.1 | Design a pipeline: fmt, validate, lint, scan, plan on PR, apply on merge | | |
| TF9.2 | Post a plan to a PR for review and explain why that's the key control | | |
| TF9.3 | Explain why plan and apply must use the same artifact | | |
| TF9.4 | Handle concurrent pipeline runs against one state | | |
| TF9.5 | Design manual approval gates for production | | |
| TF9.6 | Detect drift on a schedule and decide what to do about it | | |
| TF9.7 | Explain rollback in Terraform terms and why it isn't a real operation | | |
| TF9.8 | Handle a partially applied change after a mid-apply failure | | |
| TF9.9 | Explain ephemeral environments and their teardown discipline | | |

## TF10. Terraform Cloud & Enterprise

| # | Capability | Score | Notes |
|---|---|---|---|
| TF10.1 | Explain the workspace model and how it differs from CLI workspaces | | |
| TF10.2 | Explain remote vs local execution mode and when you'd choose each | | |
| TF10.3 | Configure VCS-driven workflows and speculative plans on PRs | | |
| TF10.4 | Manage variable sets and workspace variables, including sensitive ones | | |
| TF10.5 | Explain run tasks and their place in a governed workflow | | |
| TF10.6 | Write and enforce Sentinel policies | | |
| TF10.7 | Use the private module registry and publishing workflow | | |
| TF10.8 | Configure teams, permissions, and approval requirements | | |
| TF10.9 | Explain agents and why self-hosted execution is needed for private networks | | |
| TF10.10 | Explain state versioning, rollback, and audit in TFC/TFE | | |
| TF10.11 | Explain the cost model and what drives it | | |
| TF10.12 | Explain no-code modules and workspace automation via the API | | |

## TF11. Alternative platforms

| # | Capability | Score | Notes |
|---|---|---|---|
| TF11.1 | Explain what Spacelift adds over a plain CI pipeline | | |
| TF11.2 | Explain Spacelift stacks, contexts, and worker pools | | |
| TF11.3 | Explain Spacelift's OPA-based policies: plan, approval, push, trigger | | |
| TF11.4 | Explain stack dependencies and output sharing in Spacelift | | |
| TF11.5 | Explain drift detection and reconciliation in Spacelift | | |
| TF11.6 | Explain Atlantis and its PR-driven model | | |
| TF11.7 | Explain env0, Scalr, or Digger at a comparison level | | |
| TF11.8 | Build a decision framework: plain CI vs Atlantis vs Spacelift vs TFC/TFE | | |
| TF11.9 | Explain what these platforms cost you in lock-in and complexity | | |
| TF11.10 | Explain how you'd migrate between them | | |

## TF12. Troubleshooting

| # | Capability | Score | Notes |
|---|---|---|---|
| TF12.1 | Diagnose an unexpected forced replacement in a plan | | |
| TF12.2 | Diagnose a perpetual diff that never converges | | |
| TF12.3 | Diagnose a cycle error in the dependency graph | | |
| TF12.4 | Diagnose "resource already exists" on apply | | |
| TF12.5 | Handle a resource deleted outside Terraform | | |
| TF12.6 | Handle an apply that timed out with resources half-created | | |
| TF12.7 | Diagnose provider authentication failures across accounts | | |
| TF12.8 | Diagnose a module version or source resolution failure | | |
| TF12.9 | Debug a `for_each` over an unknown-at-plan-time value | | |
| TF12.10 | Explain what to do when state and reality have diverged badly | | |

## TF13. Judgement

| # | Capability | Score | Notes |
|---|---|---|---|
| TF13.1 | Explain when Terraform isn't the right tool | | |
| TF13.2 | Decide what should and shouldn't be in Terraform | | |
| TF13.3 | Justify a state-splitting strategy for a stated organisation | | |
| TF13.4 | Explain how you'd bring an existing unmanaged estate under IaC | | |
| TF13.5 | Balance guardrails against developer velocity | | |
| TF13.6 | Explain how you'd handle an emergency change that bypasses the pipeline | | |
| TF13.7 | Explain the failure modes of IaC as an organisational practice | | |

---

## Terraform & IaC — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| TF1. IaC fundamentals | 8 | /16 | |
| TF2. Core language | 14 | /28 | |
| TF3. State | 14 | /28 | |
| TF4. Modules | 10 | /20 | |
| TF5. Providers & versioning | 8 | /16 | |
| TF6. CLI & workflow | 17 | /34 | |
| TF7. Secrets & security | 9 | /18 | |
| TF8. Structure & scaling | 9 | /18 | |
| TF9. Automation & CI/CD | 9 | /18 | |
| TF10. Terraform Cloud & Enterprise | 12 | /24 | |
| TF11. Alternative platforms | 10 | /20 | |
| TF12. Troubleshooting | 10 | /20 | |
| TF13. Judgement | 7 | /14 | |
| **Total** | **137** | **/274** | |

---

# Domain 12 — CI/CD, Release & Deployment

Prefixed `C`. Deliberately tool-agnostic — GitHub Actions and Jenkins are separate implementation domains. Terraform pipelines are TF9; database migration sequencing is DB7.

## C1. Fundamentals

| # | Capability | Score | Notes |
|---|---|---|---|
| C1.1 | Explain continuous integration as a practice, not a tool | | |
| C1.2 | Distinguish continuous delivery from continuous deployment | | |
| C1.3 | Explain trunk-based development and its relationship to CI | | |
| C1.4 | Explain why long-lived branches undermine integration | | |
| C1.5 | Explain the value of a fast feedback loop, with a number attached | | |
| C1.6 | Explain build once, promote everywhere, and why rebuilding per environment is wrong | | |
| C1.7 | Explain reproducible builds and what breaks them | | |
| C1.8 | Explain what "done" means when delivery is continuous | | |
| C1.9 | Explain how batch size relates to deployment risk | | |

## C2. Pipeline design

| # | Capability | Score | Notes |
|---|---|---|---|
| C2.1 | Design a pipeline's stages and justify the ordering | | |
| C2.2 | Fail fast — put cheap checks before expensive ones | | |
| C2.3 | Parallelise stages and understand what actually blocks | | |
| C2.4 | Design caching to speed builds without producing stale results | | |
| C2.5 | Explain pipeline as code and why it lives with the application | | |
| C2.6 | Reuse pipeline logic across repos without creating a monolith | | |
| C2.7 | Explain ephemeral vs persistent build agents and the tradeoffs | | |
| C2.8 | Explain what makes a pipeline flaky and how you'd stabilise it | | |
| C2.9 | Set sensible timeouts and concurrency controls | | |
| C2.10 | Explain a pipeline's own observability: duration, failure rate, queue time | | |
| C2.11 | Explain the cost of a slow pipeline in engineer-hours | | |

## C3. Build & artifacts

| # | Capability | Score | Notes |
|---|---|---|---|
| C3.1 | Explain what an immutable artifact is and why it's central | | |
| C3.2 | Version artifacts so any deployment traces to a commit | | |
| C3.3 | Explain semantic versioning and its limits for internal services | | |
| C3.4 | Explain artifact promotion between environments | | |
| C3.5 | Explain artifact repositories and retention policy | | |
| C3.6 | Explain dependency caching vs vendoring | | |
| C3.7 | Explain build provenance and why you'd want it | | |
| C3.8 | Explain how you'd prove what code is running in production right now | | |

## C4. Testing in the pipeline

| # | Capability | Score | Notes |
|---|---|---|---|
| C4.1 | Explain the test pyramid and the cost of inverting it | | |
| C4.2 | Decide which tests belong at which stage | | |
| C4.3 | Explain contract testing and when it beats end-to-end tests | | |
| C4.4 | Explain flaky tests as a trust problem, not just an annoyance | | |
| C4.5 | Explain quality gates and how to set thresholds that aren't theatre | | |
| C4.6 | Explain coverage as a signal and its failure as a target | | |
| C4.7 | Design test data and environments that don't depend on production data | | |
| C4.8 | Explain smoke tests and post-deployment verification | | |
| C4.9 | Explain performance and load testing placement in delivery | | |
| C4.10 | Explain testing in production and what makes it responsible | | |

## C5. Environments

| # | Capability | Score | Notes |
|---|---|---|---|
| C5.1 | Explain what each environment is actually for, and challenge ones that aren't | | |
| C5.2 | Explain environment parity and which differences genuinely matter | | |
| C5.3 | Explain why config, not artifacts, should differ between environments | | |
| C5.4 | Manage environment-specific configuration without duplication | | |
| C5.5 | Explain ephemeral / preview environments per pull request | | |
| C5.6 | Explain the cost and teardown discipline ephemeral environments require | | |
| C5.7 | Explain environment promotion and the gates between stages | | |
| C5.8 | Explain why staging is often misleading, and what to do about it | | |
| C5.9 | Handle production-like data safely in lower environments | | |
| C5.10 | Explain environment ownership and who can deploy where | | |
| C5.11 | Explain how secrets differ per environment and how they're injected | | |

## C6. Release management

| # | Capability | Score | Notes |
|---|---|---|---|
| C6.1 | Explain the difference between deploy and release, and why decoupling them matters | | |
| C6.2 | Explain release versioning and tagging strategy | | |
| C6.3 | Generate a changelog and release notes from commits | | |
| C6.4 | Explain release trains vs on-demand releases | | |
| C6.5 | Explain freeze periods, their rationale, and their cost | | |
| C6.6 | Explain change management and CAB in a regulated context without pretending it doesn't exist | | |
| C6.7 | Explain how you'd satisfy an auditor about who approved what | | |
| C6.8 | Coordinate a release across multiple services with dependencies | | |
| C6.9 | Explain backwards and forwards compatibility as a release requirement | | |
| C6.10 | Explain API versioning and deprecation as a release concern | | |

## C7. Deployment strategies

| # | Capability | Score | Notes |
|---|---|---|---|
| C7.1 | Explain recreate deployment and when downtime is acceptable | | |
| C7.2 | Explain rolling deployment and its intermediate mixed-version state | | |
| C7.3 | Explain blue/green: mechanics, cutover, and cost | | |
| C7.4 | Explain canary: traffic percentage, bake time, and promotion criteria | | |
| C7.5 | Explain shadow / dark traffic and what it can and can't validate | | |
| C7.6 | Explain A/B deployment vs canary — different goals, often confused | | |
| C7.7 | Choose a strategy for a stated system and defend it | | |
| C7.8 | Explain how each strategy handles a stateful workload | | |
| C7.9 | Explain the database constraint that limits blue/green | | |
| C7.10 | Explain connection draining and graceful shutdown during deployment | | |
| C7.11 | Explain how health checks gate a deployment's progress | | |
| C7.12 | Explain the cost of each strategy in infrastructure and complexity | | |

## C8. Progressive delivery

| # | Capability | Score | Notes |
|---|---|---|---|
| C8.1 | Explain feature flags and how they decouple deploy from release | | |
| C8.2 | Explain flag types: release, experiment, ops, permission | | |
| C8.3 | Explain flag debt and the discipline of removing them | | |
| C8.4 | Explain the risk of flags creating untested code path combinations | | |
| C8.5 | Explain automated canary analysis against metrics | | |
| C8.6 | Define promotion and rollback criteria before starting a rollout | | |
| C8.7 | Explain ring-based or percentage-based rollout to user segments | | |
| C8.8 | Explain a kill switch and why it's operationally different from a rollback | | |

## C9. Rollback & recovery

| # | Capability | Score | Notes |
|---|---|---|---|
| C9.1 | Explain rollback vs fix-forward and choose under pressure | | |
| C9.2 | Ensure rollback is actually tested rather than assumed | | |
| C9.3 | Explain what makes a change irreversible | | |
| C9.4 | Explain how a database migration constrains rollback | | |
| C9.5 | Explain automated rollback triggers and their false-positive risk | | |
| C9.6 | Measure and reduce time to restore | | |
| C9.7 | Handle a partially completed deployment | | |
| C9.8 | Explain how you'd deploy safely when rollback isn't possible | | |

## C10. Security & governance in delivery

| # | Capability | Score | Notes |
|---|---|---|---|
| C10.1 | Explain separation of duties in an automated pipeline | | |
| C10.2 | Design approval gates that add safety rather than delay | | |
| C10.3 | Explain least privilege for deployment credentials | | |
| C10.4 | Explain why the pipeline itself is a high-value attack target | | |
| C10.5 | Place security scanning in the pipeline without blocking on noise | | |
| C10.6 | Explain break-glass deployment and its audit requirements | | |
| C10.7 | Produce a deployment audit trail from systems, not spreadsheets | | |
| C10.8 | Explain how compliance requirements change pipeline design | | |

## C11. Metrics & improvement

| # | Capability | Score | Notes |
|---|---|---|---|
| C11.1 | Explain the four DORA metrics and what each reveals | | |
| C11.2 | Explain why deployment frequency and stability are not in tension | | |
| C11.3 | Measure lead time honestly, from commit to production | | |
| C11.4 | Measure change failure rate and define what counts as a failure | | |
| C11.5 | Explain how metrics get gamed and how you'd guard against it | | |
| C11.6 | Identify the bottleneck in a delivery process with evidence | | |
| C11.7 | Make a case for delivery investment in business terms | | |

## C12. Judgement

| # | Capability | Score | Notes |
|---|---|---|---|
| C12.1 | Explain when continuous deployment is inappropriate | | |
| C12.2 | Design delivery for a monolith versus many services | | |
| C12.3 | Explain the platform team's contract with delivery teams | | |
| C12.4 | Explain golden paths and why they beat mandates | | |
| C12.5 | Migrate a team from manual releases to automated delivery | | |
| C12.6 | Explain how you'd introduce change safely into a low-trust environment | | |
| C12.7 | Explain the organisational reasons delivery improvements fail | | |

---

## CI/CD, Release & Deployment — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| C1. Fundamentals | 9 | /18 | |
| C2. Pipeline design | 11 | /22 | |
| C3. Build & artifacts | 8 | /16 | |
| C4. Testing in the pipeline | 10 | /20 | |
| C5. Environments | 11 | /22 | |
| C6. Release management | 10 | /20 | |
| C7. Deployment strategies | 12 | /24 | |
| C8. Progressive delivery | 8 | /16 | |
| C9. Rollback & recovery | 8 | /16 | |
| C10. Security & governance | 8 | /16 | |
| C11. Metrics & improvement | 7 | /14 | |
| C12. Judgement | 7 | /14 | |
| **Total** | **109** | **/218** | |

---

# Domain 13 — GitHub Actions

Prefixed `GA`. Delivery concepts are Domain 12; supply chain security is S7; Terraform pipelines are TF9. This is the tool. GitHub as a collaboration platform (PRs, branch protection, CODEOWNERS) is still a separate outstanding domain.

## GA1. Core model

| # | Capability | Score | Notes |
|---|---|---|---|
| GA1.1 | Explain the hierarchy: workflow, job, step, action | | |
| GA1.2 | Explain where workflows live and how they're discovered | | |
| GA1.3 | Explain that jobs run on separate runners and share nothing by default | | |
| GA1.4 | Explain the runner lifecycle and what's clean at the start of each job | | |
| GA1.5 | Explain the difference between an action and a run step | | |
| GA1.6 | Explain how a workflow run maps to a commit and a ref | | |
| GA1.7 | Read a workflow run's logs and identify which step failed and why | | |

## GA2. Triggers & events

| # | Capability | Score | Notes |
|---|---|---|---|
| GA2.1 | Use the common triggers: push, pull_request, schedule, workflow_dispatch | | |
| GA2.2 | Filter triggers by branch, tag, and path | | |
| GA2.3 | Explain `pull_request` vs `pull_request_target` and the security difference | | |
| GA2.4 | Explain the risk of `pull_request_target` with untrusted code | | |
| GA2.5 | Use `workflow_dispatch` inputs for manual runs | | |
| GA2.6 | Use `workflow_call` to make a workflow reusable | | |
| GA2.7 | Use `workflow_run` to chain workflows and explain its ref gotcha | | |
| GA2.8 | Use `repository_dispatch` for external triggering | | |
| GA2.9 | Explain why scheduled workflows are unreliable on timing and disabled when stale | | |
| GA2.10 | Explain why a workflow didn't trigger — the standard debugging list | | |
| GA2.11 | Explain why one workflow's push doesn't trigger another by default | | |

## GA3. Jobs, steps & control flow

| # | Capability | Score | Notes |
|---|---|---|---|
| GA3.1 | Define job dependencies with `needs` and reason about the resulting graph | | |
| GA3.2 | Pass data between jobs with outputs | | |
| GA3.3 | Use `if` conditions at job and step level | | |
| GA3.4 | Use status check functions: success, failure, always, cancelled | | |
| GA3.5 | Use `continue-on-error` and explain its effect on the run's status | | |
| GA3.6 | Build a matrix, including include and exclude | | |
| GA3.7 | Use `fail-fast` and `max-parallel` deliberately | | |
| GA3.8 | Generate a matrix dynamically from a previous job's output | | |
| GA3.9 | Use concurrency groups to cancel superseded runs | | |
| GA3.10 | Set timeouts at job and step level | | |
| GA3.11 | Use `defaults` and working directory settings | | |
| GA3.12 | Use container jobs and service containers | | |

## GA4. Expressions, contexts & data

| # | Capability | Score | Notes |
|---|---|---|---|
| GA4.1 | Use the contexts confidently: github, env, secrets, needs, matrix, runner, job, steps | | |
| GA4.2 | Explain which contexts are available where, and why some fail at job level | | |
| GA4.3 | Use expression functions: contains, startsWith, format, join, toJSON, fromJSON | | |
| GA4.4 | Explain environment variable precedence across workflow, job, and step | | |
| GA4.5 | Set an output or env var from a step via `$GITHUB_OUTPUT` and `$GITHUB_ENV` | | |
| GA4.6 | Write to the job summary | | |
| GA4.7 | Explain masking and why secrets can still leak through transformation | | |
| GA4.8 | Explain why expressions evaluate before the shell runs, and the injection risk | | |
| GA4.9 | Avoid script injection from untrusted `github.event` values | | |

## GA5. Actions & reuse

| # | Capability | Score | Notes |
|---|---|---|---|
| GA5.1 | Use marketplace actions with correct version references | | |
| GA5.2 | Pin actions to a commit SHA and explain why a tag isn't enough | | |
| GA5.3 | Write a composite action | | |
| GA5.4 | Write a JavaScript or Docker action and know when each is appropriate | | |
| GA5.5 | Design reusable workflows with clear inputs, secrets, and outputs | | |
| GA5.6 | Explain reusable workflow limits: nesting depth, matrix restrictions | | |
| GA5.7 | Choose between a composite action and a reusable workflow | | |
| GA5.8 | Version and release an internal action for other teams | | |
| GA5.9 | Enforce an allowlist of permitted actions at org level | | |

## GA6. Secrets, permissions & OIDC

| # | Capability | Score | Notes |
|---|---|---|---|
| GA6.1 | Manage secrets at repository, environment, and organisation level | | |
| GA6.2 | Explain why secrets aren't available to workflows from forks | | |
| GA6.3 | Explain `GITHUB_TOKEN`, its scope, and its lifetime | | |
| GA6.4 | Set least-privilege `permissions` on the token and explain the default risk | | |
| GA6.5 | Configure OIDC to AWS and assume a role with no stored credentials | | |
| GA6.6 | Write a trust policy that constrains the OIDC subject to a repo, branch, or environment | | |
| GA6.7 | Explain the risk of a trust policy that's too broadly scoped | | |
| GA6.8 | Use a GitHub App token when `GITHUB_TOKEN` isn't sufficient | | |
| GA6.9 | Explain why a workflow needs elevated permissions and how to minimise the grant | | |

## GA7. Environments & deployment

| # | Capability | Score | Notes |
|---|---|---|---|
| GA7.1 | Define environments with protection rules | | |
| GA7.2 | Configure required reviewers and wait timers | | |
| GA7.3 | Restrict which branches can deploy to an environment | | |
| GA7.4 | Use environment-scoped secrets for per-environment credentials | | |
| GA7.5 | Explain deployment concurrency and preventing overlapping deploys | | |
| GA7.6 | Implement a promotion flow across environments | | |
| GA7.7 | Use the deployments API and surface status back to the PR | | |

## GA8. Runners

| # | Capability | Score | Notes |
|---|---|---|---|
| GA8.1 | Explain GitHub-hosted runner types, sizes, and their limits | | |
| GA8.2 | Explain why you'd need self-hosted runners | | |
| GA8.3 | Configure self-hosted runners with labels and groups | | |
| GA8.4 | Explain the serious security risk of self-hosted runners on public repos | | |
| GA8.5 | Run ephemeral runners and explain why persistence is a risk | | |
| GA8.6 | Deploy Actions Runner Controller on Kubernetes with autoscaling | | |
| GA8.7 | Give runners cloud access without static credentials | | |
| GA8.8 | Reason about runner cost versus queue time | | |

## GA9. Caching & artifacts

| # | Capability | Score | Notes |
|---|---|---|---|
| GA9.1 | Configure caching with a sensible key and restore-keys | | |
| GA9.2 | Explain cache scope rules across branches | | |
| GA9.3 | Explain cache size limits and eviction | | |
| GA9.4 | Diagnose a cache that never hits | | |
| GA9.5 | Upload and download artifacts between jobs | | |
| GA9.6 | Explain artifact retention and cost | | |
| GA9.7 | Cache Docker layers effectively in a build job | | |

## GA10. Operations & judgement

| # | Capability | Score | Notes |
|---|---|---|---|
| GA10.1 | Debug a workflow efficiently — debug logging, act, tmate, minimal reproduction | | |
| GA10.2 | Diagnose a flaky workflow and stabilise it | | |
| GA10.3 | Explain billing: minutes, multipliers, storage, and how costs escalate | | |
| GA10.4 | Reduce workflow cost and duration with evidence | | |
| GA10.5 | Enforce org-level policies on Actions usage | | |
| GA10.6 | Explain rate limits and API throttling in workflows | | |
| GA10.7 | Explain the risks of Actions as a supply chain surface | | |
| GA10.8 | Compare GitHub Actions to Jenkins and other CI honestly | | |
| GA10.9 | Explain when Actions is the wrong tool | | |

---

## GitHub Actions — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| GA1. Core model | 7 | /14 | |
| GA2. Triggers & events | 11 | /22 | |
| GA3. Jobs, steps & control flow | 12 | /24 | |
| GA4. Expressions, contexts & data | 9 | /18 | |
| GA5. Actions & reuse | 9 | /18 | |
| GA6. Secrets, permissions & OIDC | 9 | /18 | |
| GA7. Environments & deployment | 7 | /14 | |
| GA8. Runners | 8 | /16 | |
| GA9. Caching & artifacts | 7 | /14 | |
| GA10. Operations & judgement | 9 | /18 | |
| **Total** | **88** | **/176** | |

---

# Domain 14 — Jenkins

Prefixed `J`. Delivery concepts are Domain 12. This domain assumes you may inherit a legacy Jenkins estate as much as build a new one — which is the realistic case.

## J1. Architecture & core concepts

| # | Capability | Score | Notes |
|---|---|---|---|
| J1.1 | Explain the controller/agent architecture and what runs where | | |
| J1.2 | Explain why builds should never run on the controller | | |
| J1.3 | Explain `JENKINS_HOME` and what constitutes Jenkins' state | | |
| J1.4 | Explain the job types: freestyle, pipeline, multibranch, folder, organisation | | |
| J1.5 | Explain why freestyle jobs are considered legacy | | |
| J1.6 | Explain the executor model and how concurrency is limited | | |
| J1.7 | Explain the build queue and why jobs sit in it | | |
| J1.8 | Explain the plugin architecture and the dependency risk it creates | | |

## J2. Pipeline as code

| # | Capability | Score | Notes |
|---|---|---|---|
| J2.1 | Write a declarative Jenkinsfile from scratch | | |
| J2.2 | Explain declarative vs scripted pipeline and when scripted is necessary | | |
| J2.3 | Use `agent` directives, including per-stage agents and docker agents | | |
| J2.4 | Use stages, steps, and post conditions | | |
| J2.5 | Use `when` conditions for conditional stages | | |
| J2.6 | Use `parallel` stages and understand failure behaviour | | |
| J2.7 | Use parameters and explain the first-run parameter problem | | |
| J2.8 | Use `input` for manual approval and explain the executor-blocking issue | | |
| J2.9 | Configure `options`: timeout, retry, buildDiscarder, disableConcurrentBuilds | | |
| J2.10 | Use environment directives and credential bindings | | |
| J2.11 | Use `script` blocks and explain why minimising them matters | | |
| J2.12 | Explain the Groovy sandbox and script approval | | |
| J2.13 | Explain CPS serialisation and why some Groovy fails in pipelines | | |
| J2.14 | Archive artifacts and publish test results | | |

## J3. Shared libraries

| # | Capability | Score | Notes |
|---|---|---|---|
| J3.1 | Explain the shared library structure: vars, src, resources | | |
| J3.2 | Write a custom step in `vars` | | |
| J3.3 | Write and use a class in `src` | | |
| J3.4 | Configure global vs folder-level libraries | | |
| J3.5 | Version a library and pin consumers to a tag | | |
| J3.6 | Explain implicit loading and its risk | | |
| J3.7 | Test a shared library | | |
| J3.8 | Design a library that standardises pipelines without becoming a framework nobody understands | | |

## J4. Multibranch & SCM

| # | Capability | Score | Notes |
|---|---|---|---|
| J4.1 | Configure a multibranch pipeline with branch discovery | | |
| J4.2 | Configure PR discovery and the merge vs head strategy | | |
| J4.3 | Explain branch indexing and why a branch didn't appear | | |
| J4.4 | Configure webhooks and explain why polling is a poor substitute | | |
| J4.5 | Configure orphaned item retention | | |
| J4.6 | Report build status back to the SCM | | |
| J4.7 | Manage SCM credentials securely | | |

## J5. Agents & scaling

| # | Capability | Score | Notes |
|---|---|---|---|
| J5.1 | Connect agents via SSH, JNLP, and understand the difference | | |
| J5.2 | Use labels to route jobs to appropriate agents | | |
| J5.3 | Configure the Kubernetes plugin for ephemeral pod agents | | |
| J5.4 | Write a pod template with multiple containers | | |
| J5.5 | Configure EC2 or cloud agents with autoscaling | | |
| J5.6 | Explain the risk of long-lived agents accumulating state | | |
| J5.7 | Manage agent workspaces and disk consumption | | |
| J5.8 | Diagnose an agent that won't connect or keeps dropping | | |

## J6. Credentials & security

| # | Capability | Score | Notes |
|---|---|---|---|
| J6.1 | Use the credentials store and the correct binding for each type | | |
| J6.2 | Scope credentials to folders rather than globally | | |
| J6.3 | Explain how credentials leak through logs despite masking | | |
| J6.4 | Configure authentication and authorisation strategies | | |
| J6.5 | Configure matrix or role-based authorisation | | |
| J6.6 | Explain why script approval is a privilege escalation path | | |
| J6.7 | Explain the security risk of an internet-exposed Jenkins | | |
| J6.8 | Keep Jenkins and plugins patched, and explain the CVE exposure | | |
| J6.9 | Integrate an external secrets manager rather than storing secrets in Jenkins | | |
| J6.10 | Explain audit logging and tracking who changed a job | | |

## J7. Operations & maintenance

| # | Capability | Score | Notes |
|---|---|---|---|
| J7.1 | Back up and restore `JENKINS_HOME` | | |
| J7.2 | Upgrade Jenkins and plugins with a rollback path | | |
| J7.3 | Diagnose a plugin conflict after upgrade | | |
| J7.4 | Manage build retention and disk usage | | |
| J7.5 | Tune JVM heap and diagnose controller memory pressure | | |
| J7.6 | Use Configuration as Code (JCasC) to define Jenkins declaratively | | |
| J7.7 | Use Job DSL to generate jobs programmatically | | |
| J7.8 | Explain why a click-configured Jenkins becomes unmaintainable | | |
| J7.9 | Explain HA options for Jenkins and their limitations | | |
| J7.10 | Monitor Jenkins: queue depth, executor utilisation, build duration | | |
| J7.11 | Use the script console safely, and explain why it's dangerous | | |

## J8. Troubleshooting

| # | Capability | Score | Notes |
|---|---|---|---|
| J8.1 | Diagnose a build stuck in the queue | | |
| J8.2 | Diagnose a hung build and kill it cleanly | | |
| J8.3 | Diagnose a controller running out of memory | | |
| J8.4 | Diagnose a workspace or disk space failure | | |
| J8.5 | Diagnose a pipeline failing only on one agent | | |
| J8.6 | Diagnose a shared library resolution failure | | |
| J8.7 | Read Jenkins logs and thread dumps | | |
| J8.8 | Diagnose a webhook that isn't triggering builds | | |

## J9. Judgement & migration

| # | Capability | Score | Notes |
|---|---|---|---|
| J9.1 | Explain honestly where Jenkins still wins over hosted CI | | |
| J9.2 | Explain the total cost of ownership of self-hosted Jenkins | | |
| J9.3 | Assess an inherited Jenkins estate and prioritise what to fix | | |
| J9.4 | Plan a migration from freestyle jobs to pipeline as code | | |
| J9.5 | Plan a migration from Jenkins to another CI system incrementally | | |
| J9.6 | Explain how you'd reduce plugin sprawl safely | | |
| J9.7 | Explain how you'd standardise pipelines across many teams | | |

---

## Jenkins — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| J1. Architecture & core concepts | 8 | /16 | |
| J2. Pipeline as code | 14 | /28 | |
| J3. Shared libraries | 8 | /16 | |
| J4. Multibranch & SCM | 7 | /14 | |
| J5. Agents & scaling | 8 | /16 | |
| J6. Credentials & security | 10 | /20 | |
| J7. Operations & maintenance | 11 | /22 | |
| J8. Troubleshooting | 8 | /16 | |
| J9. Judgement & migration | 7 | /14 | |
| **Total** | **81** | **/162** | |

---

# Domain 15 — Observability, Performance & Reliability

Prefixed `O`. Cross-references: SLO philosophy, alert design, runbooks, retries and chaos are T7; incident method is T1–T6; CloudWatch specifics are A9; Kubernetes debugging is K9; database metrics are DB12. This domain is telemetry itself, performance engineering, and reliability patterns.

## O1. Foundations

| # | Capability | Score | Notes |
|---|---|---|---|
| O1.1 | Explain observability vs monitoring — known unknowns vs unknown unknowns | | |
| O1.2 | Explain the three pillars and why "three pillars" is an oversimplification | | |
| O1.3 | Explain cardinality and why it drives cost and system limits | | |
| O1.4 | Explain sampling and what it costs you diagnostically | | |
| O1.5 | Explain the difference between white-box and black-box monitoring | | |
| O1.6 | Explain why you instrument for questions you haven't thought of yet | | |
| O1.7 | Explain correlation across signals via shared IDs and consistent labelling | | |
| O1.8 | Explain the build vs buy decision for an observability stack | | |

## O2. Metrics

| # | Capability | Score | Notes |
|---|---|---|---|
| O2.1 | Explain the metric types: counter, gauge, histogram, summary | | |
| O2.2 | Choose the right type for a stated measurement | | |
| O2.3 | Explain why averages hide the problem and percentiles matter | | |
| O2.4 | Explain why you can't average percentiles across instances | | |
| O2.5 | Explain histogram buckets and the cost of getting them wrong | | |
| O2.6 | Explain push vs pull collection models | | |
| O2.7 | Design labels that stay useful without exploding cardinality | | |
| O2.8 | Explain aggregation, downsampling, and retention tiers | | |
| O2.9 | Explain the RED method for services | | |
| O2.10 | Explain the USE method for resources | | |
| O2.11 | Explain the four golden signals and how they map to RED/USE | | |

## O3. Prometheus & query languages

| # | Capability | Score | Notes |
|---|---|---|---|
| O3.1 | Explain Prometheus architecture: scraping, TSDB, service discovery | | |
| O3.2 | Configure scrape targets and relabelling | | |
| O3.3 | Write PromQL: selectors, matchers, and range vectors | | |
| O3.4 | Use `rate` and `irate` correctly, and explain the difference | | |
| O3.5 | Explain why `rate` on a gauge is wrong | | |
| O3.6 | Aggregate with `sum by` and `without` | | |
| O3.7 | Compute a percentile with `histogram_quantile` and explain its approximation | | |
| O3.8 | Write a ratio query for error rate or availability | | |
| O3.9 | Use recording rules and explain when they're needed | | |
| O3.10 | Explain staleness and gaps in scraped data | | |
| O3.11 | Explain Prometheus HA, federation, and long-term storage options | | |
| O3.12 | Explain exporters and write or configure one | | |
| O3.13 | Explain the pushgateway and why it's usually the wrong answer | | |

## O4. Logging

| # | Capability | Score | Notes |
|---|---|---|---|
| O4.1 | Explain structured logging and why it beats free text | | |
| O4.2 | Design log levels and explain what belongs at each | | |
| O4.3 | Include correlation and trace IDs in every log line | | |
| O4.4 | Explain the pipeline: emit, collect, ship, parse, index, retain | | |
| O4.5 | Configure a collector or agent (Fluent Bit, Vector, or similar) | | |
| O4.6 | Explain why logging to stdout is the containerised convention | | |
| O4.7 | Explain log cost drivers and how to reduce volume without losing signal | | |
| O4.8 | Design retention against operational, cost, and compliance needs | | |
| O4.9 | Prevent secrets and PII from reaching logs | | |
| O4.10 | Write an effective query in your log platform to answer an incident question | | |
| O4.11 | Explain when a log should have been a metric | | |

## O5. Tracing

| # | Capability | Score | Notes |
|---|---|---|---|
| O5.1 | Explain traces, spans, and parent-child relationships | | |
| O5.2 | Explain context propagation across service boundaries | | |
| O5.3 | Explain W3C trace context and header propagation | | |
| O5.4 | Explain head-based vs tail-based sampling and their tradeoffs | | |
| O5.5 | Read a trace waterfall and identify the latency contributor | | |
| O5.6 | Explain span attributes and events, and what's worth attaching | | |
| O5.7 | Explain why a trace breaks — a service that doesn't propagate context | | |
| O5.8 | Explain what tracing tells you that metrics and logs can't | | |
| O5.9 | Explain the overhead cost of tracing | | |

## O6. Instrumentation & OpenTelemetry

| # | Capability | Score | Notes |
|---|---|---|---|
| O6.1 | Explain the OpenTelemetry model: API, SDK, collector, exporters | | |
| O6.2 | Explain auto-instrumentation and its limits | | |
| O6.3 | Add manual instrumentation for a business-meaningful operation | | |
| O6.4 | Deploy and configure an OTel collector with processors and pipelines | | |
| O6.5 | Explain the collector's role in decoupling apps from backends | | |
| O6.6 | Explain semantic conventions and why consistency matters more than completeness | | |
| O6.7 | Explain vendor neutrality as an argument for OTel | | |
| O6.8 | Instrument a platform component teams depend on | | |

## O7. Dashboards & visualisation

| # | Capability | Score | Notes |
|---|---|---|---|
| O7.1 | Build a dashboard that answers a specific question rather than showing everything | | |
| O7.2 | Design a dashboard hierarchy: overview, service, deep dive | | |
| O7.3 | Use variables and templating for reusable dashboards | | |
| O7.4 | Choose the right visualisation for the data | | |
| O7.5 | Explain why heatmaps beat line graphs for latency distributions | | |
| O7.6 | Manage dashboards as code | | |
| O7.7 | Explain why most dashboards go unused and how to avoid it | | |

## O8. Alerting in practice

Philosophy and design are T7.3–T7.5; this is the mechanics.

| # | Capability | Score | Notes |
|---|---|---|---|
| O8.1 | Write an alerting rule with a sensible `for` duration | | |
| O8.2 | Explain flapping and how to damp it | | |
| O8.3 | Configure routing, grouping, inhibition, and silences | | |
| O8.4 | Implement multi-window multi-burn-rate SLO alerting | | |
| O8.5 | Configure escalation policies and on-call schedules | | |
| O8.6 | Write an alert that links to a runbook and includes context | | |
| O8.7 | Audit alert volume and retire alerts that never lead to action | | |

## O9. Performance: CPU

| # | Capability | Score | Notes |
|---|---|---|---|
| O9.1 | Distinguish user, system, iowait, steal, and idle time | | |
| O9.2 | Interpret run queue length and context switch rate | | |
| O9.3 | Explain CPU steal on virtualised or shared hosts | | |
| O9.4 | Explain how cgroup CPU quota causes throttling despite idle host CPU | | |
| O9.5 | Diagnose a process consuming CPU and identify which thread | | |
| O9.6 | Explain why a multithreaded app doesn't scale linearly with cores | | |
| O9.7 | Explain cache locality and NUMA effects at a working level | | |
| O9.8 | Explain the difference between CPU-bound and lock-contended | | |

## O10. Performance: memory

| # | Capability | Score | Notes |
|---|---|---|---|
| O10.1 | Distinguish RSS, virtual size, shared memory, and working set | | |
| O10.2 | Explain page cache and why "used memory" looks alarming and isn't | | |
| O10.3 | Explain swapping and the difference between swap use and swap thrashing | | |
| O10.4 | Diagnose a memory leak and distinguish it from a growing cache | | |
| O10.5 | Explain garbage collection and how GC pauses appear as latency spikes | | |
| O10.6 | Tune JVM or runtime heap sensibly, including container awareness | | |
| O10.7 | Explain memory fragmentation | | |
| O10.8 | Explain the OOM killer's selection logic and read the evidence | | |
| O10.9 | Set a container memory limit from measurement, and explain the headroom | | |

## O11. Performance: IO, storage & network

| # | Capability | Score | Notes |
|---|---|---|---|
| O11.1 | Distinguish IOPS, throughput, and latency as separate constraints | | |
| O11.2 | Explain queue depth and its relationship to latency | | |
| O11.3 | Diagnose IO saturation and identify the responsible process | | |
| O11.4 | Explain random vs sequential access and why it matters for cost | | |
| O11.5 | Explain burst credits and the cliff when they exhaust | | |
| O11.6 | Explain filesystem caching and the durability implication of buffered writes | | |
| O11.7 | Explain bandwidth vs latency vs packet loss as distinct network problems | | |
| O11.8 | Explain how TCP window size and RTT bound throughput | | |
| O11.9 | Diagnose whether slowness is network or application | | |

## O12. Latency & throughput

| # | Capability | Score | Notes |
|---|---|---|---|
| O12.1 | Explain the relationship between utilisation and queueing delay | | |
| O12.2 | Explain why latency degrades non-linearly near saturation | | |
| O12.3 | Explain tail latency and why p99 matters more than p50 | | |
| O12.4 | Explain tail amplification when one request fans out to many | | |
| O12.5 | Explain coordinated omission in load testing | | |
| O12.6 | Break an end-to-end latency budget down by component | | |
| O12.7 | Explain Little's Law and apply it to concurrency sizing | | |
| O12.8 | Explain where connection setup, TLS, and DNS sit in a latency budget | | |

## O13. Profiling, benchmarking & load testing

| # | Capability | Score | Notes |
|---|---|---|---|
| O13.1 | Profile a running application to find the hot path | | |
| O13.2 | Read a flame graph | | |
| O13.3 | Explain continuous profiling and its production overhead | | |
| O13.4 | Explain sampling vs instrumenting profilers | | |
| O13.5 | Design a benchmark that isn't misleading | | |
| O13.6 | Design a load test with realistic traffic shape | | |
| O13.7 | Explain load vs stress vs soak vs spike testing | | |
| O13.8 | Identify the bottleneck a load test revealed rather than just the failure point | | |
| O13.9 | Explain the risks and value of load testing against production | | |
| O13.10 | Optimise something and prove the improvement with before-and-after data | | |

## O14. Capacity & scaling

| # | Capability | Score | Notes |
|---|---|---|---|
| O14.1 | Forecast capacity from growth trends | | |
| O14.2 | Determine headroom requirements and justify them | | |
| O14.3 | Explain vertical vs horizontal scaling limits for a stated workload | | |
| O14.4 | Explain what makes a system scale sub-linearly | | |
| O14.5 | Explain Amdahl's law informally and its practical consequence | | |
| O14.6 | Plan for a known traffic event | | |
| O14.7 | Explain quota and limit exhaustion as a capacity failure | | |
| O14.8 | Balance cost against headroom explicitly | | |

## O15. Reliability patterns

Retries, timeouts, circuit breakers and chaos are T7.6–T7.9; these are the design-level complements.

| # | Capability | Score | Notes |
|---|---|---|---|
| O15.1 | Explain redundancy, failure domains, and correlated failure | | |
| O15.2 | Explain why redundancy without independence buys little | | |
| O15.3 | Explain load shedding and prioritising traffic under stress | | |
| O15.4 | Explain rate limiting and throttling as protective mechanisms | | |
| O15.5 | Explain the bulkhead pattern and resource isolation | | |
| O15.6 | Explain queueing as a buffer and its limits | | |
| O15.7 | Explain graceful degradation with a concrete example | | |
| O15.8 | Explain health check design and the danger of checking too much | | |
| O15.9 | Explain how a retry storm turns a small failure into an outage | | |
| O15.10 | Explain jitter and why synchronised clients are dangerous | | |
| O15.11 | Explain cascading failure and where to place the circuit breaker | | |
| O15.12 | Explain the tradeoff between availability and consistency in a real design | | |

## O16. Judgement

| # | Capability | Score | Notes |
|---|---|---|---|
| O16.1 | Explain observability cost drivers and reduce spend without losing signal | | |
| O16.2 | Decide what's worth instrumenting and what isn't | | |
| O16.3 | Explain the platform team's observability contract with application teams | | |
| O16.4 | Assess an existing observability stack and prioritise improvements | | |
| O16.5 | Explain how you'd instrument a system you didn't build | | |
| O16.6 | Explain when "just add monitoring" is the wrong answer | | |
| O16.7 | Explain how you'd know your observability is actually working | | |

---

## Observability, Performance & Reliability — scoring summary

| Section | Items | Total | % |
|---|---|---|---|
| O1. Foundations | 8 | /16 | |
| O2. Metrics | 11 | /22 | |
| O3. Prometheus & query languages | 13 | /26 | |
| O4. Logging | 11 | /22 | |
| O5. Tracing | 9 | /18 | |
| O6. Instrumentation & OpenTelemetry | 8 | /16 | |
| O7. Dashboards & visualisation | 7 | /14 | |
| O8. Alerting in practice | 7 | /14 | |
| O9. Performance: CPU | 8 | /16 | |
| O10. Performance: memory | 9 | /18 | |
| O11. Performance: IO, storage & network | 9 | /18 | |
| O12. Latency & throughput | 8 | /16 | |
| O13. Profiling, benchmarking & load testing | 10 | /20 | |
| O14. Capacity & scaling | 8 | /16 | |
| O15. Reliability patterns | 12 | /24 | |
| O16. Judgement | 7 | /14 | |
| **Total** | **145** | **/290** | |

---

# Gap list

Anything scored 0 or 1 that you'd expect to hit in a live exercise or on-call. A gap isn't closed when you've read about it — it's closed when there's evidence.

| Item | Domain | Current | Target | Practice task | Evidence |
|---|---|---|---|---|---|
| | | | | | |
