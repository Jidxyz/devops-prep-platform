# Security, PKI & Certificates — Answer Key

Companion to Domain 6 of the DevOps Interview Skills Question Matrix. Numbering matches item for item.

Answers describe *what a good response covers*, not a script to memorise. Where an item is judgement rather than fact, the answer gives the reasoning and the tradeoff, because that's what's being assessed.

Scoping, carried over from the matrix: **TLS debugging is N7**, **AWS KMS and secrets services are A10**, **host hardening is L2**, **IAM is A2**. This domain is **PKI as a system**, certificate lifecycle operations, and security around the delivery pipeline. S1 is deliberately shallow — enough to reason about design choices, not enough to implement anything.

Three notes on how this domain is interviewed for a platform role:

- **S3 and S4 are the operational core.** Certificate expiry is one of the highest-frequency self-inflicted outage causes in the industry, and the questions about inventory, monitoring, and renewal are asked because interviewers have been burned by it.
- **S7 is the section that has grown most in importance** and is where a platform engineer is most likely to own the controls. OIDC over static keys, action pinning, and fork-PR risk are the concrete ones.
- **S10 rewards being able to argue with a control.** "Push back constructively on a control that adds cost without reducing risk" is a lead-level question, and in a regulated fintech it's a conversation you'll actually have.

---

## S1. Cryptography fundamentals

**S1.1 — Symmetric vs asymmetric**

- **Symmetric** — one key for both encryption and decryption (AES-GCM, ChaCha20-Poly1305). **Fast** — hardware-accelerated, gigabytes per second. **The problem is key distribution**: both parties need the same secret, and getting it to them securely is the hard part.
- **Asymmetric** — a keypair, where one key encrypts and only the other decrypts (RSA, ECDH, Ed25519). **Solves key distribution** — you can publish the public key freely. **Orders of magnitude slower**, and limited in what it can encrypt directly (RSA can only encrypt data smaller than its modulus).

**Where each is used, and the answer is almost always both together:**

- **TLS** — asymmetric for the handshake (authenticating the server via its certificate, and agreeing a shared secret via ECDHE), then **symmetric for the actual data**. The handshake is expensive and happens once; the bulk transfer is symmetric and fast (O12.8).
- **Envelope encryption** (A10.2) — the same pattern in storage: a symmetric data key encrypts the data, and something else protects the data key.
- **Signing** — asymmetric only (S1.3).
- **Disk and database encryption at rest** — symmetric.

The framing: **asymmetric crypto solves trust and key distribution; symmetric crypto does the work.** Every real protocol combines them, and understanding why is more useful than memorising algorithm names.

**S1.2 — Hashing vs encryption vs encoding**

- **Encoding** (base64, hex, URL encoding) — **a reversible representation change with no key and no secret.** Its purpose is transport safety — making binary data survive a text channel. **It provides zero confidentiality.** Anyone can decode it, trivially, with no information beyond the encoded string.
- **Hashing** — a **one-way** function producing a fixed-length digest. Cannot be reversed. Used for integrity checking, deduplication, and password storage (S1.4).
- **Encryption** — **reversible with the key**, and useless without it. Provides confidentiality.

**Why base64 is not security**, stated properly: it is the difference between **a locked box and a box with the contents written on the outside in a different alphabet.** The recurring real-world instance: **Kubernetes Secrets are base64-encoded, not encrypted** (K3.4) — `kubectl get secret x -o yaml | base64 -d` returns the plaintext, and anyone who can read the object has the secret. Teams routinely believe the encoding is a protection, and it's worth being able to correct that clearly.

The related confusions worth naming: **"encrypted" in a UI often means "encoded"**; **hashing is not encryption** and a "hashed then reversed" claim is nonsense unless it was encoding; and **HMAC is hashing with a key** — it proves integrity *and* authenticity, which a plain hash does not.

**S1.3 — Digital signatures: what they prove and what they don't**

The mechanism: hash the message, encrypt the hash with the **private** key. Anyone with the **public** key can decrypt the signature and compare it to their own hash of the message.

**What a valid signature proves:**

- **Integrity** — the message hasn't changed since signing. One bit different and the hashes don't match.
- **Authenticity** — it was signed by the holder of the private key.
- **Non-repudiation** — the signer cannot plausibly deny signing it, *assuming* the private key was genuinely theirs and exclusively controlled.

**What it does not prove**, which is the substance:

- **That the signer is who you think they are.** A signature proves the key signed it. **Binding that key to an identity is what a certificate and a CA are for** (S2.1) — without that binding, a signature from an unknown key is worth nothing.
- **That the content is true, safe, or correct.** A signed malicious binary is still malicious. **Signing proves provenance, not quality** — which is the most important caveat for supply chain work (S7.7): "this image is signed" means "we know who built it", not "it's safe".
- **That the key hasn't been compromised.** A signature made with a stolen key verifies perfectly.
- **When it was signed**, unless a trusted timestamp is included — which matters for whether a signature made before key compromise is still trustworthy.
- **That the signer intended to sign *this*** — relevant to blind signing and to attacks where a user is tricked into signing.

**S1.4 — Why bcrypt/argon2 rather than SHA-256**

**Because SHA-256 is designed to be fast, and speed is exactly the wrong property for password hashing.**

A modern GPU computes billions of SHA-256 hashes per second. Against a leaked database of SHA-256 password hashes, an attacker brute-forces the entire realistic password space for common passwords in hours. **The hash function is doing its job perfectly and that job is the wrong one.**

**Password hashing functions are deliberately slow and resource-intensive:**

- **bcrypt** — a configurable **work factor** (cost), each increment doubling the time. Tune so a single hash takes ~100–250ms on your hardware. Note its 72-byte input truncation, which is a real gotcha.
- **scrypt** — adds **memory hardness**: it requires a configurable amount of RAM, which defeats GPU and ASIC parallelism because memory is the expensive resource, not compute.
- **Argon2id** — the current recommendation (Password Hashing Competition winner), with separate parameters for **time, memory, and parallelism**, and resistance to both side-channel and GPU attacks.
- **PBKDF2** — iteration-based, widely available and FIPS-approved, weaker than the others because it isn't memory-hard. Acceptable where compliance requires it.

**The key insight to state**: the work factor is **tunable**, so as hardware improves you increase it. **A password hash's security is a moving target you must maintain** — a work factor set in 2016 is inadequate now, and re-hashing on next successful login is the standard migration path.

The related point: **SHA-256 is correct for integrity, HMACs, and signatures** (S1.3) — the criticism is specific to password storage, not to the algorithm.

**S1.5 — Salting and why it defeats rainbow tables**

A **salt** is a unique random value stored alongside the hash and included in the hashing input.

**Without a salt**, identical passwords produce identical hashes. That enables:

- **Rainbow tables** — precomputed hash-to-password lookups. An attacker computes them once and reverses any unsalted hash instantly. The entire attack is precomputation.
- **Cross-referencing** — identical hashes in a leaked database reveal which users share a password, and one cracked hash cracks all of them.
- **Cross-site correlation** — the same password on two sites produces the same hash on both.

**With a unique salt per password**, precomputation is worthless: an attacker would need a separate rainbow table per salt, which is the same work as brute-forcing each password individually. **It doesn't make any individual password harder to crack; it makes the attack un-amortisable across users** — that's the precise property and it's the thing to say.

The practicalities: **the salt is not secret** and is stored with the hash (bcrypt and Argon2 embed it in the output string along with the parameters, which is why their output looks like `$argon2id$v=19$m=65536,t=3,p=4$...`); it must be **unique per password and randomly generated**, not derived from the username; and **modern password hashing functions salt automatically**, so this is mostly a matter of not defeating them by doing something clever.

**A pepper** is the related concept: a secret value, shared across all passwords, stored separately from the database (in a KMS or config). It means a database leak alone is insufficient — the attacker also needs the pepper. Worth naming as defence in depth.

**S1.6 — Forward secrecy**

**Forward secrecy (or perfect forward secrecy) means that compromising a long-term private key does not allow decryption of past sessions.**

**The mechanism**: instead of using the server's long-term key to encrypt or transport the session key, both parties perform an **ephemeral Diffie-Hellman exchange** (ECDHE) to derive a session key that **exists only for that session and is never transmitted**. The long-term key is used only to *sign* the exchange, proving identity.

**Why it matters:** an attacker who records encrypted traffic today and obtains the server's private key in two years — through a breach, a subpoena, a Heartbleed-style vulnerability, or eventually quantum computing — **can decrypt all of that recorded traffic** if there's no forward secrecy. With it, each session's key was discarded when the session ended and cannot be recovered from anything.

The concrete history: **RSA key exchange** (where the client encrypted the premaster secret with the server's public key) has no forward secrecy and was widely used. It's why "harvest now, decrypt later" is a genuine threat model for nation-state adversaries.

The current state: **TLS 1.3 mandates forward secrecy** — the RSA key-exchange ciphersuites were removed entirely. In TLS 1.2 you get it by configuring ECDHE ciphersuites, which is standard practice now. **So on a modern configuration you have it by default**, and the item is mostly about understanding why the design changed.

**S1.7 — Which algorithms are current and which are deprecated**

**Deprecated or broken — should not appear anywhere:**

- **MD5, SHA-1** — collision attacks are practical. SHA-1 certificates have been rejected by browsers since 2017. **Still found in legacy internal systems and in checksums where it's arguably acceptable for non-adversarial integrity, and never for signatures.**
- **DES, 3DES, RC4** — broken or too weak.
- **SSL 2.0/3.0, TLS 1.0/1.1** — deprecated; **PCI DSS requires TLS 1.2 minimum**, and 1.0/1.1 are disabled in modern browsers.
- **RSA key exchange** (S1.6), **static Diffie-Hellman**.
- **RSA keys below 2048 bits.**

**Current:**

- **Symmetric**: AES-256-GCM, ChaCha20-Poly1305 (better on hardware without AES acceleration — mobile).
- **Hashing**: SHA-256 and above; SHA-3 and BLAKE2/3 as alternatives.
- **Signatures/keys**: **RSA-2048 or 3072**, or **ECDSA P-256** / **Ed25519**.
- **Key exchange**: ECDHE (X25519 is the preferred curve).
- **TLS 1.3** — fewer round trips (S1.6, O12.8), mandatory forward secrecy, and a drastically reduced ciphersuite list with the bad options removed by design.

**RSA vs ECDSA specifically**, since the item names it: **ECDSA gives equivalent security with much smaller keys** — P-256 ≈ RSA-3072 — which means **faster handshakes, less CPU, and smaller certificates.** The reason RSA persists is compatibility with very old clients. **The practical answer for a public-facing service is to serve both** (dual certificates), with clients negotiating; for internal PKI, ECDSA throughout.

Worth naming as current awareness: **post-quantum migration is underway** — NIST standardised ML-KEM (Kyber) and ML-DSA, and hybrid key exchange (X25519 + ML-KEM) is already deployed in Chrome and by Cloudflare. The driver is "harvest now, decrypt later" (S1.6), and it's a real planning consideration rather than a distant one.

**S1.8 — Never roll your own crypto, and where the line is**

**The rule**: don't implement cryptographic primitives or protocols. **The reason isn't that the maths is hard — it's that correctness is not observable.** A broken implementation encrypts and decrypts perfectly and is trivially attackable. There is no test that fails. Real implementations are broken by **timing side channels, padding oracles, nonce reuse, weak randomness, and error handling that leaks information** — none of which appear in functional testing, and all of which have caused real breaches in code written by competent engineers.

**Where the line actually is** — because the rule is often stated too broadly to be useful:

**Don't**: implement a cipher, a hash, a signature scheme, or a protocol like TLS. Don't invent a key derivation scheme. Don't write your own random number generation. Don't "improve" a standard construction by adding steps.

**Do**: **use cryptography.** Choosing AES-GCM over AES-CBC, using a library's authenticated encryption API, deriving keys with HKDF, using a KMS (A10.2) — these are engineering decisions you should be able to make.

**The genuinely risky middle ground, which is where most real mistakes happen:**

- **Composing primitives yourself** — encrypt-then-MAC versus MAC-then-encrypt, and getting the order wrong. **Use an AEAD mode (GCM, ChaCha20-Poly1305) and the composition problem disappears.**
- **Nonce and IV management** — **reusing a nonce with GCM is catastrophic** and completely destroys confidentiality and authenticity. This is the single most common way competent engineers break working crypto.
- **Comparing secrets with `==`**, which is timing-vulnerable — use a constant-time comparison.
- **Key derivation, storage, and rotation** — this is where most real weaknesses are, and it's operational rather than mathematical.

The framing: **use high-level, misuse-resistant APIs** (libsodium, `cryptography`'s Fernet, a cloud KMS) rather than low-level primitives, because the API design is what prevents the mistakes.

---

## S2. PKI & the trust model

**S2.1 — What a CA is and why anyone trusts one**

A **Certificate Authority** is an entity that verifies an identity and then **signs a certificate binding that identity to a public key** (S1.3's missing piece — the signature proves the key signed it; the certificate is what binds the key to a name).

**Why anyone trusts one** — the answer has three parts:

1. **Trust is pre-installed, not established.** Your operating system and browser ship with a **trust store** (S2.4) containing root CA certificates. You trust a CA because your software vendor decided to, having audited them.
2. **The vendors' programmes impose requirements.** Mozilla, Microsoft, Apple, and Google run root programmes requiring **WebTrust audits**, adherence to the CA/Browser Forum Baseline Requirements, published policy documents, and incident disclosure. A CA that misbehaves is removed.
3. **Removal has happened, repeatedly** — DigiNotar (2011, compromised and issued fraudulent Google certificates, removed and bankrupt), Symantec (2017, mis-issuance at scale, distrusted and its business sold), and others. **That the enforcement mechanism has been used is what makes the trust meaningful.**

**The uncomfortable truth to state**: **any CA in your trust store can issue a certificate for any domain.** There are hundreds of them, run by companies and governments in many jurisdictions. The trust model's weakness is that it's a chain that's only as strong as its weakest link, and you implicitly trust all of them equally. **Certificate Transparency (S2.11) and CAA records exist to mitigate exactly this.**

**S2.2 — The chain of trust**

```
Root CA (self-signed, in the trust store)
  └── Intermediate CA (signed by the root)
        └── Leaf / end-entity certificate (signed by the intermediate)
```

**Validation walks the chain upward**: the client receives the leaf and any intermediates the server sends, verifies each signature against the issuer's public key, and continues until it reaches a certificate **already in its trust store**. If it reaches a trusted root, the chain is valid. If it runs out of certificates before reaching one, validation fails (S3.5).

The checks at each step: the signature verifies; the certificate is within its validity period; the issuer's `basicConstraints` says `CA:TRUE` with an adequate `pathLen`; key usage permits certificate signing (S2.9); and for the leaf, the name matches (S2.7) and it isn't revoked (S2.10).

**The critical operational consequence: the server must send the intermediates.** The root is in the client's trust store; **the intermediates usually are not.** A server configured with only the leaf produces a chain the client can't complete — which is S3.5, the single most common certificate deployment error.

**Cross-signing** is worth knowing: an intermediate can be signed by more than one root, which lets a new CA be trusted by old clients via an established root while its own root propagates. **Let's Encrypt's ISRG Root X1 was cross-signed by IdenTrust's DST Root CA X3**, and the expiry of that cross-sign in 2021 broke a large number of old Android and OpenSSL 1.0.2 clients — the canonical example of S4.11.

**S2.3 — Why roots are offline and intermediates sign**

**The root's private key is the single most valuable secret in the entire system.** If it's compromised, an attacker can issue a trusted certificate for any domain, and **the only remedy is removing the root from every trust store on earth** — which takes years and breaks everything the CA has issued.

So the root is kept **offline**: on a hardware security module, in a physical safe, in a vault, powered off, used only in a formally witnessed and recorded **key ceremony** — perhaps a handful of times per year, to sign an intermediate or a CRL.

**The intermediate does the day-to-day signing**, online and exposed. It's also protected by an HSM, and it's exposed to operational risk in a way the root never is.

**The benefit of the separation:**

- **A compromised intermediate can be revoked by the root**, and clients that check revocation reject it. **Damage is contained to certificates issued by that intermediate, and the root survives.** That's the entire point.
- **The root's key can be very long-lived** (20+ years) because it's barely used, while intermediates rotate more frequently.
- **Separation of function** — different intermediates for different product lines, with different policies.

**The same principle applies to an internal CA** (S5.2), and it's the design point people skip: a private CA with an online root that signs leaves directly means a compromise of that machine is unrecoverable without redistributing a new root to every client. **The offline root is not ceremony for its own sake — it's the only thing that makes recovery possible.**

**S2.4 — Trust stores, and why they disagree**

The stores that exist, independently:

- **The OS store** — Windows Certificate Store, macOS Keychain, Linux's `/etc/ssl/certs` (managed by `ca-certificates`).
- **Browser stores** — **Firefox ships its own** (NSS) and ignores the OS on most platforms; Chrome historically used the OS store and is migrating to its own **Chrome Root Store**; Safari uses the OS.
- **Language runtimes** — **the JVM has its own `cacerts` truststore**, entirely separate from the OS; Python's `certifi` bundle ships with the package; Node has a compiled-in list; Go uses the OS but with its own logic.
- **Container images** — a minimal image may have an old or absent CA bundle.

**Why they disagree:**

- **Different update cadences.** The OS updates through package management; the JVM's `cacerts` updates when you update the JDK — **which may be never on a long-lived system**; `certifi` updates with pip.
- **Different inclusion policies.** Mozilla, Microsoft, and Apple each run their own root programme with different decisions.
- **Different removal timing** after a CA is distrusted.

**The practical consequences, which is why this item exists:**

- **"It works in the browser and fails in curl / the JVM / the container"** is the classic symptom (S3.5), and the trust store difference is one of the two causes (the other being a missing intermediate).
- **An old JVM with a stale `cacerts` doesn't trust newer roots** — including ISRG Root X1 for Let's Encrypt, which broke plenty of Java services.
- **A `FROM scratch` or distroless image without `ca-certificates` trusts nothing**, and every outbound TLS call fails with an unhelpful error (S7.6).
- **Adding an internal root** must be done in **every** store your workloads use, which is the distribution problem in S5.2.

**S2.5 — What a CSR contains and what the CA adds**

**The CSR (Certificate Signing Request) contains:**

- **The public key.**
- **The subject** — CN, O, OU, C, and so on.
- **Requested extensions** — most importantly the **SANs** (S2.7).
- **A signature made with the corresponding private key**, which proves the requester holds the private key for the public key being certified — **proof of possession**, and the reason the CSR is signed at all.

**The private key never leaves the requester.** That's the fundamental property (S3.2), and any process that generates the key on the CA's side is broken.

**What the CA adds:**

- **The issuer** — its own distinguished name.
- **A serial number**, unique per CA.
- **Validity dates** — and **the CA sets these, not you** (S4.6).
- **Its signature.**
- **Extensions the CA controls**: key usage and EKU (S2.9), CRL distribution points and OCSP URLs (S2.10), certificate policies, and Authority Information Access.
- **SCTs from Certificate Transparency logs** (S2.11).

**What the CA may ignore or override**: most of the subject fields. **Public CAs issuing domain-validated certificates generally discard everything except the SANs** — O, OU, and even CN are dropped or ignored, because the CA has only validated domain control, not organisational identity. **This surprises people who carefully craft a subject DN and find it absent from the issued certificate**, and it's worth knowing.

The validation the CA performs before signing is what distinguishes DV (domain control only), OV (organisation verified), and EV (extended verification) — and since browsers removed the EV UI indicator, the practical security difference is negligible.

**S2.6 — Reading a certificate**

```bash
openssl x509 -in cert.pem -noout -text
openssl x509 -in cert.pem -noout -subject -issuer -dates -serial
openssl x509 -in cert.pem -noout -ext subjectAltName

# from a live server, including the chain it sends
openssl s_client -connect api.example.com:443 -servername api.example.com -showcerts </dev/null
```

The fields that matter and what they tell you:

- **Subject** — the identity. **CN is legacy; ignore it for name matching** (S2.7).
- **Issuer** — who signed it. Compare against the next certificate in the chain (S3.4).
- **Validity: Not Before / Not After** — the expiry that causes outages (S3.12).
- **Subject Alternative Name** — **the field that actually determines which hostnames it's valid for.**
- **Public Key Algorithm and size** — RSA 2048, or `id-ecPublicKey` with a curve (S1.7).
- **Signature Algorithm** — `sha256WithRSAEncryption`. **`sha1With...` is a red flag** (S1.7).
- **Basic Constraints** — `CA:TRUE/FALSE`, and `pathlen`. A leaf must be `CA:FALSE`.
- **Key Usage / Extended Key Usage** (S2.9).
- **CRL Distribution Points / Authority Information Access** — revocation and issuer URLs (S2.10).
- **SCT list** — Certificate Transparency proofs (S2.11).

The habit worth naming: **`openssl s_client` shows what the server actually sends**, which is how you diagnose a missing intermediate (S3.5) — the local file being correct tells you nothing about the deployed configuration.

**S2.7 — SAN vs CN, and why CN stopped working**

**Common Name (CN)** is a field in the subject DN — originally a human-readable name, informally used to carry the hostname. **Subject Alternative Name (SAN)** is an extension listing the identities the certificate is valid for: DNS names, IP addresses, email addresses, URIs.

**Why CN alone stopped working:**

1. **CN is a single value.** One certificate, one name. SANs allow many, which is essential for any real deployment serving several hostnames.
2. **CN has no type information** — it's just a string, so there's no way to distinguish a DNS name from anything else. SAN entries are typed.
3. **The standards deprecated it.** RFC 2818 (2000) said SAN should be preferred and CN used only for compatibility; **RFC 6125 formalised the deprecation**, and the CA/Browser Forum Baseline Requirements require SANs.
4. **Browsers enforced it.** **Chrome stopped accepting CN-only certificates in version 58 (2017)**, and others followed. Go's TLS library did the same.

**The practical consequence**: a certificate with a correct CN and no matching SAN **fails validation in every modern client**, with an error that often points at the name rather than at the missing extension. The fix is a CSR that requests the SAN properly:

```bash
openssl req -new -key key.pem -out csr.pem \
  -subj "/CN=api.example.com" \
  -addext "subjectAltName=DNS:api.example.com,DNS:www.example.com"
```

**Note that the CN, if present, must also appear in the SAN list** — a name in CN only is not covered. That's the specific trap: people add SANs for the additional names and leave the primary name only in CN.

**S2.8 — Wildcard certificates and their scope limits**

`*.example.com` matches **exactly one label** in that position.

**What it covers**: `api.example.com`, `www.example.com`, `anything.example.com`.

**What it does not cover, and this is the item:**

- **The apex** — `example.com` itself is **not** matched. You need it as a separate SAN, which is why wildcard certificates almost always list both `*.example.com` and `example.com`.
- **Deeper subdomains** — `api.staging.example.com` is **not** matched by `*.example.com`. You'd need `*.staging.example.com`.
- **Multiple levels** — there is no `*.*.example.com` in any usable form.

**The security tradeoffs:**

- **One private key covering every subdomain.** A compromise on any host holding that key compromises **all** subdomains — a much larger blast radius than per-host certificates. **This is the main argument against them.**
- **Wide distribution** — the key must be on every server serving any subdomain, so it's copied widely and its exposure grows with your estate.
- **Revocation is all-or-nothing** — revoking because one host was compromised invalidates every service using it.
- **Issuance requires DNS-01 with ACME** (S4.3), because HTTP-01 cannot prove control of arbitrary subdomains.

**When they're justified**: a large or dynamic set of subdomains where per-name issuance is impractical, internal services, and reducing the operational burden of certificate management where automation isn't yet in place.

**The better answer where automation exists**: **per-service certificates issued automatically** (S4.8, S5.6) give a much smaller blast radius, and cert-manager makes them no more work than a wildcard. The wildcard's convenience argument largely evaporates once issuance is automated.

**S2.9 — Key usage and extended key usage**

**Key Usage (KU)** — what the key may be used for cryptographically: `digitalSignature`, `keyEncipherment`, `keyCertSign`, `cRLSign`, `keyAgreement`, `nonRepudiation`.

**Extended Key Usage (EKU)** — what purpose the certificate is for: `serverAuth` (TLS server), `clientAuth` (TLS client / mTLS), `codeSigning`, `emailProtection`, `timeStamping`, `OCSPSigning`.

**Why these constraints matter:**

- **They limit damage.** A certificate issued for `serverAuth` cannot be used for code signing, even if the key is stolen. **Scope limitation is the whole purpose.**
- **`keyCertSign` combined with `basicConstraints: CA:TRUE` is what makes a certificate a CA.** A leaf without these cannot sign others — which is what prevents a compromised web server certificate being used to mint further certificates. **This was a real historical vulnerability**: some old clients didn't check `basicConstraints`, so any valid leaf could sign for any domain.
- **mTLS needs both sides configured correctly** (S5.4) — a client certificate needs `clientAuth`, and using a server certificate as a client certificate is a common configuration error producing a rejection that doesn't obviously name the reason (S5.5).
- **Name constraints** (on a CA certificate) restrict which domains it may issue for — genuinely useful for an internal CA, and for constraining a cross-signed intermediate.

The operational relevance: **when a certificate is rejected and the name and dates look right, check the EKU.** It's a frequent cause of "the certificate is valid but the connection is refused", especially in mTLS and in non-browser clients that enforce it strictly.

**S2.10 — Revocation, and why it's weak in practice**

**The mechanisms:**

- **CRL (Certificate Revocation List)** — the CA publishes a signed list of revoked serial numbers. Clients download it. **Problems**: the list grows large, it's cached so revocation is delayed by the cache period, and downloading a multi-megabyte CRL on every connection is impractical.
- **OCSP** — the client asks the CA's responder about one certificate. **Problems**: it adds a network round trip to every handshake (latency, O12.8); it leaks the client's browsing to the CA (a privacy issue); and **the OCSP responder becomes an availability dependency for your site**.
- **OCSP stapling** — **the server** fetches its own OCSP response periodically and includes it in the handshake. Fixes latency, privacy, and the availability dependency. **The right answer**, and it requires server configuration plus `must-staple` on the certificate to be enforceable.

**Why revocation is weak in practice** — this is the substance:

- **Soft-fail.** If a client can't reach the OCSP responder, **it proceeds anyway.** It has to — hard-fail would mean any responder outage takes down large parts of the web. **But soft-fail means an attacker who can block OCSP has defeated revocation entirely**, and an attacker performing a MITM can certainly block a network request.
- **Browsers largely stopped relying on it.** Chrome disabled online revocation checks years ago and uses **CRLSets** — a curated, pushed list of high-priority revocations, which covers a small fraction of revoked certificates. Firefox uses **CRLite**. Both are pragmatic admissions that the original design failed.
- **Non-browser clients frequently don't check at all** — many HTTP libraries, JVM defaults, and internal tooling simply skip it.
- **Let's Encrypt stopped providing OCSP entirely** in 2025, moving to CRLs only — a significant recent development and a good currency signal.

**The conclusion, and it's the important one: revocation should not be your primary control.** The industry's answer is **short-lived certificates** (S5.6, S4.6) — if a certificate is valid for 90 days, or 24 hours, the exposure window from a compromise is bounded by expiry rather than by a revocation mechanism that may not work. **Short lifetimes are revocation that actually functions.**

**S2.11 — Certificate Transparency**

**CT is a set of public, append-only, cryptographically verifiable logs of every certificate issued by a participating CA.** Chrome requires certificates to be logged (evidenced by embedded SCTs, S2.6) or it rejects them, so in practice **every publicly-trusted certificate is public**.

**What it lets you detect:**

- **Mis-issuance** — a certificate for your domain issued by a CA you don't use, to someone who isn't you. **This is the primary purpose** and it directly addresses the weakness in S2.1: any CA can issue for any domain, but now it can't do so secretly.
- **Unauthorised internal issuance** — someone in your organisation obtaining a certificate outside the sanctioned process.
- **Shadow IT and forgotten infrastructure** — monitoring CT for your domains reveals subdomains and services you didn't know existed. **A genuinely useful reconnaissance-of-yourself exercise.**
- **Impending expiry and inventory gaps** — CT is a free, external certificate inventory for your public domains (S3.8).

**How to use it**: monitor CT logs for your domains — **crt.sh** for ad hoc searches, **Cert Spotter**, **Facebook's CT monitoring**, or a commercial service — and alert on unexpected issuance.

**The complementary control is CAA** — a DNS record specifying which CAs may issue for your domain:

```
example.com. CAA 0 issue "letsencrypt.org"
example.com. CAA 0 issuewild ";"
example.com. CAA 0 iodef "mailto:security@example.com"
```

**CAA is preventive** (compliant CAs refuse to issue), **CT is detective** (you find out if one does anyway). Together they substantially close the gap, and mentioning both is the complete answer.

**The side effect worth naming**: CT means **your internal hostnames become public** if you get public certificates for them. `payments-internal-staging.example.com` in a CT log is free reconnaissance for an attacker. That's a real argument for an internal CA (S5.1) or for wildcards on internal names.

**S2.12 — Certificate pinning and why it's a footgun**

**Pinning** means the client hard-codes which certificate or public key it will accept, rather than accepting anything that chains to a trusted root.

**What it protects against**: a fraudulently-issued certificate from a compromised or coerced CA (S2.1), and a MITM using a certificate that's technically valid. **In a high-threat context — a banking app, a messaging app — it's a genuine and meaningful control.**

**Why it's a footgun in most deployments:**

- **You must rotate the pin before you rotate the certificate**, and clients must have received the new pin. **Pin the wrong thing and every pinned client is bricked** — they cannot connect, and for a mobile app that means an app store release cycle to fix, during which the service is unavailable to those users.
- **It defeats emergency certificate replacement.** If you must reissue urgently (key compromise, S3.11), pinned clients reject the new certificate.
- **It breaks CA changes** — you can no longer switch CA, or accept a chain change (S4.11).
- **The failure is total and un-remediable server-side.** Every other TLS problem can be fixed by changing the server; a bad pin can only be fixed by updating the client.
- **HPKP (HTTP Public Key Pinning) was removed from browsers entirely** — precisely because sites bricked themselves and because it enabled a "RansomPKP" attack where a compromised server pins an attacker's key. **That the web platform removed it is the strongest evidence for the argument.**

**How to do it if you must**: pin to the **intermediate or root** rather than the leaf (survives leaf rotation); **pin multiple keys including a backup** you haven't deployed yet; keep the pin lifetime short; and have a remote kill switch. Mobile apps with a controlled release process are the reasonable case.

**The better answers for most deployments**: **CT monitoring plus CAA** (S2.11), which gets you detection and prevention of mis-issuance without the brittleness.

**S2.13 — Self-signed vs private CA vs public CA**

- **Self-signed** — a certificate signing itself. No chain, no CA. **Every client must explicitly trust that exact certificate**, so trust doesn't scale past a handful of endpoints, and rotating it means re-trusting everywhere.
- **Private CA** — your own root and intermediates (S5.2), with the root distributed to your clients. **Trust scales**: clients trust the root once, and any certificate it issues is accepted.
- **Public CA** — a CA already in every trust store (S2.4). No distribution needed.

**Choosing per scenario:**

| Scenario | Choice | Reason |
|---|---|---|
| Public website or API | **Public CA** (ACME/Let's Encrypt, or ACM on AWS) | Clients are outside your control and already trust it |
| Internal service-to-service mTLS | **Private CA** | Trust distribution is tractable; you control lifetimes and identity (S5.1) |
| Internal service with a public DNS name | **Public CA** is often simpler — no distribution at all | Weigh against CT exposing the hostname (S2.11) |
| Local development | **Self-signed or mkcert** | Trust scope is one machine |
| A single appliance with a handful of known clients | **Self-signed is defensible** | A private CA is more machinery than the problem needs |
| Client certificates for workload identity | **Private CA** | Public CAs won't issue for arbitrary internal identities |

The decision framework to state: **the question is who needs to trust it and whether you can reach them.** If the clients are outside your control, you need a public CA. If they're inside it and numerous, a private CA. If there are two of them and they never change, self-signed is honest and adequate — and **calling self-signed "insecure" is wrong; it's the trust distribution that doesn't scale, not the cryptography.**

---

## S3. Certificate lifecycle operations

**S3.1 — Generating a private key and CSR**

```bash
# ECDSA P-256 — preferred for new deployments (S1.7)
openssl ecparam -name prime256v1 -genkey -noout -out api.key
chmod 600 api.key

openssl req -new -key api.key -out api.csr \
  -subj "/C=GB/O=Acme Ltd/CN=api.example.com" \
  -addext "subjectAltName=DNS:api.example.com,DNS:www.api.example.com"

# RSA where compatibility demands it
openssl genrsa -out api.key 2048

# inspect before submitting — catch mistakes here, not after issuance
openssl req -in api.csr -noout -text -verify
```

The parameters that matter:

- **Algorithm and size** — ECDSA P-256 or RSA-2048 minimum (S1.7). RSA-4096 is slower for marginal benefit; if you want more than 2048's security margin, ECDSA is the better trade.
- **`-noout` on `ecparam`** — without it the file includes the curve parameters, which some software mishandles.
- **SANs are mandatory** (S2.7), and **the CN must also appear in the SAN list**.
- **`chmod 600` immediately** (S3.2).
- **No passphrase for a server key** in most cases — a passphrase means the service can't start unattended, which is usually worse than the marginal protection. If you use one, you need a mechanism to supply it at startup, which becomes a secret management problem (S6.2).

The verification step is the one people skip: **`openssl req -in csr -noout -text` before submission** catches a missing SAN, a typo'd hostname, or the wrong key — all of which are much cheaper to fix before issuance than after.

**S3.2 — Protecting private key material**

The rules:

- **Generate the key where it will be used.** It should never transit a network, an email, a chat message, or a ticket. **A key that has been sent to someone is compromised** — treat it as such.
- **File permissions `0600`, owned by the service user.** A key readable by `others` is a finding, and it's common.
- **Never in Git.** Including in history (S6.3, S6.4) — a key committed and then deleted is still in the repository and still compromised.
- **Never in a container image.** Baking a key into a layer means it's in the registry, in every pull, and in every layer cache (S7.6).
- **Never in a Terraform state file** without understanding it's stored in plaintext there (S6.9, TF3.2) — `tls_private_key` in Terraform puts the key in state.
- **Encrypted at rest** where the platform supports it, and **in an HSM or KMS for anything high-value** — a CA key should never exist as a file (S5.2).
- **Backed up**, securely, because losing a CA key is unrecoverable in a different way from leaking it.
- **Rotated**, with a defined lifetime (S5.6).

The platform-appropriate answers: **ACM** keeps the key entirely inside AWS and won't export it (A10.18) — which is a security feature and the reason ACM certificates can't be used on EC2 directly. **cert-manager** stores keys in Kubernetes Secrets (K3.4 — base64, so etcd encryption matters, K3.5). **Vault** and **cloud KMS** for CA keys. **A hardware token or HSM** for signing keys (S7.7).

The detection: **secret scanning in the commit path** catches `-----BEGIN PRIVATE KEY-----` reliably, and it should be a pre-commit hook plus a server-side check (S6.3).

**S3.3 — Converting between formats**

```bash
# PEM → DER
openssl x509 -in cert.pem -outform der -out cert.der
# DER → PEM
openssl x509 -in cert.der -inform der -out cert.pem

# PEM (cert + key + chain) → PKCS#12
openssl pkcs12 -export -out bundle.p12 \
  -inkey api.key -in api.crt -certfile chain.crt -name api

# PKCS#12 → PEM
openssl pkcs12 -in bundle.p12 -nodes -out combined.pem

# PKCS#12 → JKS (Java)
keytool -importkeystore -srckeystore bundle.p12 -srcstoretype PKCS12 \
        -destkeystore keystore.jks -deststoretype JKS

# inspect a JKS
keytool -list -v -keystore keystore.jks
```

What each is:

- **PEM** — base64 with `-----BEGIN...-----` headers. Text, concatenatable, the Unix default. **What nginx, Apache, HAProxy, and most tooling want.**
- **DER** — the binary encoding. Used by some Windows tooling and by Java in places.
- **PKCS#12 / PFX** — a password-protected container holding a key, its certificate, and the chain together. **The interchange format**, and the bridge to Java and Windows.
- **JKS** — Java's legacy keystore. **Deprecated in favour of PKCS#12**, which modern JDKs use by default — and knowing that JKS is legacy is worth saying.

The practical notes: **`.crt`, `.cer`, and `.pem` extensions tell you nothing** about whether the content is PEM or DER — check with `file` or by looking at it. **PKCS#12 requires a password** (an empty one is allowed and is a bad idea). And **Java distinguishes the keystore (your key and certificate) from the truststore (CAs you trust)** — conflating them is a common source of confusion (S2.4).

**S3.4 — Assembling a correct chain file**

**The order is leaf first, then each issuer in turn, ending with the intermediate closest to the root.** The root is optional and usually omitted (the client has it).

```
-----BEGIN CERTIFICATE-----   ← leaf (your server certificate)
-----BEGIN CERTIFICATE-----   ← intermediate that signed the leaf
-----BEGIN CERTIFICATE-----   ← intermediate that signed that one (if any)
```

```bash
cat api.crt intermediate.crt > fullchain.pem

# verify it before deploying
openssl verify -untrusted intermediate.crt api.crt
openssl crl2pkcs7 -nocrl -certfile fullchain.pem | openssl pkcs7 -print_certs -noout
```

The details that matter:

- **Wrong order breaks strict clients.** Some are lenient and reorder; **many are not**, and the failure is confusing because the file contains all the right certificates.
- **Verify each certificate's issuer matches the next one's subject** — that's what `openssl pkcs7 -print_certs -noout` lets you eyeball, and it's the fastest way to confirm a chain is coherent.
- **Including the root is harmless but pointless** — it adds bytes to every handshake, and if the client doesn't already trust it, including it doesn't help.
- **ACME clients produce `fullchain.pem` correctly** (certbot's `fullchain.pem` is exactly this; `cert.pem` is the leaf alone). **Configuring `cert.pem` instead of `fullchain.pem` is the single most common certbot deployment error** and produces S3.5.
- **Different servers want different things**: nginx wants the full chain in `ssl_certificate`; Apache historically had a separate `SSLCertificateChainFile` (now deprecated in favour of the combined file); some load balancers take the chain as a separate field.

**S3.5 — Diagnosing a missing intermediate**

**The signature symptom: it works in a browser and fails in `curl`, in a JVM, in Go, or in a container.**

**Why browsers hide it**: browsers cache intermediates they've seen before, and many will **fetch a missing intermediate** using the Authority Information Access URL in the certificate. So a browser completes a chain the server didn't send. **Other clients do neither** — `curl`, OpenSSL, the JVM, and Go require the server to send the full chain (S2.2).

The diagnosis:

```bash
# what the server actually sends
openssl s_client -connect api.example.com:443 -servername api.example.com </dev/null 2>/dev/null \
  | openssl crl2pkcs7 -nocrl -certfile /dev/stdin | openssl pkcs7 -print_certs -noout

# the verdict
openssl s_client -connect api.example.com:443 -servername api.example.com </dev/null 2>&1 \
  | grep -E 'Verify return code|verify error'
# "unable to get local issuer certificate" → missing intermediate
```

Or use **SSL Labs** / `testssl.sh`, which report "chain issues: incomplete" explicitly.

**The fix**: configure the full chain (S3.4) — usually changing `cert.pem` to `fullchain.pem`.

**The reason it keeps happening**: it's tested in a browser, it works, and it ships. **The failure appears later, from a different client type** — a mobile app, a partner's server-to-server integration, a monitoring check — and by then nobody connects it to the certificate deployment. **Testing with `openssl s_client` or `curl` rather than a browser is the practice that prevents it.**

The related cause to rule out: **a trust store missing the root** (S2.4), which produces a similar error. Distinguish by whether the server is sending the intermediates — if it is and validation still fails, it's the client's trust store.

**S3.6 — Verifying a key and certificate match**

```bash
# compare the public key moduli/points — they must be identical
openssl x509 -in api.crt -noout -pubkey | openssl md5
openssl pkey  -in api.key -pubout      | openssl md5

# RSA-specific classic form
openssl x509 -noout -modulus -in api.crt | openssl md5
openssl rsa  -noout -modulus -in api.key | openssl md5

# and that the CSR matches too
openssl req -noout -modulus -in api.csr | openssl md5
```

**All three must produce the same hash.** The `pkey -pubout` form is the general one and works for ECDSA as well as RSA, which the `-modulus` form does not — worth knowing since `-modulus` is the more commonly cited recipe and fails on EC keys.

**Why it matters**: a mismatched key and certificate produce a service that **fails to start** with an error like `key values mismatch`, or worse, starts with the wrong certificate. It happens when: multiple renewals produce several key files and the wrong one is referenced; a certificate is reissued with a new key and only one file is updated; or files are copied between hosts partially.

**Check before deploying, not after** — this is a five-second check that prevents a failed deployment, and it belongs in the automation that installs certificates (S3.10).

**S3.7 — Installing a certificate on a load balancer, reverse proxy, and app server**

**Load balancer (AWS ALB/NLB)**: the certificate lives in **ACM** or IAM, and is attached to the HTTPS listener. **ACM is preferred** — automatic renewal (A8.6), and the private key never leaves AWS. Multiple certificates per listener with SNI. **The backend leg is separate** — TLS to the target is configured independently and is frequently plaintext (S5.9).

**Reverse proxy (nginx)**:

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/ssl/certs/fullchain.pem;   # chain, not just leaf (S3.4)
    ssl_certificate_key /etc/ssl/private/api.key;

    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_stapling on;                                    # (S2.10)
    ssl_stapling_verify on;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

**Application server (JVM)**: PKCS#12 keystore (S3.3), referenced in configuration, with the truststore separate (S2.4).

**Kubernetes**: a `kubernetes.io/tls` Secret referenced by an Ingress (K4.8), populated by cert-manager (S4.8).

The points that generalise:

- **Reload, don't restart**, where the server supports it — `nginx -s reload` picks up a new certificate with no dropped connections. **This is what makes zero-downtime renewal possible** (S3.10).
- **Validate the configuration before reloading** (`nginx -t`), or a bad certificate path takes the service down.
- **Permissions** — the key readable only by the process user (S3.2).
- **Terminate once, ideally at the edge** (S5.9), so certificate management is concentrated rather than on every host.

**S3.8 — Maintaining a certificate inventory**

**The problem**: certificates are issued by different people, through different processes, deployed to different places, over years. **Nobody knows how many there are or where they are** — which is why expiry outages happen to organisations that "manage certificates" (S3.12).

**Building the inventory:**

- **Certificate Transparency** (S2.11) — for anything with a public certificate, **crt.sh gives you a free external inventory of your domains** and will surface certificates you didn't know existed. The best starting point.
- **Active scanning** — connect to every host and port in your estate and record what it presents. `testssl.sh`, `sslyze`, or a custom scanner across your IP ranges and DNS records.
- **Cloud APIs** — `aws acm list-certificates` across every account and region (A14.4), plus IAM server certificates, which are the forgotten legacy ones.
- **Kubernetes** — `kubectl get certificates -A` for cert-manager (S4.8), plus TLS Secrets not managed by it.
- **Configuration management / IaC** — certificates referenced in Terraform, Ansible, or Helm values.
- **The CA's own records** — for an internal CA, it knows what it issued (S5.2).

**What to record**: common name and SANs, issuer, expiry, the key algorithm, where it's deployed, **who owns it**, how it's renewed (automated or manual), and whether it's monitored.

**The properties that make an inventory useful rather than a spreadsheet:**

- **It must be generated, not maintained by hand** — a manual inventory is stale within weeks and this is exactly the IPAM argument (A3.10).
- **Every certificate has a named owner**, or nobody acts when it's about to expire.
- **It flags the unmanaged ones** — the certificates that aren't automatically renewed are the ones that will cause the outage, and identifying them is the inventory's main output.

**S3.9 — Monitoring and alerting on expiry**

**The alert**: days remaining until `notAfter`, with **enough lead time to act.**

```bash
# blackbox_exporter gives this natively
probe_ssl_earliest_cert_expiry - time()
```

```promql
(probe_ssl_earliest_cert_expiry - time()) / 86400 < 21
```

**The lead time is the design decision:**

- **21–30 days** for a warning — enough to raise a ticket, get approval, and go through a change process, including if someone is on holiday.
- **7 days** for an escalation.
- **48 hours** for a page.

**The reasoning**: a manual renewal in a regulated environment can take days — a request, a CSR, a CA's issuance process, a change approval, a deployment window. **An alert at 7 days is too late if the process takes 10.** Set the lead time from your actual renewal process duration, measured, plus margin.

**What to monitor, and the gaps that matter:**

- **From outside, by connecting** — this checks what's actually served, which is the only thing that counts. A certificate file on disk that isn't loaded doesn't matter; a load balancer serving an old certificate does (S3.5's lesson).
- **Every endpoint**, not just the well-known ones — including internal services, mTLS client certificates, and non-HTTP TLS (databases, message brokers, LDAP).
- **The CA's own certificates** — an expiring intermediate or root is a much larger event (S4.11).
- **Client certificates**, which are frequently forgotten because nothing browses to them.
- **Certificates in Kubernetes** — cert-manager exposes `certmanager_certificate_expiration_timestamp_seconds`.

**Even fully automated certificates need monitoring**, because automation fails silently (S4.7). The alert is the backstop that catches a broken renewal while there's still time.

**S3.10 — Planning a renewal or rotation with no downtime**

The sequence:

1. **Generate a new key and CSR** (S3.1) — **a new key each time**, not a reuse, so the rotation actually rotates the key material.
2. **Obtain the new certificate** while the old one is still valid and serving. **Never revoke or remove the old one first.**
3. **Verify before deploying**: key matches certificate (S3.6), chain is complete and correctly ordered (S3.4), SANs cover every name currently served (S2.7), and dates are right.
4. **Deploy to one instance and test** — `openssl s_client` against it directly, not through the load balancer.
5. **Roll out**, and **reload rather than restart** (S3.7) so connections aren't dropped.
6. **Verify from outside** what's actually being served.
7. **Retain the old certificate** until you're confident, so rollback is a config change.

**The properties that make it zero-downtime:**

- **Overlap.** The old certificate remains valid throughout — there is never a moment with no valid certificate.
- **Reload, not restart.**
- **Rolling deployment**, so instances update one at a time behind the load balancer.

**The cases that need extra care:**

- **Pinned clients** (S2.12) — the pin must be updated first, on the client, and confirmed deployed.
- **mTLS** (S5.5) — **both sides must trust the new issuer before either presents a certificate from it.** Rotating a client certificate to a new CA without the server trusting that CA first is an outage, and it's the classic mTLS rotation mistake. The safe sequence is: distribute the new CA to all trust stores → then issue and deploy new leaf certificates → then remove the old CA.
- **A CA change** (S4.11) — clients must trust the new root before the new leaf is served.
- **Long-lived connections** — a reload doesn't affect established connections, so old certificates persist on them until they close, which is usually fine and occasionally matters.

**The best answer is that this should be automated** (S4.4, S4.8) — a manual zero-downtime renewal executed correctly a few times a year is a process that will eventually be executed incorrectly.

**S3.11 — Handling a key compromise**

The sequence, and containment comes before investigation:

1. **Assess the scope.** Which key? What does it protect? Is it a leaf, an intermediate, or a CA root (S2.3)? **A CA key compromise is a different and far worse event** — every certificate it issued is suspect.
2. **Issue a replacement immediately, with a new key.** Get the new certificate deployed and serving **before** revoking the old one, so there's no availability gap.
3. **Revoke the old certificate** (S2.10) — accepting that revocation is weak in practice, so this is necessary and not sufficient. For a public certificate, revocation also removes it from some browsers' CRLSets.
4. **Rotate anything the key protected** — if it was used for mTLS client identity, the identity is compromised; if it signed artefacts, re-sign them (S7.7).
5. **Investigate the exposure**: how did it leak (git, a log, a backup, a laptop, a misconfigured share)? **How long was it exposed?** What could an attacker have done with it — decrypt recorded traffic (S1.6 — and if you had forward secrecy, past sessions are safe, which is the concrete payoff), impersonate the service, or sign?
6. **Look for evidence of use** — CT logs for certificates issued using it (S2.11), unusual connections, and audit logs.
7. **Fix the leak path**, which is the actual remediation (S6.4's argument — rotation without fixing the source means it happens again).
8. **Notify** — in a regulated environment, legal and compliance have disclosure obligations with clocks that start at detection.

**The reassessment part of the item**: ask why the key was exposed in a form that could leak. **If it was a file on a server, could it have been in an HSM or KMS? If it was long-lived, could it be short-lived** (S5.6) — because a 24-hour certificate reduces this entire incident to "it expires shortly anyway". **The structural fix is usually shorter lifetimes and better key storage**, not better handling procedures.

**S3.12 — Why expired certificates cause outages, and why it keeps happening**

**The mechanism**: an expired certificate causes clients to **fail validation and refuse the connection.** It's a hard failure, not a warning — the service is up, healthy by every internal metric, and completely unreachable. **Monitoring that runs inside the system sees nothing wrong** (O1.5's white-box blind spot).

The famous examples make the point about scale: Microsoft Azure, Ericsson (taking down mobile networks in several countries), Cisco, LinkedIn, Spotify — all major outages caused by a certificate nobody renewed.

**Why it keeps happening**, which is the substance:

- **It's a deadline, not a gradual degradation.** Nothing warns you as it approaches unless you built the warning (S3.9). It works perfectly right up to the second it doesn't.
- **Certificates outlive the people and processes that created them.** A two-year certificate is renewed by someone who wasn't there when it was issued, following a runbook that may not exist.
- **Ownership is unclear** — the certificate was installed by an engineer who has moved teams, on a system that has changed hands. **Nobody owns it, so nobody renews it** (S3.8).
- **There's no inventory**, so the certificate that expires is the one nobody knew about.
- **The renewal was manual**, and manual processes fail eventually.
- **Monitoring was on the main site** and the expired certificate was on an internal API, a client certificate, or an intermediate.
- **The alert existed and went to a distribution list nobody reads** (A10.29's argument).
- **A renewal automation broke silently** weeks earlier (S4.7).

**The fixes, in order of effectiveness:**

1. **Automate issuance and renewal** (S4.4, S4.8) — ACME, ACM, cert-manager. **This is the answer**; everything else is mitigation.
2. **Short lifetimes force automation** (S4.6) — a 90-day certificate cannot be manually managed at scale, which is the design intent, and the industry is moving to 47 days by 2029.
3. **Inventory** (S3.8) and **monitoring with real lead time** (S3.9) as the backstop.
4. **Named ownership** for anything not automated.

**S4 items cross-reference throughout because the answer to this item is essentially "do S4".**

---

## S4. ACME, Let's Encrypt & automation

**S4.1 — How ACME works**

The protocol, end to end:

1. **Account creation** — the client generates an **account key** and registers it with the CA. This key identifies the account for all subsequent requests and is distinct from any certificate key.
2. **Order** — the client requests a certificate for a set of identifiers (domain names).
3. **Authorisation and challenges** — the CA responds with an authorisation per identifier, each offering challenge types (S4.2). The client picks one.
4. **Challenge preparation** — the client provisions whatever the challenge requires: a file at a well-known HTTP path, or a DNS TXT record. **The value includes a key authorisation derived from the account key**, which is what binds the challenge to the requesting account.
5. **Validation** — the client tells the CA it's ready; the CA fetches the file or queries DNS, **from multiple network vantage points** (multi-perspective validation, added to resist BGP hijacking).
6. **Finalise** — with authorisations valid, the client submits a **CSR** (S2.5) and the CA issues.
7. **Download** — the client retrieves the certificate and chain.
8. **Renewal** — the same flow, run automatically well before expiry (typically at one third of the lifetime remaining).

**Why it matters as a design**: the whole protocol exists to make issuance **fully automatable with no human step**, which is what makes short lifetimes viable (S4.6) and what removes the class of outage in S3.12. **ACME is now supported by many CAs**, not just Let's Encrypt — ZeroSSL, Google Trust Services, Buypass, and internally by step-ca, Vault, and cert-manager's ACME issuer.

**S4.2 — HTTP-01 vs DNS-01 vs TLS-ALPN-01**

- **HTTP-01** — serve a token at `http://<domain>/.well-known/acme-challenge/<token>`. The CA fetches it over **plain HTTP on port 80**. Simple, and it requires the CA to reach your server publicly.
- **DNS-01** — publish a TXT record at `_acme-challenge.<domain>`. **Requires API access to your DNS provider**, and is the only option for the cases below.
- **TLS-ALPN-01** — present a special certificate during a TLS handshake on **port 443** using the `acme-tls/1` ALPN protocol. Requires no port 80 and no HTTP path, but must be handled by the TLS terminator itself.

**When each is the only option:**

| Situation | Only option | Why |
|---|---|---|
| **Wildcard certificate** | **DNS-01** | HTTP-01 proves control of one hostname; a wildcard covers arbitrary ones (S4.3) |
| Port 80 blocked or unavailable | DNS-01 or TLS-ALPN-01 | HTTP-01 requires port 80 specifically |
| Host not publicly reachable | DNS-01 | The CA can't connect inbound at all |
| Certificate for an internal-only name | DNS-01 (with public DNS) | Same |
| Only port 443 open, no HTTP handling | TLS-ALPN-01 | Handled in the TLS layer |
| No DNS API access | HTTP-01 or TLS-ALPN-01 | DNS-01 needs automation |

The practical notes: **HTTP-01 follows redirects**, so an HTTP-to-HTTPS redirect is fine as long as the path resolves. **DNS-01 is affected by propagation delay** (S4.7) and by low-TTL requirements. And **`CNAME` delegation** is the elegant DNS-01 pattern: `_acme-challenge.example.com` CNAMEs to a record in a separate zone dedicated to ACME, so **the automation credential only has write access to that zone rather than to your production DNS** — a genuinely valuable least-privilege technique (S9.1).

**S4.3 — DNS-01 for a wildcard, and why HTTP-01 can't**

**A wildcard certificate for `*.example.com` asserts validity for every possible subdomain** — including ones that don't exist yet, and ones that resolve to hosts you don't control.

**HTTP-01 proves control of a specific hostname** by demonstrating you can serve content at that name. **To prove control of `*.example.com` via HTTP you would have to serve the challenge at every possible subdomain**, which is infinite and therefore impossible. There is no HTTP request the CA can make that proves control over the wildcard space.

**DNS-01 proves control of the zone itself.** Publishing a TXT record at `_acme-challenge.example.com` demonstrates authority over `example.com`'s DNS — **and whoever controls the zone controls every name within it, including all subdomains.** That's exactly the right proof for a wildcard, and it's why the CA/Browser Forum requires DNS-01 for wildcards.

```bash
certbot certonly --dns-route53 \
  -d "example.com" -d "*.example.com"
```

The operational notes: **the wildcard and the apex need separate SANs** (S2.8). **The DNS credential is powerful** — it can modify your zone — so scope it tightly, ideally with the CNAME delegation trick (S4.2) so it can only write to a dedicated ACME zone. And **DNS propagation must complete before validation**, which is the main source of renewal failures (S4.7).

**S4.4 — Configuring certbot with renewal hooks**

```bash
certbot certonly \
  --dns-route53 \
  -d api.example.com -d "*.api.example.com" \
  --email ops@example.com --agree-tos --non-interactive \
  --deploy-hook /usr/local/bin/reload-services.sh
```

```bash
#!/usr/bin/env bash
# /usr/local/bin/reload-services.sh — runs only when a certificate was actually renewed
set -euo pipefail
nginx -t && systemctl reload nginx
systemctl reload haproxy
# push to anything that needs a copy
aws acm import-certificate --certificate-arn "$ARN" \
  --certificate fileb://"$RENEWED_LINEAGE"/cert.pem \
  --private-key fileb://"$RENEWED_LINEAGE"/privkey.pem \
  --certificate-chain fileb://"$RENEWED_LINEAGE"/chain.pem
```

**The hook types, and the distinction matters:**

- **`--pre-hook`** — before renewal is attempted. Used to open a firewall or stop a service occupying port 80.
- **`--deploy-hook`** — **only when a certificate was actually renewed.** This is the one you want for reloads: it doesn't fire on the twice-daily no-op runs.
- **`--post-hook`** — after every attempt, renewed or not. Used to undo a pre-hook.

**Renewal runs automatically** via a systemd timer or cron installed by the package, typically twice daily, renewing when within 30 days of expiry.

The essentials: **`$RENEWED_LINEAGE`** is the environment variable giving the certificate directory in a deploy hook. **Reload, don't restart** (S3.10). **Test with `certbot renew --dry-run`**, which uses staging and exercises the whole path including hooks (S4.5). And **monitor that renewal is happening** (S3.9) — a broken hook means the certificate renews and the service keeps serving the old one, which is a silent failure that surfaces at expiry.

**S4.5 — Let's Encrypt rate limits and staging**

The limits that bite:

- **50 certificates per registered domain per week** — the main one. Counted against the registrable domain (`example.com`), so all subdomains share it.
- **5 duplicate certificates per week** — the same exact set of names. **This is the one that catches you when debugging**: repeatedly retrying a failing configuration for the same names exhausts it in five attempts, and then you're locked out for a week.
- **300 new orders per account per 3 hours.**
- **5 failed validations per account per hostname per hour** — hit while debugging a challenge.
- **Renewals are exempt** from the certificates-per-domain limit, which is what makes automated renewal safe.

**The staging environment is the answer:**

```bash
certbot certonly --staging -d api.example.com ...
certbot renew --dry-run     # uses staging automatically
```

**Staging has vastly higher limits and issues certificates from an untrusted root** — so they won't validate in a browser, which is exactly right for testing the *process* without consuming production quota.

**Use staging for**: initial setup, any configuration change, testing hooks, CI pipelines, and every ephemeral or development environment. **Switch to production only once the flow works end to end.**

The related practices: **cert-manager has a staging ClusterIssuer** for the same reason and it should be the default in non-production (S4.8); **don't destroy and recreate infrastructure that requests certificates** without staging, because ephemeral environments (TF9.9) can burn the weekly limit fast; and **the limits are per registrable domain**, so a shared organisational domain means one team's mistake affects everyone — a good argument for staging discipline as a team norm.

**S4.6 — The 90-day lifetime as a design decision**

Let's Encrypt's 90 days is deliberate, and the reasoning is the item:

1. **It forces automation.** A 90-day certificate cannot be sustainably managed by hand across an estate. **By making manual renewal impractical, the lifetime makes automation mandatory** — which eliminates the entire class of outage in S3.12. The inconvenience *is* the mechanism.
2. **It limits the damage from a compromised key.** Revocation is weak and unreliable (S2.10); **expiry is not.** A short lifetime bounds the exposure window to something concrete, and that's the real answer to the revocation problem (S5.6).
3. **It limits the damage from mis-issuance** — a fraudulently obtained certificate expires quickly.
4. **It enables agility** — a shorter lifetime means the ecosystem can change algorithms, deprecate ciphers, and roll chains faster, because the installed base turns over quickly (S4.11).

**The industry has agreed with the direction**: the CA/Browser Forum has approved a schedule reducing maximum public certificate lifetimes to **200 days in 2026, 100 days in 2027, and 47 days by March 2029**. **Let's Encrypt has begun offering 6-day certificates.** Naming that trajectory is a strong currency signal, and the implication is direct: **manual certificate management is being deliberately engineered out of existence**, so any organisation still doing it has a deadline.

The framing to give: **the objection "90 days is inconvenient" is the point.** The lifetime was chosen to make the safe practice the only practice, which is the same reasoning as short-lived cloud credentials (A1.4) and short-lived workload identity (S5.6).

**S4.7 — Debugging a failed renewal**

The systematic causes, by challenge type:

**HTTP-01:**
- **Port 80 blocked** — a firewall, a security group, or a load balancer rule added since the last successful renewal. **Very common, because someone tightened security and nobody connected it to certificates.**
- **The webroot path is wrong** or the web server doesn't serve `/.well-known/acme-challenge/`.
- **A redirect to HTTPS that fails**, or a redirect chain the CA won't follow.
- **The application intercepts the path** before the static handler.
- **File permissions** — the challenge file written but not readable by the web server user.

**DNS-01:**
- **DNS propagation hasn't completed** when the CA validates. **The most common DNS-01 failure.** Increase the propagation wait, or use a provider plugin that polls authoritative nameservers.
- **DNS API credentials expired or lost permission** — a rotated key, or an IAM policy change.
- **CNAME delegation misconfigured** (S4.2).
- **DNSSEC issues**, or a provider that's slow to publish.

**Either:**
- **Rate limits already exhausted** from previous failed attempts (S4.5).
- **The account key was lost** or the account deactivated.
- **CAA records** now forbid the CA (S2.11) — someone added CAA for a different CA.
- **The domain no longer resolves** or was moved to a different zone.

**The diagnostic sequence:**

```bash
certbot renew --dry-run                    # reproduce against staging
journalctl -u certbot                      # or /var/log/letsencrypt/letsencrypt.log
curl -v http://example.com/.well-known/acme-challenge/test    # HTTP-01 reachability
dig +short TXT _acme-challenge.example.com @8.8.8.8           # DNS-01 propagation
dig CAA example.com
```

**The meta-point: automated renewal fails silently.** The certificate simply doesn't renew, and nothing surfaces until expiry. **This is exactly why S3.9's monitoring is still required even when renewal is automated** — the alert is what turns a silent failure into a ticket with weeks of margin.

**S4.8 — cert-manager in Kubernetes**

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata: { name: letsencrypt-prod }
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@example.com
    privateKeySecretRef: { name: letsencrypt-prod-account-key }
    solvers:
      - dns01:
          route53:
            region: eu-west-1
            # auth via IRSA — no static credentials (A2.7)
        selector:
          dnsZones: ["example.com"]
      - http01:
          ingress: { ingressClassName: nginx }
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata: { name: api-tls, namespace: payments }
spec:
  secretName: api-tls                    # the kubernetes.io/tls Secret it creates
  issuerRef: { name: letsencrypt-prod, kind: ClusterIssuer }
  dnsNames: ["api.example.com", "*.api.example.com"]
  duration: 2160h                        # 90d
  renewBefore: 720h                      # renew at 30d remaining
  privateKey: { algorithm: ECDSA, size: 256, rotationPolicy: Always }
```

**The concepts:**

- **Issuer** — namespaced; **ClusterIssuer** — cluster-wide. **Use ClusterIssuer for shared CAs**, so application teams don't each configure ACME credentials (K13.4's platform contract).
- **Certificate** — the desired state; cert-manager reconciles it into a TLS Secret (K1.4's controller pattern).
- **Ingress annotation shortcut** — `cert-manager.io/cluster-issuer: letsencrypt-prod` on an Ingress creates the Certificate automatically, which is the common path.
- **Issuer types beyond ACME**: `ca` (an internal CA from a Secret, S5.2), `vault`, `venafi`, and **AWS Private CA** via an external issuer (A10.18).

The operational points: **use IRSA or Pod Identity for the DNS-01 credential** (A2.7), not a static key. **`rotationPolicy: Always`** generates a new private key on each renewal — otherwise the key is reused indefinitely, which defeats part of the point of rotation. **Use the staging ClusterIssuer in non-production** (S4.5). And **monitor `certmanager_certificate_expiration_timestamp_seconds`** (S3.9), because cert-manager can fail silently too.

**S4.9 — Debugging a cert-manager certificate stuck pending**

**The diagnostic chain follows cert-manager's resource hierarchy**, and knowing the chain is most of the answer:

```
Certificate → CertificateRequest → Order → Challenge
```

```bash
kubectl describe certificate api-tls -n payments
kubectl get certificaterequest -n payments
kubectl describe certificaterequest <name> -n payments
kubectl get order -n payments
kubectl describe order <name> -n payments
kubectl get challenge -n payments
kubectl describe challenge <name> -n payments      # ← the actual reason is usually here
kubectl logs -n cert-manager deploy/cert-manager
```

**`kubectl describe challenge` is where the real error is** — the other resources report "waiting for the child" and only the Challenge names the validation failure. People stop at the Certificate and see nothing useful.

**The common causes:**

- **HTTP-01 challenge unreachable** — the solver Ingress isn't routing, the ingress class is wrong, the DNS name doesn't point at the cluster, or a NetworkPolicy blocks it (K4.10).
- **DNS-01 credential problems** — IRSA role misconfigured, missing Route53 permissions, or the wrong hosted zone.
- **DNS not propagated** (S4.7).
- **`dnsZones` selector doesn't match**, so no solver is selected and it waits forever.
- **Rate limited** (S4.5) — the Order shows a 429 from the ACME server.
- **CAA records** forbidding the CA.
- **The Ingress class annotation** missing, so the solver Ingress isn't picked up (K4.7's silent-failure pattern).
- **cert-manager's own RBAC** insufficient to create the solver resources.

The habit to state: **work down the chain, and read the Events on each resource** (K9.2). cert-manager's status conditions are informative once you know where to look, and the whole diagnostic is mechanical rather than intuitive.

**S4.10 — ACME vs ACM vs an internal CA, per environment**

| | ACME (Let's Encrypt) | AWS ACM | Internal CA |
|---|---|---|---|
| Trust | Public, universal | Public, universal | Only where the root is distributed |
| Cost | Free | Free with AWS services | Private CA charges + operational cost |
| Automation | Excellent (S4.1) | Fully automatic | Depends on what you build |
| Key export | Yes | **No** — key stays in AWS | Yes |
| Where it can be used | Anywhere | **Only AWS-integrated services** | Anywhere |
| Internal names | Only with public DNS (DNS-01) | Only public DNS | **Any name** |
| CT exposure | Yes (S2.11) | Yes | **No** |
| Client certificates | No | No (ACM PCA yes) | **Yes** |

**Choosing per environment:**

- **Public-facing on AWS** → **ACM.** Free, fully automatic renewal, and the private key is never exposed. The constraint — no export — is a feature, and the limitation is that it only works with ALB, CloudFront, API Gateway, and similar (A8.6).
- **Public-facing not on AWS, or on EC2/Kubernetes** → **ACME via cert-manager or certbot.**
- **Internal service-to-service with internal names** → **internal CA** (S5.1). ACME can't issue for names that don't resolve publicly, and you don't want internal hostnames in CT logs.
- **mTLS client identity** → **internal CA** — public CAs don't issue workload identity certificates.
- **Development** → self-signed or `mkcert` (S2.13), or ACME staging.

**The hybrid that most organisations end up with, and it's the right answer**: **ACM or ACME at the public edge** (where trust must be universal), **internal CA behind it** (where you control both ends and want workload identity). Which is also the natural fit for TLS termination at the edge with re-encryption behind (S5.9).

**S4.11 — What breaks when a CA changes its chain**

**The canonical example**: Let's Encrypt's cross-signed chain via IdenTrust's **DST Root CA X3 expired on 30 September 2021.** Clients with **ISRG Root X1** in their trust store were fine; clients without it — **older Android, OpenSSL 1.0.2, some Java versions** (S2.4) — suddenly rejected every Let's Encrypt certificate. Nothing changed on the servers. Certificates were valid. **Millions of clients broke simultaneously.**

**What breaks:**

- **Clients whose trust store lacks the new root** (S2.4) — the failure is at the client, so you cannot fix it server-side beyond serving a different chain.
- **Pinned clients** (S2.12) — if they pinned to the old intermediate or root, they break absolutely.
- **Chain files assembled manually** and never updated (S3.4) — the server keeps sending an expired or superseded intermediate.
- **Anything with an embedded, hardcoded CA bundle** — containers built long ago, embedded devices, appliances.
- **Truststores that nobody updates** — the JVM's `cacerts` on a system that hasn't been patched.

**How to prepare:**

- **Watch the CA's announcements.** Chain changes are announced well in advance — the DST X3 expiry was known for years.
- **Know your client population.** If you serve old Android or embedded devices, chain changes are a planned migration, not a non-event.
- **Keep CA bundles updated** — `ca-certificates` package updates, JDK updates, container base image rebuilds (S8.6). **The rebuild cadence argument applies directly here.**
- **Test with an old client** before the change takes effect.
- **Choose the chain deliberately where the CA offers options** — Let's Encrypt offered both the cross-signed and the short chain, and the choice traded old-client compatibility against chain length.
- **Don't pin** (S2.12), or pin with backups.
- **For an internal CA**, the equivalent is your own root rotation (S5.2) — and **distributing a new root to every trust store before it's needed is a long project**, which is one of the strongest arguments for taking the internal CA decision seriously (S5.3).

---

## S5. Internal PKI & mTLS

**S5.1 — When an internal CA is warranted**

**The cases where a public CA cannot serve:**

- **Internal hostnames that don't resolve publicly** — `payments.svc.cluster.local`, `db-primary.internal`. A public CA will not issue for a name it cannot validate control of (S4.2).
- **Client certificates for workload identity** (S5.4) — public CAs don't issue identity certificates for services.
- **Avoiding Certificate Transparency exposure** (S2.11) — internal hostnames in a public CT log are free reconnaissance.
- **Very short lifetimes** — hours or minutes (S5.6), which public CAs don't offer and which rate limits would prevent anyway (S4.5).
- **Air-gapped or disconnected environments** where ACME cannot reach a CA.
- **High issuance volume** — a service mesh issuing per-workload certificates continuously would exceed any public CA's rate limits.
- **Custom certificate content** — specific EKUs, name constraints, or SPIFFE URI SANs (S5.8).
- **Regulatory requirements** for control over the issuing authority.

**When it's not warranted, and this is the more useful half:**

- **Public-facing services** — use a public CA. Always.
- **Internal services with public DNS names** — ACME with DNS-01 works fine (S4.2), and it avoids the entire distribution problem. **Weigh this against CT exposure**, but for many organisations it's the pragmatic choice.
- **A handful of internal endpoints** — the operational burden of a CA (S5.3) exceeds the benefit; self-signed with explicit trust may be honest and adequate (S2.13).

The framing: **an internal CA is infrastructure with a long life and a real cost.** The question is whether you have a requirement a public CA genuinely cannot meet, and the two that most often make the case are **workload identity for mTLS** and **short-lived certificates at volume** — both of which point at a service mesh or SPIFFE (S5.7, S5.8) rather than at a hand-built CA.

**S5.2 — Standing up a private CA and distributing the root**

**The design:**

- **An offline root** (S2.3) — generated in a ceremony, key in an HSM or at minimum encrypted and stored offline, long-lived (10–20 years), used only to sign intermediates.
- **Online intermediates** — one per environment or purpose, shorter-lived (1–5 years), doing all leaf issuance.
- **Name constraints** on the intermediate where possible (S2.9), so it can only issue for your domains — which limits damage if it's compromised.
- **Automated issuance** — this is not optional at any scale.

**The options rather than hand-rolling with `openssl`:**

- **AWS Private CA** (A10.18) — managed, integrates with ACM and cert-manager, and expensive per CA per month.
- **HashiCorp Vault PKI** — a very good fit: short-lived certificates issued via API, with roles constraining what each caller may request.
- **smallstep `step-ca`** — open source, ACME-capable, designed for internal PKI with short lifetimes.
- **cert-manager with a `ca` Issuer** for a Kubernetes-only scope (S4.8).

**Distributing the root — and this is the hard part:**

- **Linux**: place in `/usr/local/share/ca-certificates/` and run `update-ca-certificates`; bake into base images (S7.6).
- **Containers**: into the base image, or mounted — **and every image needs it**, which is why a golden base image matters.
- **JVM**: `keytool -importcert` into `cacerts` — **separate from the OS store** (S2.4), and a frequent gap.
- **Kubernetes**: a ConfigMap mounted into pods, or a trust-distribution operator (`trust-manager`).
- **macOS/Windows**: MDM-managed.
- **Language runtimes** — Python's `certifi`, Node's bundle, Go's — each may need explicit handling.

**The point to make: distribution is the project.** Getting a new root into every trust store across an estate — including systems you'd forgotten, third-party appliances, and partner integrations — takes months, and it's why root rotation must be planned years ahead (S4.11).

**S5.3 — The operational burden an internal CA creates**

The honest list, because this is what the item is asking for:

- **You are now a CA.** The availability of your issuance path determines whether services can start, renew, and communicate. **An outage of your CA is eventually an outage of everything using it.**
- **Root and intermediate key protection** — HSM or equivalent, ceremonies, backups, and access control. **Losing the root key is unrecoverable; leaking it is catastrophic** (S3.11).
- **Trust distribution, forever** (S5.2) — every new platform, image, runtime, and partner needs the root.
- **Root and intermediate rotation** — a multi-year programme requiring the new root distributed everywhere before the old one expires (S4.11). **This is the burden people don't anticipate**, and an internal CA whose root expires with no successor distributed is a total outage.
- **Revocation infrastructure** — CRL or OCSP that clients can reach, with its own availability requirements (S2.10). **Or you avoid it entirely with short lifetimes** (S5.6), which is the better answer.
- **Issuance automation and its authorisation model** — who may request a certificate for which identity, which is an access control problem in its own right.
- **Inventory and monitoring** (S3.8, S3.9) for internal certificates too.
- **Expertise** — someone must understand this, and it's a specialist area with a small blast radius of knowledge.

**The mitigations**: **use a managed or well-supported implementation** (S5.2) rather than `openssl` scripts; **use short lifetimes** so revocation infrastructure is unnecessary; **automate issuance completely**; and **consider whether a service mesh** (S5.7) or **SPIFFE/SPIRE** (S5.8) gives you what you need with the PKI as an implementation detail you don't operate directly.

The judgement to express: **an internal CA is justified by a genuine requirement (S5.1), and the cost is a permanent operational commitment.** Standing one up as a side project and leaving it unmaintained produces the worst outcome — a critical dependency nobody owns.

**S5.4 — mTLS: what both sides present and verify**

In ordinary TLS, **the server presents a certificate and the client verifies it.** The client is unauthenticated at the TLS layer.

**In mutual TLS, both directions happen:**

1. **Server presents** its certificate; **client verifies** it: chains to a trusted root (S2.2), within validity, name matches (S2.7), EKU includes `serverAuth` (S2.9), not revoked.
2. **Server requests** a client certificate.
3. **Client presents** its certificate and **proves possession of the private key** by signing the handshake transcript.
4. **Server verifies** it: chains to a CA the server trusts (**often a different CA from the one that signed the server's own certificate**), within validity, EKU includes `clientAuth`, not revoked — **and then authorises based on the identity in the certificate** (the subject, a SAN, or a SPIFFE URI).

**The properties this gives:**

- **Cryptographic client authentication** with no shared secret and no password.
- **Identity that travels with the connection**, usable for authorisation.
- **Mutual assurance** — neither side talks to an unauthenticated peer.

**The points that matter operationally:**

- **Verification and authorisation are different steps.** A valid certificate from your CA means the client is *some* known workload; **deciding whether that workload may access this endpoint is a separate decision** based on the identity. Conflating them means any client with a certificate from your CA can reach anything — which is a very common mTLS deployment weakness.
- **Both sides need a trust store containing the issuing CA**, and rotating that CA requires the ordering in S3.10.
- **Client certificates need their own lifecycle** — issuance, renewal, monitoring — and they're the ones most often forgotten (S3.9).

**S5.5 — Configuring mTLS and debugging a rejected client certificate**

```nginx
server {
    listen 443 ssl;
    ssl_certificate     /etc/ssl/certs/server-fullchain.pem;
    ssl_certificate_key /etc/ssl/private/server.key;

    ssl_client_certificate /etc/ssl/certs/client-ca.pem;   # CA that signs clients
    ssl_verify_client on;                                   # or optional
    ssl_verify_depth 2;

    location / {
        proxy_set_header X-Client-DN $ssl_client_s_dn;      # pass identity upstream
        proxy_pass http://backend;
    }
}
```

```bash
# client side
curl --cert client.crt --key client.key --cacert server-ca.pem https://api.internal/

# see the negotiation
openssl s_client -connect api.internal:443 \
  -cert client.crt -key client.key -CAfile server-ca.pem
```

**Debugging a rejected client certificate — the causes in order:**

1. **The server doesn't trust the client's issuing CA.** Check `ssl_client_certificate` contains the right CA, **including intermediates** if the client cert chains through one (S2.2) — a missing intermediate on the client side is the mTLS version of S3.5.
2. **The client isn't sending a certificate at all.** With `ssl_verify_client optional`, this fails at the application layer instead; with `on`, at the handshake. **`openssl s_client` output shows whether a certificate request was made and what was sent.**
3. **Wrong EKU** — the client certificate lacks `clientAuth` (S2.9). **A common error when someone reuses a server certificate as a client certificate**, and the rejection message rarely names the reason.
4. **Expired** — on either side, and client certificates are the ones nobody monitors (S3.9).
5. **`ssl_verify_depth` too shallow** for the chain.
6. **Revoked**, if CRL checking is configured.
7. **Verified but not authorised** (S5.4) — the handshake succeeded and the application rejected the identity, which looks like a TLS failure to the user but is a 403.

**The diagnostic that resolves most of it**: `openssl s_client` with `-cert` and `-key`, reading the `Acceptable client certificate CA names` in the output — **that tells you exactly which CAs the server will accept**, and comparing it to your client certificate's issuer usually ends the investigation immediately.

**S5.6 — Short-lived certificates as an alternative to revocation**

**The argument**: revocation doesn't work reliably (S2.10) — soft-fail, inconsistent client support, and browsers largely abandoning it. **So stop depending on it.**

**If a certificate is valid for 24 hours, or one hour, the exposure window from a compromise is bounded by expiry rather than by a revocation mechanism that may never be consulted.** Revocation becomes unnecessary because the certificate invalidates itself, on a schedule, automatically.

**What it requires:**

- **Fully automated issuance and renewal** — at these lifetimes there is no manual option, which is also the point (S4.6).
- **A CA that can sustain the issuance rate** — an internal CA (S5.2) or a mesh's built-in CA, not a public one.
- **Reliable renewal**, because a failed renewal is an outage within hours rather than a warning within weeks. **The failure mode is faster and less forgiving**, and that's the honest tradeoff.
- **Clocks in reasonable sync**, because tight validity windows are sensitive to skew.

**What it buys beyond revocation:**

- **A compromised key has a short useful life.**
- **Key rotation happens continuously** rather than as an event.
- **Deprovisioning is automatic** — a workload that's gone simply stops renewing, so its identity expires. **No offboarding step is required**, which is a genuine operational simplification.

**The implementations**: **Istio and Linkerd issue workload certificates with 24-hour or shorter lifetimes and rotate them transparently** (S5.7); **SPIRE** issues short-lived SVIDs (S5.8); **Vault PKI** with short TTLs; **AWS IAM Roles Anywhere** for a similar pattern outside the mesh.

The framing: **this is the same argument as short-lived cloud credentials** (A1.4, A2.8) — the industry's answer to credential compromise is not better revocation, it's shorter lifetimes, and PKI has arrived at the same conclusion.

**S5.7 — How a service mesh handles identity and mTLS**

The mesh (Istio, Linkerd) provides:

- **A built-in CA** — Istio's `istiod`, Linkerd's identity service — issuing a certificate to every workload.
- **Identity derived from the platform** — the Kubernetes ServiceAccount, encoded as a **SPIFFE URI SAN** (S5.8): `spiffe://cluster.local/ns/payments/sa/api`.
- **Automatic issuance and rotation** with short lifetimes (S5.6) — typically 24 hours, rotated transparently with no application involvement.
- **Transparent mTLS** — the sidecar (or per-node proxy in Istio's ambient mode) terminates and originates TLS. **The application speaks plaintext to localhost and knows nothing about certificates.**
- **Authorisation policy** on the verified identity — `AuthorizationPolicy` in Istio, expressing "the payments service may call the ledger service on this path".

**Why this is the compelling answer to the mTLS problem** (K4.13): the hard parts of mTLS are **identity bootstrapping, issuance at scale, rotation, distribution, and per-workload authorisation** — and the mesh solves all of them without touching application code. **Doing this yourself for fifty services is a substantial project; the mesh makes it a configuration setting.** In a regulated environment where "encryption in transit between all services" is a control (A10.31), it's often the only tractable way to satisfy it.

**The costs, which must be named** (K4.13): latency per hop; a sidecar per pod consuming cluster resources; **the mesh becomes a critical component in every request path**, with its own upgrades, failure modes, and debugging surface; and a steep learning curve for the whole team. **Istio's ambient mode** removes the per-pod sidecar and materially changes the resource side of that calculation — worth naming as current.

**The judgement**: adopt a mesh when mTLS everywhere is a genuine requirement across many services. For a handful of services, cert-manager plus application-level TLS is less machinery for the same outcome.

**S5.8 — SPIFFE/SPIRE workload identity**

**SPIFFE** (Secure Production Identity Framework For Everyone) is a specification; **SPIRE** is the reference implementation.

**The concepts:**

- **SPIFFE ID** — a URI identifying a workload: `spiffe://acme.com/ns/payments/sa/api`. **Platform-agnostic** — the same scheme works for Kubernetes pods, VMs, and bare metal.
- **SVID** (SPIFFE Verifiable Identity Document) — the credential carrying the ID, either an **X.509 certificate** with the SPIFFE ID as a URI SAN, or a **JWT**.
- **Workload API** — a local endpoint (a Unix socket) where a workload fetches its SVID **with no credential of its own.**

**The bootstrapping problem and how it's solved** — this is the interesting part and the thing to explain:

**How does a workload prove who it is, in order to get a credential, without already having a credential?** SPIRE solves it with **attestation**:

- **Node attestation** — the SPIRE agent proves the node's identity using something the platform provides: an AWS instance identity document, a TPM, a Kubernetes node token.
- **Workload attestation** — when a process calls the Workload API, the agent inspects it **out of band**: its Unix UID and path, or its Kubernetes pod and ServiceAccount via the kubelet. **The workload doesn't assert its identity; the agent determines it from the platform.** That's what makes it unforgeable — the credential is derived from properties the workload cannot lie about.

**Why it matters conceptually**: it's **a uniform identity layer across heterogeneous infrastructure.** A workload on EC2, a pod in Kubernetes, and a service on-premises all get an identity in the same namespace, with the same verification, usable for mTLS and for federation to cloud IAM. **That's the value over a mesh's built-in identity**, which is Kubernetes-scoped.

The relationship to what you already know: **IRSA is conceptually the same pattern** (A2.7) — the platform attests the workload, and the workload exchanges that attestation for a credential. SPIFFE generalises it beyond one cloud.

**S5.9 — TLS termination vs passthrough vs re-encryption**

- **Termination (offload)** — TLS ends at the load balancer; traffic to the backend is **plaintext**.
- **Passthrough** — the load balancer forwards the encrypted stream without decrypting; **TLS ends at the backend**.
- **Re-encryption (bridging)** — the load balancer decrypts, inspects or modifies, then **establishes a new TLS connection to the backend.**

| | Termination | Passthrough | Re-encryption |
|---|---|---|---|
| Backend leg encrypted | **No** | Yes | Yes |
| LB can inspect / route on L7 | Yes | **No** | Yes |
| Certificate management | At the LB only | At every backend | Both |
| WAF, path routing, header injection | Yes | **No** | Yes |
| End-to-end encryption claim | **No** | Yes | Not literally — decrypted at the LB |

**The security tradeoff:**

- **Termination** is simplest and centralises certificate management — **and the backend leg is plaintext.** Whether that's acceptable depends on the network: within a private VPC subnet it's a common and defensible choice; **it is the gap that architecture diagrams hide** (A10.31), and it fails a strict "encryption in transit everywhere" control.
- **Passthrough** gives true end-to-end encryption and **gives up every L7 capability** — no path-based routing, no WAF (A8.8), no header manipulation, no HTTP-level observability. It also means certificate management on every backend (S3.7). Used where the requirement is that the load balancer must not see the plaintext at all.
- **Re-encryption** is the usual answer for a regulated environment: L7 features at the edge, encrypted on the internal leg. **The honest caveat: the traffic is decrypted at the load balancer**, so if the requirement is genuinely that no intermediary can read it, re-encryption doesn't satisfy it.

The practical guidance: **terminate at the edge for public traffic (public CA, S4.10), re-encrypt to the backend using an internal CA** (S5.1) — which is also the natural shape when a service mesh handles the internal leg (S5.7). **And know which one you're actually running**, because "we use TLS" frequently means termination with a plaintext backend leg that nobody has examined.

---

## S6. Secrets in practice

Services are A10; this section is the practice and the failure modes.

**S6.1 — Why environment variables are still a compromise**

Environment variables are the twelve-factor recommendation and are much better than hardcoding — **and they leak in ways people don't anticipate:**

- **Visible to the whole process tree.** Any child process inherits them, so a shell-out to a subprocess passes your secrets along.
- **Readable from `/proc/<pid>/environ`** by the same user or root on the host.
- **`docker inspect` and `kubectl describe pod` show them in plaintext** — so anyone with read access to the orchestrator has the secrets, regardless of how carefully the Secret was managed (K3.4).
- **Crash dumps and error reporters include the environment.** Sentry, Rollbar, and similar tools capture environment variables by default — **so a crash sends your database password to a third-party SaaS**, which is a genuinely common and under-appreciated leak.
- **Logged by debug output** — frameworks that print configuration at startup, and `env` in a CI script (S6.7).
- **Fixed at process start**, so rotation requires a restart (A7.8, S6.5).
- **In Kubernetes, they're in the pod spec**, so they appear in the API, in etcd, and in anything that mirrors the spec — including GitOps repositories if not handled carefully (K10.11).

**The better options, in order:**

1. **Fetch at runtime from a secret store** using workload identity (S6.2) — the secret exists only in the process's memory.
2. **Mounted files** (tmpfs) rather than environment variables — not in `describe`, not inherited by children, not in crash dumps, and **they can be updated in place** for rotation (K3.2, K3.6).
3. **Environment variables** — acceptable, with the leak paths understood and controlled.

The framing: **environment variables are a reasonable default and a poor destination for high-value secrets.** For a database password in a regulated environment, the file-mount or runtime-fetch options are meaningfully better and not much harder.

**S6.2 — Getting a secret to a workload without an image or repo**

**The bootstrapping principle: the workload authenticates with an identity the platform gives it, and exchanges that for the secret.** No credential is baked in, because the platform vouches for the workload (S5.8's attestation argument).

The mechanisms:

- **AWS**: **IRSA or EKS Pod Identity** (A2.7) gives the pod an IAM role; the application calls Secrets Manager or Parameter Store directly (A10.21). **Nothing is stored anywhere.**
- **Kubernetes**: **Secrets Store CSI Driver** mounts secrets from an external store as files — **the value never becomes a Kubernetes Secret and never touches etcd** (K3.6), which is the strongest posture. Or **External Secrets Operator**, which syncs into native Secrets — more compatible, and the secret does land in etcd.
- **Vault**: the Kubernetes auth method, or the agent injector sidecar, using the ServiceAccount token to authenticate.
- **EC2**: the instance profile (A2.6) to fetch from Secrets Manager.
- **CI**: **OIDC to assume a role** (A2.8, S7.9), then fetch — no static credentials in the CI system at all.

**What never to do**: bake into an image (it's in the registry, in every layer, and in the layer cache — S7.6); commit to a repo (S6.3); or pass on a command line (visible in `ps`).

**The considerations to raise:**

- **Availability** — the secret store is now in your pod startup path (K3.6). A Secrets Manager outage means pods can't start. Cache with a bounded TTL and understand the failure behaviour.
- **Rotation** — the workload must re-fetch on auth failure, not cache at startup (S6.5).
- **Cost** — a per-invocation `GetSecretValue` on a high-volume Lambda is a real KMS and API bill (A10.14).

**S6.3 — Scanning a repo and its history for secrets**

```bash
# history scanning
gitleaks detect --source . --report-format json --report-path leaks.json
trufflehog git file://. --only-verified          # verifies the credential is live
git secrets --scan-history

# pre-commit prevention
detect-secrets scan --baseline .secrets.baseline
```

**The tools and their differences:**

- **gitleaks** — fast, regex and entropy based, good CI integration.
- **TruffleHog** — **verifies findings by attempting to use the credential**, which dramatically reduces false positives and tells you which leaked secrets are still live. That verification step is its distinguishing feature and is genuinely valuable for triage.
- **detect-secrets** — baseline-oriented, designed to be adopted on an existing repo with existing findings without blocking everything.
- **Platform-native** — GitHub secret scanning with **push protection** (blocks the push), and partner integration where the provider is notified and can auto-revoke.

**The layers that actually work:**

1. **Pre-commit hook** — cheapest and stops it at source, and it's bypassable, so it isn't sufficient.
2. **Server-side push protection** — not bypassable by the developer, which is why it's the important one.
3. **CI scanning** on every PR.
4. **Periodic full-history scanning** of every repo, which finds what predates the controls.

**The critical point about history**: scanning the working tree is not enough. **A secret committed and then deleted in a later commit is still in the history, still clonable, and still compromised.** History scanning is the whole point, and the finding is often years old.

**S6.4 — Responding to a committed secret**

**The order is the item, and it's counterintuitive to most people: rotate first, clean history second.**

1. **Rotate the credential immediately.** Assume it is compromised the moment it was pushed. **Cleaning history does not un-leak it** — the repository may have been cloned, forked, mirrored, cached by GitHub, indexed by a scanner, or already harvested. Automated scanners find committed AWS keys within **minutes**.
2. **Assess exposure** — what could the credential do (A10.30)? Was the repo public or private? How long was it there? Check logs for use of it: CloudTrail for an AWS key, access logs for an API token.
3. **Investigate for actual use** — new resources, unusual API calls, data access, persistence mechanisms (A10.30's step 3 — an attacker who created a second credential survives your rotation of the first).
4. **Then clean the history** — `git filter-repo` (the current tool; `filter-branch` is deprecated) or BFG Repo-Cleaner. **This rewrites every commit hash**, so every fork and every clone diverges, everyone must re-clone, and open PRs break. **Coordinate it.**
5. **On GitHub, the old objects may persist** in cached views and in forks even after a force-push — **contact support to purge**, and don't assume the rewrite was sufficient.
6. **Fix the cause** — why did this reach a commit? Add pre-commit hooks and push protection (S6.3), and address the workflow that made it convenient to hardcode.

**The judgement to state**: **history rewriting is disruptive and is not the remediation** — rotation is. For a large repo with many contributors, **rotating and leaving the dead credential in history is frequently the right call**, with a note explaining it. Rewriting is worth it when the secret cannot be rotated (an embedded key, a customer's credential) or when the repository will be made public.

**S6.5 — Rotating credentials that can't rotate atomically**

**The problem**: changing a credential invalidates the one running systems are using. There's a window where in-flight work fails.

**The two-credential (alternating) pattern** — the general solution:

Maintain **two valid credentials**. The system uses A. Rotation: create/enable B, verify it works, switch consumers to B, then **after a full consumer refresh cycle**, disable A. **At no point is a credential in use invalidated.**

Applied:

- **Database users** (A7.8, DB13.3) — two users with identical grants, alternating.
- **API keys** — most providers support multiple active keys precisely for this.
- **Signing keys** — publish both public keys during the overlap so consumers accept either (JWKS with multiple keys is the standard mechanism).
- **CA rotation** (S3.10) — trust both roots before issuing from the new one, which is the same shape.

**The application-side requirement that makes or breaks it**: the consumer must **re-fetch the credential on authentication failure**, not cache it at process start. **A credential cached at startup means rotation breaks the app**, and this is the most common failure (A10.21).

**When two credentials aren't possible:**

- **A brief maintenance window**, accepted deliberately.
- **Rolling restart** with the new credential, accepting per-instance disruption behind a load balancer.
- **A proxy holding the credential** (RDS Proxy, DB8.6) so rotation happens in one place.

**The better answer, and it should be stated**: **dynamic credentials remove the problem entirely** (S6.6). If credentials are issued per-session with a short life, there is nothing to rotate — the rotation problem is an artefact of long-lived credentials.

**S6.6 — Dynamic / short-lived credentials**

**Dynamic credentials are generated on demand, per consumer, with a short TTL, and expire automatically.**

The examples: **Vault's database secrets engine** creates a database user per request with a 1-hour lease and drops it on expiry; **AWS STS** issues temporary credentials via role assumption (A1.7); **IAM database authentication** issues a 15-minute token (DB13.4); **cloud workload identity** (IRSA, A2.7) refreshes automatically; **service mesh SVIDs** (S5.6).

**Why they beat rotation:**

- **There is no rotation problem** (S6.5) — credentials expire on their own, continuously, with no coordination.
- **The exposure window is bounded by the TTL**, not by how long until someone remembers to rotate. **A leaked one-hour credential is largely harmless.**
- **Per-consumer credentials mean attribution** — the audit log shows exactly which consumer did what, rather than "the shared application user".
- **Revocation is real** — revoke the lease and it's immediately invalid, which is the thing certificate revocation can't reliably do (S2.10).
- **Deprovisioning is automatic** — a workload that stops running stops renewing, and its access lapses. **No offboarding step.**

**The costs to acknowledge:**

- **The credential broker is in the critical path.** Vault or STS being unavailable means workloads can't get credentials — a new availability dependency, and it must be highly available.
- **Connection churn** — a database credential with a 1-hour TTL means connections must be re-established, which interacts badly with long-lived pools (DB8.1). Lease renewal mitigates it.
- **Operational complexity** — Vault is a substantial system to run well.
- **Not every system supports it** — legacy applications and third-party APIs often only accept a static key.

The framing: **this is the same conclusion as short-lived certificates (S5.6) and OIDC in CI (S7.9) — the industry's answer to credential compromise is to make credentials expire faster, not to manage them better.**

**S6.7 — Preventing secrets leaking into logs, errors, and CI output**

The leak paths and their controls:

- **Application logs** — a framework printing its configuration at startup; an exception handler dumping the request or the connection object; debug logging of an HTTP client including the `Authorization` header. **Control: never log whole objects — log named fields** (O4.9), plus a redacting logger and **secret-wrapper types** whose `toString` returns `[REDACTED]`, which is the most robust defence because it survives accidental logging.
- **Error reporting services** — Sentry and similar **capture environment variables and local variables by default** (S6.1). **Configure the deny-list**, and verify it, because this sends secrets to a third party.
- **CI output** — `set -x` in a shell script echoing a command containing a token; `env` or `printenv` in a debug step; a tool printing its configuration; **a failing command's error message including the URL with embedded credentials.**
- **CI secret masking** — GitHub Actions and GitLab mask registered secret values in logs, which catches variables from the secret store and **does not catch values computed at runtime** — a token derived from a secret, or a secret read from a file. Useful, not sufficient.
- **Terraform** — plan output and state (S6.9); `TF_LOG=TRACE` contains request bodies with credentials (TF6.16, TF7.8).
- **Core dumps and heap dumps** — contain everything in memory, and are frequently written to shared storage or attached to tickets.
- **Shell history** — a credential passed on a command line.

**The structural defences**: **the secret should not be in the process's environment or in a string it can print** (S6.1, S6.2); **redaction at the log collector** as a backstop (O4.5); **automated scanning of log content** for credential patterns; and **treat "a secret appeared in a log" as a leak requiring rotation** (S6.4), because the log is now in your log platform, replicated, and retained.

**S6.8 — Vault vs a cloud-native secrets service**

**Vault:**

- **Multi-cloud and on-prem** — one system across a heterogeneous estate, which is the main argument.
- **Dynamic secrets** (S6.6) — database credentials, cloud credentials, PKI (S5.2), SSH — generated on demand with leases. **This is the capability cloud services largely don't match.**
- **Rich policy language**, namespaces for multi-tenancy, and extensive auth methods.
- **Transit encryption-as-a-service** — encrypt/decrypt without exposing keys.
- **The cost: you operate it.** HA, storage backend, **unseal key management** (the operational burden people underestimate — an auto-unseal mechanism is essentially mandatory), upgrades, and it is a **tier-one dependency**: Vault down means workloads can't start. Plus the licence question since the BSL change.

**Cloud-native (AWS Secrets Manager / Parameter Store, A10.19, A10.20):**

- **Managed** — no operational burden, and highly available by default.
- **Deep IAM integration** — access control uses the same model as everything else (A2.1), and audit is in CloudTrail alongside everything else.
- **Rotation built in** for supported services (A7.8).
- **Cheap** — Parameter Store standard is free (A10.20).
- **The cost: cloud-specific**, less capable on dynamic secrets, and a weaker policy model for complex multi-tenancy.

**The decision:**

- **Single cloud, no exotic requirements → the cloud-native service.** The operational saving is substantial and the capability gap usually doesn't matter.
- **Multi-cloud, hybrid, or on-prem → Vault**, because a single control plane across the estate is worth the burden.
- **Dynamic database or cloud credentials as a genuine requirement → Vault**, since that's its strongest differentiator.
- **A regulated environment already running Vault** → keep it; migrating a secrets platform is disruptive.

The framing: **the question is whether you have a requirement the cloud service can't meet**, and for most single-cloud organisations you don't — so running Vault is a substantial cost for capability you won't use (A10.17's parallel argument about CloudHSM).

**S6.9 — Secrets in Terraform state**

**Terraform state contains the full attributes of every resource, including sensitive ones, in plaintext** (TF3.2). An RDS password, a generated `random_password`, a `tls_private_key`, an IAM access key, or a secret read via a data source — **all of it is in the state file.**

**`sensitive = true` redacts it from CLI output and plan display. It does not remove it from state** (TF7.1). This is the most consequential misunderstanding in this area — people mark a variable sensitive, see the redaction, and believe the secret is protected.

**What it implies:**

- **The state backend is a credential store** and must be secured as one (TF7.3) — encrypted with a customer-managed KMS key (A10.1), tight IAM scoped per state path, deny delete, versioning, and access logging. **Read access to the state bucket is read access to every secret in it.**
- **Never commit state to git** — and if it happened, rotate everything in it (S6.4).
- **Split state** to limit the blast radius (TF3.6) — the production database's state should not be readable by everyone who can read the DNS state.
- **`terraform_remote_state` gives the consumer read access to the entire producer state file**, not just its outputs (TF3.14) — so it hands over every secret in it. **A strong argument for data sources or a parameter store instead.**
- **Plan files contain state data** too (TF6.4), so CI artefacts need the same care (TF7.8).

**The architectural fix, which is the answer to give**: **keep the secret out of Terraform.** Use `manage_master_user_password` on RDS so the password is generated and stored in Secrets Manager without transiting state; create the *container* for a secret in Terraform and populate the *value* out of band; reference secrets by ARN and let the application resolve them at runtime (A10.21). **Terraform should manage where a secret lives, not what it is.**

Worth naming as current: **OpenTofu supports native state encryption** (TF1.8), which is a genuine differentiator on this specific problem.

---

## S7. Supply chain & pipeline security

**S7.1 — The supply chain attack surface end to end**

Walking the path from source to running workload, naming what can be attacked at each stage:

1. **Developer workstation** — compromised machine, malicious IDE extension, stolen SSH or signing key.
2. **Source repository** — compromised account (**MFA and branch protection are the controls**), a malicious commit, a compromised maintainer of a repo you depend on.
3. **Dependencies** — the largest surface. A malicious package, a compromised maintainer account, **dependency confusion** (S7.3), typosquatting, and transitive dependencies you never chose. **You typically depend on hundreds of packages and thousands transitively, maintained by strangers.**
4. **Build system** — compromised runner, a malicious CI action or plugin (S7.10, S7.11), build-time code execution (`postinstall` scripts, `setup.py`), and **cache poisoning**.
5. **Build inputs** — a base image (S7.6), a compiler, a build tool.
6. **Artefact storage** — a compromised registry, a mutable tag replaced with a different image (S7.2).
7. **Distribution** — a MITM without signature verification (S7.7).
8. **Deployment** — a compromised deploy credential, an unverified image admitted to the cluster.
9. **Runtime** — the container escaping (K8.12), a compromised sidecar.

**The instructive real incidents**: **SolarWinds** (build system compromised, malicious code inserted into a legitimately signed artefact — **signing didn't help, because the build was the attack**); **Codecov** (a modified bash uploader exfiltrating CI environment variables — every secret in every pipeline that used it); **event-stream** (a maintainer handed over an npm package to an attacker); **xz/liblzma** (a multi-year social engineering campaign to become a maintainer, nearly compromising SSH globally); and **the 2025 npm `chalk`/`debug` and Shai-Hulud incidents**, self-propagating worms stealing credentials from CI environments.

**The pattern to draw out**: **attackers target the build and the dependencies rather than the artefact**, because that's where trust is extended most freely and verified least. **Signing the output of a compromised build produces a validly signed backdoor** (S1.3) — which is why provenance and build integrity (S7.12) matter more than signing alone.

**S7.2 — Pinning dependencies and lockfiles**

**Floating versions** (`^4.2.0`, `latest`, `>=1.0`) mean **your build's inputs change without any change from you.** The consequences:

- **Builds are not reproducible** — the same commit produces different artefacts on different days, so "it worked yesterday" is unfalsifiable.
- **A compromised or malicious release is pulled automatically**, with no review. **This is the mechanism by which most dependency attacks actually reach victims** (S7.1).
- **A breaking change arrives unannounced**, and the failure is attributed to whatever else changed.

**Lockfiles** (`package-lock.json`, `yarn.lock`, `Pipfile.lock`, `poetry.lock`, `go.sum`, `Cargo.lock`, `Gemfile.lock`) record **the exact resolved version of every direct and transitive dependency, with a cryptographic hash.**

The practices:

- **Commit the lockfile.** Its absence means every build resolves fresh.
- **Install from the lockfile in CI** — `npm ci`, not `npm install`; `pip install -r requirements.txt --require-hashes`; `poetry install`. **`npm install` can update the lockfile; `npm ci` fails if it disagrees**, which is the property you want in CI.
- **Verify hashes**, which is what makes the lockfile a supply chain control rather than just a version record — a substituted package fails.
- **Update deliberately** — Renovate or Dependabot raising PRs, so an upgrade is a reviewed change with tests, rather than an ambient event.
- **Pin container base images by digest** (S7.6), not by tag — `FROM node:20-slim` is mutable; `FROM node@sha256:...` is not.
- **The same applies to CI actions** (S7.11) and Terraform modules and providers (TF4.3, TF5.4).

**The tension to acknowledge**: pinning means you don't get security patches automatically. **The resolution is automated update PRs with tests** — you get the patches, reviewed, on your schedule. Pinning without an update process is how you end up years behind (S8.7).

**S7.3 — Dependency confusion and typosquatting**

**Dependency confusion** (Alex Birsan's 2021 research, which compromised Apple, Microsoft, PayPal, and dozens of others):

Your organisation has an internal package `@acme/auth-utils`, published to a private registry. Your package manager is configured with **both** the private registry and the public one. **An attacker publishes a package with the same name to the public registry, with a higher version number.** The resolver, seeing a higher version, **fetches the attacker's package from public.** No typo, no mistake — the resolution logic does exactly what it was designed to do.

**The defences:**

- **Scoped packages with a claimed scope** — register `@acme` on npm publicly so nobody else can publish under it. **The simplest effective control.**
- **Explicit registry configuration per scope** — `@acme:registry=https://internal` so those names never resolve publicly.
- **A single upstream proxy** (Artifactory, Nexus, CodeArtifact) that fetches from public but **never allows a public package to shadow an internal name.**
- **Defensively publish placeholder packages** to the public registry under your internal names.
- **Verify with hashes** in lockfiles (S7.2) — though this only helps after the first resolution.

**Typosquatting** — publishing `reqeusts`, `python-dateutil` variants, `crossenv` (versus `cross-env`) — relies on a developer's typo or a copied-and-corrupted install command. **Defences**: an internal proxy with an allow-list, dependency scanning that flags newly-introduced packages, and review of dependency additions in PRs.

**The related pattern to name**: **starjacking** (claiming a legitimate project's repository URL to inherit its apparent reputation) and **slopsquatting** — registering package names that LLMs hallucinate, which is a genuinely current attack vector worth mentioning.

**S7.4 — Scanning dependencies and triaging by exploitability**

The tools: **Dependabot**, **Snyk**, **Trivy**, **Grype**, **OWASP Dependency-Check**, **`npm audit`/`pip-audit`/`govulncheck`**.

**Why CVSS alone is a poor prioritisation signal** (S8.1): a critical CVSS score describes the vulnerability **in the abstract, under worst-case assumptions**. Your context determines whether it matters at all.

**Triaging by exploitability — the questions that actually matter:**

1. **Is the vulnerable code path reachable?** A vulnerability in a function your application never calls is not exploitable. **`govulncheck` does reachability analysis** and typically eliminates a large fraction of findings; Snyk and others offer similar. **This is the single highest-leverage triage tool.**
2. **Is it reachable by an attacker?** A vulnerability requiring local access on a host with no untrusted users is different from one reachable from the internet.
3. **Is it in the runtime path or the build?** A dev dependency used only in tests is a lower priority — **though not zero, because CI compromise is real** (S7.10).
4. **Are the preconditions met?** Many CVEs require a specific configuration you don't use.
5. **Is there a known exploit?** **CISA KEV** (Known Exploited Vulnerabilities) and **EPSS** (Exploit Prediction Scoring System) tell you what is actually being exploited in the wild. **Anything on KEV is a genuine priority regardless of CVSS; most high-CVSS items are never exploited.**
6. **Is there a compensating control?** A WAF rule, network isolation, or a disabled feature.

**VEX (Vulnerability Exploitability eXchange)** is the emerging mechanism for recording and sharing these determinations machine-readably (S7.8), so "not affected, because the vulnerable function is not invoked" is an artefact rather than a comment in a ticket.

The framing: **an unfiltered scanner output is not a work queue** — it's a list of things to assess. **A team that treats every critical as an emergency loses the ability to respond to the one that matters** (S8.7, A10.25's argument about findings nobody triages).

**S7.5 — Scanning container images and what a scanner can't see**

```bash
trivy image --severity HIGH,CRITICAL myapp:1.4.2
grype myapp:1.4.2
docker scout cves myapp:1.4.2
```

**What a scanner does**: enumerates OS packages and language dependencies present in the image, matches them against vulnerability databases, and reports CVEs.

**What it cannot see, which is the substance of the item:**

- **Your own code.** A SQL injection or an authentication bypass in your application is invisible — that's SAST and DAST territory (S9.8). **The scanner tells you about other people's code.**
- **Vulnerabilities with no CVE** — unpublished, or in a package the database doesn't cover.
- **Misconfiguration** — running as root, an exposed port, a mounted Docker socket, weak file permissions. **Separate tooling** (Trivy's config scanning, Checkov, Docker Bench) covers this, and it's frequently a bigger real risk than the CVE list.
- **Secrets in layers** — some scanners do check, but not all, and a secret in an earlier layer persists even if deleted later (S7.6).
- **Whether the vulnerable code is reachable** (S7.4) — it reports presence, not exploitability.
- **Binaries not installed via a package manager** — something `curl`ed into the image and unpacked has no package metadata, so **it is invisible to the scanner** even if it's the most vulnerable thing present. **This is a significant blind spot** and an argument for installing via package managers.
- **Behaviour at runtime** — a compromised container behaving maliciously is runtime detection (Falco), not image scanning.
- **Base image drift** — a scan is a point in time; **an image clean today has CVEs next week** because the database changed, not the image (S8.6).

The practices: **scan at build and block on policy**; **scan continuously in the registry** (ECR enhanced scanning, A5.1) because new CVEs appear against existing images; **and reduce the surface so there's less to scan** (S7.6) — a distroless image has almost no OS packages and therefore almost no findings, which is a genuine and often dramatic reduction.

**S7.6 — Minimal images and the reduction in attack surface**

```dockerfile
# multi-stage: build with a full toolchain, ship almost nothing
FROM golang:1.23 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /app ./cmd/api

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /app /app
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

**The reduction, concretely:**

- **A typical `ubuntu`-based image has hundreds of packages**, most of which your application never uses. **Each is a potential CVE and a potential tool for an attacker.**
- **Distroless contains the runtime and your binary — no shell, no package manager, no `curl`, no `wget`, no `ls`.** An attacker with code execution **has no tooling to work with** and must bring their own, which is a genuine and meaningful obstacle.
- **No shell means no shell-based exploitation** and no `RUN` steps in your final image.
- **CVE counts frequently drop by an order of magnitude**, which also makes the remaining findings actionable rather than noise (S7.5).

**The other hardening in the same breath**: **non-root** (`USER nonroot`) so a container escape lands unprivileged (K8.7); **read-only root filesystem** at runtime; **no capabilities**; and **multi-stage builds** so build tools, source, and any credentials used during build never reach the final image.

**The layer point that matters**: **deleting a file in a later layer does not remove it from the image** — the earlier layer still contains it and it's extractable. **A secret used during build and `RUN rm`'d is still in the image** (S6.2). Multi-stage builds and BuildKit secret mounts (`--mount=type=secret`) are the correct answers.

**The cost to acknowledge**: **debugging is harder** — no shell to exec into. **The answer is ephemeral debug containers** (K9.12), which attach a full toolset to a running distroless pod without weakening the image. That pairing is the complete answer, and offering it pre-empts the objection.

**S7.7 — Signing and verifying artefacts**

```bash
# keyless signing — identity from an OIDC token, no key to manage
cosign sign --yes ghcr.io/acme/api@sha256:abc123...

# verify, constraining who signed it and from where
cosign verify ghcr.io/acme/api@sha256:abc123... \
  --certificate-identity-regexp "https://github.com/acme/.*" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# provenance attestation — how it was built, not just who signed it
cosign attest --predicate provenance.json --type slsaprovenance <image>
cosign verify-attestation --type slsaprovenance <image> ...
```

**Keyless signing (Sigstore) is the significant development**: instead of managing a long-lived signing key (S3.2), the signer authenticates with an **OIDC identity** (a GitHub Actions workflow, a Google account), **Fulcio issues a short-lived certificate** bound to that identity, the signature is made and the certificate discarded, and the signature is recorded in **Rekor**, a public transparency log. **No key to store, rotate, or leak** — the same short-lived-credential argument as S5.6 and S6.6.

**What signing proves and doesn't** (S1.3): it proves **this artefact was produced by this identity and hasn't been modified.** It does **not** prove the artefact is safe — **SolarWinds was validly signed** (S7.1). That's why **provenance attestations** matter more: they record *how* it was built — which source commit, which builder, which inputs — so verification can assert "built from our repo, by our pipeline, from commit X" rather than merely "signed by someone we trust."

**Verification must be enforced or it's decorative**: an **admission controller** in Kubernetes (Kyverno's `verifyImages`, Sigstore's policy-controller, or Connaisseur) rejecting unsigned or improperly-attested images (K8.9). **Signing without enforced verification changes nothing** — and that gap is extremely common.

**S7.8 — Generating and using an SBOM**

```bash
syft ghcr.io/acme/api:1.4.2 -o spdx-json > sbom.spdx.json
trivy image --format cyclonedx --output sbom.cdx.json myapp:1.4.2

# attach it to the image as an attestation
cosign attest --predicate sbom.cdx.json --type cyclonedx <image>

# later: what's affected by a new CVE, without rebuilding or rescanning
grype sbom:./sbom.cdx.json
```

**An SBOM is an inventory of every component in an artefact** — direct and transitive dependencies, versions, licences, and ideally hashes. **CycloneDX** and **SPDX** are the two formats.

**Using it for something real** — the value is in the questions it answers:

- **"Log4Shell just dropped — which of our 300 services contain log4j, and at what version?"** **With SBOMs stored per build, that's a query answered in minutes. Without them, it's an archaeology project across every repository and image** — and that scenario is the reason SBOMs went from a compliance checkbox to something people actually want (S8.5).
- **Licence compliance** — identifying GPL or AGPL components in a proprietary product.
- **Vulnerability scanning without the artefact** — scan the SBOM as new CVEs are published, continuously, without rebuilding.
- **Regulatory requirements** — US Executive Order 14028 for federal suppliers, and the **EU Cyber Resilience Act**, which makes SBOMs a legal requirement for products sold in the EU from 2027. **Worth naming as current, because it changes SBOMs from optional to mandatory for many organisations.**

**The practices that make them useful rather than generated-and-forgotten**: **generate at build time** (the build knows what went in; scanning the finished artefact infers it and misses things, S7.5); **store and index them centrally**, keyed by image digest; **attach as an attestation** (S7.7) so it travels with the artefact; and **pair with VEX** (S7.4) so you can record "present but not exploitable".

**S7.9 — Securing a CI pipeline**

The controls, roughly in order of value:

- **OIDC instead of static credentials** (A2.8, TF7.4) — **the highest-value single change.** The pipeline exchanges a short-lived OIDC token for cloud credentials; **no long-lived secret exists in the CI system.** And the trust policy's `sub` condition binds it to a specific repo, branch, or environment — **which is what makes fork PRs safe** (S7.10). **A wildcard in that condition is the critical misconfiguration.**
- **Least-privilege job permissions** — GitHub's default `GITHUB_TOKEN` permissions should be read-only at the org level, with jobs requesting what they need. `permissions: contents: read` plus `id-token: write` only where required.
- **Separate plan and apply / build and deploy credentials**, so a PR job cannot deploy (TF9.1).
- **Protected environments with required reviewers** for production, enforced by the platform and backed by IAM (TF9.5, S7.9's OIDC point).
- **Ephemeral runners** — a fresh runner per job, so nothing persists between jobs. **Self-hosted persistent runners are a serious risk** (S7.10) because a malicious job can poison the environment for the next one.
- **Isolated self-hosted runners** — if you must, per-repository, network-restricted, non-privileged, and never shared between trust levels.
- **Pinned actions** (S7.11) and pinned dependencies (S7.2).
- **Branch protection** — required reviews, no force-push, signed commits where warranted.
- **Secret masking and no debug logging** (S6.7).
- **Egress restrictions** on runners, so exfiltration has somewhere to fail — and it's genuinely effective against the credential-stealing worms of 2025.
- **Audit the pipeline configuration itself** — CI config is code that grants access, and **anyone who can modify the workflow can usually grant themselves the workflow's permissions** (TF7.9's inversion point).

**S7.10 — Untrusted code running in CI**

**The threat**: CI runs code, and if that code is untrusted, **it runs with whatever the runner has** — secrets, cloud credentials, network access, and the ability to modify artefacts.

**Fork pull requests** are the canonical case. A PR from an external fork contains arbitrary code. If your workflow builds and tests it:

- **`pull_request_target` is the dangerous trigger.** Unlike `pull_request`, it runs **in the context of the base repository with access to secrets**, and if it checks out the PR's code, **the attacker's code runs with your secrets.** This has been exploited repeatedly in the wild and is the single most important CI misconfiguration to know.
- **`pull_request` is the safe default** — no secrets, read-only token, for fork PRs.
- **A malicious PR can also poison caches** shared with the base branch, exfiltrate anything in the environment, or modify build outputs.

**Third-party actions** are the other case: an action is arbitrary code you've invited into a privileged environment. **The Codecov and `tj-actions/changed-files` compromises** (the latter in 2025, modified to dump runner memory containing secrets into logs) both worked exactly this way.

**Dependencies with install-time scripts** — `npm postinstall`, `setup.py` — execute during a build, before any test runs (S7.1).

**The controls:**

- **Never use `pull_request_target` with a checkout of untrusted code.** If you need it, check out only the base and never execute PR code.
- **Require approval for workflows from first-time or external contributors** — GitHub supports this and it should be on.
- **No secrets in PR workflows.** Build and test without them; anything needing credentials runs after merge.
- **Ephemeral runners** (S7.9), so poisoning doesn't persist.
- **Pin actions to a digest** (S7.11).
- **Restrict which actions are allowed** at the org level — an allow-list of verified and internal actions.

**S7.11 — Pinning CI actions to a digest**

```yaml
# tag — mutable, and the tag can be repointed at any commit
- uses: actions/checkout@v4

# digest — immutable, with the version as a comment for readability
- uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608 # v4.1.0
```

**Why a tag isn't enough**: **a git tag is a mutable pointer.** The maintainer — or an attacker who has compromised the maintainer's account — can move `v4` to point at different code, and **every workflow using `@v4` picks it up on the next run, silently.** No PR, no review, no notification.

**This is not theoretical.** The **`tj-actions/changed-files` compromise in March 2025** worked precisely this way: the attacker repointed the tags for many versions at malicious code that dumped runner memory (including secrets) into build logs. **Thousands of repositories were affected within hours**, and workflows pinned to a digest were unaffected.

**The practices:**

- **Pin every third-party action to a full commit SHA**, with the version in a trailing comment so humans can read it.
- **Automate updates** — Dependabot and Renovate both understand digest pinning and raise PRs that update the digest and the comment together, **so you get updates as reviewed changes** (S7.2's argument).
- **`actions/*` from GitHub itself** is lower risk but not zero — pin it too; the marginal cost is nil.
- **Restrict allowed actions** at the organisation level.
- **Review the diff on update**, at least for actions with access to secrets.

The generalisation: **this is the same principle as pinning container images by digest** (S7.6) **and Terraform modules to tags rather than branches** (TF4.3). **Any mutable reference in your supply chain is a mechanism for code to change without review.**

**S7.12 — SLSA levels at a decision level**

**SLSA** (Supply-chain Levels for Software Artifacts) is a framework of increasing build integrity guarantees. **Version 1.0 restructured it into tracks**; the Build track is what people mean:

- **Build L1** — **provenance exists.** The build produces a document describing how it was built. Unsigned and unverified, so it's honest documentation rather than a guarantee. Cheap.
- **Build L2** — **provenance is signed and generated by a hosted build platform**, so it's authenticated and harder to forge. Requires a build service rather than a developer's laptop.
- **Build L3** — **the build platform provides strong isolation**: builds run in ephemeral, isolated environments, **provenance is unforgeable even by the person who triggered the build**, and secrets used for signing are inaccessible to the build itself. This is what defends against SolarWinds-style build compromise.

**What each buys, as a decision:**

- **L1 is nearly free** and gives you the SBOM-adjacent question "what went into this artefact" (S7.8). **Every organisation should be at L1.**
- **L2 is achievable with GitHub Actions or similar plus keyless signing** (S7.7) — the `slsa-framework/slsa-github-generator` produces conforming provenance. **Reasonable for most organisations** and a meaningful step: an attacker can no longer fabricate provenance without compromising the build platform.
- **L3 requires genuinely isolated builds** with no reusable state and no access to signing material — a substantial engineering investment, and the right target for software you distribute to others or for anything where a build compromise would be catastrophic.

**The framing to give**: **SLSA is about the integrity of the build process, not the quality of the code.** L3 provenance on a malicious commit is provenance of malice — **it complements code review and dependency scanning rather than replacing them** (S1.3's "signing proves provenance, not quality"). **The decision is how much you'd lose if your build system were compromised**, and for an organisation shipping to customers or operating in a regulated environment, L2 with verified provenance at admission (S7.7) is a defensible target.

---

## S8. Vulnerability & patch management

**S8.1 — CVE, CVSS, and why CVSS alone is poor prioritisation**

- **CVE** — a unique identifier for a publicly disclosed vulnerability. **Just an identifier**, carrying no severity.
- **CVSS** — a numerical score (0–10) from a vector of metrics: attack vector, complexity, privileges required, user interaction, and impact on confidentiality, integrity, and availability.

**Why CVSS alone is poor:**

- **It's context-free by design.** The base score assumes worst-case deployment. **A CVSS 9.8 in a library you have installed but never call is not a 9.8 for you** (S7.4). CVSS has Temporal and Environmental metrics intended to adjust for this, and **almost nobody uses them**, so the number everyone quotes is the raw base score.
- **The distribution is skewed high.** A large fraction of published CVEs score 7.0+, so "critical" stops discriminating — if everything is critical, nothing is (A10.27's argument about scores).
- **It doesn't reflect exploitation.** **Only a few percent of CVEs are ever exploited in the wild.** A 9.8 with no public exploit and complex preconditions is less urgent than a 7.5 being actively used.
- **It says nothing about reachability or your compensating controls.**

**The better signals to combine with it:**

- **CISA KEV** — a catalogue of vulnerabilities **known to be exploited.** Binary and high-signal. **Anything on KEV is a priority regardless of score.**
- **EPSS** — a probability that a vulnerability will be exploited in the next 30 days. Probabilistic, and much better correlated with real risk than CVSS.
- **Reachability analysis** (S7.4).
- **Your own exposure** — internet-facing versus internal, and what the affected component can access.

**The formulation to give**: **prioritise by `exploitability × exposure × impact-in-our-context`, using CVSS as one input.** A policy that says "all criticals within 7 days" sounds rigorous and produces a queue nobody can clear, which leads to the whole programme being ignored (S8.7).

**S8.2 — Assessing whether a vulnerability is actually reachable**

The questions, in order:

1. **Is the component present?** SBOM or scan (S7.5, S7.8). Frequently the answer is "in the image but not used" — a transitive dependency of a build tool.
2. **Is the vulnerable code path called?** **Reachability analysis** — `govulncheck` for Go, Snyk's and Endor's reachability features. **This is the highest-value filter and typically eliminates most findings.**
3. **Are the preconditions met?** Many CVEs require a specific configuration, a non-default option, or a particular input format. **Read the advisory** — the details usually make the determination straightforward.
4. **Can an attacker reach it?** Internet-facing, or behind three layers of internal network? Does it require authentication? What input does it need?
5. **What would the attacker gain?** A vulnerability in a component running unprivileged in an isolated container with no data access is different from one in the authentication path.
6. **Do compensating controls block it?** A WAF rule, a NetworkPolicy (K4.10), a disabled feature, or a non-root read-only container (S7.6).

**Record the determination.** **VEX** (S7.4) makes it machine-readable and reusable — so the next scan doesn't re-raise it and the next person doesn't redo the analysis. **Without that, the same finding is re-triaged every week**, which is a large and invisible waste.

**The honest caveat**: reachability analysis is imperfect — dynamic dispatch, reflection, and configuration-driven code paths defeat static analysis. **Treat "not reachable" as strong evidence, not proof**, and be more conservative for internet-facing components.

**S8.3 — Defining and defending a patching SLA**

A defensible policy:

| Severity / trigger | Internet-facing | Internal | Note |
|---|---|---|---|
| **On CISA KEV** | 24–48 hours | 7 days | Actively exploited — overrides CVSS |
| Critical, reachable | 7 days | 30 days | |
| High, reachable | 30 days | 60 days | |
| Medium | 90 days | Next scheduled cycle | |
| Low / not reachable | Backlog, reviewed quarterly | | Record the VEX determination |

**How to defend it:**

- **It's risk-based, not severity-based.** The trigger combines exploitability, exposure, and reachability (S8.1, S8.2) rather than CVSS alone — **which is what makes it achievable, and achievability is what makes it real.**
- **It's measurable** — time from disclosure (or detection) to remediation, reported as a distribution, not an average.
- **It has an exception process** — documented, time-bounded, with a named owner and a compensating control (A10.28). **An SLA with no exception path generates undocumented exceptions.**
- **It's resourced.** A policy nobody has time to meet is a policy that's ignored, and then the whole programme loses credibility.
- **It aligns with the compliance framework** you're actually subject to — PCI DSS requires critical patches within a month, which is a hard input rather than a preference.

**The argument to make to a security function pushing for tighter numbers**: **a 7-day SLA on all criticals, unfiltered, produces a permanently-breached SLA and a team that stops looking.** **A risk-filtered SLA that is actually met is a stronger control than an aspirational one that isn't** — and the metric to show is not the backlog size but the time-to-remediate for the things that genuinely matter (S10.7's constructive pushback).

**S8.4 — Patching at scale without downtime**

**For containerised workloads — and this is the modern answer** (S8.6): **rebuild the image and roll the deployment.** Patching is a deploy, not a maintenance operation. A rolling update (K2.6) with correct readiness probes and PDBs (K6.9) does it with no downtime, and it exercises the deploy path you use daily.

**For instances**: **immutable replacement** (A4.6, K11.5) — build a new AMI, roll the ASG with an instance refresh, or let Karpenter's node expiry handle it (K7.6). **Not in-place patching**, which produces divergent, snowflake hosts.

**For managed services**: the provider's maintenance window (DB12.9), which on multi-AZ is a failover rather than an outage (A7.1) — so making failover cheap (DB5.6) makes patching a non-event.

**For things that genuinely can't be replaced**: in-place patching with `unattended-upgrades` or a configuration management tool, rolling across the fleet with health checks between batches.

**The properties that make it safe at scale:**

- **Roll progressively** — a canary, then a percentage, then the rest, with automated abort on error-rate regression (K2.11).
- **Health checks between batches**, and stop on failure.
- **Respect disruption budgets** so capacity isn't lost (K6.9).
- **Have a rollback** — the previous image or AMI, still available.
- **Automate it**, because a manual process across hundreds of instances is where mistakes happen.

**The strategic point**: **the ability to patch quickly is a function of deployment maturity, not of patching tooling.** An organisation that deploys ten times a day patches in hours; one that deploys monthly patches in weeks regardless of how urgent it is. **Investment in deployment automation is investment in patch response** — and that's the argument that connects this to the CI/CD work.

**S8.5 — Handling a zero-day**

The sequence, and the ordering matters because the first hours are about exposure, not fixing:

1. **Establish exposure fast.** Do we run the affected component? Which versions? Where? **This is where an SBOM earns its entire cost** (S7.8) — with one, it's a query; without one, it's hours or days of searching while the clock runs. **Log4Shell is the canonical demonstration.**
2. **Determine reachability and exposure** (S8.2) — internet-facing instances first.
3. **Mitigate before you patch.** A patch may not exist yet, and even when it does, deploying everywhere takes time. **Mitigations**: a WAF rule (A8.8 — virtual patching is exactly this case, and it can be live in minutes); disabling the affected feature or configuration; network isolation of the affected component; blocking the exploit pattern at the edge.
4. **Patch when available**, prioritised by exposure (S8.4).
5. **Hunt for compromise.** A zero-day means it may have been exploited **before** disclosure. Check logs for exploitation attempts and for indicators of compromise — **assume it may already have happened** rather than only preventing future attempts. This is the step most often skipped.
6. **Communicate** — internally with a clear picture of exposure and progress, and externally where customers or regulators need to know. In a regulated environment there are disclosure clocks (A10.30).
7. **Post-incident**: why did it take that long to establish exposure? That's usually the biggest lesson and it points at inventory and SBOM investment.

**The preparation that makes this survivable**: an **artefact and dependency inventory** (S7.8), a **fast deployment pipeline** (S8.4), a **WAF or edge control** you can change quickly, **good logging with enough retention** to hunt retrospectively (O4.8), and a **defined incident process** so the first hour isn't spent deciding who's in charge.

**S8.6 — Image rebuild cadence as a patching strategy**

**The insight: for containers, patching is rebuilding.** You don't patch a running container — you build a new image with updated base packages and dependencies, and roll it out (S8.4).

**Which means the rebuild cadence *is* the patch latency.** An image built once and deployed for a year accumulates every CVE published against its base in that year — **without anything changing**, because the image is static and the vulnerability database isn't (S7.5).

**The practice:**

- **Rebuild on a schedule** — weekly or nightly — even with no code change, so base image updates flow through.
- **Rebuild on base image updates** — Renovate and Dependabot can raise a PR when the base image digest changes (S7.2).
- **Rebuild on dependency updates.**
- **Continuously scan images in the registry** (A5.1), not just at build, so you find out about new CVEs against deployed images.
- **Then actually redeploy** — a rebuilt image sitting in the registry patches nothing. **This is the step that's missed**, and the connection between rebuild cadence and deployment cadence is the point.

**The prerequisites**: **reproducible builds** (S7.2) so a rebuild without a code change produces a functionally identical artefact; **a test suite you trust** so an automated rebuild can be deployed with confidence; and **a deployment pipeline fast enough** that rolling every service weekly is routine rather than an event.

**The pairing with minimal images** (S7.6) is what makes this tractable: **a distroless image has almost no OS packages, so most base CVEs simply don't apply**, and the rebuild treadmill is much shorter. **Minimal images plus frequent rebuilds is the complete container patching strategy**, and stating it as a pair is the strong answer.

**S8.7 — Managing the backlog without ignoring it or drowning**

**The failure modes at both ends**, which is what the item names:

- **Drowning**: an unfiltered scanner produces thousands of findings, the team can't clear them, the queue grows, and eventually nobody looks at it. **Worse than nothing, because it creates the appearance of coverage** (A10.25).
- **Ignoring**: the queue is dismissed as noise, and the genuinely exploitable one is missed among the false positives.

**The practices that make it manageable:**

1. **Filter hard at intake.** Reachability (S8.2), KEV and EPSS (S8.1), exposure. **The goal is a queue that a team can actually clear**, because a clearable queue gets cleared.
2. **Record determinations as VEX** (S7.4) so a triaged finding doesn't reappear every scan. **This is the single biggest reducer of repeated effort.**
3. **Group by root cause.** Three hundred findings are usually a dozen causes — an old base image, one outdated framework, a shared library. **Fixing the base image collapses the count**, which is the leverage (A10.27's argument).
4. **Fix upstream.** Update the shared base image and every downstream image improves at once. That's the platform-team answer rather than the ticket-closing one.
5. **Automate the routine** — dependency update PRs (S7.2) and scheduled rebuilds (S8.6) mean most findings resolve without human action.
6. **Route to owners**, not to a central security queue (A10.29) — which requires ownership metadata, and is why tagging matters.
7. **Time-box exceptions** with a compensating control and an expiry (A10.28).
8. **Report the trend, not the count** — "critical, reachable, internet-facing findings" over time, and time-to-remediate. **A raw count is unactionable and demoralising; a trend on the things that matter is a management conversation.**

**The framing**: **the objective is not zero findings — it's that nothing exploitable and exposed stays unaddressed.** Stating that explicitly is what lets you defend a non-zero backlog to a security function or an auditor (S10.7).

---

## S9. Access, hardening & controls

**S9.1 — Least privilege, and why it degrades**

**The principle**: every identity has the minimum permissions needed for its function, and nothing more.

**Why it degrades over time**, which is the substance:

- **Permissions are granted under pressure and never removed.** An incident at 3am, a broad grant to unblock it, and no cleanup. **The grant is urgent; the revocation never is.**
- **Debugging by widening.** Something fails with a permission error, someone adds a wildcard to make it work, and the narrower fix is never found (A2.4's argument for reading the error properly).
- **Role accumulation.** People change teams and keep old access. **Nobody's access ever shrinks**, so tenure correlates with privilege.
- **Copying an existing role** because it works, inheriting permissions the new use doesn't need.
- **Nobody knows what's actually needed**, so nobody dares remove anything — **and removing a permission has an immediate visible cost if you're wrong, while leaving it has no visible cost at all.** That asymmetry is the core reason.
- **Service accounts are worst** — long-lived, unattended, and never reviewed (A2.11, K8.11).

**The countermeasures:**

- **Measure actual usage** — IAM Access Analyzer's unused access findings and last-accessed data (A2.10), `pg_stat` for database roles (DB13.1), Kubernetes audit logs (K8.13). **Generate policies from observed activity.**
- **Access reviews on a cadence**, with the owner attesting rather than a central team guessing.
- **Time-bound grants by default** — just-in-time elevation rather than standing access (S9.2), which makes the problem self-correcting.
- **Automated expiry** on exceptions and temporary grants.
- **Permissions boundaries** so delegated grants can't exceed a ceiling (A2.1).

**The caveat worth stating** (A2.10): **absence of use is not absence of need.** A permission unused for 90 days may be for the annual DR test or an incident path. **Remove aggressively for routine workloads, conservatively for anything that exists for rare events** — and keep removals in version control so restoring is a revert.

**S9.2 — Break-glass access with auditing**

**The requirement**: a path to elevated access for genuine emergencies, that doesn't exist as standing privilege.

**A well-designed break-glass path:**

1. **A named, pre-existing role** with elevated permissions, not held by anyone routinely (A1.4).
2. **Deliberate assumption** — a documented action, not a login someone might do by habit. Ideally requiring a justification and an incident reference.
3. **Approval where feasible** — a second person, or a time-delayed grant that can be cancelled.
4. **MFA required.**
5. **Alarmed in real time, not merely logged.** **A break-glass use that isn't an incident is itself an incident** — the alert must go somewhere a human sees it within minutes.
6. **Time-bounded** — the elevation expires automatically, typically in an hour.
7. **Fully audited** — CloudTrail (A9.5), session recording where appropriate (A3.7's Session Manager logging), and correlated to the incident.
8. **Reviewed after the fact** — every use examined, with the question "why was the normal path insufficient?"

**The design points that matter:**

- **It must not depend on the systems that might be broken.** If break-glass requires SSO and the IdP is down, it isn't a break-glass path (A1.6). **A sealed credential in a vault, with the vault independent of the failing system**, is the fallback.
- **Test it.** An untested break-glass path is discovered to be broken during the incident it exists for.
- **The existence of a documented path is what stops people improvising** — without one, the emergency access happens anyway, using someone's personal admin credentials, unrecorded (TF13.6).

**S9.3 — Defence in depth with a concrete example**

**The principle**: no single control is trusted to be sufficient; layers are arranged so a failure of one is contained by others.

**A concrete example — a payments API in AWS, and what each layer catches:**

| Layer | Control | What it stops |
|---|---|---|
| Edge | WAF, rate limiting, DDoS protection | Commodity scanning, volumetric attack (A8.8) |
| Network | Private subnets, security groups, NACLs | Direct access to compute from the internet (A3.2) |
| Transport | TLS at the edge, mTLS internally | Interception, unauthenticated callers (S5.4) |
| Identity | OIDC / IAM roles, no static credentials | Credential theft and reuse (A2.8) |
| Authorisation | Per-service IAM, least privilege | Lateral movement after a compromise (S9.1) |
| Application | Input validation, parameterised queries | Injection (DB13.7, S9.8) |
| Container | Non-root, read-only rootfs, dropped capabilities | Escape after RCE (K8.7, S7.6) |
| Data | Encryption at rest with a CMK, least-privilege DB roles | Bulk data access (DB13.1) |
| Detection | GuardDuty, audit logs, anomaly alerting | Noticing all of the above (A10.22) |
| Recovery | Tested backups, immutable copies | Ransomware and destructive action (A11.7) |

**The narrative that makes it a good answer**: **trace an attack through the layers.** An attacker exploits an application vulnerability and gets code execution in a container. **Non-root and no capabilities** mean they can't escape easily. **IMDSv2 with a hop limit** means they can't steal node credentials (A2.6). **The pod's IAM role is narrow**, so what they can reach is bounded. **NetworkPolicy** limits lateral movement (K4.10). **The database role can't drop tables** (DB13.1). **GuardDuty** flags the unusual API calls. **Each layer doesn't prevent the attack — it reduces what the attack achieves**, and that's the actual value proposition.

**S9.4 — Secure defaults, and where yours aren't**

**The principle**: the default configuration should be the safe one, so security is what happens when nobody does anything special. **A secure option that must be enabled is a security control that will frequently be absent.**

**Where defaults commonly aren't secure — and being able to name your own is the point of the item:**

- **Kubernetes**: pods run as root unless specified; `automountServiceAccountToken` is on (K8.3); the network is flat with no policy (K4.1); no resource limits.
- **AWS**: S3 buckets aren't versioned; RDS may be created without deletion protection; security groups permit all egress; **CloudTrail data events are off** (A9.5); Config isn't enabled.
- **Databases**: `PUBLIC` grants in Postgres; no `statement_timeout` (DB8.8); TLS not required (DB13.5).
- **Docker**: containers run as root; no read-only filesystem; the full capability set minus a few.
- **CI**: `GITHUB_TOKEN` with write permissions; actions unpinned (S7.11).
- **TLS**: older library defaults accepting weak protocols; **`sslmode=require` not verifying certificates** (DB13.5).

**Making defaults secure is the platform team's highest-leverage security work** (K13.4, TF8.8): a **base image** that's non-root and distroless (S7.6); a **service module** that provisions encryption, logging, and tight IAM (TF4.2); a **namespace template** with PSA labels, NetworkPolicy, and quotas (K13.3); and **admission policy** enforcing it (K8.9).

**The framing to give**: **the goal is that a team doing nothing special gets a secure result, and doing something insecure requires a deliberate, visible act.** That's a far stronger control than documentation or review, because it doesn't depend on anyone remembering (TF13.5's paved-road argument).

**S9.5 — Network segmentation and blast radius containment**

**The principle**: divide the network so a compromise in one segment cannot freely reach others.

**The layers, from coarse to fine:**

- **Separate accounts** (A1.1) — the strongest boundary on AWS, since it's an IAM boundary as well as a network one.
- **Separate VPCs** with controlled connectivity — TGW route tables expressing "prod cannot reach dev" as a routing fact rather than a security group rule (A3.13).
- **Subnet tiers** — public, private application, private data — with only the load balancer publicly reachable (A3.1).
- **Security groups referencing other security groups** rather than CIDRs (A3.2) — so "only the app tier may reach the database" survives autoscaling.
- **NetworkPolicy in Kubernetes** — default-deny plus explicit allows (K4.10), which is the pod-level equivalent.
- **Service mesh authorisation policy** — identity-based rather than IP-based (S5.7), which is the strongest form because it survives IP reuse.
- **Egress control** — restricting outbound traffic, which is the underused one. **It's what stops exfiltration and command-and-control**, and most estates allow unrestricted egress.

**Why it contains blast radius**: an attacker with code execution in one workload can only reach what that segment permits. **Without segmentation, one compromised container can scan and reach every service in the estate** (K8.12).

**The practical guidance**: **segment by trust and by blast radius, not by org chart** (A1.12's OU argument). Production separate from non-production; the data tier separate from the application tier; anything internet-facing separate from internal. **And test it** — a default-deny policy that isn't enforced because the CNI doesn't support it is a control that exists only on paper (K4.11).

**S9.6 — Zero trust beyond the marketing**

**The marketing version**: "never trust, always verify", usually attached to a product.

**The substance**: **network location is not an authorisation signal.** The traditional model had a hard perimeter and a trusted interior — once inside the VPN, you were trusted. **Zero trust rejects that**: every request is authenticated and authorised on its own merits, regardless of where it originates.

**What it actually requires:**

1. **Strong identity for every actor** — users (SSO with MFA, A1.4) and **workloads** (SPIFFE, IRSA, mTLS — S5.8, A2.7). **Workload identity is the part that's genuinely hard** and is where most implementations are weakest.
2. **Authenticate and authorise every request**, including service-to-service. Not just at the edge (S5.4's point that verification and authorisation are separate).
3. **Least privilege, continuously enforced** (S9.1).
4. **Device and context signals** — is this a managed device, in an expected location, at an expected time (conditional access).
5. **Encrypt everything in transit**, since the network is assumed hostile (S5.7).
6. **Comprehensive logging and monitoring**, because you're verifying continuously rather than once at the perimeter (S9.7).
7. **Micro-segmentation** as the network-layer expression (S9.5).

**What it doesn't mean**: that you remove network controls. **Zero trust and defence in depth are complementary** — network segmentation is still valuable, it's just no longer *sufficient*, and treating "we're zero trust" as a reason to flatten the network is a misreading.

**The honest assessment**: it's a direction, not a product or a project with an end date. **Google's BeyondCorp took years.** The pragmatic sequence is: SSO with MFA everywhere → eliminate long-lived credentials (A1.4, A2.8) → workload identity → per-service authorisation → device signals. **Each step is valuable independently**, which is what makes it adoptable.

**S9.7 — Audit logs that are complete and can't be edited by the audited**

**The three requirements:**

1. **They exist** — for every system that matters: cloud API (CloudTrail, A9.5), Kubernetes API (K8.13), database (DB13.8), application authentication and authorisation, CI/CD, and the identity provider.
2. **They're complete** — capturing who, what, when, from where, and the outcome. **The gaps that matter**: CloudTrail data events are off by default (A9.5), so object-level S3 access isn't recorded; EKS audit logs are off by default; database audit logging is usually not configured. **Each of those is a question you can't answer after an incident.**
3. **They can't be edited by the audited** — the critical property.

**Achieving tamper-resistance:**

- **Ship off-system immediately.** A log on the host an attacker controls is not evidence (A1.16). **Central log archive account**, written to by the service, with no write or delete access from the workload accounts.
- **Append-only storage** — S3 with versioning and **Object Lock in compliance mode**, so retention is enforced by the platform even against root (A6.1).
- **A separate account or trust domain** with different credentials, so compromising production doesn't grant access to the logs.
- **Cryptographic integrity** — CloudTrail log file validation produces signed digests, so alteration is detectable. **Without it, "tamper-resistant" is a claim you can't substantiate** (A9.6).
- **Monitor the logging pipeline itself** — a trail that stops delivering is a security event, and alerting on it is the control that catches an attacker disabling logging.
- **Restrict and audit access to the logs**, since they contain sensitive information.

**The property to articulate**: **an attacker with full administrative access to a production system should be unable to alter or delete the record of what they did.** Stated that way, the design follows — the trust must flow one way.

**S9.8 — OWASP Top 10 well enough to spot the common ones**

The current list, with what to look for in review:

1. **Broken Access Control** — the top item, and the most common in practice. **Look for**: authorisation checked at the UI but not the API; object IDs accepted from the client without ownership verification (IDOR); missing checks on non-GET endpoints; role checks that a modified request can bypass. **Scanners cannot find these** (S7.5) — they're logic flaws.
2. **Cryptographic Failures** — plaintext transmission or storage, weak algorithms (S1.7), hardcoded keys, secrets in logs (S6.7).
3. **Injection** — SQL (DB13.7), command, LDAP, and template injection. **Look for**: string concatenation into any interpreter.
4. **Insecure Design** — missing threat modelling (S9.9); a design with no rate limiting on a sensitive operation.
5. **Security Misconfiguration** — defaults left in place (S9.4), verbose errors exposing internals, unnecessary features enabled, permissive CORS.
6. **Vulnerable and Outdated Components** — S7.4, S8.
7. **Identification and Authentication Failures** — weak password handling (S1.4), no MFA, session fixation, tokens that don't expire.
8. **Software and Data Integrity Failures** — unsigned artefacts, unpinned dependencies, insecure deserialisation (S7.2, S7.7).
9. **Security Logging and Monitoring Failures** — S9.7.
10. **Server-Side Request Forgery (SSRF)** — user-controlled URLs fetched by the server. **In cloud this is severe**, because it reaches the metadata service (A2.6) — **IMDSv2 with a hop limit is the specific mitigation**, and it's the connection worth making.

**For a platform engineer specifically**, the ones you own or can mitigate are **5, 6, 8, 9, and the SSRF-to-metadata path in 10** — the others are application-level. **Knowing which are yours and which you can only support is the useful distinction.**

**S9.9 — Threat modelling a system**

**The method** — four questions (Shostack's framing):

1. **What are we building?** A diagram: components, data stores, trust boundaries, data flows.
2. **What can go wrong?** Systematic enumeration, usually with **STRIDE**: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege.
3. **What are we going to do about it?** Mitigate, transfer, accept, or eliminate.
4. **Did we do a good job?** Review and iterate.

**Structured as the item asks:**

- **Assets** — what's worth protecting. Customer PII, payment credentials, the ability to move money, availability, and **the credentials that grant access to those**.
- **Actors** — external attackers, malicious insiders, compromised third parties, a compromised dependency (S7.1), and honest users making mistakes.
- **Entry points** — the public API, admin interfaces, the CI pipeline (S7.9), third-party integrations, the supply chain, physical access, and support tooling.
- **Trust boundaries** — where data crosses from less trusted to more trusted. **These are where the interesting vulnerabilities are**, and drawing them explicitly is the highest-value part of the diagram.
- **Mitigations** mapped to each identified threat, with what remains unmitigated recorded as accepted risk.

**The practical guidance**: **do it at design time**, when changing the design is cheap. **Keep it proportionate** — a one-hour whiteboard session on a new service catches most of what a formal process would, and a heavyweight process gets skipped. **Focus on the trust boundaries and the data flows**, not on enumerating every conceivable threat. And **record the accepted risks**, because that's the artefact that's useful later, both for review and for an auditor (S10.2).

---

## S10. Compliance & assurance

**S10.1 — Explaining the intent behind a control**

**The skill being assessed**: an auditor asks for evidence of a control; a reciter quotes the requirement; someone who understands it explains what risk it addresses and how their implementation addresses that risk — **possibly differently from the literal wording.**

Examples:

| Control (as written) | Intent | Implementation that satisfies the intent |
|---|---|---|
| "Change passwords every 90 days" | Limit the window of a compromised credential | **Eliminate passwords** — SSO with MFA, workload identity (A2.8, S6.6). Modern guidance (NIST) actually advises *against* forced rotation, because it causes weaker passwords |
| "Review access quarterly" | Prevent privilege accumulation (S9.1) | Automated unused-access detection plus JIT elevation, which is continuous rather than quarterly |
| "Separation of duties in deployment" | No single person can unilaterally change production | PR review plus a protected environment plus an apply gate (TF7.9) |
| "Antivirus on all servers" | Detect malicious code | Immutable containers rebuilt from scratch (S8.6) plus runtime detection — AV on a container host addresses a threat model that doesn't apply |
| "Annual penetration test" | Find vulnerabilities before attackers | Continuous scanning plus a pen test, because annual leaves an eleven-month gap |

**Why it matters**: **controls are written generically and age badly.** A control written for a 2010 datacentre applied literally to containers produces work that costs money and reduces nothing. **Being able to articulate the intent lets you propose a better implementation and have it accepted** — which is the constructive version of S10.7.

**The caution**: **the auditor decides what satisfies the control**, so the conversation must happen with them, in advance, with the mapping documented. **Unilaterally deciding your alternative is equivalent produces a finding.**

**S10.2 — Evidence from systems rather than screenshots**

**The problem with screenshots**: they prove a moment, are trivially faked, go stale immediately, and generating them consumes enormous engineering time before each audit. **They demonstrate that a control was configured on the day someone took the picture, not that it operated throughout the period** — and the period is what the auditor cares about.

**Evidence generated from systems:**

- **Config rules with compliance history** (A10.24) — continuous evaluation, with a timeline showing compliance over the whole period. **This is the model answer**: it evidences the period, not the moment.
- **Security Hub compliance standards** (A10.25) with trend data.
- **CloudTrail** for who did what (A9.5) — the audit trail is the evidence.
- **Pipeline records** — every production change with its PR, approver, plan, and apply log (TF9.2). **A regulated change process evidenced entirely from git and CI**, which is far more credible than a change ticket someone filled in afterwards.
- **IaC as evidence of intent**, plus drift detection as evidence it held (TF9.6).
- **Policy-as-code results** (S10.3).
- **Automated queries** — a script producing the current state across every account (A14.4).

**The properties that make it good evidence**: **continuous** (covers the period), **tamper-evident** (S9.7), **reproducible** (the auditor could run it), and **generated as a by-product of operating the system** rather than assembled for the audit.

**The argument to make internally**: **automating evidence collection pays for itself in one audit cycle** in engineering time alone, and it produces a stronger result. That's usually enough to fund it (A10.31's "evidence generated continuously" point).

**S10.3 — Policy as code and automated compliance checking**

**Expressing controls as executable rules rather than documents**, evaluated automatically.

The layers:

- **Preventive at deploy time** — OPA/Conftest or Sentinel against a Terraform plan (TF7.6); admission control in Kubernetes (Kyverno, Gatekeeper — K8.9); CloudFormation hooks.
- **Preventive at the platform** — SCPs making non-compliant actions impossible (A1.3).
- **Detective, continuous** — AWS Config rules (A10.24), Security Hub (A10.25).
- **In the pipeline** — dependency and image scanning gates (S7.4, S7.5), secret scanning (S6.3).

```rego
package terraform.compliance
deny[msg] {
  r := input.resource_changes[_]
  r.type == "aws_s3_bucket"
  not r.change.after.server_side_encryption_configuration
  msg := sprintf("S3 bucket %v must have encryption enabled (ISO 27001 A.10.1)", [r.address])
}
```

**Why it's better than documented policy:**

- **It's enforced, not aspirational.** A document describes what should happen; a policy makes the non-compliant thing fail.
- **It generates evidence automatically** (S10.2) — every evaluation is a record.
- **It's versioned and reviewable** like any code.
- **It scales** — one rule covers every account and every deployment.
- **Feedback is immediate**, at the point of change, so it's cheap to fix.

**The practices**: **reference the control in the message** (as above), so the developer knows why and the auditor can trace rule to requirement; **audit mode before enforce** (A1.11's measure-then-enforce sequencing); and **a documented, time-bounded exception process** (A10.28), because absolute rules generate workarounds.

**S10.4 — Data residency and its architectural consequences**

**The requirement**: certain data must be stored, and sometimes processed, within a specified jurisdiction — GDPR-adjacent expectations, UK/EU financial regulation, national data localisation laws.

**The architectural consequences, which is what the item asks for:**

- **Region selection is constrained** — you may not use the cheapest or nearest region, and some services aren't available in all regions.
- **Backups and DR must stay in-region or in permitted regions.** **This directly conflicts with cross-region DR** (A11.2) — if data can't leave the jurisdiction, your DR options shrink to in-region, and the resilience conversation changes materially.
- **Replication topology is constrained** — a global database with cross-region replicas may be non-compliant.
- **Multi-region architectures become multi-jurisdiction architectures**, with data partitioned by residency rather than replicated. **That's a fundamentally different design** — per-region data stores with no cross-region replication, and an application that routes users to their jurisdiction's stack.
- **Telemetry counts.** **Logs, traces, and metrics frequently contain personal data** (O4.9) — so shipping them to a US-hosted observability vendor may breach residency. **This is the consequence people most often miss**, and it constrains the O1.8 build-vs-buy decision.
- **Third parties and sub-processors** must also comply — including your SaaS tooling.
- **Support and operations access** — an engineer in another jurisdiction accessing the data may itself be a transfer.

**The mitigations**: **data classification first** — usually only a subset is genuinely restricted, so identify it rather than treating everything as residency-bound; **pseudonymisation or tokenisation** so what crosses borders isn't personal data; **regional deployment with a routing layer**; and **contractual mechanisms** (Standard Contractual Clauses) where transfer is permitted with safeguards.

**S10.5 — The frameworks at a working level**

- **SOC 2** — an **attestation**, not a certification, against the AICPA Trust Services Criteria (Security, plus optionally Availability, Confidentiality, Processing Integrity, Privacy). **Type I** is a point in time; **Type II** covers a period (usually 3–12 months) and tests operating effectiveness. **You define your own controls** and the auditor tests them — which is why the evidence question (S10.2) matters so much. Common for B2B SaaS because customers ask for it.
- **ISO 27001** — an international **certification** of an Information Security Management System. Process-oriented: risk assessment, a Statement of Applicability against Annex A controls, management review, and continual improvement. **Certified by an accredited body**, with surveillance audits. More common in Europe.
- **PCI DSS** — **prescriptive and technical**, applying to cardholder data. Specific requirements: network segmentation, encryption, patching within defined windows (S8.3), MFA, logging and retention. **Scope reduction is the main strategy** — keeping cardholder data out of your environment via tokenisation or a hosted payment page dramatically reduces what's in scope, and that's the most valuable thing to know about it.
- **GDPR** — a **regulation**, not a certification. Lawful basis, data subject rights (access, **erasure** — which is architecturally hard, M11.5, DB13.9), breach notification within 72 hours, DPIAs, and restrictions on international transfer (S10.4). Applies regardless of where you are if you handle EU residents' data.

**For a UK fintech**, add: **FCA/PRA operational resilience** (important business services, impact tolerances — which is RTO/RPO with a regulator attached, A11.1), and **DORA** for EU financial entities.

**The working-level point**: **SOC 2 and ISO 27001 are about having and following a process; PCI DSS is about specific technical controls; GDPR is about data rights and lawfulness.** They overlap substantially, so **one well-designed control set with good evidence satisfies most of several frameworks** — which is the argument against building separate compliance programmes.

**S10.6 — How a regulated environment changes deployment practice**

The changes that actually bite:

- **Change management is formal.** Every production change needs a record, an approver, a rollback plan, and often a CAB. **The good version**: the pipeline *is* the change record — PR, review, plan, approval, apply log, all automatically captured (S10.2, TF9.2). **The bad version**: a parallel manual ticketing process that duplicates the pipeline and adds days.
- **Separation of duties** — the person who writes the change cannot be the only approver (TF7.9). **This is enforceable in the pipeline** via protected environments and required reviewers.
- **Audit trails for everything** (S9.7), retained for years.
- **Access reviews and evidence** on a cadence (S9.1).
- **Vulnerability management with defined SLAs** (S8.3).
- **DR testing as a regulatory expectation**, with evidence (A11.8) — the regulator increasingly asks for evidence of testing, not evidence of design.
- **Data residency and retention constraints** (S10.4).
- **Third-party and supply chain assurance** — your vendors are in scope.

**The tension to name honestly**: **compliance requirements are frequently interpreted as requiring slow, manual processes** — and that interpretation is usually wrong. **The intent is control and evidence** (S10.1), and **an automated pipeline provides better control and better evidence than a manual process**: it's consistent, it can't be skipped, and it produces a complete record. **Manual approval by someone who doesn't read the plan is weaker than an automated policy check** (TF9.2).

**The productive position**: work with compliance and audit early, map the pipeline's automatic artefacts to the control requirements, and get the mapping agreed. **The outcome is usually that you can deploy frequently and be more compliant than the manual alternative** — and that argument, made with evidence, is one of the more valuable things a platform lead does in a regulated firm.

**S10.7 — Pushing back on a control constructively**

**The situation**: a control is proposed or inherited that adds cost, friction, or risk without reducing risk proportionately — quarterly password rotation, antivirus on immutable containers, a manual approval on a fully-tested automated deployment, blocking a tool the team needs.

**How to push back so it works:**

1. **Start from the intent, not the wording** (S10.1). "What risk is this addressing?" — asked genuinely, not rhetorically. Often the answer reveals the control is aimed at a threat model that doesn't apply.
2. **Acknowledge the risk is real.** Arguing the risk doesn't exist loses the room. **Argue about the mechanism, not the objective.**
3. **Quantify the cost** — engineer hours, deployment latency, and **the risk the control itself introduces.** A manual step in an emergency path is a resilience risk (TF13.6). Slower patching because of change friction is a security risk (S8.4).
4. **Propose an alternative that addresses the same intent**, with evidence it does — and ideally with better evidence than the original (S10.2).
5. **Bring the framework's own language** where you can — NIST advises against forced password rotation; the control's intent is met by MFA and short-lived credentials.
6. **Accept the decision if it goes against you**, document it as a known cost, and revisit with data later.
7. **Pick your battles.** Pushing back on everything makes you the obstacle and you lose credibility for the case that matters.

**What makes it constructive rather than obstructive**: **you're offering a better way to achieve the objective, not asking for an exemption.** The framing is "here's how we can meet this intent more effectively and more cheaply" — and it works far more often than people expect, because compliance functions are usually as frustrated by ineffective controls as engineers are.

The example worth having ready: **"quarterly access review by a central team" replaced with "automated unused-access detection with owner attestation and just-in-time elevation"** — continuous rather than quarterly, evidenced automatically, and it actually reduces standing privilege rather than documenting it.

---

## Using this key

- **Score against the matrix first, then read only the items you scored 0 or 1.** At 97 items this is the smallest domain so far, and the sections are unusually independent — S2–S5 form the PKI story, S6–S8 the pipeline story, and S9–S10 the governance story.
- **S3 and S4 are the operational core** and the ones most likely to be tested practically. Certificate expiry is one of the highest-frequency self-inflicted outages in the industry, and S3.12 explains why it keeps happening to organisations that believe they manage certificates.
- **S7 is where a platform engineer most likely owns the controls**, and where the material has changed fastest. **S7.11 (digest-pinning actions) and S7.10 (`pull_request_target`) are the two most concrete, most exploitable, and most commonly wrong.**
- **S10.7 is the lead-level item.** Being able to push back on an ineffective control constructively — from intent, with an alternative and evidence — is a conversation you'll have in a regulated fintech, and it's rarer than it should be.
- **The failure modes are the part that reads as experience.** The missing intermediate that passes in a browser and fails everywhere else (S3.5); `sslmode=require` not verifying the certificate (DB13.5, S5.9); nonce reuse in GCM as the way competent engineers break working crypto (S1.8); the DST Root X3 expiry breaking millions of clients with no server change (S4.11); and rotating a secret before cleaning git history rather than after (S6.4).
- **Cross-references are dense into AWS and Kubernetes** — A10 for KMS and secrets services, A2.8 for OIDC, K8 for pod security and RBAC, K4.8 and S4.8 for cert-manager, and DB13 for the database-specific security items. Interviewers move between these constantly.
