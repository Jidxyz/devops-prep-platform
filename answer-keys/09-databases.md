# Databases — Answer Key

Companion to Domain 9 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **AWS-managed service configuration is A7** (RDS multi-AZ, read replicas, Aurora, DynamoDB capacity modes, ElastiCache). This domain is the engine-level and operational knowledge underneath — what a platform engineer needs to run, scale, and recover a database. Examples lean Postgres, because it's the most common engine in this space and because its operational specifics (vacuum, MVCC, wraparound) are the ones most frequently asked about.

Three notes on how this domain is interviewed for a platform role:

- **You are not being assessed as a DBA.** The questions that matter are the operational ones: DB5 (replication and failover), DB6 (backup and recovery), DB7 (migrations without downtime), DB8 (connection exhaustion), and DB12 (operations). Those are the ones that cause incidents a platform engineer owns.
- **DB2 and DB3 still matter**, because "the database is slow" lands on the platform team, and being able to read an execution plan and identify a missing index is the difference between diagnosing it and escalating it.
- **DB14 and DB13.10 are the judgement items.** Databases on Kubernetes, managed versus self-hosted, and production data in staging are questions where a considered position with the costs named is what's being assessed.

---

## DB1. Fundamentals

**DB1.1 — Relational, document, key-value, wide-column, graph**

- **Relational** (Postgres, MySQL) — rows and columns with a fixed schema, joins, and ACID transactions. **Fits**: anything with meaningful relationships between entities, transactional integrity requirements, and ad hoc query needs. **The right default** for most applications, and the burden of proof should be on choosing something else.
- **Document** (MongoDB, DocumentDB) — self-contained JSON-like documents, flexible schema. **Fits**: data naturally read and written as a whole aggregate, genuinely variable structure, rapid iteration. **Doesn't fit**: heavily relational data, where you end up doing joins in application code.
- **Key-value** (Redis, DynamoDB in its simplest form, Memcached) — get and put by key. **Fits**: caching, sessions, feature flags, anything where the access pattern is exactly "fetch this by its identifier". Extremely fast and extremely limited.
- **Wide-column** (Cassandra, DynamoDB, HBase, Bigtable) — a partition key plus a sort key, with rows holding many columns. **Fits**: very high write throughput, time-series and event data, known access patterns at massive scale. **Doesn't fit**: anything requiring ad hoc queries or joins.
- **Graph** (Neo4j, Neptune) — nodes and edges with traversal as the primary operation. **Fits**: relationship traversal of arbitrary depth — fraud rings, social graphs, recommendations, dependency analysis. **The distinguishing test**: if your queries are "find everything connected to X within N hops", a graph database does in milliseconds what SQL does with recursive CTEs and pain.

The framing that makes this a senior answer: **start relational and justify moving away from it.** The reasons that genuinely justify it are scale beyond what a single primary can write, an access pattern that's purely key-based at high volume, or a genuine graph traversal requirement. "It's more modern" and "it scales better" are not reasons (DB10.8), and polyglot persistence has a real operational cost — each engine is another thing to back up, monitor, patch, and be on call for (DB14.1).

**DB1.2 — Normalisation and when to denormalise**

**Normalisation** removes redundancy so each fact is stored once. Third normal form, informally: every non-key column depends on the key, the whole key, and nothing but the key.

**What it buys**: no update anomalies (change an address in one place, not in a thousand rows), smaller storage, and enforced consistency through foreign keys (DB1.3).

**When denormalising is right:**

- **Read performance where the join is the bottleneck** — measured, not assumed. A join across five tables executed on every page load may justify a denormalised read model.
- **Historical accuracy**, and this is the case people miss: **an order line should store the price at the time of the order**, not join to the current product price. That's not denormalisation for performance — it's correctness, because the fact you're recording is what the customer paid.
- **Aggregates that are expensive to compute** — a maintained counter rather than `COUNT(*)` over millions of rows.
- **Cross-service boundaries** — a service holding a copy of data it doesn't own, kept current by events (M1.4), because a synchronous join across a service boundary isn't available.
- **Analytical models** (DB1.4) — star schemas are deliberately denormalised.

The cost to state: **denormalised data can become inconsistent**, and now something must keep it in sync — a trigger, application code, or an event pipeline, each of which can fail. **You've traded a guaranteed-correct join for a maintained copy that can drift.**

The discipline: **normalise first, denormalise with evidence.** A denormalisation introduced before measurement is a consistency risk taken for a performance benefit you haven't demonstrated.

**DB1.3 — Primary keys, foreign keys, referential integrity**

- **Primary key** — uniquely identifies a row; not null, unique, and typically the clustering key determining physical order (in MySQL/InnoDB) or backed by a unique index (Postgres).
- **Foreign key** — a column referencing another table's primary key.
- **Referential integrity** — the database refuses operations that would leave a foreign key pointing at nothing.

The design decisions worth having a view on:

- **Natural vs surrogate keys.** A surrogate (an auto-generated ID) is usually right, because natural keys change — email addresses, national identifiers, and product codes all get updated, and a changing primary key cascades everywhere.
- **Sequential vs random IDs.** Sequential integers or ULIDs give good index locality; **random UUIDv4 primary keys cause index fragmentation and poor cache locality** because inserts scatter across the B-tree. **UUIDv7 (time-ordered) fixes this** and is the right choice where you need globally unique IDs generated outside the database — a good, current detail to know.
- **`ON DELETE CASCADE` is convenient and dangerous** — deleting one row can silently delete millions, and it can hold locks for a long time. `RESTRICT` is safer as a default.

The debate to be able to argue: **should foreign keys be enforced in the database?** For: it's the only guarantee that survives application bugs, bad migrations, and manual fixes, and application-level enforcement is racy. Against: they cost write performance, they complicate sharding (DB9.6) and bulk loads, and they can cause lock contention on the referenced table. **The position to hold: enforce them unless you have a specific, measured reason not to** — orphaned data is expensive to discover and painful to clean up, and "our application ensures it" reliably turns out to be untrue.

**DB1.4 — OLTP vs OLAP**

- **OLTP** — many small, short transactions touching few rows. Reads and writes by key or narrow predicate. Optimised for **concurrency and low latency per operation**. Row-oriented storage, heavy indexing, normalised.
- **OLAP** — few large queries scanning many rows, aggregating. Optimised for **throughput over large scans**. Column-oriented storage, compression, denormalised star schemas, often no indexes at all in the OLTP sense.

**Why one database rarely serves both well**, and the reasons are structural rather than a matter of tuning:

- **Storage layout is fundamentally opposed.** Row storage fetches a whole row efficiently (OLTP); column storage reads one column across millions of rows without touching the others, and compresses it well (OLAP). **You cannot be optimal at both with one physical layout.**
- **Indexing works against you.** OLTP wants many indexes for point lookups; each index costs write throughput (DB3.1). OLAP scans don't benefit from them.
- **Resource contention is the operational reality**: an analytical query scanning a hundred million rows **evicts the OLTP working set from the buffer cache** and saturates I/O, so transactional latency degrades badly while it runs. This is the concrete, everyday reason analysts get their own replica.
- **Long-running analytical queries hold snapshots**, which in Postgres blocks vacuum and causes bloat (DB12.3, DB4.9).

The practical resolutions, in increasing order of separation: **a dedicated read replica** for analytics (A7.2) — cheap and solves the contention, though it's still row storage; **an analytical database** (Redshift, BigQuery, Snowflake, ClickHouse) fed by ETL or CDC (M7.7); or **HTAP-ish options** (Aurora with column-store extensions, Postgres with `pg_analytics`) which narrow the gap without closing it.

**DB1.5 — CAP accurately, including what it doesn't say**

**The accurate statement**: in the presence of a **network partition**, a distributed system must choose between **consistency** (every read sees the latest write, or an error) and **availability** (every request gets a non-error response, possibly stale).

**What it doesn't say**, which is most of the item:

- **It is not "pick two of three."** Partition tolerance is not a choice — networks partition, so a distributed system must handle it. The real choice is what to do *during* a partition, so it's CP or AP, not CA.
- **It says nothing about normal operation.** With no partition, you can have both strong consistency and high availability. Most systems spend almost all their time in that state, so CAP describes a rare mode, not everyday behaviour.
- **"Consistency" in CAP is linearisability**, which is a much stronger and narrower property than ACID's C (DB1.6). The two Cs are unrelated, and conflating them is a very common error.
- **It's binary and the real world isn't** — real systems offer a spectrum of consistency models, and the choice is often per-operation rather than system-wide (O15.12).
- **It ignores latency**, which is the tradeoff you actually make daily. **PACELC** is the extension worth naming: during a **P**artition, choose **A** or **C**; **E**lse (normally), choose **L**atency or **C**onsistency. That second clause describes far more real decisions than CAP does — a synchronous cross-region write is slow because it's consistent.

The framing: **CAP is a useful impossibility result and a poor design tool.** The useful version is "what should this specific operation do when it can't reach a quorum" (DB5.5, O15.12).

**DB1.6 — ACID and what each property guarantees**

- **Atomicity** — a transaction happens entirely or not at all. Implemented via the WAL and rollback (DB1.9). **Guarantees**: no partial application of a multi-statement transaction. **Doesn't guarantee**: anything about other transactions seeing intermediate state — that's isolation.
- **Consistency** — the transaction moves the database from one valid state to another, where "valid" means satisfying declared constraints (primary keys, foreign keys, checks, triggers). **This is the weakest and most misunderstood property**: it doesn't mean "consistent" in the distributed-systems sense (DB1.5), and it doesn't mean your business logic is correct. It means the database enforces the constraints you declared.
- **Isolation** — concurrent transactions don't interfere. **This is the one that's routinely partial**: full isolation is serialisability, and almost every engine defaults to something weaker (DB4.1, DB4.3), so **the guarantee you actually have depends on your isolation level** and is usually weaker than people assume.
- **Durability** — once committed, it survives a crash. Implemented by flushing the WAL to durable storage before acknowledging the commit (DB1.9, O11.6). **Doesn't guarantee**: survival of disk loss (that's replication and backup) or that a replica has it (DB5.1).

The points that show understanding: **ACID is per-transaction on a single node.** It says nothing about a distributed system — a transaction can be perfectly ACID on the primary and lost on failover if replication was asynchronous (DB5.9). And **durability is only as strong as your `fsync` behaviour and your storage's honesty about write caches** (O11.6), which is where "we lost committed transactions" incidents come from.

**DB1.7 — Eventual consistency and the application consequences**

**Eventual consistency**: in the absence of new writes, all replicas will converge on the same value. It says nothing about **when**.

**The application consequences**, which is what the item asks for:

- **Read-after-write failure** — a user updates their profile, the read goes to a lagging replica, and they see the old value. **The most common and most user-visible consequence** (DB5.3).
- **Monotonic read violation** — two consecutive reads hit different replicas and the second returns *older* data than the first. The value appears to go backwards, which is deeply confusing to users.
- **Lost updates on read-modify-write** — read a stale value, compute, write back, overwriting someone else's change. Requires optimistic concurrency to prevent (DB4.8).
- **Cross-entity inconsistency** — an order exists and its line items don't yet, so a page renders half a thing.
- **Non-deterministic behaviour** in application logic that reads then branches.

The mitigations, and being able to name them is the substance: **read your own writes** — route a user's reads to the primary for a period after they write, or use a session token that pins them; **monotonic reads** — pin a session to one replica; **version numbers or timestamps** so the application can detect staleness; **compensating UI** — optimistic local updates so the user sees their change regardless; and **bounded staleness** — measure and alert on lag so you know the size of the window (DB5.2).

The design point to make: **eventual consistency is a property you must design the application around, not a database setting you tolerate.** Teams that adopt read replicas for scale without addressing this ship a class of intermittent bug that's very hard to reproduce.

**DB1.8 — How a query gets from client to disk and back**

The path, and it's worth knowing because each stage is a distinct failure and latency source:

1. **Connection** — the client uses a pooled connection or establishes one (TCP, TLS, authentication — expensive, DB8.1).
2. **Parse** — SQL text to a parse tree; syntax errors surface here.
3. **Rewrite** — views expanded, rules applied.
4. **Plan/optimise** — the planner enumerates access paths and join orders and picks the cheapest by **estimated cost, using table statistics** (DB2.6). Prepared statements may skip this via a cached plan.
5. **Execute** — the executor walks the plan. For each access:
   - **Check the buffer pool / shared buffers.** A hit is a memory read; a miss requires disk.
   - **On a miss, read from disk** — possibly from the OS page cache (O10.2), possibly from the device (O11.1).
   - **Locks and MVCC snapshots** are acquired as needed (DB4.4).
6. **Writes** additionally: modify pages in memory (marking them dirty), **write the change to the WAL and flush it** (DB1.9), and acknowledge the commit. **Dirty data pages are written later by a background process** — the commit does not wait for them.
7. **Return** — rows are serialised and sent back, potentially in batches.

The operational insights that follow: **the buffer cache hit ratio is the single most important performance metric** (DB12.1), because a miss is orders of magnitude slower; **commit latency is bounded by WAL fsync latency**, which is why storage latency matters more than throughput for OLTP (O11.1); and **plan choice happens before execution**, so a bad plan from stale statistics costs you regardless of how fast the storage is (DB2.6).

**DB1.9 — The write-ahead log**

**The rule: the log record describing a change is written and flushed to durable storage *before* the change is applied to the data pages.**

What it enables:

- **Durability** (DB1.6) — a commit is acknowledged once the WAL is flushed. The data pages are still dirty in memory, and that's fine, because the log is sufficient to reconstruct them.
- **Crash recovery** — on restart, the engine replays WAL records from the last checkpoint, redoing committed transactions and rolling back uncommitted ones.
- **Performance** — WAL writes are **sequential** (fast, O11.4), whereas data page writes are **random**. Batching random writes for later while making the durability guarantee with a sequential write is the entire performance trick.
- **Replication** — physical replication ships WAL records to replicas (DB5.8).
- **Point-in-time recovery** — archived WAL plus a base backup lets you replay to any moment (DB6.3).

The operational consequences that matter:

- **WAL disk must not fill.** If it does, the database stops accepting writes. Causes: an inactive replication slot (M7.7 — a stopped Debezium connector is a genuine database availability risk), archiving failing, or a very long transaction.
- **Checkpoints flush dirty pages** and can cause I/O spikes; tuning checkpoint frequency trades recovery time against steady-state I/O smoothness.
- **`synchronous_commit`** can be relaxed to acknowledge before the WAL flush — faster, with a small window of committed-but-lost transactions on crash. A legitimate tradeoff for some workloads and a data-loss decision to make deliberately.
- Naming varies: WAL in Postgres, **redo log** in MySQL/InnoDB and Oracle.

**DB1.10 — B-tree vs LSM-tree**

- **B-tree** (Postgres, MySQL/InnoDB, most relational engines) — a balanced tree updated **in place**. A write locates the page and modifies it. **Reads are predictable**: a small number of page accesses to reach any key.
- **LSM-tree** (Cassandra, RocksDB, ScyllaDB, Bigtable, and used internally by many systems) — writes go to an in-memory table, which is periodically flushed to an immutable sorted file (SSTable) on disk. **Background compaction** merges files.

**The tradeoff:**

| | B-tree | LSM-tree |
|---|---|---|
| Write path | Random I/O, in-place update | **Sequential append** — much faster writes |
| Read path | Predictable, few accesses | **May check several SSTables** — bloom filters mitigate |
| Write amplification | Lower per write, but random | Higher (compaction rewrites data repeatedly) |
| Space amplification | Fragmentation and bloat (DB12.5) | Obsolete versions until compacted |
| Predictability | Consistent | **Compaction causes periodic I/O spikes and latency variance** |

The summary to give: **LSM optimises for write throughput; B-tree optimises for read predictability.** LSM's sequential writes suit write-heavy workloads and cheaper storage; its cost is read amplification and — the operationally significant part — **compaction, which consumes I/O and CPU in the background and causes latency spikes that look like nothing else in your metrics.**

Why it matters for a platform engineer: **it explains the operational character of the datastore you're running.** Cassandra clusters spending significant resources on compaction and needing headroom for it, versus Postgres needing vacuum for its own version cleanup (DB12.3) — both are the maintenance cost of their respective storage models.

---

## DB2. SQL & query performance

**DB2.1 — Joins, aggregations, subqueries, CTEs**

```sql
WITH recent_orders AS (
    SELECT customer_id, COUNT(*) AS order_count, SUM(total_minor) AS total_spend
    FROM orders
    WHERE created_at >= NOW() - INTERVAL '90 days'
      AND status = 'completed'
    GROUP BY customer_id
)
SELECT c.id, c.name, c.tier,
       COALESCE(r.order_count, 0) AS order_count,
       COALESCE(r.total_spend, 0) AS total_spend
FROM customers c
LEFT JOIN recent_orders r ON r.customer_id = c.id
WHERE c.status = 'active'
ORDER BY total_spend DESC
LIMIT 50;
```

The fluency markers:

- **`LEFT JOIN` plus `COALESCE`** to include customers with no orders — the correct handling of the "zero rows" case, which an inner join silently drops.
- **Filtering in the CTE** rather than after the join, so less data is joined.
- **`GROUP BY` with aggregates**, and understanding that every non-aggregated selected column must be grouped.
- **`HAVING` filters after aggregation; `WHERE` filters before** — a distinction people muddle, and using `WHERE` where possible is faster because it reduces what's aggregated.
- **CTEs for readability**, with the caveat below.

**The CTE materialisation point is worth knowing**: in Postgres **before version 12, CTEs were an optimisation fence** — always materialised, preventing predicate pushdown, which made them a performance trap. **From 12 onwards they're inlined by default** unless marked `MATERIALIZED`. Knowing that changed, and that `NOT MATERIALIZED`/`MATERIALIZED` gives explicit control, is a good currency signal.

**DB2.2 — Join types and predicting row counts**

- **INNER** — rows matching in both. Row count depends on cardinality of the match.
- **LEFT (OUTER)** — all left rows, with NULLs where no right match. **At least as many rows as the left table.**
- **RIGHT** — the mirror; usually rewritten as a LEFT for readability.
- **FULL OUTER** — all rows from both, NULLs where unmatched.
- **CROSS** — Cartesian product. `n × m` rows.

**Predicting row counts** is the substance, because it's how you spot a bug before running it:

- **One-to-one join** → row count unchanged.
- **One-to-many** → the result has as many rows as the "many" side. **Joining `customers` to `orders` gives one row per order, not per customer** — which is why `SUM(customer.credit_limit)` after such a join over-counts, multiplying by the order count. **This is the classic aggregation bug** and it's worth being able to name.
- **Many-to-many** → the product of matching rows on each side. A join between two tables with three matching rows each produces nine.
- **A missing or wrong join condition** → an accidental cross join, which is how a query that should return 1,000 rows returns 40 million and takes the database down.

The practical checks: **run a `COUNT(*)` before and after adding a join** to see whether it multiplied; use `EXISTS` rather than a join when you only need to test for presence (no row multiplication); and **aggregate before joining** (in a CTE or subquery) when you need a sum from a one-to-many relationship — which is what DB2.1's example does.

**DB2.3 — Window functions for a real problem**

The problem: *for each customer, find their most recent order and its rank by value.*

```sql
SELECT customer_id, order_id, total_minor, created_at
FROM (
    SELECT customer_id, order_id, total_minor, created_at,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS recency_rank,
           RANK()       OVER (PARTITION BY customer_id ORDER BY total_minor DESC) AS value_rank,
           SUM(total_minor) OVER (PARTITION BY customer_id) AS customer_lifetime_value,
           LAG(created_at)  OVER (PARTITION BY customer_id ORDER BY created_at) AS previous_order_at
    FROM orders
    WHERE status = 'completed'
) ranked
WHERE recency_rank = 1;
```

The value: **window functions compute per-row values over a related set without collapsing rows**, which is the distinction from `GROUP BY`. The "top N per group" problem is the canonical use and is genuinely awkward without them — the alternative is a correlated subquery or a self-join, both slower and harder to read.

The functions worth knowing: `ROW_NUMBER` (always unique), `RANK` (gaps after ties), `DENSE_RANK` (no gaps), `LAG`/`LEAD` (previous/next row — the natural way to compute deltas between consecutive events), `SUM`/`AVG` with a frame for running totals and moving averages, `FIRST_VALUE`/`LAST_VALUE`, and `NTILE` for bucketing.

The performance points: **window functions require a sort** per partition, which can be expensive — an index matching the `PARTITION BY ... ORDER BY` can supply it. And **you cannot filter on a window function in `WHERE`** (it's computed after), hence the subquery or CTE wrapper — a syntax constraint that trips people.

**DB2.4 — Reading an execution plan**

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT ...;
```

**`ANALYZE` actually runs the query** and gives real timings and row counts — which is what you need. `EXPLAIN` alone gives only estimates. **`BUFFERS`** shows shared buffer hits versus disk reads, which is how you see whether it's I/O-bound (DB1.8).

Reading it:

```
Nested Loop  (cost=0.43..8734.21 rows=12 width=48) (actual time=0.052..2841.203 rows=48213 loops=1)
  ->  Seq Scan on orders  (cost=0.00..4521.00 rows=12 width=24)
        (actual time=0.019..312.442 rows=48213 loops=1)
        Filter: (status = 'pending')
        Rows Removed by Filter: 1951787
  ->  Index Scan using customers_pkey on customers  (...) (actual time=0.048..0.049 rows=1 loops=48213)
```

What to look at, in order:

1. **Read from the innermost/most-indented node outward** — that's execution order.
2. **Compare estimated `rows` against `actual` rows.** In the example: **estimated 12, actual 48,213.** That's a 4,000× misestimate, and it's the root cause — the planner chose a nested loop believing it would run 12 times, and it ran 48,213 times. **Estimate-versus-actual divergence is the single most informative thing in a plan**, and it points at stale or missing statistics (DB2.6).
3. **Find the node with the largest `actual time`**, remembering that **a node's time includes its children**, and that **`loops` multiplies** — a node showing 0.05ms with 48,213 loops is 2.4 seconds.
4. **`Rows Removed by Filter`** — nearly two million rows read and discarded means the filter should have been an index (DB2.5).
5. **Look for expensive node types**: `Seq Scan` on a large table, `Sort` spilling to disk (`Sort Method: external merge Disk: 82MB`), `Hash Join` with batches (meaning the hash didn't fit in `work_mem`), and `Nested Loop` with high loop counts.

**DB2.5 — A sequential scan that should be an index scan**

**The signature**: `Seq Scan` on a large table with a selective filter, and a high `Rows Removed by Filter` count. The database read every row and threw most away.

**But a sequential scan is not automatically wrong** — and this is the part that distinguishes a good answer:

- **If the query returns a large fraction of the table** (roughly more than 5–20% depending on the engine and correlation), **a sequential scan is genuinely faster** than an index scan, because an index scan does random I/O for each row plus the index traversal, while a sequential scan reads pages in order (O11.4). The planner choosing a seq scan for a non-selective query is correct.
- **On a small table**, a seq scan is faster than any index, and the planner knows it.

**So the question is whether the filter is selective and there's no usable index.** If the filter matches 0.1% of rows and it's still scanning, that's the bug.

The diagnosis and fix: check whether an index exists on the filtered column; if it does and isn't being used, that's DB3.5. If it doesn't, create it — with the composite-index design considerations in DB3.2, and concurrently on a live system (DB3.7).

The related case worth naming: **a sequential scan that appears after data growth.** The query was fine at 10,000 rows and the planner's choice was reasonable; at 10 million it isn't, and nothing changed except the data. That's why a query fast in staging is slow in production (DB2.9).

**DB2.6 — The planner, statistics, and staleness**

The planner chooses among possible execution plans by **estimating the cost of each**, using **statistics** about the data: row counts, the distribution of values per column (histograms), the number of distinct values, the most common values and their frequencies, and physical correlation between column order and disk order.

**When statistics are stale**, the estimates are wrong and the plan choice is wrong — which is the mechanism behind most sudden, unexplained query slowdowns:

- **A table that grew substantially since the last analyse** — the planner thinks it's small and chooses a nested loop that runs millions of times (DB2.4).
- **A newly loaded table with no statistics at all** — the planner uses defaults that are usually badly wrong.
- **Skewed data** where the histogram is too coarse — a column with one dominant value estimated as uniform.
- **After a bulk load or a major migration**, which is why **running `ANALYZE` after a bulk operation or a version upgrade is standard practice** (A7.5) and why forgetting it produces the "the upgrade made everything slow" report.

The management: **autovacuum runs `ANALYZE` automatically** in Postgres, triggered by a fraction of rows changed — so a very large table may not be analysed often enough, and `autovacuum_analyze_scale_factor` can be lowered per table. **Run `ANALYZE` explicitly** after bulk changes. **Increase `default_statistics_target`** (or per-column via `ALTER TABLE ... ALTER COLUMN ... SET STATISTICS`) for columns with skewed distributions. And **extended statistics** (`CREATE STATISTICS`) capture **correlation between columns**, which fixes the classic underestimate when two correlated columns are both filtered — the planner multiplies their selectivities as if independent, and gets a number orders of magnitude too small.

**DB2.7 — Identifying and fixing N+1**

**The pattern**: one query fetches N rows, then the code loops and issues one query per row.

```python
orders = db.query("SELECT * FROM orders WHERE status = 'pending'")   # 1 query
for order in orders:
    customer = db.query("SELECT * FROM customers WHERE id = ?", order.customer_id)  # N queries
```

500 pending orders means 501 round trips. **Each individual query is fast** — a few hundred microseconds — which is exactly why it's hard to spot: the slow query log shows nothing, and the database looks idle (DB2.8).

**Identifying it:**

- **In a trace**, it's unmistakable: dozens or hundreds of near-identical short spans in sequence (O5.5). **Tracing is the best detector for this** and is the reason to instrument database calls.
- **In `pg_stat_statements`**, a query with a very high `calls` count and low mean time but high `total_exec_time` (DB2.8).
- **In the application**, an ORM lazily loading a relation inside a loop.
- **The symptom**: latency proportional to result set size, and worse in production where result sets are bigger (DB2.9).

**Fixing it:**

- **A join** — fetch everything in one query.
- **A batch fetch** — `WHERE id = ANY($1)` with the collected IDs, then map in application code. Often better than a join because it avoids row multiplication (DB2.2).
- **ORM eager loading** — `select_related`/`prefetch_related` in Django, `JOIN FETCH` in JPA, `includes` in ActiveRecord. **This is usually the actual fix**, since the ORM caused it.
- **DataLoader-style batching** for GraphQL, where N+1 is endemic because the resolver structure invites it.

**DB2.8 — Finding the slowest queries on a live system**

```sql
-- Postgres: requires pg_stat_statements
SELECT substring(query, 1, 80) AS query,
       calls,
       round(total_exec_time::numeric, 1) AS total_ms,
       round(mean_exec_time::numeric, 2)  AS mean_ms,
       round(stddev_exec_time::numeric,2) AS stddev_ms,
       rows,
       round(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 1) AS hit_pct
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- currently running, longest first
SELECT pid, now() - query_start AS duration, state, wait_event_type, wait_event,
       substring(query, 1, 100)
FROM pg_stat_activity
WHERE state <> 'idle' AND now() - query_start > interval '5 seconds'
ORDER BY duration DESC;
```

**The crucial point: order by `total_exec_time`, not `mean_exec_time`.** A query taking 5 seconds and running twice a day (10 seconds total) matters far less than a query taking 20ms and running two million times a day (11 hours total). **Total time is where the load actually is**, and sorting by mean finds the dramatic outlier while missing the real problem — which is usually an N+1 (DB2.7).

The other sources: **the slow query log** (`log_min_duration_statement`) catches individual slow executions with their parameters, which `pg_stat_statements` normalises away; **Performance Insights** on RDS gives wait-event analysis, which tells you what queries were *waiting on* rather than just how long they took — genuinely valuable for distinguishing lock waits from I/O; and **`pg_stat_activity`** for what's happening right now.

The additional signals in the output: **`stddev_exec_time`** high relative to mean means the query is sometimes fast and sometimes slow — usually a cache-hit-versus-miss bimodality (O7.5) or a plan flip. **Low `hit_pct`** means it's reading from disk, so it's I/O-bound.

**DB2.9 — Why a query fast in staging is slow in production**

The causes, roughly in order of frequency:

1. **Data volume.** Staging has 10,000 rows; production has 50 million. **The planner makes a different choice** — a sequential scan that was fine becomes catastrophic (DB2.5), or a nested loop that was cheap now runs millions of times (DB2.4). **This is the dominant cause.**
2. **Data distribution.** Staging data is uniform and synthetic; production is skewed, with one customer having 400,000 orders. The query is fine for the median and terrible for the whale.
3. **Statistics differ** (DB2.6) — staging was recently loaded and analysed; production's may be stale.
4. **Concurrency.** Staging runs the query alone; production runs it alongside a thousand others, competing for buffer cache, I/O, and locks (DB4.7).
5. **Cache state.** In staging the small table is entirely in memory; in production the working set exceeds the buffer pool, so every execution hits disk (DB1.8).
6. **Different hardware and configuration** — `work_mem`, `shared_buffers`, instance size, storage IOPS (O11.1).
7. **Different indexes** — an index created by hand in staging and never migrated, or vice versa.
8. **Connection and pool contention** (DB8.3) — the query itself is fine and waits to start.

The preventions: **test against production-scale data volume and distribution** — a restored, anonymised production snapshot is the gold standard (DB13.9); **`EXPLAIN` against production** (safe, it doesn't execute) to see the real plan; **compare plans between environments**; and **review new queries for their behaviour at scale**, asking "what does this do when the customer has a million rows" as a code-review question.

**DB2.10 — Rewriting a slow query and proving the improvement**

The method mirrors O13.10:

1. **Capture the baseline**: `EXPLAIN (ANALYZE, BUFFERS)` on production-like data, and the query's `total_exec_time` and `calls` from `pg_stat_statements` (DB2.8).
2. **Identify the expensive step** from the plan (DB2.4).
3. **Change one thing** — add an index, rewrite the join, push a predicate down, replace a correlated subquery with a join, avoid `SELECT *` (DB2.11).
4. **Re-measure with the same command on the same data.**
5. **Verify the plan changed as expected** — a faster runtime with the same plan may just be a warm cache.
6. **Check it's still correct** — same rows, same order.
7. **Check nothing else regressed** — a new index costs writes (DB3.1), and a rewrite may be slower for a different parameter value.

A credible report:

> "The order-history query was 38% of total database time in `pg_stat_statements` — 2.1M calls at a mean of 340ms. The plan showed a sequential scan on `orders` filtering on `(customer_id, created_at)` with 1.9M rows removed by filter. Adding a composite index on `(customer_id, created_at DESC)` changed it to an index scan: mean 4ms, and p99 API latency for the account page went from 840ms to 210ms. The index adds 1.2GB and measurably no change to write throughput at our insert rate. Verified over a week of production traffic."

**The elements that make it credible**: a baseline with a measurement source, the mechanism (what the plan showed), the change, the result at the distribution level, the cost of the fix, and a check on the write side. **A percentage with no baseline is not evidence.**

**DB2.11 — The cost of `SELECT *` beyond aesthetics**

The real costs:

- **Network transfer and serialisation.** Fetching 40 columns when you need 3 transfers an order of magnitude more bytes, per row, per query. At scale this is a measurable share of database and application CPU.
- **It defeats covering indexes** (DB3.3). An index containing exactly the columns you query can satisfy it entirely without touching the table — an **index-only scan**. `SELECT *` forces a heap fetch for every row, which is the expensive part. **This is the biggest performance argument** and the one people don't know.
- **TOAST/off-page columns.** In Postgres, large values are stored out of line; selecting them fetches extra pages you didn't need. A table with a large JSON or text column makes `SELECT *` dramatically more expensive than selecting the scalar columns.
- **Memory in the application** — larger result objects, more GC pressure (O10.5).
- **Fragility.** Adding a column changes the result shape, which can break positional access, ORM mappings, and downstream consumers.
- **It hides intent** — a reviewer can't see which columns matter, and you can't tell whether removing a column is safe.

The nuance to acknowledge: **for a single-row lookup by primary key, it's largely irrelevant**, and insisting on explicit columns everywhere for its own sake is pedantry. **The cost is concentrated in queries returning many rows, queries that could be index-only, and tables with large columns** — which is where the rule earns its place.

---

## DB3. Indexing

**DB3.1 — What an index costs**

- **On write**: every `INSERT`, `UPDATE` (of an indexed column), and `DELETE` must update every relevant index. **A table with eight indexes does roughly nine writes per insert.** Write throughput degrades roughly linearly with index count.
- **In storage**: an index can be a significant fraction of the table's size — sometimes larger than the table for wide composite indexes. That's disk, backup size (DB6), and buffer cache displacement.
- **In buffer cache**: index pages compete with data pages for memory. Too many indexes means less of your actual data is cached (DB1.8).
- **In planning time**: more candidate paths for the planner to evaluate, a minor cost that becomes real with dozens of indexes.
- **In maintenance**: vacuum must process indexes; bloat accumulates (DB3.8, DB12.3).
- **In lock behaviour**: index updates take locks, contributing to contention on hot rows (DB4.7).

The judgement: **indexes are not free and the instinct to add one for every query is wrong.** The question for each index is whether the read benefit exceeds the write cost across the actual workload. On a write-heavy table, a rarely-used index is a permanent tax. **Auditing and removing unused indexes** (DB3.6) is a real and under-performed optimisation.

The related design point: **a composite index often replaces several single-column ones** (DB3.2), reducing count while covering more queries.

**DB3.2 — Composite indexes and column order**

An index on `(a, b, c)` is a B-tree sorted by `a`, then `b` within equal `a`, then `c`.

**Why order matters — the leftmost prefix rule:**

The index can be used for queries filtering on:
- `a`
- `a` and `b`
- `a`, `b`, and `c`

It **cannot** efficiently serve a query filtering only on `b`, or only on `c`, or on `b` and `c` — because the values of `b` are scattered throughout the index, ordered only within each `a`. **The analogy: a phone book sorted by (surname, forename) is useless for finding everyone called "James".**

The design rules:

1. **Equality predicates first, then ranges.** An index on `(status, created_at)` serves `WHERE status = 'pending' AND created_at > X` well. Reversed, `(created_at, status)` requires scanning the whole date range and filtering — because **once you use a range predicate, subsequent columns are no longer usefully ordered.**
2. **Highest selectivity first among equality columns**, generally — it narrows fastest. Though modern engines handle this reasonably either way, and matching the actual query pattern matters more.
3. **Include the `ORDER BY` columns** in the right order and direction, so the index supplies the sort and the plan avoids an explicit `Sort` node (DB2.4). `(customer_id, created_at DESC)` serves "this customer's most recent orders" with no sort at all.
4. **Consider what one index can cover** — `(a, b, c)` also serves queries on `a` and on `(a, b)`, so it may replace three indexes (DB3.1).

**DB3.3 — Covering indexes and index-only scans**

An **index-only scan** answers a query entirely from the index, without reading the table at all. That eliminates the random I/O of heap fetches, which is usually the dominant cost of an index scan.

```sql
-- covering index: INCLUDE columns are stored in the leaf, not used for ordering
CREATE INDEX idx_orders_lookup
  ON orders (customer_id, created_at DESC)
  INCLUDE (total_minor, status);

-- now this can be index-only
SELECT created_at, total_minor, status
FROM orders WHERE customer_id = $1
ORDER BY created_at DESC LIMIT 20;
```

`INCLUDE` (Postgres 11+, and MySQL/InnoDB gets it implicitly via the clustered PK) adds payload columns without making them part of the sort key — so they don't affect the index's ordering or its usefulness for other queries, but they're available for index-only scans.

**The Postgres-specific caveat that matters**: an index-only scan **still needs to check row visibility** (MVCC, DB4.4), and it does so via the **visibility map**. If the map isn't current — because **vacuum hasn't run recently** — Postgres must fetch the heap page after all, and the index-only scan degrades to a normal index scan. **So index-only scans depend on vacuum keeping up** (DB12.3), which is a non-obvious coupling and a good detail to know. The plan shows it as `Heap Fetches: N` — a high number means you're not getting the benefit.

The design tension: **covering indexes are wider**, so they cost more storage and more write overhead (DB3.1). Worth it for a hot query path, not worth it as a default.

**DB3.4 — Partial and filtered indexes**

An index built over only a subset of rows:

```sql
CREATE INDEX idx_orders_pending
  ON orders (created_at)
  WHERE status = 'pending';

CREATE UNIQUE INDEX idx_users_email_active
  ON users (lower(email))
  WHERE deleted_at IS NULL;
```

**When they're the right choice:**

- **A small, frequently-queried subset of a large table.** If 0.5% of orders are pending but every dashboard queries them, an index over just those rows is tiny, entirely cacheable, and fast — where a full index on `status` would be large and mostly useless.
- **Skewed distributions** — indexing only the rare values, since the common value is better served by a sequential scan anyway (DB2.5).
- **Excluding soft-deleted rows**, which is very common and keeps the index proportional to live data.
- **Conditional uniqueness** — the second example enforces "email unique among non-deleted users", which a plain unique constraint cannot express.
- **Sparse columns** — indexing only `WHERE col IS NOT NULL`.

The constraint: **the planner uses a partial index only when it can prove the query's predicate implies the index's predicate.** So a query with `WHERE status = 'pending'` uses it; a query with `WHERE status = $1` (a parameter) generally cannot, because the value isn't known at plan time. **That's a real and surprising limitation** — a partial index that works in testing with a literal may not be used by the parameterised application query (DB3.5).

**DB3.5 — Why an index isn't used despite existing**

Work through the causes:

1. **The planner thinks a scan is cheaper** — and may be right (DB2.5). If the query returns a large fraction of rows, a seq scan is genuinely faster.
2. **Stale statistics** (DB2.6) — the planner's row estimate is wrong, so its cost comparison is wrong. **Run `ANALYZE` and re-check; this is the first thing to try.**
3. **Leftmost prefix violation** on a composite index (DB3.2).
4. **A function or expression on the indexed column**: `WHERE lower(email) = $1` cannot use an index on `email`. **Fix: an expression index** — `CREATE INDEX ON users (lower(email))`.
5. **Type mismatch or implicit cast** — comparing a `bigint` column to a string literal, or `varchar` to `text` with a non-matching collation, can prevent index use. A subtle and common one.
6. **A leading wildcard** — `LIKE '%foo'` cannot use a B-tree (`LIKE 'foo%'` can). Trigram indexes (DB3.9) handle the former.
7. **`OR` across different columns** — sometimes better served by a `UNION` of two indexed queries, since the planner may not use a bitmap combination.
8. **Partial index predicate not provably matched** (DB3.4).
9. **The table is small enough** that it doesn't matter.
10. **The index is invalid** — a failed `CREATE INDEX CONCURRENTLY` leaves an invalid index that is not used (DB3.7).

The diagnostic sequence: `EXPLAIN (ANALYZE, BUFFERS)` to see what it chose and its estimates; `ANALYZE` and retry; check `pg_indexes` for the index's actual definition; and for testing only, `SET enable_seqscan = off` to force the alternative and compare — **which tells you whether the planner's cost model or your assumption is wrong**, and is a diagnostic rather than a fix.

**DB3.6 — Finding and removing unused and duplicate indexes**

```sql
-- unused: never scanned since stats reset
SELECT schemaname, relname AS table, indexrelname AS index,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size,
       idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelid NOT IN (SELECT conindid FROM pg_constraint)  -- keep constraint-backing
ORDER BY pg_relation_size(indexrelid) DESC;

-- duplicates / redundant prefixes
SELECT indrelid::regclass AS table, array_agg(indexrelid::regclass) AS indexes
FROM pg_index
GROUP BY indrelid, indkey
HAVING count(*) > 1;
```

**Redundancy to look for**: an index on `(a)` is redundant if an index on `(a, b)` exists, because the composite serves everything the single-column one does (DB3.2). That's the most common form and it's easy to accumulate as people add indexes for individual queries.

**Removing safely:**

1. **Check `idx_scan` over a meaningful period.** Statistics reset on restart and on `pg_stat_reset()`, so **a low count may mean "recently reset", not "unused"** — check `stats_reset` first. And **a period must cover monthly and quarterly jobs** (A2.10's argument: absence of use is not absence of need).
2. **Check all replicas**, because a read replica may use an index the primary never does — reporting queries run there. **This is the classic mistake**: dropping an index that only the analytics replica used.
3. **Never drop indexes backing constraints** (primary key, unique) — the constraint depends on them.
4. **Make it reversible**: keep the exact `CREATE INDEX` statement, and prefer `ALTER INDEX ... SET (indisvalid)`-style soft disabling where the engine supports it. Postgres 15+ has no direct "invisible index"; **MySQL 8 does** (`ALTER TABLE ... ALTER INDEX ... INVISIBLE`), which lets you test removal without dropping — a genuinely useful feature worth naming.
5. **Drop with `DROP INDEX CONCURRENTLY`** to avoid a lock (DB3.7).
6. **Monitor for plan regressions** afterwards.

The payoff: reclaimed storage, faster writes (DB3.1), less vacuum work, and less cache pressure.

**DB3.7 — Creating an index concurrently**

```sql
CREATE INDEX CONCURRENTLY idx_orders_customer_created
  ON orders (customer_id, created_at DESC);
```

**A plain `CREATE INDEX` takes an `ACCESS EXCLUSIVE`-adjacent lock** (in Postgres, a `SHARE` lock) that **blocks all writes to the table for the duration** — which on a large table is minutes to hours. On a live production table that's an outage.

**`CONCURRENTLY`** builds the index without blocking reads or writes, by making two passes over the table and waiting for existing transactions to complete.

The costs and caveats, which are the substance:

- **It takes considerably longer** — roughly twice the work, plus waiting.
- **It cannot run inside a transaction block**, which means **most migration tools need special handling** (DB7.7) — Rails, Django, and Flyway all have specific mechanisms for it, and forgetting is a common migration failure.
- **It can fail and leave an `INVALID` index** — which occupies space, is maintained on writes, and **is not used by the planner** (DB3.5). You must `DROP INDEX` and retry. **Check `pg_index.indisvalid` after any concurrent build**, and this check is routinely skipped.
- **It waits for all transactions older than the build to finish**, so **a long-running transaction blocks it indefinitely** (DB4.9). A stale idle-in-transaction session can stall an index build for hours with no obvious cause.
- **It cannot be used to create a `UNIQUE` index if duplicates exist** — it will fail at the validation pass.

The equivalents: MySQL 8 does most `ALTER TABLE` operations online by default (`ALGORITHM=INPLACE, LOCK=NONE`), and for older versions or unsupported operations, **gh-ost and pt-online-schema-change** exist (DB7.9).

**DB3.8 — Index bloat and rebuilding**

**Bloat** is space occupied by dead index entries and partially-empty pages. In Postgres, MVCC means an update writes a new row version and the old index entries remain until vacuumed (DB4.4, DB12.3); pages that empty out aren't necessarily returned.

**Causes**: high update/delete churn, vacuum falling behind (DB12.3), long transactions preventing cleanup (DB4.9), and random insertion order fragmenting the tree (DB1.3's UUIDv4 point).

**Consequences**: more pages to read for the same data, so more I/O and more buffer cache consumed; slower scans; and wasted storage and backup size.

**Detecting it**: the `pgstattuple` extension gives accurate figures; `pg_stat_user_indexes` plus size comparison gives an estimate; and community bloat-estimate queries are widely used but approximate.

**Rebuilding:**

```sql
REINDEX INDEX CONCURRENTLY idx_orders_customer;   -- Postgres 12+
REINDEX TABLE CONCURRENTLY orders;
```

**`REINDEX CONCURRENTLY` (Postgres 12+) is the important one** — before it, `REINDEX` took an exclusive lock and the workaround was building a new index concurrently and swapping names. `pg_repack` remains the tool for table bloat and for older versions.

The judgement: **rebuild when bloat is materially affecting performance or storage, not on a schedule.** Routine reindexing is unnecessary maintenance on a healthy system; **persistent bloat is usually a symptom that vacuum isn't keeping up** (DB12.3), and rebuilding without fixing that means you'll be back in a month.

**DB3.9 — Specialised index types**

- **B-tree** — the default. Equality, ranges, sorting, prefix matching.
- **Hash** — equality only; rarely worth it over B-tree in Postgres.
- **GIN (Generalised Inverted Index)** — for values containing **multiple components**: array membership (`@>`), JSONB key/value containment, and **full-text search** over `tsvector`. **Fast to search, slow to update**, and larger — the inverted structure means one row update touches many index entries. `fastupdate` batches this at the cost of search latency.
- **GiST** — a framework for **geometric and range types**: PostGIS spatial queries, range overlap (`&&`), nearest-neighbour ordering. Also supports **exclusion constraints** — e.g. "no two bookings for the same room may overlap in time", which is genuinely difficult to express otherwise.
- **BRIN (Block Range Index)** — stores min/max per block range. **Tiny and effective only when the column correlates with physical order** — a timestamp on an append-only table is the canonical case, where a BRIN can be thousands of times smaller than a B-tree and nearly as effective. Useless on unordered data.
- **`pg_trgm` with GIN/GiST** — trigram indexes enabling `LIKE '%foo%'` and fuzzy similarity matching, which B-trees cannot do (DB3.5).

The decision guidance: **B-tree unless you have a specific reason.** GIN for JSONB and full-text, GiST for spatial and ranges, BRIN for large append-only time-ordered tables, trigram for substring search. And **the honest note on full-text**: Postgres full-text search is good enough for many applications and avoids operating Elasticsearch — but if search is a core product feature with relevance tuning, faceting, and typo tolerance, a dedicated search engine is the right answer (DB9.9).

---

## DB4. Transactions & concurrency

**DB4.1 — Isolation levels and the anomalies they prevent**

| Level | Dirty read | Non-repeatable read | Phantom read | Write skew |
|---|---|---|---|---|
| Read Uncommitted | Possible | Possible | Possible | Possible |
| Read Committed | Prevented | Possible | Possible | Possible |
| Repeatable Read | Prevented | Prevented | Possible* | Possible |
| Serializable | Prevented | Prevented | Prevented | Prevented |

\* *In Postgres, Repeatable Read is implemented with snapshot isolation and does prevent phantom reads in the SQL-standard sense, but does not prevent write skew — which is why Serializable exists separately.*

The essential points:

- **The levels are a spectrum from performance to correctness.** Stronger isolation means more blocking or more aborted transactions.
- **The standard describes anomalies, not implementations**, so **the same level name behaves differently across engines** — Postgres's Repeatable Read is snapshot isolation; MySQL's is different in its locking behaviour. **Never assume the name means the same thing** across engines.
- **Serializable in Postgres is SSI** (Serializable Snapshot Isolation) — it doesn't lock more, it **detects conflicts and aborts one transaction with a serialization failure**. So **the application must be prepared to retry**, which is the practical consequence and the thing people don't build for.
- **Read Uncommitted is essentially unused** — Postgres treats it as Read Committed.

**DB4.2 — The anomalies**

- **Dirty read** — reading uncommitted data from another transaction that may roll back. Prevented at Read Committed and above.
- **Non-repeatable read** — reading the same row twice in one transaction and getting different values, because another transaction committed a change in between. Prevented at Repeatable Read.
- **Phantom read** — running the same *range* query twice and getting different *rows*, because another transaction inserted or deleted matching rows. Prevented at Serializable (and by snapshot isolation in Postgres RR).
- **Write skew** — the subtle one, and the one worth being able to explain, because it's what makes Serializable necessary:

> **Two doctors are on call. The rule: at least one must remain on call. Both simultaneously check "how many others are on call?" — each sees one other — and both take themselves off. Each transaction read a consistent snapshot, each made a locally valid decision, and the invariant is now violated. No row was updated by both transactions, so no write-write conflict was detected.**

Snapshot isolation does not prevent this, because the transactions read overlapping data and wrote disjoint data. **Only Serializable (or explicit locking, or a constraint) prevents it.**

Also worth naming: **lost update** — two transactions read a value, both compute a new one, and the second overwrites the first. Prevented by Repeatable Read in Postgres (the second update fails), and by optimistic concurrency at the application level (DB4.8).

The practical relevance: **write skew is the anomaly that causes real business-logic bugs** — overbooking, double-spending against a balance check, violating a "at least one" or "at most N" rule. If a system has an invariant across rows that's checked then acted upon, it needs Serializable, `SELECT ... FOR UPDATE`, or a database constraint.

**DB4.3 — Your engine's default and its implications**

- **Postgres: Read Committed.**
- **MySQL/InnoDB: Repeatable Read.**
- **Oracle: Read Committed.**
- **SQL Server: Read Committed** (with locking, unless RCSI is enabled).

**The implications of Postgres's Read Committed**, since it's the common case:

- **Each statement sees a new snapshot**, taken at the start of that statement — not at the start of the transaction. So **two identical `SELECT`s in one transaction can return different results** (non-repeatable read), which surprises people who assume a transaction gives a stable view.
- **`UPDATE` has special behaviour**: if it tries to update a row another transaction has changed and committed, it **re-reads the row and re-evaluates the `WHERE` clause** against the new version. That's usually what you want and can produce surprising results when the condition no longer matches.
- **Read-modify-write is unsafe** without explicit locking or optimistic concurrency (DB4.8) — you can read a value, another transaction changes it, and you write based on stale data.
- **Aggregate consistency isn't guaranteed** across statements — a report running several queries in one transaction can see an inconsistent picture.

**When to raise it**: use **Repeatable Read** for a multi-statement report needing a consistent snapshot. Use **Serializable** where a cross-row invariant must hold (DB4.2) — **and build retry logic**, because serialization failures are normal at that level and an unhandled one is an error to the user.

The MySQL note: **Repeatable Read as the default means MySQL behaves differently for read-modify-write patterns**, and code ported between engines can have subtly different concurrency behaviour — a real portability trap.

**DB4.4 — MVCC and readers not blocking writers**

**Multi-Version Concurrency Control**: rather than locking a row for reading, the engine keeps **multiple versions** of each row. Each transaction sees the version consistent with its snapshot.

In Postgres: every row version has `xmin` (the transaction that created it) and `xmax` (the transaction that deleted or superseded it). A transaction's **snapshot** determines which versions are visible. **An `UPDATE` writes a new row version and marks the old one dead** — it does not modify in place.

**The result: readers never block writers and writers never block readers.** A long analytical query and a busy write workload coexist, which is the property that makes MVCC valuable and is the main reason it's near-universal.

**The costs, which are the operationally significant part:**

- **Dead row versions accumulate** and must be cleaned up — **that's what vacuum is for** (DB12.3). This is the fundamental link between MVCC and Postgres's most characteristic operational concern.
- **Table and index bloat** if cleanup falls behind (DB3.8, DB12.5).
- **An `UPDATE` is effectively a delete plus an insert**, so it's more expensive than in-place update and it **touches every index on the table** — unless HOT (Heap-Only Tuple) optimisation applies, which requires the updated columns to be unindexed and space on the same page. **Understanding HOT explains why updating an indexed column is much more expensive than updating an unindexed one.**
- **Long-running transactions hold back cleanup** (DB4.9) — vacuum cannot remove versions that any live snapshot might still need.
- **Transaction ID consumption** leads to wraparound risk (DB12.4).

MySQL/InnoDB implements MVCC differently — old versions go to the **undo log** rather than staying in the table — which is why InnoDB has different bloat characteristics and its own equivalent problems (a long transaction growing the undo tablespace).

**DB4.5 — Lock types and escalation**

**Row-level locks**: `FOR UPDATE` (exclusive — blocks other writers and other `FOR UPDATE`), `FOR NO KEY UPDATE`, `FOR SHARE`, `FOR KEY SHARE`. Acquired implicitly by `UPDATE` and `DELETE`.

**Table-level locks**, in increasing strength: `ACCESS SHARE` (a plain `SELECT`), `ROW SHARE`, `ROW EXCLUSIVE` (`INSERT`/`UPDATE`/`DELETE`), `SHARE UPDATE EXCLUSIVE` (vacuum, `CREATE INDEX CONCURRENTLY`, some `ALTER TABLE`), `SHARE`, `SHARE ROW EXCLUSIVE`, `EXCLUSIVE`, and **`ACCESS EXCLUSIVE`** — which conflicts with everything including plain `SELECT`, and is what most `ALTER TABLE` operations take (DB7.1).

**Lock escalation** — converting many row locks into a table lock to save memory — **is a SQL Server and DB2 behaviour. Postgres does not escalate**, and neither does InnoDB. That's worth stating precisely, because the question invites the assumption that all engines do it. Postgres instead stores row locks on the row itself (in `xmax`) plus a lock table for waiting, so it has no memory pressure driving escalation.

The practically important behaviours:

- **`ACCESS EXCLUSIVE` blocks everything**, and — critically — **a query waiting for it queues behind it and blocks everything after.** So a DDL statement waiting on a long-running `SELECT` blocks all subsequent queries on that table, even reads. **This is the mechanism by which a "quick ALTER" takes down a service**, and it's the single most important locking fact for a platform engineer (DB7.1).
- **`lock_timeout`** is the mitigation: fail the DDL fast rather than queueing behind a slow query and blocking everything.
- **Advisory locks** are application-level locks for coordinating outside the data model — useful for singleton jobs.

**DB4.6 — Diagnosing a deadlock and fixing the ordering**

A deadlock is a cycle: transaction A holds a lock B wants, and B holds a lock A wants. **The engine detects the cycle and aborts one transaction** with a deadlock error.

Reading the log:

```
ERROR:  deadlock detected
DETAIL:  Process 4521 waits for ShareLock on transaction 88231; blocked by process 4498.
         Process 4498 waits for ShareLock on transaction 88235; blocked by process 4521.
         Process 4521: UPDATE accounts SET balance = balance - 100 WHERE id = 2;
         Process 4498: UPDATE accounts SET balance = balance - 50 WHERE id = 1;
HINT:  See server log for query details.
```

**The two statements together are the diagnosis**: one transaction updated account 1 then 2; the other updated 2 then 1. **Inconsistent lock ordering.**

**The fix is to acquire locks in a consistent order.** If every transaction touching multiple accounts locks them in ascending ID order, the cycle is impossible:

```sql
-- sort the IDs before locking
SELECT * FROM accounts WHERE id = ANY($1) ORDER BY id FOR UPDATE;
```

The other causes and fixes: **an index-less foreign key check** taking locks in an unexpected order; **`UPDATE ... WHERE` matching rows in different orders** in different sessions — adding a deterministic `ORDER BY` in a `SELECT ... FOR UPDATE` first fixes it; **upgrading a shared lock to exclusive** (read then write) — take the exclusive lock upfront instead; and **long transactions** widening the window (DB4.9).

The operational points: **deadlocks are normal at some rate, so the application must retry** — a deadlock error is retryable and usually succeeds on the second attempt. **`log_lock_waits = on` and `deadlock_timeout`** control detection and logging. And **a rising deadlock rate is a signal**, usually of a new code path with inconsistent ordering.

**DB4.7 — Diagnosing lock contention on a live system**

```sql
-- who is blocking whom
SELECT blocked.pid          AS blocked_pid,
       blocked.query        AS blocked_query,
       blocking.pid         AS blocking_pid,
       blocking.query       AS blocking_query,
       blocking.state       AS blocking_state,
       now() - blocking.query_start AS blocking_duration
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.wait_event_type = 'Lock';
```

**`pg_blocking_pids()` is the key function** — it gives the blocking chain directly rather than requiring a manual join through `pg_locks`.

The method:

1. **Find the blocked queries** — `wait_event_type = 'Lock'` in `pg_stat_activity`.
2. **Find the root blocker** — follow the chain to the transaction blocking others and not itself blocked. **It's frequently `idle in transaction`** (DB4.9), which is the most common and most fixable cause.
3. **Understand what lock and why** — `pg_locks` gives the lock mode and the relation.
4. **Decide**: wait, or terminate the blocker (DB12.10).

The patterns and their causes: **many sessions blocked on one row** — a hot row (a counter, a sequence table, a shared balance); **everything blocked on a table** — a DDL statement holding `ACCESS EXCLUSIVE`, or waiting for it (DB4.5); **`idle in transaction` blocking** — an application bug leaving a transaction open, often an unhandled exception path or a transaction spanning an external API call.

The preventions: **`idle_in_transaction_session_timeout`** to kill abandoned transactions automatically — one of the highest-value settings available and frequently unset; **`lock_timeout`** so a statement fails rather than queueing; **short transactions** as a design rule; and **monitoring lock waits** as a leading indicator (DB12.2).

**DB4.8 — Optimistic vs pessimistic locking**

- **Pessimistic** — lock the row before reading, on the assumption there will be a conflict. `SELECT ... FOR UPDATE`. Other transactions block until you commit.
- **Optimistic** — don't lock; read, compute, and on write **verify nothing changed** (via a version column or a timestamp). If it did, the write fails and the application retries.

```sql
-- pessimistic
BEGIN;
SELECT balance FROM accounts WHERE id = $1 FOR UPDATE;
UPDATE accounts SET balance = $2 WHERE id = $1;
COMMIT;

-- optimistic
UPDATE accounts SET balance = $2, version = version + 1
WHERE id = $1 AND version = $3;
-- 0 rows updated → someone else changed it → re-read and retry
```

**Choosing:**

- **Pessimistic when conflicts are likely**, when a retry is expensive, or when you need to hold a decision across several statements. The cost is **blocking** — other transactions wait, which under load means queueing (O12.1) and risks deadlock (DB4.6).
- **Optimistic when conflicts are rare**, which is the common case. **No blocking at all**, better throughput, and no deadlock risk. The cost is **wasted work on conflict** and the need for retry logic.
- **Optimistic is the right default for a web application** — most requests touch different rows, so contention is rare, and holding a database lock across a user's think time is unacceptable anyway.
- **Pessimistic for a genuinely hot row**, where optimistic would produce a livelock of endless retries.

The related point: **optimistic concurrency is the same mechanism as `If-Match`/ETag in HTTP APIs**, and it's the correct way to handle lost updates across a stateless request boundary — where you cannot hold a database lock across the user's editing session at all.

**DB4.9 — Long-running transactions as an operational hazard**

**A long transaction holds a snapshot, and that snapshot is a floor on what vacuum can clean up.**

The consequences, and this cluster is one of the most important operational facts about Postgres:

- **Vacuum cannot remove dead row versions newer than the oldest live snapshot** (DB4.4, DB12.3). So one long transaction **anywhere in the database** prevents cleanup **everywhere**, and bloat accumulates across all tables (DB12.5).
- **Bloat degrades performance** — more pages to read for the same data.
- **Transaction ID wraparound risk** — a very old transaction prevents the freezing that averts it (DB12.4). **This is how a forgotten session becomes an existential threat.**
- **Locks held for the duration** block others, including DDL (DB4.5, DB4.7).
- **Replication slots and replicas** — a long query on a replica with `hot_standby_feedback` on holds back cleanup on the *primary*, which is a genuinely surprising cross-node effect.
- **`CREATE INDEX CONCURRENTLY` blocks** waiting for it (DB3.7).

**The particularly dangerous form is `idle in transaction`**: a transaction opened, some work done, and then the application went off to call an API, or hit an exception path that didn't roll back. **It's holding a snapshot and locks while doing nothing.**

The controls: **`idle_in_transaction_session_timeout`** (kill idle transactions), **`statement_timeout`** (bound individual statements), **`transaction_timeout`** (Postgres 17+, bounds the whole transaction — a welcome addition), **monitoring the oldest transaction age** as a first-class metric (DB12.2), and the application-side discipline of **never holding a transaction across a network call to another service.**

**DB4.10 — Idempotency for retried operations**

Any operation that can be retried — because of a timeout, a network failure, a message redelivery (M2.2), or a user double-click — must be safe to execute more than once.

The mechanisms:

```sql
-- unique constraint on a client-supplied idempotency key, in the same transaction
BEGIN;
INSERT INTO payment_requests (idempotency_key, account_id, amount_minor)
VALUES ($1, $2, $3);                      -- unique constraint on idempotency_key
UPDATE accounts SET balance = balance - $3 WHERE id = $2;
COMMIT;
-- duplicate key violation → already processed → return the original result
```

```sql
-- upsert for naturally idempotent state
INSERT INTO user_preferences (user_id, theme) VALUES ($1, $2)
ON CONFLICT (user_id) DO UPDATE SET theme = EXCLUDED.theme;
```

The essentials, which mirror M2.3 with the database specifics:

- **The idempotency record and the business effect must be in the same transaction.** Recording the key separately means a crash between them either duplicates the effect or marks it done without doing it. **The database transaction is what makes this correct**, and it's the reason this is easier in a database than across services (M2.6).
- **The key must come from the client and be stable across retries** — generating it server-side defeats the purpose.
- **Store the original response** against the key, so a retry returns the same result rather than an error — which is what payment APIs do.
- **Absolute rather than relative operations** where possible: `SET status = 'paid'` is naturally idempotent; `balance = balance - 100` is not.
- **Optimistic concurrency with a version** (DB4.8) handles the related lost-update case.
- **Retention** — idempotency keys need a cleanup policy, and that bounds the window in which a duplicate is detected.

---

## DB5. Replication & high availability

**DB5.1 — Synchronous vs asynchronous replication**

- **Asynchronous** — the primary commits and acknowledges the client immediately; WAL is shipped to replicas afterwards. **Fast, and there is a window in which committed transactions exist only on the primary.**
- **Synchronous** — the primary waits for at least one replica to confirm receipt (or write, or apply) before acknowledging. **No committed transaction is lost if the primary dies, and every commit pays a network round trip.**

The tradeoff stated precisely: **asynchronous trades durability for latency; synchronous trades latency for durability.** With async, your RPO is your replication lag (DB5.2) at the moment of failure. With sync, RPO is zero for the confirmed replicas.

The details that matter:

- **Postgres `synchronous_commit` has levels**: `off`, `local` (local WAL flush only), `remote_write` (replica received and wrote to OS), `on` (replica flushed to disk), `remote_apply` (replica has applied it and it's visible to readers). **`remote_apply` is what gives read-after-write consistency on a replica** (DB5.3), at the highest latency cost.
- **`synchronous_standby_names` with a quorum** — `ANY 1 (replica_a, replica_b)` means any one confirmation suffices, so one slow replica doesn't stall commits.
- **The availability trap**: with **one** synchronous replica and no quorum configuration, **if that replica goes down, commits block indefinitely.** The primary is up and the database is unusable. **This is a real and severe failure mode** — synchronous replication converts a replica failure into a primary outage unless you configure a quorum or have a fallback.
- **Cost is the round trip**: single-digit milliseconds within an AZ, tens across AZs (A11.4), and it's paid on every commit.

The typical production choice: **synchronous within a region for durability, asynchronous cross-region for DR** — accepting a small RPO on regional loss rather than paying cross-region latency on every write (A11.2).

**DB5.2 — Replication lag: causes, measurement, impact**

**Causes:**

- **Write volume on the primary** exceeding the replica's apply rate.
- **Single-threaded replay** — Postgres's WAL replay is largely serial, so a replica can fall behind a primary using many parallel writers. **This is the structural reason a replica can't always keep up**, and it's not fixed by giving the replica more CPU.
- **A long-running query on the replica** conflicting with replay — the replica must either delay replay (`max_standby_streaming_delay`) or cancel the query. **You choose which** via configuration, and it's a real tradeoff.
- **Network bandwidth or latency** between primary and replica.
- **Slower storage on the replica** — a common false economy.
- **Large transactions** — a single big `UPDATE` produces a burst of WAL replayed serially.
- **Locks on the replica** blocking apply.

**Measuring:**

```sql
-- on the primary: bytes behind, per replica
SELECT client_addr, state,
       pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn)   AS sent_lag_bytes,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- on the replica: time behind
SELECT now() - pg_last_xact_replay_timestamp() AS replication_delay;
```

**Measure both bytes and time.** Bytes tell you the volume outstanding; **time is what maps to business impact and to RPO** (A11.1). A replica 500MB behind means nothing on its own; 45 seconds behind is a number a product owner can reason about.

**Impact**: stale reads (DB5.3); a larger data-loss window on failover (DB5.9); and — the one people forget — **a replica lagging beyond the primary's WAL retention cannot catch up at all** and must be rebuilt from a base backup.

**DB5.3 — Read-after-write inconsistency**

The scenario: a user updates their profile (write goes to the primary), the page reloads (read goes to a replica), and **they see the old value.** The user concludes the save failed and does it again.

It follows directly from asynchronous replication (DB5.1) and is the most common practical consequence of eventual consistency (DB1.7).

The mitigations, best to worst for most applications:

1. **Read from the primary after a write, for a bounded window.** The simplest correct approach: after a write, pin that user's session to the primary for a few seconds. Cheap, and it only shifts a small fraction of reads.
2. **Read your writes via LSN tracking** — the application records the WAL position of its write and, on read, either waits for a replica to reach it or falls back to the primary. Precise, and more machinery.
3. **`synchronous_commit = remote_apply`** (DB5.1) — guarantees the replica has applied it before the commit returns. Correct and the most expensive, since every write pays for it.
4. **Route by operation type** — writes and any read that must be fresh go to the primary; genuinely tolerant reads (dashboards, search, reporting) go to replicas. **This is the most common practical design** and it makes the tolerance decision explicit per query.
5. **UI mitigation** — optimistically render the change locally, so the user sees their write regardless.

The design point to make: **this is an application-architecture problem, not a database setting.** Adding read replicas for scale without addressing it introduces a class of intermittent, user-visible bug that's very hard to reproduce — because it depends on lag at that instant. **It should be designed in before the replicas are introduced**, not debugged afterwards.

**DB5.4 — Failover: automatic vs manual, and triggers**

**Triggers**: primary process failure, host failure, AZ failure, storage failure, network partition, an unresponsive primary (failing health checks), or a deliberate operator action (maintenance, an instance-type change).

**Automatic failover** requires a component that detects failure and promotes a replica — RDS multi-AZ (A7.1), Patroni, repmgr, Orchestrator, or a Kubernetes operator (DB14.3).

**The tradeoff:**

- **Automatic**: fast recovery (typically 30–120 seconds), no human in the loop at 3am. **The risk is false positives** — a network blip between the monitor and the primary triggers a promotion when the primary was fine, producing an unnecessary outage and, in the worst case, split-brain (DB5.5).
- **Manual**: a human verifies the primary is genuinely dead before promoting. **Safer against split-brain and much slower** — minutes to hours, depending on who's awake.

**The requirements for safe automatic failover**, which is the substance:

- **A quorum-based decision** — the failure must be agreed by multiple observers, not diagnosed by one (DB5.5). A single monitor is a single point of false diagnosis.
- **Fencing / STONITH** — the old primary must be **positively prevented from accepting writes**, not merely assumed dead. Without fencing, a primary that was only partitioned comes back and accepts writes (DB5.5).
- **A defined promotion order** — which replica, and what to do if it's lagging (DB5.9).
- **Client redirection** — DNS, a virtual IP, or a proxy (DB5.6).
- **Regular testing** (A11.8) — an untested failover mechanism is a guess.

The practical position: **automatic within a region with proper quorum and fencing; manual for cross-region**, because a cross-region failover has a much larger blast radius, a real RPO decision, and usually needs a human to confirm it's the right call.

**DB5.5 — Split-brain and how quorum prevents it**

**Split-brain**: a network partition separates the primary from the monitoring system, the monitor concludes the primary is dead and promotes a replica, **and the old primary is still alive and accepting writes.** Two primaries, divergent data, and **reconciliation is manual and frequently impossible** — you have two sets of committed transactions with no way to merge them correctly.

**Why quorum prevents it**: promotion requires agreement from a **majority** of nodes. In a partition, **only one side can hold a majority**, so only one side can promote. The minority side knows it's in the minority and refuses to act as primary.

This requires an **odd number of voting members** (3 or 5) so a majority always exists. **Two nodes cannot form a quorum-based system** — a partition gives 1 and 1, neither is a majority, so nothing can promote. This is why a two-node "HA" pair with automatic failover is unsafe, and it's a common naive design.

**Fencing is the complement and is essential**: quorum stops the minority *deciding* to be primary; **fencing stops it continuing to be one.** Mechanisms: STONITH (power off the old primary), revoking its storage access, a proxy refusing to route to it, or the old primary self-demoting when it loses quorum contact. **Without fencing, a partitioned primary that never noticed keeps serving writes to whichever clients can still reach it.**

The implementations: **Patroni uses etcd/Consul/ZooKeeper for the quorum and leader lease** — the leader must continually renew a lease, and if it can't reach the consensus store it demotes itself, which is fencing by design. **RDS handles this internally.** And the general principle mirrors K1.2's Raft requirement and M4.5's ISR reasoning — this is the same distributed-systems problem in every stateful system.

**DB5.6 — In-flight connections during failover**

**They are dropped.** The old primary is gone; its TCP connections die with it. **Every in-flight transaction is aborted and lost** (uncommitted work is rolled back — committed work survives if replication caught up, DB5.9).

The application consequences and requirements:

- **The application must handle connection errors and reconnect.** A pool that doesn't detect broken connections serves them to the application and every query fails until they're recycled. **Pool health-checking and validation on borrow is what makes this survivable** (DB8.2).
- **In-flight transactions must be retried by the application** — the database cannot do it. This is where idempotency matters (DB4.10), because you may not know whether the transaction committed before the primary died.
- **DNS caching is the classic problem**: RDS failover repoints the endpoint's CNAME (A7.1), and **a JVM caching DNS forever keeps connecting to the old IP long after failover completed.** `networkaddress.cache.ttl` must be set. **This is the most common reason a "successful" 60-second failover looks like a 20-minute outage** and is worth naming explicitly (N4.9, A8.5).
- **A proxy shortens the window** — RDS Proxy or PgBouncer holds the client connections and re-establishes its own to the new primary, so clients may see only a pause rather than an error (DB8.6). **This is one of the strongest arguments for a proxy.**
- **Connection storm on recovery** — every application instance reconnects simultaneously, which can overwhelm the new primary (O15.10). Jittered reconnection helps.

The measurement point: **failover time as experienced by the application is longer than the database's failover time** — add DNS propagation, pool recovery, reconnection, and cache warm-up. **Test it end to end** (A11.8), because the vendor's number is not your number.

**DB5.7 — Multi-primary and why it's usually a bad idea**

Multi-primary (multi-master) allows writes on more than one node.

**The fundamental problem: write conflicts.** Two nodes accept conflicting writes to the same row simultaneously. **There is no correct general resolution** — the options are:

- **Last-write-wins by timestamp** — simple, and **silently discards data**, with correctness dependent on clock synchronisation between nodes, which is not guaranteed.
- **Application-level conflict resolution** — correct in principle and requires the application to define a merge for every conflicting case, which is substantial work and often has no sensible business answer ("the balance is either £100 or £150" has no merge).
- **CRDTs** — data structures that converge by construction. Genuinely correct and only applicable to types that can be expressed that way (counters, sets), not to arbitrary business data.

The additional problems: **constraint enforcement breaks** — a unique constraint cannot be enforced across nodes without coordination, so two nodes can both accept the same email address; **foreign keys** have the same issue; **auto-increment sequences** need partitioning; **replication loops** need detection; and **the operational complexity is substantially higher** for everyone who has to reason about it.

**When it's legitimate:**

- **Geographically partitioned writes** where each region writes a disjoint set of rows — a "multi-primary" that never actually conflicts because ownership is partitioned by design. **This is the only comfortable case**, and it's really single-primary-per-partition.
- **Genuinely conflict-free data types.**
- **HA-only configurations** like Galera or Aurora Multi-Master, where the mechanism exists for failover speed and writes are still directed at one node in practice.

The recommendation: **single primary with fast failover solves the availability problem** that multi-primary is usually reached for, without the correctness problem. If the driver is write throughput, the answer is sharding (DB9.4) — partitioned ownership with a single writer per partition.

**DB5.8 — Logical vs physical replication**

- **Physical (streaming)** — ships WAL records; the replica is a **byte-identical block-level copy**. All databases, all tables, same version, same architecture. Read-only.
- **Logical** — decodes WAL into **row-level change events** (insert/update/delete) and replays them as SQL on the subscriber. Selective by table, and the subscriber is a fully writable independent database.

| | Physical | Logical |
|---|---|---|
| Granularity | Whole cluster | Per table / per publication |
| Version compatibility | Must match | **Can differ** |
| Subscriber writable | No | Yes |
| Schema changes | Replicated automatically | **Not replicated — DDL must be applied separately** |
| Overhead | Lower | Higher (decode and replay as SQL) |
| Cross-engine | No | Possible via tooling |

**When logical is needed** — and these are the cases that matter:

- **Major version upgrades with minimal downtime** (DB12.7, DB14.5) — replicate from the old version to a new-version subscriber, then cut over. **This is the standard low-downtime upgrade path** and the most important use.
- **Migration between instances, regions, or providers**, including into or out of a cloud.
- **Selective replication** — sending only certain tables to an analytics system or a partner.
- **Consolidating** several databases into one.
- **CDC** — logical decoding is what Debezium uses (M7.7).

The caveats to name: **DDL is not replicated** — schema changes must be applied to both sides, in the right order, and getting this wrong breaks replication; **replication slots retain WAL** and an inactive slot fills the primary's disk (DB1.9, M7.7) — **a genuine database availability risk**; **sequences are not replicated** in older versions and must be synchronised at cutover; and **tables need a replica identity** (a primary key, or `REPLICA IDENTITY FULL`) for updates and deletes to replicate.

**DB5.9 — Promoting a replica and the data-loss window**

```sql
-- Postgres
SELECT pg_promote();          -- or pg_ctl promote / trigger file
```

**The data-loss window is the replication lag at the moment of promotion** (DB5.2). Transactions committed on the primary but not yet received by this replica are **lost permanently** — they exist only on a primary that is gone.

Quantifying it:

- **With asynchronous replication**: lag at failure. If the replica was 3 seconds behind, you lose up to 3 seconds of committed transactions. **In a payments context that's a real number of real transactions**, and the reconciliation is a business process, not a technical one.
- **With synchronous replication** (DB5.1): zero for the synchronous replica — which is the entire reason to pay for it.
- **If the primary is reachable**, promote gracefully: stop writes, wait for the replica to catch up fully, then promote. **RPO zero, at the cost of the wait.** This is the difference between a planned failover and an emergency one, and it's worth stating because people conflate them.

The operational points that follow:

- **Choose the most caught-up replica** if there are several — compare `replay_lsn`.
- **The old primary must be fenced** (DB5.5) before or during promotion.
- **The old primary cannot simply rejoin** as a replica if it has diverged — it accepted transactions the new primary never saw. **`pg_rewind`** handles this by rewinding it to the divergence point; otherwise it's a rebuild from a base backup.
- **Other replicas must be repointed** at the new primary.
- **Sequences, connection strings, and monitoring** all need updating.
- **Record what was lost** — knowing the lag at promotion tells the business what to reconcile, and capturing it is part of the runbook.

**DB5.10 — Designing HA for a stated RTO and RPO**

The method: **take the RTO and RPO as inputs** (A11.1) and derive the architecture, rather than proposing an architecture and hoping it meets them.

| RPO / RTO | Architecture | Cost |
|---|---|---|
| RPO minutes, RTO hours | Automated backups + PITR (DB6.3), restore on failure | Lowest |
| RPO seconds, RTO ~5 min | Async replica in another AZ, automatic failover | Moderate |
| **RPO 0, RTO 1–2 min** | **Synchronous replica in another AZ + automatic failover with quorum and fencing** | Higher |
| RPO 0, RTO seconds | Sync replication + a proxy holding client connections (DB5.6) | Higher still |
| Regional failure, RPO minutes | Cross-region async replica, manual promotion | Significant, plus cross-region transfer |
| Regional failure, RPO 0 | Cross-region synchronous — **rarely viable** due to latency | Very high, and it slows every write |

A worked answer:

> "For the payments database with an RPO of zero and an RTO of two minutes: RDS multi-AZ with synchronous replication meets the RPO, and its failover is typically 60–120 seconds, which meets the RTO with little margin — so I'd want RDS Proxy in front to hold client connections and remove the DNS and reconnection time from the equation, and I'd verify the number by testing rather than trusting the documentation. For regional DR I'd take an async cross-region replica with manual promotion, accepting an RPO of seconds and an RTO of tens of minutes, because synchronous cross-region would add 30–50ms to every commit and the business hasn't asked for regional RPO zero. The residual risk to flag is that we've never actually tested the cross-region promotion, and I'd fund that before claiming the capability."

**The elements**: the RPO and RTO drive the choice; the mechanism is named; the tradeoff is quantified; the number is verified rather than assumed; and the untested part is called out honestly (A11.3, A11.8).

---

## DB6. Backup, restore & recovery

**DB6.1 — Logical vs physical backups**

- **Logical** (`pg_dump`, `mysqldump`) — extracts data as SQL statements or a portable archive. **Slower to produce and much slower to restore** (it re-executes inserts and rebuilds indexes), but **portable across versions, architectures, and sometimes engines**, and **selective** — one table, one schema, one database.
- **Physical** (`pg_basebackup`, file-level snapshots, EBS snapshots, Percona XtraBackup) — copies the data files. **Fast to take and fast to restore**, and **tied to the same major version and architecture**, and **all-or-nothing** for the cluster.

**When each is appropriate:**

- **Physical for operational backup and DR.** It's the only thing fast enough to meet a realistic RTO on a large database, and it's the basis of PITR (DB6.3). **A 2TB database restored from `pg_dump` can take many hours; from a physical backup, a fraction of that.**
- **Logical for**: migrating between major versions (DB12.7) or platforms, extracting a single table, seeding a development environment, long-term archival where portability matters, and recovering one accidentally-dropped table from a full backup without restoring everything.

**The point to make**: **most organisations need both.** Physical for the RTO, logical for flexibility and for the "we need one table back" case, which is a common real request.

The practicalities: `pg_dump -Fc` (custom format) is compressed and allows selective restore with `pg_restore`; `pg_dump` runs in a single transaction so it's consistent but holds a snapshot for the duration (DB4.9, DB6.7); and **`pg_dumpall` is needed for roles and global objects**, which a per-database `pg_dump` omits — a classic omission discovered during a restore.

**DB6.2 — Full, incremental, and continuous archiving**

- **Full** — a complete copy. Simple, self-contained, largest and slowest.
- **Incremental** — only what changed since the last backup (differential: since the last full; incremental: since the last backup of any type). Smaller and faster to take; **restore requires the full plus the chain**, and a break in the chain invalidates everything after it.
- **Continuous archiving** — a base backup plus **every WAL segment** shipped continuously. This is what enables PITR (DB6.3).

The Postgres model in practice: **`pg_basebackup` for the base, plus `archive_command` (or `pgBackRest`/`WAL-G`/`Barman`) shipping WAL to object storage.** Recovery restores the base and replays WAL forward to any chosen point.

**Postgres 17 added native incremental base backups** (`pg_basebackup --incremental` with `pg_combinebackup`), which is worth knowing as a current development — previously incremental physical backup required a third-party tool.

The considerations: **the WAL archive is as critical as the base backup** — a base backup with a gap in the WAL chain can only be restored to the moment of the backup, losing PITR entirely. **Monitor `archive_command` failures**, because a silently failing archiver means your PITR capability quietly ended weeks ago and nobody knows. And **retention must cover the full chain**, not just the base (DB6.8).

**DB6.3 — Point-in-time recovery and what it requires**

**PITR restores the database to any specific moment** — typically "just before the bad `UPDATE` at 14:23" (DB6.6).

**What it requires:**

1. **A base backup** taken at some point before the target time.
2. **An unbroken chain of WAL** from that base backup up to (at least) the target time.
3. **Somewhere to restore to** — PITR produces a *new* instance; you do not recover in place.

```
restore_command = 'pgbackrest --stanza=main archive-get %f "%p"'
recovery_target_time = '2026-08-20 14:22:59+00'
recovery_target_action = 'promote'
```

The operational realities that matter:

- **Restore time scales with the base backup size plus the volume of WAL to replay.** A base backup from seven days ago means replaying seven days of WAL, which can take longer than restoring the backup itself. **Take base backups frequently enough that replay is bounded** — this is the practical driver of base backup frequency.
- **You restore to a new instance**, so the recovery includes repointing the application — a DNS change or config update that must be in the runbook (A7.3).
- **`recovery_target_time` uses commit timestamps**, so you need to know the target precisely. **`recovery_target_lsn`** or `recovery_target_xid` are more precise if you can identify the offending transaction from the WAL.
- **You can restore, inspect, and adjust** — restore to a candidate time, check whether the bad change is present, and restore again to a different point. **That iteration is part of the real procedure** and takes time.
- **RPO is bounded by WAL archive frequency** — with `archive_timeout`, the worst case is that interval.

**DB6.4 — Performing an actual restore and timing it**

The procedure, and the point of the item is that **you should have done it, with a number:**

1. **Provision the target** — a new instance, sized like production (a smaller instance restores more slowly, so a test on an undersized instance gives a misleading time).
2. **Restore the base backup**, timing it.
3. **Replay WAL** to the target point, timing it.
4. **Verify**: row counts against known values, application-level integrity checks, a representative query, and that recent expected data is present.
5. **Record the total wall-clock time**, broken down by stage.
6. **Compare against the stated RTO** (A11.1). **The recorded time is your evidence for the RTO** — without it, the RTO is an aspiration.

What people discover when they actually do it, which is worth naming because it's the value of the exercise:

- **It takes much longer than expected** — often 2–5× the estimate.
- **Restored EBS volumes are lazily loaded** (A6.8), so the database is up and slow until the blocks are warmed. **The database being available is not the same as the service being usable**, and this frequently doubles the effective RTO.
- **Something is missing** — roles (`pg_dumpall`, DB6.1), extensions, configuration, or a dependent object.
- **The runbook is wrong** — it references a system nobody has access to, or a step that changed.
- **Nobody knew who could authorise it.**

**Automate it**: a scheduled job restoring the latest backup into an isolated environment, running verification, recording the duration, and reporting. **That turns a periodic manual exercise into continuous evidence** (A11.8), and the duration trend is a genuinely useful metric.

**DB6.5 — Why an untested backup isn't a backup**

The argument, and it should be stated as a list of concrete failure modes rather than a slogan:

- **The backup may be corrupt** and you won't know until you need it. Checksums verify the file; only a restore verifies the database.
- **It may be incomplete** — missing roles, extensions, large objects, sequences, or a tablespace (DB6.1).
- **The WAL chain may be broken** (DB6.2), silently limiting you to the base backup's timestamp.
- **The restore procedure may not work** — a version mismatch, a missing tool, a permission, an expired credential.
- **The restore may take far longer than your RTO** (DB6.4), which means you have a backup and not a recovery capability.
- **Nobody may know how to do it.** The person who wrote the runbook has left, and the first attempt is under maximum pressure at 3am.
- **The backup may not have been running at all.** Silent failure of a backup job is common — **it fails, nothing alerts, and the last good backup is from March.**

The framing: **a backup is a means; recovery is the goal.** Until you have restored it and timed it, you have an untested assumption, and the correct way to describe it to a stakeholder is "we take backups; we have not verified we can restore them", which usually produces the funding for DB6.4.

The related controls: **alert on backup job failure and on backup age** (DB12.2) — "last successful backup older than N hours" is the single most valuable backup alert and is often missing; and **verify the backup exists and is the expected size**, since a zero-byte backup file has fooled people.

**DB6.6 — Recovering from an accidental DROP or bad UPDATE**

**This is the most likely real disaster** — far more likely than hardware failure — and it deserves to be treated as the primary scenario.

**Why replication doesn't help**: the `DELETE FROM orders` with no `WHERE` clause replicates faithfully to every replica within milliseconds. **HA protects against infrastructure failure, not against a valid destructive statement.** That distinction is the most important thing to say.

**The recovery:**

1. **Stop the bleeding.** If it's still running, kill it (DB12.10). If the application is compounding it, stop writes.
2. **Determine the exact time and scope** — what statement, when, which rows. `pg_stat_statements`, the log, or the audit log (DB13.8).
3. **PITR to just before it** (DB6.3), **into a new instance** — not over the top of production.
4. **Extract just the affected data** from the restored copy and reconcile it into production, rather than replacing production wholesale — **because production has continued accepting legitimate writes since the incident**, and a full rollback would lose them. **This reconciliation step is the hard part and the one people don't anticipate.**
5. **Verify** before and after.

The faster alternatives worth knowing:

- **A delayed replica** (`recovery_min_apply_delay = '1h'`) — a standby deliberately kept an hour behind. **When someone drops a table, the data is still there**, and you can extract it in minutes rather than doing a full PITR. **Cheap insurance and disproportionately valuable**, and it's the single best mitigation for this specific scenario.
- **Aurora Backtrack** (MySQL) rewinds the cluster in place, in minutes.
- **`pg_dirtyread`** or similar for reading dead tuples not yet vacuumed — a long shot, and occasionally it works if you're fast.

**The preventions matter more than the recovery**: no direct production write access for humans (A2.1); a review requirement for destructive DDL; `BEGIN` before a manual `UPDATE` so you can check the row count before committing; safeguards in the client (`--single-transaction`, `safe-updates` mode in MySQL, which refuses an `UPDATE` without a key predicate); and separate read-only credentials for investigation (DB13.1).

**DB6.7 — Backup impact on a live primary and how to avoid it**

The impacts:

- **I/O load** — reading the entire dataset competes with the workload for IOPS and evicts the buffer cache (O11.3, DB1.8). **The cache eviction is the underrated part**: after a full backup, the working set has been displaced and query latency is elevated until it re-warms.
- **A long-held snapshot** — `pg_dump` runs in one transaction, so **it holds a snapshot for its entire duration**, blocking vacuum cleanup across the database (DB4.9). A multi-hour dump is a multi-hour vacuum stall, which causes bloat (DB12.5).
- **Locks** — `pg_dump` takes `ACCESS SHARE` on every table, which doesn't block reads or writes but **does conflict with `ACCESS EXCLUSIVE`**, so it blocks DDL and — worse — a DDL statement waiting behind it blocks everything else (DB4.5).
- **Network and CPU** for compression and transfer.

**Avoiding it:**

- **Back up from a replica**, not the primary. **The standard answer**, and it removes the load entirely from the write path. The caveats: the replica's lag defines the backup's currency, and a long backup query on the replica can conflict with WAL replay (DB5.2).
- **Use physical backup / storage snapshots** rather than logical — an EBS or storage-layer snapshot has minimal impact on the instance (DB6.10).
- **Throttle** — `pgBackRest` and `WAL-G` support I/O rate limiting.
- **Run in the maintenance window** (DB12.9), off-peak.
- **Continuous archiving** (DB6.2) spreads the cost — WAL is shipped continuously rather than in a large periodic burst.

**DB6.8 — Retention against DR and compliance**

Two different requirements with different answers:

- **DR retention** — how far back do you need to recover *operationally*? Realistically, most recoveries target the last few hours or days. **7–35 days of PITR covers essentially every real incident**, including the "we found the bad migration a week later" case.
- **Compliance retention** — what the regulator, the auditor, or the contract requires. In financial services this can be **6–7 years** and is specified rather than negotiable.

The design that satisfies both without paying compliance rates for operational convenience:

| Tier | Retention | Mechanism | Purpose |
|---|---|---|---|
| PITR window | 7–35 days | Continuous WAL archiving | Operational recovery, any second |
| Daily snapshots | 30–90 days | Physical snapshots | Recent recovery points |
| Monthly | 12 months | Snapshot or logical dump | Longer-term |
| Annual / compliance | 7 years | Logical dump to S3 + Glacier, **object-locked** | Audit and regulatory |

The points that matter:

- **Compliance copies belong in object storage with lifecycle tiering and object lock** (A6.1, A11.7), not in expensive database snapshots. **Cheaper by orders of magnitude**, and immutability is a genuine control against ransomware and against a compromised administrator.
- **A compliance backup must be restorable in seven years**, which argues for **logical format** — a physical backup from a version you no longer run may be unrestorable (DB6.1). This is a real and frequently-overlooked consideration.
- **Cross-account and cross-region copies** for the DR tier (DB6.9, A11.7).
- **Deleting an RDS instance deletes its automated backups** unless a final snapshot is taken (A7.3) — a classic irreversible mistake.
- **GDPR erasure versus retention** is a genuine conflict: personal data in a seven-year backup can't be selectively deleted. The usual resolutions are documented retention justification, or crypto-shredding (M11.5).

**DB6.9 — Cross-region backup: cost and latency**

**Why**: a regional failure destroys same-region backups along with the database. **A backup in the same region as the thing it protects doesn't protect against a regional event** (A11.2), and the same argument applies to same-account backups and account compromise (A11.7).

**The costs:**

- **Cross-region data transfer**, charged per GB and materially more expensive than within a region (A12.4). On a large database backed up daily, this is a real recurring line.
- **Storage in both regions.**
- **KMS re-encryption** — a snapshot encrypted with a regional key must be re-encrypted with a key in the destination (A10.13), and the copying principal needs permissions on both keys.
- **Copy time**, which is proportional to size and **counts toward your effective cross-region RPO** — if the copy takes 40 minutes and runs hourly, your cross-region recovery point is worse than hourly.

**The latency implications:**

- **Restore in the DR region requires the data to be there already** — you cannot copy 2TB across regions during an incident and meet any sensible RTO.
- **Continuous cross-region WAL archiving** gives a much better RPO than periodic snapshot copies, at higher transfer cost.
- **A cross-region read replica** (A7.2) gives a far better RPO and RTO than backups, at the cost of running a continuous instance — and it's a different mechanism with different failure modes (DB5.9).

The judgement to express: **decide the cross-region RPO deliberately and cost it** (A11.3). For many workloads, daily cross-region snapshot copies with a several-hour RPO are entirely adequate and cheap. Continuous replication is for the cases where the business has stated it needs better, and **that statement should exist before the spend does**.

**DB6.10 — What a snapshot does and doesn't guarantee**

**A storage-level snapshot (EBS, LVM, SAN) captures the block device at an instant.** What that means for the database:

**Guarantees**: **crash consistency.** The snapshot is equivalent to the state after a power cut — and because databases are designed to recover from exactly that (WAL replay, DB1.9), **a crash-consistent snapshot of a properly-configured database is restorable.** That's the important thing it *does* give you, and it's why snapshots work at all.

**Does not guarantee:**

- **Application consistency.** Transactions in flight are lost; the database will roll them back on recovery. Fine for the database, and **not fine if the application's state spans the database and something else** — a file on disk, another database, a message queue. **Restoring one and not the other produces an inconsistent system.**
- **Consistency across multiple volumes**, unless the snapshot mechanism is multi-volume-atomic. **A database whose data and WAL are on separate volumes snapshotted independently can produce an unrecoverable pair** — this is a real and serious trap.
- **That recovery will be fast** — WAL replay from a crash-consistent snapshot takes time proportional to the work since the last checkpoint.
- **Immediate performance** — restored EBS volumes are lazily loaded and slow until warmed (A6.8, DB6.4).
- **Logical validity** — a snapshot taken during a half-completed migration captures the half-completed state.

**Improving it**: `pg_start_backup()`/`pg_backup_start()` puts Postgres into a state where a file-level copy is valid; **filesystem freeze** (`fsfreeze`) flushes and quiesces before snapshotting; and **for MySQL, XtraBackup** handles this properly. **Or simply back up from a replica** (DB6.7), where a brief stop is harmless.

---

## DB7. Schema change & migrations

**DB7.1 — Which DDL operations lock, and for how long**

The critical distinction: **an operation that only updates catalogue metadata is instant; one that rewrites the table is proportional to table size.** Both take `ACCESS EXCLUSIVE` in Postgres — the difference is how long they hold it.

**Postgres, safe (metadata only, sub-second):**

- `ADD COLUMN` with no default, or **with a non-volatile default (Postgres 11+)** — the default is stored in the catalogue and applied on read (DB7.2).
- `DROP COLUMN` — marks it dropped; space reclaimed later by vacuum.
- `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT` separately (which takes a weaker lock).
- `RENAME` column or table.
- `ALTER COLUMN ... DROP NOT NULL`.
- Increasing a `varchar` length limit.

**Postgres, dangerous (full table rewrite, proportional to size):**

- `ALTER COLUMN ... TYPE` in most cases.
- `ADD COLUMN` with a **volatile** default (e.g. a function call).
- `SET NOT NULL` — requires a full scan to verify (mitigated by adding a `NOT VALID` check constraint first, validating it, then setting `NOT NULL`, which Postgres 12+ can do without a scan).
- `CREATE INDEX` without `CONCURRENTLY` (DB3.7).
- `CLUSTER`, `VACUUM FULL` (DB12.5).

**The mechanism that makes this dangerous, and the most important point in this section:** `ACCESS EXCLUSIVE` conflicts with everything. **A DDL statement waiting to acquire it queues, and every subsequent query on that table queues behind it — including plain `SELECT`s.** So a "quick" `ALTER TABLE` that waits 30 seconds behind a long-running report **blocks all reads and writes to that table for those 30 seconds.** The `ALTER` itself was instant; the outage came from the queue.

**The mitigation is `lock_timeout`:**

```sql
SET lock_timeout = '3s';
ALTER TABLE orders ADD COLUMN discount_minor integer;
-- fails fast rather than queueing and blocking everything; retry in a loop
```

**MySQL 8** performs many `ALTER TABLE` operations online (`ALGORITHM=INPLACE, LOCK=NONE`), but not all — check per operation, and use gh-ost for the rest (DB7.9).

**DB7.2 — Adding a column to a large live table**

**In Postgres 11+, this is genuinely easy for the common case:**

```sql
ALTER TABLE orders ADD COLUMN discount_minor integer DEFAULT 0 NOT NULL;
```

Since 11, **a non-volatile default is stored in the catalogue and applied on read**, so this is a metadata change and completes in milliseconds regardless of table size. **Before 11, this rewrote the entire table**, which on a large table was an outage — and that's why the fear exists and why plenty of runbooks still say "never add a column with a default".

The remaining cautions:

- **Take `lock_timeout`** anyway (DB7.1), because acquiring the lock can still queue behind a long query.
- **A volatile default** (`DEFAULT gen_random_uuid()`, `DEFAULT now()`) **still rewrites**, because each row needs a distinct value. For those, use the multi-step approach: add nullable, backfill in batches (DB7.8), then set the default and the constraint.
- **`NOT NULL` on an existing column** requires a scan unless you use the `NOT VALID` check-constraint route.
- **Adding a column with a `UNIQUE` constraint** creates an index — do it concurrently (DB3.7).

The general safe sequence for anything non-trivial:

1. Add the column **nullable, with no default**.
2. **Deploy application code that writes it** but doesn't require it (DB7.3).
3. **Backfill in batches** (DB7.8).
4. Add the default and/or `NOT NULL` once the data is complete.
5. Deploy code that requires it.

**DB7.3 — The expand-contract pattern**

The pattern for making a breaking schema change without a breaking deploy, in three phases:

**Expand** — add the new structure alongside the old, so **both old and new application code work against the same schema**:
- Add the new column, nullable.
- Write to **both** old and new from the application (dual-write).
- Backfill the new column from the old (DB7.8).

**Migrate** — move readers:
- Deploy code that **reads from the new** column, still writing both.
- Verify — compare old and new values, watch error rates.

**Contract** — remove the old:
- Deploy code that no longer references the old column.
- **Wait.** Long enough to be confident you won't roll back.
- Drop the old column.

**Why it's necessary**: during a rolling deploy (DB7.5), old and new application versions run simultaneously against one database. **A schema that only one version can use breaks the other**, so the schema must be compatible with both at every moment.

The examples: **renaming a column** becomes add-new, dual-write, backfill, switch reads, drop old — **never a single `RENAME`**, which breaks every running instance of the old code instantly. **Changing a type** is the same shape. **Splitting a table** likewise.

The cost to acknowledge: **it's three or four deploys instead of one**, spread over days, and the intermediate states carry the complexity of dual-writing. **That's the price of not taking downtime**, and the honest tradeoff is that for a small internal service, a two-minute maintenance window may genuinely be cheaper than a week of expand-contract.

**DB7.4 — Deploying schema and application changes in sequence**

**The rule: the schema change must be deployed before the application code that depends on it, and must remain compatible with the code that's still running.**

The safe orderings by change type:

| Change | Order |
|---|---|
| Adding a column | **Schema first**, then code that writes it |
| Removing a column | **Code first** (stop referencing it), wait, then schema |
| Renaming | Expand-contract (DB7.3) — never a single step |
| Adding an index | Schema (concurrently), any time |
| Adding a constraint | Ensure data complies, add `NOT VALID`, validate, then code relies on it |
| Widening a type | Schema first |
| Narrowing a type | Expand-contract |

**The general principle: additive changes go schema-first; destructive changes go code-first.** That single rule covers most cases and is worth stating as the takeaway.

The pipeline mechanics: **run migrations as a separate step before the application deploy**, not on application startup — because on startup, **N replicas all try to migrate simultaneously**, which needs locking and produces confusing failures, and a failed migration becomes a crash-loop (K9.4). Most migration tools take an advisory lock (DB7.7), which turns the race into a wait, but the separate-step approach is cleaner.

**The gap between the two deploys matters**: the schema change must be safe with the *currently running* code for however long that gap lasts — which during a slow rollout or a paused canary can be hours.

**DB7.5 — Why a migration must be backwards compatible during a rolling deploy**

During a rolling deploy (K2.6), **both versions of the application run simultaneously**, potentially for many minutes — longer if the rollout is staged or paused for canary analysis (K2.11).

So at every moment during the deploy, **the schema must work with both the old code and the new code**:

- **The old code must not break.** A dropped or renamed column, a new `NOT NULL` column it doesn't populate, or a tightened constraint all break instances that haven't been replaced yet — **and those instances are serving production traffic.**
- **The new code must not break.** It cannot depend on a schema change that hasn't been applied.

**The rollback consideration is the one people miss**: if you deploy the new code and need to roll back, **the old code must work against the migrated schema.** A migration that's compatible forwards but not backwards means **you cannot roll back the application** — which removes your primary incident response for a bad deploy (TF9.7). **That's usually a more serious constraint than the rolling deploy itself.**

The consequence: **schema changes and code changes should be decoupled across releases** (DB7.3). The schema change ships in release N, the code that uses it in release N+1, and the cleanup in N+2. Each release is independently rollback-able.

And the honest note: **for a service that can take a brief maintenance window**, a stop-migrate-start sequence is far simpler and sometimes the right answer. Expand-contract exists because downtime is unacceptable, not because it's inherently better.

**DB7.6 — Reversible migrations and when reversal is impossible**

A reversible migration has a defined `down` that returns the schema to its prior state.

```python
def upgrade():
    op.add_column('orders', sa.Column('discount_minor', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('orders', 'discount_minor')
```

**When reversal is impossible or lossy:**

- **Dropping a column or table** — the `down` recreates the structure and **the data is gone.** Structurally reversible, semantically not.
- **Narrowing a type** — `varchar(255)` to `varchar(50)` truncates; reversing widens the column and doesn't restore the truncated characters.
- **Data transformations** — merging two columns into one, or normalising a value, generally can't be inverted.
- **Deduplication** — you cannot un-merge rows.
- **Anything involving external systems**.

The practical positions:

- **Prefer forward-only migrations for destructive changes**, and rely on **expand-contract** (DB7.3) so the destructive step happens long after the point where you'd want to roll back. **By the time you drop the column, rollback is no longer a live option anyway.**
- **Where reversal is impossible, say so explicitly** in the migration, and make the recovery path a restore (DB6.3) rather than a `down` migration.
- **Never delete data in a migration that also changes structure** — separate them, so the structural change is reversible and the data change is a deliberate, separately-approved step.
- **Soft-delete first**: rename `orders` to `orders_deprecated_20260820`, wait, then drop. **The rename is instant and instantly reversible**, and it gives you a window to discover what still depends on it. This is a genuinely useful trick and it's the DDL equivalent of disabling before deleting (A10.7).

**DB7.7 — Using a migration tool in a pipeline**

**Flyway** (SQL files, versioned, `V1__create_orders.sql`), **Liquibase** (XML/YAML/SQL changesets with rollback support), **Alembic** (Python/SQLAlchemy), **golang-migrate**, and framework-native tools (Rails, Django, EF Core).

What they all provide: **a version table in the database** recording what's been applied; **ordered, idempotent application** of pending migrations; **checksums** so an already-applied migration that's been edited is detected; and **an advisory lock** so concurrent runners don't collide.

The pipeline integration:

```yaml
- name: Validate migrations
  run: flyway validate            # checksums, ordering, no gaps
- name: Dry run against a restored production snapshot
  run: flyway migrate -dryRunOutput=migration.sql
- name: Review                    # the SQL is the reviewable artefact
- name: Apply
  run: flyway migrate
- name: Deploy application        # separate step (DB7.4)
```

The practices that matter:

- **A separate pipeline step, before the application deploy** (DB7.4) — not on application startup.
- **Migrations in version control, reviewed like code**, with the generated SQL visible in the PR (the same argument as `terraform plan`, TF9.2). **A reviewer should see the actual DDL**, because an ORM-generated migration can do something surprising.
- **Test against a production-sized restored snapshot** — a migration that takes 200ms on an empty dev database can take four hours on production (DB2.9). **This is the check that catches the table-rewrite problem** (DB7.1).
- **`CREATE INDEX CONCURRENTLY` needs special handling** because it can't run in a transaction (DB3.7) — every tool has a mechanism for it and forgetting is a common failure.
- **Set `lock_timeout` and `statement_timeout`** in the migration session so a blocked migration fails rather than blocking production (DB7.1).
- **Never edit an applied migration** — the checksum will fail, and any environment that already ran it is now divergent.

**DB7.8 — Backfilling a large table without saturating the database**

**The naive approach is the classic incident:**

```sql
UPDATE orders SET discount_minor = 0 WHERE discount_minor IS NULL;
-- 200 million rows: hours-long transaction, enormous WAL, massive bloat,
-- locks held throughout, replication lag spikes, possible disk exhaustion
```

**The batched approach:**

```sql
-- loop, in the application or a script, with a pause between batches
UPDATE orders
SET discount_minor = 0
WHERE id IN (
    SELECT id FROM orders
    WHERE discount_minor IS NULL
    ORDER BY id
    LIMIT 5000
    FOR UPDATE SKIP LOCKED
)
RETURNING id;
-- commit each batch; sleep briefly; repeat until zero rows returned
```

The essentials:

- **Small batches, each in its own transaction** — bounded lock duration, bounded WAL, and vacuum can clean up between batches (DB4.9).
- **Sleep between batches**, and make the sleep adaptive — **watch replication lag** (DB5.2) and pause when it grows. **This is the control that keeps replicas healthy**, and it's the one people omit.
- **Drive the batches off an indexed column**, usually the primary key, and track progress by the last ID processed rather than re-scanning with `IS NULL` each time (which gets slower as the remaining set shrinks and scatters).
- **`SKIP LOCKED`** so the backfill doesn't block on rows the application is updating.
- **Make it resumable and idempotent** — it will be interrupted, and restarting from scratch on a 200-million-row table is unacceptable.
- **Run it off-peak** and monitor: replication lag, disk, vacuum activity, and application latency.
- **Consider a new table plus a swap** for very large transformations — write the transformed data into a new table, then rename — which avoids bloating the original entirely.

**DB7.9 — Online schema change tools and why they exist**

**gh-ost** (GitHub) and **pt-online-schema-change** (Percona), for MySQL primarily.

**Why they exist**: before MySQL 8's online DDL, most `ALTER TABLE` operations **locked the table for the duration of a full rewrite** — hours on a large table. Even now, some operations aren't online, and Postgres's `ALTER COLUMN TYPE` still rewrites (DB7.1).

**How they work:**

1. Create a **new empty table** with the desired schema.
2. **Copy rows in batches** from the original.
3. **Capture ongoing changes** — pt-osc uses **triggers** on the original table; **gh-ost reads the binlog instead**, which is its key differentiator.
4. **Atomically swap** the tables with a rename.

**gh-ost's advantage** is worth naming: **no triggers.** Triggers add write latency to every production write for the duration, they're a source of lock contention, and they can't easily be paused. gh-ost's binlog approach means **the migration can be throttled, paused, and resumed based on replication lag** without affecting the production write path — which makes it genuinely operable rather than a fire-and-forget hours-long operation.

The general considerations: **they require significant free disk** (a full second copy of the table); **the swap is brief but not free**; **foreign keys are problematic** (both tools have caveats); and **triggers on the original table** conflict with pt-osc.

**For Postgres**: the equivalent for table rewrites is **`pg_repack`**, and the general approach is **expand-contract** (DB7.3), which avoids the rewrite rather than making it online. **Postgres's superior DDL story** — most operations being metadata-only (DB7.1) — is why these tools are much less needed there, and that's a fair comparative point.

**DB7.10 — Recovering from a migration that fails halfway**

The first question: **is DDL transactional in your engine?**

- **Postgres: yes.** DDL is transactional, so a migration wrapped in `BEGIN`/`COMMIT` either fully applies or fully rolls back. **This is a genuine and significant Postgres advantage** and it removes most of this problem.
- **MySQL: no** (before 8.0's atomic DDL, and even then with limitations). **Each DDL statement implicitly commits**, so a multi-statement migration that fails halfway leaves the schema in a partial state that must be repaired manually.

**The recovery procedure:**

1. **Stop the pipeline.** Do not retry blindly — a partially-applied migration retried from the start may fail on the steps that succeeded.
2. **Determine the actual state** — inspect the schema and compare to what the migration intended. **The migration tool's version table may say "failed" or may say nothing**, and it may disagree with reality.
3. **Decide: forward or back.** Usually **forward is safer** — write a corrective migration bringing the schema to the intended state — because a `down` on a partially-applied migration may itself fail.
4. **Reconcile the version table** so the tool's view matches reality (Flyway `repair`, Alembic `stamp`).
5. **If data was modified and is wrong**, that's a restore (DB6.3, DB6.6) — the schema is recoverable, data isn't.

**The preventions, which are the more useful half:**

- **Wrap in a transaction where the engine supports it** — and know which statements can't be (DB3.7).
- **Test against a production-sized restored snapshot** (DB7.7) — most halfway failures are timeouts or lock waits that only manifest at scale.
- **Set `statement_timeout` and `lock_timeout`** so it fails fast and cleanly rather than after two hours of partial work.
- **Keep migrations small and single-purpose** — one change per migration means a failure has a small, comprehensible blast radius.
- **Separate schema changes from data changes**, so a data backfill failing doesn't leave the schema inconsistent (DB7.6).

---

## DB8. Connections & pooling

**DB8.1 — The cost of a database connection**

**In Postgres specifically, a connection is a forked OS process** — not a thread. That makes connections expensive in a way people underestimate:

- **Memory**: several megabytes of private memory per backend, plus its share of `work_mem` for sorts and hashes — **and `work_mem` is per operation, not per connection**, so a complex query can use several multiples of it. 500 connections each potentially using 4MB × several operations is gigabytes.
- **Establishment cost**: process fork, authentication, TLS handshake — **tens of milliseconds**, which is significant relative to a 2ms query (O12.8).
- **Context switching**: hundreds of runnable backends on a machine with 16 cores means the scheduler thrashes (O9.2).
- **Shared resource contention** — lock tables, buffer pool access, and internal structures scale with backend count.

**The result: Postgres throughput peaks at a connection count around 2–4× the core count and then declines.** More connections beyond that make it *slower*, not faster — a genuinely counterintuitive fact and the whole reason pooling matters (O9.6's contention curve, applied here).

**MySQL uses threads**, which are cheaper, so it tolerates higher connection counts — but the same principle holds directionally.

The consequence: **`max_connections` is not a capacity target to fill.** It's a safety limit. The right number of active connections is small, and getting there requires pooling (DB8.2) — which is why this item is the foundation for the rest of the section.

**DB8.2 — Connection pooling and where the pool should live**

A pool maintains a set of established connections and lends them to requests, avoiding per-request establishment (DB8.1).

**Where it can live:**

1. **In the application process** (HikariCP, `pgx` pool, SQLAlchemy pool, `node-postgres`). **Simple, no extra component, lowest latency.** The problem: **the pool is per process**, so total connections = pool size × process count — which is exactly the autoscaling problem (DB8.4).
2. **Sidecar** — PgBouncer alongside each application pod. Reduces per-pod connection count, still scales with pod count.
3. **Standalone / centralised** — PgBouncer or RDS Proxy between the application and the database. **The total connection count to the database is bounded regardless of how many application instances exist**, which is the property that actually solves the problem.

**The recommendation and its reasoning:**

- **Application pool for a small, stable number of instances** — simplest, and adequate.
- **A centralised pooler once instance count is dynamic or large** (DB8.4) — because that's the only place you can enforce a global bound.
- **Often both**: a small application-side pool for local reuse, and a centralised pooler enforcing the database-side limit. That's the common mature setup.

The considerations for a centralised pooler: **it's another hop** (a little latency) and **another component in the critical path** with its own availability and scaling. **PgBouncer is single-threaded**, so it needs multiple instances (or `so_reuseport`) at high throughput — a real and commonly-missed constraint. **RDS Proxy** is managed and adds failover connection-holding as a benefit (DB5.6).

**DB8.3 — Sizing a pool**

The arithmetic:

```
total connections = pool_size_per_instance × instance_count   (+ background jobs, admin, monitoring)
                  ≤ max_connections − reserved_superuser_connections
```

**Sizing the per-instance pool** uses Little's Law (O12.7):

```
pool_size = peak_throughput_per_instance × average_query_duration
          = 200 req/s × 0.010 s = 2
```

**Which is much smaller than people expect** — and that's the point of the item. The common instinct is a pool of 50 or 100 per instance; the arithmetic frequently says 5 to 10.

**Why a bigger pool is worse, not neutral**: connections beyond what's needed don't increase throughput (the database is the bottleneck, not the pool) and **they let more concurrent queries hit the database, which increases contention and queueing there** (DB8.1, O12.1). **A smaller pool queues in the application — where queueing is cheap — rather than in the database, where it degrades everyone.** That inversion is the key insight, and it's the reasoning behind HikariCP's well-known "small pool" guidance.

The practical method:

1. Compute from Little's Law with measured query duration.
2. **Add headroom** for variance and slow queries.
3. **Multiply by peak instance count** and check against `max_connections`.
4. **Reserve capacity** for migrations, monitoring, admin sessions, and background jobs — and reserve superuser connections so you can always get in to fix things (DB12.10).
5. **Load test** and observe whether the pool saturates or the database does.

**DB8.4 — How autoscaling pods exhaust database connections**

The mechanism, and it's one of the most common real incidents at the intersection of Kubernetes and databases:

```
20 pods × 20-connection pool = 400 connections     (fine)
traffic spike → HPA scales to 100 pods
100 pods × 20 = 2,000 connections                  (max_connections = 500)
```

**The database rejects connections. Every pod fails, including the ones that were working.** And because the application is now erroring, health checks fail, pods restart, and the reconnection storm makes it worse (O15.10).

**The compounding factor**: the autoscaler scaled *because* of load, so the database was already under pressure — and now it's receiving five times the connections, each running queries, which pushes it further past saturation (O12.2). **The autoscaling response to load actively worsens the bottleneck.**

The mitigations:

- **A centralised pooler** (DB8.2) — **the real fix**, because it bounds total database connections regardless of pod count. RDS Proxy or PgBouncer.
- **Small per-pod pools** (DB8.3) — a pool of 5 rather than 20 changes the arithmetic by 4×.
- **Cap `maxReplicas`** on the HPA at a value the database can support, and **treat that as a documented constraint** rather than an arbitrary number (K7.1).
- **Scale on a metric that reflects the actual bottleneck** — if the database is the constraint, scaling the application tier on CPU is scaling the wrong thing (K7.1).
- **Alert on connection count as a fraction of `max_connections`** (DB12.2), as a leading indicator.

The general lesson worth drawing: **an autoscaling stateless tier in front of a fixed-capacity stateful one is a structural mismatch**, and connections are the most common way it manifests. It's the same shape as O14.4 — you scaled the part that scales and moved the load onto the part that doesn't.

**DB8.5 — Transaction, session, and statement pooling**

PgBouncer's modes:

- **Session pooling** — a client holds a server connection for its entire session (until it disconnects). **Safest, least efficient** — effectively just connection reuse.
- **Transaction pooling** — a server connection is assigned for the duration of a transaction and returned to the pool at commit. **Dramatically better multiplexing**: hundreds of client connections can share a few dozen server connections, because most clients are idle between transactions. **This is the mode that delivers the value.**
- **Statement pooling** — the connection is returned after every statement. Most aggressive, and **multi-statement transactions are impossible**, so it's rarely usable.

**What transaction pooling breaks**, which is the substance of the item — anything relying on session state, because you're not guaranteed the same server connection:

- **Prepared statements** (the classic problem — many drivers use them by default; PgBouncer has improved support in recent versions but it remains a common source of errors).
- **`SET` / session-level configuration** — `SET search_path`, `SET timezone`, `SET statement_timeout`.
- **Session-level advisory locks.**
- **`LISTEN`/`NOTIFY`.**
- **Temporary tables.**
- **`WITH HOLD` cursors.**

The practical guidance: **transaction pooling is what you want, and it requires the application to be stateless at the session level.** Configure the driver to disable server-side prepared statements (or use the appropriate PgBouncer setting), avoid session `SET` in favour of per-query configuration or connection-string parameters, and test thoroughly — **the failures are intermittent and confusing**, because they depend on which server connection you happen to get.

**DB8.6 — Using an external pooler and the tradeoffs**

**PgBouncer**: lightweight, mature, very low overhead. **Single-threaded**, so it needs multiple processes or instances at scale. Self-operated — you own its availability, and it's now in the critical path of every query.

**RDS Proxy**: managed, multi-AZ, integrates with IAM authentication (DB13.4) and Secrets Manager, and — the distinctive benefit — **holds client connections across a database failover** (DB5.6), so applications see a pause rather than a wave of errors. Costs per vCPU-hour of the underlying instance, which is a real ongoing charge.

**The tradeoffs to state:**

- **Another hop** — a small latency addition on every query, usually sub-millisecond and worth measuring.
- **Another component in the critical path** — its failure is a total database outage from the application's perspective. It needs HA, monitoring, and capacity planning of its own.
- **Transaction pooling constraints** (DB8.5) — real application changes may be required.
- **Reduced visibility** — `pg_stat_activity` shows the pooler's connections, so **attributing a query to an application instance becomes harder**, which matters during an incident. Application-level tagging (`application_name`) helps.
- **Cost**, for RDS Proxy.

**The benefits that justify it**: bounded database connections regardless of application scale (DB8.4); faster connection acquisition for the application; failover connection holding; and for RDS Proxy, IAM auth without the application handling token generation.

The judgement: **introduce a pooler when connection count is a live constraint or when autoscaling makes it unpredictable** — not by default. For a small, fixed deployment, an application-side pool is simpler and has fewer failure modes.

**DB8.7 — Diagnosing connection exhaustion and finding the leak**

The symptom: `FATAL: sorry, too many clients already`, or pool acquisition timeouts in the application.

```sql
-- what's using connections
SELECT state, count(*), max(now() - state_change) AS max_age
FROM pg_stat_activity GROUP BY state ORDER BY count DESC;

-- by application and host
SELECT application_name, client_addr, state, count(*)
FROM pg_stat_activity GROUP BY 1,2,3 ORDER BY count DESC;

-- the smoking gun: idle in transaction
SELECT pid, application_name, client_addr,
       now() - state_change AS idle_duration,
       substring(query, 1, 80)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY state_change;
```

**The state distribution is the diagnosis:**

- **Mostly `idle`** — connections held by pools and not in use. **Not a leak; the pools are oversized** (DB8.3) or there are too many instances (DB8.4).
- **Mostly `idle in transaction`** — **an application leak.** A transaction was opened and never committed or rolled back, usually an exception path that doesn't clean up, or a transaction spanning an external call. **This is the classic leak** and it's also blocking vacuum and holding locks (DB4.9).
- **Mostly `active`** with long durations — not a connection leak; the database is saturated and queries are slow (DB12.6). **Connections are a symptom, not the cause.**
- **Growing steadily over time** — a genuine leak: connections created and never returned to the pool, usually a code path that opens a connection outside the pool's management or fails to close on an error.

The fixes: **`idle_in_transaction_session_timeout`** to kill leaked transactions automatically — the single most valuable setting here; **pool leak detection** (HikariCP's `leakDetectionThreshold` logs a stack trace for a connection held too long, which identifies the offending code path directly); **`application_name`** set per service so you can attribute connections; and structurally, **a pooler** (DB8.6).

**DB8.8 — Timeouts: connection, statement, idle-in-transaction**

The layers, each bounding a different thing:

- **Connection timeout** (client-side) — how long to wait to *establish* a connection. Bounds the impact of an unreachable or overloaded database.
- **Pool acquisition timeout** (client-side) — how long to wait for a connection *from the pool*. **Distinct from the above and frequently confused** — exhaustion of the pool manifests here (DB8.7).
- **`statement_timeout`** (server-side) — kills any statement running longer than this. **The most important one to set**, because it bounds the damage of a runaway query (DB12.10) and prevents one bad query saturating the database.
- **`idle_in_transaction_session_timeout`** (server-side) — kills a session idle inside a transaction. **The fix for the most common leak** (DB8.7) and for the vacuum-blocking hazard (DB4.9).
- **`lock_timeout`** (server-side) — fails a statement waiting too long for a lock. **Essential for DDL** (DB7.1).
- **`idle_session_timeout`** (Postgres 14+) — kills sessions idle outside a transaction. Use carefully; it will disconnect healthy pooled connections.
- **`transaction_timeout`** (Postgres 17+) — bounds the whole transaction.
- **TCP keepalives** — detect a dead peer where no timeout would otherwise fire.

The design principles:

- **Set them at multiple layers**, and **make outer timeouts longer than inner ones** — an application request timeout shorter than `statement_timeout` means the client gives up while the query keeps running, consuming resources for nobody (O15.6's stale-work point).
- **Set `statement_timeout` per role or per connection**, not globally — a reporting role can have a long one, an OLTP role a short one (DB13.1). **A global setting is either too short for reports or too long to protect OLTP.**
- **Migrations need their own values** (DB7.7), usually a short `lock_timeout` and a long `statement_timeout`.
- **A timeout is not a fix** — it bounds the damage. A query hitting `statement_timeout` regularly is a query to fix (DB2.10).

---

## DB9. Scaling

**DB9.1 — Vertical scaling limits, and why it's still often right first**

**The limits**: a hard ceiling at the largest instance available; cost rises super-linearly at the top of the range; **it remains a single point of failure** regardless of size; resizing requires a restart or a failover (A7.1); and eventually **a single write path cannot be made faster**, because writes must serialise through the WAL (DB1.9).

**Why it's still usually the right first move:**

- **It requires no application changes.** Sharding (DB9.4) is a major engineering project measured in quarters; resizing an instance is a maintenance window.
- **Modern instances are very large.** 128 vCPUs and 4TB of RAM handles a workload that would have needed a cluster a decade ago — **most applications will never outgrow a single well-tuned primary**, and assuming otherwise is premature.
- **The cheapest capacity is often optimisation, not hardware** — a missing index (DB3.2), an N+1 (DB2.7), or a bad query (DB2.10) frequently recovers more headroom than a size upgrade, at no ongoing cost.
- **Engineering time is scarcer than machine time** until you're large.
- **Distributed databases have their own costs** — cross-shard queries (DB9.6), operational complexity, and a new set of failure modes.

The sequence to state: **optimise → cache → vertical → read replicas → partition → shard.** Each step is more invasive than the last, and **skipping to sharding because it's the "real" answer is a common and expensive mistake.** The honest position is that vertical scaling buys years for most workloads, and the right time to plan for horizontal is when you can see the ceiling, not before.

**DB9.2 — Scaling reads with replicas, and what it doesn't solve**

Read replicas (A7.2) add read capacity: route read-only queries to replicas, keeping the primary for writes.

**What it solves**: read throughput; isolating analytical queries from the OLTP workload (DB1.4); and providing a promotion target for HA (DB5.9).

**What it doesn't solve**, which is the point of the item:

- **Write throughput.** **Every write still goes to the single primary**, and every replica must apply the full write stream. **Adding replicas increases total write work** (each one replays everything), so read replicas make the write bottleneck slightly worse, not better.
- **Storage size.** Every replica holds a full copy.
- **Read-after-write consistency** (DB5.3) — introducing replicas introduces a class of bug.
- **Replication lag** as a new operational concern (DB5.2).
- **Application complexity** — routing logic, deciding per query which reads can tolerate staleness.
- **A single hot row or table** — replicas don't help contention on the primary's write path (DB9.5).

The framing: **read replicas scale one dimension.** If you're write-bound, storage-bound, or bound by contention on a hot row, they do nothing — and teams reach for them reflexively because they're easy to add. **Diagnose which resource you're actually short of** (DB12.6) before assuming replicas are the answer.

**DB9.3 — Partitioning and choosing a partition key**

**Partitioning splits one logical table into physical pieces within a single database.** (Distinct from sharding, DB9.4, which splits across separate databases.)

```sql
CREATE TABLE orders (
    id bigserial, customer_id bigint, created_at timestamptz NOT NULL, ...
) PARTITION BY RANGE (created_at);

CREATE TABLE orders_2026_08 PARTITION OF orders
  FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
```

**Strategies**: **range** (dates — the most common), **list** (region, tenant, status), **hash** (even distribution when there's no natural range).

**What it buys:**

- **Partition pruning** — a query with `WHERE created_at >= '2026-08-01'` scans one partition instead of the whole table. **The main performance benefit.**
- **Cheap bulk deletion** — `DROP TABLE orders_2025_01` is instant and reclaims space immediately, versus a `DELETE` of 50 million rows that generates enormous WAL and bloat. **This is often the strongest practical reason to partition** (DB9.7).
- **Smaller indexes per partition**, so index maintenance and vacuum are faster and more parallel.
- **Tiered storage** — old partitions on cheaper storage.

**Choosing the key:**

- **It must appear in the `WHERE` clause of most queries**, or pruning doesn't happen and you've added complexity for nothing. **This is the single most important criterion.**
- **Time is the usual answer** for event, order, and log data — it matches both the query pattern and the retention pattern.
- **Even distribution** to avoid hot partitions (DB9.5).
- **It should be immutable** — updating the partition key moves the row between partitions, which is expensive.

The caveats: **unique constraints must include the partition key**, which is a real modelling constraint; **too many partitions** (thousands) degrade planning time; and **partition maintenance must be automated** (`pg_partman`) or you wake up to inserts failing because no partition exists for today.

**DB9.4 — Sharding and the operational cost**

**Sharding splits data across independent databases**, each holding a subset. Unlike partitioning (DB9.3), the shards are separate systems with separate connections, separate failover, and no shared query layer.

**What it enables**: write throughput beyond a single primary, and storage beyond a single instance. **It's the only real answer to a write ceiling.**

**The operational cost, which is the substance:**

- **Cross-shard queries and transactions become hard or impossible** (DB9.6).
- **Rebalancing** — adding a shard means moving data, online, without downtime. **This is the hardest ongoing operation** and it must be designed for from the start (consistent hashing or a lookup-table approach, rather than modulo, which requires rehashing everything when the shard count changes — the same problem as Kafka partition counts, M4.11).
- **Schema migrations must run on every shard**, consistently, with partial-failure handling (DB7.10).
- **Backups, failover, monitoring, and upgrades multiply** by shard count. Ten shards is ten primaries, ten replica sets, ten backup chains.
- **Application complexity** — routing logic, a shard map, and handling a shard being unavailable.
- **Hot shards** (DB9.5) — an uneven key distribution means one shard is the bottleneck and the others idle.
- **Referential integrity across shards is gone** (DB1.3).

**The alternatives to consider first**: vertical scaling (DB9.1), read replicas if read-bound (DB9.2), caching (DB11), partitioning (DB9.3), archiving old data (DB9.7), moving a high-volume table to a different datastore (DB9.9), and functional decomposition — **splitting by service rather than by row**, which is often easier and delivers much of the benefit.

The judgement: **shard when you have a demonstrated write or storage ceiling that nothing else addresses**, and be honest that it's a multi-quarter project with permanent operational overhead. **Managed options** — Aurora Limitless, Citus, Vitess, DynamoDB (DB10) — take on some of the burden and are worth evaluating before building it yourself.

**DB9.5 — Hot partitions and skew**

**Skew**: an uneven distribution of data or traffic across partitions or shards, so one carries disproportionate load.

**The signature**: aggregate metrics look fine, one shard or partition is saturated, and **adding capacity doesn't help** because the constraint is one unit that can't be split.

**Causes:**

- **Low-cardinality key** — partitioning by `status` when 95% of rows are `completed`.
- **A dominant tenant** — one customer with 40% of the data. **Structural in multi-tenant systems** and not a mistake so much as a reality to design for.
- **Time-based keys with current-time concentration** — partitioning by month means **all writes go to the current month's partition**, so write load is entirely on one partition regardless of how many exist. **A very common and under-appreciated case**: range partitioning by time spreads *storage* and *reads* but concentrates *writes*.
- **Sequential IDs** with hash partitioning are fine; sequential IDs with range partitioning concentrate.

**The fixes:**

- **Higher-cardinality key**, or a **composite key** (`tenant_id, created_at`).
- **Hash partitioning** where the access pattern doesn't need range pruning — spreads writes evenly, at the cost of losing pruning for range queries.
- **Isolate the whale** — give the dominant tenant its own shard or its own database. **Often the cleanest answer in multi-tenant systems** (the same conclusion as M5.4).
- **Salt the key** for the hot value specifically, accepting that queries for it must scatter-gather.

The diagnostic: **per-partition size and per-shard query rate**, which requires monitoring at that granularity — aggregate database metrics hide skew completely, which is why it's usually discovered late (DB12.1).

**DB9.6 — Why cross-shard joins and transactions are hard**

**Joins**: a join requires bringing matching rows together. If `customers` is sharded by `customer_id` and `products` by `product_id`, **a join between them requires data from every shard.** The options are all bad: scatter-gather (query every shard and join in the middle tier — latency is the slowest shard, and it doesn't scale), broadcasting a small table to every shard (works only for small reference data), or denormalising so the join isn't needed (DB1.2).

**The design response**: **shard by a key that keeps related data together.** Sharding everything by `tenant_id` means all of a tenant's data is on one shard and joins within a tenant are local. **This is why tenant-based sharding is so common** — it makes the common query pattern shard-local by construction.

**Transactions**: an atomic write across shards requires a distributed transaction.

- **Two-phase commit** — a coordinator asks all participants to prepare, then commit. **It works and it's avoided**: it holds locks across the network for the duration, it blocks if the coordinator fails at the wrong moment, and it scales badly. Also, `PREPARE TRANSACTION` in Postgres leaves prepared transactions that block vacuum if orphaned (DB4.9).
- **Sagas** — a sequence of local transactions with compensating actions (M2.11). Available, and it gives up atomicity and isolation, so intermediate states are visible and compensation is an application design problem.
- **Avoid the requirement** — design so transactions are shard-local. **This is the real answer**, and it's a constraint on the data model rather than a technical solution.

The framing: **sharding trades the relational model's convenience for scale.** Joins and cross-entity transactions are the things you give up, and if the application depends on them heavily, sharding is a much larger project than it appears (DB9.4).

**DB9.7 — Archiving and purging as a scaling strategy**

**The most under-used scaling lever**, and often the cheapest.

The argument: **a table with 5 billion rows of which 4.8 billion are older than two years and never queried is 20× larger than it needs to be.** Every index is larger, vacuum takes longer, backups take longer, restores take longer (DB6.4), and the working set doesn't fit in cache (DB1.8).

**The approaches:**

- **Partition by time and drop old partitions** (DB9.3). **`DROP TABLE` is instant and reclaims space immediately**, where a `DELETE` of a billion rows generates enormous WAL, bloats the table (DB12.5), and doesn't return the space without a `VACUUM FULL`. **This alone is a strong argument for partitioning.**
- **Archive to cheaper storage** — export old partitions to S3 as Parquet, queryable with Athena (A15.5) when needed. Retains access at a fraction of the cost.
- **Move to a separate archive database** — same engine, cheaper instance, kept for the rare query.
- **Delete in batches** if partitioning isn't available (DB7.8), and follow with a repack to reclaim space.

The prerequisites: **a retention policy agreed with the business and with compliance** (DB6.8, DB13.9) — the blocker is almost never technical, it's that nobody has authorised deleting anything. **Getting that decision made is the actual work**, and framing it with the cost of retention ("this data costs £X/month and has been queried twice in a year") is what moves it.

The benefits to quantify: smaller backups and faster restores (directly improving RTO, A11.1); faster vacuum; better cache hit ratio; lower storage cost; and faster queries through smaller indexes.

**DB9.8 — CQRS and read-model separation**

**Command Query Responsibility Segregation**: separate the model used for writes from the model(s) used for reads.

The write side is normalised, transactional, and optimised for correctness. The read side is a **projection** — denormalised, pre-joined, shaped exactly for how it's queried — kept current by events or CDC (M7.7).

**When it's worth it:**

- **Read and write patterns are genuinely different** — a write model with complex invariants, and reads that are simple lookups of pre-computed views.
- **Read volume massively exceeds write volume**, and the reads require expensive joins or aggregations that can be pre-computed once.
- **Multiple different read shapes** — the same data needed as a search index, an analytical rollup, and an API response, each best served by a different store (DB9.9).
- **You've already got the events** — if you're publishing domain events anyway (M1.4), building a projection is incremental work.

**The costs, which must be named:**

- **Eventual consistency between the models** (DB1.7) — the read model lags the write model, with all the read-after-write consequences (DB5.3).
- **A projection pipeline** to build, monitor, and recover — and **rebuilding a projection from scratch** must be possible and tested, because they get corrupted or need reshaping (M2.10).
- **Two models to keep aligned** as the domain evolves.
- **Substantially more complexity**, and CQRS is frequently adopted where a read replica plus a materialised view would have sufficed.

The judgement: **the lightweight version — a read replica (DB9.2), a materialised view, or a cache (DB11) — solves most of what people reach for CQRS to solve.** Full CQRS earns its place when the read shapes are genuinely different in kind from the write model, not merely more numerous. And it's frequently conflated with event sourcing (M8.7) — they're independent, and adopting both at once is a large commitment.

**DB9.9 — When the answer is a different datastore**

The cases where continuing to scale the relational database is the wrong move:

- **Full-text search with relevance ranking, faceting, and typo tolerance** → **Elasticsearch/OpenSearch.** Postgres full-text is good enough for basic needs (DB3.9); it is not a search engine.
- **Time-series at high ingest volume** → **TimescaleDB** (still Postgres, so lower operational cost), **InfluxDB**, or **Prometheus** for metrics (O3.1). Purpose-built compression and retention.
- **Analytical queries over billions of rows** → a **column store** (ClickHouse, Redshift, BigQuery, Snowflake). Orders of magnitude faster for scans and aggregations (DB1.4).
- **Caching and ephemeral state** → **Redis** (DB11).
- **Graph traversal of arbitrary depth** → a graph database (DB1.1).
- **Extremely high write throughput with simple access patterns** → **Cassandra or DynamoDB** (DB10).
- **Large binary objects** → **object storage**, not the database. Storing files as BLOBs bloats backups and buffer cache for no benefit.

The critical counterweight: **every additional datastore has a fixed operational cost** — backup, monitoring, patching, expertise, on-call, and a new failure mode. **Polyglot persistence is frequently adopted for one team's convenience and paid for by the platform team forever** (DB14.1).

The framing that makes this a senior answer: **the bar for adding a datastore should be that the relational database is genuinely the wrong tool, not merely suboptimal.** And **the first question is whether the workload should be in the primary transactional database at all** — moving analytics off to a replica or a warehouse (DB1.4) frequently solves the problem without a new engine.

---

## DB10. NoSQL

**DB10.1 — Single-table design and access-pattern-first modelling**

**The inversion**: in relational modelling you design entities and relationships, then write queries. **In DynamoDB you enumerate the access patterns first and design the table to serve them** — because you cannot join, and a query you didn't design for may require a scan.

**Single-table design** puts multiple entity types in one table, using a generic partition key (`PK`) and sort key (`SK`) with overloaded meanings:

| PK | SK | Attributes |
|---|---|---|
| `CUSTOMER#123` | `PROFILE` | name, email, tier |
| `CUSTOMER#123` | `ORDER#2026-08-01#9981` | total, status |
| `CUSTOMER#123` | `ORDER#2026-08-14#9995` | total, status |
| `ORDER#9981` | `ITEM#1` | sku, quantity, price |

**One query on `PK = CUSTOMER#123` returns the profile and all orders in one round trip** — the equivalent of a join, achieved by co-locating related items in one partition. `SK` prefix conditions (`begins_with(SK, 'ORDER#')`) filter within it, and the sort key's ordering gives you date-ordered results for free.

**The tradeoffs to state honestly:**

- **It's genuinely harder to reason about** — the table is not self-describing, and a new engineer cannot understand it from the schema.
- **New access patterns may not be servable** without a GSI (DB10.3) or a migration, and **the modelling decision is very hard to change later** — the opposite of SQL, where a new query is just a new query.
- **It requires knowing the access patterns up front**, which is a strong assumption for a product still evolving.

The honest position: **single-table design is correct for DynamoDB at scale and is over-applied.** For a low-volume table with simple access, multiple simple tables are clearer and the performance difference is irrelevant. **The complexity is justified by the round-trip savings at high volume**, not by orthodoxy.

**DB10.2 — Choosing a partition key and sort key**

**The partition key determines physical distribution** — items with the same PK live together and are the unit of query. **The sort key orders items within a partition** and enables range queries.

The criteria for the **partition key**:

- **High cardinality**, so load spreads (DB10.4's throttling, DB9.5's skew).
- **Even access distribution** — not just many distinct values, but no dominant one.
- **It must be known at query time** — every `Query` requires an exact partition key. **You cannot query without it**, which is the fundamental constraint.

The criteria for the **sort key**:

- **It defines the ordering and the range queries you can do**, so encode what you'll filter and sort by.
- **Composite sort keys** (`ORDER#2026-08-01#9981`) enable hierarchical `begins_with` queries — a genuinely powerful technique: `begins_with(SK, 'ORDER#2026-08')` gives one month's orders.
- **It's part of the uniqueness constraint** — PK+SK must be unique.

For stated access patterns:

| Access pattern | PK | SK |
|---|---|---|
| Get a customer's orders, newest first | `CUSTOMER#<id>` | `ORDER#<timestamp>#<order_id>` |
| Get one order by ID | `ORDER#<id>` | `METADATA` |
| Get orders in a status for a customer | `CUSTOMER#<id>` | `STATUS#<status>#<timestamp>` (or a GSI) |
| Time-series per device | `DEVICE#<id>` | `<timestamp>` |

The anti-patterns: **a low-cardinality PK** (`status`, `type`, a date) creating a hot partition (DB9.5); **a timestamp as PK**, which concentrates all current writes on one partition; and **choosing the PK from the entity's natural identity** without checking it matches the query pattern — the most common modelling error.

**DB10.3 — GSIs and LSIs, and their constraints**

- **LSI (Local Secondary Index)** — **same partition key, different sort key.** Shares the base table's partitions and throughput. **Must be created with the table and cannot be added later** — a hard constraint. Limited to 10GB per partition key value. Supports strongly consistent reads.
- **GSI (Global Secondary Index)** — **different partition key and sort key.** A separate structure with **its own partitions and its own capacity**. Can be created and deleted at any time. **Eventually consistent only.**

**GSIs are what make additional access patterns possible**, and their constraints matter:

- **Eventually consistent** — a write to the table propagates to the GSI asynchronously. **Reading your own write from a GSI may return stale data** (DB1.7).
- **Separate capacity**, and **this is the operationally important one: if a GSI is throttled, writes to the base table are throttled too.** A GSI under-provisioned relative to the table throttles everything — a non-obvious coupling and a real incident cause (A7.6).
- **Projections** — `KEYS_ONLY`, `INCLUDE`, or `ALL`. **Projecting fewer attributes costs less storage and less write throughput**, and requires a second fetch from the base table if you need more. A covering-index tradeoff (DB3.3).
- **Sparse indexes** — items lacking the GSI's key attributes aren't indexed at all. **This is a powerful technique**: a GSI keyed on `status` where the attribute is only present while an order is pending gives you a small, efficient index over just the pending orders (the DynamoDB equivalent of a partial index, DB3.4).
- **20 GSIs per table** by default.

The design point: **each GSI is a full copy of the projected data, with its own cost.** They're not free, and a table with eight GSIs has eight times the write amplification.

**DB10.4 — Provisioned vs on-demand, and throttling**

- **On-demand** — pay per request, scales instantly, no capacity planning. **Considerably more expensive per request at sustained high volume**, and the right choice for unpredictable, spiky, or new workloads.
- **Provisioned** — specify RCU/WCU, optionally with auto-scaling. **Much cheaper at steady predictable load**, and reservable for further discount.

**Throttling behaviour**, which is what the item is really testing:

- Exceeding capacity returns **`ProvisionedThroughputExceededException`**; the SDK retries with backoff, and sustained throttling surfaces as application errors and latency.
- **Auto-scaling reacts in minutes**, so it **does not protect against a sudden spike** — a provisioned table with auto-scaling still throttles during a flash event. That's the key limitation.
- **Burst capacity** provides a small buffer of unused capacity (up to 5 minutes' worth) — which masks brief spikes and then exhausts (O11.5's cliff, again).
- **Adaptive capacity** automatically shifts capacity toward hot partitions and **substantially mitigates but does not eliminate the hot-partition problem** (DB9.5). It's worth knowing this improved — the old "capacity is divided evenly across partitions" model is outdated.
- **The diagnostic signature of a hot partition**: throttling while **aggregate consumed capacity is well below provisioned.** CloudWatch's aggregate metrics hide it; **Contributor Insights** shows the offending keys.

The guidance: **on-demand for new or unpredictable workloads and while you learn the pattern; provisioned with auto-scaling once it's steady**, with reserved capacity for the baseline. And **monitor throttling events as a first-class alert** (DB12.2), because the failure is a client-visible error rather than a slowdown.

**DB10.5 — Strongly vs eventually consistent reads**

- **Eventually consistent** (the default) — may return stale data if it reads a replica that hasn't caught up. Typically consistent within milliseconds. **Costs 0.5 RCU per 4KB.**
- **Strongly consistent** — always reflects all prior successful writes. **Costs 1 RCU per 4KB — double** — and has slightly higher latency.

The constraints worth knowing:

- **Not available on GSIs at all** (DB10.3), which is often the binding limitation.
- **Not available on cross-region replicas** in a global table.
- **More susceptible to unavailability** — a strongly consistent read requires the leader replica, so it can fail where an eventually consistent read would succeed.

The guidance: **default to eventually consistent**, because it's half the cost and the staleness window is usually milliseconds. **Use strongly consistent only where a stale read causes an actual problem** — reading a balance before a decision, checking whether a resource was just created, or any read-after-write in a workflow (DB5.3).

The practical pattern: **a workflow that writes then immediately reads should either use a strongly consistent read or carry the value forward** rather than re-reading — the second is free and is usually the better design.

**DB10.6 — DynamoDB Streams and CDC uses**

Streams capture **item-level changes** in order, per partition key, retained for 24 hours. Each record carries the change type and, depending on `StreamViewType`, the `OLD_IMAGE`, `NEW_IMAGE`, both, or just keys.

**Uses:**

- **Triggering downstream work** — a Lambda consuming the stream to send a notification, update a search index, or call another service.
- **Materialising a read model** (DB9.8) — projecting DynamoDB changes into Elasticsearch, a relational database, or S3.
- **Replication and archiving** — feeding a data lake, and the mechanism behind global tables.
- **Audit** — an immutable record of every change (DB13.8).
- **The outbox equivalent** — because the stream is derived from the committed write, it **solves the dual-write problem** for DynamoDB (M2.6): write to the table, and the event is guaranteed to follow.

The operational details: **ordering is guaranteed per partition key**, not globally (M2.4). **Lambda processing is per shard, and a failing batch blocks that shard** until it succeeds or expires (A4.7, M2.7) — so a poison record halts a partition's stream, and `BisectBatchOnFunctionError` plus an on-failure destination are essential. **24-hour retention** means a consumer down longer than that loses data permanently (M1.7). And **Kinesis Data Streams for DynamoDB** is the alternative with longer retention and multiple independent consumers.

**DB10.7 — Document stores and when schema flexibility becomes a liability**

**The appeal**: no migrations, add fields freely, store naturally-shaped nested data, and iterate quickly early in a product's life.

**When it becomes a liability:**

- **The schema still exists — it's just implicit and unenforced.** After two years you have documents written by six versions of the application, with `email`, `emailAddress`, and `email_address`, some missing fields entirely, and some with a string where others have an array. **Every reader must handle every historical variant**, and nothing tells you what they are.
- **Migrations don't disappear, they move into the application** — as defensive code handling old shapes, forever, because you never migrated the old documents.
- **No referential integrity** (DB1.3), so orphaned references accumulate silently.
- **Querying across documents is limited**, and joins are done in application code (DB1.1).
- **Analytics become painful** — a warehouse or a query engine needs a schema, and inferring one from inconsistent documents is genuinely hard.
- **Validation moves to the application**, so a bug or a direct write introduces bad data that nothing catches.

The mitigations: **schema validation** (MongoDB's JSON Schema validation) — which is re-adding the schema you avoided, and is the right call; **a version field** on every document so readers can dispatch; **actually migrating old documents** rather than accumulating compatibility code; and **treating schema changes with the same discipline as relational migrations** (DB7.3).

The framing: **schema flexibility defers the cost of schema decisions; it doesn't remove it.** The cost arrives later, spread across every reader, in a less manageable form. It's genuinely valuable for heterogeneous data and rapid early iteration, and it's frequently chosen to avoid migrations and then paid for with interest.

**DB10.8 — Why "NoSQL scales better" is incomplete**

The claim contains something true and omits the price:

**What's true**: systems like DynamoDB and Cassandra scale horizontally to enormous write throughput and storage, largely automatically, because they made design choices a relational database doesn't.

**What's omitted — the choices that make it possible:**

- **They gave up joins.** Scaling is easy when every query hits one partition. **The relational database's problem is that it promises arbitrary joins across all data**, and that promise is what's hard to distribute (DB9.6).
- **They gave up multi-row transactions and constraints** (or restricted them severely).
- **They gave up ad hoc queries** — access patterns must be designed up front (DB10.1), and an unanticipated query may be impossible or require a full scan.
- **They gave up strong consistency by default** (DB10.5), pushing the consequences into the application (DB1.7).
- **They gave up flexibility to change** — the data model is very hard to alter later.

**So the accurate statement**: NoSQL systems scale horizontally *because they restrict the workload to patterns that distribute well*. **It's a trade, not a free improvement.**

The further points: **a well-tuned relational database on a large instance handles far more than most people assume** (DB9.1), so the scaling ceiling is often theoretical for a given application; **Postgres can be scaled horizontally** (Citus, read replicas, partitioning) when needed; and **the operational cost is not lower** — it's different, and Cassandra in particular is demanding to operate well.

The framing to give: **choose based on the access pattern, not the scaling ceiling.** If your access is genuinely key-based at high volume, a key-value store is the right tool and will be simpler as well as faster. If you need ad hoc queries and transactional integrity, choosing NoSQL for a scaling headroom you'll never use buys you a permanent constraint for no benefit (DB14.1).

---

## DB11. Caching

**DB11.1 — Caching strategies**

- **Cache-aside (lazy loading)** — the application checks the cache; on a miss, reads the database and populates the cache. **The most common.** Only requested data is cached; the first request for each key is slow; and stale data persists until TTL or invalidation.
- **Read-through** — the cache itself fetches from the database on a miss. Same behaviour, with the logic in the cache layer rather than the application.
- **Write-through** — writes go to the cache and the database synchronously. **The cache is always current**, at the cost of write latency, and you cache data that may never be read.
- **Write-behind (write-back)** — writes go to the cache and are flushed to the database asynchronously. **Fastest writes, and a window where committed data exists only in the cache** — a cache failure loses it (DB11.6). Rarely acceptable for anything durable.
- **Refresh-ahead** — proactively refresh popular keys before they expire, avoiding the miss entirely.

The guidance: **cache-aside is the default and the right starting point** — simple, resilient (a cache failure degrades to database load rather than an outage), and it caches only what's used. **Write-through where staleness is unacceptable and the data is read frequently.** **Write-behind essentially never** for data you can't afford to lose.

The design points regardless of strategy: **the application must work with the cache empty or unavailable** (DB11.8) — treating the cache as required makes it a single point of failure; and **the failure mode should be a slow response, not an error.**

**DB11.2 — TTL choice and the staleness tradeoff**

**The TTL is a direct trade between staleness and load.** Longer TTL means a higher hit ratio and less database load, and data can be stale for that long. Shorter is fresher and more expensive.

The reasoning:

- **Start from how stale the data may acceptably be**, as a business question. Product prices: seconds. A user's display name: minutes. A country list: hours or days.
- **Consider the cost of a miss** — if regenerating the value is very expensive, a longer TTL is worth more staleness.
- **Consider the rate of change** — caching data that changes every second with a 60-second TTL means it's almost always wrong.

**The critical operational point: add jitter** (O15.10). A fixed TTL means all keys populated together expire together, producing a synchronised stampede (DB11.4). **`ttl = base ± random(0, base * 0.1)`** costs nothing and removes an entire failure mode.

The complementary technique: **a TTL is a safety net, not the primary invalidation mechanism.** Explicit invalidation on write (DB11.3) keeps data fresh; the TTL bounds the damage when invalidation is missed or fails — which it will be. **Relying solely on TTL means accepting staleness up to the TTL on every change; relying solely on invalidation means a missed invalidation is stale forever.** Use both.

**DB11.3 — Cache invalidation approaches and why it's hard**

The approaches:

- **TTL expiry** (DB11.2) — passive, simple, bounded staleness.
- **Explicit invalidation on write** — delete or update the key when the underlying data changes. Fresh, and it requires every write path to know which keys it affects.
- **Write-through** (DB11.1) — the write updates the cache, so it's never stale.
- **Event-driven invalidation** — the database publishes changes (CDC, M7.7) and a consumer invalidates. **Catches writes from every path, including ones that don't go through the application** — which is its main advantage.
- **Versioned or generational keys** — include a version in the key (`user:123:v7`), so a version bump makes all old keys unreachable and they expire naturally. **Avoids the need to enumerate keys**, which is the elegant part.

**Why it's genuinely hard:**

- **Knowing which keys an update affects.** A change to a product affects the product key, every category listing containing it, the search results, and any aggregate. **The dependency graph between data and cached derivations is not tracked anywhere**, so it lives in developers' heads and is incomplete.
- **Multiple write paths** — the application, a batch job, an admin tool, a direct SQL fix. **Any path that doesn't invalidate leaves stale data**, and the direct-SQL case is the one nobody remembers.
- **Distributed caches** — invalidating across many nodes, and local in-process caches on many instances which may not be reachable at all.
- **Race conditions** — invalidate then repopulate can interleave with a concurrent write, caching the old value *after* the invalidation. **This is a real and subtle bug**, and it's why "delete on write" is safer than "update on write".
- **Partial failures** — the database write succeeds and the invalidation fails (the dual-write problem again, M2.6).

The pragmatic position: **explicit invalidation on the primary write path, plus a bounded TTL as the backstop, plus versioned keys for anything with a complex dependency graph.** And **accept that some staleness will occur** — designing the application to tolerate it is more robust than trying to make invalidation perfect.

**DB11.4 — Cache stampede and preventing it**

**The scenario**: a popular key expires. Hundreds of concurrent requests miss simultaneously, all query the database for the same value, and **the database receives a burst of identical expensive queries.** On a hot enough key this alone can saturate the database.

**The worse variant**: a cache node fails or restarts, so **everything misses at once** and the database receives 100% of the traffic it was shielded from. **The cache outage becomes a database outage**, which is the cascading failure people don't plan for (A7.7).

**The preventions:**

- **Jittered TTLs** (DB11.2, O15.10) — prevents the synchronised-expiry variant. **Cheapest and most effective single measure.**
- **Request coalescing / single-flight** — the first miss acquires a lock and fetches; concurrent requests for the same key wait for its result rather than issuing their own query. **This is the direct fix** and most cache libraries support it.
- **Probabilistic early expiration** — each read has a small, increasing chance of refreshing the value before it actually expires, so one request refreshes it while others still get the cached value. Elegant, and it eliminates the cliff entirely.
- **Refresh-ahead** (DB11.1) for known-hot keys.
- **Serve stale while revalidating** — return the expired value immediately and refresh in the background. **Best user experience**, and requires tolerating brief staleness.
- **Ensure the database can survive a cold cache** — capacity planning that assumes the cache is present is planning for a system that fails when the cache does (DB11.8).

**DB11.5 — Eviction policies and spotting a badly sized cache**

Redis `maxmemory-policy`:

- **`noeviction`** — reject writes when full. **Turns memory pressure into write errors**, which for a cache is usually wrong but is correct if Redis is being used as a datastore (DB11.7).
- **`allkeys-lru`** — evict least-recently-used across all keys. **The sensible default for a pure cache.**
- **`allkeys-lfu`** — least-frequently-used. Better when access frequency is a stronger signal than recency, which is often true for caches with a stable hot set.
- **`volatile-lru`/`volatile-ttl`/`volatile-random`** — evict only keys with a TTL set. **Dangerous if most keys have no TTL** — the policy has nothing to evict and behaves like `noeviction`.

**Spotting a badly sized cache:**

- **Hit ratio below expectation** — under 80% for a cache that should have a stable working set suggests it's too small (or the TTL is too short, or the key space is too large).
- **High eviction rate** — the direct signal. **Evictions rising while hit ratio falls means the working set exceeds the memory**, and you're churning: caching things and evicting them before they're read again.
- **`used_memory` at `maxmemory`** persistently.
- **Latency of database queries rising** as more traffic passes through.
- **A hit ratio that drops sharply at a particular time** — a batch job flooding the cache with single-use keys, evicting the hot set. **A classic and easily fixed problem** (cache the batch job's data separately or not at all).

The response: size it to hold the working set, or reduce the key space, or separate workloads into different caches or logical databases so one can't evict another's data (O15.5's bulkhead applied to cache).

**DB11.6 — Redis persistence and that a cache can lose data**

Redis is **in-memory**, with optional persistence:

- **RDB (snapshotting)** — periodic point-in-time dumps. Compact, fast to restore, and **loses everything since the last snapshot** — potentially minutes.
- **AOF (append-only file)** — logs every write. `appendfsync everysec` (the usual setting) loses up to a second; `always` is durable and much slower. Larger files, slower restart, and needs periodic rewriting.
- **Both** — AOF for durability, RDB for fast restarts. The recommended combination when durability matters.
- **Neither** — pure cache. **Restart loses everything.**

**The point of the item: a cache can lose data, and the application must tolerate it.**

- **A Redis restart or failover with RDB-only persistence loses recent writes.**
- **Even with AOF, `everysec` loses up to a second** on an unclean shutdown.
- **Failover to a replica loses whatever hadn't replicated** — Redis replication is asynchronous by default (DB5.1).
- **Eviction silently removes data** (DB11.5) — with `allkeys-lru`, **any key can vanish at any time**, including ones you assumed were durable.
- **`maxmemory` with the wrong policy** can drop data you needed.

The design consequence: **if losing it matters, Redis is not the right store for it** — or at least not without accepting the window. Session data lost on failover means users are logged out; a rate-limit counter lost means limits reset; a job queue lost means work disappears. **Each of those may be acceptable, and the decision must be deliberate** (DB11.7).

**DB11.7 — Redis as cache, datastore, and queue**

Redis is capable in all three roles, and **the risk is conflating them within one instance** without noticing the different requirements:

- **As a cache** — data is reconstructible from the source of truth. **Loss is a performance event, not a data event.** Eviction is fine, persistence optional, `allkeys-lru`.
- **As a datastore** — Redis holds the only copy (session state, rate limit counters, leaderboards, feature flags). **Loss is a data event.** Needs persistence, replication, and `noeviction` — because eviction would silently delete the only copy.
- **As a queue** (lists, or Streams) — needs at-least-once semantics, consumer tracking, and durability. **Redis Streams provide consumer groups and acknowledgement** and are a reasonable lightweight queue; plain `LPUSH`/`RPOP` loses a message if the consumer dies after popping.

**The risk of conflating them, concretely:**

- **One instance with `allkeys-lru` holding both cache entries and session data** — under memory pressure, **sessions are evicted and users are logged out**, apparently at random. **This is the classic failure** and it's very hard to diagnose because it looks like an application bug.
- **Persistence configured for the cache use case** (none, for speed) while the same instance holds data that must survive a restart.
- **A cache-scale key space evicting datastore keys.**

**The resolution: separate instances, or at minimum separate logical databases with different policies** — and be explicit about which role each serves. **The most valuable question to ask of any Redis usage is "if this instance restarted empty right now, what would break?"** — and if the answer is anything other than "it would be slower", it's not being used as a cache and needs to be configured accordingly (DB11.6).

**DB11.8 — When a cache is masking a problem you should fix**

The signals:

- **The cache exists to make an unoptimised query bearable.** A query taking 3 seconds cached for an hour is a missing index (DB3.2) or an N+1 (DB2.7) with a plaster on it. **The fix is the query**, and the cache hides both the problem and the fact that it's getting worse.
- **The system cannot survive a cold cache** (DB11.4). If a cache restart takes the database down, **the cache isn't an optimisation — it's a load-bearing component with no redundancy**, and your actual database capacity is far below what you think.
- **Cache hit ratio is a critical metric rather than an efficiency one** — meaning a small drop causes an incident.
- **Staleness bugs are frequent** (DB11.3), indicating the caching is too aggressive or too complex for the data's change rate.
- **The cache is caching the cache** — layers of caching added over time, each hiding the previous layer's inadequacy, and nobody can reason about freshness.
- **You're caching to work around a scaling problem** you should have addressed (DB9).

**Why it matters**: a cache converts a capacity problem into a hidden dependency. The database's real capacity is untested and probably inadequate; you discover this during a cache failure, which is the worst moment (O15.1's correlated-failure point — the cache and the database fail together in effect).

The discipline: **fix the underlying query first, then cache for the remaining benefit.** **Periodically test with a cold cache** — deliberately, in a controlled way (T7.9) — to know whether the database can actually take the load. And **size the database for a plausible cache failure**, or accept explicitly that a cache outage is a database outage and document it as such.

---

## DB12. Operations & monitoring

**DB12.1 — The metrics that matter**

**Connections**: active, idle, **idle in transaction** (DB8.7), and total as a **fraction of `max_connections`** — the fraction is what you alert on, not the absolute number.

**Replication**: **lag in bytes and in seconds** per replica (DB5.2), replication slot retained WAL, and slot activity.

**Cache**: **buffer cache hit ratio** — `blks_hit / (blks_hit + blks_read)`. **Below ~95% on an OLTP workload suggests the working set doesn't fit in memory** (DB1.8), and it's one of the highest-signal single numbers.

**I/O**: read and write IOPS against the provisioned limit, **queue depth and await** (O11.2), and **burst balance** if applicable (O11.5).

**Queries**: slow query count, **`total_exec_time` by query** (DB2.8), and the number of long-running queries.

**Locks**: lock waits, deadlock rate (DB4.6), and **the age of the oldest transaction** (DB4.9) — an underused and very valuable metric.

**Vacuum**: dead tuple counts per table, **time since last autovacuum**, autovacuum workers active, and **`age(datfrozenxid)`** (DB12.4).

**Storage**: database size, growth rate, table and index bloat estimates (DB12.5), and **free disk on the WAL volume specifically** (DB1.9).

**Resources**: CPU (including steal, O9.3), memory, and — for RDS — the DB-specific ones like `FreeableMemory` and `DiskQueueDepth`.

The framing: **replication lag, connection saturation, cache hit ratio, transaction age, and oldest-transaction are the leading indicators**; slow queries and CPU are lagging ones (O2.10's saturation argument).

**DB12.2 — Alerts that catch degradation before an outage**

The alerts worth having, chosen for lead time rather than coverage:

| Alert | Threshold | Why it's leading |
|---|---|---|
| Connections used | > 80% of `max_connections` | Exhaustion is a hard failure (DB8.7) |
| Replication lag | > 30s, or > your RPO | Data-loss window and stale reads (DB5.2) |
| Oldest transaction age | > 15 min | Blocks vacuum, holds locks (DB4.9) |
| `age(datfrozenxid)` | > 50% of `autovacuum_freeze_max_age` | **Wraparound is existential** (DB12.4) |
| Disk free | < 20%, and predicted-full in < 4h | WAL full stops writes (DB1.9) |
| Buffer cache hit ratio | < 95% sustained | Working set no longer fits (DB1.8) |
| Deadlock rate | Rising above baseline | New contention pattern (DB4.6) |
| Backup age | > expected interval | **Silent backup failure** (DB6.5) |
| Replication slot lag | > threshold | Retained WAL fills the disk (DB5.8) |
| Failed connections | Any sustained rate | Exhaustion or auth problems |
| Burst balance | < 30% | The cliff (O11.5) |

The design principles (O8, T7.3): **alert on the leading indicator, not the outage.** Connection saturation at 80% gives you time; `too many clients` does not. **Predicted-full** (`predict_linear`, O3.5) beats a static disk threshold, because it accounts for growth rate.

**The two most valuable and most frequently missing**: **transaction ID age** — because wraparound is preventable and catastrophic and nobody notices it until it's urgent; and **backup age** — because a silently failing backup job is only discovered when you need the backup.

**DB12.3 — Vacuum and autovacuum, and the consequences of falling behind**

**Why it exists**: MVCC means an update or delete leaves a **dead tuple** — an old row version no longer visible to any transaction (DB4.4). **Vacuum reclaims that space** for reuse.

Vacuum's three jobs: **reclaim dead tuples**, **update the visibility map** (which enables index-only scans, DB3.3), and **freeze old transaction IDs** to prevent wraparound (DB12.4).

**Autovacuum** triggers per table when dead tuples exceed `autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor × reltuples` — **the scale factor (default 0.2) means a table must accumulate 20% dead rows**, which on a 500-million-row table is 100 million dead tuples before it even starts. **Lowering the scale factor for large, high-churn tables is one of the most valuable per-table tunings available.**

**The consequences of falling behind:**

- **Table and index bloat** (DB12.5) — more pages for the same data, so more I/O and worse cache efficiency.
- **Degraded query performance**, progressively.
- **Index-only scans stop working** because the visibility map is stale (DB3.3).
- **Transaction ID wraparound risk** (DB12.4) — **the existential one**.
- **A vicious cycle**: bloat makes vacuum slower, so it falls further behind.

**Why it falls behind:**

- **A long-running or idle-in-transaction transaction** holding back the cleanup horizon (DB4.9). **The most common cause**, and vacuum will run and reclaim nothing, which looks like vacuum being broken.
- **Autovacuum throttling** — `autovacuum_vacuum_cost_delay` and cost limits deliberately slow it to limit I/O impact. On a busy system the defaults are frequently too conservative.
- **Too few `autovacuum_max_workers`** for the number of tables needing it.
- **A replica with `hot_standby_feedback`** holding back the primary's horizon.
- **Replication slots** retaining WAL and, indirectly, an old snapshot.

The management: **tune per table** for the high-churn ones; **raise the cost limit** so autovacuum keeps up; **monitor dead tuples and last-autovacuum time** (DB12.1); and **eliminate long transactions** (DB4.9), which is usually the actual fix.

**DB12.4 — Transaction ID wraparound as an existential risk**

**The mechanism**: Postgres uses a **32-bit transaction ID**, so there are about 4 billion of them and they wrap around. Visibility is determined by comparing transaction IDs modulo 2³¹ — so a transaction ID "in the future" by more than 2 billion appears to be in the past, and **rows that should be visible become invisible.** That would be silent, catastrophic data loss.

**The protection**: vacuum **freezes** old tuples, marking them as visible to all transactions regardless of ID, which removes them from the comparison. As long as freezing keeps up, wraparound never happens.

**What happens when it doesn't:**

1. At `autovacuum_freeze_max_age` (default 200 million), **autovacuum starts an aggressive anti-wraparound vacuum** on the table — **even if autovacuum is disabled**, and it will not be cancelled by normal means.
2. As the age approaches the limit, Postgres emits increasingly urgent warnings.
3. **At around 1 million transactions remaining, the database refuses all new write transactions** and shuts down to protect the data. **Recovery requires single-user mode and a manual vacuum**, which on a large table takes hours — with the database completely unavailable throughout.

**This is genuinely existential**: a multi-hour, total, unplanned outage that could have been prevented by a metric nobody was watching.

**The monitoring:**

```sql
SELECT datname, age(datfrozenxid),
       round(100.0 * age(datfrozenxid) / 2000000000, 1) AS pct_toward_wraparound
FROM pg_database ORDER BY age(datfrozenxid) DESC;
```

**Alert well before it matters** (DB12.2). The causes of it happening at all: vacuum falling behind (DB12.3), a very long-running transaction, an abandoned replication slot, an orphaned prepared transaction, or autovacuum disabled by someone who thought it was causing load problems.

**Postgres has been improving this** — 64-bit transaction IDs are a long-discussed change — but on every version currently in production it remains a real risk, and knowing about it is a strong signal of operational experience with Postgres.

**DB12.5 — Table and index bloat, and reclaiming space safely**

**Bloat** is space occupied by dead tuples and partially-empty pages (DB12.3). **Vacuum makes the space reusable but does not return it to the operating system** — the table stays the same size on disk and reuses the space internally. **That's the key fact**: normal vacuum controls growth; it doesn't shrink.

**Detecting it**: the `pgstattuple` extension for accurate figures; community bloat-estimate queries for a fast approximation; and the practical signal of a table much larger than its row count and average width suggest.

**Reclaiming it:**

- **`VACUUM FULL`** — rewrites the table compactly. **Takes `ACCESS EXCLUSIVE` for the duration**, so the table is completely unavailable — reads and writes both. **Unusable on a live production table of any size.** It also needs disk space for a full second copy.
- **`pg_repack`** — rebuilds the table online, using triggers to capture concurrent changes and swapping at the end with only a brief lock. **This is the production answer.** Requires roughly double the table's disk space.
- **`CLUSTER`** — reorders by an index and reclaims space; same exclusive lock problem as `VACUUM FULL`.
- **`REINDEX CONCURRENTLY`** for index bloat specifically (DB3.8).
- **Partitioning and dropping old partitions** (DB9.3) — sidesteps the problem entirely for time-series data, and is the best structural answer.

The judgement: **reclaim when bloat is materially affecting performance or when you need the disk back — not routinely.** And **persistent bloat is a symptom** (DB12.3); repacking without fixing why vacuum isn't keeping up means doing it again next quarter. The question to ask is "why did this bloat", and the answer is usually a long transaction or an under-tuned autovacuum.

**DB12.6 — Diagnosing "the database is slow" methodically**

The method, working from symptom to cause (T1):

1. **Establish what "slow" means and its scope.** All queries or one? All clients or one? Since when? What changed? **"Everything is slow" and "the checkout query is slow" have almost disjoint cause sets.**
2. **Check whether it's actually the database.** Application-side latency versus database-side query time (O11.9). **Frequently the database is fine and the application is waiting on connection acquisition** (DB8.7) or something else entirely.
3. **Look at the resource picture** (O2.10): CPU (including steal, O9.3), I/O (await and queue depth, O11.2), memory and cache hit ratio (DB12.1), and network.
4. **Look at what's running now** — `pg_stat_activity` for long queries and, critically, **`wait_event_type`**, which tells you what they're waiting *on*: `Lock` (contention, DB4.7), `IO` (storage), `LWLock` (internal contention), `Client` (waiting on the application — an idle-in-transaction problem).
5. **Look at the aggregate** — `pg_stat_statements` ordered by `total_exec_time` (DB2.8) to find where the load actually is.
6. **Check for the specific operational causes**: locks (DB4.7), vacuum behind (DB12.3), a long transaction (DB4.9), replication lag (DB5.2), a burst-credit cliff (O11.5), connection saturation (DB8.7).
7. **Correlate with changes** — a deploy, a migration, a data volume threshold crossed, a new query, a batch job.
8. **For a specific slow query**, get its plan (DB2.4) and compare against what it used to be — a plan flip from stale statistics is a common cause of sudden degradation (DB2.6).

The discriminating question early on: **is this a change in the database, a change in the workload, or a change in the data?** Those three point at completely different investigations, and asking it explicitly prevents an hour of undirected checking.

**DB12.7 — Version upgrade with a rollback path**

The approaches, and the rollback story is what distinguishes them:

**In-place major upgrade** (`pg_upgrade`, or RDS's managed upgrade):
- Downtime measured in minutes with `--link` mode, longer otherwise.
- **Rollback is a restore from the pre-upgrade snapshot** (A7.5) — losing anything written since. **There is no downgrade.**
- Simple, and the rollback is expensive enough that you must be confident before starting.

**Logical replication upgrade** (DB5.8) — **the low-downtime approach**:
1. Build a new instance on the target version.
2. Set up logical replication from old to new; wait for it to catch up.
3. **Test against the new instance** while it's still a replica — run the application's test suite, check query plans (DB2.6).
4. **Cut over**: stop writes, confirm zero lag, promote the new instance, repoint the application.
5. **Rollback is repointing back to the old instance**, which is still running and intact — optionally with reverse replication configured so it stays current.
- Downtime is seconds to a minute; **rollback is fast and cheap**, which is the entire value.
- More setup, and the DDL and sequence caveats of logical replication apply.

**Blue/green deployments** (RDS) package this pattern as a managed feature and are the right answer where available (A7.5).

The essential steps regardless: **read the release notes** for breaking changes; **test on a restored production-sized snapshot** first, especially query plans, since **a new planner version can regress specific queries** (DB2.9); **take a snapshot immediately before**; **run `ANALYZE` afterwards** — a fresh planner with no statistics produces exactly the "the upgrade made everything slow" report (DB2.6); and **check extension and client-driver compatibility**, which is a frequent blocker.

**DB12.8 — Storage growth and IOPS as capacity inputs**

**Storage:**

- **Measure the growth rate** over months, per table if possible, and separate genuine data growth from bloat (DB12.5) and from index growth.
- **Project forward** (O14.1) and subtract lead time.
- **Include WAL and backups** — WAL volume scales with write rate, and backup storage with database size × retention (DB6.8).
- **Plan the response before it's needed**: archiving (DB9.7), partition dropping (DB9.3), or expansion. **Note that most cloud volumes can grow online but not shrink** (A6.8), so over-provisioning is a one-way door.
- **Alert on predicted-full, not just current free** (DB12.2).

**IOPS:**

- **The distinct constraints are IOPS, throughput, and latency** (O11.1), and you're limited by whichever binds first — for OLTP it's usually IOPS and latency, not throughput.
- **IOPS demand grows with the working set exceeding memory**, which is a **step change, not a linear one**: while the working set fits in the buffer cache, disk IOPS are low; **once it exceeds memory, IOPS demand jumps sharply.** This is why databases degrade suddenly rather than gradually as they grow, and it's the most important thing to say here.
- **Replicas multiply write IOPS** — each applies the full write stream (DB9.2).
- **Vacuum, backups, and index builds** are significant IOPS consumers on top of the workload.
- **Burst credits mask the true requirement** until they run out (O11.5).

The planning input: **track buffer cache hit ratio alongside data growth** (DB12.1). **A declining hit ratio is the early warning that you're approaching the memory cliff**, and it gives you months of notice where IOPS alone gives you none.

**DB12.9 — Maintenance windows and what happens in them**

For a managed service (RDS), the weekly maintenance window is when AWS applies: **OS and database patches**, **minor version upgrades** (if auto-upgrade is on), **hardware maintenance and instance replacement**, and **certificate rotation**.

**What actually happens:**

- **Most patches require a restart** — 1–2 minutes of unavailability on single-AZ.
- **On multi-AZ, it's applied to the standby first, then a failover** (A7.1) — so the impact is a failover rather than a full outage, typically 60–120 seconds, with all the connection consequences (DB5.6).
- **Some operations are online** with no impact.
- **Instance replacement** for hardware issues can be longer.

The management:

- **Choose the window deliberately** — genuinely low-traffic, and not overlapping with batch jobs, backups, or other systems' maintenance. **The default is rarely right for your traffic pattern.**
- **Know what's pending** — RDS shows pending maintenance actions, and some are deferrable while others have a deadline after which AWS applies them regardless. **Being surprised by a forced upgrade is avoidable.**
- **Separate "required" from "optional"** — some actions can be applied immediately at a time you choose, which is better than a window you're not watching.
- **Disable auto minor version upgrade** if you want to control timing, accepting that you must then do it yourself (DB12.7).
- **Test failover behaviour** (A11.8), since that's what maintenance will exercise.

For self-managed: the window is your own, and the same content applies — OS patching, minor upgrades, certificate rotation, index maintenance (DB3.8), and any operation needing an exclusive lock (DB7.1).

The point to make: **a maintenance window is a planned failover, so if failovers hurt, maintenance hurts.** Making failover cheap (DB5.6 — a proxy, correct DNS TTLs, connection handling) makes maintenance a non-event, and that's the higher-value investment.

**DB12.10 — Killing a runaway query safely**

```sql
-- identify it
SELECT pid, now() - query_start AS duration, state, wait_event_type,
       usename, application_name, substring(query, 1, 200)
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '5 minutes'
ORDER BY duration DESC;

-- cancel the query, leave the session alive  ← try this first
SELECT pg_cancel_backend(12345);

-- terminate the whole session — more forceful
SELECT pg_terminate_backend(12345);
```

**The distinction matters**: **`pg_cancel_backend` sends SIGINT** — it cancels the running statement and the transaction is rolled back, but the connection survives, so the application gets an error and can handle it cleanly. **`pg_terminate_backend` sends SIGTERM** — it kills the whole backend and drops the connection, which the application sees as a connection failure.

**Always try cancel first.** Terminate when cancel doesn't work — some operations don't check for cancellation promptly.

**Before killing, consider:**

- **What will the rollback cost?** A long-running `UPDATE` that has modified 50 million rows **must roll back**, and the rollback can take as long as the work did — during which it still holds resources and cannot be interrupted. **Killing it is not instant relief**, and this is the thing people don't expect.
- **What is the application going to do?** If it retries immediately, you've achieved nothing (O15.9).
- **Is it actually the problem?** A long query may be a symptom of blocking rather than the cause (DB4.7) — killing the victim rather than the blocker.
- **Is it a critical job?** A killed migration or backfill may leave partial state (DB7.10).

**The preventions matter more**: **`statement_timeout`** set appropriately per role (DB8.8) means runaway queries kill themselves; **`idle_in_transaction_session_timeout`** for the leaked-transaction case; and **a read-only role with a short statement timeout** for analysts and ad hoc access (DB13.1), which is where most runaway queries originate.

**Never `kill -9` the backend process** at the OS level — Postgres will restart the entire instance to guarantee shared memory consistency, turning one bad query into a full outage.

---

## DB13. Security

**DB13.1 — Least-privilege roles per application**

```sql
-- a role per application, with only what it needs
CREATE ROLE payments_app LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE acme TO payments_app;
GRANT USAGE ON SCHEMA payments TO payments_app;
GRANT SELECT, INSERT, UPDATE ON payments.transactions TO payments_app;
GRANT SELECT ON payments.accounts TO payments_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA payments TO payments_app;

-- default privileges so future tables are covered
ALTER DEFAULT PRIVILEGES IN SCHEMA payments
  GRANT SELECT, INSERT, UPDATE ON TABLES TO payments_app;

-- separate read-only role for analysts and investigation
CREATE ROLE analyst_ro LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE acme TO analyst_ro;
GRANT USAGE ON SCHEMA payments TO analyst_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA payments TO analyst_ro;
ALTER ROLE analyst_ro SET statement_timeout = '30s';   -- (DB12.10)

-- migration role: DDL, used only by the pipeline
CREATE ROLE payments_migrator LOGIN PASSWORD '...';
GRANT CREATE ON SCHEMA payments TO payments_migrator;
```

The design principles:

- **A role per application, not a shared one** — so an audit trail attributes actions, and a compromised credential has bounded scope.
- **Separate the migration role from the runtime role.** **The application should not have DDL permissions**, which means a SQL injection or a compromised application cannot drop tables (DB13.7). **This is one of the highest-value separations available** and it's routinely omitted.
- **No `DELETE` unless the application actually deletes** — many don't, and granting it enables a class of damage for no benefit.
- **`ALTER DEFAULT PRIVILEGES`** so new tables don't silently break the application or require a manual grant.
- **A read-only role for humans**, with a statement timeout, so investigation is safe.
- **Revoke `PUBLIC` grants** — by default `PUBLIC` has `CONNECT` on new databases and `CREATE` on the `public` schema in older versions, which is broader than intended. Postgres 15 fixed the schema default.

**DB13.2 — Why applications shouldn't connect as superuser**

**Superuser bypasses all permission checks.** The consequences:

- **A SQL injection becomes total compromise** (DB13.7) — not just reading a table, but reading every table, dropping the database, writing files, and in Postgres, **executing arbitrary code on the host** via untrusted procedural languages or `COPY ... PROGRAM`. **That escalation from injection to host compromise is the specific reason this matters most.**
- **An application bug can destroy the schema** — a bad migration, a typo'd command in a shell.
- **No audit distinction** — every action is superuser, so attribution is lost (DB13.8).
- **Row-level security is bypassed**, so any multi-tenant isolation built on it evaporates.
- **It defeats every other control you've configured.**

The related points: **RDS doesn't give you true superuser** (`rds_superuser` is a restricted role), which mitigates the worst of it but doesn't make it acceptable. **The migration role needs DDL, not superuser** (DB13.1) — those are different, and conflating them is common. And **superuser credentials should exist, be stored in a vault, be used only for administration, and their use should be alarmed** (A1.4's break-glass argument applied to the database).

The check to suggest: **`SELECT rolname, rolsuper FROM pg_roles WHERE rolsuper;`** and then ask who and what uses each. In most estates that query returns something surprising.

**DB13.3 — Rotating credentials without downtime**

The problem: changing a password invalidates the credential the running application holds.

**The two-user (alternating) pattern**, which is what Secrets Manager's multi-user rotation implements (A7.8):

Maintain two roles with identical permissions. The secret points at user A. Rotation: change **user B's** password, verify it, then update the secret to point at B. Applications pick up B on their next fetch; A's password is changed on the *following* rotation, by which time nothing uses it. **At no point is a credential in use invalidated** — that's the property that makes it zero-downtime.

**Single-user rotation** is simpler and has a brief window where existing connections hold an invalid password — acceptable if connections are short-lived and the client re-fetches on auth failure.

**The application-side requirement is where this usually fails**: the application must **fetch the credential at connection time and re-fetch on authentication failure**, not cache it at process start. **A credential cached at startup defeats the whole mechanism**, and it's the most common reason rotation "breaks the app" (A10.21).

The better answers where available: **IAM authentication** (DB13.4) removes the password entirely, so there's nothing to rotate; **certificate-based auth** shifts the problem to certificate lifecycle (A10.18). **The best credential is the one that doesn't exist.**

The operational details: the rotation function needs network reachability to both the database and the secret store (a Lambda in the VPC with the right security groups and endpoints, A3.3); and **alert on rotation failure**, because a silently failing rotation means credentials that haven't changed in a year while a dashboard says they have.

**DB13.4 — IAM or certificate-based auth instead of passwords**

**IAM database authentication** (RDS): the client requests a **short-lived token** (15 minutes) from AWS using its IAM identity, and presents it as the password.

```python
token = rds_client.generate_db_auth_token(
    DBHostname=host, Port=5432, DBUsername='payments_app')
conn = psycopg.connect(host=host, user='payments_app', password=token, sslmode='verify-full')
```

**The benefits:**

- **No password exists.** Nothing to store, rotate (DB13.3), or leak.
- **The database identity is the workload's cloud identity** — an instance profile (A2.6), IRSA, or Pod Identity (A2.7) — so access is governed by IAM policy alongside everything else.
- **Revocation is an IAM change**, immediate and central.
- **CloudTrail records token generation** (A9.5), so there's an audit trail in the same place as everything else.
- **TLS is mandatory**, so encryption in transit is enforced by construction (DB13.5).

**The constraints to name:**

- **Connection rate limits** — IAM auth has a lower connections-per-second ceiling than password auth, which makes it a poor fit for a workload creating connections rapidly. **A connection pooler largely resolves this** (DB8.2) by keeping connections long-lived, and RDS Proxy handles the token generation itself.
- **The token expires in 15 minutes**, so it's obtained per connection, not per query — fine with pooling, awkward without.
- **Not supported by every engine or every client library.**

**Certificate-based auth** (mTLS) is the equivalent for self-managed: the client presents a certificate and the DN maps to a role. Strong, and **the certificate lifecycle becomes the operational burden** (A10.18) — issuance, distribution, rotation, and the fact that expiry is an outage.

The recommendation: **IAM auth where the engine and workload support it** — it's the same argument as removing long-lived access keys (A1.4, A2.8).

**DB13.5 — Enforcing encryption in transit and verifying it**

**Enforcing:**

```sql
-- Postgres pg_hba.conf: hostssl only, no plain host entries
hostssl  all  all  0.0.0.0/0  scram-sha-256
```

```sql
-- MySQL: require TLS per user
ALTER USER 'payments_app'@'%' REQUIRE SSL;
-- or globally
SET GLOBAL require_secure_transport = ON;
```

On RDS, the parameter is **`rds.force_ssl = 1`** (Postgres) — which **requires a reboot**, so it's a planned change.

**The client side is where it actually breaks down**, and this is the substance of the item:

- **`sslmode=require` encrypts but does not verify the server's certificate** — so it's vulnerable to a man-in-the-middle. **`sslmode=verify-full` is the only setting that both encrypts and authenticates the server**, and it requires the CA bundle. **Most connection strings say `require`**, and people believe they have TLS in the meaningful sense when they have encryption without authentication.
- **The RDS CA bundle must be distributed** to clients, and **CA rotation is a scheduled event** that breaks `verify-full` clients if they haven't updated — a real and recurring operational task.

**Verifying it's actually on:**

```sql
-- Postgres: per-connection TLS status
SELECT datname, usename, application_name, client_addr, ssl, version, cipher
FROM pg_stat_ssl JOIN pg_stat_activity USING (pid);

-- find anything connected without TLS
SELECT count(*) FROM pg_stat_ssl WHERE NOT ssl;
```

**That query is the answer to "prove it's on"** — configuration says what should happen; `pg_stat_ssl` says what is happening. **Alert on any non-TLS connection**, and treat a non-zero count as a finding (A10.31's "evidence generated continuously" argument).

**DB13.6 — Encryption at rest and what it protects against**

Provided by the storage layer — encrypted EBS volumes, RDS's KMS integration (A10.1), or filesystem encryption. Transparent to the database and the application.

**What it protects against**: physical media theft or improper disposal; unauthorised access to a snapshot, a backup file, or the underlying volume; and it satisfies a near-universal compliance control.

**What it does not protect against**, which is the point:

- **Anyone with database access.** The engine decrypts transparently, so a user with `SELECT` gets plaintext. **Encryption at rest is invisible to the entire application and authorisation layer.**
- **A compromised host** — root on the instance reads decrypted data.
- **A DBA or cloud operator** with legitimate access.
- **SQL injection** (DB13.7).
- **Data in memory** — the buffer cache is unencrypted.

So it protects against media-level threats and nothing above them. **If the requirement is that a privileged operator cannot read specific data, you need application-level or column-level encryption** — where the application encrypts before storing and holds the key elsewhere. The costs of that: **you cannot index, search, sort, or join on the encrypted column**, key management becomes yours, and rotation means re-encrypting the data (A10.12). **Deterministic encryption allows equality matching at the cost of leaking value distribution.**

The practical detail worth adding: **RDS encryption must be enabled at creation and cannot be added to an existing unencrypted instance** — the migration is snapshot, copy-with-encryption, restore, cut over (A10.12). Which makes it a decision to get right at provisioning, and a project afterwards.

**DB13.7 — SQL injection and parameterisation**

**The mechanism**: user input concatenated into a SQL string is parsed as SQL, so input becomes code.

```python
# vulnerable
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")
# email = "x' OR '1'='1" → returns every user
# email = "x'; DROP TABLE users; --" → if permissions allow (DB13.1)

# safe — parameterised
cur.execute("SELECT * FROM users WHERE email = %s", (email,))
```

**Why parameterisation works, precisely**: the SQL statement and the parameters are sent **separately**. The database parses and plans the statement with placeholders, then binds the values. **A value can never be interpreted as SQL syntax, because parsing has already happened.** It is not escaping — escaping is a filter that can be bypassed; parameterisation is a structural separation that cannot.

The cases where parameterisation doesn't apply and care is needed:

- **Identifiers** — table and column names cannot be parameterised. **Use an allow-list**, never string interpolation.
- **`ORDER BY` direction and sort columns** — same, allow-list.
- **`LIMIT` in some drivers** — usually parameterisable, check.
- **Dynamic `IN` lists** — use an array parameter (`= ANY($1)`) rather than building a list.
- **Stored procedures with dynamic SQL** are vulnerable internally if they concatenate.
- **ORMs are safe for normal use and vulnerable in raw-SQL escape hatches** — which is where injection appears in modern codebases.

**The defence in depth that matters for a platform engineer**: **least privilege** (DB13.1) — an application role without DDL cannot drop tables even with a successful injection, and one without superuser cannot execute code on the host (DB13.2). **That containment is what turns a catastrophic injection into a serious one**, and it's the layer platform teams own.

**DB13.8 — Audit logging and what to capture**

**What to capture, prioritised:**

- **Authentication events** — successful and failed logins, with source address and username. **Failed logins are a reconnaissance signal.**
- **DDL** — every schema change, with who and when. **This is what tells you who dropped the table** (DB6.6).
- **Privilege changes** — grants, revokes, role creation. **The highest-value category for detecting compromise.**
- **Access to sensitive tables** — reads of PII or financial data, which is frequently a regulatory requirement.
- **Bulk operations** — large `DELETE`/`UPDATE`, and `COPY`/exports, which are the exfiltration signature.
- **Superuser and administrative actions** (DB13.2).
- **Connections from unexpected sources.**

The mechanisms: **`pgaudit`** for Postgres (session and object-level auditing with far better granularity than `log_statement`); `log_statement = 'ddl'` as a lightweight minimum; **MySQL's audit plugin**; and **RDS integration** shipping to CloudWatch Logs.

The operational realities:

- **Volume.** Full statement logging on a busy database is enormous and expensive (O4.7). **Be selective** — DDL, privilege changes, and sensitive-object access, not every `SELECT`.
- **Performance impact** — logging is synchronous in some configurations and adds latency.
- **Ship it off the database host** (A1.16) — an audit log a compromised administrator can delete is not an audit log. **This is the control that makes it meaningful.**
- **Never log parameter values for sensitive statements**, or the audit log becomes a plaintext store of the data it audits (O4.9).
- **Retention** per compliance (DB6.8).

The gap to be honest about: **database audit logs tell you what a *role* did, not which person** — because applications connect as a service role. **Attributing to a human requires the application to propagate identity**, typically via `SET application_name` or a session variable per request. Without that, the audit trail stops at "the payments application did it".

**DB13.9 — Handling PII: masking, non-production data, retention**

**The three problems and their answers:**

**Non-production data** (DB13.10): **never copy production data to a lower environment unmasked.** The options: **generated synthetic data** (safest, and it takes real effort to make representative — DB2.9's point about realistic distributions); **masked/anonymised copies** — a restore with a transformation applied before the data is accessible; and **subsetting** — a referentially-consistent slice, which is smaller and faster to refresh.

The masking techniques: **substitution** (replace with realistic fake values — the best for usability), **redaction**, **hashing** (deterministic, so joins still work, and it's reversible by brute force for low-cardinality values like national IDs), **shuffling** within a column, and **generalisation** (a birth year instead of a date). **Referential consistency must be preserved** or the data is useless for testing.

**In production**: **column-level encryption** for the most sensitive fields (DB13.6); **row-level security** for tenant isolation; **dynamic masking** so a support role sees a redacted view of a column while the application sees the full value — implemented as a view plus permissions; and **minimise collection** — the data you don't hold needs no protection.

**Retention and erasure**: **a documented retention policy per data category**; **purge or archive on schedule** (DB9.7); and **GDPR erasure**, which is genuinely hard because personal data spreads — into backups (DB6.8), replicas, analytics warehouses, logs (O4.9), caches (DB11), and event streams (M11.5). **The answer is knowing where it went**, which requires a data inventory, and **crypto-shredding** where deletion from an immutable store isn't possible.

**DB13.10 — Production data in staging as a serious risk**

**Why it happens**: it's the fastest way to get realistic test data, it makes performance testing meaningful (DB2.9), and it's what people have always done.

**Why it's a serious risk:**

- **Lower environments have weaker controls, by design and by neglect** — broader access (often the whole engineering team), weaker network restrictions, less monitoring, no audit logging, older patches, and credentials shared more freely. **The data is identical; the protection is not.**
- **The blast radius is the same as a production breach.** A regulator does not distinguish between customer data leaked from production and the same data leaked from staging, and neither does a customer.
- **Access is much wider** — contractors, new joiners, and anyone with a laptop, rather than a controlled production access path.
- **It's copied onward** — a developer restores it locally, a subset ends up in a test fixture, someone shares a dump.
- **GDPR applies to it** (DB13.9) — including erasure requests, which nobody applies to staging.
- **Emails and notifications** can be sent to real customers from a test environment. **This happens, and it's an incident.**

**The resolution**: **mask on the way out** (DB13.9), as part of the restore pipeline, so an unmasked copy never exists outside production. **Automate it** so the easy path is the safe one — if masking is a manual step, it will be skipped. **Restrict who can restore production backups.** And **detect it** — periodic scanning of lower environments for data patterns that look like real PII.

The framing for a fintech: **treat staging data as an in-scope system or make it genuinely not-production-data.** The middle position — production data in a lower environment with lower controls — is the one that fails an audit and causes the breach, and it's also the most common state.

---

## DB14. Judgement

**DB14.1 — Choosing a database for a stated workload**

The method: **derive from the workload's actual properties**, not from familiarity or fashion.

The questions to ask: **What are the access patterns** — key lookups, ad hoc queries, range scans, traversals? **What's the read/write ratio and absolute volume?** **What consistency does the business genuinely require?** **How relational is the data?** **What's the expected growth?** **What does the team know?** **What's the operational capacity?**

A worked answer:

> "For a payments ledger with strong consistency requirements, complex relationships between accounts, transactions, and reconciliation records, ad hoc regulatory reporting, and a write volume in the low thousands per second — **Postgres on RDS**. The volume is comfortably within a single primary's capacity, the transactional guarantees are non-negotiable for a ledger (DB1.6), the relational model fits the domain, and reporting needs ad hoc SQL. I'd add a read replica for reporting to isolate it from OLTP (DB1.4), and plan partitioning by month on the transactions table for retention (DB9.3).
>
> I'd rule out DynamoDB because the reporting requirement needs ad hoc queries it can't serve (DB10.1), and the relationship-heavy model would mean joins in application code. I'd rule out sharding for now because a single primary handles this volume with room, and sharding is a multi-quarter project with permanent overhead (DB9.4) — I'd want the growth curve to show a ceiling before committing."

**The elements that make it strong**: the workload properties drive the choice; the rejected alternatives are named with reasons; the operational plan is included; and **the scaling decision is deferred with a stated trigger** rather than either ignored or over-engineered.

The general default worth stating: **Postgres unless there's a specific reason otherwise.** It handles relational, JSON (DB10.7), full-text (DB3.9), time-series (with Timescale), and geospatial competently — **and one well-understood database is operationally worth more than three specialised ones** (DB9.9).

**DB14.2 — Managed vs self-hosted**

**Managed** (RDS, Aurora, Cloud SQL): the provider handles provisioning, patching, backups, failover, monitoring integration, and replication setup. **You still own**: schema, queries, indexes, capacity, connection management, and the application's use of it — **which is most of what actually goes wrong** (A7, K1.10's parallel argument).

**Self-hosted**: full control over version, extensions, configuration, and placement. **You own everything**, including being on call for it.

**The argument for managed, which should be the default:**

- **The hard, high-consequence operations are done for you** — failover (DB5.4), backup and PITR (DB6.3), patching. **Getting failover and backup right is genuinely difficult and the failure modes are catastrophic**, so having someone else's engineering behind them is worth a great deal.
- **It's cheaper in total cost of ownership** for most organisations once engineering time is counted.
- **It's a supported product** with an SLA and someone to escalate to at 3am.
- **The premium is typically modest** relative to a DBA's salary.

**When self-hosting is justified:**

- **A specific extension or configuration** the managed service doesn't permit — the most common genuine reason.
- **Regulatory constraints** on data location or operator access.
- **Scale where the premium is very large** and you have a dedicated team.
- **A version or engine** not offered.
- **On-premises or air-gapped** environments.

The honest caution: **"managed" does not mean "not your problem"** (K1.10). You still need to understand replication, vacuum, connections, and query performance — and teams that adopt RDS believing it removes the need for database expertise discover otherwise during their first incident. **The expertise requirement shifts from operations to design and diagnosis; it doesn't disappear.**

**DB14.3 — Databases on Kubernetes, and when operators make it viable**

**The risks:**

- **Kubernetes is designed for disposable, rescheduled workloads** (K2.12); databases are the opposite. Every mechanism that makes Kubernetes good — rescheduling, node consolidation (K7.6), rolling updates — is a hazard for a stateful primary.
- **Storage is the hard part** — zonal persistent volumes pin pods to an AZ (K5.3), volume attachment failures are a real failure class (K5.9), and `Delete` reclaim policy can destroy data (K5.4).
- **A StatefulSet gives identity and storage, not high availability** (K2.8) — clustering, failover, and replication are the application's problem.
- **Force-deleting a pod on an unreachable node can produce two primaries** writing to the same data (K9.7) — the split-brain scenario (DB5.5) with a Kubernetes-specific trigger.
- **Performance overhead** from overlay networking and container storage, usually modest and non-zero.
- **The blast radius of a cluster-level mistake** now includes your database.

**When operators make it viable**: **CloudNativePG, Zalando's Postgres Operator, Crunchy PGO, Percona's operators, Vitess** for MySQL. A mature operator encodes the operational knowledge (K12.2): automated failover with proper fencing (DB5.5), backup and PITR to object storage (DB6.3), rolling minor upgrades, connection pooling, and monitoring.

**With a good operator, it's genuinely viable** — and the honest position is that **CloudNativePG in particular has made Postgres on Kubernetes a defensible choice**, which was not true a few years ago.

**When it's the right call**: on-premises or where no managed service exists; multi-cloud portability as a real requirement; a large number of small databases where the per-instance managed cost dominates; and where the team already operates Kubernetes well and has evaluated the operator seriously (K12.3).

**When it isn't**: a cloud with a good managed offering, a small team, and no specific driver — **use RDS.** The question to ask is "what does running this on Kubernetes give us that RDS doesn't", and if the answer is "consistency with how we run everything else", that's a preference, not a reason (DB14.2).

**DB14.4 — The platform team's responsibility boundary**

**The platform team provides:**

- **Provisioned, configured databases** with sensible defaults — encryption (DB13.6), TLS enforced (DB13.5), backups (DB6.2), multi-AZ (DB5.10), monitoring and alerting (DB12.2), parameter groups reviewed.
- **Backup and recovery capability**, tested (DB6.4), with a stated and evidenced RTO/RPO.
- **HA and failover**, tested (A11.8).
- **Connection infrastructure** — a pooler where needed (DB8.6).
- **Version upgrades and patching** (DB12.7), with a defined cadence and notice.
- **Capacity monitoring and forecasting** (DB12.8), and the conversation about scaling.
- **Security baseline** — roles, network isolation, audit logging, credential rotation (DB13).
- **Standard dashboards and the metrics** (DB12.1), so teams can self-diagnose.

**Application teams provide:**

- **Schema design and migrations** (DB7), written to be online-safe and reviewed.
- **Query performance** — their queries, their indexes, their N+1s (DB2.7).
- **Connection pool sizing** within the allocation they've been given (DB8.3).
- **Understanding their consistency requirements** and handling replica lag (DB5.3).
- **Data retention decisions** (DB9.7) and PII classification (DB13.9).
- **Responding to alerts about their queries.**

**The boundary that must be explicit**: **the platform team owns the database's availability; application teams own their use of it.** A slow query is the application team's problem; a failed failover is the platform's. **Ambiguity here is the most common source of the dysfunction where the platform team is paged for every slow query** and gradually becomes the bottleneck for all database work (K13.4).

The complication worth naming: **application teams frequently lack database expertise**, so a hard boundary leaves them unsupported. **The productive model is that the platform team provides the tooling, the guardrails, and consultation — reviewing migrations, providing query analysis dashboards, and being available for design input — while ownership of the query stays with the team that wrote it.**

**DB14.5 — A zero-downtime migration between engines or versions**

The general pattern:

1. **Assess** — schema compatibility, feature and extension differences, SQL dialect, data types, and the volume to move.
2. **Stand up the target** and migrate the schema, adjusting for dialect differences.
3. **Initial load** — bulk copy the data.
4. **Continuous replication** to keep the target current — **logical replication** for Postgres-to-Postgres (DB5.8), **AWS DMS with CDC** for cross-engine, or **Debezium** (M7.7).
5. **Validate** — row counts, checksums, and application-level consistency checks. **Run the application's read path against the target** while it's still a replica.
6. **Dual-write or shadow-read** for a period, comparing results — the highest-confidence approach.
7. **Cut over** — stop writes briefly (or use a proxy to pause them), confirm zero replication lag, switch the application's connection target, resume. **Seconds of write unavailability**, not minutes.
8. **Keep the source running** with reverse replication configured, so **rollback is repointing back** (TF9.7's "roll forward" caveat doesn't apply here if you've prepared this).
9. **Decommission** after a confidence period.

The hard parts to name honestly:

- **The cutover is the easy part; validation is the hard part.** Proving the target is correct across every access pattern is where the time goes.
- **Sequences and auto-increment values** must be synchronised at cutover or you get duplicate key errors immediately.
- **Cross-engine dialect differences** — data types, collation and sort order (which changes query results), transaction semantics (DB4.3), and functions. **Collation differences are a subtle one** that silently changes ordering and comparison behaviour.
- **DDL during migration** must be applied to both sides (DB5.8).
- **Performance characteristics differ** — plans and indexes that worked on the source may not on the target (DB2.9), so load testing the target matters.
- **Application code changes** for dialect differences, deployed and tested before the cutover.

**DB14.6 — Approaching an inherited database you don't understand**

The sequence, working from safe to invasive:

1. **Read-only first.** Get a read-only role (DB13.1) and change nothing.
2. **Inventory the structure** — tables, sizes, row counts, indexes, constraints, foreign keys, views, triggers, stored procedures, extensions. `\d+`, `pg_stat_user_tables`, and the size queries.
3. **Find what's actually used** — `pg_stat_user_tables` (sequential and index scans per table) reveals which tables are live and which are abandoned; `pg_stat_user_indexes` shows unused indexes (DB3.6). **Tables with zero scans over weeks are candidates for archiving or deletion**, and there are usually many.
4. **Find the workload** — `pg_stat_statements` by `total_exec_time` (DB2.8) tells you what the database actually spends its time on, which is the fastest route to understanding what it's *for*.
5. **Map the consumers** — `pg_stat_activity` grouped by `application_name` and `client_addr` shows who connects. **Frequently reveals connections nobody knew about** — a legacy job, an analyst's laptop, a decommissioned service still polling.
6. **Check the operational state** — backups running and restorable (DB6.5), replication healthy (DB5.2), vacuum keeping up (DB12.3), **transaction ID age** (DB12.4), disk headroom, and version support status.
7. **Check the security state** — superusers (DB13.2), roles and grants, TLS enforcement (DB13.5), and whether credentials have ever been rotated.
8. **Instrument it** (O16.5) — get the metrics and dashboards in place before changing anything.
9. **Then prioritise**, by risk: an unrestorable backup or imminent wraparound first; performance and cost second.

The realities: **the documentation is wrong or absent**; **the people who built it have left**; **there are tables nobody can explain, and deleting them is riskier than it looks** — the safe move is renaming and waiting (DB7.6); and **the highest-value early finding is usually operational** — a backup that has never been tested, a vacuum that hasn't run on a large table for months, or a version approaching end of support.

The framing: **establish that it's safe before making it better.** An inherited database's most likely serious problem is not performance — it's that nobody has verified it can be recovered (DB6.5).

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 129 items this is a large domain, and for a platform role you are not expected to answer all of it at DBA depth.
- **The sections that matter most for a platform engineer are DB5, DB6, DB7, DB8, and DB12** — replication and failover, backup and recovery, online migrations, connection exhaustion, and operations. **Those are the ones that cause incidents you own**, and they're where an interviewer for a platform role will concentrate.
- **DB2 and DB3 are worth being competent at rather than expert in.** Reading an execution plan, spotting a missing index, and recognising an N+1 is the bar — it's the difference between diagnosing "the database is slow" and escalating it.
- **DB14 and DB13.10 are the judgement items**, and DB14.3 (databases on Kubernetes) in particular is a question where a considered position with the operator caveat is a strong senior signal.
- **The failure modes are the part that reads as experience.** A `SELECT`-blocking `ACCESS EXCLUSIVE` queue from a "quick" ALTER (DB7.1), transaction ID wraparound shutting the database down (DB12.4), autoscaling pods exhausting connections (DB8.4), `sslmode=require` not verifying the certificate (DB13.5), a delayed replica as the cheapest recovery from an accidental `DROP` (DB6.6), and Redis evicting session data because it shares an instance with the cache (DB11.7).
- **Cross-references into AWS are dense in DB5, DB6, and DB8** — A7.1 for multi-AZ failover, A7.3 for backups and the final-snapshot trap, A7.8 for credential rotation, A10.12 for retrofitting encryption, and A11.1 for the RTO/RPO conversation that drives DB5.10.
