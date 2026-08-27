# Linux — Answer Key

Companion to Domain 2 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*. Where an item is judgement rather than recall, the answer gives the reasoning and the tradeoff.

---

## L1. Filesystem & navigation

**L1.1 — Navigate and manipulate files/permissions**

`cd`, `ls -lah`, `cp -r`, `mv`, `rm -rf`, `mkdir -p`, `touch`, `ln -s`. Worth knowing: `mv` across filesystems is a copy-then-delete (not atomic); within a filesystem it's a rename (atomic). `cp -a` preserves everything — mode, ownership, timestamps, symlinks — and is what you want for backups. `rm -rf` has no undo and no trash.

**L1.2 — The Filesystem Hierarchy Standard**

- `/etc` — system-wide configuration. Text files, no binaries.
- `/var` — variable data: logs (`/var/log`), spools, caches, databases. The directory that fills up.
- `/usr` — installed software: `/usr/bin`, `/usr/lib`, `/usr/local` for locally-compiled things.
- `/opt` — self-contained third-party packages.
- `/proc` — virtual filesystem exposing kernel and process state. Not on disk.
- `/sys` — virtual filesystem for device and kernel object attributes.
- `/tmp` — world-writable, cleared on reboot (often tmpfs, i.e. RAM).
- `/home` — user directories.
- `/dev` — device nodes.

The operationally relevant point: `/var` and `/tmp` are the ones that fill, and `/proc` is where you look when a tool doesn't tell you enough.

**L1.3 — Paths**

Absolute starts at `/`; relative resolves from the current directory. `.` is here, `..` is parent, `~` is your home, `~user` is theirs. `cd -` returns to the previous directory. In scripts, always use absolute paths or resolve them explicitly — relative paths break the moment the script runs from a different cwd (cron being the classic case).

**L1.4 — Symlinks vs hard links**

A **symlink** is a file containing a path. It can cross filesystems, can point at directories, and breaks if the target moves. A **hard link** is a second directory entry pointing at the same inode. It can't cross filesystems, can't link directories, and the data survives until the last link is removed.

```bash
ln -s /target /link      # symlink
ln /target /link         # hard link
ls -li                   # inode numbers reveal hard links
```

Practical relevance: deleting a file that a process still has open frees no space until the process closes it — same principle as link counting, and the cause of "df says full but du doesn't agree" (L6.2).

**L1.5 — `find`**

```bash
find /var/log -name "*.log" -mtime +30 -delete
find . -type f -size +100M
find /app -user deploy -perm -o+w
find . -name "*.tmp" -exec rm {} +
```

`-exec ... +` batches arguments (efficient); `-exec ... \;` runs once per file. `-mtime +30` is "modified more than 30 days ago". Test with `-print` before adding `-delete`.

**L1.6 — Search file contents**

```bash
grep -r "pattern" /etc
grep -rn --include="*.py" "TODO" .
rg "pattern"              # ripgrep: faster, respects .gitignore
```

`-n` line numbers, `-i` case-insensitive, `-l` filenames only, `-C 3` three lines of context.

**L1.7 — Archive and compress**

```bash
tar -czf archive.tar.gz dir/       # create gzipped
tar -xzf archive.tar.gz            # extract
tar -tzf archive.tar.gz            # list without extracting
```

Always list before extracting an archive from an untrusted source — tar can contain absolute paths or `../` traversal that writes outside the target directory. `tar` bundles, `gzip`/`bzip2`/`xz` compress; `zip` does both but preserves Unix permissions less reliably.

**L1.8 — `scp` vs `rsync`**

```bash
rsync -avz --progress src/ user@host:/dest/
rsync -avz --delete --dry-run src/ host:/dest/
```

`rsync` wins because it transfers only differences, resumes, preserves attributes with `-a`, can delete removed files with `--delete`, and offers `--dry-run`. `scp` copies everything every time and is now deprecated in favour of `sftp`/`rsync`. Note the trailing slash: `src/` copies contents, `src` copies the directory itself.

**L1.9 — File type and metadata**

```bash
file binary               # identifies type from magic bytes, not extension
stat file                 # inode, size, permissions, atime/mtime/ctime
```

`stat` distinguishes mtime (content changed), ctime (inode changed — includes permission changes), and atime (last read, often disabled for performance).

---

## L2. Permissions, users & access

**L2.1 — Octal and symbolic permissions**

Three triplets: owner, group, other. Read 4, write 2, execute 1.

```bash
chmod 644 file        # rw-r--r--
chmod 755 script      # rwxr-xr-x
chmod u+x,go-w file   # symbolic
```

`755` for executables and directories, `644` for regular files, `600` for secrets and private keys, `640` when a group needs read.

**L2.2 — Permissions on files vs directories**

Different meanings, and this is the item people fumble:

| Bit | On a file | On a directory |
|---|---|---|
| `r` | read contents | list entries |
| `w` | modify contents | create/delete/rename entries |
| `x` | execute | traverse into it, access entries by name |

Consequences: you can delete a file you have no write permission on, if you have write on its directory. And `r` without `x` on a directory lets you list names but not `stat` them. `x` without `r` lets you access a known path but not enumerate.

**L2.3 — Ownership**

```bash
chown user:group file
chown -R deploy:deploy /app
chgrp group file
```

Only root can give a file away to another user.

**L2.4 — setuid, setgid, sticky**

- **setuid** (`chmod u+s`, shows as `rws`) — the binary runs as its owner, not the caller. `/usr/bin/passwd` is the canonical example. A major privilege-escalation surface; audit with `find / -perm -4000`.
- **setgid** on a binary — runs as the owning group. On a *directory* — new files inherit the directory's group, which is how shared project directories work.
- **sticky bit** (`chmod +t`) on a directory — only the file's owner can delete it, regardless of directory write permission. That's what makes `/tmp` world-writable but safe.

**L2.5 — Users, groups, and the files behind them**

```bash
useradd -m -s /bin/bash alice
usermod -aG docker alice      # -a is essential; without it you REPLACE groups
groups alice
id alice
```

`/etc/passwd` — username, UID, GID, home, shell (world-readable). `/etc/shadow` — password hashes, root-only. `/etc/group` — group membership. A UID of 0 means root regardless of the name. Note: `usermod -aG docker` is effectively granting root, since the Docker socket allows container escape to the host.

**L2.6 — sudoers**

Always edit with `visudo` — it syntax-checks before saving, and a broken sudoers file can lock everyone out. Prefer dropping files in `/etc/sudoers.d/`. Scope narrowly:

```
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart myapp
```

Avoid `ALL=(ALL) NOPASSWD: ALL`. Also be aware that allowing an editor, or any command with a shell escape, is equivalent to full root.

**L2.7 — SSH key auth**

`~/.ssh/authorized_keys` on the *server* lists public keys permitted to log in as that user. `~/.ssh/known_hosts` on the *client* records server host keys, so you're warned if a host's identity changes (possible MITM). Permissions matter: `~/.ssh` must be `700`, `authorized_keys` `600`, or sshd silently refuses.

**L2.8 — Harden sshd**

In `/etc/ssh/sshd_config`:

```
PasswordAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
AllowUsers deploy admin
```

Then `sshd -t` to validate and `systemctl reload sshd`. **Keep an existing session open** while testing a new one — reloading a broken config with password auth disabled and no working key locks you out. Changing the port reduces log noise but isn't security.

**L2.9 — umask**

A mask of bits to *remove* from default permissions. Default file creation is 666, directories 777. With `umask 022`: files become 644, directories 755. With `umask 077`: 600 and 700 — appropriate for anything handling secrets. Set per-service in systemd with `UMask=`.

**L2.10 — "Permission denied" that isn't file permissions**

Check in order: the file's mode and ownership; the *directory* traversal permissions on every parent; then SELinux (`getenforce`, `ausearch -m avc`, `ls -Z`) or AppArmor (`aa-status`, `dmesg | grep -i apparmor`). SELinux denials are the classic "everything looks right and it still fails" — the give-away is a denial in the audit log with correct-looking file permissions. Temporarily `setenforce 0` to confirm the diagnosis, then fix the context with `restorecon` or a policy rather than leaving it permissive.

---

## L3. Text processing & the shell

**L3.1 — Redirection**

```bash
cmd > file          # stdout, truncate
cmd >> file         # stdout, append
cmd 2> file         # stderr
cmd > file 2>&1     # both to file — order matters
cmd &> file         # both (bash shorthand)
cmd < file          # stdin from file
cmd > /dev/null 2>&1
```

`2>&1` means "make fd 2 point where fd 1 currently points" — so `cmd 2>&1 > file` does *not* do what people expect (stderr goes to the original stdout, stdout goes to the file).

**L3.2 — Exit codes and chaining**

0 is success, non-zero is failure. `$?` holds the last exit code. `a && b` runs b only if a succeeded; `a || b` runs b only if a failed; `a ; b` runs b regardless. In pipelines, `$?` is the *last* command's status unless `set -o pipefail` is on — that's the whole reason pipefail exists.

**L3.3 — `grep`**

```bash
grep -E "error|warn" app.log     # extended regex
grep -v "healthcheck" app.log    # invert
grep -C 3 "exception" app.log    # 3 lines of context
grep -c "500" access.log         # count matches
grep -o "user=[0-9]*" app.log    # print only the match
```

**L3.4 — `sed`**

```bash
sed 's/old/new/g' file           # substitute, global
sed -i.bak 's/old/new/g' file    # in place, with backup
sed -n '10,20p' file             # print a line range
sed '/pattern/d' file            # delete matching lines
```

Always `-i.bak` rather than bare `-i` when you care about the file. Note macOS/BSD `sed` requires an argument to `-i`, GNU doesn't — a common portability bug in scripts.

**L3.5 — `awk`**

```bash
awk '{print $1, $4}' access.log
awk -F: '{print $1}' /etc/passwd
awk '$9 == 500 {count++} END {print count}' access.log
awk '{sum += $3} END {print sum/NR}' data.txt
```

`$0` is the whole line, `$1..$n` the fields, `NR` the record number, `NF` the field count. `awk` earns its place when you need conditionals or accumulation — otherwise `cut` is clearer.

**L3.6 — The rest of the toolkit**

```bash
cut -d: -f1 /etc/passwd
sort -k2 -n file
sort | uniq -c | sort -rn        # the canonical "count and rank" idiom
tr -d '\r' < file                # strip carriage returns
wc -l file
head -20 / tail -20
```

`uniq` only collapses *adjacent* duplicates, so it must follow `sort`.

**L3.7 — `jq`**

```bash
jq '.items[] | .name' data.json
jq -r '.token'                       # raw output, no quotes
jq '.[] | select(.status=="failed")'
jq -r '.data | to_entries[] | "\(.key)=\(.value)"'
aws ec2 describe-instances | jq -r '.Reservations[].Instances[].InstanceId'
```

`-r` matters constantly — without it you get quoted strings that break downstream commands.

**L3.8 — `yq`**

Same idea for YAML. Useful against Kubernetes manifests, pipeline definitions, and compose files:

```bash
yq '.spec.containers[].image' deployment.yaml
yq -i '.spec.replicas = 3' deployment.yaml
```

Note there are two different `yq` implementations (Go and Python) with different syntax — check which is installed.

**L3.9 — `xargs`**

```bash
find . -name "*.log" -print0 | xargs -0 rm
cat urls.txt | xargs -n1 -P8 curl -sO       # 8 in parallel
echo "a b c" | xargs -n1 echo
```

`-print0`/`-0` handles filenames with spaces. `-P` gives cheap parallelism. `-n1` runs the command once per argument rather than batching.

**L3.10 — A real one-liner**

"Top 10 IPs hitting 500s":

```bash
awk '$9 == 500 {print $1}' access.log | sort | uniq -c | sort -rn | head -10
```

The pattern — extract, sort, count, rank — covers most log questions you'll be asked to answer live.

**L3.11 — Quoting and command substitution**

`$(cmd)` is command substitution (prefer over backticks — it nests). Double quotes allow expansion; single quotes are literal. **Always quote variables**: `"$file"` not `$file`. Unquoted, a value containing spaces splits into multiple arguments, and one containing `*` gets glob-expanded. `"$@"` preserves arguments individually; `"$*"` joins them into one string.

**L3.12 — Job control**

```bash
cmd &            # background
jobs
fg %1 / bg %1
Ctrl+Z           # suspend
nohup cmd &      # survive logout
tmux / screen    # persistent sessions
```

`nohup` survives hangup but you lose interactivity; `tmux` is the better answer for anything long-running you might need to reattach to — reconnect with `tmux attach`.

---

## L4. Processes & signals

**L4.1 — Inspect processes**

```bash
ps aux                       # BSD style, all processes
ps -ef                       # System V style
ps aux --sort=-%mem | head
pgrep -a nginx
ps -eLf                      # include threads
```

`ps` is a snapshot; `top` is continuous.

**L4.2 — Reading `top`/`htop`**

Key columns: `%CPU` (of one core, so >100% means multithreaded), `%MEM`, `RES` (resident memory, the real number), `VIRT` (virtual — usually alarming and meaningless), `S` (state: R running, S sleeping, D uninterruptible sleep, Z zombie), `TIME+` (cumulative CPU).

`D` state is the interesting one — uninterruptible sleep almost always means blocked on IO, and a pile of `D` processes points at storage, not CPU.

**L4.3 — Signals**

- `SIGTERM` (15) — polite request to stop. Catchable. The default for `kill`. Lets the process flush, close connections, deregister.
- `SIGKILL` (9) — immediate, uncatchable, kernel-level. No cleanup. Risks corrupt state and orphaned resources.
- `SIGHUP` (1) — historically "terminal closed"; by convention many daemons use it to reload config without restarting.
- `SIGINT` (2) — Ctrl+C.
- `SIGSTOP`/`SIGCONT` — suspend and resume.

Correct order: TERM, wait, then KILL only if it hangs.

**L4.4 — Killing**

```bash
kill <pid>              # TERM
kill -9 <pid>           # KILL
pkill -f "pattern"      # match full command line
killall nginx
```

`-9` is a last resort because the process gets no chance to clean up — it can leave lock files, partial writes, or unreleased resources. If a process only dies with `-9`, that's a symptom worth investigating (usually stuck in `D` state).

**L4.5 — Process tree, PID 1, orphans, zombies**

`pstree -p` shows the hierarchy. PID 1 is init/systemd; it adopts orphans and reaps them. An **orphan** is a process whose parent died — harmless, it gets reparented. A **zombie** has exited but its parent hasn't called `wait()` to collect the exit status; it holds only a process table entry, no memory. Zombies can't be killed — you kill or fix the parent. Many zombies means a buggy parent, and in containers it means PID 1 isn't reaping (the `--init`/tini problem).

**L4.6 — nice and renice**

`nice -n 10 cmd` starts a process at lower priority; `renice -n 10 -p <pid>` changes it. Range is -20 (highest) to 19 (lowest); negative values need root. Only matters under CPU contention. `ionice` is the IO-priority equivalent, often more useful for backup jobs.

**L4.7 — What's holding a file or port**

```bash
lsof -i :8080            # what's on this port
lsof /var/log/app.log    # what has this file open
lsof -p <pid>
fuser -k 8080/tcp        # kill whatever holds the port
lsof | grep deleted      # deleted-but-open files
```

That last one is the fix for "disk full but `du` shows nothing" — see L6.2.

**L4.8 — `strace`**

```bash
strace -p <pid>
strace -f -e trace=openat,connect ./app
strace -c ./app          # summary count by syscall
```

Shows every system call. Use it when a process is silently failing or hanging and logs tell you nothing — you'll typically see it blocked on a `read`, retrying a `connect`, or failing to `openat` a config file it's looking for in an unexpected place. It slows the process significantly, so use it deliberately in production.

**L4.9 — The OOM killer**

When the kernel can't satisfy an allocation, it kills a process chosen by an `oom_score` heuristic weighted by memory footprint. Find the evidence:

```bash
dmesg -T | grep -i "killed process"
journalctl -k | grep -i oom
grep -i oom /var/log/syslog
```

The killed process's own logs usually show nothing — it received SIGKILL with no warning, which is exactly why you check the kernel log. In containers, an OOM kill against the cgroup limit shows as exit code 137.

---

## L5. Resources & performance

**L5.1 — Load average**

Three numbers: 1, 5, and 15-minute averages of runnable *plus* uninterruptible-sleep processes. Interpret relative to core count: load 4 on 4 cores is fully utilised; load 4 on 16 cores is quiet. Rising 1-minute above the 15-minute means load is increasing.

The nuance worth stating: Linux load includes `D`-state processes, so high load can mean IO saturation with idle CPU. Load alone doesn't tell you which — that's why you check `%iowait` next.

**L5.2 — Memory**

```bash
free -h
```

`used` on modern `free` already excludes cache. The column that matters is **`available`** — memory obtainable without swapping, because the kernel will evict page cache on demand. `buff/cache` looking huge is normal and healthy; the kernel using free RAM for cache is the correct behaviour. Alerting on "used" rather than "available" produces endless false alarms.

**L5.3 — CPU-bound vs memory-bound vs IO-bound**

- **CPU-bound** — high `%us`, load ≈ cores, low iowait. Profile the application.
- **Memory-bound** — low `available`, swap activity (`si`/`so` in `vmstat`), OOM kills.
- **IO-bound** — high `%wa`, processes in `D` state, high `await` in `iostat`, low CPU.

The single fastest triage: `vmstat 1 5` and look at `r` (run queue), `b` (blocked), `si`/`so` (swap in/out), `wa`.

**L5.4 — IO pressure**

```bash
iostat -xz 1
iotop -o
```

In `iostat`: `%util` near 100 means the device is saturated (misleading on SSDs/NVMe, which parallelise), `await` is average IO latency in ms, `aqu-sz` is queue depth. Rising `await` with rising queue depth is the signature of saturation.

**L5.5 — Per-process usage over time**

`pidstat 1` for CPU/memory/IO per process; `pidstat -d 1` for IO specifically. `top -p <pid>`. For history rather than live, `sar` (from sysstat) gives you retrospective data, which is invaluable when asked "what happened at 3am".

**L5.6 — Swap**

Swap being *used* is not itself a problem — the kernel pages out genuinely idle memory. Swap *thrashing* is: constant `si`/`so` in `vmstat`, high iowait, everything slow. That means the working set exceeds RAM. Modern guidance for servers is a small amount of swap (it improves reclaim behaviour) with `vm.swappiness` tuned low; databases and latency-sensitive services often disable it. Kubernetes historically required swap off entirely.

**L5.7 — `/proc/<pid>/`**

```bash
cat /proc/<pid>/status      # memory, threads, state
cat /proc/<pid>/limits      # ulimits actually in effect
ls -l /proc/<pid>/fd        # open file descriptors
cat /proc/<pid>/cmdline     # full command
cat /proc/<pid>/environ     # environment (as started)
ls -l /proc/<pid>/cwd       # working directory
```

`limits` and `fd` are the two that solve real problems — file descriptor exhaustion is common and invisible elsewhere.

**L5.8 — A method for "the box is slow"**

Don't guess. A workable order:

1. **Scope it** — one box or many? Started when? What changed?
2. `uptime` — load relative to cores.
3. `vmstat 1 5` — run queue, blocked, swap, iowait. This one command usually points at CPU, memory, or IO.
4. Follow the pointer: `top`/`pidstat` for CPU, `free`/`dmesg` for memory, `iostat`/`iotop` for IO, `ss`/`sar -n DEV` for network.
5. Identify the *process*, then ask whether it's misbehaving or just busy.
6. Check the boring causes: disk full, log flood, a cron job, a deploy.

Stating the method matters more than the commands — it's what distinguishes systematic diagnosis from tool recital.

---

## L6. Disk & storage

**L6.1 — Free space and what's using it**

```bash
df -h                          # per filesystem
du -sh /var/* | sort -h        # per directory
du -h --max-depth=1 /var
ncdu /var                      # interactive, much faster to explore
```

`df` reports what the filesystem says; `du` walks and sums files. They disagree in the case below.

**L6.2 — "Disk full" when `df` shows space**

Three causes, in order of likelihood:

1. **Deleted but open files.** A process holds an open fd to a deleted file — the space isn't freed until it closes. `lsof | grep deleted`. Fix by restarting the process (or truncating via `/proc/<pid>/fd/N`). Classic with log files rotated badly while the app holds the handle.
2. **Inode exhaustion.** `df -i`. Millions of tiny files (session files, cache) exhaust inodes while bytes remain free. `ENOSPC` with free space is the tell.
3. **Reserved blocks.** ext4 reserves ~5% for root by default; non-root writes fail first. `tune2fs -m 1` reduces it.

**L6.3 — Block devices and partitions**

```bash
lsblk -f          # tree with filesystems and UUIDs
fdisk -l
blkid             # UUIDs for fstab
```

**L6.4 — Format, mount, unmount**

```bash
mkfs.ext4 /dev/xvdf
mount /dev/xvdf /data
umount /data
mount | grep data
```

If `umount` says "target is busy", `lsof +D /data` or `fuser -m /data` finds the culprit. `umount -l` (lazy) detaches immediately and cleans up when free — useful, but doesn't actually stop the writes.

**L6.5 — `/etc/fstab` without bricking boot**

```
UUID=abc-123  /data  ext4  defaults,nofail  0  2
```

Two rules. **Use UUID or LABEL**, never `/dev/sdX` — device names are not stable across reboots. **Add `nofail`** so a missing device doesn't drop the machine into emergency mode at boot. Always test with `mount -a` before rebooting; a bad fstab on a cloud instance without console access is a genuinely bad afternoon.

**L6.6 — Grow a filesystem after expanding the volume**

Two steps, and people forget the second:

```bash
growpart /dev/xvda 1              # grow the partition
resize2fs /dev/xvda1              # ext4 — grow the filesystem
xfs_growfs /data                  # XFS — takes a mount point, not a device
```

Both can be done online. Expanding the EBS volume alone changes nothing the OS sees.

**L6.7 — LVM basics**

**PV** (physical volume) — a disk or partition given to LVM. **VG** (volume group) — a pool of PVs. **LV** (logical volume) — a slice of the VG that you format and mount. The value is flexibility: add a PV to the VG, extend the LV, resize the filesystem, all online.

```bash
pvcreate /dev/xvdf
vgextend vg0 /dev/xvdf
lvextend -l +100%FREE /dev/vg0/data
resize2fs /dev/vg0/data
```

**L6.8 — Log rotation**

`/etc/logrotate.d/myapp`:

```
/var/log/myapp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

The key decision is `copytruncate` vs `create` + a signal. `copytruncate` copies then truncates in place — works with apps that hold the fd open, but risks losing lines written during the copy. `create` renames and makes a new file, requiring the app to reopen (usually via `postrotate ... systemctl reload`). Getting this wrong is the most common cause of L6.2's deleted-but-open problem. Test with `logrotate -d` (debug, no changes).

---

## L7. Services & systemd

**L7.1 — Basic service control**

```bash
systemctl start|stop|restart|reload myapp
systemctl enable myapp        # start at boot
systemctl disable myapp
systemctl enable --now myapp  # both
systemctl mask myapp          # prevent starting entirely
```

`restart` stops and starts; `reload` asks the service to re-read config without dropping connections (only if it supports it). `mask` is stronger than `disable` — it symlinks the unit to `/dev/null` so nothing can start it, including dependencies.

**L7.2 — Status and failure output**

```bash
systemctl status myapp
systemctl --failed
journalctl -u myapp -n 50 --no-pager
```

`status` shows loaded/active state, PID, memory, and the last few log lines. The important fields are `Active:` (and how long), `Main PID`, and the exit code/status on failure. `Result: exit-code` with `status=203/EXEC` means the binary path is wrong; `status=1` is an application error.

**L7.3 — Write a unit file**

`/etc/systemd/system/myapp.service`:

```ini
[Unit]
Description=My Application
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/bin/server
Restart=on-failure
RestartSec=5
Environment=NODE_ENV=production
EnvironmentFile=-/etc/myapp/env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then `systemctl daemon-reload` (required after any unit change) and `systemctl enable --now myapp`. `Type=simple` means the process doesn't fork; `Type=forking` is for daemons that do; `Type=notify` for services that signal readiness explicitly.

**L7.4 — Unit types**

- **service** — a process.
- **timer** — scheduled activation of a service (cron replacement).
- **socket** — socket activation; systemd holds the port and starts the service on first connection.
- **target** — a grouping/synchronisation point (`multi-user.target`, `network-online.target`).
- **mount**, **path**, **device** — filesystem and device units.

**L7.5 — Restart policies and restart storms**

`Restart=` takes `no`, `on-failure`, `on-abnormal`, `always`. `RestartSec=` sets the delay. The risk: a service that fails instantly and restarts forever hammers dependencies and floods logs. Bound it:

```ini
StartLimitIntervalSec=300
StartLimitBurst=5
```

Five failures in five minutes and systemd gives up, leaving it failed — which is usually better than an invisible crash loop. `systemctl reset-failed` clears the state.

**L7.6 — Drop-in overrides**

```bash
systemctl edit myapp
```

Creates `/etc/systemd/system/myapp.service.d/override.conf` with only your changes. Vendor updates to the original unit continue to apply. Editing the shipped unit directly means the next package update silently overwrites your change. For list-valued directives, set them empty first (`ExecStart=` then `ExecStart=/new/path`) or they append.

**L7.7 — Boot sequence, for debugging purposes**

Firmware → bootloader (GRUB) → kernel + initramfs → root filesystem mounted → systemd as PID 1 → units activated toward `default.target` in dependency order.

Debugging tools: `systemd-analyze blame` (slowest units), `systemd-analyze critical-chain` (the actual critical path), `journalctl -b` (this boot), `journalctl -b -1` (previous boot — essential after an unexplained reboot).

**L7.8 — A service that starts then immediately exits**

Check, in order:

1. `journalctl -u svc -n 50` — the error is usually right there.
2. Exit code in `systemctl status` — 203 is exec/permission, 200-family are systemd setup failures, others are application-level.
3. **`Type=` mismatch** — the most common non-obvious cause. A daemon that forks with `Type=simple` looks like it exited immediately; conversely a foreground process with `Type=forking` times out.
4. Permissions on `User=`, `WorkingDirectory=`, and any files it opens.
5. Missing environment — systemd gives a minimal env, so a service that works in your shell may not have `PATH` or variables it expects.
6. Run `ExecStart` manually as the service user to see the real error.

---

## L8. Scheduling

**L8.1 — crontab fields**

```
* * * * * command
│ │ │ │ └── day of week (0-7, both 0 and 7 = Sunday)
│ │ │ └──── month (1-12)
│ │ └────── day of month (1-31)
│ └──────── hour (0-23)
└────────── minute (0-59)
```

`*/5 * * * *` every five minutes. `0 2 * * *` daily at 02:00. `0 3 * * 1` Mondays at 03:00. Note that day-of-month and day-of-week are OR'd, not AND'd, when both are specified — a common surprise.

**L8.2 — Cron works manually but not on schedule**

Almost always **environment**. Cron runs with a minimal environment: `PATH` is typically just `/usr/bin:/bin`, no profile is sourced, `HOME` may differ, and no shell login variables exist.

Fixes: use absolute paths for every binary; set variables explicitly at the top of the crontab; or have the cron entry call a wrapper script that sources what it needs. Second most common cause: output goes nowhere, so failures are silent — redirect to a log (`>> /var/log/job.log 2>&1`) rather than `/dev/null`. Also check the user's crontab vs `/etc/crontab` (which has an extra user field), and whether the timezone is what you assumed.

**L8.3 — systemd timers**

```ini
# backup.timer
[Unit]
Description=Nightly backup

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

Paired with `backup.service`. Advantages over cron: output goes to the journal automatically, `systemctl status` shows the last run and result, `Persistent=true` runs a missed job after downtime, dependencies on other units are expressible, resource limits apply, and `RandomizedDelaySec` spreads load across a fleet. `systemctl list-timers` shows next and last run.

**L8.4 — Overlapping runs and locking**

```bash
flock -n /var/lock/myjob.lock /path/to/script.sh
```

`-n` fails immediately if the lock is held rather than queueing. Without this, a job that occasionally runs longer than its interval will pile up instances and can take the box down. systemd services get this for free — a `.service` won't start if it's already running.

---

## L9. Logging & troubleshooting

**L9.1 — `journalctl`**

```bash
journalctl -u nginx -f                    # follow one unit
journalctl -u nginx --since "1 hour ago"
journalctl --since "2026-08-17 09:00" --until "09:30"
journalctl -p err -b                      # errors this boot
journalctl -k                             # kernel messages
journalctl -b -1                          # previous boot
journalctl --disk-usage
journalctl -o json-pretty                 # structured fields
```

Priority levels run 0 (emerg) to 7 (debug); `-p err` includes everything more severe.

**L9.2 — What lives where in `/var/log`**

Debian/Ubuntu: `syslog` (everything), `auth.log` (authentication and sudo), `kern.log`, `dpkg.log`. RHEL/CentOS: `messages`, `secure` (auth), `yum.log`. Both: `/var/log/nginx/`, `/var/log/audit/audit.log` (auditd/SELinux). On systemd systems much of this is duplicated in the journal, and some distros ship journal-only.

**L9.3 — Follow and filter live**

```bash
tail -f app.log | grep -i error
tail -F app.log                    # survives rotation — use this
multitail a.log b.log
```

`-F` rather than `-f` matters: `-f` follows the file descriptor and goes silent after log rotation, which is a genuinely confusing failure during an incident.

**L9.4 — `dmesg`**

```bash
dmesg -T | tail -50          # -T for human timestamps
dmesg -w                     # follow
dmesg -l err,crit
```

Where you find OOM kills, disk IO errors, filesystem remounts to read-only, network interface resets, and hardware faults. If a process died with no application-level explanation, check here.

**L9.5 — Correlating timestamps during an incident**

Confirm every system's timezone and clock sync first (`timedatectl`, `chronyc tracking`) — correlating across hosts with drifted clocks produces wrong conclusions. Normalise to UTC. Then build a single timeline: deploys, config changes, alerts, log entries, metric inflections. The goal is finding what happened *first*, since the loudest symptom is usually downstream of the actual cause.

**L9.6 — Getting logs off the box**

An agent (Fluent Bit, Vector, Filebeat, CloudWatch agent) tails files or reads the journal, parses and enriches, buffers locally, and ships to a central store. Key concerns: buffering so a network blip doesn't lose logs, backpressure so shipping doesn't consume the host, structured output (JSON) so it's queryable, and consistent metadata (host, service, environment, trace ID). The reason it matters: on ephemeral infrastructure the box is gone before you'd want to log in, so logs that only exist locally don't exist.

---

## L10. Packages & software

**L10.1 — Install, update, remove**

```bash
apt update && apt upgrade
apt install nginx
apt remove nginx          # keep config
apt purge nginx           # remove config too
apt list --upgradable

dnf install nginx
dnf update
dnf remove nginx
dnf check-update
```

`apt update` refreshes metadata; `apt upgrade` installs. They're separate and both are needed.

**L10.2 — What owns a file, and what a package installed**

```bash
dpkg -S /usr/sbin/nginx        # which package owns this file
dpkg -L nginx                  # what did this package install
apt-file search <path>         # for not-yet-installed packages

rpm -qf /usr/sbin/nginx
rpm -ql nginx
```

**L10.3 — Pinning and holding**

```bash
apt-mark hold nginx
apt-mark unhold nginx
dnf versionlock add nginx
```

Warranted when a known-good version is validated and an upgrade would be risky mid-incident, or when an application requires a specific version. The cost is that you also stop receiving security patches, so a hold should have an owner and an expiry rather than becoming permanent.

**L10.4 — Third-party repos and signing keys**

```bash
curl -fsSL https://example.com/key.gpg | gpg --dearmor -o /usr/share/keyrings/example.gpg
echo "deb [signed-by=/usr/share/keyrings/example.gpg] https://example.com/apt stable main" \
  > /etc/apt/sources.list.d/example.list
```

Verifying the key matters because an unverified repo can serve you arbitrary packages that install as root. The old `apt-key add` approach is deprecated precisely because it trusted the key for *all* repos rather than scoping it.

**L10.5 — Install from source**

`./configure && make && make install` — or increasingly a language package manager or a tarball of prebuilt binaries. Install to `/usr/local` or `/opt` so you don't collide with the package manager. The tradeoff: you own patching forever, and nothing tracks the dependency. Prefer a package or container if either exists.

**L10.6 — `$PATH` resolution**

The shell searches `$PATH` left to right and runs the first match. Debug:

```bash
which -a python3        # every match, in order
type python3            # also reveals aliases and functions
echo $PATH
hash -r                 # clear the shell's command cache
```

Common causes of "wrong binary": a shim directory (pyenv, nvm, asdf) earlier in PATH, `/usr/local/bin` shadowing `/usr/bin`, a stale hash cache after installing a new version, or a completely different PATH in a non-interactive shell (cron, systemd, CI).

---

## L11. Shell scripting

**L11.1 — Script skeleton**

```bash
#!/usr/bin/env bash
set -euo pipefail

main() {
    local input="${1:?usage: $0 <input>}"
    echo "processing $input"
}

main "$@"
```

`#!/usr/bin/env bash` rather than `/bin/bash` finds bash via PATH, which matters on systems where it's elsewhere. `chmod +x` to run it.

**L11.2 — `set -euo pipefail`**

- `-e` — exit on any command returning non-zero. Prevents a script continuing after a failed step and doing damage.
- `-u` — error on undefined variables. Catches typos, and prevents the classic `rm -rf "$DIR/"` disaster when `DIR` is unset.
- `-o pipefail` — a pipeline fails if *any* stage fails, not just the last. Without it, `false | true` succeeds.

Caveats worth knowing: `-e` doesn't fire inside conditions, `||`, or `&&` chains, and `-u` breaks `"$@"` on very old bash. Use `cmd || true` where a non-zero exit is genuinely acceptable.

**L11.3 — Conditionals and loops**

```bash
if [[ -f "$file" ]]; then ... fi
if [[ "$a" == "$b" ]]; then ... fi
if [[ -z "$var" ]]; then ... fi      # empty
if [[ -n "$var" ]]; then ... fi      # non-empty

for f in *.log; do ... done
while read -r line; do ... done < file
case "$env" in
    prod) ... ;;
    dev|test) ... ;;
    *) echo "unknown"; exit 1 ;;
esac
```

Prefer `[[ ]]` over `[ ]` in bash — it handles unquoted variables more safely and supports pattern matching. Use `read -r` always, or backslashes get mangled.

**L11.4 — Functions**

```bash
log() {
    local level="$1"; shift
    echo "[$(date -Is)] [$level] $*" >&2
}

get_version() {
    local v
    v=$(cat VERSION)
    echo "$v"
}
version=$(get_version)
```

`local` prevents variables leaking globally. Functions "return" by echoing to stdout; `return` sets an exit code (0-255 only). Log to stderr so it doesn't pollute a function's captured output.

**L11.5 — Input validation and useful failure**

```bash
if [[ $# -lt 1 ]]; then
    echo "usage: $0 <environment>" >&2
    exit 2
fi

command -v jq >/dev/null || { echo "jq required" >&2; exit 3; }
```

Errors to stderr, distinct non-zero exit codes for distinct failures, and a message that says what to do rather than just what broke.

**L11.6 — `trap` for cleanup**

```bash
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
trap 'echo "interrupted" >&2; exit 130' INT TERM
```

`EXIT` fires on any exit path including errors under `set -e`, which makes it the reliable place for cleanup. Without it, a script that fails midway leaves temp files, lock files, or a service stopped.

**L11.7 — Filenames with spaces and special characters**

Quote everything: `"$file"`, `"$@"`, `"${array[@]}"`. Use `find -print0 | xargs -0`, and `while IFS= read -r -d '' file` for null-delimited reads. Never parse `ls` output. `IFS=` prevents leading/trailing whitespace being stripped.

**L11.8 — Safe temp files**

```bash
tmpfile=$(mktemp)
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
```

`mktemp` creates atomically with safe permissions. A predictable name like `/tmp/myapp.tmp` is a symlink-attack vector in a world-writable directory.

**L11.9 — `getopts`**

```bash
while getopts ":e:vh" opt; do
    case $opt in
        e) env="$OPTARG" ;;
        v) verbose=1 ;;
        h) usage; exit 0 ;;
        \?) echo "invalid: -$OPTARG" >&2; exit 2 ;;
        :) echo "-$OPTARG needs an argument" >&2; exit 2 ;;
    esac
done
shift $((OPTIND - 1))
```

Positional-only arguments become unreadable past two or three and can't be reordered. `getopts` handles short flags; long options need manual parsing or `getopt`.

**L11.10 — `shellcheck`**

Run it on every script and in CI. It catches unquoted variables, useless `cat`, `cd` without error handling, misuse of `[ ]`, and subshell scoping bugs that are genuinely hard to spot by eye. Directives like `# shellcheck disable=SC2086` should be rare and justified with a comment.

**L11.11 — When it should have been Python**

Signals to switch: past ~100–200 lines; anything with data structures beyond flat strings and arrays; JSON or XML manipulation beyond a simple `jq` call; arithmetic beyond counters; needing real error handling with context; needing tests; or when it'll be maintained by people who aren't comfortable in bash.

Bash's strength is orchestrating other programs — glue, pipelines, short-lived automation. Its weaknesses are data structures, error handling, and testability. A 400-line bash script with nested functions and associative arrays is a Python program someone refused to start writing. Being able to name that boundary is worth more in an interview than any individual bash trick.

---

## L12. Host-level networking

**L12.1 — Interfaces and addresses**

```bash
ip addr show
ip -br addr             # brief, very readable
ip link set eth0 up
```

`ifconfig` is deprecated and absent on many modern distros.

**L12.2 — Routing table**

```bash
ip route
ip route get 8.8.8.8    # which route would actually be used
```

`ip route get` is the useful one — it answers "which interface and gateway will this specific destination use", rather than making you interpret the table yourself. Most specific prefix wins; `default` (`0.0.0.0/0`) is the fallback.

**L12.3 — Listening sockets**

```bash
ss -tulpn
ss -tan state established
ss -s                   # summary counts
```

`-t` TCP, `-u` UDP, `-l` listening, `-p` process (needs root), `-n` numeric. This answers both "is my service actually listening" and "is it bound to 127.0.0.1 when it should be 0.0.0.0" — which is one of the most common causes of "the app is running but I can't reach it".

**L12.4 — Name resolution order**

`/etc/nsswitch.conf` defines the order — typically `files dns`, meaning `/etc/hosts` is consulted before DNS. `/etc/resolv.conf` lists nameservers, `search` domains, and options. On systemd-resolved systems `/etc/resolv.conf` is often a symlink to a stub at `127.0.0.53`, so `resolvectl status` shows the real upstream servers.

Practical consequence: `dig` queries DNS directly and bypasses `/etc/hosts`, so `dig` and `ping` can legitimately disagree. Use `getent hosts <name>` to see what the *system* resolver returns.

**L12.5 — Host firewall**

```bash
ufw status verbose
ufw allow 22/tcp

iptables -L -n -v --line-numbers
nft list ruleset
firewall-cmd --list-all
```

Chains are evaluated in order, first match wins, with a default policy at the end. Note that Docker inserts its own iptables rules and can bypass ufw entirely — published container ports may be reachable despite a firewall that appears to block them.

**L12.6 — SSH tunnels**

```bash
ssh -L 5432:db.internal:5432 bastion     # local: your :5432 → db via bastion
ssh -R 8080:localhost:80 remote          # remote: their :8080 → your :80
ssh -D 1080 bastion                      # dynamic SOCKS proxy
```

Local forwarding is the everyday one — reaching a private database or admin UI through a bastion without a VPN.

**L12.7 — `~/.ssh/config`**

```
Host bastion
    HostName bastion.example.com
    User jahid
    IdentityFile ~/.ssh/id_ed25519

Host prod-*
    ProxyJump bastion
    User deploy

Host *
    ServerAliveInterval 60
    AddKeysToAgent yes
```

`ProxyJump` (`-J`) replaces the old `ProxyCommand` netcat pattern and is the clean way to reach hosts behind a bastion. Wildcards mean you configure a fleet once. `ServerAliveInterval` stops idle sessions being dropped by NAT timeouts.
