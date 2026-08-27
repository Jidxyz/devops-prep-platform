# Messaging, Queues & Streaming — Answer Key

Companion to Domain 10 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **AWS service configuration is A13** (SQS visibility timeouts, SNS fan-out, EventBridge rules). This domain is the concepts underneath, with Kafka covered in depth. Where a topic overlaps, the answer covers the conceptual half and points to A13 for the service specifics.

Three notes on how this domain is interviewed:

- **M2 (delivery semantics) is the section that separates people who have run messaging from people who have used it.** At-least-once, idempotency, the dual-write problem, and the outbox pattern are asked constantly, and the answers are structural rather than tool-specific — they transfer to any broker.
- **M6 (Kafka consumers) and M10 (troubleshooting) are where practical Kafka experience shows.** Consumer lag diagnosis, rebalance storms, and offset commit semantics are the day-to-day reality of operating Kafka, and they're hard to answer convincingly from reading.
- **M12 rewards the case against.** "When is Kafka overkill" and "what does running it yourself actually cost" are questions where the expected senior answer is a genuine no, with numbers.

---

## M1. Fundamentals & patterns

**M1.1 — Why introduce a broker rather than call synchronously**

The reasons, in rough order of how often they're the actual driver:

- **Availability decoupling.** With a synchronous call, if the downstream service is down, the upstream call fails. With a broker, the producer writes to the queue and carries on; the consumer processes when it recovers. **The producer's availability no longer depends on the consumer's** (M1.6).
- **Load levelling.** A traffic spike that would overwhelm a downstream service becomes a queue that drains at the consumer's own rate. The queue absorbs the burst rather than the database doing so.
- **Temporal decoupling.** The work doesn't have to happen now. A user's HTTP request returns as soon as the event is durably enqueued, and the expensive work — sending email, generating a report, running fraud checks — happens afterwards. Latency for the user drops sharply.
- **Fan-out.** One event, many independent consumers, without the producer knowing who they are (M1.2). Adding a consumer requires no change to the producer, which is the property that makes event-driven architecture scale organisationally.
- **Independent scaling.** Producer and consumer scale on their own characteristics.
- **Retry and durability.** The broker holds the message until it's successfully processed, so a transient failure doesn't lose the work — which is much harder to guarantee with a synchronous call plus in-process retry.

The framing that makes this a senior answer: **name the specific problem you're solving**, because "we use a broker" without one produces the costs in M1.8 for no benefit. The strongest single justification is usually availability decoupling or load levelling; "loose coupling" as an abstract virtue is the weakest, because it's often achievable more cheaply.

**M1.2 — Queue (point-to-point) vs pub/sub (fan-out)**

- **Queue** — a message goes to **exactly one** consumer. Multiple consumers compete for messages (M1.9), which is how you scale throughput. The message is removed once processed. SQS, RabbitMQ work queues.
- **Pub/sub** — a message goes to **every** subscriber, each getting its own copy. Adding a subscriber doesn't reduce what others receive. SNS, EventBridge, Kafka consumer groups.

The distinction that matters in design: **a queue distributes work; pub/sub distributes information.** "Process this payment" should go to exactly one worker — processing it twice is a bug. "A payment was processed" may interest the ledger, the notification service, the analytics pipeline, and the fraud system, none of which should prevent the others from seeing it.

The composite pattern worth naming: **pub/sub into per-consumer queues** — SNS fanning out to several SQS queues (A13.2), or Kafka consumer groups where each group is a queue over the same log. This gives you both properties: every consumer *group* gets every message, and within a group the messages are distributed across workers. That's the shape most real systems use, and being able to describe it as a composition rather than a choice is the better answer.

Kafka is worth noting as unifying both: a topic is pub/sub across consumer groups and a competing-consumer queue within a group (M6.1).

**M1.3 — The log/stream model and how it differs from a queue**

A **log** is an append-only, ordered, durable sequence of records. Consumers read at their own position (an **offset**) and **reading does not remove the record** — it stays until retention expires (M4.8).

The differences from a queue, which are the substance:

| | Queue | Log |
|---|---|---|
| After consumption | Message deleted | Record retained |
| Position | Broker tracks per-message | Consumer tracks an offset |
| Replay | Not possible (or awkward) | Fundamental — just reset the offset |
| Multiple independent readers | Each needs its own queue | Each has its own offset on the same data |
| Ordering | Per-queue, and lost with parallelism | Strict per-partition |
| Scaling reads | Adding consumers splits the work | Adding consumer groups is free |

**The three properties that follow, and which justify choosing a log:**

1. **Replay.** You can reprocess history — after fixing a bug, when adding a new consumer that needs to build state from the beginning, or to rebuild a derived store (M2.10). A queue cannot do this because the data is gone.
2. **Multiple independent consumers over the same data**, each at their own position, without duplicating storage.
3. **The log is a source of truth**, not just a transport. That's what makes event sourcing (M8.7) and stream-table duality (M8.5) possible.

The costs: **storage** (you're keeping everything for the retention period), **operational complexity**, and **the consumer owns its position**, so offset management becomes your problem (M6.5).

**M1.4 — Command vs event, and why it shapes the design**

- **A command** is an instruction to do something: `ProcessPayment`, `SendEmail`, `CancelOrder`. Imperative, addressed to a specific handler, expects to be acted upon, and the sender cares that it succeeds.
- **An event** is a statement that something happened: `PaymentProcessed`, `OrderCancelled`. Past tense, addressed to nobody in particular, and the publisher doesn't know or care who reacts.

**Why the distinction shapes the design:**

- **Coupling direction.** A command couples the sender to the receiver — the sender must know a handler exists and what it's called. An event couples the receiver to the sender's *schema* only. So **events allow new consumers without changing producers**, which is the property that makes event-driven architecture scale across teams (M12.4).
- **Ownership of failure.** If a command fails, the sender usually needs to know and handle it. If an event's consumer fails, that's the consumer's problem — the fact still happened.
- **Cardinality.** A command should have exactly one handler; an event may have zero or many.
- **Schema evolution.** An event describes a fact and should be complete and self-describing; a command describes an intent and can be narrower.

The failure mode to name: **events named like commands** — publishing `SendWelcomeEmail` to a topic. That's a command wearing an event's clothes, and it re-couples the producer to a specific consumer's responsibility. The producer now knows an email service exists, which is exactly what you were trying to avoid. The corrected version publishes `UserRegistered` and lets the email service decide it cares.

**M1.5 — Choreography vs orchestration**

- **Orchestration** — a central coordinator holds the process definition and invokes each step. Step Functions (A13.6), a saga orchestrator, a workflow engine.
- **Choreography** — each service reacts to events and emits its own; no central controller.

The tradeoff:

**Orchestration wins when** the process has meaningful state and failure semantics — retries per step, compensating actions, timeouts, human approval. **You can answer "where is order 12345 right now"** from the orchestrator's execution history; with choreography that's a distributed-tracing exercise (M10.6). And the process is visible in one place, which matters when it's a business process people reason about and change.

**Choreography wins on autonomy.** Adding a consumer requires no change to any existing service. Teams deploy independently. There's no central component whose failure stops everything, and no team owning a workflow definition that everyone else needs changed.

The costs of each: orchestration introduces a coupling point and a component that must be available; choreography means **no single place describes the process**, so understanding "what happens when an order is placed" requires reading every service, and emergent behaviour is genuinely hard to reason about.

The judgement to state: **orchestrate within a bounded context, choreograph between them.** Most real systems use both — a payment flow orchestrated internally because its failure handling is intricate, with a `PaymentCompleted` event choreographed outward to whoever cares. And the practical warning: **choreography's failure mode is that nobody can explain the system anymore**, which arrives gradually and is expensive to reverse (M12.4).

**M1.6 — How a broker decouples availability**

With a synchronous call, the caller's availability is the *product* of its own and every downstream dependency's. Three services at 99.9% in a chain give 99.7% — availability degrades multiplicatively with depth.

A broker breaks the chain: the producer's success depends only on **the broker accepting the message durably**. If the consumer is down, messages accumulate; when it recovers, it drains. The producer never knew.

The important qualifications, which is where a good answer distinguishes itself:

- **You've moved the dependency, not removed it.** The producer now depends on the *broker's* availability, which had better be higher than the consumer's. A broker with worse availability than the service it fronts makes things worse.
- **The work is delayed, not done.** For anything the user is waiting on, "the message was accepted" is not "the thing happened". If the consumer is down for two hours, the emails go out two hours late, and whether that's acceptable is a product decision.
- **The queue is not infinite.** Extended consumer downtime means unbounded growth: storage, cost, and eventually rejection or eviction (M1.7). Decoupling buys time proportional to your queue capacity, not indefinite immunity.
- **Recovery is a thundering herd.** When the consumer comes back it faces the entire backlog, which can immediately overwhelm it and whatever it depends on (M10.10).

So the honest framing: **a broker converts a hard failure into a latency problem with a time limit.** That's a very good trade for most work, and it's not the same as making the failure disappear.

**M1.7 — Backpressure and what happens when consumers can't keep up**

Backpressure is the mechanism by which a slow consumer causes the producer to slow down. The problem: **an asynchronous broker is designed to break that feedback loop**, so by default there is no backpressure — the producer keeps producing and the queue grows.

What actually happens as the queue grows:

1. **Lag increases** — messages sit longer, so the end-to-end latency of whatever the message represents grows. Often the first user-visible symptom, and often mis-diagnosed because the producer is fine.
2. **Storage and cost grow.**
3. **Then a limit is hit**, and what happens depends on the broker: SQS retains for up to 14 days then **silently drops**; Kafka evicts by retention policy, so a consumer that falls further behind than the retention window **loses data permanently** (M4.8) — the worst version, because it's silent; RabbitMQ can hit memory or disk limits and block producers or apply overflow policies.

**Mechanisms that reintroduce backpressure**, which is what a good answer covers:

- **Bounded queues that reject or block producers** when full — RabbitMQ's `max-length` with `overflow: reject-publish`. This propagates the pressure upstream, which is often exactly what you want.
- **Rate limiting at the producer**, based on observed lag.
- **Scaling consumers automatically on queue depth** (K7.1, A4.3) — the standard cloud answer, and it works until you hit the partition limit (M6.2) or a downstream bottleneck.
- **Load shedding** — deliberately dropping or rejecting low-value messages to protect the system (M10.10).

The design point to state: **decide the behaviour under overload deliberately.** The default — grow until something breaks — is a decision made by omission, and the failure is usually silent data loss at exactly the moment you can least afford it.

**M1.8 — The cost: eventual consistency, debugging, operations**

The honest costs, which any advocate should be able to name:

- **Eventual consistency.** The write succeeded and the read doesn't reflect it yet. A user updates their profile and immediately sees the old value; an order exists but doesn't appear in the list. **This propagates into product decisions and UI design**, not just architecture — and teams routinely underestimate how much of it leaks to users.
- **Debugging is genuinely harder.** A synchronous failure gives you a stack trace. An asynchronous failure gives you "the email never arrived" and a search across producer logs, broker state, consumer logs, and a DLQ, potentially hours later. Distributed tracing (M10.6) is not optional here — it's the thing that makes the system debuggable at all.
- **Operational burden.** The broker is now a tier-one dependency: capacity, upgrades, monitoring, security, DR. For Kafka specifically this is substantial (M12.3).
- **Correctness burden shifts to you.** At-least-once delivery means every consumer must be idempotent (M2.3). Ordering requires deliberate design (M2.4). Dual writes need the outbox pattern (M2.6). None of that is free and all of it is application work.
- **More failure modes**, and unfamiliar ones: poison messages (M2.7), rebalance storms (M6.3), partition skew (M5.4), consumer lag (M6.7).
- **Testing is harder** — asynchronous, ordering-dependent, timing-sensitive integration tests are flaky in ways synchronous ones aren't.

The framing: **these costs are paid continuously by everyone who touches the system, while the benefits accrue at specific points.** That asymmetry is why "introduce a broker" should be a decision with a named problem behind it (M1.1, M1.10).

**M1.9 — Competing consumers and how throughput scales**

Multiple consumers read from the same queue; each message goes to exactly one of them. Adding consumers increases throughput roughly linearly — this is the standard scale-out pattern for queue-based work.

What actually limits it, in order:

- **The downstream dependency.** Ten consumers all writing to one database gets you database contention, not ten times the throughput. **This is the most common real limit** and the one people miss — scaling consumers moves the bottleneck rather than removing it.
- **The broker's partitioning.** In Kafka, consumers beyond the partition count sit idle (M6.2) — a hard ceiling. SQS has no such limit, which is a genuine advantage for pure work queues.
- **Message ordering requirements.** Competing consumers process concurrently, so ordering is lost. If you need ordering, you need partitioning by key, which caps parallelism at the number of distinct keys (M2.5).
- **Per-message cost** — if each message takes 500ms of I/O wait, concurrency within each consumer matters as much as consumer count.

The correctness consequence to name: **competing consumers means concurrent processing of related messages.** Two messages about the same order processed simultaneously by different workers is a race condition, and the mitigations are partitioning by key so related messages go to one consumer, or optimistic locking in the datastore.

**M1.10 — When synchronous request/response is simply better**

The cases, and being willing to argue this is a positive signal:

- **The caller needs the result to continue.** Fetching a user's balance, validating a card, checking authorisation. Making that asynchronous means inventing a correlation and callback mechanism to rebuild what a function call gave you for free.
- **The operation must be immediately consistent.** Some invariants genuinely cannot tolerate a window — a strict balance check before a debit, uniqueness enforcement.
- **The failure needs to reach the user now.** "Your card was declined" is far better returned synchronously than as an email ten seconds later.
- **The system is small.** Two services with one integration point do not need a broker; they need an HTTP call. The broker's operational cost (M1.8) is fixed and only amortises over scale.
- **Debuggability matters more than resilience.** A synchronous call with a trace is enormously easier to reason about, and for a small team that's a real consideration.
- **Low, predictable volume** with no spikes — load levelling buys nothing.

The strongest version of the argument: **asynchronous messaging is a distributed systems problem you're choosing to take on.** It brings eventual consistency, idempotency requirements, ordering concerns, and a new operational dependency. If the problem it solves isn't one you actually have, you've bought all the cost and none of the benefit — and "we might need it later" is not a problem you have.

The pragmatic middle ground worth naming: **synchronous for the request path, asynchronous for the consequences.** Validate and persist the order synchronously so the user gets an immediate answer; publish `OrderPlaced` and let the email, analytics, and fulfilment happen asynchronously. That gets you both properties and is the shape most well-designed systems settle on.

---

## M2. Delivery semantics & correctness

**M2.1 — At-most-once, at-least-once, exactly-once**

- **At-most-once** — the message is delivered zero or one times. Achieved by acknowledging *before* processing: if the consumer crashes mid-work, the message is already acked and is lost. Acceptable only where loss is genuinely tolerable (some metrics, some telemetry).
- **At-least-once** — delivered one or more times. Achieved by acknowledging *after* processing: if the consumer crashes before acking, the message is redelivered. **Duplicates are possible; loss is not.**
- **Exactly-once** — delivered and processed precisely once.

**Why exactly-once is contested**, which is the point of the item:

The impossibility argument: in a distributed system, the consumer and the broker communicate over an unreliable network. After processing, the consumer sends an ack that may be lost. The broker cannot distinguish "the consumer processed it and the ack was lost" from "the consumer died before processing". It must choose: redeliver (risking a duplicate) or not (risking loss). **There is no third option**, and this is a consequence of the Two Generals problem, not an implementation gap.

What systems that claim exactly-once actually provide:

- **Kafka's exactly-once semantics** are real but scoped: **atomicity across a read-process-write cycle within Kafka**, via idempotent producers and transactions (M5.6, M5.7). It guarantees the *effects* appear once in Kafka. It does not extend to a side effect outside Kafka — if your consumer writes to Postgres and calls a payment API, exactly-once does not cover those.
- **Effectively-once through idempotency** — the message may be delivered many times, but processing it repeatedly produces the same state (M2.3). This is what everyone actually builds.

The answer that lands: **"exactly-once delivery is not achievable; exactly-once *processing* is, and you achieve it with at-least-once delivery plus an idempotent consumer."** Distinguishing delivery from processing is the whole insight.

**M2.2 — Why at-least-once is the practical default**

Because the alternative is worse. At-most-once loses data on any consumer crash, which for anything meaningful — a payment, an order, an audit record — is unacceptable. At-least-once means duplicates, and **duplicates are a problem you can solve in the consumer** (M2.3), whereas loss is a problem you cannot solve anywhere.

So the trade is: **accept a solvable problem to avoid an unsolvable one.**

It's also what every mainstream broker gives you by default. SQS standard, SNS, EventBridge, and Kafka with default settings are all at-least-once. That's not a coincidence — it's the only sensible default.

The consequence to state clearly: **duplicates are not an edge case, they are normal.** They arise from visibility timeouts expiring (M3.1), redelivery after an ambiguous failure, network partitions where the ack is lost, consumer restarts and rebalances (M6.3), and producer retries (M5.8). A consumer that isn't idempotent is not "mostly fine" — it's a bug waiting for load.

**M2.3 — Designing an idempotent consumer**

An idempotent consumer produces the same end state whether it processes a message once or ten times.

The mechanisms, best to worst:

1. **Naturally idempotent operations.** `SET status = 'shipped'` is safe; `balance = balance + 100` is not. Where you can express the operation as setting an absolute value rather than applying a delta, do — it's free idempotency with no bookkeeping.
2. **An idempotency key with a conditional write.** The producer includes a unique, business-meaningful ID; the consumer records it on processing with a uniqueness constraint or conditional put. A duplicate fails the condition and is discarded.

```sql
BEGIN;
INSERT INTO processed_messages (message_id) VALUES ($1);  -- unique constraint
UPDATE accounts SET balance = balance - $2 WHERE id = $3;
COMMIT;
```

3. **Optimistic concurrency** with a version number — the update applies only if the version matches, so a replay of an already-applied change is a no-op.
4. **Upserts** keyed on a business identifier.

**The critical detail, and the one people get wrong: the idempotency record and the business effect must be committed atomically.** If you write the business change and then separately record the message ID, a crash between them means reprocessing duplicates the effect. If you record the ID first and then crash, the message is marked processed but the work never happened — silent loss. **The same transaction, or it doesn't work.** Where the effect is in an external system that can't share a transaction, you're back to the dual-write problem (M2.6).

Other practicalities: **the dedup store needs a retention policy** or it grows forever — bound it by the maximum plausible redelivery window plus margin, and note that this means idempotency is time-bounded, not permanent. And **the key must come from the producer and be stable across retries** — generating it in the consumer defeats the purpose.

In a payments context this stops being architectural nicety: a duplicated debit is a customer-impacting, regulator-visible incident, which is why idempotency keys are standard in payment APIs (A13.5).

**M2.4 — Ordering guarantees and their scope**

The scopes, and being precise about them is the item:

- **Global ordering** — every message in the system in a total order. Essentially no distributed broker provides this at scale, because it requires serialising everything through one point.
- **Per-partition / per-message-group** — Kafka guarantees order within a partition (M4.2); SQS FIFO guarantees it within a message group ID (M3.6). **This is what "ordered" means in practice.**
- **Per-queue** — RabbitMQ delivers in order from a queue, but **that guarantee evaporates with multiple consumers** or with redelivery, so it's weaker than it sounds.
- **No ordering** — SQS standard, SNS. Best-effort at most.

The practical points:

- **The key determines the scope.** Kafka orders by partition, and the partition is chosen by the key hash (M5.2), so **ordering is per-key, and choosing the key is choosing the ordering domain.** Key by `order_id` and all events for one order are ordered; events for different orders are not, which is almost always exactly what you want.
- **Ordering is lost the moment you process concurrently** within the ordering domain — competing consumers (M1.9), or a consumer that hands messages to a thread pool.
- **Retries break ordering** even in an ordered system: a failed message retried later arrives after messages that came behind it (M5.8, M2.8).

The design guidance: **ask what actually needs ordering.** Usually it's "events about the same entity", not "all events". Scoping ordering to an entity gives you correctness and parallelism simultaneously (M2.5). Demanding global ordering is nearly always a requirement that hasn't been examined.

**M2.5 — Why global ordering and parallelism are in tension**

The argument is short and worth being able to state cleanly: **strict ordering requires that message N+1 is not processed until message N has completed. That is the definition of serial processing.** Any parallelism means two messages are in flight simultaneously, so their completion order is not guaranteed.

So there's a hard trade, and the only way to get both is to **partition the ordering domain**: split messages into independent streams, order strictly within each, and process the streams in parallel. Throughput scales with the number of partitions; ordering holds within each.

The consequences that follow:

- **The partition key determines both** your ordering guarantee and your maximum parallelism. Key by customer: ordered per customer, parallelism up to the number of customers (bounded by partitions, M4.11).
- **Skew wrecks it.** One dominant key means one partition carries most traffic and the parallelism is theoretical (M5.4).
- **A single message group in SQS FIFO serialises the whole queue** — the most common reason people conclude "FIFO is too slow" (M3.6).
- **Adding partitions later changes the key-to-partition mapping** and breaks ordering across the change (M4.11).

The senior framing: **global ordering is a requirement to be challenged, not accepted.** In most systems it's a proxy for "events about the same thing must not be reordered", which is a per-entity requirement and is cheap. Genuine global ordering means a single-threaded pipeline, and if it's truly needed, that's a significant architectural constraint that should be explicit.

**M2.6 — The dual-write problem and the transactional outbox**

**The problem**: a service must update its database *and* publish an event. These are two separate systems with no shared transaction.

```
BEGIN; UPDATE orders SET status='paid'; COMMIT;
publish(OrderPaid)                              // ← crash here
```

Whichever order you choose, a crash between them leaves the system inconsistent: the database says paid and no event was published (downstream never learns), or the event published and the transaction rolled back (downstream acts on something that didn't happen). **There is no ordering of two non-transactional writes that is safe**, and retry doesn't fix it — it just changes which inconsistency you get.

**The transactional outbox** solves it by making both writes one transaction:

1. In a **single database transaction**, update the business tables *and* insert the event into an `outbox` table.
2. A **separate relay process** reads unpublished rows from the outbox and publishes them to the broker, marking them sent.

```sql
BEGIN;
UPDATE orders SET status = 'paid' WHERE id = $1;
INSERT INTO outbox (id, aggregate_id, type, payload)
  VALUES (gen_random_uuid(), $1, 'OrderPaid', $2);
COMMIT;
```

Now atomicity is guaranteed by the database, which is the only place you had a transaction to begin with.

The relay can poll the table, or — better — read the database's write-ahead log via **CDC with Debezium** (M7.7), which avoids polling load and captures the event with the commit.

The properties to state: **the outbox gives at-least-once publishing, not exactly-once** — the relay can crash after publishing and before marking, so it republishes. Which is fine, because consumers are idempotent (M2.3). And **the outbox table needs cleanup** or it grows without bound.

The alternative worth naming: **listen-to-yourself** — publish the event first, and have the service consume its own event to perform the database write. Correct, and it makes the database update asynchronous, which is often a bigger change than teams want. The outbox is the mainstream answer.

**M2.7 — Poison messages and how they block progress**

A poison message is one the consumer cannot process successfully — a malformed payload, a schema it doesn't understand, a reference to a deleted entity, or a bug triggered by that specific content.

**Why it blocks progress** depends on the broker, and the difference matters:

- **In a queue** (SQS, RabbitMQ): the message fails, becomes visible again, is picked up, fails again — **an infinite loop consuming capacity and generating errors indefinitely**. Other messages still flow, but a share of your throughput is permanently wasted, and the error rate makes real problems invisible.
- **In a Kafka partition**: catastrophically worse. Offsets are sequential, so **the consumer cannot commit past the poison message.** It retries forever and **everything behind it in that partition is blocked** — lag grows without limit on that partition while others are fine. That distinctive signature (one partition's lag climbing, the rest healthy) is a strong diagnostic (M6.7).
- **In a Lambda event-source mapping on a stream**: the batch is retried until success or expiry, blocking the shard (A4.7).

**The handling** (M2.9, M6.11): a retry limit, then move the message aside — a DLQ in queue systems, or in Kafka an explicit error topic the consumer produces to before committing the offset and moving on. Kafka has no native DLQ; you build it.

The design point: **decide the poison-message behaviour before you meet one.** The default in every system is "retry forever", which is never what you want, and discovering that during an incident with a blocked partition is a bad time to design the mechanism.

**M2.8 — Retry with backoff and a retry limit**

The design:

- **Retry, because most failures are transient** — a network blip, a brief database contention, a rate limit, a dependency restarting.
- **Exponential backoff**, because retrying immediately against an overloaded dependency makes it worse. 1s, 2s, 4s, 8s, capped.
- **Jitter**, because synchronised retries from many consumers produce a thundering herd that re-creates the outage. Full jitter (a random value between 0 and the backoff) is the standard recommendation and materially better than fixed backoff.
- **A retry limit**, after which the message goes to a DLQ (M2.9). Unlimited retry is how a poison message becomes an infinite loop (M2.7).

The distinctions that show experience:

- **Distinguish retryable from non-retryable failures.** A 503 from a downstream service is retryable. A malformed payload or a validation failure is not — retrying it will fail identically every time, so it should go straight to the DLQ without burning the retry budget. Classifying errors properly is the single biggest improvement most retry logic could make.
- **In-process retry vs redelivery.** Retrying within the consumer keeps the message in flight and consumes the visibility timeout (M3.1) — so an in-process retry loop can exceed it and cause a *concurrent* duplicate. Letting the broker redeliver is usually cleaner: fail fast, let the visibility timeout or `nack` return it.
- **Retry breaks ordering** (M2.4) — a retried message arrives after ones behind it. Where ordering matters, the choice is to block (halting the partition) or to accept reordering, and it should be a deliberate one.
- **Delayed retry queues** are the pattern for longer backoffs: publish to a delay queue (M3.9) with increasing delays rather than holding the message in flight.

**M2.9 — Dead-letter handling: who looks at it and when**

A DLQ receives messages that failed after the retry limit. The mechanics vary — SQS redrive policy with `maxReceiveCount` (A13.1, M3.4), RabbitMQ dead-letter exchanges, a custom error topic in Kafka.

**The technical part is easy; the item is really about the operational half**, which is where most implementations fail:

- **The DLQ must be monitored and alarmed on depth.** An unmonitored DLQ is a silent data-loss bucket. Discovering 40,000 messages that have been accumulating for a month is a genuinely common and unpleasant finding, and the messages may be past the point where reprocessing is meaningful.
- **It needs a named owner** — the team that owns the consumer, not a central platform team who cannot understand the payloads.
- **It needs an SLA.** "Look at the DLQ within one business day" is a real commitment; "someone will check it" is not.
- **It needs a documented triage procedure**: inspect the message, determine why it failed, then either fix and redrive, discard with a record, or escalate.
- **Redrive must be deliberate and safe** — redriving 10,000 messages into a live consumer can overwhelm it, and redriving messages that were poison for a reason simply reproduces the failure.

**Enrich the message when dead-lettering**: the original payload, the error, the stack trace, the retry count, a timestamp, and a trace ID (M10.6). A DLQ containing only the raw payload requires the triager to reconstruct why it failed, which is often impossible after the fact.

The framing: **a DLQ is a work queue for humans.** If nobody works it, you've built a place for data to go and be forgotten, which is worse than failing loudly because it looks like it's handled.

**M2.10 — Message replay: what makes it safe or unsafe**

Replay means reprocessing messages already processed — from a Kafka offset reset (M6.9), a DLQ redrive, or a log archive.

**Safe when:**

- **Consumers are idempotent** (M2.3), so reprocessing produces the same state. This is the prerequisite, and everything else is secondary.
- **The processing is a pure function of the message** — deriving a projection, rebuilding a search index, populating a cache.
- **Side effects are internal**, contained within systems you're deliberately rebuilding.

**Unsafe when:**

- **Processing has external side effects.** Replaying `OrderPlaced` sends the confirmation email again, charges the card again, calls the partner API again. **This is the big one**, and it's why replay must be designed for rather than assumed.
- **The consumer has been deployed since**, and now behaves differently — replaying old events through new logic may produce a state that never validly existed.
- **Downstream consumers also see the replay** and react as if the events are new — replaying into a shared topic broadcasts to everyone.
- **The events reference entities that no longer exist**, or reference state that has moved on.
- **Ordering relative to newer messages is wrong** — replaying old events interleaved with current traffic can apply a stale state after a newer one.

The design that makes replay usable: **separate the projection from the side effects.** Consumers that build state are replayable; consumers that send emails or call payment APIs are not, and should be guarded by an idempotency check or a replay flag that suppresses external actions. **Replaying into a separate topic or a separate consumer group** rather than the live one is the standard safe pattern, and worth naming.

**M2.11 — The saga pattern**

The problem: a business transaction spanning several services, none of which share a database, so there is no distributed transaction to roll back. (Two-phase commit exists and is avoided — it holds locks across services, blocks on coordinator failure, and doesn't scale.)

**A saga is a sequence of local transactions, each with a compensating action.** If step 4 fails, you execute the compensations for steps 3, 2, 1 in reverse.

```
Reserve inventory   → compensate: release inventory
Charge payment      → compensate: refund payment
Create shipment     → compensate: cancel shipment
```

Two forms:

- **Choreographed saga** — each service listens for the previous step's event and emits its own, including failure events that trigger compensation. No coordinator; harder to follow (M1.5).
- **Orchestrated saga** — a coordinator (Step Functions, a saga orchestrator) invokes each step and handles compensation. The process is visible in one place, which for anything with intricate failure handling is worth the coupling.

The properties that must be stated, because they're what makes sagas hard rather than just fiddly:

- **Compensation is not rollback.** A refund is not an un-charge — the charge happened, appeared on a statement, and is now followed by a refund. **The intermediate state was visible**, which has real business and regulatory consequences in a payments context.
- **Sagas are not isolated.** Other transactions can observe the partially-completed state. There is no ACID isolation across services, and designing for that visibility is part of the work (semantic locks, or marking records as pending).
- **Compensations can fail**, and must be retried and idempotent. A compensation that fails needs an escalation path, which usually means a human.
- **Some steps cannot be compensated** — an email sent, a partner notified. Order the saga so irreversible steps come last.

The alternative to consider first: **restructure so the transaction doesn't span services.** A saga is a real cost, and its need is often a signal that a service boundary is in the wrong place.

---

## M3. Queues

**M3.1 — Visibility timeout**

When a consumer receives a message it becomes **invisible to other consumers** for the visibility timeout. If the consumer deletes it within that window, it's gone. If not, it becomes visible again and is redelivered.

**What happens when processing outlasts it** — the message is redelivered **while the original consumer is still working on it**. Two consumers now process the same message concurrently, which is not the usual "duplicate on retry" case but a genuine race: two workers writing the same record at the same time. The symptoms are duplicated side effects and data corruption that looks nothing like a messaging problem.

Worse, it's self-reinforcing: the second consumer also takes longer than the timeout, so a third gets it. **A slow consumer produces exponentially growing duplicate processing**, and the queue appears to be doing enormous work while making no progress.

The handling:

- **Set the timeout above your worst-case processing time**, not your average. The p99, with margin.
- **Extend it dynamically for long jobs** — `ChangeMessageVisibility` (the heartbeat pattern), so you extend while working rather than setting a very long default. A long default delays recovery from a genuine consumer crash, so the heartbeat is the better answer for variable work.
- **Idempotency covers you** when it goes wrong (M2.3) — which is the real reason it matters that consumers are idempotent even in a "well-configured" system.
- **Monitor `ApproximateAgeOfOldestMessage` and receive counts**, because a rising receive count with no DLQ activity means messages are timing out repeatedly.

**M3.2 — Acknowledgement modes and when to ack**

- **Auto-ack / ack on delivery** — the broker considers the message handled as soon as it's sent. **At-most-once** (M2.1): a consumer crash loses the message. Fast, and appropriate only where loss is acceptable.
- **Manual ack after processing** — the consumer explicitly acknowledges once the work is committed. **At-least-once**: a crash before the ack means redelivery.
- **Nack / reject** — explicitly signal failure, with `requeue` deciding whether it returns to the queue or goes to a dead-letter exchange.

**When to ack: after the work is durably committed, not before, and not after side effects you can't undo.** The precise point matters — ack after the database transaction commits. Acking before means loss on crash; acking long after means holding the message in flight unnecessarily.

The subtleties:

- **Prefetch / `max-in-flight`** controls how many unacked messages a consumer holds. Too high and one slow consumer hoards messages while others idle — a real cause of apparent under-utilisation. Too low and you add a round trip per message.
- **Acking is not transactional with your database write** — this is the dual-write problem again (M2.6) in miniature. You commit the DB then ack; a crash between them means redelivery, which idempotency handles.
- **In Kafka the analogue is the offset commit** (M6.5), with the same before/after processing question and the same answers.

**M3.3 — SQS standard vs FIFO**

| | Standard | FIFO |
|---|---|---|
| Ordering | Best effort | Strict, per message group |
| Delivery | At-least-once | Exactly-once processing within the dedup window |
| Throughput | Effectively unlimited | 300 msg/s per group (3,000 with batching); high-throughput mode raises this substantially |
| Deduplication | None | 5-minute window, by dedup ID or content hash |
| Queue name | Any | Must end `.fifo` |

The nuances worth stating:

- **FIFO's "exactly-once" is scoped to a 5-minute deduplication window.** A duplicate arriving six minutes later is delivered. So it handles a retry storm; it does not remove the need for idempotent consumers (M2.3). Presenting FIFO as a substitute for idempotency is the common error.
- **Ordering is per message group, not per queue** (M3.6) — which is the feature that makes FIFO usable at all.
- **Standard's "best effort ordering" means no ordering.** Don't design against it.

The judgement to express: **standard SQS plus idempotent consumers is usually the better choice** — cheaper, faster, simpler, and no throughput ceiling. Reach for FIFO when you have a genuine per-entity ordering requirement, and be aware that choosing FIFO to avoid writing idempotency logic doesn't actually work (A13.1).

**M3.4 — DLQ with a sensible redrive policy**

```json
{
  "deadLetterTargetArn": "arn:aws:sqs:eu-west-1:111122223333:payments-dlq",
  "maxReceiveCount": 5
}
```

`maxReceiveCount` is the number of *receives*, not failures — so a message that times out (M3.1) counts toward it even without an explicit failure. Setting it too low means transient failures dead-letter prematurely; too high means a poison message burns capacity for a long time. Three to five is a reasonable default for work with meaningful retries, and lower where each attempt is expensive.

Redriving:

```bash
aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:eu-west-1:111122223333:payments-dlq \
  --destination-arn arn:aws:sqs:eu-west-1:111122223333:payments \
  --max-number-of-messages-per-second 10
```

The details that matter: **rate-limit the redrive** — dumping the whole DLQ back into a live consumer can overwhelm it or its dependencies (M10.10). **Fix the cause first**, or you simply refill the DLQ. **The DLQ needs the same retention consideration** — SQS's 14-day maximum means messages sitting in a DLQ for two weeks disappear, which is silent data loss from a queue that exists to prevent it. And **the DLQ's own redrive policy should be absent**, or you get a DLQ for the DLQ.

The operational half is M2.9, and it's the half that determines whether any of this is useful.

**M3.5 — Long polling vs short polling**

- **Short polling** — the request samples a subset of servers and returns immediately, possibly empty even when messages exist. Repeated empty responses cost API calls.
- **Long polling** — the request waits up to `WaitTimeSeconds` (max 20) for a message to arrive, returning as soon as one does.

**Use long polling essentially always.** It reduces empty receives (which are billed), reduces latency (the message is returned the instant it arrives rather than on the next poll), and queries all servers so it doesn't return empty when messages exist.

Enable it per-queue with `ReceiveMessageWaitTimeSeconds` or per-request. The only reason to use short polling is a specific need to return immediately regardless — which is rare and usually a design smell.

The cost consequence is real at scale: a fleet of consumers short-polling an empty queue generates a continuous stream of billed empty receives, and it's a recognisable line item in an SQS bill (A12.3).

**M3.6 — Message groups and how FIFO parallelises**

In SQS FIFO, every message carries a `MessageGroupId`. **Ordering is guaranteed within a group; different groups are processed independently and concurrently.**

That's the mechanism that makes FIFO usable: with `MessageGroupId = order_id`, all messages for one order are strictly ordered, and thousands of orders process in parallel. Throughput scales with the number of active groups.

The failure that follows directly: **a single group ID for the whole queue serialises everything.** Throughput collapses to one message at a time, and this is the number one reason people report "FIFO is too slow" — the group ID was set to a constant, or omitted and defaulted.

The other behaviour to know: **a message that fails blocks its group.** Since order must be preserved within the group, the broker won't deliver the next message in that group until the current one is deleted or dead-lettered. So one poison message stalls that entity's stream (M2.7) while other groups continue — which is correct behaviour and a diagnostic signature.

The design guidance mirrors Kafka's partition key (M5.3): **choose the group ID as the smallest scope that satisfies your ordering requirement**, usually a per-entity identifier. Choosing something coarse (a tenant, a region, a message type) buys ordering you don't need at a large throughput cost.

**M3.7 — RabbitMQ's model**

The components:

- **Producers publish to an exchange**, never directly to a queue.
- **An exchange routes** according to its type and its bindings.
- **A binding** connects an exchange to a queue, with a **routing key** or pattern.
- **Consumers read from queues.**

Exchange types:

- **Direct** — routes to queues whose binding key exactly matches the message's routing key.
- **Topic** — pattern matching with wildcards (`payments.*.completed`, `#.error`). The most flexible and the most used.
- **Fanout** — routes to every bound queue, ignoring the routing key. Pub/sub (M1.2).
- **Headers** — routes on message header attributes rather than the routing key.

The insight that makes the model click: **the producer knows only the exchange and the routing key; the consumer owns the queue and its binding.** So consumers decide what they receive, and adding a consumer means declaring a queue and a binding — with no change to the producer. That's a genuinely elegant separation and it's why RabbitMQ's routing is more expressive than SQS's (which has none) or Kafka's (which is topic-and-partition only).

Other essentials: **durability** must be set on exchanges, queues, and messages independently — a durable queue holding non-persistent messages loses them on restart, which surprises people. **Quorum queues** are the current recommendation for replicated, durable queues (classic mirrored queues are deprecated). And **the queue is the unit of consumption**, so competing consumers on one queue is the work-queue pattern (M1.9).

**M3.8 — When RabbitMQ suits better than Kafka or SQS**

RabbitMQ's distinctive strengths:

- **Complex routing.** Topic exchanges with wildcard patterns let consumers subscribe to precisely the slice they care about, decided at the consumer. Kafka's routing is "which topic", and filtering means consuming everything and discarding — wasteful for a consumer wanting 1% of a high-volume topic. SQS has no routing at all.
- **Per-message operations** — priority queues, per-message TTL, delayed delivery (M3.9), and rejecting individual messages back to the queue. Kafka has none of these; its model is a sequential log.
- **Low-latency, low-volume work distribution** — RabbitMQ excels where Kafka's batching-oriented design is overkill.
- **Request/reply patterns** with reply-to queues and correlation IDs.
- **Protocol flexibility** — AMQP, MQTT, STOMP, which matters for IoT and for existing clients.
- **Self-hostable and comparatively simple** to operate versus Kafka (M12.3).

Where it loses: **no replay** (once consumed, gone — M1.3), **retention is not the model** so it's not a source of truth, **throughput is lower** than Kafka for high-volume streaming, and **queues that grow very large degrade** — RabbitMQ is designed for queues that stay short, and a multi-million-message backlog causes real performance problems, unlike Kafka where a large log is normal.

The decision framing: **RabbitMQ for sophisticated routing and task distribution; Kafka for high-volume streams that need retention and replay; SQS when you want a queue and no operational burden.** On AWS specifically, SQS's zero operations makes it the default for pure queueing unless you need routing that justifies running Amazon MQ or self-managed RabbitMQ.

**M3.9 — Delay queues and scheduled delivery**

Mechanisms:

- **SQS delay queues** — a queue-level `DelaySeconds` (up to 15 minutes) applied to every message, or **per-message `DelaySeconds`** on send.
- **RabbitMQ** — via a per-message or per-queue TTL on a queue with a dead-letter exchange pointing at the real queue (the message expires and is dead-lettered onward), or the delayed-message plugin.
- **EventBridge Scheduler** for arbitrary future times, which is the right tool beyond short delays.
- **Kafka has no native delay** — you build it with a delay topic and a consumer that sleeps or re-publishes, which is awkward and a genuine gap.

Uses: **retry backoff** — publish a failed message to a delay queue with an increasing delay rather than holding it in flight (M2.8); **scheduled work** like a reminder or a timeout ("cancel if unpaid in 30 minutes"); and **rate smoothing**.

The limits to know: **SQS caps at 15 minutes**, so anything longer needs chaining (republish with another delay) or a scheduler. **Delay is per-message, not a sorted schedule** — SQS doesn't reorder by delivery time, so messages with different delays can arrive out of order. And **delayed messages count toward queue metrics**, which can confuse lag alerting (M10.2).

**M3.10 — Message size limits and the claim-check pattern**

Limits: **SQS and SNS 256 KB**, **EventBridge 256 KB**, **Kafka default 1 MB** (`message.max.bytes`, raisable but with real costs), **RabbitMQ** practically limited by memory.

**The claim-check pattern**: store the payload in object storage and put a **reference** on the queue.

```json
{
  "eventType": "DocumentUploaded",
  "documentId": "doc-8891",
  "payloadLocation": "s3://acme-payloads/2026/08/doc-8891.json",
  "payloadSha256": "a3f9...",
  "sizeBytes": 4718592
}
```

The consumer fetches the object when it processes the message. The SQS Extended Client Library does this transparently.

The considerations:

- **Lifecycle coupling.** The object must outlive the message, including retries and DLQ residence (M2.9). An S3 lifecycle rule expiring objects after 7 days plus a message sitting in a DLQ for 14 days means an unreprocessable message pointing at nothing. **This mismatch is the classic claim-check bug.**
- **Access control** — every consumer needs read access to the bucket, and the message no longer carries the data so the permission model splits across two systems.
- **Now two failure modes** — the message can arrive and the fetch can fail.
- **Include a checksum and size** so the consumer can validate, and ideally enough metadata that the message is useful without fetching (routing decisions shouldn't require a download).

The design point that's more important than the pattern: **large messages are usually a signal that the event carries too much.** An event should describe what happened, often with an identifier the consumer uses to fetch what it needs from the owning service. A 5 MB event usually means someone is using the bus to move data rather than to signal facts (M12.4).

---

## M4. Kafka architecture

**M4.1 — Topics, partitions, offsets, and the commit log**

- **Topic** — a named stream of records. Purely logical.
- **Partition** — the physical unit. A topic is split into partitions, each an **ordered, immutable, append-only log** stored as segment files on a broker's disk.
- **Offset** — a monotonically increasing integer identifying a record's position **within a partition**. Not global; offset 500 in partition 0 is unrelated to offset 500 in partition 1.
- **The commit log model** — writes append to the end; reads are sequential from an offset; records are never modified and are not removed on consumption (M1.3), only by retention (M4.8).

The consequences that flow from this and explain most of Kafka's behaviour:

- **Ordering is per partition, not per topic** (M4.2), because only within a partition is there a single sequence.
- **Consumers track their own position**, so multiple consumer groups read the same data independently and replay is trivial (M6.9).
- **Both writes and reads are sequential disk I/O**, which is why it's fast (M4.10).
- **A record is identified by (topic, partition, offset)** — which is what makes exactly-once semantics expressible within Kafka (M5.7).

**M4.2 — How partitioning enables parallelism and constrains ordering**

**Parallelism**: partitions are distributed across brokers, so writes and reads spread across the cluster. Within a consumer group, **each partition is assigned to exactly one consumer** (M6.1), so partition count sets the maximum consumer parallelism.

**Ordering**: Kafka guarantees order **within a partition only**. Across partitions there is no ordering — two records written a millisecond apart to different partitions may be consumed in either order.

The two facts combine into the central design decision: **the partition key determines both which records are ordered relative to each other and how work is distributed** (M2.5, M5.3). Key by `account_id` and every event for an account is ordered, processed by one consumer, while thousands of accounts process in parallel.

The consequences to name:

- **More partitions = more parallelism, but a smaller ordering domain** if the key changes; the same ordering domain with more spread if the key stays.
- **Consumers beyond partition count idle** (M6.2).
- **Skew defeats it** (M5.4).
- **Changing partition count changes the key→partition mapping** and breaks ordering across the change (M4.11).

**M4.3 — Brokers, the cluster, and partition leadership**

A **broker** is a Kafka server. A **cluster** is a set of brokers sharing metadata. Each partition has one **leader** replica and zero or more **followers**.

- **All produce and consume traffic for a partition goes through its leader.** Followers replicate from the leader and serve no client traffic (with the exception of follower fetching for rack-local reads).
- **Leadership is distributed** across brokers so load spreads — each broker leads some partitions and follows others.
- The **controller** (one broker, elected) manages partition leadership and cluster metadata (M4.7).
- Clients **discover leadership via metadata requests** and connect directly to the right broker, which is why a Kafka client needs network access to every broker, not just a load balancer — a genuine networking design consideration and a common source of connectivity confusion.

**Preferred leader election** matters operationally: each partition has a preferred leader (the first replica in its assignment list), and after a broker restart, leadership doesn't automatically return, leaving the cluster unbalanced with some brokers leading far more partitions than others. `auto.leader.rebalance.enable` or a manual `kafka-leader-election.sh` restores it — and forgetting this after a rolling restart (M9.3) is a common cause of uneven load.

**M4.4 — Replication factor, ISR, and lagging replicas**

**Replication factor** is the number of copies of each partition. RF=3 is standard: one leader, two followers.

**ISR (in-sync replicas)** is the set of replicas — including the leader — that are sufficiently caught up. A follower stays in the ISR while it has fetched from the leader within `replica.lag.time.max.ms` (default 30s).

**When a replica falls behind:**

1. It's **removed from the ISR** ("ISR shrink"), and the partition becomes **under-replicated**.
2. The partition keeps serving — the leader is fine.
3. **But durability has decreased**, and if `min.insync.replicas` is now unsatisfiable, **producers with `acks=all` start failing** (M4.5). This is the mechanism by which one slow broker breaks writes across a cluster, and it's the connection that makes under-replicated partitions an urgent alert rather than an informational one (M10.1, M10.3).
4. When it catches up, it rejoins the ISR ("ISR expand").

Causes of a shrinking ISR: a slow or failing disk, network saturation, an overloaded broker, long GC pauses, or a rebalance moving a lot of data (M10.3).

The key property: **only ISR members are eligible to become leader** under normal settings, which is what prevents data loss on failover — a replica that's behind can't be promoted and silently lose the records it hasn't got (M4.6).

**M4.5 — `min.insync.replicas` and its interaction with acks**

`min.insync.replicas` is a **topic-level** setting specifying the minimum ISR size for a write to be accepted **when the producer uses `acks=all`**.

The interaction is the whole item, and it only works when both sides are set correctly:

- **`acks=all` alone is not enough.** It means "wait for all *in-sync* replicas" — and if the ISR has shrunk to just the leader, "all in-sync replicas" is one replica. The write is acknowledged with a single copy, and losing that broker loses the data. `acks=all` gives a false sense of durability without `min.insync.replicas`.
- **`min.insync.replicas=2` with `acks=all`** means the write is rejected (`NotEnoughReplicasException`) unless at least two replicas have it. That's a real durability guarantee.

**The canonical configuration: RF=3, `min.insync.replicas=2`, `acks=all`.** This tolerates one broker failure with no data loss and no write interruption — two replicas remain, which satisfies the minimum.

The tradeoff to state explicitly: **`min.insync.replicas` trades availability for durability.** With RF=3 and min ISR=2, losing two brokers stops writes entirely — the partition is readable but not writable. That's a deliberate choice: refuse the write rather than accept it without adequate durability. Setting min ISR equal to RF is the mistake — it means *any* single broker failure stops writes.

**M4.6 — Leader election and unclean leader election**

When a leader fails, the controller elects a new leader from the **ISR** — a replica known to be caught up, so no acknowledged data is lost.

**If the ISR is empty** — every in-sync replica has failed — there are two options:

- **`unclean.leader.election.enable=false`** (the default, and correct for most cases): the partition becomes **unavailable** until an ISR member returns. No data loss, no availability.
- **`unclean.leader.election.enable=true`**: an out-of-sync replica is promoted. The partition becomes available immediately, and **every record the new leader hadn't replicated is permanently lost** — silently, with no error to anyone. Producers that received acknowledgements will never see their data again.

The tradeoff to articulate: **availability versus durability, and the choice depends on what the data is.** For financial transactions, an audit log, or anything that is a source of truth, unavailability is vastly preferable to silent loss — leave it off and accept the outage. For high-volume telemetry or metrics where a gap is tolerable and continuous ingestion matters more, enabling it is defensible.

The other consequence worth naming: **unclean election can cause log divergence** — consumers that read records from the old leader now see a log that doesn't contain them, so offsets shift under them and downstream state can be inconsistent in ways that are extremely hard to reconcile.

**M4.7 — ZooKeeper's former role and what KRaft changed**

**ZooKeeper** historically stored cluster metadata: broker registration, topic and partition configuration, ACLs, and the controller election. Kafka brokers watched ZooKeeper for changes.

The problems: **a second distributed system to operate, secure, monitor, and upgrade**, with its own failure modes and its own expertise requirement; **metadata scalability limits** — controller failover meant loading all partition metadata from ZooKeeper, which took minutes on large clusters; and **a split-brain surface** between two consensus systems.

**KRaft** (Kafka Raft) replaces it: Kafka brokers run their own Raft-based consensus, storing metadata in an internal Kafka topic managed by a quorum of **controller** nodes (which can be dedicated or combined with brokers).

What changed practically:

- **One system to operate.** No ZooKeeper ensemble, no separate ZK security model.
- **Far faster controller failover and much better metadata scalability** — supporting many more partitions per cluster.
- **Simpler deployment**, and simpler security since ACLs and metadata live in Kafka.

The current state to know: **ZooKeeper mode was deprecated in 3.5 and removed in Kafka 4.0.** KRaft is the only mode going forward. Migration from ZooKeeper to KRaft is supported but is a real project with a defined sequence. **MSK supports KRaft**, and knowing that ZK is gone rather than merely optional is the currency signal here.

**M4.8 — Retention: time, size, and compaction**

Two distinct policies (`cleanup.policy`):

- **`delete`** — records are removed after `retention.ms` (time-based, default 7 days) or when the partition exceeds `retention.bytes` (size-based). **Whichever triggers first**, which surprises people: a size limit can silently reduce your effective time retention on a busy topic, so a consumer relying on 7 days of replay may find 2.
- **`compact`** — **log compaction** retains **the most recent value for each key**, indefinitely. Older values for the same key are removed by a background cleaner. A **tombstone** (a record with a key and a null value) marks a key for deletion, and after `delete.retention.ms` the key is removed entirely.

Compaction details that matter: **it's asynchronous and best-effort** — there's an active segment that is never compacted, so duplicate keys are always present near the head of the log and consumers must handle that. It's not a database; it's a log with a garbage collector.

You can also set **`cleanup.policy=compact,delete`** to compact *and* enforce a maximum age, which is the right choice for a compacted topic that should still forget eventually (M11.6).

Retention is what makes Kafka a source of truth rather than a transport (M1.3), and it's the setting that determines your replay window (M2.10) and how long a stalled consumer can be down before losing data permanently (M1.7).

**M4.9 — When a compacted topic is the right choice**

A compacted topic represents **current state keyed by identity**, rather than a history of events. Use it when a consumer needs "the latest value for every key" and doesn't need the full history.

The canonical cases:

- **A changelog / materialised view source** — Kafka Streams state stores are backed by compacted topics, so a restarting instance rebuilds state by replaying the compacted log rather than the entire history (M8.4).
- **Configuration and reference data** on the bus — a topic of current customer records, product catalogue, or feature flags, where a new consumer bootstraps by reading from the beginning and gets exactly one entry per key.
- **CDC snapshots** — a table's current rows as a topic, keyed by primary key (M7.7).
- **Kafka's own `__consumer_offsets`** topic is compacted, which is the built-in example.

The requirements and caveats:

- **Every record must have a key.** Null-keyed records in a compacted topic can't be compacted and cause problems.
- **You lose history.** If a consumer needs to see every change (an audit trail, an event-sourced aggregate), compaction destroys exactly what you need. This is the decision — compaction is for state, not for events.
- **Compaction lag is real**, and the un-compacted head means duplicates are always possible.
- **Tombstones are how deletion works**, and their retention window matters for correctness and for GDPR (M11.6).

**M4.10 — Why Kafka is fast**

Four mechanisms, and being able to name all four with the reason for each is the answer:

1. **Sequential disk I/O.** Appending to a log file is sequential, and sequential disk access is orders of magnitude faster than random — fast enough that spinning disks were viable for Kafka long after random workloads had moved to SSD. Reads are also sequential, from an offset forward.
2. **The OS page cache.** Kafka doesn't maintain its own cache; it writes to the filesystem and lets the kernel cache. Consumers reading recent data — the common case — are served from RAM without Kafka involvement. It also means a broker restart doesn't lose the cache, and JVM heap stays small (no huge object graphs, so no GC pressure — which is a second-order benefit worth mentioning).
3. **Zero-copy** (`sendfile`). Sending data to a consumer copies directly from page cache to the network socket **without passing through user space** — no copy into the JVM, no serialisation. This is why Kafka can saturate a NIC with modest CPU. Note it's defeated by broker-side decompression or TLS termination in some configurations, which is a real cost of enabling encryption (M11.1).
4. **Batching and compression.** Producers batch records (`linger.ms`, `batch.size`, M5.5) and compress the batch. Compression applies to the whole batch, which compresses far better than individual records, and the batch is stored and transmitted compressed end to end.

Plus the architectural point: **partitioning distributes load horizontally**, so throughput scales with brokers and partitions rather than being bounded by one machine.

**M4.11 — Choosing a partition count, and why changing it is disruptive**

**Choosing:**

- **Start from target throughput** — measure per-partition throughput for your workload (produce and consume), then `partitions = target / per-partition-capacity`, with headroom.
- **Bound by consumer parallelism** — you can never have more active consumers in a group than partitions (M6.2), so partition count is your maximum consumer scale-out. Size for peak consumer count plus growth.
- **Bound by key cardinality** — more partitions than distinct keys means empty partitions.
- **Don't over-provision wildly.** Each partition costs file handles, memory, replication overhead, and adds to controller metadata and rebalance time. Tens of thousands of partitions per cluster is where problems begin (less severe under KRaft, M4.7).

A common heuristic: enough for 2–3× current peak throughput, typically 6–30 for a mainstream topic rather than 3 or 300.

**Why changing it later is disruptive** — this is the substance:

- **The default partitioner is `hash(key) % partition_count`.** Change the count and the mapping changes, so **records for a given key now go to a different partition than their history.** Ordering for that key is broken across the change — old events in the old partition, new ones elsewhere, with no ordering between them.
- **Stateful consumers break.** A consumer that accumulated per-key state on partition 3 now receives that key on partition 7, where it has no state. Kafka Streams applications require a full state rebuild.
- **You can only increase, never decrease.** Reducing requires creating a new topic and migrating.
- **Existing data is not redistributed** — old records stay where they are, so the log is inconsistently keyed by design.

The mitigation: **over-provision modestly at creation** — it's much cheaper than changing later. And where a change is unavoidable, the safe route is usually a **new topic with the desired partitioning, dual-write or replay into it, migrate consumers, retire the old topic** — which is a project rather than a config change.

---

## M5. Kafka producers

**M5.1 — Acks and the durability/latency tradeoff**

- **`acks=0`** — the producer doesn't wait for any acknowledgement. Lowest latency, highest throughput, **and messages can be lost silently** — including if the broker is simply unreachable. Only for genuinely disposable data.
- **`acks=1`** — the leader acknowledges after writing to its own log, before followers replicate. Fast. **Data is lost if the leader fails before replication** — a real window, not a theoretical one.
- **`acks=all` (`-1`)** — the leader waits for all in-sync replicas. Highest durability, highest latency.

**`acks=all` is only meaningful with `min.insync.replicas` set** (M4.5) — this is the point to make, because `acks=all` alone can be satisfied by a single-member ISR.

The tradeoff in practice: `acks=all` with RF=3 and min ISR=2 adds latency equal to the slowest in-sync follower's fetch round trip — usually single-digit milliseconds within an AZ, more across AZs (M9.7). **For most workloads that cost is negligible and durability is worth it**; the default recommendation for anything that matters is `acks=all`.

The related settings that complete the durable configuration: **`enable.idempotence=true`** (now the default in recent clients, and it implies `acks=all`), **`retries`** set high, and **`max.in.flight.requests.per.connection<=5`** with idempotence to preserve ordering (M5.8).

**M5.2 — The partitioner and the effect of a null key**

- **With a key**: `partition = murmur2(key) % numPartitions`. **Deterministic** — the same key always goes to the same partition (for a fixed partition count, M4.11), which is what delivers per-key ordering (M5.3).
- **With a null key**: the record has no partition affinity. Historically this was round-robin; **modern clients use the sticky partitioner** — records go to one partition until the batch is full or `linger.ms` elapses, then it switches. This produces better batching (M5.5) and therefore better throughput, at the cost of slightly less even distribution over short windows.

The consequences of a null key, which is what the item is probing:

- **No ordering guarantee for related records.** Two events about the same order land in different partitions and can be consumed in any relative order.
- **No key means compaction is impossible** (M4.9).
- **Even distribution** across partitions, which is good for throughput and load balance.

So the decision is exactly the M2.5 tradeoff in producer form: **key when you need per-entity ordering or compaction; null key when you want maximum spread and don't need either.** A custom partitioner is possible but rarely the right answer — it usually indicates the key should be different.

**M5.3 — Choosing a partition key**

The key determines **the ordering domain** and **the distribution**. Choose it by asking: *what set of records must be processed in order relative to each other?*

- `order_id` → all events for one order ordered; high cardinality; good spread.
- `customer_id` → all events for one customer ordered (useful if cross-order sequencing matters); moderate cardinality.
- `account_id` in payments → ordering for balance-affecting operations, which is usually the actual requirement.

The guarantee to state explicitly: **records with the same key go to the same partition, and a partition is consumed by one consumer in a group, therefore records with the same key are processed in order by a single consumer.** That chain of reasoning is the answer — it's not just "same key, same partition", it's why that gives you the property you want.

The mistakes:

- **Too coarse** — keying by `tenant_id` or `region` or `event_type` creates few, huge partitions and severe skew (M5.4). Keying by country in a UK-centric business puts 90% of traffic on one partition.
- **Too fine** — keying by a unique event ID means every record is its own domain, which is equivalent to no key at all for ordering purposes.
- **A key that changes** for the same logical entity — the ordering breaks precisely when it matters.
- **Choosing before understanding the requirement** — the key is very hard to change later, since it's baked into every producer and into the history.

**M5.4 — Diagnosing partition skew**

**The symptom**: some partitions have far more data and lag than others. Consumers assigned to hot partitions are saturated while others idle. **Aggregate throughput looks fine and one consumer is the bottleneck** — and adding consumers doesn't help, which is the confusing part.

**Diagnosis:**

```bash
# per-partition lag and offsets
kafka-consumer-groups.sh --bootstrap-server broker:9092 \
  --describe --group payments-processor

# partition sizes on disk
kafka-log-dirs.sh --bootstrap-server broker:9092 \
  --describe --topic-list payments | jq
```

Look for partition offsets or sizes differing by an order of magnitude, and for lag concentrated on specific partitions (M6.7).

**Causes:**

- **Low-cardinality key** — few distinct values, so few partitions used.
- **A dominant key** — one tenant, one large customer, one high-volume account. This is the most common in multi-tenant systems and it's structural rather than a mistake.
- **A key correlated with volume** — keying by date or hour means one partition takes all current traffic.

**Fixes:**

1. **Choose a higher-cardinality key** — the right answer where possible, but it changes ordering semantics and requires a new topic (M4.11).
2. **Composite key with a salt** — `customer_id:shard_n` for the dominant customer only, which spreads that one key across N partitions **at the cost of losing ordering for it**. Whether that's acceptable is the design question.
3. **Separate topic for the whale** — route the dominant tenant to its own topic with its own consumer group and its own scaling. Often the cleanest answer in multi-tenant systems.
4. **A custom partitioner** that spreads deliberately — a last resort.

The point to make: **skew is a design problem, not a tuning problem.** No amount of consumer scaling fixes it because the constraint is that one partition is one consumer's work.

**M5.5 — Batching, linger, and compression**

```properties
batch.size=32768              # bytes per partition batch (default 16KB)
linger.ms=10                  # wait this long to fill a batch (default 0)
compression.type=lz4          # none | gzip | snappy | lz4 | zstd
buffer.memory=67108864        # total producer buffer
```

How they interact:

- **`batch.size`** is the maximum batch; **`linger.ms`** is how long the producer waits for the batch to fill before sending anyway. **With `linger.ms=0` (the default) the producer sends immediately**, so batches are only as large as what happens to be queued while the previous request is in flight.
- **Raising `linger.ms` to 5–20ms typically produces a large throughput improvement** for the cost of a few milliseconds of latency — larger batches mean fewer requests, better compression ratios, and less per-record overhead. This is one of the highest-value single tuning changes available and it's very often left at the default.
- **Compression applies per batch**, so bigger batches compress much better. Compression reduces network and disk, and — importantly — **the batch stays compressed at rest and is sent compressed to consumers**, so the saving is end to end.

Compression choice: **lz4 or zstd** for most cases (fast, good ratio); **zstd** where storage and network dominate and CPU is available; **gzip** is slow and rarely the right answer now; **snappy** is fine and largely superseded by lz4.

The tradeoff to state: **batching trades latency for throughput and cost.** For a high-volume pipeline, `linger.ms=20` with zstd can dramatically cut broker load and network spend. For a low-latency path where each message matters individually, keep linger low. And note **compression costs producer CPU**, with broker CPU also affected if the broker must recompress (which happens when the message format or compression type doesn't match).

**M5.6 — The idempotent producer and what it actually prevents**

`enable.idempotence=true` (default in modern clients). The mechanism: the producer gets a **producer ID (PID)** and attaches a **monotonic sequence number per partition** to each batch. The broker tracks the last sequence per (PID, partition) and **rejects duplicates** while detecting gaps.

**What it prevents**: **duplicates caused by producer retries.** The classic scenario — the producer sends a record, the broker writes it, the acknowledgement is lost in the network, the producer retries, and without idempotence the record is written twice. With idempotence, the broker recognises the sequence number and discards the retry.

It also **preserves ordering under retry** (M5.8), because the broker rejects out-of-sequence batches rather than accepting them in the wrong order.

**What it does not prevent**, and this is the important half:

- **Duplicates from the application producing the same logical event twice** — a retried HTTP request that causes two `send()` calls is two different records with different sequence numbers, and Kafka has no idea they're the same.
- **Duplicates across producer sessions.** The PID is per-session; a producer restart gets a new PID, so a record resent after a restart is not deduplicated.
- **Anything on the consumer side** (M2.3).

So: **idempotent producer removes a specific, mechanical source of duplicates — retries within one session — and is not a substitute for idempotent consumers.** Stating that boundary precisely is what the question is testing. It's cheap and should always be on; it just doesn't solve the general problem.

**M5.7 — Transactional producers and exactly-once semantics**

Transactions let a producer **write to multiple partitions and topics atomically**, and — critically — **commit consumer offsets in the same transaction**.

```java
producer.initTransactions();
producer.beginTransaction();
producer.send(record1);
producer.send(record2);
producer.sendOffsetsToTransaction(offsets, consumerGroupMetadata);
producer.commitTransaction();
```

That last part is what makes **exactly-once semantics for read-process-write** possible: consuming a record, producing derived records, and committing the input offset either all happen or none do. Without it, you commit the offset and crash before producing (loss) or produce and crash before committing (duplicates).

Consumers must set **`isolation.level=read_committed`** to skip records from aborted transactions — otherwise they see uncommitted data and the guarantee is void from their perspective. That's the setting people forget.

**The scope limitation is the essential caveat**: exactly-once applies **within Kafka**. If the processing step writes to Postgres or calls a payment API, those are outside the transaction and are not covered. So EOS is powerful for Kafka-to-Kafka pipelines (Kafka Streams uses it, M7.5) and does nothing for a consumer whose job is to call an external system — which is most consumers.

The costs: **throughput and latency overhead** from the transaction coordinator and commit markers, added complexity, and `read_committed` consumers see records only after commit, adding latency proportional to transaction size.

The practical position: **use transactions for Kafka-internal stream processing; use idempotent consumers everywhere else** (M2.3).

**M5.8 — Producer retries and reordering**

The mechanism: with `max.in.flight.requests.per.connection > 1`, the producer has several batches in flight to a partition simultaneously. If batch 1 fails and is retried while batch 2 succeeded, **batch 1 is written after batch 2 — the records are reordered within the partition**, silently breaking the ordering guarantee people assume is absolute.

The fixes:

- **`enable.idempotence=true`** (M5.6) — the broker enforces sequence numbers and rejects out-of-order batches, so ordering is preserved **with up to 5 in-flight requests**. This is the correct modern answer and is the default.
- **`max.in.flight.requests.per.connection=1`** — the older fix. Guarantees ordering without idempotence and severely limits throughput. Unnecessary now.

The subtlety worth knowing: **the guarantee is per partition per producer session.** And `delivery.timeout.ms` bounds total time including retries — when it expires the send fails permanently, which the application must handle (dropping it is silent loss).

The framing: **"Kafka guarantees ordering within a partition" is true of the log, and the producer can still write in the wrong order** if misconfigured. Since idempotence became the default this is mostly historical, but it's a favourite interview question precisely because it reveals whether someone understands where the guarantee actually lives.

**M5.9 — Buffer exhaustion and producer-side backpressure**

The producer accumulates records in an in-memory buffer (`buffer.memory`, default 32MB) while a background thread sends batches. **If the application produces faster than the sender can transmit — because brokers are slow, the network is saturated, or the partition leader is unavailable — the buffer fills.**

What happens then is the item: **`send()` blocks** for up to `max.block.ms` (default 60s), and then throws `TimeoutException`.

**This is producer-side backpressure** (M1.7) and it's the mechanism by which broker slowness propagates back into the application. The failure modes:

- **Blocking `send()` stalls the calling thread**, so a web request handler calling `send()` synchronously blocks — a Kafka problem becomes an HTTP latency problem and then a thread pool exhaustion problem. **This is how a Kafka slowdown takes down a web tier**, and it's a genuinely common incident shape.
- **`max.block.ms=0`** fails immediately instead, which converts blocking into errors — better if you have somewhere to put the failure, worse if you just drop it.
- **After the timeout, records are lost** unless the application handles the exception and retries or persists them.

The handling: **monitor `buffer-available-bytes` and `record-error-rate`** — buffer pressure is a leading indicator of a broker problem, often earlier than broker metrics show it. **Handle the send callback** rather than fire-and-forget, so failures are visible. **Bound the producer's impact on the request path** — produce asynchronously with a bounded internal queue and an explicit overflow policy, rather than letting the Kafka client's blocking behaviour reach your request handlers. And **the outbox pattern** (M2.6) sidesteps the whole problem, since the application writes to its database and a separate relay deals with Kafka's availability.

---

## M6. Kafka consumers

The section where practical Kafka experience is most visible.

**M6.1 — Consumer groups and partition assignment**

A **consumer group** is a set of consumers sharing a `group.id`. Kafka assigns each partition of the subscribed topics to **exactly one consumer in the group**. Different groups are independent — each gets every record and tracks its own offsets (M1.2).

The mechanics: a **group coordinator** (a broker) manages membership; one consumer is elected **group leader** and computes the assignment; the coordinator distributes it. Assignment strategies:

- **Range** — assigns contiguous partition ranges per topic. Can distribute unevenly across multiple topics.
- **RoundRobin** — spreads partitions evenly across consumers.
- **Sticky** — even distribution while **minimising movement** on rebalance, so a consumer keeps most of its previous partitions.
- **CooperativeSticky** — sticky plus incremental rebalancing (M6.4). **The right default in modern clients.**

The consequences that follow: **partition count caps group parallelism** (M6.2); **adding or removing a consumer triggers a rebalance** (M6.3); and **per-partition ordering plus one-consumer-per-partition is what gives you ordered processing per key** (M5.3).

**M6.2 — Why consumers beyond the partition count sit idle**

Because a partition is assigned to **exactly one** consumer in a group — that's the invariant that preserves per-partition ordering (M4.2). With 6 partitions and 10 consumers, 6 are assigned and **4 receive nothing at all.**

They aren't broken and they aren't sharing work; they're idle, holding a group membership and consuming resources. The symptom is a scaled-out consumer deployment where throughput doesn't improve, and CPU on several pods is flat at zero.

The implications:

- **Partition count is your maximum consumer scale-out** (M4.11), and it must be chosen with peak consumer count in mind because increasing it later is disruptive.
- **Idle consumers still participate in rebalances**, so over-provisioning makes rebalances slower without adding throughput.
- **They're not entirely useless** — they're warm standbys that take over immediately if an active consumer dies, which for a slow-starting consumer is a legitimate reason to run one or two spares.

The escape routes when you're partition-bound but need more parallelism: **increase partitions** (with the M4.11 caveats); **parallelise within the consumer** — fetch from the partition and hand work to a thread pool, which recovers throughput **but sacrifices ordering and complicates offset commits** (M6.5), so it must be deliberate; or **use a per-key concurrency library** (like Confluent's parallel consumer) that maintains per-key ordering while processing keys concurrently — the best of both, and worth naming as the sophisticated answer.

**M6.3 — Rebalancing, its triggers, and the stop-the-world cost**

A **rebalance** reassigns partitions across group members. Triggers:

- A consumer **joins** (scale-up, deploy, restart).
- A consumer **leaves** gracefully.
- A consumer is **deemed dead** — missed heartbeats (`session.timeout.ms`) or exceeded `max.poll.interval.ms` (M6.8).
- **Topic metadata changes** — partitions added, or a subscribed pattern matches a new topic.

**The stop-the-world cost** (with the classic eager protocol): **every consumer in the group revokes all its partitions and stops processing**, the group re-forms, the assignment is computed, and consumers resume. For the duration, **the entire group processes nothing** — lag accumulates across all partitions, not just the ones moving.

Why it hurts more than it sounds:

- **Rebalance duration scales with group size and partition count** — seconds to minutes on a large group.
- **Stateful consumers must rebuild state** for newly-assigned partitions, which can dominate the cost (M8.4).
- **A rolling deployment of N pods triggers N rebalances** (or 2N with eager protocol — one on leave, one on join), so a routine deploy can stall consumption for minutes.
- **Rebalance storms** — a consumer that keeps being evicted and rejoining causes continuous rebalancing and the group never processes anything (M10.4).

The mitigations are M6.4: **cooperative rebalancing** and **static membership**, both of which materially change this and are the reason a modern well-configured group doesn't suffer the classic pain.

**M6.4 — Cooperative rebalancing and static membership**

**Cooperative (incremental) rebalancing** — `partition.assignment.strategy=CooperativeStickyAssignor`. Instead of everyone revoking everything, the protocol computes the assignment and **only the partitions that actually need to move are revoked**. Consumers keep processing their unchanged partitions throughout.

The effect is substantial: adding one consumer to a 20-partition group moves a handful of partitions and leaves the rest processing, rather than stopping all 20. It takes two rounds rather than one, but the group never fully stops.

**Static membership** — set `group.instance.id` to a stable identifier per consumer instance. The consumer is then recognised as the *same member* across restarts, so **a restart within `session.timeout.ms` does not trigger a rebalance at all** — the returning consumer reclaims its previous partitions.

This is the answer to the deployment problem: with static membership and a session timeout longer than your pod restart time, **a rolling deploy causes no rebalances**. For Kubernetes, a StatefulSet gives stable ordinal names that map naturally to `group.instance.id` (K2.8), which is a neat and non-obvious pairing worth mentioning.

The caveats: **static membership delays detection of a genuinely dead consumer** to `session.timeout.ms`, so there's a real availability trade — set it long enough to cover restarts, short enough that a crash doesn't stall a partition for minutes. And both settings need client and broker version support.

Together these two settings turn rebalancing from a significant operational pain into a mostly-solved problem, and knowing that is a good currency signal.

**M6.5 — Offset commits: auto vs manual, and where duplicates come from**

The consumer's position is stored in the `__consumer_offsets` topic. **The committed offset is where a new or restarted consumer resumes.**

- **Auto-commit** (`enable.auto.commit=true`, default) — commits the last polled offset periodically (`auto.commit.interval.ms`, default 5s). Simple, and **it commits on a timer regardless of whether the records were actually processed.**
- **Manual commit** — the application calls `commitSync()` or `commitAsync()` when it chooses.

**Where duplicates come from**, which is the substance:

- **With auto-commit**: the consumer polls 500 records, auto-commit fires after processing 100, then the consumer crashes. On restart it resumes from the committed offset — records 101–500 are reprocessed. **Worse, the reverse is possible**: auto-commit fires after the poll but before processing completes, so a crash means records are skipped entirely — **silent loss, not duplication.** That's the genuinely dangerous auto-commit failure and it's less well known.
- **On rebalance** (M6.3): partitions are revoked before the in-flight batch's offsets are committed, and the new owner resumes from the last commit — reprocessing.
- **Any crash between processing and committing**, which is unavoidable in principle (M2.1).

So: **manual commit after processing** is the correct pattern for anything that matters, and even then duplicates remain possible (M2.2), which is why consumers must be idempotent (M2.3).

Practicalities: **commit in batches, not per record** — a commit per message is a round trip per message and destroys throughput. **`commitAsync` with a final `commitSync` on shutdown** is the standard shape. And **commit in the rebalance listener's `onPartitionsRevoked`** so you don't lose progress when partitions move.

**M6.6 — Committing before versus after processing**

The whole delivery-semantics question in one decision:

- **Commit before processing** → **at-most-once.** If processing fails or the consumer crashes, the offset has moved and the record is never reprocessed. **Data loss, silently.**
- **Commit after processing** → **at-least-once.** If the consumer crashes after processing but before committing, the record is redelivered. **Duplicates, handled by idempotency** (M2.3).

**Commit after, essentially always** — for the M2.2 reason: duplicates are solvable in the consumer, loss is not solvable anywhere.

The subtlety that makes this more than a binary: **"after processing" means after the work is durably committed**, not after the function returns. If the consumer hands the record to an async worker and then commits, it has effectively committed before processing and reintroduced the loss window — which is a common mistake when someone adds a thread pool to increase throughput (M6.2).

And the atomicity point (M2.3): even committing after processing, the database write and the offset commit are two separate systems, so a crash between them means reprocessing. **The only way to make them atomic is Kafka transactions with `sendOffsetsToTransaction`** (M5.7), which only works if the output is also Kafka. For everything else, idempotency is the answer, and the offset commit ordering just determines which failure mode you get.

**M6.7 — Diagnosing consumer lag**

**Lag = latest offset in the partition − committed offset.** It's the number of records waiting.

```bash
kafka-consumer-groups.sh --bootstrap-server broker:9092 \
  --describe --group payments-processor
```

Output gives per-partition `CURRENT-OFFSET`, `LOG-END-OFFSET`, `LAG`, and the assigned `CONSUMER-ID` — and **the shape of that per-partition breakdown is the diagnosis**:

- **Lag rising evenly across all partitions, consumers busy** → **slow consumer**: throughput is below the produce rate. Either scale out (up to partition count, M6.2), optimise processing, or find the downstream bottleneck (M1.9). Check whether the consumer is CPU-bound or waiting on I/O.
- **Lag rose sharply then is draining evenly** → **a spike**. The system is recovering; the question is whether it drains before it matters (M10.2). Often no action needed beyond watching.
- **Lag high on one partition, near zero elsewhere** → **a stuck partition or skew.** Either a **poison message** blocking commits on that partition (M2.7 — the classic), or **partition skew** from a bad key (M5.4). Distinguish them by whether the partition's current offset is advancing at all: not moving = stuck; moving but behind = skew.
- **Lag on partitions assigned to one consumer** → that consumer instance is unhealthy — GC pauses, a resource limit, a bad node.
- **Lag flat and no consumer assigned** → the group has no members, or fewer members than partitions.
- **Lag oscillating with periodic resets** → **rebalance storms** (M10.4), where the group keeps restarting and reprocessing.

The metric caveat: **lag in records is not lag in time.** 100,000 records on a topic doing 1,000/s is 100 seconds behind; on a topic doing 10/s it's nearly three hours. **Time lag is what matters for business impact** and is what you should alert on (M10.2).

**M6.8 — `max.poll.interval.ms` and being kicked from the group**

Two distinct liveness mechanisms, and confusing them is the common error:

- **`session.timeout.ms`** (default 45s) — the **heartbeat** thread sends heartbeats in the background. Missing them means the consumer process is dead or partitioned.
- **`max.poll.interval.ms`** (default 5 minutes) — the maximum time between successive `poll()` calls. **This detects a consumer that is alive but stuck** — processing a batch too slowly, blocked on a downstream call, or hung.

**The failure mode**: a consumer polls 500 records and takes 6 minutes to process them. Heartbeats keep flowing (separate thread, so the consumer looks alive), but `poll()` isn't called within `max.poll.interval.ms`, so **the coordinator evicts it and triggers a rebalance**. The consumer finishes its batch, tries to commit, and gets `CommitFailedException` because it's no longer a member. It rejoins, gets partitions, fetches the same records, and does it again.

**This is a rebalance storm** (M10.4): continuous rebalancing, continuous reprocessing, near-zero progress, and the logs are full of `CommitFailedException` and "member has left the group" messages.

The fixes, in preference order:

1. **Reduce `max.poll.records`** so each batch is small enough to process within the interval. **This is usually the right fix** and it's the one people miss, reaching for the timeout instead.
2. **Increase `max.poll.interval.ms`** if processing is legitimately slow — at the cost of slower detection of a genuinely hung consumer.
3. **Make processing faster**, or move slow work off the poll loop (with the M6.6 caveat about committing before processing).

**M6.9 — Resetting offsets deliberately**

```bash
# always dry-run first
kafka-consumer-groups.sh --bootstrap-server broker:9092 \
  --group payments-processor --topic payments \
  --reset-offsets --to-datetime 2026-08-18T00:00:00.000 --dry-run

# then execute
kafka-consumer-groups.sh ... --reset-offsets --to-earliest --execute
```

Options: `--to-earliest`, `--to-latest`, `--to-offset N`, `--to-datetime`, `--shift-by N`, `--by-duration`.

**The group must have no active members** — Kafka refuses otherwise, so you stop the consumers first.

**The blast radius:**

- **Resetting backwards means reprocessing**, with every consequence in M2.10: duplicate side effects, emails re-sent, payments re-attempted, downstream systems re-notified. **Only safe if the consumer is genuinely idempotent**, and even then only if its side effects are internal.
- **Resetting forwards skips records permanently** — they're never processed, silently. Used deliberately to abandon a backlog (M10.10), and it's data loss by choice, which should be a recorded decision.
- **It affects the entire group**, all partitions, all consumers — not one instance.
- **`--to-earliest` on a large topic** replays everything, which can take hours and may overwhelm downstream systems at replay speed rather than production speed. Rate-limiting the consumer during a replay is often necessary.
- **Other consumer groups are unaffected**, which is the useful property — you can replay into a *new* group without touching production (M2.10).

The safe pattern for a reprocess: **create a new consumer group, reset it, and run a separate consumer deployment** — rather than resetting the live group. Production keeps running; the replay is isolated and can be abandoned.

**M6.10 — Scaling consumers and what actually limits throughput**

The scaling levers, and the ceilings each hits:

1. **More consumer instances** — up to the partition count, then nothing (M6.2).
2. **More partitions** — raises the ceiling, disruptive to change (M4.11).
3. **Concurrency within the consumer** — a thread pool over polled records. Recovers throughput past the partition limit, **loses per-partition ordering and complicates offset commits** (M6.5, M6.6). A per-key parallel consumer preserves ordering while parallelising.
4. **Tuning fetch behaviour** — `max.poll.records`, `fetch.min.bytes`, `fetch.max.wait.ms` to trade latency for batch efficiency.
5. **Making processing faster** — usually the highest-value and least-explored option.

**What actually limits throughput**, in the order it usually binds:

- **The downstream dependency.** Almost always. Ten consumers writing to one Postgres instance produces database contention, not ten times throughput. **Scaling consumers moves the bottleneck rather than removing it**, and this is the single most common misdiagnosis.
- **Per-message processing cost** — if each record makes a 200ms external API call, throughput per consumer is 5/s regardless of hardware. Batching the downstream calls is the fix, not more consumers.
- **Partition count** (M6.2).
- **Partition skew** — one hot partition means one consumer is the bottleneck and the rest idle (M5.4).
- **Consumer resource limits** — CPU, memory, GC pauses (which also cause M6.8 evictions).
- **Broker or network capacity** — rarely the limit in practice, but worth ruling out.

The diagnostic discipline: **before scaling, establish where the time goes.** A consumer at 10% CPU with rising lag is not CPU-bound and adding instances won't help; it's waiting on something, and that something is the actual constraint.

**M6.11 — Handling a poison message without an infinite loop**

Kafka has **no native DLQ** — you build one. The pattern:

```java
try {
    process(record);
} catch (RetryableException e) {
    // let it retry — do not commit
    throw e;
} catch (Exception e) {
    // non-retryable, or retry budget exhausted
    dlqProducer.send(new ProducerRecord<>("payments.dlq",
        record.key(), enrich(record, e)));   // include error, stack, offset, trace ID
    consumer.commitSync(offsetOf(record) + 1);   // move past it
}
```

The essentials:

- **Produce to an error topic, then commit past the record.** Committing is what unblocks the partition (M2.7) — without it, everything behind this record is stuck indefinitely.
- **Enrich before dead-lettering** — original payload, exception, stack trace, source topic/partition/offset, attempt count, trace ID (M2.9, M10.6). Without the offset you can't correlate back to the original.
- **Classify errors** (M2.8): a downstream 503 should retry; a deserialisation failure never will, so send it straight to the error topic without burning retries.
- **Bound in-process retries** with backoff, and remember the retry time counts toward `max.poll.interval.ms` (M6.8) — a retry loop inside the poll loop can get you evicted, which is a nasty interaction.
- **Alert on the error topic**, and give it an owner (M2.9).

Additional mechanisms worth naming: **retry topics with increasing delays** (`payments.retry.5s`, `payments.retry.1m`, `payments.retry.10m`) — a consumer reads a retry topic, waits, and republishes to the main topic. This gets you delayed retry without blocking the main partition, and it's the standard Kafka answer to the delay-queue gap (M3.9). And **Kafka Connect and Spring Kafka have built-in DLQ support**, so you don't always write this by hand.

The design point: **the default behaviour is retry forever and block the partition.** Every Kafka consumer needs an explicit poison-message policy, and not having one is a latent incident.

---

## M7. Kafka ecosystem

**M7.1 — Kafka Connect: connectors, workers, tasks**

Connect is a framework for moving data between Kafka and external systems without writing consumer or producer code.

- **Source connector** — pulls from an external system into Kafka (a database via CDC, S3, an API).
- **Sink connector** — pushes from Kafka to an external system (S3, Elasticsearch, a data warehouse, JDBC).
- **Worker** — the JVM process running connectors. **Distributed mode** runs a cluster of workers that share work and rebalance on failure; **standalone mode** is a single process for development.
- **Task** — the unit of parallelism. A connector is configured with `tasks.max` and splits its work into tasks distributed across workers. For a JDBC source that might be one task per table; for a sink, tasks map to partitions.

Why use it rather than writing a consumer: **it's declarative configuration rather than code**, it handles offset management, retries, restarts, scaling, and rebalancing for you, there's a large library of existing connectors, and **Single Message Transforms** provide light in-flight modification (masking a field, renaming, routing) without a stream processor.

The operational realities: **Connect is another distributed system to run** — workers, their own rebalancing, their own monitoring — and a badly-behaved connector can consume a worker cluster. **Connector quality varies enormously** between vendors and community connectors. **Error handling needs explicit configuration** (`errors.tolerance`, `errors.deadletterqueue.topic.name`), and the default is to fail the task, which stops the pipeline. And **schema handling** with Connect's internal converters is a frequent source of confusion (M7.2).

**M7.2 — Schema Registry and why schemas matter on a shared bus**

Schema Registry stores versioned schemas and assigns each an ID. Producers register the schema and **write the schema ID in the message header**, not the schema itself; consumers fetch the schema by ID (cached) to deserialise.

**Why schemas matter on a shared bus** — the argument:

- **A topic is an interface between teams.** Without a schema, that interface is implicit, undocumented, and enforced only by whatever the consumer happens to parse. A producer adding, renaming, or removing a field breaks consumers with no warning and no way to have known.
- **The registry makes compatibility a build-time check** rather than a production incident: an incompatible schema is rejected at registration (M7.3).
- **It's the documentation** — a browsable, versioned catalogue of what's on the bus, which is the antidote to the undocumented integration layer problem (M12.4).
- **Efficiency** — the schema ID is a few bytes, versus JSON repeating field names in every message. On a high-volume topic the size reduction is significant.

The operational points: **the registry is in the serialisation path**, so its availability matters — clients cache aggressively but a cold start with a down registry fails. **Subject naming strategy** (`TopicNameStrategy` by default, versus `RecordNameStrategy`) determines whether one topic can carry multiple event types, which is a real design decision. And **it doesn't validate semantics** — a schema-valid message with nonsense values passes.

**M7.3 — Compatibility modes and planning a breaking change**

Compatibility modes, and what each permits:

- **BACKWARD** (default) — a **new schema can read data written with the old schema**. So consumers upgrade first. Permits **deleting fields and adding optional fields (with defaults)**.
- **FORWARD** — the **old schema can read data written with the new schema**. Producers upgrade first. Permits **adding fields and deleting optional ones**.
- **FULL** — both. Only optional-field changes with defaults.
- **NONE** — no checking.
- **`_TRANSITIVE`** variants check against **all** previous versions, not just the latest — which matters, because non-transitive BACKWARD lets you drift incompatibly over several versions.

**Choosing**: BACKWARD is the sensible default on a bus with many unknown consumers, because you can upgrade consumers at their own pace and producers change last. But **the mode determines the deployment order**, and getting that backwards is a real outage — worth stating explicitly.

**Planning a breaking change** — renaming a field, changing a type, or removing a required one. It cannot be done in one step, so:

1. **Add the new field alongside the old**, both optional with defaults. Compatible.
2. **Producers write both.**
3. **Migrate consumers** to read the new field, at their own pace. **You need to know who your consumers are** for this — which is a governance requirement, not a technical one (M12.5).
4. **Once all consumers have migrated**, stop writing the old field.
5. **Remove the old field** from the schema.

That's the expand/contract pattern, and it's the same shape as a database migration. The alternative for a truly breaking change is **a new topic with a new version** (`payments.v2`), dual-publishing during migration, and retiring v1 once consumers have moved — heavier, but it decouples the timelines completely and is the right answer when the change is fundamental.

**M7.4 — Avro, Protobuf, JSON**

| | Avro | Protobuf | JSON |
|---|---|---|---|
| Size | Compact (binary, no field names) | Compact (binary, field numbers) | Verbose |
| Schema | Required, external | Required, `.proto` file | Optional (JSON Schema) |
| Evolution | Excellent, with defaults | Excellent, via field numbers | Weak without a schema |
| Human-readable | No | No | Yes |
| Tooling | Strong in the JVM/Kafka ecosystem | Strong everywhere, especially gRPC | Universal |
| Code generation | Optional (generic records possible) | Required in practice | None needed |

The decision:

- **Avro** is the Kafka-native default — designed for exactly this (schema evolution over a stream), best Schema Registry integration, and the ability to read data with a different schema than it was written with is fundamental to its design.
- **Protobuf** where you already use gRPC and want one IDL across synchronous and asynchronous interfaces, or where you're polyglot and want the best cross-language tooling. **Field numbers make evolution explicit and hard to get wrong**, which some teams prefer to Avro's name-based resolution.
- **JSON** for low-volume topics, for debuggability, or where consumers are outside your control. **The verbosity cost is real at high volume** — repeating field names in every record can be a large multiple of the payload — and evolution without a registered schema is unmanaged, which is how you get the M12.4 problem.

The pragmatic note: **JSON with a registered JSON Schema** gets you most of the governance benefit while staying readable, and is a reasonable compromise for a mid-volume bus where debuggability matters more than bytes.

**M7.5 — Kafka Streams and stateful processing**

A Java library (not a cluster) for processing Kafka topics — filtering, mapping, aggregating, joining, windowing — where your application *is* the stream processor.

The key concepts: **KStream** (a record stream), **KTable** (a changelog stream interpreted as current state per key, M8.5), and **state stores** (local RocksDB instances holding aggregation state).

**Where the state lives**, which is the important part: **locally, on the instance, in RocksDB — backed by a compacted changelog topic in Kafka** (M4.9). So state is fast (local disk, no network per lookup) and durable (recoverable by replaying the changelog). On failure or rebalance, another instance rebuilds the state from the changelog — which can take a long time for large state, and **standby replicas** (`num.standby.replicas`) exist to keep a warm copy and make failover fast.

Why it's attractive: **no separate cluster to operate** — it's a library, so it deploys like any other application (a Deployment in Kubernetes). It uses Kafka's consumer groups for scaling and Kafka's transactions for exactly-once (M5.7). Elastic scaling comes free from the consumer group protocol.

The limits: **JVM only**; **Kafka-to-Kafka only** (input and output must be Kafka); **less sophisticated than Flink** for complex event-time processing, large state, and advanced windowing (M8.8); and **rebalances are expensive with large state**, so the M6.4 settings matter a great deal here.

**M7.6 — ksqlDB at a decision level**

ksqlDB provides a SQL interface over Kafka Streams — you write streaming SQL and it runs as a Kafka Streams topology on a ksqlDB server cluster.

```sql
CREATE TABLE fraud_scores AS
  SELECT account_id, COUNT(*) AS attempts
  FROM payments WINDOW TUMBLING (SIZE 5 MINUTES)
  WHERE status = 'DECLINED'
  GROUP BY account_id
  EMIT CHANGES;
```

**When it's the right choice**: the transformations are genuinely expressible in SQL; the people who need to write them are analysts or engineers who know SQL but not the JVM; you want fast iteration on stream transformations without a deploy cycle; and the use case is filtering, enrichment, aggregation, and joins rather than arbitrary logic.

**When it isn't**: the logic needs anything SQL expresses awkwardly — calling an external service, complex conditional flows, custom serialisation; you need proper software engineering practice (version control, testing, code review) around the logic, which SQL statements in a server are poor at; or you don't want another cluster to operate, since ksqlDB servers are a deployment with their own scaling and failure modes.

The honest positioning: **ksqlDB lowers the barrier to stream processing and raises the ceiling problem.** Simple things become very easy; the moment you exceed SQL, you're rewriting in Kafka Streams or Flink anyway. It's also worth noting that **Confluent has de-emphasised it** in favour of Flink, which is relevant to a long-term platform bet.

**M7.7 — Change data capture and Debezium**

**CDC** reads a database's transaction log (Postgres WAL, MySQL binlog, MongoDB oplog) and emits a stream of row-level changes. **Debezium** is the standard implementation, usually deployed as Kafka Connect source connectors (M7.1).

Why it matters:

- **It solves the dual-write problem** (M2.6) — the database transaction is the only write, and the event is derived from the committed log. **Atomicity is guaranteed by the database**, which is the whole point. This is the strongest argument for CDC and the reason it belongs in this domain rather than just in data engineering.
- **It captures every change**, including those made by paths that don't publish events — legacy code, manual updates, batch jobs.
- **It's the standard way to get data out of a monolith** without modifying it — the strangler pattern's data half.
- **It gives before and after images** for each change, which is valuable for auditing and for computing deltas.

The operational realities to name:

- **Snapshot then stream.** The connector takes an initial consistent snapshot of the tables, then follows the log. **The snapshot can be very expensive** on a large table and can hold locks depending on the mode — this is the step that causes incidents.
- **Replication slots must be monitored.** In Postgres, an inactive slot causes WAL to accumulate and **can fill the disk and take down the database.** A stopped Debezium connector is a database availability risk, which surprises people badly.
- **Schema changes propagate** and must be handled (M7.3).
- **It emits table rows, not domain events.** A CDC stream of `orders` table changes is a leaky abstraction — consumers become coupled to your schema, which is precisely the coupling you were trying to avoid. **The outbox pattern combined with CDC is the better shape**: write purpose-designed events to an outbox table, and CDC that table rather than your domain tables.

**M7.8 — MirrorMaker and cross-cluster replication**

**MirrorMaker 2** (built on Kafka Connect) replicates topics between clusters, along with consumer group offsets and topic configurations.

Uses: **disaster recovery** (a standby cluster in another region), **aggregation** (many regional clusters into a central one for analytics), **migration** between clusters (M12.6), and **geo-locality** (data close to regional consumers).

The realities that make this harder than it sounds:

- **Replication is asynchronous**, so there's an RPO. A regional failure loses whatever hadn't replicated.
- **Offsets don't translate directly.** A record at offset 5000 in the source may be at a different offset in the target, because replication starts from a point in time and the logs aren't identical. MM2 provides offset translation via a checkpoints topic, but **it's approximate**, so failover means consumers may reprocess or skip. This is the crux of why active-passive Kafka failover is hard.
- **Topics are renamed by default** (prefixed with the source cluster alias) to prevent replication loops in bidirectional setups — which means consumer configuration differs between clusters, and forgetting this breaks failover.
- **Active-active is genuinely difficult** — the same key produced in two regions has no global ordering and conflict resolution is an application problem.
- **Cost** — cross-region data transfer on high-volume topics is substantial (M9.8, A12.4).

The judgement: **for DR, ask whether you actually need cross-region Kafka**, or whether the data can be reconstructed from the source systems after a regional failover. Replicating a high-volume bus continuously to a cluster you've never failed over to is expensive and unproven (A11.2, A11.8).

**M7.9 — MSK, Confluent Cloud, self-managed**

| | MSK | Confluent Cloud | Self-managed |
|---|---|---|---|
| Broker operations | AWS | Confluent | You |
| Upgrades | Guided, you choose timing | Transparent | You |
| Ecosystem | You run Connect, Registry, Streams (or MSK Connect / Glue Registry) | All included and managed | You run everything |
| Cost model | Broker-hours + storage (+ Serverless option) | Throughput/storage/partition based | Infrastructure + engineering time |
| Lock-in | Low — standard Kafka | Higher — proprietary extensions, KSQL, tiered features | None |
| Support | AWS | Kafka's originators | Yourself |

The judgement:

- **MSK** is the pragmatic default on AWS: managed brokers, IAM authentication (M11.2), VPC-native, and standard Kafka so you can leave. **You still operate the ecosystem** — Schema Registry, Connect, and your Streams applications — and you still own partition planning, topic management, and client tuning. **MSK does not make you not-a-Kafka-operator**, which is the misconception worth correcting.
- **Confluent Cloud** removes the most operational burden and includes the ecosystem. Expensive at scale, and the proprietary surface (ksqlDB, some connectors, Stream Governance) creates real lock-in. Best fit where Kafka is critical and you have no appetite for a platform team.
- **Self-managed** only with a specific driver — regulatory constraints on where data lives, an on-prem estate, or scale where the managed premium exceeds a dedicated team's cost (M12.3). Rarely justified otherwise.

The frame that makes this a good answer: **compare on total cost of ownership including engineering time, and on what you still own in each case.** The gap between MSK and Confluent Cloud is mostly the ecosystem and the expertise; the gap between MSK and self-managed is the part most people underestimate.

---

## M8. Streaming concepts

**M8.1 — Event time vs processing time**

- **Event time** — when the thing actually happened, as recorded in the event (the timestamp the payment was made).
- **Processing time** — when your system got round to processing it.

They diverge constantly: network delay, a consumer backlog (M6.7), a mobile client offline for an hour, a batch replay (M2.10), a retry.

**Why it matters**: aggregations computed on processing time are **not reproducible and not correct**. "Payments per hour" computed on processing time attributes a payment delayed by two hours to the wrong hour, and **replaying the same data produces a different answer** because processing times differ on replay. Event time gives you a deterministic result — the same input always produces the same output, which is essential for anything reconciled or audited.

The cost of event time: **you must wait for late data** (M8.3) or accept incomplete windows, which means results are delayed or revised. Processing time gives immediate answers that are wrong in a specific, bounded way.

The rule to state: **use event time for anything correctness-sensitive — financial aggregations, reconciliation, billing — and processing time for operational monitoring where latency matters more than exactness.** And the practical requirement: **the event must carry a trustworthy timestamp set by the producer**, which means it's a schema and governance concern (M12.5), not just a processing configuration.

**M8.2 — Windowing**

- **Tumbling** — fixed size, non-overlapping, contiguous. Every event in exactly one window. "Count per 5-minute interval."
- **Hopping** — fixed size, fixed advance, **overlapping** when the advance is smaller than the size. A 5-minute window advancing every minute means each event appears in 5 windows. "Rolling 5-minute count, updated every minute."
- **Sliding** — a window defined relative to each event, containing everything within the interval around it. Used for pairwise comparisons and joins.
- **Session** — dynamically sized, defined by a **gap of inactivity**. Events for a key are grouped until there's a gap longer than the timeout. "A user's browsing session" — no fixed duration; it ends when they stop.

Choosing: **tumbling** for regular reporting periods (per-hour billing, per-minute metrics) — it's the simplest and each event counts once. **Hopping** for smoothed rolling metrics — with the caveat that each event contributes to several windows, so state and output volume multiply. **Session** for activity-based grouping where the natural boundary is inactivity, which is genuinely the right model for user behaviour and fraud patterns.

The practical concerns: **windowed state grows with the number of windows retained**, so a hopping window with a small advance is expensive; **windows must be retained past their end to accept late data** (M8.3), which is what `grace period` controls; and **session windows can merge retroactively** when a late event bridges two sessions, which is powerful and makes the state management noticeably more complex.

**M8.3 — Late-arriving data and watermarks**

**Late data** is an event whose event time falls in a window you've already closed and emitted a result for.

**A watermark** is the system's assertion that "no further events with event time earlier than T are expected" — it's a heuristic that lets a stream processor decide when a window is complete enough to emit.

The mechanism: as events flow, the processor tracks the maximum observed event time and subtracts an allowed lateness to produce the watermark. When the watermark passes a window's end, the window fires.

The handling options for data arriving after the watermark:

- **Drop it** — simple, and silently loses data. Must be **monitored**, or you're discarding records with no visibility.
- **A grace period** — keep windows open past their end (Kafka Streams' `grace()`), accepting late events and re-emitting updated results. Bounded by how long you'll hold state.
- **Emit updates / retractions** — the downstream consumer must handle a corrected result replacing an earlier one, which pushes complexity outward but is the most correct.
- **A side output** for late records, processed separately or reconciled in batch.

The tradeoff to articulate: **the watermark delay is a direct trade between latency and completeness.** A short delay gives fast results that may be revised or wrong; a long delay gives accurate results late. **There is no setting that gives both**, and choosing it is a business decision about how wrong a fast answer is allowed to be.

The related architectural point: this is why some organisations keep a **batch reconciliation pass** alongside the stream — the stream gives fast approximate answers, the batch gives the authoritative one. That's the surviving kernel of the lambda architecture idea, and it's a defensible pattern in finance specifically.

**M8.4 — Stateful processing and where the state lives**

Stateless operations (filter, map) need no memory of previous records. **Stateful** operations — aggregations, joins, windows, deduplication — must remember.

**Where the state lives** by system:

- **Kafka Streams** — locally in **RocksDB** on each instance, backed by a **compacted changelog topic** in Kafka (M4.9, M7.5). Local reads are fast; durability comes from the changelog.
- **Flink** — in a configurable state backend (heap or RocksDB) with **periodic checkpoints** to durable storage (S3, HDFS), and **savepoints** for deliberate snapshots.
- **A custom consumer** — wherever you put it, usually an external store, which means a network call per lookup.

The operational implications, which are the substance of the item:

- **State makes instances non-interchangeable.** A consumer holding state for partition 3 cannot be trivially replaced — the replacement must rebuild that state.
- **Rebuild time dominates recovery.** Restoring a large state from a changelog can take minutes to hours, during which the partition isn't processing. **This is what makes rebalances expensive for stateful applications** (M6.3) and why standby replicas and static membership (M6.4) matter so much more here.
- **Local state means local disk** — in Kubernetes, that's a StatefulSet with persistent volumes (K2.8), or accepting a rebuild on every pod move. This is a real deployment constraint people discover late.
- **State size must be planned.** Unbounded aggregation state (grouping by a high-cardinality key with no window or retention) grows forever and eventually exhausts disk.
- **External state trades local speed for operational simplicity** — a Redis or DynamoDB lookup per record is slower but the processing instances become stateless and disposable. For moderate throughput that's frequently the better engineering trade, and it's worth naming rather than assuming local state is always right.

**M8.5 — Stream-table duality**

**A stream is a table's changelog; a table is a stream's current state.**

- Given a **stream** of changes keyed by entity, replaying it and keeping the latest value per key produces a **table** — the current state.
- Given a **table**, capturing every change produces a **stream** — the changelog.

They are two representations of the same information, and you can convert freely in both directions.

Why it matters practically:

- **It's the model behind Kafka Streams' KStream and KTable**, and behind compacted topics (M4.9) — a compacted topic *is* a table stored as a stream.
- **It's what CDC does** (M7.7): turning a database table into a stream of changes.
- **It's why event sourcing works** (M8.7) — the event log is the source of truth, and any current-state view is a derived table you can rebuild by replay.
- **It resolves the "should this be a stream or a table" question**: it's both, and the choice is about which representation is convenient for the consumer.

The concrete consequence for design: **you don't need to publish both an event stream and a state snapshot.** Publish the stream, and let consumers materialise the table they need — with a compacted topic if bootstrapping from the beginning of history is too expensive.

**M8.6 — Joins in a streaming context**

The types and their constraints:

- **Stream-stream join** — joining two unbounded streams. **Requires a window**, because you cannot wait indefinitely for a match. Both sides' records must be buffered for the window duration, so **state grows with window size × throughput**. Used for correlating related events (an order and its payment within 10 minutes).
- **Stream-table join** — enriching each stream record with the current table value for its key. **No window needed** — the table is a lookup. Cheap and the most common. The subtlety: **it's not deterministic on replay** unless the table is versioned by event time, because the table's "current" value depends on when you process.
- **Table-table join** — joining two changelogs, producing a new changelog. Both sides materialised as state.

The constraints that catch people:

- **Co-partitioning is mandatory** for most joins: both inputs must have the same number of partitions and the same partition key, so matching records land on the same instance. **If they don't, the join silently produces nothing or requires an expensive repartition step.** This is the single most common streaming-join failure and it's not obvious from the code.
- **Windowed joins hold state proportional to the window**, so a long window on a high-volume stream is expensive.
- **Late data** affects join results (M8.3) — a match arriving after the window closes is missed.
- **Foreign-key joins** (joining on something other than the partition key) are supported in newer Kafka Streams but involve internal repartitioning and are much more expensive.

**M8.7 — Event sourcing and its operational implications**

Event sourcing stores **the sequence of events that led to the current state as the source of truth**, rather than storing current state and mutating it. Current state is derived by replaying events.

The benefits: **a complete audit trail by construction** — every change with its cause, which in a regulated environment is genuinely valuable; **temporal queries** ("what was this account's balance on the 3rd"); **the ability to derive new projections** from history when a new requirement appears; and **debugging by replay**.

The operational implications, which is what the item asks for:

- **The event log is now a permanent, immutable source of truth**, so it can never be deleted — which collides directly with GDPR erasure requirements (M11.5, M11.6) and is the hardest problem in event-sourced systems handling personal data.
- **Schema evolution is forever.** You must be able to read events written years ago with today's code. Old event versions never go away, so upcasting logic accumulates.
- **Rebuild time grows with history.** Replaying millions of events to rebuild a projection takes real time, which matters for recovery. **Snapshots** are the standard mitigation — periodically persist the derived state so replay starts from there.
- **Queries need separate projections** (CQRS in practice), because you cannot query an event log the way you query a table. That's a second set of stores to build, maintain, and keep consistent.
- **Eventual consistency between the log and projections** is inherent, with all the M1.8 consequences.
- **It's harder to hire for and harder to reason about**, and a partially-understood event-sourced system is worse than a well-built CRUD one.

The judgement: **event sourcing is right where the history is genuinely the valuable artefact** — ledgers, trading, audit-heavy domains. It's a heavy commitment adopted for the wrong reasons surprisingly often, and "we might want the history later" doesn't justify it.

**M8.8 — Kafka Streams, Flink, Spark Streaming**

| | Kafka Streams | Flink | Spark Structured Streaming |
|---|---|---|---|
| Deployment | A library in your app | A cluster (or K8s operator) | A cluster |
| Sources/sinks | Kafka only | Many | Many |
| State | Local RocksDB + changelog | Configurable, checkpointed | Checkpointed |
| Event time | Good | **Best in class** | Good |
| Latency | Low (per-record) | Very low (true streaming) | Micro-batch (higher, though continuous mode exists) |
| Operational cost | Lowest — it's just an app | Highest | High |
| Language | JVM | Java/Scala/Python/SQL | Scala/Java/Python/SQL |

The decision:

- **Kafka Streams** when input and output are Kafka, the team is JVM-based, and you want no extra cluster. **The operational simplicity is the killer feature** — it deploys like any other service, scales with consumer groups, and there's nothing new to run. For most Kafka-to-Kafka transformation this is the right answer.
- **Flink** when you need sophisticated event-time semantics, very large state, exactly-once across heterogeneous sources and sinks, or genuinely low latency at high volume. It's the most capable stream processor and the industry has consolidated around it — but it's a cluster with its own operational model, checkpointing configuration, and expertise requirement.
- **Spark Structured Streaming** when you already run Spark for batch and want one engine and one skill set across both. The micro-batch model means higher latency, which is fine for many pipelines and disqualifying for some.

The honest framing: **choose based on what you already operate and what latency you actually need.** Adding a Flink cluster to a shop with no Flink experience for a job Kafka Streams could do is a poor trade; conversely, forcing complex event-time windowing into Kafka Streams because you don't want a cluster produces a fragile application.

---

## M9. Operations

**M9.1 — Sizing a cluster**

Work from throughput and retention:

1. **Ingress throughput** — records/sec × average record size. Then **multiply by replication factor** for the write volume the cluster actually handles: RF=3 means 3× the network and disk writes of your producer rate. **This is the number people forget** and it's why clusters are undersized by a factor of three.
2. **Egress** — ingress × number of consumer groups, plus replication traffic.
3. **Storage** — ingress/sec × retention seconds × RF, plus headroom (aim to stay under 60–70% disk to leave room for spikes and rebalances). A topic at 10 MB/s with 7-day retention and RF=3 needs roughly 18 TB.
4. **Brokers** — enough for the throughput, the storage, and **N+1 for failure**: the cluster must handle full load with one broker down, and with enough disk that one broker's partitions can be replicated elsewhere.
5. **Partitions** — per M4.11, then check the total against per-broker limits (a few thousand partitions per broker is a reasonable ceiling; KRaft raises cluster-wide limits considerably).

The constraints that usually bind first: **network** (replication multiplies it), **disk throughput** (not capacity — sequential write bandwidth), and **partition count per broker** (file handles, memory for index structures, and replication overhead).

The points worth adding: **leave substantial headroom** — a cluster at 80% has no capacity to recover from a broker failure, when surviving brokers take over its partitions and its traffic. **Storage tiering** (available in MSK and Confluent) moves older segments to object storage, which decouples retention from broker disk and materially changes the sizing arithmetic for long retention.

**M9.2 — Adding a broker and rebalancing partitions**

**Adding a broker does nothing on its own.** It joins the cluster and sits empty — Kafka does not automatically move partitions to it. This surprises people, and it's the first thing to say.

The process:

```bash
# 1. generate a proposed reassignment
kafka-reassign-partitions.sh --bootstrap-server broker:9092 \
  --topics-to-move-json-file topics.json \
  --broker-list "1,2,3,4" --generate

# 2. execute, with a throttle
kafka-reassign-partitions.sh --bootstrap-server broker:9092 \
  --reassignment-json-file reassign.json --execute \
  --throttle 50000000        # bytes/sec

# 3. verify, and remove the throttle when complete
kafka-reassign-partitions.sh --bootstrap-server broker:9092 \
  --reassignment-json-file reassign.json --verify
```

**The throttle is the critical part.** Reassignment copies partition data between brokers, and unthrottled it saturates network and disk, which **starves normal replication, causes ISR shrink, and can make producers with `acks=all` fail** (M4.5). A rebalance that takes down the cluster is a genuinely common self-inflicted incident — the "without disrupting traffic" in the item is doing real work.

Other essentials: **do it incrementally**, a subset of topics or partitions at a time, rather than reassigning everything at once. **Monitor under-replicated partitions throughout** (M10.1) — if they climb, the throttle is too high. **Remember to remove the throttle** after verification, or replication stays limited indefinitely and you have a mystery performance problem weeks later. And **rerun preferred leader election** afterwards to balance leadership (M4.3).

**Cruise Control** automates all of this with continuous rebalancing and goal-based optimisation, and it's the right answer for a cluster of any size.

**M9.3 — Rolling broker upgrade**

The sequence:

1. **Read the upgrade notes** for the target version, particularly `inter.broker.protocol.version` and `log.message.format.version` requirements.
2. **Verify the cluster is healthy first** — zero under-replicated partitions, balanced leadership. **Never start an upgrade on an unhealthy cluster**, because you're about to remove capacity deliberately.
3. **Pin `inter.broker.protocol.version` to the current version** in the config, so upgraded brokers still speak the old protocol and can coexist with un-upgraded ones.
4. **Restart brokers one at a time.** For each: **gracefully shut down** (controlled shutdown migrates leadership off the broker rather than forcing an election), upgrade, restart, and **wait for zero under-replicated partitions before moving to the next.** That wait is the discipline — proceeding while replicas are catching up compounds risk.
5. **Once every broker is on the new version**, bump `inter.broker.protocol.version` and do a second rolling restart.

The points that matter: **one broker at a time, with full recovery between**, because with RF=3 and min ISR=2 you can afford one broker down and not two (M4.5). **Controlled shutdown** avoids an unnecessary leader election storm. **Rebalance leadership afterwards** (M4.3) — brokers don't reclaim preferred leadership automatically after restart, so the cluster ends up lopsided. And **client compatibility** — Kafka's protocol is broadly backward compatible, but check.

On MSK, this is largely orchestrated for you, though **you still choose when**, and the same health preconditions apply.

**M9.4 — Broker failure: what recovers automatically**

**Automatic:**

- **Leadership fails over** to an in-sync replica within seconds (M4.6). Producers and consumers refresh metadata and reconnect to the new leader — a brief error spike, then normal.
- **The partition remains available** provided the ISR was adequate.
- **Consumers continue** — no rebalance is triggered by a broker failure (that's a *consumer* group event, M6.3), though the group coordinator may move if it was on that broker.
- **On broker return**, replicas catch up and rejoin the ISR automatically.

**Not automatic, and this is the important half:**

- **Under-replication persists** while the broker is down. The cluster is running with reduced durability, and **if `min.insync.replicas` is now unsatisfiable, producers with `acks=all` are failing** (M4.5) — which is why a single broker failure can look like a production outage.
- **Leadership does not rebalance on return.** The recovered broker follows but doesn't lead until preferred leader election runs (M4.3) — so the surviving brokers stay overloaded.
- **Partitions are not reassigned** to a replacement broker (M9.2). If the broker is permanently lost, you must reassign explicitly, or those partitions stay under-replicated forever.
- **If the disk is lost**, the replacement broker must replicate everything from scratch — hours for a large broker, and that catch-up traffic itself loads the cluster.

The framing: **Kafka handles a broker failure gracefully and does not handle broker *loss* automatically.** Distinguishing "down and coming back" from "gone" is the operational decision, and the second one requires deliberate action.

**M9.5 — Disk usage, retention, and running out of space**

**Disk full is the classic Kafka outage** and deserves to be named as such. When a broker's disk fills, it **cannot write**, which means it stops accepting produce requests and stops replicating — so it falls out of the ISR for its follower partitions, and its leader partitions become unavailable.

The causes:

- **Retention set too long** for the volume (M4.8).
- **Volume growth** outpacing the sizing assumption.
- **A topic created without explicit retention**, inheriting a long cluster default.
- **Compaction not keeping up**, or a compacted topic with an unbounded key space.
- **Reassignment traffic** (M9.2) temporarily doubling data on a broker.
- **A consumer that's down**, in a tiered-storage setup, preventing offload.

The management:

- **Monitor disk usage per broker with a threshold alert well before full** — 70% is a reasonable trigger, because remediation takes time.
- **Set explicit retention per topic** rather than relying on defaults, and enforce it at topic creation (M9.9).
- **`log.retention.bytes` per partition** as a backstop, so a single runaway topic can't consume the broker.
- **Use both time and size retention** so neither alone can surprise you (M4.8).
- **Storage tiering** where available, which moves the problem to object storage and largely removes it.

**In an emergency** — a broker approaching full: reduce retention on the largest topics (it takes effect on the next log cleaner run and frees space quickly), delete unused topics, or add disk if the platform allows online expansion (A6.8). **Deleting log segments manually is dangerous** and should be a last resort.

**M9.6 — Quotas and protecting from a noisy client**

Kafka supports quotas per client-id, per user, or per user+client-id combination:

- **Network bandwidth quotas** — produce and fetch bytes/sec.
- **Request rate quotas** — a percentage of broker request-handler thread capacity, which catches clients making enormous numbers of small requests.

```bash
kafka-configs.sh --bootstrap-server broker:9092 --alter \
  --add-config 'producer_byte_rate=10485760,consumer_byte_rate=20971520' \
  --entity-type clients --entity-name analytics-batch-job
```

Enforcement is by **throttling, not rejecting**: the broker delays the response to bring the client's rate within the quota. So a throttled client sees increased latency rather than errors — which is graceful and also means **throttling can be invisible unless you monitor it** (the `throttle-time` metrics).

Why it matters in a multi-tenant cluster (M9.10): **one team's batch job or backfill can saturate broker network and disk, degrading every other tenant.** Quotas are the mechanism that makes a shared cluster safe, and without them "shared" means "everyone's performance depends on everyone else's behaviour".

The practicalities: **quotas are per broker, not cluster-wide**, so a client's effective total is the quota times the number of brokers it talks to. **Set defaults** so a new client can't arrive unbounded. And **quotas require meaningful client IDs**, which means a naming convention teams actually follow — a governance requirement more than a technical one.

**M9.7 — Rack awareness and multi-AZ placement**

`broker.rack` tags each broker with its availability zone. Kafka's replica assignment then **spreads a partition's replicas across racks**, so RF=3 across three AZs means one replica per AZ and **an AZ failure leaves the partition available with the ISR intact**.

Without it, replica assignment is rack-blind and all three replicas of a partition can land in one AZ — so a zonal failure takes the partition fully offline despite RF=3, which entirely defeats the replication.

The costs to acknowledge:

- **Cross-AZ replication traffic is charged in both directions** (A12.4), and with RF=3 across AZs, every produced byte crosses AZ boundaries twice. **On a high-volume cluster this is a substantial and often unexpected bill.**
- **Produce latency increases** with `acks=all`, since the leader waits for cross-AZ replicas.
- **Consumers fetch from the leader by default**, so a consumer in a different AZ pays cross-AZ transfer for everything it reads. **Follower fetching** (`client.rack` plus rack-aware replica selection) lets consumers read from a local replica — a significant cost reduction and worth naming, since it's under-used.

The judgement: **rack awareness is non-negotiable for anything requiring AZ resilience**, and the cost is the price of that resilience (A11.4). The optimisation lever is follower fetching, not reducing replication.

**M9.8 — The cost and risk of cross-region streaming**

**Cost**: cross-region data transfer is charged per GB and is materially more expensive than cross-AZ (A12.4). Replicating a topic at 50 MB/s continuously across regions is a large, ongoing bill — and it's charged on the raw stream, so retention doesn't reduce it.

**Risks:**

- **Asynchronous replication means a real RPO** (M7.8). A regional failure loses in-flight data.
- **Offset translation is approximate**, so consumer failover means reprocessing or skipping (M7.8). This is the hard part of cross-region Kafka DR and the reason many such setups have never actually been failed over.
- **Latency** makes synchronous cross-region replication impractical, so you cannot have both regions writing the same partition consistently.
- **Active-active means conflict resolution**, which is an application problem with no infrastructure solution.
- **Operational complexity doubles** — two clusters, two sets of topics with different names (M7.8), two monitoring surfaces, and a failover procedure that must be rehearsed (A11.8).

The judgement to express, which mirrors A11.3: **ask whether you need the Kafka data in the second region, or whether you need the *system* to work there.** Often the events can be regenerated from the source systems after failover, or the second region only needs the current state rather than the history — both of which are far cheaper than continuous replication. Cross-region streaming is justified when the log itself is the source of truth (M8.7) and its loss is unacceptable; it's frequently adopted as a default when it isn't.

**M9.9 — Topics as code**

Ad hoc topic creation — `kafka-topics.sh --create` by whoever needs one, or worse, `auto.create.topics.enable=true` — produces: inconsistent partition counts and replication factors, missing or default retention (M9.5), no ownership, no naming convention, and topics nobody can account for.

**Managing topics as code** means declaring them in a repository with their configuration, reviewed and applied by a pipeline:

```yaml
topics:
  - name: payments.transactions.v1
    partitions: 12
    replication_factor: 3
    config:
      min.insync.replicas: "2"
      retention.ms: "604800000"
      cleanup.policy: delete
    owner: payments-team
    schema: avro://payments.transactions.v1
```

Tools: the **Terraform Kafka provider**, **Strimzi's `KafkaTopic` CRD** on Kubernetes (which reconciles continuously, K12.2), **Julie Ops**, or a purpose-built pipeline.

The benefits: **reviewed changes** (partition count is hard to change later, M4.11, so getting it reviewed matters); **consistent defaults** enforced by a module or template; **ownership recorded** (M9.10); **auditability**; and **reproducibility** in a new cluster or a DR environment.

**Disable `auto.create.topics.enable`** as the first step — auto-creation produces topics with default partitioning and default retention at the moment a typo'd topic name is used, and cleaning those up later is tedious. This is a one-line change with disproportionate value.

**M9.10 — Multi-tenancy: naming, isolation, ownership**

**Naming convention** is the foundation, because everything else keys off it:

```
<domain>.<entity>.<event-type>.v<version>
payments.transaction.completed.v1
```

Naming carries the domain (which team owns it), the entity, the event type, and the version. **A convention that encodes ownership is what makes ACLs, quotas, and alerting routable by prefix** — `payments.*` maps to a team, a set of ACLs (M11.3), and a quota (M9.6).

**Isolation mechanisms**, in increasing strength:

- **ACLs** per prefix — the minimum, and it's authorisation, not isolation (M11.3).
- **Quotas** per client — protects against noisy neighbours (M9.6). Essential on a shared cluster.
- **Separate topics with distinct retention and partition counts** — the normal boundary.
- **Separate clusters** — genuine isolation for compliance boundaries or wildly different workload profiles, at the cost of running more clusters.

**Ownership** must be explicit and recorded: every topic has an owning team, a documented schema (M7.2), and a stated retention and PII classification (M11.5). **A topic with no owner is the failure state** — nobody can approve schema changes, nobody responds when it's misbehaving, and nobody can say whether it's safe to delete.

The framing: **a shared Kafka cluster is a multi-tenant platform, and it needs the same governance as any other** — naming, ownership, quotas, ACLs, and a catalogue (M12.5, M12.7). Without those, it becomes the undocumented integration layer in M12.4.

---

## M10. Observability & troubleshooting

**M10.1 — The metrics that matter**

**Consumer side:**

- **Consumer lag** — records and, more usefully, **time behind** (M6.7, M10.2). The primary business-impact signal.
- **Rebalance rate** — frequent rebalances mean instability (M10.4).
- **Records consumed/sec, and processing time per batch.**
- **Commit failure rate** — `CommitFailedException` indicates eviction (M6.8).

**Broker side:**

- **`UnderReplicatedPartitions`** — should be **zero**. Non-zero means reduced durability and possible produce failures (M4.5, M10.3). The single most important broker alert.
- **`UnderMinIsrPartitionCount`** — partitions below `min.insync.replicas`. **Producers with `acks=all` are failing right now.** More urgent than under-replicated.
- **`OfflinePartitionsCount`** — partitions with no leader. Unavailable. Should always be zero.
- **`ActiveControllerCount`** — must be exactly 1 across the cluster. Zero means no controller; more than one means split brain.
- **ISR shrink/expand rate** — churn indicates instability even when the current count looks fine.
- **Request latency** (produce and fetch, p99) and **request handler idle ratio** — a low idle ratio means the broker is saturated.
- **Disk usage per broker** (M9.5) and **network throughput.**

**Producer side:**

- **Record error rate**, **retry rate**, **buffer available bytes** (M5.9), and **request latency.**

The framing to give: **`UnderReplicatedPartitions` and consumer lag are the two you'd alert on if you could only have two** — one for cluster health, one for business impact.

**M10.2 — Alerting on consumer lag meaningfully**

**Alerting on raw record count is the common mistake.** A threshold of 10,000 records means different things on different topics and at different times of day — it fires constantly during normal spikes on a busy topic and never fires on a slow topic that's hours behind.

**Alert on time lag**: how far behind in wall-clock terms the consumer is. Either the difference between now and the event time of the last committed record, or the record lag divided by the current consumption rate to project drain time.

Better still, **alert on the business consequence**:

- **"Payments are being processed more than 5 minutes after receipt"** — meaningful, actionable, and maps to an SLO.
- **"Lag is growing and projected drain time exceeds 30 minutes"** — catches the sustained-growth case rather than a spike.
- **Different thresholds for different topics**, because a fraud-check pipeline and an analytics feed have entirely different tolerances.

The refinements that reduce noise: **alert on the derivative, not just the level** — steadily growing lag is a problem even at a low absolute value, while a large spike that's draining is often fine. **Suppress during known batch windows.** And **exclude idle consumer groups**, which otherwise alert perpetually.

The related check that's frequently missing: **alert when a consumer group has no members**, which is not lag but is the most complete failure — lag stops growing when nothing is producing either, so a dead consumer group on a quiet topic is invisible to lag alerting entirely.

**M10.3 — Diagnosing under-replicated partitions**

`UnderReplicatedPartitions > 0` means at least one replica is out of the ISR (M4.4).

The diagnostic sequence:

```bash
kafka-topics.sh --bootstrap-server broker:9092 --describe --under-replicated-partitions
```

1. **Is it concentrated on one broker?** If the same broker is missing from every affected partition's ISR, that broker is the problem. Check it directly.
2. **Broker-level causes**: disk saturation or failure (check I/O wait and disk latency), network saturation, CPU exhaustion, **long GC pauses** (a classic and easily missed cause — check GC logs), or the broker being down entirely (M9.4).
3. **Cluster-level causes**: a **partition reassignment running unthrottled** (M9.2) consuming replication bandwidth; a sudden traffic spike exceeding replication capacity; or too many partitions per broker for the replication threads (`num.replica.fetchers`).
4. **Is it spread evenly?** That suggests a cluster-wide capacity problem rather than one bad broker.

**Why it's urgent rather than informational**: reduced durability now, and **if the ISR drops below `min.insync.replicas`, producers using `acks=all` are already failing** (M4.5). So an under-replicated partition alert can be a live production outage rather than a warning, and treating it as informational is a mistake.

The immediate mitigations: throttle or pause a running reassignment; take load off the affected broker; add replica fetcher threads. The structural fix is usually capacity (M9.1).

**M10.4 — A consumer group stuck in perpetual rebalance**

The symptom: continuous "rejoining group" and "member has left the group" log lines, lag that never drains, and near-zero throughput despite consumers appearing to run.

**The causes, in order of likelihood:**

1. **`max.poll.interval.ms` exceeded** (M6.8) — processing a batch takes longer than the interval, the consumer is evicted mid-batch, rejoins, gets the same records, and repeats. **This is the most common cause by a wide margin.** The tell is `CommitFailedException` in the logs alongside the rebalances.
2. **A consumer crashing and restarting repeatedly** — an OOM kill (K6.3), a poison message causing an unhandled exception (M2.7), or a failing liveness probe (K9.11). Each restart is a rebalance.
3. **`session.timeout.ms` too short** relative to GC pauses or network jitter, so healthy consumers are declared dead.
4. **A rolling deployment** — expected and transient, unless it never finishes.
5. **Large state rebuild** on each rebalance causing the next `poll()` to be late, triggering another rebalance — a self-sustaining loop for stateful applications (M8.4).

The diagnosis: consumer logs are definitive — they say why the member left. Check `max.poll.interval.ms` against actual batch processing time first.

The fixes: **reduce `max.poll.records`** (usually the right one), increase the interval, fix the crash, adopt **cooperative rebalancing and static membership** (M6.4) which prevents the deployment case entirely, and add standby replicas for stateful applications.

**M10.5 — Diagnosing a producer failing to publish**

Work through the error, because Kafka's producer exceptions are specific:

- **`TimeoutException: Topic not present in metadata`** — the topic doesn't exist (and auto-create is off, M9.9), or the producer can't reach a broker to fetch metadata.
- **`NotEnoughReplicasException` / `NotEnoughReplicasAfterAppendException`** — `acks=all` with the ISR below `min.insync.replicas` (M4.5). **The cluster is under-replicated** (M10.3) — the producer is a symptom, not the cause.
- **`TimeoutException: Expiring N records`** — records sat in the buffer past `delivery.timeout.ms`. Broker slow, network problem, or the producer is overwhelmed (M5.9).
- **`RecordTooLargeException`** — exceeds `max.request.size` or the broker's `message.max.bytes` (M3.10).
- **`TopicAuthorizationException`** — ACLs (M11.3).
- **`SSLHandshakeException` / `SaslAuthenticationException`** — TLS or auth configuration (M11.1, M11.2), often an expired certificate.
- **Blocking in `send()`** — buffer exhaustion (M5.9).

The systematic approach: **check cluster health first** (`UnderReplicatedPartitions`, M10.1) because a large share of producer failures are broker-side; then connectivity and auth; then producer configuration. And **check whether the producer's callback is being handled at all** — fire-and-forget `send()` with no callback swallows failures silently, so "the producer isn't failing" sometimes means "we aren't looking".

**M10.6 — Tracing a message end to end**

The mechanism: **propagate a trace context through the message headers.**

```java
producer.send(new ProducerRecord<>(topic, key, value) {{
    headers().add("traceparent", currentTraceContext().getBytes());
    headers().add("correlation-id", correlationId.getBytes());
}});
```

OpenTelemetry's Kafka instrumentation does this automatically, creating a producer span, injecting `traceparent` into the headers, and creating a linked consumer span on the other side (A9.8).

**Why it's essential rather than nice-to-have**: in a synchronous system, a stack trace connects cause and effect. In an asynchronous one, the producer's work finished long before the consumer's began, potentially in a different service, minutes later. **Without a propagated trace ID there is no way to connect them**, and "the email never arrived" becomes an unbounded search across services.

The practicalities:

- **Log the trace ID and message key at both ends** — the trace shows the path, the logs show the detail, and correlating them requires the ID in both (A9.2).
- **Include the trace ID when dead-lettering** (M2.9), or a DLQ message is uninvestigable.
- **Spans should be linked, not nested.** A consumer span isn't a child of the producer span in the usual sense — the relationship is a link, because the consumer may process the message much later and the producer's span has long since closed. Getting this wrong produces traces spanning hours with misleading durations.
- **Sampling must be consistent** — a sampled-out producer span means a consumer span with no parent.
- **Batch processing complicates it** — one poll of 500 records with 500 different trace contexts needs per-record span creation, not one span for the batch.

**M10.7 — A message published but never processed**

Work down the path, and each step has a definitive check:

1. **Was it actually published?** Producer logs and the callback result (M10.5). A fire-and-forget `send()` that failed silently is a very common answer, and it means the message never existed.
2. **Is it in the topic?** Read the partition directly:

```bash
kafka-console-consumer.sh --bootstrap-server broker:9092 \
  --topic payments --partition 3 --offset 45210 --max-messages 1 \
  --property print.key=true --property print.headers=true
```

If it's not there, it was never published or went to a different topic/partition than expected.
3. **Which partition did it go to?** If the key was null (M5.2), or the partitioner differs from the assumption, it may be somewhere the consumer isn't looking.
4. **Has the consumer group's committed offset passed it?** (M6.7). If the committed offset is beyond the record's offset, **the consumer skipped it** — which happens with auto-commit racing processing (M6.5), an offset reset (M6.9), or a manual commit that moved past a failure.
5. **Is the group's lag behind that offset?** Then it simply hasn't got there yet — the answer is lag, not loss.
6. **Did it fail and go to a DLQ/error topic?** (M6.11) — check there before concluding it vanished.
7. **Did the consumer process it and the side effect fail?** Trace ID (M10.6) and consumer logs. "Processed" and "the outcome happened" are different claims.
8. **Was it past retention?** (M4.8) — a consumer down longer than the retention window loses data permanently and silently, which is the most brutal version.

The point to make: **most "lost message" investigations end at step 1 or step 4** — it was never published, or it was skipped by an offset commit. Both are more common than genuine broker-side loss, which is rare with correct durability settings (M4.5).

**M10.8 — Growing lag: scale, optimise, or shed**

First **diagnose** (M6.7): even growth, spike, skew, or stuck partition. The response depends entirely on which.

**Scale** when the consumer is genuinely resource-bound and partitions allow:
- Add consumers up to the partition count (M6.2).
- Beyond that, add partitions (M4.11) or add in-consumer concurrency (M6.10).
- **Check the downstream first** — if the database is the bottleneck, more consumers make it worse (M1.9).

**Optimise** when consumers are not resource-saturated but throughput is low:
- Batch downstream operations rather than per-record calls — usually the single biggest win.
- Increase `max.poll.records` and fetch sizes.
- Remove synchronous external calls from the hot path.
- Fix the skew if that's the cause (M5.4) — no amount of scaling addresses it.

**Shed** when the backlog cannot be drained in acceptable time and the data has decreasing value:
- **Skip forward** by resetting offsets (M6.9), abandoning the backlog deliberately.
- **Filter** low-value messages, processing only what matters.
- **Degrade** — process a simplified path that's much faster.
- Shedding is **data loss by choice** and must be a recorded decision with an owner, not an operator's improvisation.

The decision framework: **project the drain time.** If lag is 2 million records, the consumer does 5,000/s, and the produce rate is 3,000/s, then net drain is 2,000/s and it takes ~17 minutes — that's a wait, not an incident. If the produce rate exceeds consumption, **lag grows without bound and no amount of waiting helps** — that's the case requiring scale or shed. **Doing that arithmetic is the answer**, and it's what distinguishes a considered response from reflexively scaling.

**M10.9 — CLI tooling**

```bash
# topics
kafka-topics.sh --bootstrap-server b:9092 --list
kafka-topics.sh --bootstrap-server b:9092 --describe --topic payments
kafka-topics.sh --bootstrap-server b:9092 --describe --under-replicated-partitions
kafka-topics.sh --bootstrap-server b:9092 --alter --topic payments --partitions 24

# consumer groups
kafka-consumer-groups.sh --bootstrap-server b:9092 --list
kafka-consumer-groups.sh --bootstrap-server b:9092 --describe --group payments-proc
kafka-consumer-groups.sh --bootstrap-server b:9092 --describe --group payments-proc --members --verbose
kafka-consumer-groups.sh --bootstrap-server b:9092 --group g --topic t \
  --reset-offsets --to-datetime 2026-08-18T00:00:00.000 --dry-run

# reading
kafka-console-consumer.sh --bootstrap-server b:9092 --topic payments \
  --from-beginning --property print.key=true --property print.timestamp=true
kafka-console-consumer.sh --bootstrap-server b:9092 --topic payments \
  --partition 3 --offset 45210 --max-messages 5

# offsets at a point in time
kafka-get-offsets.sh --bootstrap-server b:9092 --topic payments --time -1   # latest

# config and storage
kafka-configs.sh --bootstrap-server b:9092 --describe --entity-type topics --entity-name payments
kafka-log-dirs.sh --bootstrap-server b:9092 --describe --topic-list payments
```

The fluency markers: **`--describe` on a consumer group is the single most-used command** and its output is the lag diagnosis (M6.7); **`--members --verbose`** shows partition assignment, which is how you spot idle consumers (M6.2); **`--dry-run` before any offset reset**, always (M6.9); **`kafka-log-dirs.sh`** for per-partition sizes when diagnosing skew (M5.4); and reading a specific partition and offset to prove whether a message exists (M10.7).

Worth naming: **`kcat` (formerly kafkacat)** is far more pleasant for ad hoc inspection than the shipped scripts, and **AKHQ / Kafka UI / Conduktor** give a browsable interface that most teams end up preferring for day-to-day work.

**M10.10 — A queue backing up in a live incident**

The sequence, and the ordering matters:

1. **Establish the trend and project it.** Is lag growing, flat, or draining? At what rate? **Projected drain time is the number that determines whether this is an incident or a wait** (M10.8).
2. **Establish business impact.** What is delayed, and does it matter? Payments delayed 20 minutes is very different from analytics delayed 20 minutes. **This determines urgency**, and it's the question to answer before touching anything.
3. **Find the constraint.** Consumers saturated (scale), consumers idle (something is blocking — poison message, stuck partition, downstream failure), or produce rate genuinely exceeding capacity. `kafka-consumer-groups --describe` shows the per-partition shape (M6.7).
4. **Check the downstream first.** A backed-up queue is very often a symptom of a database, an API, or a dependency being slow — and scaling consumers into a struggling dependency makes the outage worse. **This is the most important instinct to demonstrate.**
5. **Act proportionately:**
   - Downstream degraded → fix or protect the downstream; consider *reducing* consumer concurrency to relieve it.
   - Consumers under-scaled → scale out (M6.10).
   - Poison message → move it aside (M6.11).
   - Genuinely over capacity with an unacceptable drain time → shed load deliberately (M10.8), with a recorded decision.
6. **Communicate the expected drain time**, because that's what stakeholders need — not "we're looking at it".
7. **Watch for the recovery thundering herd.** When consumers scale up or a dependency recovers, the full backlog hits at once and can immediately re-break the thing that just recovered (M1.6). **Ramp deliberately** rather than restoring full capacity instantly.

The judgement to demonstrate: **a growing queue is a symptom, and the reflex to scale consumers is right about half the time and actively harmful the other half.** Establishing where the constraint actually is, before acting, is the whole skill (T1).

---

## M11. Security

**M11.1 — TLS in transit**

Configure listeners with a TLS security protocol:

```properties
listeners=SSL://0.0.0.0:9093
security.inter.broker.protocol=SSL
ssl.keystore.location=/etc/kafka/secrets/broker.keystore.jks
ssl.truststore.location=/etc/kafka/secrets/truststore.jks
ssl.client.auth=required        # for mTLS (M11.2)
```

Clients need the truststore containing the CA that signed the broker certificates, and for mTLS their own keystore.

The points that matter:

- **Certificate management is the real work**, not the configuration. Broker certificates need SANs covering every advertised hostname, and **expiry is a foreseeable cluster-wide outage** (A8.6) — alert on days-to-expiry, and automate issuance (cert-manager, ACM Private CA, A10.18).
- **TLS defeats zero-copy** (M4.10) — data must pass through user space for encryption, so broker CPU increases measurably and throughput drops. On a high-volume cluster this is a real capacity consideration, not a footnote, and it's the most interesting thing to say about Kafka and TLS.
- **Encrypt inter-broker traffic too**, not just client connections — replication carries the same data.
- **Both `SSL` and `SASL_SSL`** are TLS; the difference is whether authentication is certificate-based or SASL over the TLS channel (M11.2).

**M11.2 — Authentication options**

- **mTLS** — the client presents a certificate; the principal is derived from the certificate DN. No shared secrets, strong, and **certificate lifecycle is the burden** — issuing, distributing, rotating, and revoking per client. Revocation in particular is weak in practice, so short lifetimes matter more than CRLs (A10.18).
- **SASL/SCRAM** — username and password with salted challenge-response, credentials stored in Kafka (or ZooKeeper historically). Simpler to manage, and **you now have passwords to distribute and rotate** (A7.8). Common choice for self-managed clusters.
- **SASL/PLAIN** — username and password sent in the clear, so **only acceptable over TLS**, and credentials are usually in a static file, which makes rotation painful. Avoid where alternatives exist.
- **SASL/GSSAPI (Kerberos)** — where an enterprise Kerberos realm already exists.
- **SASL/OAUTHBEARER** — OIDC tokens, which fits a modern identity story and avoids long-lived secrets entirely.
- **IAM (MSK)** — AWS SigV4 authentication using the caller's IAM identity. **The best option on AWS by some margin**: no passwords, no certificates, credentials from the instance profile or IRSA (A2.6, A2.7), and authorisation expressed as IAM policy so it's managed with everything else. The tradeoff is AWS-specific lock-in and that IAM policy is coarser than Kafka ACLs for some patterns.

The framing: **prefer the option that eliminates long-lived secrets** — IAM on MSK, OAUTHBEARER elsewhere — for the same reason as A1.4 and A2.8. mTLS is strong but the certificate lifecycle is real work; SCRAM is pragmatic and leaves you with passwords to manage.

**M11.3 — ACLs for least-privilege topic access**

```bash
kafka-acls.sh --bootstrap-server b:9092 --add \
  --allow-principal User:payments-service \
  --operation Write --topic payments.transactions.v1

kafka-acls.sh --bootstrap-server b:9092 --add \
  --allow-principal User:fraud-service \
  --operation Read --topic payments.transactions.v1 \
  --group fraud-detector
```

The model: `(principal, operation, resource, permission)`, where resources are topics, consumer groups, transactional IDs, and the cluster. Resource patterns can be **literal or prefixed** — prefixed patterns on a naming convention (M9.10) are what make this manageable: `payments.*` granted to the payments team as one rule.

The details that catch people:

- **A consumer needs `Read` on the topic *and* `Read` on the consumer group.** Granting only the topic produces a `GroupAuthorizationException` that people misread as a topic permission problem. **This is the most common ACL mistake.**
- **`Describe` is needed for metadata**, and its absence produces confusing "topic not present in metadata" errors (M10.5) rather than clear authorisation failures.
- **Transactional producers need `Write` on the transactional ID** (M5.7).
- **`allow.everyone.if.no.acl.found=true`** is a dangerous default in some setups — it means a topic with no ACLs is world-accessible.
- **ACLs should be managed as code** alongside topics (M9.9), not applied ad hoc.

The principle mirrors A2.2: **enumerate the specific operations a service needs on the specific resources**, driven by the naming convention so it scales.

**M11.4 — Encryption at rest and its limits**

Kafka has **no built-in encryption at rest.** It's provided by the storage layer — encrypted EBS volumes (A10.12), MSK's KMS integration, or disk-level encryption.

**What it protects against**: physical media theft, an improperly decommissioned disk, and unauthorised access to a snapshot or the underlying volume. It satisfies a common compliance control.

**What it does not protect against**, which is the substance of the item:

- **Anyone with Kafka access.** The broker decrypts transparently, so a client with ACLs to read the topic gets plaintext. Encryption at rest is invisible to the entire application layer.
- **A compromised broker.** Root on the broker reads decrypted data.
- **An operator or administrator** with cluster access.
- **Data in the page cache** (M4.10), which is unencrypted memory.

So it protects against media-level threats and nothing above them. **If the requirement is that the platform operator cannot read the data, you need end-to-end encryption** — the producer encrypts the payload and only authorised consumers hold the key, with Kafka carrying ciphertext.

The costs of that: **key management and distribution** become your problem; **compaction and keys still leak metadata** (the key is unencrypted or you can't compact); **no server-side filtering or stream processing** on encrypted fields; and **schema validation can't inspect the payload**. Field-level encryption of just the sensitive fields is the usual compromise — it keeps routing and non-sensitive processing working while protecting the data that matters (M11.5).

**M11.5 — PII on an event bus and the retention/GDPR problem**

The tension is structural: **Kafka's log is immutable and append-only, and GDPR grants a right to erasure.** You cannot delete one record from the middle of a Kafka log.

Compounding it: **events fan out.** A record containing personal data has been consumed by an unknown number of downstream systems, each of which has copied it into its own store. Deleting from Kafka doesn't reach any of them.

The approaches:

1. **Don't put PII on the bus.** Publish an identifier and let consumers fetch personal data from the owning service, which can enforce erasure at one point. **This is the strongest answer** and it should be the default design (M3.10's "events should signal facts, not carry data" applied to privacy).
2. **Crypto-shredding** — encrypt personal fields with a per-subject key held externally. **Erasure means deleting the key**, after which the ciphertext in the log is unrecoverable. The log stays immutable; the data becomes unreadable. This is the standard technical answer for event-sourced systems that genuinely must carry personal data, and it's worth being able to name.
3. **Short retention** on topics carrying PII, so the problem ages out — with the caveat that it doesn't address downstream copies.
4. **Compaction with tombstones** (M11.6) for keyed topics.
5. **Pseudonymisation** — a stable surrogate ID on the bus, with the mapping held in one controllable place.

Whichever you choose, the governance requirements are the same: **classify every topic for PII** (M9.10), record it in the catalogue, and **know your consumers** — because an erasure request must propagate to every store derived from the stream, and you cannot do that without a consumer inventory (M12.5).

**M11.6 — Compaction, tombstones, and deletion requests**

On a **compacted topic** (M4.8), producing a record with a **key and a null value** — a **tombstone** — marks that key for deletion. The log cleaner removes prior values for the key, then removes the tombstone itself after `delete.retention.ms`.

**How this relates to deletion requests:**

- **It works for keyed state topics** — a compacted topic of customer records, keyed by customer ID, can honour an erasure request by publishing a tombstone. The value is eventually removed from the log.
- **The tombstone must survive long enough for every consumer to see it.** That's what `delete.retention.ms` is for: if a consumer is offline longer than that, it **never sees the tombstone and keeps the record in its own store forever** — silent non-compliance. Setting this window correctly requires knowing how long consumers can plausibly be down.
- **Compaction is asynchronous and best-effort.** Removal is not immediate, and the active segment is never compacted, so a recently-tombstoned value may persist for some time. **"Deleted" is eventual**, which may or may not satisfy a regulator's expectations.
- **It does not work for event-history topics.** A stream of `PaymentMade` events isn't keyed by person in a way compaction can meaningfully collapse, and compacting it would destroy the history that's the point of the topic. **This is why crypto-shredding exists** (M11.5).

The honest summary: **tombstones handle state topics; they do not handle event logs.** Being clear about that distinction — and reaching for crypto-shredding or not-putting-PII-on-the-bus for the event case — is the answer that demonstrates real understanding rather than knowledge of the feature.

**M11.7 — Audit: who published and consumed what**

The requirement in a regulated environment: demonstrate who wrote to a topic and who read it.

The mechanisms:

- **Broker authorizer logs** — the authorizer logs authorisation decisions, including denials, at a configurable level. This gives you principal, operation, and resource, and is the primary audit source in self-managed Kafka. **It's high volume**, so it needs routing to a log platform rather than sitting on brokers (A9.1).
- **CloudTrail on MSK** for control-plane operations (cluster and configuration changes), and IAM-based data access for MSK IAM auth (M11.2) — which is a meaningful advantage of IAM auth: access is expressed and logged in the same system as everything else (A9.5).
- **Consumer group metadata** — `kafka-consumer-groups --describe` shows which groups exist and are reading a topic, which is a point-in-time view rather than a historical record.
- **Message-level provenance** — headers carrying the producing service, a trace ID (M10.6), and a timestamp. **This is what actually answers "who produced this record"** after the fact, because broker logs don't retain per-record detail.
- **Confluent's audit logs** as a managed feature.

The design points: **audit requirements should shape the header convention** — a mandatory `producer-service`, `correlation-id`, and `event-time` on every message, enforced by the schema (M7.2), gives you record-level provenance that no infrastructure log will. And **the audit trail must live outside the cluster** and be tamper-resistant (A1.16), for the same reason as any other audit log.

The gap worth being honest about: **Kafka gives you good authorisation logging and poor per-record consumption auditing.** You can show which principals were authorised to read a topic; showing that a specific consumer read a specific record requires the consumer to log it. Where a regulator wants that, it's an application requirement.

---

## M12. Judgement

**M12.1 — Choosing between SQS, SNS, EventBridge, Kafka, and Kinesis**

The discriminating questions, asked in order:

1. **Does anything need to replay history or read from an arbitrary point?** → Kafka or Kinesis. Nothing else can.
2. **Do multiple independent consumers need the same data?** → pub/sub: SNS, EventBridge, or Kafka consumer groups. Not a bare SQS queue.
3. **Does ordering matter, and at what scope?** → Kafka (per partition), SQS FIFO (per message group), Kinesis (per shard). Standard SQS, SNS, and EventBridge give none.
4. **What throughput?** → Kafka for very high sustained volume; EventBridge is the slowest and has per-event pricing that adds up.
5. **Is routing decided by content?** → EventBridge (content-based rules) or RabbitMQ. SNS filters only on attributes.
6. **How much operational capacity do you have?** → SQS/SNS/EventBridge are zero-ops; Kinesis is managed with shard management; Kafka is a platform even on MSK (M7.9).

The quick mapping:

- **SQS** — work queue, buffering, load levelling, one logical consumer. The default for decoupling a producer from a slow consumer.
- **SNS** — simple fan-out, push, immediate.
- **EventBridge** — event routing by content with many unknown consumers, plus AWS service and SaaS integration. The default for event-driven architecture on AWS.
- **Kinesis** — ordered, replayable streaming, AWS-native, simpler than Kafka, less capable, and shard management is its own discipline.
- **Kafka** — high-volume, retention, replay, a rich ecosystem, and it becomes the backbone rather than a component. Highest capability and highest cost.

**The composite is usually right** (A13.4): EventBridge routing into SQS queues gives content-based routing plus per-consumer buffering and DLQs. Saying that, rather than picking one, is the better answer.

**M12.2 — When Kafka is overkill**

The cases, and being willing to say this is a strong signal:

- **Moderate throughput with no replay requirement.** If you need a queue and SQS would do, SQS will do — with no cluster, no partition planning, no consumer group semantics, and no upgrade treadmill.
- **A small number of services and integrations.** Kafka's value is as a shared backbone across many teams; with three services it's a substantial dependency serving a problem an HTTP call or a queue solves.
- **No team to operate it.** Even MSK leaves you owning partition design, client tuning, consumer group behaviour, Schema Registry, Connect, and the incidents in M10 (M12.3).
- **Simple pub/sub** — SNS or EventBridge do this with zero operations.
- **The requirement is really task distribution** with priorities, delays, or complex routing — RabbitMQ or SQS fit better (M3.8).
- **The data isn't a stream.** Kafka models an ordered log of facts. Request/reply, RPC, or occasional notifications are not that shape.

The framing: **Kafka is a distributed systems platform, not a message queue.** Its concepts — partitions, offsets, consumer groups, rebalancing, ISR — are all things every engineer touching it must understand, and that learning cost is paid across the whole organisation. **Adopt it when you need retention, replay, high throughput, or a genuine shared event backbone**, and be honest that "we might want streaming later" doesn't justify it today.

**M12.3 — The real operational cost of running Kafka yourself**

Beyond infrastructure:

- **Capacity planning that's genuinely hard** — partitions, brokers, retention, and the RF multiplier (M9.1), with mistakes that are expensive to correct (M4.11).
- **Upgrades** — rolling broker upgrades (M9.3), client compatibility, and the ZooKeeper-to-KRaft migration if you're not already there (M4.7).
- **The ecosystem is separate work**: Schema Registry, Connect workers, MirrorMaker, and the monitoring stack — each a deployment with its own scaling and failure modes (M7.1, M7.2).
- **Rebalancing and reassignment** as routine operations that can take the cluster down if done carelessly (M9.2).
- **Storage management** — disk-full is a real outage class and needs continuous attention (M9.5).
- **Client expertise across every consuming team.** This is the underestimated one: producer acks, consumer offset semantics, rebalancing, poison messages, and lag are things *every* team must understand, and the platform team ends up teaching and supporting them.
- **On-call for an unfamiliar failure surface** — under-replicated partitions, ISR churn, rebalance storms, controller issues.
- **Security** — TLS certificate lifecycle, ACL management, auth integration (M11).
- **Multi-tenancy governance** — naming, quotas, ownership, schema review (M9.10, M12.5).

The honest number: **a production Kafka platform is one to three dedicated engineers**, and self-managing rather than using MSK adds meaningfully to that. Being willing to state a number is what makes the answer credible.

The counterweight to state fairly: **the cost is largely fixed and amortises** across topics and teams. It's a poor investment for three topics and a reasonable one for a genuine organisation-wide backbone — which is the same shape of argument as K13.5.

**M12.4 — The event bus becoming an undocumented integration layer**

The failure mode, and it's worth describing as a progression because that's how it happens:

1. A team publishes events for their own consumers.
2. Another team discovers the topic and starts consuming it — **without telling anyone**, because nothing requires them to.
3. The producing team changes the schema, or the semantics, or the volume, and **breaks a consumer they didn't know existed.**
4. Having been burned, they stop changing anything. **The event schema becomes frozen**, because nobody knows what depends on it.
5. Meanwhile the bus accumulates topics with no owner, no schema, unclear semantics, and events that are actually commands (M1.4).
6. **The system's integration architecture is now the set of topics, and it exists nowhere in documentation** — you have to read every service to know what talks to what (M1.5's choreography risk, realised).

Why it's insidious: **the property that makes event-driven architecture valuable — producers not needing to know their consumers — is exactly the property that produces this.** It's not a misuse; it's the default outcome without governance.

The controls (M12.5, M12.7): **a schema registry with compatibility enforcement**, so changes are checked rather than discovered (M7.2, M7.3); **a topic catalogue with owners and consumers recorded**, so "who depends on this" is answerable; **naming conventions** that make ownership visible (M9.10); **treating a published event as a public API** with versioning and deprecation; and **discoverability** so that finding an event is easy and registering as a consumer is the natural path.

The framing: **an event bus without governance converts explicit coupling into implicit coupling.** You haven't removed the dependencies, you've made them invisible — which is worse, because you can no longer reason about the blast radius of a change.

**M12.5 — Event ownership and schema governance**

The model:

- **Every topic has an owning team**, recorded and discoverable (M9.10). Ownership means responsibility for the schema, the semantics, the retention, the PII classification, and responding when it misbehaves.
- **A published event is a public API.** It gets a version, a documented schema (M7.2), a compatibility policy (M7.3), and a deprecation process with notice — the same discipline as a REST API or a shared library (TF4.9).
- **Schema changes go through review** and are enforced by the registry, so incompatible changes fail at CI rather than in production.
- **A catalogue** — topics, schemas, owners, consumers, classification, retention. **The consumer list is the part that's hardest to maintain and most valuable**, because it's what makes a breaking change plannable and an erasure request executable (M11.5).
- **Consumers register.** Whether by convention, by a pull request to the catalogue, or by deriving it from ACLs (M11.3) — which is the neat trick, since ACLs already record who can read what and can be the source of truth for the consumer list.
- **Event design standards** — events are facts not commands (M1.4), carry identifiers rather than bulk data (M3.10), include an event time (M8.1), and have mandatory headers for tracing and provenance (M10.6, M11.7).

The organisational point: **governance must be lighter than the alternative.** If registering a schema is a two-week process, teams publish to an ungoverned topic, and you get M12.4 anyway. The registry check in CI plus a catalogue that updates from the registry is the low-friction version, and low friction is what makes it stick (TF13.5).

**M12.6 — Migrating between broker technologies**

The general shape, using SQS-to-Kafka or Kafka-cluster-to-cluster as the example:

1. **Inventory** — every topic/queue, its producers, its consumers, its semantics, its volume, its retention. **This is the hard part**, and if you can't produce it, that's M12.4 and the migration starts there.
2. **Stand up the target** and validate it independently — capacity, security, monitoring.
3. **Dual-write.** Producers write to both old and new for a period. This is the safest bridge and it requires producer changes, so it's the step that needs coordination.
4. **Migrate consumers one at a time**, from the old to the new, verifying each. Consumers are usually independent, so this can be gradual.
5. **Verify equivalence** — reconcile counts and content between old and new during the dual-write period. **This is what catches ordering, partitioning, and serialisation differences** before they matter.
6. **Stop writing to the old**, once every consumer has moved and been stable.
7. **Drain and decommission** the old, after its retention period, keeping it available for rollback until then.

The alternatives to dual-write: **a bridge/replication process** (MirrorMaker for Kafka-to-Kafka, M7.8; a Connect connector or a small relay for cross-technology) that copies from old to new, so producers don't change — lower coordination cost, and it adds a component and a lag.

The hazards: **semantics differ between technologies** — SQS's per-message visibility and delete has no Kafka equivalent, and Kafka's ordering and replay have no SQS equivalent, so consumer code changes rather than just configuration. **Offsets and positions don't translate** (M7.8). **Ordering guarantees may differ**, which can be a correctness change rather than a migration detail. And **the cutover must be reversible** until you're confident.

**M12.7 — The platform team's contract with producing and consuming teams**

**The platform team provides:**

- A **running, monitored, upgraded cluster** with a stated SLO, capacity headroom, and DR posture.
- **Self-service topic provisioning** through a reviewed, automated path (M9.9) — not a ticket queue.
- **Schema Registry** with compatibility enforcement and a discoverable catalogue (M12.5).
- **Client libraries or templates** with sensible defaults baked in — `acks=all`, idempotence, sane timeouts, tracing headers, DLQ handling. **This is the highest-leverage thing a platform team can ship**, because it makes correct behaviour the default rather than something every team rediscovers.
- **Quotas and isolation** so one tenant can't degrade another (M9.6).
- **Observability** — lag dashboards, cluster health, and alerting infrastructure teams can plug into (M10.1).
- **Documentation and support**, including the client-side concepts teams must understand.

**Producing and consuming teams provide:**

- **Owned topics with documented schemas, semantics, and retention** (M12.5).
- **Idempotent consumers** (M2.3) — non-negotiable, because at-least-once is the platform's guarantee.
- **Poison-message handling** with a DLQ or error topic, and an owner who works it (M2.9, M6.11).
- **Lag monitoring and alerting for their own consumers**, at thresholds reflecting their business impact (M10.2).
- **Compliance with the naming convention and governance process.**
- **Being on call for their own consumers**, not expecting the platform team to debug their processing logic (K13.4).

The boundary that must be explicit: **the platform team owns the cluster; application teams own their producers, consumers, and topics.** Consumer lag is the application team's problem; under-replicated partitions are the platform's. Ambiguity here is what produces the failure mode where the platform team is paged for every application's processing errors and gradually becomes a bottleneck for everything.

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 113 items, reading straight through produces recognition rather than recall.
- **M2 (delivery semantics) is the highest-value section per item**, and it's the most transferable — at-least-once, idempotency, the dual-write problem, and the outbox pattern come up regardless of which broker the interviewer uses.
- **M6 and M10 are where Kafka experience is unmistakable.** Consumer lag diagnosis by per-partition shape (M6.7), the `max.poll.interval.ms` eviction loop (M6.8/M10.4), and the "queue backing up in an incident" judgement (M10.10) are the questions that separate having run it from having read about it.
- **M12 rewards the case against.** "When is Kafka overkill" and "what does it actually cost to run" are questions where a considered no, with a number attached, is the senior answer.
- **The failure modes are the part that reads as experience.** The visibility timeout producing concurrent duplicate processing (M3.1), one poison message blocking an entire Kafka partition (M2.7), a single SQS FIFO message group serialising the whole queue (M3.6), `acks=all` being meaningless without `min.insync.replicas` (M4.5), and an inactive Debezium replication slot filling the database disk (M7.7).
- **Cross-references into AWS are dense in M3 and M12** — A13.1 for SQS visibility timeouts and DLQs, A13.4 for the service selection framework, A13.5 for idempotency, A12.4 for cross-AZ transfer costs behind M9.7. Interviewers move between the two constantly.
