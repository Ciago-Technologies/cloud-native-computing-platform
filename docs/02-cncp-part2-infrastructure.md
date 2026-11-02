# Cloud Native Computing Platform (CNCP)
## Enterprise Architecture & Implementation Blueprint — Part 2
### Ciago Technologies — Confidential

**Covers:** Chapter 13 (Cloud Infrastructure / IaaS), Chapter 14 (Networking), Chapter 15 (Storage), Chapter 15b (Distributed Filesystem), Chapter 16 (Security)

**Continuity note:** This is Part 2 of a multi-part master blueprint. Part 1 covered Chapters 1-12 (Vision through Scheduling Engine). See Part 1 for the Document Delivery Plan table.

---

# Chapter 13 — Cloud Infrastructure (IaaS Substrate)

The Scheduling Engine (Chapter 12) decides *where* a workload should run. This chapter defines *what it runs on* once "cloud" is chosen — the actual compute substrate underneath every Data Plane region.

## 13.1 Why a Two-Layer Compute Substrate

CNCP workloads fall into two fundamentally different execution shapes, and one orchestrator is not correct for both:

1. **Container-shaped workloads**: dev environments, CI builds, stateless services, most of the Developer Platform (Part 3). These are best served by **Kubernetes**.
2. **VM/microVM-shaped workloads**: full-GPU-passthrough creative apps (Resolve, Blender, Unreal), cloud gaming sessions, and anything requiring kernel-level isolation from co-tenants (security requirement, not just a performance one) or a non-Linux guest OS surface. These are best served by **KubeVirt** (VM-in-Kubernetes) for heavier sessions and **Firecracker** microVMs for lightweight, fast-boot isolated sessions.

Running both under Kubernetes as the single control plane (via KubeVirt and the Kata Containers/Firecracker runtime class) avoids operating two separate orchestration stacks, which would double operational burden for no benefit — this is a deliberate simplification versus a naive design that might stand up OpenStack Nova and Kubernetes as two independent islands.

## 13.2 Where OpenStack Fits

OpenStack is **not** used as the primary workload orchestrator (Kubernetes fills that role). OpenStack (specifically **Ironic** for bare-metal provisioning, and optionally **Neutron** for datacenter-level SDN if Cilium's underlying capabilities are insufficient at a given site) is adopted at the **bottom** of the stack, for:

- Bare-metal lifecycle management of physical GPU/CPU hosts before they're handed to Kubernetes as nodes (via **Cluster API Provider for OpenStack**, or Ironic directly for bare-metal Kubernetes nodes via `metal3`).
- Datacenter-level tenant network isolation in owned/colocated facilities (as opposed to when running on top of a public cloud's own networking, where CNCP would use that cloud's native VPC primitives instead — see Multi-Cloud Federation, Part 4/5).

This is an important architectural clarification versus a naive reading of "adopt OpenStack": **OpenStack is the bare-metal/IaaS foundation layer for self-operated datacenters, not the workload scheduler users' sessions run through.** Kubernetes is that layer, uniformly, whether the underlying node was provisioned by OpenStack Ironic (owned DC), a public cloud API (federated capacity), or a partner GPU marketplace (Part 5).

## 13.3 Compute Substrate Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Kubernetes Control Plane (per region)            │
│         (etcd, kube-apiserver, controller-manager, scheduler)        │
└───────────────────────────────┬───────────────────────────────────────┘
                                 │
        ┌────────────────────────┼─────────────────────────┐
        ▼                        ▼                          ▼
┌───────────────┐      ┌──────────────────┐        ┌─────────────────┐
│  Standard Node │      │  KubeVirt Node    │        │ Firecracker Node │
│  Pool          │      │  Pool (GPU VMs)   │        │ Pool (microVMs)  │
│  (containers:  │      │                    │        │                  │
│   dev envs,    │      │  Full GPU passthru │        │ Fast-boot        │
│   CI, APIs)    │      │  or vGPU (NVIDIA   │        │ isolated sessions│
│                │      │  MIG/vGPU)         │        │ (short-lived     │
│                │      │  DaVinci, Blender, │        │ builds, sandboxed│
│                │      │  Unreal, gaming    │        │ agent execution) │
└───────────────┘      └──────────────────┘        └─────────────────┘
        │                        │                          │
        └────────────────────────┼──────────────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │  Bare-Metal Provisioning │
                    │  OpenStack Ironico /      │
                    │  metal3 + Cluster API     │
                    └─────────────────────────┘
```

## 13.4 GPU Allocation Strategies

| Strategy | Technology | Use Case | Isolation |
|---|---|---|---|
| Full passthrough | PCIe passthrough via KubeVirt | Creative workstation sessions needing full GPU (DaVinci color grading, Unreal packaging) | Strongest (dedicated physical GPU per session) |
| vGPU / MIG partitioning | NVIDIA vGPU or Multi-Instance GPU | Multiple concurrent lighter sessions on a single datacenter GPU (e.g., several Blender viewport sessions) | Hardware-enforced partition, shared physical die |
| Time-sliced sharing | Kubernetes device plugin time-slicing | Bursty/inference workloads (Part 3 AI) that don't need dedicated GPU continuously | Weakest, software-scheduled — never used for a paying session's *interactive* workload, only for background/batch AI tasks |
| Cloud gaming pool | Dedicated vGPU profiles tuned for encode (NVENC) | Cloud Gaming (Part 4) | Per-session vGPU slice sized for the target game's requirements |

**Assumption stated explicitly:** vGPU licensing (NVIDIA GRID/vGPU software licensing) is a commercial dependency, not an open-source component — flagged here because it is the one place in this "open-source-first" platform where a proprietary vendor dependency is structurally unavoidable given the current state of GPU virtualization technology. AMD MxGPU is a lower-cost alternative worth evaluating for cost-sensitive GPU pools, at the trade-off of a smaller CUDA-adjacent software ecosystem for creative/ML tooling.

## 13.5 Build vs Adopt vs Modify — Compute Substrate

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Container orchestration | ❌ | ✅ Kubernetes | ❌ | Industry standard, no viable alternative worth building |
| VM-in-Kubernetes | ❌ | ✅ KubeVirt | Partial (CNCP GPU-migration controller, Ch.11.3) | Mature CNCF project; GPU-state-migration hooks are the only CNCP-specific extension needed |
| MicroVMs | ❌ | ✅ Firecracker | ❌ | Purpose-built for exactly this (AWS Lambda/Fargate heritage), extremely mature |
| Bare-metal provisioning | ❌ | ✅ OpenStack Ironic / metal3 | ❌ | Solved problem |
| Kubernetes scheduler extensions | ✅ | Adopt framework | ✅ | The scheduler *framework* is adopted (Kubernetes scheduler framework); the CNCP scoring plugin is built (Ch.12.5) |
| GPU device plugins | ❌ | ✅ NVIDIA/AMD device plugins | Partial | Vendor-provided plugins adopted; thin CNCP wrapper for telemetry integration |

## 13.6 Testing Matrix — Compute Substrate

| Feature | Local | Docker | Kubernetes (Kind) | OpenStack (DevStack) | Public Cloud | Production |
|---|---|---|---|---|---|---|
| Container scheduling | N/A | ✅ single container | ✅ full scheduler tests | N/A | ✅ (managed K8s) | ✅ |
| KubeVirt VM lifecycle | N/A | N/A | ✅ (KubeVirt runs on Kind with nested virt or software emulation) | N/A | ✅ (bare-metal-backed cloud instances) | ✅ |
| GPU passthrough | N/A | N/A | ⚠️ requires physical GPU node, not emulable in Kind | N/A | ✅ (GPU instance types) | ✅ |
| Bare-metal provisioning | N/A | N/A | N/A | ✅ DevStack Ironic (virtual bare metal) | N/A | ✅ |

---

# Chapter 14 — Networking

## 14.1 Requirements Recap

From Chapter 8 (NFRs): sub-80ms added latency (p95) for cloud-streamed interactive workloads, mTLS everywhere internally, Zero Trust posture. Networking is the layer where CNCP's "feels local" promise is won or lost — no amount of Cloud OS UX polish compensates for laggy streamed input.

## 14.2 Edge/Transport Architecture

```
┌────────────┐      Anycast IP        ┌──────────────────────┐
│   Client    │───────────────────────►│  Nearest Regional PoP │
│  (WebRTC/   │◄───────────────────────│  (STUN/TURN, session   │
│   QUIC)     │   media + control       │   negotiation, WAF)    │
└────────────┘                         └──────────┬─────────────┘
                                                    │ private backbone
                                                    │ (WireGuard mesh between
                                                    │  regions, or provider
                                                    │  backbone if available)
                                                    ▼
                                        ┌──────────────────────┐
                                        │  Regional Data Plane   │
                                        │  (session actually runs│
                                        │   here; PoP is only a  │
                                        │   relay/negotiator)    │
                                        └──────────────────────┘
```

Key design decision: the **PoP is a negotiator and TURN relay, not where compute happens.** For most users, WebRTC establishes a direct(ish) path from client to the regional data-plane node closest to them (selected by the Scheduler using the regional GPU pool availability signal from Ch.12.2), with the PoP falling back to relay mode (TURN) only when direct/STUN-assisted connectivity fails (roughly 15-20% of real-world networks, per typical WebRTC deployment experience, due to symmetric NATs/restrictive firewalls).

## 14.3 Protocol Choices

| Layer | Protocol | Why |
|---|---|---|
| Media transport (video/audio stream from cloud session) | WebRTC (SRTP over DTLS) | Industry standard for real-time media, built-in congestion control (via Google Congestion Control / BBR-derived), NAT traversal via ICE/STUN/TURN out of the box |
| Control/data channel (input events, session control) | WebRTC DataChannel (SCTP) or raw QUIC stream | Ordered-or-unordered, reliable-or-unreliable delivery choice per message type — input events use unreliable/unordered with sequence numbers (a stale mouse-move is worse than a dropped one) |
| Client-to-control-plane API calls | HTTP/3 (QUIC) | 0-RTT reconnection after network change (e.g., WiFi→cellular handoff on a laptop), critical for the "session continuity across devices" commitment (Ch.2.2) |
| Service-to-service (control plane, data plane internal) | gRPC over mTLS | Strong typing, streaming support, standard in cloud-native stacks |
| East-west encryption/policy | Cilium (eBPF-based CNI) + mTLS via service mesh | See 14.5 |

## 14.4 Video Codec Strategy (Cloud-Streamed Windows/Gaming)

- **AV1** preferred where client GPU decode support exists (increasingly common on 2023+ hardware) — best quality-per-bit, reducing bandwidth requirements which directly reduces both latency-under-congestion and egress cost.
- **H.264** universal fallback for older client hardware.
- **Adaptive bitrate**, driven by the same telemetry loop as the Scheduler (Ch.12.2 bandwidth signal) — not a separate subsystem, deliberately, so that "bad network" triggers both a bitrate reduction *and* is available as a scheduler signal (e.g., a workload might be a better candidate for local execution if the network is currently bad, even if it would normally be cloud-only-preferred).
- Encode side: NVENC/AMF hardware encoders on the datacenter GPU node, never software x264 encode at scale (cost and latency both suffer).

## 14.5 Zero Trust & Service Mesh

- **Cilium** (eBPF-based CNI) adopted for Kubernetes networking — chosen over alternatives (Calico, Flannel) for its eBPF-native performance profile (no iptables overhead at scale) and built-in L7 policy/observability (Hubble), which reduces the need for a separate service mesh sidecar for many use cases.
- **Linkerd** adopted as the service mesh for the subset of services needing full mTLS+traffic-shaping (control plane services in particular) — chosen over Istio for its materially lower operational complexity and resource overhead, which matters given CNCP's own philosophy of not over-engineering non-differentiating infrastructure.
- **Zero Trust posture**: no service trusts another based on network location alone; every service-to-service call is authenticated (mTLS client cert, workload identity via SPIFFE/SPIRE — adopted, integrates with Linkerd) and authorized (OPA policy check, same engine as Ch.12.6).

## 14.6 SD-WAN / Private Backbone (Enterprise & Multi-Region)

For Phase 5 (enterprise, multi-region), inter-region backbone connectivity uses a **WireGuard mesh** (adopted — extremely low overhead, kernel-native on Linux, simple key rotation) between regional data planes, with route optimization informed by the same latency telemetry the Scheduler already collects (Ch.12.2), avoiding a second independent network-monitoring system.

## 14.7 Build vs Adopt vs Modify — Networking

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| CNI | ❌ | ✅ Cilium | ❌ | Best-in-class eBPF CNI, mature |
| Service mesh | ❌ | ✅ Linkerd | ❌ | Lower overhead than Istio, sufficient feature set |
| Media transport | ❌ | ✅ WebRTC (libwebrtc) | ✅ (CNCP signaling server, congestion-control tuning for datacenter-to-client profile) | Reinventing real-time media transport is not defensible; the signaling layer is CNCP-specific |
| CDN/Edge/WAF | ❌ | ✅ (Cloudflare, or self-op via adopted OSS like Envoy Gateway) at smaller scale | Partial | Build vs buy decision for Phase 1-2 leans "buy" (Cloudflare) for time-to-market; revisit self-operated edge at Phase 5 scale for cost reasons (Chapter 12.6-style trade-off, deferred to Part 7 cost analysis) |
| Session signaling/negotiation server | ✅ | Framework adopted (e.g., built on `pion` WebRTC Go library, or `aiortc`) | — | The negotiation logic tying signaling to Scheduler placement decisions is CNCP-specific business logic |

## 14.8 Testing Matrix — Networking

| Feature | Local | Docker Compose | Kubernetes (Kind) | Staging (real network) | Production |
|---|---|---|---|---|---|
| WebRTC session establishment | ✅ (loopback) | ✅ (two containers, simulated NAT via `netem`) | ✅ | ✅ (real-world NAT diversity testing) | ✅ |
| Adaptive bitrate under packet loss | ✅ (`tc netem` loss injection) | ✅ | ✅ | ✅ | Monitored, not "tested" per se |
| mTLS/Cilium policy enforcement | N/A | Partial | ✅ (Kind + Cilium) | ✅ | ✅ |
| Cross-region backbone failover | N/A | N/A | N/A | ✅ (multi-region staging) | ✅ (chaos drills) |

---

# Chapter 15 — Storage

## 15.1 Storage Tiers

CNCP needs three distinct storage systems, each solving a different problem — a common mistake is trying to use one storage system for all of them:

| Tier | Purpose | Technology | Consistency Model |
|---|---|---|---|
| **Object storage** | Personal cloud file storage, marketplace assets, workspace snapshot blobs, backups | MinIO (self-operated, S3-compatible) | Eventually consistent for cross-region replication; strongly consistent within a region |
| **Block storage** | VM/microVM root and data disks (KubeVirt/Firecracker) | Ceph RBD | Strongly consistent, replicated (default 3x) |
| **Distributed/POSIX-ish filesystem** | The unified namespace spanning local disk + cloud + NAS presented to the user (Chapter 15b) | Built on top of the above, CNCP-specific sync/metadata layer | Documented per-operation in 15b |

## 15.2 Why Ceph AND MinIO (Not One or the Other)

This is a deliberate architectural choice worth justifying explicitly, since a reasonable alternative design would pick just one:

- **Ceph** is the right choice for **block storage** (RBD) backing VM disks, where CNCP needs POSIX/block semantics, snapshotting, and thin-provisioning with strong consistency — this is what KubeVirt VMs need for their virtual disks.
- **MinIO** is the right choice for **object storage** (S3 API) because the vast majority of CNCP's storage volume (user files, marketplace assets, workspace snapshot blobs, ML model artifacts) is accessed via object semantics (GET/PUT whole objects or byte-ranges), not block semantics, and MinIO's operational simplicity and S3-API compatibility (huge ecosystem of existing tools, SDKs, and the ability to let *advanced* users point their own S3-compatible tools directly at their personal cloud storage) outweighs the benefit of consolidating onto Ceph's RGW (Ceph's own S3-compatible object gateway), which is more operationally complex to run well at CNCP's expected scale in Phases 1-3.
- **Reassess at Phase 5 scale**: at true hyperscale, consolidating onto Ceph (RGW + RBD from one cluster) may reduce operational surface area; this is flagged as a deferred architecture decision, not resolved now, since premature consolidation risks optimizing for a scale CNCP hasn't reached yet.

## 15.3 Object Storage Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                      MinIO Cluster (per region)                 │
│  Erasure-coded across ≥4 nodes (default EC:4+2, tunable)        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  Node 1    │ │  Node 2    │ │  Node 3    │ │  Node 4    │       │
│  │  (drives)  │ │  (drives)  │ │  (drives)  │ │  (drives)  │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└──────────────────────────┬────────────────────────────────────┘
                            │ async bucket replication (site-replication)
                            ▼
              ┌───────────────────────────┐
              │  MinIO Cluster (region 2)  │  ← cross-region durability +
              │                            │     data-residency compliance
              └───────────────────────────┘     (bucket placement policy
                                                   enforces EU-only replication
                                                   for GDPR-flagged accounts)
```

Durability target (Ch.8 NFR: 11 nines) achieved via erasure coding (EC:4+2 tolerates 2 simultaneous drive failures per erasure set) combined with cross-region replication for disaster recovery (Part 7 will cover full DR runbooks).

## 15.4 Storage Lifecycle & Data Model

```sql
-- Illustrative schema for the object storage metadata layer
-- (MinIO stores objects; this metadata table is CNCP's own catalog
--  for versioning UX, sharing, and quota enforcement beyond raw S3 semantics)

CREATE TABLE storage_object (
    id                UUID PRIMARY KEY,
    bucket            TEXT NOT NULL,
    object_key        TEXT NOT NULL,
    owner_account_id  UUID NOT NULL REFERENCES account(id),
    size_bytes        BIGINT NOT NULL,
    content_hash      TEXT NOT NULL,          -- for dedup detection (Ch.15b)
    version_id        TEXT NOT NULL,          -- MinIO/S3 native versioning id
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    lifecycle_class   TEXT NOT NULL DEFAULT 'standard',  -- standard|cold|archive
    encryption_key_ref TEXT NOT NULL,         -- reference into KMS, not the key itself
    UNIQUE (bucket, object_key, version_id)
);

CREATE INDEX idx_storage_object_owner ON storage_object(owner_account_id);
CREATE INDEX idx_storage_object_hash ON storage_object(content_hash);
```

- **Lifecycle policies**: standard → cold (after 90 days no access, configurable) → archive (after 1 year), implemented via MinIO's native lifecycle management (ILM) rules, not reinvented.
- **Encryption**: server-side encryption with per-object data keys (envelope encryption), master keys held in the KMS (Chapter 16.4) — object storage itself never sees the master key.

## 15.5 Build vs Adopt vs Modify — Storage

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Object storage | ❌ | ✅ MinIO | ❌ | Mature, S3-compatible, self-hostable, Apache 2.0/AGPL depending on version — license terms must be verified per deployment model (see note below) |
| Block storage | ❌ | ✅ Ceph (RBD) | ❌ | Industry-standard distributed block storage |
| Storage metadata catalog | ✅ | — | — | CNCP-specific (versioning UX, quota, sharing semantics beyond raw S3) |
| KMS | ❌ | ✅ OpenBao (Vault fork) | Partial | Mature secrets/KMS; CNCP integrates, doesn't rebuild |

**License note (explicit assumption):** MinIO's licensing has shifted over time between Apache 2.0 and AGPLv3 for different components/versions; this must be verified against MinIO's current licensing terms at implementation time and reviewed by legal/compliance before production adoption, since AGPL obligations differ materially from Apache 2.0 for a company redistributing/operating the software as a service. This is flagged rather than asserted because license terms change and asserting a specific one here without current verification would be unreliable.

## 15.6 Testing Matrix — Storage

| Feature | Local (Docker) | Kubernetes (Kind) | Staging | Production |
|---|---|---|---|---|
| Object CRUD + versioning | ✅ (single-node MinIO container) | ✅ (MinIO Operator, multi-node) | ✅ | ✅ |
| Erasure coding / drive failure tolerance | ⚠️ limited (needs ≥4 simulated drives) | ✅ | ✅ (real drive-pull tests) | ✅ (chaos drills) |
| Cross-region replication | N/A | ✅ (two Kind clusters) | ✅ | ✅ |
| Ceph RBD for VM disks | N/A | ✅ (Rook-Ceph on Kind, reduced replica count) | ✅ | ✅ |

---

# Chapter 15b — Distributed Filesystem

## 15b.1 The Unified Namespace Problem

The user should see **one filesystem** — `~/CNCP/` (or platform-equivalent) — that transparently spans:

- Local disk (fast, always available, no network dependency)
- Personal cloud object storage (Ch.15)
- Mounted NAS (home lab / office server)
- External drives

This is presented via a **FUSE-based filesystem driver** (macOS/Linux via `libfuse`/`macFUSE`; Windows via `WinFsp`, which provides FUSE-equivalent semantics) backed by a metadata service that tracks, for every file, its current location(s) and sync state.

## 15b.2 Metadata & Caching Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      Local FUSE Mount                        │
│   Reads/writes routed based on local metadata cache first    │
└───────────────────────┬────────────────────────────────────┘
                         │ cache miss / write-through
                         ▼
┌────────────────────────────────────────────────────────────┐
│                Filesystem Metadata Service                   │
│   PostgreSQL: file tree, location pointers, version chain     │
│   Valkey: hot-path metadata cache (recently accessed files)   │
└───────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼─────────────────┐
        ▼                ▼                  ▼
   Local Disk      MinIO (Ch.15)      Mounted NAS/SMB
```

## 15b.3 Sync Model — Event-Driven, Delta-Based

| Concern | Approach |
|---|---|
| Change detection | OS-native file watchers (inotify/FSEvents/ReadDirectoryChangesW) rather than polling — immediate sync trigger, lower CPU overhead |
| Delta sync | Content-defined chunking (rolling hash, similar to rsync's algorithm / restic's chunker) — only changed chunks re-uploaded, not whole files |
| Compression | Zstd, applied per-chunk before upload | 
| Deduplication | Content-hash-addressed chunk store — identical chunks across different files/users' shared marketplace assets stored once (subject to per-tenant encryption boundaries — dedup only within a security domain, never across tenants, to avoid any cross-tenant information leakage via storage side-channels) |
| Conflict detection | Vector-clock-style version tracking per file; concurrent edits from two devices produce a conflict marker (both versions preserved, user/last-writer-wins policy configurable per workspace) rather than silent data loss |
| Offline mode | Local writes queue in a durable local WAL (write-ahead log); sync resumes and replays the WAL when connectivity returns; WAL replay order preserves causal ordering per file |
| Bandwidth optimization | Chunk-level resume (interrupted upload/download resumes from last complete chunk, not from zero) |

## 15b.4 Consistency Model

CNCP's Distributed Filesystem deliberately adopts **eventual consistency with explicit conflict surfacing**, not a false promise of strong consistency across disconnected devices — this is stated explicitly because over-promising POSIX-strength consistency across a distributed, sometimes-offline filesystem is a common design trap that leads to silent data corruption in edge cases. Within a single connected session, writes are read-after-write consistent (the FUSE layer serves its own writes from local cache immediately). Across devices, consistency is "sync-then-consistent" — i.e., consistent once the sync round-trip completes, with the conflict-detection mechanism (15b.3) as the safety net for the window where it hasn't.

## 15b.5 Build vs Adopt vs Modify — Distributed Filesystem

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| FUSE driver (Linux/macOS) | Partial | ✅ (libfuse/macFUSE as the kernel-interface library) | ✅ (CNCP filesystem logic on top) | No OSS project provides the *specific* unified local+cloud+NAS namespace with CNCP's metadata model; the low-level FUSE plumbing is adopted, the filesystem logic is built |
| Windows filesystem driver | Partial | ✅ (WinFsp) | ✅ | Same pattern as above for Windows |
| Chunking/dedup algorithm | ❌ | ✅ (adapt `restic`'s or `rclone`'s chunking approach as reference implementation, or use `FastCDC` library directly) | Partial | Content-defined chunking is a well-solved algorithmic problem; use an established library rather than inventing a new chunking algorithm |
| Metadata service | ✅ | Adopt substrate (Postgres, Valkey) | — | The schema and sync-state machine are CNCP-specific business logic |
| General-purpose cloud sync engine reference | — | Studied (Nextcloud, Syncthing, rclone are useful prior art) | — | None of these solve the *unified local+cloud+execution-aware* namespace CNCP needs, but their sync-conflict algorithms are useful reference designs, not directly adoptable wholesale |

## 15b.6 Testing Matrix — Distributed Filesystem

| Feature | Local | Docker (simulated multi-device) | Kubernetes (metadata service) | Staging | Production |
|---|---|---|---|---|---|
| Basic FUSE read/write | ✅ | N/A | N/A | ✅ | ✅ |
| Delta sync correctness | ✅ (two local mounts, one mock remote) | ✅ (two containers acting as two devices) | ✅ | ✅ | ✅ |
| Conflict detection | ✅ (forced concurrent write test) | ✅ | ✅ | ✅ | Monitored |
| Offline queue + replay | ✅ (network namespace isolation to simulate offline) | ✅ | N/A | ✅ | ✅ |

---

# Chapter 16 — Security

## 16.1 Threat Model Summary

CNCP's threat model is unusually broad because it spans (a) a consumer-facing client running on untrusted end-user devices, (b) a multi-tenant cloud substrate running arbitrary user workloads including GPU-passthrough VMs, and (c) enterprise compliance requirements. Key threat classes:

| Threat | Primary Mitigation |
|---|---|
| Cross-tenant data leakage via shared GPU/compute | Hardware-enforced isolation where possible (MIG partitioning, passthrough); never share a physical GPU between tenants without hardware partitioning for anything above the lowest trust tier |
| Credential theft / session hijacking | Passkeys/WebAuthn as primary auth, short-lived session tokens, mTLS for all service calls |
| Malicious marketplace content (apps, AI agents, IaC templates) | Sandboxed execution (Firecracker microVM isolation per Ch.13), static scanning, SBOM requirement, staged rollout/reputation system (Part 5) |
| Supply chain compromise (CNCP's own build pipeline) | SLSA-aligned build provenance, signed artifacts (Sigstore/cosign), SBOM generation on every release |
| Data exfiltration via clipboard/file sync | Clipboard content-type filtering (Ch.10.3), DLP policy hooks at the org level (enterprise tier) |
| Physical device compromise (lost/stolen laptop) | Local client stores no long-lived credentials; session re-auth required, remote session revocation from the Cloud OS |

## 16.2 Identity & Access Management

- **Keycloak** adopted as the IAM core — OIDC/SAML/OAuth2 provider, supports the full enterprise SSO surface (SAML for legacy enterprise IdPs, OIDC for modern), MFA, and passkey/WebAuthn support natively.
- **Passkeys as the default/preferred consumer auth method**, with password+MFA as fallback — reduces phishing surface area significantly versus password-first design, and aligns with the "computing should just work" experience contract (Ch.2.2) since passkeys remove password-management friction.
- **RBAC hierarchy**: Org → Team → Project → Workspace, with role inheritance and explicit override capability at each level (schema detail in Part 5, Multi-Tenancy chapter).

## 16.3 Zero Trust Enforcement Points

```
┌──────────┐    mTLS+JWT    ┌──────────┐    mTLS+SPIFFE   ┌──────────┐
│  Client   │───────────────►│  Gateway  │─────────────────►│ Control  │
│           │  (short-lived   │           │  (workload ID,   │  Plane   │
│           │   session token)│           │   OPA policy)     │ Services │
└──────────┘                └──────────┘                  └──────────┘
                                                                   │
                                                        every internal
                                                        call re-checked
                                                        against OPA policy,
                                                        never implicitly
                                                        trusted by network
                                                        location alone
```

No service, including internal CNCP infrastructure services, is trusted purely because it's "inside the VPC" — this is the literal meaning of Zero Trust and is enforced structurally via the mesh (Linkerd, Ch.14.5) + OPA policy layer (Ch.12.6), not just asserted as a principle.

## 16.4 Encryption & Key Management

| Data Class | At Rest | In Transit | Key Holder |
|---|---|---|---|
| Personal cloud object storage | AES-256-GCM, envelope encryption | TLS 1.3 | KMS-managed data keys; master key optionally user-escrowed for "sovereign" tier accounts (advanced/enterprise feature, not default, since full user-held keys preclude server-side features like search-over-content and must be explicitly opted into) |
| Block storage (VM disks) | LUKS/dm-crypt at the Ceph RBD layer | N/A (internal) | KMS-managed |
| Secrets (API keys, DB credentials for Personal Cloud) | Encrypted, versioned | TLS 1.3, mTLS internal | OpenBao (Vault-compatible) |
| Backups | AES-256, separate key rotation schedule from primary data | TLS 1.3 | KMS-managed, cross-region key replication policy matches data replication policy (Ch.15.3) |

**KMS**: OpenBao (open-source Vault fork, post-HashiCorp's license change to BUSL) adopted for secrets management and as the root of the key hierarchy; HSM-backed root keys (via PKCS#11 integration, cloud KMS HSM tiers, or self-operated HSM in owned datacenters) for the top of the key hierarchy in enterprise/compliance-sensitive deployments.

## 16.5 Confidential Computing & Attestation (Forward-Looking, Phase 4-5)

For the highest-trust tier (enterprise workloads processing regulated data), CNCP should evaluate **confidential computing** (AMD SEV-SNP / Intel TDX) for GPU-passthrough VM sessions, combined with **remote attestation** so an enterprise customer can cryptographically verify their workload executed in a genuinely isolated, unmodified environment before trusting it with sensitive data. This is explicitly scoped as Phase 4-5, not earlier, because confidential computing GPU support is still maturing industry-wide and should not block earlier phases' delivery.

## 16.6 Compliance Posture by Phase

| Framework | Relevance | Target Phase |
|---|---|---|
| GDPR | Data residency controls, right-to-erasure workflows, DPA-ready | Phase 3 (when EU users/enterprise onboarding begins in earnest) |
| SOC 2 Type II | Baseline enterprise trust requirement | Phase 5 entry |
| ISO 27001 | Larger enterprise/regulated-industry requirement | Phase 5, opportunistic (pursue if a design partner requires it sooner) |
| HIPAA | Only relevant if CNCP pursues healthcare-vertical enterprise customers | Not committed in current roadmap; would require a dedicated compliance workstream and BAA-capable infrastructure, out of scope unless a specific business decision is made to pursue this vertical |
| PCI DSS | Only relevant to CNCP's own billing/payment handling, not customer workload data | Handled by using a PCI-compliant payment processor (e.g., Stripe) rather than CNCP handling raw card data directly — standard "outsource PCI scope" pattern |

## 16.7 Build vs Adopt vs Modify — Security

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| IAM/SSO | ❌ | ✅ Keycloak | Partial (custom passkey-first UX flow) | Mature, feature-complete OIDC/SAML provider |
| Secrets/KMS | ❌ | ✅ OpenBao | ❌ | Mature, Vault-API-compatible |
| Policy engine | ❌ | ✅ Open Policy Agent | ✅ (CNCP-authored Rego policies) | Industry standard |
| Workload identity | ❌ | ✅ SPIFFE/SPIRE | ❌ | Purpose-built for exactly this problem |
| SBOM / supply chain | ❌ | ✅ Syft/Grype (generation/scanning), Sigstore/cosign (signing) | Partial (CI pipeline integration) | Established CNCF supply-chain security tooling |
| Marketplace content sandboxing | ✅ (policy/orchestration layer) | ✅ (Firecracker as the isolation primitive, Ch.13) | — | The isolation primitive is adopted; the marketplace-specific sandboxing policy and review pipeline is CNCP-specific (Part 5) |

## 16.8 Testing Matrix — Security

| Feature | Local | Docker/Kind | Staging | Production |
|---|---|---|---|---|
| IAM/auth flows (passkey, OIDC, SAML) | ✅ (Keycloak dev-mode container) | ✅ | ✅ (full IdP integration tests with partner IdPs) | ✅ |
| mTLS/policy enforcement | ⚠️ limited (mesh needs multi-node) | ✅ (Kind + Linkerd + OPA) | ✅ | ✅ |
| Penetration testing | N/A | N/A | ✅ (internal red team) | ✅ (third-party pentest, at least annually, required before Phase 5 enterprise GA) |
| SBOM generation & signing | ✅ (local CI dry-run) | ✅ | ✅ | ✅ (gate: no unsigned artifact reaches production) |
| Chaos/failure-mode security (e.g., forced node compromise simulation) | N/A | Partial | ✅ | ✅ (game days) |

---

## End of Part 2

Part 2 has covered the full infrastructure substrate: Compute (Chapter 13 — Kubernetes/KubeVirt/Firecracker/OpenStack-Ironic, GPU allocation strategy), Networking (Chapter 14 — WebRTC/QUIC transport, Cilium/Linkerd, Zero Trust), Storage (Chapter 15 — Ceph + MinIO split rationale, lifecycle/encryption), the Distributed Filesystem (Chapter 15b — unified namespace, sync/conflict model), and Security (Chapter 16 — IAM, Zero Trust enforcement, KMS, compliance roadmap).

**Next:** Part 3 will cover AI Integration, the AI Memory System (Mem0/Qdrant/OpenSearch), Digital Twin, and the Developer Platform (CLI/SDK/CI-CD/cloud IDE).

Reply **"continue with Part 3"** to proceed.
