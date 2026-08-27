# Troubleshooting & Incident Response — Answer Key

Companion to Domain 5 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

This domain differs from the tool domains: almost nothing here has a command as its answer. These are judgement items, and in an interview they're assessed on whether you can describe a *method* and back it with a real example. Where possible, the answer names the failure mode that makes the skill matter — that's usually the part that reads as experience rather than reading.

---

## T1. Diagnostic method

**T1.1 — State the problem precisely before touching anything**

The instinct under pressure is to start fixing. Thirty seconds of definition saves an hour of wrong-direction work. Establish:

- **What is the actual symptom?** "The site is down" is a report, not a symptom. Is it errors, latency, or a blank page? What status code? Which endpoint?
- **Who is affected?** All users, one region, one customer, internal only?
- **When did it start?** Precisely, from data, not from when someone noticed.
- **What changed?** Deploys, config, flags, certificates, infrastructure, upstream dependencies.

A good answer also names the trap: the reported symptom is often downstream of the real one. "Checkout is failing" may be a database connection pool problem that also affects five other things nobody has reported yet.

**T1.2 — Hypothesis, and the cheapest disproving test**

Form a specific hypothesis ("the new deploy exhausted the connection pool"), then pick the test that would most cheaply *disprove* it. Disproof is the right framing because confirming evidence is easy to find for almost any theory — you'll always find something that looks consistent.

Cheap tests first: a metric you can read in ten seconds beats a code review. If the hypothesis is "the deploy caused it," the cheapest test is comparing the incident start time to the deploy timestamp — one look, and it either rules the theory in or out.

**T1.3 — Bisect the problem space**

Rather than checking components in whatever order they come to mind, cut the space in half. Is the failure before or after the load balancer? Inside or outside the VPC? Present in staging or only production? Each answer eliminates half the surface.

Concrete version: test by IP to eliminate DNS, test from inside the subnet to eliminate network controls, test the backend directly to eliminate the proxy. Two or three well-chosen tests localise most faults. The alternative — checking things sequentially — is why some incidents take four hours and others take fifteen minutes.

**T1.4 — Correlation vs causation when a deploy coincides**

A deploy immediately before an incident is strong evidence and usually the right first suspect — most incidents are change-induced. But it isn't proof, and treating it as proof leads to rolling back, seeing no improvement, and having lost twenty minutes.

Discriminating questions: does the timing match *precisely*, or was there a gap? Did the deploy touch anything on the failing path? Did anything else happen at that time (a scheduled job, a traffic change, an upstream deploy, a certificate expiry)? Has this deploy pattern run safely many times before?

The practical resolution: rollback is often still the right *action* even without certainty, because it's cheap and reversible. But mitigate and keep investigating — don't declare the cause resolved just because the symptom stopped.

**T1.5 — Recognising you're pattern-matching to a past incident**

Experience is fast because it pattern-matches, and that's usually an advantage — until the current incident superficially resembles a previous one and you spend an hour treating the wrong cause.

The check is cheap: after forming the hypothesis from memory, ask "what evidence would this incident produce that the previous one also produced, and is it actually present?" If you're recognising the *shape* but haven't verified a single specific signal, you're guessing with confidence, which is worse than guessing.

**T1.6 — Change one thing at a time, and when to break the rule**

Changing several things at once means that if the symptom clears, you don't know what fixed it — so you can't prevent it recurring and you may have left something harmful in place.

When to break it: when impact is severe and ongoing, restoring service beats understanding. In a full outage, applying three plausible mitigations simultaneously is correct. The discipline is to *know* you've broken the rule and to record what you changed, so the postmortem can untangle it afterwards. State that explicitly — "we did three things at once because the site was down; we'll determine which mattered in the review."

**T1.7 — When to stop debugging and mitigate**

The trigger is impact, not curiosity. If users are affected and a mitigation exists — rollback, failover, scale up, disable a feature, shed load — take it *now* and investigate afterwards with the pressure off.

The failure mode this prevents is the engineer who is close to understanding the root cause while the outage continues. Understanding is not the objective during an incident; restoring service is. Root cause analysis is what the postmortem is for, and you'll do it better without a live outage.

**T1.8 — Working with incomplete information, and stating confidence**

You will never have complete information during an incident. The skill is acting on partial evidence while being explicit about how partial it is: "I'm fairly confident it's the database connection pool — the pool metrics saturate at exactly the incident start. I have not confirmed why the pool filled."

Separating those two clauses is what makes the statement useful to everyone else. Overstating confidence sends people down a wrong path with conviction; refusing to commit at all leaves the team without direction. Calibration is the skill.

**T1.9 — Recognising you're stuck, and handing off**

Signals: you've been on the same hypothesis for 30+ minutes with no new evidence, you're re-reading the same logs, or you're trying things without a hypothesis at all. Tunnel vision is real and you cannot detect it from the inside reliably — which is why the time-box should be agreed in advance.

Handing off is not failure. A fresh person asks the obvious question you stopped asking an hour ago. In an interview, being willing to say "I'd escalate and I'd rather do that early than late" reads as senior; the candidate who describes heroic solo persistence reads as mid-level.

**T1.10 — Keeping a running log**

Timestamped notes of what you tried, what you observed, and what you changed. This does four jobs: it enables handover, it prevents repeating tests, it produces the postmortem timeline for free, and it forces you to articulate hypotheses rather than flailing.

In practice, a dedicated incident channel serves as the log if people narrate there. The habit worth having is writing observations *and* the reasoning, not just actions — "restarted pod X" is much less useful in review than "restarted pod X because it was the only one showing elevated GC pauses."

---

## T2. Evidence gathering

**T2.1 — Establish a timeline**

Get the precise start time from data, not from the first report — reports lag reality, often by a lot. Metric inflection points, first error log entry, first failed health check.

Then overlay everything that happened around that time: deploys, config changes, scaling events, scheduled jobs, upstream provider status, certificate expiries, traffic changes. Most incidents resolve at this step, because something in that overlay lines up.

**T2.2 — Correlating across systems**

Requires a shared key. In order of usefulness: a trace or request ID propagated across services; a correlation ID in logs; failing that, timestamps.

Timestamps require care: confirm clock sync and normalise everything to UTC. Correlating logs across hosts with drifted clocks produces confidently wrong conclusions about causal order. Ordering matters most — the *first* thing to fail is usually nearer the cause than the loudest thing.

**T2.3 — Last known good, and what changed since**

Find the most recent point the system demonstrably worked, then enumerate every change since. "Changes" is broader than deploys: infrastructure, configuration, feature flags, dependency versions, data volume, traffic patterns, and things that changed *by themselves* like a certificate expiring or a disk filling.

The uncomfortable case is when nothing changed — which usually means something crossed a threshold gradually (disk, memory, connection count, a counter wrapping) or an external dependency changed.

**T2.4 — First-class suspects**

Check these early, every time, because they're cheap to check and disproportionately often the cause:

- **Deploys** — most incidents are change-induced.
- **Config and feature flag changes** — often not tracked as deploys, so invisible in a deploy log.
- **Certificate expiry** — dramatic, total, and entirely predictable.
- **Credential and secret rotation** — expiring or newly rotated credentials.
- **Scheduled jobs** — a nightly batch that just got bigger.
- **Capacity thresholds** — disk, connections, quotas, IP exhaustion.
- **Upstream provider status** — check the status page before assuming it's you.

**T2.5 — Determining scope**

Scope is one of the most diagnostic pieces of information available, because each answer implicates a different layer:

- **One user** → data-specific, permissions, their client.
- **One region or AZ** → infrastructure, not code.
- **One instance** → that host, that pod.
- **One endpoint** → that code path, that dependency.
- **Everyone, everywhere** → shared dependency, global config, DNS, certificate.
- **A consistent percentage** → one unhealthy backend out of N (N9.7).

Establish scope before diving in — it often eliminates most of the search space in one question.

**T2.6 — Ours or upstream, with evidence**

Check the provider's status page, but don't stop there — status pages lag and under-report. Better evidence: does the failure affect only calls to that provider? Do you see connection failures or timeouts at your egress rather than errors in your own logs? Can you reproduce the failure from a completely independent network path? Are other customers reporting it?

Naming this matters because the response differs entirely: if it's upstream, your job becomes degrading gracefully and communicating, not debugging your own code.

**T2.7 — Capture evidence before destroying it**

Restarting fixes things and destroys the evidence for why they broke. Before you restart, if impact allows: capture logs, a thread dump or heap dump, current metrics, `ps`/`top` output, open file descriptors, network state.

The tension is real — during a severe outage, restoring service wins and you accept the loss. But in a degraded state where you have a few minutes, thirty seconds of capture is the difference between a postmortem with a root cause and one that says "we restarted it and it went away." Practically: leave one affected instance running and out of the pool if you can, then restart the rest.

**T2.8 — Reproduce, or explain why you can't**

A reliable reproduction turns an incident into a bug, which is a vastly easier problem. Attempt it in a lower environment, or against a single instance out of the pool.

When you can't, that itself is diagnostic. Not reproducible in staging usually means the difference *is* the cause: data volume, real traffic patterns, concurrency, production-only config, scale, or a specific data record. Saying "I couldn't reproduce it, and the fact that staging has 1/1000th the data volume is my leading hypothesis" is a much stronger answer than "it's intermittent."

---

## T3. Common failure patterns

**T3.1 — Resource exhaustion**

The general shape: something accumulates until it hits a ceiling, then everything fails at once. The specific resources worth having on a mental checklist:

- **Disk** — logs, temp files, deleted-but-open files (L6.2), inodes.
- **Memory** — leaks, unbounded caches, OOM kills.
- **File descriptors** — leaked sockets and file handles; CLOSE_WAIT accumulation (N5.4).
- **Connection pools** — database, HTTP client. Autoscaling multiplies this (DB8.4).
- **Ephemeral ports** — many short-lived outbound connections (N5.6).
- **Thread pools** — blocked threads with no queue limit.
- **Cloud quotas** — API rate limits, IP addresses, instances.

Signature: gradual degradation then a cliff, and often a time-based pattern (fails every N days as something fills).

**T3.2 — Cascading failure, retries, and thundering herds**

One component slows or fails. Callers retry. Retries multiply load on the struggling component, making it slower. More callers time out and retry. The system saturates itself, and the failure spreads upstream to services that were healthy.

The amplification is the key insight: three retries turns one failure into four requests. Under partial failure, that's a 4× load increase precisely when there's least capacity. Recovery is also hampered — the moment the service comes back, the accumulated retry backlog knocks it over again (the thundering herd).

Countermeasures: exponential backoff **with jitter**, retry budgets that cap total retry load, circuit breakers that stop calling a failing dependency, and load shedding.

**T3.3 — Slow dependency causing upstream queue buildup**

A downstream call that used to take 20ms starts taking 2s. Upstream request handlers block waiting. Threads or connections are held longer, the pool exhausts, queues build, and the upstream service now fails *even for requests that don't touch the slow dependency*.

This is why a slow dependency is often worse than a failed one — a fast failure releases the resource immediately, a slow one holds it. It's the argument for aggressive timeouts, bulkheads that isolate dependency-specific resources, and circuit breakers that fail fast once a dependency is known bad.

**T3.4 — DNS and certificate expiry**

Both are unglamorous, both cause total outages, both keep happening. Certificate expiry is entirely predictable and therefore entirely preventable, which is why it's embarrassing — and the usual root cause isn't forgetfulness but ownership: nobody knew that certificate existed (S3.8, S3.12).

DNS: TTL and caching mean changes propagate unevenly (N4.6), and application-level caching can hold a stale answer indefinitely (N4.9). Both belong on the first-suspects list (T2.4) because they're cheap to check and dramatic when wrong.

**T3.5 — Partial failure, one bad node**

A consistent fraction of requests fail — roughly 1/N — while aggregate metrics look acceptable and retries usually succeed. Users report flakiness; dashboards show a healthy p50.

Isolation: look at per-instance metrics rather than service aggregates, check per-target health and response codes on the load balancer, and see whether failures correlate with a single instance ID in logs. The general lesson is that averages hide partial failure, which is why per-instance visibility matters.

**T3.6 — Config or secret change, not code**

Config changes frequently bypass the deploy pipeline — changed in a console, a parameter store, a feature flag UI — so they don't appear in the deploy log everyone checks first. A rotated credential that wasn't propagated everywhere produces failures that look like an application bug.

The lesson for investigation: "no deploys today" does not mean "nothing changed." Ask specifically about config, flags, secrets, and infrastructure. The lesson for prevention: config changes should be versioned and audited like code.

**T3.7 — Capacity and quota limits**

Distinct from resource exhaustion because the limit is external and often invisible until hit: cloud API rate limits, service quotas, IP address exhaustion in a subnet, Lambda concurrency, connection limits on a managed database.

Signature is characteristic — throttling errors, or a scaling event that simply doesn't happen. It's insidious because the system behaves fine until the exact moment it needs to grow, which is usually during a traffic spike. Worth monitoring quota utilisation proactively rather than discovering it during an incident (A11.9).

**T3.8 — Clock, timezone, and leap-related problems**

Clock drift breaks certificate validation, token expiry, TOTP, distributed consensus, and log correlation. Timezone bugs produce failures at predictable hours — a job that runs at the wrong time after a DST transition, or a date comparison that's off by hours near midnight.

Also in this family: leap seconds and leap years, month-boundary and year-boundary arithmetic, and epoch-adjacent rollovers. The tell is periodicity — a failure that recurs at a specific time or date rather than under load.

**T3.9 — "Works in staging"**

The differences that actually cause it, in rough order of frequency:

- **Data volume** — a query that's fine on 10k rows and fatal on 10M, or a missing index that only matters at scale.
- **Concurrency** — race conditions and lock contention that need real parallel traffic to surface.
- **Config** — different endpoints, timeouts, pool sizes, feature flags.
- **Permissions** — different IAM roles, different network policy.
- **Scale and topology** — one instance vs fifty, single AZ vs multi.
- **Real traffic shape** — bursty, uneven, with unexpected inputs.

The productive framing: staging passing is weak evidence, and the specific difference is usually the diagnosis. This is also the argument for shifting confidence to production techniques — canaries, flags, observability — rather than trying to make staging perfectly faithful (C5.8).

**T3.10 — Intermittent failure with no reliable reproduction**

Approach: stop trying to reproduce and start characterising. Gather every instance of the failure and look for what they share — same instance, same AZ, same customer, same time of day, same request shape, same code path, same data. Intermittent failures almost always have a hidden pattern; "random" usually means "we haven't found the correlate yet."

Common underlying causes: one bad node (T3.5), a race condition under specific concurrency, a resource that fills and gets cleared, DNS or caching returning different answers, or a specific data record that trips a code path.

If characterisation fails, add instrumentation and wait. Increasing observability on the failing path is a legitimate action, not an admission of defeat.

---

## T4. Incident response

**T4.1 — Classifying severity consistently**

Severity should be defined by **impact**, not by how alarming it feels or how hard it is to fix. A usable scale is anchored on user-visible consequence:

- **Sev1** — total outage or critical function unavailable, or data loss/security breach. All hands, immediate.
- **Sev2** — major degradation or a significant subset of users affected. Urgent, business hours or page.
- **Sev3** — minor degradation, workaround available, limited scope.

The reason consistency matters: severity drives paging, communication, and escalation. Under-classifying delays the right people; over-classifying causes fatigue and makes people ignore the next one. Justify the call in impact terms — "checkout is failing for all users, that's revenue-affecting, Sev1" — not in terms of technical severity.

**T4.2 — Assessing blast radius early**

Answer three questions quickly: **who** is affected (all users, a segment, internal only), **how badly** (broken, degraded, slow), and **is it growing**. That last one changes urgency completely — a contained failure and a spreading one warrant different responses even at the same current impact.

Also assess whether there's data loss or corruption risk, because that changes the calculus: with data at stake, stopping the bleeding takes priority over restoring availability, and you may deliberately keep the system down.

**T4.3 — Incident command**

For anything beyond a small incident, separate the roles:

- **Incident commander** — coordinates, decides, tracks state. Explicitly *not* debugging.
- **Operations / responders** — the people actually investigating and fixing.
- **Communications** — stakeholder and customer updates.
- **Scribe** — the timeline.

The single most important property is **one person deciding**. The failure mode without it is several engineers making changes simultaneously without knowing about each other, so nobody can tell what helped and things get worse. The commander doesn't need to be the most technical person — they need to be the one holding the overall picture.

**T4.4 — Mitigate-first vs diagnose-first**

Default is **mitigate first** whenever a mitigation exists and users are affected. Rollback, failover, scale, disable the feature, shed load. Understanding can wait; the outage can't.

Diagnose first only when: no mitigation is known, mitigation is risky or irreversible, or acting blindly could make it worse (particularly with data corruption, where a hasty restore can destroy the evidence and the data). Articulating *why* you chose one is the assessed part — "I'd roll back immediately because it's cheap and reversible, and investigate after" is a complete answer.

**T4.5 — Rollback vs fix-forward**

**Rollback** when: the change is recent and identified, the rollback path is tested, and there's no forward-migration barrier. It's the default because it's the fastest route to a known-good state.

**Fix-forward** when: rollback is impossible (database migration already applied, data already written in a new format), the bug predates the deploy, rollback would itself cause harm, or the fix is genuinely trivial and verified.

The risk of each: rollback risks losing an unrelated fix in the same release and can be blocked by irreversible changes; fix-forward risks deploying an untested change under pressure, which is how a Sev2 becomes a Sev1. State the risk you're accepting.

**T4.6 — Executing a rollback, having verified it's possible**

The clause matters more than the mechanics. Teams routinely assume rollback works and discover during an incident that it doesn't — because a migration ran, because the artifact was garbage-collected, because the previous version isn't compatible with the current schema or config.

So: verify the rollback target exists and is deployable, confirm no irreversible change has occurred since, then execute and *verify the symptom actually cleared* rather than assuming. If the symptom persists after rollback, the deploy wasn't the cause and you've learned something valuable.

**T4.7 — Mitigation levers other than rollback**

- **Feature flag / kill switch** — instant, targeted, no deploy. The fastest lever you can have.
- **Traffic shifting** — move away from a bad region, AZ, or version.
- **Scaling** — more capacity, if the problem is load.
- **Load shedding / rate limiting** — protect the core function by rejecting some traffic deliberately.
- **Failover** — to a replica or secondary region.
- **Disabling a non-critical dependency** — degrade gracefully.
- **Restarting** — crude, effective for leaks and stuck state, and destroys evidence (T2.7).

Having several levers is itself a reliability property. The team whose only lever is "deploy a fix" has a much longer time to restore.

**T4.8 — When to declare an incident**

Bias toward declaring. The cost of declaring unnecessarily is a bit of noise; the cost of *not* declaring is that the right people aren't involved, communication doesn't happen, customers find out first, and there's no timeline for the review.

Declare when: users are affected, you're not confident it's contained, it needs more than one person, or it'll last more than a few minutes. The instinct to quietly fix it first is understandable and usually wrong — quiet fixes that turn out to be bigger than expected are how incidents become prolonged.

**T4.9 — When to wake someone up, and being willing to**

Wake someone when their expertise materially shortens the outage, when the decision is above your authority, or when you're stuck and impact is ongoing (T1.9). Waking someone at 3am for a Sev1 is what on-call is for.

The failure mode is hesitation out of politeness — an hour of solo struggling because you didn't want to disturb anyone. Reframe it: the person being woken would rather be woken than discover in the morning that the outage ran for six hours. Being explicit that you'd escalate early is a maturity signal; the answer that emphasises handling it alone is not.

**T4.10 — Managing a long incident**

Fatigue degrades judgement quickly, and long incidents are where bad decisions get made. Practices:

- **Rotate people out** — including the commander. Plan handovers before people are exhausted, not after.
- **Explicit handover** (T5.6) — current state, hypotheses tried, what's in flight.
- **Force breaks** — the commander should send people away from screens.
- **Watch for tunnel vision** — periodically restate the problem and ask whether the current line of investigation is still justified.
- **Keep the log current** — it's the only thing that survives a shift change intact.

**T4.11 — Declaring resolved, with evidence**

Resolution means the symptom is gone *and you can demonstrate it*: metrics returned to baseline, error rates normal, a synthetic or manual transaction succeeding, affected users confirming. Not "the alert cleared" — alerts clear for reasons other than the problem being fixed.

Also state whether the fix is permanent or a mitigation. "Resolved with a temporary mitigation; the underlying cause is still open and tracked as X" is honest and prevents the follow-up work evaporating. Watch for a period after declaring, because premature resolution followed by recurrence damages trust more than a slightly delayed all-clear.

---

## T5. Communication during an incident

**T5.1 — A status update that works**

Three elements, every time:

1. **Impact** — what users are experiencing, in their terms. "Customers can't complete checkout," not "the order service is returning 503s."
2. **Current status** — what's known, what's being done, without technical detail nobody needs.
3. **Next update time** — a specific commitment, e.g. "next update in 30 minutes."

The third is the one people omit and the one that matters most, because it stops everyone asking for updates and lets stakeholders plan. Keep it short. Avoid speculation about cause in external updates — early theories are frequently wrong and get quoted back.

**T5.2 — Communicating to non-technical stakeholders**

Lead with business impact and expected duration, not architecture. They need to make decisions — whether to notify customers, whether to hold a launch, whether to escalate — and they need impact and time to do that.

Neither minimise ("just a small glitch") nor catastrophise. If you don't know the duration, say so plainly and give the next update time instead of inventing an estimate. Inventing an ETA you then miss costs more credibility than admitting uncertainty.

**T5.3 — Updating on a cadence even with nothing new**

"No update yet, still investigating, next update in 30 minutes" is a valuable message. Silence gets interpreted as things being worse than they are, or as nobody working on it, and it generates a stream of interruptions to the people trying to fix the problem.

Set the cadence by severity — every 15–30 minutes for a Sev1 — and hold it. The predictability is the point.

**T5.4 — Separating what you know from what you suspect**

Say it explicitly: "Confirmed: error rate rose at 14:32 and correlates with the deploy at 14:30. Suspected: the new query is causing lock contention. Unconfirmed: whether this affects the reporting service too."

Two reasons this matters. It stops speculation hardening into accepted fact as it's repeated — a theory mentioned once at 14:40 becomes "the cause" by 15:10 if nobody labelled it. And it lets others correct you, because they know which parts are open.

This is a small verbal habit that reads as strongly senior, and it's worth practising.

**T5.5 — Managing stakeholder pressure**

Pressure during an incident is legitimate — they're accountable too — but it can push toward bad decisions: skipping verification, deploying an untested fix, declaring resolved early.

Handling it: acknowledge the urgency, give a concrete update, and be clear about what you're not willing to skip and why. "I understand the pressure. Deploying this fix without testing risks making it worse; here's what I'm doing instead and when I'll update you." Route pressure through the incident commander so responders aren't fielding it directly — that's a large part of why the role exists.

**T5.6 — A clean handover**

Cover, in order:

- **Current impact and severity** — what's broken now.
- **Timeline so far** — key events.
- **Hypotheses tested and ruled out** — the most valuable part, and the most often omitted. Without it the next person repeats your work.
- **Current leading theory** and what evidence supports it.
- **Actions in flight** — anything running, anything changed and not reverted.
- **Who else is involved** and what they're doing.
- **Open decisions** awaiting someone.

Do it verbally *and* in writing. Confirm the incoming person has picked it up explicitly — an ambiguous handover where both parties think the other has it is a genuine failure mode.

**T5.7 — Communicating customer impact honestly, including when you don't know**

Say what you know, say what you don't, and commit to following up. "We've confirmed checkout failures between 14:30 and 15:10. We're still determining whether any orders were partially processed and will confirm within two hours."

The temptation is to wait until you have the full picture, but silence during that gap is worse — customers form their own conclusions. For anything involving data loss or a security implication, involve legal and comms early rather than making the call alone; there are usually regulatory notification requirements with clocks attached.

---

## T6. Post-incident

**T6.1 — Writing a postmortem**

Structure:

- **Summary** — what happened, in a few sentences.
- **Impact** — quantified: duration, users affected, requests failed, revenue, SLO budget consumed.
- **Timeline** — from first change or first signal through resolution, with timestamps.
- **Contributing factors** — plural, deliberately (T6.3).
- **What went well** — genuinely useful; detection speed, a mitigation that worked, a runbook that helped.
- **What made it harder** — missing observability, unclear ownership, a broken runbook.
- **Action items** — specific, owned, prioritised (T6.5).

Write it while it's fresh. The audience is people who weren't there, so explain context rather than assuming it.

**T6.2 — Blameless, and meaning it**

Blameless means the analysis targets the system and conditions, not the individual. If an engineer ran a destructive command, the questions are: why was that command available, why was there no confirmation, why did the tooling make the dangerous path easy, why did nothing catch it before impact.

"Meaning it" is the operative phrase. Teams that say blameless but assign implicit fault get the worst outcome: people stop volunteering information, so postmortems become inaccurate, and you lose the data you needed. The test is whether people report their own near-misses voluntarily. Note it doesn't mean no accountability — it means accountability for *fixing the system*, not for having been the person at the keyboard.

**T6.3 — Getting past the first plausible cause**

The first plausible cause is where analysis stops if nobody pushes. "The deploy broke it" is a trigger, not an explanation.

Keep going: why did the change have that effect? Why didn't tests catch it? Why didn't the canary catch it? Why did detection take 20 minutes? Why did the runbook not exist? Each answer is a separate improvement opportunity, and most incidents have several contributing conditions rather than one cause — which is why "root cause" singular is a slightly misleading term.

**T6.4 — Trigger vs latent cause**

The **trigger** is the proximate event — the deploy, the traffic spike, the disk filling. The **latent cause** is the condition that made the trigger harmful — no connection pool limit, no autoscaling headroom, no alerting on disk, an untested rollback path.

Fixing only the trigger prevents this specific recurrence and nothing else. Fixing the latent cause prevents a whole class. The latent conditions are usually more valuable and less comfortable, because they're often "we knew about this and deprioritised it."

**T6.5 — Actions that are specific, owned, prioritised**

Bad: "improve monitoring." Good: "add an alert on database connection pool utilisation above 80%, owned by X, by date Y, priority P1."

Each action needs a named owner (a person, not a team), a due date, a priority relative to other work, and a clear definition of done. Actions that are vague, unowned, or unprioritised do not get done — and a postmortem whose actions evaporate is a meeting that produced nothing.

Also worth distinguishing: actions that *prevent* recurrence, actions that *detect* faster, and actions that *mitigate* faster. All three are valid; a list containing only prevention is usually unrealistic.

**T6.6 — Pushing back on "add more monitoring"**

It's the default action item because it feels productive and costs nothing to propose. It's often the wrong one.

Questions to ask: would this alert have actually fired before impact? Would it have told anyone what to do? Is the real problem that we lacked the signal, or that we had it and it was buried in noise? Would fixing the underlying fragility be better than watching it more closely?

Sometimes more monitoring is genuinely right. But an incident that produces only monitoring action items usually means the harder work was avoided — and every added alert has an ongoing cost in noise and fatigue (T7.4).

**T6.7 — Tracking actions to completion**

Action items decay: urgency fades as the incident recedes, and feature work reasserts itself. Practices that work: put actions in the same tracker as normal work rather than a separate document nobody opens, review open incident actions at a regular cadence, and give high-priority actions explicit sprint capacity.

Notice when items are quietly dropped and treat that as a signal in itself — either the action wasn't actually important (fine, close it explicitly) or the team lacks the capacity to do reliability work (a conversation to have with management, backed by the incident record).

**T6.8 — Spotting a systemic pattern across incidents**

Individual postmortems miss patterns; three incidents in a quarter all caused by the same fragile subsystem, or all delayed by the same missing observability, is information no single review contains.

Do periodic aggregate analysis: group incidents by contributing factor, affected system, and detection gap. When a pattern emerges, escalate it as its own piece of work rather than another action item — the appropriate response is usually a project, not a task. This is also the most effective way to make the business case for platform and reliability investment, because it converts anecdote into evidence.

---

## T7. Prevention & reliability

**T7.1 — SLIs and SLOs that reflect user experience**

An **SLI** is a measurement of service behaviour; an **SLO** is the target for it. The discipline is choosing indicators that track what users actually experience, not what's convenient to measure.

Good SLIs: successful request rate as seen by the client, latency at a percentile that reflects real experience, and end-to-end journey success. Poor SLIs: CPU utilisation, host uptime, internal queue depth — these are causes, not experiences, and a system can be 100% "up" while completely unusable.

Set the target from what users need and what the business will fund, not from what you currently achieve. And keep the number of SLOs small — a handful of meaningful ones beats forty that nobody watches.

**T7.2 — Error budgets and how they change decisions**

An error budget is the inverse of the SLO: 99.9% availability permits 0.1% failure. That allowance is a *budget to spend* on change and risk, not a failure to avoid.

The decision effect: budget remaining means you can deploy aggressively and take risks. Budget exhausted means you slow down — freeze non-essential releases and spend effort on reliability. That makes the launch-versus-stability argument a data question rather than an opinion clash, which is its real value. It also implies 100% is the wrong target: no budget means no ability to change anything.

**T7.3 — Alerting on symptoms rather than causes**

Alert on what users experience — error rate, latency, SLO burn — not on every possible cause. Reasons: cause-based alerts are numerous and mostly don't matter (high CPU with everything working fine is not an incident), and they can never be exhaustive, so the cause you didn't think of produces an outage with no alert.

Symptom alerts are few, always meaningful, and catch unknown failure modes. Cause-level signals still belong in dashboards for diagnosis — the distinction is between what *pages a human* and what's available when they look.

**T7.4 — Auditing and reducing alert noise**

Every alert has an ongoing cost: attention, sleep, and — most damagingly — desensitisation. A team that routinely ignores alerts will ignore the important one.

Audit method: for each alert, ask how often it fired last quarter, how often it required action, and what the responder did. Alerts that never fire may be broken; alerts that fire constantly and are always acknowledged without action should be deleted or converted to a dashboard. Track the ratio of actionable to total pages as a metric in its own right. Deleting alerts is real reliability work, though it rarely feels like it.

**T7.5 — A runbook someone can follow at 3am**

Assumptions to make: the reader is tired, not the author, and possibly unfamiliar with the system. So:

- Start with **how to confirm this is the right runbook** — the specific symptom.
- Give **exact commands**, copy-pasteable, with expected output.
- State **what to check before acting** and what each result means.
- Include **decision points** explicitly rather than assuming judgement.
- Say **when to escalate and to whom**.
- Link to the dashboard and the relevant logs directly.

Runbooks decay. Test them — during game days, or by having the newest team member follow one — and date them. A runbook with a stale command is worse than none, because it costs time and confidence at the worst moment.

**T7.6 — Graceful degradation, circuit breakers, bulkheads**

**Graceful degradation** — shed non-essential functionality to preserve the core. Recommendations fail, so serve the page without them rather than erroring.

**Circuit breaker** — after N failures to a dependency, stop calling it and fail fast for a cooldown, then test tentatively (half-open) before restoring. Prevents wasting resources on calls that will fail and gives the dependency room to recover (T3.2).

**Bulkhead** — isolate resources per dependency, so a slow one exhausts only its own pool rather than every thread in the service. Named after ship compartments: contain the flooding.

All three address the same underlying problem — that a partial failure shouldn't become a total one.

**T7.7 — Retry strategy**

Three components, all necessary:

- **Exponential backoff** — increasing delay so a struggling service isn't hammered.
- **Jitter** — randomisation, so clients that failed together don't retry together (T7.9/T7.10).
- **A retry budget or cap** — a limit on total retry load, so retries can't multiply into a self-inflicted DDoS.

Also: only retry idempotent operations (N6.8), and only retry errors that might succeed on a retry — retrying a 400 is pointless load. Retries at multiple layers multiply (3 at the client × 3 at the proxy = 9), which is a common and under-appreciated amplification.

**T7.8 — Timeouts as a design decision**

Every network call needs a timeout, and the default in most libraries is either infinite or far too long. Without one, a slow dependency holds your resources indefinitely and turns into T3.3.

Setting them: derive from the actual latency distribution — something like p99 plus headroom — not from a round number. They must be coherent across layers: an inner timeout longer than the outer one means the outer gives up while the inner still holds resources. And timeout budgets should shrink as you go deeper into a call chain, so the whole chain fails within the caller's limit.

**T7.9 — Game days and chaos experiments**

Deliberately inject failure to verify the system behaves as designed and, equally, that the *people* and processes work — that alerts fire, runbooks are correct, and responders know what to do.

Running one responsibly: form a hypothesis ("if we kill an AZ, traffic shifts within 60s with no user-visible errors"), start small and in a lower environment, define the blast radius and the abort condition, notify people, and have a rollback. The value is finding the gap before it finds you — and the most common finding isn't a technical failure but a process one: nobody knew who to call, or the runbook was wrong.

**T7.10 — A healthy on-call rotation**

Characteristics: enough people that the rotation is infrequent (a week every 6–8 is reasonable, weekly every 3 is not), a realistic page volume (a couple of actionable pages per shift, not per hour), compensation or time back, a clear escalation path, and handover between shifts.

What makes one unsustainable: too few people, too much noise (T7.4), no authority to fix the causes so the same page recurs, no follow-up time, and an expectation of heroism. The consequence is burnout and attrition, and the people who leave are typically the ones who knew the most.

The senior framing worth stating: on-call load is a *product* of system reliability and alert hygiene. If on-call is painful, that's a signal about the system, not about the people.

**T7.11 — Measuring whether reliability is improving**

Candidate measures, each with a caveat:

- **SLO attainment and error budget consumption** over time — the most direct.
- **Incident frequency by severity** — but beware improved reporting looking like more incidents.
- **MTTD and MTTR** — detection and restoration times; genuinely useful, though the mean hides distribution.
- **Change failure rate** — from DORA (C11.4).
- **Repeat incidents** — recurrence of the same cause is a strong negative signal.
- **Actionable page rate** — proxy for both system health and alert quality.

State the caveat too: every one of these can be gamed (classify fewer incidents, close them faster, weaken the SLO). The honest position is to use several, trend them over quarters rather than sprints, and pair them with qualitative signal from the people carrying the pager.
