# Observability, Performance & Reliability — Answer Key

Companion to Domain 15 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **SLO philosophy, alert design, runbooks, retries and chaos are T7**; **incident method is T1–T6**; **CloudWatch specifics are A9**; **Kubernetes debugging is K9**; **database metrics are DB12**. This domain is telemetry itself, performance engineering, and reliability patterns. O8 deliberately covers alerting *mechanics* and points at T7 for the philosophy.

Three notes on how this domain is interviewed:

- **It's the broadest domain in the matrix**, spanning telemetry, Linux performance, distributed systems theory, and reliability design. Interviewers rarely test all of it — they pick the half that matches the role. For an AI platform role, O1–O8 and O16 carry most of the weight; for an SRE role, O9–O15 does.
- **O9–O12 is where a lot of candidates are weakest**, because it's systems performance rather than tooling, and it can't be learned from a vendor's documentation. The steal-time, cgroup-throttling, page-cache, and coordinated-omission items are all strong discriminators.
- **O16 is the lead-level section.** "How would you know your observability is actually working" and "when is 'just add monitoring' the wrong answer" are questions where the expected answer is a considered position, not a tool list.

---

## O1. Foundations

**O1.1 — Observability vs monitoring**

**Monitoring** is checking whether the things you predicted might break, have broken. You define the metric, the threshold, and the dashboard in advance. It answers **known unknowns**: *is the disk full? is the error rate above 1%? is the queue backing up?*

**Observability** is the property that lets you ask **new questions of a running system without shipping new code**. It answers **unknown unknowns**: *why are requests from this one customer, on this one API version, slow only on Tuesdays?* — a question nobody anticipated and for which no dashboard exists.

The distinction that matters practically: **monitoring is about predefined aggregates; observability is about retaining enough detail to slice arbitrarily after the fact.** A dashboard showing p99 latency is monitoring. Being able to break that p99 down by customer, endpoint, region, and build version — dimensions you didn't think to pre-aggregate — is observability.

Why the difference has grown: in a monolith on a handful of servers, the failure modes were enumerable, so monitoring was sufficient. In a distributed system, **the number of possible states exceeds what you can predict**, and most production incidents are novel. You cannot dashboard your way to covering them.

The caveat worth adding, because the term is heavily marketed: **observability is a property of your system, not a product you buy.** Buying a vendor's platform without instrumenting for high-cardinality, contextual data gets you monitoring with a better UI. And **monitoring is still essential** — you need the predefined alerts for the failures you *can* predict (T7.3). The two are complementary, not a progression.

**O1.2 — The three pillars, and why it's an oversimplification**

The conventional framing: **metrics** (numeric aggregates over time), **logs** (discrete records of events), **traces** (the path of a request through a distributed system).

**Why it's an oversimplification:**

- **It implies three separate systems, which is the failure mode.** Three tools, three query languages, three retention policies, and no correlation between them means an investigation involves manually copying a timestamp from a dashboard into a log search. **The value is overwhelmingly in the connections between signals** (O1.7), not in the signals themselves.
- **They're not really distinct data types.** A structured log with a duration field and a trace ID is arguably a span. A span with attributes is arguably a structured log. Metrics can be derived from either. The underlying concept is **a wide, contextual event**, and the "pillars" are three lossy projections of it — which is the argument behind the wide-events view of observability.
- **It omits signals that matter**: **profiles** (continuous profiling, O13.3), **events** (deployments, config changes, feature flag flips — often the highest-value signal in an incident and rarely in the model), **exceptions**, and **real user monitoring**.
- **It says nothing about cardinality**, which is the actual constraint that determines whether you can answer novel questions (O1.3).

The framing to offer instead: **think in terms of the questions you need to answer and the context required to answer them.** Metrics are cheap and low-cardinality, so they're for aggregate health and alerting. Traces and structured events are expensive and high-context, so they're for investigation. Choosing which signal carries a given piece of information is a cost and cardinality decision (O4.11, O16.2).

**O1.3 — Cardinality**

**Cardinality** is the number of distinct values a dimension can take. In a metrics system, **each unique combination of label values is a separate time series**, stored and indexed independently.

The multiplication is what gets people:

```
http_requests_total{method, status, endpoint, region}
  5 methods × 8 statuses × 200 endpoints × 3 regions = 24,000 series
```

Add `user_id` with a million users and it becomes 24 billion series. **The metric didn't get bigger — the label set did.**

Why it drives cost and limits:

- **Storage and memory** — Prometheus holds an index of every active series in memory; series count is the primary driver of its memory footprint and the usual cause of OOM (O3.1).
- **Query performance** degrades with series count; a query touching millions of series is slow or fails.
- **Vendor billing** is frequently per-series or per-custom-metric, so a high-cardinality label is a direct and large cost (A9.3, O16.1).
- **Ingestion** — cardinality explosions can take down the metrics backend, which is an outage of your ability to see outages.

The labels that cause it, and they're always the same ones: **user ID, request ID, trace ID, session ID, email address, full URL path with IDs embedded (`/orders/12345`), IP address, and container ID** in a high-churn environment. **Unbounded is the property that matters, not size** — a label with 500 fixed values is fine; a label that grows with your users is not.

The resolution: **high-cardinality data belongs in logs and traces, not in metric labels** (O1.2, O2.7). Normalise the path to `/orders/:id`, put the actual ID in the trace. And note the genuine tension — high cardinality is exactly what makes observability powerful (O1.1), which is why systems designed for it (Honeycomb, ClickHouse-backed platforms) handle it as a first-class concern rather than a hazard.

**O1.4 — Sampling and what it costs diagnostically**

Sampling means keeping a subset of telemetry — typically traces, sometimes logs — and discarding the rest.

Why it exists: at high volume, retaining everything is unaffordable and often unnecessary. A service handling 50,000 requests per second generates traces faster than any backend can economically store.

**What it costs diagnostically**, which is the substance:

- **You lose the specific request someone is asking about.** "Customer X's order at 14:32 failed" — if that trace was sampled out, it's gone, and you cannot get it back. This is the single most painful consequence, and it happens constantly.
- **Rare events are disproportionately lost.** A 1% sample keeps 1% of the errors too — and errors are exactly the thing you want all of. This is what tail-based sampling addresses (O5.4).
- **Aggregate accuracy degrades in the tail.** Sampled p50 is fine; sampled p99.9 on a low-volume endpoint may be based on a handful of retained spans.
- **Traces break if sampling is inconsistent** across services — one service sampling independently produces partial traces with missing spans (O5.7).

The mitigations: **tail-based sampling** (decide after seeing the whole trace — keep all errors and slow requests, sample the fast successes, O5.4); **head-based with propagated decisions** so a trace is either fully kept or fully dropped; **error and latency biasing**; and **keeping metrics unsampled** so aggregate accuracy doesn't depend on sampling at all — metrics are cheap enough to compute over 100% of requests, which is a good reason to keep them as the source of aggregate truth.

**O1.5 — White-box vs black-box monitoring**

- **White-box** — based on internals the system exposes about itself: application metrics, logs, traces, queue depths, GC statistics. **You know why**, because you can see the mechanism.
- **Black-box** — probing the system from outside as a user would: synthetic HTTP checks, an end-to-end transaction from a remote location, a TCP connect. **You know whether it works**, and nothing about why.

Why you need both:

- **Black-box catches what white-box can't see** — DNS failure, expired certificates (A8.6), a CDN misconfiguration, a load balancer with no healthy targets, a network path problem, a whole-region failure. **If your monitoring runs inside the thing that's broken, it can't tell you it's broken** — which is the fundamental argument, and it's why synthetic checks should run from outside your infrastructure.
- **White-box gives you the diagnosis and the leading indicators.** Black-box tells you the symptom after users are already affected; white-box shows the queue growing or the error rate climbing beforehand.

The practical rule: **alert on black-box for the user-facing symptom** ("the checkout journey is failing from London"), and **use white-box to diagnose and for early warning**. The classic gap is an organisation with rich white-box dashboards that all look green during an outage caused by DNS or a certificate — because nothing in the system was actually broken from its own point of view.

**O1.6 — Instrumenting for questions you haven't thought of**

The problem: **you cannot add instrumentation retroactively.** When an incident raises a question — "which tenant was affected?", "did this correlate with the deploy?", "was it one AZ?" — the answer exists only if you already recorded the data. If `tenant_id` isn't in the log line, no query recovers it, and the investigation stops there.

That asymmetry is what justifies instrumenting beyond current requirements: **the cost of recording a field you never use is small and continuous; the cost of not having it during an incident is large and concentrated at the worst moment.**

What it means in practice:

- **Attach rich context to logs and spans** — tenant, user, region, version, feature flags, request path, upstream caller. Not to metric labels, where it explodes cardinality (O1.3) — this is exactly why the signal-choice question matters.
- **Record deploy and config-change events**, because "what changed" is the first question in most incidents (T1) and is answerable only if changes are recorded as telemetry.
- **Use semantic conventions** so fields are named consistently and cross-service queries are possible (O6.6).
- **Emit the identifiers that let you join signals** (O1.7).
- **Prefer wide events over narrow ones** — one log line per request with thirty fields is far more useful and often cheaper than thirty log lines with one field each.

The counterweight, because this can be taken too far: **instrumentation has cost** — cardinality, storage, developer time, and code noise (O16.2). The judgement is to be generous with *context on events you're already emitting* and disciplined about *emitting more events*.

**O1.7 — Correlation via shared IDs and consistent labelling**

The mechanism: **a trace ID generated at the entry point, propagated through every service call (O5.2), and included in every log line and span.** Plus consistent resource labelling — `service.name`, `service.version`, `deployment.environment`, `region` — applied identically across all three signals.

Why this is where the value is:

- It turns three separate tools into one investigation. **A latency spike on a dashboard → an exemplar linking to a slow trace → the trace showing which service → that service's logs for that trace ID.** That path takes seconds; without correlation the same investigation is manual timestamp-matching across systems and takes an hour.
- **Exemplars** are the concrete mechanism on the metrics side: Prometheus histograms can carry a trace ID alongside a bucket observation, so a point on a latency graph links directly to a real trace that produced it. Under-used and genuinely valuable.
- **Consistent labels make cross-signal queries possible** — filtering logs, metrics, and traces by the same `service.name` and `version` only works if they agree on the field name and value (O6.6).

The failures to name: **inconsistent naming** (`service`, `service_name`, `app`, `application` across four teams) makes correlation impossible without a translation layer; **a service that doesn't propagate context** breaks the chain and the trace ends there (O5.7); and **logs without trace IDs** are the most common gap — the tracing is set up, the logging is set up, and nobody wired the ID into the log formatter, so the two systems remain unconnected.

**O1.8 — Build vs buy for an observability stack**

**Buy** (Datadog, New Relic, Honeycomb, Grafana Cloud, Splunk):

- No infrastructure to run, scale, or upgrade. Fast to value.
- Integrated correlation across signals out of the box (O1.7).
- **The cost is usage-based and grows super-linearly with your system**, and it is genuinely hard to predict. Observability spend reaching a significant fraction of infrastructure spend is common and is a recurring source of surprise (O16.1).
- **Lock-in** through proprietary agents and query languages — mitigated substantially by instrumenting with OpenTelemetry (O6.7).

**Build** (Prometheus, Loki/Elasticsearch, Tempo/Jaeger, Grafana):

- Cost is infrastructure plus engineering time. Much cheaper at high volume — sometimes by an order of magnitude.
- Full control over retention, cardinality, and data residency (which can be a hard regulatory requirement).
- **You now operate a distributed storage system that must be more reliable than the systems it monitors** — and that's the point people underestimate. A Prometheus that falls over under load during an incident, or a Loki cluster with its own scaling problems, is worse than useless.
- Correlation between components is your integration work.

The judgement to express:

- **Small team, moving fast, moderate volume → buy.** The engineering time to run the stack costs more than the licence, and observability is not your differentiator.
- **Large volume, cost-sensitive, platform team available → build**, or a hybrid.
- **The hybrid is often best**: self-hosted Prometheus for high-volume metrics (where the cost of a vendor is worst and the tooling is mature), a vendor for tracing and logs (where correlation and UX matter most and self-hosting is hardest).
- **Instrument with OpenTelemetry regardless** (O6.7). It makes the decision reversible, which converts a strategic commitment into a procurement one — and that's the single most valuable thing to say about this question.

---

## O2. Metrics

**O2.1 — Metric types**

- **Counter** — monotonically increasing, resets to zero on restart. Total requests, total errors, total bytes. **You query the rate, never the raw value** (O3.4).
- **Gauge** — a value that goes up and down. Current memory usage, queue depth, active connections, temperature.
- **Histogram** — observations bucketed into configurable ranges, plus a sum and count. Exposed as cumulative buckets (`_bucket{le="0.1"}`), `_sum`, and `_count`. **Aggregatable across instances** (O2.4), which is the crucial property.
- **Summary** — client-side calculated quantiles, plus sum and count. Cheaper to query, **and quantiles cannot be aggregated across instances**, which is the fatal limitation.

The distinction that matters most: **histogram vs summary.** A summary computes p99 on each instance; you cannot combine ten instances' p99s into a fleet p99 (O2.4). A histogram ships bucket counts, which *are* additive, so the fleet-wide quantile can be computed at query time (O3.7). **Use histograms almost always**; summaries only when you need precision on a single instance and never aggregate.

Also worth naming: **OpenTelemetry adds exponential (native) histograms**, which use automatically-scaled buckets rather than fixed ones — removing the bucket-selection problem in O2.5. Prometheus supports them too. That's a genuine improvement and a good currency signal.

**O2.2 — Choosing the right type**

Work from what you'll query:

| Measurement | Type | Why |
|---|---|---|
| Requests served | Counter | You want rate over time |
| Errors | Counter | Rate, and ratio against total (O3.8) |
| Request duration | Histogram | You need percentiles, aggregated across instances |
| Queue depth | Gauge | Goes up and down; current value is meaningful |
| Active connections | Gauge | Same |
| Memory in use | Gauge | Same |
| Bytes transferred | Counter | Rate |
| Payload size | Histogram | Distribution matters, not just total |
| Cache hit ratio | **Two counters** | Hits and misses separately, ratio at query time |
| Build/version info | Gauge set to 1 with labels | The `_info` pattern |

The mistakes worth flagging:

- **Exposing a pre-computed ratio as a gauge** (cache hit rate as a single number). You cannot aggregate it correctly across instances or re-window it — a 5-minute ratio can't be turned into a 1-hour ratio. **Export the numerator and denominator as counters** and divide at query time. This is the most common metric-design error.
- **A gauge where a counter belongs** — "errors in the last minute" as a gauge loses information on scrape gaps and can't be rated properly.
- **A counter that resets** because it's re-derived rather than accumulated — `rate()` handles genuine restarts but not arbitrary decreases.

**O2.3 — Why averages hide the problem**

An average is a single number that describes a distribution only if the distribution is roughly normal — and **latency distributions never are.** They're heavily right-skewed with a long tail.

The concrete demonstration: 1,000 requests, 990 at 10ms and 10 at 5 seconds. **The mean is 60ms — which looks excellent, and ten users just waited five seconds.** The average is not merely imprecise; it is actively misleading, because the users experiencing the problem are exactly the ones the average erases.

What percentiles give: **p50** is the typical experience; **p95/p99** is what a meaningful minority experience; **p99.9** is your worst-case behaviour under load. **The percentile you should care about depends on request volume per user** — if a page makes 20 backend calls, p99 per call means roughly 1 in 5 page loads hits it (O12.4).

The related points: **percentiles are computed over a window**, so a p99 over 24 hours hides a bad ten minutes — window choice matters. **A histogram is what lets you compute percentiles at all after the fact** (O2.1). And **the best view is the full distribution** — a heatmap (O7.5) shows bimodality that no percentile reveals, which is how you spot "there are two populations of request here", such as cache hits and misses.

**O2.4 — Why you can't average percentiles**

**Percentiles are not linear, so the average of percentiles is not the percentile of the whole.**

The intuition: instance A serves 1 request/second with a p99 of 10ms. Instance B serves 10,000 requests/second with a p99 of 900ms. Averaging gives 455ms — a number that describes neither instance and no user's experience. The fleet's true p99 is dominated by B, because B serves virtually all the traffic.

Even with equal traffic it's wrong: p99 is a boundary in each instance's distribution, and combining two distributions requires combining the underlying observations, not their boundaries.

**The correct approach**: export **histogram buckets** from each instance, sum the buckets across instances, then compute the quantile from the combined histogram:

```promql
histogram_quantile(0.99,
  sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
)
```

Note `sum by (le)` — summing bucket counts, which is valid because counts are additive — *then* `histogram_quantile`. Doing it the other way round (`avg(histogram_quantile(...))`) is the error.

This is precisely why **summaries are the wrong choice for anything multi-instance** (O2.1): they give you pre-computed quantiles that cannot be legitimately combined. Any dashboard averaging a summary's quantile across pods is showing a fabricated number, and this is common enough to be worth checking for.

**O2.5 — Histogram buckets and the cost of getting them wrong**

Buckets are the boundaries at which observations are counted. `histogram_quantile` **interpolates linearly within the bucket containing the target quantile** (O3.7), so accuracy depends entirely on bucket placement.

**Too few or badly placed buckets**: if your p99 falls in a bucket spanning 1s to 10s, the reported p99 is a linear interpolation across a 9-second range — essentially fiction. The classic symptom is a p99 that reports a suspiciously round number, or that snaps between values as traffic shifts.

**Too many buckets**: every bucket is a time series per label combination, so buckets multiply cardinality (O1.3). A histogram with 20 buckets and 100 label combinations is 2,000 series before you count `_sum` and `_count`.

**Buckets that don't cover the range**: observations above the highest bucket land only in `+Inf`, so **any quantile above that boundary is unbounded and `histogram_quantile` returns the last finite boundary or `+Inf`** — you literally cannot measure your tail.

Getting it right: **place buckets around your SLO threshold and your actual distribution.** If the SLO is 300ms, you want buckets tightly spaced around 300ms so you can measure compliance precisely. Prometheus's default buckets (0.005 to 10s) suit a general web service and are wrong for anything unusual — a service with sub-millisecond latencies gets everything in the first bucket and no resolution at all.

**The cost of getting it wrong is that you cannot change it retroactively.** Recomputing yesterday's p99 with better buckets is impossible; the data was aggregated at collection time. That irreversibility is the point of the item — and it's the strongest argument for **native/exponential histograms** (O2.1), which adapt their buckets automatically and largely eliminate this class of problem.

**O2.6 — Push vs pull**

- **Pull (Prometheus)** — the monitoring system scrapes targets over HTTP on a schedule.
- **Push (StatsD, Graphite, OTLP, CloudWatch)** — the application sends metrics to a collector.

**Pull's advantages**: **the scrape itself is a health check** — a target that can't be scraped is visibly down, which is information you get for free. **Service discovery drives targets** (O3.1), so the monitoring system knows what *should* exist, and a missing target is detectable. It's easy to run a second Prometheus for HA or to scrape a target manually with curl for debugging. And **the monitoring system controls the rate**, so a misbehaving application can't flood it.

**Pull's problems**: **short-lived jobs** may not exist long enough to be scraped (hence the pushgateway, O3.13). **Network topology** must allow the scraper to reach every target, which is awkward across NAT, firewalls, or into customer environments. And it doesn't suit client-side or serverless workloads where nothing is listening.

**Push's advantages**: works for ephemeral and serverless workloads; works through NAT; the client controls timing, so it fits batch jobs.

**Push's problems**: **a silent client is indistinguishable from a client with nothing to report** — you lose the free liveness signal, and this is the significant one. It also allows clients to overwhelm the collector, and it requires every client to know the endpoint and hold credentials.

The practical resolution: **pull where you can, push where you must**, and note that **OpenTelemetry's collector blurs the line usefully** — applications push to a local collector (solving the ephemeral and topology problems), and the collector can be scraped or can push onward (O6.5). That architecture gets most of both sets of advantages and is the modern default.

**O2.7 — Designing labels**

Good labels are **bounded, meaningful for aggregation, and stable**:

```
http_requests_total{service, method, status_code, endpoint, environment}
```

The design rules:

- **Every label must have bounded cardinality** — a fixed or slowly-growing set of values (O1.3).
- **Normalise paths**: `/orders/:id`, never `/orders/12345`. An unnormalised path label is one of the most common cardinality explosions, and it looks innocuous.
- **Group status codes** where the detail isn't needed — `2xx`, `4xx`, `5xx`, or the code itself if it's a bounded set.
- **Never**: user ID, request ID, trace ID, session ID, email, IP, full URL, timestamp, container ID in a high-churn cluster, error message text (unbounded free text is the worst offender).
- **Ask "will I aggregate or filter by this?"** If not, it's not a label — it's context, and it belongs on a log or span.
- **Consistent names across services** (O1.7, O6.6) — `service`, not `service` in one place and `app` in another.

The practical guardrails: **set a cardinality limit** in your collector or backend so an explosion is capped rather than fatal; **monitor series count growth** and alert on it (a sudden jump is usually a new label deployed); and **know your top-cardinality metrics** — `topk(10, count by (__name__)({__name__=~".+"}))` is the query to have.

The escalation path when someone needs high-cardinality analysis: **that's what traces and structured events are for** (O1.2). "You can't put customer ID in a metric label, but you can put it on the span and query traces by it" is the correct, helpful answer rather than a flat no.

**O2.8 — Aggregation, downsampling, and retention tiers**

Raw high-resolution metrics are expensive to store indefinitely, and nobody queries last year's data at 15-second resolution.

- **Aggregation** — pre-computing a coarser view: summing per-pod series into a per-service series (recording rules, O3.9). Reduces series count and query cost.
- **Downsampling** — reducing temporal resolution over time: 15s raw, 5m after a week, 1h after a month. Thanos, Mimir, and Cortex do this automatically.
- **Retention tiers** — how long each resolution is kept.

A typical policy:

| Age | Resolution | Purpose |
|---|---|---|
| 0–15 days | 15s raw | Incident investigation |
| 15–90 days | 5m | Trend analysis, post-incident review |
| 90 days–2 years | 1h | Capacity planning (O14.1), seasonality |

The judgement to state: **retention should be driven by the questions you'll ask.** Incident debugging needs high resolution and a short window. Capacity forecasting needs a long window and doesn't care about 15-second detail. Compliance may mandate a specific period. Storing everything at full resolution forever is the expensive default nobody chose deliberately (O16.1).

The caveats: **downsampling loses spikes** — a one-minute outage may vanish entirely in hourly data, so post-incident analysis beyond your raw window is limited. **Downsampled quantiles are approximations of approximations.** And **aggregation destroys the dimension you aggregated away**, so a recording rule that sums across pods means you can never again ask "was it one pod?" for that period — which is precisely the question you'll want (O1.6).

**O2.9 — The RED method**

For **request-driven services**:

- **Rate** — requests per second.
- **Errors** — failed requests per second (and as a ratio).
- **Duration** — the distribution of request latency.

```promql
sum(rate(http_requests_total{service="api"}[5m]))                                    # Rate
sum(rate(http_requests_total{service="api",status=~"5.."}[5m]))
  / sum(rate(http_requests_total{service="api"}[5m]))                                # Errors
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m]))) # Duration
```

Its value: **three metrics that apply to every request-driven service, so a dashboard template works for all of them** (O7.3). It's the basis of a consistent service dashboard across an organisation, which is worth more than each team designing their own.

The refinements: **break down by endpoint**, because a healthy aggregate hides one broken endpoint. **Errors must be defined deliberately** — a 404 is usually not a service error, a 429 might be either, and counting them wrongly makes the error rate meaningless. And **RED describes the service's own view**; a service can report low errors while returning wrong answers, so it complements rather than replaces black-box checks (O1.5).

**O2.10 — The USE method**

For **resources** (CPU, memory, disk, network, and any bounded pool):

- **Utilisation** — the fraction of time the resource was busy.
- **Saturation** — the degree of queued work the resource couldn't service. Run queue length, queue depth, swap activity.
- **Errors** — error events for the resource.

**Saturation is the part people omit, and it's the most predictive.** Utilisation has a ceiling of 100%, so it tells you nothing about how far past capacity you are — a CPU at 100% with a run queue of 2 and one with a run queue of 200 look identical on a utilisation graph and are completely different situations (O9.2, O12.1).

Applied:

| Resource | Utilisation | Saturation | Errors |
|---|---|---|---|
| CPU | % non-idle | Run queue length, cgroup throttling (O9.4) | — |
| Memory | Used / total | Swap activity, page scan rate, OOM kills | OOM events |
| Disk | % time busy | Average queue depth (O11.2) | I/O errors |
| Network | Bandwidth used | Drops, retransmits, queue overflows | Errors, discards |
| Connection pool | Active / max | Threads waiting for a connection | Acquisition timeouts |

The framing to give: **RED for services, USE for resources**, and the two answer different questions — RED tells you users are affected, USE tells you which resource is why. That pairing is the practical value of knowing both.

**O2.11 — The four golden signals and how they map**

From the Google SRE book: **latency, traffic, errors, saturation.**

The mapping:

- **Latency = RED's Duration.** With the important refinement that **latency of successful and failed requests must be separated** — fast failures can drag the overall distribution down and make a service look fine while it's erroring, which is a genuinely misleading artefact.
- **Traffic = RED's Rate.**
- **Errors = RED's Errors.**
- **Saturation = USE's Saturation** — the one RED lacks.

So **golden signals ≈ RED + saturation**, which is the useful thing to say: golden signals bridge the service-level and resource-level views, and the addition of saturation is what gives you the leading indicator. Latency, traffic, and errors tell you something is wrong *now*; saturation tells you it's about to be (O12.1).

Which to alert on: **latency, errors, and traffic anomalies are symptom-based and page-worthy** (T7.3). **Saturation is generally a warning, not a page** — high saturation without user impact is a capacity conversation, not an incident. That distinction is what stops a saturation alert becoming noise.

---

## O3. Prometheus & query languages

**O3.1 — Prometheus architecture**

The components:

- **The server** — scrapes targets, stores samples in a local TSDB, evaluates rules, serves PromQL.
- **Service discovery** — dynamically finds targets (Kubernetes API, EC2, Consul, DNS, file-based). This is what makes pull viable in a dynamic environment (O2.6): Prometheus asks the orchestrator what exists rather than being told.
- **The TSDB** — samples in 2-hour blocks, compacted over time, with a write-ahead log for crash recovery. **An in-memory index of all active series**, which is why series count drives memory (O1.3).
- **Alertmanager** — a separate process handling routing, grouping, deduplication, and silencing (O8.3). Prometheus evaluates rules and fires; Alertmanager decides what to do about it.
- **Exporters** — translate a system's native metrics into the Prometheus format (O3.12).

The properties that follow and shape how you use it:

- **A single Prometheus server is a single node.** It doesn't cluster. Scaling means sharding by target set or moving to Thanos/Mimir/Cortex (O3.11).
- **Local storage is not durable long-term** — designed for weeks, not years. Long-term retention needs remote write (O3.11).
- **It's a pull-based, sample-at-interval system**, so it sees a snapshot every `scrape_interval`. Events between scrapes are invisible unless they're recorded in a counter — which is a fundamental reason counters beat gauges for anything event-like (O2.2).
- **Scrape interval bounds your resolution and your alerting latency** (O8.1).

**O3.2 — Scrape targets and relabelling**

```yaml
scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # only scrape pods with the annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: "true"
      # use the annotated port
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      # promote namespace and pod to real labels
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
```

The concepts:

- **`relabel_configs` runs before the scrape** — it selects targets and rewrites the labels used to scrape them. `keep`/`drop` here is how you control *what gets scraped at all*.
- **`metric_relabel_configs` runs after the scrape**, on the returned metrics. **This is your cardinality control** — dropping expensive metrics or labels before ingestion (O1.3, O2.7):

```yaml
metric_relabel_configs:
  - source_labels: [__name__]
    regex: 'go_gc_duration_seconds.*'
    action: drop
```

- **Meta labels (`__meta_*`) are discarded unless you promote them**, which is why you explicitly map namespace and pod into real labels.
- **Labels starting with `__` are dropped** after relabelling.

The practical point: **relabelling is the main cost-control lever in a Prometheus setup** (O16.1). A verbose exporter can be trimmed at ingestion rather than at the source, and knowing that `metric_relabel_configs` is where you do it is the useful takeaway.

**O3.3 — PromQL: selectors, matchers, range vectors**

```promql
http_requests_total                                    # instant vector: latest sample per series
http_requests_total{job="api", status=~"5.."}          # with matchers
http_requests_total{status!="200"}                     # negative match
http_requests_total[5m]                                # range vector: all samples in 5m
rate(http_requests_total[5m])                          # range vector → instant vector
http_requests_total offset 1h                          # value an hour ago
```

Matchers: `=` exact, `!=` not equal, `=~` regex match, `!~` regex not match. Regexes are fully anchored, so `status=~"5.."` matches exactly three characters.

**The instant/range distinction is the core concept and the source of most PromQL errors:**

- An **instant vector** is one sample per series at a point in time. Most functions and all binary operations work on these.
- A **range vector** is a set of samples over a window. **You cannot graph a range vector directly** — the error "expected type instant vector but got range vector" means you selected a range and didn't apply a function that collapses it (`rate`, `increase`, `avg_over_time`, `max_over_time`).
- Conversely, `rate(http_requests_total)` fails because `rate` requires a range.

The other essentials: **`_over_time` functions** (`avg_over_time`, `max_over_time`, `quantile_over_time`) aggregate a single series across time, whereas `avg`/`max` aggregate across series at a point in time — a distinction people conflate constantly. And **subqueries** (`max_over_time(rate(x[5m])[1h:])`) for computing a function over a derived series.

**O3.4 — `rate` vs `irate`**

- **`rate(counter[5m])`** — the per-second average rate of increase over the window, calculated across all samples in it. Smooth, and it's what you want almost always.
- **`irate(counter[5m])`** — the instantaneous rate, using **only the last two samples** in the window. Very responsive, very spiky.

The practical guidance:

- **`rate` for alerting and for most graphs.** Averaging over the window damps noise, and alerting on a spiky signal produces flapping (O8.2).
- **`irate` only for high-resolution graphs of fast-moving counters**, where you want to see brief spikes and are prepared for the noise. **Never for alerting.**
- **`irate` with a long range is misleading** — it still uses the last two samples, so `irate(x[1h])` isn't "the rate over an hour"; it's the instantaneous rate, with an hour's tolerance for finding two samples.

The rule that catches people: **the range must cover at least two scrape intervals, and in practice four is the recommendation** — `rate(x[1m])` with a 30-second scrape interval has only two samples and produces gaps or nothing whenever a scrape is missed. **A range of at least 4× the scrape interval** is the guidance, and "my rate query returns no data intermittently" is almost always this.

Both handle **counter resets correctly** — a drop to zero is interpreted as a restart, not a negative rate, which is the whole reason counters are safe across process restarts.

**O3.5 — Why `rate` on a gauge is wrong**

`rate` assumes a **monotonically increasing counter**. When it sees a decrease, it interprets it as a counter reset and **adds the pre-reset value back in** to compensate.

Applied to a gauge — which legitimately goes down — every decrease is treated as a reset, and the function fabricates increases that never happened. **The result is not merely noisy, it's numerically wrong**, and it produces plausible-looking output that nobody notices is nonsense.

What to use instead, depending on the question:

- **The rate of change of a gauge** → `deriv(gauge[5m])` (least-squares derivative) or `delta(gauge[5m])` (difference between first and last, which does *not* correct for resets).
- **How much it changed** → `delta()`.
- **A smoothed value** → `avg_over_time(gauge[5m])`.
- **Predicting when it hits a threshold** → `predict_linear(node_filesystem_avail_bytes[6h], 4*3600) < 0` — the standard disk-full-in-4-hours alert, and a good example of a genuinely useful gauge function.

The related error in the other direction: **using `delta` or `deriv` on a counter** misses resets and undercounts.

The check to apply: **if the metric name ends in `_total` or `_count`, it's a counter (use `rate`/`increase`); otherwise assume a gauge.** The naming convention exists precisely to make this decidable.

**O3.6 — Aggregating with `sum by` and `without`**

```promql
sum by (service, status) (rate(http_requests_total[5m]))     # keep only these labels
sum without (instance, pod) (rate(http_requests_total[5m]))  # keep all except these
```

- **`by`** — an allow-list: the result has only the listed labels. Explicit, and it breaks when a new label is needed.
- **`without`** — a deny-list: keeps everything except the listed labels. Better when you want to preserve labels you haven't enumerated, and it's the more robust choice for generic rules because a newly-added label survives.

Aggregation operators: `sum`, `min`, `max`, `avg`, `count`, `stddev`, `quantile`, `topk`, `bottomk`, `count_values`.

The points that matter:

- **`sum` is valid for counters and rates; `avg` usually isn't what you want** — averaging rates across pods gives the per-pod average, not the total, and people frequently want the latter.
- **Never average percentiles across instances** (O2.4) — aggregate the buckets, then compute the quantile.
- **`topk` is for investigation, not alerting** — it returns different series each evaluation, which makes alert state meaningless.
- **Aggregating away a label discards it permanently** for that query, so a recording rule that sums across pods means "was it one pod?" becomes unanswerable from that series (O2.8).

**O3.7 — `histogram_quantile` and its approximation**

```promql
histogram_quantile(0.99,
  sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
)
```

The mechanics, and the order is essential: **`rate()` the buckets** (they're counters), **`sum by (le)`** across instances (valid because bucket counts are additive), **then `histogram_quantile`**. Getting this order wrong is the most common PromQL error in this area (O2.4).

**The approximation** — this is what the item is asking about:

`histogram_quantile` finds the bucket containing the target quantile and **interpolates linearly within it**, assuming observations are uniformly distributed across the bucket. They aren't — within a bucket, latency observations cluster toward the lower bound.

The consequences:

- **Accuracy depends entirely on bucket width around the quantile** (O2.5). If p99 falls in a bucket spanning 1s–10s, the answer is a guess across a 9-second range.
- **The result can never exceed the highest finite bucket boundary.** If everything above 10s lands in `+Inf`, a p99 above 10s reports as 10s (or `+Inf`), so **you cannot measure a tail that exceeds your buckets** — and the graph looks like a flat line at your top boundary, which is the recognisable signature.
- **Percentiles of low-volume series are unreliable** — a p99 over 20 requests is one observation.
- **`+Inf` bucket must be present** or the calculation is invalid.

The framing: **it's an estimate whose error you control through bucket design**, and reporting it as an exact figure is over-claiming. **Native/exponential histograms** (O2.1) largely remove the problem by adapting bucket boundaries automatically.

**O3.8 — Ratio queries for error rate and availability**

```promql
# error ratio
sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m]))

# availability (success ratio)
sum(rate(http_requests_total{status!~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))

# per-service, preserving the label
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
  / sum by (service) (rate(http_requests_total[5m]))
```

The rules that make this correct:

- **Rate both sides over the same window**, then divide. Dividing raw counters gives you a lifetime ratio, not a current one.
- **The label sets must match for the division to work.** Prometheus matches series by label; if the numerator has a `status` label and the denominator doesn't, you get no result. **`sum` both sides down to the same label set** — this is the number one reason a ratio query returns empty.
- **Guard against divide-by-zero**: with no traffic, the denominator is zero and the result is `NaN`. Either accept it (an alert won't fire on `NaN`, which is usually the desired behaviour) or add `or vector(0)`. Being aware that no traffic produces no alert is important — it means a total outage where requests stop entirely doesn't trigger an error-ratio alert, which is a real gap and an argument for also alerting on traffic disappearing.
- **Define "error" deliberately** (O2.9) — 5xx yes, 4xx usually no, 429 debatable.

This form is the basis of SLI measurement and burn-rate alerting (O8.4).

**O3.9 — Recording rules**

```yaml
groups:
  - name: api_slis
    interval: 30s
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))
      - record: job:http_errors:ratio_rate5m
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
            / sum by (job) (rate(http_requests_total[5m]))
```

Recording rules pre-compute expressions on a schedule and store the result as a new series.

**When they're needed:**

- **Expensive queries used repeatedly** — a dashboard panel aggregating across thousands of series, refreshed by twenty people, recomputed every time.
- **Queries over long ranges** — a 30-day quantile is very expensive to compute ad hoc; precomputing shorter windows and combining them is far cheaper.
- **Alerting rules that would otherwise be slow**, since a slow rule delays evaluation and therefore alerting.
- **SLO burn-rate calculations** (O8.4), where you need the same ratio over several windows and computing all of them ad hoc is heavy.
- **Cardinality reduction** — aggregating per-pod series to per-service, then retaining the aggregate for longer (O2.8).

The conventions: **name them `level:metric:operation`** (`job:http_requests:rate5m`) so it's obvious the series is derived and at what aggregation level. **The rule's `interval` bounds the resolution** of the recorded series. And **recording rules only apply going forward** — they don't backfill, so a new rule has no history, which matters when you need it during an incident and it was created that morning.

**O3.10 — Staleness and gaps**

**Staleness**: when a series stops being reported — a target disappears, a label combination stops appearing — Prometheus marks it **stale** and it disappears from query results after roughly 5 minutes (the staleness delta). It doesn't linger as a flat line forever.

**Why this matters:**

- **A disappeared series doesn't evaluate to zero — it evaluates to nothing.** An alert like `rate(errors[5m]) > 0` simply stops firing when the target vanishes entirely, because there's no data. **The absence of a signal is not a zero**, and this is the single most important consequence.
- That's what **`absent()`** and **`absent_over_time()`** are for: alerting on a metric that *should* exist and doesn't. **`up == 0`** is the corresponding target-level check.
- **Gaps in scraped data** — a failed scrape, a restart, a network blip — produce holes. `rate()` handles small gaps if the range covers enough samples (O3.4), which is why the 4× rule matters.
- **Graphs show gaps rather than interpolating**, which is honest and occasionally alarming.

The practical rule for alerting: **always pair a threshold alert with a presence check.** "Error rate > 1%" plus "the metric exists" — otherwise a total failure that stops the exporter looks identical to perfect health. That's a genuinely common gap and a good thing to volunteer.

**O3.11 — HA, federation, long-term storage**

**HA**: run **two identical Prometheus servers** scraping the same targets. They're independent, so their data differs slightly (scrape timing), which is why deduplication is needed at query time. Alertmanager deduplicates alerts from both (O8.3) — this is the standard, simple approach, and it gives redundancy without clustering.

**Federation**: a Prometheus scrapes aggregated metrics from other Prometheus servers via `/federate`. Historically used for hierarchical setups. **Now largely superseded** — it's fragile at scale, only carries aggregates, and creates a bottleneck. Worth knowing but not recommending.

**Long-term storage and horizontal scale** — the real answers:

- **Thanos** — a sidecar ships TSDB blocks to object storage; a querier fans out across sidecars and store gateways with deduplication; a compactor downsamples. Retains the Prometheus-per-cluster model and adds a global query layer.
- **Mimir** (formerly Cortex) — a horizontally scalable, multi-tenant TSDB. Prometheus **remote-writes** into it; Mimir owns storage and querying. Better for very large multi-tenant estates.
- **VictoriaMetrics** — a simpler, resource-efficient alternative, often chosen for lower operational cost.
- **Managed** — Amazon Managed Prometheus, Grafana Cloud, which is the buy side of O1.8.

The decision framing: **Thanos if you want to keep Prometheus as the primary and add global query plus long retention; Mimir if you want a proper multi-tenant central store and are prepared to run it.** And **remote write is the interface** either way, which means the choice is comparatively reversible.

**O3.12 — Exporters**

An exporter is a process that reads a system's native metrics and exposes them in Prometheus format on `/metrics`.

Common ones: **node_exporter** (host CPU, memory, disk, network — the basis of USE for hosts, O2.10), **cAdvisor/kubelet** (container metrics), **kube-state-metrics** (Kubernetes object state — desired vs available replicas, pod phase, K9.13), **blackbox_exporter** (synthetic probes, O1.5), and database, message-broker, and cloud exporters.

Writing one is straightforward:

```python
from prometheus_client import Counter, Histogram, start_http_server

REQUESTS = Counter("app_requests_total", "Total requests", ["method", "status"])
LATENCY  = Histogram("app_request_duration_seconds", "Request duration",
                     ["endpoint"], buckets=[.01, .05, .1, .25, .5, 1, 2.5, 5])

REQUESTS.labels(method="GET", status="200").inc()
with LATENCY.labels(endpoint="/orders").time():
    handle_request()

start_http_server(9090)
```

The conventions that matter: **`_total` suffix on counters, base units** (seconds not milliseconds, bytes not megabytes — Prometheus convention is strict about this and mixing units across services is a real annoyance), **`_seconds`/`_bytes` suffixes**, and **help text on every metric.**

The design points: **exporters should be stateless and compute at scrape time**, not maintain their own scheduling; **a slow exporter causes scrape timeouts** and gaps (O3.10), so an exporter that queries a database on every scrape needs caching; and **third-party exporters vary enormously in cardinality discipline** — check what a new exporter adds before deploying it fleet-wide (O3.2 for trimming it).

**O3.13 — The pushgateway and why it's usually wrong**

The pushgateway accepts pushed metrics and holds them for Prometheus to scrape. It exists for **short-lived batch jobs** that finish before any scrape could reach them (O2.6).

**Why it's usually the wrong answer:**

- **Metrics persist forever until explicitly deleted.** The gateway is not a proxy — it holds the last pushed value indefinitely. A job that ran once six months ago is still reporting its final metrics, indistinguishable from a job that just ran. **This is the killer problem**, and it means stale data silently pollutes queries.
- **It becomes a single point of failure** and a bottleneck for everything pushing to it.
- **You lose the `up` signal** — the gateway is up, so Prometheus is happy, regardless of whether the job ran at all. **A job that stopped running entirely is invisible**, which is usually the failure you most wanted to detect.
- **Timestamps are of the scrape, not the job**, so the timing information is misleading.
- **People use it as a general push endpoint** for services that could be scraped, which multiplies all of the above.

The alternatives, in preference order: **make the job long-lived enough to scrape**, or expose metrics from the scheduler rather than the job; **have the job write to a textfile that node_exporter collects** (the textfile collector — much better for host-local batch jobs); **push to an OTel collector** which handles lifecycle properly (O6.5); or **for Kubernetes CronJobs, use kube-state-metrics** for job success/failure, which gives you the "did it run" signal the pushgateway can't.

**Legitimate use**: a genuine batch job whose *result* you want recorded (records processed, last success timestamp), where you understand the persistence semantics and delete the group when the job is retired. And even then, alert on **`time() - last_success_timestamp`** rather than on the job's absence, because the gateway can't tell you about absence.

---

## O4. Logging

**O4.1 — Structured logging**

```json
{"timestamp":"2026-08-20T14:32:11.482Z","level":"error","service":"payments-api",
 "trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7",
 "tenant_id":"acme-ltd","endpoint":"/v1/charges","http_status":502,
 "duration_ms":4821,"upstream":"card-processor","error":"upstream timeout",
 "message":"Charge failed due to upstream timeout"}
```

versus:

```
2026-08-20 14:32:11 ERROR Charge failed due to upstream timeout after 4821ms for acme-ltd
```

Why structured wins:

- **Fields are queryable without regex.** `level:error AND tenant_id:"acme-ltd" AND duration_ms > 3000` is a query; extracting that from free text requires a parser that breaks the moment someone changes the message.
- **Aggregation becomes possible** — count by `upstream`, percentile of `duration_ms`, group by `tenant_id`. Free text can't be aggregated meaningfully.
- **Correlation works** because `trace_id` is a field (O1.7, O4.3).
- **Parsing happens once, at write time, correctly** — rather than repeatedly, at query time, fragilely (O4.4).
- **Schema evolution is safe** — adding a field breaks nothing, whereas changing a log message breaks every regex that parsed it.

The practicalities: **keep a human-readable `message` field** as well, because during an incident people read logs with their eyes. **Use consistent field names across services** (O6.6) or cross-service queries fail. **Emit JSON in production and pretty-printed text locally**, which most logging libraries support with a config switch. And **structured logging is the prerequisite for O4.11's question** — once fields are structured, it becomes obvious which ones should have been metrics.

**O4.2 — Log levels**

- **ERROR** — something failed that requires attention. A request couldn't be served, a dependency is unreachable after retries, data is inconsistent. **Should be rare enough that a human could plausibly read them all.**
- **WARN** — something unexpected that the system handled. A retry succeeded, a fallback was used, deprecated input was accepted, a config value was defaulted. **Potentially a problem if the rate rises.**
- **INFO** — significant business or lifecycle events. Service started, config loaded, a request completed (if you log request completion), a scheduled job ran. **The default production level.**
- **DEBUG** — detail for diagnosis. Intermediate values, branch decisions, external call payloads. **Off in production by default.**
- **TRACE** — extremely verbose; individual operations. Almost never on.

The judgement points:

- **The most common failure is level inflation** — everything logged at ERROR because it felt important, until ERROR is high-volume and nobody reads it. **If your ERROR log has thousands of entries a day, the level has stopped meaning anything**, and any alert built on it is noise.
- **The second most common is WARN as a dumping ground** for things nobody decided about.
- **An expected condition is not an error.** A 404 for a resource that doesn't exist, a validation failure on user input, a rate-limited client — these are INFO or WARN at most. Logging them as ERROR is how you get an unusable error log.
- **Make levels runtime-adjustable** — the ability to turn on DEBUG for one service during an incident without a redeploy is disproportionately valuable, and per-logger granularity more so.
- **Debug logging left on in production is a top cost driver** (O4.7).

**O4.3 — Correlation and trace IDs in every log line**

The requirement: **every log line emitted while handling a request carries the trace ID** (and ideally span ID), so logs and traces are joinable (O1.7).

The mechanism: the tracing SDK puts the current context in thread-local or async-local storage; the logging framework reads it via an MDC (Java), a context processor (Python's structlog), or a middleware. **OpenTelemetry's logging integrations do this automatically** in most languages, and configuring it is a one-off task per service.

Why it's the highest-value single logging practice:

- **It's what makes a distributed investigation tractable.** A slow trace shows *which* service; the trace ID pulls that service's logs for exactly that request, out of millions.
- **It works backwards too** — an error log gives a trace ID that shows the whole request path and what led to it.
- **It survives sampling asymmetry** — logs are typically unsampled while traces are (O1.4), so an error log can point at a trace that wasn't kept, which is at least a signal to adjust sampling.

The related IDs worth propagating: a **correlation/request ID** at the edge (useful when the caller is external and you want an ID to give a customer), **tenant ID**, **user ID**, and **session ID** — all as log fields, none as metric labels (O2.7).

The failure to name: **the tracing is instrumented, the logging is structured, and nobody wired the ID into the log formatter.** Two working systems with no connection between them, which is extremely common and cheap to fix.

**O4.4 — The pipeline: emit, collect, ship, parse, index, retain**

1. **Emit** — the application writes structured JSON to stdout (O4.6).
2. **Collect** — an agent reads it: a DaemonSet tailing container log files in Kubernetes (K9.13), a sidecar, or a host agent.
3. **Ship** — the agent buffers and forwards to a backend, with batching, retry, and backpressure.
4. **Parse** — extract fields. **Ideally already done by structured emission** (O4.1); otherwise regex or grok at this stage, which is fragile and CPU-expensive.
5. **Enrich** — add Kubernetes metadata (pod, namespace, labels), host, region, environment. **This is what makes logs queryable by service** and is done by the collector, not the app.
6. **Index** — the backend indexes fields for search. **Indexing is the main cost driver** in Elasticsearch-style systems; Loki deliberately indexes only labels and not content, which is the fundamental architectural difference.
7. **Retain** — tiered retention (O4.8).

The failure points worth knowing: **buffer overflow at the agent** when the backend is slow — logs are dropped, usually silently, and exactly during an incident when the backend is under load. **Node disk pressure** from unrotated container logs (K6.11). **Parse failures** turning structured data into an unqueryable blob. **Index mapping explosions** in Elasticsearch when a high-cardinality field is indexed as a keyword (the same class of problem as O1.3). And **the pipeline itself needs monitoring** — dropped-log counters and agent health, because a silently broken pipeline is discovered when you need the logs.

**O4.5 — Configuring a collector**

Fluent Bit, as the common Kubernetes case:

```ini
[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    Parser            cri
    Tag               kube.*
    Mem_Buf_Limit     50MB
    Skip_Long_Lines   On
    DB                /var/log/flb_kube.db     # checkpoint: survives restarts

[FILTER]
    Name                kubernetes
    Match               kube.*
    Merge_Log           On                      # parse the JSON in the log field
    Keep_Log            Off
    Labels              On
    Annotations         Off

[FILTER]
    Name    grep
    Match   kube.*
    Exclude log_processed_level debug           # drop debug at the collector

[OUTPUT]
    Name        loki
    Match       kube.*
    labels      job=fluentbit, namespace=$kubernetes['namespace_name'], app=$kubernetes['labels']['app']
    Retry_Limit 5
```

The configuration decisions that matter:

- **`DB` (checkpointing)** so a restarted agent resumes rather than re-reading or skipping — without it, a restart duplicates or loses logs.
- **`Mem_Buf_Limit`** bounds memory; exceeding it drops logs. **Filesystem buffering** trades disk for durability and is worth enabling for anything important.
- **Kubernetes enrichment** is the step that makes logs attributable (O4.4).
- **Filtering at the collector** is the cheapest place to reduce volume (O4.7) — dropping health-check logs and debug output before they're shipped saves ingestion cost.
- **Label cardinality on the output** is critical for Loki — labels are the index, so a high-cardinality label (pod name in a churning cluster) destroys performance. Same discipline as O2.7.

**Vector** is the modern alternative with a richer transform language (VRL) and better performance; the **OTel Collector** unifies logs with metrics and traces (O6.4) and is the direction of travel.

**O4.6 — Why logging to stdout is the containerised convention**

The application writes to stdout/stderr; the container runtime captures it to a file on the node; a collector tails those files (O4.4).

Why this is the convention:

- **The application doesn't need to know about the logging infrastructure.** No file paths, no log shipping library, no backend credentials, no rotation config. The app has one job: write to stdout. **That's the separation of concerns that makes the twelve-factor argument.**
- **The runtime handles rotation** and the collector handles delivery.
- **`kubectl logs` and `docker logs` work** (K9.1), which is the debugging path everyone reaches for first.
- **It's uniform across languages and frameworks**, so one collector configuration serves everything.
- **Writing to a file inside a container** means the logs vanish with the container, or need a shared volume plus a sidecar — more moving parts, and a common source of "where did the logs go".

The caveats worth knowing: **stdout is not durable** — logs buffered in the runtime during a crash can be lost. **Very high log volume through stdout has real overhead** (it's a blocking write in many runtimes, so a slow collector can back-pressure the application, which is a genuinely surprising failure mode). **Multi-line logs (stack traces) need collector-side reassembly** or each line becomes a separate record. And **node disk fills** if rotation is misconfigured, triggering pod eviction (K6.11).

**O4.7 — Log cost drivers and reducing volume**

The drivers, in order of typical impact:

1. **Ingestion volume** — usually billed per GB and dominant. Halving volume halves the bill.
2. **Indexing** — in Elasticsearch-style systems, indexing all fields is expensive; Loki's label-only indexing is the architectural response.
3. **Retention** — storage over time (O4.8).
4. **Query** — some platforms bill by data scanned (A9.2).

Reducing volume **without losing signal**:

- **Turn off debug logging in production.** Consistently the single largest win, and consistently present.
- **Don't log health checks and readiness probes.** On a Kubernetes service these can be the majority of access log lines, and they carry essentially no information.
- **Sample high-volume, low-value logs** — keep 1% of successful request logs, 100% of errors. Biased sampling preserves signal while cutting volume dramatically.
- **Collapse per-request logs into one wide event** rather than five narrow ones (O1.6) — fewer records, more context, less cost.
- **Move counting to metrics** (O4.11). If you're logging an event solely to count occurrences, that's a counter.
- **Drop noisy known-benign messages at the collector** (O4.5).
- **Tier retention** (O4.8) rather than keeping everything hot.
- **Compress and use efficient formats** downstream.

The framing to give: **the goal is not fewer bytes, it's a better signal-to-cost ratio.** Blanket volume caps cause teams to drop the wrong things. The productive approach is to identify the top talkers (nearly always a handful of services or a single chatty message) and address those specifically — an 80/20 that leaves the useful logs untouched (O16.1).

**O4.8 — Retention design**

Three competing requirements:

- **Operational** — incident investigation. Realistically 7–30 days covers almost all of it; after that you're reading the post-incident review, not the logs.
- **Cost** — hot indexed storage is expensive and grows continuously.
- **Compliance** — may mandate years for audit, security, or transaction logs. In a regulated environment this is non-negotiable and specified.

The design that satisfies all three: **tier by access pattern, not by a single global policy.**

| Tier | Duration | Storage | Purpose |
|---|---|---|---|
| Hot, indexed | 7–14 days | Search platform | Incident investigation |
| Warm | 30–90 days | Cheaper index or object storage | Trend and post-incident |
| Cold / archive | 1–7 years | S3 + Glacier, queried with Athena (A15.5) | Compliance, forensics |

The points that matter:

- **Classify logs by type, not by service.** Audit and security logs need long retention; application debug logs need days. A single retention policy over-retains the cheap stuff and under-retains the important stuff.
- **Compliance retention belongs in object storage with lifecycle rules and object lock** (A6.1, A11.7), not in an expensive search index. **Paying search-platform rates for seven years of data nobody queries interactively is a classic and large waste** (A9.9).
- **Know your query pattern before setting the tier** — if you genuinely need to search two-year-old logs regularly, archive-only doesn't work.
- **Deletion must be enforceable** for GDPR (M11.5), which means knowing which logs contain personal data (O4.9).

**O4.9 — Preventing secrets and PII from reaching logs**

The exposures: **an exception dumping a request object** containing an Authorization header or a card number; **logging the full request or response body**; **connection strings with embedded passwords**; **debug logging of an entire config object**; **a stack trace including argument values**; and **user data logged for "debugging" and never removed.**

The controls, and defence in depth matters because each layer leaks:

1. **At the application** — a logging library with **redaction**, either by field-name allow-list (log only named fields, never whole objects — the strongest approach) or deny-list (redact `password`, `token`, `secret`, `authorization`, `card_number`). Deny-lists always miss something.
2. **Type-level protection** — wrap secrets in a type whose `toString`/`__repr__` returns `[REDACTED]`, so an accidental log of the object is safe. This is the most robust language-level control.
3. **At the collector** — regex-based redaction of card-number and token patterns before shipping (O4.5). A backstop for what the app missed.
4. **At the platform** — automated scanning of log content for secret patterns, alerting when found.
5. **In review** — treat logging a request body as a code-review flag.

The consequences of failure: **a secret in a log is a leaked secret** requiring rotation (A10.30), and log retention means it's leaked for the retention period across every replica of the log store. **PII in logs brings the logs into GDPR scope**, which means deletion requests must reach them — a genuinely hard problem given log immutability and archival (M11.5).

The framing: **never log whole objects.** Log named fields. That single rule prevents most of this class, and it's the practice to advocate rather than a redaction list.

**O4.10 — An effective query for an incident question**

The question: *"Which endpoints started returning 5xx at 14:20, for which tenants, and what was the upstream error?"*

Loki:

```logql
{namespace="payments", app="api"}
  | json
  | http_status >= 500
  | line_format "{{.endpoint}} {{.tenant_id}} {{.error}}"
```

with aggregation:

```logql
sum by (endpoint, upstream) (
  count_over_time({namespace="payments"} | json | http_status >= 500 [5m])
)
```

Elasticsearch/Kibana KQL:

```
service: "payments-api" and http_status >= 500 and @timestamp >= "2026-08-20T14:15:00Z"
```
then aggregate by `endpoint` and `upstream`.

CloudWatch Logs Insights (A9.2):

```
fields @timestamp, endpoint, tenant_id, upstream, error
| filter http_status >= 500
| stats count(*) as errors, count_distinct(tenant_id) as tenants by endpoint, upstream
| sort errors desc
```

The technique, which is the transferable part:

1. **Narrow the time range first** — most platforms bill by data scanned and all of them are faster on a narrow window.
2. **Narrow by service/namespace before parsing** — in Loki especially, label selectors use the index and everything after is a linear scan, so a broad selector is enormously more expensive.
3. **Filter, then aggregate.** Get to a count-by-dimension as fast as possible; reading individual lines is the last step, not the first.
4. **Group by the dimension that discriminates** — endpoint, upstream, tenant, version, AZ. **The goal is to find what's different about the failing population**, which is the core diagnostic move (T1).
5. **Then pull a few full lines** and their trace IDs (O4.3) for the detail.

The meta-point worth making: **the query is the easy half.** Whether you can answer the question was decided when the log line was written — if `tenant_id` and `upstream` aren't fields, no query recovers them (O1.6).

**O4.11 — When a log should have been a metric**

The signal: **you are logging an event solely so you can count or time it later.**

```python
log.info("cache miss for key %s", key)        # then: count these per minute
log.info("request took %dms", duration)       # then: compute p99 from these
```

Both are metrics wearing logs' clothing. Counting log lines to derive a rate is **expensive** (you're paying ingestion and index for data whose only use is aggregation), **slow** (a query scanning millions of lines versus reading a time series), **lossy** (sampling and retention limits break the count, O1.4), and **imprecise** (log-derived rates depend on the pipeline's completeness).

**Use a metric when**: you want a rate, a count, a percentile, or a gauge; you'll alert on it; you want it over a long time range; and the dimensions are bounded (O2.7).

**Use a log/span when**: you need per-event context; the dimensions are high-cardinality (tenant, user, key); you need it for forensics rather than aggregation; and it's rare enough that volume isn't a concern.

**The complementary pattern is the right answer most of the time**: emit a metric for the aggregate *and* a log/span for the detail. `cache_misses_total` counted as a metric, with the specific key on the span for the requests that were traced. You get cheap alerting and rich investigation without paying for either twice.

The related anti-pattern in the other direction: **metric-ifying something high-cardinality** because it felt like a metric (O1.3). The two errors are mirror images, and the discriminator in both directions is **cardinality and whether you'll aggregate**.

---

## O5. Tracing

**O5.1 — Traces, spans, and parent-child relationships**

- **A span** is one unit of work: a duration, a name, a status, attributes, and events. An HTTP handler, a database query, an outbound call.
- **A trace** is the tree of spans for one logical request, sharing a **trace ID**.
- **Parent-child** — each span records its parent's span ID, forming a tree. The **root span** has no parent and represents the request's entry into the system.

The relationships worth being precise about:

- **Child spans are usually nested in time within the parent**, but not necessarily — an async operation the parent didn't wait for can outlive it.
- **A span's duration includes its children**, so the *self time* (duration minus children) is what tells you where the work actually happened (O5.5).
- **Span links** are a different relationship from parent-child: used when work is causally related but not nested — most importantly for **asynchronous messaging**, where a consumer processes a message minutes after the producer's span closed (M10.6). Modelling that as parent-child produces traces spanning hours with nonsensical durations; a link is correct.

The practical implication: **the trace structure mirrors your call graph**, so a trace is a live architecture diagram of one request. That's part of why it's valuable on a system you didn't build (O16.5).

**O5.2 — Context propagation**

The active span's context — trace ID, span ID, sampling decision, and trace state — must travel with the request across process boundaries so the receiving service creates a child rather than a new root.

- **Injection** — the outbound client serialises the context into the transport (HTTP headers, message headers, gRPC metadata).
- **Extraction** — the inbound server reads it and sets it as the active context.
- **In-process propagation** — thread-local, async-local, or context objects carry it between functions. **This is where it usually breaks**: a thread pool, an async boundary, or a callback loses the context and everything downstream becomes a new trace.

The mechanism is standardised as W3C trace context (O5.3), and OpenTelemetry's instrumentation handles injection and extraction automatically for common libraries (O6.2).

The cases needing care: **thread pools and executors** (the context must be captured and restored around the task); **async/await** in languages without automatic context flow; **message queues** (headers, and a link rather than a parent, M10.6); **batch processing** (one poll of 500 messages carries 500 contexts — one span for the batch loses all of them); and **any custom transport** where nothing knows to inject.

**O5.3 — W3C trace context**

Two headers, and the standard exists so different vendors' instrumentation interoperates:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             │  │                                │                │
             │  trace-id (16 bytes)              parent-id        trace-flags
             version                             (span id)        (01 = sampled)

tracestate: vendor1=value1,vendor2=value2
```

- **`traceparent`** carries the identity and the sampling flag. **The sampled flag is what makes a sampling decision propagate** — a downstream service honours the upstream decision rather than making its own, which is what prevents partial traces (O1.4, O5.4).
- **`tracestate`** carries vendor-specific data across a multi-vendor path.

Why the standard matters: **before it, every vendor had its own headers** (B3/Zipkin, X-Ray's `X-Amzn-Trace-Id`, Jaeger's `uber-trace-id`), so a request crossing services using different tools produced broken traces. W3C is the interop layer, and OTel propagators can be configured to emit and accept several formats simultaneously during a migration — which is the practical detail worth knowing, because AWS services (ALB, API Gateway, Lambda) emit X-Ray format and bridging that to W3C is a real task.

**O5.4 — Head-based vs tail-based sampling**

- **Head-based** — the decision is made at the root span, before anything is known about the request, and propagated (O5.3) so the whole trace is consistently kept or dropped. Cheap, stateless, and **it cannot know whether the request will be slow or fail.**
- **Tail-based** — spans are buffered until the trace completes, then a decision is made **with full knowledge**: keep all errors, keep everything above a latency threshold, sample the fast successes at 1%.

**Tail-based is what you want, and it costs more**:

- It requires **buffering all spans of a trace in one place** until complete, which means memory in the collector and — crucially — **all spans of a trace must reach the same collector instance.** That needs a load-balancing exporter that routes by trace ID, which is a real deployment consideration people miss.
- It adds **latency** to the export path and a **timeout** for incomplete traces.
- It scales less trivially than head-based.

The practical position: **head-based with a low rate for baseline volume, plus tail-based (or error-biased head sampling) to guarantee errors and slow requests are kept.** The property that matters is that **you never sample away the traces you'll actually want** — a 1% head-based sample that discards 99% of your errors is the failure this is all about (O1.4).

Two refinements worth naming: **rate-limiting samplers** (keep N traces/sec per service) give predictable cost regardless of traffic; and **`parentbased_traceidratio`** is the standard OTel sampler that respects an upstream decision and applies a ratio only at the root.

**O5.5 — Reading a trace waterfall**

The waterfall shows spans as horizontal bars: position is start time, length is duration, indentation is depth.

The reading method:

1. **Look at the root span's total duration** — that's what the user experienced.
2. **Find the longest bar that isn't just containing others.** Look for **self time** (a span's duration minus its children's) — a 2-second span with a 1.95-second child is not where the time went; the child is.
3. **Look for gaps** — unaccounted time between a parent's start and its first child, or between children. **Gaps are time spent in code you haven't instrumented**: serialisation, GC pauses (O10.5), lock waiting (O9.8), queueing, or connection acquisition. **Gaps are frequently the most informative thing in the trace** and people overlook them because there's no bar to click.
4. **Look for serialisation** — many short spans in sequence that could have been concurrent. N+1 query patterns are unmistakable in a waterfall: dozens of near-identical short spans in a row.
5. **Look for fan-out** — parallel children, where the parent's duration is bounded by the slowest (O12.4).
6. **Check span status and attributes** on anything anomalous.

The patterns and their diagnoses: **one dominant span** → that service or query is the problem; **many small sequential spans** → N+1, batch them; **a long gap before a child starts** → connection pool exhaustion or queueing (O12.7); **all spans slow proportionally** → a shared resource (CPU, network, a saturated dependency) rather than a specific call.

**O5.6 — Span attributes and events**

- **Attributes** — key-value pairs on the span describing the operation: `http.request.method`, `http.response.status_code`, `db.system`, `db.query.text`, `messaging.destination.name`, plus your own (`tenant.id`, `order.value`, `feature_flag.new_pricing`).
- **Events** — timestamped occurrences within a span: an exception, a retry, a cache miss, a state transition. A span with events is a mini-log of the operation with the timing preserved.

**What's worth attaching:**

- **Anything you'd want to filter or group by during an investigation** — tenant, user tier, region, version, feature flags, request size, the specific resource. **This is where high-cardinality data belongs** (O1.3), and it's the answer to "we can't put customer ID in a metric label."
- **Semantic convention attributes** (O6.6), so tooling recognises them.
- **The error, as a recorded exception event** with the type, message, and stack trace, plus setting span status to `ERROR`.
- **Business-meaningful values** — order total, item count, model name and token count for an LLM call. These make traces answerable to product questions, not just technical ones.

**What isn't:** entire request or response bodies (size, cost, and PII, O4.9); secrets (a span is a log, with the same exposure); and anything unboundedly large.

The cost consideration: **attributes are stored per span**, so a verbose attribute set multiplied by span count multiplied by trace volume is a real cost driver (O16.1). And **`db.query.text` should be the parameterised statement**, not the interpolated one — otherwise it's both high-cardinality and a PII risk.

**O5.7 — Why a trace breaks**

A broken trace shows a root span with no children, or a trace that starts mid-system with no parent, or two separate traces for what was one request.

The causes:

- **A service that doesn't propagate context** (O5.2) — the most common. An uninstrumented service in the middle of the chain receives the headers, ignores them, and makes its outbound calls with no context. Everything downstream starts a new trace, so **the trace ends at that service and a second, orphaned trace begins after it.** The gap in the waterfall is exactly where the uninstrumented service sits, which is at least diagnostic.
- **In-process context loss** — a thread pool, an async boundary, or a callback that doesn't carry the context. The service is instrumented and still produces disconnected spans.
- **A proxy or gateway stripping headers** — some load balancers and API gateways drop unknown headers by default, which silently breaks propagation at the edge.
- **Format mismatch** — one service emits B3, another expects W3C (O5.3). Configure multiple propagators during migration.
- **Inconsistent sampling** — a service making its own head-based decision rather than honouring the propagated flag produces partial traces (O5.4).
- **Async boundaries modelled wrongly** — a message queue where the consumer creates a root instead of a linked span (M10.6).

The diagnostic: **look at where the trace stops.** The last span before the gap tells you which service's outbound call lost the context, and it's usually a specific library or code path rather than the whole service.

**O5.8 — What tracing tells you that metrics and logs can't**

**The causal path and the latency breakdown of a single request across service boundaries.**

- **Metrics** tell you the aggregate — p99 latency of service A is up. They cannot tell you *why*, or which downstream call is responsible, because they're pre-aggregated and dimensionless beyond their labels.
- **Logs** tell you what one service did. Correlating them across ten services for one request requires the trace ID anyway (O4.3), and even then you're reconstructing timing by hand from timestamps across machines with clock skew.
- **Traces** give you the tree, the timings, and the parent-child structure directly.

The specific questions only tracing answers:

- **"Where did the time go for this request?"** — the waterfall, including self time and gaps (O5.5).
- **"Which of the twelve services in this path is slow?"** without checking twelve dashboards.
- **"What is the actual call graph?"** — the service map derived from traces is often the only accurate architecture documentation, and it's derived from reality rather than from a diagram (O16.5).
- **"Is this slow for everyone or just this tenant?"** — high-cardinality attributes make that filterable (O5.6).
- **"Did this request hit the cache, and did that matter?"**

The honest limits, worth stating: **tracing is sampled**, so it's poor for aggregate accuracy (use metrics); it's **expensive at full fidelity**; and **it tells you about requests, so it's blind to background work** and to problems that don't manifest as a traced operation. The three signals are complements, and the interesting cases are where they're used together (O1.7).

**O5.9 — The overhead cost of tracing**

The components:

- **In-process CPU and memory** — creating spans, recording attributes, serialising. Typically a few percent for a well-instrumented service; **more if you span too finely.** Spanning every function call rather than every meaningful operation is the usual cause of unacceptable overhead.
- **Network** — exporting spans, batched. Non-trivial at high span volume.
- **Collector resources** — especially with tail-based sampling, which buffers (O5.4).
- **Backend storage and query cost** — the dominant financial cost (O16.1).
- **Latency in the request path** — should be near zero, because export is asynchronous and batched. **If it isn't, the exporter is misconfigured** — a synchronous exporter, or a full queue applying backpressure, can add real latency and in the worst case block the application. That failure mode is worth naming: a tracing backend outage should never take down the application, and verifying the exporter drops rather than blocks is a real check.

The controls: **sampling** (O5.4) is the main lever; **span granularity** — instrument boundaries and expensive operations, not every method; **attribute discipline** (O5.6); **batch export with a bounded queue and a drop policy**; and **the collector as a buffer** so the application exports locally and cheaply (O6.5).

The framing: **the overhead is manageable and worth it, and it becomes unmanageable if you instrument indiscriminately.** The judgement is the same as O16.2 — instrument boundaries and the things you'd want to ask about, not everything.

---

## O6. Instrumentation & OpenTelemetry

**O6.1 — The OpenTelemetry model**

- **API** — the interface application code compiles against to create spans, record metrics, and emit logs. **Deliberately separable from the SDK**: a library can instrument with the API and be a no-op if no SDK is configured, which is what makes it safe for third-party libraries to ship OTel instrumentation.
- **SDK** — the implementation: sampling, batching, resource detection, processors, exporters. Configured in the application.
- **Collector** — a standalone binary that receives, processes, and exports telemetry. Not required, and almost always used (O6.4, O6.5).
- **Exporters** — the backend-specific output: OTLP, Prometheus, Jaeger, vendor-specific.
- **OTLP** — the wire protocol, gRPC or HTTP, which is the standard interchange.
- **Semantic conventions** — standard attribute names (O6.6).

The architectural point: **the API/SDK split is what delivers vendor neutrality** (O6.7). Application code and libraries depend on the API only; swapping backends is an SDK or collector configuration change. And **instrumentation is the expensive, invasive part** — it lives in your code — so making it backend-independent is a strategic decision rather than a tooling preference.

Signal maturity is worth being accurate about: **traces and metrics are stable; logs are stable in the protocol but the SDK story is less mature in some languages**, and many organisations still ship logs through their existing pipeline (O4.4) while using OTel for traces and metrics. Knowing that is a currency signal.

**O6.2 — Auto-instrumentation and its limits**

Auto-instrumentation adds spans and metrics without code changes — a Java agent (`-javaagent`), Python's `opentelemetry-instrument`, monkey-patching in Node, or the Kubernetes operator injecting it via an annotation.

**What it gives you**: HTTP servers and clients, database drivers, message broker clients, gRPC, cache clients — the boundaries. That's a genuinely large fraction of the value for near-zero effort, and it's the right first step on any service.

**Its limits**, which is the substance of the item:

- **It knows about libraries, not about your business.** It spans a database call; it can't tell you *which customer's order* the call was for, or that the operation was a fraud check. **The high-value attributes are the ones only you can add** (O5.6, O6.3).
- **It doesn't cover custom or unusual libraries**, in-house transports, or anything niche.
- **It can't see inside your logic** — a slow function between two instrumented calls appears as an unexplained gap (O5.5).
- **It can be too verbose** — some auto-instrumentation spans every ORM operation, producing enormous traces (O5.9).
- **Overhead is less controllable**, and agent-based instrumentation can have startup cost and, occasionally, compatibility problems with a specific framework version.
- **Context propagation across custom async boundaries** may not be handled (O5.2).

The practical position: **auto-instrumentation for breadth, manual for depth.** Turn it on everywhere to get the call graph and the boundaries; add manual spans and attributes for the operations that matter to the business (O6.3). That combination gets you most of the value for a fraction of the work, and it's the recommendation to give.

**O6.3 — Manual instrumentation for a business-meaningful operation**

```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

def process_payment(order):
    with tracer.start_as_current_span("payment.process") as span:
        span.set_attribute("payment.amount_minor", order.amount_minor)
        span.set_attribute("payment.currency", order.currency)
        span.set_attribute("payment.method", order.method)
        span.set_attribute("tenant.id", order.tenant_id)

        try:
            result = gateway.charge(order)           # auto-instrumented HTTP span, child
            span.set_attribute("payment.gateway_ref", result.reference)
            span.add_event("payment.authorised")
            return result
        except GatewayDeclined as e:
            span.set_attribute("payment.decline_reason", e.reason)
            span.set_status(Status(StatusCode.ERROR, "declined"))
            span.record_exception(e)
            raise
```

What makes this worth adding on top of auto-instrumentation:

- **The span name is a business operation**, so the trace reads as a business process, not a sequence of HTTP calls.
- **The attributes are the dimensions you'll actually filter by** during an investigation — tenant, amount, method, decline reason. **None of these could be inferred by auto-instrumentation**, and all of them are high-cardinality so they can't be metric labels (O1.3).
- **The error is recorded with a business-meaningful reason**, so "why are payments failing" is answerable by grouping on `decline_reason`.

What to instrument manually: **operations that mean something to the business** and that you'd want to ask questions about — a payment, a fraud check, a model inference call (with model name, token counts, and latency), a batch job stage. **Not every function**, which costs overhead (O5.9) and produces unreadable traces.

**O6.4 — Deploying and configuring a collector**

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  memory_limiter:                    # MUST be first — prevents OOM
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 25
  k8sattributes:                     # enrich with pod/namespace/labels
    auth_type: serviceAccount
  resource:
    attributes:
      - { key: deployment.environment, value: production, action: upsert }
  attributes:                        # redaction (O4.9)
    actions:
      - { key: http.request.header.authorization, action: delete }
  tail_sampling:
    decision_wait: 10s
    policies:
      - { name: errors, type: status_code, status_code: { status_codes: [ERROR] } }
      - { name: slow, type: latency, latency: { threshold_ms: 1000 } }
      - { name: baseline, type: probabilistic, probabilistic: { sampling_percentage: 1 } }
  batch:                             # MUST be last — batches for export efficiency
    timeout: 5s
    send_batch_size: 8192

exporters:
  otlphttp/vendor:
    endpoint: https://otlp.vendor.example.com
  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, k8sattributes, resource, attributes, tail_sampling, batch]
      exporters: [otlphttp/vendor]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, k8sattributes, resource, batch]
      exporters: [prometheus, otlphttp/vendor]
```

The points that matter:

- **Processor order is significant and is a real source of bugs.** `memory_limiter` first (it can't protect you if it runs after the queue has filled); `batch` last (batching before sampling or enrichment wastes work and breaks some processors).
- **Deployment topology**: an **agent** (DaemonSet or sidecar) per node for local, low-latency receipt and enrichment, exporting to a **gateway** (Deployment) for tail sampling, aggregation, and egress. Tail sampling **must** be in the gateway with a load-balancing exporter routing by trace ID (O5.4), or traces are split across instances and the sampling decision is made on partial data.
- **The collector is production infrastructure** — it needs resource limits, autoscaling, monitoring of its own dropped-span counters, and a PDB (K6.9). A collector that OOMs silently drops telemetry precisely when load is high.

**O6.5 — The collector's role in decoupling apps from backends**

Without a collector, every application holds the backend endpoint, credentials, sampling configuration, and export logic. Changing the backend, adjusting sampling, or adding a second destination means **redeploying every service.**

With a collector, applications export OTLP to `localhost:4318` and know nothing else. Everything backend-specific lives in collector configuration.

What that buys:

- **Change backends without touching applications** — the practical realisation of vendor neutrality (O6.7). Evaluating a new vendor becomes adding an exporter and dual-sending, which is a genuinely reversible experiment.
- **Adjust sampling centrally** without a deploy (O5.4).
- **Enrich uniformly** — Kubernetes metadata, environment, region added once rather than in every service (O1.7).
- **Redact centrally** as a backstop for PII and secrets (O4.9).
- **Buffer and retry** — the application's export is a local call that always succeeds fast; the collector handles a backend outage without applying backpressure to the request path (O5.9).
- **Fan out** — send traces to a vendor and metrics to Prometheus, or dual-send during a migration.
- **Reduce egress** — batching and compression at the gateway rather than per-pod.

The framing that lands: **the collector is the seam that makes your observability backend a replaceable component rather than a strategic commitment** (O1.8). That's the strongest argument for deploying one even in a simple setup.

**O6.6 — Semantic conventions, and why consistency beats completeness**

Semantic conventions are the standardised attribute names: `http.request.method`, `http.response.status_code`, `url.path`, `server.address`, `db.system`, `db.namespace`, `messaging.system`, `service.name`, `deployment.environment`.

**Why consistency matters more than completeness:**

- **Cross-service queries only work if everyone agrees on names.** "Show me p99 latency by service for all HTTP servers" requires every service to use the same attribute for the method and status. If three teams use `http.status`, `status_code`, and `httpStatusCode`, the query is impossible without a translation layer — and you will not build that layer.
- **Tooling depends on the conventions.** Backends build service maps, RED dashboards, and error detection by recognising standard attributes. Non-standard names mean the tooling shows nothing and you build dashboards by hand.
- **Ten services with consistent, sparse attributes are more useful than three with exhaustive, bespoke ones.** Completeness in one service doesn't enable comparison; consistency across many does. That's the trade the item is pointing at.
- **Correlation across signals** requires the same resource attributes on metrics, logs, and traces (O1.7).

The practicalities: **the conventions have been through breaking changes** (the HTTP conventions were renamed in the stabilisation process — `http.method` → `http.request.method`), so pin versions and migrate deliberately; **use the `resource` processor in the collector** to enforce standard resource attributes centrally rather than trusting every service (O6.4); and **define your own conventions for domain attributes** (`tenant.id`, not `tenantId` in one place and `customer` in another) and document them — that's part of the platform contract (O16.3).

**O6.7 — Vendor neutrality as an argument for OTel**

The argument, and it should be made as a strategic one:

- **Instrumentation is the expensive part and it lives in your application code.** Getting spans, attributes, and context propagation right across dozens of services is months of work spread across every team. **A vendor-specific SDK makes that investment non-portable** — changing backends means re-instrumenting everything, which in practice means you never change backends.
- **With OTel, the instrumentation is an asset independent of the vendor.** Changing backends is a collector configuration change (O6.5) — hours, not quarters.
- **That changes your commercial position.** Observability pricing is usage-based and grows with your system (O1.8, O16.1); the ability to credibly move is what keeps renewal negotiations honest. That's a blunt point and a true one.
- **It's the industry standard**, so libraries, frameworks, and platforms ship OTel instrumentation natively, and hiring is easier.
- **You can send to several backends simultaneously** — a vendor for traces, self-hosted Prometheus for metrics, or dual-sending during an evaluation.

The honest caveats: **vendors' proprietary agents sometimes do more** — deeper profiling, better auto-instrumentation for specific frameworks, richer defaults — and you may give some of that up. **OTel's operational surface is yours** (the collector is a component you run). And **maturity varies by language and signal** (O6.1).

The position to hold: **instrument with OTel, then choose a backend on its merits.** The decision you're protecting is the ability to change your mind, and for a platform role that framing — reversibility as the thing being bought — is what makes it a senior answer rather than a preference.

**O6.8 — Instrumenting a platform component teams depend on**

The distinction: a platform component (an ingress controller, a message broker, an internal API gateway, a shared cache, a model-serving proxy) is used by many teams, so **its telemetry must serve consumers who don't own it.**

What that means:

- **Expose per-consumer dimensions.** Aggregate metrics for the component tell the platform team it's healthy; **application teams need to see their own slice** — per-service, per-tenant, per-route. A gateway reporting only global p99 is useless to a team asking whether *their* route is slow.
- **Propagate trace context correctly** (O5.2). A platform component in the request path that breaks propagation breaks tracing for everyone downstream (O5.7) — the blast radius of that mistake is the whole estate, which is why it's worth calling out separately.
- **Emit RED metrics for the component as a service** (O2.9) and USE for its resources (O2.10).
- **Publish an SLO for the component**, so teams know what they're depending on and can budget for it in their own SLOs (O16.3).
- **Provide the dashboard**, not just the metrics — teams should not each build their own view of your component (O7.3).
- **Instrument the failure modes teams will hit**: rate limiting and throttling (with the consumer identified), queue depth, connection pool saturation, retries and their causes. **When a consumer is throttled, they need to see that it was them and why**, or they'll open a ticket instead.
- **Document the metric and attribute names** as part of the contract (O16.3).

The principle: **a platform component's observability is part of its interface.** If teams can't self-diagnose whether their problem is your component, you become the bottleneck for every investigation that touches it — which is the same failure mode as K13.4 and TF8.8.

---

## O7. Dashboards & visualisation

**O7.1 — A dashboard that answers a specific question**

The design method: **start with the question, not the metrics.**

Bad: a dashboard with forty panels showing every metric the service emits, arranged by whatever order they were added.

Good: a dashboard titled *"Is the payments API healthy?"* with, in reading order:

1. **The SLI at the top** — error rate and latency against the SLO threshold, with the error budget remaining (T7.2).
2. **Traffic**, so you can tell a drop in errors from a drop in requests.
3. **Error rate broken down by endpoint and status**, because that's the first follow-up question.
4. **Latency distribution** as a heatmap (O7.5), not just percentile lines.
5. **Deploy and config-change annotations** overlaid, because "what changed" is the first diagnostic question (T1, O1.6).
6. **Immediate dependencies' health** — database, cache, downstream services — because that's the second follow-up.

The principles:

- **Every panel should answer a question someone actually asks**, and you should be able to say what that question is. A panel nobody can justify should be deleted.
- **Order panels by the diagnostic path** — top to bottom should follow how an investigation actually proceeds, so scrolling down is narrowing.
- **Put the most important thing top-left**, because that's where eyes land.
- **Show thresholds and SLO lines**, so a value has meaning without the viewer knowing the target.
- **Annotate deploys.** Disproportionately valuable and frequently absent.
- **Fewer panels, better chosen.** A dashboard that fits on one screen gets used; one requiring scrolling through forty graphs does not (O7.7).

**O7.2 — A dashboard hierarchy**

Three levels, each with a distinct audience and question:

1. **Overview / service health** — one row per service: is it up, is it within SLO, is the error budget healthy. **For on-call triage and for leadership.** The question: *which service is unhealthy?* Should fit on one screen and be readable at a glance from across a room.
2. **Service dashboard** — RED for one service (O2.9), broken down by endpoint and version, with dependency health and deploy annotations. **For the owning team and for an on-call responder who has identified the service.** The question: *what's wrong with this service?*
3. **Deep dive** — resource-level (USE, O2.10), runtime internals (GC, thread pools, connection pools), specific subsystem detail. **For someone diagnosing a known problem.** The question: *why is it wrong?*

The value of the hierarchy: **an incident responder navigates down it**, and each level narrows the search. Without it, you either have one enormous dashboard nobody can parse or a flat list of two hundred dashboards nobody can find.

Practicalities: **link between levels** — a service on the overview should click through to its dashboard, which should link to its deep dives and to the relevant logs and traces (O1.7). **Standardise levels 1 and 2 via templating** (O7.3) so every service looks the same and an on-call engineer can read any service's dashboard without learning it. **Level 3 is where team-specific customisation is legitimate.**

**O7.3 — Variables and templating**

```
$environment  = label_values(up, environment)
$service      = label_values(up{environment="$environment"}, service)
$endpoint     = label_values(http_requests_total{service="$service"}, endpoint)
```

```promql
sum by (endpoint) (rate(http_requests_total{service="$service", environment="$environment"}[5m]))
```

The value: **one dashboard serves every service** rather than one dashboard per service. Which means: a fix or improvement applies everywhere at once; every service's dashboard looks identical so an on-call engineer can read any of them; and adding a service requires no dashboard work at all — it appears in the dropdown automatically.

The techniques: **chained variables** (selecting an environment filters the service list) keep the options relevant; **`All` and multi-select** for comparison across instances; **repeated rows or panels** per variable value to show every endpoint without predefining them; and **`__interval`/`__rate_interval`** so the query window adapts to the selected time range — **use `$__rate_interval` in `rate()`**, because a fixed `[5m]` breaks when someone zooms out to 30 days, which is a very common dashboard bug.

This pairs directly with dashboards-as-code (O7.6): a templated dashboard defined once and deployed to every environment is the practical version of a platform team providing observability rather than each team building it (O16.3).

**O7.4 — Choosing the right visualisation**

| Data | Visualisation | Why |
|---|---|---|
| A rate over time | Line graph | Trend and shape |
| Latency distribution | **Heatmap** (O7.5) | Shows the distribution, not just summary lines |
| Current value against a threshold | Stat / gauge panel with thresholds | Instant read, colour-coded |
| Composition over time | Stacked area | Shows both total and breakdown |
| Comparing many series at a point in time | Bar chart or table, sorted | Line graphs with 50 series are unreadable |
| Ranked worst offenders | Table with `topk` | Sortable, precise |
| Discrete state over time | State timeline | Up/down, deploy status, alert firing |
| Correlation between two metrics | Two y-axes, or a scatter | With care — dual axes mislead easily |
| SLO burn | Stat with error budget remaining | The number people act on |

The rules worth stating:

- **Line graphs with more than about ten series are noise.** Aggregate, or use `topk`, or use a table.
- **Stacked graphs hide individual series' shapes** — good for composition, bad for spotting one series' anomaly.
- **Gauges and pie charts waste space** and are hard to read precisely; a stat panel with a threshold colour does the same job in a fraction of the area.
- **Dual y-axes invite false correlation** — two lines can be made to look related by scaling. Use with care and label clearly.
- **Log scale for anything spanning orders of magnitude**, which latency often does.
- **Consistent colours across panels** — errors always red, one service always the same colour — so a dashboard is readable at a glance.

**O7.5 — Why heatmaps beat line graphs for latency**

A percentile line graph shows p50, p95, p99 as three lines. **That's three points from a distribution, and it hides everything between and beyond them.**

A heatmap plots time on x, latency buckets on y, and colour intensity as the count of requests in each bucket. **You see the whole distribution at every point in time.**

What the heatmap reveals that lines cannot:

- **Bimodality.** Two distinct bands — say 5ms and 200ms — means two populations of request: cache hits and misses, warm and cold instances, two code paths. **The percentile lines just show a smooth curve somewhere between them, describing a request that doesn't exist.** This is the single most valuable thing heatmaps show, and it's genuinely common.
- **How much of the traffic is in the tail** — a p99 of 2s tells you the boundary; the heatmap shows whether that's a thin wisp or a substantial band.
- **Distribution shape changes** — a distribution widening before the percentiles move is an early warning.
- **Whether an improvement moved the whole distribution** or just the summary statistic you optimised for (O13.10).

The practical points: **heatmaps come naturally from Prometheus histograms** (the `le` buckets are the y-axis), so if you're already exporting histograms you get this for free. **Bucket resolution limits the heatmap's resolution** (O2.5). And **use both** — heatmap for understanding, percentile lines for alerting and for SLO tracking, since a threshold needs a single number.

**O7.6 — Dashboards as code**

The problem with UI-built dashboards: no version control, no review, no reproducibility, no consistency across environments, and **they're lost or diverge when someone edits one during an incident.**

The approaches: **Grafana provisioning** from JSON files in git; **Terraform's Grafana provider**; **Grafonnet** (Jsonnet) or **grafana-foundation-sdk** for programmatic generation; and the **Grafana Operator** on Kubernetes with dashboards as CRDs.

The benefits: **review** — a dashboard change is a PR, so a bad panel gets caught; **reproducibility** across environments and after a Grafana rebuild; **consistency** through generation from a template, which is how you make every service's dashboard identical (O7.3); **bulk change** — improving the standard service dashboard updates a hundred of them at once; and **disaster recovery**, since dashboards are as easy to lose as anything else.

The friction to acknowledge honestly: **iterating on a dashboard in code is slower than dragging panels in the UI**, and that friction is real. The workable pattern is **build in the UI, export the JSON, commit it** — and then treat the committed version as authoritative, with the provisioned dashboards read-only in the UI so drift is impossible.

The scaling argument: **generate rather than copy.** A hundred hand-maintained service dashboards diverge; a hundred generated from one template don't. That's the same argument as module reuse in Terraform (TF4.1), and it's what makes dashboards a platform deliverable rather than a per-team chore.

**O7.7 — Why most dashboards go unused, and how to avoid it**

**Why they go unused:**

- **They were built to display everything rather than to answer a question** (O7.1), so nobody knows what to look at.
- **They show data without context** — a graph at 47 with no threshold, no baseline, and no indication of whether that's good.
- **Too many panels** — forty graphs means nobody reads any of them.
- **They were built for a specific past incident** and never removed, so the collection accumulates.
- **Nobody can find them** — hundreds of dashboards with inconsistent names and no hierarchy (O7.2).
- **They're stale** — metrics renamed, panels broken, and half the graphs show "No data", which trains people not to trust any of it.
- **They were built by someone who left**, and nobody knows what the panels mean.
- **The real answer is elsewhere** — people go straight to logs or traces because that's where the information actually is.

**How to avoid it:**

- **One question per dashboard, stated in the title** (O7.1).
- **A clear hierarchy with links** (O7.2).
- **Standardise and generate** (O7.3, O7.6), so every service's dashboard is familiar.
- **Show thresholds and SLO context** so numbers mean something.
- **Annotate deploys.**
- **Prune ruthlessly.** Review usage — Grafana reports dashboard view counts — and **delete what nobody opens.** An unused dashboard is not harmless; it's clutter that makes the useful ones harder to find.
- **Build the dashboard the incident actually needed**, then generalise it — dashboards derived from real investigations get used, because they answer real questions.

The parallel worth drawing: **this is the same problem as unactioned alerts** (O8.7) and unread findings (A10.29). Telemetry that nobody consumes is cost without benefit, and the discipline of removing it is as important as the discipline of adding it (O16.7).

---

## O8. Alerting in practice

Philosophy and design are T7.3–T7.5; this section is the mechanics.

**O8.1 — An alerting rule with a sensible `for` duration**

```yaml
groups:
  - name: api-slis
    rules:
      - alert: HighErrorRate
        expr: |
          sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
            / sum by (service) (rate(http_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: page
          team: payments
        annotations:
          summary: "{{ $labels.service }} error rate {{ $value | humanizePercentage }}"
          runbook: "https://runbooks.acme.io/payments/high-error-rate"
          dashboard: "https://grafana.acme.io/d/payments?var-service={{ $labels.service }}"
```

**The `for` duration is the condition-must-hold-continuously period before firing.** Choosing it:

- **Too short** → flapping and pages for transient blips (O8.2). A single slow scrape or a brief deploy-related spike pages someone at 3am.
- **Too long** → slow detection, and you burn error budget while the alert waits.
- **The rule of thumb**: `for` should exceed the duration of a blip you'd tolerate, and be short enough that the alert fires well within your response-time objective.
- **It must be at least several scrape intervals**, or a single missed scrape resets the timer and the alert never fires. This interacts with O3.10 — during the `for` window, if the series goes stale, the pending state is discarded.
- **Interaction with the query window**: `rate(...[5m])` already averages over 5 minutes, so a `for: 5m` on top means roughly 10 minutes to fire. **Don't double-count** — people frequently add a long `for` to an already-smoothed query and get very slow alerting.

Better than tuning `for` for SLO alerts: **multi-window multi-burn-rate** (O8.4), which encodes fast and slow detection explicitly rather than through one compromise value.

**O8.2 — Flapping and how to damp it**

Flapping is an alert repeatedly firing and resolving as the metric oscillates around the threshold. It produces notification spam, and worse, **it trains people to ignore the alert.**

The causes: a threshold sitting inside the metric's normal variance; a noisy metric (`irate`, O3.4); a short `for`; a genuinely borderline system.

The damping techniques:

- **`for` duration** (O8.1) — the primary mechanism.
- **Smooth the query** — `rate` over a longer window, or `avg_over_time`. Trades responsiveness for stability.
- **Hysteresis** — fire at one threshold, resolve at a lower one. Prometheus doesn't support this natively; you approximate it with `for` plus `keep_firing_for`, which holds the alert active for a period after the condition clears — genuinely useful and under-used.
- **Alertmanager `group_interval` and `repeat_interval`** to control notification frequency independently of alert state (O8.3).
- **Move the threshold** if it's simply in the wrong place — sometimes the alert is correct and the threshold is too tight.
- **Burn-rate alerting** (O8.4), which is inherently more stable because it's integrating over a window.

The diagnostic question: **is it flapping because the alert is badly tuned, or because the system is genuinely oscillating around unacceptable?** The second case is real, and damping it hides a problem. Check the underlying metric before assuming it's an alerting bug.

**O8.3 — Routing, grouping, inhibition, silences**

```yaml
route:
  receiver: default
  group_by: [alertname, cluster, service]
  group_wait: 30s          # wait to collect related alerts before first notification
  group_interval: 5m       # wait before notifying about new alerts in an existing group
  repeat_interval: 4h      # re-notify for a still-firing alert
  routes:
    - matchers: [severity="page"]
      receiver: pagerduty
      continue: false
    - matchers: [severity="ticket"]
      receiver: jira
    - matchers: [team="payments"]
      receiver: payments-slack

inhibit_rules:
  - source_matchers: [alertname="ClusterDown"]
    target_matchers: [severity=~"page|ticket"]
    equal: [cluster]

receivers:
  - name: pagerduty
    pagerduty_configs:
      - service_key: <key>
```

- **Routing** — a tree matched on labels, sending alerts to the right destination. **Route by team label**, so alerts reach owners rather than a central inbox (A10.29).
- **Grouping** — bundles related alerts into one notification. **Without it, a node failure sends fifty separate pages.** `group_by` choice matters: too coarse and unrelated alerts are bundled; too fine and you're back to spam.
- **Inhibition** — suppress alerts when a more significant one is firing. "If the whole cluster is down, don't page for every service in it." **This is the main tool for reducing cascade noise**, and it's the one most often unconfigured.
- **Silences** — time-bounded, matcher-based suppression for maintenance and known issues. **Silences must expire** — a permanent silence is an alert you should have deleted (O8.7), and an audit of long-lived silences is a good hygiene exercise.

The design point: **Alertmanager's job is to turn alert state into an appropriate number of human interruptions.** Prometheus decides what's wrong; Alertmanager decides who hears about it and how often. Conflating the two — trying to solve noise by editing rules — misses the tool designed for it.

**O8.4 — Multi-window multi-burn-rate SLO alerting**

The problem with a simple threshold alert on error rate: **it doesn't relate to the SLO.** A 1% error rate might be catastrophic or irrelevant depending on your budget and how long it lasts.

**Burn rate** = how fast you're consuming the error budget relative to the rate that would exhaust it exactly at the end of the window. A burn rate of 1 exhausts the budget precisely at period end; a burn rate of 14.4 exhausts a 30-day budget in about 2 days.

**Multi-window multi-burn-rate** uses several (burn rate, window) pairs:

| Burn rate | Long window | Short window | Budget consumed | Severity |
|---|---|---|---|---|
| 14.4 | 1h | 5m | 2% | Page |
| 6 | 6h | 30m | 5% | Page |
| 3 | 1d | 2h | 10% | Ticket |
| 1 | 3d | 6h | 10% | Ticket |

```promql
(
  job:slo_errors:ratio_rate1h{job="api"} > (14.4 * 0.001)
    and
  job:slo_errors:ratio_rate5m{job="api"} > (14.4 * 0.001)
)
```

**Why two windows**: the **long window** ensures the burn is sustained rather than a blip — it's what stops flapping. The **short window** ensures the problem is *still happening* — it's what makes the alert **reset quickly** once resolved, rather than staying fired for an hour because the long window still contains the incident.

**Why multiple burn rates**: a fast burn (14.4×) pages immediately because you'll exhaust the budget in days; a slow burn (1×) is a ticket because you have weeks. **The severity is proportional to the actual urgency**, which is exactly what a static threshold cannot express.

The prerequisites: **a defined SLO** (T7.2), **an SLI query** (O3.8), and **recording rules** for each window (O3.9), because computing four ratios over four windows ad hoc on every evaluation is expensive.

**O8.5 — Escalation policies and on-call schedules**

The mechanics, in PagerDuty/Opsgenie terms:

- **A schedule** — who is on call when. Rotation length (weekly is common), handover time (**not Friday evening**), and coverage across time zones if you have them.
- **An escalation policy** — notify the primary; if unacknowledged after N minutes, notify the secondary; then the manager. **The timeout is the important parameter** — long enough that someone can wake up and acknowledge, short enough that an unresponsive primary doesn't delay response.
- **Routing from Alertmanager** to the right policy by service or team label (O8.3).
- **Overrides** for holidays and illness.

The design considerations that matter:

- **Follow-the-sun beats overnight on-call** where you have the geography for it — it's the only structural fix for the human cost.
- **A secondary is not optional.** People miss pages: phone on silent, poor signal, deep sleep. A single point of contact for production incidents is a single point of failure.
- **Page volume must be sustainable.** More than a couple of pages per week per person, sustained, causes attrition and alert fatigue — and **tracking page volume per rotation is the metric that surfaces it** (O8.7).
- **Compensate on-call.** It's work.
- **The on-call must have the access and authority to act** — a rotation that can only escalate is a notification service.
- **Handover matters** — a short written handover of ongoing issues at rotation change prevents the new primary starting cold.

**O8.6 — An alert that links to a runbook and includes context**

```yaml
annotations:
  summary: >-
    {{ $labels.service }} in {{ $labels.cluster }} is returning
    {{ $value | humanizePercentage }} errors (SLO: 99.9%)
  description: >-
    Error rate has exceeded the fast-burn threshold for 5 minutes.
    Affected endpoints: check the dashboard breakdown.
    Recent deploys: see the annotations overlay.
  runbook_url: "https://runbooks.acme.io/payments/high-error-rate"
  dashboard_url: "https://grafana.acme.io/d/payments?var-service={{ $labels.service }}&from=now-1h"
  logs_url: "https://logs.acme.io/explore?q=service:{{ $labels.service }}+status:5xx"
  trace_url: "https://traces.acme.io/search?service={{ $labels.service }}&status=error"
```

**What a good alert contains:**

- **What is broken, in user-impact terms**, not "metric X exceeded Y". The reader is half-asleep.
- **The current value and the threshold**, so severity is immediately apparent.
- **Which service, cluster, environment, and tenant** — from labels.
- **A runbook link** with actual diagnostic steps (T4).
- **A dashboard link, pre-filtered to the affected service and time range.** The `&from=now-1h` detail matters — landing on a default 6-hour view wastes the responder's first minute.
- **Links to logs and traces**, pre-filtered (O1.7).

**Why it matters**: the alert is the entry point to an investigation conducted under time pressure by someone who may not own the service. **Every second spent working out what the alert means and where to look is response time.** An alert saying `HighErrorRate firing` with no links costs minutes per incident, multiplied by every incident.

The runbook standard: **it must contain diagnostic steps and decision points, not a description of the alert.** "Check X; if A then do B; if C then escalate to team D." A runbook that only restates what the alert already said is what causes people to stop opening runbooks.

**O8.7 — Auditing alert volume and retiring alerts**

The measurements to take:

- **Alerts fired per week, by rule.** The top talkers are usually a handful of rules generating most of the volume.
- **Actioned vs auto-resolved.** An alert that consistently resolves itself before anyone looks is not an alert.
- **Pages per rotation per person**, tracked over time as a health metric.
- **Time to acknowledge** — rising times indicate fatigue.
- **Alerts that fired during real incidents vs alerts that were the first signal.** The ones that never lead detection are candidates for demotion.
- **Long-lived silences** (O8.3) — a silence older than a few weeks is an alert that should be deleted or fixed.

The retirement criteria — an alert should be deleted or downgraded if:

- **It has never resulted in action.** This is the primary test.
- **It always fires alongside a more meaningful alert** — inhibit or delete (O8.3).
- **It's a cause alert where a symptom alert already covers the impact** (T7.3).
- **It's permanently silenced.**
- **Nobody knows what it means or who owns it.**

**Why this needs to be a deliberate, recurring exercise**: alert rules accumulate. Every incident adds one; almost nothing removes them. **The endpoint is a pager nobody reads, at which point your alerting provides negative value** — it costs attention and creates false assurance. A quarterly review with the on-call rotation, asking "which of these woke you up for nothing", is the practical mechanism.

The framing to give: **alert count is not a measure of coverage; actioned alerts per incident is.** Twenty alerts that all fire together during one incident is one alert's worth of information and twenty interruptions (O16.7).

---

## O9. Performance: CPU

**O9.1 — User, system, iowait, steal, idle**

From `top`, `vmstat`, or `/proc/stat`:

- **`us` (user)** — executing application code in user space. **High user time is normal for a busy application** and means the work is computational.
- **`sy` (system)** — executing kernel code on the process's behalf: syscalls, network stack, filesystem. **High system time suggests syscall-heavy behaviour** — excessive small I/O, lots of context switching, heavy network traffic. Worth investigating because it's often fixable by batching.
- **`wa` (iowait)** — the CPU was idle *and* there was at least one outstanding disk I/O. **Not "time spent waiting for I/O"** — it's idle time attributed to pending I/O, so it's a hint that I/O may be the constraint, not proof. **High iowait with low utilisation means the CPU has nothing to do because everything is blocked on disk** (O11.3).
- **`st` (steal)** — time the hypervisor gave to another guest. **You wanted CPU and didn't get it** (O9.3).
- **`id` (idle)** — genuinely nothing to do.
- **`ni`** (niced user), **`hi`/`si`** (hardware/software interrupts — high `si` can indicate network interrupt load), **`gu`** (guest).

The diagnostic value: **the split tells you what kind of problem you have.** High user → the application is computing (profile it, O13.1). High system → syscall overhead (batch, check for pathological I/O patterns). High iowait → storage (O11). High steal → the host is oversubscribed (O9.3). All low with slow application → not CPU-bound at all; it's blocking on something (O9.8, O11.9).

**O9.2 — Run queue length and context switch rate**

```bash
vmstat 1
# r  b   swpd   free   buff  cache   si  so   bi   bo   in    cs  us sy id wa st
```

- **`r`** — processes runnable or running. **This is CPU saturation** (O2.10). Compare against core count: `r` consistently above the number of cores means processes are queueing for CPU. **This is the metric utilisation can't give you** — a CPU at 100% with `r`=2 and one with `r`=50 are entirely different situations, and only the run queue distinguishes them.
- **Load average** is a related but different measure — on Linux it includes uninterruptible sleep (D state, usually disk I/O), so a high load average with low CPU utilisation frequently means I/O blocking, not CPU pressure. That's a genuinely useful distinction and commonly misread.
- **`cs` (context switches/sec)** — high rates mean the CPU is spending time switching rather than working. Causes: too many runnable threads, lock contention (O9.8), frequent short I/O, aggressive timer usage. Tens of thousands per second per core warrants investigation.
- **`in` (interrupts/sec)** — high values often mean network or storage interrupt load.

The interpretation: **run queue is the saturation signal; context switches are an efficiency signal.** A system with `r` at 2× cores is under-provisioned. A system with normal `r` but enormous `cs` is thrashing between threads, which usually means too much concurrency for the work (O12.7) or contention.

`pressure stall information` (`/proc/pressure/cpu`) is the modern, better metric — it directly reports the time tasks were stalled waiting for CPU, and it's worth naming as the more precise alternative.

**O9.3 — CPU steal**

Steal time is time the vCPU was ready to run but the hypervisor scheduled another guest instead. **The workload wanted CPU and the physical host didn't give it any.**

Where it comes from: **an oversubscribed host** — the hypervisor has allocated more vCPUs across guests than physical cores, and under contention someone waits. Also **burstable instance types** exhausting credits (A4.2), where the throttling appears as steal.

Why it matters: **your application is slow and every metric inside the guest looks fine.** CPU utilisation is moderate, the run queue is short, and the work is taking longer than it should. Steal is the only signal, and it's frequently not on dashboards — which makes it a classic "we spent three hours before someone ran `top`" problem.

The responses: **on shared/burstable instances, move to a dedicated or larger type** — this is the T-family trap (A4.2) manifesting as steal. **On dedicated instances, sustained steal means the provider's host is oversubscribed**, which for AWS is unusual on non-burstable types and worth raising. **On on-prem virtualisation, reduce overcommit.**

The monitoring point: **alert on sustained steal above a few percent.** It's cheap to collect (node_exporter has it) and it explains a class of otherwise-baffling slowness.

**O9.4 — cgroup CPU quota and throttling despite idle host CPU**

The mechanism: cgroups v2 enforces a CPU limit via `cpu.max` — a quota of microseconds per period (default 100ms). **When a container exhausts its quota within a period, it is stopped until the next period begins.**

**The symptom is distinctive and confusing**: the application is slow, its p99 latency is bad, **container CPU utilisation looks low**, and **the host has idle CPU**. Nothing on any dashboard suggests a CPU problem.

**Why utilisation looks low**: utilisation is averaged over the reporting interval. A container that uses its full quota in the first 30ms of each 100ms period and is throttled for the remaining 70ms averages 30% utilisation — while being stopped 70% of the time.

**Why it hurts latency disproportionately** (K6.2): the throttling is bursty. A request needing a brief burst of parallel work is paused mid-flight for tens of milliseconds. **Multi-threaded runtimes make it worse** — 4 threads consume the quota 4× faster, so the throttled fraction of each period grows.

The diagnosis: **`container_cpu_cfs_throttled_seconds_total` and `container_cpu_cfs_throttled_periods_total`** in Prometheus, or `cpu.stat` in the cgroup filesystem (`nr_throttled`, `throttled_time`). **These are not on default dashboards and should be**, because throttling is common and invisible otherwise.

The fixes: **raise or remove the CPU limit** (K6.2 discusses the argument for omitting CPU limits entirely); **reduce thread/worker count** so the runtime doesn't burn quota in parallel; **set the runtime's parallelism from the quota** rather than from host core count — a JVM or Go runtime seeing 64 host cores while limited to 2 CPUs behaves badly, and container-awareness settings (`GOMAXPROCS`, `-XX:ActiveProcessorCount`) are the fix (O10.6).

**O9.5 — Diagnosing a process consuming CPU, down to the thread**

```bash
top -H -p <pid>              # per-thread view
ps -L -p <pid> -o tid,pcpu,comm      # threads with CPU and name
pidstat -t -p <pid> 1        # per-thread over time

# what is it actually doing
perf top -p <pid>
perf record -F 99 -p <pid> -g -- sleep 30 && perf report
strace -c -p <pid>           # syscall summary — for system-time-heavy processes
```

For the JVM specifically, the classic sequence:

```bash
top -H -p <pid>                          # find the hot TID, e.g. 12345
printf '%x\n' 12345                      # convert to hex: 3039
jstack <pid> | grep -A 30 'nid=0x3039'   # find that thread in the dump
```

That thread-ID-to-hex-to-jstack path is a well-known and genuinely useful trick, and knowing it signals hands-on experience.

The method: **narrow from process → thread → stack.** The thread name alone often identifies it (a GC thread, a worker pool thread, a specific scheduler). Then a profiler or thread dump gives the stack, and a flame graph aggregates it into where the time actually goes (O13.1, O13.2).

The interpretation: **is it user or system time** (O9.1)? User-heavy → profile the code. System-heavy → `strace -c` for the syscall distribution. **Is one thread hot or all of them?** One hot thread in a multi-threaded app suggests a serialisation point or a single-threaded bottleneck (O9.6); all threads busy suggests genuine CPU-bound work.

**O9.6 — Why a multithreaded app doesn't scale linearly with cores**

The reasons, roughly in order of how often they bind:

- **Lock contention.** Threads serialise on shared state. Adding threads increases contention, so throughput can *decrease* past a point. **The signature is high context switches and threads in a blocked state, with CPU utilisation well below capacity** (O9.8).
- **Amdahl's Law** (O14.5) — the serial fraction bounds the speedup regardless of core count.
- **Shared resource saturation** — all threads hitting one database, one connection pool, one disk. The bottleneck moved (O12.7).
- **Cache contention and false sharing** — threads on different cores writing to the same cache line force constant invalidation. Invisible in every normal metric and can be dramatic (O9.7).
- **Memory bandwidth** — cores share it, so a memory-bound workload saturates bandwidth before it saturates cores.
- **NUMA effects** — a thread accessing memory attached to another socket pays a latency penalty (O9.7).
- **GC** — a stop-the-world collector serialises everything periodically, and GC cost often rises with heap and thread count (O10.5).
- **Context switching overhead** when thread count far exceeds cores (O9.2).
- **cgroup quota** — the container is limited regardless of host cores (O9.4).

The diagnostic approach: **measure throughput at increasing concurrency and find where it stops improving** (O13.8). The shape tells you a lot — plateau suggests a saturated shared resource; *decline* past a peak strongly suggests contention or context-switch overhead, which is a distinctive and useful signature.

**O9.7 — Cache locality and NUMA at a working level**

**Cache locality**: CPUs have a hierarchy (L1 ~1ns, L2 ~4ns, L3 ~20ns, main memory ~100ns). **A cache miss costs roughly 100× an L1 hit**, so data layout dominates performance for memory-intensive work. Sequential access over an array is fast because prefetching works; chasing pointers through a linked list defeats it. This is why array-of-structs vs struct-of-arrays matters, and why an algorithm with worse big-O can be faster in practice.

**False sharing**: two threads writing to different variables that share a **cache line** (64 bytes) force the line to bounce between cores. Each write invalidates the other core's copy. **Throughput collapses with no visible cause** — CPU is busy, no locks are held, and nothing in a profiler obviously points at it. The fix is padding to separate hot variables onto different lines. Worth knowing because it's genuinely baffling when met.

**NUMA**: on multi-socket systems, memory is attached to specific sockets. **Local access is meaningfully faster than remote.** A process whose threads run on socket 0 but whose memory was allocated on socket 1 pays a penalty on every access.

The working-level tools and actions:

```bash
numactl --hardware              # topology and per-node memory
numastat -p <pid>               # local vs remote allocations for a process
lscpu                           # NUMA node to CPU mapping
perf stat -e cache-misses,cache-references,LLC-load-misses -p <pid>
numactl --cpunodebind=0 --membind=0 ./app   # pin to one node
```

The practical guidance: **for most application work, this is below the level you need to operate at.** It matters for databases, JVMs with large heaps, high-throughput network processing, and anything latency-critical — and the usual remedy is **pinning** (CPU and memory affinity) or **sizing instances to fit within one NUMA node**, which is the simpler answer and often available in cloud sizing.

**O9.8 — CPU-bound vs lock-contended**

The distinction, and it's one of the more valuable diagnostic discriminations available:

| | CPU-bound | Lock-contended |
|---|---|---|
| CPU utilisation | High, near capacity | **Moderate or low** |
| Adding cores | Helps | **Doesn't help, may hurt** |
| Adding threads | Helps to core count | **Makes it worse** |
| Thread states | Running | Blocked/waiting |
| Context switches | Moderate | **High** |
| Throughput vs concurrency | Plateaus | **Peaks then declines** |

**The tell is high latency with unsaturated CPU.** If the application is slow and the CPU is at 40%, it is not CPU-bound — it's waiting for something, and lock contention is one of the main candidates (the others being I/O, O11.3, and downstream calls, O11.9).

The diagnosis:

- **Thread dumps** (JVM `jstack`, several samples seconds apart) — repeated dumps showing many threads blocked on the same monitor is definitive, and it names the lock.
- **`perf` with lock events**, or off-CPU profiling — which shows where threads spend time *not* running, and is the direct tool for this. Off-CPU flame graphs are the specialist answer (O13.2).
- **Async-profiler's lock mode** for JVM, `pprof` block/mutex profiles for Go.
- **Rising context switches** with flat throughput (O9.2).
- **The concurrency sweep** — throughput peaking and then declining as you add threads is the classic contention signature (O13.8).

The fixes: reduce critical section size; use finer-grained or lock-free structures; shard the contended resource; use read-write locks where reads dominate; or **remove the sharing entirely** — per-thread state aggregated periodically is usually the biggest win.

---

## O10. Performance: memory

**O10.1 — RSS, virtual size, shared memory, working set**

- **VSZ (virtual size)** — the total address space mapped, including memory never touched, memory-mapped files, and shared libraries. **Frequently enormous and largely meaningless** — a JVM with a 4GB heap may show 20GB VSZ. Alarm at VSZ is almost always a false alarm.
- **RSS (resident set size)** — physical memory currently in RAM for this process. **Includes shared pages, counted in full for every process sharing them** — so summing RSS across processes double-counts, and that's why "the sum of RSS exceeds total memory" happens.
- **Shared memory** — pages shared between processes (libraries, shared memory segments, copy-on-write pages after fork).
- **PSS (proportional set size)** — RSS with shared pages divided by the number of sharers. **The honest per-process figure**, and what you want when attributing memory.
- **Working set** — pages actively in use. **This is what Kubernetes uses for eviction decisions** (`container_memory_working_set_bytes`), and it's roughly RSS minus inactive file-backed pages that could be reclaimed.

Why the distinctions matter:

- **Alerting on RSS produces false positives** for processes with large shared mappings.
- **`container_memory_usage_bytes` includes page cache** and is not what triggers OOM (O10.2); **`container_memory_working_set_bytes` is the one to alert on** in Kubernetes. Using the wrong one is a very common dashboard error.
- **The JVM's RSS exceeds its heap** — metaspace, thread stacks, code cache, direct buffers, and native allocations all count. Sizing a container limit from heap size alone guarantees an OOM kill (O10.6).

**O10.2 — Page cache and why "used memory" looks alarming**

Linux uses free memory for **page cache** — caching file contents to avoid disk reads. **This is desirable behaviour**: unused RAM is wasted RAM.

The confusion: `free -m` traditionally showed most memory as "used", because cache counted as used. **Modern `free` has an `available` column, and that's the number that matters** — it's an estimate of how much memory a new application could get, accounting for reclaimable cache.

```bash
free -h
#               total   used   free   shared  buff/cache   available
# Mem:           31Gi   8.2Gi  1.1Gi   210Mi        22Gi        22Gi
```

**Free is 1.1GB and available is 22GB** — the system is healthy, and someone alarmed by "free" is reading the wrong column.

The consequences:

- **Alert on `available`, not `free`.** Alerting on free memory produces constant false alarms on a healthy system.
- **Page cache is reclaimed under pressure** automatically, without swapping.
- **In a container, page cache counts toward the cgroup memory limit** — which is why heavy file I/O can trigger an OOM kill in a process whose heap is fine (K6.3). The kernel will reclaim cache before killing, but the accounting surprises people, and `container_memory_usage_bytes` including cache is exactly why working set is the better metric (O10.1).
- **Dropping caches** (`echo 3 > /proc/sys/vm/drop_caches`) is a diagnostic tool, not a fix, and it will make things slower.

**O10.3 — Swapping vs swap thrashing**

- **Swap use** — some pages have been written to swap. **Not necessarily a problem**: the kernel proactively swaps out long-idle pages to free RAM for cache. A few hundred MB of swap used on a long-running system is normal and harmless.
- **Swap thrashing** — pages are being read from and written to swap **continuously** because the active working set exceeds physical memory. **This is catastrophic**: memory access latency goes from ~100ns to ~100µs (SSD) or ~10ms (spinning disk), so the system becomes hundreds or thousands of times slower and appears hung.

**The metric that distinguishes them is swap I/O rate, not swap used.** `vmstat`'s `si`/`so` columns (swap in/out, pages per second) — **sustained non-zero values are thrashing; a static amount of swap used with zero I/O is fine.** Alerting on swap *used* is a common false-positive generator; alerting on swap *rate* is correct.

The operational positions:

- **Databases and latency-sensitive services usually disable swap** or set `vm.swappiness=1` — a slow system is often worse than a killed process, and predictable failure beats unpredictable slowness.
- **Kubernetes historically required swap disabled** because it breaks the memory accounting the scheduler and eviction logic depend on. Swap support has been added in recent versions but remains a deliberate choice, not a default.
- **Thrashing is worse than an OOM kill** in most production contexts: an OOM kill is fast, visible, and recovers via a restart; thrashing is a slow, hard-to-diagnose degradation that takes the node's other workloads with it.

**O10.4 — Diagnosing a leak vs a growing cache**

Both show memory growing over time. The distinctions:

| | Leak | Growing cache |
|---|---|---|
| Growth shape | Unbounded, roughly linear with work done | Approaches a bound and plateaus |
| Under memory pressure | Keeps growing until OOM | Evicts and stabilises |
| After GC (managed runtimes) | Live set grows each cycle | Live set stable, collections reclaim |
| Correlation | With uptime and cumulative requests | With working-set size, then flat |
| Restart | Resets, then climbs again identically | Resets, then climbs to the same plateau |

The diagnostic method:

1. **Plot memory over a long window** — the sawtooth-with-rising-floor pattern is the leak signature: each GC reclaims less than the last (O10.5).
2. **Check whether it plateaus.** Give it time and load. A cache with a bound will stop; a leak won't.
3. **Take heap dumps at intervals and diff them** — `jmap -dump` for the JVM analysed in Eclipse MAT, `pprof` heap profiles for Go, `tracemalloc` for Python. **The diff shows which object types grew**, which is usually the answer immediately.
4. **Look for the classic causes**: an unbounded collection used as a cache with no eviction, listeners or callbacks registered and never removed, thread-locals in a pooled thread, connection or resource leaks, and — in the JVM — classloader leaks on redeploy.
5. **Check native memory too** if RSS grows while heap doesn't (O10.1) — direct byte buffers, JNI, or a native library.

The subtlety worth naming: **an unbounded cache is a leak.** The distinction is about whether there's a bound, not about intent. "It's a cache" is not a defence if nothing evicts.

**O10.5 — GC and how pauses appear as latency spikes**

Garbage collection reclaims unreachable objects. Most collectors have **stop-the-world phases** where application threads are paused.

**How it appears in observability**: as **latency spikes with no corresponding change in load or downstream latency**. The request wasn't doing anything — it was paused. In a trace this shows as **an unexplained gap** (O5.5) with no span accounting for the time, which is one of the most useful things a trace reveals about GC.

**Why it disproportionately affects the tail** (O12.3): a 200ms pause affects every request in flight at that moment. If a pause happens every 30 seconds and requests take 20ms, a small percentage of requests are hit — landing precisely in your p99 and p99.9. **Mean latency barely moves; the tail moves a lot**, which is exactly the pattern O2.3 warns about.

The amplification (O12.4): with a fan-out of 20 backend calls, the chance that *at least one* hits a GC pause is much higher than the per-call probability — so tail latency at the edge is dominated by GC in the backends.

The management:

- **Choose the collector for the goal** — G1 (balanced, default), ZGC and Shenandoah (sub-millisecond pauses, higher throughput cost), Parallel (throughput, longer pauses). **For latency-sensitive services, a low-pause collector is often the single biggest p99 improvement available.**
- **Size the heap appropriately** — too small means frequent GC; too large means longer pauses with some collectors and more time between them.
- **Reduce allocation rate** — the most effective structural fix. Fewer objects means less to collect.
- **Monitor GC pause time and frequency as first-class metrics**, and correlate them with latency spikes.

**O10.6 — Tuning heap sensibly, with container awareness**

```bash
# JVM: size from the container limit, not the host
-XX:MaxRAMPercentage=75.0
-XX:InitialRAMPercentage=50.0
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp
```

**Container awareness is the crux of this item.** Historically, a JVM in a container read the *host's* memory and cores and sized its heap accordingly — so a JVM in a 512MB container on a 64GB host would size a ~16GB heap and be OOM-killed almost immediately (K6.3). Modern JVMs (8u191+, 11+) respect cgroup limits by default, and **`MaxRAMPercentage` is the correct way to size** — never a fixed `-Xmx` that must be manually kept in sync with the container limit.

**The headroom calculation**, which is the part people get wrong: **the container limit must exceed the heap by a significant margin**, because the JVM's total footprint includes metaspace, thread stacks (~1MB × thread count), code cache, GC structures, direct byte buffers, and native allocations. **75% for heap is a common starting point**; a container limit equal to `-Xmx` guarantees an OOM kill (O10.1).

The same applies to other runtimes: **`GOMAXPROCS`** should be set from the CPU limit (automatic in Go 1.25+, and `automaxprocs` before that) or the Go scheduler over-parallelises and burns cgroup quota (O9.4); **Node's `--max-old-space-size`**; **Python worker counts** from the CPU limit.

The method: **measure, don't guess** (O10.9). Run under realistic load, observe the live set after GC and the total RSS, and size from that with headroom.

**O10.7 — Memory fragmentation**

Fragmentation is memory that is free but unusable because it's not contiguous in the needed size.

- **External fragmentation** — many small free blocks, but no single block large enough for a large allocation. The allocation fails or triggers reclaim despite plenty of free memory in total.
- **Internal fragmentation** — allocators round up to size classes, so a 33-byte allocation may consume a 64-byte slot. The waste is small per allocation and significant in aggregate for allocation-heavy workloads.

Where it manifests in practice:

- **Long-running processes with varied allocation sizes** — RSS grows and doesn't shrink even after objects are freed, because the allocator holds the arenas. **glibc malloc is notably reluctant to return memory to the OS**, which is why a process's RSS stays high after a load spike. Switching to jemalloc or tcalloc often reduces this materially, and it's a real, under-used fix.
- **Redis** reports `mem_fragmentation_ratio` explicitly, and high values are a known operational concern with a defragmentation setting.
- **Kernel-level** — huge page allocation failing despite free memory, visible in `/proc/buddyinfo`.
- **Compacting garbage collectors avoid it by design**, which is one of their advantages — the JVM heap doesn't fragment the way a native allocator does, though native memory outside the heap still can.

The practical significance: **it's usually a second-order concern**, and it explains the specific mystery of "the process freed the memory and RSS didn't drop." Recognising that pattern and knowing the allocator is the reason — rather than chasing a leak (O10.4) — is the value here.

**O10.8 — The OOM killer's selection logic and reading the evidence**

**Two distinct mechanisms** and confusing them is the common error (K6.11):

- **cgroup OOM** — a container exceeded its memory limit. The kernel kills a process **within that cgroup**. Contained, and the usual case in Kubernetes.
- **System OOM** — the whole host is out of memory. The kernel must choose a victim from all processes, and it may kill something unrelated to the cause.

**Selection logic (system OOM)**: each process gets an `oom_score` derived primarily from its memory footprint (so the biggest consumer is the usual victim), adjusted by `oom_score_adj` (-1000 to +1000, where -1000 makes a process immune). **Kubernetes sets `oom_score_adj` based on QoS class** — BestEffort pods get a high score (killed first), Guaranteed pods a very low one (K6.4). That's the mechanism behind the QoS eviction ordering.

**Reading the evidence**:

```bash
dmesg -T | grep -i -E 'killed process|out of memory'
journalctl -k | grep -i oom
cat /sys/fs/cgroup/memory.events        # cgroup v2: oom_kill counter
kubectl describe pod <pod>              # Last State: Terminated, Reason: OOMKilled, Exit Code 137
```

The kernel log entry contains the invoking process, the memory state at the time, a table of candidate processes with their scores and RSS, and the chosen victim — **that table is genuinely useful**, because it shows what else was consuming memory, which frequently identifies the real culprit when the victim was a bystander.

The interpretation: **exit code 137 (128+9, SIGKILL) with reason OOMKilled** is the container-level signature. **A pod `Evicted` with a memory-pressure message is a different thing** — the kubelet chose to evict based on node pressure, which is graceful and rescheduled, versus the kernel killing a process abruptly (K6.11).

**O10.9 — Setting a container memory limit from measurement**

The method:

1. **Run under realistic peak load** for long enough to reach steady state — including any warm-up, cache filling, and at least one full GC cycle.
2. **Measure `container_memory_working_set_bytes`** (O10.1), not `usage_bytes` (which includes reclaimable cache) and not heap alone.
3. **Take the p99 over the observation window**, not the mean — you're sizing for the worst case, since exceeding the limit is fatal (K6.3).
4. **Add headroom** — typically 20–30% over observed peak.
5. **Set requests equal to limits for anything important** (Guaranteed QoS, K6.4), so it's last to be evicted and scheduling reflects reality.
6. **Re-measure after changes** to the workload or the runtime.

**Why headroom is necessary and how much**, which is the substance:

- **Memory over-limit is fatal and immediate**, unlike CPU which merely throttles (O9.4). The asymmetry justifies conservatism.
- **Traffic varies**, and a burst that increases concurrency increases memory proportionally.
- **GC is not instantaneous** — a managed runtime's memory oscillates, and the limit must accommodate the peak of the sawtooth, not the trough.
- **Page cache counts** toward the cgroup limit (O10.2), so file I/O consumes headroom.
- **Native memory outside the heap** grows with thread count and connections (O10.1).

The counterweight: **excessive headroom is directly wasted money** at fleet scale, and it worsens bin-packing (K6.5). The judgement is that **memory headroom should be more generous than CPU headroom** because the failure modes differ — a CPU-throttled container is slow, a memory-exceeded container is dead.

---

## O11. Performance: IO, storage & network

**O11.1 — IOPS, throughput, and latency as separate constraints**

- **IOPS** — operations per second. Bound by the device's ability to service requests.
- **Throughput** — bytes per second. IOPS × average I/O size.
- **Latency** — time for one operation to complete.

**They are separate constraints and you can be limited by any one of them**, which is the point of the item:

- **Small random reads** — you hit the **IOPS** limit long before the throughput limit. A 4KB random read workload at 3,000 IOPS is only 12 MB/s, nowhere near the volume's bandwidth.
- **Large sequential reads** — you hit the **throughput** limit at low IOPS. 250 MB/s at 1MB per operation is 250 IOPS.
- **Latency** is independent of both — a device can be well within its IOPS and throughput limits and still have poor per-operation latency, typically because of queueing (O11.2).

Why it matters practically: **provisioning on the wrong dimension is a common and expensive mistake.** On EBS gp3 you provision IOPS and throughput separately (A6.8) — a database doing small random I/O needs IOPS; an analytics job doing large sequential scans needs throughput; buying the wrong one leaves the workload slow and the money spent.

The diagnostic: **`iostat -x 1`** gives `r/s`, `w/s` (IOPS), `rkB/s`, `wkB/s` (throughput), `r_await`, `w_await` (latency), and `aqu-sz` (queue depth). **Compare each against the device's rated limit** — the one you're near is your constraint.

**O11.2 — Queue depth and its relationship to latency**

**Queue depth** is the number of I/O requests outstanding at the device.

The relationship is the fundamental queueing result (O12.1): **as utilisation approaches capacity, queue depth grows, and latency grows with it — non-linearly.** A device servicing requests as fast as they arrive has a queue near zero and latency equal to service time. As arrival rate approaches service rate, the queue grows and each request waits behind the queue.

Consequences worth stating:

- **Latency = service time + queue wait.** At low utilisation, service time dominates. At high utilisation, queue wait dominates and can be many multiples of service time.
- **`await` in `iostat` includes queue time**; **`svctm`** (where reported) is the service time alone. A high `await` with low `svctm` means the device is fine and the queue is deep — **you're saturated, not slow**.
- **Some queue depth is good** — it lets the device reorder and coalesce operations, which is why NVMe wants deep queues for maximum throughput. **Zero queue depth means you're not extracting the device's parallelism**, so a single-threaded synchronous I/O workload underutilises a fast SSD badly.
- **Too deep and latency suffers** without throughput gain — you've saturated it.

The practical read: **`aqu-sz` consistently above a small number with rising `await` is I/O saturation** (O2.10's saturation signal for disk). And **the fix is either less I/O, faster storage, or more parallelism spread across devices** — not deeper queues.

**O11.3 — Diagnosing IO saturation and finding the responsible process**

```bash
iostat -x 1                 # per-device: %util, await, aqu-sz, r/s, w/s
iotop -oPa                  # per-process I/O, accumulated
pidstat -d 1                # per-process read/write rates
biolatency / biosnoop       # BCC/bpftrace: I/O latency distribution and per-I/O detail
cat /proc/<pid>/io          # cumulative bytes for one process
```

The method:

1. **Confirm it's I/O** — high `iowait` (O9.1), high `await`, deep queue (O11.2), and application latency correlating with them. **Note `%util` is misleading on modern SSDs and NVMe** — it measures the fraction of time at least one request was outstanding, and a device capable of high parallelism can show 100% util while far from saturated. **Use `await` and queue depth, not `%util`.** That's a genuinely important correction and a good detail to offer.
2. **Identify the device** — which volume is saturated.
3. **Identify the process** — `iotop` or `pidstat -d`. In a container context, the process is in a container, so map it back (K9.1).
4. **Identify the pattern** — random or sequential (O11.4)? Reads or writes? Large or small? `biosnoop` shows individual operations with size and latency.
5. **Identify why** — a missing database index causing table scans, a log file being written synchronously, a backup job, a compaction, an unexpected swap (O10.3), or page cache pressure forcing re-reads.

The distinction that matters: **is the workload legitimately I/O-heavy, or is it doing unnecessary I/O?** The second is far more common and far cheaper to fix — an unindexed query, a missing cache, synchronous writes that could be buffered, or logging at debug level (O4.7).

**O11.4 — Random vs sequential, and why it matters for cost**

- **Sequential** — contiguous blocks. The device reads ahead, and on spinning disks the head doesn't move. **Throughput-bound.**
- **Random** — scattered blocks. Each operation is independent. **IOPS-bound.**

The performance gap: on spinning disks it's enormous — seek time dominates, so random I/O can be 100× slower. **On SSDs the gap is much smaller but still real**, because random I/O can't benefit from readahead and has more per-operation overhead.

**Why it matters for cost:**

- **You provision differently.** A random workload needs provisioned IOPS (io2, or gp3 with high IOPS); a sequential workload needs throughput. **Provisioning IOPS for a sequential workload wastes money; provisioning throughput for a random one leaves it slow** (A6.8).
- **st1/sc1 HDD volumes are throughput-optimised and terrible for random I/O** — cheap per GB and a poor fit for a database. Choosing them on price alone is a classic mistake.
- **Cache effectiveness differs.** Sequential access benefits from readahead; random access needs the working set to fit in cache to help at all.

The application-level connection worth drawing: **database access patterns determine this.** An index scan is closer to random; a full table scan is sequential. **Adding an index converts a sequential scan into random lookups**, which is faster for selective queries and *slower* for queries touching much of the table — which is why the planner chooses between them, and why "add an index" isn't universally right (DB domain).

**O11.5 — Burst credits and the cliff**

Several cloud storage and instance types provide a baseline performance level plus a burst allowance accrued as credits when running below baseline.

**Where it appears**: EBS gp2 (IOPS credits, A6.8), EBS `st1`/`sc1` (throughput credits), **EFS bursting mode** (throughput credits proportional to stored data, A6.9), and **T-family EC2 instances** (CPU credits, A4.2).

**The cliff is the characteristic failure**: the workload performs well for hours or days while credits last, then **abruptly drops to baseline** — which can be a small fraction of what it was doing. The symptom is *"it was fine and then it suddenly became very slow, with no deployment and no traffic change."*

Why it's so confusing when met: **every instantaneous metric looks normal.** The device isn't erroring, utilisation may even drop, and the only evidence is the credit balance metric — which nobody has on a dashboard until they've been caught once.

The management:

- **Monitor the credit balance** (`BurstBalance` for EBS, `CPUCreditBalance` for T instances, `BurstCreditBalance` for EFS) **and alert before it hits zero.** This is the entire mitigation and it's a five-minute dashboard change.
- **Size for the sustained requirement, not the burst** — if the baseline can't carry your normal load, credits are hiding an under-provisioned system.
- **Move to a non-bursting type** for anything with a sustained baseline: gp3 (fixed IOPS independent of size), EFS elastic throughput, non-T instance families.

The general lesson: **any resource with a credit model has a cliff, and a system that only works because of burst credits is under-provisioned with a delayed failure.**

**O11.6 — Filesystem caching and the durability implication of buffered writes**

A `write()` normally returns once the data is in the **page cache** (O10.2), not when it's on disk. The kernel flushes dirty pages later. **This is what makes writes fast** — you're writing to RAM.

**The durability implication**: between the `write()` returning and the flush completing, **the data exists only in volatile memory.** A power loss or kernel panic loses it. The application believes the write succeeded.

The controls:

- **`fsync()` / `fdatasync()`** — block until the data is durably on the device. **This is what databases call after every commit**, and it's why commit latency is bounded by storage latency rather than memory latency.
- **`O_DIRECT`** — bypass the page cache entirely. Used by databases that manage their own buffer pool and don't want double caching.
- **Write barriers and the device's own write cache** — a device with a volatile write cache can acknowledge an `fsync` before the data is truly persistent unless the cache is battery-backed or barriers are honoured. **This is why "we lost data despite fsync" incidents happen**, and it's a genuinely deep failure mode worth knowing about.

The tuning knobs: `vm.dirty_ratio` and `vm.dirty_background_ratio` control how much dirty data accumulates before flushing. **Large values give better throughput and a bigger loss window, and can cause latency spikes when a large flush occurs** — a real cause of periodic stalls under write-heavy load.

The design point: **this is the durability/performance tradeoff in its most fundamental form.** A database that fsyncs every commit is slower and safe; one that doesn't is faster and loses recent transactions on power loss. Knowing which your system does — and that "the write returned successfully" is not the same as "the data is safe" — is the substance.

**O11.7 — Bandwidth vs latency vs packet loss**

Three distinct network problems with different symptoms and different fixes (N1):

- **Bandwidth (throughput) limitation** — the link is saturated. Symptom: transfers are slow but consistent; latency rises under load due to queueing (bufferbloat). Fix: more capacity, compression, or less data.
- **Latency (RTT)** — the round trip takes too long. Symptom: **chatty protocols are slow while bulk transfer is fine.** An application making 100 sequential round trips at 50ms RTT takes 5 seconds regardless of bandwidth. **Fix: fewer round trips** — batching, pipelining, connection reuse, moving compute closer. **You cannot fix latency with bandwidth**, which is the key insight (O11.8).
- **Packet loss** — packets dropped. Symptom: **wildly variable throughput and stalls**, because TCP interprets loss as congestion and backs off dramatically. **Even 1% loss can halve effective throughput** over a high-RTT path, which is disproportionate and surprising. Fix: find the drop point (congested link, faulty hardware, an overloaded middlebox, or an undersized queue).

The diagnostic distinctions:

```bash
ping -c 100 host              # RTT and loss
mtr host                      # per-hop loss and latency (N3)
iperf3 -c host                # achievable bandwidth
ss -ti                        # per-socket: RTT, retransmits, congestion window
netstat -s | grep -i retrans  # retransmission counters
```

**Retransmissions are the loss signal** and are visible per-socket in `ss -ti` — a high retransmit count with normal bandwidth utilisation points at loss rather than saturation, which is exactly the distinction people struggle to make.

**O11.8 — TCP window size and RTT bounding throughput**

**The bandwidth-delay product**: the maximum in-flight unacknowledged data is the receive window, so:

```
max throughput = window size / RTT
```

With a 64KB window and 100ms RTT: `65536 / 0.1 = 655 KB/s ≈ 5 Mbit/s` — **regardless of a 10 Gbit link.**

This is why:

- **A high-bandwidth, high-latency path ("long fat network") performs poorly** without tuning. Transatlantic transfers, cross-region replication (M9.8), and backup to a distant region all hit this.
- **Window scaling** (RFC 1323) exists — it allows windows beyond 64KB and is on by default in modern stacks, but can be broken by an old middlebox that strips the option, producing exactly this symptom on one path and not others.
- **Buffer tuning matters** for high-BDP paths: `net.ipv4.tcp_rmem`/`tcp_wmem` must allow a window large enough for the BDP.
- **Parallel streams work around it** — N connections each with their own window multiply throughput, which is why tools like `aria2`, S3 multipart upload, and `rclone --transfers` are dramatically faster than a single stream over a long path.
- **Slow start** means short connections never reach full throughput at all, which is why connection reuse matters so much (O12.8).

The practical framing: **for a distant endpoint, throughput is a latency problem, not a bandwidth problem.** Buying more bandwidth changes nothing; increasing window size or parallelism does. That inversion is what the item is testing.

**O11.9 — Diagnosing whether slowness is network or application**

The bisection approach, and this is the transferable method:

1. **Measure at both ends.** If the client sees 500ms and the server logs 20ms of processing, **480ms is somewhere in between** — network, queueing, connection setup, TLS, or DNS. If the server also reports 500ms, it's the application.
2. **Test the network path independently** — `ping` for RTT, `iperf3` for bandwidth, `mtr` for per-hop loss (O11.7). If they're clean, the network isn't the problem.
3. **Test the application independently** — call it from a client on the same host (`localhost`), removing the network entirely. If it's still slow, it's the application.
4. **Check the connection lifecycle** — `curl -w` breaks down DNS, connect, TLS, first byte, and total:

```bash
curl -w "dns:%{time_namelookup} conn:%{time_connect} tls:%{time_appconnect} ttfb:%{time_starttransfer} total:%{time_total}\n" -o /dev/null -s https://api.example.com
```

**This one command frequently answers the question outright** — a large `time_namelookup` is DNS, a large gap between `time_appconnect` and `time_starttransfer` is server processing, and a large `time_connect` is network or a backlogged listener.

5. **Use tracing** (O5.5) — a span for the outbound call versus the server's own span shows the difference directly, and that gap *is* the network plus queueing time.
6. **Check for queueing at the server** — a full accept queue or a saturated thread pool means the request waited before the application saw it, so application-side timing looks fine (O12.7).

The pattern-matching shortcuts: **slow for large payloads only** → bandwidth or MTU (N1.6); **slow for all requests uniformly** → RTT or a per-request overhead like TLS; **intermittently very slow** → packet loss and retransmission (O11.7), or GC (O10.5); **slow only under load** → queueing somewhere (O12.1).

---

## O12. Latency & throughput

**O12.1 — Utilisation and queueing delay**

The fundamental result from queueing theory: **as utilisation approaches 100%, queueing delay approaches infinity.** For a simple M/M/1 queue:

```
average wait ≈ service_time × ρ / (1 - ρ)     where ρ = utilisation
```

| Utilisation | Queue multiplier |
|---|---|
| 50% | 1× service time |
| 80% | 4× |
| 90% | 9× |
| 95% | 19× |
| 99% | 99× |

**At 50% utilisation a request waits about as long as it takes to serve. At 95% it waits nineteen times as long.** The resource is doing the same work per request; the waiting is all queueing.

Why this is the most important idea in performance engineering:

- **It explains why systems fall off a cliff** rather than degrading gracefully (O12.2).
- **It's the mathematical justification for headroom** (O14.2). Running at 90% utilisation is not "efficient" — it's operating in the region where latency is 9× worse and any variance makes it far worse.
- **It applies to every resource with a queue**: CPU (run queue, O9.2), disk (O11.2), connection pools, thread pools, network buffers, and the application's own request queue.
- **Variability makes it worse.** The formula assumes exponential arrivals; real traffic is burstier, so real queues are worse than the model at the same utilisation.

The practical target: **plan for 50–70% utilisation at peak** for latency-sensitive services. Higher is acceptable for throughput-oriented batch work where queueing delay doesn't matter.

**O12.2 — Why latency degrades non-linearly near saturation**

Directly from O12.1: the `ρ/(1-ρ)` term explodes as ρ → 1. **The system doesn't degrade proportionally — it degrades hyperbolically.**

What that means operationally, and this is the intuition to convey:

- **A 10% traffic increase can be harmless or catastrophic depending on where you were.** From 50% to 55% utilisation, latency barely moves. From 90% to 99%, it goes from 9× to 99× — the same 10% increase in absolute traffic, an eleven-fold difference in outcome.
- **This is why capacity problems appear suddenly.** Everything is fine, fine, fine, then a modest increase and the service is unusable. **There is no gradual warning in the latency signal** until you're already in the steep region — which is why saturation metrics are the leading indicator and latency is the lagging one (O2.10).
- **Recovery is also non-linear** — once the queue is deep, draining it takes time even after arrival rate drops, so the incident outlasts the cause (M10.10).
- **It compounds through a chain** — each saturated hop multiplies (O12.4).

The design responses: **maintain headroom** (O14.2); **shed load before saturation** rather than after (O15.3); **bound queues** so they fail fast rather than queueing unboundedly (O15.6); and **alert on saturation, not just latency**, because latency is the lagging indicator.

**O12.3 — Tail latency and why p99 matters more than p50**

**p50 is the median experience; p99 is the experience of 1 in 100 requests.** The tail matters more than the proportion suggests, for several reasons:

- **Users hit the tail more often than 1%.** A page making 20 backend calls, each with an independent 1% chance of being slow, has a **~18% chance that at least one is slow** — and the page is as slow as its slowest call (O12.4). So a p99 backend latency becomes a p82 user experience.
- **The tail is disproportionately your most valuable users** — those with the most data, the most items in their cart, the largest queries. Slowness correlates with account size.
- **The tail is where the failures are.** Timeouts, retries, and cascading failures start in the tail (O15.9).
- **The mean hides it entirely** (O2.3).

What causes the tail specifically: **GC pauses** (O10.5), **queueing at high utilisation** (O12.1), **cache misses** creating bimodal distributions (O7.5), **retries** adding a full extra round trip, **connection establishment** on a cold pool (O12.8), **noisy neighbours** and steal (O9.3), and **cgroup throttling** (O9.4).

The practical guidance: **set SLOs on the tail** (p99 or p99.9 depending on fan-out), **measure the tail with adequate histogram resolution** (O2.5), and **when optimising, check the whole distribution moved** rather than just the mean (O7.5, O13.10). And note the diminishing returns honestly — p99.99 is often dominated by irreducible physical effects and chasing it can be very expensive.

**O12.4 — Tail amplification with fan-out**

If one user request fans out to N backend calls and must wait for all of them, **the request's latency is the maximum of N samples**, not the average.

The arithmetic: if each call independently has a probability `p` of exceeding some threshold, the probability that **at least one** does is `1 - (1-p)^N`.

| Fan-out N | p = 1% (p99) | Probability at least one is slow |
|---|---|---|
| 1 | 1% | 1% |
| 10 | 1% | **9.6%** |
| 100 | 1% | **63%** |

**With a fan-out of 100, the backend's p99 becomes the user's median.** That's the result to state, because it's counterintuitive and it completely reframes what "p99" means.

The implications:

- **The required backend SLO tightens with fan-out.** For a fan-out of 100 to have a good p99 at the edge, backends need p99.99 behaviour — which is very expensive.
- **This is why large-scale systems obsess over the tail** far beyond what a single-service view would justify.

The mitigations: **reduce fan-out** — batch requests, denormalise, cache; **hedged requests** — send a duplicate to another replica after a short delay and take the first response, which trades a few percent extra load for a dramatically better tail (a genuinely effective technique worth naming); **tolerate partial results** so you don't wait for the slowest (O15.7); **timeouts with fallbacks** so one slow backend can't hold the whole response; and **reduce variance at the source** — GC tuning, headroom, and avoiding bimodality.

**O12.5 — Coordinated omission in load testing**

The flaw: a load generator that **sends the next request only after the previous one completes** stops sending requests when the system is slow — so **it fails to measure exactly the period when latency was worst.**

The illustration: a test intended to send 1,000 requests/second. The system stalls for 1 second. A naive closed-loop generator sends nothing during the stall, then resumes. It records the one slow request and **omits the ~1,000 requests that a real client population would have sent and which would all have experienced up to a second of queueing.** The reported p99 looks fine; the real p99 is catastrophic.

**The name comes from the load generator "coordinating" with the system under test** — backing off precisely when it should be applying pressure.

The consequences: **reported percentiles are wildly optimistic**, and the more the system stalls, the more it under-reports. The error is largest exactly where accuracy matters most.

The corrections:

- **Open-loop / constant-rate load generation** — send at a fixed rate regardless of responses. Tools designed for this: **wrk2**, **k6** with constant-arrival-rate executors, **Gatling** with open injection profiles. **JMeter and classic `wrk` are closed-loop by default** and exhibit the problem.
- **Correct the measurement** — record intended send time rather than actual, so a delayed request's latency includes the time it *should* have been sent (HdrHistogram's `recordValueWithExpectedInterval`).
- **Watch for backlog** — if the generator can't keep up, results are invalid.

The framing: **this is why load test results routinely fail to predict production behaviour.** Knowing the term and the mechanism is a strong signal, because it's a specific, well-defined trap that separates people who have done serious load testing from people who have run a load tool.

**O12.6 — Breaking down an end-to-end latency budget**

The method: state the target, then allocate it across components with the actual measured cost of each.

Target: **200ms p99 for an API response.**

| Component | Budget | Notes |
|---|---|---|
| DNS (cached) | ~0ms | Cold lookup 20–50ms (O12.8) |
| TCP connect | 0ms | Reused from pool; ~1 RTT if cold |
| TLS handshake | 0ms | Reused; 1–2 RTT if cold |
| Load balancer | 5ms | |
| Auth check (cached) | 5ms | 50ms on a cache miss |
| Application logic | 30ms | |
| Database query | 60ms | The dominant component |
| Downstream service call | 50ms | Their SLO — a dependency on someone else's budget |
| Serialisation and response | 10ms | |
| Headroom | 40ms | For variance and GC (O10.5) |

What makes this a useful exercise rather than a spreadsheet:

- **It identifies the dominant component**, which is where optimisation effort belongs (O13.8). Halving the 10ms serialisation is irrelevant; halving the 60ms query is meaningful.
- **It exposes dependencies on others' SLOs** — you cannot commit to 200ms if a downstream service only commits to 150ms.
- **It shows where the budget is already spent** before your code runs — connection setup, TLS, and auth can consume most of a tight budget (O12.8).
- **Explicit headroom** acknowledges variance rather than budgeting for the mean (O12.1).
- **The budget must be for the percentile you're committing to**, not the mean — summing means and calling it p99 is a common and serious error, because percentiles don't add that way.

Traces give you the measured breakdown directly (O5.5), which is the practical way to populate the table rather than estimating.

**O12.7 — Little's Law and concurrency sizing**

```
L = λ × W
concurrency = throughput × latency
```

The relationship is exact and assumption-free for a stable system, which is what makes it so useful.

**Applications:**

- **Sizing a thread or connection pool**: to serve 500 requests/second where each holds a connection for 40ms, you need `500 × 0.04 = 20` concurrent connections. **A pool of 10 caps you at 250 req/s regardless of anything else**; a pool of 200 wastes resources and, worse, allows enough concurrency to overwhelm the downstream (O15.5).
- **Diagnosing a throughput ceiling**: if throughput is stuck at 250 req/s and latency is 40ms, concurrency is 10 — **find what is limiting you to 10.** It's almost always a pool size, a semaphore, or a worker count, and this arithmetic points straight at it.
- **Predicting the effect of a latency change**: at fixed concurrency, halving latency doubles throughput. Which is why **optimising latency is often the cheapest way to increase capacity** — no extra infrastructure required.
- **Understanding queue depth**: in a message system, in-flight messages = consumption rate × processing time (M6.10).

The subtlety worth naming: **increasing concurrency does not increase throughput if the bottleneck is elsewhere.** Doubling a connection pool against a saturated database increases queueing at the database and makes latency worse (O12.1) — throughput stays flat and the system degrades. **Little's Law tells you the concurrency you need; it doesn't tell you the system can deliver it.** Recognising that distinction is what separates using the formula correctly from applying it mechanically.

**O12.8 — Connection setup, TLS, and DNS in the latency budget**

The costs for a cold connection:

| Step | Cost | Notes |
|---|---|---|
| DNS lookup | 0ms cached, 20–50ms cold, more on a miss chain | (N4) |
| TCP handshake | 1 RTT | 50ms on a 50ms RTT path |
| TLS 1.2 handshake | 2 RTT | |
| TLS 1.3 handshake | **1 RTT** | 0-RTT for resumption, with replay caveats |
| **Total cold** | **~3–4 RTT plus DNS** | 150–250ms on a 50ms path |

**On a 50ms RTT path, establishing a connection can cost more than the request itself.**

The consequences and the mitigations:

- **Connection pooling and keep-alive are the single biggest win**, and their absence is a common, easily-fixed performance problem. A client creating a new connection per request pays the full cost every time.
- **A cold pool after a deploy or a scale-out causes a latency spike** — every new instance establishes connections. This is a recognisable post-deploy p99 bump and it's why connection pre-warming exists.
- **TLS 1.3 halves the handshake cost** versus 1.2, which is a real and easy improvement.
- **Session resumption** avoids the full handshake.
- **DNS caching matters**, and TTLs interact with failover (A8.5, N4.9) — a very short TTL for failover agility costs a lookup more often.
- **HTTP/2 and HTTP/3 multiplex** over one connection, removing per-request setup entirely; **HTTP/3 (QUIC) combines transport and crypto handshakes** into fewer round trips, which matters most on high-latency mobile paths.
- **A pool that's too small forces new connections** under load, so the cost appears precisely at peak (O12.7).

The diagnostic is `curl -w` (O11.9), which breaks these out explicitly and frequently shows that most of a "slow API" is setup rather than service time.

---

## O13. Profiling, benchmarking & load testing

**O13.1 — Profiling a running application**

```bash
# Linux, any language with symbols
perf record -F 99 -g -p <pid> -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > profile.svg

# JVM
async-profiler: ./profiler.sh -d 30 -e cpu -f profile.html <pid>
# also: -e alloc (allocation), -e lock (contention, O9.8), -e wall (off-CPU)

# Go — built in
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30
go tool pprof http://localhost:6060/debug/pprof/heap

# Python
py-spy record -o profile.svg --pid <pid> --duration 30
```

The method:

1. **Profile under representative load.** A profile of an idle process tells you nothing; a profile under synthetic load tells you about the synthetic load.
2. **Sample for long enough** to be statistically meaningful — 30 seconds is a reasonable default, longer for infrequent paths.
3. **Choose the right event.** CPU profiling finds compute hot spots; **it will not find a program waiting on a lock or on I/O** — that needs **off-CPU** or **wall-clock** profiling. Picking CPU profiling for a latency problem where the process is 40% idle is the classic mistake (O9.8).
4. **Read the flame graph** (O13.2).
5. **Confirm with a measurement** — profiles show where time is spent, not that changing it will help (O13.10).

The practical point: **`perf` needs symbols and, for JIT languages, a symbol map** (`perf-map-agent` for the JVM), or you get unresolved addresses. Language-specific profilers avoid that and are usually the better choice.

**O13.2 — Reading a flame graph**

The structure: **x-axis is not time** — it's alphabetically sorted stack frames, and **width is the proportion of samples**. **Y-axis is stack depth**, with callers below and callees above.

How to read it:

- **Width is what matters. Find the widest frames.** A wide frame means many samples had that function on the stack, so time is being spent there or below it.
- **A wide frame with wide children** means the time is in the children — keep going up.
- **A wide frame with narrow or no children ("a plateau") is where the work actually happens.** That's your hot spot, and it's the thing to look for.
- **Height is irrelevant to cost** — a deep stack isn't slow, it's just deep.
- **Look for unexpected width** — a wide frame in logging, serialisation, reflection, or string formatting is a very common and easily-fixed finding.

The variants worth knowing: **icicle graphs** (inverted, root at top) are the same data; **differential flame graphs** colour the difference between two profiles and are excellent for before/after comparison (O13.10); **off-CPU flame graphs** show where threads are blocked rather than running, which is the tool for lock contention and I/O waits (O9.8); and **allocation flame graphs** show where memory is allocated, which is the direct route to reducing GC pressure (O10.5).

**O13.3 — Continuous profiling and production overhead**

Continuous profiling runs a sampling profiler permanently in production at low frequency, storing profiles for later comparison. Tools: **Pyroscope/Grafana Phlare**, **Parca**, **Datadog Continuous Profiler**, **Google Cloud Profiler**.

**Why it's valuable**:

- **You have the profile from when the problem happened.** Reproducing a production performance issue in a test environment is often impossible; with continuous profiling you simply look at the relevant window. This is the same argument as retaining traces (O1.6).
- **Comparison across time and versions** — a differential profile between last week and this week shows exactly what a release changed (O13.2).
- **Comparison across instances** — why is one pod slower?
- **No need to decide in advance to profile**, which is the practical barrier to profiling at all.

**The overhead**: typically **1–3% CPU** at low sampling frequencies (around 100Hz), plus a small amount of memory and the network cost of shipping profiles. **That's low enough to be acceptable for most services**, and stating a number is what the question wants.

The caveats: **overhead depends on the profiler and the event** — allocation profiling and lock profiling cost more than CPU sampling; **JIT languages need symbol resolution** which can add cost; and **it's another agent in production** with its own failure modes and resource limits. The mitigations are sampling frequency and enabling it selectively per service rather than fleet-wide by default.

**O13.4 — Sampling vs instrumenting profilers**

- **Sampling** — periodically interrupt and record the stack. Cost is proportional to sampling frequency, **not to program behaviour**. Statistically accurate for hot paths, and it **misses rare events entirely** — a function called twice that takes 10ms each may not appear at all.
- **Instrumenting** — insert probes at function entry and exit to record exact counts and durations. Exact, and **the overhead is proportional to call frequency** — so it distorts the very thing it measures. A tiny function called ten million times may see its measured cost dominated by instrumentation, which makes it look like a hot spot when it isn't.

The tradeoff and when to use each:

- **Sampling for production and for finding hot paths.** Low, predictable overhead; safe to run continuously (O13.3). This is the default.
- **Instrumenting for exact call counts** and for understanding a specific function's behaviour in a controlled environment. Also for tracing-style profiling of infrequent, expensive operations that sampling would miss.
- **The observer effect is the key distinction to name** — instrumentation changes the program's performance characteristics, especially for small hot functions, and can lead you to optimise something that was only slow because you were measuring it.

The related point: **tracing (O5) is instrumentation at the operation level** — it has the same properties, which is why span granularity matters for overhead (O5.9).

**O13.5 — Designing a benchmark that isn't misleading**

The pitfalls, and each has a corresponding discipline:

- **Measuring a warm-up.** JIT compilation, cache filling, connection pool establishment, and lazy initialisation all mean early iterations are unrepresentative. **Discard warm-up iterations explicitly.**
- **Dead code elimination.** The compiler removes computation whose result is unused, so you benchmark nothing. **Consume the result** — JMH's `Blackhole`, or returning the value.
- **Unrealistic data.** Benchmarking with a 100-row table when production has 100 million; using sequential IDs when production access is random; using a uniform distribution when production is heavily skewed (M5.4). **Data shape dominates results.**
- **Measuring the mean only** (O2.3) — report the distribution.
- **A single run.** Variance between runs is often larger than the difference being measured. **Multiple runs, report variance, use statistical comparison.**
- **Environmental noise** — a shared CI runner, a noisy neighbour (O9.3), thermal throttling, background processes. **Isolate, pin, and repeat.**
- **Benchmarking the wrong layer** — a microbenchmark showing function X is 30% faster is irrelevant if X is 2% of the workload (O14.5).
- **Coordinated omission**, if throughput is involved (O12.5).

The discipline to state: **define the question first.** "Is A faster than B for our workload?" is answerable; "which is faster?" is not, because it depends on the workload. And **verify the benchmark measures what you think** — a benchmark that shows an implausible result usually has a bug rather than a discovery.

**O13.6 — A load test with realistic traffic shape**

What "realistic" means, and each of these is commonly wrong:

- **Request mix** — production isn't one endpoint. Model the actual distribution, including the expensive rare calls that dominate resource usage.
- **Arrival pattern** — real traffic is bursty, not a constant rate. Model bursts, and use **open-loop generation** so the arrival rate doesn't depend on system responsiveness (O12.5).
- **Ramp** — a step from zero to peak tests a cold system; a realistic ramp tests the steady state. **Test both**, because they answer different questions (cold-start capacity vs sustained capacity).
- **Data distribution** — real users have wildly varying data sizes; a test where every user has 10 items misses the customer with 10,000. **Skewed, realistic data is what surfaces the tail** (O12.3).
- **Cache behaviour** — a test hammering one key has a 100% hit rate; production has a long tail of cold data. **This is one of the biggest sources of optimistic results.**
- **Think time** — real users pause. A test with zero think time is a different workload.
- **Concurrency and connection behaviour** — connection reuse, keep-alive, HTTP/2 multiplexing (O12.8).
- **State** — a test that only reads misses write contention and lock behaviour.

The practical approach: **derive the shape from production telemetry.** Endpoint distribution from metrics, payload sizes from logs, arrival pattern from request rate over a real day. **Traffic replay** — capturing and replaying real production traffic — is the highest-fidelity approach and worth naming.

**O13.7 — Load vs stress vs soak vs spike**

- **Load test** — expected peak traffic. **Question: can we handle our expected load within SLO?** The routine, pre-release test.
- **Stress test** — beyond capacity until something breaks. **Question: where is the limit, and how does it fail?** The most valuable output is the *failure mode* — does it shed load gracefully, degrade, or collapse? (O15.3)
- **Soak/endurance test** — sustained moderate load for hours or days. **Question: does anything degrade over time?** Finds **memory leaks** (O10.4), connection leaks, disk filling, log growth, and slow fragmentation (O10.7). **The only test that finds this class**, and the one most often skipped because it's slow.
- **Spike test** — sudden sharp increase then drop. **Question: how do we handle a burst?** Tests autoscaling reaction time (K7.3), queue absorption, connection pool behaviour, and cold-start cost.

Two more worth naming: **capacity test** — increase load stepwise to find the throughput/latency knee (O12.1), which is the input to capacity planning (O14.1); and **breakpoint/scalability test** — how does capacity change as you add instances, which finds sub-linear scaling (O14.4).

The point to make: **these answer different questions and most teams only run the first.** The failure-mode information from a stress test and the leak detection from a soak test are the ones with the most incident-prevention value, and they're the ones skipped because they take longer and produce uncomfortable results.

**O13.8 — Identifying the bottleneck rather than the failure point**

The distinction: **a load test tells you it broke at 5,000 req/s. That's the failure point. The bottleneck is *what* limited it** — and only the second is actionable.

The method:

1. **Instrument everything during the test** — application metrics (RED, O2.9), resource metrics at every layer (USE, O2.10), database metrics, queue depths, pool utilisation.
2. **Find what saturated first.** Work through: CPU (and check throttling, O9.4), memory, disk I/O (O11.3), network, connection pools, thread pools, database connections, downstream service latency, locks (O9.8).
3. **Look at the shape of the throughput curve** (O9.6): a plateau means a saturated resource; a **decline** past a peak means contention or thrashing; a sharp cliff often means a hard limit (a pool, a quota, a semaphore).
4. **Apply Little's Law** (O12.7) — if throughput is capped and latency is known, concurrency is determined; find what limits it to that number.
5. **Confirm by relieving it.** Increase the suspected constraint and re-test. **If throughput improves, that was the bottleneck; if not, keep looking.** This is the only real proof and it's the step people skip.
6. **Then find the next one** — removing a bottleneck reveals the next, and capacity work is iterative.

The insight to convey: **"it failed at 5,000 req/s" is not a finding; "it failed at 5,000 req/s because the database connection pool was capped at 50 and each request held a connection for 40ms" is** — because the second tells you exactly what to change and predicts the result (O12.7).

**O13.9 — Load testing against production**

**The value:**

- **It's the only environment that's actually production** — real data volumes, real cache states, real network topology, real neighbours, real configuration drift. A staging environment is a model, and models are wrong in ways you discover during incidents.
- **It validates the whole path** — CDN, load balancer, autoscaling, database, third parties.
- **It tests autoscaling behaviour** in the configuration that matters (K7.3).
- **A production-sized test environment is often unaffordable**, so the alternative is testing at a scale that predicts nothing.

**The risks:**

- **You can cause a real outage** for real users.
- **Data pollution** — test transactions in real tables, test users in real analytics, test emails to real addresses.
- **Cost** — triggering autoscaling and downstream usage-based charges.
- **Third-party impact** — hitting a partner's API with synthetic load, potentially breaching rate limits or contracts.

**The controls that make it defensible:**

- **Start small and ramp with a defined abort condition** tied to real user SLIs — the moment real-user error rate or latency degrades, stop automatically.
- **Traffic tagging** so synthetic requests are identifiable end to end, excluded from analytics and billing, and routed to test doubles for irreversible actions.
- **Shadow/mirror traffic** — duplicate real requests to a parallel stack, discarding responses. **Realistic load with no user impact**, and the best option where it's feasible.
- **Off-peak, announced, with the on-call informed** and a rollback plan.
- **Read-only where possible**; test accounts and sandboxed downstreams where not.

The framing: **the question isn't whether to test in production but how to do it safely**, and the honest position is that a well-controlled production test is lower risk than the false confidence of a staging test that doesn't represent reality.

**O13.10 — Optimising and proving the improvement**

The method, and the discipline is the point:

1. **Measure the baseline properly** — the distribution (O2.3), under realistic load (O13.6), over enough time to capture variance.
2. **Find the actual bottleneck** (O13.8, O13.1), don't guess. **The most common failure is optimising something that wasn't the constraint**, which produces a measurable local improvement and no end-to-end change (O14.5).
3. **Change one thing.**
4. **Measure again**, same conditions, same load, same data.
5. **Compare the distribution, not the mean** — a heatmap (O7.5) or a differential flame graph (O13.2). **Check the change moved the whole distribution** and didn't just improve the median while worsening the tail.
6. **Verify statistical significance** — run both several times; if the difference is within run-to-run variance, you have not demonstrated anything.
7. **Confirm end-to-end.** A 40% improvement in a component that was 5% of the budget is a 2% improvement overall (O12.6).
8. **Check for regressions elsewhere** — memory for CPU, throughput for latency, cost for speed.

The reporting that makes it credible:

> "p99 checkout latency went from 840ms to 310ms measured over a week of production traffic before and after, with p50 unchanged at 90ms. The change was adding a covering index for the order-history query, which the traces showed as 60% of the request budget. Throughput at the same instance count rose from 400 to 950 req/s, so we scaled down from 12 pods to 6, saving roughly £X per month. No increase in database CPU."

**A baseline, a period, a mechanism, the distribution not just a summary statistic, and a check that nothing else regressed.** That structure is what makes a performance claim believable, and it's the same shape as the cost story in A12.7.

---

## O14. Capacity & scaling

**O14.1 — Forecasting capacity from growth trends**

The method:

1. **Establish the metric that actually drives capacity** — usually not "users". It's requests/second, concurrent connections, data volume, or writes/second. **Pick the one your bottleneck responds to** (O13.8).
2. **Get enough history** — at least several months, ideally a year, to see seasonality. This is what long-retention downsampled metrics are for (O2.8).
3. **Decompose the trend**: baseline growth, seasonality (daily, weekly, annual — Black Friday, quarter-end, tax deadlines), and step changes (a launch, a customer onboarding, a marketing campaign).
4. **Project forward** with a simple model — linear or exponential fit is usually sufficient; `predict_linear` in PromQL for short horizons (O3.5). **Sophisticated forecasting is rarely the constraint**; the data quality and the choice of metric are.
5. **Convert to resources** using measured capacity per unit — "one pod handles 400 req/s at 60% utilisation" from a load test (O13.7).
6. **Add headroom** (O14.2) and **subtract lead time** — if procurement, quota increases (O14.7), or a migration takes six weeks, your decision point is six weeks before the capacity is needed.
7. **Review regularly**, because the trend changes.

The realities to name: **growth is rarely smooth** — a single large customer onboarding can exceed a quarter's organic growth, so **the sales pipeline is a capacity input** and talking to that team is part of the job. **Efficiency changes shift the curve** — an optimisation (O13.10) can buy more headroom than scaling. And **forecast the constraint, not the average** — you run out of one thing first, and it may be database connections or an API quota rather than compute.

**O14.2 — Headroom requirements and justifying them**

**The justification is queueing theory, not caution** (O12.1). At 90% utilisation, latency is roughly 9× service time; at 50% it's about 1×. **Headroom is not waste — it's the difference between a system that's fast and one that's technically working.**

The specific things headroom must absorb:

- **Traffic variance** — real traffic is bursty, and the peak within a minute is well above the five-minute average your dashboard shows.
- **Instance or AZ failure.** **Size for N-1**: three AZs at 33% each means an AZ loss puts survivors at 50%. If they were at 70%, they're now at 105% (A11.4, K13.6). **This is usually the binding constraint and the easiest to justify.**
- **Deployment** — rolling updates temporarily reduce capacity (K2.6).
- **Autoscaling reaction time** — scale-out takes minutes (K7.5), so headroom covers the gap between the spike and the new capacity.
- **Growth between capacity reviews.**
- **Degraded-mode operation** — retries and fallbacks increase load during partial failure (O15.9).

The targets to state: **50–70% at peak for latency-sensitive services; higher for batch and throughput-oriented work** where queueing delay doesn't affect anyone.

The justification to leadership: **frame it as the failure scenario, not as a percentage.** "We run at 60% so that losing an availability zone doesn't cause an outage" is a conversation about risk that people can engage with; "we need 40% headroom" sounds like inefficiency. And quantify the alternative — the cost of the outage versus the cost of the headroom (O14.8).

**O14.3 — Vertical vs horizontal scaling limits**

- **Vertical** — a bigger machine. **Simple**: no distribution, no coordination, no application changes. **Limits**: a hard ceiling at the largest instance available; cost rises super-linearly at the top end; **it's a single point of failure** regardless of size; and resizing usually requires a restart.
- **Horizontal** — more machines. **Limits**: requires the workload to be distributable — statelessness, or a partitioning scheme; introduces coordination and consistency problems; and **scales sub-linearly** because of shared resources (O14.4).

For a stated workload:

- **Stateless web/API tier** → horizontal, trivially. The only reason to scale vertically is per-instance efficiency (fewer, larger instances reduce per-instance overhead).
- **Relational database primary** → **vertical first, and this is the important case.** Write scaling on a single-primary RDBMS is fundamentally vertical; horizontal means read replicas (which only scale reads, A7.2) or sharding (which is a major application change). Vertical scaling of the primary is usually the right answer until it isn't, and then sharding is a project.
- **Cache** → horizontal with consistent hashing, though a single large node is often simpler and adequate.
- **Message consumers** → horizontal, bounded by partition count (M6.2).
- **Anything with large in-memory state** → vertical is often simpler than distributing the state (O8 of the Kubernetes domain, K13.8).

The pragmatic sequence to state: **vertical until it's uncomfortable, then horizontal** — because vertical is cheap in engineering time and horizontal is cheap in machine time, and engineering time is usually the scarcer resource until scale makes the arithmetic flip.

**O14.4 — What makes a system scale sub-linearly**

Adding 2× the instances rarely gives 2× the throughput. The causes:

- **A shared bottleneck** — all instances hitting one database, one cache, one queue, one file system. **The most common by a wide margin**: you scaled the stateless tier and moved the load onto a stateful component that didn't scale (O13.8).
- **Coordination overhead** — leader election, distributed locks, consensus, rebalancing (M6.3). Coordination cost typically grows worse than linearly with node count.
- **The serial fraction** (O14.5).
- **Increased contention** — more clients on the same lock or the same database rows (O9.8).
- **Connection multiplication** — N app instances × M connections each can exhaust a database's connection limit, and connections have per-connection memory cost. A very common wall (K13.8, A4.8).
- **Cache hit rate degradation** — more instances each with their own local cache means each sees a smaller share of traffic, so hit rates fall and backend load rises **more than proportionally**. A genuinely counterintuitive effect.
- **Cross-instance chatter** — a fan-out or gossip pattern where communication grows as N².
- **Rebalancing and warm-up cost** on every scaling event.

The **Universal Scalability Law** is worth naming as the formal version: throughput is limited by contention (the serial fraction) *and* coherency (the cost of keeping nodes consistent), and **the coherency term is negative and quadratic — so past a point, adding nodes reduces throughput.** That's a real, observed phenomenon and it's why "just add more instances" eventually stops working and then starts hurting.

The practical test: **measure throughput at 1, 2, 4, 8 instances** and look at the shape (O13.8). Where it flattens tells you the bottleneck; where it declines tells you there's coordination cost.

**O14.5 — Amdahl's law informally and its consequence**

Informally: **the speedup from parallelising a program is limited by the part that can't be parallelised.**

If 10% of the work is inherently serial, then even with infinite parallelism you can only ever be **10× faster** — the serial 10% remains.

| Serial fraction | Maximum speedup |
|---|---|
| 50% | 2× |
| 10% | 10× |
| 5% | 20× |
| 1% | 100× |

**The practical consequence, which generalises far beyond parallelism:**

- **Optimising the non-bottleneck has bounded and usually trivial value.** If the database is 60% of your latency budget, making the application logic infinitely fast improves things by 40% at most (O12.6). **This is the argument for finding the bottleneck before optimising** (O13.8, O13.10).
- **Diminishing returns are guaranteed.** Each optimisation reduces its component's share, so the next optimisation of the same component matters less. Eventually the serial part dominates and further effort is wasted.
- **The serial part is often not code** — it's a lock, a single-primary database write path, a sequential coordination step, or a third-party call.
- **It sets a ceiling you should calculate before committing effort.** "Even if we make this free, what's the best case?" is the question that prevents months spent on a 3% improvement.

The generalisation worth stating: **Amdahl's law is really about the limits of local optimisation in any system with a fixed structure**, and it's why architectural change sometimes beats any amount of tuning.

**O14.6 — Planning for a known traffic event**

For a launch, a marketing campaign, Black Friday, or a regulatory deadline:

1. **Get a number.** Expected peak requests/second, concurrent users, or orders/minute — from the business, from last year's equivalent, or from a comparable event. **A plan without a target is not a plan.**
2. **Load test to that number, plus a margin** (O13.6), with realistic shape including the spike pattern.
3. **Find and fix the bottleneck** revealed (O13.8), then re-test.
4. **Pre-scale.** Don't rely on autoscaling for a known event — reaction time is minutes and the spike may be seconds (K7.3). Scale up in advance and scale down after.
5. **Check the things that don't autoscale**: **quotas and limits** (O14.7), database connections, third-party API rate limits, licence limits, and IP address space (A5.7).
6. **Warm the caches and the connection pools** (O12.8), because a cold start at peak is the worst case.
7. **Verify downstream dependencies** can take the load — including partners, who need telling.
8. **Plan degradation** — what do you turn off if it's worse than expected (O15.7)? Decide in advance, because you won't reason well during it.
9. **Staff it** — extra people on call, a war room, and a decision-maker available.
10. **Increase observability temporarily** — higher sampling, more granular dashboards (O1.4).
11. **Freeze changes** in the run-up.
12. **Review afterwards** with real numbers, which becomes the input for the next event.

The point to emphasise: **the most common failure is a resource that doesn't autoscale** — a quota, a connection limit, a rate limit, a single-primary database (O14.7). Compute scales; the constraint is almost always something else, and step 5 is the one that saves the event.

**O14.7 — Quota and limit exhaustion as a capacity failure**

The category: **limits imposed by a provider or a system that you cannot exceed regardless of how much you're willing to spend**, and which typically bind only under load.

Examples (A11.9): **cloud service quotas** — EC2 vCPUs per family, Lambda concurrency, ENIs, Elastic IPs, API request rates; **database connection limits**; **connection pool sizes**; **file descriptors and process limits** (`ulimit`); **thread pool sizes**; **port exhaustion** for outbound connections (ephemeral port range, and NAT gateway port allocation, A3.1); **Kubernetes limits** — pods per node, IPs per subnet (A5.7); **third-party API rate limits**; and **licence seat limits**.

Why they're a distinct failure class:

- **They bind suddenly and absolutely.** Not degradation — a hard error at a specific threshold.
- **They're invisible until hit**, because utilisation against a quota is rarely on a dashboard.
- **You can't fix them at the time.** A quota increase takes hours to days and may need provider review. **Requesting one during an incident is not a mitigation.**
- **They're often per-account or per-region**, so one team's batch job exhausts a shared quota and breaks unrelated production services (A10.15).

The management (A11.9): **inventory quotas against actual usage**; **alarm at 70–80% utilisation** so a future outage becomes a ticket — the highest-value, lowest-effort control here; **request increases proactively** before known events (O14.6); **include quota requests in account provisioning** (A1.13); and **account for the failure scenario** — during an AZ loss you need more capacity in fewer AZs, and during a regional failover you need quotas in a region that has never been exercised.

**O14.8 — Balancing cost against headroom explicitly**

The tension: **headroom costs money continuously; running out costs money in a concentrated, unpredictable way.**

Making the tradeoff explicit:

1. **Quantify the headroom cost** — "40% headroom on this tier is £X/month."
2. **Quantify the risk** — what's the probability and cost of an incident caused by insufficient headroom? Revenue per hour of downtime, SLA penalties, regulatory consequences, and reputational cost.
3. **Recognise the asymmetry** — the cost of headroom is small, certain, and recurring; the cost of exhaustion is large, uncertain, and concentrated. **Most organisations are risk-averse about the second**, and correctly so, but they rarely make the comparison explicit.
4. **Differentiate by tier.** The payment path and the internal reporting dashboard should not carry the same headroom. **Uniform headroom over-provisions the unimportant and under-provisions the critical**, which is the most common error.
5. **Use the cheap levers first** — Spot for interruptible work, autoscaling to reduce headroom needs by shortening reaction time, scheduled scaling for known patterns, and **right-sizing** (K6.5), which frequently frees more capacity than it costs to buy.
6. **Revisit as the system changes** — an efficiency improvement (O13.10) is capacity you already paid for.

The framing that works with leadership: **present it as a risk decision with numbers, not as an engineering preference.** "We can run at 85% and save £X per month, accepting that an AZ failure would cause a customer-facing outage; or run at 60% and survive it" is a decision a business can make. "We need more instances" is not.

And the honest counterweight: **headroom is not the only answer.** Load shedding (O15.3), graceful degradation (O15.7), and faster autoscaling all reduce the headroom required, and are sometimes cheaper than buying capacity.

---

## O15. Reliability patterns

Retries, timeouts, circuit breakers and chaos are T7.6–T7.9; these are the design-level complements.

**O15.1 — Redundancy, failure domains, and correlated failure**

- **A failure domain** is a set of components that fail together — a process, a host, a rack, an availability zone, a region, a provider.
- **Redundancy** means having more instances than you need, **placed in different failure domains** so a single domain's failure doesn't take them all.

The essential point: **redundancy is only meaningful relative to a failure domain.** Three replicas on one host protect against process failure and nothing else. Three replicas in one AZ protect against host failure and not AZ failure (A11.4, K13.6).

**Correlated failure** is when supposedly independent components fail together because they share something you didn't account for:

- **Shared infrastructure** — the same host, rack, power supply, network switch, or AZ.
- **Shared dependencies** — all replicas depending on the same database, the same config service, the same DNS resolver, the same secret store. **Redundancy in the compute tier is irrelevant if all replicas depend on one thing that failed.**
- **Shared code** — a bug affects every replica identically, which is why redundancy doesn't protect against a bad deploy (K13.6) and why progressive rollout does.
- **Shared configuration** — a bad config pushed everywhere at once.
- **Shared state** — a poison record that crashes every replica processing it (M2.7).
- **Shared saturation** — all replicas hit the same limit at the same time.

The design discipline: **enumerate what your replicas share.** Everything shared is a potential correlated failure, and the redundancy only covers what isn't shared. That enumeration is a genuinely useful review exercise and is what O15.2 is about.

**O15.2 — Why redundancy without independence buys little**

The arithmetic: two components each with 99% availability give 99.99% **only if their failures are independent**. If they fail together 50% of the time, the benefit largely evaporates.

Where independence is violated in practice — worth being able to list, because it's the practical form of O15.1:

- **A bad deploy** goes to all replicas. No amount of redundancy helps; **progressive rollout and canary do** (K2.11).
- **A shared dependency's failure** takes all replicas out simultaneously.
- **A correlated load spike** — all replicas saturate together because they receive the same traffic.
- **A shared control plane** — all replicas fail to start because the image registry or the API server is down.
- **The same latent bug** triggered by the same input.
- **Certificate expiry** — every replica has the same certificate with the same expiry (A8.6). Perfectly redundant and simultaneously dead.
- **A cascading failure** propagating through the redundant set (O15.11).

The consequence to state: **most real outages are correlated failures, not independent component failures.** Hardware redundancy solves the problem the industry solved decades ago; the failures that cause modern incidents — bad deploys, config changes, dependency failures, saturation — are precisely the correlated ones that redundancy doesn't address.

Which reframes the reliability investment: **diversity and independence matter more than count.** Different AZs beats more instances; staged rollout beats more replicas; a fallback path that doesn't share the failing dependency beats a redundant path that does. And that's the argument for spending on progressive delivery and graceful degradation rather than on a third replica.

**O15.3 — Load shedding and prioritising traffic**

**Load shedding** is deliberately rejecting some requests to protect the system's ability to serve the rest.

The justification is O12.1 and O12.2: **past saturation, accepting more work makes everything worse.** A system accepting requests it cannot serve queues them, blows its latency, times out, and often serves *nobody* — whereas rejecting 20% immediately keeps 80% healthy. **Shedding converts a total failure into a partial one**, which is almost always better.

The mechanics:

- **Reject early and cheaply.** The rejection must cost far less than the work — at the edge, before authentication and database access, or the shedding itself consumes the capacity.
- **Return a clear signal** — HTTP 429 or 503 with `Retry-After`, so well-behaved clients back off rather than retrying immediately (O15.9).
- **Trigger on a leading indicator** — queue depth, concurrency, or latency, not CPU. **Shedding based on a saturation signal acts before collapse** (O2.10).

**Prioritisation** is what makes it acceptable:

- **By criticality** — shed analytics and recommendation traffic before checkout.
- **By user tier** — paying customers before free, authenticated before anonymous.
- **By cost** — shed expensive queries first, which frees the most capacity per rejection.
- **Retries before first attempts** — a retry is by definition a duplicate of work already attempted, so shedding retries preserves more original requests.

The design point: **prioritisation requires knowing the request's importance at the point of shedding**, which means classification must happen early and cheaply — usually a header, a route, or a token claim. Systems that can't classify can only shed randomly, which is much less valuable.

**O15.4 — Rate limiting and throttling as protective mechanisms**

**Rate limiting** bounds the request rate from a client; **throttling** slows rather than rejects.

The purposes, and they're distinct: **protecting the system** from overload (a form of load shedding applied per-client, O15.3); **fairness** so one client can't consume everyone's capacity (the noisy-neighbour problem, M9.6); **cost control**; and **abuse prevention**.

The algorithms:

- **Token bucket** — tokens accrue at a fixed rate up to a bucket size; each request consumes one. **Allows bursts up to the bucket size while bounding the sustained rate.** The most common and usually the right choice, because real traffic is bursty and a limiter that forbids bursts rejects legitimate use.
- **Leaky bucket** — smooths output to a constant rate; queues rather than rejects.
- **Fixed window** — simple, and has a **boundary problem**: 2× the limit can pass across a window boundary.
- **Sliding window** — corrects the boundary problem at more cost.

The design decisions:

- **Limit by what?** Per user, per API key, per IP, per tenant, per endpoint. **Per-IP is weak** (shared NATs, mobile carriers) and per-tenant is usually what you want.
- **Where?** At the edge (cheapest, protects everything) versus in the application (knows more context). **Usually both** — a coarse edge limit and a fine-grained application limit.
- **Distributed enforcement** is the hard part — a limit across many instances needs shared state (Redis) with its own latency and availability implications, or you accept approximation with per-instance limits.
- **Communicate the limit** — `X-RateLimit-Remaining` and `Retry-After` headers, so clients can behave well rather than hammering.

The point to make: **a rate limit is a contract, not just a defence.** Published limits let clients design correctly; secret limits produce mysterious failures and support tickets. And **rate limiting protects you from your clients; it doesn't protect you from yourself** — internal retry storms bypass it if applied only at the edge (O15.9).

**O15.5 — The bulkhead pattern**

From ship design: compartments so a breach floods one section rather than sinking the vessel. **In software: isolate resources so one failing component can't consume everything.**

The instances:

- **Separate thread or connection pools per dependency.** If service A and service B share one pool of 50 threads and B becomes slow, all 50 threads block on B and **requests that only need A also fail.** With separate pools of 25 each, B's failure consumes only its own — A keeps working. **This is the canonical example** and the clearest demonstration of the idea.
- **Separate connection pools per database or shard.**
- **Separate compute for different workload classes** — batch and interactive on different node pools (K6.7), so a batch job can't starve interactive traffic.
- **Separate instances per tenant** for critical customers.
- **Separate queues per consumer** rather than a shared one (M1.2).
- **Separate rate limit buckets** per client (O15.4).

The tradeoff to state: **isolation costs efficiency.** Pooled resources are more efficiently used — 50 shared threads serve variable demand better than two fixed pools of 25, because one pool sits idle while the other queues. **You're paying utilisation for containment**, and whether that's worth it depends on how much you care about partial failure versus peak efficiency.

The connection to the wider argument: **bulkheads are what stop a dependency failure becoming a total failure** (O15.11), and they're the structural complement to circuit breakers — the breaker stops you calling a broken thing, the bulkhead limits the damage while you're still calling it.

**O15.6 — Queueing as a buffer, and its limits**

A queue absorbs a mismatch between arrival rate and service rate, converting a spike into a backlog (M1.1).

**What it buys**: load levelling, temporal decoupling, availability decoupling (M1.6), and retry durability.

**Its limits, which is the substance of the item:**

- **A queue solves a temporary mismatch, not a sustained one.** If the arrival rate persistently exceeds the service rate, **the queue grows without bound** and no amount of buffering helps — you need more capacity or less load (M10.8). **A queue converts an immediate failure into a delayed one**, which is only useful if the mismatch ends.
- **Queue depth is latency.** Little's Law (O12.7): a queue of 100,000 items draining at 1,000/s is 100 seconds of latency for the last item. **A deep queue means every item is late**, and "the queue is absorbing it" can mean "everything is now unacceptably delayed".
- **Unbounded queues are dangerous** — they consume memory or disk until something breaks, and they defer the failure to the least convenient moment. **Bounded queues that reject when full are usually correct** (O15.3), because they apply backpressure (M1.7).
- **Stale work** — items in a deep queue may be irrelevant by the time they're processed. A request whose client timed out 30 seconds ago should be discarded, not served. **Deadline propagation** — carrying the caller's deadline so downstream can drop expired work — is the sophisticated answer and worth naming.
- **Recovery is a thundering herd** — draining a backlog at full speed can re-break whatever recovered (M10.10).

The framing: **a queue is a shock absorber, not a capacity multiplier.** Sizing it is about how long a mismatch you want to survive, not about how much load you can handle.

**O15.7 — Graceful degradation with a concrete example**

**Serving a reduced but useful experience rather than failing entirely.**

A concrete example — an e-commerce product page depends on: the product service, the pricing service, inventory, recommendations, reviews, and personalisation.

| Dependency | If it fails | Degraded behaviour |
|---|---|---|
| Product service | Fatal | Cannot render — this is the only hard dependency |
| Pricing | Serious | Serve last-known price from cache with a staleness marker |
| Inventory | Moderate | Hide the stock indicator; allow the order and validate at checkout |
| Recommendations | Minor | Omit the section entirely |
| Reviews | Minor | Show cached, or omit |
| Personalisation | Minor | Serve the generic page |

**The page still sells the product with four of six dependencies down.** That's the outcome, and the design work is deciding in advance which dependencies are essential and what the fallback for each is.

The mechanisms: **timeouts with fallbacks** so a slow dependency doesn't hold the response (T7.6); **circuit breakers** so a failing dependency is skipped quickly rather than waited on (O15.11); **cached or default responses**; **feature flags** to disable expensive features under stress; and **partial rendering** so the response goes out with what's available (O12.4).

The design principles: **classify every dependency as critical or optional, explicitly** — most teams have never done this, and the default is that everything is critical because everything is awaited. **Optional dependencies must have a defined fallback and a short timeout.** And **test the degraded path** — a fallback that has never been exercised usually doesn't work (T7.9, A11.8).

**O15.8 — Health check design and the danger of checking too much**

The distinction (K9.10): **liveness** — is this process wedged and in need of a restart? **Readiness** — should this instance receive traffic right now?

**The danger of checking too much** is the substance, and it's the same failure as K9.11 stated generally:

A health check that verifies the database, the cache, and three downstream services seems thorough. But when the database has a brief problem, **every instance's health check fails simultaneously** — because they share the dependency. The load balancer removes every instance, or the orchestrator restarts every container. **A transient dependency blip becomes a total outage**, caused by the mechanism intended to improve reliability.

Worse, restarting doesn't fix a database problem, and the restarted instances all reconnect at once, making it worse (O15.9).

The rules:

- **Liveness checks only the process.** "Is my event loop responsive?" Nothing external. If it can fail because of something outside the process, it will cause a restart storm.
- **Readiness may check dependencies the instance genuinely cannot function without** — but consider whether removing all instances from rotation is better than serving degraded (O15.7). Often it isn't.
- **Distinguish "I am broken" from "the world is broken."** If every instance is unhealthy for the same external reason, taking them all out of service helps nobody. **Some systems deliberately ignore readiness when all backends are unhealthy** (fail-open) precisely for this reason — worth naming as a real technique.
- **Generous thresholds and timeouts** on anything that triggers a restart.
- **A health check that's slow or expensive** becomes a load source itself at scale — hundreds of instances checking a database every second is real traffic.

**O15.9 — How a retry storm turns a small failure into an outage**

The sequence:

1. A downstream service becomes slow or starts erroring — perhaps briefly, perhaps at 5% of requests.
2. Every caller retries. **Load on the struggling service increases by the retry multiplier** — with 3 attempts, up to 3× the original load.
3. The additional load makes it slower, so more requests fail or time out, so more are retried.
4. **Retries compound through layers**: if each of three tiers retries 3×, a single user request becomes up to 27 downstream calls. **This is the multiplication that turns a blip into a collapse.**
5. The service is now receiving far more load than it was when the problem started, and it cannot recover **even after the original cause is gone**, because the retry load is self-sustaining.
6. Callers' own thread pools fill with pending retries, so **they fail too** (O15.5), and the failure spreads upward (O15.11).

The mitigations:

- **Exponential backoff with jitter** (O15.10) — the single most important.
- **A retry budget** — cap retries as a *fraction of total requests* (e.g. retries may not exceed 10% of traffic) rather than per-request. **This bounds the multiplier globally** and is far more effective than per-request limits, which each look reasonable in isolation.
- **Retry only at one layer.** Multi-layer retries multiply; picking one layer (usually the outermost, or the one closest to the failure) avoids it.
- **Circuit breakers** — stop calling entirely when the failure rate is high, which is the mechanism that actually lets the downstream recover (O15.11).
- **Don't retry non-retryable errors** — a 400 will fail identically every time (M2.8).
- **Deadline propagation** — don't retry when the caller's deadline has already passed.
- **Load shedding at the receiver** (O15.3) with a clear 429 and `Retry-After`.

**O15.10 — Jitter and why synchronised clients are dangerous**

Jitter is deliberate randomness added to timing.

**Why synchronisation happens**: clients that started together, or were all affected by the same event, do the same thing at the same time — retrying after a fixed backoff, refreshing a cache on a fixed TTL, polling on a fixed schedule, reconnecting after a shared outage, or running a cron at the top of the hour.

**Why it's dangerous**: the load arrives as a spike rather than spread out. **A thousand clients retrying after exactly 1 second produce a thousand simultaneous requests** — which can be far more than the service can take, causing another failure, another synchronised retry, and a self-sustaining oscillation. The system rings rather than recovers.

The instances worth naming: **retry storms** (O15.9); **cache stampedes** — a popular key expires and every request misses simultaneously and hits the database (M7.7); **reconnection storms** after a broker or database restart; **cron alignment** — everything scheduled at midnight; **certificate renewal** and **token refresh** all coming due together; and **metrics scrape alignment**.

The mitigations: **full jitter** on retries — `sleep = random(0, min(cap, base * 2^attempt))` — which is the AWS-recommended form and measurably better than fixed or partial jitter; **randomised cache TTLs** (a TTL of `300 ± 30` seconds); **staggered schedules** rather than the top of the hour; **randomised startup delays**; and **request coalescing** so concurrent misses for the same key result in one backend call.

The general principle: **any fixed interval shared by many clients is a synchronisation hazard.** Adding randomness costs nothing and removes an entire class of self-inflicted spike.

**O15.11 — Cascading failure and where to place the circuit breaker**

**Cascading failure**: one component's failure causes its callers to fail, which causes their callers to fail, propagating outward until the system is down.

The mechanism, and it's usually resource exhaustion rather than error propagation: service A calls slow service B. A's threads block waiting for B. **A's thread pool fills.** A can no longer serve *any* request — including ones that don't need B. A's callers now see A failing and their pools fill. The failure has propagated upward and outward.

**Where to place the circuit breaker: at the caller, around each dependency, individually.**

- **At the caller**, because the breaker's purpose is to protect *the caller* from a slow dependency by failing fast instead of blocking. A breaker at the callee protects the callee, which is load shedding (O15.3) — a different and complementary mechanism.
- **Around each dependency separately**, because a shared breaker means one failing dependency trips calls to healthy ones. This pairs with per-dependency bulkheads (O15.5).
- **At the boundary where a fallback exists** — a breaker is only useful if there's something to do when it's open: a cached value, a default, a degraded response (O15.7). **A breaker with no fallback just fails faster**, which is still valuable (it stops resource exhaustion) but much less so.

The mechanics: **closed** (normal), **open** (fail immediately without calling), **half-open** (allow a trickle to test recovery). The half-open state must be limited, or recovery attempts are themselves a thundering herd (O15.10).

The complementary controls that matter as much: **aggressive timeouts** — a breaker only trips after failures accumulate, and a timeout bounds each individual call (T7.6); **bulkheads** to contain the exhaustion (O15.5); and **load shedding at the callee** (O15.3). **Timeouts are the more fundamental control** — a system with no timeouts will cascade regardless of breakers, because threads block indefinitely.

**O15.12 — Availability vs consistency in a real design**

CAP stated properly: **during a network partition, you must choose between consistency and availability.** When there's no partition you can have both, so the tradeoff is specifically about partition behaviour — and the common misstatement ("pick two of three") obscures that.

A concrete design — **an account balance in a payments system across two regions:**

**Choosing consistency (CP)**: writes require a quorum. During a partition, the minority side **refuses writes**. No double-spend, no divergent balances, and **the service is unavailable in that region for the duration.** For a balance, this is usually correct: **an incorrect balance is worse than an unavailable one**, and it's a regulatory position as much as a technical one.

**Choosing availability (AP)**: both sides accept writes and reconcile later. The service stays up and **balances can diverge**, allowing an overdraft that shouldn't have been possible. Reconciliation is an application problem with no infrastructure solution (M9.8).

**The real design uses both, per operation:**

| Operation | Choice | Reasoning |
|---|---|---|
| Debit / balance check | **CP** | Correctness is non-negotiable; refuse rather than risk double-spend |
| Transaction history read | **AP** | Slightly stale history is acceptable |
| Fraud scoring | **AP** | Degrade to a cached model rather than block payments (O15.7) |
| Audit log write | **CP** | Must not be lost |
| Notification | **AP** | Delayed is fine |

The senior framing: **this is not a system-wide choice, it's a per-operation one**, and the interesting work is classifying operations by what failure they can tolerate. **PACELC** is worth naming as the extension — even without a partition (Else), you trade **latency** against **consistency**, which is the tradeoff you're actually making every day when choosing between a synchronous cross-region write and an asynchronous one.

---

## O16. Judgement

**O16.1 — Observability cost drivers and reducing spend without losing signal**

The drivers, roughly in order:

1. **Log ingestion volume** (O4.7) — usually the largest single line.
2. **Metric cardinality** (O1.3) — series count, often billed directly.
3. **Trace volume** (O5.9) and retention.
4. **Retention duration** across all three (O2.8, O4.8).
5. **Query cost** on platforms billing by data scanned.
6. **Self-hosted infrastructure** if you build (O1.8).

The reductions that preserve signal:

- **Turn off debug logging in production.** Consistently the biggest single win and consistently present.
- **Stop logging health checks and readiness probes.**
- **Find and fix the top cardinality offenders** — usually one or two labels (an unnormalised URL path, a container ID) creating most of the series. `topk` on series count by metric name finds them in a minute.
- **Drop unused metrics at ingestion** (O3.2). Verbose exporters emit hundreds of metrics of which you query a handful.
- **Tail-based sampling** so you keep errors and slow traces and drop the boring successes (O5.4) — dramatic volume reduction with almost no diagnostic loss.
- **Tier retention** rather than keeping everything hot (O4.8).
- **Route high-volume, rarely-queried logs to object storage** and query with Athena (A9.9).
- **Convert count-only logs into metrics** (O4.11).

The framing that makes this a senior answer: **optimise signal per pound, not volume.** A blanket 50% cut applied uniformly removes signal proportionally; **targeted removal of the top talkers typically cuts 40–60% while removing almost no diagnostic value**, because telemetry volume is heavily concentrated. And **attribute the cost to teams** — observability spend that appears as one central line item is nobody's problem; per-team attribution changes behaviour (A12.2).

**O16.2 — Deciding what's worth instrumenting**

The test: **would this change a decision, or answer a question I'll actually be asked?**

**Worth instrumenting:**

- **Everything on the critical user path** — RED for every service (O2.9), and the operations that constitute the user's experience.
- **Every boundary** — inbound and outbound calls, database queries, queue operations. Boundaries are where the failures and the latency live, and auto-instrumentation gets most of them free (O6.2).
- **Business-meaningful operations** with business dimensions (O6.3) — payments, sign-ups, model inference — because those are the questions leadership asks and the ones that connect telemetry to impact.
- **Saturation signals for every bounded resource** (O2.10) — pools, queues, quotas (O14.7). Cheap, and they're the leading indicators.
- **Anything you've been burned by**, which is the empirical version of O1.6.
- **Error paths and fallbacks**, which are otherwise invisible until they fail.

**Not worth it:**

- **Every function.** Overhead (O5.9), noise, and unreadable traces.
- **Metrics nobody queries** — audit them and remove the ones with no dashboard, no alert, and no query history.
- **High-cardinality data as metrics** (O1.3) — it belongs on spans.
- **Duplicating what's free** — re-implementing what auto-instrumentation or the platform already provides.
- **Detail for a hypothetical future need** with no plausible question attached.

The discriminating question when someone proposes a new metric: **"what alert or decision will use this?"** If there isn't an answer, it's probably a span attribute or a log field instead. And **instrument the boundaries generously and the internals sparingly** is the heuristic that gets most of the value for a fraction of the cost.

**O16.3 — The platform team's observability contract**

**The platform team provides:**

- **A telemetry pipeline that just works** — collectors deployed, enrichment automatic (O4.4, O6.4), backends running with a stated SLO.
- **Standard instrumentation** — libraries or a base image with OTel configured, semantic conventions applied, trace-ID-in-logs wired up (O4.3). **The single highest-leverage deliverable**, because it makes correct instrumentation the default rather than a per-team project.
- **Standard dashboards**, templated so every service gets RED and USE views without building them (O7.3, O7.6).
- **Alerting infrastructure** — Alertmanager, routing, on-call integration (O8.3), and SLO alerting templates (O8.4).
- **Documented conventions** — metric naming, label standards, required attributes (O6.6).
- **Cost visibility per team** (O16.1).
- **Observability for platform components teams depend on** (O6.8).

**Application teams provide:**

- **Instrumentation of their own business logic** (O6.3) — the platform can't know what matters in their domain.
- **Meaningful SLOs and alerts** on their own services, tuned to their business impact (T7.2).
- **Cardinality discipline** within the documented conventions.
- **Runbooks for their alerts** (O8.6).
- **Responding to their own alerts** — the platform team is not on call for application errors.
- **Managing their own telemetry cost** against an attributed budget.

The boundary that must be explicit: **the platform owns the pipeline and the defaults; teams own what they emit and what they do about it.** Ambiguity here produces the failure where the platform team is asked to diagnose every application problem because they're the ones who "own monitoring" (K13.4, TF8.8).

**O16.4 — Assessing an existing stack and prioritising improvements**

The assessment, structured as questions:

1. **Can you answer basic incident questions?** Try it: pick a recent incident and see whether the telemetry could have diagnosed it. **This is the most informative single exercise** and it's better than any checklist.
2. **Coverage** — do all services emit RED? Are all resources covered by USE? Are there blind spots (batch jobs, third parties, the edge)?
3. **Correlation** — can you go from a metric to a trace to a log for one request (O1.7)? If not, that's usually the highest-value gap.
4. **Alerting health** — page volume, actioned rate, alert-to-incident ratio, permanent silences (O8.7).
5. **SLOs** — do they exist, are they meaningful, are they measured (T7.2)?
6. **Cost** — what is it, what drives it, is it attributed (O16.1)?
7. **Usage** — which dashboards are actually opened (O7.7)? Which metrics are queried?
8. **Cardinality and stability** — is the backend healthy, or does it fall over under load?

The prioritisation, and the ordering matters:

1. **Fix the blind spots that caused recent incidents.** Evidence-driven, and it earns credibility.
2. **Get correlation working** if it isn't — the multiplier on everything else.
3. **Fix alerting noise**, because a pager nobody reads negates all other investment.
4. **Establish SLOs** for the top services, which reframes everything else around user impact.
5. **Standardise instrumentation** for consistency (O16.3).
6. **Then cost optimisation**, which is easier once you know what's used.

The framing: **prioritise by what would have shortened your last five incidents**, not by a maturity model. That grounds the work in evidence and is far more persuasive than a capability gap analysis.

**O16.5 — Instrumenting a system you didn't build**

The approach, working outside-in because you can't start from the code:

1. **Start black-box** (O1.5). Synthetic checks against the user-facing endpoints give you availability and latency **without touching the system at all**, and they establish a baseline immediately.
2. **Instrument the edges** — the load balancer, ingress, or API gateway gives request rate, error rate, and latency per route with no code changes. **Often 80% of the RED signal for zero application risk.**
3. **Collect what already exists** — most systems emit logs and many expose metrics or JMX. Collect and enrich them before adding anything (O4.4).
4. **Add auto-instrumentation** (O6.2) — an agent or sidecar gives traces and the call graph without code changes, which is the fastest route to understanding the architecture.
5. **Infrastructure and resource metrics** (O2.10) — free, and they cover the saturation signals.
6. **Then targeted manual instrumentation** (O6.3), guided by what the earlier steps revealed as important or opaque.

The specific value of tracing here: **the service map derived from traces is often the only accurate architecture documentation** (O5.8). For an inherited system, that alone justifies the work — you learn what calls what, in reality rather than according to a diagram that's three years old.

The additional considerations: **be cautious about overhead** on a system whose performance characteristics you don't know (O5.9) — roll out to one instance first. **Find the people who ran it** and ask what breaks; their knowledge is the fastest route to knowing what to instrument. And **document as you go**, because you're building the understanding the organisation lacks.

**O16.6 — When "just add monitoring" is the wrong answer**

The cases:

- **When the fix is to remove the failure mode, not to watch it.** A recurring disk-full incident gets an alert; the actual fix is log rotation or retention (O4.8). **Monitoring a preventable problem is choosing to keep having it**, with a page attached.
- **When it's a substitute for fixing the underlying issue.** "We'll add an alert for when it happens again" is often a way of closing an incident without addressing the cause. The alert becomes permanent noise (O8.7).
- **When the problem is understanding, not visibility.** If nobody knows what the system does, more telemetry produces more data nobody can interpret. Sometimes the answer is documentation, a design review, or simplification.
- **When it adds alert load without adding decisions.** Every alert costs attention permanently (O8.7).
- **When automation is the right answer.** If the response to an alert is always the same action, automate the action (K7, A9.7). A page whose runbook is one command is a task, not an incident.
- **When it's a proxy for a missing SLO.** Adding twelve metrics because nobody has agreed what "healthy" means produces twelve opinions rather than one target (T7.2).
- **When the cost exceeds the value** — instrumenting a low-value path at high cardinality (O16.1).

The framing to give: **observability tells you what is happening; it does not make the system better.** Reaching for monitoring reflexively is a way of appearing to act. **The question to ask after any incident is "what would have prevented this?" before "what would have detected it?"** — detection matters, and it's the second question.

**O16.7 — How you'd know your observability is actually working**

The measures — and the point is that observability should itself be evaluated with evidence:

- **MTTD and MTTR trends.** Are you detecting faster and resolving faster over time? The single most direct measure.
- **How incidents are detected.** **What fraction are found by monitoring versus reported by users or customers?** A high customer-reported fraction is the clearest possible evidence of a gap, and it's a number most organisations could produce and don't.
- **Time from alert to diagnosis.** If responders spend 40 minutes working out *what* is wrong before starting to fix it, the telemetry isn't serving them.
- **Post-incident findings.** How often does a review conclude "we didn't have the data"? That's the direct failure signal (O1.6), and tracking it over time shows whether you're closing gaps.
- **Alert quality** — actioned rate, pages per rotation, false-positive rate (O8.7).
- **Usage** — are dashboards opened, are metrics queried, do people use traces during incidents (O7.7)? Unused telemetry is cost without benefit.
- **Can a new team member debug an unfamiliar service?** A practical, revealing test of whether the tooling and conventions actually work.
- **Cost per unit of value** — spend relative to system size, trending (O16.1).

The exercise worth proposing: **take a recent incident and ask whether the telemetry available at the time could have diagnosed it without the tribal knowledge people brought.** Do that for the last five incidents and you have a concrete, prioritised improvement list (O16.4) — which is more useful than any maturity assessment.

The framing that lands: **the purpose of observability is to shorten the time between something breaking and someone understanding why.** Every measure above is a proxy for that, and if none of them are improving, the investment isn't working regardless of how much telemetry you're collecting.

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 145 items this is the largest domain in the matrix and reading it end to end produces recognition rather than recall.
- **Which half matters depends on the role.** For a platform or AI-platform position, **O1–O8 and O16** carry most of the weight — telemetry design, instrumentation strategy, and the judgement items. For an SRE position, **O9–O15** does — systems performance and reliability patterns.
- **O9–O12 are the strongest discriminators** and the hardest to learn from documentation. CPU steal (O9.3), cgroup throttling with idle host CPU (O9.4), page cache versus available memory (O10.2), the utilisation/queueing relationship (O12.1), tail amplification (O12.4), and coordinated omission (O12.5) are all things people either know from having met them or don't.
- **The failure modes are the part that reads as experience.** A health check that verifies dependencies taking down every instance at once (O15.8, O15.11), a burst-credit cliff with every instantaneous metric looking normal (O11.5), a 1% head-based sample discarding 99% of your errors (O5.4), summaries whose percentiles cannot be aggregated (O2.4), and `rate()` on a gauge fabricating increases (O3.5).
- **Cross-references are dense throughout** — T7 for alerting philosophy and SLOs, A9 for CloudWatch specifics, K6 and K9 for the Kubernetes resource and debugging equivalents, M6 and M10 for consumer lag as a saturation signal, and A11.9 for quotas as a capacity failure. Interviewers move between these constantly, and O12.1 in particular underpins arguments in half the other domains.
