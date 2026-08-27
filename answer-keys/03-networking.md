# Networking — Answer Key

Companion to Domain 3 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*. Host-side commands are Linux L12; this key focuses on protocol reasoning and fault isolation.

---

## N1. Fundamentals

**N1.1 — The layers, and using them to locate a fault**

TCP/IP model, bottom up:

1. **Link** — Ethernet, MAC addresses, ARP. Same-segment delivery.
2. **Internet** — IP, routing, ICMP. Host-to-host across networks.
3. **Transport** — TCP/UDP, ports. Process-to-process.
4. **Application** — HTTP, DNS, TLS.

The reason to know it isn't recitation, it's triage. Each layer has a distinct failure signature: no ARP resolution is link; "no route to host" is internet; "connection refused" or timeout is transport; a 502 is application. Working bottom-up prevents you debugging application code when the security group is the problem.

**N1.2 — What happens when you type a URL**

Rough sequence, with the parts that actually break in bold:

1. Browser checks its cache, then **DNS resolution** (stub → resolver → root → TLD → authoritative), honouring TTLs at each cache.
2. Routing decision: is the IP local or via the default gateway. ARP for the next hop's MAC.
3. **TCP three-way handshake** to port 443.
4. **TLS handshake** — ClientHello with SNI, server cert, chain validation, key exchange.
5. HTTP request sent; likely traverses a load balancer, which may terminate TLS and open a separate connection to a backend.
6. Response returns; browser renders and fetches sub-resources, reusing connections.

A good answer names where latency accrues (DNS, TCP RTT, TLS RTTs, server time) because that maps directly to `curl -w` timing breakdown (N6.2).

**N1.3 — Encapsulation**

Each layer wraps the one above with its own header. Application data → TCP segment (ports, sequence numbers) → IP packet (source/destination IP, TTL) → Ethernet frame (MAC addresses, FCS). Each hop strips the frame, examines the IP header, decrements TTL, and re-frames for the next link. Source and destination *IP* stay constant end to end (absent NAT); source and destination *MAC* change at every hop.

**N1.4 — MAC vs IP**

MAC is a layer-2 hardware address, flat and non-routable, meaningful only within a broadcast domain. IP is a layer-3 logical address, hierarchical, routable globally. IP gets a packet to the right network; MAC gets a frame to the right device on that network. Both are needed at every hop.

**N1.5 — ARP**

Maps an IP to a MAC on the local segment: "who has 10.0.1.5?" broadcast, unicast reply, cached. `ip neigh` shows the table.

When it matters operationally: a stale ARP entry after a failover (the IP moved to a new MAC) causes traffic to blackhole until the cache expires — which is why gratuitous ARP is sent on VIP failover. Also relevant to duplicate-IP problems, where the ARP table flaps between two MACs.

**N1.6 — MTU and PMTU blackholes**

MTU is the largest frame a link accepts, typically 1500 bytes on Ethernet. Encapsulation (VPN, VXLAN, GRE) reduces the usable payload. If a packet exceeds the path MTU and has the Don't Fragment bit set, the router sends ICMP "fragmentation needed" so the sender reduces its segment size.

The failure mode: something filters ICMP, the sender never learns, and large packets vanish while small ones succeed. Signature is distinctive — the TCP handshake works, small requests work, and anything above a certain size hangs. Test with `ping -M do -s 1472 <host>` stepping the size down. Fixes: MSS clamping, lowering the interface MTU, or allowing ICMP type 3 code 4. "SSH connects then freezes on a large output" is the classic report.

---

## N2. Addressing & subnetting

**N2.1 — CIDR and usable ranges**

`/24` = 256 addresses, `10.0.1.0` – `10.0.1.255`. Network address at the bottom, broadcast at the top, so 254 usable on a normal LAN. The prefix is the number of fixed bits; host bits = 32 − prefix; addresses = 2^host bits.

Quick table worth having memorised:

| CIDR | Addresses | Mask |
|---|---|---|
| /16 | 65,536 | 255.255.0.0 |
| /20 | 4,096 | 255.255.240.0 |
| /24 | 256 | 255.255.255.0 |
| /26 | 64 | 255.255.255.192 |
| /28 | 16 | 255.255.255.240 |
| /30 | 4 | 255.255.255.252 |

**N2.2 — Subnetting by hand**

Method: work in the octet where the prefix falls. Block size = 256 − that octet's mask value. Networks start at multiples of the block size.

Example: split `10.0.0.0/22` into `/24`s. `/22` is 1,024 addresses. Third octet block size for `/22` is 4, so the range is `10.0.0.0`–`10.0.3.255`. The four `/24`s are `10.0.0.0/24`, `10.0.1.0/24`, `10.0.2.0/24`, `10.0.3.0/24`.

Example: `192.168.1.0/26`. Block size = 256 − 192 = 64. Subnets at `.0`, `.64`, `.128`, `.192`. For `192.168.1.100`: it falls in the `.64` block, so network `192.168.1.64`, broadcast `192.168.1.127`, usable `.65`–`.126`.

**N2.3 — RFC1918 ranges**

- `10.0.0.0/8` — 10.0.0.0 to 10.255.255.255
- `172.16.0.0/12` — 172.16.0.0 to 172.31.255.255 (note: not the whole 172.x)
- `192.168.0.0/16` — 192.168.0.0 to 192.168.255.255

Also worth knowing: `169.254.0.0/16` link-local, which is where the cloud instance metadata endpoint `169.254.169.254` lives, and `127.0.0.0/8` loopback. `100.64.0.0/10` is carrier-grade NAT and shows up in some managed services.

**N2.4 — Splitting a VPC across AZs**

Take a `/16` (65,536 addresses). Typical layout across three AZs:

- Public subnets: `/24` each — small, only load balancers and NAT gateways live here.
- Private app subnets: `/20` each — the bulk of workloads, especially with EKS where every pod takes an IP.
- Private data subnets: `/24` each.

Leave contiguous unallocated space for growth. The mistake people make is sizing private subnets too small for Kubernetes: with the VPC CNI, pod density is bounded by available IPs, and a `/24` per AZ runs out fast.

**N2.5 — Overlapping CIDRs**

Two networks with overlapping ranges can't route to each other — the routing table has no way to distinguish "my 10.0.0.0/16" from "their 10.0.0.0/16". VPC peering and Transit Gateway attachments simply refuse overlapping CIDRs.

Options: re-IP one side (correct, expensive), NAT one side behind a non-overlapping range, or use PrivateLink to expose specific services rather than routing whole networks. The real answer is prevention — central IP address management before anyone provisions, which is what IPAM (A3.9) exists for.

**N2.6 — AWS reserving five addresses per subnet**

In every subnet: `.0` network address, `.1` VPC router, `.2` DNS (the Amazon-provided resolver, also at the VPC base +2), `.3` reserved for future use, and the last address for broadcast (reserved even though VPC doesn't support broadcast). So a `/28` gives 11 usable, not 16 — which matters when sizing small subnets.

**N2.7 — IPv6 basics**

128-bit, written as eight hex groups, with `::` collapsing one run of zeros: `2001:db8::1`. No NAT by design — every host can have a globally routable address. `/64` is the standard subnet size regardless of host count. Link-local addresses (`fe80::/10`) are always present.

Dual-stack implications: happy-eyeballs means clients may prefer IPv6 and fail over silently, so a misconfigured AAAA record produces intermittent slowness rather than a clean failure. Security groups and firewall rules must be written for both families — allowing IPv4 only and forgetting IPv6 is a real exposure.

---

## N3. Routing & switching

**N3.1 — Reading a routing table and predicting the winner**

```bash
ip route
ip route get 10.0.5.20     # ask the kernel directly
```

Selection is by longest prefix match first, then metric as a tiebreaker. `ip route get` is the answer to "which route will actually be used" — far more reliable than reading the table and reasoning about it.

**N3.2 — Longest prefix match**

Given `10.0.0.0/8`, `10.0.5.0/24`, and `0.0.0.0/0`, a packet to `10.0.5.20` uses the `/24` — the most specific match wins regardless of table order. This is why a specific route can override a default route, and why adding a `/32` is a valid surgical fix.

**N3.3 — Default gateway and `0.0.0.0/0`**

`0.0.0.0/0` matches everything, so it's the least specific route and therefore the last resort. It points at the gateway that handles anything not on a known network. In AWS, a public subnet is defined precisely by having a `0.0.0.0/0` route to an internet gateway; a private subnet routes it to a NAT gateway instead.

**N3.4 — NAT, SNAT, DNAT**

NAT rewrites addresses in the packet header and tracks the translation in a state table so replies can be reversed.

- **SNAT** (source NAT) — rewrites the source address on egress. Many private hosts share one public IP. This is what a NAT gateway does.
- **DNAT** (destination NAT) — rewrites the destination on ingress. Port forwarding, and what publishing a container port does.

Because NAT is stateful, idle connections get evicted from the table — which is why long-lived idle connections die behind a NAT gateway and why TCP keepalives matter (N5.5).

**N3.5 — Public vs private, and how a private host reaches the internet**

Private (RFC1918) addresses aren't routable on the internet. A private host reaching out sends to the default gateway; a NAT device SNATs the source to a public IP, records the mapping, forwards it, and reverses the translation on the reply. Inbound-initiated connections can't work without an explicit DNAT rule — which is the security property people rely on.

**N3.6 — traceroute and mtr**

```bash
traceroute -T -p 443 host    # TCP mode, more likely to get through
mtr host                     # continuous, shows loss per hop
```

Works by sending packets with incrementing TTL; each hop that decrements TTL to zero returns ICMP time-exceeded, revealing itself. `mtr` is better for intermittent problems because it samples continuously and shows per-hop loss.

**N3.7 — Gaps in traceroute output, without concluding it's broken**

Stars mean a hop didn't reply to the probe — usually because it deprioritises or blocks ICMP, not because traffic is failing. Two rules for reading it:

- **Loss at an intermediate hop that doesn't persist to the end is not real.** Routers rate-limit their own ICMP responses; forwarded traffic is unaffected.
- **Only loss that continues to the final hop is meaningful.**

Also, the return path may differ from the forward path and isn't visible, so asymmetric problems are invisible to traceroute.

**N3.8 — VLANs and broadcast domains**

A VLAN partitions a physical switch into separate logical layer-2 segments. Each VLAN is its own broadcast domain; traffic between VLANs must be routed. The purpose is isolation and limiting broadcast scope. In cloud terms, subnets play a similar role, and the VPC router handles inter-subnet traffic implicitly.

**N3.9 — Asymmetric routing and stateful firewalls**

Traffic leaves via one path and returns via another. Pure routing tolerates this; **stateful firewalls don't** — the return path's firewall never saw the outbound SYN, has no state entry, and drops the reply.

Signature: connections that establish in one direction only, or that work until a topology change. Common with multiple gateways, VPN plus direct-connect setups, or multi-homed hosts. Relevant to AWS: security groups are stateful (so return traffic is implicitly allowed), NACLs are stateless (so you must allow ephemeral return ports explicitly) — that difference is a frequent source of confusion (N10.1).

---

## N4. DNS

**N4.1 — Resolution end to end**

1. Application calls the **stub resolver** (the OS, per `/etc/nsswitch.conf` — `/etc/hosts` first).
2. Stub queries the configured **recursive resolver**.
3. If uncached, the recursive queries a **root** server → referral to the TLD servers.
4. Queries the **TLD** server (`.com`) → referral to the domain's authoritative nameservers.
5. Queries the **authoritative** server → the actual answer.
6. Caches at every level for the record's TTL, then returns.

The key structural point: the recursive resolver does the walking; the client makes one query. And caching happens at multiple independent layers, which is why changes propagate unevenly.

**N4.2 — `dig` and its sections**

```bash
dig example.com
dig +short example.com
dig +trace example.com        # walk the delegation yourself
```

- **QUESTION** — what was asked.
- **ANSWER** — the records returned. This is what you usually want.
- **AUTHORITY** — the nameservers responsible for the zone.
- **ADDITIONAL** — glue records, typically IPs for those nameservers.

`status: NOERROR` with an empty answer means the name exists but has no record of that type. `NXDOMAIN` means the name doesn't exist. That distinction matters — NXDOMAIN gets negatively cached (N4.7).

**N4.3 — Querying a specific nameserver**

```bash
dig @ns1.example.com example.com
dig @8.8.8.8 example.com
dig @169.254.169.253 internal.example.com     # AWS VPC resolver
```

Comparing the authoritative answer against a resolver's answer immediately distinguishes "the record is wrong" from "the record is right but something is serving stale data." First move in most DNS incidents.

**N4.4 — Record types**

- **A** / **AAAA** — name to IPv4 / IPv6.
- **CNAME** — alias to another name. Cannot coexist with other records at the same name.
- **ALIAS**/**ANAME** (provider-specific, e.g. Route53 alias) — CNAME-like behaviour that *is* allowed at the apex.
- **MX** — mail exchangers, with priority.
- **TXT** — arbitrary text; SPF, DKIM, DMARC, domain verification.
- **NS** — delegation to authoritative nameservers.
- **SRV** — service location with port and priority; used by service discovery and Kubernetes.
- **CAA** — restricts which CAs may issue certificates for the domain.
- **PTR** — reverse lookup.

**N4.5 — CNAME at the apex**

A CNAME says "this name is an alias for that name," and the RFCs forbid any other record existing alongside it. The apex (`example.com`) must have NS and SOA records, so a CNAME there is illegal.

The workaround is provider-specific: Route53 **alias records** resolve to the target's IPs at query time and are returned as A records, so the restriction doesn't apply. Cloudflare calls it CNAME flattening. Alias records are also free of charge in Route53 and health-check aware, so they're preferred over CNAMEs for AWS targets generally (A8.2).

**N4.6 — TTL and cutover planning**

TTL is how long a resolver may cache the record. Planning a change:

1. **Lower the TTL** (say to 60s) well in advance — at least the *current* TTL beforehand, so every cached copy of the old high TTL has expired.
2. Wait for the old TTL to fully elapse.
3. Make the change. Propagation now takes ~60s.
4. Verify, then restore a normal TTL.

Skipping step 1 is the classic mistake — you change the record and then wait out the old 24-hour TTL you didn't lower in time.

**N4.7 — Stale DNS**

Layers to check, in order:

- **Negative caching** — NXDOMAIN responses are cached per the SOA's minimum field. Creating a record after someone queried it produces a delay that isn't explained by the record's own TTL.
- **Resolver cache** — the recursive resolver may hold it; some ignore low TTLs and enforce a minimum.
- **OS cache** — `systemd-resolved`, `nscd`.
- **Application cache** — see N4.9.

Verify by querying authoritative directly (N4.3) and comparing.

**N4.8 — Split-horizon / private DNS**

The same name resolves differently depending on where the query comes from — internal clients get a private IP, external clients get a public one. Implemented in AWS with Route53 private hosted zones associated to a VPC.

Why you'd want it: internal traffic stays internal rather than hairpinning out to a public endpoint and back, and you can expose internal-only names. Complication: hybrid environments need Route53 Resolver endpoints so on-prem can resolve VPC names and vice versa (A3.14).

**N4.9 — Runtime DNS caching past TTL**

The JVM historically cached successful lookups **forever** (`networkaddress.cache.ttl` defaulting to -1 when a security manager was installed). Result: after a failover changes an IP, the application keeps connecting to the dead address indefinitely while `dig` shows the correct answer.

Same class of problem appears with connection pools that resolve once at startup, and with HTTP clients that reuse connections. This is a genuinely common outage cause and naming it is a strong signal. Fix by setting the JVM TTL explicitly (e.g. 30s), or by not relying on DNS for failover at all.

**N4.10 — Health-check-based failover routing**

Route53 health checks probe an endpoint; a failover routing policy returns the secondary record when the primary is unhealthy. Configure with a primary and secondary record set, each associated with a health check.

Limits worth stating: it's bounded by TTL and by client caching (N4.9), so it's a coarse tool — minutes, not seconds. It's appropriate for regional failover, not for in-region load balancing, where a load balancer's own health checks act far faster.

---

## N5. Transport layer

**N5.1 — Three-way handshake and teardown**

Handshake: client SYN → server SYN-ACK → client ACK. Three packets, one full RTT before any data flows — which is why connection reuse matters for latency.

Teardown: FIN → ACK → FIN → ACK, each direction closing independently. The side that closes first enters TIME_WAIT.

**N5.2 — Refused vs timeout vs reset**

The single most useful diagnostic distinction in networking:

- **Connection refused** — a RST came back. Something reachable answered and said no. The host is up and routing works; nothing is listening on that port, or a firewall is configured to reject rather than drop.
- **Timeout** — nothing came back at all. Packet dropped silently: security group, NACL, firewall DROP rule, wrong route, or the host is down.
- **Connection reset (mid-connection)** — the connection was established and then torn down abruptly. Application crashed, idle timeout on a middlebox, or a load balancer dropping the backend.

**N5.3 — What each tells you about the fault's location**

Refused means you reached the destination host — so investigate the *service*: is it running, is it bound to the right interface (`ss -tulpn`), right port.

Timeout means you probably didn't reach it — so investigate the *path*: security groups, NACLs, routing, the host being down. Timeouts are network-layer until proven otherwise; refusals are service-layer.

That inference is what makes this pair worth memorising — it halves the search space immediately.

**N5.4 — TCP states, TIME_WAIT and CLOSE_WAIT**

- **TIME_WAIT** — the side that closed first waits 2×MSL (typically 60s) to absorb stray packets. **Normal.** Thousands on a busy client or proxy is expected, not a bug. It only becomes a problem when it exhausts ephemeral ports (N5.6).
- **CLOSE_WAIT** — the peer sent FIN and *your application hasn't called close()*. This is **an application bug**, essentially always. A growing CLOSE_WAIT count means a file descriptor leak, and the process will eventually hit its fd limit.

The distinction is the point: TIME_WAIT accumulating is the kernel doing its job; CLOSE_WAIT accumulating is code that isn't closing sockets.

**N5.5 — Keepalives and idle connections dying**

NAT devices and load balancers evict idle flows from their state tables (AWS NAT gateway: 350 seconds; ELB idle timeout: 60s by default). When the client later sends on that connection, the middlebox has no state and drops or resets it.

Symptom: a connection that works, sits idle, then fails on next use — very common with database connection pools and long-lived RPC channels. Fix: enable TCP keepalives with an interval *below* the shortest idle timeout on the path, or set the pool to recycle idle connections proactively. Note Linux defaults are far too long (`tcp_keepalive_time` is 7200s) to help by default.

**N5.6 — Ephemeral port exhaustion**

Outbound connections need a source port from the ephemeral range (`net.ipv4.ip_local_port_range`, typically ~28k ports). A host making many short-lived outbound connections to the *same* destination IP and port can exhaust the tuple space, especially with connections sitting in TIME_WAIT.

Signs: `EADDRNOTAVAIL`, connection failures under load with no server-side errors, high TIME_WAIT count. Mitigations: connection pooling and reuse (the real fix), widening the port range, `tcp_tw_reuse`, or spreading across more destination IPs. In AWS, a NAT gateway has a hard limit of ~55,000 simultaneous connections per destination.

**N5.7 — When UDP is right, and what you give up**

Right for: DNS, real-time media, metrics/telemetry (StatsD), QUIC's foundation, and anything where a late packet is worse than a lost one.

You give up: delivery guarantee, ordering, congestion control, and connection state. Any of those you still need must be reimplemented in the application — which is what QUIC does. UDP also fares worse through NAT and stateful firewalls, since there's no connection to track.

**N5.8 — Testing a specific port**

```bash
nc -zv host 5432
timeout 3 bash -c '</dev/tcp/host/5432' && echo open
curl -v telnet://host:5432
```

The `/dev/tcp` form is useful on minimal containers with no tooling installed. Interpret the result via N5.2 — the *way* it fails is the information.

**N5.9 — Backlog and the accept queue**

Two queues: the SYN queue (half-open, handshake in progress) and the accept queue (established, waiting for the application to `accept()`). `listen(backlog)` and `net.core.somaxconn` bound the accept queue.

When the accept queue fills — because the application is too slow to accept — new connections are dropped or reset depending on `tcp_abort_on_overflow`. Symptom is intermittent connection failures under load with the server looking healthy. Check with `ss -lnt` (the `Send-Q` column on a listening socket is the backlog limit, `Recv-Q` the current queue depth) and `netstat -s | grep -i listen` for overflow counters.

---

## N6. HTTP & the application layer

**N6.1 — `curl -v`**

```bash
curl -v https://example.com
```

Output convention: `*` is curl's own commentary (DNS, connection, TLS), `>` is the request it sent, `<` is the response. You get the resolved IP, the TLS version and cipher, certificate details, every request and response header, and the status line. `-I` for headers only (issues HEAD), `-L` to follow redirects, `--resolve host:443:1.2.3.4` to test a specific backend without changing DNS.

**N6.2 — Timing breakdown**

```bash
curl -w "dns:%{time_namelookup} connect:%{time_connect} tls:%{time_appconnect} ttfb:%{time_starttransfer} total:%{time_total}\n" -o /dev/null -s https://example.com
```

Cumulative values, so subtract to get each phase. Interpretation:

- Large `time_namelookup` → DNS problem.
- Large `time_connect` − `namelookup` → network latency or SYN retransmits.
- Large `time_appconnect` − `connect` → TLS handshake cost (extra RTTs, cert chain fetching, OCSP).
- Large `time_starttransfer` − `appconnect` → **server-side processing**. This is the one that means "it's the application, not the network."

This single command settles most "is it the network or the app" arguments.

**N6.3 — Status codes, and 502 vs 503 vs 504**

4xx is the client's fault, 5xx is the server's — which matters for ownership. The three that get confused, all emitted by a proxy or load balancer:

- **502 Bad Gateway** — the upstream returned something invalid, or the connection to it failed/reset. Backend is reachable but broken.
- **503 Service Unavailable** — no healthy upstream to send to, or the proxy is deliberately shedding load. Typically *no backends passing health checks*.
- **504 Gateway Timeout** — the upstream accepted the connection but didn't respond in time. Backend is alive but too slow.

So: 502 = broken backend, 503 = no backend, 504 = slow backend. Also worth knowing 499 (nginx: client closed the connection first) and 429 (rate limited).

**N6.4 — Headers that matter**

- **Host** — required in HTTP/1.1; how one IP serves many sites.
- **Content-Type** — how to interpret the body; wrong values cause silent parsing failures.
- **Authorization** — credentials; must never be logged.
- **Cache-Control** — caching policy for browsers and CDNs; `no-store` vs `no-cache` differ meaningfully.
- **X-Forwarded-For / X-Forwarded-Proto** — original client IP and scheme through proxies. Only trustworthy if every hop is trusted, since clients can forge them.
- **Connection / Keep-Alive** — connection reuse.
- **Retry-After** — accompanies 429/503, tells clients when to come back.

**N6.5 — Keep-alive, reuse, and pooling**

HTTP/1.1 defaults to persistent connections, so multiple requests share one TCP (and TLS) connection, avoiding the handshake cost each time. Clients pool these. Issues to know: pools sized too small serialise requests; pools too large exhaust server connections; and idle pooled connections die to middlebox timeouts (N5.5), producing intermittent errors on first use after idle.

**N6.6 — HTTP/2 and HTTP/3**

**HTTP/2**: binary framing, multiplexing many streams over one TCP connection (eliminating head-of-line blocking *at the HTTP layer*), header compression (HPACK), server push (now largely deprecated). Practical effect: far fewer connections, so domain sharding became an anti-pattern.

**HTTP/3**: runs over QUIC on UDP. Solves TCP-level head-of-line blocking (in HTTP/2 a lost TCP segment stalls all streams), integrates TLS 1.3 into the handshake for fewer round trips, and supports connection migration across network changes. Operational consequence: it needs UDP/443 open, and traditional TCP-based middleboxes and packet captures don't see it the same way.

**N6.7 — CORS, enough to debug it**

A browser-enforced policy. When JavaScript on origin A calls origin B, the browser requires B to opt in via `Access-Control-Allow-Origin`. For non-simple requests the browser first sends an `OPTIONS` **preflight** and checks `Allow-Methods` and `Allow-Headers`.

Debugging notes: it is *browser-only* — `curl` succeeds while the browser fails, which confuses people. The fix belongs on the **server** (B), not the client. Credentialed requests can't use `Allow-Origin: *`. And a failed preflight often shows as a generic network error in the console rather than a clear CORS message.

**N6.8 — Idempotency and safe retries**

- **Safe** — no side effects: GET, HEAD, OPTIONS.
- **Idempotent** — repeating produces the same state: GET, PUT, DELETE, HEAD.
- **Neither** — POST, PATCH.

So a proxy or client may safely retry GET/PUT/DELETE on a timeout, but retrying POST risks duplicate creation. The mitigation is an idempotency key that the server deduplicates on. Relevant because load balancers and service meshes retry by default, and enabling retries on non-idempotent endpoints causes duplicate charges and records.

**N6.9 — Websockets through a proxy**

A websocket starts as an HTTP request with `Upgrade: websocket` and `Connection: Upgrade`, then the connection becomes bidirectional. Things that break it:

- Proxies that don't forward the Upgrade headers, or that are configured for HTTP/1.0.
- **Idle timeouts** — the connection is long-lived and often quiet; an LB idle timeout of 60s kills it. Fix with application-level pings or a longer timeout.
- Load balancers without sticky routing sending frames to different backends.
- Buffering proxies that hold data rather than streaming.

Check the response is `101 Switching Protocols`; anything else means the upgrade never happened.

---

## N7. TLS & certificates

**N7.1 — The handshake, for debugging purposes**

TLS 1.2: ClientHello (versions, cipher suites, **SNI**) → ServerHello (chosen cipher) + Certificate + key exchange → client validates the chain, both derive session keys → Finished. Two round trips.

TLS 1.3: cut to one round trip, with a smaller cipher suite list and forward secrecy mandatory.

What breaks where: no shared cipher/version → handshake failure at ServerHello; wrong SNI → wrong certificate returned; chain problems → failure at client validation. Knowing which stage failed narrows it immediately.

**N7.2 — Inspecting a live endpoint**

```bash
openssl s_client -connect example.com:443 -servername example.com
openssl s_client -connect example.com:443 -servername example.com -showcerts
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates -subject -issuer
```

`-servername` is essential — without it, no SNI is sent and you may get the default certificate rather than the one you meant to check. `-showcerts` dumps the whole chain the server presented, which is how you diagnose N7.4.

**N7.3 — Chain of trust**

**Root CA** — self-signed, in the client's trust store, kept offline. **Intermediate** — signed by the root, does the day-to-day signing. **Leaf** — your certificate, signed by an intermediate.

The client validates leaf → intermediate → root, checking signatures, validity dates, and name match. The server must send the leaf *and* intermediates; the root is expected to be in the client's store already.

**N7.4 — Missing intermediate: works in a browser, fails in curl**

The server sends only the leaf. Browsers paper over this — they cache intermediates from previous sites and can fetch them via the AIA extension. `curl`, JVMs, Go clients, and mobile apps typically don't, so they fail with "unable to get local issuer certificate."

Diagnose with `openssl s_client -showcerts` and count the certificates presented, or use an external SSL checker which will flag chain issues explicitly. Fix: configure the server with the full chain file (leaf first, then intermediates, root optional). This is one of the most common real TLS incidents.

**N7.5 — SNI**

Server Name Indication is a ClientHello extension carrying the hostname *in plaintext*, before encryption starts. It's what allows one IP and port to serve certificates for many hostnames — without it, the server can't know which certificate to present.

Operational relevance: any client not sending SNI gets the default certificate and a name mismatch. Also, because SNI is unencrypted, it's visible to network observers and is used for filtering — ECH/ESNI addresses this but isn't universally deployed.

**N7.6 — Expiry checking and alerting**

```bash
echo | openssl s_client -connect host:443 2>/dev/null | openssl x509 -noout -enddate
```

Alert on **days remaining**, not on expiry, with enough lead time to actually act — 30 days for manual processes, less for automated ones but still enough to notice a renewal failure. Monitor from *outside*, against the live endpoint, not against the file on disk: the common failure is a renewed certificate that was never deployed, or deployed to only some nodes.

**N7.7 — SAN vs CN, and wildcard limits**

Subject Alternative Name is the list of hostnames the certificate is valid for. Common Name is legacy; browsers have ignored it for name validation since roughly 2017, so a certificate with only a CN and no SAN fails everywhere modern. Every name must be in the SAN.

Wildcards (`*.example.com`) match exactly **one** label: `api.example.com` yes, `a.b.example.com` no, and the apex `example.com` no unless separately listed. Wildcards also require DNS-01 validation with ACME (N7.10/S4.3), and they concentrate risk — one compromised key affects every subdomain.

**N7.8 — Termination vs passthrough vs re-encryption**

- **Termination** — LB decrypts, forwards plaintext to the backend. Simplest; enables L7 routing, header inspection, and WAF. Requires the internal network to be trusted.
- **Passthrough** — LB forwards encrypted bytes; only the backend has the key. Preserves true end-to-end encryption and client certificates, but the LB can only do L4 (no path routing, no header injection).
- **Re-encryption** — LB terminates, then opens a new TLS connection to the backend. Gets L7 features *and* encryption on the internal hop, at the cost of double handshakes and managing backend certificates.

Choose on requirements: mTLS or compliance demanding true end-to-end → passthrough; need for L7 features plus encrypted internal traffic → re-encryption; internal network genuinely trusted → termination.

**N7.9 — mTLS**

Both sides present certificates. The server requests a client certificate during the handshake and validates it against a configured CA. Used for service-to-service authentication where you want cryptographic identity rather than shared secrets, for zero-trust internal networks, and for regulated partner integrations.

Cost: you now operate a CA, distribute and rotate client certificates, and handle revocation — which is why short-lived certificates issued automatically (S5.6) or a service mesh (S5.7) are the usual answers at scale.

**N7.10 — ACM and Let's Encrypt validation and renewal**

**ACM**: request a certificate, prove domain control via DNS (a CNAME record you add — Route53 can do it in one click) or email. DNS validation is preferred because ACM re-validates automatically and renews without intervention. Certificates are free but **can only be attached to AWS services** (ALB, CloudFront, API Gateway) — the private key is never exported, so you can't put an ACM cert on an EC2 instance directly. Renewal fails silently if the validation CNAME is later removed.

**Let's Encrypt**: ACME protocol. Client proves control via HTTP-01 (serve a token at a well-known path) or DNS-01 (publish a TXT record — required for wildcards). 90-day lifetime by design, renewal automated at ~60 days. Failure modes: rate limits, DNS propagation delays on DNS-01, and renewal hooks that don't reload the server after the new cert is written.

---

## N8. Load balancing & proxies

**N8.1 — L4 vs L7**

**L4** operates on IP and port. It doesn't decrypt or parse; it forwards flows. Faster, protocol-agnostic, preserves the connection end to end, supports TLS passthrough and non-HTTP protocols. AWS NLB.

**L7** parses the application protocol. Enables routing by path/host/header, TLS termination, header manipulation, cookie-based stickiness, WAF integration, request-level retries and observability. AWS ALB.

Choose L7 when you need content-based routing or per-request features; choose L4 for raw throughput, non-HTTP protocols, static IPs, or when you need TLS to reach the backend untouched.

**N8.2 — Forward vs reverse proxy**

**Forward proxy** sits in front of *clients*, acting on their behalf to reach the internet — egress control, filtering, caching, corporate proxies. The client knows about it.

**Reverse proxy** sits in front of *servers*, receiving client requests and distributing them — load balancing, TLS termination, caching. The client thinks it's talking to the origin.

Same mechanism, opposite direction, different purpose.

**N8.3 — Health checks and their failure modes**

Configure the path, interval, timeout, and healthy/unhealthy thresholds. Design considerations:

- **Too shallow** (TCP connect only) — passes while the application is broken.
- **Too deep** (checks every downstream dependency) — one slow dependency marks every instance unhealthy simultaneously and takes the whole service down. This is a real and severe failure mode.
- **Timeout too short** — instances flap under load, removing capacity exactly when it's needed, which makes the problem worse.

The usual guidance: liveness-style checks should be shallow and local; dependency health belongs in readiness or in monitoring, not in the check that removes you from the pool.

**N8.4 — Connection draining / deregistration delay**

When an instance is removed, the LB stops sending *new* connections but allows in-flight requests to complete for a configured period before terminating. Without it, deployments and scale-in events drop live requests.

Set it above your longest normal request duration. It must also be coordinated with the application: the app should stop accepting new work but keep serving existing requests on SIGTERM, and the container/pod grace period must exceed the drain time or the process gets killed mid-drain anyway.

**N8.5 — Sticky sessions**

The LB pins a client to one backend, usually via a cookie. Needed when the backend holds session state locally.

Why you'd rather avoid it: it defeats even load distribution, breaks when an instance dies (those users lose their session), complicates deploys and scaling, and creates hot backends. The better answer is stateless application servers with session state in Redis or a signed token — then any instance can serve any request. Stickiness is a workaround for an architecture problem.

**N8.6 — Tracing client IP through proxies**

`X-Forwarded-For` is appended to at each hop, producing a comma-separated list with the original client leftmost. The **PROXY protocol** is the L4 equivalent — a small header prepended to the TCP stream, used by NLB and HAProxy where there's no HTTP layer to add headers to.

Critical detail: `X-Forwarded-For` is client-supplied and forgeable. Trust only the portion added by proxies you control — typically by counting from the right, or configuring trusted proxy ranges in the application framework. Getting this wrong means IP-based rate limiting and allow-listing can be trivially bypassed.

**N8.7 — Where TLS should terminate**

Decision inputs: is the internal network trusted; are there compliance requirements for encryption in transit everywhere; do you need L7 routing or WAF; do backends need to see client certificates; and who manages certificate lifecycle.

A defensible default for most web workloads: terminate at the edge (ALB/CloudFront) for L7 features and centralised certificate management, then re-encrypt to backends if the environment demands in-transit encryption internally. For regulated or zero-trust contexts, passthrough or mTLS all the way through. State the tradeoff rather than asserting one answer.

**N8.8 — Balancing algorithms, and when round-robin is wrong**

- **Round-robin** — even distribution by count.
- **Least connections** — sends to the backend with fewest active connections.
- **Least outstanding requests** — ALB's default; similar but request-based.
- **IP hash / consistent hashing** — deterministic mapping, used for cache locality.
- **Weighted** — for heterogeneous instance sizes or canary traffic splits.

Round-robin is wrong when requests have highly variable cost or duration: a backend handling three long queries gets the same share as one handling three trivial ones, and queues build unevenly. It's also wrong with long-lived connections (websockets, gRPC), where connection *count* rather than request count determines load, and where a newly added instance receives nothing until clients reconnect. Least-outstanding-requests handles variable cost far better.

---

## N9. Diagnostics & fault isolation

**N9.1 — A method for "can't connect"**

Work up the layers, and let each result narrow the next step:

1. **Name** — does it resolve, and to the right address? `dig`, `getent hosts`.
2. **Reachability** — `ping` (with N9.6's caveat), `traceroute`/`mtr`.
3. **Port** — `nc -zv`. The *manner* of failure (N5.2) tells you refused vs dropped.
4. **Listener** — on the target: `ss -tulpn`. Is it listening, and on which interface?
5. **Filtering** — security groups, NACLs, host firewall, and the direction each applies to.
6. **Application** — `curl -v`, then logs.

State the hypothesis before each test, and what the result would rule out. That's what's being assessed, not the command list.

**N9.2 — Distinguishing DNS vs routing vs firewall vs application**

- **DNS** — the name fails but the IP works. `dig` returns the wrong or no answer.
- **Routing** — "no route to host", or traceroute dies at a consistent hop that isn't the destination.
- **Firewall** — timeout (drop) or refusal, with the service confirmed listening. Test from a host on the same subnet to isolate.
- **Application** — TCP connects fine, but the response is an error, slow, or malformed. `curl -w` timing (N6.2) attributes latency to the server.

The universal shortcut: **test by IP to skip DNS, and test from a host inside the same subnet to skip network controls.** Two tests bisect the space.

**N9.3 — `tcpdump` with a useful filter**

```bash
tcpdump -i any -nn host 10.0.5.20 and port 5432
tcpdump -i eth0 -nn 'tcp[tcpflags] & (tcp-syn|tcp-rst) != 0'
tcpdump -i any -nn -w capture.pcap port 443    # write for Wireshark
tcpdump -i any -nn -A port 80                  # print payload
```

`-nn` stops DNS and port-name resolution (which otherwise generates its own traffic and slows things). Filter tightly — an unfiltered capture on a busy host is unusable and can affect performance.

**N9.4 — Reading a capture**

The signatures worth recognising:

- **SYN with no SYN-ACK** — packet dropped inbound, or the reply dropped. Firewall or routing. If you see repeated SYNs at 1s, 2s, 4s intervals, that's the retransmit backoff confirming nothing came back.
- **SYN → RST** — actively refused; nothing listening.
- **Retransmissions** — packet loss or a stalled receiver.
- **Zero window** — the receiver's buffer is full; the *application* isn't reading fast enough. Points at the app, not the network.
- **RST mid-stream** — abrupt teardown; crash, timeout, or middlebox.
- **Duplicate ACKs** — loss triggering fast retransmit.

Capture on both ends when possible — comparing what was sent against what arrived localises the drop precisely.

**N9.5 — Wireshark**

Open the pcap, apply a display filter (`tcp.port == 443 && ip.addr == 10.0.5.20`), and use **Follow → TCP Stream** to see one conversation in order. Statistics → Conversations ranks talkers. Expert Information surfaces retransmissions and resets automatically. The TCP stream graph makes stalls and window issues visually obvious.

**N9.6 — What `ping` failing does and doesn't prove**

Ping uses ICMP echo. Many hosts, security groups, and network devices block ICMP by policy while permitting TCP traffic normally.

So **ping failing proves nothing** about whether the service is reachable. Ping succeeding does prove the host is up and routing works in both directions — which is useful, but the converse doesn't hold. Always follow with a TCP test to the actual port (N5.8). Conversely, ping succeeding while the service fails points at the service or a port-specific rule, not the path.

**N9.7 — Intermittent failure from one unhealthy backend**

Signature: a consistent *fraction* of requests fail — roughly 1/N with N backends — and retries usually succeed. Users report flakiness; averages look fine.

Isolate by: checking per-target metrics rather than aggregates (per-target response codes and health check status on the LB), bypassing the LB to test each backend directly with `curl --resolve`, and looking at whether failures correlate with a single instance ID in logs. Percentile metrics hide this; the p50 is fine and only the tail moves. This is exactly why per-instance dashboards matter alongside service-level ones.

**N9.8 — Flow logs as evidence**

VPC flow logs record source, destination, ports, protocol, packets, bytes, and **ACCEPT/REJECT** per flow. They answer two questions definitively:

- **Did the traffic arrive at all?** No record → it never reached the ENI; the problem is upstream (routing, wrong destination, client-side).
- **Was it accepted or rejected?** REJECT → a security group or NACL blocked it, and you now know which layer to fix.

Caveats: flow logs are aggregated over an interval so they're not real-time, and they record at the ENI, so they won't show intra-host or intra-pod traffic.

**N9.9 — Localising to a hop and stating your evidence**

The deliverable of an investigation isn't "it's fixed" — it's "the fault is *here*, and this is why." A good statement looks like:

> Traffic leaves the pod and reaches the node (tcpdump on the node shows the SYN). Flow logs show the SYN arriving at the RDS ENI with action REJECT. The security group on RDS allows 5432 from the node security group, but the pod's traffic is SNAT'd to the node IP, which is not in that security group. Evidence: flow log REJECT entries, matching timestamps, and the SG rule set.

Naming the evidence for each link in the chain is what distinguishes a senior diagnosis from a plausible guess — and it's what makes the fix verifiable rather than hopeful.

---

## N10. Cloud & overlay networking

**N10.1 — Security groups vs NACLs**

| | Security group | NACL |
|---|---|---|
| Attached to | ENI / instance | Subnet |
| State | **Stateful** | **Stateless** |
| Rules | Allow only | Allow **and** deny |
| Evaluation | All rules, any match allows | In rule-number order, first match wins |

The debugging consequence: because security groups are stateful, allowing inbound 443 automatically permits the return traffic. Because NACLs are stateless, you must **also** allow the outbound ephemeral port range (1024–65535) or replies are silently dropped. That asymmetry is the single most common NACL mistake, and it presents as a timeout with a security group that looks correct.

Security groups can reference other security groups as sources, which is the idiomatic way to express "app tier may reach database tier" without hardcoding CIDRs.

**N10.2 — Internet to a private instance and back**

Inbound: internet → internet gateway → public subnet route → load balancer → (LB's security group allows 443) → new connection to the instance in the private subnet → instance security group allows the LB's security group on the app port.

Outbound from the private instance: default route `0.0.0.0/0` → NAT gateway in the *public* subnet → NAT SNATs to its elastic IP → internet gateway → internet. Return traffic reverses via the NAT's state table.

The instance never has a public IP and cannot be reached inbound directly — that's the property the design buys.

**N10.3 — NAT gateway vs internet gateway, and cost**

**Internet gateway** — free, horizontally scaled, provides bidirectional routing for resources *with public IPs*. It's a route target, not a device you size.

**NAT gateway** — allows *private* resources outbound-only access. Charged per hour **and per GB processed**, on top of normal data transfer. This is a very common surprise line item: chatty private workloads pulling container images or writing to S3 through NAT can run into thousands per month.

The mitigations: VPC endpoints for AWS services (N10.4), one NAT per AZ (needed for AZ-independence, but multiplies cost), and being deliberate about what actually needs egress.

**N10.4 — VPC endpoints**

**Gateway endpoints** (S3, DynamoDB only) — a route table entry. **Free.** Traffic to those services stops traversing the NAT gateway entirely. There is essentially no reason not to have these.

**Interface endpoints** (PrivateLink, most other services) — an ENI in your subnet with a private IP. Charged hourly per endpoint per AZ plus per GB, but usually cheaper than the NAT processing they replace at moderate volume, and they keep traffic off the public internet, which is often the compliance driver.

When they pay for themselves: high-volume S3 or ECR traffic from private subnets makes gateway endpoints an immediate win; interface endpoints need a volume calculation but are frequently justified for ECR, Secrets Manager, and SSM.

**N10.5 — VPC peering vs Transit Gateway**

**Peering** — a direct, non-transitive one-to-one link. No bandwidth bottleneck, no hourly charge (data transfer still applies). But non-transitivity means N VPCs need N(N−1)/2 connections, and each VPC's route tables must carry entries for every peer. Fine up to a handful.

**Transit Gateway** — a hub. Each VPC attaches once; routing is centralised in TGW route tables, which also support segmentation (e.g. prod can't reach dev). Costs per attachment-hour plus per GB. Scales to hundreds of VPCs and integrates VPN and Direct Connect.

The tipping point is roughly when the mesh becomes unmanageable — typically beyond 5–10 VPCs, or as soon as you need hybrid connectivity or centralised inspection.

**N10.6 — VPN vs Direct Connect**

**Site-to-site VPN** — IPsec over the public internet. Fast to provision (hours), cheap, encrypted by default. Bandwidth is capped per tunnel (~1.25 Gbps) and latency is variable because it's the public internet.

**Direct Connect** — a dedicated physical circuit to an AWS location. Consistent latency, high and predictable bandwidth, lower per-GB data transfer cost at volume. But lead time is weeks to months, it costs a fixed monthly fee, and **it is not encrypted by default** — you'd run a VPN over it or use MACsec if encryption is required.

The standard production answer is Direct Connect for the primary path with a VPN as backup, since a single DX circuit is a single point of failure.

**N10.7 — Container networking differences**

The key departure from VM networking: **every pod gets its own IP** and pods communicate directly without NAT, which is the Kubernetes network model. How that's implemented varies by CNI.

With the AWS VPC CNI specifically, pods get **real VPC IPs from the subnet**, which means: security groups and flow logs work naturally at pod level, but IP consumption is enormous, and each instance type has a hard limit on ENIs and IPs per ENI. Hitting that limit shows as pods stuck `Pending` with no IP available despite free CPU and memory — a genuinely common EKS capacity surprise. Prefix delegation raises the ceiling.

Overlay CNIs (Calico VXLAN, Flannel) instead encapsulate pod traffic, so pod IPs are private to the cluster — conserving VPC addresses but adding encapsulation overhead and reducing MTU (N1.6).

**N10.8 — Service discovery in a dynamic environment**

Instances and pods are ephemeral, so hardcoded IPs are unworkable. Mechanisms: DNS-based (Kubernetes Services with cluster DNS, Route53 private zones, ECS Service Connect / Cloud Map), load balancer as a stable front, or a service registry (Consul) with client-side lookup.

The failure modes to name: DNS TTL and client-side caching mean discovery isn't instant (N4.9), and health-check integration matters — a registry that lists dead endpoints is worse than no registry.

**N10.9 — Egress control**

Restricting what internal workloads can reach outbound. Motivations: preventing data exfiltration, containing a compromised workload, and satisfying compliance requirements that mandate a controlled and logged egress path.

Mechanisms: NAT gateway as a single chokepoint, a proxy with domain allow-listing, AWS Network Firewall for domain and protocol filtering, and VPC endpoints so legitimate AWS traffic never needs egress at all. Kubernetes NetworkPolicies handle pod-level egress.

The tension worth naming: strict egress control breaks package installs, container pulls, and third-party API calls, so it needs an allow-list process that teams can actually use — otherwise it gets disabled during the first incident.
