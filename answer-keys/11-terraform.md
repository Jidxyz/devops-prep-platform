# Terraform & Infrastructure as Code — Answer Key

Companion to Domain 11 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **cloud service knowledge is Domain 4** (the AWS key), and **pipeline mechanics are the CI/CD domain**. This domain is IaC as a discipline, the tool itself, and the platforms that run it at scale. Where a topic sits on the boundary — OIDC authentication, for instance — the answer covers the Terraform-specific half and points to A2.8 for the rest.

Three things worth knowing about how this domain is interviewed:

- **State (TF3) and troubleshooting (TF12) are where experience shows.** Everyone can write HCL. Far fewer have recovered a corrupted state file, moved resources between states during a refactor, or explained why a plan shows a forced replacement nobody asked for. If you're triaging prep time, start there.
- **TF13 and TF8 are the senior/lead differentiators.** The judgement items — what belongs in Terraform, how to split state, how to bring an unmanaged estate under control, and how IaC fails *organisationally* — are what separate someone who uses Terraform from someone who owns an IaC platform.
- **TF10 and TF11 reward honesty about tradeoffs.** The expected answer to "Spacelift vs TFC vs Atlantis vs plain CI" is not a favourite; it's a decision framework with costs attached.

---

## TF1. IaC fundamentals

**TF1.1 — Declarative vs imperative IaC**

**Imperative** — you specify the sequence of operations: a shell script calling `aws ec2 run-instances`, an Ansible playbook of tasks, a CDK program in the sense of executing statements. **Declarative** — you specify the desired end state and the tool computes the operations: Terraform, CloudFormation.

The consequences, which is what the item asks for:

- **Declarative gives you a diff.** Because the tool knows the desired state and can observe the current state, it can tell you what will change *before* it changes it. `terraform plan` is the single most valuable artefact in this domain, and it exists only because the model is declarative (TF9.2).
- **Declarative is naturally idempotent** (TF1.2). Running it twice against a converged system does nothing. An imperative script run twice may create two of everything.
- **Imperative gives you control over sequence and logic** that declarative models express awkwardly. Anything genuinely procedural — a multi-step migration, a conditional workflow, an operation with checkpoints — is easier imperatively.
- **Declarative hides the operations, which is usually good and occasionally terrible.** You asked for a state; Terraform decided that reaching it requires destroying and recreating your database. That decision is visible in the plan, which is why reading plans carefully is a discipline rather than a formality (TF6.3, TF12.1).

The nuance worth adding: **the distinction is less clean than it looks.** CDK and Pulumi are imperative *programs* that generate declarative *state descriptions* — you write loops and conditionals, but the output is a desired-state document. And Terraform's HCL has expressions, loops, and conditionals, so it isn't purely declarative either. The meaningful line is **whether the tool computes a diff before acting**, not whether the language has control flow.

**TF1.2 — Idempotency, and why it's the core property**

An idempotent operation produces the same result whether applied once or many times. `terraform apply` against converged infrastructure makes no changes.

Why it's *the* core property:

- **It makes re-running safe**, which makes automation possible. A pipeline that can be retried after a network blip, a partial failure, or an ambiguous outcome is only safe if re-running is harmless (TF9.8).
- **It removes the need to know the current state before acting.** You don't ask "has this been applied yet?" — you apply, and the tool converges. That's what allows the same code to create an environment from scratch and to update an existing one.
- **It's the basis of drift correction** (TF1.4). Reconciling to desired state and being idempotent are the same property viewed from two directions.
- **It makes the code the source of truth** rather than a historical record of operations performed.

Where idempotency breaks, which is the more interesting half: **provisioners** (TF2.11) run arbitrary commands with no notion of convergence, so a `local-exec` that appends to a file is not idempotent. **`null_resource`/`terraform_data` with triggers** re-runs on trigger change but the command itself may not be safe to repeat. And **anything with side effects outside Terraform's model** — an API call that increments a counter, a script that sends a notification — sits outside the guarantee. This is the main technical argument for keeping provisioners out of Terraform (TF1.7).

**TF1.3 — Immutable vs mutable infrastructure**

**Mutable** — you change servers in place: patch them, upgrade packages, edit config, restart services. **Immutable** — you never modify a running instance; you build a new artefact and replace it (A4.6, K11.5).

Why immutable wins in most cloud contexts:

- **Determinism.** A machine built from a known image is identical every time. A machine that has been patched for two years is unique, and its state is the accumulated result of every operation ever applied to it — including the ones nobody recorded.
- **Configuration drift becomes impossible** by construction, rather than something you detect and correct (TF1.4).
- **Rollback is redeploying the previous artefact**, not un-applying changes.
- **The build path is exercised constantly**, so you find out it's broken during a routine deploy rather than during an incident.

The costs to acknowledge: replacement is slower than patching for a small change; it requires the workload to tolerate being replaced (K2.12); and stateful components need their data handled separately, which is precisely why "immutable" applies cleanly to compute and awkwardly to databases.

In Terraform terms specifically: **`create_before_destroy`** (TF2.9) is the lifecycle setting that makes immutable replacement safe; **forced replacement in a plan** (TF6.3) is Terraform expressing immutability for a resource whose attribute can't be updated in place; and **`ignore_changes`** is often a signal that something is being managed mutably outside Terraform, which is worth examining rather than accepting.

**TF1.4 — Configuration drift**

Drift is divergence between the declared desired state and the actual state of the infrastructure.

**How it happens:**

- **Console changes during an incident** — the most common and the most forgivable. Someone fixes production at 3am and doesn't reconcile the code afterwards.
- **Another tool managing the same resource** — an autoscaler adjusting a desired count, a Kubernetes controller creating a load balancer, a backup tool adding tags.
- **Cloud provider changes** — defaults changing, resources being modified by AWS-side automation, or attributes populated after creation.
- **Manual "just this once" changes** that were never meant to be permanent.
- **A failed apply** leaving things partially changed (TF9.8).

**How you detect it:**

- **`terraform plan` is the primary detector.** A plan against unchanged code that proposes changes *is* a drift report. That's the whole mechanism, and it's why regular plans matter even when nothing has changed.
- **`terraform plan -refresh-only`** (TF3.11) shows drift specifically, separating "the world changed" from "the code changed".
- **Scheduled drift detection** in CI or a platform like Spacelift or TFC (TF9.6, TF11.5).
- **Cloud-native detection** — AWS Config for compliance drift (A10.23), which is a different thing: Config knows your *policy*, Terraform knows your *intent*. Both matter and they're not the same.

The important distinction to draw: **drift detection tells you something diverged; it doesn't tell you which side is wrong.** Sometimes the code is stale and reality is correct. Deciding is a judgement call, and automatically reverting drift can destroy a legitimate emergency fix (TF9.6).

**TF1.5 — Why manual console changes undermine the model**

The mechanism, stated precisely: Terraform's contract is that **the code describes reality**. Every manual change weakens that contract, and the damage compounds:

- **The next apply may revert it.** Someone's fix disappears at the next unrelated deployment, often days later, with no obvious connection between cause and effect. Debugging that is genuinely nasty.
- **Or the next apply may fail** — a manually created resource with the same name causes "already exists" (TF12.4), and a manually deleted one causes a plan to recreate something unexpectedly (TF12.5).
- **The code stops being trustworthy**, and once people don't trust it they stop reading it, and once they stop reading it they make more manual changes. This is the death spiral, and it's organisational rather than technical.
- **Review and audit are bypassed.** The value of IaC for a regulated environment is that every change is a reviewed, attributable commit. A console change has none of that (TF9.2).
- **Environments diverge.** Prod acquires manual changes that staging doesn't have, so testing in staging stops predicting production behaviour.

The mature framing, which is what separates a senior answer from a lecture: **manual changes are a symptom, not a moral failing.** People make them because the pipeline is too slow, the module doesn't support what they need, or there's a genuine emergency. The remedy is to make the paved road faster than the console (TF13.5) and to have **a documented emergency path that includes reconciliation afterwards** (TF13.6) — not to simply prohibit it. Prohibiting it without providing an alternative produces the same changes, undocumented.

The enforcement mechanism worth naming: **IAM.** If humans don't have write access to what Terraform manages, drift can't happen (A2.1, A14.5). That's the only control that actually works.

**TF1.6 — Terraform, CloudFormation, CDK, Pulumi**

| | Terraform | CloudFormation | CDK | Pulumi |
|---|---|---|---|---|
| Language | HCL (declarative DSL) | YAML/JSON | TypeScript, Python, Java, Go | TypeScript, Python, Go, C# |
| Scope | Multi-cloud + SaaS | AWS only | AWS (CDK) / multi (CDKTF) | Multi-cloud |
| State | You own it | AWS owns it | AWS owns it (via CFN) | Pulumi service or self-managed |
| Diff | `plan` | Change sets | `cdk diff` (via CFN) | `preview` |
| Maturity | Very high, huge ecosystem | Very high on AWS | High | Moderate |

The honest comparison, which is what "honestly" in the item is asking for:

- **Terraform's advantage is breadth and ubiquity.** Providers for AWS, Azure, GCP, Kubernetes, GitHub, Datadog, Cloudflare, Okta — one tool and one workflow for your whole estate. For a platform team, that consistency is worth a great deal, and it's the reason Terraform usually wins even in single-cloud shops.
- **CloudFormation's advantage is that AWS owns the state** (A14.5) — no state file to store, lock, secure, or lose, and automatic rollback on failure. That's a genuine operational simplification, and the reason to prefer it is usually "we don't want to run a state backend". Its disadvantages are YAML's expressiveness, slower support for new services than you'd expect, and stacks that get stuck in `UPDATE_ROLLBACK_FAILED`.
- **CDK's advantage is real programming languages** — abstraction, types, unit tests, IDE support. Its disadvantage is that **the abstraction can hide what's actually deployed**; a few lines of CDK can synthesise hundreds of resources, and debugging means reading generated CloudFormation. It also inherits every CloudFormation limitation.
- **Pulumi's advantage is real languages *and* multi-cloud.** Its disadvantage is a smaller community, so when something breaks there are fewer people who've hit it before — which matters more than feature comparisons suggest.

The judgement to express: **the language question is less important than the operational model.** The real questions are who owns state, how changes get reviewed, and whether your team can debug it at 3am. For most organisations Terraform is the safe default because of ecosystem size and hiring; CloudFormation/CDK is defensible in an all-AWS shop that values the managed state; and choosing Pulumi should be a deliberate decision with a reason, not a preference for TypeScript.

**TF1.7 — Where Terraform stops and configuration management begins**

**Terraform provisions infrastructure**: the VPC, the instance, the load balancer, the database, the IAM role, the DNS record. **Configuration management configures the inside of things**: packages, files, services, users, application deployment.

The boundary and why it exists:

- Terraform's model is **desired state of resources described by an API**. It's excellent at "this VPC should exist with these subnets" and poor at "this file should contain these lines and this service should be restarted if it changes" — because that's not an API-described resource, it's a sequence of operations on a machine.
- Terraform has **no agent and no continuous convergence**. It runs when you run it. Configuration management tools (Ansible, Chef, Puppet) can run continuously and correct drift on the machine.
- **Provisioners are the tempting wrong answer** (TF2.11) — they let you run scripts from Terraform, and they break idempotency, don't appear in the plan, and fail in ways Terraform can't recover from.

The modern answer, which is worth giving because it reframes the question: **in a cloud-native estate the boundary has largely moved.** Instead of Terraform provisioning a server and Ansible configuring it, you **bake the configuration into an image** (Packer, A4.6) or **into a container image**, and Terraform deploys the immutable artefact. Configuration management shrinks to the image build step. So the honest answer is: Terraform provisions, Packer or Docker builds, and Kubernetes or an ASG runs — with Ansible remaining relevant for long-lived servers, on-prem estates, and anything you can't rebuild.

Where they legitimately meet: **user data / cloud-init** for minimal bootstrap, and **`templatefile`** (TF2.7) to render that config from Terraform's knowledge of the infrastructure.

**TF1.8 — OpenTofu and the licence change**

In August 2023, HashiCorp changed Terraform's licence from **MPL 2.0 (open source)** to the **Business Source License (BUSL)**, which restricts using the software to compete with HashiCorp commercially. The community response was a fork of the last MPL-licensed version, initially OpenTF, donated to the Linux Foundation and renamed **OpenTofu**.

What matters practically:

- **The BUSL restriction targets competing commercial offerings**, not ordinary users. A company using Terraform to manage its own infrastructure is unaffected by the letter of the licence. But **the risk is not the current terms, it's the precedent** — a licence that can change once can change again, and for organisations with strict open-source policies or long procurement cycles, that uncertainty is itself the problem.
- **OpenTofu is a drop-in replacement** for Terraform 1.5.x, with the same HCL, the same providers (the registry is separate but mirrors), and the same CLI. Migration is largely changing the binary.
- **The two have diverged since.** OpenTofu has shipped features Terraform hasn't (state encryption natively, early variable evaluation, provider-defined functions arriving in both at different times), and Terraform has continued its own roadmap under IBM's ownership following the acquisition. **They are no longer identical**, and that divergence is growing, so "drop-in" is becoming less true over time.
- **The provider ecosystem is shared** — the AWS provider remains MPL-licensed and works with both, which is what makes the fork viable at all.

The position to hold in an interview: **name the licence change accurately, describe the fork's origin and governance, and treat the choice as a risk and procurement decision rather than a technical one.** Most organisations have stayed on Terraform because the risk is theoretical and switching has a cost; some regulated and open-source-policy-driven organisations have moved. Either is defensible; not knowing the fork exists is not.

---

## TF2. Core language

**TF2.1 — Resources, data sources, variables, outputs, locals**

```hcl
variable "environment" {
  type        = string
  description = "Deployment environment."
}

locals {
  name_prefix = "${var.environment}-payments"
  common_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "payments"
  }
}

data "aws_vpc" "main" {
  tags = { Name = "${var.environment}-vpc" }
}

resource "aws_security_group" "api" {
  name   = "${local.name_prefix}-api"
  vpc_id = data.aws_vpc.main.id
  tags   = local.common_tags
}

output "security_group_id" {
  description = "ID of the API security group."
  value       = aws_security_group.api.id
}
```

The distinctions that matter:

- **Resources are managed** — Terraform creates, updates, and destroys them, and they're in state. **Data sources are read** — Terraform looks them up and never modifies them. Using a data source to reference something another team owns is the right way to consume infrastructure you don't manage.
- **Variables are inputs** (the module's public interface, TF4.1); **outputs are the interface out**, and are what other configurations consume via `terraform_remote_state` (TF3.14).
- **Locals are internal, computed once, not overridable.** Use them for expressions repeated in several places and for composed values. The common mistake is using a variable where a local belongs — if a consumer shouldn't set it, it isn't a variable.

Worth adding: **`default_tags` on the AWS provider** (TF5.1) is better than merging `common_tags` into every resource, and it's the highest-leverage way to enforce a tagging standard (A12.2).

**TF2.2 — The type system and variable validation**

```hcl
variable "instance_config" {
  description = "Per-environment instance configuration."
  type = object({
    instance_type = string
    min_size      = number
    max_size      = number
    subnet_ids    = list(string)
    tags          = optional(map(string), {})
  })

  validation {
    condition     = var.instance_config.max_size >= var.instance_config.min_size
    error_message = "max_size must be greater than or equal to min_size."
  }
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}
```

Types: primitives (`string`, `number`, `bool`), collections (`list(T)`, `set(T)`, `map(T)`), structural (`object({...})`, `tuple([...])`), and `any`.

The points worth making:

- **`any` defeats the purpose.** It accepts anything and fails later with an unhelpful error deep in a resource. Typing properly moves errors to `terraform plan` where they're cheap.
- **`optional(type, default)` in object types** is the feature that makes rich object variables usable — without it, every consumer must specify every field.
- **`validation` blocks fail at plan time with your message**, which is the difference between "the module rejected your input because max_size must be ≥ min_size" and a provider error 200 lines later about an invalid ASG configuration. For a module with many consumers (TF4.1), good validation messages are the main thing that stops you being the support desk.
- **`sensitive = true`** suppresses the value in output — with the caveat that it does *not* remove it from state (TF7.1).
- **`nullable = false`** prevents a caller passing null explicitly.

**TF2.3 — `count` vs `for_each`, and why `for_each` is usually better**

```hcl
# count — indexed by position
resource "aws_instance" "web" {
  count         = 3
  instance_type = "t3.micro"
}
# addresses: aws_instance.web[0], [1], [2]

# for_each — keyed by a meaningful identifier
resource "aws_instance" "web" {
  for_each      = toset(["api", "worker", "scheduler"])
  instance_type = "t3.micro"
  tags          = { Name = each.key }
}
# addresses: aws_instance.web["api"], ["worker"], ["scheduler"]
```

**`for_each` is usually better because the resource address is stable and meaningful.** With `count`, the address is the position in a list; with `for_each`, it's a key. That single difference determines what happens when the collection changes (TF2.4).

When each is right:

- **`count` is fine for a genuinely positional or conditional case** — `count = var.enabled ? 1 : 0` is the idiomatic conditional resource, and a homogeneous set where the ordering genuinely doesn't matter and never shrinks from the middle.
- **`for_each` for anything keyed** — per-subnet, per-environment, per-team, per-account. Which is almost everything real.

The practical gotchas:

- **`for_each` keys must be known at plan time.** Deriving keys from another resource's computed attribute produces the "Invalid for_each argument" error (TF12.9), and it's one of the most common Terraform frustrations.
- **`for_each` accepts a map or a set of strings**, not a list — hence `toset()`. And a set of strings means `each.key == each.value`.
- **Converting a resource from `count` to `for_each`** rewrites every address, so Terraform sees destroys and creates. That's exactly what `moved` blocks are for (TF2.12).

**TF2.4 — How `count` index shifting destroys and recreates resources**

The failure, concretely. Given:

```hcl
variable "names" { default = ["alpha", "beta", "gamma"] }
resource "aws_iam_user" "u" {
  count = length(var.names)
  name  = var.names[count.index]
}
```

State holds `u[0]=alpha`, `u[1]=beta`, `u[2]=gamma`. Now **remove `alpha`** from the list:

- `u[0]` should now be `beta` — Terraform sees the resource at index 0 has changed name from alpha to beta, and for a resource where name forces replacement, **destroys and recreates it**.
- `u[1]` becomes `gamma` — destroyed and recreated.
- `u[2]` no longer exists — destroyed.

**Removing one item from the middle of a list destroys and recreates everything after it.** For IAM users that's noisy; for stateful resources — RDS instances, EBS volumes, anything with data — it's catastrophic, and it's the kind of thing you discover by reading a plan carefully at 4pm on a Friday.

With `for_each` on a set, removing `alpha` produces exactly one destroy — `u["alpha"]` — and leaves `u["beta"]` and `u["gamma"]` untouched, because their addresses never depended on position.

The lesson to state: **`count` couples resource identity to list position, and list position is not stable.** This is the single strongest argument for `for_each`, and being able to walk this example is the difference between reciting "for_each is better" and demonstrating why.

The mitigation if you're stuck with `count`: `moved` blocks to re-map addresses (TF2.12), or restructure to `for_each` in a planned refactor.

**TF2.5 — Dynamic blocks, and when they hurt**

```hcl
resource "aws_security_group" "api" {
  name = "api"

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port       = ingress.value.port
      to_port         = ingress.value.port
      protocol        = "tcp"
      cidr_blocks     = ingress.value.cidrs
      description     = ingress.value.description
    }
  }
}
```

Dynamic blocks generate repeated nested blocks from a collection. Legitimate uses: a variable number of security group rules, listener rules, or lifecycle rules where the count genuinely varies by consumer.

**When they hurt readability more than they help** — the substance of the item:

- **They obscure what's actually created.** A static block you can read; a dynamic block requires mentally executing the loop against the input to know what exists. In a module with several nested dynamics, that becomes genuinely hard.
- **Error messages get worse**, referring to generated content rather than to source lines.
- **Nested dynamic blocks** (a dynamic inside a dynamic) are almost always a sign the abstraction is wrong. They're extremely hard to read and to debug.
- **They're frequently used to avoid writing two or three static blocks**, which is a bad trade — three explicit blocks are more readable than one dynamic that produces three.

The rule to state: **use a dynamic block when the number of blocks genuinely varies at the consumer's discretion; write them statically when it doesn't.** And if a module needs deeply nested dynamics to serve its consumers, the module is probably trying to be too general (TF4.5) — separate modules or accepting duplication is often the better answer.

**TF2.6 — For expressions, splat, and conditionals**

```hcl
# for over a list → list
locals {
  upper_names = [for n in var.names : upper(n)]
}

# for with a filter
locals {
  prod_subnets = [for s in var.subnets : s.id if s.environment == "prod"]
}

# for over a map → map (note the => )
locals {
  by_name = { for s in var.subnets : s.name => s.id }
}

# splat — shorthand for a simple projection
locals {
  ids  = aws_instance.web[*].id            # equivalent to [for i in aws_instance.web : i.id]
}

# conditional
locals {
  instance_type = var.environment == "prod" ? "m5.large" : "t3.micro"
}
```

Points worth knowing: **splat only works on lists and sets of resources**, not on maps — so a `for_each` resource needs `values(aws_instance.web)[*].id` or a `for` expression. **A `for` producing a map with duplicate keys is an error**, which is a common surprise when keying by a non-unique attribute. And **conditionals evaluate both branches for type-checking**, so a conditional referencing an attribute that doesn't exist in one branch fails even when that branch isn't taken — the workaround is `try()` (TF2.7).

**TF2.7 — Common functions**

```hcl
try(var.config.optional_field, "default")        # first non-erroring expression
coalesce(var.name, var.fallback_name, "default") # first non-null, non-empty
lookup(var.map, "key", "default")                # map access with default
merge(local.common_tags, var.extra_tags)         # right-hand wins on conflict
flatten([for s in var.subnets : s.cidrs])        # collapse nested lists
templatefile("${path.module}/user-data.sh.tftpl", {
  cluster_name = var.cluster_name
  region       = var.region
})
```

The distinctions that come up:

- **`try` vs `coalesce`** — `try` catches *errors* (a missing attribute, a wrong type); `coalesce` selects the first *non-null* value. Reaching for `coalesce` when you need `try` produces an error rather than a default. And `try` swallowing genuine mistakes is worth being careful about — it's easy to mask a typo.
- **`lookup` on a map is largely superseded** by `var.map["key"]` with `try`, and `lookup` with only two arguments errors on a missing key rather than defaulting.
- **`merge` is how tag inheritance works**, and the ordering matters — the last map wins, so consumer-supplied tags should come last if they're meant to override.
- **`templatefile` is the right way to render user data, policy documents, and config files**, and it's far better than string concatenation. Use the `.tftpl` extension by convention. The one caution: a template with heavy logic is a sign the logic belongs in HCL, not in the template.
- Others worth knowing: `jsonencode`/`jsondecode` (the correct way to write IAM policies rather than heredocs), `cidrsubnet` for subnet maths, `one()` for collapsing a single-element list, `sensitive()`, and `can()` for validation conditions.

**TF2.8 — Implicit vs explicit dependencies**

**Implicit** — Terraform builds the dependency graph from references. Because `aws_instance.web` references `aws_security_group.api.id`, Terraform knows the security group must exist first. **This is the correct mechanism and covers the overwhelming majority of cases**, and it's why you should reference attributes rather than hardcoding values you already know.

**Explicit** — `depends_on` declares a dependency Terraform can't infer:

```hcl
resource "aws_instance" "app" {
  # ...
  depends_on = [aws_iam_role_policy.app_permissions]
}
```

**When it's genuinely required**: a dependency that exists in the real world but not in the configuration. The canonical example is IAM — an instance's user data calls an API that needs a policy attached, but nothing in the instance's config references the policy, so Terraform may create them in parallel and the instance boots before it has permissions. Similar: a resource that requires a service to be enabled, or an S3 bucket policy that must exist before something writes to the bucket.

The cautions:

- **`depends_on` is over-used as a band-aid** for problems that are really a missing reference. If you can reference the attribute, do — it's more precise and self-documenting.
- **`depends_on` on a module** makes everything in the module depend on the target, which is coarse and can serialise things unnecessarily, slowing applies.
- **`depends_on` with computed values forces the whole resource to be deferred** — Terraform can't know the dependency's outcome at plan time, so attributes that would otherwise be known become unknown, which cascades and can produce a much less informative plan.

**TF2.9 — Lifecycle meta-arguments**

```hcl
resource "aws_launch_template" "app" {
  lifecycle {
    create_before_destroy = true
    prevent_destroy       = false
    ignore_changes        = [tags["LastScanned"]]
  }
}
```

- **`create_before_destroy`** — create the replacement before destroying the original. Essential for anything in a traffic path, and required for resources that can't be recreated with the same name while the original exists. **The gotcha: it's contagious.** Any resource depending on one with `create_before_destroy` usually needs it too, or you get a cycle error (TF12.3). Name collisions are the other issue — resources with a fixed `name` can't be created alongside their replacement, so you need `name_prefix` or a generated suffix.
- **`prevent_destroy`** — the plan errors if anything would destroy this resource. A genuine safety net for databases and state buckets. **Its limitation: it blocks the plan entirely**, so you can't proceed even for an unrelated change to the same resource — and removing it means a code change, which is deliberate friction. It also doesn't protect against `terraform destroy` on a config where the resource has been removed from code entirely.
- **`ignore_changes`** — stop Terraform reverting attributes changed elsewhere. Legitimate for `desired_count` managed by autoscaling, tags applied by other tooling, or an AMI ID that another process updates. **The risk: it hides real drift.** `ignore_changes = all` is almost always wrong and means the resource isn't really managed by Terraform. Each ignored attribute is a small admission that something else owns it, which should be a deliberate decision.

`replace_triggered_by` is TF2.10.

**TF2.10 — `replace_triggered_by`**

```hcl
resource "aws_instance" "app" {
  lifecycle {
    replace_triggered_by = [
      aws_launch_template.app.latest_version,
      terraform_data.deployment_version
    ]
  }
}
```

It forces replacement of a resource when a referenced resource or attribute changes — even though nothing about this resource's own configuration changed.

**A real use**: an instance or task that must be recreated when its configuration source changes but which doesn't reference it in a way Terraform sees as replacement-forcing. For example, an ECS service that should be redeployed when a ConfigMap-equivalent parameter changes, or an instance that must be rebuilt when a launch template version increments but whose own arguments are unchanged.

The pattern it replaces: the old `null_resource` with `triggers` plus a provisioner, or manually tainting the resource (TF6.9). `replace_triggered_by` expresses the intent declaratively and appears in the plan, which the alternatives don't.

The caution: it's a blunt instrument — it forces full replacement, not an update — so it's inappropriate where a cheaper in-place update exists, and it can cause surprising cascading replacements if the trigger changes more often than you expect. Referencing `terraform_data` with an explicit input is the controlled way to use it, since you decide exactly when the trigger value changes.

**TF2.11 — Provisioners and why they're a last resort**

```hcl
resource "aws_instance" "app" {
  provisioner "remote-exec" {
    inline = ["sudo apt-get update", "sudo apt-get install -y nginx"]
  }
  provisioner "local-exec" {
    when    = destroy
    command = "./deregister.sh ${self.id}"
  }
}
```

HashiCorp's own documentation describes them as a last resort. The reasons:

- **They break the plan/apply contract.** A provisioner's effects don't appear in the plan at all, so `terraform plan` no longer tells you what will happen — which is the tool's single most valuable property (TF1.1).
- **They break idempotency** (TF1.2). The commands run once at creation and are never reconciled. Change the script and nothing happens to existing resources.
- **Failure semantics are bad.** A failed provisioner marks the resource **tainted**, so the next apply destroys and recreates it — meaning a transient SSH failure destroys a working instance. `on_failure = continue` avoids that and silently ignores real failures.
- **They require connectivity and credentials from wherever Terraform runs** — SSH or WinRM reachability from a CI runner into a private subnet, plus key management. That's an unpleasant coupling.
- **Destroy-time provisioners are especially fragile** — they can't reference variables or other resources, only `self`, and if they fail the resource can't be destroyed.

**The alternatives, in order of preference**: bake it into the image (Packer, A4.6); use **cloud-init / user data** rendered with `templatefile` (TF2.7), which is the provider's own mechanism and appears in the plan; use a configuration management tool triggered separately (TF1.7); use the cloud's own automation (SSM Automation, A4.9). If you genuinely need to run something local, **`terraform_data` with an explicit trigger** is cleaner than `null_resource` and at least makes the re-run condition visible.

**TF2.12 — `moved` blocks and refactoring without destroying**

```hcl
moved {
  from = aws_instance.web
  to   = aws_instance.api
}

moved {
  from = aws_security_group.this[0]
  to   = aws_security_group.this["api"]
}

moved {
  from = module.old_networking
  to   = module.networking
}
```

The problem it solves: Terraform identifies resources by their **address in configuration**. Rename a resource, move it into a module, or change `count` to `for_each` (TF2.3) and the address changes — so Terraform sees the old address gone (destroy) and a new one (create), even though it's the same infrastructure.

Before `moved` blocks, the fix was `terraform state mv` (TF3.10), run manually by whoever applied, against every state file, remembered correctly. **`moved` blocks put the refactor in code**, so it's reviewed, applied automatically, and works for every consumer of a module — which is what makes safe module refactoring possible at all (TF4.9).

The mechanics: they're **declarative and idempotent** — once the move has happened, the block is a no-op. Keep them for a release cycle or two so all consumers pick them up, then remove them. They can be chained (A→B→C). And crucially, **the plan will show the move explicitly** as a "moved" line rather than destroy/create, which is your confirmation it worked before you apply.

**TF2.13 — `import` block vs the CLI import command**

```hcl
import {
  to = aws_s3_bucket.legacy
  id = "acme-legacy-reports"
}

resource "aws_s3_bucket" "legacy" {
  bucket = "acme-legacy-reports"
}
```

`terraform plan` then shows what would be imported and any configuration differences; `terraform apply` performs the import.

The differences from `terraform import <address> <id>` (TF3.8):

- **It's declarative and in code**, so it's reviewed in a PR like any other change, and it runs in the pipeline rather than requiring someone with local state access.
- **It's planned first.** You see exactly what will be imported and — critically — **what Terraform would change about it afterwards**, before committing. CLI import writes to state immediately and you only discover the config mismatch on the next plan.
- **It supports `for_each`**, so you can import many resources in one operation, driven by a map. Importing forty existing resources with the CLI is forty commands; with an import block and a for_each it's one apply. This matters enormously for TF13.4.
- **It can generate configuration** — `terraform plan -generate-config-out=generated.tf` writes HCL for the imported resources, which is a genuine time-saver for a large estate even though the output needs tidying.

The CLI command still has a place for quick one-offs and for situations where you can't run a plan. But **import blocks are the right default now**, and knowing the `-generate-config-out` flag is a good practical signal.

**TF2.14 — `check` blocks, preconditions and postconditions**

```hcl
resource "aws_instance" "app" {
  lifecycle {
    precondition {
      condition     = data.aws_ami.selected.architecture == "x86_64"
      error_message = "The selected AMI must be x86_64 for this instance type."
    }
    postcondition {
      condition     = self.private_ip != ""
      error_message = "Instance must have a private IP."
    }
  }
}

check "api_health" {
  data "http" "endpoint" {
    url = "https://${aws_lb.api.dns_name}/healthz"
  }
  assert {
    condition     = data.http.endpoint.status_code == 200
    error_message = "API health endpoint did not return 200."
  }
}
```

The distinction:

- **Preconditions** are checked before the resource is created or updated — asserting assumptions about inputs and data sources. They fail the plan or apply.
- **Postconditions** are checked after — asserting guarantees about the result. They fail the apply.
- **`check` blocks are non-blocking.** They produce a **warning**, not an error, and they run on every plan and apply. That's the key difference and the reason they exist: they let you assert things about the world — an endpoint responding, a certificate not near expiry — without a transient failure blocking an unrelated deployment.

Where each fits: **preconditions for input assumptions** (this module requires a VPC with DNS enabled), **postconditions for guarantees to consumers** (this module always returns a non-empty subnet list), and **`check` blocks for continuous verification** of things outside Terraform's control.

The value to articulate: these move failures from "the apply succeeded and the thing doesn't work" to "the plan told me why". For a module with many consumers, preconditions with good error messages are one of the highest-value things you can add (TF4.1), because they turn support requests into self-service.

---

## TF3. State

The section that most reliably separates people who have run Terraform in anger from people who have used it.

**TF3.1 — What state is and why Terraform can't work without it**

State is Terraform's record of **which real-world objects correspond to which configuration addresses**, plus a cached copy of their attributes.

Why it's structurally necessary:

- **Mapping.** Configuration says `aws_instance.web`; the world has `i-0abc123`. Nothing in AWS records that this instance is the one your config means. Without state, Terraform cannot know whether to create a new instance or update an existing one.
- **Deletion detection.** If you remove a resource from configuration, Terraform knows to destroy it *only because state says it existed*. With no state, removing code would simply mean Terraform stops knowing about the resource — it would leak, not be destroyed.
- **Dependency ordering on destroy.** The configuration is gone, so the dependency graph for teardown has to come from state.
- **Performance.** State caches attributes so a plan doesn't need to read everything from the provider — relevant on large state (TF8.6).

The counterargument people raise, worth addressing: *couldn't Terraform just query the API and match by tags?* In principle for some resources, but it breaks immediately — many resources have no reliable natural key, tags can be edited, several resources can match, and some providers have no listable API. **CloudFormation avoids the state file problem by having AWS maintain the equivalent server-side** (TF1.6, A14.5) — the state doesn't disappear, it just isn't yours to manage.

The implication that flows from all of this: **state is as critical as the infrastructure it describes.** Losing it doesn't lose your infrastructure, but it loses your ability to manage it (TF3.12).

**TF3.2 — Why state contains secrets, and what that implies**

Terraform stores **the full attributes of every resource** in state, including attributes the provider returns that happen to be sensitive: RDS `password`, IAM access keys, generated private keys from `tls_private_key`, `random_password` values, Secrets Manager secret values if you read them via a data source, and any variable value that flows into a resource argument.

Marking a variable `sensitive = true` **suppresses it from CLI output and plan display. It does not remove it from state** (TF7.1). This is the single most misunderstood thing in this area.

What it implies:

- **The state backend is a credential store** and must be secured as one: encryption at rest with a CMK you control (A10.1), TLS in transit, and **tight IAM** — read access to the state bucket is read access to every secret in it (TF7.3).
- **Never commit state to git.** Ever. Including in history — a `.tfstate` in a repo means rotating everything it contains (A10.30).
- **Bucket access logging and versioning**, so you know who read it and can recover it (TF3.3).
- **Split state to limit exposure** (TF3.6) — the production database state file should not be readable by everyone who can read the DNS state file.
- **Prefer not to have the secret in Terraform at all.** Generate credentials outside Terraform and reference them by ARN; use IAM database authentication (A7.8); let the resource generate its own password with `manage_master_user_password` on RDS, which puts the value straight into Secrets Manager and never through state. **The best mitigation is architectural, not access control** — and that's the answer that shows seniority.

OpenTofu's native **state encryption** (TF1.8) is worth naming as a genuine differentiator here.

**TF3.3 — Configuring a remote backend with encryption and versioning**

```hcl
terraform {
  backend "s3" {
    bucket       = "acme-tfstate-prod"
    key          = "platform/networking/terraform.tfstate"
    region       = "eu-west-1"
    encrypt      = true
    kms_key_id   = "arn:aws:kms:eu-west-1:111122223333:key/abcd-..."
    use_lockfile = true          # S3-native locking, replaces DynamoDB
  }
}
```

The backing resources and why each:

- **S3 bucket with versioning enabled** — versioning is your recovery path from a corrupted or truncated state write (TF3.12). This is not optional.
- **Encryption with a customer-managed KMS key**, so key policy is a second authorisation layer over the secrets in state (A10.1, A10.3).
- **Block Public Access at account level**, and a bucket policy denying non-TLS (A6.4).
- **Locking** — historically a DynamoDB table with `LockID` as the partition key; **S3 now supports native conditional-write locking via `use_lockfile`**, which removes the DynamoDB dependency. Knowing that's changed is a good currency signal.
- **Access logging** and, in a regulated environment, **replication to a separate account** so state survives account compromise (A1.16).
- **Least-privilege IAM** on the state path — per-state-file prefixes so a team's role can only read its own (TF7.3).

The bootstrapping problem worth naming: **the state bucket itself has to come from somewhere.** Either create it manually once and import it (TF2.13), or manage it in a small separately-stated bootstrap configuration with local state committed carefully — everyone solves this once, and describing it shows you've actually set one up.

Also: `-backend-config` for keeping backend values out of code and varying them per environment (TF6.1), since the backend block itself cannot use variables — a real and frequently-hit limitation.

**TF3.4 — State locking and what happens without it**

Terraform acquires a lock before any operation that writes state. Without it, **two concurrent applies read the same state, each makes changes, and each writes back a state file that doesn't include the other's changes.** The second write wins and the first apply's resources are now **orphaned** — they exist in the cloud, they're not in state, and nothing manages them. Worse, both may attempt conflicting operations on the same resources simultaneously, producing partial failures and genuinely confusing wreckage.

This is the most damaging class of Terraform failure, because the damage is silent — nothing errors, and you discover it weeks later when a plan proposes creating something that already exists (TF12.4).

The mechanism: S3 native locking or a DynamoDB table (TF3.3), or the backend's own mechanism (TFC, Spacelift, and Terragrunt all handle it). **Not all backends support locking** — the local backend and plain HTTP backends may not, which is a reason to check rather than assume.

The related control at pipeline level: **serialise runs against a given state** (TF9.4), because locking makes concurrent runs *fail* rather than *corrupt*, and a failed pipeline run is still a disruption you'd rather avoid.

**TF3.5 — Recovering from a stuck lock safely**

A lock persists when the process holding it died without releasing — a killed CI job, a lost network connection, a laptop closed mid-apply.

```bash
terraform force-unlock <LOCK_ID>
```

**The safety procedure before running it**, which is the actual answer:

1. **Read the lock information** — Terraform's error message includes who holds it, from where, the operation, and when it was created. That's usually enough to identify the run.
2. **Confirm the holder is genuinely dead.** Check the CI job, ask the person. **This is the whole point** — force-unlocking a lock held by a *running* apply lets a second apply start concurrently, which is precisely the corruption scenario in TF3.4. A slow apply is not a stuck lock.
3. **If the apply was interrupted mid-flight, assume state may be inconsistent** with reality (TF9.8). After unlocking, run a plan and read it very carefully before applying anything — resources may have been created without being recorded.
4. **Force-unlock, then verify** with `terraform plan` before proceeding.

The preventive measures: **CI timeouts shorter than any plausible apply**, so jobs don't hang indefinitely holding locks; running applies in CI rather than from laptops, so the holder is always identifiable and killable; and alerting on locks held beyond a threshold.

**TF3.6 — How state should be split, and the blast-radius reasoning**

The axes to split along, roughly in order of importance:

1. **Environment** — prod state separate from non-prod, always. Non-negotiable: it's the primary blast-radius boundary and the primary access-control boundary.
2. **Account and region** — follows naturally from environment in a multi-account estate (A1.1).
3. **Rate of change / lifecycle** — networking, IAM, and DNS change rarely; application infrastructure changes daily. Putting them in one state means every application deploy runs a plan against the VPC, which is slow (TF8.6) and risks an unrelated destroy.
4. **Ownership** — a team should be able to apply their own state without needing permission over someone else's resources.
5. **Blast radius of a mistake** — the question to ask is: *if someone ran `terraform destroy` against this state, or an apply went badly wrong, what would be lost?* If the answer is "the entire production estate", the state is too big.

The reasoning to articulate: **a state file is a unit of atomic change, a unit of locking, a unit of access control, and a unit of failure.** Those four things should align with how your organisation actually works. A monolithic state means every change locks everyone out, every plan is slow, everyone needs broad permissions, and one bad apply can take out everything.

The counter-pressure is TF3.14 and TF8.4: **splitting creates dependencies between states**, which have to be managed via remote state or data sources, and that coupling has its own costs. Which is why TF8.3 frames it as a genuine tradeoff rather than "split as much as possible".

A workable default: `account/region/environment/component`, where component is something like networking, security, data, or a service group.

**TF3.7 — Workspaces, and why they're a poor fit for environments**

CLI workspaces let one configuration have multiple state files, selected with `terraform workspace select`, with `terraform.workspace` available as an interpolation.

Why they're a poor fit for environment separation — and this is a question people get wrong:

- **All workspaces share one backend and one set of credentials.** Dev and prod state sit in the same bucket, and whoever can run against dev can run against prod. **There is no access-control boundary**, which is the main thing you want from environment separation.
- **All workspaces share one configuration.** Environments legitimately differ structurally, not just in values — prod has replicas, backups, and monitoring that dev doesn't. Expressing that with `terraform.workspace` conditionals produces exactly the sprawling conditionals that make code unreadable, and worse, **the code you test in dev is not the code that runs in prod**.
- **It's easy to be in the wrong workspace.** `terraform workspace select` is stateful and invisible in the code; applying to prod because you forgot to switch is a real and recurring incident. Compare with a directory-per-environment layout where the path tells you where you are.
- **Provider configuration is shared**, so multi-account deployment requires conditionals in the provider block, which is awkward.

**Where workspaces are genuinely appropriate**: short-lived parallel instances of the *same* thing with the *same* configuration and the *same* credentials — ephemeral PR environments (TF9.9), or a developer spinning up a personal copy. That's their actual design purpose.

**The alternative to recommend**: a directory or repository per environment, with shared modules and per-environment `.tfvars` and backend configs (TF8.1, TF8.2). More files, far more explicit, and the separation is real rather than conventional.

Note also that **TFC/TFE workspaces are a different concept entirely** despite the name (TF10.1) — they're a first-class unit with their own variables, credentials, and permissions, and they *are* an appropriate environment boundary.

**TF3.8 — Importing an existing resource into state**

Two mechanisms — the import block (TF2.13) is now preferred; the CLI form:

```bash
terraform import aws_s3_bucket.legacy acme-legacy-reports
terraform import 'aws_instance.web["api"]' i-0abc123def456
```

The workflow that actually works:

1. **Write the resource block first** — even minimally. Import needs an address to import *to*; it does not generate configuration (the CLI form, at least).
2. **Import.**
3. **Run `terraform plan` and expect a diff.** This is the step people are unprepared for: your hand-written config almost never matches the real resource exactly. The plan shows the gaps.
4. **Reconcile until the plan is clean** — add the missing arguments until Terraform proposes no changes. **A clean plan is the definition of a successful import**, and stopping before that means the next apply will "fix" the resource to match your incomplete config, potentially destructively.
5. **Only then commit.**

The details that matter:

- **The import ID format is resource-specific** and documented per resource — sometimes the ARN, sometimes the name, sometimes a composite like `vpc-id/sg-id`. Getting it wrong is the usual first failure.
- **Some resources can't be imported at all**, and some import incompletely (attributes the API doesn't return).
- **Child resources must be imported separately** — importing a VPC doesn't bring its subnets, route tables, or security groups. A realistic import of an existing estate is dozens of resources (TF13.4), which is exactly why import blocks with `for_each` and `-generate-config-out` matter.
- **Import is idempotent-ish but not free**: importing a resource already in state errors.

**TF3.9 — Removing a resource from state without destroying it**

```bash
terraform state rm aws_s3_bucket.legacy
# or, declaratively:
removed {
  from = aws_s3_bucket.legacy
  lifecycle { destroy = false }
}
```

The resource stays in the cloud; Terraform simply forgets it. Legitimate uses:

- **Handing ownership to another team or another state file** (the first half of TF3.10).
- **Decommissioning management** without decommissioning the resource — you want to stop managing it but not delete it.
- **A resource that was destroyed outside Terraform** and you want state to reflect reality without a destroy attempt (though `plan -refresh-only` usually handles that, TF3.11, TF12.5).
- **Escaping a broken resource** that can't be updated or destroyed cleanly, as a step in a recovery.

The cautions:

- **The resource becomes unmanaged and invisible.** Nothing will detect drift on it, nothing will patch it, and eventually nobody will remember why it exists. Orphaned resources accumulate cost and risk (A12.3).
- **If it's still referenced in configuration, the next plan will try to create it** — and fail with "already exists" (TF12.4). Remove it from state *and* from code, together.
- **`state rm` is immediate and writes state.** Back up first (`terraform state pull > backup.tfstate`).

**The `removed` block is the modern, reviewable form** — it's in code, it goes through PR review, and `lifecycle { destroy = false }` makes the intent explicit. That's a meaningful improvement over an undocumented CLI command run by one person, and worth naming.

**TF3.10 — Moving a resource between state files**

```bash
# pull both states locally
terraform state pull > source.tfstate     # in the source directory
# in the target directory
terraform state pull > target.tfstate

# move, operating on local files
terraform state mv -state=source.tfstate -state-out=target.tfstate \
  aws_s3_bucket.data aws_s3_bucket.data

# push both back
terraform state push target.tfstate       # in target
terraform state push source.tfstate       # in source
```

The safer and more common approach in practice: **`state rm` from the source, then `import` into the target** (TF3.9 + TF3.8). It's more steps but each step is independently verifiable, and it doesn't involve pushing hand-edited state files.

The procedure and its risks:

1. **Back up both state files first.** Non-negotiable — this is one of the genuinely risky operations.
2. **Lock both**, or ensure nobody else runs against either during the move.
3. **Move the configuration code too**, in the same change.
4. **Plan both** afterwards and expect *no* changes in either. A destroy in the source plan or a create in the target plan means the move didn't take.

The specific hazards: **cross-state dependencies break** — if the target state's resources reference the moved resource through `terraform_remote_state`, ordering matters (TF3.14, TF8.4). **Provider configuration must match** — moving a resource to a state with a different provider alias or region produces confusing results. And **there's a window where the resource is in both states or neither**, which is why locking and speed matter.

This operation is common during a state-splitting refactor (TF3.6), and doing it for fifty resources is a scripted, rehearsed exercise, not an afternoon of manual commands.

**TF3.11 — `terraform refresh` and the refresh-only plan**

**`terraform refresh` is deprecated** as a standalone command because it **writes state immediately with no review** — it updates state to match reality, and if reality is wrong (a resource deleted by mistake), you've just recorded that mistake with no opportunity to object.

**`terraform plan -refresh-only`** is the replacement and the right tool: it shows you **what has changed in the real world since the last apply**, as a reviewable plan, without proposing any configuration-driven changes.

```bash
terraform plan -refresh-only
terraform apply -refresh-only     # accept reality into state
```

Why this distinction matters:

- **It separates two questions**: "what has drifted?" (refresh-only) and "what does my code change?" (normal plan). A normal plan conflates them, so you can't tell whether a proposed change is because you edited code or because someone edited the console.
- **It's the cleanest drift-detection mechanism** (TF1.4, TF9.6).
- **It lets you accept reality deliberately** — a resource was legitimately changed outside Terraform and you want state to reflect that without reverting it.

Also worth knowing: **`-refresh=false`** on a normal plan skips refreshing entirely, which is the standard mitigation for very slow plans on large state (TF8.6) — at the cost of planning against a possibly-stale view. And **refresh happens automatically at the start of every plan and apply by default**, which is why plans get slow as state grows.

**TF3.12 — Recovering from a corrupted or lost state file**

**Corrupted** (truncated write, invalid JSON, interrupted push):

1. **Restore the previous version from S3 versioning** (TF3.3). This is why versioning is mandatory and it's the answer 90% of the time — recovery is one `aws s3api get-object --version-id` away.
2. If versioning isn't there, check for a local `terraform.tfstate.backup`, or the backup Terraform writes before state-modifying operations.
3. **After restore, run `terraform plan -refresh-only`** to see what has changed since that version, and reconcile.

**Lost entirely** — the harder case, and the answer should be a plan rather than a shrug:

1. **Stop all pipelines** immediately so nothing applies against empty state and starts recreating things.
2. **Inventory what exists** in the cloud — the console, `aws resourcegroupstaggingapi get-resources`, Config (A10.23), or a script (A14.4). Tags applied by Terraform (`ManagedBy = terraform`) make this dramatically easier, which is an argument for `default_tags` you can make in advance.
3. **Rebuild state by importing** every resource (TF3.8), which is where `import` blocks with `for_each` and `-generate-config-out` earn their keep (TF2.13).
4. **Iterate until `terraform plan` is clean**, which will take longer than expected.
5. If the estate is small and disposable, **recreating from scratch may genuinely be faster** than importing — a legitimate answer for a dev environment and never for prod.

The preventive points to close on: **versioning, replication, backups, and restricted delete permissions on the state bucket** (TF7.3), plus **object lock in a regulated environment**. And the framing: **state is a tier-one asset** and belongs in the backup and DR conversation alongside databases (A11.7).

**TF3.13 — Manual state editing: the risk and when it's unavoidable**

Manual editing means pulling state, editing JSON, and pushing:

```bash
terraform state pull > state.json
# edit
terraform state push state.json
```

**The risks**: state has a `serial` and a `lineage` that Terraform uses to detect conflicts — pushing an edited file with the wrong serial either fails or, with `-force`, overwrites someone else's changes. Malformed JSON corrupts state entirely. And the edit is unreviewed, unlogged, and done by one person under pressure, which is the classic setup for making an incident worse.

**When it's unavoidable** — and there are genuine cases:

- **A resource whose provider schema changed incompatibly**, leaving state unreadable by the new provider version (TF5.5).
- **A corrupted entry** that `state rm` can't remove because parsing fails.
- **Removing a stale `depends_on` or provider reference** after a `replace-provider` didn't fully take.
- **Recovering from a partial state move** (TF3.10) that left a resource in an inconsistent form.

The discipline when you must:

1. **Back up first**, always, to a file you keep.
2. **Prefer the `terraform state` subcommands** (`mv`, `rm`, `replace-provider`) over hand-editing — they understand the format and maintain serial and lineage correctly. Reach for raw JSON only when no subcommand does the job.
3. **Lock, or ensure exclusivity.**
4. **Have a second person review the diff** before pushing. This is a change to production, and it deserves the same scrutiny as one.
5. **Plan immediately afterwards** and read it fully.
6. **Write down what you did** — it will matter later.

The framing that signals maturity: **needing to hand-edit state is usually evidence of an earlier process failure** — a missing `moved` block, a concurrent apply without locking, a provider upgrade done carelessly. Fixing the underlying process matters more than getting good at editing JSON.

**TF3.14 — `terraform_remote_state` and output coupling**

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "acme-tfstate-prod"
    key    = "platform/networking/terraform.tfstate"
    region = "eu-west-1"
  }
}

resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.network.outputs.private_subnet_ids[0]
}
```

It reads another state file's outputs, and it's the standard mechanism for wiring split states together (TF3.6, TF8.4).

**Why outputs create coupling**, which is the substance of the item:

- **Outputs become a published API.** Once another state consumes an output, you cannot rename or remove it without breaking them — and unlike a module interface, there's no versioning and no deprecation mechanism. You find out you broke someone when their pipeline fails.
- **The consumer needs read access to the producer's entire state file**, not just the outputs — which means read access to every secret in it (TF3.2). That's a real and frequently-overlooked security consequence, and on its own is a strong argument against the pattern for sensitive states.
- **It creates an ordering dependency** that Terraform doesn't enforce. The producer must be applied before the consumer, and nothing checks — you get a stale value or a missing output, and the error is unhelpful.
- **Changes propagate implicitly.** A change to a producer output silently changes consumer behaviour on their next apply, at a time they didn't choose.

**The alternatives, in preference order:**

1. **Data sources that query the provider directly** — look up the VPC by tag rather than reading another state. **This is usually the better answer**: it needs no state access, no ordering assumption, and no coupling to another team's code structure. The cost is that the lookup key (a tag or naming convention) becomes the contract instead — but that's a much lighter contract.
2. **A parameter store** — the producer writes to SSM Parameter Store (A10.20); consumers read by well-known path. Explicit, versioned, access-controlled per path, and readable by things that aren't Terraform.
3. **`terraform_remote_state`** where the two states are owned by the same team and the coupling is acknowledged.

Platform-level alternatives: **Spacelift stack dependencies with output sharing** (TF11.4) and **TFC run triggers** solve the ordering problem explicitly, which is one of the real arguments for those platforms.

---

## TF4. Modules

**TF4.1 — A reusable module with a clear interface**

```hcl
# modules/service/variables.tf
variable "name" {
  type        = string
  description = "Service name; used as the resource name prefix."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "name must be lowercase alphanumeric with hyphens, 3-31 chars."
  }
}

variable "vpc_id" {
  type        = string
  description = "VPC in which to create the service."
}

variable "scaling" {
  description = "Autoscaling configuration."
  type = object({
    min_capacity = optional(number, 2)
    max_capacity = optional(number, 10)
    target_cpu   = optional(number, 70)
  })
  default = {}
}

variable "tags" {
  type        = map(string)
  description = "Additional tags merged with module defaults."
  default     = {}
}

# modules/service/outputs.tf
output "security_group_id" {
  description = "Security group attached to the service tasks."
  value       = aws_security_group.this.id
}
```

The design principles:

- **The variable set is the contract.** Every variable is something you will support indefinitely; every one you don't expose is something you're free to change. Expose what genuinely varies between consumers and nothing else.
- **Sensible defaults for everything optional**, so the minimal call is short. A module requiring fifteen inputs to do anything gets wrapped (TF4.5) or copy-pasted.
- **Descriptions on every variable and output**, because they generate the documentation (TF4.7).
- **Validation with useful error messages** (TF2.2), and **preconditions for assumptions about the environment** (TF2.14). These are what stop you becoming the support desk.
- **Outputs for everything a consumer might reasonably need to reference** — including IDs and ARNs of things they might attach to. Missing outputs are the most common reason people fork a module.
- **Grouped object variables** rather than a flat list of thirty scalars, which keeps call sites readable and lets you add fields without changing the signature.

**TF4.2 — What belongs in a module and what doesn't**

**Belongs**: a coherent unit of infrastructure that is deployed together, owned together, and meaningful as a concept — a VPC with its subnets and routing; a service with its task definition, load balancer target group, security group, and autoscaling; an S3 bucket with its policy, encryption, and lifecycle rules.

**Doesn't belong:**

- **Provider blocks.** A module should not configure providers — it should accept them from the caller (TF5.1, TF5.2). A module with its own provider block cannot be used with `for_each` and is very hard to use across accounts. This is the most consequential rule.
- **Backend configuration.** Modules don't have state; the root does.
- **A single resource with no added value.** A module wrapping one `aws_s3_bucket` with a passthrough for every argument is worse than using the resource directly — it adds indirection, a version to track, and nothing else (TF4.5).
- **Environment-specific values.** Hardcoded account IDs, CIDRs, or names belong in the caller's variables, not in the module.
- **Everything.** A module that creates a VPC *and* a database *and* an EKS cluster is a root configuration wearing a module's clothes; it can't be composed and it can't be partially adopted.

The test to state: **a module should have a name that describes a thing, and a consumer should be able to explain what it creates without reading the source.** If you can't name it without "and", it's probably two modules (TF4.6).

The other principle: **a module's job is to encode decisions, not to expose them.** The value of a platform team's `service` module is that it makes encryption, logging, tagging, and monitoring automatic — not that it lets you configure them. A module that passes every argument through has abstracted nothing (TF4.5).

**TF4.3 — Versioning modules and pinning in consumers**

```hcl
module "service" {
  source  = "app.terraform.io/acme/service/aws"
  version = "~> 3.2"          # >= 3.2.0, < 4.0.0
}

module "network" {
  source = "git::https://github.com/acme/tf-modules.git//network?ref=v2.4.1"
}
```

- **Semantic versioning**: major for breaking interface changes, minor for backwards-compatible additions, patch for fixes. Tag releases in git; registries derive versions from tags.
- **Pin in consumers.** For registry modules, `version = "~> 3.2"` (pessimistic constraint) is the usual balance — patches and minors flow automatically, majors require a deliberate change. For git sources, **pin to a tag, never to a branch**: `ref=main` means your infrastructure changes when someone else merges, which is exactly the unreviewed change IaC exists to prevent.
- **Pinning to an exact version** (`= 3.2.1`) is right for production where you want zero surprise, at the cost of manual upgrade work — Renovate or Dependabot can raise those PRs automatically, which is the pattern that makes exact pinning practical at scale.

The points that matter operationally: **module versions are not in the lock file** — `.terraform.lock.hcl` covers providers only (TF5.4), so an unpinned module genuinely does float. **Test module releases before consumers adopt them** (TF4.8). And **breaking changes need a migration path**, not just a major version bump (TF4.9).

**TF4.4 — Module sources and their tradeoffs**

| Source | Pros | Cons |
|---|---|---|
| **Local path** (`./modules/x`) | No versioning overhead, atomic changes with the caller | No independent versioning; only usable within the repo |
| **Git** (`git::...?ref=tag`) | No registry needed, private by default, works everywhere | Requires git auth in CI; no version constraint syntax (exact ref only); no discovery |
| **Public registry** | Discoverable, versioned, documented, huge library | Third-party code and supply-chain risk (TF7.7); breaking changes on someone else's schedule |
| **Private registry** (TFC/TFE, Spacelift, Artifactory) | Versioned with constraints, discoverable internally, access-controlled | Requires the platform; publishing workflow to maintain |
| **S3 / HTTP archive** | Simple, no extra service | Manual versioning; poor discoverability |

The judgement:

- **Local modules for anything used once, in one repo.** Don't publish a module with one consumer — you've added versioning ceremony for no reuse.
- **Git-sourced modules are the pragmatic default** for internal modules without a platform, and the main friction is CI authentication (SSH keys or a token) and the absence of constraint syntax.
- **A private registry once you have real internal reuse** — the version constraint syntax and discoverability are worth the platform (TF10.7).
- **Public registry modules are genuinely excellent for well-trodden ground** — the community AWS VPC and EKS modules encode a great deal of hard-won knowledge. The tradeoffs: they're very general so they carry a lot of surface area you don't use, they're third-party code running with your credentials (TF7.7), and their upgrade cadence is theirs. Pinning and reviewing the diff on upgrade is the mitigation.

**TF4.5 — Over-abstraction and wrapper-module sprawl**

The failure mode: a module wraps a resource and passes every argument through. Then a team wraps *that* module to set their defaults. Then an environment wraps *that*. Now changing one argument means editing four repositories and cutting three releases, and understanding what actually gets created means reading four modules.

The symptoms to name:

- **Passthrough variables** — a variable whose only job is to be forwarded unchanged. If most variables are passthroughs, the module isn't abstracting anything.
- **Modules with more variables than resources.**
- **Wrapper chains** more than two deep.
- **"Add a variable" as the response to every request**, which ratchets the interface wider until the module is as complex as the resources it wraps.
- **Consumers reading the module source** to understand behaviour, which means the abstraction has failed (TF4.7).

Why it happens: the instinct that all duplication is bad, applied to infrastructure where the duplication is often superficial. Two teams using an S3 bucket differently do not necessarily have a shared abstraction.

The corrective principles: **abstract when you're encoding a decision, not when you're forwarding an argument** (TF4.2). **Prefer composition over nesting** (TF4.6). **Accept some duplication** rather than a shared module serving two genuinely different needs (TF4.10). And **the rule of three** — wait until you have three real consumers before extracting a module, because two is not enough evidence to know what varies.

**TF4.6 — A module hierarchy that composes rather than nests**

**Nesting**: a root calls `platform`, which calls `network`, which calls `subnets`, which calls `routing`. Changes propagate through every layer, versions must be bumped in sequence, and the plan for a small change touches everything.

**Composition**: the root calls `network`, `security`, and `service` as siblings, wiring them together with outputs and inputs.

```hcl
module "network" {
  source = "./modules/network"
  cidr   = var.vpc_cidr
}

module "service" {
  source     = "./modules/service"
  vpc_id     = module.network.vpc_id
  subnet_ids = module.network.private_subnet_ids
}
```

Why composition wins:

- **The root configuration is readable** — you can see what exists and how it connects in one file.
- **Modules stay independently versionable and testable** (TF4.8).
- **Dependencies are explicit** in the wiring rather than buried three layers down.
- **You can adopt or replace one module** without touching the rest.

The guidance: **two levels of nesting is the practical maximum** — a module may reasonably use a small helper module, but beyond that the indirection costs more than it saves. And **a "platform" or "everything" module that calls all the others is usually an anti-pattern**, because it eliminates the composition point that made the modules useful; it's a root configuration that can't be varied.

Where deeper nesting is defensible: a genuinely reusable low-level primitive (a tagging or naming module) used by several mid-level modules — because it's a leaf with a stable, tiny interface.

**TF4.7 — Documenting a module**

The target: **a consumer should never need to read the source.** What that requires:

- **A README with a working example first.** The single most useful thing in module documentation is a copy-pasteable minimal call, followed by a realistic one. People read examples, not prose.
- **Generated input/output tables** — `terraform-docs` reads descriptions from variables and outputs and injects a table into the README, kept current by a pre-commit hook or CI check. Hand-written tables go stale immediately, so generation is the only version that stays true.
- **Descriptions on every variable and output** (TF4.1), since they're the source for the generated docs.
- **An `examples/` directory** with runnable configurations — which doubles as test fixtures (TF4.8).
- **A CHANGELOG**, particularly for breaking changes and migration steps (TF4.9).
- **What the module does *not* do**, and what it assumes about the environment — the assumptions are where consumers get stuck, and preconditions (TF2.14) make them enforceable as well as documented.

The signal to watch for: **if consumers keep asking questions the README answers, the README is in the wrong order or too long; if they ask questions it doesn't answer, add them.** Support questions are the feedback loop for documentation quality, and treating them as such is the platform-as-product mindset (TF8.8).

**TF4.8 — Testing a module**

The layers, cheapest first:

1. **`terraform fmt -check` and `terraform validate`** — syntax and internal consistency. Fast, run on every commit.
2. **Static analysis** — tflint for provider-specific correctness and deprecated usage, tfsec/Checkov/Trivy for security misconfiguration (TF7.5).
3. **`terraform plan` against the examples** — catches type errors, missing variables, and provider rejections without creating anything.
4. **`terraform test`** (native, from 1.6) — HCL-native test files that can run `plan`-only assertions or full `apply` against real infrastructure, with automatic teardown:

```hcl
# tests/defaults.tftest.hcl
run "defaults_are_sane" {
  command = plan
  variables { name = "test-service" }
  assert {
    condition     = aws_security_group.this.name == "test-service-sg"
    error_message = "Security group name did not follow the naming convention."
  }
}
```

5. **Terratest** (Go) — full apply/verify/destroy with arbitrary assertions, including calling the deployed thing. More powerful, more machinery, and a Go codebase to maintain.

The judgement to express: **plan-only tests catch most of what actually breaks** — type errors, bad interpolations, invalid combinations — and they're fast and free. **Apply tests are where the real cost is** (time, money, cleanup, flakiness, and a test account to run in), so reserve them for modules where the deployed behaviour matters and where breakage is expensive. For most internal modules, `validate` + lint + scan + plan-against-examples in CI is the right level, and `terraform test` has largely removed the reason to reach for Terratest unless you need to assert on runtime behaviour.

The thing to name regardless: **modules need a release process with testing, because a bad module version breaks every consumer at once** (TF4.3).

**TF4.9 — Evolving a module interface without breaking consumers**

The techniques, in order of preference:

- **Add, don't change.** New optional variables with defaults preserving existing behaviour are always safe. Most evolution should look like this.
- **`optional()` with defaults** in object variables (TF2.2), so adding a field doesn't break existing calls.
- **Deprecate before removing.** Keep the old variable working, have it feed the new one, and emit a warning — via a `check` block (TF2.14) or a validation message. Give consumers a release cycle or two.
- **`moved` blocks for internal refactoring** (TF2.12) — this is the crucial one for modules. Renaming a resource inside a module, or converting `count` to `for_each`, would destroy and recreate consumers' infrastructure. A `moved` block shipped in the module makes the refactor invisible to them. **This is what makes module internals genuinely changeable**, and it's the most valuable thing in this item.
- **Major version bump with a migration guide** when a break is unavoidable — and the guide must include the exact `moved` blocks or `state mv` commands needed, not just a description.

The process points: **communicate before you release**, know who your consumers are (a private registry tells you; git sources don't), and **run the new version against a real consumer's configuration before publishing** — a plan showing unexpected destroys is the check that catches the mistake.

The principle: **a module with many consumers is a product with an API, and breaking it is a breaking change to other teams' production infrastructure.** Treating it with less care than a shared library is the mistake.

**TF4.10 — When a shared module is worse than duplication**

The cases where duplication genuinely wins:

- **The consumers' needs are diverging.** If every new consumer requires a new variable and a new conditional, the module is serving two different things badly. Two focused modules — or two copies — are clearer and independently changeable.
- **The module has become a coordination bottleneck.** If a team can't ship because they're waiting on a platform team to add a variable, the abstraction is costing more velocity than it saves (TF13.5).
- **The shared code is trivial.** Sharing twenty lines of straightforward resource definitions creates a version, a repo, a release process, and a support obligation to avoid twenty lines of duplication. Bad trade.
- **The duplication is superficial.** Two S3 buckets are not the same thing just because they're both S3 buckets. Shared structure is not shared purpose, and coupling them means a change for one forces consideration of the other.
- **Blast radius.** A shared module used by fifty consumers means a bad release affects fifty. Sometimes the isolation of separate copies is worth the maintenance.

The framing that lands: **DRY is a principle about knowledge, not about text.** Duplicating a representation of the *same decision* is bad — that's when you get drift and inconsistent behaviour. Duplicating text that happens to look similar but represents *different decisions* is fine, and forcing it into one abstraction creates coupling between things that should be free to diverge.

The practical heuristic: **wait for three consumers, and extract only the parts that are genuinely the same decision.** Premature abstraction is much harder to undo than duplication, because by the time you know the abstraction is wrong, fifty consumers depend on it.

---

## TF5. Providers & versioning

**TF5.1 — Configuring providers, including aliases**

```hcl
provider "aws" {
  region = "eu-west-1"
  default_tags {
    tags = {
      ManagedBy = "terraform"
      Repo      = "acme/platform-infra"
    }
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "cloudfront" {
  provider          = aws.us_east_1        # CloudFront certs must be here (A8.6)
  domain_name       = "www.acme.com"
  validation_method = "DNS"
}
```

The points that matter:

- **`default_tags` is the highest-leverage provider setting** — every resource that supports tags gets them automatically, which is how you make a tagging standard actually stick (A12.2, TF2.1) rather than relying on every module remembering.
- **Aliases are how you address multiple regions or accounts from one configuration** (TF5.2).
- **Modules must not declare their own provider blocks** (TF4.2). They declare *requirements* in `required_providers` and receive configured providers from the caller, either implicitly or via `providers = { aws = aws.us_east_1 }`. A module with its own provider block can't be used with `for_each` or `count`, and can't be cleanly removed.

**TF5.2 — Multi-account and multi-region with aliases**

```hcl
provider "aws" {
  alias  = "network"
  region = "eu-west-1"
  assume_role {
    role_arn = "arn:aws:iam::111122223333:role/TerraformExecution"
  }
}

provider "aws" {
  alias  = "workload"
  region = "eu-west-1"
  assume_role {
    role_arn = "arn:aws:iam::444455556666:role/TerraformExecution"
  }
}

module "peering" {
  source = "./modules/vpc-peering"
  providers = {
    aws.requester = aws.network
    aws.accepter  = aws.workload
  }
}
```

The pattern: **the pipeline authenticates once (ideally via OIDC, TF7.4) into a central identity, then each provider alias assumes a role in the target account** (A1.7). The execution role must exist in every target account, which is a job for account vending (A1.13).

The constraints that shape design:

- **Provider aliases cannot be generated dynamically.** You cannot `for_each` over a list of accounts to create providers — each alias must be written out statically. This is the single biggest limitation in multi-account Terraform, and it's why "one state per account" (TF3.6) is usually the answer rather than one configuration spanning fifty accounts.
- **Cross-account state is a real coupling risk.** A single state managing resources in several accounts means one apply can break several accounts, and the state file's access control has to cover all of them (TF3.2).
- **The `assume_role` in the provider is evaluated at plan time**, so credentials must be valid for the whole run — relevant for long applies against a one-hour session (A1.7).

The alternative for genuine scale: **one state per account/region, driven by a pipeline that iterates** — which is exactly the problem Terragrunt (TF8.5) and Spacelift stacks (TF11.2) exist to solve, and the rollout question in TF8.7.

**TF5.3 — `required_providers` and version constraints**

```hcl
terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}
```

Constraint syntax: `= 5.40.0` (exact), `>= 5.40` (minimum), `~> 5.40` (pessimistic — allows 5.40.x through 5.x but not 6.0), `~> 5.40.0` (allows 5.40.x only), and comma-separated for ranges.

The judgement on where to constrain:

- **Modules should declare permissive constraints** (`>= 5.0`), because a module with a narrow constraint conflicts with every other module in the same configuration. Terraform resolves one version per provider across the whole configuration, so **over-constraining in a module makes it uncombinable**.
- **Root configurations should pin tightly** (`~> 5.40`), because that's where the reproducibility decision belongs — combined with the lock file (TF5.4).
- **`source` is mandatory** for non-HashiCorp providers and good practice always, since it disambiguates namespaces.

**TF5.4 — The lock file and why it belongs in version control**

`.terraform.lock.hcl` records the **exact provider versions selected and their cryptographic hashes** for each platform.

Why it belongs in git:

- **Reproducibility.** Everyone — every developer, every CI run — uses byte-identical providers. Without it, `terraform init` resolves the constraint fresh, so a provider released between your plan and your colleague's plan produces different behaviour, and that's a genuinely maddening class of bug.
- **Supply-chain integrity.** The hashes mean a tampered or substituted provider fails verification (TF7.7). That check is only meaningful if the file is committed and reviewed.
- **Deliberate upgrades.** Provider versions change when someone runs `terraform init -upgrade` and commits the resulting diff — which is a reviewable event rather than an ambient one.

The operational details:

- **`terraform init -upgrade`** is what updates it; ordinary `init` respects it.
- **`terraform providers lock -platform=linux_amd64 -platform=darwin_arm64`** adds hashes for platforms you haven't run on. **Without this, a lock file generated on an Apple Silicon laptop fails in Linux CI** with a missing-hash error — one of the most common lock file problems and worth naming.
- **It covers providers only, not modules** (TF4.3).
- Merge conflicts on it are common; regenerate rather than hand-merging.

**TF5.5 — Upgrading a provider major version safely**

The procedure:

1. **Read the upgrade guide.** Major provider versions have published guides listing removed arguments, renamed resources, and changed defaults. The AWS provider's guides are detailed and reading them is the bulk of the work.
2. **Check the minimum Terraform core version** the new provider requires (TF5.7).
3. **Upgrade in a non-production state first**, ideally one that exercises the same resource types.
4. **`terraform init -upgrade`, then `terraform plan`, and read it in full.** The plan is your test. **What you are looking for is unexpected replacements** — a provider that changed how an attribute is represented can produce a forced replacement of a database (TF12.1). This is where the risk concentrates.
5. **Fix deprecated usage** flagged as warnings before they become errors in the next major.
6. **Roll through environments** with a plan review at each stage, and don't batch it with other changes — a provider upgrade should be its own PR so the plan diff is attributable.

The hazards worth naming:

- **State schema migrations are one-way.** Some upgrades rewrite state in a format older providers can't read, so rolling back the provider version after applying may not be possible (TF3.13). Back up state first.
- **Skipping majors compounds risk.** Going 4.x → 6.x means two sets of breaking changes at once with no intermediate verification. Go one at a time.
- **Provider upgrades can change behaviour without changing your code** — new defaults, new computed attributes, different drift detection. A clean plan on the old version and a large plan on the new one with no code change is the signature.
- **`ignore_changes` may mask a change you needed to see** (TF2.9).

**TF5.6 — How providers map to APIs, and what happens when a resource lags**

A provider is a plugin translating Terraform's resource model into a service's API calls (create, read, update, delete), plus a schema describing arguments and attributes. It's maintained separately from Terraform core and released on its own cadence — the AWS provider ships weekly.

**When a resource lags** — a new AWS service or a new argument on an existing one isn't in the provider yet. This is common and the options are, in order:

1. **Wait and pin.** If the timeline permits, the provider usually catches up within weeks for mainstream services. Check the provider's GitHub issues — there's often an open issue with a target release.
2. **Use a lower-level escape hatch**: `aws_cloudformation_stack` to deploy a CloudFormation snippet for the unsupported resource, or the **`awscc` provider** (Cloud Control API), which is auto-generated from AWS's resource schemas and therefore covers new services much sooner than the hand-written `aws` provider. This is the underused answer and worth naming — mixing `awscc` for the gaps and `aws` for everything else is a legitimate pattern.
3. **`terraform_data` / `null_resource` with a `local-exec` calling the CLI** — works, breaks the model (TF2.11), and should be temporary with a tracked ticket to remove it.
4. **Manage it outside Terraform** and reference it with a data source or hardcoded ARN, documented as an exception (TF13.2).
5. **Contribute the resource** to the provider — realistic for a well-scoped addition, and worth mentioning as an option even if rarely taken.

The judgement to express: **all of these are debt, so choose the one that's easiest to remove later.** A CloudFormation stack or `awscc` resource can be replaced with the native resource and imported (TF3.8); a shell script wrapped in `null_resource` tends to become permanent.

**TF5.7 — Core version constraints and upgrade planning**

```hcl
terraform {
  required_version = ">= 1.6.0, < 2.0.0"
}
```

Terraform core upgrades are generally low-risk within 1.x — HashiCorp has been careful about backwards compatibility — but the planning still matters:

- **State format changes are one-way.** A state file written by a newer Terraform cannot be read by an older one. So **the first person to run a newer version against a shared state upgrades it for everyone**, and colleagues on the older version get a hard error. That's the practical failure and the reason to pin `required_version` and manage the upgrade deliberately.
- **Pin the version in CI explicitly** (a `.terraform-version` file for tfenv, or the version input in the CI action), so runs are reproducible and the upgrade is a committed change.
- **`required_version` in the root config** prevents someone running an unexpectedly old or new binary against it — which is the guardrail that turns a confusing state error into a clear message.
- **New features require new minimums**: `moved` (1.1), `import` blocks and `check` (1.5), `terraform test` and `removed` blocks (1.6+). Adopting a feature raises the floor for everyone using that code, which matters for shared modules (TF4.3) — a module using `optional()` in object types can't be consumed by an older core.
- **Watch the licence boundary** (TF1.8): 1.6 onwards is BUSL, and OpenTofu diverges from there.

**TF5.8 — When the provider can't express what you need**

Largely covered by TF5.6 for missing resources. The other shapes of this problem:

- **The resource exists but an argument is missing or read-only.** Sometimes solvable with `ignore_changes` plus an out-of-band configuration step; sometimes it requires the escape hatches above.
- **The API is stateful in a way the provider can't model** — an operation with no idempotent representation, like triggering a one-off migration or rotating something on a schedule. **This usually means it shouldn't be in Terraform at all** (TF13.2) — it's an operation, not a desired state, and belongs in a pipeline step or a runbook.
- **Ordering or timing the provider doesn't handle** — a resource that's created but not usable for some seconds. `depends_on` (TF2.8) doesn't help; `time_sleep` from the `time` provider is the ugly-but-honest answer, and a retry in the consuming resource is better if available.
- **Cross-provider coordination** the graph can't express — usually solvable by restructuring the dependency rather than by force.

The framing that shows judgement: **before working around the provider, ask whether the thing belongs in Terraform.** A large share of "the provider can't do this" cases are really "this is an imperative operation being forced into a declarative tool" (TF1.1, TF1.7). Naming that distinction is worth more than knowing every escape hatch.

---

## TF6. CLI & workflow

**TF6.1 — `init`**

```bash
terraform init
terraform init -upgrade                          # re-resolve providers, update lock file
terraform init -reconfigure                      # ignore existing backend state, reconfigure
terraform init -migrate-state                    # move state to a new backend
terraform init -backend-config=prod.backend.hcl  # supply backend values externally
terraform init -backend=false                    # init modules/providers without a backend
```

What `init` does: downloads providers, downloads and caches modules, configures the backend, and writes/verifies the lock file.

The flags that matter and why:

- **`-upgrade`** — the only way provider versions move within existing constraints (TF5.4). Ordinary `init` respects the lock file.
- **`-reconfigure` vs `-migrate-state`** — the distinction people get wrong. **`-migrate-state` copies your existing state to the new backend**; **`-reconfigure` discards the backend configuration cache and starts fresh, without copying.** Using `-reconfigure` when you meant `-migrate-state` leaves your state behind in the old backend and initialises an empty one — which then plans to create everything. Know which you mean.
- **`-backend-config`** — because **the backend block cannot use variables or interpolation**, this is the mechanism for per-environment backends. Either a file or repeated `-backend-config="key=value"` flags. This limitation is one of the main things Terragrunt exists to fix (TF8.5).
- **`-backend=false`** is useful in CI for validation-only jobs that don't need state access, which also means they don't need state credentials (TF9.1).

**TF6.2 — `plan`**

```bash
terraform plan -out=tfplan                    # save the plan (TF6.4)
terraform plan -var-file=prod.tfvars
terraform plan -target=module.network         # break-glass only (TF6.6)
terraform plan -refresh=false                 # skip refresh — faster, staler (TF8.6)
terraform plan -destroy                       # preview a destroy
terraform plan -refresh-only                  # drift only (TF3.11)
terraform plan -detailed-exitcode             # 0=no changes, 1=error, 2=changes
```

`-detailed-exitcode` is the one worth calling out for automation: it's how a pipeline decides whether there's anything to apply, and how scheduled drift detection decides whether to alert (TF9.6).

`-out` is the basis of the safe workflow (TF6.4). `-var-file` for environment values, with `TF_VAR_` environment variables for secrets so they don't land in a file (TF6.17, TF7.2).

**TF6.3 — Reading a plan properly**

The symbols:

```
  + create
  ~ update in-place
-/+ destroy and then create replacement       # replacement
+/- create replacement and then destroy       # replacement with create_before_destroy
  - destroy
 <= read (data source)
```

**Reading a plan properly means three specific habits:**

1. **Check the summary line first** — `Plan: 2 to add, 1 to change, 0 to destroy`. **Any unexpected destroy is a stop condition.** Not a "probably fine", a stop.
2. **For every replacement, find the reason.** Terraform prints it: `# forces replacement` next to the offending attribute. That one annotation is the answer to TF12.1, and skipping it is how people apply a plan that recreates a database.
3. **Read the whole diff for critical resources**, not just the summary. `~` on a security group could be a description change or an ingress rule opening 0.0.0.0/0.

The subtleties worth knowing:

- **`(known after apply)`** means the value is computed. Too many of these obscure the plan, and they cascade — one unknown value makes everything depending on it unknown. That's the cost of `-target` misuse and of unnecessary `depends_on` (TF2.8).
- **A plan is a point-in-time prediction.** If the world changes between plan and apply, the apply can differ — which is why applying a *saved* plan is safer (TF6.4) and why Terraform rechecks and errors if state moved.
- **`terraform show -json tfplan`** gives a machine-readable plan for policy evaluation (TF7.6) and for tooling.
- **`terraform plan` output in a PR** is the key review artefact (TF9.2), and the reviewer's job is exactly the three habits above.

**TF6.4 — Why applying a saved plan file is the safe pattern**

```bash
terraform plan -out=tfplan
# review...
terraform apply tfplan          # no prompt: the plan IS the approval
```

The reasoning:

- **What was reviewed is what is applied.** Running `terraform apply` fresh generates a *new* plan, which can differ from the one a human approved — because the code changed, the variables changed, or the world changed. Applying a saved plan removes that gap entirely. **In a pipeline with an approval gate, this is the property that makes the approval meaningful** (TF9.3, TF9.5).
- **It removes the interactive prompt** without `-auto-approve`, so the pipeline isn't blindly approving whatever it generates.
- **The plan file is an artefact** — it can be stored, attached to a change record, and audited. In a regulated environment that's the evidence that a specific change was reviewed and applied.
- **Terraform verifies the state hasn't moved** since the plan was created and refuses if it has, which is a genuine safety check.

The practical cautions: **the plan file contains state data including secrets** (TF3.2, TF7.8), so it must be treated as sensitive — encrypted artefact storage, short retention, never a public CI artefact. And **plan files are tied to the Terraform and provider versions** that produced them, so the apply step must use identical versions (TF9.3).

**TF6.5 — `apply`**

```bash
terraform apply tfplan
terraform apply -auto-approve                 # CI only, and only with a reviewed plan
terraform apply -parallelism=5                # default 10
terraform apply -replace=aws_instance.web     # (TF6.9)
terraform apply -target=module.network        # break-glass (TF6.6)
```

- **`-auto-approve`** skips the confirmation prompt. Fine in a pipeline that applies a reviewed saved plan; dangerous as a habit locally, and a red flag in a pipeline that generates its own plan at apply time.
- **`-parallelism`** controls concurrent resource operations. **Lowering it is the standard fix for provider API rate limiting** — a large apply hammering the AWS API gets throttled, and the errors look like random failures. Raising it rarely helps much and increases throttling risk.
- Apply is **not transactional.** If it fails partway, the resources created so far stay created and are recorded in state (TF9.8). There is no rollback (TF9.7).

**TF6.6 — Why `-target` is break-glass, not a workflow**

`-target` restricts the operation to specific resources and their dependencies.

Why it's break-glass:

- **It produces a partial plan against a whole configuration**, so Terraform warns explicitly that the result may not be consistent with the configuration as a whole. Anything depending on untargeted resources gets `(known after apply)` or stale values.
- **It hides changes.** You applied what you targeted; whatever else had drifted is still pending and invisible, accumulating until someone runs a full apply and gets a surprise.
- **It becomes a habit that masks a structural problem.** People reach for `-target` because the plan is slow (TF8.6) or because the state is too big (TF3.6) — both of which are the actual problem. Routine `-target` use is a symptom that state should be split.
- **It's easy to get the dependency closure wrong** and apply something half-configured.

**When it is justified**: recovering from a partially failed apply where one resource needs fixing before the rest can proceed (TF9.8); breaking a dependency deadlock during a refactor; and applying a fix urgently where a full plan would include unrelated pending changes you don't want to ship. In each case it's a deliberate, explained, one-off action — and **the follow-up is a full plan and apply to reconcile**.

**TF6.7 — `destroy` and the safeguards around it**

```bash
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```

The safeguards worth having:

- **`prevent_destroy`** on stateful and irreplaceable resources — databases, state buckets, KMS keys, anything holding data (TF2.9). It's the last line of defence and it works.
- **Deletion protection at the provider level** — RDS `deletion_protection`, S3 bucket with objects, EKS cluster protection. Belt and braces, and provider-level protection survives a state file that no longer has your lifecycle rules.
- **Never `-auto-approve` a destroy** outside genuinely ephemeral environments.
- **Restrict who can run destroy in CI**, and ideally don't expose it as a pipeline action at all for production — make it require a deliberate, logged, manual action (TF7.9).
- **Separate credentials or a separate role** for destructive operations.
- **Backups verified before any planned teardown** (A11.7).
- **Read the destroy plan in full.** A destroy plan on the wrong workspace or with the wrong `-var-file` is one of the classic career-defining incidents.

The related risk to name: **an accidental destroy doesn't require running `destroy`.** Removing a resource block from code, or a bad `for_each` key change (TF2.4), produces destroys in a normal apply. The plan review is the control (TF6.3), and `prevent_destroy` is the backstop.

**TF6.8 — `state` subcommands**

```bash
terraform state list                                    # all addresses in state
terraform state list | grep aws_iam
terraform state show aws_instance.web                    # full attributes
terraform state mv aws_instance.web aws_instance.api     # rename/move (prefer `moved`, TF2.12)
terraform state rm aws_s3_bucket.legacy                  # forget without destroying (TF3.9)
terraform state pull > backup.tfstate                    # download current state
terraform state push state.tfstate                       # upload (dangerous, TF3.13)
terraform state replace-provider \
  registry.terraform.io/-/aws registry.terraform.io/hashicorp/aws
```

Usage notes: **`state list` and `state show` are read-only and are your primary inspection tools** — `state show` in particular is how you check what Terraform believes about a resource when a plan is behaving strangely. **`state pull > backup` before any mutating operation** is the habit that saves you. **`replace-provider`** matters when a provider's source address changes (the legacy-to-namespaced migration, or moving between Terraform and OpenTofu registries, TF1.8).

The general principle: **prefer declarative equivalents where they exist** — `moved` over `state mv` (TF2.12), `removed` over `state rm` (TF3.9), `import` blocks over `terraform import` (TF2.13) — because those are reviewed, repeatable, and run in the pipeline rather than depending on one person's local shell.

**TF6.9 — `taint` vs `-replace`**

**`terraform taint`** (deprecated) immediately marked a resource in state as tainted, so the *next* plan would replace it. The problem: it mutated state as a side effect, before any plan was reviewed, and if you changed your mind you had to `untaint`.

**`terraform apply -replace=ADDRESS`** (and `plan -replace=`) is the replacement: it's a **plan-time flag**, so the replacement appears in a reviewable plan and nothing is written to state until you apply.

```bash
terraform plan -replace=aws_instance.web -out=tfplan
terraform apply tfplan
```

The difference to state: **`-replace` keeps the change in the plan/apply workflow where it can be reviewed; `taint` moved it into a state mutation outside that workflow.** That's the whole reason for the deprecation, and it's the same principle as `moved` blocks over `state mv` (TF6.8).

When you'd use it: a resource in a bad state that Terraform sees as correct — a corrupted instance, a container that needs recreating, a resource whose out-of-band configuration has drifted in a way Terraform can't see. The declarative alternative for recurring cases is `replace_triggered_by` (TF2.10).

**TF6.10 — `output`**

```bash
terraform output                              # all outputs
terraform output vpc_id                       # one value
terraform output -raw vpc_id                  # unquoted, for shell consumption
terraform output -json                        # machine-readable, includes sensitive
```

`-json` is how downstream tooling consumes Terraform results — a pipeline step that needs the cluster name, a script that configures something afterwards, or a test harness. **`-raw` for a single value in a shell variable** avoids the quoting that `-json` or plain output introduces.

Two cautions: **`-json` includes values marked sensitive** (unredacted), so piping it into a log is a leak (TF7.8). And **outputs are the coupling surface between states** (TF3.14) — treat adding one as publishing an API.

**TF6.11 — `fmt`, `validate`, `console`**

```bash
terraform fmt -recursive                      # rewrite to canonical style
terraform fmt -check -recursive               # CI gate: fail if unformatted
terraform validate                            # syntax + internal consistency (no API calls)
terraform console                             # interactive expression evaluation
```

**`fmt -check` in CI** removes an entire category of review comment — style is settled by the tool, not by people. **`validate` requires `init` but not credentials or state** (with `-backend=false`), which makes it a cheap, fast, early gate (TF9.1). It catches type errors, undefined references, and missing required arguments; it does *not* catch anything requiring provider API knowledge — that's `plan`.

**`console` is the underused one.** Iterating on a `for` expression or a `flatten`/`merge` chain by running `terraform plan` repeatedly is slow and painful; `console` evaluates expressions against your actual variables and state instantly. Anyone who has debugged a nested `for` expression knows the difference, and mentioning it is a small but real signal of hands-on use.

**TF6.12 — `graph` and reasoning about dependencies**

```bash
terraform graph | dot -Tsvg > graph.svg
terraform graph -type=plan
```

Emits the dependency graph in DOT format. On any real configuration the rendered graph is too dense to read as a picture — which is worth saying, because the honest answer is that **`graph` is rarely the tool you actually reach for.**

Where it genuinely helps: **diagnosing a cycle error** (TF12.3), where the graph shows the loop; and understanding why Terraform is ordering operations unexpectedly, or why a `depends_on` is causing something to be deferred.

The more useful daily skill is **reasoning about the graph without rendering it**: dependencies come from references (TF2.8), Terraform walks the graph in dependency order with `-parallelism` concurrent operations (TF6.5), destroys happen in reverse dependency order, and `create_before_destroy` propagates to dependents (TF2.9). Knowing those rules explains most ordering behaviour without ever generating a diagram.

**TF6.13 — `providers`, `version`, `show -json`**

```bash
terraform version                             # core + provider versions in use
terraform providers                           # provider requirements tree, incl. per-module
terraform providers schema -json              # full schema, for tooling
terraform show -json tfplan > plan.json       # machine-readable plan
terraform show -json                          # machine-readable state
```

**`terraform providers`** is the diagnostic for version constraint conflicts — it shows which module requires which constraint, which is exactly what you need when resolution fails because two modules disagree (TF5.3).

**`show -json` on a plan file is the integration point for policy as code** — Conftest, OPA, and Checkov all consume it (TF7.6), as do cost estimation tools like Infracost and custom pipeline checks. Knowing that the plan is machine-readable, and that this is how policy engines actually see it, is the substantive point here rather than the commands themselves.

**TF6.14 — `login` / `logout`**

```bash
terraform login                               # app.terraform.io by default
terraform login app.terraform.io
terraform login spacelift.io
terraform logout
```

Obtains an API token via browser and stores it in `~/.terraform.d/credentials.tfrc.json`. Used for the remote backend, remote execution, and **the private module registry** (TF10.7) — pulling a private registry module requires credentials, and this is how a developer gets them locally.

In CI you don't use `terraform login`; you set the token via **`TF_TOKEN_app_terraform_io`** environment variable (the `TF_TOKEN_<hostname>` convention with dots replaced by underscores) or a credentials file, sourced from the CI secret store. That's the detail worth knowing, because "it works locally and fails in CI" for module resolution is almost always this (TF12.8).

**TF6.15 — `force-unlock` and when it's justified**

Covered in TF3.5. The short form: justified **only when you have positively confirmed the lock holder is dead** — the CI job finished or was killed, the person confirms their process died. Never because a lock has been there a while and you're impatient; a long-running apply legitimately holds a lock for a long time, and force-unlocking it lets a second apply run concurrently against the same state, which is the corruption scenario in TF3.4.

**TF6.16 — `TF_LOG` and debug logs**

```bash
export TF_LOG=DEBUG                # TRACE, DEBUG, INFO, WARN, ERROR
export TF_LOG_PATH=./terraform.log
export TF_LOG_PROVIDER=TRACE       # provider only — usually what you want
terraform plan
```

What it gives you: the **actual API requests and responses** the provider makes. That's the point — when a provider does something inexplicable, the debug log shows the request it sent and the error the API returned, which is frequently far more informative than the message Terraform surfaces.

Where it earns its keep: **authentication failures** (which credential chain step was used, which role was assumed, what the STS response said — TF12.7); **provider behaviour that contradicts the documentation**; **rate limiting and retries**, visible as repeated calls with throttling responses; and **perpetual diffs** (TF12.2), where the log shows what the API returned versus what Terraform expected.

The cautions: **TRACE is enormous** — a large plan produces hundreds of megabytes, so use `TF_LOG_PROVIDER` to narrow it and always write to a file. And **debug logs contain credentials and secrets in request bodies**, so they must never be attached to a ticket or committed without redaction (TF7.8).

**TF6.17 — Environment variables that matter**

```bash
TF_VAR_db_password="..."          # sets var.db_password
TF_CLI_ARGS_plan="-parallelism=5" # appended to every `plan` invocation
TF_IN_AUTOMATION=1                # suppresses "run terraform apply next" style hints
TF_INPUT=0                        # never prompt interactively — fail instead
TF_WORKSPACE=prod                 # select workspace without a command
TF_DATA_DIR=.terraform            # relocate the working directory
TF_LOG / TF_LOG_PATH              # (TF6.16)
TF_TOKEN_app_terraform_io         # registry/backend token (TF6.14)
TF_PLUGIN_CACHE_DIR               # shared provider cache — big CI speedup
```

The ones that matter most in practice:

- **`TF_VAR_`** is how secrets reach Terraform without a `.tfvars` file on disk (TF7.2) — the CI secret store sets the environment variable.
- **`TF_INPUT=0`** is essential in automation: without it, a missing variable causes Terraform to **hang waiting for input** rather than fail, which manifests as a pipeline job that times out after an hour with no useful error. Everyone hits this once.
- **`TF_IN_AUTOMATION`** just tidies output, but signals you know the tool is running unattended.
- **`TF_PLUGIN_CACHE_DIR`** shared across CI runs avoids re-downloading providers on every job, which on a large provider like AWS is a meaningful chunk of pipeline time (TF8.6).

---

## TF7. Secrets & security

**TF7.1 — Why `sensitive` doesn't remove a value from state**

`sensitive = true` on a variable or output tells Terraform to **redact the value in CLI output, plan display, and logs**. It shows `(sensitive value)` instead of the content.

**It has no effect on state.** State stores the full resource attributes as returned by the provider, and a sensitive variable's value is still written there in plaintext if it flows into a resource argument (TF3.2). Same for outputs — a sensitive output is stored unredacted.

Why the confusion is dangerous: people mark a variable sensitive, see the redaction in the plan, and conclude the secret is protected. It isn't — anyone with read access to the state file has it.

The consequences and the correct responses:

- **Secure the backend as a credential store** (TF7.3) — this is the primary control.
- **`terraform output -json` returns sensitive values unredacted** (TF6.10), so it must not be logged.
- **Sensitivity propagates**: a value derived from a sensitive value is treated as sensitive, which is useful, and occasionally over-eager — you may need `nonsensitive()` to unwrap something for use as a `for_each` key, and doing that deliberately is fine.
- **The real fix is architectural** — don't put the secret in Terraform. Use `manage_master_user_password` on RDS so the password is generated and stored in Secrets Manager without transiting state; reference secrets by ARN and let the application resolve them at runtime (A10.21); use IAM auth (A7.8). **Terraform should manage the *container* for a secret, not its value** (TF7.2).

**TF7.2 — Sourcing secrets at runtime**

The hierarchy, best to worst:

1. **Don't have the secret.** Let the resource generate it (`manage_master_user_password`), or use IAM/OIDC auth so no password exists. **Best because nothing can leak.**
2. **Reference by ARN.** Terraform creates the secret container and grants access; the application resolves the value at runtime (A10.21, K3.6). The value never enters Terraform.
3. **Read at plan time from a secret store** via a data source (`aws_secretsmanager_secret_version`, `vault_generic_secret`). **The value lands in state** (TF3.2) — better than hardcoding, still a state exposure, and worth being explicit about that tradeoff rather than presenting it as a solution.
4. **`TF_VAR_` from the CI secret store** (TF6.17) — no file on disk, but again ends up in state if used in a resource.
5. **A `.tfvars` file** — acceptable only for non-secrets, and `*.auto.tfvars` containing secrets is a classic accidental commit.
6. **Hardcoded in `.tf`** — never.

The related discipline: **`.gitignore` covering `*.tfvars`, `*.tfstate`, `*.tfstate.backup`, `.terraform/`, and `*.tfplan`**, plus **secret scanning in the commit path** (pre-commit hooks and server-side scanning), because the recovery from a committed secret is rotation, not deletion (A10.30).

**TF7.3 — Securing state access**

The controls, and each maps to a specific threat:

- **Encryption at rest with a customer-managed KMS key** (TF3.3), so the key policy is a second authorisation layer and key use is auditable (A10.16). An attacker with S3 read but no KMS decrypt gets ciphertext.
- **Least-privilege IAM on the backend**, scoped **per state path**: `s3:GetObject` and `s3:PutObject` on `platform/networking/*` for the networking pipeline, not on the whole bucket. This is the control that makes state splitting (TF3.6) a security boundary rather than just an operational one.
- **Separate read and write**: a role that can read state for `terraform_remote_state` (TF3.14) should not be able to write it.
- **Deny delete** except for a narrowly scoped administrative role, and enable **versioning** (TF3.3) so deletion is recoverable.
- **Bucket policy denying non-TLS** and enforcing the org boundary with `aws:PrincipalOrgID` (A2.5).
- **Access logging and CloudTrail data events** on the state bucket, so you know who read it — noting that S3 data events are off by default (A9.5).
- **Block Public Access at the account level** (A6.4).
- **In a regulated environment**: replication to a separate account, and object lock.

The framing to lead with: **the state file contains every secret Terraform has touched** (TF3.2), so the threat model is "credential store", not "config file". Stating it that way makes the controls follow naturally rather than sounding like a checklist.

**TF7.4 — Authenticating without long-lived keys**

The mechanism is OIDC federation (A2.8 for the full AWS treatment). In short: the CI provider issues a signed token asserting the workflow's identity; AWS trusts that provider as an OIDC IdP; the pipeline exchanges the token for short-lived credentials via `AssumeRoleWithWebIdentity`.

```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::111122223333:role/terraform-plan
      aws-region: eu-west-1
```

The Terraform-specific points on top of A2.8:

- **Separate roles for plan and apply.** Plan needs read access plus state read; apply needs write. Binding the apply role to the `main` branch or a protected environment via the trust policy's `sub` condition means **a fork PR can never assume the apply role** — which is the control that makes running plans on untrusted PRs safe (TF9.2).
- **The trust policy `sub` condition is the entire security boundary**, and a wildcard there is the common critical misconfiguration (A2.8).
- **Cross-account applies then chain from that identity** into per-account execution roles via provider `assume_role` (TF5.2) — noting the one-hour role chaining cap (A1.7) for long applies.
- **The result**: no static credentials in the CI secret store at all, so there's nothing to rotate and nothing to leak. That's the argument to make, and it pairs with A10.30's "the fix isn't better key hygiene, it's eliminating keys".

**TF7.5 — Scanning Terraform for misconfiguration**

```bash
tfsec .
checkov -d . --framework terraform
trivy config .
terraform show -json tfplan | checkov -f - --framework terraform_plan
```

What they catch: unencrypted storage, public S3 buckets and security groups open to 0.0.0.0/0, missing logging, weak TLS policies, IAM wildcards, unversioned buckets — the same class of findings as Config rules or Security Hub (A10.24, A10.25), but **at PR time rather than after deployment.** That shift-left property is the whole value.

The nuance that matters:

- **Scanning source HCL misses what's computed.** A module call whose values come from variables can't be fully evaluated statically. **Scanning the plan JSON** (`terraform show -json`) is far more accurate because it has resolved values — and it's the mode people under-use.
- **False positives will dominate initially**, and an un-tuned scanner in blocking mode teaches people to bypass it. Start in report mode, tune the rule set, then enforce — the same sequencing as everywhere else in governance (A1.11).
- **Inline suppressions need justification and review** (`#tfsec:ignore:aws-s3-enable-versioning`), or they become permanent and unexamined (A10.28).
- **Scanners check configuration, not intent.** They can't tell you the architecture is wrong, and passing a scan is not a security review.

**TF7.6 — Policy as code**

Beyond scanners, which check against a generic rule library, policy engines enforce **your organisation's** rules against the plan:

- **Sentinel** — HashiCorp's language, TFC/TFE only (TF10.6), with enforcement levels: advisory (warn), soft-mandatory (overridable by an authorised user), hard-mandatory (blocks).
- **OPA/Rego with Conftest** — open source, works anywhere against `terraform show -json` (TF6.13). What Spacelift uses (TF11.3).

```rego
package terraform.policy

deny[msg] {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  resource.change.after.storage_encrypted == false
  msg := sprintf("RDS instance %v must be encrypted", [resource.address])
}
```

Typical policies: no unencrypted storage, no security groups open to the internet on admin ports, mandatory tags (A12.2), approved instance types and regions, cost thresholds requiring approval, **no destroys of resources tagged as protected**, and restricting which modules may be used.

The distinction from scanners: **scanners answer "is this a known misconfiguration"; policy engines answer "does this comply with our rules"** — including rules about cost, naming, ownership, and which team may change what. And the **soft-mandatory / overridable-with-approval** tier is the feature that makes policy workable in practice, because absolute rules generate exceptions that get worked around (TF13.5).

**TF7.7 — Compromised providers and public registry modules**

The risk is direct and worth stating plainly: **a Terraform provider is arbitrary code executing with your cloud credentials, and a module is code that runs with your provider.** A malicious or compromised provider can exfiltrate credentials, create backdoor resources, or alter what it reports. A malicious module can call `local-exec` (TF2.11) or add resources you didn't notice in a large plan.

The mitigations:

- **The lock file with hashes** (TF5.4), committed and reviewed — this is the primary integrity control, and it only works if the file is in git.
- **Pin module versions to tags, never branches** (TF4.3), so the code can't change under you.
- **Review the diff on every upgrade**, both providers and modules. A module bump from 3.2.1 to 3.3.0 is a code change to your infrastructure and deserves the same review as any other.
- **Prefer verified/official namespaces** on the public registry, and prefer well-known community modules over obscure ones — popularity is weak evidence but it's evidence.
- **Vendor or mirror critical dependencies** — a private registry (TF10.7) or a provider mirror means you control what's available and aren't exposed to a registry outage or a deleted version.
- **Restrict which sources are permitted** via policy (TF7.6) — allow only your private registry and an approved list.
- **Least-privilege execution roles** so a compromised provider is bounded by what the role can do (TF7.4) — and separate plan and apply roles limit the blast radius of a read-only run.
- **Network egress restrictions** on runners, so exfiltration has somewhere to fail.

The framing: **this is a software supply chain problem identical in shape to npm or PyPI**, and it should be handled with the same seriousness — which most organisations don't, because Terraform doesn't feel like application code.

**TF7.8 — Preventing a plan from leaking secrets into CI logs**

The exposures, each with its own control:

- **Plan output shows resource attributes**, and while Terraform redacts values marked sensitive, **attributes the provider returns as sensitive-unaware are shown in full** — a generated password in a `random_password` result, a policy document containing a token. Mark outputs and variables `sensitive` (TF7.1), and check what the plan actually renders.
- **Posting the plan to a PR** (TF9.2) publishes it to anyone who can read the repo — which for a public repo is everyone. **Redact before posting, or post to a restricted location and link to it.**
- **The saved plan file contains state data** (TF6.4) — never a public build artefact, encrypted at rest, short retention.
- **`terraform output -json` is unredacted** (TF6.10) — never pipe it to a log.
- **`TF_LOG=TRACE` contains request bodies with credentials** (TF6.16) — never enable it by default in CI, and never attach the log to a ticket unredacted.
- **CI secret masking** — most CI systems redact known secret values from logs automatically, which catches variables sourced from the secret store but not values computed at runtime. Useful, not sufficient.
- **`TF_IN_AUTOMATION`** and disabling colour reduce noise but do nothing for secrets.

The structural answer, again: **if the secret never enters Terraform, it can't leak from Terraform** (TF7.2). Every control above is mitigation for a design that put the secret in scope in the first place.

**TF7.9 — Who can approve an apply, and why that's a security boundary**

**The apply approval is the point at which reviewed intent becomes production change.** Whoever holds it can change production infrastructure — which makes it equivalent in power to holding the credentials themselves, and it should be governed accordingly.

What that means concretely:

- **Separation of duties.** The person who wrote the change should not be the only person who approves it. In a regulated environment this is often an explicit control, and Terraform pipelines are a place it's easy to accidentally lose — a solo-approved PR that auto-applies is a change to production with one pair of eyes on it.
- **Approval must apply to the reviewed artefact.** Approving a plan and then applying a freshly-generated one breaks the control (TF6.4, TF9.3). This is the technical requirement that makes the governance real.
- **Environment-scoped permissions.** Approving a dev apply and approving a prod apply are different privileges (TF9.5). GitHub environments with required reviewers, TFC workspace permissions (TF10.8), and Spacelift approval policies (TF11.3) all express this.
- **The apply role is the credential.** OIDC trust conditions binding the apply role to a protected branch or environment (TF7.4) mean the approval gate is enforced by IAM, not just by the CI system's UI — which matters because CI configuration is often editable by the same people who write the code.
- **Audit.** Who approved what, when, and against which plan, retained. This is standard change-management evidence in a fintech, and Terraform pipelines can produce it well or not at all.

The point to land: **an auto-applying pipeline with no approval gate grants production write access to anyone who can merge**, which is usually a much broader group than anyone intended, and often broader than the group with direct cloud console access. That inversion — where the pipeline is a privilege escalation path around your IAM model — is the thing to notice.

---

## TF8. Structure & scaling

**TF8.1 — Repository layout for many environments and accounts**

A workable layout:

```
platform-infra/
├── modules/                          # local modules, or a separate repo
│   ├── network/
│   ├── service/
│   └── data/
├── live/
│   ├── prod/
│   │   ├── eu-west-1/
│   │   │   ├── network/
│   │   │   │   ├── main.tf
│   │   │   │   ├── terraform.tfvars
│   │   │   │   └── backend.hcl
│   │   │   ├── security/
│   │   │   └── payments/
│   │   └── eu-west-2/
│   ├── staging/
│   └── dev/
└── .github/workflows/
```

The reasoning:

- **Directory per state file**, and the path tells you exactly which account, region, and component you're operating on — which is the main safety property missing from workspaces (TF3.7).
- **`backend.hcl` per directory**, supplied with `-backend-config` (TF6.1), because the backend block can't be parameterised.
- **Modules separate from `live/`** — modules are versioned reusable code, live directories are thin compositions. A live directory should be mostly module calls and variables, not resource definitions.
- **Environment promotion is a change to the higher environment's directory**, referencing a newer module version (TF4.3) — explicit and reviewable.

The alternatives and their tradeoffs: **modules in a separate repository** gives independent versioning and access control at the cost of cross-repo changes for anything that touches both — the right call once modules have consumers outside the team. **Repository per environment** gives the strongest access separation (different reviewers, different permissions on prod) at the cost of drift between repos. **Repository per team** scales ownership but makes cross-cutting changes hard (TF8.7).

The duplication objection is real: `live/prod/eu-west-1/network` and `live/staging/eu-west-1/network` contain near-identical `main.tf`. That duplication is deliberate — it means prod can differ visibly and staging changes can't accidentally affect prod. **This is exactly the duplication Terragrunt exists to remove** (TF8.5), which is a genuine tradeoff rather than a settled question.

**TF8.2 — Environment separation approaches, and defending a choice**

| Approach | Isolation | Complexity | Verdict |
|---|---|---|---|
| CLI workspaces | Weak — shared backend, shared config, shared creds | Low | Poor fit (TF3.7) |
| Directory per environment | Strong — separate state, config, backend, credentials | Medium | The default |
| Repository per environment | Strongest — separate access control and review | High | For strict separation requirements |
| Branch per environment | Weak, and actively harmful | Medium | Avoid |
| TFC/Spacelift workspaces/stacks | Strong — first-class, with per-workspace vars and permissions | Medium (needs the platform) | Good, if you have the platform |

**The defence of directory-per-environment**, which is the mainstream answer:

- **Separate state per environment** means a mistake in dev cannot touch prod (TF3.6).
- **Separate credentials** — the dev pipeline's role can't reach the prod account (TF7.4). This is the property workspaces cannot give you.
- **Environments can differ structurally** where they legitimately should, visibly, in code — rather than through `terraform.workspace` conditionals that make the code you tested different from the code you shipped.
- **The path is the safety mechanism.** You can see which environment you're changing in the PR diff.

**Why branch-per-environment is actively harmful**, since it's a common suggestion: it means environments differ by *merge state*, so promoting a change is a merge rather than a version bump, cherry-picks create divergence that never reconciles, and the code for prod is whatever happens to be on that branch — which is very hard to reason about. It also conflicts with the module-versioning model. The GitOps-adjacent intuition is understandable but Terraform's model doesn't fit it.

**TF8.3 — Monolithic vs fragmented state**

**Monolithic** — few large state files.

- Pros: dependencies resolve naturally within one graph, no cross-state coupling (TF3.14), one apply gives a consistent view, simpler to reason about.
- Cons: **slow plans** that get worse over time (TF8.6); one lock blocks everyone (TF3.4); **enormous blast radius** — one bad apply or destroy affects everything; broad permissions needed because everyone applying needs access to everything; and a corrupted state file is a catastrophe (TF3.12).

**Fragmented** — many small state files.

- Pros: fast plans, parallel work, small blast radius, tight per-state permissions (TF7.3), and failures are contained.
- Cons: **cross-state dependencies** must be managed explicitly (TF3.14, TF8.4); a change spanning several states needs orchestration and ordering; more backends and pipelines to maintain; and **no single plan shows the full effect of a change**, which can hide inconsistency.

The judgement to express: **fragmentation is right up to the point where the coupling cost exceeds the blast-radius benefit.** The signal you've gone too far is when routine changes require applying three states in a specific order — at that point you've distributed a single unit of change across multiple transactions, which is worse than a slightly larger state.

The practical heuristic (TF3.6): **split along lines that already exist** — account, region, environment, team ownership, and rate of change. Don't split for its own sake, and don't split a tightly-coupled set of resources that always change together.

**TF8.4 — Managing dependencies between separately-stated components**

The mechanisms, best to worst:

1. **Data sources querying the provider.** The consumer looks up the VPC by tag or name rather than reading the producer's state. **No state access, no ordering coupling, no output contract** — just a naming convention as the interface. Usually the right answer (TF3.14).
2. **A parameter store as the interface** — the producer writes outputs to SSM Parameter Store, consumers read by path (A10.20). Explicit, versioned, access-controlled per path, and readable by non-Terraform consumers.
3. **`terraform_remote_state`** — direct and simple, with the coupling and state-access costs in TF3.14.
4. **Hardcoded values passed as variables** — crude, but honest and completely decoupled. Fine for a handful of stable values like an account ID.

**Ordering** is the other half, and it's the part that data sources don't solve:

- **Pipeline orchestration** — a workflow that applies networking before workloads. Simple, and brittle when the dependency graph grows.
- **Platform-native stack dependencies** — Spacelift stack dependencies with output sharing (TF11.4), TFC run triggers. **This is one of the strongest arguments for those platforms**: they make cross-state ordering an explicit, managed property rather than a convention.
- **Terragrunt `dependency` blocks** (TF8.5), which both wire outputs and derive the apply order — the problem it was originally built to solve.

The design principle to state: **minimise cross-state dependencies rather than getting better at managing them.** If two components depend on each other bidirectionally, they probably belong in one state. Dependencies should flow one way — foundational (network, IAM) to consuming (workloads) — and the foundational layer should change rarely.

**TF8.5 — Terragrunt: the problem it solves and its cost**

**The problems it addresses**, all real limitations of plain Terraform:

- **Backend configuration can't be parameterised** (TF6.1), so every state directory repeats a nearly-identical backend block. Terragrunt generates it from one root definition.
- **Provider configuration is repeated** across dozens of directories. Terragrunt generates it.
- **Cross-state dependencies and ordering** — `dependency` blocks wire another unit's outputs in and derive the apply order automatically, then `run-all apply` walks the graph (TF8.4).
- **DRY environment configuration** — the `live/prod/.../network` vs `live/staging/.../network` duplication (TF8.1) collapses to a `terragrunt.hcl` per unit that references a shared module with different inputs.
- **Running a command across many units** — `run-all plan` across an account (TF8.7).

```hcl
# live/prod/eu-west-1/payments/terragrunt.hcl
include "root" { path = find_in_parent_folders() }

terraform { source = "git::git@github.com:acme/modules.git//service?ref=v3.2.1" }

dependency "network" {
  config_path = "../network"
  mock_outputs = { vpc_id = "vpc-mock", private_subnet_ids = ["subnet-mock"] }
}

inputs = {
  vpc_id     = dependency.network.outputs.vpc_id
  subnet_ids = dependency.network.outputs.private_subnet_ids
}
```

**The cost, stated honestly:**

- **It's another tool, another DSL, and another thing to learn** on top of Terraform. New team members now need both.
- **It's a wrapper**, so error messages sometimes come from Terragrunt about generated code rather than from your source, and debugging is a layer removed.
- **The generated files** (`backend.tf`, `provider.tf`) mean what runs isn't quite what you wrote.
- **`mock_outputs` is a genuine sharp edge** — plans against not-yet-applied dependencies use mocks, so a plan can be misleading in ways that only surface at apply.
- **It's third-party** (Gruntwork), so its support for new Terraform features lags, and you're taking a dependency on another vendor's roadmap.
- **`run-all` across many units** can produce a very large blast radius in one command, which is the thing you were splitting state to avoid.

The judgement: **Terragrunt is most valuable in a many-account, many-region estate where the duplication is genuinely painful** — and less valuable now than it was, because Terraform has closed some of the gap and because **Spacelift, TFC, and similar platforms solve the ordering and configuration problems at the platform layer instead** (TF11.8). Adopting it is a long-term commitment; it's hard to remove once your whole live tree depends on it.

**TF8.6 — Very slow plans on large state**

Causes and their fixes, in the order to try them:

1. **Refresh dominates.** Terraform refreshes every resource by default, which is one or more API calls each. **`-refresh=false`** skips it (TF3.11) — the fastest immediate win, at the cost of planning against a possibly-stale view. Reasonable for a routine change; risky if drift is likely.
2. **Too many resources in one state.** The structural fix is **splitting state** (TF3.6, TF8.3). Everything else is mitigation.
3. **Provider API rate limiting.** Manifests as a plan that's slow with no obvious hotspot; visible in `TF_LOG_PROVIDER` as throttling responses (TF6.16). Fix with `-parallelism` tuning (up or down depending on whether you're throttled or under-utilised) and provider-level retry configuration.
4. **Expensive data sources** — a data source enumerating thousands of objects on every plan. Cache the value, narrow the query, or replace it with an explicit variable.
5. **Module and provider download time** in CI — fix with **`TF_PLUGIN_CACHE_DIR`** and a persisted `.terraform` cache between runs (TF6.17).
6. **Very large state file transfer** on every operation.

The mitigations that are *not* fixes, worth flagging as such: **`-target`** (TF6.6) speeds up a plan by hiding most of it, which is exactly the wrong trade as a routine practice.

The framing: **plan time is a leading indicator that state has outgrown its boundaries.** A plan that takes fifteen minutes doesn't just waste time — it changes behaviour, because people stop running plans, stop reading them fully, and start reaching for `-target`. So the velocity cost compounds into a safety cost, and that's the argument for treating it as a priority rather than an annoyance.

**TF8.7 — Rolling a change across many accounts safely**

The approach:

1. **Change the module and version it** (TF4.3). The change itself lives in one place.
2. **Roll the version bump progressively**, not everywhere at once: one sandbox account → all dev → one prod account → the rest of prod. Each wave is a separate, reviewed change.
3. **Plan everywhere before applying anywhere in a wave.** Aggregate the plans and look for anything unexpected — a plan that shows a destroy in one account and not others means that account has drifted or differs in a way you didn't know about (TF1.4). **This step is what catches the surprises**, and skipping it is how a routine module bump takes out an account nobody remembered was special.
4. **Automate the iteration** — Terragrunt `run-all` (TF8.5), a matrix pipeline, Spacelift stacks (TF11.2), or a script that iterates accounts (A14.4).
5. **Define the abort condition before starting**, and make it specific: any unexpected destroy, any plan that fails, any account whose plan differs materially from the others.
6. **Verify between waves** — not just that the apply succeeded but that the thing still works.

The realities to name:

- **Accounts are never as identical as you think.** One has a manually-created resource, one is in a different region, one has an older module version pinned. The plan-everywhere step is what surfaces that.
- **Rollback is forward** (TF9.7) — you cannot un-apply, so the recovery is applying the previous module version, which must itself be tested.
- **Rate limits and quotas** apply per account and to the API in aggregate (A11.9).
- **This is exactly the same shape as the governance rollout in A1.15** — measure first, phase, define the exception process — and drawing that parallel is a good sign of pattern recognition.

**TF8.8 — The platform team's module ownership model**

The model that works:

- **The platform team owns modules as a product**, with a public interface (TF4.1), versioning (TF4.3), documentation (TF4.7), tests (TF4.8), a changelog, and a support path. Not as internal code they happen to share.
- **Application teams own their live configurations** — the composition, the variables, the environment values. They call modules; they don't fork them.
- **Modules encode decisions** — encryption, logging, tagging, network placement, backup — so a team using the module is compliant by default (TF4.2). That's the value proposition, and it's what makes the module worth using rather than mandated.
- **Contribution is welcome and reviewed.** A team needing something the module doesn't do should be able to raise a PR, not wait in a queue. **A platform team that's the only permitted author becomes a bottleneck** (TF4.10, TF13.5).
- **Deprecation has a process** — advance notice, a migration path with `moved` blocks (TF4.9), and a deadline.

The tensions to acknowledge honestly:

- **Golden path vs escape hatch.** The module must cover the common case beautifully and permit the unusual case somehow — otherwise teams fork it, and once they fork you've lost the compliance property entirely.
- **Mandating module use** works only if the modules are genuinely better than the alternative. Enforcing via policy (TF7.6) a module that people find obstructive produces resentment and workarounds.
- **Knowing your consumers.** A private registry tells you who's using what version (TF10.7); git sources don't, and you find out you broke someone when they complain.

The measure of success: **the paved road is the path of least resistance** (TF13.5). If teams use the modules because they're the fastest way to ship, the model is working; if they use them because they're required, it's fragile.

**TF8.9 — Onboarding a team used to the console**

The approach that works, and the point is that this is a change-management problem more than a technical one:

1. **Start with something they want.** Don't begin by taking away console access. Begin by using IaC to give them something — a new environment provisioned in minutes, a repeatable dev stack, an easy way to replicate a setup they currently rebuild by hand.
2. **Import what they already have** (TF2.13, TF13.4) rather than asking them to rebuild it. The estate is theirs; IaC should adopt it, not replace it.
3. **Give them modules, not a blank page.** A team new to Terraform writing raw resource blocks will produce something that works and is hard to maintain. A module call with five inputs is a much gentler start (TF8.8).
4. **Read-only console access is fine and useful.** People need to see what exists. Remove *write* access, and do it after the pipeline works, not before.
5. **Make the pipeline fast.** If a change takes forty minutes to ship through review and CI when the console takes thirty seconds, they will use the console — and they will be right to (TF13.5).
6. **Pair on the first few changes.** The failure mode is a team that produces a broken plan, can't interpret it, and concludes Terraform is hostile.
7. **Teach plan reading explicitly** (TF6.3). It's the single most important skill and it isn't obvious.
8. **Have an emergency path from day one** (TF13.6), so the first incident doesn't destroy trust in the whole approach.

What to avoid: **starting with the most complex thing they own**; **mandating before enabling**; and **treating console changes as a discipline problem** rather than as feedback about the pipeline (TF1.5).

---

## TF9. Automation & CI/CD

Pipeline mechanics in general are the CI/CD domain; this is what's Terraform-specific.

**TF9.1 — Designing the pipeline**

The stages, and what each catches:

```
On PR:
  1. terraform fmt -check -recursive       # style, seconds
  2. terraform init -backend=false         # no state credentials needed
  3. terraform validate                    # syntax, types, references
  4. tflint                                # provider-specific correctness
  5. tfsec / checkov                       # security misconfiguration (TF7.5)
  6. terraform init                        # now with backend
  7. terraform plan -out=tfplan            # the real check
  8. policy check on plan JSON             # OPA/Conftest (TF7.6)
  9. infracost                             # cost delta
 10. post plan to PR                       # (TF9.2)

On merge to main:
 11. manual approval for prod              # (TF9.5)
 12. terraform apply tfplan                # the same artifact (TF9.3)
```

The design points:

- **Cheap checks first.** `fmt` and `validate` take seconds and need no credentials; failing fast on those saves runner time and reviewer attention.
- **Separate plan and apply credentials** (TF7.4) — the PR job assumes a read-only role, and the apply role is bound to the protected branch. This means a fork PR can run a plan and cannot possibly apply.
- **Plan on PR is the review artefact** (TF9.2); everything before it is a gate to make the plan trustworthy.
- **Policy evaluated against the plan JSON**, not the source, because that's where values are resolved (TF7.5).
- **Concurrency control** so two PRs don't plan against the same state simultaneously (TF9.4).

**TF9.2 — Posting the plan to a PR, and why it's the key control**

The plan is posted as a comment (or a check summary) so reviewers see exactly what the change does to infrastructure.

**Why it's the key control**, stated properly:

- **Code review of HCL is not review of the change.** A three-line diff can produce a database replacement (TF12.1), and a reviewer reading only the diff cannot know that. The plan is the only artefact that shows the actual effect.
- **It's where destroys are caught.** `Plan: 2 to add, 0 to change, 1 to destroy` on a PR that claimed to add a tag is the moment to stop — and it's visible to everyone, not just the author.
- **It creates a reviewable record** for change management: what was proposed, who approved it, when.
- **It shifts the conversation** from "does this code look right" to "is this the change we want", which is the right conversation.

The implementation details that matter:

- **Truncation.** GitHub comments have a size limit and large plans exceed it. Post a summary with the counts and a link to the full plan, or collapse the detail — but **never silently truncate the part containing the destroys**.
- **Secrets** (TF7.8) — the plan can contain sensitive attributes, and a PR comment on a public repo is public.
- **Stale comments** — update the existing comment rather than appending a new one per push, or the PR becomes unreadable and reviewers read the wrong plan.
- **The plan must correspond to what will be applied** (TF9.3).

**TF9.3 — Why plan and apply must use the same artifact**

If the pipeline plans on PR, a human approves, and then apply generates a *fresh* plan on merge, **the approval was for a different change than the one applied.** The gap can be:

- **Code changed** between the plan and the merge (another PR merged first, or the branch was updated).
- **The world changed** — someone made a console change, another pipeline applied, a resource was deleted.
- **Variables or provider versions resolved differently** — an unpinned provider released a new version between the two runs (TF5.4).

So the approval control is void: you reviewed one thing and shipped another. **In a regulated environment that's a genuine audit finding**, not a theoretical concern.

The correct pattern: **save the plan** (`-out=tfplan`, TF6.4), **persist it as an artifact**, and **apply exactly that file**. Terraform verifies the state serial hasn't moved and refuses if it has — which is the safety net that turns "the world changed" from a silent difference into a clear failure you re-plan for.

The requirements to make it work: **identical Terraform and provider versions** between the plan and apply jobs (pin them explicitly); **the artifact stored securely** because it contains state data (TF7.8); **a short expiry**, since an old plan against a moved state will fail anyway; and **the same working directory and variables**.

**TF9.4 — Concurrent pipeline runs against one state**

State locking (TF3.4) makes concurrency **safe** — the second run fails to acquire the lock. But failing is still disruptive: a queued PR plan errors out, and a developer sees a red check for reasons unrelated to their change.

The controls:

- **Concurrency groups in CI**, keyed on the state path — GitHub Actions `concurrency: terraform-${{ matrix.state }}`, so runs against the same state queue rather than collide. This is the main mechanism.
- **Cancel in-progress *plans*** on a new push (a superseded plan is worthless), but **never cancel an in-progress apply** — killing an apply mid-flight is exactly how you get a stuck lock (TF3.5) and a partially-applied change (TF9.8).
- **Serialise applies globally per state**; plans can be more relaxed since they don't write.
- **Platform-native queuing** — TFC and Spacelift queue runs per workspace/stack automatically, which is one of the practical conveniences they provide (TF11.1).
- **Timeouts shorter than any plausible legitimate run**, so a hung job releases eventually.

The related point: **fragmenting state reduces contention** (TF8.3) — one monolithic state means every team's changes serialise behind each other, which is a velocity cost people don't attribute to state design.

**TF9.5 — Manual approval gates for production**

The design:

- **Gate the apply, not the plan.** Plans should run freely — they're read-only and they're what reviewers need.
- **Use the CI system's environment protection** — GitHub Environments with required reviewers, GitLab protected environments, TFC workspace apply permissions (TF10.8). The gate should be enforced by the platform, not by convention.
- **Back it with IAM** (TF7.4) — the apply role's OIDC trust condition scoped to the protected environment, so approval isn't merely a UI step someone can bypass by editing the workflow.
- **Different approvers for different environments.** Dev may auto-apply; prod requires a named group.
- **Approve the artifact** (TF9.3), not the intent.
- **Separation of duties** — the author should not be a sufficient approver (TF7.9).

The judgement to express: **auto-apply is appropriate in low-risk environments and the friction of a gate is only worth it where the blast radius justifies it.** Gating everything trains people to approve without reading, which is worse than no gate because it manufactures false assurance. The useful shape is: dev auto-applies, staging auto-applies on merge, prod requires approval — and the approval is meaningful because it's rare enough to be read.

The thing to add: **an approval gate on a plan nobody reads is theatre.** The control is the plan review (TF9.2); the gate is what makes there be time for it.

**TF9.6 — Scheduled drift detection, and what to do about it**

```bash
terraform plan -detailed-exitcode -refresh-only
# exit 0 = no drift, 2 = drift detected, 1 = error
```

Run on a schedule (nightly or weekly) per state, and alert on exit code 2.

**What to do about detected drift** is the substance of the item, because the answer is not "revert it":

1. **Investigate before acting.** Drift means the world and the code disagree; it does *not* say which is right. An emergency fix applied during an incident is legitimate drift, and auto-reverting it re-breaks production (TF1.5).
2. **Categorise it.** Was it an emergency change (reconcile the code to match), a mistake (revert), another tool legitimately managing the attribute (add `ignore_changes`, TF2.9), or a provider/API-side change (usually accept)?
3. **Then reconcile deliberately** — either update the code and apply, or apply to revert.

**Auto-remediation is a genuine tradeoff.** Automatically applying to revert drift keeps the estate consistent and is defensible in tightly-controlled production. It also means a legitimate emergency fix silently disappears, potentially in the middle of an incident. Spacelift and TFC both support it (TF11.5), and the right default for most organisations is **detect and notify, not auto-revert** — with auto-revert reserved for specific high-assurance resources like security groups or bucket policies where any drift is definitionally wrong.

The practical points: **route the alert to the owning team**, not a central inbox (A10.29); **track drift as a trend**, because recurring drift in one place is a signal that something else owns that resource or that the pipeline is too slow (TF13.5); and **exclude known-noisy attributes** or the alert becomes background noise.

**TF9.7 — Rollback in Terraform terms, and why it isn't a real operation**

**There is no rollback.** Terraform has no undo, no transaction log, and no previous-version restore for infrastructure. What people mean by rollback is **applying the previous version of the code**, which is a *forward* operation with all the same risks.

Why that distinction matters:

- **Reverting the code and applying may not restore the previous state.** If the change replaced a resource, reverting replaces it again — a new instance, a new ID, and if it held data, the data is gone. You cannot un-destroy.
- **The revert apply can fail** for its own reasons, leaving you worse off than before.
- **Some changes are irreversible in practice**: a deleted RDS instance, a released Elastic IP, a destroyed KMS key (A10.7). The revert plan can't recreate what's gone.
- **Restoring an old state file is not a rollback either** — it changes Terraform's belief about the world without changing the world (TF3.13), which makes things worse.

So the correct framing: **prevention over recovery.** The controls are plan review (TF9.2), `prevent_destroy` on irreplaceable resources (TF2.9), policy denying destructive operations (TF7.6), progressive rollout across environments (TF8.7), and backups of anything stateful (A11.7) — because the actual recovery for data loss is a database restore, not a Terraform operation.

The honest answer to "how do you roll back": **"we don't — we roll forward, and the real controls are upstream of the apply."** Being able to say that clearly, and then list the upstream controls, is a much stronger answer than describing a rollback procedure that doesn't exist.

**TF9.8 — A partially applied change after a mid-apply failure**

**Terraform applies are not transactional.** If an apply fails at resource 7 of 12, resources 1–6 exist and are recorded in state, 7 may be in an unknown condition, and 8–12 were never attempted.

The recovery:

1. **Don't panic and don't immediately re-run.** Read the error — it names the resource and the provider error.
2. **State is usually consistent for what completed.** Terraform writes state as it goes, so successfully created resources are recorded. The dangerous case is **a resource created in the cloud where the state write failed** — that becomes an orphan and shows as "already exists" on the next apply (TF12.4).
3. **Fix the underlying cause** — a quota (A11.9), a permission, an invalid argument, a dependency that wasn't ready, a rate limit.
4. **Re-run the plan and read it carefully.** Idempotency (TF1.2) means Terraform will attempt only what's missing. **This is the property that makes recovery straightforward in most cases**, and it's worth saying explicitly.
5. **For a resource in an inconsistent state**, `-replace` it (TF6.9) or import the orphan (TF3.8).
6. **`-target` is legitimate here** (TF6.6) if you need to fix one thing before the rest can proceed — followed by a full apply to reconcile.

The specific hazards: **an interrupted apply may leave a lock held** (TF3.5); **`create_before_destroy` failures** can leave both old and new resources; and **a failed provisioner taints the resource** (TF2.11), so the next apply destroys and recreates something that may be fine.

The preventive framing: **smaller state files mean smaller partial-failure surfaces** (TF8.3), and **applies that are idempotent and re-runnable make partial failure a nuisance rather than an incident.**

**TF9.9 — Ephemeral environments and teardown discipline**

A per-PR or per-branch environment, created on open and destroyed on merge or close.

The mechanics: a workspace (**one of the legitimate uses**, TF3.7) or a generated state key per PR; a naming convention including the PR number; the pipeline creating on open and running `terraform destroy` on close.

**Teardown discipline is the entire risk**, and it's what the item is really about:

- **Destroy on PR close *and* on merge**, and handle the case where the PR is closed without merging.
- **A scheduled reaper** that destroys environments older than N days regardless — because the close hook will fail sometimes (a cancelled job, a deleted branch, a CI outage), and without a backstop those environments live forever. **This is the control people skip and then discover months later in a cost review** (A12.3).
- **Tag everything with the PR number and a TTL** so orphans are identifiable and attributable.
- **Budget alerts on the ephemeral account** (A12.6).
- **A separate account for ephemeral environments**, so a reaper that's slightly too aggressive can't touch anything real, and so quota exhaustion is contained (A11.9).

The design constraints worth naming: **ephemeral environments must be cheap and fast to create**, or nobody uses them — which means they can't include heavyweight stateful resources, so they typically share a database or use a seeded lightweight one. And **`prevent_destroy` must not be set** on anything in them, or teardown fails (TF2.9). That's a real tension with the module you use in production, and it's usually resolved with a variable that disables the protection in ephemeral contexts — deliberately, and visibly.

---

## TF10. Terraform Cloud & Enterprise

**TF10.1 — The workspace model, and how it differs from CLI workspaces**

A **TFC workspace** is a first-class object owning: its own **state**, its own **variables** (including sensitive ones), its own **credentials**, its own **VCS connection and working directory**, its own **run history and audit trail**, and its own **permissions**.

**A CLI workspace is just an alternative state file within one backend** (TF3.7). That's the whole difference, and it's substantial:

| | CLI workspace | TFC workspace |
|---|---|---|
| State | Separate | Separate |
| Variables | Shared config, shared vars | Per-workspace |
| Credentials | Shared | Per-workspace |
| Permissions | None | Per-workspace teams and roles |
| Run history | None | Full, with audit |
| Configuration | One shared config | Own VCS repo/directory |

**This is why TFC workspaces *are* an appropriate environment boundary and CLI workspaces are not** — the objections in TF3.7 (shared credentials, shared config, no access control) all disappear. A prod workspace can have different variables, different cloud credentials, different approvers, and a different working directory in the repo.

The naming convention matters at scale — `<app>-<environment>-<region>` — because a large organisation ends up with hundreds and the workspace name is the primary navigation. And **workspaces map roughly one-to-one with state files** in the layout of TF8.1, so the design thinking is the same (TF3.6).

**TF10.2 — Remote vs local execution**

- **Remote execution** — plan and apply run on TFC's infrastructure. The CLI (or VCS trigger) submits the configuration; TFC executes and streams output back. Variables and credentials live in the workspace and never touch a developer's machine.
- **Local execution** — TFC stores state and provides locking and history, but the run happens on your machine or your CI runner.

When you'd choose each:

- **Remote is the default and the point of the product** — centralised credentials, consistent Terraform versions, full audit of every run, policy enforcement (TF10.6), and no one needing cloud credentials locally.
- **Local execution** when: you need **network access TFC's runners don't have** (private endpoints, on-prem, a VPC-internal API) — though **agents** are the better answer to that (TF10.9); you have a heavily customised pipeline that TFC's run environment can't accommodate; or you're **migrating incrementally** and want state management first, execution later.

The migration point worth naming: **local execution mode is a good first step** for an organisation moving to TFC — you get remote state, locking, and history without changing how runs happen, then move to remote execution once the workspace structure is settled.

**TF10.3 — VCS-driven workflows and speculative plans**

Connect a workspace to a repository and directory. Then:

- **A PR touching that directory triggers a speculative plan** — a plan that runs and reports but **can never be applied**. The result posts to the PR as a status check.
- **A merge to the tracked branch triggers a run** — plan, then apply (auto or gated, TF10.8).

**Speculative plans are the feature that makes this valuable**: they give you TF9.2's control (the plan as the review artefact) natively, with the plan executed using the workspace's real credentials and variables, without any risk that a PR can apply. Contrast with a hand-built pipeline where you have to carefully separate plan and apply credentials to get the same property (TF7.4).

The configuration details: **`working_directory`** so one repo drives many workspaces (TF8.1); **trigger patterns / trigger prefixes** so a workspace only runs when its own paths change — without which every merge queues runs on every workspace, which is both slow and noisy; and **`auto_apply`** per workspace, typically on for dev and off for prod.

The alternative is the **API/CLI-driven workflow**, where your own CI uploads a configuration version — used when you need pipeline steps TFC's VCS flow doesn't provide.

**TF10.4 — Variable sets and workspace variables**

Two kinds of variable in TFC:

- **Terraform variables** — become `var.x` in the configuration.
- **Environment variables** — set in the run environment, which is how cloud credentials (`AWS_ACCESS_KEY_ID`, or better, dynamic provider credentials) and `TF_LOG` get in.

Either can be marked **sensitive**, which means **write-only**: it can be set and used but never read back through the UI or API. That's genuinely useful — it's a stronger property than a CI secret store that lets an admin reveal values.

**Variable sets** apply a group of variables to many workspaces, or to a whole project or organisation. The obvious use: cloud credentials and standard tags applied to every workspace in an environment, defined once. Precedence runs workspace-specific over variable set, with more specific scopes winning.

The point worth making: **the sensible pattern is credentials in an org- or project-scoped variable set, environment-specific values on the workspace.** And better than either — **dynamic provider credentials**, where TFC uses OIDC to assume a role per run (TF7.4), so no long-lived cloud credentials are stored in TFC at all. That's the current best practice and worth naming, because storing static AWS keys in TFC is exactly the pattern OIDC exists to eliminate (A1.4).

The caveat that still applies: **sensitive variables end up in state** (TF7.1), so TFC's write-only variables protect the input, not the stored output.

**TF10.5 — Run tasks**

A run task is a **webhook at a defined stage of a run** — pre-plan, post-plan, pre-apply, post-apply. TFC calls your endpoint (or a partner's) with run details, waits for a response, and either proceeds or blocks depending on whether the task is advisory or mandatory.

Uses: **third-party security scanning** (Snyk, Bridgecrew) on the plan; **cost estimation and approval** (Infracost); **CMDB or change-management integration** — creating a ServiceNow change record and blocking until it's approved; **custom organisational checks** that Sentinel can't express.

Their place in a governed workflow: **run tasks are the extension point for things that need to happen outside Terraform but inside the run's control flow.** Sentinel (TF10.6) evaluates the plan against policy; run tasks call out to systems that have their own view. In a regulated environment the ServiceNow integration is often the concrete reason they're used — it makes the change record a hard gate on the apply rather than a parallel manual process.

The tradeoff: a mandatory run task is now a **dependency in your apply path**, so its availability affects your ability to deploy. Same consideration as an admission webhook (K8.8).

**TF10.6 — Writing and enforcing Sentinel policies**

```python
import "tfplan/v2" as tfplan

required_tags = ["Environment", "Owner", "CostCentre"]

all_resources_tagged = rule {
  all tfplan.resource_changes as _, rc {
    rc.mode is not "managed" or
    rc.change.actions is ["delete"] or
    all required_tags as t {
      keys(rc.change.after.tags else {}) contains t
    }
  }
}

main = rule { all_resources_tagged }
```

**Enforcement levels are the important part:**

- **Advisory** — logs a warning, run proceeds.
- **Soft-mandatory** — blocks, but a user with override permission can proceed (and the override is recorded).
- **Hard-mandatory** — blocks unconditionally; the only way past is changing the policy.

**The soft-mandatory tier is what makes policy usable.** Hard rules generate genuine exceptions, and if there's no legitimate override path, people find illegitimate ones. Soft-mandatory with a recorded, attributable override is the mechanism that lets you enforce broadly while handling the real cases (A10.28, TF13.5).

Typical policies: mandatory tags, approved regions, no unencrypted storage, instance type allow-lists, cost thresholds, **restricting destroys of protected resources**, and enforcing module sources.

The honest caveat: **Sentinel is TFC/TFE-only and is its own language.** OPA/Rego with Conftest (TF7.6) does the same job, is portable, and works in any pipeline — so unless you're already committed to TFC, OPA is the more transferable investment. Worth saying, because it's a genuine consideration rather than a preference.

**TF10.7 — The private module registry**

Publish internal modules to a registry within your TFC organisation, then consume them with version constraints:

```hcl
module "service" {
  source  = "app.terraform.io/acme/service/aws"
  version = "~> 3.2"
}
```

The publishing workflow: a repo named `terraform-<provider>-<name>` (the naming convention is mandatory), connected to the registry, and **releases are driven by git tags** — tag `v3.2.1` and the registry publishes that version.

What it gives you over git sources (TF4.4):

- **Version constraint syntax** (`~> 3.2`) rather than an exact ref, so patches flow without a PR.
- **Discoverability** — a browsable catalogue with generated documentation from the module's README and variable descriptions (TF4.7).
- **Usage visibility** — you can see which workspaces consume which module versions, which is exactly what you need to manage a deprecation (TF4.9) and which git sources cannot tell you.
- **Access control** aligned with the organisation.

The operational points: **tags must be semver-formatted** (`v1.2.3`), a version once published is immutable, and the registry does not run tests — so the release process still needs CI validation before tagging (TF4.8).

**TF10.8 — Teams, permissions, and approval requirements**

The model: **organisation → projects → workspaces**, with **teams** granted permissions at each level.

Workspace permission levels: **read** (view state and runs), **plan** (queue speculative plans), **write** (apply), **admin** (manage settings, variables, and permissions). Plus organisation-level permissions for managing policies, the registry, and teams.

The design that follows:

- **Application teams get `write` on their non-prod workspaces and `plan` on prod** — they can propose but not apply to production. That single split is the main structural control (TF7.9).
- **A platform or release team holds `write` on prod workspaces**, or prod requires explicit apply approval by a named team.
- **Project-level permissions** avoid granting per workspace across hundreds of them.
- **`admin` is tightly held** — it includes managing variables, so it's equivalent to holding the credentials.

The approval mechanism: **auto-apply off** on prod workspaces means every run stops after the plan and waits for someone with apply permission to confirm — with the confirmation recorded against a specific plan (TF9.3) and a specific person. That's the audit artefact.

The comparison worth drawing: this is the same separation-of-duties model as a CI pipeline with protected environments (TF9.5), but **enforced by the platform holding the credentials rather than by the CI system's configuration** — which is stronger, because CI configuration is usually editable by the people it's meant to constrain.

**TF10.9 — Agents and self-hosted execution**

A TFC **agent** is a lightweight process you run **inside your own network**, which polls TFC for runs, executes them locally, and reports back. The workspace is configured to use an agent pool rather than TFC's shared runners.

**Why it's needed**: TFC's hosted runners are on the public internet. They cannot reach:

- **Private API endpoints** — a Kubernetes API server with no public endpoint, an internal Vault, an on-prem vCenter or database.
- **Resources behind a VPN or Direct Connect** (A3.12).
- **Anything requiring a fixed source IP** for allow-listing.

Since Terraform providers need network access to the APIs they manage, a private-only control plane simply cannot be managed by a hosted runner. **The Kubernetes provider against a private EKS endpoint is the canonical example** and comes up constantly.

The considerations: agents run **your** code with **your** network access, so they're a privileged component — they need hardening, isolation, and their own credentials (which is where dynamic provider credentials help, TF10.4). They need capacity planning and monitoring since they're now in your deploy path. And **agent pools can be scoped per project or workspace**, so a prod agent pool with prod network access is separate from a dev one — which is worth doing.

The equivalent concept in the alternatives: **Spacelift worker pools** (TF11.2) and self-hosted CI runners solve the identical problem.

**TF10.10 — State versioning, rollback, and audit**

TFC keeps **every version of state** for a workspace, with the run that produced it, the user who triggered it, and the timestamp. You can view, download, compare, and **roll back to a prior state version** through the UI or API.

The value: **state history is a first-class, browsable audit trail** rather than a collection of S3 object versions you'd have to correlate manually (TF3.3). "What did this workspace look like on the 12th, and which run changed it" is a couple of clicks.

**The rollback caveat is essential and must be stated**: rolling back a state version **changes Terraform's record, not the infrastructure** (TF9.7). After rolling back, state describes an earlier world while the real world is unchanged — so the next plan will propose whatever is needed to bring reality back in line, which may include destroying things created since. **It is a state repair tool, not an undo button**, and using it as an undo is how you make an incident worse (TF3.13).

Where it's legitimately useful: recovering from a corrupted state write, undoing a bad `state rm` or a mistaken import, or recovering after a failed state manipulation — the same use cases as S3 versioning (TF3.12), with a better interface.

Alongside it, **the organisation audit trail** records logins, permission changes, variable changes, and policy overrides — which is the evidence a compliance function asks for.

**TF10.11 — The cost model and what drives it**

TFC's commercial model is based on **resources under management (RUM)** — the count of managed resources across all workspaces' state — with free, Standard, Plus, and Enterprise tiers layering on features (policy, agents, drift detection, SSO, audit).

**What drives cost, and this is where the practical judgement is:**

- **Resource count, not activity.** A workspace that never runs still costs if it holds resources.
- **Verbose modules inflate it disproportionately.** A community module that creates 60 resources where you needed 12 costs 5× in RUM terms. **This creates a genuine tension with using large public modules** (TF4.4) and is a real consideration people miss until the renewal.
- **Resources that aren't really infrastructure** — dozens of IAM policy attachments, route table associations, security group rules as individual resources — count the same as an EKS cluster. Using inline blocks rather than separate resources where the provider offers both actually reduces the count.
- **Ephemeral environments** (TF9.9) inflate the count while they exist.
- **Feature tier**, particularly if you need Sentinel, agents, or SSO — which most enterprises do, so the effective floor is higher than the headline.

The reason this item is in the matrix: **the cost model influences architecture**, and being aware of that is a platform-lead consideration. It's also the main driver of "should we use TFC at all" (TF11.8) — at scale, RUM pricing can exceed the cost of running Atlantis or Spacelift, and that arithmetic is worth doing explicitly rather than assuming.

**TF10.12 — No-code modules and workspace automation via the API**

**No-code modules** let a platform team publish a module that non-Terraform users provision through a form in the TFC UI. TFC generates the workspace and configuration behind the scenes; the consumer picks inputs and clicks. It's TFC's answer to Service Catalog (A15.7) and to the self-service question in TF13.5 — a genuine paved road for teams who shouldn't need to learn HCL.

The tradeoff: it's a very constrained interface, so the module must cover the case completely, and consumers can't compose it with anything else. It works for well-bounded, standardised things (a standard S3 bucket, a standard service) and not for anything requiring adaptation.

**The API** is the more important half for a platform team: workspaces, variables, variable sets, teams, permissions, run triggers, and runs are all API-managed — and there's a **`tfe` Terraform provider**, so you can manage TFC itself with Terraform.

That's the pattern worth naming: **workspace-as-code.** A repository defining every workspace, its variables, its permissions, and its VCS connection, applied by a bootstrap workspace. At the scale of hundreds of workspaces, clicking them into existence is unmanageable and produces inconsistency; generating them from a definition is the only workable approach — and it's the same reasoning as account vending in AWS (A1.13).

---

## TF11. Alternative platforms

**TF11.1 — What Spacelift adds over a plain CI pipeline**

The things you'd otherwise build yourself:

- **State, locking, and run history** as managed concerns.
- **Policy as code with OPA** at multiple decision points (TF11.3) — richer than most hand-rolled pipeline checks, and evaluated by the platform rather than by a step someone can remove.
- **Stack dependencies with output sharing** (TF11.4) — the cross-state ordering problem (TF8.4) solved natively, which is genuinely hard to build well in plain CI.
- **Drift detection and optional reconciliation** on a schedule (TF11.5), built in.
- **Worker pools** for private network access (TF11.2), equivalent to TFC agents.
- **A run UI** designed for infrastructure — plan visualisation, approval, resource-level detail — rather than a generic log viewer.
- **Contexts** for shared configuration and credentials across stacks.
- **Multi-tool support** — Terraform, OpenTofu, Pulumi, CloudFormation, Ansible, Kubernetes — under one governance model, which matters if your estate isn't Terraform-only.

The honest framing: **a competent team can build most of this in GitHub Actions.** What they get from Spacelift is not capability but **not having to build and maintain it**, plus a coherent policy model that's hard to retrofit. The question is whether the engineering time saved exceeds the licence cost and the lock-in (TF11.9) — which depends heavily on how many stacks and teams you have.

**TF11.2 — Spacelift stacks, contexts, worker pools**

- **Stack** — the core unit: a repository, a branch, a project directory, a backend/state, a set of variables, and its own run history and policies. Roughly equivalent to a TFC workspace (TF10.1) or one directory in TF8.1.
- **Context** — a named bundle of environment variables, files, and hooks attached to multiple stacks. This is how shared credentials, common configuration, and mounted files are managed without duplication across stacks — the equivalent of TFC variable sets (TF10.4), with the addition of **hooks** (before/after plan/apply) which is a useful extension point.
- **Worker pool** — self-hosted runners executing runs inside your network. Same purpose as TFC agents (TF10.9): reaching private endpoints, meeting egress requirements, and controlling the execution environment. Spacelift's public workers exist but private pools are the norm for anything real.

The scaling mechanism worth naming: **stacks can be generated programmatically** via the `spacelift` Terraform provider — the same workspace-as-code pattern as TF10.12, and equally necessary once you have hundreds.

**TF11.3 — Spacelift's OPA-based policies**

Spacelift evaluates **Rego policies at distinct decision points**, which is what makes its governance model more granular than most:

- **Plan policy** — evaluates the plan; can deny or warn. The equivalent of Sentinel (TF10.6): no unencrypted storage, mandatory tags, no destroys of protected resources.
- **Approval policy** — decides **whether a run needs human approval, and from whom**, based on the plan's content. This is the interesting one: *"any run that destroys a resource, or touches production IAM, requires two approvals; everything else auto-applies."* Risk-proportionate approval, expressed as code, rather than a blanket gate.
- **Push policy** — decides what a git push does: trigger a run, trigger a proposed (speculative) run, or ignore. This is how you implement path-based triggering and custom branching workflows.
- **Trigger policy** — decides which stacks to run after another stack finishes, which is how dependency chains are expressed dynamically.
- Plus login, access, and notification policies.

The value to articulate: **policy decides the workflow, not just the outcome.** In a plain pipeline the approval requirement is static YAML; here it's a function of what the change actually does. That's a meaningfully better governance model, and it directly addresses the "gate everything and nobody reads it" problem (TF9.5, TF13.5) — you gate the risky 5% and let the rest flow.

The cost: **Rego is a real learning curve**, and policies become infrastructure themselves that need testing and review.

**TF11.4 — Stack dependencies and output sharing in Spacelift**

Stacks can declare dependencies on other stacks, with **outputs from the upstream stack passed as inputs to the downstream one**. Spacelift builds the dependency graph and triggers runs in order.

This is the native solution to TF8.4 and directly addresses the problems with `terraform_remote_state` (TF3.14):

- **Ordering is explicit and enforced** by the platform rather than by pipeline convention.
- **The consumer never reads the producer's state file**, so it doesn't need state access — which removes the "read access to every secret in that state" problem (TF3.2). Only the declared outputs cross the boundary.
- **Changes propagate deliberately** — an upstream apply can trigger downstream runs, so a VPC change flows to dependent stacks in the right order rather than being picked up whenever someone next applies.

The considerations: **a deep dependency chain means one change triggers a long cascade**, which is powerful and can be surprising — so the graph needs to be shallow and deliberate, the same argument as module composition (TF4.6). And you're now expressing your architecture's dependency structure in Spacelift's model, which is a meaningful piece of the lock-in in TF11.9.

**TF11.5 — Drift detection and reconciliation in Spacelift**

Scheduled drift detection runs a plan against each stack on a cron and reports differences, with the option to **automatically reconcile** by applying.

The mechanics are TF9.6; what Spacelift adds is that it's built in, scheduled per stack, and the reconciliation decision can be **governed by policy** (TF11.3) — so you can auto-reconcile drift on security groups while merely alerting on drift in application infrastructure.

The judgement remains as in TF9.6: **detect-and-notify is the right default; auto-reconcile is appropriate for specific high-assurance resources.** Auto-reverting an emergency fix in the middle of an incident is a real failure mode, and the ability to scope reconciliation by policy is precisely what makes it safe enough to use at all.

**TF11.6 — Atlantis and the PR-driven model**

Atlantis is **open source and self-hosted**: a webhook server that listens to PR events, runs `terraform plan` on the changed directories, and comments the output on the PR. Engineers then comment `atlantis apply` to apply, and Atlantis merges or unlocks.

The model: **everything happens in the PR.** Plan output, discussion, approval, and apply are all in one place, and the PR is the change record.

Its strengths: **free and self-hosted**, so no per-resource licensing (TF10.11); **simple and well-understood**; **the PR-centric workflow is genuinely good** — the plan is right next to the code review, which is exactly TF9.2; and it's mature and widely deployed.

Its limits: **you run it** — availability, upgrades, scaling, and the security of a server holding cloud credentials; **no built-in policy engine** (you bolt on Conftest); **no drift detection**; **no stack dependencies** (TF8.4) — cross-state ordering is your problem; **limited RBAC** — permissions are essentially repo permissions; and the UI is GitHub comments, which becomes unwieldy on large plans (TF9.2).

Where it fits: **a strong middle option for a team that wants better than raw CI without a commercial platform**, particularly where the estate is a manageable number of states without complex cross-state dependencies.

**TF11.7 — env0, Scalr, Digger**

At a comparison level:

- **env0** — a TFC-like SaaS platform with an emphasis on **cost management and environment lifecycle** (TTL-based auto-destroy for ephemeral environments, TF9.9), OPA policies, and self-service templates. Positioned partly on pricing being more predictable than RUM (TF10.11).
- **Scalr** — closest to a direct TFC alternative: workspaces, OPA policies, a private module registry, a hierarchical account/environment/workspace model, and pricing based on runs rather than resources — which is the pitch for organisations where RUM pricing bites.
- **Digger** — architecturally different and the most interesting to name: it **runs Terraform inside your existing CI** (GitHub Actions, GitLab CI) rather than on its own compute, providing the orchestration, locking, and PR workflow layer on top. So your credentials and compute never leave your CI, and you're not paying for someone else's runners. Open source core with a commercial tier.

The comparison point that matters: **these differ mainly in pricing model, where execution happens, and how much of the surrounding platform they provide** — not in Terraform capability, since they all run the same binary. **Digger's "use your own CI" model is the meaningful architectural distinction** in the group, because it changes the security and cost profile rather than just the price.

**TF11.8 — A decision framework**

The questions, in order:

1. **How many state files / stacks?** Under ~10: plain CI is fine. 10–50: Atlantis or a commercial platform starts paying off. Hundreds: you need a platform, and the question is which.
2. **Do you have cross-state dependencies that need ordering?** If yes, that's a strong pull toward Spacelift or TFC — building it reliably in plain CI is real engineering (TF8.4).
3. **Do you need policy enforcement, and how granular?** Basic checks: Conftest in CI. Risk-proportionate approval decided by policy: Spacelift (TF11.3). Enterprise policy with override tiers: Sentinel/TFC (TF10.6).
4. **Who needs to see and approve runs?** If non-engineers or a change board need a UI, that pushes toward a platform. If it's all engineers in PRs, Atlantis is ideal.
5. **What's the budget and what's the RUM count?** Do the TFC arithmetic explicitly (TF10.11); at scale it may exceed the cost of alternatives by a wide margin.
6. **Do you have the team to run self-hosted?** Atlantis and Digger mean you own availability.
7. **Regulatory constraints** — where can state live, where can execution happen, what audit is required? This can be decisive on its own and often rules out SaaS or forces agents/worker pools (TF10.9, TF11.2).

The shape of a good answer:

> "For a mid-size platform with 30 or 40 states, a handful of teams, and no complex cross-state ordering, I'd start with plain CI plus Conftest and OIDC — it's free, it's transparent, and the team already knows GitHub Actions. The trigger to move is when we're maintaining pipeline plumbing instead of infrastructure: cross-state ordering, drift detection, and per-risk approval are the three things I'd rather buy than build. At that point Spacelift's policy model is the strongest fit for a regulated environment, and I'd want the RUM arithmetic on TFC done properly before ruling it in or out."

**TF11.9 — What these platforms cost you in lock-in and complexity**

The lock-in, from lightest to heaviest:

- **State** — the easiest to move. State is a portable file; you can pull it from any platform and push it elsewhere (TF6.8).
- **Workflow configuration** — workspace/stack definitions, variables, triggers, and VCS connections are platform-specific and must be recreated. Painful in proportion to how many you have.
- **Policy** — **Sentinel is TFC-only** and would need rewriting in Rego to move (TF10.6). Rego-based policies are portable in principle between OPA-based platforms, less so in the details of the input document.
- **Structural dependencies** — Spacelift stack dependencies with output sharing (TF11.4) become part of your architecture. Migrating away means reintroducing `terraform_remote_state` or data sources for every link, which is a real refactor rather than a config export.
- **Organisational habit** — the deepest and least discussed. Once teams' daily workflow is the platform's UI, moving is a change-management exercise, not a technical one.

The complexity cost: another system in the deploy path with its own availability, another set of permissions to manage, another vendor relationship and renewal, and another thing to debug when a run behaves unexpectedly — is it Terraform, the provider, or the platform?

The framing: **the portable core is Terraform configuration and state; everything the platform adds on top is what you'd re-implement.** So the practical mitigation is to **keep as much logic as possible in Terraform and in your repository** — policies as Rego files in git rather than pasted into a UI, stack definitions generated from code (TF10.12, TF11.2), and dependencies expressed in ways that have a plain-Terraform fallback. That keeps the exit cost bounded.

**TF11.10 — Migrating between platforms**

The sequence:

1. **Inventory** — every workspace/stack, its state location, its variables, its VCS binding, its permissions, and its policies.
2. **Recreate the target structure as code** (TF10.12, TF11.2) rather than by hand, so it's reproducible and reviewable.
3. **Migrate state.** Pull from the source, push to the target — either via `terraform state pull/push` (TF6.8) or by reconfiguring the backend with `terraform init -migrate-state` (TF6.1). Straightforward per state; the work is in the volume.
4. **Migrate variables and secrets**, re-entering sensitive values (they're write-only in both TFC and Spacelift, so they can't be exported — this is a manual step by design).
5. **Recreate policies**, rewriting Sentinel to Rego if applicable.
6. **Run in parallel for a period.** Point the new platform at the same state in read/plan mode and compare plans against the old one. **A matching plan on both platforms is the verification** that variables and provider configuration transferred correctly — this is the step that catches the missed variable.
7. **Cut over per stack, not all at once**, starting with non-production. Disable the old platform's triggers as you go to avoid two systems applying against one state (TF3.4).
8. **Decommission** once nothing has run on the old platform for a defined period.

The hazards: **two platforms running against one state simultaneously** is the concurrency disaster (TF3.4), so trigger disablement must be part of each cutover step, not a final tidy-up. **Sensitive variables can't be exported** and must be re-sourced from the original secret store. And **run history and audit trail don't migrate**, which matters if you're required to retain it — export it before decommissioning.

---

## TF12. Troubleshooting

**TF12.1 — An unexpected forced replacement**

**The plan tells you.** Terraform annotates the specific attribute:

```
~ resource "aws_db_instance" "main" {
    ~ engine_version = "14.7" -> "15.3" # forces replacement
```

The diagnostic sequence:

1. **Find the `# forces replacement` annotation.** It names the attribute. This is the answer, and it's the step people skip before panicking.
2. **Ask why that attribute changed.** Usually one of:
   - **You changed it** — deliberately or as a side effect of a variable change.
   - **A provider upgrade changed how it's represented** (TF5.5) — a default that's now explicit, or a normalisation change.
   - **A module upgrade changed it** (TF4.3, TF4.9).
   - **`count` index shifting** — the resource at index N is now a different logical thing (TF2.4).
   - **A resource address changed** through a rename or a move, so Terraform sees destroy+create rather than the same resource (TF2.12).
   - **Drift** — someone changed it in the console and your code is reverting it (TF1.4).
3. **Decide the response:**
   - If the address changed, use a **`moved` block** (TF2.12) — the fix is almost always this for refactors.
   - If the attribute genuinely can't be updated in place and the change is wanted, plan the replacement properly: `create_before_destroy` (TF2.9), a maintenance window, data migration.
   - If it's unwanted, revert the change or add `ignore_changes` (TF2.9) if something else legitimately owns the attribute.

The habit to state: **any unexpected destroy is a stop condition, not something to reason past** (TF6.3). And `prevent_destroy` on stateful resources means this fails loudly at plan time rather than succeeding destructively (TF2.9).

**TF12.2 — A perpetual diff that never converges**

Apply succeeds, and the very next plan proposes the same change again, forever.

The causes:

- **The provider normalises the value.** You wrote a policy document with different key ordering or whitespace than AWS returns; the strings differ, the semantics don't. **Fix**: use `jsonencode()` for policy documents (TF2.7) or the dedicated `aws_iam_policy_document` data source, which produce canonical output.
- **Case or format normalisation** — an ARN, a region, an instance type that the API returns in a different case than you wrote.
- **The API returns a value you didn't set**, computed at creation. Setting it in config makes it permanently different from what the API reports.
- **Something else is changing it** — an autoscaler adjusting `desired_count`, a controller adding tags, another Terraform state managing an overlapping resource. **Two states managing the same resource is the nastiest version** and produces a diff that flips back and forth.
- **A provider bug** in how an attribute is read.

The diagnostic: **`terraform plan` shows the exact `-`/`+` values; `TF_LOG_PROVIDER=TRACE` shows what the API actually returned** (TF6.16). Comparing "what I wrote", "what state holds", and "what the API returns" identifies which of the three is the odd one out.

The fixes, in preference order: **write the value in the form the API returns** (canonical JSON, correct case); **remove it from config** if the API owns it; **`ignore_changes`** on that attribute (TF2.9) — effective but it hides real drift, so it's a last resort and should be commented with why; and **fix the ownership conflict** if two things are managing the resource, which is the only real fix for that case.

**TF12.3 — A cycle error**

```
Error: Cycle: aws_security_group.a, aws_security_group_rule.b, aws_security_group.c
```

Terraform's graph must be acyclic. A cycle means resources depend on each other directly or transitively.

The common causes:

- **Mutually-referencing security groups** — A allows ingress from B, B allows ingress from A, both defined with inline rules. **The canonical fix**: use separate `aws_security_group_rule` (or `aws_vpc_security_group_ingress_rule`) resources rather than inline `ingress` blocks, so the groups exist first and the rules reference both afterwards. Worth knowing because it's the most frequent real instance.
- **`create_before_destroy` propagation** (TF2.9) — it's contagious to dependents, and a partial application of it across a dependency chain creates a cycle. Fix by applying it consistently through the chain.
- **Over-broad `depends_on`**, especially on a module (TF2.8), creating a dependency that loops back.
- **A module's outputs depending on its own inputs** in a circular way, when two modules reference each other's outputs.

The diagnostics: **`terraform graph | dot -Tsvg`** to see the loop (TF6.12) — one of the few cases where the graph output genuinely earns its keep. Read the cycle in the error message carefully; it lists the participating nodes in order.

The structural fix: **break the cycle by introducing an intermediary or splitting the resource.** Separate rule resources, a data source instead of a direct reference, or restructuring so the dependency flows one way. If two modules reference each other, they probably want to be one module or need a third that wires them (TF4.6).

**TF12.4 — "Resource already exists" on apply**

```
Error: creating S3 Bucket (acme-reports): BucketAlreadyOwnedByYou
```

Terraform is trying to create something that already exists in the cloud but is not in state. The causes:

- **Created manually** in the console (TF1.5).
- **Created by a previous apply that failed after creation but before the state write** (TF9.8) — an orphan.
- **Removed from state** with `state rm` but left in code (TF3.9).
- **State was lost or rolled back** (TF3.12, TF10.10).
- **Another state file manages the same resource** — the worst case, because fixing it in one place breaks the other.
- **A global namespace collision** — S3 bucket names, IAM role names — where the resource genuinely belongs to someone else. Distinguish this: `BucketAlreadyExists` (someone else) versus `BucketAlreadyOwnedByYou` (you).

The resolution:

1. **Identify who owns it.** If another state manages it, stop — you have a conflict to resolve at the organisational level, not a technical fix.
2. **If it's genuinely orphaned, import it** (TF2.13, TF3.8), then plan and reconcile until clean.
3. **If it shouldn't exist, delete it manually** and re-apply — only after confirming nothing depends on it.

The prevention: **plan review** (TF9.2) catches the case where an unexpected create appears; **locking** (TF3.4) prevents the concurrent-apply version; and **removing human write access** prevents the manual version (TF1.5).

**TF12.5 — A resource deleted outside Terraform**

Terraform detects it during refresh and plans to recreate it:

```
# aws_instance.web has been deleted
# (will be recreated)
```

The decision, which is what the item is about:

1. **Establish why it was deleted.** A mistake? A deliberate decommission nobody reflected in code? Cleanup automation? An incident response action? **This determines everything that follows** and it's the step people skip.
2. **If it should exist** — apply and let Terraform recreate it. Fine for stateless resources; **for stateful ones, recreation means an empty new resource**, so the real recovery is a data restore (A11.7), and the Terraform apply is only part of it.
3. **If it shouldn't exist** — remove it from code and apply, so state and code agree with reality.
4. **If you want state to reflect reality without acting** — `terraform apply -refresh-only` (TF3.11) accepts the deletion into state, and then you decide separately.

The trap worth naming: **blindly applying to "fix" the drift can recreate a resource that was deliberately deleted**, or create a new empty database where a deleted one used to be — and if something then starts writing to it, you've created a split-brain data problem on top of the original incident. Investigating first is not bureaucracy here.

**TF12.6 — An apply that timed out with resources half-created**

A timeout is a specific case of TF9.8 with an extra ambiguity: **the operation may still be in progress on the provider's side.** Terraform gave up waiting; AWS may still be creating the RDS instance.

The approach:

1. **Do not immediately re-run.** A second apply while the first operation completes can produce duplicates or conflicting operations.
2. **Check the provider's actual state** — the console or CLI. Is the resource creating, created, or failed?
3. **Wait for the operation to settle**, then run a plan. Terraform refreshes and discovers the true state.
4. **If the resource was created but not recorded, import it** (TF12.4).
5. **If it's stuck in a bad state**, delete it manually and re-apply, or `-replace` (TF6.9).

The prevention: **provider-level timeout blocks** on resources known to be slow:

```hcl
resource "aws_rds_cluster" "main" {
  timeouts {
    create = "60m"
    delete = "60m"
  }
}
```

Default timeouts are often too short for large RDS instances, EKS clusters, and CloudFront distributions. And **CI job timeouts must be longer than the Terraform timeouts**, or the runner kills the process mid-operation, which produces the stuck lock as well (TF3.5).

**TF12.7 — Provider authentication failures across accounts**

The symptoms vary and the causes are specific:

- **`NoCredentialProviders` / `Unable to locate credentials`** — nothing in the chain provided credentials. Check the credential provider chain order (A14.3): environment variables, then shared config, then instance metadata, then the container endpoint.
- **`AccessDenied` on `sts:AssumeRole`** — the trust policy on the target role doesn't allow the caller, or the caller lacks `sts:AssumeRole` permission. **Both sides must allow it** (A1.7).
- **`ExpiredToken`** mid-apply — the session expired during a long run. **Role chaining caps at one hour** (A1.7), which is the classic cause when a pipeline assumes through a hub role.
- **Works for one provider alias and not another** — the alias's `assume_role` is wrong, or the alias isn't being passed to the module (TF5.2).
- **Works locally, fails in CI** — the local environment has credentials the runner doesn't. With OIDC, this is usually the `sub` condition on the trust policy not matching the actual workflow context (TF7.4, A2.8).

The diagnostics:

```bash
aws sts get-caller-identity                    # who am I actually (A14.3)
TF_LOG_PROVIDER=TRACE terraform plan 2>&1 | grep -i "assume\|sts\|credential"
```

`get-caller-identity` before the Terraform step in CI is a cheap and extremely effective debugging addition — it answers "is the pipeline the identity I think it is" in one line, and a surprising share of these investigations end there.

**TF12.8 — Module version or source resolution failure**

```
Error: Failed to download module
Error: Module not installed / no available releases match the constraint
```

The causes:

- **Authentication** — a private git repo or private registry needing credentials the runner doesn't have. **The single most common cause of "works locally, fails in CI"** (TF6.14): your laptop has an SSH key or a cached token; the runner doesn't. Fix with a deploy key, a token in `TF_TOKEN_<host>`, or a git `insteadOf` rewrite in the runner's config.
- **A tag or ref that doesn't exist** — a typo, or a tag deleted/moved upstream.
- **Version constraint unsatisfiable** — no published version matches, often after a constraint tightened somewhere.
- **`terraform init` not re-run** after changing a module source or version — Terraform uses the cached `.terraform/modules`. **`terraform init -upgrade`** is the fix, and forgetting it produces genuinely confusing behaviour where your change appears to have no effect.
- **Registry hostname or namespace wrong** for a private registry (TF10.7).
- **Network egress restrictions** on the runner blocking the registry or git host.

The diagnostics: `terraform init -upgrade` first; then `terraform providers` and the `.terraform/modules/modules.json` manifest to see what was actually resolved; then `TF_LOG=DEBUG` for the fetch attempt and its error.

**TF12.9 — `for_each` over an unknown-at-plan-time value**

```
Error: Invalid for_each argument
The "for_each" value depends on resource attributes that cannot be
determined until apply.
```

**Why it happens**: `for_each` keys determine **resource addresses**, and Terraform must know the full set of addresses at plan time to produce a plan. If the keys derive from an attribute that won't exist until apply — an ID of a resource being created in the same run — Terraform cannot know how many resources there will be or what they'll be called.

Note the asymmetry that confuses people: **values can be unknown at plan time; keys cannot.** `for_each = toset(var.names)` with values computed later is fine as long as the *keys* are static.

The fixes, best first:

1. **Key on something static.** Iterate over the input that *produced* the resources rather than over the resources themselves — `for_each = var.subnet_configs` keyed by name, referencing `aws_subnet.this[each.key].id` inside. **This is almost always possible and is the right answer**, and recognising it is the mark of someone who's hit this properly.
2. **Use `depends_on` plus a static key set**, so ordering is right but keys are known.
3. **Split into two applies** — create the upstream resources first, then the dependent ones. Ugly, sometimes necessary, and a signal the states may want splitting anyway (TF3.6).
4. **`-target` the upstream first** as a one-off (TF6.6) — break-glass, not a workflow.

The design lesson to state: **structure configurations so that iteration is driven by inputs, not by outputs.** When you find yourself iterating over created resources, there's usually a variable or a local you should be iterating over instead.

**TF12.10 — When state and reality have diverged badly**

The bad case: many resources missing, extra, or wrong; plans proposing large numbers of unexpected creates and destroys.

The approach:

1. **Stop all automation immediately.** Disable the pipeline. **An apply against badly-diverged state can destroy production**, and this is the first and most important action.
2. **Back up state** (`terraform state pull > backup.tfstate`) before touching anything.
3. **Establish ground truth** — what actually exists in the cloud? Console, tag-based inventory, AWS Config (A10.23), or a script (A14.4).
4. **Run `terraform plan -refresh-only`** (TF3.11) to see Terraform's view of the divergence, without proposing configuration changes. This separates "what drifted" from "what my code wants".
5. **Categorise every difference**: exists-in-reality-not-in-state (import, TF3.8), in-state-not-in-reality (accept the deletion, or recreate), in-both-but-different (reconcile the code, or apply to correct).
6. **Reconcile incrementally, smallest blast radius first**, planning after each step. Resist the urge to fix everything in one apply.
7. **Never run a broad apply until the plan is one you can fully explain**, line by line.

The escalation: **if divergence is severe enough, rebuilding state by importing everything is more reliable than repairing it** (TF3.12) — and `import` blocks with `-generate-config-out` make that far more tractable than it used to be (TF2.13).

The root-cause work afterwards matters as much as the fix: divergence at scale means something structural — no locking (TF3.4), console access nobody removed (TF1.5), two states managing the same resources, or a failed migration. **Fixing the state without fixing the cause means doing it again next quarter.**

---

## TF13. Judgement

**TF13.1 — When Terraform isn't the right tool**

- **Application deployment.** Terraform can deploy an ECS task definition or a Kubernetes manifest, but it's a poor fit for the deploy cadence — application deploys happen many times a day, need fast rollback, and want progressive delivery. That's a CD tool's job (Argo, Spinnaker, a normal pipeline). **Terraform manages the cluster; something else manages what runs on it** (K10.7).
- **In-machine configuration** — package installs, file contents, service management (TF1.7). Packer, cloud-init, or a config management tool.
- **Anything genuinely imperative** — a data migration, a one-off backfill, an operational procedure with checkpoints. These are operations, not desired states, and forcing them into Terraform produces provisioner sprawl (TF2.11).
- **Highly dynamic, short-lived resources** — anything created and destroyed many times per minute by application logic. Terraform's plan/apply cycle is the wrong granularity; that belongs in application code or a controller.
- **Rapidly-changing values** — feature flags, DNS records that change constantly, autoscaling parameters. Managing them in Terraform means a PR for every change.
- **Where a controller already reconciles it.** If Kubernetes or a cloud service is already managing something continuously, Terraform fighting it produces perpetual diffs (TF12.2).
- **Secret values** (TF7.2).

The framing: **Terraform is for infrastructure that changes on the timescale of days, not seconds, and whose desired state is meaningfully declarative.** Applying that test resolves most boundary cases.

**TF13.2 — What should and shouldn't be in Terraform**

**Should**: networks, accounts, IAM, compute infrastructure, managed data services, load balancers, DNS zones and stable records, storage, encryption keys, monitoring configuration, and — importantly — **the guardrails themselves**: SCPs, Config rules, budgets (A1.9). Anything whose configuration is a compliance control benefits enormously from being reviewed, versioned, and enforced.

**Shouldn't**: the categories in TF13.1, plus:

- **Resources managed by another controller** — Kubernetes-created load balancers, autoscaler-adjusted capacity (use `ignore_changes` where the boundary is unavoidable, TF2.9).
- **Secret values** (TF7.2).
- **Things whose lifecycle you don't own** — a partner's resources, an account you don't control.

**The genuinely hard boundary cases**, which is where the judgement is:

- **Kubernetes resources.** Terraform *can* apply manifests, but it means the Kubernetes provider needs API access at plan time (a real problem for private clusters, TF10.9), and it duplicates what GitOps does better. **The defensible line: Terraform creates the cluster and its cloud-side dependencies; GitOps manages what runs inside it** (K10.7). The exception is the bootstrap layer — the CNI, the ingress controller, the ArgoCD installation itself — which has to come from somewhere, and Terraform is a reasonable place.
- **DNS records** — zones in Terraform, yes; application records that change with every deploy, no.
- **IAM for applications** — usually yes, because it's a security control that should be reviewed.

The principle to state: **the test is "does this benefit from review, versioning, and drift detection more than it suffers from the plan/apply cycle?"** Where the answer is unclear, the follow-up question is who owns the change and how often it happens.

**TF13.3 — Justifying a state-splitting strategy for a stated organisation**

The shape of a good answer is to take a concrete context and reason from it:

> "For a fintech with a multi-account AWS org, four environments, and eight product teams, I'd split on account/region first, then by lifecycle within each. So: a foundation state per account holding networking, IAM baseline, and shared services — changed rarely, owned by the platform team, with tight apply permissions. Then a state per product team per environment for their own infrastructure, owned by them.
>
> The reasoning is blast radius and permissions: an application team's apply should be incapable of touching the VPC or the org's IAM, and that's enforced by the state boundary plus the role each pipeline assumes. The foundation state changes monthly and is reviewed by the platform team; product states change daily and are reviewed by the owning team.
>
> The cost is cross-state dependencies — product states need the VPC ID and subnet IDs. I'd handle that with data sources looking up by tag rather than `terraform_remote_state`, because that avoids giving every product pipeline read access to the foundation state, which contains IAM and secrets.
>
> What I'd watch for: if product teams routinely need foundation changes to ship, the boundary is in the wrong place and it's become a bottleneck rather than a guardrail."

The elements that make it credible: **a specific context**, **the boundary drawn on ownership and rate of change**, **the security consequence made explicit**, **the coupling cost acknowledged with a mitigation**, and **a stated failure signal**. Any answer with those five parts is a strong one, regardless of the specific split chosen.

**TF13.4 — Bringing an existing unmanaged estate under IaC**

The approach, and the sequencing is the substance:

1. **Inventory first.** What exists, who owns it, what's actually load-bearing. Tag-based reporting, AWS Config (A10.23), or a script across accounts (A14.4). **You will find resources nobody can account for** — that's normal and informative.
2. **Prioritise by risk and rate of change**, not by ease. Foundational, security-relevant, and frequently-changed resources first. A static resource nobody touches can stay unmanaged for a long time without harm.
3. **Write the code, then import** (TF2.13). Use `import` blocks with `for_each` and `-generate-config-out` for bulk work, then tidy the generated HCL.
4. **Iterate to a clean plan** for each tranche (TF3.8). **A clean plan is the acceptance criterion** — anything less means the next apply will change the resource.
5. **Only then remove console write access** for that scope. Not before, or you break people's ability to work while the code isn't ready.
6. **Repeat, tranche by tranche**, with the pipeline running plans continuously so drift is visible from the moment something is adopted.

The realities to name:

- **This takes far longer than anyone estimates**, mostly because of the reconcile-to-clean-plan step, and because every import turns up an undocumented dependency.
- **Some resources genuinely shouldn't be imported** — legacy things being decommissioned, or resources whose lifecycle belongs elsewhere. Documenting the exclusion is a valid outcome (TF13.2).
- **Do it alongside a rebuild where that's cheaper.** For a small stateless environment, recreating from clean code is faster and better than importing accumulated cruft. For anything stateful or bespoke, import.
- **The organisational half matters more than the technical half** (TF8.9) — you're changing how people work, and the migration succeeds or fails on whether the new path is faster than the old one.

This is structurally the same programme as retrofitting AWS governance (A1.15): **measure, prioritise by risk, phase it, provide a path, and agree an exception process.**

**TF13.5 — Guardrails vs developer velocity**

The tension is real and shouldn't be argued away: every control adds friction, and friction has a cost that's paid continuously while the risk it mitigates is occasional.

The framing that resolves it: **the goal is not to minimise friction or maximise control, but to make the safe path the fast path.**

What that looks like concretely:

- **Modules that make compliance automatic** (TF8.8) — a team using the standard service module gets encryption, logging, tagging, and monitoring without asking. They're compliant because it was easier, not because they were audited.
- **Risk-proportionate gates.** Auto-apply in dev, plan review in staging, approval in prod (TF9.5). Spacelift's approval policies express this precisely: gate the runs that destroy or touch IAM, let the rest flow (TF11.3).
- **Fast feedback.** A plan on every PR within two minutes is a guardrail people value; a forty-minute pipeline is one they route around (TF8.6).
- **Escape hatches with a process.** A documented emergency path (TF13.6) and a time-bounded exception process (A10.28) means the answer to an unusual need is "here's how" rather than "no", which is what keeps people inside the system.
- **Policy that explains itself.** A denial with a clear message and a link to the alternative is a guardrail; an opaque failure is an obstacle.

The diagnostic to offer: **measure how often people go around the controls.** Console changes (TF1.4), `-target` applies (TF6.6), and emergency overrides are all telemetry about whether the paved road is actually paved. Rising numbers mean the controls are mis-calibrated, not that people are undisciplined — and treating it as the former is what distinguishes a platform lead from a compliance function.

**TF13.6 — An emergency change that bypasses the pipeline**

The position to hold: **you need one, it should be designed in advance, and pretending otherwise means it happens anyway, undocumented.**

A well-designed break-glass path:

1. **A named, pre-existing role** with elevated access, not used routinely (A1.4).
2. **Access requires a deliberate act** — assuming the role explicitly, an approval from a second person where feasible, or a documented incident reference.
3. **Every use is alarmed**, not merely logged. **A break-glass login that isn't an incident is itself an incident** (A1.4). Real-time notification to a channel where someone will see it.
4. **Fully audited** — CloudTrail, who, what, when, and correlated to the incident.
5. **A mandatory reconciliation step**, with an owner and a deadline: the change must be brought back into code and the state reconciled, ideally within days. **This is the part that's always skipped**, and skipping it is how emergency changes become permanent invisible drift (TF1.4).
6. **A post-incident review** that asks not just "what broke" but **"why did the normal path not work?"** — because if the pipeline was simply too slow, that's the actual finding (TF13.5).

The alternatives to name, since bypassing entirely isn't always necessary: an **expedited pipeline path** with reduced gates for incidents (still producing a plan and a record) is better than bypassing, because it keeps the change in the system. And often the fastest safe action during an incident is not a Terraform change at all — scaling something, failing over, or disabling a feature flag.

The framing: **the goal is not to prevent emergency changes but to ensure they're visible, attributed, and temporary.** An organisation with no break-glass path doesn't have fewer emergency changes; it has the same number, made with someone's personal admin credentials, unrecorded.

**TF13.7 — The failure modes of IaC as an organisational practice**

The ways IaC fails that aren't about the tool — and this is the item where a senior answer really shows:

- **The pipeline is slower than the console, so people use the console.** The most common failure by far. IaC's value depends on it being the path of least resistance (TF13.5); when it isn't, you get the worst of both — drift plus the overhead of maintaining code that doesn't describe reality.
- **The code stops describing reality**, and once people notice, they stop trusting it, which accelerates the divergence (TF1.5). Trust is the load-bearing property and it's lost gradually then suddenly.
- **The platform team becomes a bottleneck.** Every change requires a module update only they can make, and infrastructure work queues behind them (TF4.10, TF8.8).
- **Over-abstraction** — wrapper sprawl to the point where nobody can determine what a change actually does (TF4.5).
- **Nobody reads the plan.** The single most important control (TF9.2) degrades into a formality, and approvals are rubber-stamped. Usually caused by plans that are too large, too frequent, or too noisy with irrelevant diffs.
- **Knowledge concentrates in one person.** The Terraform expert leaves and nobody can operate the estate — particularly acute with Terragrunt or a heavily-customised setup (TF8.5).
- **IaC covers only new things.** The legacy estate stays unmanaged indefinitely, so you have two operating models permanently (TF13.4).
- **Security theatre** — scanners and policies producing thousands of findings nobody triages, which is worse than nothing because it manufactures false assurance (A10.25, TF7.5).
- **The state becomes a monolith** and plans take twenty minutes, which causes `-target` habits, which cause hidden drift (TF8.3, TF8.6).

The leading indicators worth naming, because they let you catch this early: **plan duration**, **frequency of console changes and break-glass use**, **time from PR to applied**, **the proportion of the estate under management**, and **how many people can confidently apply to production**. Those five numbers tell you whether the practice is healthy far better than any compliance score.

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 137 items, reading straight through produces recognition rather than recall.
- **TF3 (state) and TF12 (troubleshooting) carry the most interview weight per item.** They're where hands-on experience is unmistakable, and where the answers can't be reconstructed from documentation under pressure.
- **TF13, TF8, and TF11.8 are the lead-role differentiators.** State-splitting for a stated organisation, bringing an unmanaged estate under control, the guardrails-versus-velocity tension, and a platform decision framework with costs attached — these are the questions where an interviewer is assessing whether you can own the platform rather than use it.
- **The failure modes are the part that reads as experience.** `count` index shifting destroying everything after the removed element (TF2.4), `-reconfigure` versus `-migrate-state` (TF6.1), applying a fresh plan after approving a different one (TF9.3), the `for_each` unknown-keys error and why keying on inputs fixes it (TF12.9), and the ephemeral environment reaper nobody built (TF9.9).
- **Cross-references into AWS are dense in TF3, TF5, and TF7** — A10.1 and A10.3 for state encryption, A2.8 for OIDC, A1.7 for cross-account role assumption and the one-hour chaining cap, and A11.9 for quotas during large applies. Interviewers move between the two domains constantly.
- **On currency**: the items where a dated answer is most obvious are `moved`/`import`/`removed` blocks replacing CLI state surgery (TF2.12, TF2.13, TF3.9), `-replace` replacing `taint` (TF6.9), S3 native locking replacing DynamoDB (TF3.3), and the OpenTofu fork (TF1.8).
