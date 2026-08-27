# Git — Answer Key

Companion to Domain 1 of the DevOps Interview Skills Matrix. Numbering matches item for item.

Answers are written as *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

---

## 1. Setup & configuration

**1.1 — Configure user, email, editor, default branch**

```bash
git config --global user.name "Jahid"
git config --global user.email "you@example.com"
git config --global core.editor "vim"
git config --global init.defaultBranch main
```

Worth knowing: `user.email` is what links commits to a GitHub account. A mismatch means commits show as unattributed. For work vs personal, use `includeIf` in `~/.gitconfig` to switch identity by directory:

```
[includeIf "gitdir:~/work/"]
  path = ~/.gitconfig-work
```

**1.2 — Config scopes**

Three levels, narrowest wins: `--system` (all users, `/etc/gitconfig`), `--global` (your user, `~/.gitconfig`), `--local` (this repo, `.git/config`). There's also `--worktree`. Check where a value came from with `git config --list --show-origin`, which is the fastest way to answer "why is this repo using the wrong email".

**1.3 — Aliases**

```bash
git config --global alias.lg "log --oneline --graph --decorate --all"
git config --global alias.st "status -sb"
```

Shell commands need a `!` prefix: `alias.cleanup = '!git branch --merged | grep -v main | xargs git branch -d'`.

**1.4 — SSH key auth and rotation**

Generate with `ssh-keygen -t ed25519 -C "label"`, add the public key to the host, test with `ssh -T git@github.com`. Rotation: generate the new key, add it, verify it works, *then* remove the old one from the host. Keys live in `~/.ssh`; the private key must be `600`. Multiple keys are handled in `~/.ssh/config` with `Host` blocks and `IdentityFile`.

**1.5 — Signed commits**

`git config --global commit.gpgsign true` plus a signing key. SSH signing is now simpler than GPG: `gpg.format = ssh` and `user.signingkey` pointing at your public key. Verify with `git log --show-signature`. The point is provenance — proving a commit came from who it claims to, which matters because the author field is trivially forgeable.

**1.6 — `.gitignore`, and why an already-tracked file keeps appearing**

`.gitignore` only affects *untracked* files. Once a file is tracked, ignoring it does nothing. Fix:

```bash
git rm --cached path/to/file
```

then commit. `--cached` removes it from the index but leaves it on disk. Use `git check-ignore -v <path>` to find which rule (or which file) is matching. Note precedence: repo `.gitignore`, then `.git/info/exclude` for local-only ignores, then the global ignore file.

**1.7 — `.gitattributes`**

Controls per-path behaviour. Most common use is line endings: `* text=auto` normalises to LF in the repo. Also marks binaries (`*.png binary`) so Git doesn't try to diff them, sets custom diff drivers, marks generated files with `linguist-generated`, and configures `merge=ours` for files like changelogs. Unlike `.gitignore`, it's committed and applies to everyone, which is the point.

**1.8 — Git LFS**

Replaces large files with pointer files, storing the real content on a separate server. Warranted for binaries that change often — design assets, ML models, media. Not warranted for large files that never change (the delta cost is low anyway) and it adds a hard dependency: without the LFS client, a clone gives you pointer text instead of files. Track with `git lfs track "*.psd"`, which writes to `.gitattributes`.

---

## 2. Core workflow

**2.1 — Working directory vs index vs HEAD**

- **Working directory** — the files on disk, what you're editing.
- **Index (staging area)** — a snapshot you're building for the next commit. `git add` copies from working directory to index.
- **HEAD** — a pointer to the commit at the tip of the current branch; the last committed state.

`git diff` compares working directory to index. `git diff --staged` compares index to HEAD. `git status` describes both gaps. The index existing as a separate layer is what makes partial staging possible.

**2.2 — `git add -p`**

Interactively stage individual hunks. Prompts per hunk: `y` stage, `n` skip, `s` split into smaller hunks, `e` edit the hunk manually, `q` quit. Use it to split unrelated changes in one file into separate commits. `git add -p` is the single highest-value habit for producing reviewable commits.

**2.3 — Unstage without losing work**

```bash
git restore --staged <file>    # modern
git reset HEAD <file>          # older equivalent
```

Both move the change back to unstaged; the file on disk is untouched. Note `git restore <file>` *without* `--staged` discards working-directory changes — different and destructive.

**2.4 — A good commit message**

Subject line under ~50 chars, imperative mood ("Add retry to webhook handler", not "Added" or "Adds"), blank line, then a body explaining *why*. The diff already shows what changed; the message exists to explain the reasoning that isn't recoverable from the code. Reference the issue. A commit should be one logical change — if the message needs "and", it's probably two commits.

**2.5 — Amend**

```bash
git commit --amend                    # edit message and/or include staged changes
git commit --amend --no-edit          # keep message, just add staged changes
```

Amend creates a *new* commit and discards the old one, so never amend something already pushed to a shared branch without understanding the force-push consequence.

**2.6 — What `.git/` contains**

`objects/` (all content, as blobs/trees/commits/tags), `refs/` (branch and tag pointers), `HEAD` (pointer to current ref), `index` (the staging area, a binary file), `config` (local config), `logs/` (the reflog), `hooks/`. Deleting `.git/` turns the repo into a plain directory — everything Git knows lives there.

**2.7 — The object model**

Four types, all content-addressed by SHA:
- **Blob** — file contents. No name, no metadata.
- **Tree** — a directory listing: names, modes, and pointers to blobs and other trees.
- **Commit** — a pointer to one tree (the full snapshot), plus parent commit(s), author, committer, message.
- **Tag** — an annotated tag object pointing at a commit, with its own message and signature.

Key insight: Git stores **snapshots, not diffs**. Diffs are computed on demand. Identical content anywhere in history is stored once, because the SHA is the same. Inspect with `git cat-file -p <sha>`.

---

## 3. Branching

**3.1 — Create, switch, rename, delete**

```bash
git switch -c feature      # create and switch
git switch main            # switch
git branch -m old new      # rename
git branch -d feature      # delete (safe: refuses if unmerged)
git branch -D feature      # force delete
```

`-d` refusing on unmerged work is a feature, not an obstacle.

**3.2 — `switch`/`restore` vs `checkout`**

`git checkout` was overloaded — it changed branches *and* discarded file changes, which meant a typo could destroy work. Git 2.23 split it: `switch` for branches, `restore` for files. `checkout` still works and you'll see it everywhere, but the split is clearer and safer.

**3.3 — Track a remote branch**

```bash
git push -u origin feature       # push and set upstream
git branch -u origin/feature     # set upstream for existing branch
```

Upstream is what makes bare `git push` and `git pull` work, and what lets `git status` say "ahead by 2 commits".

**3.4 — Merged vs unmerged, and pruning**

```bash
git branch --merged main       # safe to delete
git branch --no-merged main
git fetch --prune              # remove local refs to deleted remote branches
```

`--merged` is relative to the branch you name — check against the right base. Note it reports false negatives for squash-merged branches, since the commits technically never merged.

**3.5 — Branching strategies**

- **Trunk-based** — short-lived branches (hours to a day), merge to main constantly, feature flags hide incomplete work. Requires good CI and test coverage. Best fit for continuous delivery.
- **GitFlow** — develop/release/hotfix/feature branches. Heavy. Designed for versioned software with supported releases, not for services deploying multiple times a day.
- **Release branches** — trunk plus a branch cut per release for stabilisation and backports.

Choosing: the question is release model, not team size. If you deploy continuously, trunk-based; GitFlow's overhead buys you nothing and its long-lived branches actively fight integration. If you ship versioned artifacts customers install and you support old versions, release branches earn their cost.

**3.6 — Detached HEAD**

HEAD points at a commit rather than a branch — happens when you check out a SHA or tag. Commits made here belong to no branch and will eventually be garbage collected. Recover with:

```bash
git switch -c rescue-branch   # keep the work
git switch main               # discard it
```

If you already left and lost the SHA, `git reflog` has it.

**3.7 — Tags: lightweight vs annotated**

```bash
git tag v1.0.0                        # lightweight: just a pointer
git tag -a v1.0.0 -m "Release 1.0.0"  # annotated: a real object
git push origin v1.0.0                # tags aren't pushed by default
```

Annotated tags store tagger, date, message, and can be signed — use them for releases. Lightweight tags are fine as private bookmarks. Tags are meant to be immutable; moving a published tag breaks everyone who fetched it.

---

## 4. Merging & rebasing

**4.1 — Merge and read the result**

`git merge feature` while on the target branch. A merge commit has two parents. `git log --graph --oneline` shows the topology. `git log --first-parent` follows only the mainline, which is often what you actually want on a busy repo.

**4.2 — Fast-forward vs no-ff**

If the target branch hasn't moved since the feature branched, Git just moves the pointer forward — no merge commit, linear history. `--no-ff` forces a merge commit anyway, which preserves the fact that a branch existed and groups its commits.

Force fast-forward (`--ff-only`) when you want strictly linear history and want the merge to fail if a rebase is needed. Force `--no-ff` when the branch boundary is meaningful — it makes the whole feature revertable as one commit, which is a real operational advantage.

**4.3 — Rebase onto updated main**

```bash
git switch feature
git fetch origin
git rebase origin/main
```

Replays each of your commits on top of the new base, creating new commits with new SHAs. Result is linear history with no merge commit. If conflicts occur, resolve, `git add`, `git rebase --continue`.

**4.4 — Interactive rebase**

```bash
git rebase -i HEAD~5
```

Opens an editor listing commits oldest-first. Actions: `pick` (keep), `reword` (change message), `edit` (stop to amend), `squash` (merge into previous, combine messages), `fixup` (merge into previous, discard message), `drop` (delete), and reorder by moving lines. `--autosquash` with commits made as `git commit --fixup=<sha>` automates the common case.

**4.5 — The golden rule of rebasing**

Don't rebase commits that others have based work on. Rebasing rewrites SHAs; anyone who pulled the old commits now has divergent history and gets a mess on their next pull.

When it's safe to break it: your own feature branch that nobody else is using, even if it's pushed — force-push with lease and carry on. Also fine if the whole team agrees and coordinates, though that's rarely worth it. The rule is really about *shared* branches, not *pushed* branches.

**4.6 — Rebase vs merge for a 20-person team**

The case for rebase/squash-merge: linear history, easy to read, `git bisect` works cleanly, each PR is one commit on main. The case for merge: preserves true history, no rewriting, no force-pushes, keeps the individual commits of a large change.

A defensible position for that team size: rebase or squash *feature branches before merging*, but never rebase main. Squash-merge for small PRs; merge commits for large features where the individual commits carry real information. The important part is that it's enforced in branch protection rather than left to preference, because mixed strategies produce the worst of both.

**4.7 — `rerere`**

"Reuse recorded resolution." `git config --global rerere.enabled true`. Git records how you resolved a conflict and replays it automatically next time the same conflict appears. Valuable during long rebases and repeated merges of a long-lived branch. It's silently helpful, which is also its risk — it can apply a stale resolution, so review the result.

**4.8 — Squash-merge vs merge commit, and bisect**

Squash-merge collapses a PR into one commit on main. History is clean, but the individual commits are gone and the branch's relationship to main is lost — which is why `git branch --merged` won't list it.

For `git bisect`: squash-merge is actually *better*. Each commit on main is a complete, tested change, so bisect lands on a meaningful unit. With merge commits, bisect can land on an intermediate commit from inside a feature branch that never built on its own. `git bisect --first-parent` mitigates that.

---

## 5. Conflict resolution

**5.1 — Reading conflict markers**

```
<<<<<<< HEAD
your version
=======
their version
>>>>>>> feature-branch
```

Top is the current branch (HEAD), bottom is what's being merged in. `git config merge.conflictStyle zdiff3` adds a third section showing the common ancestor, which usually makes the intent obvious and is worth enabling permanently.

**5.2 — Resolve during merge**

Edit the file, remove all markers, `git add <file>` to mark resolved, then `git commit`. `git status` lists unmerged paths. `git diff` during a conflict shows a combined diff against both parents.

**5.3 — Resolve during rebase, and inverted sides**

Same mechanics, but "ours" and "theirs" feel backwards. During a rebase, Git is replaying *your* commits onto the base branch — so at each step, "ours" is the base branch (the thing being replayed onto) and "theirs" is your commit. This trips people up constantly. Then `git add` and `git rebase --continue`.

**5.4 — Abort cleanly**

```bash
git merge --abort
git rebase --abort
git cherry-pick --abort
```

Returns to the state before you started. Safe, and the right instinct when a merge turns out to be much larger than expected.

**5.5 — `--ours` / `--theirs`**

```bash
git checkout --ours <file>     # take current branch's version wholesale
git checkout --theirs <file>   # take incoming version wholesale
```

Use deliberately for files where merging line by line is meaningless — lockfiles, generated output, binary assets. Remember the inversion during rebase (5.3).

**5.6 — Merge tools**

`git mergetool` launches a configured three-way diff (vimdiff, meld, VS Code, Beyond Compare). The three-way view — base, ours, theirs — is far more informative than the inline markers because you can see what each side actually changed relative to the ancestor.

**5.7 — Lockfiles and generated files**

Don't hand-merge. Take one side, then regenerate:

```bash
git checkout --theirs package-lock.json
npm install    # regenerate from package.json
git add package-lock.json
```

Hand-merging a lockfile produces a file that's internally inconsistent and will fail in ways that are painful to debug. The same applies to any generated artifact — resolve the source, regenerate the output.

---

## 6. Undo & recovery

**6.1 — `reset --soft` vs `--mixed` vs `--hard`**

All three move the branch pointer to the target commit. They differ in what else they touch:

| Mode | Branch pointer | Index | Working directory |
|---|---|---|---|
| `--soft` | moved | unchanged | unchanged |
| `--mixed` (default) | moved | reset | unchanged |
| `--hard` | moved | reset | **overwritten** |

So `--soft HEAD~1` undoes the commit but leaves everything staged, ready to recommit. `--mixed HEAD~1` leaves changes unstaged. `--hard HEAD~1` destroys the changes. `--hard` is the only one that loses work.

**6.2 — Revert on a shared branch**

```bash
git revert <sha>
```

Creates a *new* commit that undoes the change. History is preserved and nothing is rewritten, so collaborators are unaffected. Reset rewrites history, which on a shared branch means everyone else's next pull produces divergence and confusion. Rule: reset for local, revert for published.

Reverting a merge commit needs `-m 1` to specify which parent is the mainline. Note the follow-on trap: after reverting a merge, re-merging that branch won't reintroduce the changes, because Git considers them already merged. You have to revert the revert.

**6.3 — Recover via reflog**

```bash
git reflog
git switch -c recovered <sha>    # or git reset --hard <sha>
```

The reflog records every position HEAD has held — commits, resets, rebases, checkouts — for around 90 days by default. It's local-only and it's why almost nothing in Git is truly lost. This is the first thing to reach for after any "I've destroyed everything" moment.

**6.4 — Recover a deleted file from an earlier commit**

```bash
git restore --source=<sha> -- path/to/file
git checkout <sha> -- path/to/file      # older syntax
```

To find when it was deleted: `git log --diff-filter=D -- path/to/file`.

**6.5 — Recover after `reset --hard`**

If the work was **committed**, reflog has it (6.3). If it was **staged but not committed**, the blobs are still in the object database:

```bash
git fsck --lost-found
```

which surfaces dangling blobs you can inspect with `git cat-file -p`. If it was **never staged**, it's gone — Git never saw it. That's the honest answer, and it's the argument for committing early and often, even if messily, since you can always tidy history later.

**6.6 — Undo a bad rebase**

```bash
git reset --hard ORIG_HEAD
```

Git sets `ORIG_HEAD` before dangerous operations. If that's been overwritten, find the pre-rebase commit in `git reflog` and reset to it.

**6.7 — Remove a secret from history**

Order matters: **rotate the secret first**. History rewriting doesn't help if the secret was ever pushed — assume it's compromised the moment it left your machine. Then clean:

```bash
git filter-repo --path secrets.env --invert-paths
```

Blast radius: every commit after the touched one gets a new SHA, so everyone must re-clone or hard reset. Open PRs break. Forks keep the old objects. GitHub retains unreferenced commits accessible by SHA until support purges them. Tags need re-pointing. This is why rotation is the real fix and rewriting is cosmetic cleanup.

**6.8 — Clean untracked files safely**

```bash
git clean -n -d      # dry run — ALWAYS do this first
git clean -fd        # then actually delete
```

`-x` also removes ignored files, which will delete `node_modules`, `.env`, and build output. `git clean` is unrecoverable — these files were never in Git, so there's no reflog to save you.

---

## 7. Inspection & investigation

**7.1 — Useful `log` flags**

```bash
git log --oneline --graph --decorate --all   # topology at a glance
git log --since="2 weeks ago"
git log --author="jahid"
git log -S "functionName"                    # commits where the count of this string changed
git log -G "regex"                           # commits whose diff matches the regex
git log -p -- path/to/file                   # patches for one file
git log --stat                               # files changed per commit
```

`-S` (the "pickaxe") is the one people don't know and it's excellent for "when was this introduced".

**7.2 — Diff scopes**

```bash
git diff                    # working directory vs index
git diff --staged           # index vs HEAD
git diff HEAD               # working directory vs HEAD
git diff main..feature      # tip to tip
git diff main...feature     # feature vs their common ancestor
```

The three-dot form is what code review shows — changes *on* the branch, excluding changes main made independently.

**7.3 — `blame`**

```bash
git blame path/to/file
git blame -L 40,60 file           # limit to a line range
git blame -w -C file              # ignore whitespace, detect moved code
```

`-w -C` matters because a reformat commit otherwise makes every line blame to the person who ran the formatter. `--ignore-rev` and `.git-blame-ignore-revs` let you permanently exclude formatting commits.

**7.4 — `bisect`**

```bash
git bisect start
git bisect bad                 # current commit is broken
git bisect good v1.2.0         # this one was fine
# test, then mark each commit:
git bisect good | git bisect bad
git bisect reset               # when done
```

Binary search across history — 1000 commits takes about 10 tests. The main requirement is a reliable way to test each commit.

**7.5 — Automated bisect**

```bash
git bisect run ./test-script.sh
```

Script exits 0 for good, non-zero for bad, 125 to skip an untestable commit. Fully automatic. This turns bisect from a tedious manual process into something you start and walk away from, and it's the version worth mentioning in an interview.

**7.6 — Search history for a string**

`git log -S "string"` finds commits where the number of occurrences changed — i.e. where it was added or removed. `git log -G "regex"` finds commits whose diff text matches. Add `--all` to search every branch, and `-p` to see the actual change.

**7.7 — File history through renames**

```bash
git log --follow -- path/to/file
```

Git doesn't record renames; it infers them by content similarity. `--follow` enables that inference, which is why file history looks truncated without it.

**7.8 — Inspect arbitrary objects**

```bash
git cat-file -t <sha>    # type
git cat-file -p <sha>    # pretty-print contents
git rev-parse HEAD       # resolve a ref to a SHA
git show <sha>           # commit with its diff
git ls-tree HEAD         # tree contents
```

Useful for understanding the object model concretely, and occasionally for recovering things.

---

## 8. Remotes & collaboration

**8.1 — Manage remotes**

```bash
git remote -v
git remote add upstream git@github.com:org/repo.git
git remote rename origin old-origin
git remote set-url origin <new-url>
```

**8.2 — `fetch` vs `pull`**

`fetch` downloads remote refs and objects but doesn't touch your working branch. `pull` is `fetch` plus an immediate `merge` (or `rebase`). Fetch-first is usually right because it lets you inspect what arrived — `git log HEAD..origin/main` — before deciding how to integrate it. `pull` on a branch with local commits is where surprise merge commits come from.

**8.3 — `pull.rebase`**

```bash
git config --global pull.rebase true
```

Makes `git pull` rebase your local commits on top of the fetched ones instead of merging. Produces linear history and avoids the noise of "Merge branch 'main' of ..." commits. The tradeoff is that it rewrites your local commits, so a conflict mid-pull is a rebase conflict. Setting `pull.ff only` is a defensible alternative: pull fails if a merge or rebase is needed, forcing you to decide explicitly.

**8.4 — `--force-with-lease`**

```bash
git push --force-with-lease
```

`--force` overwrites the remote branch unconditionally, including commits a colleague pushed while you were working. `--force-with-lease` checks that the remote is still where you last saw it and refuses if someone else pushed. It's the difference between "overwrite" and "overwrite if nothing changed underneath me". Always use the lease version. Note that a background `git fetch` (some IDEs do this) can update your remote-tracking ref and undermine the check — `--force-with-lease=<ref>:<sha>` is the paranoid form.

**8.5 — Recover after someone force-pushed over your work**

Your commits still exist locally. `git reflog` to find your pre-fetch position, or `origin/branch@{1}` in the reflog for the remote-tracking ref. Create a branch from that SHA, then rebase or cherry-pick onto the new remote state. If it's only on the remote, the pushed-but-orphaned commits may still be retrievable by SHA from the hosting provider's API.

**8.6 — Shallow and partial clone**

```bash
git clone --depth 1 <url>                 # shallow: only recent history
git clone --filter=blob:none <url>        # partial: blobs fetched on demand
git clone --single-branch --branch main <url>
```

Shallow is standard in CI where history isn't needed — much faster, less disk. Tradeoffs: `git log` is truncated, `bisect` and `blame` are limited, and some operations trigger a fetch anyway. Partial clone (`blob:none`) is usually the better choice for large repos you'll actually work in, since history is intact and file contents arrive lazily. Deepen later with `git fetch --unshallow`.

**8.7 — Fork workflow**

```bash
git clone git@github.com:you/repo.git
git remote add upstream git@github.com:org/repo.git
git fetch upstream
git rebase upstream/main       # or merge
git push origin feature
```

`origin` is your fork, `upstream` is the source. Keep your fork's main clean and unmodified — branch for every change — so syncing stays trivial.

---

## 9. Stash & housekeeping

**9.1 — Stash and reapply**

```bash
git stash
git stash pop
```

Saves modified tracked files and reverts the working directory to HEAD. Stashes are stored as commits in `refs/stash`.

**9.2 — Named and specific stashes**

```bash
git stash push -m "wip: retry logic"
git stash list
git stash apply stash@{2}
git stash show -p stash@{0}     # see the contents
```

Message your stashes. `git stash list` showing five entries of "WIP on main" is useless.

**9.3 — Include untracked files**

```bash
git stash -u        # include untracked
git stash -a        # include ignored too
```

Plain `git stash` leaves untracked files in place, which surprises people — you switch branches and the new files are still sitting there.

**9.4 — `apply` vs `pop`**

`pop` applies and deletes the stash; `apply` applies and keeps it. The difference bites when applying to the wrong branch: with `pop`, if the apply conflicts, the stash *is* kept — but if it applies cleanly onto the wrong branch, it's gone from the list and you have to recover it from the reflog. `apply` is safer when you're unsure; delete explicitly with `git stash drop` once you've confirmed.

**9.5 — `gc`, loose vs packed objects, repo size**

New objects are written individually ("loose"). `git gc` packs them into packfiles with delta compression and prunes unreachable objects past the reflog expiry. Runs automatically on a threshold. `git count-objects -vH` shows the breakdown. Repos bloat from committed binaries and large files — and because history is permanent, deleting the file later doesn't shrink the repo. That's what LFS and `filter-repo` address.

**9.6 — Worktrees**

```bash
git worktree add ../hotfix main
git worktree list
git worktree remove ../hotfix
```

Multiple working directories from one repository, each on a different branch, sharing the object database. Much better than stashing when you need to jump to a hotfix mid-feature — no stash, no rebuild of dependencies, both checkouts remain intact. The same branch can't be checked out in two worktrees at once.

---

## 10. Advanced / situational

**10.1 — Cherry-pick**

```bash
git cherry-pick <sha>
git cherry-pick <sha1>^..<sha2>     # a range
git cherry-pick -n <sha>            # apply without committing
```

Applies a commit's *changes* as a new commit with a new SHA. Legitimate for backporting a fix to a release branch. Overused as a substitute for proper merging, which leads to duplicated commits and confusing history — if you're cherry-picking regularly between the same two branches, the branching strategy is wrong.

**10.2 — Cherry-pick conflicts**

Resolve, `git add`, `git cherry-pick --continue`. Abort with `--abort`. Conflicts here usually signal the target branch has diverged enough that the commit doesn't apply cleanly — at that point, consider whether a proper merge or a fresh fix for that branch is more honest than forcing it through.

**10.3 — Submodules**

```bash
git submodule add <url> path
git clone --recurse-submodules <url>
git submodule update --init --recursive
```

A submodule pins a specific commit of another repo. The pain: clones don't include them by default (people get empty directories), updates are a two-step commit dance, detached HEAD inside the submodule is the default state, and branch switching doesn't update submodule contents automatically. They work, but they demand discipline the whole team has to share.

**10.4 — Subtree**

```bash
git subtree add --prefix=lib/thing <url> main --squash
git subtree pull --prefix=lib/thing <url> main --squash
```

Vendors the other repo's content directly into yours. Better than submodules when consumers shouldn't have to know: a plain clone just works, no extra commands, no detached HEAD. Worse when you frequently push changes back upstream, and it inflates repo size. Rule of thumb: subtree for consuming, submodule for tight bidirectional development.

**10.5 — Client-side hooks**

Scripts in `.git/hooks/`, executable, named for the event. `pre-commit` (lint, format, block secrets — exit non-zero to abort), `commit-msg` (validate message format), `pre-push` (run tests). They're local and not committed, so they can't be relied on for enforcement — and `--no-verify` skips them.

**10.6 — Pre-commit framework across a team**

`.pre-commit-config.yaml` in the repo defines hooks and versions; each developer runs `pre-commit install` once. Solves the distribution problem that raw `.git/hooks` has. Still bypassable with `--no-verify`, so the same checks must also run in CI — hooks are a fast-feedback convenience, not a control.

**10.7 — Server-side hooks**

Run on the remote, so they can't be bypassed by the client. `pre-receive` can reject a push outright — enforce commit signing, message format, file size limits, or block direct pushes to main. That's the enforcement a client-side hook can never provide. On managed platforms you don't get raw server hooks; the equivalents are branch protection rules, required status checks, and push rulesets.

**10.8 — Conventional commits and changelogs**

Format: `type(scope): description` — `feat`, `fix`, `chore`, `docs`, `refactor`, with `BREAKING CHANGE:` in the footer. Enforce with commitlint in a `commit-msg` hook plus a CI check. Tools like semantic-release then derive the version bump (feat → minor, fix → patch, breaking → major) and generate the changelog automatically. The value is machine-readable history; the cost is friction, so it's worth it mainly where you publish versioned artifacts.

**10.9 — `filter-repo`, not `filter-branch`**

`git filter-branch` is officially discouraged: extremely slow, and its default behaviour is subtly unsafe in ways that produce corrupted results. `git-filter-repo` is the recommended replacement — orders of magnitude faster, safer defaults, and it forces a fresh clone so you can't half-rewrite a repo in place. Use it for removing files, purging secrets, splitting a repo, or rewriting author details.

**10.10 — How Git stores history efficiently**

Content-addressed storage means identical content is stored once regardless of how many commits or branches reference it. Objects start loose, then `gc` packs them into packfiles using delta compression — storing similar objects as deltas against each other, chosen heuristically by size and name similarity rather than by commit order. Packfiles are further zlib-compressed. This is why a repo with long history can be surprisingly small, and why a few committed binaries (which don't delta well) can make it surprisingly large.
