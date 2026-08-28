# Git — Answer Key

Companion to Domain 1 of the DevOps Interview Skills Matrix. Numbering matches item for item.

Answers are written as *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

---

## 1. Setup & configuration


## 1. Setup & configuration

**1.1 — How would you configure Git user name, email, editor, and default branch on a new machine**

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

**1.2 — If commits from a repo are showing the wrong author or default branch, how would you diagnose and fix the Git config**

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

**1.3 — How would you explain Git config scopes: system, global, local, and worktree**

Three levels, narrowest wins: `--system` (all users, `/etc/gitconfig`), `--global` (your user, `~/.gitconfig`), `--local` (this repo, `.git/config`). There's also `--worktree`. Check where a value came from with `git config --list --show-origin`, which is the fastest way to answer "why is this repo using the wrong email".

**1.4 — When a repository is using an unexpected Git setting, how would you find which config file is winning**

Three levels, narrowest wins: `--system` (all users, `/etc/gitconfig`), `--global` (your user, `~/.gitconfig`), `--local` (this repo, `.git/config`). There's also `--worktree`. Check where a value came from with `git config --list --show-origin`, which is the fastest way to answer "why is this repo using the wrong email".

**1.5 — How would you create useful Git aliases for everyday work**

```bash
git config --global alias.lg "log --oneline --graph --decorate --all"
git config --global alias.st "status -sb"
```

Shell commands need a `!` prefix: `alias.cleanup = '!git branch --merged | grep -v main | xargs git branch -d'`.

**1.6 — What makes a Git alias helpful, and when would you use a shell alias with the `!` prefix**

```bash
git config --global alias.lg "log --oneline --graph --decorate --all"
git config --global alias.st "status -sb"
```

Shell commands need a `!` prefix: `alias.cleanup = '!git branch --merged | grep -v main | xargs git branch -d'`.

**1.7 — How would you set up SSH authentication for GitHub or another Git host**

Generate with `ssh-keygen -t ed25519 -C "label"`, add the public key to the host, test with `ssh -T git@github.com`. Rotation: generate the new key, add it, verify it works, *then* remove the old one from the host. Keys live in `~/.ssh`; the private key must be `600`. Multiple keys are handled in `~/.ssh/config` with `Host` blocks and `IdentityFile`.

**1.8 — How would you rotate a Git SSH key without locking yourself or a team out**

Generate with `ssh-keygen -t ed25519 -C "label"`, add the public key to the host, test with `ssh -T git@github.com`. Rotation: generate the new key, add it, verify it works, *then* remove the old one from the host. Keys live in `~/.ssh`; the private key must be `600`. Multiple keys are handled in `~/.ssh/config` with `Host` blocks and `IdentityFile`.

**1.9 — How would you sign Git commits with GPG or SSH and verify the signature**

`git config --global commit.gpgsign true` plus a signing key. SSH signing is now simpler than GPG: `gpg.format = ssh` and `user.signingkey` pointing at your public key. Verify with `git log --show-signature`. The point is provenance — proving a commit came from who it claims to, which matters because the author field is trivially forgeable.

**1.10 — Why do signed commits matter if Git already records an author name and email**

`git config --global commit.gpgsign true` plus a signing key. SSH signing is now simpler than GPG: `gpg.format = ssh` and `user.signingkey` pointing at your public key. Verify with `git log --show-signature`. The point is provenance — proving a commit came from who it claims to, which matters because the author field is trivially forgeable.

**1.11 — How would you write a `.gitignore` rule and confirm it is working**

`.gitignore` only affects *untracked* files. Once a file is tracked, ignoring it does nothing. Fix:

```bash
git rm --cached path/to/file
```

then commit. `--cached` removes it from the index but leaves it on disk. Use `git check-ignore -v <path>` to find which rule (or which file) is matching. Note precedence: repo `.gitignore`, then `.git/info/exclude` for local-only ignores, then the global ignore file.

**1.12 — Why does a file keep appearing in Git after you added it to `.gitignore`, and how would you fix it**

`.gitignore` only affects *untracked* files. Once a file is tracked, ignoring it does nothing. Fix:

```bash
git rm --cached path/to/file
```

then commit. `--cached` removes it from the index but leaves it on disk. Use `git check-ignore -v <path>` to find which rule (or which file) is matching. Note precedence: repo `.gitignore`, then `.git/info/exclude` for local-only ignores, then the global ignore file.

**1.13 — How would you use `.gitattributes` for line endings, binary files, diff drivers, or LFS**

Controls per-path behaviour. Most common use is line endings: `* text=auto` normalises to LF in the repo. Also marks binaries (`*.png binary`) so Git doesn't try to diff them, sets custom diff drivers, marks generated files with `linguist-generated`, and configures `merge=ours` for files like changelogs. Unlike `.gitignore`, it's committed and applies to everyone, which is the point.

**1.14 — When should a rule live in `.gitattributes` instead of `.gitignore`**

Controls per-path behaviour. Most common use is line endings: `* text=auto` normalises to LF in the repo. Also marks binaries (`*.png binary`) so Git doesn't try to diff them, sets custom diff drivers, marks generated files with `linguist-generated`, and configures `merge=ours` for files like changelogs. Unlike `.gitignore`, it's committed and applies to everyone, which is the point.

**1.15 — How would you set up Git LFS for large binary assets**

Replaces large files with pointer files, storing the real content on a separate server. Warranted for binaries that change often — design assets, ML models, media. Not warranted for large files that never change (the delta cost is low anyway) and it adds a hard dependency: without the LFS client, a clone gives you pointer text instead of files. Track with `git lfs track "*.psd"`, which writes to `.gitattributes`.

**1.16 — When is Git LFS worth using, and what tradeoffs does it introduce for clones and contributors**

Replaces large files with pointer files, storing the real content on a separate server. Warranted for binaries that change often — design assets, ML models, media. Not warranted for large files that never change (the delta cost is low anyway) and it adds a hard dependency: without the LFS client, a clone gives you pointer text instead of files. Track with `git lfs track "*.psd"`, which writes to `.gitattributes`.


## 2. Core workflow

**2.1 — How would you explain the working directory, index, and HEAD in Git**

- **Working directory** — the files on disk, what you're editing.
- **Index (staging area)** — a snapshot you're building for the next commit. `git add` copies from working directory to index.
- **HEAD** — a pointer to the commit at the tip of the current branch; the last committed state.

`git diff` compares working directory to index. `git diff --staged` compares index to HEAD. `git status` describes both gaps. The index existing as a separate layer is what makes partial staging possible.

**2.2 — Which Git diff commands would you use to prove what is unstaged, staged, and committed**

- **Working directory** — the files on disk, what you're editing.
- **Index (staging area)** — a snapshot you're building for the next commit. `git add` copies from working directory to index.
- **HEAD** — a pointer to the commit at the tip of the current branch; the last committed state.

`git diff` compares working directory to index. `git diff --staged` compares index to HEAD. `git status` describes both gaps. The index existing as a separate layer is what makes partial staging possible.

**2.3 — How would you use `git add -p` to stage only part of a file**

Interactively stage individual hunks. Prompts per hunk: `y` stage, `n` skip, `s` split into smaller hunks, `e` edit the hunk manually, `q` quit. Use it to split unrelated changes in one file into separate commits. `git add -p` is the single highest-value habit for producing reviewable commits.

**2.4 — Why is partial staging useful when preparing clean commits for review**

Interactively stage individual hunks. Prompts per hunk: `y` stage, `n` skip, `s` split into smaller hunks, `e` edit the hunk manually, `q` quit. Use it to split unrelated changes in one file into separate commits. `git add -p` is the single highest-value habit for producing reviewable commits.

**2.5 — How would you unstage a file without losing your local changes**

```bash
git restore --staged <file>    # modern
git reset HEAD <file>          # older equivalent
```

Both move the change back to unstaged; the file on disk is untouched. Note `git restore <file>` *without* `--staged` discards working-directory changes — different and destructive.

**2.6 — What is the difference between `git restore --staged <file>` and `git restore <file>`**

```bash
git restore --staged <file>    # modern
git reset HEAD <file>          # older equivalent
```

Both move the change back to unstaged; the file on disk is untouched. Note `git restore <file>` *without* `--staged` discards working-directory changes — different and destructive.

**2.7 — What makes a Git commit message clear and useful**

Subject line under ~50 chars, imperative mood ("Add retry to webhook handler", not "Added" or "Adds"), blank line, then a body explaining *why*. The diff already shows what changed; the message exists to explain the reasoning that isn't recoverable from the code. Reference the issue. A commit should be one logical change — if the message needs "and", it's probably two commits.

**2.8 — How would you decide whether one set of changes should be one commit or several commits**

Subject line under ~50 chars, imperative mood ("Add retry to webhook handler", not "Added" or "Adds"), blank line, then a body explaining *why*. The diff already shows what changed; the message exists to explain the reasoning that isn't recoverable from the code. Reference the issue. A commit should be one logical change — if the message needs "and", it's probably two commits.

**2.9 — How would you amend the last commit message or add staged changes to it**

```bash
git commit --amend                    # edit message and/or include staged changes
git commit --amend --no-edit          # keep message, just add staged changes
```

Amend creates a *new* commit and discards the old one, so never amend something already pushed to a shared branch without understanding the force-push consequence.

**2.10 — Why can amending a pushed commit cause problems for other people**

```bash
git commit --amend                    # edit message and/or include staged changes
git commit --amend --no-edit          # keep message, just add staged changes
```

Amend creates a *new* commit and discards the old one, so never amend something already pushed to a shared branch without understanding the force-push consequence.

**2.11 — How would you explain what lives inside the `.git/` directory**

`objects/` (all content, as blobs/trees/commits/tags), `refs/` (branch and tag pointers), `HEAD` (pointer to current ref), `index` (the staging area, a binary file), `config` (local config), `logs/` (the reflog), `hooks/`. Deleting `.git/` turns the repo into a plain directory — everything Git knows lives there.

**2.12 — What would happen if someone deleted `.git/`, and why**

`objects/` (all content, as blobs/trees/commits/tags), `refs/` (branch and tag pointers), `HEAD` (pointer to current ref), `index` (the staging area, a binary file), `config` (local config), `logs/` (the reflog), `hooks/`. Deleting `.git/` turns the repo into a plain directory — everything Git knows lives there.

**2.13 — How would you explain Git objects: blob, tree, commit, and tag**

Four types, all content-addressed by SHA:
- **Blob** — file contents. No name, no metadata.
- **Tree** — a directory listing: names, modes, and pointers to blobs and other trees.
- **Commit** — a pointer to one tree (the full snapshot), plus parent commit(s), author, committer, message.
- **Tag** — an annotated tag object pointing at a commit, with its own message and signature.

Key insight: Git stores **snapshots, not diffs**. Diffs are computed on demand. Identical content anywhere in history is stored once, because the SHA is the same. Inspect with `git cat-file -p <sha>`.

**2.14 — How would you inspect a Git object directly and prove that Git stores snapshots, not just diffs**

Four types, all content-addressed by SHA:
- **Blob** — file contents. No name, no metadata.
- **Tree** — a directory listing: names, modes, and pointers to blobs and other trees.
- **Commit** — a pointer to one tree (the full snapshot), plus parent commit(s), author, committer, message.
- **Tag** — an annotated tag object pointing at a commit, with its own message and signature.

Key insight: Git stores **snapshots, not diffs**. Diffs are computed on demand. Identical content anywhere in history is stored once, because the SHA is the same. Inspect with `git cat-file -p <sha>`.


## 3. Branching

**3.1 — How would you create, switch, rename, and delete Git branches**

```bash
git switch -c feature      # create and switch
git switch main            # switch
git branch -m old new      # rename
git branch -d feature      # delete (safe: refuses if unmerged)
git branch -D feature      # force delete
```

`-d` refusing on unmerged work is a feature, not an obstacle.

**3.2 — Why does `git branch -d` refuse some deletes, and when would `-D` be appropriate**

```bash
git switch -c feature      # create and switch
git switch main            # switch
git branch -m old new      # rename
git branch -d feature      # delete (safe: refuses if unmerged)
git branch -D feature      # force delete
```

`-d` refusing on unmerged work is a feature, not an obstacle.

**3.3 — How would you explain `git switch` and `git restore` compared with older `git checkout` usage**

`git checkout` was overloaded — it changed branches *and* discarded file changes, which meant a typo could destroy work. Git 2.23 split it: `switch` for branches, `restore` for files. `checkout` still works and you'll see it everywhere, but the split is clearer and safer.

**3.4 — Why did Git split branch switching and file restoration into separate commands**

`git checkout` was overloaded — it changed branches *and* discarded file changes, which meant a typo could destroy work. Git 2.23 split it: `switch` for branches, `restore` for files. `checkout` still works and you'll see it everywhere, but the split is clearer and safer.

**3.5 — How would you set a local branch to track a remote branch**

```bash
git push -u origin feature       # push and set upstream
git branch -u origin/feature     # set upstream for existing branch
```

Upstream is what makes bare `git push` and `git pull` work, and what lets `git status` say "ahead by 2 commits".

**3.6 — What does an upstream branch change about `git status`, `git pull`, and `git push`**

```bash
git push -u origin feature       # push and set upstream
git branch -u origin/feature     # set upstream for existing branch
```

Upstream is what makes bare `git push` and `git pull` work, and what lets `git status` say "ahead by 2 commits".

**3.7 — How would you list merged and unmerged branches and prune stale remote references**

```bash
git branch --merged main       # safe to delete
git branch --no-merged main
git fetch --prune              # remove local refs to deleted remote branches
```

`--merged` is relative to the branch you name — check against the right base. Note it reports false negatives for squash-merged branches, since the commits technically never merged.

**3.8 — What can make `git branch --merged` misleading after squash merges**

```bash
git branch --merged main       # safe to delete
git branch --no-merged main
git fetch --prune              # remove local refs to deleted remote branches
```

`--merged` is relative to the branch you name — check against the right base. Note it reports false negatives for squash-merged branches, since the commits technically never merged.

**3.9 — How would you compare trunk-based development, GitFlow, and release branches**

- **Trunk-based** — short-lived branches (hours to a day), merge to main constantly, feature flags hide incomplete work. Requires good CI and test coverage. Best fit for continuous delivery.
- **GitFlow** — develop/release/hotfix/feature branches. Heavy. Designed for versioned software with supported releases, not for services deploying multiple times a day.
- **Release branches** — trunk plus a branch cut per release for stabilisation and backports.

Choosing: the question is release model, not team size. If you deploy continuously, trunk-based; GitFlow's overhead buys you nothing and its long-lived branches actively fight integration. If you ship versioned artifacts customers install and you support old versions, release branches earn their cost.

**3.10 — Given a team and release model, how would you choose a branching strategy and defend it**

- **Trunk-based** — short-lived branches (hours to a day), merge to main constantly, feature flags hide incomplete work. Requires good CI and test coverage. Best fit for continuous delivery.
- **GitFlow** — develop/release/hotfix/feature branches. Heavy. Designed for versioned software with supported releases, not for services deploying multiple times a day.
- **Release branches** — trunk plus a branch cut per release for stabilisation and backports.

Choosing: the question is release model, not team size. If you deploy continuously, trunk-based; GitFlow's overhead buys you nothing and its long-lived branches actively fight integration. If you ship versioned artifacts customers install and you support old versions, release branches earn their cost.

**3.11 — How would you recognise a detached HEAD state**

HEAD points at a commit rather than a branch — happens when you check out a SHA or tag. Commits made here belong to no branch and will eventually be garbage collected. Recover with:

```bash
git switch -c rescue-branch   # keep the work
git switch main               # discard it
```

If you already left and lost the SHA, `git reflog` has it.

**3.12 — If you made commits while detached, how would you keep or recover that work safely**

HEAD points at a commit rather than a branch — happens when you check out a SHA or tag. Commits made here belong to no branch and will eventually be garbage collected. Recover with:

```bash
git switch -c rescue-branch   # keep the work
git switch main               # discard it
```

If you already left and lost the SHA, `git reflog` has it.

**3.13 — How would you create and push Git tags**

```bash
git tag v1.0.0                        # lightweight: just a pointer
git tag -a v1.0.0 -m "Release 1.0.0"  # annotated: a real object
git push origin v1.0.0                # tags aren't pushed by default
```

Annotated tags store tagger, date, message, and can be signed — use them for releases. Lightweight tags are fine as private bookmarks. Tags are meant to be immutable; moving a published tag breaks everyone who fetched it.

**3.14 — How would you explain lightweight versus annotated tags, and which would you use for releases**

```bash
git tag v1.0.0                        # lightweight: just a pointer
git tag -a v1.0.0 -m "Release 1.0.0"  # annotated: a real object
git push origin v1.0.0                # tags aren't pushed by default
```

Annotated tags store tagger, date, message, and can be signed — use them for releases. Lightweight tags are fine as private bookmarks. Tags are meant to be immutable; moving a published tag breaks everyone who fetched it.


## 4. Merging & rebasing

**4.1 — How would you merge a branch and inspect the resulting Git history**

`git merge feature` while on the target branch. A merge commit has two parents. `git log --graph --oneline` shows the topology. `git log --first-parent` follows only the mainline, which is often what you actually want on a busy repo.

**4.2 — What does a merge commit with two parents tell you when reading `git log --graph`**

`git merge feature` while on the target branch. A merge commit has two parents. `git log --graph --oneline` shows the topology. `git log --first-parent` follows only the mainline, which is often what you actually want on a busy repo.

**4.3 — How would you explain fast-forward versus `--no-ff` merges**

If the target branch hasn't moved since the feature branched, Git just moves the pointer forward — no merge commit, linear history. `--no-ff` forces a merge commit anyway, which preserves the fact that a branch existed and groups its commits.

Force fast-forward (`--ff-only`) when you want strictly linear history and want the merge to fail if a rebase is needed. Force `--no-ff` when the branch boundary is meaningful — it makes the whole feature revertable as one commit, which is a real operational advantage.

**4.4 — When would you require `--ff-only`, and when would you deliberately force `--no-ff`**

If the target branch hasn't moved since the feature branched, Git just moves the pointer forward — no merge commit, linear history. `--no-ff` forces a merge commit anyway, which preserves the fact that a branch existed and groups its commits.

Force fast-forward (`--ff-only`) when you want strictly linear history and want the merge to fail if a rebase is needed. Force `--no-ff` when the branch boundary is meaningful — it makes the whole feature revertable as one commit, which is a real operational advantage.

**4.5 — How would you rebase a feature branch onto the latest main branch**

```bash
git switch feature
git fetch origin
git rebase origin/main
```

Replays each of your commits on top of the new base, creating new commits with new SHAs. Result is linear history with no merge commit. If conflicts occur, resolve, `git add`, `git rebase --continue`.

**4.6 — What happens to commit SHAs during a rebase, and how do you continue after conflicts**

```bash
git switch feature
git fetch origin
git rebase origin/main
```

Replays each of your commits on top of the new base, creating new commits with new SHAs. Result is linear history with no merge commit. If conflicts occur, resolve, `git add`, `git rebase --continue`.

**4.7 — How would you use interactive rebase to squash, fixup, reword, reorder, or drop commits**

```bash
git rebase -i HEAD~5
```

Opens an editor listing commits oldest-first. Actions: `pick` (keep), `reword` (change message), `edit` (stop to amend), `squash` (merge into previous, combine messages), `fixup` (merge into previous, discard message), `drop` (delete), and reorder by moving lines. `--autosquash` with commits made as `git commit --fixup=<sha>` automates the common case.

**4.8 — When would `--autosquash` make an interactive rebase cleaner**

```bash
git rebase -i HEAD~5
```

Opens an editor listing commits oldest-first. Actions: `pick` (keep), `reword` (change message), `edit` (stop to amend), `squash` (merge into previous, combine messages), `fixup` (merge into previous, discard message), `drop` (delete), and reorder by moving lines. `--autosquash` with commits made as `git commit --fixup=<sha>` automates the common case.

**4.9 — What is the golden rule of rebasing**

Don't rebase commits that others have based work on. Rebasing rewrites SHAs; anyone who pulled the old commits now has divergent history and gets a mess on their next pull.

When it's safe to break it: your own feature branch that nobody else is using, even if it's pushed — force-push with lease and carry on. Also fine if the whole team agrees and coordinates, though that's rarely worth it. The rule is really about *shared* branches, not *pushed* branches.

**4.10 — When is it safe to rebase a pushed branch, and what must you do afterwards**

Don't rebase commits that others have based work on. Rebasing rewrites SHAs; anyone who pulled the old commits now has divergent history and gets a mess on their next pull.

When it's safe to break it: your own feature branch that nobody else is using, even if it's pushed — force-push with lease and carry on. Also fine if the whole team agrees and coordinates, though that's rarely worth it. The rule is really about *shared* branches, not *pushed* branches.

**4.11 — How would you argue rebase versus merge for a 20-person engineering team**

The case for rebase/squash-merge: linear history, easy to read, `git bisect` works cleanly, each PR is one commit on main. The case for merge: preserves true history, no rewriting, no force-pushes, keeps the individual commits of a large change.

A defensible position for that team size: rebase or squash *feature branches before merging*, but never rebase main. Squash-merge for small PRs; merge commits for large features where the individual commits carry real information. The important part is that it's enforced in branch protection rather than left to preference, because mixed strategies produce the worst of both.

**4.12 — What branch protection or merge policy would you recommend to avoid mixed-history confusion**

The case for rebase/squash-merge: linear history, easy to read, `git bisect` works cleanly, each PR is one commit on main. The case for merge: preserves true history, no rewriting, no force-pushes, keeps the individual commits of a large change.

A defensible position for that team size: rebase or squash *feature branches before merging*, but never rebase main. Squash-merge for small PRs; merge commits for large features where the individual commits carry real information. The important part is that it's enforced in branch protection rather than left to preference, because mixed strategies produce the worst of both.

**4.13 — How would you enable and use Git `rerere`**

"Reuse recorded resolution." `git config --global rerere.enabled true`. Git records how you resolved a conflict and replays it automatically next time the same conflict appears. Valuable during long rebases and repeated merges of a long-lived branch. It's silently helpful, which is also its risk — it can apply a stale resolution, so review the result.

**4.14 — What risk should you watch for when Git reuses a recorded conflict resolution**

"Reuse recorded resolution." `git config --global rerere.enabled true`. Git records how you resolved a conflict and replays it automatically next time the same conflict appears. Valuable during long rebases and repeated merges of a long-lived branch. It's silently helpful, which is also its risk — it can apply a stale resolution, so review the result.

**4.15 — How would you compare squash-merge and merge commits**

Squash-merge collapses a PR into one commit on main. History is clean, but the individual commits are gone and the branch's relationship to main is lost — which is why `git branch --merged` won't list it.

For `git bisect`: squash-merge is actually *better*. Each commit on main is a complete, tested change, so bisect lands on a meaningful unit. With merge commits, bisect can land on an intermediate commit from inside a feature branch that never built on its own. `git bisect --first-parent` mitigates that.

**4.16 — How do squash merges and merge commits affect `git bisect` and branch history**

Squash-merge collapses a PR into one commit on main. History is clean, but the individual commits are gone and the branch's relationship to main is lost — which is why `git branch --merged` won't list it.

For `git bisect`: squash-merge is actually *better*. Each commit on main is a complete, tested change, so bisect lands on a meaningful unit. With merge commits, bisect can land on an intermediate commit from inside a feature branch that never built on its own. `git bisect --first-parent` mitigates that.


## 5. Conflict resolution

**5.1 — How do you read Git conflict markers and identify each side**

```
<<<<<<< HEAD
your version
=======
their version
>>>>>>> feature-branch
```

Top is the current branch (HEAD), bottom is what's being merged in. `git config merge.conflictStyle zdiff3` adds a third section showing the common ancestor, which usually makes the intent obvious and is worth enabling permanently.

**5.2 — How does `merge.conflictStyle zdiff3` help when resolving conflicts**

```
<<<<<<< HEAD
your version
=======
their version
>>>>>>> feature-branch
```

Top is the current branch (HEAD), bottom is what's being merged in. `git config merge.conflictStyle zdiff3` adds a third section showing the common ancestor, which usually makes the intent obvious and is worth enabling permanently.

**5.3 — How would you resolve a conflict during a Git merge**

Edit the file, remove all markers, `git add <file>` to mark resolved, then `git commit`. `git status` lists unmerged paths. `git diff` during a conflict shows a combined diff against both parents.

**5.4 — Which Git commands show unresolved paths and mark a merge conflict as resolved**

Edit the file, remove all markers, `git add <file>` to mark resolved, then `git commit`. `git status` lists unmerged paths. `git diff` during a conflict shows a combined diff against both parents.

**5.5 — How would you resolve a conflict during a Git rebase**

Same mechanics, but "ours" and "theirs" feel backwards. During a rebase, Git is replaying *your* commits onto the base branch — so at each step, "ours" is the base branch (the thing being replayed onto) and "theirs" is your commit. This trips people up constantly. Then `git add` and `git rebase --continue`.

**5.6 — Why do `ours` and `theirs` feel inverted during a rebase conflict**

Same mechanics, but "ours" and "theirs" feel backwards. During a rebase, Git is replaying *your* commits onto the base branch — so at each step, "ours" is the base branch (the thing being replayed onto) and "theirs" is your commit. This trips people up constantly. Then `git add` and `git rebase --continue`.

**5.7 — How would you abort a merge, rebase, or cherry-pick cleanly**

```bash
git merge --abort
git rebase --abort
git cherry-pick --abort
```

Returns to the state before you started. Safe, and the right instinct when a merge turns out to be much larger than expected.

**5.8 — When should you stop and abort instead of continuing through a large conflict**

```bash
git merge --abort
git rebase --abort
git cherry-pick --abort
```

Returns to the state before you started. Safe, and the right instinct when a merge turns out to be much larger than expected.

**5.9 — How would you use `checkout --ours` and `checkout --theirs` deliberately**

```bash
git checkout --ours <file>     # take current branch's version wholesale
git checkout --theirs <file>   # take incoming version wholesale
```

Use deliberately for files where merging line by line is meaningless — lockfiles, generated output, binary assets. Remember the inversion during rebase (5.3).

**5.10 — For which files is taking one whole side safer than line-by-line conflict resolution**

```bash
git checkout --ours <file>     # take current branch's version wholesale
git checkout --theirs <file>   # take incoming version wholesale
```

Use deliberately for files where merging line by line is meaningless — lockfiles, generated output, binary assets. Remember the inversion during rebase (5.3).

**5.11 — How would you use a merge tool or three-way diff view**

`git mergetool` launches a configured three-way diff (vimdiff, meld, VS Code, Beyond Compare). The three-way view — base, ours, theirs — is far more informative than the inline markers because you can see what each side actually changed relative to the ancestor.

**5.12 — Why is a three-way conflict view more useful than inline conflict markers alone**

`git mergetool` launches a configured three-way diff (vimdiff, meld, VS Code, Beyond Compare). The three-way view — base, ours, theirs — is far more informative than the inline markers because you can see what each side actually changed relative to the ancestor.

**5.13 — How would you resolve a conflict in a lockfile or generated file**

Don't hand-merge. Take one side, then regenerate:

```bash
git checkout --theirs package-lock.json
npm install    # regenerate from package.json
git add package-lock.json
```

Hand-merging a lockfile produces a file that's internally inconsistent and will fail in ways that are painful to debug. The same applies to any generated artifact — resolve the source, regenerate the output.

**5.14 — Why is hand-merging generated output usually the wrong fix**

Don't hand-merge. Take one side, then regenerate:

```bash
git checkout --theirs package-lock.json
npm install    # regenerate from package.json
git add package-lock.json
```

Hand-merging a lockfile produces a file that's internally inconsistent and will fail in ways that are painful to debug. The same applies to any generated artifact — resolve the source, regenerate the output.


## 6. Undo & recovery

**6.1 — How would you explain `git reset --soft`, `--mixed`, and `--hard` precisely**

All three move the branch pointer to the target commit. They differ in what else they touch:

| Mode | Branch pointer | Index | Working directory |
|---|---|---|---|
| `--soft` | moved | unchanged | unchanged |
| `--mixed` (default) | moved | reset | unchanged |
| `--hard` | moved | reset | **overwritten** |

So `--soft HEAD~1` undoes the commit but leaves everything staged, ready to recommit. `--mixed HEAD~1` leaves changes unstaged. `--hard HEAD~1` destroys the changes. `--hard` is the only one that loses work.

**6.2 — Which parts of Git state does each reset mode change: branch pointer, index, and working directory**

All three move the branch pointer to the target commit. They differ in what else they touch:

| Mode | Branch pointer | Index | Working directory |
|---|---|---|---|
| `--soft` | moved | unchanged | unchanged |
| `--mixed` (default) | moved | reset | unchanged |
| `--hard` | moved | reset | **overwritten** |

So `--soft HEAD~1` undoes the commit but leaves everything staged, ready to recommit. `--mixed HEAD~1` leaves changes unstaged. `--hard HEAD~1` destroys the changes. `--hard` is the only one that loses work.

**6.3 — How would you revert a commit on a shared branch**

```bash
git revert <sha>
```

Creates a *new* commit that undoes the change. History is preserved and nothing is rewritten, so collaborators are unaffected. Reset rewrites history, which on a shared branch means everyone else's next pull produces divergence and confusion. Rule: reset for local, revert for published.

Reverting a merge commit needs `-m 1` to specify which parent is the mainline. Note the follow-on trap: after reverting a merge, re-merging that branch won't reintroduce the changes, because Git considers them already merged. You have to revert the revert.

**6.4 — Why should you use `git revert` instead of `git reset` for published history**

```bash
git revert <sha>
```

Creates a *new* commit that undoes the change. History is preserved and nothing is rewritten, so collaborators are unaffected. Reset rewrites history, which on a shared branch means everyone else's next pull produces divergence and confusion. Rule: reset for local, revert for published.

Reverting a merge commit needs `-m 1` to specify which parent is the mainline. Note the follow-on trap: after reverting a merge, re-merging that branch won't reintroduce the changes, because Git considers them already merged. You have to revert the revert.

**6.5 — How would you recover a lost commit or deleted branch using reflog**

```bash
git reflog
git switch -c recovered <sha>    # or git reset --hard <sha>
```

The reflog records every position HEAD has held — commits, resets, rebases, checkouts — for around 90 days by default. It's local-only and it's why almost nothing in Git is truly lost. This is the first thing to reach for after any "I've destroyed everything" moment.

**6.6 — Why is the reflog local-only, and what kind of Git mistakes can it recover from**

```bash
git reflog
git switch -c recovered <sha>    # or git reset --hard <sha>
```

The reflog records every position HEAD has held — commits, resets, rebases, checkouts — for around 90 days by default. It's local-only and it's why almost nothing in Git is truly lost. This is the first thing to reach for after any "I've destroyed everything" moment.

**6.7 — How would you recover a deleted file from an earlier commit**

```bash
git restore --source=<sha> -- path/to/file
git checkout <sha> -- path/to/file      # older syntax
```

To find when it was deleted: `git log --diff-filter=D -- path/to/file`.

**6.8 — How would you find the commit where a file was deleted before restoring it**

```bash
git restore --source=<sha> -- path/to/file
git checkout <sha> -- path/to/file      # older syntax
```

To find when it was deleted: `git log --diff-filter=D -- path/to/file`.

**6.9 — How would you recover work after a bad `git reset --hard`**

If the work was **committed**, reflog has it (6.3). If it was **staged but not committed**, the blobs are still in the object database:

```bash
git fsck --lost-found
```

which surfaces dangling blobs you can inspect with `git cat-file -p`. If it was **never staged**, it's gone — Git never saw it. That's the honest answer, and it's the argument for committing early and often, even if messily, since you can always tidy history later.

**6.10 — When is uncommitted work unrecoverable, and what does that teach you about staging and committing**

If the work was **committed**, reflog has it (6.3). If it was **staged but not committed**, the blobs are still in the object database:

```bash
git fsck --lost-found
```

which surfaces dangling blobs you can inspect with `git cat-file -p`. If it was **never staged**, it's gone — Git never saw it. That's the honest answer, and it's the argument for committing early and often, even if messily, since you can always tidy history later.

**6.11 — How would you undo a bad rebase using `ORIG_HEAD` or reflog**

```bash
git reset --hard ORIG_HEAD
```

Git sets `ORIG_HEAD` before dangerous operations. If that's been overwritten, find the pre-rebase commit in `git reflog` and reset to it.

**6.12 — What would you do if `ORIG_HEAD` no longer points to the pre-rebase state**

```bash
git reset --hard ORIG_HEAD
```

Git sets `ORIG_HEAD` before dangerous operations. If that's been overwritten, find the pre-rebase commit in `git reflog` and reset to it.

**6.13 — How would you remove a leaked secret from Git history**

Order matters: **rotate the secret first**. History rewriting doesn't help if the secret was ever pushed — assume it's compromised the moment it left your machine. Then clean:

```bash
git filter-repo --path secrets.env --invert-paths
```

Blast radius: every commit after the touched one gets a new SHA, so everyone must re-clone or hard reset. Open PRs break. Forks keep the old objects. GitHub retains unreferenced commits accessible by SHA until support purges them. Tags need re-pointing. This is why rotation is the real fix and rewriting is cosmetic cleanup.

**6.14 — Why is rotating the secret more important than rewriting Git history**

Order matters: **rotate the secret first**. History rewriting doesn't help if the secret was ever pushed — assume it's compromised the moment it left your machine. Then clean:

```bash
git filter-repo --path secrets.env --invert-paths
```

Blast radius: every commit after the touched one gets a new SHA, so everyone must re-clone or hard reset. Open PRs break. Forks keep the old objects. GitHub retains unreferenced commits accessible by SHA until support purges them. Tags need re-pointing. This is why rotation is the real fix and rewriting is cosmetic cleanup.

**6.15 — How would you clean untracked files safely**

```bash
git clean -n -d      # dry run — ALWAYS do this first
git clean -fd        # then actually delete
```

`-x` also removes ignored files, which will delete `node_modules`, `.env`, and build output. `git clean` is unrecoverable — these files were never in Git, so there's no reflog to save you.

**6.16 — Why should `git clean -n` come before `git clean -fd`, and what extra risk does `-x` add**

```bash
git clean -n -d      # dry run — ALWAYS do this first
git clean -fd        # then actually delete
```

`-x` also removes ignored files, which will delete `node_modules`, `.env`, and build output. `git clean` is unrecoverable — these files were never in Git, so there's no reflog to save you.


## 7. Inspection & investigation

**7.1 — How would you use `git log` flags to inspect history effectively**

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

**7.2 — When would you use `git log -S` or `git log -G` instead of a plain log search**

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

**7.3 — How would you diff the working tree, index, HEAD, and another branch**

```bash
git diff                    # working directory vs index
git diff --staged           # index vs HEAD
git diff HEAD               # working directory vs HEAD
git diff main..feature      # tip to tip
git diff main...feature     # feature vs their common ancestor
```

The three-dot form is what code review shows — changes *on* the branch, excluding changes main made independently.

**7.4 — What is the practical difference between two-dot and three-dot Git diffs**

```bash
git diff                    # working directory vs index
git diff --staged           # index vs HEAD
git diff HEAD               # working directory vs HEAD
git diff main..feature      # tip to tip
git diff main...feature     # feature vs their common ancestor
```

The three-dot form is what code review shows — changes *on* the branch, excluding changes main made independently.

**7.5 — How would you use `git blame` to trace where a line came from**

```bash
git blame path/to/file
git blame -L 40,60 file           # limit to a line range
git blame -w -C file              # ignore whitespace, detect moved code
```

`-w -C` matters because a reformat commit otherwise makes every line blame to the person who ran the formatter. `--ignore-rev` and `.git-blame-ignore-revs` let you permanently exclude formatting commits.

**7.6 — How can you avoid misleading blame results after formatting or moved-code commits**

```bash
git blame path/to/file
git blame -L 40,60 file           # limit to a line range
git blame -w -C file              # ignore whitespace, detect moved code
```

`-w -C` matters because a reformat commit otherwise makes every line blame to the person who ran the formatter. `--ignore-rev` and `.git-blame-ignore-revs` let you permanently exclude formatting commits.

**7.7 — How would you use `git bisect` to find the commit that introduced a bug**

```bash
git bisect start
git bisect bad                 # current commit is broken
git bisect good v1.2.0         # this one was fine
# test, then mark each commit:
git bisect good | git bisect bad
git bisect reset               # when done
```

Binary search across history — 1000 commits takes about 10 tests. The main requirement is a reliable way to test each commit.

**7.8 — What makes a good and bad commit useful when starting a bisect session**

```bash
git bisect start
git bisect bad                 # current commit is broken
git bisect good v1.2.0         # this one was fine
# test, then mark each commit:
git bisect good | git bisect bad
git bisect reset               # when done
```

Binary search across history — 1000 commits takes about 10 tests. The main requirement is a reliable way to test each commit.

**7.9 — How would you automate `git bisect` with `bisect run`**

```bash
git bisect run ./test-script.sh
```

Script exits 0 for good, non-zero for bad, 125 to skip an untestable commit. Fully automatic. This turns bisect from a tedious manual process into something you start and walk away from, and it's the version worth mentioning in an interview.

**7.10 — What exit codes should a bisect test script return for good, bad, and skipped commits**

```bash
git bisect run ./test-script.sh
```

Script exits 0 for good, non-zero for bad, 125 to skip an untestable commit. Fully automatic. This turns bisect from a tedious manual process into something you start and walk away from, and it's the version worth mentioning in an interview.

**7.11 — How would you search Git history for when a string was added or removed**

`git log -S "string"` finds commits where the number of occurrences changed — i.e. where it was added or removed. `git log -G "regex"` finds commits whose diff text matches. Add `--all` to search every branch, and `-p` to see the actual change.

**7.12 — How do `git log -S` and `git log -G` differ when investigating history**

`git log -S "string"` finds commits where the number of occurrences changed — i.e. where it was added or removed. `git log -G "regex"` finds commits whose diff text matches. Add `--all` to search every branch, and `-p` to see the actual change.

**7.13 — How would you show a file history across renames**

```bash
git log --follow -- path/to/file
```

Git doesn't record renames; it infers them by content similarity. `--follow` enables that inference, which is why file history looks truncated without it.

**7.14 — Why does Git infer renames instead of storing them directly**

```bash
git log --follow -- path/to/file
```

Git doesn't record renames; it infers them by content similarity. `--follow` enables that inference, which is why file history looks truncated without it.

**7.15 — How would you inspect an arbitrary Git object with `cat-file` or `show`**

```bash
git cat-file -t <sha>    # type
git cat-file -p <sha>    # pretty-print contents
git rev-parse HEAD       # resolve a ref to a SHA
git show <sha>           # commit with its diff
git ls-tree HEAD         # tree contents
```

Useful for understanding the object model concretely, and occasionally for recovering things.

**7.16 — What commands would you use to identify an object type, print it, and resolve a ref to a SHA**

```bash
git cat-file -t <sha>    # type
git cat-file -p <sha>    # pretty-print contents
git rev-parse HEAD       # resolve a ref to a SHA
git show <sha>           # commit with its diff
git ls-tree HEAD         # tree contents
```

Useful for understanding the object model concretely, and occasionally for recovering things.


## 8. Remotes & collaboration

**8.1 — How would you add, rename, inspect, or change Git remotes**

```bash
git remote -v
git remote add upstream git@github.com:org/repo.git
git remote rename origin old-origin
git remote set-url origin <new-url>
```

**8.2 — How would you explain the difference between `origin` and `upstream` in a repo**

```bash
git remote -v
git remote add upstream git@github.com:org/repo.git
git remote rename origin old-origin
git remote set-url origin <new-url>
```

**8.3 — How would you explain `git fetch` versus `git pull`**

`fetch` downloads remote refs and objects but doesn't touch your working branch. `pull` is `fetch` plus an immediate `merge` (or `rebase`). Fetch-first is usually right because it lets you inspect what arrived — `git log HEAD..origin/main` — before deciding how to integrate it. `pull` on a branch with local commits is where surprise merge commits come from.

**8.4 — Why is fetching first often safer than pulling immediately on a branch with local commits**

`fetch` downloads remote refs and objects but doesn't touch your working branch. `pull` is `fetch` plus an immediate `merge` (or `rebase`). Fetch-first is usually right because it lets you inspect what arrived — `git log HEAD..origin/main` — before deciding how to integrate it. `pull` on a branch with local commits is where surprise merge commits come from.

**8.5 — How would you configure `pull.rebase` and explain the choice**

```bash
git config --global pull.rebase true
```

Makes `git pull` rebase your local commits on top of the fetched ones instead of merging. Produces linear history and avoids the noise of "Merge branch 'main' of ..." commits. The tradeoff is that it rewrites your local commits, so a conflict mid-pull is a rebase conflict. Setting `pull.ff only` is a defensible alternative: pull fails if a merge or rebase is needed, forcing you to decide explicitly.

**8.6 — When would `pull.ff only` be a better default than automatic merge or rebase**

```bash
git config --global pull.rebase true
```

Makes `git pull` rebase your local commits on top of the fetched ones instead of merging. Produces linear history and avoids the noise of "Merge branch 'main' of ..." commits. The tradeoff is that it rewrites your local commits, so a conflict mid-pull is a rebase conflict. Setting `pull.ff only` is a defensible alternative: pull fails if a merge or rebase is needed, forcing you to decide explicitly.

**8.7 — How would you force-push safely with `--force-with-lease`**

```bash
git push --force-with-lease
```

`--force` overwrites the remote branch unconditionally, including commits a colleague pushed while you were working. `--force-with-lease` checks that the remote is still where you last saw it and refuses if someone else pushed. It's the difference between "overwrite" and "overwrite if nothing changed underneath me". Always use the lease version. Note that a background `git fetch` (some IDEs do this) can update your remote-tracking ref and undermine the check — `--force-with-lease=<ref>:<sha>` is the paranoid form.

**8.8 — How is `--force-with-lease` different from `--force`, and what edge case can weaken it**

```bash
git push --force-with-lease
```

`--force` overwrites the remote branch unconditionally, including commits a colleague pushed while you were working. `--force-with-lease` checks that the remote is still where you last saw it and refuses if someone else pushed. It's the difference between "overwrite" and "overwrite if nothing changed underneath me". Always use the lease version. Note that a background `git fetch` (some IDEs do this) can update your remote-tracking ref and undermine the check — `--force-with-lease=<ref>:<sha>` is the paranoid form.

**8.9 — How would you recover after someone force-pushed over your work**

Your commits still exist locally. `git reflog` to find your pre-fetch position, or `origin/branch@{1}` in the reflog for the remote-tracking ref. Create a branch from that SHA, then rebase or cherry-pick onto the new remote state. If it's only on the remote, the pushed-but-orphaned commits may still be retrievable by SHA from the hosting provider's API.

**8.10 — Where would you look locally for the old remote-tracking branch position**

Your commits still exist locally. `git reflog` to find your pre-fetch position, or `origin/branch@{1}` in the reflog for the remote-tracking ref. Create a branch from that SHA, then rebase or cherry-pick onto the new remote state. If it's only on the remote, the pushed-but-orphaned commits may still be retrievable by SHA from the hosting provider's API.

**8.11 — How would you clone a large repository shallowly or partially**

```bash
git clone --depth 1 <url>                 # shallow: only recent history
git clone --filter=blob:none <url>        # partial: blobs fetched on demand
git clone --single-branch --branch main <url>
```

Shallow is standard in CI where history isn't needed — much faster, less disk. Tradeoffs: `git log` is truncated, `bisect` and `blame` are limited, and some operations trigger a fetch anyway. Partial clone (`blob:none`) is usually the better choice for large repos you'll actually work in, since history is intact and file contents arrive lazily. Deepen later with `git fetch --unshallow`.

**8.12 — What tradeoffs do shallow and partial clones create for blame, bisect, log, and later fetches**

```bash
git clone --depth 1 <url>                 # shallow: only recent history
git clone --filter=blob:none <url>        # partial: blobs fetched on demand
git clone --single-branch --branch main <url>
```

Shallow is standard in CI where history isn't needed — much faster, less disk. Tradeoffs: `git log` is truncated, `bisect` and `blame` are limited, and some operations trigger a fetch anyway. Partial clone (`blob:none`) is usually the better choice for large repos you'll actually work in, since history is intact and file contents arrive lazily. Deepen later with `git fetch --unshallow`.

**8.13 — How would you work with a fork using `origin` and `upstream` remotes**

```bash
git clone git@github.com:you/repo.git
git remote add upstream git@github.com:org/repo.git
git fetch upstream
git rebase upstream/main       # or merge
git push origin feature
```

`origin` is your fork, `upstream` is the source. Keep your fork's main clean and unmodified — branch for every change — so syncing stays trivial.

**8.14 — How would you keep your fork synced while keeping feature work isolated**

```bash
git clone git@github.com:you/repo.git
git remote add upstream git@github.com:org/repo.git
git fetch upstream
git rebase upstream/main       # or merge
git push origin feature
```

`origin` is your fork, `upstream` is the source. Keep your fork's main clean and unmodified — branch for every change — so syncing stays trivial.


## 9. Stash & housekeeping

**9.1 — How would you stash and reapply local work**

```bash
git stash
git stash pop
```

Saves modified tracked files and reverts the working directory to HEAD. Stashes are stored as commits in `refs/stash`.

**9.2 — What does Git store when you create a stash**

```bash
git stash
git stash pop
```

Saves modified tracked files and reverts the working directory to HEAD. Stashes are stored as commits in `refs/stash`.

**9.3 — How would you create a named stash and apply a specific stash entry**

```bash
git stash push -m "wip: retry logic"
git stash list
git stash apply stash@{2}
git stash show -p stash@{0}     # see the contents
```

Message your stashes. `git stash list` showing five entries of "WIP on main" is useless.

**9.4 — Why are named stashes easier to use than a list of default WIP messages**

```bash
git stash push -m "wip: retry logic"
git stash list
git stash apply stash@{2}
git stash show -p stash@{0}     # see the contents
```

Message your stashes. `git stash list` showing five entries of "WIP on main" is useless.

**9.5 — How would you stash untracked files as well as tracked changes**

```bash
git stash -u        # include untracked
git stash -a        # include ignored too
```

Plain `git stash` leaves untracked files in place, which surprises people — you switch branches and the new files are still sitting there.

**9.6 — What is the difference between `git stash -u` and `git stash -a`**

```bash
git stash -u        # include untracked
git stash -a        # include ignored too
```

Plain `git stash` leaves untracked files in place, which surprises people — you switch branches and the new files are still sitting there.

**9.7 — How would you explain `git stash apply` versus `git stash pop`**

`pop` applies and deletes the stash; `apply` applies and keeps it. The difference bites when applying to the wrong branch: with `pop`, if the apply conflicts, the stash *is* kept — but if it applies cleanly onto the wrong branch, it's gone from the list and you have to recover it from the reflog. `apply` is safer when you're unsure; delete explicitly with `git stash drop` once you've confirmed.

**9.8 — When can `pop` be riskier than `apply`, especially on the wrong branch**

`pop` applies and deletes the stash; `apply` applies and keeps it. The difference bites when applying to the wrong branch: with `pop`, if the apply conflicts, the stash *is* kept — but if it applies cleanly onto the wrong branch, it's gone from the list and you have to recover it from the reflog. `apply` is safer when you're unsure; delete explicitly with `git stash drop` once you've confirmed.

**9.9 — How would you explain Git garbage collection, loose objects, packed objects, and repo size**

New objects are written individually ("loose"). `git gc` packs them into packfiles with delta compression and prunes unreachable objects past the reflog expiry. Runs automatically on a threshold. `git count-objects -vH` shows the breakdown. Repos bloat from committed binaries and large files — and because history is permanent, deleting the file later doesn't shrink the repo. That's what LFS and `filter-repo` address.

**9.10 — Why can committing large binaries bloat a repo even after the file is deleted later**

New objects are written individually ("loose"). `git gc` packs them into packfiles with delta compression and prunes unreachable objects past the reflog expiry. Runs automatically on a threshold. `git count-objects -vH` shows the breakdown. Repos bloat from committed binaries and large files — and because history is permanent, deleting the file later doesn't shrink the repo. That's what LFS and `filter-repo` address.

**9.11 — How would you use Git worktrees to work on two branches at once**

```bash
git worktree add ../hotfix main
git worktree list
git worktree remove ../hotfix
```

Multiple working directories from one repository, each on a different branch, sharing the object database. Much better than stashing when you need to jump to a hotfix mid-feature — no stash, no rebuild of dependencies, both checkouts remain intact. The same branch can't be checked out in two worktrees at once.

**9.12 — Why are worktrees often better than stashing when switching to an urgent hotfix**

```bash
git worktree add ../hotfix main
git worktree list
git worktree remove ../hotfix
```

Multiple working directories from one repository, each on a different branch, sharing the object database. Much better than stashing when you need to jump to a hotfix mid-feature — no stash, no rebuild of dependencies, both checkouts remain intact. The same branch can't be checked out in two worktrees at once.


## 10. Advanced / situational

**10.1 — How would you cherry-pick one commit or a range of commits**

```bash
git cherry-pick <sha>
git cherry-pick <sha1>^..<sha2>     # a range
git cherry-pick -n <sha>            # apply without committing
```

Applies a commit's *changes* as a new commit with a new SHA. Legitimate for backporting a fix to a release branch. Overused as a substitute for proper merging, which leads to duplicated commits and confusing history — if you're cherry-picking regularly between the same two branches, the branching strategy is wrong.

**10.2 — When is cherry-pick a good fit, and when does regular cherry-picking suggest a bad branching strategy**

```bash
git cherry-pick <sha>
git cherry-pick <sha1>^..<sha2>     # a range
git cherry-pick -n <sha>            # apply without committing
```

Applies a commit's *changes* as a new commit with a new SHA. Legitimate for backporting a fix to a release branch. Overused as a substitute for proper merging, which leads to duplicated commits and confusing history — if you're cherry-picking regularly between the same two branches, the branching strategy is wrong.

**10.3 — How would you resolve a cherry-pick conflict and continue**

Resolve, `git add`, `git cherry-pick --continue`. Abort with `--abort`. Conflicts here usually signal the target branch has diverged enough that the commit doesn't apply cleanly — at that point, consider whether a proper merge or a fresh fix for that branch is more honest than forcing it through.

**10.4 — When should you abort a cherry-pick instead of forcing the commit through**

Resolve, `git add`, `git cherry-pick --continue`. Abort with `--abort`. Conflicts here usually signal the target branch has diverged enough that the commit doesn't apply cleanly — at that point, consider whether a proper merge or a fresh fix for that branch is more honest than forcing it through.

**10.5 — How would you add, clone, and update Git submodules**

```bash
git submodule add <url> path
git clone --recurse-submodules <url>
git submodule update --init --recursive
```

A submodule pins a specific commit of another repo. The pain: clones don't include them by default (people get empty directories), updates are a two-step commit dance, detached HEAD inside the submodule is the default state, and branch switching doesn't update submodule contents automatically. They work, but they demand discipline the whole team has to share.

**10.6 — Why are Git submodules painful for teams, and what discipline do they require**

```bash
git submodule add <url> path
git clone --recurse-submodules <url>
git submodule update --init --recursive
```

A submodule pins a specific commit of another repo. The pain: clones don't include them by default (people get empty directories), updates are a two-step commit dance, detached HEAD inside the submodule is the default state, and branch switching doesn't update submodule contents automatically. They work, but they demand discipline the whole team has to share.

**10.7 — How would you use Git subtree as an alternative to submodules**

```bash
git subtree add --prefix=lib/thing <url> main --squash
git subtree pull --prefix=lib/thing <url> main --squash
```

Vendors the other repo's content directly into yours. Better than submodules when consumers shouldn't have to know: a plain clone just works, no extra commands, no detached HEAD. Worse when you frequently push changes back upstream, and it inflates repo size. Rule of thumb: subtree for consuming, submodule for tight bidirectional development.

**10.8 — When is subtree better than submodules, and what cost does it introduce**

```bash
git subtree add --prefix=lib/thing <url> main --squash
git subtree pull --prefix=lib/thing <url> main --squash
```

Vendors the other repo's content directly into yours. Better than submodules when consumers shouldn't have to know: a plain clone just works, no extra commands, no detached HEAD. Worse when you frequently push changes back upstream, and it inflates repo size. Rule of thumb: subtree for consuming, submodule for tight bidirectional development.

**10.9 — How would you write a client-side Git hook such as `pre-commit` or `commit-msg`**

Scripts in `.git/hooks/`, executable, named for the event. `pre-commit` (lint, format, block secrets — exit non-zero to abort), `commit-msg` (validate message format), `pre-push` (run tests). They're local and not committed, so they can't be relied on for enforcement — and `--no-verify` skips them.

**10.10 — Why can client-side hooks help developers but not fully enforce policy**

Scripts in `.git/hooks/`, executable, named for the event. `pre-commit` (lint, format, block secrets — exit non-zero to abort), `commit-msg` (validate message format), `pre-push` (run tests). They're local and not committed, so they can't be relied on for enforcement — and `--no-verify` skips them.

**10.11 — How would you set up the pre-commit framework across a team**

`.pre-commit-config.yaml` in the repo defines hooks and versions; each developer runs `pre-commit install` once. Solves the distribution problem that raw `.git/hooks` has. Still bypassable with `--no-verify`, so the same checks must also run in CI — hooks are a fast-feedback convenience, not a control.

**10.12 — Why should the same checks run in CI even if developers use pre-commit locally**

`.pre-commit-config.yaml` in the repo defines hooks and versions; each developer runs `pre-commit install` once. Solves the distribution problem that raw `.git/hooks` has. Still bypassable with `--no-verify`, so the same checks must also run in CI — hooks are a fast-feedback convenience, not a control.

**10.13 — How would you explain what server-side hooks can enforce that client-side hooks cannot**

Run on the remote, so they can't be bypassed by the client. `pre-receive` can reject a push outright — enforce commit signing, message format, file size limits, or block direct pushes to main. That's the enforcement a client-side hook can never provide. On managed platforms you don't get raw server hooks; the equivalents are branch protection rules, required status checks, and push rulesets.

**10.14 — How do branch protection rules and required checks replace raw server hooks on hosted Git platforms**

Run on the remote, so they can't be bypassed by the client. `pre-receive` can reject a push outright — enforce commit signing, message format, file size limits, or block direct pushes to main. That's the enforcement a client-side hook can never provide. On managed platforms you don't get raw server hooks; the equivalents are branch protection rules, required status checks, and push rulesets.

**10.15 — How would you enforce conventional commits and generate a changelog from them**

Format: `type(scope): description` — `feat`, `fix`, `chore`, `docs`, `refactor`, with `BREAKING CHANGE:` in the footer. Enforce with commitlint in a `commit-msg` hook plus a CI check. Tools like semantic-release then derive the version bump (feat → minor, fix → patch, breaking → major) and generate the changelog automatically. The value is machine-readable history; the cost is friction, so it's worth it mainly where you publish versioned artifacts.

**10.16 — When is conventional commit discipline worth the extra friction**

Format: `type(scope): description` — `feat`, `fix`, `chore`, `docs`, `refactor`, with `BREAKING CHANGE:` in the footer. Enforce with commitlint in a `commit-msg` hook plus a CI check. Tools like semantic-release then derive the version bump (feat → minor, fix → patch, breaking → major) and generate the changelog automatically. The value is machine-readable history; the cost is friction, so it's worth it mainly where you publish versioned artifacts.

**10.17 — How would you use `git filter-repo` for history rewriting**

`git filter-branch` is officially discouraged: extremely slow, and its default behaviour is subtly unsafe in ways that produce corrupted results. `git-filter-repo` is the recommended replacement — orders of magnitude faster, safer defaults, and it forces a fresh clone so you can't half-rewrite a repo in place. Use it for removing files, purging secrets, splitting a repo, or rewriting author details.

**10.18 — Why is `git filter-repo` preferred over `git filter-branch`**

`git filter-branch` is officially discouraged: extremely slow, and its default behaviour is subtly unsafe in ways that produce corrupted results. `git-filter-repo` is the recommended replacement — orders of magnitude faster, safer defaults, and it forces a fresh clone so you can't half-rewrite a repo in place. Use it for removing files, purging secrets, splitting a repo, or rewriting author details.

**10.19 — How would you explain how Git stores history efficiently with objects, packfiles, and deltas**

Content-addressed storage means identical content is stored once regardless of how many commits or branches reference it. Objects start loose, then `gc` packs them into packfiles using delta compression — storing similar objects as deltas against each other, chosen heuristically by size and name similarity rather than by commit order. Packfiles are further zlib-compressed. This is why a repo with long history can be surprisingly small, and why a few committed binaries (which don't delta well) can make it surprisingly large.

**10.20 — Why can Git history stay small for text changes but grow quickly with binary files**

Content-addressed storage means identical content is stored once regardless of how many commits or branches reference it. Objects start loose, then `gc` packs them into packfiles using delta compression — storing similar objects as deltas against each other, chosen heuristically by size and name similarity rather than by commit order. Packfiles are further zlib-compressed. This is why a repo with long history can be surprisingly small, and why a few committed binaries (which don't delta well) can make it surprisingly large.
