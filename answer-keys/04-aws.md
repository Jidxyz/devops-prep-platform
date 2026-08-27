# AWS — Answer Key

Companion to Domain 4 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Two scoping notes carried over from the matrix:

- Networking *reasoning* lives in Domain 3. Where a topic is genuinely a networking concept wearing an AWS badge, the answer points there rather than repeating it — e.g. stateful vs stateless filtering is N10.1, peering vs Transit Gateway is N10.5.
- Tier markings are on section headings. **T3 (A15) gets one or two lines per item** — enough to place the service in a conversation, not enough to be interviewed on.

The recurring theme across the T1 sections is that AWS interviews at senior level rarely test whether you know a service exists. They test whether you know what it costs, what it breaks, and what it does under failure. The answers below lean heavily on that.

---

## A1. Account structure & identity — T1

**A1.1 — Multi-account strategy, and why prod/non-prod/security/logging separate**

The account is the only *hard* isolation boundary AWS gives you. Everything else — IAM policy, tags, VPCs — is a soft boundary enforced by configuration you can get wrong. That single fact drives the whole strategy:

- **Blast radius.** A compromised credential, a runaway Terraform apply, or a misapplied `Deny` is contained to one account. Within an account, an over-broad IAM policy reaches everything.
- **Quotas and limits.** Service quotas are largely per-account per-region. A non-prod account exhausting Lambda concurrency, ENIs, or EC2 vCPU quota must not be able to starve prod. This is the argument people forget, and it's the one that actually causes outages (A11.9).
- **Billing and attribution.** Account is the cleanest cost dimension there is — it works even when tagging discipline fails (A12.2).
- **Separation of duties.** The logging account exists so that an attacker with full admin in prod still cannot delete the evidence. That property only holds if prod has no write path to it (A1.16).
- **Different policy regimes.** Prod and sandbox need genuinely different guardrails — region restrictions, instance-type limits, who can assume admin. SCPs attach to OUs, so accounts are how you make policy differences expressible.

The honest tradeoff: multi-account is *more* operational work, not less. Cross-account networking, centralised logging, image and artefact sharing, and identity all become problems you have to solve deliberately. It only pays off if account creation and baselining are automated (A1.13) — a hand-built multi-account estate is worse than a well-run single account, because you get the complexity without the consistency.

**A1.2 — AWS Organizations: OUs, root, member accounts**

The org has a **management account** (formerly "master"/payer) at the top, a **root** container, **OUs** that nest (up to five levels deep), and **member accounts** that sit in exactly one OU or directly under root.

The parts that matter operationally:

- **Do not run workloads in the management account.** It holds billing, org control, and account creation. It's also the account where SCPs *don't apply* — so any workload there is ungoverned by design. Keep it near-empty: Organizations, billing, and the roles needed to manage them.
- **Consolidated billing** aggregates usage across the org, which is also how Savings Plans and RI benefits get shared org-wide (A12.5) — occasionally a surprise when an account "gets" a discount it didn't buy.
- **Trusted access / service-linked features**: enabling org-wide CloudTrail, Config, GuardDuty, Security Hub, RAM, and IPAM requires enabling trusted access for that service in the org, then usually delegating administration (A1.17).
- An account can only be moved between OUs, never between orgs directly — leaving an org and joining another is a separate, awkward process requiring the account to have standalone billing details.

**A1.3 — Writing an SCP, and how it differs from an IAM policy**

An SCP is a **guardrail, not a grant**. It defines the maximum set of permissions available to principals in member accounts. Effective permissions are the *intersection* of the SCP and the identity's IAM policy: something must be allowed in both places. Nothing is ever granted by an SCP alone.

Two authoring strategies:

- **Deny list** (the common one): leave `FullAWSAccess` attached and add explicit `Deny` statements. Simple, low-risk, additive.
- **Allow list**: detach `FullAWSAccess` and enumerate permitted services. Far tighter, far more brittle — every new service adoption becomes a policy change, and the failure mode is a confusing `AccessDenied` for an engineer whose IAM policy looks correct.

A representative deny-list SCP:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyRegionsOutsideEurope",
      "Effect": "Deny",
      "NotAction": ["iam:*", "sts:*", "cloudfront:*", "route53:*", "support:*", "organizations:*"],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": { "aws:RequestedRegion": ["eu-west-1", "eu-west-2"] }
      }
    },
    {
      "Sid": "ProtectGuardrails",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "guardduty:DeleteDetector",
        "config:DeleteConfigurationRecorder",
        "organizations:LeaveOrganization"
      ],
      "Resource": "*",
      "Condition": {
        "ArnNotLike": { "aws:PrincipalArn": "arn:aws:iam::*:role/OrgAutomationRole" }
      }
    }
  ]
}
```

Misconceptions worth flagging, because they come up constantly:

- **SCPs do not apply to the management account.** Ever. Which is the strongest argument for keeping it empty.
- **SCPs do not apply to service-linked roles.** A deny that would break AWS's own automation is silently skipped for those.
- **The `NotAction` on global services matters.** IAM, STS, CloudFront, Route53, and Support are global but transact through `us-east-1`; a naive region-restriction SCP that omits them breaks IAM entirely. This is the single most common self-inflicted SCP outage.
- **Excluding your own automation role** from a protective deny is what stops you locking your pipeline out of the very thing it manages.
- **RCPs** (Resource Control Policies) are the newer counterpart: SCPs bound what *your principals* can do, RCPs bound what can be done *to your resources* — including by principals outside your org. Worth naming if the interviewer is current; the canonical use is an org-wide `aws:PrincipalOrgID` condition on S3 and STS to stop data being shared externally at all.

**A1.4 — Identity Center vs IAM users, and why IAM users are a smell**

Identity Center brokers **short-lived credentials** from a central identity source. A user authenticates against the IdP, gets a session, and assumes a role in a target account with a bounded session duration. Nothing long-lived exists to leak.

IAM users are a smell because:

- Access keys are **long-lived and unrotated by default**, and they end up in `~/.aws/credentials`, CI variables, laptop backups, and git history. Leaked-key incidents are overwhelmingly IAM user keys (A10.30).
- Lifecycle is **decoupled from HR**. Someone leaves, the IdP account is disabled, and their IAM user in three accounts is still live because nobody owned the offboarding step.
- They **don't scale across accounts** — you either duplicate users per account or build a hub account with cross-account roles, which is Identity Center, badly.
- Auditing "who is this" requires correlating a username to a person out of band. Identity Center puts the IdP identity in the CloudTrail session name.

Legitimate exceptions, worth naming so it doesn't sound dogmatic: **break-glass** users with MFA and sealed credentials for the scenario where the IdP itself is down, and a small number of legacy integrations that genuinely cannot do OIDC or role assumption. Both should be monitored with an alarm on *any* use — a break-glass login that isn't an incident is an incident.

**A1.5 — Permission sets mapped to IdP groups**

A permission set is effectively a role template: Identity Center provisions it as an IAM role into every account it's assigned to. The assignment triple is **group → permission set → account**.

Design principles that separate an experienced answer from a textbook one:

- **Assign to groups, never to individuals.** Individual assignments are invisible in the IdP and become the thing nobody remembers to remove.
- **Model on job function, not per-team snowflakes.** A handful of sets — `ReadOnly`, `Developer`, `Operator`, `SecurityAudit`, `AdminBreakGlass` — applied across many accounts beats one set per team. Scale comes from the account axis, not the permission-set axis.
- **Use SCIM** so group membership provisions automatically. Manual group sync is the same offboarding gap as IAM users, one layer up.
- **Attach a permissions boundary** inside the permission set for anything that grants IAM privileges, so a developer who can create roles cannot create one more powerful than their own (A2.1, A2.9).
- **Session duration** should reflect risk: 12 hours for read-only, 1 hour for admin. It's a real control, not a nuisance setting.
- **Naming convention matters** because the provisioned role name shows up in every CloudTrail event and every trust policy you'll later write.

The differentiation to state: permission sets are how you make "prod access is a different thing to non-prod access" a structural fact rather than a policy document.

**A1.6 — Federation from an external IdP, and troubleshooting it**

Two independent channels, and the first diagnostic step is always to work out which one is broken:

- **SAML (or OIDC) for authentication** — the sign-in flow. Failures here are IdP-side: certificate expiry, wrong ACS/audience URI, clock skew, the app not assigned to the user.
- **SCIM for provisioning** — pushes users and groups into Identity Center. Failures here look completely different: the user signs in fine but has no accounts to choose from, because their group didn't sync or the group synced with no members.

The debugging sequence: does the user exist in Identity Center? Are they in the expected group? Does that group have an assignment to the account and permission set? If all yes and it still fails, it's the SAML assertion — capture it with a browser SAML tracer and check the `NameID` and audience.

Non-obvious failure modes worth having ready:

- **SCIM group membership sync is not instant** and, in some IdPs, nested groups don't flatten — a user in a group that's a member of the assigned group gets nothing.
- **Renaming a group in the IdP** can orphan the assignment, silently revoking access for everyone in it.
- **IdP certificate rotation** is a scheduled outage nobody schedules. It expires, all federated login stops org-wide, and this is exactly the scenario break-glass exists for.
- Deleting and recreating a user with the same email creates a *new* Identity Center user; old assignments don't follow.

**A1.7 — Cross-account role assumption, end to end**

It is a **double opt-in**. Both sides must agree, and this is the single most useful thing to say about it:

1. **Account B** (target) creates a role with a **trust policy** naming who may assume it:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::111122223333:role/DeployRole" },
    "Action": "sts:AssumeRole",
    "Condition": { "Bool": { "aws:MultiFactorAuthPresent": "true" } }
  }]
}
```

2. **Account A** grants its principal `sts:AssumeRole` on that role ARN in an identity policy.
3. The principal calls `sts:AssumeRole`, gets temporary credentials (access key, secret, session token), and acts as the role in B. CloudTrail in B records the assumption and the session name; correlating back to the human requires the `sourceIdentity` or session name.

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::444455556666:role/ReadOnlyCrossAccount \
  --role-session-name jahid-investigation
```

Points that demonstrate you've debugged this:

- **Trusting the root ARN of account B** (`arn:aws:iam::B:root`) does not mean "the root user". It means "anyone in account B who is also granted permission by B's own IAM" — you are delegating the decision to B's administrators. Trusting a specific role ARN is tighter and usually what you want.
- **Role chaining is capped at one hour**, regardless of the role's `MaxSessionDuration`, and you cannot chain from a chained session in some paths. This bites long-running pipelines that assume through a hub role; the symptom is a job that works for 55 minutes then dies with expired credentials.
- Deleting and recreating a role with the same name **breaks trust policies that reference it by ARN** — the ARN is the same but the internal principal ID isn't, and trust policies store the ID after resolution.
- `sourceIdentity` is the underused feature: set it on assumption and it propagates through chains, so the audit trail keeps the human identity.

**A1.8 — External ID and the confused deputy**

The scenario: a third-party SaaS (monitoring, cost tooling, backup) needs read access to your account, so it assumes a role you create. The vendor's own AWS account is the principal in your trust policy.

The problem: that same vendor account is the principal for *every* customer. If another customer of the vendor learns your role ARN — which is not secret — they can ask the vendor to assume it, and the vendor, having valid credentials, complies. The vendor is the "confused deputy": it has authority and is tricked into using it on someone else's behalf.

The fix is an **External ID**: a value the vendor generates uniquely per customer and passes on every `AssumeRole` call, which you require in the trust condition:

```json
"Condition": { "StringEquals": { "sts:ExternalId": "a7f3c9-tenant-unique-value" } }
```

Because the vendor associates it with your tenant only, another customer can't cause it to be sent.

Two things that make the answer land: **the External ID is not a secret** in the password sense — its job is to bind the assumption to a tenant, not to be unguessable, though it should not be something predictable like your account ID. And the **service-principal equivalent** is `aws:SourceAccount` / `aws:SourceArn` in resource policies — the same confused-deputy shape when, say, S3 is configured to publish to your SNS topic and you haven't constrained which bucket may do so.

**A1.9 — What a landing zone is, and what it must provide**

A landing zone is the pre-built, opinionated foundation that every account is born into, so that teams get a compliant environment without designing one. If a team has to make security decisions to ship, you don't have a landing zone.

The components it must provide:

| Capability | What "done" looks like |
|---|---|
| Account structure | OUs reflecting policy differences; automated vending (A1.13) |
| Identity | Identity Center federated to the IdP; no IAM users; break-glass defined |
| Guardrails | Preventive SCPs plus detective Config rules, per OU (A1.11) |
| Network baseline | Non-overlapping CIDRs from IPAM, TGW attachment, controlled egress, private DNS |
| Logging & audit | Org CloudTrail, Config, VPC flow logs, all into a locked log archive account |
| Security services | GuardDuty, Security Hub, Access Analyzer enabled org-wide via delegated admin |
| Encryption | KMS key strategy and defaults; encryption enforced by policy, not convention |
| Cost | Tagging standard, budgets, anomaly detection wired to a real channel |
| Backup | Org-level AWS Backup policies with a defined retention baseline (A11.7) |

The senior framing: a landing zone's value is measured by **how much of it a team can't accidentally turn off**, and by the time from "we need an account" to "we're deploying". If that's weeks, the landing zone has failed regardless of how correct the controls are — people will route around it.

**A1.10 — Control Tower vs a custom landing zone**

**Control Tower** is AWS's managed implementation: it sets up the org, the Security and Sandbox OUs, the log archive and audit accounts, a catalogue of managed controls, Account Factory for vending, and drift detection. It gets a greenfield org to a defensible baseline in days rather than months, and the controls are maintained by AWS.

The costs of that, which are real:

- It is **opinionated**, and its opinions are visible in your account structure forever.
- It **owns resources you then can't freely modify** — its CloudFormation StackSets, its roles, its log buckets. Changing them registers as drift, and remediating drift can mean re-enrolling accounts.
- **Landing zone version upgrades** are periodic, occasionally disruptive work you don't control the timing of.
- Native Account Factory is Service Catalog–driven and **doesn't fit a Terraform-centric workflow**, which is why AFT (Account Factory for Terraform) exists as a bolt-on.

**Custom** — Organizations APIs plus Terraform — gives you exactly the structure you want, in the IaC you already use, with your review process. The cost is that you are now maintaining guardrail content, account baselining, and drift detection yourself, forever, and it typically takes a quarter to reach parity with what Control Tower gives on day one.

How to state the tradeoff so it sounds like judgement rather than preference: **greenfield, small platform team, standard compliance posture → Control Tower** (possibly with AFT). **Existing estate with dozens of accounts already carrying their own history, or unusual structural requirements → custom**, because retrofitting Control Tower onto accounts that predate it is where the pain concentrates (A1.15). The Landing Zone Accelerator (LZA) is the middle path: AWS-maintained, config-driven, more flexible than Control Tower, considerably more machinery.

**A1.11 — Control Tower guardrails: preventive, detective, proactive; mandatory vs elective**

By **enforcement mechanism**:

- **Preventive** — implemented as SCPs. Block the API call outright. Result: `AccessDenied`. Strong, but blunt, and a badly scoped one causes an outage.
- **Detective** — implemented as Config rules. The action succeeds, then the resource is flagged non-compliant. No blast radius, but the window between violation and detection is real, and detection with no remediation path is just a dashboard.
- **Proactive** — CloudFormation hooks. Blocks non-compliant resources at deployment time, before they exist. Only covers what deploys through CloudFormation, so a Terraform shop gets limited value.

By **obligation**: **mandatory** controls are always on and can't be disabled; **strongly recommended** are the well-architected defaults; **elective** are opt-in for specific compliance needs.

The judgement to express: **start detective, then promote to preventive once you know what would break.** Turning on a preventive control across an estate you haven't measured is how you find out at 2am which team depended on the behaviour. The workflow is: enable detective → query CloudTrail and Config for what would have been denied → fix or grant exceptions → then enforce.

**A1.12 — A baseline OU structure, and the justification**

```
Root
├── Security                 (Log Archive, Audit/Security Tooling)
├── Infrastructure           (Network/Transit, Shared Services, CI/CD)
├── Workloads
│   ├── Prod
│   └── NonProd
├── Sandbox                  (time-boxed, budget-capped, heavily restricted)
├── PolicyStaging            (new accounts land here for baselining)
└── Suspended                (deny-all; decommissioning)
```

The justification is the point of the question. **SCPs attach to OUs, so OU boundaries should follow policy boundaries — not the org chart.** Prod and NonProd are separate OUs because they need different region restrictions, different instance-type limits, different rules on who can assume admin, and different backup mandates. If two OUs would carry identical policy, they probably shouldn't be two OUs.

Specific reasoning to attach:

- **Security is its own OU at the top** so its SCPs can be the strictest in the org, and so the log archive is never accidentally caught by a workload-oriented policy.
- **Infrastructure is separate from Workloads** because the network and shared-services accounts are consumed by everyone; their change control is different in kind.
- **Sandbox exists so that experimentation has a legitimate home.** Without one, experiments happen in NonProd and eventually in Prod. Cap it with budgets and an SCP restricting expensive services.
- **Suspended with a deny-all SCP** is how you decommission safely: retain the account and its logs, remove all capability, delete later.
- **Avoid mirroring team structure.** Teams reorganise every eighteen months; you don't want to restructure your org each time.

**A1.13 — Account vending / account factory**

A pipeline, not a runbook. The stages:

1. **Request** — a PR into an accounts repo, or a Service Catalog product. Captures: name, owner, cost centre, environment, target OU, budget, and a unique root email (use a distribution list or plus-addressing — *never* a personal mailbox, because that address is the account recovery path).
2. **Create** — `organizations:CreateAccount`, then move into the target OU. Idempotency matters: account creation is not reversible and names aren't reusable cleanly.
3. **Baseline** — the substantial part. Applied as code, identically, every time: VPC from an IPAM allocation, TGW attachment, IAM roles and permission-set assignments, Config recorder, GuardDuty member enrolment, log shipping, KMS keys, budgets and tags, backup plan.
4. **Hand over** — the team gets an account that's already compliant, with a documented path to request exceptions.

The details that read as experience:

- **Root credentials on a new account must be secured immediately** — password reset to something stored in a vault, MFA enrolled, root access keys never created. AWS's centralised root access management now lets you remove root credentials from member accounts entirely, which is the better answer where available.
- **The baseline must be re-runnable**, because it will drift and because you will add controls later and need to backfill.
- **New accounts have default quotas**, not your org's raised ones. Quota increase requests are per-account and take time; a vending pipeline that doesn't request them delivers an account that falls over on first real load (A11.9).
- Closing accounts is rate-limited and has a 90-day suspension period — worth knowing before someone vends fifty test accounts.

**A1.14 — Onboarding an existing account into an org with guardrails intact**

The sequence, and the reason for it:

1. **Inventory before you invite.** What's running, who has access, what IAM users and access keys exist, what regions are in use, what trails and Config recorders already exist.
2. **Invite** (`organizations:InviteAccountToOrganization`) and accept. Billing moves to consolidated immediately — flag that to finance, because the standalone bill stops.
3. **Land it in a staging OU with minimal SCPs**, not directly into Prod OU. This is the step people skip.
4. **Dry-run the guardrails.** Query the account's CloudTrail for the last 30–90 days and check which actions the target OU's SCPs would have denied. This is the only reliable way to know whether attaching them will cause an outage.
5. **Baseline**: enrol into org CloudTrail, GuardDuty, Security Hub, Config via delegated admin; apply tags and budgets; reset root; remove IAM users in favour of Identity Center.
6. **Move to the real OU** once clean.

Non-obvious failure modes:

- **Pre-existing account-level CloudTrail and Config recorders conflict with org-level ones.** You get duplicate delivery and duplicate cost, and Config in particular can be surprisingly expensive when doubled. Decommission the local ones after verifying org-level coverage.
- **Existing region usage may violate a region-restriction SCP.** Resources already there keep running; you just can't manage them. That's arguably worse than them being deleted, because they become invisible and unpatched.
- **Reserved Instances and Savings Plans get pooled** across the org on joining, which changes the effective discount distribution and can make another account's bill mysteriously move.
- Some services (older marketplace subscriptions, certain support plans) don't transfer cleanly.

**A1.15 — Retrofitting governance onto pre-landing-zone accounts**

This is the item where a real answer is unmistakable, because everyone who's done it describes the same tension: the controls are easy, the migration is political.

The approach:

1. **Measure first.** Deploy a Config aggregator and Security Hub across the estate in *detective mode only* and produce an honest baseline. You cannot negotiate a remediation plan without a number.
2. **Rank by risk, not by ease.** Public S3 buckets and long-lived admin keys before missing tags.
3. **Report-then-enforce for every preventive control.** Take the SCP you intend to apply, translate it into a CloudTrail query, and show teams the list of calls it would have blocked. This converts "you're going to break us" into a concrete, finite list.
4. **Give a migration path and a deadline, together.** Neither works alone. A deadline with no path breeds exceptions; a path with no deadline never completes.
5. **Build the exception process before you need it** — documented, time-boxed, with a named owner and an expiry date. Undocumented permanent exceptions are how governance programmes quietly die.
6. **Phase by OU.** Move accounts into the governed OU in waves, starting with the ones that are already close to compliant, so early waves generate evidence that it's survivable.

What to flag: the hardest accounts are the ones with an owner who has left, running something nobody will admit to depending on. The tactic that works is disabling in stages with a loud, well-advertised rollback window rather than deleting — and the resilience-review framing ("we found six accounts with no owner and no backup") gets executive attention where a compliance score never does.

**A1.16 — Centralised logging and the log archive account**

The pattern: **one account whose only job is to receive logs, and to which nothing else has write access.**

- **Org CloudTrail** created in the management account (or the delegated admin), delivering all member accounts' events to an S3 bucket in the log archive account. Member accounts can't disable or reconfigure it.
- The **bucket policy denies delete and denies write from anything other than the CloudTrail service principal**; humans in the log account get read at most.
- **S3 Object Lock in compliance mode**, or at minimum versioning plus MFA delete, so retention is enforced by the platform rather than by policy.
- **A KMS key owned by the log account** encrypts the objects. If prod owned the key, an attacker with prod admin could make the logs unreadable without touching the bucket — the same evidence-destruction outcome by a different route (A10.5).
- **Cross-region replication** to protect against a regional event.
- The same account receives Config snapshots, VPC flow logs, ALB access logs, and CloudWatch Logs exports.

The property to articulate: **an attacker with full administrative access to a workload account should be unable to alter or delete the record of what they did.** That's the whole point, and it only holds if the trust flows one way — log account can read nothing from prod, prod can write but not read or delete. Say it that way and it's clear you've thought about the threat model rather than the architecture diagram.

Also worth naming: retention tiering, because org trails on a large estate get expensive fast (A9.9), and access to the log account being itself audited and alarmed.

**A1.17 — Delegated administration**

Most org-level services (GuardDuty, Security Hub, Config, Access Analyzer, IPAM, CloudTrail, Firewall Manager, Inspector, Backup) let you nominate a member account as their administrator:

```bash
aws organizations register-delegated-administrator \
  --account-id 444455556666 \
  --service-principal guardduty.amazonaws.com
```

Why it matters: it's the mechanism that lets you **keep the management account empty** (A1.2). Without it, every security tool has to be operated from the account that also controls billing and account creation — so your security engineers need credentials in the most privileged account in the org, which is precisely the wrong outcome.

With delegation, the security team gets full org-wide visibility and control of *their* services from the audit account, and nobody routinely logs into the management account at all. That last property is the one to state, because "how often does anyone log into your management account" is a good proxy question for whether an org is well run.

Caveats: delegation is per-service, so it's a checklist not a switch; a few services still require actions in the management account; and the delegated admin account should itself be locked down, since it now holds org-wide security control.

---

## A2. IAM — T1

**A2.1 — Identity-based, resource-based, and permissions boundaries**

- **Identity-based** — attached to a user, group, or role. Says "this principal may do X to Y". No `Principal` element, because the principal is whoever it's attached to.
- **Resource-based** — attached to the resource (S3 bucket, KMS key, SQS queue, SNS topic, Secrets Manager secret, Lambda function, ECR repo, EventBridge bus). Has a `Principal` element, because it must say *who*. This is what enables cross-account access without the caller assuming a role in your account.
- **Permissions boundary** — attached to a user or role; sets the *maximum* permissions that identity can have. It grants nothing. Effective permissions are the intersection of the identity policy and the boundary.

Two further types complete the picture and are worth naming: **SCPs** (org guardrail, A1.3) and **session policies** (passed at `AssumeRole` to further narrow a session).

The non-obvious parts:

- **For most services, cross-account access needs an allow on both sides** — the caller's identity policy *and* the resource policy. **KMS is the exception**: the key policy alone is authoritative, and if it doesn't delegate to IAM (via the `Principal: {"AWS": "arn:aws:iam::ACCT:root"}` statement), no amount of IAM policy will help. This asymmetry is behind a large share of KMS access-denied confusion (A10.3, A10.4).
- **Boundaries are the mechanism for safe delegation.** Letting developers create roles is desirable; letting them create a role more powerful than themselves is privilege escalation (A2.9). The pattern is: grant `iam:CreateRole` with a condition requiring `iam:PermissionsBoundary` be set to a specific boundary policy ARN, and deny `iam:DeleteRolePermissionsBoundary`.

**A2.2 — Writing a least-privilege policy from scratch**

Method: start from the requirement, enumerate the exact API calls, scope resources to ARNs, then add conditions. Not "start from `*` and trim", which never actually gets trimmed.

Requirement: *a service reads objects from one prefix of one bucket, and the objects are encrypted with a CMK.*

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOnlyThatPrefix",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::acme-reports",
      "Condition": { "StringLike": { "s3:prefix": "ingest/*" } }
    },
    {
      "Sid": "ReadObjects",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::acme-reports/ingest/*"
    },
    {
      "Sid": "DecryptWithTheBucketKey",
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:DescribeKey"],
      "Resource": "arn:aws:kms:eu-west-1:111122223333:key/1234abcd-...",
      "Condition": {
        "StringEquals": { "kms:ViaService": "s3.eu-west-1.amazonaws.com" }
      }
    }
  ]
}
```

Things this example demonstrates deliberately:

- **Bucket-level actions and object-level actions take different ARNs.** `ListBucket` on the bucket, `GetObject` on `bucket/*`. Getting this wrong produces the classic "I can read the object but `aws s3 ls` returns nothing".
- **KMS permissions are separate and constantly forgotten.** Read access to an SSE-KMS object without `kms:Decrypt` fails with an access-denied that names KMS, not S3 — and people go looking at the bucket policy.
- **`kms:ViaService`** confines key use to requests routed through S3, so a leaked credential can't call `Decrypt` directly on arbitrary ciphertext.
- Refine with **Access Analyzer policy generation** from CloudTrail after the workload has run (A2.10), rather than guessing the action list.

**A2.3 — Policy evaluation logic**

Evaluation order, and any single failure means deny:

1. **Explicit `Deny` anywhere** — in any policy type, at any level. Always wins, immediately, full stop.
2. **SCP** — must allow (for member-account principals; not evaluated for the management account or service-linked roles).
3. **RCP** — must allow, for actions on resources in the org.
4. **Resource-based policy** — if one exists and grants directly, this can be sufficient on its own for same-account access, and for cross-account it must allow.
5. **Permissions boundary** — must allow, if attached.
6. **Session policy** — must allow, if one was passed.
7. **Identity-based policy** — must allow.
8. **Default: implicit deny.**

The two clarifications that matter in practice:

- **An explicit deny cannot be overridden by any allow**, which is what makes deny-list SCPs safe and also what makes a mis-scoped deny an org-wide outage.
- **Same-account resource policies can shortcut the identity policy** for some services — an S3 bucket policy granting a principal in the same account works without a matching identity policy — but cross-account always needs both. This asymmetry is worth stating explicitly, because it's the source of "it works in dev and not in prod" when dev happens to be same-account.

**A2.4 — Debugging access denied methodically**

The error message is the first tool, and it's more informative than people assume. AWS distinguishes cases:

- *"with an explicit deny in a service control policy"* — it's an SCP; stop looking at IAM.
- *"with an explicit deny in an identity-based policy"* / *"in a resource-based policy"* — names the policy type.
- *"because no identity-based policy allows"* — implicit deny; nothing is denying, nothing is allowing.
- *"is not authorized to perform: sts:AssumeRole"* — trust policy on the target role, not the caller's permissions (A1.7).

The sequence:

1. **Read the message.** Note the *exact* principal ARN it reports — very often it's not the principal you thought you were, which makes this an A14.3 problem, not a policy problem.
2. **CloudTrail** for the failed event: `errorCode`, `errorMessage`, `userIdentity`, and the request parameters. Filter on `errorCode = AccessDenied`.
3. **IAM Policy Simulator** for identity policies, and the **`--dry-run`** flag where a service supports it.
4. **Walk the layers in evaluation order** (A2.3), cheapest first: am I who I think I am → is there an SCP → boundary → resource policy → identity policy.

Non-obvious cases to have ready:

- **A KMS denial masquerading as a service denial** — the S3/RDS/EBS call fails because the key policy doesn't allow the principal (A10.4).
- **Condition keys that don't behave as assumed**: `aws:SourceIp` **does not match** when the request goes via a VPC endpoint, because the source is the endpoint, not a public IP. Use `aws:SourceVpce` or `aws:SourceVpc` instead. This silently breaks IP-restricted policies the day someone adds an endpoint for cost reasons (A3.3).
- **Eventual consistency in IAM.** Newly created or modified policies can take seconds to propagate; a CI job that creates a role and immediately uses it fails intermittently. Retry with backoff, don't "fix" it by widening the policy.
- **Permissions boundary present but forgotten** — the identity policy looks perfect and the boundary silently caps it.

**A2.5 — Using conditions effectively**

```json
"Condition": {
  "StringEquals":    { "aws:PrincipalTag/team": "platform" },
  "StringNotEquals": { "aws:RequestedRegion": "us-east-1" },
  "Bool":            { "aws:SecureTransport": "true" },
  "ArnLike":         { "aws:PrincipalArn": "arn:aws:iam::*:role/deploy-*" }
}
```

The ones that earn their place:

- **`aws:PrincipalOrgID`** — on a resource policy, restricts access to principals in your org. The single highest-value condition key for preventing accidental external sharing, and the basis of most RCPs.
- **`aws:PrincipalTag` / `aws:ResourceTag`** — attribute-based access control. One policy that says "you may act on resources tagged with your own team" replaces dozens of per-team policies. The catch: it's only as good as tag integrity, so it must be paired with the next item.
- **`aws:RequestTag` and `aws:TagKeys`** — enforce tagging *at creation*, which is the only point at which tagging enforcement works (A12.2). Deny `RunInstances` unless `aws:RequestTag/cost-centre` exists.
- **`aws:SourceIp`** — with the VPC-endpoint caveat above.
- **`aws:MultiFactorAuthPresent`** — on trust policies for privileged roles.
- **`kms:ViaService`**, **`s3:prefix`**, **`iam:PassedToService`** — service-specific and very effective at narrowing.

Gotchas worth flagging: multiple keys in one condition block are **AND**; multiple values for one key are **OR**. `Bool` on `aws:MultiFactorAuthPresent` with `false` is not the same as `BoolIfExists` — for principals where the key is absent entirely (like service roles), the plain version silently doesn't match, which is a common way to write a deny that never fires. And `StringLike` with a careless `*` is how over-broad trust policies happen (A2.8).

**A2.6 — Instance profiles and keyless credentials**

An instance profile is a container that binds an IAM role to an EC2 instance. The instance retrieves temporary credentials from the **Instance Metadata Service** at `169.254.169.254`; the SDK does this automatically via the credential provider chain (A14.3), and the credentials rotate before expiry without anything on the instance handling rotation.

The security point: **no key material exists on the box**, so there's nothing to leak in a backup, an AMI, or a config file.

The failure mode that matters: **IMDSv1 was request/response, so any SSRF vulnerability in an application on the instance could fetch role credentials** — this is the mechanism behind several large breaches. **IMDSv2 requires a PUT to obtain a session token**, which most SSRF primitives can't do, and honours a hop limit (default 1) so a container on the host can't reach it by default.

```bash
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

Enforce IMDSv2 as required (`HttpTokens: required`) in launch templates, and back it with an SCP denying `RunInstances` without it. The hop-limit subtlety: containers on ECS/EKS need a hop limit of 2 to reach IMDS, which is also why you should be using task roles / IRSA rather than the node role (A2.7).

**A2.7 — IRSA and EKS Pod Identity**

Both solve the same problem: **giving a pod its own IAM identity instead of falling back to the node instance role**, which would grant every pod on the node the union of all permissions any pod needs.

**IRSA** — the cluster gets an OIDC provider registered in IAM. A ServiceAccount is annotated with a role ARN; a mutating webhook injects a projected service-account token and `AWS_ROLE_ARN` / `AWS_WEB_IDENTITY_TOKEN_FILE` into the pod; the SDK calls `AssumeRoleWithWebIdentity`. The role's trust policy conditions on the OIDC issuer, the `sub` (namespace and service account), and `aud`:

```json
"Condition": {
  "StringEquals": {
    "oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:payments:api",
    "oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com"
  }
}
```

**Pod Identity** — newer. An agent DaemonSet plus an association API maps a service account to a role; no per-cluster OIDC provider, and no trust policy edit per cluster. Trust is on `pods.eks.amazonaws.com` and is reusable across clusters, which is the main operational win: with IRSA, adding a cluster means editing the trust policy of every role it uses, which does not scale across many clusters.

Tradeoffs to state: **Pod Identity doesn't support Fargate**, and IRSA works anywhere OIDC federation does — including outside EKS — so IRSA remains the general answer. Pod Identity supports session tags and role chaining, which makes cross-account cleaner.

The mistakes: using `StringLike` with a wildcard in the `sub` condition (any service account in the cluster can then assume the role); forgetting the `aud` condition; and pods silently falling back to the node role when the annotation is wrong — it *works*, with the wrong identity, which is worse than failing. Check with `aws sts get-caller-identity` from inside the pod.

**A2.8 — GitHub Actions OIDC to AWS**

Configure the GitHub OIDC provider in IAM (`token.actions.githubusercontent.com`), then a role whose trust policy conditions on the repository and ref:

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:acme/payments-infra:ref:refs/heads/main"
    }
  }
}
```

Workflow side needs `permissions: id-token: write` and `aws-actions/configure-aws-credentials`.

The security review points, which are the reason this item exists:

- **The `sub` condition is the entire security boundary.** `repo:acme/*` lets any repo in the org assume the role. Worse, a missing `sub` condition with only `aud` checked lets **any GitHub repository on the internet** assume it. That misconfiguration is common enough to be worth checking for explicitly.
- **Constrain on `ref` or `environment`** for deployment roles, so a branch or a fork PR can't assume the production role. `pull_request` events have a different `sub` (`repo:org/repo:pull_request`) — this is the control that stops a fork PR deploying.
- Pair with **GitHub environments and required reviewers** for prod, since the AWS side can only see what GitHub asserts.
- The gain over stored keys: no long-lived secret exists, credentials are scoped per-run and expire in an hour, and revocation is a trust-policy edit rather than a key rotation across every repo (see the CI/CD domain for the pipeline-level treatment).

**A2.9 — `iam:PassRole` and privilege escalation**

`PassRole` is the permission to hand an existing role to an AWS service. It's necessary — you can't launch EC2 with an instance profile, create a Lambda, or run a CloudFormation stack without it — and it's an escalation primitive, because **the ability to pass a powerful role to a service you control is equivalent to holding that role.**

The attack: a user with `lambda:CreateFunction`, `lambda:InvokeFunction`, and unconstrained `iam:PassRole` creates a function with an admin role attached and invokes it. They're now admin, without ever having had admin permissions. Same shape with `ec2:RunInstances` and a user-data script, or CloudFormation with an admin service role.

Constraining it:

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::111122223333:role/app-runtime-*",
  "Condition": { "StringEquals": { "iam:PassedToService": "lambda.amazonaws.com" } }
}
```

Scope the resource to a naming convention, and pin the target service.

Related escalation paths to name, because a good answer treats this as a class rather than one permission: `iam:CreatePolicyVersion` (rewrite an attached policy), `iam:AttachUserPolicy` / `PutUserPolicy`, `iam:UpdateAssumeRolePolicy` (make yourself trusted by a privileged role), `lambda:UpdateFunctionCode` on an already-privileged function, `glue`/`datapipeline`/`cloudformation` service roles, and `ssm:SendCommand` against an instance with a privileged profile. The generalisation: **any permission that lets you influence code or configuration executed under another identity is an escalation path**, and reviewing for that class is more useful than blocklisting individual actions.

**A2.10 — Access Analyzer and last-accessed data for right-sizing**

Three distinct capabilities, worth separating:

- **External access findings** — resources (S3, KMS, roles, SQS, Secrets Manager, Lambda) whose policies grant access outside your defined zone of trust (account or org). This is how you find the bucket shared with an ex-vendor's account.
- **Unused access findings** — roles, users, permissions, and access keys not used within a configured window. The direct input to right-sizing.
- **Policy generation** — builds a policy from the principal's actual CloudTrail activity over up to 90 days. The practical way to get from `*` to least privilege without guessing.

Plus **service last-accessed data** (`aws iam get-service-last-accessed-details`, and the console's Access Advisor tab), which shows which services a principal has actually touched.

The workflow that works: generate a candidate policy from observed activity → **widen it slightly for known-infrequent paths** (quarterly jobs, DR procedures, incident response) → apply in a lower environment → monitor for denials → promote.

The caveat that separates experience from theory: **absence of use is not absence of need.** A 90-day window misses the annual DR test, the quarter-end batch, and every break-glass path. Removing a permission because it wasn't used in 90 days is how you discover during an incident that the incident response role can no longer respond. Right-size aggressively for routine workloads, conservatively for anything that exists for rare events — and where you do trim, keep the removal in version control so restoring it is a revert rather than an investigation.

**A2.11 — Auditing and removing unused credentials across an org**

Mechanics:

```bash
aws iam generate-credential-report
aws iam get-credential-report --query Content --output text | base64 -d
```

The report gives, per user: password last used, access key last used and rotation age, MFA status. Run it per account and aggregate — via a script assuming a read-only role in each account, or via Access Analyzer's unused-access analyser at the org level with a delegated admin, which is the better answer because it covers roles as well as users.

The process, which is the actual content of the question:

1. **Inventory and attribute.** Every credential needs a named owner. Unowned credentials are the highest-risk category and the hardest to remove, because nobody will confirm they're safe to delete.
2. **Notify with a deadline.**
3. **Disable, don't delete.** Deactivate the key, wait through a full business cycle (at least a month, to catch monthly jobs), then delete. Deletion is irreversible and the recovery path for "we deleted the key that runs payroll" is bad.
4. **Alarm on use of anything you've disabled** — that tells you immediately who depended on it.
5. **Close the tap**: SCP denying `iam:CreateAccessKey` (with an exception role), Identity Center for humans, OIDC for CI, roles for workloads. Removing keys without preventing new ones is a treadmill.

Report the outcome as a trend — "long-lived keys down from 340 to 12, all with named owners and rotation" — because that's what makes it a resilience and audit story rather than a cleanup ticket.

---

## A3. VPC, connectivity & hybrid — T1

Networking *reasoning* is Domain 3; this section is the AWS-specific configuration and the operational decisions.

**A3.1 — Building a VPC: subnets, route tables, IGW, NAT**

The standard three-tier, three-AZ layout:

- **VPC CIDR** from IPAM allocation (A3.9), sized with growth in mind — see N2.4 for sizing and the EKS trap.
- **Public subnets** (one per AZ): route `0.0.0.0/0` → **internet gateway**. Only load balancers and NAT gateways live here. A subnet is "public" purely because its route table points at an IGW — there is no `public: true` flag, and this is worth saying because people look for one.
- **Private app subnets**: route `0.0.0.0/0` → **NAT gateway in the same AZ**.
- **Private data subnets**: often no default route at all, reaching AWS services via endpoints only.
- **Route tables per tier per AZ**, not one shared table — because the NAT target differs per AZ.

The decisions that show experience:

- **One NAT gateway per AZ, not one per VPC.** A single NAT is both a single point of failure (its AZ goes, all egress dies) and a cross-AZ data-transfer bill on every byte. The counter-argument for non-prod is cost — three NATs at ~$32/month each plus processing, versus one — and that's a legitimate environment-dependent choice, but state it as a deliberate tradeoff, not a default.
- **NAT gateways are the classic surprise line item** (A12.4): you pay hourly *and* per GB processed, and traffic to S3 or ECR from private subnets goes through it unless you add endpoints (A3.3).
- Public IP addressing now carries an hourly charge, which changes the arithmetic on giving instances public IPs "just for setup".
- Reserve address space contiguously so a later subnet expansion doesn't require re-IPing. You can add secondary CIDRs to a VPC, but you cannot resize the primary.

**A3.2 — Security groups vs NACLs**

The mechanism is N10.1 — **security groups are stateful, NACLs are stateless** — and a good answer doesn't just recite that, it names the consequence: with a NACL you must explicitly allow the **ephemeral port range** (1024–65535) inbound for return traffic, and forgetting it produces a connection that establishes and then hangs, which looks nothing like a firewall problem.

The AWS-specific operational points:

- **Default to security groups for everything.** They're the primary control: instance-level, stateful, and — the key feature — **they can reference other security groups as sources**. `allow 5432 from sg-app` survives autoscaling, IP changes, and re-deploys, where a CIDR rule doesn't. If a candidate doesn't mention SG-to-SG references, they haven't run this at scale.
- **NACLs are a subnet-level blunt instrument.** Legitimate uses: a coarse deny of a known-bad CIDR, or a compliance requirement for a second layer of defence at a subnet boundary. They're evaluated in rule-number order with first-match-wins, unlike SGs which are pure allow-lists with no ordering.
- **SGs cannot express deny.** If the requirement is "everything except this range", that's a NACL or a firewall, not an SG.
- Rule quotas are real on large estates (rules per SG, SGs per ENI) and referencing SGs rather than CIDRs is also how you stay under them.
- Debugging order: **VPC Reachability Analyzer** answers "can this path work at all" statically, then flow logs (A3.5) answer "what actually happened".

**A3.3 — VPC endpoints, justified on cost or compliance**

Two kinds:

- **Gateway endpoints** — S3 and DynamoDB only. Implemented as a route-table entry to a prefix list. **Free.** There is no reason not to have them in every VPC; omitting them means S3 traffic from private subnets goes out through the NAT gateway and you pay per GB for data you could have moved for nothing.
- **Interface endpoints (PrivateLink)** — an ENI with a private IP in your subnet, for most other services (ECR, Secrets Manager, SSM, KMS, STS, CloudWatch Logs, SQS...). Charged **per endpoint per AZ per hour, plus per GB**.

The two justifications:

**Cost** — arithmetic, not ideology. An interface endpoint costs roughly $7–8/month per AZ; NAT processing is ~$0.045/GB. So an endpoint pays for itself somewhere around 200 GB/month per AZ. ECR is the usual winner: a large EKS cluster pulling images through NAT generates startling bills, and image pulls need *two* endpoints (`ecr.api` and `ecr.dkr`) plus the **S3 gateway endpoint**, because layers are stored in S3. Missing the S3 gateway endpoint is why "I added ECR endpoints and my NAT bill didn't move".

**Compliance** — traffic never traverses the public internet, and you can go further: a **VPC endpoint policy** restricting which buckets can be reached, plus an S3 bucket policy with `aws:SourceVpce`, gives you a genuine data-exfiltration control — a compromised workload cannot copy data to an attacker's bucket, because the endpoint won't route to it.

The failure mode to flag: **interface endpoints enable private DNS by default**, which overrides the public hostname for that service VPC-wide. If something in the VPC relied on reaching that service another way, it breaks with a confusing DNS resolution, and the fix isn't obvious unless you know private DNS was switched on. Also: endpoints are AZ-specific, and an endpoint missing in one AZ produces a workload that fails only when scheduled there.

**A3.4 — Peering vs Transit Gateway**

The comparison is N10.5. The AWS-specific additions:

- **Peering is non-transitive and that's a hard property, not a limitation to work around.** A↔B and B↔C does not give A↔C. People try to fix this with routes; it doesn't work.
- **Both refuse overlapping CIDRs** (N2.5, A3.16).
- **TGW costs per attachment-hour plus per GB**, and crucially charges for traffic that peering carries for free within a region — so a heavily chatty two-VPC pair can be materially cheaper peered even in an estate that otherwise uses TGW.
- **TGW gives segmentation via multiple route tables** (A3.13), which peering cannot: "prod can reach shared services but not dev" is a route-table design, not a set of SG rules.
- **PrivateLink is the third option people forget.** If the requirement is "expose one service to another VPC", PrivateLink does it without routing the networks together at all — which also sidesteps overlapping CIDRs entirely.

Decision framing: two or three VPCs with a stable relationship → peering. More than a handful, or any hybrid connectivity, or any need for centralised inspection/segmentation → TGW. One service, not a network → PrivateLink.

**A3.5 — Reading VPC flow logs to prove accept or reject**

Flow logs record IP traffic metadata (not payload) per ENI, subnet, or VPC, to CloudWatch Logs or S3. The default format:

```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
```

A Logs Insights query for rejected traffic to a port (A9.2):

```
fields @timestamp, srcAddr, dstAddr, dstPort, action
| filter action = "REJECT" and dstPort = 5432
| stats count(*) by srcAddr, dstPort
| sort by count(*) desc
```

What flow logs actually prove, and this is the useful part:

- **`REJECT` means a security group or NACL blocked it** — the packet reached AWS's network and was refused by your configuration. That's a definitive answer to "is it the firewall".
- **`ACCEPT` with no application response means the problem is above layer 4** — the packet was allowed through, so look at the application, the listener, or the target. This is the direction people fail to use: flow logs are as valuable for exonerating the network as for indicting it.
- **No log entry at all** means the traffic never arrived — routing, DNS resolving to the wrong place, or the client never sent it.

The gotchas: **stateful SG behaviour means you'll see the accepted flow but not a separate reject for return traffic**; NACL rejects appear as a rejected flow in the direction the NACL blocked. There's an **aggregation interval** (default 10 minutes, can be 1), so flow logs are not real-time and are useless for a "what's happening right now" question. And **not everything is captured** — DNS to the Amazon resolver, DHCP, instance metadata, and license activation traffic are excluded, which regularly causes "the flow logs show nothing" confusion when the issue is DNS. Custom formats can add `vpc-id`, `pkt-srcaddr` (the real source behind a NAT), and `tcp-flags`, which is what you want when diagnosing whether SYNs are being answered.

**A3.6 — Route53 Resolver and private hosted zones for cross-account resolution**

A private hosted zone is associated with one or more VPCs, and only those VPCs resolve its records. The mechanisms:

- **Same account**: associate the PHZ with each VPC directly.
- **Cross-account**: create an authorisation from the zone owner (`create-vpc-association-authorization`), then the VPC owner associates. Awkward via console, straightforward in Terraform, and it's a two-step because both sides must consent.
- **At scale**: a shared services account owns the zones, and either associates many VPCs, or you use **Route53 Profiles** to distribute a set of zones and rules to many VPCs as a unit — which is the modern answer for a large org and avoids the N-associations problem.

Requirements people miss: `enableDnsSupport` and `enableDnsHostnames` must be on. The VPC resolver lives at the **VPC base +2** address (N2.6) and has a **per-ENI packet-per-second limit** (~1024) that is a genuine, hard-to-diagnose scaling wall — the symptom is intermittent DNS failures under load with nothing obviously wrong, and the fix is caching (NodeLocal DNSCache on EKS) rather than more instances. And **split-horizon**: if a private zone and a public zone share a name, the private one wins inside the VPC, which is either the design or a very confusing incident depending on whether you intended it.

**A3.7 — Bastion-free access with SSM Session Manager**

Requirements: SSM agent on the instance (pre-installed on current Amazon Linux and Ubuntu AMIs), an instance profile with `AmazonSSMManagedInstanceCore`, and network egress to the SSM endpoints — either via NAT or, better, **interface endpoints for `ssm`, `ssmmessages`, and `ec2messages`** (all three; missing `ssmmessages` is the usual cause of "the instance shows as not managed").

```bash
aws ssm start-session --target i-0123456789abcdef0
# port forwarding to a private RDS instance, no bastion, no inbound rule
aws ssm start-session --target i-0123... \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["db.internal"],"portNumber":["5432"],"localPortNumber":["5432"]}'
```

Why it beats a bastion, stated as properties rather than preferences:

- **No inbound rules at all** — the agent polls outbound. The attack surface of an internet-facing SSH port simply doesn't exist.
- **No SSH keys to distribute, rotate, or lose.** Access is IAM, so it's revoked by removing a permission set, immediately, org-wide.
- **Every session is logged to CloudTrail, and the session content itself can be logged** to S3 or CloudWatch — which is an audit capability a bastion gives you only with extra tooling.
- IAM conditions can restrict sessions by **instance tag**, so "developers can shell into dev-tagged instances only" is expressible.

The counterpoints worth acknowledging: it depends on the SSM control plane and on IAM being available, so **your break-glass path shouldn't depend solely on it** — a documented emergency route matters (A1.4). It's chattier and slightly higher-latency than SSH. And the more mature position is that shelling into instances at all is the smell: if the answer to every incident is a session, the observability is inadequate (A9) and the instances aren't immutable (A4.6).

**A3.8 — Planning VPC CIDR allocation across an org**

The requirement: **no two networks that might ever need to talk can overlap** — and "might ever" includes acquisitions, partner VPNs, and the on-prem estate you don't control (A3.16).

The method:

1. **Reserve a large supernet for AWS** as a whole (say `10.128.0.0/9`) and agree it with whoever runs on-prem addressing, so the two estates can never collide.
2. **Sub-allocate by region**, then by environment, then by account. Regional blocks matter because they keep route tables summarisable — a TGW route table with one aggregate per region is manageable, one with two hundred VPC-specific routes is not.
3. **Standardise VPC sizes** — a small number of t-shirt sizes rather than bespoke sizing per request. Bespoke sizing is where fragmentation comes from.
4. **Leave deliberate gaps** for growth adjacent to each allocation.

The sizing reasoning is N2.4, and the EKS warning bears repeating here: with the VPC CNI every pod consumes a VPC IP (A5.7), so app subnets need to be far larger than instinct suggests.

**A3.9 — VPC IPAM: pools, scopes, allocation rules, utilisation**

Structure: an **IPAM** instance, **scopes** (public and private; private is the interesting one), **pools** which nest hierarchically — typically a top-level pool per supernet, regional pools beneath, then environment pools — and **allocation rules** on each pool (minimum and maximum netmask length, required tags, whether allocations must be automatic).

In practice: Terraform requests a CIDR from a pool rather than hardcoding one (`ipv4_ipam_pool_id` with `ipv4_netmask_length` on `aws_vpc`), IPAM allocates and records it, and utilisation is visible per pool with CloudWatch metrics and alarms when a pool crosses a threshold.

The operationally important bits: IPAM **discovers existing CIDRs** across the org, so it can be adopted onto a live estate rather than requiring greenfield — that's the feature that makes it viable in a real environment. Allocations can be **shared cross-account via RAM**, which is how a central network account governs allocation without provisioning every VPC. And it monitors for overlap and for resources whose CIDR came from outside the pool, which is how you catch the team that provisioned a VPC by hand.

**A3.10 — What IPAM solves that a spreadsheet doesn't**

The spreadsheet fails not because it's a bad data structure but because **it isn't in the provisioning path**. Specifically:

- It records intent, not reality. Someone provisions without updating it, and the drift is invisible until a TGW attachment fails.
- **Nothing enforces it.** IPAM is an allocation authority — Terraform requests a CIDR and gets one, so it is not possible to provision an overlapping VPC through the normal path.
- No utilisation visibility. You discover a pool is exhausted when a provisioning request fails, not when it crosses 80%.
- No reclamation. Deleted VPCs leave permanently-reserved space in a spreadsheet; IPAM sees the deallocation.
- No cross-account view without someone maintaining it manually — which is exactly the work that doesn't happen.

The framing that lands: **overlapping CIDRs are discovered at the worst possible moment** — when you're trying to connect two things under time pressure, and the fix is re-IPing a live workload, which is a project, not a change. IPAM converts a class of expensive, late-discovered failure into a provisioning-time error. That's the argument, and it's the same argument as any other shift-left control.

**A3.11 — Site-to-site VPN: customer gateway, tunnels, BGP vs static**

Components: a **virtual private gateway** (VPC-attached) or **TGW**, a **customer gateway** resource representing the on-prem device's public IP and ASN, and a **VPN connection** — which AWS always provisions as **two IPsec tunnels to two separate endpoints** for redundancy.

**The single most common real-world problem: only one tunnel is configured.** AWS gives you two, the on-prem side configures one because it works, and then AWS performs routine maintenance on that endpoint and connectivity drops. Both tunnels must be up, and you should alarm on the `TunnelState` CloudWatch metric per tunnel, not on aggregate connectivity.

**BGP vs static:**

- **BGP (dynamic)** — routes are exchanged and withdrawn automatically, so failover between tunnels is automatic and fast, and adding a subnet on either side propagates without a change request. Requires a device that speaks BGP and an ASN on each side.
- **Static** — routes configured manually on both sides. Simpler, works with basic devices, but **failover is not automatic in any meaningful sense** and every network change is a coordinated manual edit on both sides.

Use BGP unless the far-end device genuinely cannot. Also worth naming: **asymmetric routing** when both tunnels are up and each side prefers a different one — solvable with AS path prepending or local preference; **~1.25 Gbps per tunnel** as a hard ceiling (ECMP over multiple connections with TGW to exceed it); **MTU/MSS clamping**, because IPsec overhead means 1500-byte packets fragment and the symptom is the classic PMTU blackhole from N1.6 — SSH connects and then freezes on a large output; and DPD/rekey settings mismatching between vendors causing periodic drops.

**A3.12 — Direct Connect: VIFs, LAG, and why you still want VPN backup**

The VPN/DX comparison is N10.6. AWS specifics:

- **Virtual interfaces**: a **private VIF** reaches one VGW or a Direct Connect gateway (and thence VPCs); a **transit VIF** attaches to Transit Gateway, which is how you reach many VPCs without a VIF per VPC; a **public VIF** reaches AWS public service endpoints (S3, DynamoDB) over the circuit rather than the internet.
- **Direct Connect Gateway** decouples the circuit from the region — one DX can reach VPCs in multiple regions and multiple accounts.
- **LAG** aggregates multiple physical connections into one logical link for bandwidth and resilience, but only within the same location and device.

**Why you still want a VPN backup, said properly:** a single DX connection is a single circuit, through a single provider, to a single DX location, terminating on a single router. Fibre gets cut; providers have outages; devices fail; and maintenance windows are the provider's, not yours. Real resilience is either two circuits at two DX locations with diverse providers — expensive and slow to provision — or a VPN over the internet as backup, which is cheap, quick, and gives you *something* when the circuit is down. With BGP, failover is automatic; you influence path preference so DX wins when it's up.

The two additional points: **DX is not encrypted** — it's a private circuit, not a secure one — so if the compliance requirement is encryption in transit, you run a VPN over the DX or use MACsec. And **lead times are weeks to months**, so DX is a planning decision, never an incident response.

**A3.13 — TGW route tables and attachment propagation**

Two separable concepts, and conflating them is the usual source of confusion:

- **Association** — which TGW route table an attachment *uses for its outbound lookups*. Each attachment associates with exactly one.
- **Propagation** — which route tables *learn* an attachment's CIDRs. An attachment can propagate into many tables.

That separation is what makes segmentation possible. The canonical design:

| Route table | Associated attachments | Propagations received |
|---|---|---|
| `prod` | prod VPCs | prod VPCs, shared services, on-prem |
| `dev` | dev VPCs | dev VPCs, shared services |
| `shared` | shared services VPC | prod and dev VPCs |
| `onprem` | VPN / DX attachment | prod VPCs only |

Prod and dev cannot reach each other because neither's route table has learned the other's routes — enforced in routing, not in security groups, so no SG mistake can undo it.

Details worth having: routes can be **static as well as propagated**, and static wins; **appliance mode** on an attachment keeps flows symmetric through an inspection appliance, and without it stateful firewalls drop return traffic that arrives via a different AZ — a genuinely obscure failure that looks like random connection drops; **TGW is regional**, with **inter-region peering** for cross-region; and there's **no transitive routing through a peering attachment to a third TGW**. Also, TGW attachments consume a subnet IP per AZ, and traffic crossing AZs within TGW incurs charges.

**A3.14 — Hybrid DNS: Resolver endpoints and forwarding rules**

Two directions, and being crisp about which is which is the test:

- **Inbound endpoint** — ENIs in your VPC that **on-prem DNS servers forward queries to**, so on-prem can resolve AWS private zones (`*.internal.acme.com`, RDS endpoints, PrivateLink names).
- **Outbound endpoint** — ENIs your VPC uses to **send queries to on-prem resolvers**, driven by **forwarding rules** that match a domain and specify target IPs, so AWS workloads can resolve on-prem names.

Rules are shareable across accounts via **RAM**, which is the scaling mechanism: the network account owns the rules and shares them, rather than every VPC configuring its own.

Design points: put endpoints in **at least two AZs** — they're ENIs and they fail with their AZ. There's a **queries-per-second limit per endpoint IP** (~10k) that becomes a real constraint for a big EKS estate. Forwarding rules are matched **most-specific-first**, and a `.` catch-all rule sending everything on-prem is a common misconfiguration that breaks resolution of AWS service endpoints in ways that look like service outages. And **conditional forwarding must be configured on both sides** — the on-prem server needs a conditional forwarder for the AWS zone pointing at the inbound endpoint IPs, or you'll have built half a solution and be debugging one direction.

**A3.15 — Debugging on-prem to AWS connectivity across the full path**

The value of a good answer here is a *method* that eliminates layers in order, rather than a list of things to check (T1.1 in the Troubleshooting domain is the general form).

1. **Establish the scope precisely.** One host or all? One port or all? One direction? Did it ever work? What changed? "All traffic from one subnet stopped" and "one port from everywhere stopped" have almost disjoint cause sets.
2. **Name resolution first**, because DNS failure impersonates every other failure. Resolve the target from both sides. Is the answer a private IP or a public one? A hybrid DNS misconfiguration (A3.14) resolving an internal name to a public endpoint produces "connectivity" that is actually going out to the internet and being blocked — and the packet capture looks bizarre until you spot it.
3. **Tunnel/circuit state.** VPN `TunnelState` per tunnel, DX connection and BGP session state. Both tunnels, not one.
4. **Routing, both directions.** Does on-prem have a route to the VPC CIDR? Does the VPC route table have a route back via the VGW/TGW? Is it propagated into the *associated* TGW route table (A3.13)? **Return-path routing is the most common single cause** and the easiest to miss, because the outbound path looks perfect.
5. **AWS filtering.** SGs, then NACLs — and check the ephemeral range on NACLs (A3.2). **Reachability Analyzer** answers this statically in seconds and is underused.
6. **Flow logs** (A3.5) to prove whether packets arrived and what happened: `REJECT` is a filtering answer, `ACCEPT` moves you to the application, nothing at all sends you back to routing.
7. **Application layer**: is it listening, on the right interface, and is TLS/certificate validation the actual failure (N7)?

The overall discipline: **prove each layer before moving up**, and prefer evidence that distinguishes hypotheses over evidence that confirms one. The asymmetric cases — works one way, or works for small packets only — are the tell: asymmetric routing (A3.13 appliance mode) and MTU/MSS (N1.6, A3.11) respectively.

**A3.16 — Overlapping on-prem and AWS address space**

You cannot route between overlapping ranges; the routing table has no way to disambiguate (N2.5). The options, worst to best:

1. **Re-IP one side.** Correct, permanent, and expensive — a project measured in months if the overlapping side is a live on-prem estate. Usually the right long-term answer and almost never the immediate one.
2. **NAT one side.** Present the overlapping network behind a non-overlapping translation range — commonly a private NAT gateway or an on-prem firewall doing bidirectional NAT. Works, but application traffic now sees translated addresses, so anything embedding IPs (some legacy protocols, SIP, certain database clustering) breaks, and troubleshooting gets materially harder because the address you see isn't the address that sent it.
3. **PrivateLink for service-level exposure.** Sidesteps routing entirely: you expose a specific service endpoint rather than connecting networks, so overlap is irrelevant. This is the best answer when the actual requirement is "these three services need to talk", which it usually is — people ask for network connectivity when they need service connectivity.
4. **Add a secondary, non-overlapping CIDR to the VPC** and place the resources that need hybrid reachability there. Partial, but often the pragmatic bridge.

Prevention is the real answer (A3.8, A3.9), and the acquisition scenario is worth naming as the case where prevention was never available to you — inheriting a `10.0.0.0/8` estate that collides with yours is common, and PrivateLink plus a NAT bridge while a re-IP programme runs is the standard shape of the answer.

---

## A4. Compute — T1

**A4.1 — Launching and configuring EC2**

The components and what each is for: an **AMI** (the base image — ideally yours, A4.6), an **instance profile** (A2.6, never keys), **user data** (cloud-init on first boot), **EBS volumes** (root plus data, encrypted by default via the account-level EBS encryption setting), a **security group**, a **subnet** that determines the AZ, and **tags**, which are how the instance gets attributed for cost and found by automation.

In production this is a **launch template**, not console clicks, and the instance is launched by an ASG (A4.3) — a hand-launched instance is a pet that will be forgotten and unpatched.

Points that read as experience:

- **User data runs once on first boot by default** and its output goes to `/var/log/cloud-init-output.log`. When an instance comes up healthy but wrong, that's the first file to read. Long user-data scripts are a smell — they mean you're building the machine at boot time, which is slow and non-deterministic (A4.6).
- **Enable IMDSv2 as required** in the launch template (A2.6).
- **Instance store vs EBS**: instance-store volumes vanish on stop or termination, which is fine for scratch and catastrophic for anything else.
- **The root volume's `DeleteOnTermination` defaults to true, attached volumes default to false** — so terminating instances leaves orphaned EBS volumes accumulating cost, which is a reliable finding in any cost audit (A12.3).

**A4.2 — Choosing an instance family**

Reason from the bottleneck, and say which resource you expect to saturate first:

- **C** (compute) — CPU-bound: encoding, batch processing, CI runners, some model inference.
- **M** (general) — balanced; the sensible default when you don't yet know.
- **R / X** (memory) — caches, in-memory databases, JVM heaps, Spark executors.
- **I / D** (storage) — high local NVMe IOPS: NoSQL nodes, data-heavy scratch.
- **G / P / Inf / Trn** (accelerated) — GPU/accelerator workloads. For AI platform work this is where the specifics matter: memory *per accelerator* and interconnect bandwidth usually bind before FLOPs, and the availability and quota constraints are as much a design factor as the price.
- **T** (burstable) — CPU credits, not guaranteed CPU.

The judgement points:

- **The T-family trap**: T instances accrue credits and throttle when exhausted. The symptom is an application that's fine for weeks and then becomes inexplicably slow under sustained load, with CPU pinned at a low ceiling. Fine for dev and idle services; wrong for anything with a sustained baseline. **Unlimited mode** silently converts the problem into a bill.
- **Graviton (`g` suffix)** is typically 20–40% better price/performance and should be the default question — the constraint is whether your dependencies have arm64 builds, which for containerised workloads is usually a multi-arch build away (Docker domain).
- **Network and EBS bandwidth scale with instance size**, so a small instance can be network-bound long before CPU-bound — the reason "we sized on CPU and it's still slow" happens.
- **Right-size from data, not from the spec sheet.** Compute Optimizer plus actual utilisation, and remember CloudWatch doesn't report memory without the agent (A9.3), so memory-driven sizing decisions are often made blind.

**A4.3 — ASGs, launch templates, scaling policies**

A **launch template** (versioned; prefer it over the legacy launch configuration) defines *what* to launch. The **ASG** defines *how many, where, and when*: min/max/desired, subnets across multiple AZs, health check type, and policies.

Scaling policy types:

- **Target tracking** — "keep average CPU at 60%". The default choice: simplest, self-tuning, and it handles scale-in as well.
- **Step scaling** — different responses at different alarm thresholds. Use when the reaction needs to be non-linear.
- **Scheduled** — known patterns (business hours, batch windows). Underused, and the cheapest win in non-prod.
- **Predictive** — ML-based forecast, useful for regular daily cycles with long warm-up times.

What separates a real answer: **scale on the metric that reflects the bottleneck**. CPU is the default and frequently wrong — for a queue worker the right metric is queue depth per instance (backlog per capacity unit), for a web tier it's often request count per target or p99 latency. Scaling a memory-bound service on CPU means it never scales until it's already failing.

Also: **warm-up and cooldown** matter — if an instance takes four minutes to be useful and your alarm period is one minute, you'll over-scale badly and then thrash. **Instance refresh** is the mechanism for rolling out a new AMI with a minimum healthy percentage. **Mixed instance policies with multiple types and AZs** are what make Spot viable (A4.5) and also protect against a single instance type being unavailable in an AZ — a real capacity event, not a theoretical one.

**A4.4 — Health checks and instance replacement**

Two check types, and the difference is the whole item:

- **EC2 health checks** — only the hypervisor's view: is the instance running and passing system/instance status checks. **An instance whose application has crashed is perfectly healthy by this measure**, so an ASG using EC2 checks alone will happily keep a fleet of running instances serving nothing.
- **ELB health checks** — the load balancer's application-level probe. This is what you want in almost every case: the ASG replaces instances the load balancer has judged unfit.

Behaviour: unhealthy → terminated → new instance launched to restore desired capacity. **Health check grace period** suppresses checks during boot; set too short, the ASG kills instances mid-startup and you get an infinite replacement loop that looks like a crash-loop and costs money all night. That's the classic failure and worth naming.

Further points: **failing checks should reflect the service's real health** — a health endpoint that returns 200 whenever the process is up (rather than checking its dependencies) hides failure, while one that fails on any downstream blip causes a cascading fleet replacement during a transient dependency outage. That tension is the interesting part: health checks that are too shallow don't detect failure, too deep and they amplify it. The usual resolution is a shallow liveness check for replacement decisions and a deeper readiness check for traffic decisions, which is the same distinction Kubernetes makes explicit. **Termination protection during scale-in**, `standby` state for debugging without the ASG replacing your instance, and **lifecycle hooks** for graceful connection draining round it out.

**A4.5 — Spot, On-Demand, Reserved, Savings Plans**

- **On-Demand** — no commitment, highest rate. The baseline for unpredictable or short-lived work.
- **Reserved Instances** — 1 or 3 year commitment to a specific configuration; Standard RIs are cheapest but rigid, Convertible allows exchange. Largely superseded by Savings Plans for compute.
- **Savings Plans** — commit to a dollar-per-hour spend for 1 or 3 years. **Compute Savings Plans** apply across instance family, region, and to Fargate and Lambda — far more flexible. **EC2 Instance Savings Plans** are cheaper but pin you to a family in a region.
- **Spot** — spare capacity at up to ~90% off, **reclaimable with a two-minute notice**.

Where Spot is safe: work that is **interrupt-tolerant** — stateless workers pulling from a queue, CI runners, batch and ETL, and Kubernetes workloads with pod disruption budgets and multiple instance types. Where it isn't: anything stateful without fast rebuild, anything with a strict deadline and no fallback, and singleton services.

The practical detail that makes Spot work rather than merely cheap: **diversify across many instance types and AZs**, use `capacity-optimized` allocation rather than `lowest-price`, and **handle the interruption notice** — drain connections, checkpoint, cordon the node. A workload that ignores the two-minute warning will lose in-flight work, and then someone concludes "Spot is unreliable" when the application was.

The commitment reasoning: commit to the **trough of your steady-state usage**, not the average and definitely not the peak — unused commitment is pure waste, and the whole point of the discount evaporates if you over-commit. Layer it: Savings Plan for the baseline, On-Demand for the variable band, Spot for anything interruptible (A12.5).

**A4.6 — Golden AMI pipeline**

A pipeline (Packer or EC2 Image Builder) that takes a base AMI, applies patches, the agent set (CloudWatch, SSM, security tooling), hardening (CIS benchmark), and the runtime, then **tests the result** and publishes a versioned AMI shared to the accounts that need it.

Why bother:

- **Boot time.** Building at boot with a long user-data script means minutes to useful capacity, which directly undermines autoscaling responsiveness — you can't scale out fast enough to absorb a spike.
- **Determinism.** A user-data script that `apt-get install`s at boot produces a different machine every time it runs, and eventually a broken one when an upstream package changes or a repo is unavailable. **The instance that failed to launch at 3am because a package mirror was down** is the story that sells this.
- **Patching becomes a deploy.** Instead of patching live instances in place, you build a new AMI and roll the fleet through an instance refresh. Immutable infrastructure — the same argument as container images.
- **Auditability and rollback.** A known artefact with a version, a manifest, and a scan result, and the previous version is still there.

The operational parts people miss: **AMIs are regional**, so multi-region needs copies (and re-encryption if using CMKs, A10.13); **deprecation and cleanup** matter because old AMIs and their snapshots accumulate real cost; sharing cross-account requires the KMS key to be shared too if encrypted; and the pipeline needs a **test stage** — an AMI that boots but whose agent doesn't start is worse than no pipeline, because now every instance is broken identically.

**A4.7 — Writing a Lambda and configuring it**

The moving parts: handler code, **runtime**, **memory** (which also determines CPU allocation proportionally — this is the non-obvious one), **timeout**, **execution role**, **environment variables**, and a **trigger** (API Gateway, EventBridge, SQS, S3, ALB, Kinesis).

```python
import json, boto3
s3 = boto3.client("s3")            # client created outside the handler:
                                    # reused across warm invocations
def handler(event, context):
    for record in event["Records"]:
        key = record["s3"]["object"]["key"]
        ...
    return {"statusCode": 200, "body": json.dumps({"ok": True})}
```

Configuration judgement:

- **Memory is the performance dial.** CPU scales with it, so a CPU-bound function at 512 MB may be *cheaper* at 1769 MB because it finishes disproportionately faster. Tune empirically (Lambda Power Tuning) rather than defaulting to 128 MB.
- **Timeout should reflect the work, and be shorter than the caller's timeout.** A 15-minute timeout on a function invoked synchronously behind API Gateway is meaningless — API Gateway caps at 29 seconds — and it turns a fast failure into a slow one.
- **Least-privilege execution role** (A2.2), and remember the managed `AWSLambdaBasicExecutionRole` only covers logs.
- **Retry semantics differ by trigger and this catches people out**: asynchronous invocations retry twice by default; SQS retries per the queue's visibility timeout and redrive policy (A13.1); stream sources (Kinesis, DynamoDB Streams) **retry the batch until success or expiry and block the shard while doing so** — one poison-pill record halts the whole shard. Configure a DLQ or on-failure destination, and set `BisectBatchOnFunctionError` / `MaximumRetryAttempts` for streams.

**A4.8 — Cold starts, concurrency limits, VPC tradeoffs**

**Cold start** = the initialisation of a new execution environment: download code, start the runtime, run initialisation code outside the handler. Magnitude depends heavily on runtime (Go and Python at the low end, JVM and .NET at the high end) and on package size and init work. Mitigations: keep the deployment package small, do heavy init once outside the handler, use **provisioned concurrency** for latency-sensitive paths, and consider SnapStart for JVM. State the tradeoff: provisioned concurrency costs money continuously, so it's for user-facing p99 requirements, not for a nightly job.

**Concurrency**: the account has a regional limit (1000 by default, raiseable). **Reserved concurrency** guarantees a function a slice *and* caps it — both effects, which is the useful bit: reserving concurrency on a low-priority function protects the rest of the account from it, and capping a function protects a downstream database from being overwhelmed by unbounded scale-out. **Throttling manifests as `429`/`TooManyRequestsException`**, and for asynchronous invocations it's retried silently, so the symptom is latency and eventual loss rather than an obvious error.

**VPC attachment**: now uses shared ENIs created at function-configuration time rather than per-execution, so the historic multi-second VPC cold-start penalty is largely gone — worth saying, because plenty of interviewers still expect the old answer, and demonstrating you know it changed is a positive signal. What remains true: a **VPC-attached Lambda has no internet access without a NAT gateway** (or endpoints), which surprises people whose function suddenly can't reach a third-party API; and Lambda consumes **subnet IPs**, so it competes with everything else for address space (A3.8).

The overarching concurrency risk to name: **Lambda scales faster than most things behind it.** A function that opens a database connection per invocation will exhaust an RDS connection limit almost immediately at scale — the fix is RDS Proxy or a connection-less data access pattern, and this is one of the most common real Lambda incidents.

**A4.9 — SSM: Session Manager, Run Command, Patch Manager**

- **Session Manager** — shell access without inbound ports or keys (A3.7).
- **Run Command** — execute a document across a targeted fleet (by tag, by resource group), with rate control and output to S3/CloudWatch. The tool for "run this on all 200 instances" without SSH looping, and the audit trail is automatic.
- **Patch Manager** — patch baselines defining which patches are approved and after what auto-approval delay, with maintenance windows for when they apply and compliance reporting on what's actually patched.

Prerequisites are the same for all three and are the usual cause of "SSM doesn't work": the agent must be running, the instance profile needs `AmazonSSMManagedInstanceCore`, and there must be a network path to the three SSM endpoints (A3.7). `aws ssm describe-instance-information` is the check — if the instance isn't listed, nothing else will work.

Also worth naming: **Parameter Store is part of SSM** (A10.20), **State Manager** for continuous configuration enforcement, **Automation documents** for multi-step runbooks — a genuinely good way to make an incident runbook executable rather than a wiki page — and **Inventory** for software inventory across a fleet.

The mature position: Patch Manager is the right answer for long-lived instances, but for anything containerised or ASG-backed, patching means **rebuilding the AMI and rolling the fleet** (A4.6), not patching in place. Say which model you're in.

---

## A5. Containers — T1 (see also the Containers / Kubernetes domains)

**A5.1 — ECR: lifecycle policies, scanning, cross-account pull**

```bash
aws ecr get-login-password --region eu-west-1 \
  | docker login --username AWS --password-stdin 111122223333.dkr.ecr.eu-west-1.amazonaws.com
docker push 111122223333.dkr.ecr.eu-west-1.amazonaws.com/payments-api:1.4.2
```

- **Lifecycle policies** expire images by count or age, usually with a rule that keeps tagged releases and aggressively expires untagged layers. Without them, ECR grows without bound and quietly becomes a top-ten line item — and untagged images from a busy CI pipeline are the bulk of it.
- **Scanning**: basic (on push, CVE database) or **enhanced** via Inspector (continuous rescanning as new CVEs are published, which matters because an image that was clean at build time isn't clean forever). Wire findings into Security Hub (A10.25) rather than a dashboard (A10.29).
- **Cross-account pull** needs a **repository policy** (a resource-based policy, A2.1) allowing the other account's principals `ecr:BatchGetImage` and `ecr:GetDownloadUrlForLayer`, *plus* `ecr:GetAuthorizationToken` in the pulling account's IAM. The two-part requirement is where people get stuck.
- **Immutable tags** are the setting to enable: they prevent `:latest`-style mutation and make a deployed digest a reliable record of what's running. Referencing images by digest rather than tag in production is the stronger version of the same idea.
- **Pull-through cache** for upstream registries avoids Docker Hub rate limits, which is a real CI failure mode.
- Cross-region replication for multi-region deploys, and note images are stored in S3 — so the S3 gateway endpoint matters for pull cost (A3.3).

**A5.2 — ECS task definition and service**

A **task definition** is the immutable, versioned template: container image, CPU/memory (at both task and container level), port mappings, environment variables, **secrets** referenced from Secrets Manager/Parameter Store (A10.21), log configuration (`awslogs` driver), the **task role** (the application's identity) and the **execution role** (what the ECS agent uses to pull the image and fetch secrets).

**The task role vs execution role distinction is the most commonly confused thing in ECS** and worth being crisp about: the execution role is used *before* your container runs, to pull from ECR and resolve secrets; the task role is what your application code uses to call AWS. A task that can't start with an image-pull error is an execution-role problem; a task that starts and then gets AccessDenied from S3 is a task-role problem. That single distinction resolves most ECS support tickets.

A **service** maintains N copies of a task, registers them with a target group, handles rolling deployment, and integrates with autoscaling. Key settings: `minimumHealthyPercent` / `maximumPercent` (which together determine whether a deployment can proceed without spare capacity), health check grace period, and the deployment circuit breaker with rollback.

**A5.3 — Fargate vs EC2 launch type**

**Fargate** — no instances to manage, patch, or scale. Per-task billing, strong task-level isolation. Costs more per unit of compute, has fixed CPU/memory combinations, no GPU support, no daemonset-style sidecars on the host, limited ephemeral storage, and no control over the underlying host (so no privileged containers, no custom kernel parameters).

**EC2** — you own the capacity. Cheaper at sustained high utilisation, especially with Spot or Savings Plans; gives GPU, larger and arbitrary instance shapes, host-level agents, and bin-packing efficiency. In exchange you own patching, scaling the cluster, and capacity headroom.

The decision framing: **Fargate's premium buys you the elimination of a whole operational category**, and for a small team that's usually the right trade — the "expensive" comparison ignores the engineer-time and the fact that EC2 capacity is rarely 100% utilised, so you're paying for headroom either way. EC2 wins on sustained, predictable, high-utilisation workloads, anything needing GPUs, and anywhere you've already got the operational machinery. State it as: cost per task favours EC2 at high utilisation; total cost of ownership favours Fargate until you're big enough that the delta funds the team.

**A5.4 — Deploy, roll back, and debug a task that won't start**

Deployment: register a new task definition revision, update the service, ECS rolls tasks respecting the min/max healthy percentages, target group health checks gate the cutover, and the **deployment circuit breaker** automatically rolls back on repeated failures. Rollback is updating the service back to the previous revision — which is why immutable, versioned task definitions matter.

Debugging a task that won't start, in the order the failure occurs:

1. **`aws ecs describe-tasks`** and read `stoppedReason` and the container-level `reason`. This is the single most informative field and people skip it.
2. **Image pull failures** — `CannotPullContainerError`. Execution role permissions, no route to ECR (needs endpoints or NAT, A3.3), or a wrong tag/architecture. **arm64 image on an x86 task** is a nastily common one with a confusing error.
3. **Secrets resolution failures** — execution role lacks `secretsmanager:GetSecretValue` or `kms:Decrypt` (A10.21, A10.4). Task never starts, error mentions the secret ARN.
4. **The container starts and exits immediately** — `exitCode`. Check CloudWatch Logs; if there are no logs at all, the log configuration itself failed (log group missing and execution role lacking `logs:CreateLogGroup`), which produces a genuinely opaque failure where the cause is invisible precisely because logging is what broke.
5. **Task starts, fails health checks, gets killed and retried** — the loop. Is the health check path right, is the grace period long enough, is the container listening on the mapped port and on `0.0.0.0` rather than `127.0.0.1`?
6. **Capacity**: on EC2 launch type, "unable to place task" means no instance satisfies the CPU/memory/port/ENI constraints. On Fargate, check subnet IP availability and quotas.

**ECS Exec** (`aws ecs execute-command`) gets a shell into a running task, which turns the "start, exit, no logs" case from guesswork into inspection.

**A5.5 — EKS: managed node groups vs Fargate vs Karpenter**

- **Managed node groups** — AWS-managed ASGs of EC2 nodes with coordinated draining on update. Predictable, supports GPUs and daemonsets, and it's the conventional default. Scaling is via Cluster Autoscaler, which is ASG-based and therefore constrained to the instance types in each group.
- **Fargate profiles** — a pod per micro-VM, no nodes. Good isolation and zero node management, but: no daemonsets (so log and monitoring agents must be sidecars), no GPUs, no privileged pods, restrictive storage, and slower pod start. Practically, most clusters end up using it for a subset — or not at all.
- **Karpenter** — provisions nodes directly from pending pods' actual requirements, choosing instance types itself from a broad set. Faster scale-up, better bin-packing, straightforward Spot diversification (A4.5), and consolidation that actively repacks and removes underutilised nodes.

The judgement: **Karpenter is now the default recommendation for a cluster of any size** because Cluster Autoscaler's per-node-group model forces you to predefine instance shapes, which is exactly the decision Karpenter removes — and the consolidation behaviour is a genuine, measurable cost win (a good A12.7 story). The cost is that node lifecycle is more dynamic, so workloads must actually tolerate disruption: PDBs, correct termination handling, and `do-not-disrupt` annotations where genuinely needed. If your workloads can't tolerate a node going away, Karpenter will surface that fact quickly, which is either a feature or an incident depending on when you find out.

**A5.6 — AWS Load Balancer Controller**

The controller watches Kubernetes resources and provisions AWS load balancers: an **Ingress** produces an ALB, a **Service of type LoadBalancer** with the right annotations produces an NLB.

The important concept is **target type**:

- **`instance` mode** — traffic goes to a NodePort on the node, then kube-proxy forwards to a pod. An extra hop, and the source IP is obscured unless you handle it.
- **`ip` mode** — the ALB targets **pod IPs directly**, which is possible because the VPC CNI gives pods real VPC IPs (A5.7). Fewer hops, faster deregistration, and it's required for Fargate. This is the one to use, and knowing *why* it's possible ties it back to the CNI.

Setup requires an IAM policy attached via IRSA (A2.7), correctly tagged subnets (`kubernetes.io/role/elb` for public, `internal-elb` for private) — **missing subnet tags is the single most common reason an Ingress silently never provisions**, with the error only visible in the controller logs. Also worth knowing: `IngressGroup` lets multiple Ingress resources share one ALB, which matters because an ALB per service gets expensive quickly; and **pod readiness gates** ensure a pod isn't considered ready until it's registered and healthy in the target group, without which rolling deployments drop connections.

**A5.7 — VPC CNI and ENI-per-pod IP exhaustion**

The AWS VPC CNI gives every pod a **real VPC IP address** from the subnet, which is why security groups, flow logs, and direct ALB targeting all work naturally at pod level (N10.7).

The consequence: **pod density per node is bounded by ENIs and IPs per ENI, which are fixed per instance type** — not by CPU or memory. A `t3.medium` supports 17 pods regardless of how idle it is. The failure signature is distinctive and worth describing precisely: **pods stuck `Pending`, the node has abundant free CPU and memory, and the event says no IP addresses are available.** People chase resource requests for hours because every dashboard says the node is idle.

Two exhaustion levels, and distinguishing them is the expert bit: **per-node** (ENI limits — fix with prefix delegation, which assigns /28 prefixes rather than individual IPs and raises density dramatically, or with bigger instances) and **subnet-wide** (the subnet's CIDR is genuinely full — fix by sizing correctly up front, N2.4, adding secondary CIDRs, or using CNI custom networking to place pods in a separate, larger address range).

Also worth naming: the WARM_ENI/WARM_IP target settings mean nodes pre-allocate addresses, so **actual consumption exceeds running pod count** — a subnet can exhaust while apparently having spare capacity. And alternative CNIs (Calico in overlay mode) trade the VPC-native benefits for address efficiency.

**A5.8 — EKS authentication: aws-auth vs access entries**

Authentication is IAM; **authorisation is Kubernetes RBAC**. The mapping between them is the interesting part.

- **`aws-auth` ConfigMap** (the legacy mechanism) — a ConfigMap in `kube-system` mapping IAM role/user ARNs to Kubernetes users and groups. Its problems are structural: it's a single ConfigMap, so editing it is a race between teams; **a malformed edit can lock every principal out of the cluster** with no IAM-side recovery, which is a genuinely bad afternoon; and it's not manageable through IAM or auditable as an AWS resource.
- **Access entries** (the current mechanism) — an EKS API for mapping principals to access policies or to RBAC groups. Managed through IAM/EKS APIs, expressible in Terraform, auditable in CloudTrail, and no shared-ConfigMap failure mode. Cluster access config can be `API`, `CONFIG_MAP`, or `API_AND_CONFIG_MAP` for migration.

Use access entries for anything new and migrate existing clusters. The historical detail worth knowing because it still bites: **the IAM principal that created the cluster had implicit, permanent `cluster-admin`** and was invisible in `aws-auth` — so clusters created by a CI role were administrable by anyone who could assume that role, unrecorded. Access entries make that principal explicit and removable.

---

## A6. Storage — T1

**A6.1 — S3: bucket policies, versioning, lifecycle**

- **Bucket policy** — resource-based (A2.1). Common patterns: deny non-TLS (`aws:SecureTransport: false`), deny unencrypted uploads, restrict to `aws:PrincipalOrgID`, restrict to a VPC endpoint (`aws:SourceVpce`, A3.3).
- **Versioning** — every overwrite and delete creates a version; a delete places a **delete marker** rather than removing data. This is your protection against both accidental deletion and ransomware, and it's the prerequisite for replication and Object Lock. It's off by default and cannot be switched off once on (only suspended).
- **Lifecycle rules** — transition between storage classes and expire objects on age. The two rules people forget: **expire noncurrent versions** and **abort incomplete multipart uploads**. Both accumulate invisible cost — incomplete multipart uploads in particular don't appear in the object listing at all, so a bucket can be billed for terabytes that `aws s3 ls` says don't exist. That's a reliable finding in a cost audit and a satisfying one to explain (A12.3).

**A6.2 — Storage classes for an access pattern**

| Class | Use when | Watch out for |
|---|---|---|
| Standard | Frequent access, unpredictable | — |
| Intelligent-Tiering | Unknown or changing patterns | Small per-object monitoring fee; poor fit for many tiny objects |
| Standard-IA | Infrequent, needs millisecond access | 30-day minimum, 128 KB minimum billable size, retrieval charge |
| One Zone-IA | Reproducible data, infrequent access | Single AZ — data is lost if that AZ is lost |
| Glacier Instant Retrieval | Archive, occasional immediate access | 90-day minimum |
| Glacier Flexible Retrieval | Archive, minutes-to-hours retrieval acceptable | 90-day minimum, retrieval time and cost |
| Glacier Deep Archive | Long-term compliance retention | 180-day minimum, up to 12h retrieval |

The reasoning to demonstrate: **the minimum storage durations and per-request retrieval charges dominate the decision for small or short-lived objects.** Transitioning millions of small objects to IA can cost *more* than leaving them in Standard, because of the 128 KB minimum billable size and the per-object transition request charge. Intelligent-Tiering is the right default when the access pattern is genuinely unknown, and specifically wrong for large numbers of tiny objects.

The other point: choose based on **retrieval time requirement first, then cost**. A cheap class that takes twelve hours to retrieve is useless if it holds your backups and your RTO is four hours (A11.1) — a mismatch that only surfaces during a real recovery.

**A6.3 — S3 encryption options**

- **SSE-S3 (AES256)** — AWS-managed keys, free, no configuration. The default; all new objects are encrypted at rest regardless.
- **SSE-KMS** — a KMS key (AWS-managed `aws/s3` or a CMK). Gives you a **key policy as a second authorisation layer**, and CloudTrail records every decrypt (A10.16). The reason to pay for it: you can deny access at the key even if bucket policy is wrong, and you get an audit trail of data access.
- **DSSE-KMS** — dual-layer, for specific regulatory requirements.
- **SSE-C** — you supply the key on every request; AWS never stores it. If you lose it, the data is gone. Rare, and usually a sign the requirement should have been solved elsewhere.

**S3 Bucket Keys** are the operationally important one: without them, **SSE-KMS makes a KMS API call per object operation**, which at scale is both a significant cost (A10.14) and a **KMS quota risk** (A10.15). Bucket keys generate a short-lived bucket-level key that reduces KMS requests by up to 99%. Enable them by default; the only reason not to is if you need per-object encryption-context granularity in the audit trail.

The workload to flag: a data pipeline reading millions of small SSE-KMS objects can generate more spend on KMS requests than on S3 storage, and can hit KMS throttling that presents as intermittent read failures with no obvious cause.

**A6.4 — Block Public Access, and how buckets get exposed**

**Block Public Access** has four settings (block new public ACLs, ignore existing public ACLs, block new public bucket policies, restrict public bucket policies) and can be applied at bucket *and* account level. **Enable all four at account level and enforce it with an SCP.** Account-level BPA overrides bucket-level configuration, which is what makes it a real control rather than a default.

How buckets get exposed by accident, which is the substance of the question:

- **A bucket policy with `"Principal": "*"`** and no conditions — often written to make something work quickly and never narrowed.
- **Legacy ACLs**, particularly `AuthenticatedUsers`, which many people read as "users in my account" when it actually means **any authenticated AWS user in the world**. That misreading is the classic. Object Ownership set to "bucket owner enforced" disables ACLs entirely and is the right default.
- **A policy that's over-broad rather than public** — granting to `arn:aws:iam::*:root`, or to a partner account long after the partnership ended.
- **Presigned URLs with excessive expiry** (A6.6) — not a bucket exposure, but the same outcome.
- **Static website hosting** deliberately made public and then reused for something else.

Detection: **IAM Access Analyzer external-access findings** (A2.10) is the systematic answer, plus Config rules (A10.24) and Security Hub. The point to make is that prevention (account BPA + SCP) is worth more than detection here, because the detection window on a public bucket is the exposure window.

**A6.5 — Consistency, prefixes, and request-rate scaling**

**S3 is strongly read-after-write consistent** for all operations, including overwrites and deletes, and has been since December 2020. This matters because a large amount of received wisdom — and plenty of interview questions — still assumes eventual consistency and read-after-write only for new objects. Knowing it changed, and roughly when, is a good signal. List operations are consistent too. What remains eventually consistent: cross-region replication, and some metadata like bucket configuration changes.

**Request rates**: 3,500 PUT/COPY/POST/DELETE and 5,500 GET/HEAD per second **per partitioned prefix**, and S3 partitions automatically as load grows. Historically you'd hash-prefix keys to spread load; that's mostly unnecessary now, but the underlying property still applies — sustained heavy traffic concentrated on one prefix can hit `503 SlowDown` while S3 repartitions, which takes time. If you know a workload will be hot from the start, spreading keys across prefixes still helps.

The gotcha: **sequential key names (timestamps, incrementing IDs) concentrate writes on one partition**, which is exactly the pattern log and event pipelines naturally produce. Same shape of problem as a DynamoDB hot partition (A7.6).

**A6.6 — Presigned URLs and the tradeoff**

A presigned URL embeds a signature granting a specific operation on a specific object until an expiry, generated by a principal that already has that permission.

```bash
aws s3 presign s3://acme-reports/2026/q1.pdf --expires-in 300
```

The use case: letting a browser or third party upload or download directly to S3 without proxying bytes through your application, and without giving them credentials. That's a real architectural win — it removes your service from the data path entirely.

The tradeoff, and the parts that make it a security question:

- **The URL is a bearer token.** Anyone who obtains it has that access — and URLs leak through browser history, referrer headers, logs, and chat. **Keep expiry short** (minutes, not days) and treat the URL as a credential.
- **It cannot be revoked.** Once issued, it's valid until it expires; the only ways to invalidate it are deleting the object or removing the *signer's* permission, which is drastic.
- **The URL inherits the signer's permissions**, capped by its own expiry — so a URL signed by an over-privileged role is more dangerous than it looks.
- **A presigned URL signed by an IAM role cannot outlive the role's session credentials**, which is a very common surprise: you set a 7-day expiry, the underlying session expires in an hour, and the URL dies early with a confusing error.
- For uploads, constrain what can be uploaded — presigned **POST** with a policy limiting content-type and size is stronger than a presigned PUT, which accepts anything of any size.

**A6.7 — Cross-region replication**

Requires **versioning on both buckets**, a replication role, and a rule. Options: replicate everything or filtered by prefix/tag, optionally change storage class or ownership, and **Replication Time Control** for a 15-minute SLA with metrics.

Use cases: DR and regional resilience for critical data (A11.2), data residency, latency for geographically distributed readers, and **cross-account replication into a separate backup account** — which is the interesting one, because it's a defence against deletion by a compromised principal in the source account.

The details that matter: replication is **asynchronous**, so there's an RPO measured in seconds to minutes — it is not a synchronous mirror and shouldn't be described as one. **By default, delete markers are not replicated** (you can enable it), which is deliberate and worth understanding: not replicating them means a delete in the source doesn't propagate, which is protective; replicating them makes the destination a true mirror, including mirroring your mistakes. **Existing objects aren't replicated** unless you run batch replication explicitly — enabling CRR and assuming the bucket is now protected is a real and dangerous misconception. And replication needs `kms:Decrypt` on the source key and `kms:Encrypt` on the destination key if either uses SSE-KMS (A10.11).

**A6.8 — EBS volume types, snapshots, restore, resize**

- **gp3** — the default. Baseline 3,000 IOPS and 125 MB/s **independent of size**, with throughput and IOPS provisioned separately. Cheaper than gp2 for equivalent performance; there is essentially no reason to choose gp2 for a new volume.
- **gp2** — legacy; IOPS scale with size (3 per GB), which forced people to over-provision capacity to get performance.
- **io1/io2** — provisioned IOPS for latency-sensitive databases; io2 Block Express for the highest tiers, and io2 supports multi-attach.
- **st1/sc1** — throughput-optimised HDD for large sequential workloads; terrible for random I/O.

**Snapshots** are incremental and stored in S3, but each snapshot is independently restorable — deleting an older snapshot doesn't invalidate newer ones, which people frequently get wrong in both directions. Restore creates a new volume.

The performance trap worth naming: **a volume restored from a snapshot is lazily loaded** — blocks are fetched from S3 on first access, so the volume is slow until it's warmed. During a DR restore this presents as "the database is up but everything is crawling", and if you haven't tested it (A11.8) you'll meet it for the first time during a real recovery. Fast Snapshot Restore removes it, at cost.

**Resize** is `modify-volume` — online, no downtime, but **it only grows the block device; you must then grow the partition and filesystem** (`growpart` then `resize2fs`/`xfs_growfs`). "I resized the volume and the disk is still full" is that missing step. Shrinking isn't supported at all — you create a smaller volume and copy. There's also a cooldown before a volume can be modified again.

**A6.9 — When EFS is right, and when it's a performance trap**

EFS is right when you genuinely need **shared POSIX filesystem semantics across many instances or containers simultaneously** — legacy applications expecting a shared mount, content shared between web servers, home directories, some ML workloads sharing datasets across nodes. It scales capacity automatically, is multi-AZ by default, and integrates with EKS via the CSI driver.

The trap is **per-operation latency**. EFS is NFS over the network: single-operation latency is an order of magnitude worse than local EBS, and workloads that do many small file operations — build directories, `node_modules`, source trees, SQLite databases, anything with heavy metadata operations — perform dramatically worse than people expect. The characteristic report is "it works fine but everything takes ten times longer", with no obvious bottleneck on any dashboard.

The second trap is the **throughput model**. Bursting mode accrues credits proportional to stored data, so a small filesystem gets a small sustained baseline; a workload that runs fine for hours then collapses is usually burst credit exhaustion — structurally identical to the T-instance CPU credit problem (A4.2), and just as puzzling if you don't know to look. Elastic throughput avoids it and costs more per GB transferred.

The decision rule: **if you don't need concurrent shared access, use EBS.** If you need shared object storage rather than a filesystem, use S3. EFS is for the case where the application genuinely requires POSIX semantics on shared storage — and reaching for it because it's convenient is how the performance problem arrives. FSx is the answer for Windows/SMB or high-performance Lustre workloads.

---

## A7. Databases — T2

**A7.1 — RDS multi-AZ and failover behaviour**

Standard multi-AZ maintains a **synchronous standby in another AZ**. The standby serves no traffic — it is not a read replica and cannot be read from. On failure, **the DNS CNAME of the endpoint is repointed** to the promoted standby, typically within 60–120 seconds.

The operational consequences to name:

- **Failover is not zero-downtime.** Connections are dropped and applications must reconnect. An application that caches DNS indefinitely (the JVM's default `networkaddress.cache.ttl` being the notorious case) will keep trying the old IP long after failover completes — which is the single most common reason a "successful" failover looks like an outage (N4.9).
- **Synchronous replication costs write latency**, which is the price of the durability.
- Failover is triggered by AZ failure, instance failure, storage failure, or an instance-type change — and **you can trigger it deliberately with `reboot --force-failover`**, which is how you test it (A11.8).
- **Multi-AZ DB cluster** (three instances, two readable) is the newer variant offering faster failover and readable standbys — worth knowing as it changes the "standby is wasted capacity" objection.

**A7.2 — Read replicas vs multi-AZ**

Different problems, and being clear about it is the whole item:

| | Multi-AZ | Read replica |
|---|---|---|
| Solves | Availability | Read scalability |
| Replication | Synchronous | Asynchronous |
| Readable | No (standard) | Yes |
| Failover | Automatic | Manual promotion |
| Data loss on failover | None | Possible (replica lag) |
| Cross-region | No | Yes |

The confusion is understandable because both are "another copy", and the failure it causes is specific: **promoting a read replica after a primary failure can lose data**, because replication was asynchronous and lag was non-zero. Replicas are a scaling tool that can be pressed into DR service with an accepted RPO — not an HA mechanism.

The application-side point that shows experience: **replica lag means read-after-write inconsistency.** A user updates their profile, the read goes to a replica that hasn't caught up, and they see the old value. Handling that is an application concern — route reads that must be fresh to the writer, or use a session-consistency mechanism. Discovering it in production is a bad way to learn it. Monitor `ReplicaLag` and alarm on it, because a replica that's hours behind is worse than no replica: it's serving stale data while appearing healthy.

**A7.3 — Backups, retention, PITR, and testing a restore**

**Automated backups** take a daily snapshot plus continuous transaction logs, enabling **point-in-time recovery** to any second within the retention window (up to 35 days). **Manual snapshots** persist until you delete them and are the mechanism for longer retention.

The details that bite:

- **Automated backups are deleted when the instance is deleted** unless you take a final snapshot. Deleting an RDS instance without a final snapshot destroys the backups with it — irreversibly.
- **PITR restores create a new instance.** You do not restore in place. So recovery involves a new endpoint and either a DNS change or an application config change, and that step needs to be in the runbook.
- **Restore time scales with database size** and is the thing that determines whether you can actually meet your RTO (A11.1). Nobody knows their real restore time until they've measured it.
- Backups within the retention window are free up to the size of the database; beyond that you pay.
- **Cross-region and cross-account copies** are what protect against a regional event or a compromised account, and copying an encrypted snapshot cross-region requires re-encryption with a key in the target region (A10.13).

**Testing a restore** is the part that matters (A11.8): a scheduled, automated job that restores the latest backup into an isolated environment, runs integrity checks and a representative query, records the wall-clock time, and reports it. The recorded restore duration is your evidence for the RTO. Backups that have never been restored should be described as untested, not as backups.

**A7.4 — Aurora's architecture difference and when it's worth it**

Aurora decouples compute from storage: a **distributed, log-structured storage layer replicating six ways across three AZs**, with quorum-based reads and writes. Instances are stateless compute over that shared volume.

What that buys:

- **Replicas share the storage volume**, so replica lag is typically milliseconds rather than seconds, and adding a replica doesn't copy data.
- **Failover is faster** (usually under 30 seconds) because there's no data to promote — just a new writer over the same storage.
- **Storage auto-scales** to 128 TiB with no volume management.
- Backtrack (MySQL), fast clones for test environments, Global Database for cross-region with sub-second replication, and Serverless v2 for variable workloads.

When it's worth it: read-heavy workloads needing many low-lag replicas, workloads where fast failover materially affects the SLO, environments where fast cloning of production-sized data is valuable, and anything with unpredictable growth.

When it isn't: **Aurora costs more** — both the instance premium and I/O charges, which on a very I/O-heavy workload can be a large and surprising component (the I/O-Optimized configuration exists precisely because of this and is worth modelling). A small, steady, low-traffic database gains little. And you're now on an AWS-specific engine variant — compatible, but not identical, and it constrains portability. State it as: Aurora is the right default for a serious production relational workload on AWS; standard RDS remains defensible for small or cost-sensitive ones.

**A7.5 — Parameter groups and a low-risk engine upgrade**

**Parameter groups** hold engine configuration; **option groups** hold engine features. You cannot modify the default group — create a custom one. Parameters are **static** (require a reboot) or **dynamic** (apply immediately), and a static change sits in `pending-reboot` doing nothing until you reboot, which is a common "I changed it and nothing happened".

A low-risk engine upgrade:

1. **Read the release notes** for breaking changes and deprecated behaviour. Minor versions are usually safe; major versions change query planner behaviour and can regress specific queries badly.
2. **Restore a snapshot into a test instance and upgrade that**, then run the application's test suite and a representative production query workload against it. This is the step that catches the plan regressions.
3. **Check extension and client-driver compatibility** — for Postgres, extension versions are a frequent blocker.
4. **Take a manual snapshot immediately before** — the automated one isn't a substitute for a known, named restore point.
5. **Use a maintenance window**, and know the expected downtime: minor upgrades on multi-AZ can be done with a failover to reduce it; **major version upgrades take the database down for the duration** and are not instantaneous.
6. **Have a rollback plan, and be honest that it's a restore.** You cannot downgrade an engine in place. Rollback means restoring the pre-upgrade snapshot and replaying anything since — which is why the decision to proceed must be made before you start, not halfway through.
7. **Blue/green deployments** for RDS are the modern answer: a synchronised green environment on the new version, switched over in about a minute, with the blue retained for rollback. If it's available for your engine, it changes this from a risky operation to a routine one.

Post-upgrade: **run `ANALYZE`/update statistics**, because a fresh planner with stale statistics produces exactly the mysterious performance regression people blame on the upgrade itself.

**A7.6 — DynamoDB partition keys, hot partitions, capacity modes**

Data is distributed across partitions by a **hash of the partition key**. Throughput is allocated per partition, so **an uneven key distribution concentrates traffic on one partition and you get throttled while total consumed capacity looks comfortably under the provisioned figure.** That gap — throttling at low aggregate utilisation — is the diagnostic signature of a hot partition, and CloudWatch's aggregate metrics actively hide it. Contributor Insights is the tool that shows you the offending key.

Causes: low-cardinality keys (`status`, `tenant_id` with one dominant tenant), sequential keys (dates), or a genuine celebrity item. Fixes: pick a higher-cardinality key, **write-sharding** (append a suffix and scatter/gather on read), or caching in front (DAX) for a hot read.

**Capacity modes:**

- **On-demand** — pay per request, instant scaling, no capacity planning. Best for unpredictable, spiky, or new workloads, and considerably more expensive per request at sustained high volume.
- **Provisioned** — specify RCU/WCU, optionally with auto-scaling. Cheaper at steady, predictable load, and reservable. Auto-scaling reacts in minutes, so it does **not** protect against a sudden spike — that's the tradeoff, and the reason a provisioned table with auto-scaling still throttles during a flash event.

Design points: the schema is driven by access patterns, decided up front — you cannot cheaply add a new access pattern later, unlike SQL. GSIs have their own capacity and **can be throttled independently, which then throttles writes to the base table** — a genuinely non-obvious coupling. Item size limit is 400 KB. And **`Scan` is almost always wrong** in production.

**A7.7 — ElastiCache and the cache invalidation risk**

**Redis vs Memcached**: Redis for data structures, persistence, replication, pub/sub, and clustering; Memcached for a simple multi-threaded key-value cache. Redis is the default choice for almost everything; Valkey is now also offered and is materially cheaper.

Patterns: **cache-aside** (application checks cache, falls back to the database, populates) is the common one; **write-through** keeps the cache current at write cost; **TTL-based expiry** bounds staleness without explicit invalidation.

The risks, which are the substance of the item:

- **Stale data** — the cache and the source of truth disagree because an update path didn't invalidate. Every "why is the old price still showing" bug. Bounded TTLs limit the damage even when invalidation logic is wrong, which is why a TTL is a safety net rather than a substitute for invalidation.
- **Thundering herd / cache stampede** — a popular key expires and hundreds of concurrent requests all miss and hit the database simultaneously. Mitigate with jittered TTLs, request coalescing, or probabilistic early refresh.
- **Cold cache after a restart or failover** is the most under-appreciated: the database has been sized for the *cached* load, and suddenly receives 100% of the traffic. **The cache outage becomes a database outage**, which is the cascading failure people don't plan for. Warm the cache, or ensure the database can survive a cold start.
- **Eviction under memory pressure** silently degrades hit rate — monitor `Evictions` and hit ratio, not just CPU. `maxmemory-policy` choice matters, and `noeviction` turns memory pressure into write errors.

**A7.8 — Rotating database credentials without downtime**

The naive approach — change the password and update the application — has a window where the running application holds the old credential. Two approaches that don't:

**Two-user (alternating) rotation**, which is what Secrets Manager's multi-user rotation strategy implements: maintain two database users. The secret points at user A; rotation changes user B's password, verifies it, then updates the secret to point at B. Applications reading the secret pick up B on their next fetch; A's password is changed on the *following* rotation, by which time nothing is using it. **At no point is a credential in use invalidated**, which is the property that makes it zero-downtime.

**Single-user rotation** is simpler but has a brief window where existing connections hold a now-invalid password; acceptable if the client reconnects and re-fetches on auth failure, and if connections are short-lived.

The implementation points: Secrets Manager rotation runs a Lambda that must reach both the database (VPC-attached, so security group rules) and the Secrets Manager endpoint (NAT or interface endpoint — a rotation Lambda that can't reach the endpoint hangs and rotation silently stops, which you discover during an audit). Applications must **fetch the secret at connection time and handle re-fetch on auth failure**, not cache it at process start — a cached credential defeats the whole mechanism, and this is the most common reason rotation "breaks the app". Cache with a short TTL to avoid hammering the API (A10.14).

The better answer where available: **IAM database authentication** removes passwords entirely — the client requests a short-lived token via IAM. It has connection-rate limits and doesn't suit every workload, but where it fits, rotation stops being a problem you have to solve.

---

## A8. DNS & edge — T1 for Route53, T2 for the rest

DNS mechanics are N4; this section is Route53 configuration and the edge services.

**A8.1 — Hosted zones, records, and subdomain delegation**

A **public hosted zone** is authoritative on the internet; a **private hosted zone** is resolvable only from associated VPCs (A3.6). Creating a zone gives you four NS records — and the zone does nothing until the parent delegates to those nameservers.

**Delegating a subdomain**: create a hosted zone for `dev.acme.com`, take its NS records, and add an `NS` record for `dev` in the parent `acme.com` zone pointing at them. The parent keeps control of the apex; the child zone can live in a different account, which is the pattern for giving teams control of their own subdomain without write access to the production zone. That account-boundary use is the reason this is asked.

Failure modes worth naming: **recreating a hosted zone assigns new nameservers**, so the delegation silently breaks — the zone exists, the records are right, and resolution fails, which is maddening if you don't know to check. **NS TTLs at the parent** mean delegation changes take as long as the parent's TTL to propagate. And a dangling record pointing at a released resource (an S3 bucket name, an ELB hostname) is a **subdomain takeover** risk — someone else claims the resource and now serves content on your domain (see the Security domain).

**A8.2 — Alias records vs CNAMEs**

An **alias** is a Route53-specific record type that points at an AWS resource (ALB, NLB, CloudFront, S3 website, API Gateway, another record in the zone) and resolves to its current addresses.

Why they beat CNAMEs:

- **A CNAME cannot exist at the zone apex.** DNS forbids a CNAME coexisting with other records at a name, and the apex must carry SOA and NS. So `acme.com` → ALB is impossible with a CNAME; alias makes it work. This is the headline reason.
- **Alias queries to AWS targets are free**; CNAME lookups are billed per query.
- **No extra resolution hop** — the alias returns the A/AAAA record directly rather than requiring the client to resolve a second name.
- **Health of the target is tracked automatically** with `evaluate_target_health`.
- The TTL is managed by AWS for the target, so a load balancer's IP changes propagate without you managing TTLs.

The constraint: aliases only point at AWS resources and only within Route53. For an external target you need a CNAME — or the modern workaround for apex records at other providers (ALIAS/ANAME/flattening), which is provider-specific.

**A8.3 — Routing policies**

- **Simple** — one record, one answer set.
- **Weighted** — proportional distribution. The mechanism for canary and gradual migration; setting a weight to zero drains a target.
- **Latency** — routes to the region with lowest measured latency for the client. Note it's *latency*, not geography, and the measurements are AWS's.
- **Failover** — primary/secondary with a health check (A8.4).
- **Geolocation** — by the client's location; used for data residency and content localisation. Needs a default record for unmatched locations, and omitting it means those clients get **no answer at all**.
- **Geoproximity** — geographic with a bias dial to shift traffic between regions.
- **Multivalue answer** — up to eight healthy records returned; a poor man's load balancing with health checking, but the client chooses.

The reasoning to state: **all DNS-based routing is subject to caching and client behaviour** (A8.5). Weighted routing at 90/10 does not mean 90% of requests — it means roughly 90% of *resolutions*, and a client that resolves once and holds the connection for hours skews it arbitrarily. For fine-grained traffic control, a load balancer or service mesh is the right tool; DNS is for coarse-grained, regional decisions.

**A8.4 — Health checks and DNS-based failover**

Route53 health checks come in three kinds: **endpoint** checks (from a distributed set of global checkers), **calculated** checks (boolean combinations of other checks), and **CloudWatch alarm** checks (health derived from a metric, which is how you fail over on a business signal rather than a ping).

Failover routing pairs a primary record with a secondary; when the primary's health check fails, Route53 serves the secondary.

The realities that determine whether this actually works:

- **Failover time is health-check interval × failure threshold, plus TTL, plus client cache.** With a 30-second interval and three failures that's 90 seconds before Route53 even changes the answer, plus the record TTL, plus however long clients hold it. **DNS failover is minutes, not seconds** — if the RTO demands seconds, the answer is a load balancer or Global Accelerator, not DNS (A11.1).
- **Health checkers come from AWS IP ranges globally** and must be allowed through firewalls, and a check against an endpoint that's only reachable privately can't work at all.
- **Check something meaningful.** A check hitting `/` on the load balancer proves the load balancer is up, which is rarely the failure you're worried about. A deep check that exercises the database is more truthful but also fails during transient blips, causing a regional failover you didn't want. That tension is the interesting part — the usual resolution is a check that's deep enough to detect real unavailability but with a threshold that tolerates a brief blip.
- **Test the secondary regularly**, because a failover target that was never exercised is a guess (A11.8).

**A8.5 — Zero-downtime DNS cutover accounting for TTL**

The procedure:

1. **Days ahead, lower the TTL** on the record to something short (60 seconds or less). You must do this at least the *old* TTL in advance — lowering the TTL doesn't help anyone who already cached the record at the old value. This is the step people skip, and it's the whole reason cutovers go wrong.
2. **Verify the new target fully** — it should be serving correctly and warmed before any traffic arrives.
3. **Cut over**, ideally by shifting weights gradually (A8.3) rather than flipping, so you can observe error rates on a small fraction first.
4. **Keep the old target running** — for considerably longer than the TTL suggests. This is the critical point.
5. **Watch traffic to the old target decay**, and only decommission when it reaches zero.
6. **Restore the TTL** afterwards.

The realities to name, because they're what separates a textbook answer from an experienced one: **clients ignore TTLs.** JVM applications with default caching settings hold DNS answers for the process lifetime; some resolvers and libraries have their own caches; connection pools keep long-lived connections open to the old IP regardless of DNS. So "the TTL was 60 seconds, it's been an hour, we can turn it off" is exactly the reasoning that causes the outage. The empirical answer is to **watch actual traffic on the old endpoint rather than reasoning from TTL**, and to keep it alive until observed traffic is genuinely zero — often days.

**A8.6 — ACM certificates: validation and auto-renewal failure modes**

Request a certificate, validate ownership by **DNS** (a CNAME record) or **email**. Always DNS: it's automatable, and it's the only method that supports automatic renewal without human action.

ACM certificates attach to integrated services (ALB, NLB, CloudFront, API Gateway) — **you cannot export the private key** for use on an EC2 instance. That's the main constraint, and the answer for arbitrary servers is ACM Private CA (A10.18) or an external CA.

Renewal is automatic *provided* validation still succeeds — which is where the failure modes live, and this is the substance of the item:

- **The validation CNAME was deleted** after issuance, because someone tidied up an unexplained record. Renewal then fails silently and you find out when the certificate expires. **Leave the validation records in place permanently.**
- **The domain is no longer publicly resolvable**, or the zone was moved/recreated (A8.1).
- **The certificate isn't attached to anything.** ACM only auto-renews certificates in use; an unattached certificate expires.
- Certificates for CloudFront **must be in `us-east-1`**, regardless of where anything else is — a regional gotcha that costs people an hour.

Operationally: **alarm on `DaysToExpiry`** via CloudWatch, and treat certificate expiry as a foreseeable, preventable incident class. It's also worth saying that expiry is one of the highest-frequency causes of self-inflicted outages industry-wide, precisely because it's silent until it isn't (N7).

**A8.7 — CloudFront: origins, behaviours, cache keys, invalidation**

- **Origins** — where content comes from (S3, ALB, any HTTP endpoint). Origin groups give origin failover.
- **Behaviours** — path-pattern rules that select an origin and a policy set. This is how one distribution serves `/api/*` from an ALB and everything else from S3.
- **Cache key** — the set of things that distinguish one cached object from another: path plus whichever headers, query strings, and cookies you include via cache policies.
- **Invalidation** — explicitly purge paths, with a charge beyond a free allowance.

The judgement, which is the whole item: **the cache key determines your hit rate, and getting it wrong is the difference between a CDN and an expensive proxy.** Including all headers and cookies in the cache key means every request is unique and nothing is ever cached — a very common misconfiguration that looks like CloudFront "not working". Include only what genuinely varies the response.

The correspondingly important practice: **prefer versioned object paths over invalidation.** `/static/app.a3f9c2.js` never needs purging — deploy a new filename and the old one ages out. Invalidation is slow (minutes), costs money at volume, and if it's part of your normal deploy process that's a design smell rather than a workflow.

Also: Origin Access Control (OAC) to keep the S3 bucket private so nobody bypasses CloudFront; `Cache-Control` from the origin drives TTLs and is usually the right control point; CloudFront Functions (lightweight, viewer events) vs Lambda@Edge (heavier, origin events) for edge logic; and the security benefit of terminating TLS and absorbing traffic at the edge, including as DDoS surface reduction with Shield.

**A8.8 — WAF: what it does and doesn't protect against**

WAF inspects HTTP(S) requests at CloudFront, ALB, API Gateway, or AppSync, and allows/blocks/counts/CAPTCHAs based on rules: AWS managed rule groups (common vulnerabilities, bad inputs, known bad IPs), rate-based rules, geo-matching, IP sets, and custom rules on any request component.

**What it does well**: blocks broad automated scanning and commodity exploitation, provides rate limiting, buys time as a **virtual patch** while a real fix is deployed (this is genuinely valuable — a WAF rule can be live in minutes when a code fix is days), enforces geo restrictions, and gives visibility into request patterns.

**What it does not protect against**, which is the more important half of the answer:

- **Business logic flaws** — broken access control, IDOR, price manipulation. These are perfectly well-formed requests; there's no signature.
- **Authentication and authorisation bugs**, which is where most real breaches actually live.
- **Anything not in the inspected request** — it can't see what your application does with the input.
- **A determined attacker.** Managed rules are signature-based and bypasses are widely known; WAF raises cost, it doesn't prevent.
- **Volumetric L3/L4 DDoS** — that's Shield.
- Note the **body inspection size limit**, which means a large POST can carry a payload past the inspected window.

The operational reality: **run new rules in Count mode first and analyse the logs before blocking.** Deploying managed rule groups straight to Block reliably breaks legitimate traffic — file uploads, rich text fields, and anything with unusual encoding are the usual casualties — and the resulting incident is hard to diagnose because the request never reaches the application, so application logs show nothing. That last detail is the tell of someone who's debugged it.

The framing to close on: WAF is a compensating control and a defence-in-depth layer, not a substitute for secure code. Treating it as a security boundary is the misconception.

**A8.9 — Global Accelerator vs CloudFront**

**CloudFront** is a CDN: it caches content at edge locations and is optimised for HTTP/HTTPS. Its main value is serving cacheable content close to users and terminating TLS at the edge.

**Global Accelerator** provides **static anycast IPs** and routes traffic over the AWS backbone to the nearest healthy regional endpoint. It doesn't cache, it works for **TCP and UDP** (so non-HTTP protocols), and it fails over between regions in seconds without any DNS change.

The distinctions that matter:

- **Cacheable web content → CloudFront.** Non-HTTP protocols, gaming, VoIP, IoT, or anything needing static IPs → Global Accelerator.
- **The static IP property is the underrated one**: enterprise clients whose firewalls require IP allow-listing cannot cope with a load balancer's changing addresses. Global Accelerator gives them two fixed IPs. In fintech this comes up constantly for partner integrations.
- **Failover speed**: Global Accelerator shifts traffic in seconds because it's not DNS-dependent — no TTL, no client caching (A8.5). If the requirement is fast regional failover, this is the mechanism, and it's the direct counterpoint to A8.4's limitations.
- They **compose**: CloudFront in front for caching, Global Accelerator behind for regional routing, is a legitimate architecture.

---

## A9. Observability — T1

The observability *discipline* — SLOs, alerting philosophy, what to instrument — is its own domain. This section is the AWS-native tooling and the operational traps.

**A9.1 — Shipping logs to CloudWatch Logs**

Mechanisms by platform:

- **EC2** — the **CloudWatch agent** (which also provides memory and disk metrics, A9.3), configured with a JSON config specifying log files, log group, and stream. Deployed via SSM or baked into the AMI (A4.6).
- **ECS** — the `awslogs` log driver in the task definition, or FireLens/Fluent Bit for routing and filtering before delivery.
- **EKS** — Fluent Bit as a DaemonSet, usually via the CloudWatch Observability add-on.
- **Lambda** — automatic; `stdout` goes to a log group named for the function.
- **VPC/ALB/CloudTrail** — configured on the service, delivered directly.

Structure to get right: **log group per application or service, stream per instance/container/invocation**; retention set explicitly at group creation (A9.9); IAM permission on the role (`logs:CreateLogStream`, `logs:PutLogEvents`).

The two things that separate an experienced answer: **retention defaults to Never Expire**, so an unmanaged estate accumulates log spend forever — this is the most common single line item in a CloudWatch cost review. And **log in structured JSON**, because Logs Insights can then query fields natively rather than by regex (A9.2); retrofitting structure onto free-text logs during an incident is not possible, so it's a decision you make before you need it.

**A9.2 — A Logs Insights query that answers a real incident question**

"Which endpoints started returning 5xx at 14:20, and for which customers?"

```
fields @timestamp, status, path, tenant_id, duration_ms
| filter status >= 500
| stats count(*) as errors,
        avg(duration_ms) as avg_ms,
        count_distinct(tenant_id) as tenants
        by path
| sort errors desc
| limit 20
```

Latency distribution, which is the query that actually matters for a "it's slow" report:

```
filter @type = "REPORT"
| stats count(*), avg(@duration), pct(@duration, 50), pct(@duration, 95), pct(@duration, 99) by bin(5m)
```

Useful constructs: `parse` to extract fields from unstructured messages, `bin()` for time bucketing, `stats ... by` for grouping, `count_distinct`, `filter @message like /pattern/`, and querying multiple log groups at once for a request crossing services.

The practical points: **narrow the time range first** — Insights is charged by data scanned, and an unbounded query over a month of logs is both slow and expensive. **Percentiles, not averages** — an average latency hides the tail that users are complaining about. And the meta-point worth making: your ability to answer an incident question is determined by what you logged before the incident, so the query language is the cheap half. If `tenant_id` isn't in the log line, no query recovers it.

**A9.3 — Metrics: custom and metric-filter-derived**

Three sources:

- **Service metrics** — published automatically by AWS services.
- **Custom metrics** — via `PutMetricData` or, better, the **Embedded Metric Format**: write a specially structured JSON log line and CloudWatch extracts metrics from it, so you get a log record and a metric from one write, with no extra API call in the request path. This is the right pattern for application metrics and is under-used.
- **Metric filters** — pattern-match a log group and increment a metric. The way to get a metric from something that only ever appears in logs, e.g. counting a specific error string, or counting root-account logins from CloudTrail.

The point people miss and interviewers probe: **EC2 does not report memory or disk usage by default.** Those aren't hypervisor-visible, so they require the CloudWatch agent. A team monitoring only the default metrics is blind to the most common cause of instance failure — and right-sizing decisions made on CPU alone (A4.2) are made without the data that usually binds.

Also: **`PutMetricData` is charged per call** and per custom metric, so a naive per-request call is expensive — batch, or use EMF. **High-resolution metrics** (1 second) cost more and retain for a shorter period. Metric **dimensions form a unique metric per combination**, so a dimension with high cardinality (user ID, request ID) creates a cost explosion — that's the classic mistake, and the fix is that high-cardinality data belongs in logs or traces, not metric dimensions.

**A9.4 — Alarms on symptoms, and composite alarms**

The principle: **alert on what users experience, not on what a machine is doing.** High CPU is not a problem — it may be exactly what you're paying for. Elevated error rate, latency past the SLO, or a growing queue backlog are problems. Cause-based alerts generate noise proportional to fleet size; symptom-based alerts generate pages proportional to actual user impact.

Constructing one well: choose the statistic deliberately (p99 not average), set evaluation periods and datapoints-to-alarm so a single blip doesn't page, decide `TreatMissingData` explicitly — **missing data defaulting to `notBreaching` means an alarm that silently never fires when the thing it monitors stops reporting entirely**, which is the exact failure it exists to catch. That's the trap worth naming.

**Composite alarms** combine alarms with boolean logic, and serve two purposes: **suppression** (don't page for fifty instance alarms when the alarm that matters is "the load balancer is returning errors"), and **correlation** (only alarm if error rate is high *and* the deploy alarm is clear). They're the main native tool for reducing pager noise, which is the difference between an on-call rotation people can sustain and one they can't.

Also worth naming: **anomaly detection** bands for metrics with a strong daily cycle where a static threshold is either noisy or useless; and alarm actions doing something more useful than notifying — triggering an ASG action, an SSM Automation runbook, or an EventBridge rule.

**A9.5 — CloudTrail: management vs data events, and "who did this"**

- **Management events** — control-plane operations (`RunInstances`, `AssumeRole`, `PutBucketPolicy`). On by default, first copy free. This is the audit trail.
- **Data events** — data-plane operations (`s3:GetObject`, `lambda:Invoke`, DynamoDB item operations). **Off by default**, charged per event, and extremely high volume.

That default is the crucial fact: **by default, CloudTrail does not record who read an object from S3.** So "which objects did the compromised credential access?" is unanswerable after the fact unless data events were already enabled on that bucket — a decision you must make before the incident. Enable them selectively on sensitive buckets rather than everywhere, because everywhere is unaffordable.

Answering "who did this":

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=prod-db-sg \
  --start-time 2026-08-17T00:00:00Z
```

For anything beyond 90 days or complex queries, query the S3 archive with Athena (A15.5), or CloudTrail Lake.

Read the `userIdentity` block carefully: for an assumed role you get the role and session name, and mapping that back to a human requires either the Identity Center session name or `sourceIdentity` (A1.7). **A generic session name like `deploy` on a shared role means the audit trail cannot identify a person** — that's a design flaw to catch during a review, not during an investigation.

Other facts: there's a **delay of up to ~15 minutes** to delivery, so CloudTrail is not real-time and is the wrong tool for "what's happening right now". Global service events (IAM, STS) are recorded in `us-east-1`. And the 90-day console history exists even without a trail, which is often enough for a quick question.

**A9.6 — Organisation trail with a central, tamper-resistant log account**

Covered architecturally in A1.16. The specifics for this item:

- Create the trail in the management account (or delegated administrator) with `--is-organization-trail`, applying to all regions.
- Deliver to an S3 bucket in the **log archive account**, with a bucket policy allowing only the CloudTrail service principal to write, and denying delete to everyone.
- **Enable log file validation** (`--enable-log-file-validation`) — CloudTrail writes signed digest files so you can prove logs weren't altered. Without it, "tamper-resistant" is a claim you cannot substantiate.
- **Object Lock in compliance mode** so retention is enforced even against the account's own root.
- Encrypt with a **KMS key owned by the log account** (A10.5 — a key in prod would let a prod compromise render logs unreadable).
- Member accounts cannot disable it; back that with an SCP denying `cloudtrail:StopLogging` (A1.3).

The property to articulate is the same one as A1.16: an attacker with full admin in a workload account can neither stop the recording nor alter it. Worth adding: **alarm on the trail's own health** — a trail that stops delivering is a security incident, and CloudTrail publishes delivery-failure metrics for exactly this.

**A9.7 — EventBridge to react to an AWS event**

EventBridge receives events from AWS services, custom applications, and SaaS partners, matches them with rules, and routes to targets (Lambda, SQS, SNS, Step Functions, ECS tasks, cross-account buses).

A rule matching a security-relevant change:

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["ec2.amazonaws.com"],
    "eventName": ["AuthorizeSecurityGroupIngress"],
    "requestParameters": { "cidrIp": ["0.0.0.0/0"] }
  }
}
```

Common uses: auto-remediation (a public security group rule opened → revoke it and notify), routing GuardDuty or Security Hub findings to a ticketing system (A10.29), reacting to ECS task state changes or CodePipeline results, and **scheduled rules** as a managed cron replacement.

The details: **event patterns match, they don't transform** — use input transformers to reshape the payload for the target. Delivery is **at-least-once**, so targets must be idempotent (A13.5). Failures need a **DLQ configured on the target**, otherwise events are silently lost — that's the trap, because a rule that appears configured and is quietly dropping events looks identical to a rule that's working. And **not every service emits CloudTrail-derived events at useful granularity**, so verify the event actually fires before building on it. The archive-and-replay feature is genuinely useful for testing and for recovering from a downstream outage.

**A9.8 — Distributed tracing, X-Ray, and OTel**

Tracing follows a single request across service boundaries: each service emits a **span** with timing and metadata, correlated by a propagated **trace ID**, assembled into a **trace** showing where the time went and where the error originated.

Why it exists: logs tell you what one service did, metrics tell you the aggregate shape, but in a system of a dozen services neither answers "why was *this* request slow" — the latency is somewhere in a call graph you can't see. Tracing is the only one of the three signals that reconstructs the graph.

- **X-Ray** — AWS-native, integrates with Lambda, API Gateway, ECS, and the SDKs with minimal work. Service map, trace timelines, sampling rules.
- **OpenTelemetry** — vendor-neutral instrumentation and collector. **ADOT** is AWS's distribution, and it can export to X-Ray *and* to third-party backends simultaneously.

The recommendation and its reasoning: **instrument with OTel, export wherever you like.** Instrumentation is the expensive, invasive part — it's in your application code — and doing it with a vendor-neutral API means changing backends later is a collector config change rather than a re-instrumentation project. That's the argument, and it's a strategic one worth making explicitly, especially for a platform role where you're setting the standard for other teams.

Practical points: **sampling is mandatory at volume** — tracing every request is unaffordable and unnecessary — but head-based sampling can miss the rare errors you most want, so tail-based sampling (decide after seeing the trace) is better where the collector supports it. **Context propagation must be complete**: one service that drops the trace header breaks the chain, and the resulting trace looks like the request simply ended. And correlating trace IDs into log lines is what makes logs and traces useful together rather than separately.

**A9.9 — Log retention, cost control, and routing to S3**

CloudWatch Logs charges for **ingestion** (the dominant cost, per GB), **storage**, and **queries scanned**. The three levers:

1. **Set retention on every log group.** Default is never expire. This alone is frequently the largest single saving in a CloudWatch bill, and it's a one-line fix that nobody owns.
2. **Reduce ingestion.** Debug logging left on in production is the usual culprit, along with excessively verbose access logs and health-check requests logged at full detail. Ingestion is where the money is, so filtering at source beats any retention policy.
3. **Route high-volume, low-query-frequency logs to S3 instead** — VPC flow logs, ALB access logs, CloudTrail. S3 storage is dramatically cheaper, lifecycle rules tier it to Glacier (A6.2), and Athena queries it when needed (A15.5).

**Log class** matters too: CloudWatch Logs Infrequent Access has a lower ingestion price with reduced features (no Live Tail, no metric filters), which suits logs kept for compliance rather than operations.

The framing to use: **retention should be driven by what question you might need to answer and by regulatory requirement, not by "just in case".** In a regulated environment those requirements are explicit — and the correct design is usually short retention in CloudWatch for operational queries plus long retention in S3 with Object Lock for compliance, rather than paying CloudWatch rates for seven years of data nobody will ever query interactively.

---

## A10. Encryption, secrets & security services — T1

The largest section in the domain, and the one where an audit background shows most clearly. The KMS items in particular reward describing *failure modes and cost behaviour* rather than definitions — anyone can define envelope encryption; far fewer can explain why a data pipeline started throttling at month end.

**A10.1 — KMS key types, and when a CMK earns its cost**

- **AWS-owned** — owned and used by AWS across many accounts. Invisible to you: no key policy, no CloudTrail visibility, no rotation control. Free. This is what "encrypted by default" usually means.
- **AWS-managed** (`aws/s3`, `aws/rds`, `aws/ebs`) — one per service per account, visible in your account, auto-rotated annually. Free to keep; you pay for API requests. **You cannot modify the key policy**, which is the decisive limitation.
- **Customer-managed (CMK)** — you create and control it. ~$1/month plus request charges. Full key policy control, configurable rotation, aliases, grants, cross-account and multi-region capability, and deletion control.

When the extra cost is justified — and the answer should be about *capability*, not about "more secure", since the cryptography is identical:

- **You need a key policy as an independent authorisation layer.** This is the main one. A CMK lets you deny access at the key even when the resource policy or IAM is wrong, which is a genuine second control plane and the reason security teams want it (A10.3).
- **Cross-account access** — an AWS-managed key cannot be shared cross-account. Any cross-account S3, snapshot sharing, or AMI sharing forces a CMK.
- **You need to revoke access decisively.** Disabling a CMK makes every ciphertext under it immediately unreadable — a blunt but effective containment action during an incident (A10.30). You cannot do that with an AWS-managed key.
- **Separation of duties** — the log archive account owning its own key so no workload-account admin can read or destroy the logs (A1.16).
- **Compliance requirements** that mandate customer-controlled key material, rotation schedules, or auditable key usage.

Where a CMK is *not* justified: routine internal data with no cross-account or separation requirement. At $1/month the direct cost is trivial, but a CMK per bucket per environment across a large estate becomes a management burden — and the real cost is request charges, not the key (A10.14). The honest tradeoff: pick a small number of CMKs aligned to *data classification and blast radius* rather than one per resource.

**A10.2 — Envelope encryption**

KMS doesn't encrypt your data. It encrypts a **data key**, and the data key encrypts your data.

The flow: call `GenerateDataKey` → KMS returns a **plaintext data key** and an **encrypted copy** of it → encrypt your data locally with the plaintext key → discard the plaintext key from memory → store the encrypted data key alongside the ciphertext. To decrypt: send the encrypted data key to KMS's `Decrypt`, get the plaintext key back, decrypt locally.

Why it exists — three independent reasons, and naming all three is the mark of understanding rather than recital:

1. **KMS has a 4 KB limit on direct encryption.** Envelope encryption is what allows arbitrarily large objects.
2. **Your data never leaves your environment.** Only the small data key transits to KMS, which matters for both latency and data governance.
3. **Bulk encryption happens locally at local speed.** A network round trip per megabyte would be unusable.

The properties that follow, which are what interviewers actually probe: **rotating the KMS key does not re-encrypt your data** (A10.6), because the data is under the data key — the KMS key only ever wrapped the data key. And **the encrypted data key stored next to the ciphertext is safe**, because it's useless without a KMS `Decrypt` call that IAM and the key policy must authorise. That's the elegant bit: the security boundary is an API call, not the storage of the key.

**A10.3 — How key policy, IAM policy, and grants combine**

**The key policy is the root of authority for a KMS key, and this is the fundamental asymmetry with every other AWS service.** For S3, an IAM policy alone can grant access. For KMS, **if the key policy doesn't allow it, nothing else can** — an IAM policy granting `kms:*` on `*` gets you exactly nothing on a key whose policy doesn't reference you.

Three mechanisms:

1. **Key policy** — resource-based, mandatory, authoritative. The conventional pattern includes a statement granting the account root principal, which **delegates the decision to IAM**:

```json
{
  "Sid": "EnableIAMPolicies",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::111122223333:root" },
  "Action": "kms:*",
  "Resource": "*"
}
```

That statement is what makes IAM policies work for the key. Without it, IAM is irrelevant and every permission must be enumerated in the key policy itself.

2. **IAM policy** — only effective if the key policy delegates as above (or the principal is named directly).
3. **Grants** — programmatic, fine-grained, temporary permissions, used by AWS services on your behalf (A10.9).

So authorisation is: key policy allows (directly or via delegation) **AND** IAM allows **AND** no SCP denies **AND** any grant constraints are satisfied.

The practical consequence, which is the single most useful diagnostic heuristic in this whole section: **when a KMS operation is denied, determine first whether the key policy contains the root-delegation statement.** If it does, the problem is IAM. If it doesn't, the problem is the key policy, and no IAM change will ever fix it. People burn hours widening IAM policies against a key that was never going to honour them.

**A10.4 — Debugging a KMS access denied**

The error message distinguishes the cases, and reading it precisely is most of the work:

- *"The ciphertext refers to a customer master key that does not exist, does not exist in this region, or you are not allowed to access."* — deliberately vague to avoid leaking key existence. Usually wrong region or no access at all.
- *"User: ... is not authorized to perform: kms:Decrypt on resource: ... because no identity-based policy allows"* — IAM side, and it means the key policy *does* delegate to IAM (otherwise you'd see a different message). Fix the IAM policy.
- *"...with an explicit deny in a resource-based policy"* — the key policy denies.
- *"The request was rejected because the specified key was disabled/pending deletion."* — not a permissions problem at all.

The method:

1. **Identify the actual calling principal.** For a service-mediated call (S3 decrypting an object for you, RDS reading its storage) the principal may be the *service* using a grant, not you — so check whether the failing identity is who you assume (A14.3).
2. **Check the key policy for the root-delegation statement** (A10.3). This one check resolves the majority of cases immediately.
3. **Check the region.** Keys are regional; a cross-region call with a key ARN from elsewhere fails with the vague message above.
4. **Check for `kms:ViaService` conditions** — a key restricted to `s3.eu-west-1.amazonaws.com` will refuse a direct `Decrypt` call from the CLI even by an authorised principal, which looks bizarre until you read the condition.
5. **Check `EncryptionContext`** — if the ciphertext was created with a context and the decrypt call doesn't supply the identical context, it fails (A10.10). This is a common and confusing one because it's not a permissions issue at all.
6. **CloudTrail** — every KMS call is logged with the principal, the key, the context, and the error.

The cases that masquerade as something else: **an S3 `AccessDenied` that is actually a KMS problem** (A2.2) — the user has bucket access but not `kms:Decrypt`; **an EC2 instance that fails to launch** because its role can't use the EBS key; **a snapshot copy that fails** because the destination key isn't accessible (A10.13); and **an ECS task stuck in PENDING** because the execution role can't decrypt a secret (A5.4). In each case the visible error names the wrong service, and knowing to look one layer down is the experience.

**A10.5 — The risk of a key policy that locks out all administrators**

**A KMS key policy can be written such that no principal can modify it — and AWS Support cannot fix it.** This is unlike almost everything else in AWS, where support can eventually recover you. The only remedy is to schedule the key for deletion and wait out the mandatory window, which destroys every ciphertext under it.

How it happens: someone writes a tight key policy naming a single role or removes the root-delegation statement (A10.3), then that role is deleted, renamed, or its trust changes. Or an over-zealous `Deny` on `kms:PutKeyPolicy` matches everyone including the administrators. The result is a key that still *works* for encrypt and decrypt but can never have its policy changed — so you can never grant a new principal, and the data becomes progressively more stranded as roles change.

Guardrails:

- **Always retain the account-root delegation statement** unless you have a specific, reviewed reason not to. It is the recovery path.
- **Name a durable administrative principal**, not an individual or an ephemeral role — and prefer a role with a stable name managed by IaC.
- **Never grant `kms:PutKeyPolicy` to a principal that can also delete itself.**
- **Review key policies in code review**, treating them with the same care as an SCP, because the failure modes are comparably severe and less reversible.
- Deploy key policies via IaC so the intended state is recorded and reviewable.

Worth stating plainly in an interview: this is one of a very small number of AWS actions that are genuinely, permanently unrecoverable. Knowing which those are — this, S3 Object Lock in compliance mode, and deleting the last copy of a snapshot — is a good proxy for operational maturity.

**A10.6 — Key rotation: what rotates, what doesn't, what happens to old ciphertext**

With automatic rotation enabled on a symmetric CMK, KMS generates **new key material annually** (or on a configurable schedule, and you can rotate on demand). Critically:

- **The key ID, ARN, and alias do not change.** Nothing that references the key needs updating — this is why rotation is operationally invisible.
- **Old key material is retained indefinitely.** KMS keeps every previous version, so **existing ciphertext remains decryptable forever** without re-encryption.
- **New encrypt operations use the new material**; decrypt operations automatically select the material the ciphertext was created under.

The misconception to correct explicitly, because it's near-universal: **rotating a KMS key does not re-encrypt your data.** Under envelope encryption (A10.2) your data is encrypted with a *data key*; the CMK only wraps data keys. Rotating the CMK changes what future data keys are wrapped with. The data key protecting a five-year-old S3 object is unchanged, and the object is still readable under the old material.

The consequence people miss: **if your reason for rotating is that the key material may have been compromised, automatic rotation does not achieve it** — old ciphertext is still readable under the old material, which is exactly what you were worried about. Genuine key compromise requires re-encrypting the data under new material (A10.12), which is a data migration, not a setting. Automatic rotation satisfies a compliance control and limits the volume of data encrypted under any single version; it is not an incident response.

What doesn't auto-rotate: **imported key material (BYOK)** and asymmetric keys — you must rotate those manually by importing new material or creating a new key and migrating.

**A10.7 — Key deletion and the waiting period**

Scheduling deletion requires a **7–30 day waiting period** (default 30), during which the key is unusable but recoverable by cancelling. After it elapses, the key and all its material are destroyed and **every ciphertext under it is permanently unrecoverable** — there is no recovery, no support escalation, no backup.

Why disabling is the right first move:

- **Disabling is instantly reversible.** Deletion is not.
- **Disabling has the same containment effect** — nothing can encrypt or decrypt with the key — so as an incident action it's equally effective and carries no irreversible risk (A10.30).
- **It reveals what still depends on the key.** This is the real argument: it is genuinely difficult to prove nothing uses a key. Disable it, monitor CloudTrail for `Decrypt` failures and application errors for a full business cycle — including month-end and quarterly jobs — and the dependencies surface themselves. Deleting a key that a quarterly reconciliation job needed is discovered three months later, when the data is gone.

Also: **enable an alarm on `ScheduleKeyDeletion`.** Unexpected key deletion is either an error or an attack, and it's the kind of thing you want to know about within minutes rather than on day 29. CloudTrail plus EventBridge (A9.7) makes it trivial, and it's a good example of an alarm that's cheap to build and disproportionately valuable.

**A10.8 — Aliases, and why you reference the alias**

An alias is a friendly, mutable pointer (`alias/prod-payments-data`) to a key ID.

Why reference the alias:

- **Indirection.** If you need to move to a new key — new material after a genuine compromise, a change of key strategy, migration between accounts — you repoint the alias rather than changing every application, template, and policy that references the key.
- **Readability.** `alias/prod-rds-eu-west-1` in a policy or a Terraform file communicates intent; `1234abcd-12ab-34cd-56ef-1234567890ab` communicates nothing, and a reviewer cannot tell whether the right key is being used.
- **Environment portability.** The same IaC deploys to dev and prod referencing `alias/app-data`, resolving to different keys per account.

The important limits, which is where the nuance lives:

- **Aliases are regional and account-scoped.** You cannot reference another account's alias — cross-account use requires the key ARN (A10.11). This trips people building cross-account replication or snapshot sharing.
- **`kms:Decrypt` doesn't take a key identifier at all** — the ciphertext blob embeds the key ID. So the alias matters for *encrypt* operations, not decrypt, which is why repointing an alias affects new data only and old ciphertext still resolves to the old key. That is the correct behaviour and worth stating, because it's exactly what makes alias repointing safe.
- Key policies are attached to keys, not aliases, and `kms:ResourceAliases` is the condition key if you need alias-based conditions.

**A10.9 — Grants**

A grant is a **programmatic, fine-grained, revocable** permission on a key, created via API rather than by editing the key policy. It specifies a grantee principal, permitted operations, and optional constraints (typically on encryption context).

Where they're used instead of policy changes:

- **AWS services acting on your behalf.** When you attach a CMK to an ASG, an EBS volume, or an RDS instance, the service creates a grant so it can use the key for that resource. This is why you'll see grants you didn't create — and why revoking them breaks things in non-obvious ways.
- **Temporary or ephemeral access** — a job that needs decrypt access for the duration of its run. Grants can be retired when done.
- **Avoiding key policy churn.** Key policies have a size limit, and a policy edited by many teams for many workloads becomes both unreviewable and a change-collision point. Grants scale where policy statements don't.
- **Delegation without escalation** — `CreateGrant` can be granted to a principal so it can delegate a subset of its own key permissions, which is how services safely propagate access.

Points to make: grants are **additive only** — they can't deny. They're **eventually consistent**, so a newly created grant may not be immediately usable (use the returned grant token for the immediate call — a genuinely obscure detail that signals real use). And they are **easy to overlook in an audit**: reviewing the key policy alone does not tell you who can use a key. `aws kms list-grants --key-id ...` is the missing half of that audit, and it's the kind of thing that separates a thorough key review from a superficial one.

**A10.10 — Encryption context**

A set of non-secret key-value pairs supplied at encrypt time and **cryptographically bound to the ciphertext** as additional authenticated data. The identical context must be supplied at decrypt, or decryption fails.

Two purposes:

1. **Authorisation.** Key policies and grants can condition on it, so a principal may decrypt only ciphertext with a matching context:

```json
"Condition": {
  "StringEquals": { "kms:EncryptionContext:tenant": "acme-ltd" }
}
```

That's real multi-tenant isolation on a single shared key — a compromised tenant's credentials cannot decrypt another tenant's data even though both use the same CMK.

2. **Auditing.** The context appears in CloudTrail, so decrypt events carry meaningful business identifiers rather than an opaque key ID. This is what turns "the key was used 4 million times" into "these tenants' data was accessed by this principal" (A10.16).

The practical facts: **the context is not encrypted** — it's authenticated, not confidential — so never put secrets in it. It's **an exact match including case and, for the condition, all pairs**; a mismatch produces a decrypt failure that reads like a permissions error and confuses people badly (A10.4). AWS services set their own contexts automatically (S3 uses the object ARN, which is why an object can't be decrypted after being copied elsewhere in some configurations). And your application must **store or be able to reconstruct the context**, since decryption is impossible without it — losing the context loses the data as surely as losing the key.

**A10.11 — Multi-region keys and cross-account key usage**

**Multi-region keys** are a primary key plus replicas in other regions sharing the same key material and the same key ID suffix. **Ciphertext encrypted in one region can be decrypted in another without a KMS call across regions** — that's the entire point.

Where they're necessary: cross-region DR where data must be readable in the failover region without a re-encryption step (A11.2), global DynamoDB tables, and client-side encryption in an active-active architecture. Where they're not: most single-region workloads, where an ordinary regional key is simpler and avoids the operational surface.

The caveats: replicas have **independent key policies, grants, and rotation is coordinated but aliases are per-region**, so they're not one key so much as synchronised siblings — treat them as separate resources for policy review. And they weaken the regional isolation property, which some compliance regimes care about.

**Cross-account usage** requires **both**: the key policy in the owning account must allow the external principal (or its account root), *and* the external principal's IAM policy must allow the KMS actions on the key ARN. The double requirement (A2.1) is where this fails, and the diagnostic is A10.3.

The scenarios where this comes up constantly: **sharing an encrypted snapshot or AMI** — sharing the resource alone is insufficient, the recipient must also be able to use the key, and an unshared key is why "I shared the AMI and they still can't launch it"; **cross-account S3 replication** with different keys on each side; and **a central backup account** reading resources encrypted with workload-account keys. Note also that you **cannot share an AWS-managed key**, which is often the moment a CMK becomes mandatory (A10.1). Cross-account references must use the **key ARN, not an alias** (A10.8).

**A10.12 — Encrypting an existing unencrypted resource**

The general rule: **you cannot encrypt in place.** Every service requires creating a new encrypted resource and migrating.

- **EBS** — snapshot the volume, **copy the snapshot with encryption enabled** (the copy operation is where encryption is applied), create a volume from the encrypted copy, stop the instance, detach and reattach. Downtime is the stop/start. Enable **EBS encryption by default** at the account level so this never recurs.
- **RDS** — snapshot, copy the snapshot with encryption, restore to a new instance, then cut over. **The cutover is the hard part**, not the encryption: you either take downtime, or you set up replication from old to new (DMS or native replication) and switch with minimal interruption. For a fintech with a tight change window, DMS with CDC is usually the answer, and it turns a one-hour outage into a planned switchover of seconds.
- **S3** — new objects can be encrypted by setting default bucket encryption, but **existing objects are unaffected**. Re-encrypt by copying objects in place (`aws s3 cp s3://b/ s3://b/ --recursive --sse aws:kms`) or with **S3 Batch Operations** for large buckets, which is the right tool at scale. Watch versioning: copying creates new versions, so old unencrypted versions persist until lifecycle expires them — a detail that fails a compliance check even after you've "encrypted the bucket".

What makes this a good interview answer is naming the **planning** rather than the commands: measure the data volume and estimate the copy time, identify the cutover mechanism and its downtime, verify the application's connection handling, sequence non-prod first, have a documented rollback (keep the unencrypted original until verified), and — the part everyone forgets — **check that every consumer's IAM role has `kms:Decrypt` on the new key before cutover** (A2.2), because otherwise the migration succeeds and the application fails immediately afterwards with an error that points at the wrong service.

**A10.13 — Cross-region snapshot copy and re-encryption**

**KMS keys are regional.** A snapshot encrypted with a key in `eu-west-1` cannot be decrypted in `eu-west-2`, because the key doesn't exist there. So copying an encrypted snapshot cross-region **necessarily re-encrypts it** with a key in the destination region — you specify the destination key ID in the copy operation, and the copy decrypts with the source key and re-encrypts with the target.

```bash
aws ec2 copy-snapshot \
  --source-region eu-west-1 --source-snapshot-id snap-0123456789 \
  --destination-region eu-west-2 \
  --encrypted --kms-key-id arn:aws:kms:eu-west-2:1111:key/abcd-...
```

The implications for DR (A11.2), which is why this item exists:

- **The copying principal needs permissions on both keys** — decrypt on the source, encrypt on the destination. Missing the destination permission is the usual failure, and it surfaces mid-copy rather than at the start.
- **The destination key must exist and be managed** before the DR event, in IaC. Building the key during a disaster is not a plan.
- **The copy takes real time proportional to data size**, and that duration is part of your RPO — if snapshots copy hourly and a copy takes 40 minutes, your effective cross-region RPO is worse than hourly.
- **You cannot copy a snapshot encrypted with an AWS-managed key to another account**, and the cross-region copy of an `aws/ebs`-encrypted snapshot must be re-encrypted with a CMK to be shareable. This is another forcing function toward CMKs (A10.1).
- **Multi-region keys (A10.11) avoid the re-encryption step entirely** for some architectures, which is the main practical argument for using them.

The same pattern applies to RDS snapshot copies and to AMI copies, and the same permission trap applies to all three.

**A10.14 — KMS request costs, bucket keys, and data key caching**

KMS charges per API request (roughly $0.03 per 10,000, with `GenerateDataKey` and `Decrypt` being the volume drivers). Individually trivial; at scale, not.

The workloads that generate surprising bills:

- **S3 with SSE-KMS and many small objects.** Without bucket keys, **every `GetObject` is a KMS `Decrypt` call**. A pipeline reading ten million small files generates ten million KMS requests. **S3 Bucket Keys** (A6.3) cut this by up to 99% by generating a short-lived bucket-level key, and should be on by default.
- **Lambda functions fetching a secret on every invocation** (A10.21) — one KMS decrypt per invocation, multiplied by invocation volume. Cache in the execution environment with a TTL.
- **Envelope encryption in application code without data key caching.** The AWS Encryption SDK supports a **caching CMM** that reuses a data key across multiple operations subject to configurable limits on messages, bytes, and age. That's the correct mechanism, and the limits are the security control — you're trading a bounded reduction in cryptographic isolation for a large cost and latency reduction, and stating that tradeoff explicitly is the mark of understanding it.

The point worth making beyond cost: **KMS request volume is also a latency and availability concern** (A10.15). Reducing it is not purely a financial optimisation — it removes a synchronous dependency from your data path. That reframing is what makes it an architecture argument rather than a cost ticket, and it's the version that gets prioritised.

**A10.15 — KMS quotas as an availability risk**

KMS has **per-region, per-account request rate quotas** on cryptographic operations (in the low tens of thousands per second for symmetric operations, varying by region and operation type; asymmetric operations have far lower limits). Exceeding them returns `ThrottlingException`.

Why this is an availability risk rather than a cost footnote:

- **KMS is a synchronous dependency in the data path.** If every S3 read requires a KMS decrypt, then KMS throttling means your application cannot read data — a hard failure, not a slowdown.
- **The quota is shared across the whole account and region.** A batch job in one team's workload can exhaust the quota and take out an unrelated production service. This is the failure that's genuinely hard to diagnose, because the affected service didn't change and its own metrics look fine — it's a noisy-neighbour problem inside a service most people don't think of as shared capacity.
- **It manifests as intermittent, partial failure** under load, which pattern-matches to a dozen other things before anyone looks at KMS.

Mitigations, which are the same levers as A10.14: **bucket keys**, **data key caching**, spreading load across keys where the quota is per-key (some operations are), **quota increase requests raised proactively**, and **monitoring KMS throttling metrics with an alarm** before it becomes an incident. Architecturally, reducing the number of encryption operations in the hot path is better than raising the ceiling.

The framing for an audit or resilience review: **KMS is a single-region, account-shared, synchronous dependency for a large fraction of your data plane, and its quota is a shared resource with no isolation between workloads.** Stated that way it belongs on a resilience risk register alongside NAT gateways and Route53 resolver limits (A3.6), and that's exactly the kind of finding that makes an audit valuable rather than a checklist exercise (A11.9).

**A10.16 — Auditing key usage via CloudTrail**

Every KMS operation is a CloudTrail management event — `Encrypt`, `Decrypt`, `GenerateDataKey`, `CreateGrant`, `ScheduleKeyDeletion` — recording the principal, source IP, the key, the **encryption context** (A10.10), and, for service-mediated calls, the invoking service.

Answering "what decrypted this, and when":

```
fields @timestamp, userIdentity.arn, requestParameters.encryptionContext.tenant, sourceIPAddress
| filter eventSource = "kms.amazonaws.com" and eventName = "Decrypt"
| filter requestParameters.keyId like /abcd-1234/
| stats count(*) by userIdentity.arn, bin(1h)
```

The subtleties that matter for a real investigation:

- **The identity may be a service principal using a grant** (A10.9) rather than the human or role you're looking for. `s3.amazonaws.com` decrypting on someone's behalf requires you to correlate with the S3 data event (A9.5) to find the actual requester — and **S3 data events are off by default**, so if they weren't enabled beforehand, that correlation is impossible. This is the concrete reason to enable data events on sensitive buckets in advance.
- **Encryption context is the highest-value field** for attribution, because it carries business meaning. A key policy design that mandates a tenant or dataset in the context turns key auditing from "something used the key a lot" into an answerable access log.
- **Volume is the practical obstacle.** A busy key generates enormous numbers of events; querying them via Athena over the S3 archive (A15.5) is more workable than Logs Insights, and worth setting up before you need it.
- **Baseline first.** "Is this decrypt volume abnormal?" is unanswerable without knowing normal — which is an argument for a metric on decrypt volume per key, not just logs.

**A10.17 — When CloudHSM or imported key material is actually required**

The default position: **standard KMS is FIPS 140-2 Level 3 validated on its HSM fleet and is sufficient for the overwhelming majority of regulatory requirements, including PCI DSS and most financial regulation.** Reaching for CloudHSM or BYOK without a specific driver adds significant operational burden for no security gain — and being able to say that clearly is more valuable than being able to describe the alternatives.

**CloudHSM** is genuinely required when:

- A regulation or contract mandates **single-tenant, dedicated HSMs** rather than a shared service.
- You need **cryptographic operations KMS doesn't offer** — specific algorithms, PKCS#11/JCE/CNG integration for an application that expects a hardware token, or payment HSM operations (though AWS Payment Cryptography now covers much of the latter).
- You must hold key material where **AWS demonstrably cannot access it**, and "AWS operates the HSM but cannot extract material" is insufficient for the regulator.

The cost: you own availability, clustering, backup, and the loss of key material if you lose your credentials — AWS cannot recover a CloudHSM cluster for you. It is materially more expensive and materially more operational work.

**Imported key material (BYOK)** is required when the requirement is that key material **originates outside AWS** — generated on your own HSM, with your own ceremony and escrow. The tradeoffs are real and worth naming: **no automatic rotation** (A10.6), you must re-import to rotate, keys can be set to expire, and **if you lose your copy and the material expires or is deleted, the data is unrecoverable** — AWS has no copy by design, which is the entire point and also the entire risk.

The senior answer: ask what control the requirement is actually trying to achieve. Usually it's "prove AWS staff cannot read our data" or "we control the key lifecycle", and often a CMK with a tight key policy, encryption context, and CloudTrail auditing satisfies the underlying control at a fraction of the cost. Escalate to CloudHSM only when the requirement is explicitly single-tenancy or external key origin.

**A10.18 — ACM Private CA and internal certificate issuance**

ACM Private CA is a managed private CA hierarchy — root and subordinate CAs — issuing certificates for internal use that chain to a private root your organisation distributes as a trust anchor.

Where it fits: mutual TLS between internal services, service mesh identity, certificates for internal endpoints that shouldn't be in Certificate Transparency logs, device and workload identity, and any internal name (`*.internal.acme.com`) that a public CA won't issue for.

The decision-level tradeoffs, which is what this item asks for:

- **Cost is the first consideration and it's not trivial** — a monthly charge per CA plus a per-certificate charge. A large mesh issuing short-lived certificates per workload adds up, and the alternative (an open-source CA like Vault PKI or cert-manager with an internal issuer) is cheaper but is now your operational responsibility, including its own availability and key protection. That's the actual tradeoff: managed and audited versus cheaper and self-run.
- **Trust distribution is the hard part, and it isn't solved by the CA.** Every client — containers, JVMs with their own truststores, mobile, partner systems — must trust the root. Getting a new root into every truststore in an enterprise is a project, and it's why the private CA decision is a long-lived commitment.
- **Rotation and expiry become an operational concern at scale.** Short-lived certificates are better security and require automation (cert-manager, the ACM Private CA issuer) — without automation, short-lived certificates are an outage generator (A8.6).
- **Revocation** (CRL/OCSP) needs to be configured and actually consumed by clients, and in practice many clients don't check. Short lifetimes are a more reliable control than revocation.
- ACM Private CA integrates with ACM for issuance to ALBs and with EKS, which is a meaningful convenience over a self-run CA.

The framing that lands for a platform role: this is an identity infrastructure decision, not a certificate decision. Choose it when you need workload identity at scale with an audit trail, and pair it with automation from day one — see the Security/PKI domain for the CA hierarchy design itself.

**A10.19 — Secrets Manager: storage, retrieval, rotation**

Store a secret (string or binary, commonly JSON), encrypted with a KMS key. Retrieve via API:

```bash
aws secretsmanager get-secret-value --secret-id prod/payments/db --query SecretString --output text
```

Access is controlled by IAM plus an optional **resource policy on the secret** — which is how you do cross-account secret sharing, and it needs the KMS key shared too (A10.11).

**Rotation** runs a Lambda on a schedule implementing four steps: `createSecret` (generate the new value), `setSecret` (apply it to the service), `testSecret` (verify it works), `finishSecret` (move the `AWSCURRENT` label). AWS provides templates for RDS and other databases; anything else is a custom function.

**Version labels are the mechanism that makes rotation safe** and are worth understanding: `AWSCURRENT` is the current value, `AWSPREVIOUS` the prior one, `AWSPENDING` the one being tested. Clients get `AWSCURRENT` by default, so the new value only becomes live when the label moves — and `AWSPREVIOUS` remains retrievable, which is what allows a graceful transition for clients that haven't re-fetched yet.

Operational points: **secrets have a 7–30 day recovery window on deletion** (like KMS keys), so `delete-secret` isn't immediate and the name is unusable until it completes — which trips up IaC that deletes and recreates a secret in one apply, and the error is confusing. `--force-delete-without-recovery` exists but removes the safety net. Rotation Lambdas need network reachability to both the target service and the Secrets Manager endpoint (A7.8). And **cache retrieved secrets with a short TTL**: `GetSecretValue` is charged per call and generates a KMS decrypt (A10.14), so a per-request fetch is both expensive and a latency and availability dependency in your hot path.

**A10.20 — Secrets Manager vs Parameter Store**

| | Secrets Manager | Parameter Store (SSM) |
|---|---|---|
| Cost | ~$0.40/secret/month + API calls | Standard tier free; Advanced ~$0.05/param/month |
| Rotation | Built in, with Lambda templates | None built in |
| Cross-account | Resource policy | Advanced tier only, more limited |
| Size | 64 KB | 4 KB standard, 8 KB advanced |
| Versioning | Yes, with labels | Yes, by version number |
| Hierarchy | Flat names (by convention) | Native path hierarchy with `get-parameters-by-path` |
| Encryption | Always KMS | Optional (`SecureString`) |
| Throughput | Higher default | Lower default; Advanced tier for higher |

The decision, stated as reasoning rather than preference:

- **Use Secrets Manager when you need rotation.** That's the feature you're paying for, and building rotation yourself on Parameter Store means writing and maintaining the state machine that Secrets Manager already implements correctly (A10.19). For database credentials in a regulated environment, this is usually decisive.
- **Use Parameter Store for configuration** — feature flags, endpoints, non-secret settings, and secrets that don't rotate. The free standard tier and the path hierarchy make it excellent for hierarchical config (`/prod/payments/db/host`), and `get-parameters-by-path` fetches a whole tree in one call.
- **Cost matters at scale.** A thousand secrets is $400/month in Secrets Manager and free in Parameter Store standard. On a large estate that's a real number, and blanket "everything in Secrets Manager" is a defensible default that becomes indefensible at volume.

The nuance worth adding: this isn't either/or. A common and sensible pattern is Parameter Store for configuration and Secrets Manager for credentials that rotate — and Parameter Store can reference a Secrets Manager secret (`/aws/reference/secretsmanager/...`), so consumers can use one retrieval path for both. Also worth naming as alternatives: HashiCorp Vault where you have multi-cloud or need dynamic short-lived credentials, and **IAM database authentication (A7.8), which removes the secret entirely** — the best secret is the one that doesn't exist.

**A10.21 — Getting secrets into a container or Lambda without baking them in**

The requirement: the secret must never be in the image, the repository, or an environment variable set at build time.

- **ECS** — `secrets` in the task definition, referencing a Secrets Manager ARN or Parameter Store name. The **execution role** fetches it at task start and injects it as an environment variable (A5.2). Simple and the standard answer, but note the value ends up in the environment, visible to `docker inspect` and to anything that dumps env — including crash handlers and some logging libraries.
- **EKS** — the **Secrets Store CSI driver with the AWS provider** mounts secrets as files in the pod, authenticated via IRSA (A2.7), optionally syncing to a Kubernetes Secret. Files are better than environment variables for the reason above, and they support in-place refresh on rotation. **External Secrets Operator** is the popular alternative, syncing into native Kubernetes Secrets — note that native Secrets are only base64-encoded in etcd, so enable etcd encryption at rest.
- **Lambda** — fetch via the SDK **at cold start, cached in a module-level variable**, or use the **Parameters and Secrets Lambda extension**, which provides a local caching HTTP endpoint and avoids a KMS call per invocation (A10.14). Do not put secrets in Lambda environment variables: they're visible in the console, in the API, and in IaC state.

The principles that generalise, and which are the actual answer:

1. **The identity fetches the secret at runtime** — instance profile, task role, or IRSA. No credential is needed to get the credential; that's the bootstrapping problem solved.
2. **Prefer files or a local cache over environment variables**, because environment variables leak into logs, crash dumps, and child processes.
3. **Handle rotation** — the application must be able to re-fetch on auth failure, or the rotation you configured breaks the app (A7.8).
4. **Never in the image, never in IaC state.** Terraform state contains secret values in plaintext if a secret's value passes through it — which is a frequently-missed exposure and an argument for creating the secret container in IaC but populating the value out of band.

**A10.22 — GuardDuty: detections, data sources, triage**

GuardDuty is a managed threat detection service analysing telemetry for malicious or anomalous activity. **Data sources**: CloudTrail management events, VPC flow logs, and DNS query logs (all consumed directly, without you enabling or paying for them separately — a genuinely useful detail, since it means enabling GuardDuty doesn't require enabling flow logs), plus optional protection plans for S3 data events, EKS audit logs, EBS malware scanning, RDS login activity, and Lambda network activity.

**What it detects**: credential exfiltration and use from unusual locations, instances communicating with known command-and-control or crypto-mining infrastructure, reconnaissance patterns, unusual API calls, IAM anomalies, and — the highest-signal finding in practice — **`UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration`**, which means instance role credentials are being used from outside the instance. That one is almost never a false positive and maps directly to A10.30.

**Triage method**, which is the part being assessed:

1. **Read the finding type and severity properly.** Types are structured (`ThreatPurpose:ResourceType/ThreatFamily`) and the type tells you the hypothesis.
2. **Establish whether it's expected behaviour.** A vulnerability scanner, a penetration test, a VPN egress in an unusual country, or a backup job hitting an unfamiliar endpoint all generate genuine-looking findings. Context beats the finding.
3. **Corroborate with CloudTrail** (A9.5) and flow logs (A3.5) — what else did that principal or instance do around that time? A single finding is a signal; a pattern is an incident.
4. **Assess blast radius** — what can that identity reach? For instance credentials, that's the instance role's permissions.
5. **Decide: suppress with justification (A10.28), act, or escalate.**

The operational point that determines whether GuardDuty is useful: **enable it org-wide with a delegated administrator (A1.17), and route findings to somewhere people actually look (A10.29).** GuardDuty findings in a console nobody opens have prevented no breaches. Also flag that it's **regional** — enable in every region including unused ones, because an attacker will happily mine crypto in `ap-south-1` precisely because nobody's watching there.

**A10.23 — AWS Config: inventory, history, drift**

Config records the configuration of supported resources and every change to them, producing: a **resource inventory** across accounts and regions, a **configuration timeline** for each resource, **relationship mapping** between resources, and **compliance evaluation** against rules.

The questions it answers that nothing else does: *what did this security group look like last Tuesday?*, *what changed in the hour before the incident?*, *how many unencrypted RDS instances exist across all 40 accounts right now?*, and *which resources reference this subnet?* Its **configuration timeline plus CloudTrail** is the standard pairing for incident forensics — Config tells you *what changed*, CloudTrail tells you *who changed it* (A9.5).

**Drift detection** here means divergence from a *compliance rule*, which is subtly different from IaC drift (A14.5) — Config doesn't know your Terraform intent, it knows your policy. Both matter and they're not the same thing; conflating them is a common muddle.

The thing to flag hard: **Config is expensive at scale, and its cost is a genuine surprise.** You pay per configuration item recorded and per rule evaluation, and recording all resource types in all regions across a large org — especially with high-churn resources — produces a bill that regularly appears in the top five services in a cost review (A12.3). Control it by excluding high-churn, low-value resource types, recording global resources in one region only, using periodic rather than change-triggered evaluation where appropriate, and being deliberate about which regions record. Enabling it everywhere by default without that tuning is a recognised trap, and knowing it before the bill arrives is worth saying.

**A10.24 — Writing a Config rule or conformance pack**

- **Managed rules** — a large library of AWS-authored rules (`s3-bucket-public-read-prohibited`, `rds-storage-encrypted`, `iam-user-mfa-enabled`). Start here; most requirements are already covered.
- **Custom rules** — a Lambda (or a **Guard** rule, which is a policy-as-code DSL and much lighter than a Lambda for structural checks) evaluating a resource and returning `COMPLIANT` / `NON_COMPLIANT` / `NOT_APPLICABLE`.
- **Conformance packs** — a YAML bundle of rules and remediation actions deployable across an org as a unit, which is how you deploy a standard rather than a list of rules.

**Remediation** attaches an SSM Automation document to a rule, optionally automatic. The judgement to express: **automatic remediation is powerful and occasionally dangerous.** Auto-removing a public S3 ACL is almost always right. Auto-terminating a non-compliant instance is how you cause an outage from a policy violation. The sensible default is auto-remediate the reversible and clearly-wrong, and notify for everything else — and always ensure the remediation is itself logged and attributable.

The detective/preventive relationship is A1.11, and the sequencing argument matters here: **write the Config rule first, measure how non-compliant the estate actually is, then decide whether to promote to an SCP.** Going straight to prevention without the measurement is how governance programmes break production and lose their mandate.

Also worth naming: Config rules evaluate *recorded* resource types, so a rule for a resource type you're not recording silently never fires — a quiet false-assurance failure mode that's easy to miss in an audit, because the dashboard says compliant.

**A10.25 — Security Hub as an aggregator**

Security Hub does not detect anything itself. It **aggregates findings** — from GuardDuty, Config, Inspector, Macie, IAM Access Analyzer, Firewall Manager, and third-party tools — into a normalised format (ASFF), deduplicates, applies its own standards' controls, and produces a compliance score and a single queue.

The relationships, which is what the item asks for:

- **Config is the evaluation engine** behind most Security Hub controls. Many Security Hub standards controls are implemented as Config rules, so **Security Hub depends on Config being enabled and recording the relevant resource types** — the single most common reason for controls showing as "no data" (A10.23).
- **GuardDuty is a finding source**; Security Hub is where its findings land alongside everything else.
- **Security Hub's own value is normalisation, aggregation, and workflow** — one format, one queue, one place to suppress and track, and cross-account aggregation to a delegated admin.

The honest assessment worth offering: Security Hub's value is entirely determined by whether findings are triaged. Enabled with all standards on and nobody assigned to it, it produces thousands of findings, a mediocre score, and organisational fatigue — which is worse than not having it, because it creates the appearance of coverage. The valuable pattern is: enable, suppress what's genuinely not applicable *with documented justification* (A10.28), route the rest to a work queue (A10.29), and track the trend rather than the absolute score.

**A10.26 — Security Hub org-wide with delegated admin**

The setup: enable trusted access for Security Hub in the org, **register the security/audit account as delegated administrator** (A1.17), enable auto-enrolment of new accounts, and configure a **finding aggregation region** so all regional findings surface in one place.

The pieces that are easy to get wrong:

- **It's regional, and so is the aggregation.** Without a designated aggregation region, you have a Security Hub per region per account and no single view — which defeats the purpose. Enable in all regions (including unused ones, for the same reason as GuardDuty) and aggregate to one.
- **Auto-enrolment for new accounts** must be switched on, or every account vended after setup (A1.13) silently sits outside the programme. Verifying this is a good audit check because it fails quietly.
- **Config must be enabled and recording** in every member account and region, or controls report no data (A10.25). This dependency is the number one cause of "Security Hub says we're compliant" being meaningless.
- **Central configuration policies** let you define which standards and controls apply per OU from the delegated admin, rather than configuring each account — the modern approach, and much better than StackSets pushing per-account config.

Do the same delegation for GuardDuty, Config, Access Analyzer, and Inspector so the security account is the single operating point (A1.17), and keep the management account out of routine use.

**A10.27 — Standards, and acting on a low score**

- **AWS Foundational Security Best Practices (FSBP)** — AWS's own broad baseline; the sensible default for everyone.
- **CIS AWS Foundations Benchmark** — a well-recognised external baseline, commonly referenced by auditors.
- **PCI DSS**, **NIST 800-53**, and others — enable when they're actually in scope for your regulatory environment.

The score is a percentage of passed controls, weighted by severity. **Acting on a low score:**

1. **Triage by severity and exploitability, not by count.** A single critical finding — a publicly exposed database, a root account without MFA — matters more than four hundred medium findings about logging configuration. A score-driven approach naturally optimises for the wrong thing, because fixing many trivial findings moves the number more than fixing the one that matters.
2. **Separate "not applicable" from "not done".** A large fraction of low scores in a real estate are controls that genuinely don't apply — suppress those with justification (A10.28) so the remaining number means something.
3. **Group findings by root cause.** Three hundred findings are usually a dozen causes: no default encryption setting, a missing SCP, a module that doesn't set a flag. **Fix the Terraform module and the finding count collapses** — that's the leverage, and it's the platform-engineering answer rather than the ticket-closing one.
4. **Prevent recurrence.** For each cause, ask what makes it impossible next time — an SCP (A1.3), a proactive control, or a module default. Otherwise the score decays back.
5. **Set a target and a trend, and report the trend.** "Critical and high findings, and time-to-remediate" is a better executive metric than a score, because it's actionable and harder to game.

The framing that works with leadership: a low score is a *measurement*, not a failure — and the first honest measurement of a legacy estate is always bad. What matters is the slope and whether the top-severity items are shrinking (A1.15).

**A10.28 — Suppressing or accepting a finding with justification**

Mechanism: set the finding's workflow status to `SUPPRESSED`, or use an automation rule to suppress matching findings on ingest, with a note. In Config, a resource can be marked as an exception via a rule exclusion.

Why do it properly rather than ignore: **an unsuppressed finding you've decided not to fix is indistinguishable from one nobody has looked at.** Once the queue contains a stable population of known-ignored findings, people stop reading the queue, and the next real finding arrives into a channel that everyone has learned to skip. The suppression is not bureaucracy — it's what keeps the signal usable.

A defensible suppression records: **what** is being accepted, **why** (with the compensating control if there is one), **who** accepted it and at what authority, **when it expires**, and **what would change the decision**. The expiry is the part that's most often missing and matters most — a permanent exception is a policy change, and should go through whatever process policy changes go through, not through a suppression button.

The distinction worth drawing in an interview: **suppression is for "this control does not apply here"** (a finding about a resource that's deliberately public because it's a public website). **Risk acceptance is for "this control applies, we're not meeting it, and we've decided to live with it for now."** They look the same in the tool and are completely different governance acts. Conflating them is how a risk register quietly empties itself.

For fintech specifically: exceptions are audit evidence. An auditor asking "why is this control failing" wants a documented, time-bounded, authorised acceptance — and being able to produce one turns a finding into evidence of a working risk process rather than a gap.

**A10.29 — Routing findings to a ticket or alert**

The pattern: **Security Hub → EventBridge → destination.** Security Hub emits findings as EventBridge events, so a rule filters by severity, standard, or finding type and routes to Lambda, SNS, an SQS queue, or a ticketing integration (Jira, ServiceNow, PagerDuty).

```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Imported"],
  "detail": {
    "findings": {
      "Severity": { "Label": ["CRITICAL", "HIGH"] },
      "Workflow": { "Status": ["NEW"] }
    }
  }
}
```

The design decisions that make this work rather than just exist:

- **Route by severity to different destinations.** Critical → page. High → ticket with an SLA. Medium and low → a periodic digest or a dashboard review. Paging on everything is the fastest route to nobody responding to anything (T7.4 in the Troubleshooting domain).
- **Route to the owning team, not to a central security inbox.** Ownership comes from resource tags (A12.2), which is one of the strongest arguments for tag enforcement — without it, every finding lands on the security team, who cannot fix most of them and become a bottleneck.
- **Create a real work item with an owner and a due date**, not a notification. Notifications are read once and lost; tickets are tracked.
- **Deduplicate and suppress before routing** (A10.28), or the first day of operation generates thousands of tickets and the integration is switched off by the end of the week. Backfill deliberately: route *new* findings first, and work the existing backlog as a separate exercise.
- **Close the loop** — when the finding resolves, the ticket should close, or the queue diverges from reality.

The principle to state: **a dashboard is a place findings go to be not-acted-upon.** A finding that doesn't create an owned work item hasn't been managed, it's been displayed.

**A10.30 — Responding to a leaked credential**

Sequence, and the ordering is the point — **contain before you investigate**, because the investigation takes hours and the attacker doesn't wait:

1. **Contain immediately.**
   - **IAM user access key**: deactivate it (`aws iam update-access-key --status Inactive`) rather than deleting — deactivation stops use instantly and preserves it as evidence.
   - **Role credentials** (the instance-exfiltration case): you cannot revoke an issued session token, so **attach a deny-all policy to the role with a `aws:TokenIssueTime` condition** — the AWS-documented "revoke sessions" action, which invalidates existing sessions while allowing new legitimate ones.
   - **Isolate the source**: quarantine security group on the instance, or stop it (**snapshot the volume and capture memory first if forensics matter** — stopping destroys volatile evidence).
2. **Assess blast radius.** What did that identity have? Enumerate its policies and, critically, **what it could assume or pass** (A2.9). Assume everything it could reach is compromised until proven otherwise.
3. **Determine what was actually done.** CloudTrail for every action by that principal from first suspicious use: new IAM users or keys, policy modifications, new roles, trust policy changes, data access, resources created in unusual regions, snapshots shared to unknown accounts, CloudTrail or GuardDuty disabled. **Persistence mechanisms are the priority** — an attacker who created a second access key or a trusted role survives your rotation of the first credential, and this is the step people skip in the rush to rotate.
4. **Rotate.** The leaked credential and anything it could have read — database passwords, API keys, secrets it had `GetSecretValue` on. And rotate everything it could have *reached*, not just what you know it took.
5. **Find the leak source.** Git history (and remember rotating doesn't remove it from history), a public bucket, a log, a laptop, a CI variable, an image layer.
6. **Prevent recurrence.** This is where the answer should land for a senior role: if it was a long-lived IAM user key, the fix isn't better key hygiene, it's **eliminating long-lived keys** — Identity Center for humans (A1.4), OIDC for CI (A2.8), roles for workloads (A2.6), an SCP denying `iam:CreateAccessKey`, and secret scanning in the commit path.
7. **Notify.** In a regulated environment, legal and compliance have disclosure obligations with clocks attached, and that assessment starts at detection, not at resolution.

Worth naming: **AWS detects some exposed keys automatically** (public GitHub scanning) and applies a quarantine policy plus a support case — so the first notification may come from AWS, which is a bad way to find out but a good reason to make sure support contacts are monitored (A1.13). And the honest closing point: **the detection time is the metric that matters.** A key leaked and detected in ten minutes is an incident; the same key detected in three weeks is a breach.

**A10.31 — Encryption in transit and at rest, and proving it's on**

The structure of a good answer is per-layer, and crucially includes **how you'd prove it** rather than assert it — which is the difference between an architecture claim and an audit finding.

**At rest:**

| Service | Mechanism | Proof |
|---|---|---|
| S3 | Default bucket encryption, SSE-KMS | `get-bucket-encryption`; Config rule; deny unencrypted PUT in bucket policy |
| EBS | Volume encryption; account-level default on | `describe-volumes` filtered on `encrypted=false`; Config rule |
| RDS | `StorageEncrypted` at creation | `describe-db-instances`; note it **cannot be enabled later** (A10.12) |
| EFS / DynamoDB | Encryption at rest | On by default for DynamoDB; explicit for EFS |
| Secrets/SSM | KMS | SecureString type for Parameter Store |
| Logs | KMS on log groups and the trail bucket | A9.6 |

**In transit:**

- **Public endpoints**: TLS, enforced by `aws:SecureTransport: false` deny in bucket and other resource policies — and note that this **denies, rather than merely preferring**, which is the enforceable version.
- **Load balancers**: HTTPS listeners with a modern security policy; **and the backend leg** — TLS terminating at the ALB with plaintext to the target is a very common gap that architecture diagrams hide.
- **Within the VPC**: traffic between instances is not encrypted by default at the application layer, though AWS encrypts some inter-AZ/inter-region traffic at the physical layer and Nitro instances encrypt in-transit traffic between supported instance types. If the requirement is application-level encryption everywhere, that's mTLS or a service mesh (A10.18), not an AWS setting.
- **Databases**: `rds.force_ssl` / `require_secure_transport` parameters (A7.5) — enforced at the engine, not merely offered.
- **Direct Connect is not encrypted** (A3.12).

**Proving it** is the part that distinguishes an audit answer: **Config rules for continuous evidence** (A10.24), **SCPs and resource policies for prevention** so non-compliance is impossible rather than merely detected, Security Hub controls for the aggregate view, and — the point auditors care most about — **evidence that is generated continuously rather than assembled for the audit.** A screenshot proves a moment; a Config rule with a compliance timeline proves a period. In a fintech that distinction is the difference between passing cleanly and a finding about control monitoring.

---

## A11. Resilience & DR — T1

**A11.1 — Defining RTO and RPO from business requirements**

- **RTO** — how long the service can be unavailable before the impact is unacceptable.
- **RPO** — how much data loss is acceptable, measured in time.

The point of the item is that **these are business decisions engineers must extract, not technical targets engineers should set.** Asked directly, every stakeholder says "zero" — which is unimplementable and unaffordable, so it's a non-answer. The productive questions are the ones that force a tradeoff:

- What actually happens to the business in the first hour of downtime? The first day? Is the loss revenue, regulatory, contractual, or reputational?
- Are there **contractual or regulatory** commitments — an SLA with a customer, a regulator's operational resilience expectation, an impact tolerance already documented?
- **If we lost the last fifteen minutes of transactions, could we reconstruct them?** From upstream systems, from counterparty records, from logs? Often the answer is yes, which relaxes the RPO enormously — and this question is far more productive than asking for a number.
- What does an hour of the recovery capability cost per year, and is the business willing to fund it?

In UK financial services this is a regulated conversation — **operational resilience requirements (the FCA/PRA framework) require firms to identify important business services and set impact tolerances**, which are RTO/RPO by another name with a regulator attached. Framing the discussion in the firm's own resilience language rather than in AWS terms is what gets it taken seriously, and it converts "the platform team wants budget" into "we are evidencing a regulatory obligation".

Two technical points to close on: **different services in one system legitimately have different targets** — the payment path and the reporting dashboard should not be engineered to the same tolerance, and treating them identically wastes money on one and under-protects the other. And **an RTO you have never measured is a guess** (A11.8). The deliverable is a documented, tested, signed-off number per important business service, not a global aspiration.

**A11.2 — The DR strategies**

| Strategy | RTO | RPO | Standing cost | Shape |
|---|---|---|---|---|
| Backup & restore | Hours to days | Hours | Lowest | Backups replicated cross-region; rebuild on demand |
| Pilot light | Tens of minutes to hours | Minutes | Low | Data replicated and core services present but switched off |
| Warm standby | Minutes | Seconds to minutes | Medium-high | Full stack running at reduced scale, scaled up on failover |
| Active-active | Near zero | Near zero | Highest | Both regions serving; failover is traffic shifting |

What each actually involves:

- **Backup & restore** — cross-region snapshot copies (A10.13), AWS Backup (A11.7), IaC to rebuild. Cheap and, crucially, **it protects against corruption and deletion, which replication does not** — a replicated mistake is still a mistake. It is also the only strategy that covers "someone dropped the table".
- **Pilot light** — database replicated continuously, infrastructure defined but minimal or stopped. Recovery is scaling up and switching traffic. The core data is warm; the compute is cold.
- **Warm standby** — everything running, small. No cold start, and — the underrated benefit — **you know it works because it's running**, which is exactly the property untested DR lacks.
- **Active-active** — genuinely hard. Requires solving cross-region data consistency, which is the real cost, not the infrastructure.

The point that carries weight: **most organisations claiming warm standby actually have a pilot light with an untested runbook**, because the standby has never taken production traffic. The distinguishing question is "when did the secondary last serve real requests?"

**A11.3 — Costing each strategy and recommending one**

The method: cost the standing infrastructure (duplicate compute, storage, replication data transfer, cross-region transfer charges — A12.4), plus the engineering time to build and, more significantly, to **maintain** it, plus the cost of testing it regularly. Then compare against the cost of downtime at each RTO.

The recommendation should be framed as a tradeoff, not an answer, and it should be **per business service** (A11.1):

> "For the payments path, downtime costs roughly £X per hour and we have a contractual commitment of four hours. Warm standby gets us to ~15 minutes for about £Y per month, roughly 15% of the primary's cost. Pilot light halves that spend but puts us at 2–4 hours, which leaves no margin against the commitment if anything goes wrong during recovery — and something always does. I'd recommend warm standby for the payment path and backup-and-restore for reporting, where a day's outage is tolerable. The largest single risk in either case is that we've never tested a full regional failover, so I'd fund the first test before the standby."

That structure — quantified impact, options with numbers, a recommendation, and the honest residual risk — is what's being assessed. Two additional points worth making: **multi-AZ is not DR** (A11.4/A11.6) and covers a different failure class; and **cross-region DR is often not the highest-value resilience spend** — for many organisations, a tested backup restore and removal of single points of failure within the region buys more real availability per pound than a second region that has never been exercised. Being willing to say that is a senior signal, because the expected answer is "build multi-region".

**A11.4 — Multi-AZ HA for a stated workload**

The standard pattern, layer by layer:

- **Load balancer** across at least three AZs (cross-zone load balancing on).
- **Compute** in an ASG or Kubernetes cluster spanning those AZs, with the desired count such that **losing one AZ still leaves enough capacity to serve peak load** — this is the calculation people get wrong. Three AZs at 33% each means an AZ loss puts the survivors at 50%; if they were already at 70% utilisation, they now can't cope. Size for N-1, not for N.
- **Database** multi-AZ (A7.1) or Aurora across three AZs.
- **State** in S3, EFS, or a replicated cache — never on instance local disk.
- **NAT gateway per AZ** with per-AZ route tables (A3.1), or an AZ failure takes out egress for the survivors too.
- **Kubernetes**: topology spread constraints so replicas don't all land in one AZ, and PDBs so a node drain doesn't remove them all.

The parts that separate a real design:

- **Every layer must be multi-AZ, or the least-redundant one defines your availability.** A perfectly redundant web tier in front of a single-AZ database is a single-AZ system.
- **Cross-AZ data transfer costs money** (A12.4), and a chatty microservice architecture spread across AZs can generate a startling bill — so there's a genuine tension between resilience and cost that you should acknowledge rather than pretend away.
- **Zonal dependencies hide in surprising places**: a VPC endpoint present in only two AZs, a single-AZ EFS mount target, a hardcoded subnet in a launch template, one NAT. These are exactly what an audit surfaces, and they're invisible until the AZ fails.
- **Quotas are per-AZ in some cases**, and capacity in the surviving AZs is not guaranteed during a large zonal event — everyone else is failing over into them at the same time. Capacity reservations are the mitigation for genuinely critical workloads, and mentioning this shows you've thought past the diagram.

**A11.5 — What multi-region actually costs you**

Beyond the obvious duplication, the costs that make multi-region hard:

- **Data consistency is the real problem.** Synchronous cross-region replication imposes tens of milliseconds of latency on every write, which most applications can't absorb. Asynchronous means a non-zero RPO and the possibility of **conflicting writes in an active-active design** — and conflict resolution is an application-level design problem with no infrastructure solution. This is the crux, and an answer that doesn't reach it hasn't engaged with the question.
- **Operational complexity multiplies.** Every deployment, migration, secret rotation, certificate renewal, and config change must be applied consistently in both regions, and **drift between regions is the failure mode that makes a failover fail** — you fail over to a region running last month's schema.
- **Data transfer charges** between regions are substantial and continuous (A12.4).
- **Regional service differences** — not every service, instance type, or feature is available in every region, and quotas are per-region and must be raised in both. The secondary that's never carried load has never had its quotas tested (A11.9).
- **Testing cost.** A DR capability that's never exercised is a liability; exercising it properly is expensive and disruptive, and organisations under-fund it precisely because it produces no visible feature.
- **Encryption and key management** — cross-region key strategy, snapshot re-encryption (A10.13), or multi-region keys (A10.11).
- **Split brain and failback.** Failing over is the easy half. **Failing back with data that diverged during the outage is the hard half**, and most runbooks stop at failover — which means the first real event ends with an unplanned data reconciliation exercise.

The senior framing: multi-region should be a deliberate response to a specific, quantified requirement (A11.1). Adopted as a default posture, it often *reduces* reliability, because the added complexity introduces more failure modes than the regional redundancy removes — and the honest comparison is against what the same money would buy in testing, single-points-of-failure removal, and operational maturity within one region.

**A11.6 — How an AZ failure manifests, and what fails over automatically**

**How it manifests** — rarely as a clean, total outage, which is the important part. Typically: elevated error rates and latency in one AZ, some resources unreachable while others in the same AZ are fine, control-plane operations failing or slow (you may be unable to launch replacement instances *in that AZ*, or anywhere, if the control plane is degraded), and EBS volumes becoming unresponsive rather than gone. **Partial, degraded, and ambiguous** is the normal presentation, and it's much harder to respond to than a clean failure — automated health checks may not trip decisively, and the system sits in a half-broken state.

**Automatic:**
- ALB/NLB stop routing to failed targets and to the affected AZ (with zonal shift available to force it).
- RDS multi-AZ fails over to the standby (A7.1) — with connection drops and DNS caching caveats.
- ASGs replace failed instances **in the remaining AZs** if capacity allows.
- S3, DynamoDB, SQS and other regional services absorb it transparently.
- Kubernetes reschedules pods onto surviving nodes, if there's capacity and if PVs aren't zonal.

**Manual, or at least not automatic:**
- **Anything single-AZ**: a single NAT (A3.1), a single-AZ EFS mount target, a self-managed database on one instance.
- **EBS volumes are zonal** — the data is in that AZ; recovery is from snapshot.
- **Capacity in the surviving AZs**, if the ASG can't launch because the instance type is exhausted region-wide (everyone is failing over simultaneously).
- **Read replica promotion** (A7.2).
- **Stateful workloads with zonal persistent volumes** in Kubernetes.

The two points worth adding: **ARC zonal shift** lets you deliberately evacuate an AZ, which is the right first action when you suspect a zonal issue and is far faster than diagnosing it. And **the most common real failure is capacity, not connectivity** — the AZ is degraded, everyone's ASG tries to launch replacements at once, and the constraint becomes instance availability. That's why sizing for N-1 (A11.4) rather than relying on scale-out during the event is the correct design.

**A11.7 — AWS Backup for centralised, cross-account policy**

AWS Backup provides **backup plans** (schedules, lifecycle to cold storage, retention) applied to resources by **tag or resource type**, across services (EBS, RDS, DynamoDB, EFS, S3, FSx), with **vaults** holding the recovery points and **backup policies deployable org-wide** from the management or delegated admin account.

Why it beats per-service backup configuration:

- **One policy, one report, across accounts and services.** The audit question is "prove everything critical is backed up", and per-service configuration can't answer it without an inventory exercise every time.
- **Tag-based selection means new resources are covered automatically** — the coverage gap otherwise appears every time someone provisions something, and nobody notices until it's needed.
- **Cross-account copy into a dedicated backup account** with a **vault lock** — the critical control. Vault Lock in compliance mode makes recovery points immutable and undeletable *even by root*, which is the only real defence against ransomware and against a compromised administrator deleting the backups before the data (A10.30). That's the property to lead with in a fintech context.
- **Cross-region copy** for regional DR (A11.2), with the re-encryption considerations of A10.13.
- **Compliance reporting** through Backup Audit Manager, giving continuous evidence rather than assembled-for-audit evidence (A10.31).

The caveats: **it's a coordination layer over each service's native mechanism**, so it inherits their characteristics — an RDS backup through AWS Backup is still an RDS snapshot with the same restore behaviour and the same lazy-loading performance profile (A6.8). Restore is still per-resource and still needs testing (A11.8). And **vault lock in compliance mode is irreversible** — if you set a retention period you can't afford, you're paying for it for the full term, so model the cost before locking.

**A11.8 — Actually testing DR**

The progression, and naming it as a progression is the answer:

1. **Restore test** — restore a backup into an isolated environment, verify integrity, **record the wall-clock duration**. Automate it to run on a schedule and report. This is the minimum viable DR test and most organisations don't do it.
2. **Component failover** — force an RDS failover (`reboot --force-failover`), terminate instances, drain a node. Cheap, low-risk, and catches the DNS-caching class of problem (A7.1).
3. **Game day / tabletop** — walk the runbook with the people who'd actually be on call, in the middle of the night, without the person who wrote it. **The most common finding is never technical**: the runbook references a system nobody has access to, the escalation contact left, or step 4 assumes a console you can't reach because SSO is in the failed region.
4. **Zonal evacuation** — ARC zonal shift in production, which is genuinely low-risk and genuinely informative.
5. **Full regional failover** — expensive, disruptive, and the only thing that actually proves the capability. Run it in a controlled window with a defined abort condition.
6. **Fault injection** (FIS, A15.10) — systematic, repeatable, controlled failure injection as a routine practice rather than an event.

The principles: **measure against the stated RTO/RPO and publish the delta** — a test that "passed" without a measured recovery time proves nothing. **Test the failback too** (A11.5), because that's the half nobody rehearses. **Include the people and process**, not just the infrastructure. And **treat every finding as a defect with an owner**, or the same test produces the same findings next year.

The line that lands: **an untested DR plan is a document, not a capability** — and in a regulated environment, the regulator increasingly asks for evidence of testing, not evidence of design. That reframes DR testing from an engineering nice-to-have into a compliance deliverable, which is usually how it gets funded.

**A11.9 — Quotas and limits as an availability risk**

Nearly every AWS service has quotas, most **per-account per-region**, and hitting one produces a hard failure at exactly the worst moment — because the moment you hit a quota is the moment you're scaling in response to something.

The ones that actually cause incidents:

- **EC2 vCPU quotas per instance family** — the ASG cannot launch replacements during a scale-out or an AZ failure.
- **Lambda concurrent executions** — account-wide, so one function's spike throttles unrelated functions (A4.8).
- **VPC: ENIs, security group rules, route table entries, IPs per subnet** — the EKS IP exhaustion case (A5.7).
- **KMS request rate** — a shared, synchronous dependency for the data plane (A10.15).
- **NAT gateway connections and port allocation** — `ErrorPortAllocation`, which presents as random connection failures under high outbound concurrency to a single destination, and is very hard to diagnose blind.
- **EBS volume and snapshot limits**, **API throttling**, **Route53 resolver queries per ENI** (A3.6), **CloudFormation stack limits**.

Managing them, which is what the item is really asking:

1. **Inventory them against actual usage** — Service Quotas provides current values and, for many, utilisation metrics. This is a standard, high-value audit output.
2. **Alarm at a threshold, not at the limit.** CloudWatch alarms on quota utilisation at 70–80% turn a future outage into a ticket. This is one of the highest-value, lowest-effort resilience controls available, and it's routinely missing.
3. **Request increases proactively**, before the peak — increases are not instant, some require support review, and requesting one during an incident is not a mitigation.
4. **Include quota requests in account vending** (A1.13), because new accounts get defaults.
5. **Account for the failure scenario**: your quota must accommodate not steady state but the state during an AZ failure, when you're running more instances than usual in fewer AZs — and during a regional failover, when the secondary region needs quotas it has never exercised (A11.5).

The framing for a resilience review: **quotas are an availability dependency you don't control, with no failover, that only bind under load.** Presented that way it belongs on the risk register next to single points of failure — and it's the kind of finding that's easy to remediate and impressive to have found, because most estates have never looked.

---

## A12. Cost — T2, but disproportionately valued

**A12.1 — Cost Explorer to attribute spend and find an anomaly**

Group by **service**, **account** (A1.1 — the cleanest dimension because it works even when tagging doesn't), **region**, **usage type**, and **tag**. Filter to the anomalous window, compare to the prior period, and drill down.

The method for a spike: **start at the service level, then the usage-type level.** Usage type is where the answer usually is — `DataTransfer-Regional-Bytes`, `NatGateway-Bytes`, `KMS-Requests`, `CW:GMD-Metrics`. It tells you *what kind of consumption* changed, which is more diagnostic than which service. Then attribute by account and tag to find who, and correlate to the timeline: a deploy, a new environment, a job that started retrying in a loop, a lifecycle rule that was removed.

Practical points: Cost Explorer data lags by up to a day, so it's not real-time. **Amortised vs unblended cost** matters when Savings Plans and RIs are involved — unblended shows the raw charge, amortised spreads commitments, and comparing the wrong one across a period produces confusing results. For anything deeper, **CUR into Athena or QuickSight** is the real tool; Cost Explorer is for triage. And enable **cost allocation tags** in the billing console, or your tags won't appear as a Cost Explorer dimension at all — a step that's easy to miss and makes the whole tagging strategy invisible (A12.2).

**A12.2 — Designing and enforcing a tagging strategy**

A minimal, actually-usable set: `Environment`, `Owner` (team, not person), `CostCentre`, `Service`/`Application`, `DataClassification`, and `ManagedBy` (the IaC that owns it).

**Enforcement is where strategies fail**, and the answer should be about mechanism:

1. **Enforce at creation with IAM conditions** — deny `RunInstances` and equivalents unless `aws:RequestTag/CostCentre` is present (A2.5). This is the only enforcement that actually holds, because it makes the untagged resource impossible rather than reportable.
2. **Tag Policies** in Organizations to standardise allowed keys and values — preventing `env`, `Env`, `environment`, and `ENVIRONMENT` from becoming four dimensions.
3. **Enforce in IaC modules** — default tags at the provider level in Terraform means every resource inherits them without anyone remembering. For an IaC-managed estate this is the highest-leverage single control.
4. **Detect with Config rules** for what slips through (A10.24), and report by owner, not centrally.
5. **Activate them as cost allocation tags**, or none of this shows up in billing.

Two points that show experience: **tags are load-bearing beyond cost** — they drive backup selection (A11.7), ABAC (A2.5), finding routing (A10.29), and patching groups, so tagging discipline is an operational control rather than a finance one, which is a much stronger argument when asking teams to comply. And **retrofitting tags onto an existing estate is the hard part** — the answer is enforce-at-creation immediately so the problem stops growing, then backfill by ownership campaign, accepting that some resources will never be attributable and belong in an "unallocated" bucket you shrink over time.

**A12.3 — Usual top spend drivers and quick wins**

**Typical top drivers**: EC2/compute, RDS, S3 storage, **data transfer** (A12.4 — and it's usually higher than people expect because it's spread across line items), NAT gateways, CloudWatch (logs ingestion especially), Config on a large org (A10.23), and KMS requests on high-volume data paths (A10.14).

**Quick wins**, roughly in order of effort-to-return:

- **Delete orphans**: unattached EBS volumes (A4.1), old snapshots, unassociated Elastic IPs, idle load balancers, unused NAT gateways, forgotten dev environments.
- **Set CloudWatch Logs retention** — often the single biggest one-line saving in an unmanaged estate (A9.9).
- **S3 lifecycle rules**, especially **expiring noncurrent versions and aborting incomplete multipart uploads** (A6.1) — invisible data you're paying for.
- **Shut down non-production out of hours.** Dev and test running 24/7 for a team that works 40 hours is roughly a 70% waste on that spend, and a scheduled ASG action is trivial to implement.
- **gp2 → gp3** on EBS: cheaper at equal or better performance, essentially free money (A6.8).
- **Right-size** from Compute Optimizer and actual utilisation (A4.2).
- **VPC endpoints** where NAT processing charges justify them (A3.3).
- **Savings Plans on the steady-state baseline** (A12.5).
- **Graviton** where the workload supports arm64.

The framing point: **quick wins are one-off; the durable saving is changing the mechanism that creates the waste** — module defaults, lifecycle rules applied at creation, budgets per team, and cost visibility that reaches the team that generates the spend. Otherwise you repeat the same clean-up annually, which is a strong observation to make because it's the platform-engineering answer rather than the FinOps-ticket answer.

**A12.4 — Data transfer charges**

The rules that matter:

- **Inbound from the internet**: free.
- **Outbound to the internet**: charged per GB, with a free tier, and it's the largest transfer cost for most public-facing workloads. CloudFront egress is cheaper than direct EC2 egress, which is a real architectural lever.
- **Cross-AZ within a region**: charged **in both directions**. This is the one people forget, and it's why a chatty service mesh spread across three AZs generates significant cost simply by being resilient (A11.4).
- **Same AZ, private IPs**: free. Same AZ via a public IP or an internet-facing load balancer: charged — so addressing choice has a cost consequence.
- **Cross-region**: charged, and higher than cross-AZ.
- **NAT gateway**: hourly *plus* per-GB processing, **on top of** any transfer charge. Traffic to S3 through a NAT pays processing that a free gateway endpoint would eliminate (A3.3).
- **VPC peering within a region**: no charge beyond the cross-AZ component. **Transit Gateway**: per-GB on top, which is a real difference at volume (A3.4).
- **PrivateLink**: hourly per endpoint per AZ plus per GB.

The reason this is asked: **data transfer is the cost that doesn't appear as a single line item you can point at**, so it hides. The diagnostic is to group Cost Explorer by usage type (A12.1) and look for `DataTransfer-Regional-Bytes` and `NatGateway-Bytes`. Common findings: cross-AZ chatter between services that could be AZ-affine, logs and metrics shipped cross-region, a NAT gateway carrying traffic that should use an endpoint, and replication configured more aggressively than the RPO requires.

**A12.5 — Savings Plans vs Reserved Instances**

Covered as pricing models in A4.5. For the commitment recommendation specifically:

- **Compute Savings Plans** — most flexible: any instance family, size, region, OS, tenancy, plus Fargate and Lambda. Slightly lower discount. **The default recommendation** for most organisations, because the flexibility is worth more than the extra few percent when your workload mix will change over the term.
- **EC2 Instance Savings Plans** — locked to a family in a region; deeper discount. Suitable for a genuinely stable, large, known workload.
- **Reserved Instances** — still relevant for RDS, ElastiCache, OpenSearch, and Redshift, which Savings Plans don't cover. That's the main reason to still discuss RIs at all, and it's a good detail to know.

The recommendation method:

1. **Look at the last 3–6 months of usage and find the trough** — the floor beneath which usage never falls.
2. **Commit to a fraction of that floor** (60–80% is a common starting point), not to the average and never to the peak. **Unused commitment is pure loss**, and over-committing turns a discount programme into a liability.
3. **Prefer 1-year over 3-year** unless the workload is genuinely stable and the organisation's direction is certain — a 3-year commitment made just before a migration to containers, Graviton, or another provider is an expensive mistake. In a company undergoing platform change, this is the decisive consideration.
4. **Layer, don't monolith**: Savings Plan for the baseline, On-Demand for the variable band, Spot for interruptible (A4.5).
5. **Buy incrementally** — several smaller commitments at different times rather than one large one, so you're never fully exposed to a single decision and can adjust as usage evolves.
6. **Remember commitments pool across the org** (A1.2), so the analysis belongs at org level.

**A12.6 — Budgets, anomaly detection, and alerting**

- **AWS Budgets** — thresholds on cost or usage, per account, service, or tag, with **forecast-based alerts** as well as actual. Forecast alerts are the more useful kind, because they warn you mid-month rather than confirming the overspend at the end. **Budget Actions** can automatically apply a restrictive policy or stop instances at a threshold, which is appropriate for sandbox accounts (A1.12) and dangerous for production.
- **Cost Anomaly Detection** — ML-based, learns each service's normal pattern and alerts on deviation. Better than a static threshold for spend that grows legitimately, because it catches the *shape* change rather than the absolute number.
- **Alerting**: route to the **owning team**, not just to finance. A central finance alert produces an email to someone who can't fix it; a team alert produces a fix. The tag strategy (A12.2) is what makes that routing possible.

The design points: **set a budget per account at vending time** (A1.13) so no account exists without one. **Alert on rate of change, not just totals** — a 300% week-on-week increase in a small account is a stronger signal than a 5% increase in a large one. And keep the alerting quiet enough to be read: budget alerts that fire monthly on a growing service become noise, and then the real anomaly is missed — the same alert-fatigue dynamic as A9.4, and worth naming as such.

**A12.7 — A cost-reduction story with a number and no reliability regression**

The structure interviewers are listening for:

1. **How you found it** — the method, not luck. Cost Explorer grouped by usage type, an anomaly alert, an audit.
2. **What the driver was** — specific and technical.
3. **What you changed**, and why it was safe.
4. **The number**, with a baseline and a period.
5. **How you verified nothing degraded.**
6. **What stops it recurring.**

A worked example in that shape:

> "A multi-account review showed data transfer as the third-largest line item, and grouping by usage type put most of it in NAT gateway processing. Flow logs showed the bulk was ECR image pulls and S3 traffic from private subnets — traffic that didn't need to leave the VPC at all. We added S3 gateway endpoints (free) and interface endpoints for ECR in the accounts where the volume justified them, which was about half. That cut NAT processing by roughly 60%, about £X a month. Because endpoints keep the traffic inside the VPC, availability improved slightly rather than regressing — we removed a dependency on the NAT path — and we confirmed it with pull latency and error rates before and after. We then added the endpoints to the account baseline module so new accounts get them by default."

The three things that make it credible: **the number is attached to a baseline and a period** rather than being a bare percentage; **the reliability check is explicit** rather than assumed; and **it ends with the mechanism that prevents recurrence** (A12.3), which is what distinguishes a platform engineer from someone who closed a cost ticket. If you have a genuine figure from your own audit work, use it — the specificity is the credibility, and vague "we saved a lot" answers are read as second-hand.

---

## A13. Messaging & integration — T2

The broader messaging patterns are their own domain; this is the AWS service selection and semantics.

**A13.1 — SQS: visibility timeout, DLQs, standard vs FIFO**

**Visibility timeout**: when a consumer receives a message it becomes invisible to others for this period. If the consumer deletes it within the window, it's gone; if not, it reappears for redelivery. **The timeout must exceed your worst-case processing time**, or a slow message is redelivered while still being processed — producing duplicate processing that looks like a mysterious data bug. Use `ChangeMessageVisibility` to extend it for long jobs (the heartbeat pattern) rather than setting a very long default, which delays recovery from genuine consumer crashes.

**Dead-letter queues**: after `maxReceiveCount` failed attempts, the message moves to a DLQ. Essential, because without one a poison message loops forever, consuming capacity and generating errors indefinitely. **The DLQ needs an alarm on depth** — an unmonitored DLQ is a silent data-loss bucket, and finding ten thousand messages in one that's been filling for a month is a common and unpleasant discovery. Redrive lets you replay after fixing the cause.

**Standard vs FIFO**: standard is at-least-once with best-effort ordering, effectively unlimited throughput. FIFO is exactly-once processing within a deduplication window and strict ordering **per message group ID**, at lower throughput. The key insight: **ordering is per group, not per queue**, so choosing a good group ID (per customer, per account, per entity) preserves the ordering you actually need while retaining parallelism. Using a single group ID serialises the entire queue, which is the usual reason "FIFO is too slow".

The design point: **standard SQS plus idempotent consumers is usually better than FIFO** (A13.5) — cheaper, faster, simpler — and reaching for FIFO is often a way of avoiding the idempotency work rather than a genuine ordering requirement.

**A13.2 — SNS and fan-out**

SNS is pub/sub: publishers send to a topic, and every subscriber gets a copy. Subscribers can be SQS queues, Lambda, HTTP endpoints, email, SMS, or Kinesis Firehose. **Message filtering** by attributes means subscribers receive only what matches their filter policy, which avoids the anti-pattern of every consumer receiving everything and discarding most of it.

**The canonical fan-out pattern is SNS → multiple SQS queues**, and the reason matters: each consumer gets its own queue, so a slow or failed consumer buffers independently without affecting the others, and each gets retries and a DLQ. Subscribing Lambdas directly to SNS loses that buffering — a Lambda failure means the message is retried a few times and then lost unless you've configured an on-failure destination.

Other points: SNS is push, so **there's no backpressure** — a fast publisher can overwhelm an HTTP subscriber, which is another argument for the SQS buffer. **FIFO topics** exist and pair with FIFO queues. Delivery is at-least-once, so consumers must be idempotent (A13.5). Cross-account and cross-region subscriptions work via topic policy.

**A13.3 — EventBridge rules, buses, and schema**

**Buses**: the default bus receives AWS service events; **custom buses** carry your application's events; **partner buses** receive from SaaS providers. **Rules** match events by pattern (A9.7) and route to targets, with input transformation. The **schema registry** discovers event structures and generates code bindings.

Where it differs from SNS, which is the substance of the item: EventBridge routes on **content** — the rule inspects the whole event body and matches on any field — whereas SNS filters only on message attributes. That makes EventBridge the right tool for event-driven architecture where routing logic is genuinely about what happened, and it means **producers don't need to know their consumers**: a new consumer adds a rule without any change to the publisher. That decoupling is the architectural argument.

It also natively receives AWS service events, supports scheduled rules, archives and replays events, and does cross-account delivery bus-to-bus. The tradeoffs: **lower throughput and higher latency than SNS or SQS**, per-event pricing, and — critically — **a target failure needs a DLQ configured or events are silently lost** (A9.7). Also, an event that matches no rule is simply discarded, which makes "my event went nowhere" a common and confusing debugging session; the archive feature is the antidote.

**A13.4 — Choosing between SQS, SNS, EventBridge, and Kinesis**

Decide on the shape of the problem:

- **SQS** — one producer to one logical consumer group, work queue semantics, buffering and load levelling, and you want backpressure. The default for decoupling a producer from a slow consumer.
- **SNS** — one message to many subscribers, immediately, push-based. Notifications and simple fan-out.
- **EventBridge** — event routing where consumers subscribe to *what happened* by content, with many potential consumers unknown to the producer. Integration with AWS services and SaaS. The right default for an event-driven architecture.
- **Kinesis / MSK** — an **ordered, replayable, retained stream** consumed by multiple independent readers at their own positions. The distinguishing features are **retention and replay** (re-read the last 7 days) and **ordered high-throughput partitioned processing**. Analytics, event sourcing, log aggregation, CDC.

The discriminating questions to ask out loud: *Do consumers need to replay history?* (only Kinesis/MSK). *Does ordering matter?* (FIFO SQS or Kinesis). *Is it one consumer or many?* (SQS vs SNS/EventBridge). *Does the producer need to know its consumers?* (SNS is more coupled than EventBridge). *What throughput?* (Kinesis for very high sustained volume; EventBridge is the slowest).

The composite answer is often correct and worth stating: **EventBridge for routing, with SQS queues as targets for buffering** gives content-based routing plus per-consumer backpressure and DLQs — the pattern that combines the strengths rather than choosing between them.

**A13.5 — Idempotency and at-least-once delivery**

**Almost every AWS messaging service guarantees at-least-once delivery**, meaning duplicates are not an edge case — they are a normal, expected occurrence. They arise from visibility timeouts expiring (A13.1), retries after an ambiguous failure, network partitions where the ack is lost, and consumer restarts mid-processing.

So **the consumer must be idempotent**: processing the same message twice produces the same end state as processing it once. Mechanisms:

- **Idempotency key** — a business-meaningful, producer-supplied unique ID stored on receipt in a database or DynamoDB table with a conditional write; a duplicate fails the condition and is discarded. The standard approach.
- **Naturally idempotent operations** — `SET status = 'paid'` is safe; `balance = balance + 100` is not. Designing operations to be idempotent where possible is cheaper than detecting duplicates.
- **Optimistic concurrency** with a version number.
- **Conditional writes** in DynamoDB (`attribute_not_exists`).

The points that show real experience: **"exactly-once" is a property of processing, not delivery.** FIFO SQS deduplicates within a five-minute window, which handles a retry storm but not a duplicate arriving an hour later — so it reduces the problem without removing the requirement. **The idempotency record and the business effect must be committed atomically**, or you crash between them and either reprocess or lose the work — this is the subtle part and the reason people get it wrong. And in a payments context this stops being an architectural nicety: a duplicated debit is a customer-impacting, regulator-visible incident, which is why idempotency keys are standard in payment APIs and why "we'll use FIFO" is an inadequate answer.

**A13.6 — Step Functions, and orchestration vs choreography**

**Step Functions** is a managed state machine: states, transitions, error handling with typed retries and catches, parallel and map states, and the choice of **Standard** (long-running, exactly-once, full execution history) or **Express** (high-volume, short, at-least-once) workflows.

**Orchestration** — a central coordinator holds the process definition and invokes each step. **Choreography** — each service reacts to events and emits its own, with no central controller (EventBridge/SNS).

When orchestration wins:

- **The process has meaningful state and multi-step failure semantics** — retries per step, compensating transactions, a saga. Expressing that across choreographed services means the logic is scattered across every participant and exists nowhere as a whole.
- **You need to answer "where is order 12345 right now?"** Step Functions gives you the execution history for free; with choreography, reconstructing it means correlating logs across services, which is a build.
- **Human approval steps, waits, timeouts, and long-running processes** — callback tokens and wait states handle these natively.
- **The sequence is a business process that people reason about and change**, and having it in one readable definition matters more than the coupling it introduces.

When choreography wins: **autonomy and decoupling.** Adding a consumer requires no change to any existing service, teams deploy independently, and there's no central component whose failure stops everything. The cost is that no single place describes the process, and debugging is a distributed-tracing exercise (A9.8).

The judgement to state: **use orchestration for a business process with defined steps and failure handling, choreography for reactive integration between autonomous services** — and note that most real systems use both, orchestrating within a bounded context and choreographing between them. Also worth mentioning: Step Functions' direct SDK integrations remove a great deal of glue Lambda code, and "we replaced a chain of Lambdas invoking each other with a state machine" is a common and genuinely good refactor, because Lambda-chaining hides the retry semantics in code where nobody can see them.

---

## A14. Access & tooling — T1

**A14.1 — CLI fluency**

```bash
aws sso login --profile prod-admin
aws s3 ls --profile prod-admin

# server-side filtering (API-level) vs client-side
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].{Id:InstanceId,Type:InstanceType,AZ:Placement.AvailabilityZone}' \
  --output table

# pagination
aws s3api list-objects-v2 --bucket big-bucket --max-items 100 --starting-token "$TOKEN"
aws logs describe-log-groups --no-paginate
```

The distinctions worth knowing: **`--filters` is applied server-side by the API; `--query` (JMESPath) is applied client-side after the response.** For large result sets, filtering server-side is dramatically faster and cheaper — a `--query` over 10,000 instances still transfers all 10,000. The CLI **auto-paginates by default**, which is convenient and occasionally surprising when a command takes minutes; `--page-size` controls the request size and `--max-items` the total.

Other fluency markers: `--output json|table|text|yaml` and piping `json` into `jq` for anything complex; `--dry-run` on EC2 mutations to test permissions without acting; `--no-cli-pager` in scripts; `--debug` when you need to see the actual signed request; and `aws configure export-credentials` for feeding tools that don't understand SSO natively.

**A14.2 — `~/.aws/config` for multi-account SSO**

```ini
[sso-session acme]
sso_start_url = https://acme.awsapps.com/start
sso_region = eu-west-1
sso_registration_scopes = sso:account:access

[profile dev]
sso_session = acme
sso_account_id = 111122223333
sso_role_name = Developer
region = eu-west-1
output = json

[profile prod-ro]
sso_session = acme
sso_account_id = 444455556666
sso_role_name = ReadOnly
region = eu-west-1

[profile prod-deploy]
role_arn = arn:aws:iam::444455556666:role/DeployRole
source_profile = prod-ro
role_session_name = jahid
```

The points: **the `sso-session` block is the modern form** — one login (`aws sso login --sso-session acme`) refreshes the token for every profile that references it, instead of authenticating per profile. **Role chaining** via `source_profile` covers the case where SSO gets you into an account and you then assume a further role (A1.7) — remembering the one-hour chaining cap. `credential_process` integrates external credential tools. And a naming convention that makes the account and privilege level obvious (`prod-ro` vs `prod-admin`) is a genuine safety control: `AWS_PROFILE` set to the wrong thing is one of the more common causes of self-inflicted production incidents, and a profile name that reads as dangerous makes you pause.

**A14.3 — The credential provider chain, and "which credentials am I using"**

Resolution order (roughly, for the CLI and most SDKs):

1. Command-line arguments / explicit code parameters
2. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SESSION_TOKEN`, `AWS_PROFILE`)
3. Web identity token (`AWS_WEB_IDENTITY_TOKEN_FILE` — IRSA, A2.7)
4. Shared credentials file (`~/.aws/credentials`)
5. Shared config file with SSO or `role_arn` (`~/.aws/config`)
6. Container credentials (ECS task role endpoint; EKS Pod Identity)
7. Instance metadata (IMDS — instance profile, A2.6)

The single most useful command in AWS troubleshooting:

```bash
aws sts get-caller-identity
```

It answers "who am I actually" in one call, and a surprising share of access-denied investigations end there (A2.4).

The classic traps, all of which are "the environment is overriding what you think you configured":

- **Stale environment variables take precedence over everything below them.** `AWS_PROFILE` or exported keys left over from an earlier session silently override the profile you passed. This is the number one cause of "it works for my colleague".
- **On EC2 or in a pod, credentials come from IMDS or the container endpoint** — so a script that works locally with your SSO profile behaves as the instance role in production, with completely different permissions.
- **In a pod, a misconfigured IRSA annotation silently falls back to the node role** (A2.7) — it works, as the wrong identity.
- **Expired SSO tokens** produce a confusing error rather than a clean "please log in".
- **Region resolution follows its own chain** (`AWS_REGION`, profile, then unset) and a missing region produces "you must specify a region" or, worse, operations against the wrong one.

`aws configure list` shows which source each value came from, which is the fast way to see what's actually in effect.

**A14.4 — Using boto3 for what the CLI can't do neatly**

Where the SDK is the right tool: **anything with control flow, error handling, or state.** Iterating across every account in an org and aggregating results; conditional logic on the response; retry with custom backoff; joining data from several APIs; anything that needs to be tested.

```python
import boto3
from botocore.config import Config

cfg = Config(retries={"max_attempts": 10, "mode": "adaptive"})

def assume(account_id, role="OrgReadOnly"):
    sts = boto3.client("sts")
    creds = sts.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role}",
        RoleSessionName="org-audit",
    )["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )

org = boto3.client("organizations")
for page in org.get_paginator("list_accounts").paginate():
    for acct in page["Accounts"]:
        if acct["Status"] != "ACTIVE":
            continue
        session = assume(acct["Id"])
        ec2 = session.client("ec2", config=cfg, region_name="eu-west-1")
        for p in ec2.get_paginator("describe_volumes").paginate(
            Filters=[{"Name": "encrypted", "Values": ["false"]}]
        ):
            for v in p["Volumes"]:
                print(acct["Id"], v["VolumeId"], v["Size"])
```

That shape — **assume a read-only role in every account, paginate, aggregate** — is the backbone of any multi-account audit, and being able to write it fluently is worth more in an interview than knowing any individual API.

The details that matter: **always use paginators** rather than manual token loops; **configure adaptive retries** because org-wide scripts hit API throttling constantly; **`Session` per account** rather than mutating global state; handle accounts where the role doesn't exist without aborting the whole run; and remember that **`describe_*` calls are throttled per-account per-region**, so a naive parallel run across 40 accounts will be throttled and needs backoff rather than more threads.

**A14.5 — CloudFormation vs CDK vs Terraform: state and drift**

- **CloudFormation** — **AWS manages the state**; the stack is the source of truth and lives in the service. No state file to store, lock, or lose. Drift detection is a built-in operation, but it's **detection only** — it reports differences without reconciling them, and coverage isn't complete across all resource types. Rollback on failure is automatic, which is genuinely valuable, though a stack stuck in `UPDATE_ROLLBACK_FAILED` is its own kind of misery.
- **CDK** — a programming-language abstraction that **synthesises CloudFormation**. So the state and drift model is CloudFormation's exactly; what differs is the authoring experience, the ability to use real language constructs and testing, and the risk that generated templates are large and the abstraction hides what's actually deployed.
- **Terraform** — **you own the state file**, which must be stored remotely (S3 with locking) and protected, because **it contains resource attributes including secret values in plaintext** (A10.21). `terraform plan` compares state to reality on every run, so drift is surfaced continuously rather than as a separate operation, and `terraform apply` reconciles it. That continuous reconciliation is the practical advantage.

The comparison that matters operationally:

- **State ownership is the fundamental difference**, and everything else follows. CloudFormation's model removes an operational burden and a security exposure; Terraform's gives you visibility and control, including `import`, `state mv`, and targeted operations, at the cost of protecting a sensitive file and managing locking.
- **Drift handling**: Terraform's plan-based reconciliation means manual console changes are surfaced on the next plan and reverted on apply. CloudFormation may overwrite or fail depending on the change. Neither prevents drift — **prevention is IAM: humans shouldn't have write access to what IaC manages** (A2.1), which is the actual answer to drift and worth saying.
- **Scope**: Terraform is multi-cloud and has providers for everything, which matters when your platform spans AWS, Kubernetes, GitHub, and a DNS provider — one tool, one workflow.
- **Blast radius**: Terraform's `plan` output is the best pre-change review artefact of the three, and in a regulated change process that's a real advantage — the plan *is* the change record.

The Terraform domain covers state management and module design in depth; here the point is knowing the models differ and being able to justify a choice.

**A14.6 — Regional vs global services and failover implications**

**Global** (or with global components): IAM, Route53, CloudFront, WAF (for CloudFront scope), Organizations, Shield, and — importantly — the STS *global* endpoint. **Regional**: essentially everything else, including KMS keys, S3 buckets (the namespace is global, the data is regional), VPCs, EC2, RDS, and Secrets Manager.

The implications:

- **Global services have a home region, usually `us-east-1`**, and their control planes are exercised there. Historically, `us-east-1` events have affected global service *control planes* — you could still resolve DNS and serve CloudFront, but you might not be able to *change* anything. So your failover runbook should not depend on making IAM or Route53 changes during an incident: **pre-create everything you'll need in the secondary region**, including roles, keys, and DNS records with health-check-driven failover already configured (A8.4).
- **KMS keys are regional** — a secondary region needs its own keys and your data needs to be readable there (A10.13, A10.11). This is one of the most common gaps in a DR design.
- **Secrets and parameters are regional** and must be replicated; Secrets Manager supports multi-region replication for exactly this.
- **AMIs, snapshots, and ECR images are regional** and must be copied ahead of time — a failover that begins with copying an AMI has already blown its RTO.
- **Quotas are per-region** (A11.9), and the secondary's quotas are untested.
- **Use regional STS endpoints** (`sts.eu-west-1.amazonaws.com`) rather than the global one — better latency and it removes a dependency on a single region. Most modern SDKs do this by default, but it's worth verifying.

The framing: **the question "what in my failover path depends on a region other than the one I'm failing into?" is the one that catches most DR design flaws**, and it's a good question to have in your pocket for a resilience review (A11.5).

---

## A15. Awareness only — T3

Know what it is and when you'd reach for it. One or two lines each.

**A15.1 — API Gateway.** Managed API front door for HTTP APIs, REST APIs, and WebSockets: authorisation, throttling, request validation, and stage management. HTTP APIs are cheaper and faster and are the default choice; REST APIs retain features like request validation, WAF integration, and API keys. Note the 29-second integration timeout (A4.7); an ALB is often the simpler answer for a container-backed service.

**A15.2 — CloudFormation StackSets.** Deploys a CloudFormation stack across many accounts and regions from a single definition, with service-managed permissions driven by Organizations OUs. The native mechanism for account baselining (A1.13), and what Control Tower uses under the hood.

**A15.3 — CodePipeline / CodeBuild / CodeDeploy.** AWS's native CI/CD: pipeline orchestration, managed build compute, and deployment automation including blue/green and canary for ECS, Lambda, and EC2. Worth knowing because CodeDeploy's deployment strategies are used even by teams whose pipelines run in GitHub Actions or Jenkins (see the CI/CD domain).

**A15.4 — App Runner, Lightsail, Elastic Beanstalk.** Three levels of "just run my app": App Runner for containers from a repo with no infrastructure, Lightsail for simple fixed-price VPS-style workloads, Beanstalk as the older PaaS over EC2/ASG/ELB. All trade control for speed; the usual concern is the exit path when you outgrow them.

**A15.5 — Athena.** Serverless SQL over data in S3, charged per TB scanned. The standard way to query CloudTrail archives, VPC flow logs, ALB logs, and Cost and Usage Reports (A9.9, A10.16, A12.1). Partitioning and columnar formats (Parquet) are what keep it fast and cheap.

**A15.6 — Kinesis / MSK.** Ordered, replayable, partitioned streaming — Kinesis Data Streams as the managed AWS-native option, MSK as managed Apache Kafka. Reach for them when consumers need to replay history or when you need high-throughput ordered processing (A13.4); Kafka specifically when you need its ecosystem or portability.

**A15.7 — Service Catalog.** A curated catalogue of approved, pre-configured products (CloudFormation templates) that teams can self-provision within guardrails. The mechanism behind Control Tower's Account Factory, and a way to offer paved-road infrastructure without granting broad provisioning permissions.

**A15.8 — Resource Access Manager (RAM).** Shares specific resources across accounts without cross-account roles — most commonly subnets (so workload accounts run in a network account's VPC), Transit Gateways, Route53 Resolver rules (A3.14), IPAM pools (A3.9), and Private CAs. Central to a shared-VPC network design.

**A15.9 — Inspector, Macie, Detective.** Inspector: continuous vulnerability scanning of EC2, container images in ECR, and Lambda (A5.1). Macie: discovers and classifies sensitive data in S3. Detective: graph-based investigation that correlates CloudTrail, flow logs, and GuardDuty findings to speed up root-cause analysis on a finding (A10.22).

**A15.10 — Fault Injection Service (FIS).** Managed chaos engineering — inject instance termination, AZ impairment, API throttling, network latency, or resource exhaustion under controlled conditions with defined stop conditions. The tooling for systematic resilience testing (A11.8), and the natural next step once basic DR tests pass.

**A15.11 — Bedrock.** Managed access to foundation models through one API, with Knowledge Bases for RAG, Agents for tool-use orchestration, and Guardrails for content and topic controls. **T1 if you're targeting AI platform roles**, in which case the things to be fluent in are: model access and quota management as a capacity constraint, per-model token pricing and how it drives cost, VPC endpoints and data-residency guarantees for regulated data, provisioned throughput versus on-demand, CloudWatch and CloudTrail coverage for model invocation, and Guardrails as an enforceable policy layer rather than a prompt convention. The platform-engineering framing that lands: Bedrock is a regional, quota-bound, per-token-priced synchronous dependency — which makes it an availability, cost, and governance problem of exactly the kind this domain covers, not a novel category.

---

## Using this key

A few notes on how to work through it, given the volume:

- **Score against the matrix first, then read only the items you scored 0 or 1.** Reading it end to end is a poor use of time and produces recognition rather than recall.
- **The T1 sections that carry the most interview weight are A1, A2, A3, A10, and A11.** A10 alone is 31 items and is where security-conscious interviewers spend their time in a fintech context.
- **For A1, A10, and A11, the answers above are pitched at articulation rather than learning** — the multi-account audit work is the evidence, and the gap for most people who've done the work is having the finding, the number, and the tradeoff ready in one or two sentences rather than reconstructing it live. Practise those out loud.
- **Where an answer names a failure mode, that's usually the part that reads as experience.** Anyone can define envelope encryption; the KMS quota as an availability dependency (A10.15), the ASG health-check grace period replacement loop (A4.4), and the ACM validation record someone tidied up (A8.6) are what distinguish having run it from having read it.
- **The cross-references are load-bearing.** Interviewers probe by following a topic sideways — a KMS question becomes an S3 question becomes a cost question. Following the links here is good preparation for that.
