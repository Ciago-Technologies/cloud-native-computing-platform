# \<Project Name\>
## Cloud Native Computing Platform — Enterprise Architecture & Design Document

**Prepared for:** Ciago Technologies — Engineering Leadership, Investors, Enterprise Customers, Implementation Teams
**Classification:** Confidential — Internal Codename "Ciago CNCP" (not for public use)
**Document Type:** Software Architecture Design Document (SADD)
**Version:** 1.0 — Draft for Executive & Technical Review

---

### Table of Contents

1. Executive Summary
2. Product Vision
3. Business Goals
4. Market Opportunity
5. Industry Analysis
6. User Personas
7. Functional Requirements
8. Non-Functional Requirements
9. System Architecture
10. Cloud OS Architecture
11. Hybrid Execution Engine
12. Scheduling Engine
13. Cloud Infrastructure
14. Networking
15. Storage
16. Security
17. AI Integration
18. Developer Platform
19. IaaS Platform
20. Application Platform
21. Gaming Platform
22. Creative Platform
23. Billing
24. Scalability
25. Disaster Recovery
26. Monitoring
27. Cost Optimization
28. Deployment Strategy
29. Roadmap
30. Competitive Analysis
31. Risks
32. Future Innovations
33. Conclusion

---

## 1. Executive Summary

\<Project Name\> is Ciago Technologies' next-generation **Cloud Native Computing Platform (CNCP)** — a system designed to function not as an incremental cloud service, but as a full replacement for the traditional relationship between a user's device and their compute. The fundamental thesis of this platform is that the historical binding between "the device you own" and "the compute you can access" is an artifact of 1980s personal computing economics, not a law of nature. \<Project Name\> breaks this binding by presenting every user — regardless of the physical hardware in front of them — with an elastic, workstation-class (or better) computing environment that is delivered as a *service*, not as a *machine*.

Concretely, \<Project Name\> is composed of four tightly integrated layers:

1. **A native lightweight client** for Windows, macOS, and Linux that behaves as a "portal" rather than a full remote-desktop application, providing near-native input latency, display fidelity, and OS-level integration (file system mounts, clipboard, notifications, peripheral passthrough).
2. **A Cloud Operating System (Cloud OS)** — an original, opinionated desktop environment, application launcher, window manager, and workspace model that runs partially on the client and partially in Ciago's data centers, giving users a single coherent "OS" experience regardless of where any individual application is actually executing.
3. **A Hybrid Execution Engine** that transparently and continuously decides, on a per-process and per-workload basis, whether execution should occur locally, remotely, or in a split configuration — using live migration, checkpointing, and state synchronization to move workloads without user-visible interruption.
4. **A full Infrastructure-as-a-Service and Platform-as-a-Service substrate** beneath the consumer-facing Cloud OS, exposing the same GPU/CPU/storage/network fabric to developers, enterprises, and automated systems via APIs, CLI, Terraform/Pulumi providers, and Kubernetes-compatible primitives.

This document is the authoritative architecture reference for the platform. It covers the complete stack from client-side input handling down to physical GPU allocation, and every subsystem in between: identity, networking, storage, scheduling, billing, multi-tenancy, observability, and security. It is written to a level of technical depth suitable for direct implementation planning — assumptions are stated explicitly wherever the architecture depends on them, and no section is a placeholder.

**Assumption A-1:** Wherever this document references a decision that depends on unannounced third-party pricing, licensing, or hardware roadmaps (e.g., future NVIDIA GPU generations, cloud provider spot pricing, or CXL 3.x consortium timelines), we state the assumption used for planning purposes and flag it as subject to revision.

The strategic bet underlying \<Project Name\> is that three converging trends make this platform viable in a way it was not five years ago: (1) commodity fiber and 5G/6G access networks have pushed median last-mile latency below the threshold where remote execution feels "instant" for the majority of interactive workloads; (2) GPU virtualization and partitioning technologies (MIG, SR-IOV, vGPU) have matured to the point where fractional, secure, multi-tenant GPU sharing is a solved engineering problem rather than a research problem; and (3) container and micro-VM isolation technology (Firecracker, Kata Containers, gVisor) makes it economically and operationally feasible to give every user session strong isolation without the overhead of full hardware virtualization.

\<Project Name\> is not a remote desktop product, a cloud gaming product, or an IaaS product in isolation — it is the fusion of all three under one identity, one billing model, and one seamless client experience, architected so that the boundary between "your computer" and "the cloud" disappears from the user's point of view.

---

## 2. Product Vision

### 2.1 Vision Statement

*Any device becomes any computer.* A person should be able to sit down at a five-year-old, fanless, 8GB-RAM laptop and, within the same session, browse the web locally, open a 40GB Autodesk Maya scene that streams from a cloud workstation with a virtualized top-of-stack GPU, spin up a 64-node Kubernetes cluster from a terminal window on the desktop, and play a AAA game at 4K/120fps — all without ever being aware of where computation is actually happening, and without installing anything beyond the initial lightweight client.

### 2.2 Why "Cloud Operating System" and Not "Remote Desktop"

Existing remote desktop and DaaS (Desktop-as-a-Service) products — Windows 365, Azure Virtual Desktop, VMware Horizon, Citrix — provide access to a *specific remote machine or session*, rendered pixel-for-pixel over a remote display protocol (RDP, PCoIP, Blast, or similar). The user experience is fundamentally "I am looking at another computer through a window." This creates persistent, perceptible friction:

- Window resizing and multi-monitor behave awkwardly because the remote session has its own independent notion of display topology.
- Local and remote clipboard, file systems, and notification systems are bridged rather than unified.
- The remote session is a single monolithic VM or persistent desktop — it cannot silently decompose a workload into "the 2% that must run in the cloud" and "the 98% that can run locally."

\<Project Name\>'s Cloud OS instead treats "local" and "remote" as *implementation details of a single environment*. The window manager, notification system, clipboard, and file explorer are cloud-OS-native constructs that route their backing operations to whichever execution venue currently holds the relevant process — including mid-session migration — while presenting one consistent visual and interaction model. This is the core differentiator and the most architecturally demanding component of the system (detailed in Sections 10 and 11).

### 2.3 Design Principles

| Principle | Description | Architectural Consequence |
|---|---|---|
| Invisible infrastructure | The user should never be asked "run this locally or in the cloud?" | Requires an always-on, low-overhead scheduling engine (Section 12) making placement decisions transparently |
| Continuity over consistency | A session surviving a network blip matters more than perfect state consistency at every instant | Requires checkpoint/restore and eventually-consistent file sync rather than strict distributed transactions for most subsystems |
| Progressive disclosure of power | Casual users see a simple desktop; power users can drop into a full IaaS/Kubernetes control plane from the same identity | Single control plane with layered UX, not two separate products |
| Hardware abstraction, not hardware negation | We do not claim to make local hardware irrelevant — thin/low-power clients still handle local-first workloads (input, audio, low-latency compositing) | The client is a real runtime, not a dumb pixel receiver (Section 9) |
| Cost-aware by default | Every placement and scaling decision has a cost dimension surfaced to the user/org, not hidden until the invoice | FinOps instrumentation is a first-class scheduler input (Section 12, Section 27) |

### 2.4 Non-Goals (Explicitly Out of Scope for v1)

- Replacing enterprise identity providers (we federate with them, we do not attempt to replace Okta/Entra ID/Ping for existing enterprise customers).
- Building proprietary silicon (the platform is designed around commodity and merchant-silicon GPUs/CPUs; a custom ASIC/accelerator strategy is a Phase 4+ consideration, see Section 29).
- Supporting arbitrary legacy hardware peripherals (e.g., exotic USB dongles, proprietary industrial hardware) in the initial GA — peripheral passthrough is scoped to common classes (HID, audio, storage, printers, standard webcams) in Phase 1–2.

---

## 3. Business Goals

### 3.1 Strategic Objectives

| # | Objective | Metric | Target (36 months post-GA) |
|---|---|---|---|
| B-1 | Democratize workstation-class compute | % of active users on sub-$600 devices running "workstation-tier" workloads | ≥ 40% |
| B-2 | Become a credible IaaS alternative for GPU workloads | Monthly active developer accounts deploying via CLI/API/Terraform | 250,000 |
| B-3 | Establish recurring, predictable revenue | % revenue from subscription vs. pure usage-based | 60/40 blended by Phase 3 |
| B-4 | Achieve gross margin parity with hyperscaler IaaS | Blended gross margin on compute/storage/network | ≥ 55% (Phase 3), ≥ 65% (Phase 5) |
| B-5 | Win creative & engineering professional segment | Paid seats among 3D/video/CAD professionals | 500,000 |
| B-6 | Build a credible cloud-gaming alternative | Concurrent peak gaming sessions | 1,000,000 |
| B-7 | Enterprise land-and-expand | Net revenue retention (enterprise tier) | ≥ 130% |

### 3.2 Revenue Model Overview

\<Project Name\> monetizes through five overlapping streams, described fully in Section 23:

1. **Consumer/Prosumer subscriptions** — tiered plans bundling a baseline of CPU/GPU/RAM/storage credits with the Cloud OS experience (analogous to a "computer as a subscription").
2. **Usage-based metering** — for consumption beyond subscription baseline: GPU-seconds, vCPU-seconds, GB-months of storage, egress bandwidth.
3. **IaaS/PaaS consumption** — developers and enterprises paying directly for infrastructure primitives (VMs, containers, functions, managed databases, Kubernetes clusters, object storage) independent of the consumer Cloud OS.
4. **Marketplace take-rate** — a percentage of transactions for third-party applications, game streaming titles, and creative-tool plugins distributed through the platform's App Store/Marketplace.
5. **Enterprise contracts** — annual committed-use agreements, private cluster deployments, dedicated GPU reservations, and compliance-tier add-ons (HIPAA, FedRAMP-equivalent controls).

### 3.3 Why This Business Is Defensible

- **Data-plane lock-in through workflow continuity, not contractual lock-in.** Once a user's projects, workspace snapshots, and application state live in the Cloud OS's continuity model, switching cost is behavioral (the alternative is worse), not merely contractual.
- **Cross-subsidized economics.** Idle GPU capacity provisioned for gaming peak hours (evenings/weekends) can be re-sold as batch AI training or rendering capacity during business hours, improving utilization beyond what a single-purpose gaming cloud or single-purpose AI cloud achieves.
- **Two-sided marketplace dynamics.** As more ISVs (Blender Foundation-style open source projects, Adobe, Autodesk, indie game studios) certify against the platform's App Store, switching cost rises for both users and developers.

---

## 4. Market Opportunity

### 4.1 Total Addressable Market (TAM) Framing

**Assumption A-2:** All TAM figures below are directional, derived from public analyst estimates (Gartner, IDC, Newzoo) as of the most recent published data available to the writing team, and are to be revalidated by the FP&A/strategy team before external use in fundraising materials.

| Segment | Approx. Global TAM (annual) | Relevant Overlap for \<Project Name\> |
|---|---|---|
| Public Cloud IaaS/PaaS | > $300B | GPU/CPU compute, storage, networking primitives |
| DaaS / VDI (Desktop-as-a-Service) | ~$15–20B, high growth | Direct DaaS competitors (Windows 365, Horizon, Citrix) |
| Cloud Gaming | ~$10B, high growth | GeForce NOW, Xbox Cloud Gaming, Luna |
| Creative/Engineering Workstation Software & Hardware | ~$50B+ (software + associated workstation hardware) | Users who currently buy $3–15k workstations |
| Consumer PC Hardware Replacement Cycle | ~$230B/year (all PCs) | Long-term disruption target: reduce need for high-spec local hardware |

### 4.2 Structural Tailwinds

1. **Network improvement curve.** Median fixed broadband speeds and 5G/6G latency continue to improve; last-mile RTT to a metro edge PoP under 10ms is now achievable for a large and growing fraction of target users in Tier 1 metro areas.
2. **GPU virtualization maturity.** NVIDIA MIG, vGPU, and SR-IOV, combined with maturing scheduler ecosystems (Kubernetes device plugins, KubeVirt), make secure multi-tenant GPU sharing operationally tractable at a scale that was not true in 2019–2020.
3. **Codec efficiency.** AV1 and emerging codecs deliver console-quality video at meaningfully lower bitrate than H.264, reducing the bandwidth tax on interactive streaming.
4. **Hybrid work normalization.** Enterprises are already comfortable procuring "compute as a service" for knowledge workers (Windows 365, AVD), lowering the education burden for a more ambitious hybrid-execution model.

### 4.3 Structural Headwinds (Addressed in Section 31 — Risks)

1. Latency-sensitive workloads (competitive gaming, real-time audio production) remain hard-capped by physics — speed of light over fiber sets an irreducible floor (~3.3µs/km one-way in fiber, in practice ~5µs/km with routing overhead), which bounds how close a data center must be to a user for certain workload classes.
2. GPU capacity has been a supply-constrained market during multiple recent cycles; a capacity-heavy business model carries real supply risk.
3. Incumbents (Microsoft, NVIDIA, Google, Amazon) have both capital and distribution advantages and could bundle equivalent offerings into existing products.

---

## 5. Industry Analysis

### 5.1 Category Convergence

\<Project Name\> sits at the intersection of four historically distinct categories that are now converging:

```
            DaaS / VDI                     Cloud Gaming
        (Horizon, AVD,                  (GeForce NOW, Xbox
         Windows 365)                    Cloud Gaming, Luna)
               \\                              /
                \\                            /
                 \\                          /
                  v                        v
              +-----------------------------------+
              |     <Project Name> Cloud OS        |
              |  (unifies execution venue choice)   |
              +-----------------------------------+
                  ^                        ^
                 /                          \
                /                            \
         IaaS / PaaS                    Creative/Engineering
      (AWS, Azure, GCP,                  Workstation Cloud
       Fly.io, Railway)                (Shadow PC, Paperspace,
                                          RunPod, Lambda Labs)
```

No incumbent currently spans all four quadrants with a single identity and a single seamless client. Microsoft is closest structurally (Windows 365 + Xbox Cloud Gaming + Azure), but these remain separate products with separate clients, separate billing, and no automatic workload-placement layer between them.

### 5.2 Category-by-Category Positioning

| Category | Representative Incumbents | Their Core Strength | Their Core Limitation vs. \<Project Name\> |
|---|---|---|---|
| DaaS/VDI | Windows 365, AVD, Horizon, Citrix | Enterprise trust, AD/Entra integration, compliance maturity | Session is monolithic; no per-app hybrid execution; UX is "remote desktop," not native |
| Cloud Gaming | GeForce NOW, Xbox Cloud Gaming, Luna | GPU streaming pipeline maturity, game licensing relationships | Single-purpose; no general compute, no dev/creative story |
| IaaS/PaaS (general) | AWS, Azure, GCP | Breadth, reliability, ecosystem | Not consumer-facing; no unified desktop; steep learning curve |
| IaaS/PaaS (GPU-specialist) | RunPod, Lambda Labs, Paperspace | GPU price/performance, ML-developer focus | Narrow audience (ML engineers); no consumer Cloud OS |
| PC-as-a-Service (niche) | Shadow PC | Closest conceptual analog — full remote PC | Legacy architecture (fixed VM per user, not dynamic hybrid placement); limited GPU tiers historically |

### 5.3 Why Now

The historical failure mode of "cloud PC" products (OnLive's 2012 shutdown being the canonical cautionary tale) was launching before the access-network and GPU-virtualization substrate could support it economically. \<Project Name\>'s architecture explicitly avoids OnLive's mistake of running one dedicated GPU per user session with no fractional sharing — MIG/vGPU-based fractional allocation (Section 20 and Section 25) is central to unit economics viability.

---

## 6. User Personas

### 6.1 Persona Summary Table

| Persona | Profile | Primary Jobs-to-be-Done | Primary Revenue Stream |
|---|---|---|---|
| P1 — "Everyday Ana" | Consumer, low-end laptop, browsing/office/media | Wants a fast, reliable general computer without buying new hardware | Consumer subscription (base tier) |
| P2 — "Creative Caleb" | Freelance 3D artist / video editor | Needs workstation GPU power intermittently, can't justify a $6k workstation | Prosumer subscription + usage-based GPU billing |
| P3 — "Developer Devi" | Software engineer / ML engineer | Wants cloud dev environments, GPU training runs, reproducible infra | IaaS/PaaS consumption, CLI/API-first |
| P4 — "Gamer Gio" | Enthusiast gamer, mid-tier hardware or none | Wants AAA gaming without a $2k GPU purchase | Gaming subscription tier + marketplace |
| P5 — "IT Director Imani" | Enterprise IT/infrastructure leader | Needs fleet-wide managed desktops, compliance, cost control | Enterprise contract, committed-use |
| P6 — "Studio Sam" | Small VFX/architecture/engineering studio owner | Needs burst capacity for renders/simulations beyond in-house workstations | Studio plan + spot/burst GPU billing |
| P7 — "Platform Priya" | ISV / plugin developer | Wants to distribute an app/plugin/game to the platform's install base | Marketplace revenue share |

### 6.2 Persona Deep Dives

**P1 — Everyday Ana.** Ana owns a 2019 laptop with 8GB RAM and integrated graphics. She does email, document editing, video calls, and streams media. Her requirement from \<Project Name\> is that the platform *never introduces friction versus just using her laptop natively* — every millisecond of added latency for a basic task is a defection risk. Architecturally, this persona is why local-first execution for lightweight workloads (Section 11) is non-negotiable: routing her word processor to the cloud "because we can" would be a UX regression, not an improvement.

**P2 — Creative Caleb.** Caleb needs Blender or DaVinci Resolve at full workstation GPU performance for a few hours a week, not 24/7. His economic model only works if he pays close to zero when idle and a fair metered rate when active — this persona is the primary driver of fractional/burst GPU billing (Section 23) and fast cold-start times for creative-tier sessions (target: <10s from launch to usable GPU session, detailed in Section 21/22).

**P3 — Developer Devi.** Devi wants Terraform/Pulumi providers, a CLI, and Kubernetes-compatible APIs (Section 18/19). She does not want a "desktop" at all for most of her workflow — she wants API-level control. The Cloud OS must not be mandatory for this persona; the IaaS layer must be fully usable headless.

**P4 — Gamer Gio.** Gio's tolerance for input latency is the tightest of any persona (competitive titles demand <60–80ms total input-to-photon latency). This persona drives the regional GPU cluster and edge PoP placement strategy (Section 14, Section 21).

**P5 — IT Director Imani.** Imani needs SSO/SAML federation, per-department cost allocation, device compliance posture checks, and audit logging (Section 16, Section 24). She will not adopt a platform that cannot integrate with her existing Entra ID/Okta tenant.

**P6 — Studio Sam.** Sam's studio owns 6 workstations but occasionally needs 40 render nodes for 48 hours before a deadline. Burst capacity with predictable spot pricing and no long-term commitment is the core requirement (Section 19, Section 23).

**P7 — Platform Priya.** Priya needs SDKs, a submission/certification pipeline, and a fair, transparent revenue share (Section 20's Marketplace model). Her adoption is a leading indicator of platform network effects.


## 7. Functional Requirements

Requirements are grouped by subsystem and tagged with an ID for traceability into later architecture sections. Priority: **M** = Must-have for GA, **S** = Should-have (Phase 2), **C** = Could-have (Phase 3+).

### 7.1 Client & Cloud OS

| ID | Requirement | Priority |
|---|---|---|
| FR-C1 | Native client installable on Windows 10/11, macOS 13+, and major Linux distributions (Ubuntu, Fedora, Arch via AUR) with a single installer artifact per OS | M |
| FR-C2 | Client establishes an authenticated, encrypted session to the platform within 3 seconds of launch on a broadband connection | M |
| FR-C3 | Cloud OS desktop provides a window manager, launcher, notification center, clipboard manager, and multi-monitor support indistinguishable in interaction model from a native OS | M |
| FR-C4 | Cloud file explorer presents a unified namespace across local mounted paths and cloud object/file storage | M |
| FR-C5 | Workspace snapshot/restore ("time travel") allows a user to save full desktop + running-application state and restore it later, including on a different device | S |
| FR-C6 | AI assistant embedded in the Cloud OS shell, invocable via hotkey, with access (subject to permission) to running application context | S |
| FR-C7 | Offline/degraded-connectivity mode preserves access to locally-executing applications and a read-only cached view of cloud file storage | S |

### 7.2 Hybrid Execution & Scheduling

| ID | Requirement | Priority |
|---|---|---|
| FR-H1 | Every process/application launch is evaluated by the scheduling engine for placement (local / cloud / split) before execution begins | M |
| FR-H2 | Running workloads can be live-migrated between local and cloud execution venues without terminating the process, where the application's checkpoint/restore contract supports it | M |
| FR-H3 | GPU-bound sessions support state migration (frame buffer, GPU context) between physical GPUs within the same region with sub-second pause | S |
| FR-H4 | Users and administrators can view, and administrators can override/pin, the placement decision for a given application or workload class | M |
| FR-H5 | Placement decisions are explainable — the system can report, on request, why a workload was placed locally vs. remotely | S |

### 7.3 Application & IaaS Platform

| ID | Requirement | Priority |
|---|---|---|
| FR-A1 | Support native app packaging (Windows/macOS/Linux binaries), container apps (OCI images), and web apps (URL-wrapped PWA-style) | M |
| FR-A2 | Provide an App Store/Marketplace with search, categories, ratings, and one-click install | M |
| FR-A3 | Provide CLI, REST API, and GraphQL API covering all IaaS primitives (VMs, containers, functions, storage, networking) | M |
| FR-A4 | Provide Terraform and Pulumi providers for infrastructure-as-code management of platform resources | S |
| FR-A5 | Provide Kubernetes-compatible cluster provisioning (managed control plane, worker autoscaling) | M |
| FR-A6 | Support GitHub/GitLab-integrated CI/CD pipelines that can deploy directly to platform compute | S |

### 7.4 Gaming Platform

| ID | Requirement | Priority |
|---|---|---|
| FR-G1 | Stream PC games from cloud GPU instances at up to 4K/120fps with adaptive bitrate | M |
| FR-G2 | Support physical and virtual controller input with sub-frame input-mapping latency overhead | M |
| FR-G3 | Cloud save synchronization across devices, independent of local storage | M |
| FR-G4 | Anti-cheat compatibility for supported titles (kernel-level anti-cheat running inside the cloud VM, not the client) | S |
| FR-G5 | Voice chat and multiplayer session support with regional server matchmaking | S |

### 7.5 Creative Platform

| ID | Requirement | Priority |
|---|---|---|
| FR-CR1 | Provide pre-configured, certified environments for Blender, Adobe Creative Cloud, Autodesk products, DaVinci Resolve | M |
| FR-CR2 | Support fractional and full GPU allocation tiers with < 15 second cold-start for cached environments | M |
| FR-CR3 | Support GPU-accelerated AI image/video generation workloads with model-serving infrastructure | S |
| FR-CR4 | Support collaborative real-time review sessions (e.g., shared viewport streaming to a second viewer) | C |

### 7.6 Billing, Identity, Multi-Tenancy

| ID | Requirement | Priority |
|---|---|---|
| FR-B1 | Usage-metered billing at sub-hour granularity for compute, storage, and bandwidth | M |
| FR-B2 | Organization/team/project hierarchy with RBAC and quota enforcement | M |
| FR-B3 | SSO via SAML/OIDC federation with enterprise IdPs | M |
| FR-B4 | Self-service subscription management and usage dashboards | M |
| FR-B5 | Enterprise invoicing, committed-use discounts, and cost-center allocation reporting | S |

---

## 8. Non-Functional Requirements

| ID | Category | Requirement | Target |
|---|---|---|---|
| NFR-1 | Latency | End-to-end input-to-photon latency for interactive streaming sessions (gaming/creative) from a well-connected client to nearest regional PoP | ≤ 40ms network RTT contribution; ≤ 80ms total added latency vs. local execution for the 90th percentile session |
| NFR-2 | Availability | Control plane (auth, scheduler, billing API) uptime | 99.95% monthly |
| NFR-3 | Availability | Data plane (execution venues) uptime per region | 99.9% monthly |
| NFR-4 | Durability | Object/block storage durability | ≥ 99.999999999% (11 nines) via erasure coding + cross-AZ replication |
| NFR-5 | Security | All data in transit encrypted (TLS 1.3 / WireGuard); all data at rest encrypted (AES-256 or equivalent) | 100% coverage, no exceptions |
| NFR-6 | Scalability | Control plane horizontally scalable with no single-region single point of failure | Validated via chaos testing per region |
| NFR-7 | Performance | Cold-start time from application launch request to first usable frame, cached environment | ≤ 10s (creative/dev), ≤ 5s (gaming), ≤ 2s (lightweight apps) |
| NFR-8 | Compliance | SOC 2 Type II, ISO 27001 certification achieved | Prior to enterprise GA (Phase 3) |
| NFR-9 | Compliance | GDPR data residency controls (EU data stays in EU regions unless explicitly opted out) | GA requirement for EU market |
| NFR-10 | Observability | Mean time to detect (MTTD) a regional degradation event | ≤ 2 minutes via automated health monitoring |
| NFR-11 | Observability | Mean time to resolve (MTTR) a P1 incident | ≤ 30 minutes, with automated failover reducing user-visible impact to near-zero for stateless workloads |
| NFR-12 | Cost efficiency | GPU utilization across the fleet (busy-time / provisioned-time) | ≥ 65% blended by Phase 3 (vs. typical enterprise on-prem GPU utilization of 15–30%) |
| NFR-13 | Portability | Client footprint (installed size) | ≤ 150MB installer, ≤ 400MB installed |
| NFR-14 | Accessibility | Cloud OS shell meets WCAG 2.1 AA for screen reader and keyboard navigation | GA requirement |


## 9. System Architecture

### 9.1 Layered Overview

\<Project Name\> is architected in six horizontal layers, plus one vertical cross-cutting layer (identity/security) that every horizontal layer depends on.

```
+---------------------------------------------------------------------+
|  LAYER 6 — CLIENT                                                    |
|  Native client (Windows/macOS/Linux) — Cloud OS shell renderer,       |
|  local execution runtime, input capture, codec decode, local file     |
|  cache, WireGuard tunnel endpoint                                      |
+---------------------------------------------------------------------+
|  LAYER 5 — EDGE / GATEWAY                                             |
|  Anycast entrypoints, TLS termination, session negotiation,           |
|  regional routing, CDN, edge functions, DDoS scrubbing                |
+---------------------------------------------------------------------+
|  LAYER 4 — CONTROL PLANE                                               |
|  Identity/IAM, Scheduler, Orchestration API, Billing metering          |
|  ingestion, Policy engine, Marketplace/App catalog service             |
+---------------------------------------------------------------------+
|  LAYER 3 — DATA PLANE / EXECUTION                                      |
|  Kubernetes + KubeVirt clusters, Firecracker/Kata micro-VMs,           |
|  GPU virtualization (MIG/vGPU), session compositors, game/creative     |
|  execution hosts                                                       |
+---------------------------------------------------------------------+
|  LAYER 2 — STORAGE & DATA SERVICES                                     |
|  Distributed object store, block store, managed databases,            |
|  file-sync backend, secrets/KMS                                        |
+---------------------------------------------------------------------+
|  LAYER 1 — PHYSICAL INFRASTRUCTURE                                     |
|  Bare-metal compute (CPU/GPU), regional data centers, private          |
|  backbone network, power/cooling                                       |
+---------------------------------------------------------------------+
       ^                    (cross-cutting, all layers)
       |
+---------------------------------------------------------------------+
|  IDENTITY, SECURITY & OBSERVABILITY (vertical, spans all layers)       |
|  Zero Trust mesh, mTLS everywhere, audit logging, OpenTelemetry,       |
|  policy-as-code (OPA/Kyverno)                                          |
+---------------------------------------------------------------------+
```

### 9.2 End-to-End Request Flow (Illustrative: Launching a Cloud-Placed Application)

```
 [User double-clicks app icon in Cloud OS launcher]
            |
            v
 [Client: local intent event] --------------------------------+
            |                                                  |
            v                                                  |
 [Edge Gateway: authenticates session token, routes to         |
  nearest healthy regional Control Plane]                      |
            |                                                  |
            v                                                  |
 [Control Plane: Scheduler evaluates placement]                |
   - checks app manifest requirements (GPU class, RAM, etc.)   |
   - checks user's current device telemetry                   |
   - checks regional GPU capacity + user's org quota           |
   - checks cost policy / subscription entitlement             |
            |                                                  |
            v                                                  |
 [Decision: CLOUD placement, region us-east-2, GPU class A10-frac] 
            |                                                  |
            v                                                  |
 [Orchestration API: requests a session from Data Plane]       |
   - Kubernetes admits a KubeVirt VM / Kata pod                |
   - vGPU/MIG slice attached                                   |
   - session compositor starts, begins encoding output          |
            |                                                  |
            v                                                  |
 [Data Plane: cached container image / golden snapshot         |
  restored -> app process starts inside isolated session]      |
            |                                                  |
            v                                                  |
 [Edge Gateway: establishes low-latency media/transport         |
  channel (QUIC-based) between session compositor and client]  |
            |                                                  |
            v                                                  |
 [Client: decodes video/audio stream, renders into a native      |
  window inside the Cloud OS window manager; captures local     |
  input and sends back over the same QUIC channel] <------------+
```

### 9.3 Architectural Style Decisions

| Decision | Choice | Rationale | Alternative Considered | Why Rejected |
|---|---|---|---|---|
| Control plane API style | REST (OpenAPI) + GraphQL federation for aggregated queries | REST for simple CRUD/automation clients (Terraform, CLI), GraphQL for the Cloud OS UI which needs flexible, aggregated queries across many resources in one round trip | Pure gRPC-only | Harder for third-party ISV integration; REST/GraphQL has broader tooling and client library maturity for external developers |
| Inter-service communication (control plane internal) | gRPC over mTLS | Low overhead, strong typing, native streaming support for telemetry | REST internally | Unnecessary serialization overhead at internal call volumes |
| Event backbone | NATS (JetStream) for control-plane events; Kafka for high-volume telemetry/billing event streams | NATS is lightweight and well suited to control-plane pub/sub with modest throughput; Kafka's log-based model and ecosystem (Flink/ksqlDB-style consumers) suits billing-grade event durability and replay at very high throughput | Kafka everywhere | Kafka operational overhead is not justified for low-volume control-plane signaling; running one unified bus would either under-serve high-throughput billing or over-provision for lightweight control signals |
| Workflow orchestration (long-running processes: migrations, billing runs, provisioning) | Temporal | Durable execution semantics are a natural fit for multi-step, failure-prone processes like live migration and multi-stage provisioning, with built-in retry/versioning | Custom state machines on top of a database | Reinvents a hard problem (exactly-once step execution across failures) that Temporal already solves robustly |
| Primary transactional datastore | PostgreSQL (with Vitess-sharded topology for billing/usage at scale) | Strong consistency for identity, billing, and org/RBAC data; mature ecosystem; Vitess allows horizontal sharding without a rewrite when a single Postgres primary becomes the bottleneck | CockroachDB / distributed SQL from day one | Added operational complexity not justified until proven scale need; Postgres + Vitess sharding is a well-trodden incremental path (see Section 24) |
| Analytical/telemetry datastore | ClickHouse | Column-oriented storage and vectorized execution are well suited to the very high cardinality, append-heavy telemetry and usage-metering workload | TimescaleDB | ClickHouse's ingestion throughput and compression ratio are better proven at platform scale for this specific access pattern (wide aggregation queries over billions of rows) |


## 10. Cloud OS Architecture

### 10.1 What the Cloud OS Actually Is

The Cloud OS is not a kernel, and \<Project Name\> does not build a new kernel from scratch. It is a **distributed desktop environment**: a shell, compositor, application lifecycle manager, and set of system services that runs partly as native client code and partly as cloud-hosted services, presenting one coherent environment. Underneath, local processes run on the host OS's own kernel (Windows/macOS/Linux), and cloud-hosted processes run inside Linux-based micro-VMs or containers in Ciago data centers. The Cloud OS's job is to make that split invisible.

**Assumption A-3:** We assume the initial Cloud OS shell is built as a native client application (not a browser-hosted web app) for performance and OS-integration reasons (global hotkeys, low-latency compositing, GPU decode access), using a cross-platform native UI toolkit (evaluated: Qt, or a custom Rust/Skia-based renderer — see Section "Technology Recommendations" cross-reference in Section 9 and repeated in the closing technology table).

### 10.2 Component Breakdown

```
+--------------------------------------------------------------------+
|                         CLOUD OS SHELL (client-resident)             |
|                                                                      |
|  +---------------+  +---------------+  +---------------------+     |
|  | Window Manager |  | Launcher /    |  | Notification Center |     |
|  | (compositing,   |  | App Center    |  |                     |     |
|  |  multi-monitor) |  +---------------+  +---------------------+     |
|  +---------------+                                                   |
|  +---------------+  +---------------+  +---------------------+     |
|  | Clipboard       |  | Cloud File    |  | Task/Resource        |     |
|  | Manager         |  | Explorer      |  | Monitor              |     |
|  +---------------+  +---------------+  +---------------------+     |
|  +---------------+  +---------------+  +---------------------+     |
|  | AI Assistant     |  | Terminal      |  | Settings / Identity   |     |
|  | (local agent +   |  | (local shell  |  | Panel                 |     |
|  |  cloud LLM calls)|  |  or cloud SSH)|  |                        |     |
|  +---------------+  +---------------+  +---------------------+     |
+--------------------------------------------------------------------+
                |  session control channel (gRPC/QUIC over mTLS)
                v
+--------------------------------------------------------------------+
|                    CLOUD OS BACKEND SERVICES (control plane)         |
|                                                                      |
|  Session Registry  |  Workspace State Store  |  App Catalog Service |
|  Snapshot Service   |  Sync Coordinator        |  Presence/Notif Bus  |
+--------------------------------------------------------------------+
```

### 10.3 Window Manager & Compositor

Each application window in the Cloud OS is tagged with a **venue attribute**: `local`, `remote`, or `split`. For `local` windows, the client's own compositor renders the application's native surface directly (standard OS windowing). For `remote` windows, the client compositor renders a decoded video/texture stream received from the cloud session compositor, but treats it as a first-class window: it can be resized, snapped, moved across monitors, and alt-tabbed exactly like a local window. Resize events are forwarded to the cloud session compositor which re-renders the source application at the new resolution (with debouncing to avoid resize-storms consuming excess encode bandwidth).

For `split` windows (e.g., an IDE where the editor UI is local but a build/debug backend is remote), the client renders local UI elements directly and remote elements as embedded texture regions within the same window — this is the most architecturally complex rendering mode and is scoped as Phase 2+.

### 10.4 Cloud File Explorer

The file explorer presents a single namespace merging:
- Local filesystem paths the user has chosen to expose (e.g., `~/Documents`)
- Cloud object storage buckets mounted as a virtual filesystem (via a FUSE-like driver on Linux/macOS and a Cloud Files/Projected File System provider on Windows, modeled after OneDrive/Dropbox's on-demand file materialization pattern)
- Session-scoped ephemeral storage attached to currently running cloud sessions (e.g., scratch disks for an active Blender render)

Files show a materialization state indicator (fully local / cloud-only placeholder / syncing) and support on-demand download. This mirrors, and is directly inspired by, the "cloud files" APIs already proven at scale by OneDrive and Dropbox, extended to also cover block-level session-scratch storage.

### 10.5 Workspace Snapshots & "Time Travel"

A workspace snapshot captures: (a) the set of open applications and their venue assignments, (b) for cloud-resident applications, a checkpoint of their process/VM state (Section 11.4), (c) window layout and monitor topology, and (d) references (not copies) to open files. Snapshots are stored as versioned metadata plus content-addressed checkpoint blobs in object storage. "Time travel" is the user-facing feature of browsing and restoring historical snapshots — implemented as an application of the same checkpoint/versioning primitives used for live migration and fault recovery (Section 11.4), not a separate subsystem, minimizing duplicated engineering effort.

### 10.6 AI Assistant Integration in the Shell

The AI assistant is invoked via global hotkey and has three operating modes: (1) **Ambient Q&A** — general questions, no application context; (2) **Contextual** — with explicit per-application user permission, the assistant can read the foreground application's accessible state (e.g., "summarize this document," "explain this error in my terminal") via an accessibility-API-style bridge, never raw memory access; (3) **Agentic** — the assistant can, with confirmation, take actions on the user's behalf (installing an app, resizing a GPU allocation, running a CLI command). All agentic actions are logged to the audit trail described in Section 16.


## 11. Hybrid Execution Engine

This is the single most technically demanding subsystem in the platform, and the one most directly responsible for the product's differentiated feel. This section covers dynamic migration, live migration, checkpointing, memory synchronization, GPU state migration, file synchronization, session continuity, and the distinct migration strategies required for applications, containers, and VMs.

### 11.1 Why Migration Is Hard: A Taxonomy of Workload State

Not all "state" is equal in migration difficulty. We classify workloads into four tiers:

| Tier | Description | Example | Migration Strategy |
|---|---|---|---|
| T0 — Stateless / restartable | No meaningful in-memory state that must survive; restart is invisible or near-invisible to the user | Calculator, PDF viewer, static web app | Kill-and-relaunch at new venue; no checkpoint needed |
| T1 — Session-stateful, checkpoint-friendly | Meaningful state, but the application (or a wrapper) supports serializing and restoring state cleanly | Text editor with unsaved buffer, most productivity apps | Application-level checkpoint API (save-state hook) + relaunch with restored state |
| T2 — Process-stateful, OS-checkpoint-required | Large, complex in-memory state with no clean application-level save/restore hook | Blender scene mid-edit, a running Docker build, a compiler mid-compilation | OS/VM-level checkpoint (CRIU-style process checkpoint, or full micro-VM snapshot) |
| T3 — GPU-resident, hardware-state-required | State lives substantially in GPU memory/context, not just CPU RAM | Active game session, in-progress GPU render, ML training step | GPU context checkpoint via vendor APIs (e.g., CUDA checkpoint/restore primitives) combined with VM-level snapshot |

### 11.2 Migration Trigger Conditions

The scheduling engine (Section 12) can trigger migration for any of the following reasons:

1. **Resource pressure** — local device is thermal-throttling, on battery below a threshold, or CPU/RAM contention crosses a policy threshold.
2. **Workload escalation** — a locally-running application requests a resource class the local device cannot provide (e.g., a plugin invokes GPU-accelerated rendering beyond local GPU capability).
3. **Cost optimization** — the AI cost optimizer (Section 17) determines that continuing cloud execution in the current region/GPU class is more expensive than an available alternative (e.g., spot capacity freed up in a cheaper region).
4. **Network degradation** — for cloud-resident sessions, if the current region's latency/jitter crosses a threshold, the platform may migrate the session to a different, better-connected region.
5. **Explicit user action** — user manually requests "move to cloud" / "move to my device" via the Task/Resource Monitor.
6. **Maintenance/fault** — underlying host requires draining for patching, or a hardware fault is detected (Section 25).

### 11.3 Live Migration Workflow (Cloud-to-Cloud, VM-Level)

```
 STEP 1: Pre-copy phase
   Source host begins iterative memory-page copying to destination host
   while VM continues running on source (dirty-page tracking via
   hardware-assisted dirty bitmaps).
        |
        v
 STEP 2: Convergence check
   Scheduler monitors dirty-page rate. If dirty rate stays below a
   threshold relative to copy bandwidth, convergence is reachable;
   if not (e.g., a memory-thrashing workload), fall back to a
   brief-pause "stop-and-copy" strategy instead.
        |
        v
 STEP 3: GPU context migration (if T3 workload)
   GPU driver-level checkpoint of the CUDA/compute context is taken;
   for the small class of workloads where live GPU migration is not
   yet supported by vendor primitives, this step forces a brief
   pause (typically under 500ms for small contexts, more for large
   ML training state -- see 11.3.1 caveat below).
        |
        v
 STEP 4: Final sync + cutover
   Remaining dirty pages copied, VM paused for a final delta
   (target: <100ms for T0-T2 workloads on same-region migration),
   network session (QUIC connection ID) is migrated to the new
   host transparently -- QUIC's connection-ID-based design means
   the client does not need to re-handshake.
        |
        v
 STEP 5: Resume + verify
   VM resumes on destination host, health checks confirm
   application responsiveness, source host resources released
   after a grace period (rollback window, see 11.6).
```

**11.3.1 Caveat on GPU Live Migration.** As of the writing of this document, no GPU vendor offers a fully general, production-grade "live" (zero-pause) migration primitive for arbitrary compute contexts comparable to CPU/hypervisor live migration — vendor checkpoint/restore APIs (e.g., CUDA's checkpoint/restore support) provide *pause-and-resume* semantics with pause durations that scale with GPU memory footprint. **Assumption A-4:** For planning purposes we assume typical pause durations of 200ms–2s for GPU contexts under 8GB, scaling upward for larger contexts, and we architect the user experience (loading transitions, brief "optimizing your session" indicators) to mask this rather than promise literal zero-perceived-interruption for T3 workloads. This is disclosed explicitly rather than glossed over, because it is a real physics/vendor-API constraint, not an engineering shortcut we intend to eliminate.

### 11.4 Checkpointing Architecture

| Layer | Mechanism | Used For |
|---|---|---|
| Application-level | Cooperative save/restore hooks exposed via the platform SDK; apps that integrate get faster, cleaner checkpoints | T1 workloads, first-party and certified ISV apps |
| Process-level (Linux) | CRIU (Checkpoint/Restore In Userspace) for container/process checkpointing | T2 workloads running in containers/Kata pods |
| VM-level | Firecracker/Cloud Hypervisor snapshot-and-restore (full guest memory + device state serialization) | T2/T3 workloads running in micro-VMs, and all cross-host live migration |
| GPU-level | Vendor checkpoint/restore APIs, combined with our own GPU memory delta-diffing to reduce transferred state size | T3 workloads |

Checkpoint blobs are content-addressed and stored with a layered/delta model (similar in spirit to container image layers): a full baseline snapshot plus incremental deltas, so that frequent auto-checkpointing (for fault tolerance) does not require re-transmitting entire memory images each time.

### 11.5 Memory Synchronization for "Split" Execution

For workloads that genuinely split (e.g., local UI thread + cloud compute thread within one logical application), the platform does not attempt to present a single coherent shared-memory space across local and cloud (see Section on Local + Cloud Memory, Section for why this is fundamentally hard). Instead, split execution uses an explicit **message-passing boundary**: the application (or an SDK-provided shim) marshals only the specific data structures that cross the boundary, over a low-latency RPC channel, rather than any attempt at transparent distributed shared memory. This is a deliberate architectural constraint, not a limitation we intend to lift — see Section 11's companion discussion in the dedicated memory section below.

### 11.6 Rollback & Fault Recovery

Every migration retains the source-side resources in a **quarantined-but-not-released** state for a configurable grace period (default 30 seconds for VM-level, 5 minutes for full session snapshots) after cutover. If post-migration health checks fail (application crash-loops, GPU context corruption detected, network path black-holes), the orchestrator can roll back to the source, or in the case of source-side failure, promote the most recent successful checkpoint on any available host. This grace-period-based rollback model favors availability over resource efficiency during the migration window, which is judged an acceptable tradeoff given migrations are a small fraction of total session-time resource consumption.

### 11.7 Container, VM, and Application Migration — Differentiated Handling

| Workload Type | Migration Primitive | Special Considerations |
|---|---|---|
| Native application (T0/T1) in a micro-VM | VM snapshot (Firecracker) | Fast (sub-second) for small memory footprints; primary path for most Cloud OS "apps" |
| Container (e.g., a dev/build container) | CRIU-based container checkpoint, OR treat container as ephemeral and rely on declarative re-creation (rebuild from image + mounted volumes) when the workload tolerates a cold restart | Many CI/build workloads are *better* served by kill-and-recreate than checkpoint, since build state is often reproducible from cache layers — the scheduler defaults to the cheaper strategy when the workload's manifest declares it as "restart-safe" |
| Full VM (e.g., a user-provisioned IaaS VM, Section 19) | Standard hypervisor live migration (KubeVirt/QEMU-based, well-precedented from OpenStack/oVirt-style live migration) | This is the most "solved" case; the platform reuses mature KVM live-migration mechanics rather than inventing new ones |
| Kubernetes workload (user's own cluster on the IaaS layer) | Not migrated transparently by the platform — Kubernetes' own rescheduling (pod eviction + re-admission elsewhere) is the migration mechanism, exposed to the user as standard k8s behavior | We do not attempt to out-clever Kubernetes' own scheduler for user-owned clusters; the Hybrid Execution Engine's transparent migration applies to platform-managed Cloud OS sessions, not to user-managed k8s workloads, which follow standard cloud-native operational patterns instead |


### 11.8 Deep Dive: Why "Cloud RAM" Cannot Simply Extend Local RAM

A recurring question from both engineers and stakeholders is: "why not just let the local machine use cloud RAM as extended memory, the way it uses cloud storage as extended disk?" This subsection addresses that directly, because it is a foundational constraint that shapes the entire hybrid execution model.

**11.8.1 The Latency Gap.** Local DRAM access latency is on the order of 60–120 **nanoseconds** (CAS latency plus memory controller overhead, roughly 10²–10³ CPU cycles). Even a best-case data-center-to-data-center RDMA round trip within the same building is on the order of 1–5 **microseconds** — already 10–80x slower. A round trip from a user's home network to a regional data center, even over an excellent connection with a nearby PoP, is realistically 5–20 **milliseconds** — a further 1,000–20,000x slower than that. CPUs issue memory loads/stores at a rate and with a stall tolerance calibrated for nanosecond-scale latency; a single millisecond-scale stall on a naive "remote memory" access would stall a modern CPU core for literally millions of cycles, which is catastrophic for any workload with non-trivial memory access patterns (i.e., almost all real workloads).

| Memory Tier | Typical Latency | Relative to Local DRAM |
|---|---|---|
| L1 Cache | ~1ns | 0.01x |
| L2 Cache | ~3–10ns | 0.1x |
| Local DRAM | ~60–120ns | 1x (baseline) |
| CXL-attached memory (same server/rack) | ~150–400ns | ~2–4x |
| RDMA over same-datacenter fabric | ~1–5µs | ~10–50x |
| RDMA cross-datacenter (same metro) | ~50–200µs | ~500–2000x |
| WAN round trip, home-to-regional-DC | ~5–30ms | ~50,000–300,000x |

**11.8.2 Cache Coherency and NUMA as Cautionary Precedent.** Even *within* a single physical machine, multi-socket NUMA architectures already demonstrate how sensitive real workloads are to memory locality: a memory access to a "remote" NUMA node's DRAM (still within the same server chassis, still nanosecond-scale, just attached to a different socket) can be 30–100% slower than a local-node access, and this is well-documented as a serious performance concern requiring explicit NUMA-aware scheduling. If cross-socket-within-one-server latency differences already meaningfully hurt performance, cross-continent latency differences (a million-fold larger gap) are not an engineering inconvenience to optimize away — they are a different regime entirely. Cache coherency protocols (MESI and its variants) rely on the assumption that invalidation/snoop round trips are cheap enough to happen on nearly every contested access; this assumption categorically breaks down at WAN distances, which is why no serious systems architecture proposes maintaining hardware cache coherency across a WAN link.

**11.8.3 What We Do Instead: Paging and Swap as a Model, Not RDMA-as-RAM.** Rather than attempting transparent remote memory, \<Project Name\> treats "cloud-assisted memory" the way an OS treats swap/paging — as a strictly slower fallback tier, used deliberately and sparingly, not as an unnoticed extension of RAM:

- When a local device's RAM is under pressure, the platform can migrate the *entire process* to a cloud venue with ample RAM (Section 11.3) rather than attempting to page individual memory regions over the network — moving the computation to the memory, rather than the memory to the computation, which is the architecturally sound direction for this latency gap.
- For specific, narrow cases where an application's working set legitimately spans local and cloud (e.g., a local UI process referencing a large cloud-resident dataset), we use explicit, application-aware data movement (prefetching, caching, and the message-passing boundary described in 11.5) rather than any attempt at page-fault-driven transparent remote paging.

**11.8.4 Emerging Technology That Narrows, But Does Not Close, the Gap.** Compute Express Link (CXL), particularly CXL 2.0/3.x pooled-memory and memory-expansion topologies, allows disaggregated memory *within a rack or a small number of adjacent racks* at latencies (per the table above) only 2–4x worse than local DRAM — this is a genuinely usable tier for **cloud-side** memory pooling (letting Ciago's own data center infrastructure share memory more efficiently across cloud-hosted VMs), and we do plan to adopt CXL-based memory pooling in cloud data-center design (Section 29, Future Innovations) to improve GPU/CPU memory elasticity for cloud-resident workloads. This is architecturally distinct from, and does not solve, the client-to-cloud WAN latency gap — CXL requires physical rack-scale proximity and dedicated fabric; it is not a wide-area technology. **Assumption A-5:** We assume no wide-area technology plausibly closes the millisecond-scale WAN gap to anything resembling DRAM latency within this document's planning horizon (5–7 years), and the architecture is designed around that assumption rather than betting the product on its obsolescence.


## 12. Scheduling Engine

### 12.1 Role and Position in the Architecture

The scheduling engine is the decision-making core that answers, continuously, "where should this workload execute right now?" It sits logically in the control plane (Layer 4, Section 9.1) but maintains a lightweight local agent on the client for low-latency telemetry collection and for making fast local decisions (e.g., "don't migrate — the resource pressure was a 2-second transient") without a round trip to the control plane for every signal.

### 12.2 Inputs to the Scheduler

The scheduler is a multi-signal decision system. Signals are grouped into five categories:

| Category | Signals | Source |
|---|---|---|
| Device telemetry | CPU usage, GPU usage, RAM pressure, battery %, thermal state, power mode (plugged/battery saver), storage I/O latency | Local client agent |
| Network telemetry | RTT to nearest regional PoP, jitter, packet loss, available bandwidth (measured, not just advertised) | Local client agent + edge gateway measurements |
| Workload requirements | Declared resource class from app manifest (min/preferred CPU, GPU tier, RAM, storage IOPS), observed runtime resource consumption | App Catalog Service + runtime profiling |
| Platform state | Regional GPU/CPU capacity and headroom, spot capacity availability, current incident/degradation status per region | Control plane capacity service |
| Policy & economics | User/org subscription entitlements, quota consumption to date, org-level cost policies, security policy constraints (e.g., "this workload must stay in-region for compliance") | Billing service, Policy engine (OPA) |

### 12.3 Decision Model

We use a **layered decision model**, not a single monolithic ML model, for both explainability (FR-H5) and operational safety — a pure black-box scheduler that occasionally makes an inexplicable, expensive, or non-compliant placement decision is an unacceptable risk for an infrastructure product.

```
LAYER 1 — Hard constraints (deterministic, policy-engine evaluated)
  - Security/compliance placement constraints (data residency, org policy)
  - Subscription entitlement gates (e.g., free tier cannot request top-tier GPU)
  - Capacity hard-floors (never place onto a region reporting critical health)
  --> Produces a filtered SET of admissible (venue, region, resource-class) options

LAYER 2 — Deterministic scoring (rule-based, fast, always available as fallback)
  - Score each admissible option on: estimated latency, estimated cost,
    estimated cold-start time, current load
  - Weighted sum with organization-configurable weights (a cost-sensitive
    org can weight cost higher; a latency-sensitive gaming session
    weights latency near-exclusively)
  --> Produces a ranked shortlist

LAYER 3 — AI prediction refinement (ML-based, advisory, can be disabled)
  - Historical-usage and pattern-based prediction model adjusts the
    Layer 2 ranking using signals like "this user typically escalates
    this app to full-GPU within 90 seconds of launch, pre-warm accordingly"
    or "this workload's dirty-page rate historically makes live migration
    fail to converge, prefer stop-and-copy proactively"
  --> Produces the FINAL decision, always traceable back to a Layer 2
      baseline so a Layer 3 anomaly cannot produce an inexplicable choice
```

This layered design means the AI layer can degrade gracefully to the deterministic Layer 2 ranking if the ML service is unavailable or produces a low-confidence prediction — the scheduler always has a safe, explainable fallback and never blocks on an ML inference call for latency-critical decisions.

### 12.4 Scheduling Latency Budget

| Decision Type | Target Latency | Notes |
|---|---|---|
| Initial placement (app launch) | ≤ 150ms (control-plane round trip) | Must not be perceptible as "loading" beyond the app's own startup time |
| Migration trigger evaluation | Continuous, evaluated every 2–5s per active session (adaptive interval based on volatility of signals) | Local agent pre-filters obvious non-events to avoid control-plane chatter |
| Migration execution decision-to-cutover | Varies by tier (T0: <1s, T1: 1–3s, T2: 2–10s, T3: 2–30s depending on GPU memory footprint) | See Section 11.3 |

### 12.5 Worked Example: Placement Decision Trace

To satisfy FR-H5 (explainability), every placement decision produces a structured trace record. Example (illustrative):

```json
{
  "decision_id": "plc_8f2a...",
  "app": "blender-3d-workstation",
  "layer1_admissible_options": ["cloud:us-east-2:gpu-a10-frac", "cloud:us-east-2:gpu-l40-full", "cloud:us-west-2:gpu-a10-frac"],
  "layer1_excluded": [{"option": "local", "reason": "manifest requires GPU class above local device capability (RTX-equivalent tier 3, device has integrated graphics)"}],
  "layer2_scores": {"cloud:us-east-2:gpu-a10-frac": 0.81, "cloud:us-east-2:gpu-l40-full": 0.74, "cloud:us-west-2:gpu-a10-frac": 0.52},
  "layer3_adjustment": {"selected": "cloud:us-east-2:gpu-a10-frac", "confidence": 0.93, "reasoning_tag": "historical_usage_match"},
  "final_decision": "cloud:us-east-2:gpu-a10-frac",
  "estimated_cost_per_hour_usd": 0.74,
  "estimated_cold_start_ms": 4200
}
```

### 12.6 Alternatives Considered for the Scheduler Architecture

| Option | Description | Why Not Chosen as Primary |
|---|---|---|
| Pure Kubernetes scheduler extension (scheduler-framework plugins) | Implement placement logic entirely as k8s scheduler plugins | K8s scheduling model assumes workloads are already containerized/pod-shaped; our scheduler must make decisions *before* that (including "should this even be containerized at all, or run natively in a micro-VM, or stay local") — k8s scheduling becomes a downstream execution detail once a cloud placement is chosen, not the top-level decision engine |
| Pure reinforcement-learning scheduler | End-to-end learned policy with no explicit rule layers | Rejected as sole mechanism due to explainability and safety requirements (FR-H5, NFR compliance) — retained only as the Layer 3 advisory refinement |
| Static, manifest-declared placement only (no dynamic scheduler) | Every app simply declares "local" or "cloud" at build time | Fails the core product vision (Section 2) — cannot respond to real-time device/network conditions, defeats the "invisible infrastructure" principle |

## 13. Cloud Infrastructure

### 13.1 Regional Topology Model

\<Project Name\> deploys in a three-tier physical topology:

1. **Core regions** — full-capability data centers (control plane, all storage tiers, full GPU catalog including top-tier training-class GPUs). Target: 6–10 core regions at GA, chosen for population density coverage and power/land economics (e.g., US East, US West, EU West, EU Central, UK, Southeast Asia, Japan/Korea, Australia).
2. **Edge PoPs (Points of Presence)** — latency-optimized, smaller-footprint sites providing gateway/CDN termination and a curated subset of GPU capacity for latency-critical gaming/creative sessions, positioned in additional metro areas beyond the core regions.
3. **Partner/colo capacity** — for markets where building owned data centers is not yet justified by demand, capacity is leased from colocation and wholesale providers, using the same control-plane abstractions so the distinction is invisible to the scheduler beyond a "cost and capacity" input.

### 13.2 Compute Fleet Composition

| Fleet Class | Hardware Profile | Primary Use |
|---|---|---|
| General CPU fleet | Commodity dense-core x86 (AMD EPYC / Intel Xeon Scalable class) | Control plane services, lightweight T0/T1 app hosting, general IaaS VMs/containers |
| GPU-fractional fleet | NVIDIA data-center GPUs (Ampere/Ada/Blackwell-class, exact SKUs per Assumption A-1) with MIG/vGPU partitioning | Creative workstation sessions, dev/ML inference, gaming (mid-tier) |
| GPU-full fleet | Dedicated, unpartitioned top-tier GPUs | AAA gaming at highest settings, ML training, high-end rendering |
| Storage-dense fleet | High-capacity NVMe/HDD hybrid nodes | Object/block storage backend (Section 15) |
| Edge fleet | Smaller CPU + fractional GPU footprint, optimized for density and low idle power | Edge PoP gateway, CDN cache, latency-sensitive session hosting |

### 13.3 Physical-to-Logical Mapping

```
 Physical rack
   |-- Bare-metal host (CPU: EPYC 9xx4, GPU: N x data-center GPU)
         |-- Host OS: minimal Linux (hardened, immutable image)
               |-- Kubernetes node (kubelet)
                     |-- KubeVirt VMs (Cloud OS sessions, IaaS user VMs)
                     |     |-- Firecracker/Cloud Hypervisor microVM
                     |           |-- Guest: session compositor + app, or user's VM OS
                     |-- Kata Containers pods (lighter-weight isolated containers)
                     |-- MIG/vGPU slice assignment (per-VM or per-pod GPU fraction)
```


## 14. Networking

### 14.1 Objectives

Networking design must simultaneously serve three very different traffic profiles: (a) bursty, latency-critical, high-bandwidth interactive streaming (gaming/creative sessions), (b) bulk data transfer (file sync, storage, backups), and (c) low-latency control-plane API traffic. A single flat network design would force an unacceptable compromise between these, so the network is explicitly tiered.

### 14.2 Global Edge Network

```
        [User Device]
              |
       (ISP / Access Network)
              |
              v
    +-------------------+        Anycast IP -- routes to
    |  Nearest Edge PoP  |  <---  topologically/latency-nearest
    +-------------------+        healthy PoP via BGP anycast
              |
     (Ciago Private Backbone -- owned/leased dark fiber +
      wavelength services between core regions and PoPs)
              |
              v
    +-------------------+
    |  Core Region DC     |
    +-------------------+
```

- **Anycast + BGP**: All gateway entrypoints are announced via anycast from every PoP, so a user's connection is routed to the topologically nearest healthy PoP without client-side region selection logic.
- **Private backbone**: Once traffic enters Ciago's network at a PoP, it travels over owned/leased backbone capacity rather than the public internet for the hop to the core region, avoiding public-internet congestion and peering unpredictability for the highest-value traffic (interactive session streams).
- **CDN**: Static assets (client installer, app store assets, cached game/app images, cached creative-tool binaries) are served from PoP-local CDN cache, with standard cache invalidation via a control-plane-driven purge API.

### 14.3 Transport Protocol Choices

| Traffic Type | Protocol | Rationale |
|---|---|---|
| Interactive session streaming (video/audio/input) | Custom protocol over QUIC (HTTP/3 transport, non-HTTP framing above it) | QUIC's 0-RTT/1-RTT connection establishment, connection migration (survives client IP changes — e.g., WiFi-to-cellular handoff — without session drop), and per-stream loss recovery (avoiding head-of-line blocking across independent streams like video vs. input) are all directly valuable for this traffic class |
| Control-plane API | HTTP/2 (REST/GraphQL), gRPC internally | Mature, well-supported by client libraries and API tooling |
| Site-to-site / backbone | Standard IP with MPLS/segment-routing traffic engineering where backbone is owned infrastructure | Standard WAN practice, no need for novel approach |
| Client VPN / secure tunnel for enterprise/zero-trust access | WireGuard | Minimal attack surface, high performance, simple enough to audit, now broadly proven in production (used as the substrate for Cloudflare WARP and Tailscale, among others) |

### 14.4 Traffic Engineering & Load Balancing

- **L4 anycast load balancing** at the PoP edge for initial connection admission.
- **L7 session-aware load balancing** at the regional gateway layer, aware of which sessions are latency-sensitive (pinned to lowest-RTT healthy backend) versus latency-tolerant (can be load-balanced more freely for bin-packing efficiency).
- **Regional failover**: if a core region degrades (Section 25), the gateway layer redirects new session admission to the next-best region per the scheduler's Layer 1/2 evaluation (Section 12.3), while existing sessions attempt live migration (Section 11.3) rather than hard disconnection where feasible.

### 14.5 Zero Trust Network Model

No implicit trust is granted based on network location (including "inside our own data center"). Every service-to-service call is authenticated and encrypted via mutual TLS with short-lived certificates issued by an internal CA (cross-reference Section 16.3), and every client-to-platform call is authenticated via session tokens validated on every hop, not just at the perimeter. This is standard modern zero-trust practice (comparable in spirit to Google's BeyondCorp model and to service-mesh-enforced mTLS patterns) applied consistently rather than only at the network perimeter.

## 15. Storage

### 15.1 Storage Tiers

| Tier | Purpose | Backing Technology | Consistency Model |
|---|---|---|---|
| Object storage | User files, app images, marketplace assets, checkpoint blobs, backups | Custom S3-compatible service built on an erasure-coded distributed object layer (evaluated: Ceph RGW vs. MinIO vs. custom — see decision below) | Strong read-after-write for a given object key; eventual consistency for bucket-listing operations at very large scale (standard object-store tradeoff, matching S3's own historical model) |
| Block storage | VM boot/data disks, session scratch disks, database storage volumes | Distributed block layer with synchronous replication within an availability zone, asynchronous cross-AZ | Strong consistency within a volume (single-writer semantics, standard for block devices) |
| Managed databases | Platform's own control-plane data (Postgres/Vitess), and user-provisioned managed DB offerings on the IaaS layer | PostgreSQL (primary/replica + Vitess sharding at scale), with additional managed engine options (MySQL-compatible, Redis/Valkey) offered to IaaS customers | ACID within a shard; standard distributed-SQL tradeoffs across shards |
| Cache/ephemeral | Session state cache, hot-path lookups | Redis/Valkey clusters | Best-effort, not durable by design |

### 15.2 Object Storage Design Decision

**Decision: Build on Ceph (RGW) for the initial GA, evaluate a fully custom object layer only if Ceph's operational ceiling becomes a genuine bottleneck at multi-exabyte scale.**

| Option | Pros | Cons |
|---|---|---|
| Ceph (RGW) | Mature, battle-tested at very large scale, S3-API compatible, active community, supports erasure coding and multi-site replication natively | Operational complexity is non-trivial; performance tuning requires real expertise |
| MinIO | Simpler operational model, good S3 compatibility | Historically stronger for single-cluster deployments; multi-region/multi-site replication and erasure-coding flexibility at Ciago's target scale favor Ceph's more mature multi-site tooling |
| Fully custom object store | Maximum control, could be tuned exactly to our access patterns | Multi-year engineering investment to reach the durability/availability maturity Ceph already has; not justified until Ceph is proven insufficient |

### 15.3 File Synchronization Architecture

File sync (bi-directional, cloud <-> Windows/macOS/Linux) is a distinct subsystem from raw object storage — it must handle partial files, conflict detection, and offline operation, which raw object storage APIs do not provide out of the box.

```
 [Local filesystem watcher] --detects change--> [Local sync agent]
                                                        |
                                              computes content hash,
                                              chunks file (content-defined
                                              chunking, similar in spirit
                                              to rsync's rolling-checksum
                                              approach), deduplicates
                                              against known chunks
                                                        |
                                                        v
                                          [Delta upload to Sync Coordinator]
                                                        |
                                     Sync Coordinator resolves against
                                     server-side version vector; if no
                                     conflicting concurrent edit, commits
                                     new version to object storage and
                                     fans out change notification to all
                                     other devices/sessions
                                                        |
                                                        v
                                      [Other devices' sync agents receive
                                       delta, apply to local cache, or
                                       mark cloud-only placeholder as stale]
```

- **Delta sync**: only changed chunks are transferred, not entire files, using content-defined chunking so that small edits to large files (e.g., a project file) do not require full re-upload.
- **Compression**: chunk-level compression (zstd) applied before transfer.
- **Deduplication**: content-addressed chunk storage means identical chunks across different files/users are stored once (subject to per-tenant encryption boundaries — deduplication never crosses encryption-key boundaries between tenants, to avoid any cross-tenant information leakage via storage side channels).
- **Conflict detection**: version-vector-based (each device tracks the last-known server version per file); a true concurrent conflicting edit produces a conflict copy (same UX pattern as Dropbox/OneDrive's "conflicted copy" file, a well-understood and acceptable model for end users) rather than silent data loss.
- **Offline mode**: local sync agent queues changes durably (local WAL) when disconnected, replays on reconnect, and the Cloud OS file explorer indicates offline/stale status for cloud-only files that cannot currently be materialized.

### 15.4 Data Lifecycle, Versioning, Encryption

- **Versioning**: object storage retains prior versions per configurable policy (default: 30 days of version history for user files, longer for compliance-tier enterprise accounts).
- **Lifecycle policies**: automatic tiering of infrequently accessed data to a cheaper cold tier (higher latency, lower cost per GB), configurable per bucket/project.
- **Encryption**: all data encrypted at rest using per-tenant envelope encryption (data encryption keys wrapped by tenant-specific keys held in the KMS, Section 16.4); encryption in transit via TLS 1.3 for all API access and WireGuard/QUIC-native encryption for session/sync traffic.
- **Cross-region replication**: configurable per bucket — default single-region for cost efficiency, opt-in cross-region for disaster-recovery-conscious customers (Section 25), mandatory cross-region for the platform's own control-plane data.


## 16. Security

### 16.1 Security Model Summary

Security is designed around four pillars: **Zero Trust networking** (Section 14.5), **strong workload isolation** (micro-VM/Kata boundaries between every tenant session, never shared-kernel container isolation alone for untrusted multi-tenant workloads), **comprehensive identity and access control**, and **verifiable trust from hardware boot through to running workload** (attestation).

### 16.2 Identity & Access Management

```
 [Enterprise IdP (Entra ID / Okta / generic SAML or OIDC IdP)]
              |
              | SAML 2.0 / OIDC federation
              v
 +----------------------------------------------------+
 |            Ciago Identity Service                    |
 |  - Federated SSO broker                              |
 |  - Native identity (email/password + passkey/MFA)    |
 |    for accounts not federated to an enterprise IdP   |
 |  - Session token issuance (short-lived JWT + refresh) |
 |  - Device posture check integration (optional,        |
 |    enterprise tier: verifies device compliance         |
 |    before granting session)                            |
 +----------------------------------------------------+
              |
              v
 [Control Plane services validate tokens on every request;
  RBAC/policy engine (OPA) evaluates org/team/project-scoped
  permissions per request]
```

- **Authentication methods supported**: passkeys (WebAuthn/FIDO2) as the recommended primary method, password + TOTP/authenticator MFA as fallback, biometric unlock on supported client platforms (delegating to OS-native biometric APIs — Windows Hello, macOS Touch ID/Face ID — rather than handling raw biometric data ourselves, which keeps biometric templates entirely on-device and out of Ciago's trust boundary).
- **SSO/Federation**: SAML 2.0 and OIDC support for enterprise IdP federation; OAuth 2.0 (authorization code + PKCE) for third-party app/marketplace integrations.

### 16.3 Workload Isolation

| Isolation Mechanism | Used For | Isolation Strength |
|---|---|---|
| Firecracker/Cloud Hypervisor micro-VMs | Default isolation boundary for all multi-tenant Cloud OS sessions and IaaS VMs | Strongest practical isolation short of dedicated bare metal; hardware-virtualization-backed, minimal device model attack surface (this is the same isolation technology AWS Lambda/Fargate rely on) |
| Kata Containers | Container-API-compatible workloads (e.g., a user's Docker build) that want VM-grade isolation with container-like UX | VM-grade isolation, OCI-compatible |
| gVisor | Lower-trust, high-density workloads where full micro-VM overhead is not justified (e.g., some edge/CDN functions) | Strong syscall-interception-based isolation, lighter weight than a full VM, more overhead than a raw container |
| Standard Linux containers (namespaces/cgroups only) | Never used as the sole isolation boundary for untrusted multi-tenant workloads on this platform | N/A — explicitly avoided as a primary tenant boundary given shared-kernel attack surface; may be used only for the platform's own trusted first-party services |

### 16.4 Encryption, Key Management, and Hardware Root of Trust

- **KMS**: A dedicated Key Management Service manages per-tenant envelope encryption keys; root keys are held in HSMs (Hardware Security Modules), never in software-only key stores, for the top of the key hierarchy.
- **Secrets management**: user/developer secrets (API keys, database credentials for IaaS deployments) managed via OpenBao (the open-source Vault-derived secrets engine), providing dynamic secrets, leasing, and audit logging.
- **Secure Boot & TPM**: physical hosts boot via UEFI Secure Boot with TPM-backed measured boot; the measured boot chain feeds into remote attestation (below).
- **Remote attestation**: before a host is admitted into the scheduling pool for sensitive workloads (e.g., confidential-computing-tier customers), it must present a valid attestation quote proving its boot chain and running hypervisor/kernel match an expected, signed-good configuration.
- **Confidential computing**: for customers requiring it (a Phase 3+ enterprise tier offering), workloads can run inside hardware-based trusted execution environments (e.g., AMD SEV-SNP or Intel TDX-class technology) where even Ciago's own hypervisor cannot inspect guest memory contents — offered as a premium, opt-in tier given the performance overhead and hardware-generation constraints involved.

### 16.5 Compliance Program

| Framework | Applicability | Target Timing |
|---|---|---|
| SOC 2 Type II | All customers, baseline trust signal for enterprise sales | Prior to enterprise GA (Phase 3) |
| ISO 27001 | International enterprise/public-sector customers | Phase 3 |
| GDPR | EU users/data | GA requirement for EU market entry (data residency controls, Section 15.4, and data subject rights tooling — export/delete APIs) |
| HIPAA | Healthcare/medical-imaging creative-platform customers (Section 22) | Phase 4, offered as a dedicated compliance-tier add-on with signed BAAs |
| PCI DSS | Only relevant to Ciago's own billing/payment-processing path; we minimize scope by using a PCI-compliant third-party payment processor rather than handling card data directly | Ongoing, SAQ-A scope by design |

### 16.6 Supply Chain Security

- All first-party and marketplace-distributed container/app images are scanned and signed; the platform enforces admission-time signature verification (Kyverno policy) before any image is scheduled.
- SBOMs (Software Bill of Materials) are generated for every first-party build and required as part of marketplace ISV submission (Section 20), enabling downstream vulnerability tracking (e.g., rapid identification of exposure to a newly disclosed CVE in a common dependency).
- Container registry: Harbor, providing vulnerability scanning, signed-image enforcement, and RBAC-scoped access for both first-party and marketplace image publishing pipelines.

### 16.7 Audit Logging

Every control-plane mutating action (resource creation/deletion, permission changes, billing changes, AI-assistant agentic actions per Section 10.6) is written to an append-only, tamper-evident audit log (hash-chained records), queryable by org administrators and exportable to enterprise customers' own SIEM tooling via a standard log-forwarding integration.


## 17. AI Integration

AI is embedded as a cross-cutting capability rather than a bolted-on feature; this section catalogs each integration point, its scope, and its safety boundary.

| AI System | Function | Scope of Autonomy | Safety/Fallback Boundary |
|---|---|---|---|
| AI Assistant (Cloud OS shell) | Conversational help, contextual Q&A, agentic actions | Can take confirmed actions on the user's behalf (Section 10.6) | All agentic actions require explicit confirmation and are audit-logged; no destructive action (delete, billing change) without confirmation |
| AI Resource Optimizer | Recommends/right-sizes resource allocations (e.g., "your Blender sessions never use more than 60% of the allocated GPU tier, consider downgrading") | Advisory by default; can be granted auto-apply permission by the user/org | Never auto-applies changes to billing-affecting resource tiers without opt-in |
| AI Scheduler (Layer 3 of Section 12.3) | Refines placement ranking using historical patterns | Advisory refinement only, always bounded by Layer 1/2 deterministic guardrails | Cannot override Layer 1 hard constraints (compliance, entitlement, capacity floors) under any circumstance |
| AI Cost Optimizer | Identifies cheaper viable placement/resource options, spot-capacity opportunities, idle-resource waste | Advisory + opt-in auto-apply for non-disruptive changes (e.g., migrating a batch job to spot capacity) | Never migrates a "pinned" or explicitly latency-critical workload purely for cost without explicit permission |
| AI Security (anomaly detection) | Flags anomalous access patterns (impossible travel, unusual API call volume, credential misuse patterns) | Can auto-trigger step-up authentication or temporary session suspension for high-confidence anomalies | High-severity auto-actions are reversible and always paired with immediate human-reviewable alerting; false-positive appeal path always available |
| AI Auto Scaling | Predicts load and pre-scales IaaS/PaaS capacity ahead of demand | Operates within org-configured scaling bounds (min/max) | Cannot exceed org-configured budget/quota ceilings |
| AI Code Assistant (developer platform) | Code completion, review assistance, infra-as-code generation (Terraform/Pulumi snippets) integrated into Cloud IDE | Suggests only; developer always reviews/accepts | No auto-commit/auto-deploy without explicit developer action |
| AI Troubleshooting | Diagnoses failed deployments, crashed sessions, network issues; suggests remediation | Advisory, with one-click "apply suggested fix" for well-understood, low-risk remediation classes | Higher-risk remediations (e.g., infrastructure recreation) always require explicit confirmation |
| AI Deployment Advisor | Recommends resource sizing, region selection, and architecture patterns for new IaaS deployments based on declared workload type | Advisory at deployment-configuration time | Never silently changes an already-deployed resource's configuration |

### 17.1 Model Serving Infrastructure

AI features are served through an internal model-serving layer supporting both (a) smaller, latency-critical models run close to the point of use (e.g., a lightweight anomaly-detection model co-located with each region's control plane) and (b) larger models (the conversational assistant, code assistant) served from a smaller number of GPU-backed inference clusters, with response caching and request batching for cost efficiency. **Assumption A-6:** For the conversational and code-assistant capabilities, we assume the platform will integrate with a leading third-party large language model provider via API for the initial GA rather than training foundation models in-house, revisiting in-house model investment only if usage scale and differentiation needs justify the capital expenditure (Section 29).

### 17.2 Data Governance for AI Features

- Contextual AI assistant access to application state (Section 10.6) is opt-in per application and revocable at any time from the Settings panel.
- No user file content or session telemetry is used to train third-party or first-party models without explicit, separate opt-in consent, and enterprise customers can contractually disable any model-training data usage entirely (a standard enterprise-tier data-processing addendum term).
- AI Security anomaly detection operates on access-pattern metadata (timestamps, IPs, API call types), not content, minimizing the sensitivity of data touched by that subsystem.


## 18. Developer Platform

### 18.1 Surface Areas

The developer platform exposes every capability of the IaaS/PaaS layer (Section 19) and portions of the Cloud OS/Application Platform (Section 20) through programmatic interfaces, so that no capability is "trapped" behind the graphical Cloud OS shell.

| Interface | Purpose | Notes |
|---|---|---|
| CLI (`ciago` binary) | Primary interactive/scriptable interface for provisioning, deployment, session management | Cross-platform (Windows/macOS/Linux), single static binary, shells out to same REST/gRPC APIs as everything else — no hidden capability |
| REST API | Resource CRUD, broad third-party integration surface | OpenAPI 3.1 spec published; auto-generated client SDKs for major languages (Go, Python, TypeScript, Rust) |
| GraphQL API | Aggregated, flexible querying — primarily consumed by the Cloud OS shell itself, also available to third parties for dashboard-style integrations | Federated gateway over underlying REST/gRPC services, not a separate source of truth |
| gRPC (internal + selectively external) | High-throughput/streaming use cases (e.g., real-time log/metric streaming to a CLI or third-party observability integration) | |
| Terraform Provider | Declarative infra-as-code management of platform resources | First-class citizen — many enterprise and Studio-tier customers will manage the platform exclusively through Terraform |
| Pulumi Provider | Same as Terraform, for teams preferring general-purpose-language IaC | Generated from the same underlying resource schema as the Terraform provider to avoid drift between the two |

### 18.2 CI/CD & Source Integration

- **GitHub/GitLab integration**: OAuth-based repository connection; webhook-triggered build pipelines.
- **Build pipelines**: containerized build execution on the platform's own CPU fleet (dogfooding the IaaS layer), with build-cache layering to minimize repeated work.
- **Deployment targets**: a successful build can deploy directly to platform compute (a container app, a function, a full VM, or a Kubernetes cluster workload) via a declarative deployment manifest, conceptually similar to established PaaS deployment models (Vercel/Netlify/Railway/Fly.io-style "git push to deploy," extended to also cover GPU-backed workload types those platforms do not support).

### 18.3 Cloud IDE & Remote Development

- **Cloud IDE**: a browser-accessible and Cloud-OS-embedded development environment, backed by the same execution venues as any other cloud-placed workload — meaning a "cloud dev environment" is not a bespoke product, it is simply a specific application manifest running through the standard Hybrid Execution Engine.
- **Dev Containers**: standard `devcontainer.json`-compatible environment definitions, so existing VS Code Dev Container configurations work without modification.
- **VS Code / JetBrains integration**: native extensions allowing a locally-running VS Code or JetBrains IDE to attach to a remote development session (same underlying protocol/model as VS Code Remote-SSH or JetBrains Gateway, extended to use the platform's own low-latency transport and to participate in the Hybrid Execution Engine's placement/migration model rather than being a static, manually-selected remote host).

### 18.4 Developer Experience Principles

1. **No capability exclusive to the GUI.** Anything achievable by clicking in the Cloud OS shell must be achievable via CLI/API — the GUI is a client of the same API surface developers use, not a privileged special case.
2. **Idempotent, declarative-first.** The primary recommended workflow is declarative (Terraform/Pulumi/deployment manifests); imperative CLI commands are supported for interactive/exploratory use but are not the primary recommended production workflow.
3. **Local-first tooling where possible.** The CLI, SDKs, and IaC providers run and can be tested locally without requiring a live cloud session, minimizing developer inner-loop friction.

## 19. IaaS Platform

### 19.1 Resource Catalog

| Resource Type | Description | Underlying Primitive |
|---|---|---|
| Virtual Machines | General-purpose or GPU-attached VMs, user-managed OS | KubeVirt-managed Firecracker/Cloud Hypervisor micro-VMs |
| Containers | OCI-image-based workloads, platform-managed lifecycle | Kata Containers (default, strong isolation) or standard containers for lower-sensitivity, cost-optimized workloads (opt-in) |
| Functions (serverless) | Event-driven, short-lived execution | gVisor-sandboxed or Firecracker-based (Lambda/Fargate-style) execution, scale-to-zero |
| Static Sites / Web Apps | Git-deploy static or SSR web applications | Built on the CDN/edge layer (Section 14) plus containerized SSR runtime where needed |
| Managed Databases | Postgres/MySQL-compatible, Redis/Valkey | Operator-managed (Kubernetes operators) stateful services with automated backup/failover |
| AI Model / LLM Hosting | Managed inference endpoints for open-weight or customer-uploaded models | GPU-backed serving infrastructure shared with Section 17's model-serving layer, exposed as a customer-facing product |
| GPU Clusters | Dedicated or shared multi-node GPU clusters for training/batch workloads | Kubernetes-native scheduling with GPU device plugins, MIG/vGPU or full-GPU allocation per customer choice |
| Managed Kubernetes | Fully managed control plane + autoscaling worker pools | Standard managed-Kubernetes pattern (comparable to EKS/GKE/AKS), built on the same underlying Kubernetes/KubeVirt substrate as the rest of the platform |
| Object/Block Storage | As described in Section 15 | Ceph-backed |
| Queues / Streaming | Managed message queues and event streams | Managed NATS (queues, lightweight pub/sub) and managed Kafka (high-throughput streaming) offerings |
| Secrets | Managed secrets storage for customer workloads | OpenBao-backed, tenant-isolated |
| Identity (for customer apps) | "Auth-as-a-service" for customers building their own apps on the platform | OIDC-compliant managed identity service, reusing the platform's own Identity Service architecture (Section 16.2) multi-tenant-ized for customer use |
| Networking (VPC-equivalent, DNS, LB, CDN, Edge Functions) | Standard cloud networking primitives | Software-defined overlay networking per tenant (Cilium/eBPF-based, Section "Technology Recommendations"), managed DNS, L4/L7 load balancers, CDN and edge functions built on the Global Edge Network (Section 14.2) |

### 19.2 Why Kubernetes as the IaaS Foundation (Cross-Reference to Dedicated Kubernetes Section Below)

The IaaS layer is built on Kubernetes + KubeVirt as the unifying orchestration substrate for both containerized and VM-based workloads, rather than maintaining a separate VM-only orchestrator (e.g., a bespoke OpenStack deployment) alongside a separate container orchestrator. The detailed rationale, alternatives considered, and tradeoffs are covered in the dedicated Kubernetes section later in this document; the summary conclusion is that a single orchestration substrate materially reduces operational surface area and lets the same bin-packing, scheduling, and node-management logic serve both VM and container workloads.

### 19.3 Multi-Tenancy at the IaaS Layer

Every customer resource belongs to a Project, every Project to a Team, every Team to an Organization (full detail in the dedicated Multi-Tenancy section). At the infrastructure level, tenant isolation is enforced at three points: (1) namespace-level isolation in Kubernetes (network policy + RBAC scoping), (2) VM/Kata-level isolation for actual workload execution (no tenant ever shares a kernel with another tenant's untrusted workload), and (3) storage-level isolation via per-tenant encryption keys (Section 15.4/16.4).

## 20. Application Platform

### 20.1 Application Types Supported

| Type | Packaging | Execution Model |
|---|---|---|
| Native apps | Windows/macOS/Linux binaries, platform-signed | Run locally (if venue = local) inside a sandboxed host-OS process, or inside a cloud micro-VM matching the target OS (Windows apps run inside a Windows guest VM in the cloud fleet when cloud-placed — see Assumption A-7 below) |
| Container apps | OCI images | Run inside Kata Containers pods, cloud-placed only (containers are not a "local execution" concept in the traditional consumer sense, though local Docker Desktop-style execution is supported for developer personas via the IaaS layer, Section 19) |
| Web apps / PWAs | Standard web app manifest, URL-based | Rendered via an embedded, sandboxed web runtime in the Cloud OS shell; can run fully locally in virtually all cases given modern browser engine efficiency |
| Cloud-native apps | First-party manifest declaring cloud-only requirements (e.g., requires a specific GPU class) | Always cloud-placed by scheduler determination |
| Android apps | APK, run inside an Android compatibility layer | Cloud-placed by default (Android emulation is resource-intensive); local execution supported on capable devices as a Phase 2+ enhancement |

**Assumption A-7:** Running Windows-native applications inside cloud-hosted Windows guest VMs is licensed appropriately under applicable OS licensing programs for multi-tenant cloud hosting (comparable in structure to existing Windows 365/AVD licensing arrangements); this document assumes such licensing is negotiated as a business/legal workstream in parallel with engineering, not an engineering decision.

### 20.2 App Store / Marketplace

```
   [ISV submits app/plugin] --> [Automated scan: malware, SBOM
                                  generation, signature verification]
                                          |
                                          v
                                [Manual/automated certification
                                 review: resource-manifest sanity
                                 check, policy compliance]
                                          |
                                          v
                                 [Published to Marketplace catalog]
                                          |
                                          v
                        [User discovers via search/category browse,
                         one-click install]
                                          |
                                          v
                          [Revenue share settled monthly: default
                           85/15 split favoring the ISV, negotiable
                           for high-volume/strategic partners]
```

### 20.3 SDK & Developer APIs for App Integration

The Application SDK provides: (a) the cooperative checkpoint/restore hooks referenced in Section 11.1 (T1 tier), (b) resource-manifest declaration format (min/preferred CPU/GPU/RAM, restart-safety flags per Section 11.7), (c) Cloud OS shell integration APIs (notifications, clipboard, file-picker), and (d) the accessibility-bridge API used by the AI Assistant's contextual mode (Section 10.6), which apps can opt into to expose structured context safely rather than requiring raw screen-scraping.

## 21. Gaming Platform

### 21.1 Architecture Overview

```
 [Client: input capture + video decode]
        <---- QUIC-based low-latency transport ---->
 [Regional GPU cluster: session compositor + game process]
        |
        +-- GPU virtualization (full-GPU for AAA titles requiring
        |   maximum performance; MIG/vGPU fractional for lighter titles)
        +-- Video encode (hardware NVENC/AV1 encode on the GPU)
        +-- Anti-cheat kernel module runs inside the guest VM,
        |   attested as part of session integrity checks
        +-- Cloud save sync (hooks into Section 15.3's sync backend)
```

### 21.2 Key Design Points

- **GPU virtualization**: full dedicated GPU allocation for top-tier/competitive titles where frame-time consistency is critical; fractional (MIG/vGPU) allocation for lighter titles, improving fleet utilization (Section 13.2, NFR-12).
- **Low latency**: achieved through (a) regional GPU cluster placement close to population centers (Section 13.1), (b) QUIC transport with connection migration to survive network handoffs without session drop, (c) client-side frame prediction/interpolation techniques to smooth over minor jitter without adding input lag (distinct from, and complementary to, server-side rendering — the client never fabricates gameplay-affecting state, only smooths presentation).
- **Controller support**: standard HID passthrough for physical controllers; virtual/touch controller overlays for platforms without physical controllers, with input events time-stamped client-side and delivered over the lowest-latency available stream to minimize added mapping overhead.
- **Adaptive bitrate**: real-time bitrate/resolution/frame-rate adjustment based on measured network conditions (packet loss, available bandwidth), prioritizing frame-rate stability over peak resolution when forced to trade off, based on user research indicating input responsiveness perception is more sensitive to frame-time consistency than to resolution.
- **Video codecs**: AV1 preferred where client hardware decode support exists (materially better quality-per-bit than H.264), with H.264/HEVC fallback for broader device compatibility.
- **Frame prediction**: client-side techniques analogous to NVIDIA Reflex/frame-warping approaches — extrapolating from recent frames plus latest input to reduce perceived latency, always bounded so the extrapolation window cannot exceed a threshold that would risk visible artifacts.
- **Anti-cheat**: kernel-level anti-cheat modules run inside the cloud-hosted guest VM (not on the client), which is actually an advantage over local PC gaming for anti-cheat integrity — the client only ever receives a video/audio stream, meaning traditional memory-scanning cheat techniques that require local process access have no local process to attach to.
- **Mods**: supported per-title based on the title's own mod-support policy; mod files are stored in the user's cloud storage and mounted into the session's guest VM at launch.
- **Multiplayer & voice chat**: regional matchmaking servers are co-located with the GPU clusters to minimize the additional hop between rendering and multiplayer-authoritative game-state servers; voice chat uses a low-latency audio codec (Opus) over the same QUIC session transport.
- **Regional GPU clusters**: capacity planning for gaming explicitly accounts for strong diurnal/weekly demand curves (evening/weekend peaks) — this peak capacity is the same capacity cross-subsidized for business-hours AI/rendering batch work referenced in Section 3.3.

## 22. Creative Platform

### 22.1 Supported Application Classes

Blender, Adobe Creative Cloud suite, Autodesk suite (Maya, 3ds Max, AutoCAD, Revit), DaVinci Resolve, professional audio/DAW software, AI image/video generation tooling, engineering simulation (FEA/CFD-class workloads), architecture/BIM tooling, and medical imaging visualization (DICOM viewers, 3D reconstruction) are supported as certified, pre-configured environments.

### 22.2 GPU Allocation Model for Creative Workstations

| Tier | GPU Allocation | Target Workload | Cold-Start Target |
|---|---|---|---|
| Light | Fractional (MIG/vGPU slice, ~1/4 to 1/2 of a data-center GPU) | 2D editing, light 3D viewport work, basic AI image generation | ≤ 8s |
| Standard | Fractional, larger slice (~1/2 to full single GPU equivalent) | Blender/Maya production scenes, 4K video editing, standard AI generation workloads | ≤ 10s |
| Pro | Full dedicated top-tier GPU, optionally multi-GPU | Heavy simulation, large-scene rendering, high-resolution AI video generation, engineering FEA/CFD | ≤ 15s (larger environments, more state to restore) |

Cold-start targets are achieved via **golden snapshot caching**: rather than booting a generic OS and then installing/configuring the target application at launch time, each certified environment is pre-baked as a VM/container snapshot with the application already installed, licensed, and warmed (application process started, common asset caches primed), stored in a fast-restore-optimized format and pre-staged onto hosts with predicted demand (informed by the AI Resource Optimizer, Section 17) so that "cold start" is actually closer to a snapshot restore than a true cold boot.

### 22.3 Collaborative Review (Phase 3+)

A shared-viewport streaming capability allows a second viewer to observe (and, with permission, annotate) a live creative session — architecturally, this reuses the same session-compositor-to-multiple-viewers fan-out pattern already required for any multi-client scenario, rather than introducing a bespoke collaboration subsystem.


## 23. Billing

### 23.1 Pricing Model Structure

| Component | Model | Example Unit |
|---|---|---|
| Subscription plans (consumer/prosumer) | Flat monthly/annual fee including a bundled resource credit allowance | "$29/mo includes 40 hrs of Standard-tier cloud sessions + 100GB storage" |
| Usage overage | Metered beyond subscription allowance | Per GPU-second, per vCPU-hour, per GB-month storage, per GB egress |
| IaaS/PaaS direct consumption | Pure usage-based, no subscription required | Per vCPU-hour, per GPU-hour (by class), per GB-month, per million function invocations |
| Marketplace | Revenue share on ISV transactions | Default 85/15 split favoring ISV (Section 20.2) |
| Enterprise/committed-use | Discounted rate for committed capacity/spend over a term | Standard reserved-instance-style discounting, comparable in structure to hyperscaler committed-use discounts |
| Spot/burst capacity | Discounted, interruptible-tolerant pricing for flexible batch workloads (Studio persona, Section 6) | Priced dynamically against real-time spare-capacity levels |

### 23.2 Metering Pipeline

```
 [Every billable event: session-second of GPU use, GB stored,
  GB egressed, function invocation, etc.]
              |
              v
 [High-throughput event stream (Kafka) -- durable, ordered per
  tenant, designed for exactly-once downstream aggregation via
  idempotent consumer offsets]
              |
              v
 [Real-time aggregation service -- rolls raw events into
  per-tenant, per-resource-type usage counters at multiple
  granularities (minute/hour/day)]
              |
              v
 [ClickHouse analytical store -- powers usage dashboards
  (FR-B4) and finance-grade invoice generation]
              |
              v
 [Billing/Invoicing service -- applies subscription credits,
  overage rates, committed-use discounts, generates invoices,
  hands off to payment processor for consumer/prosumer, or
  enterprise invoicing workflow for committed contracts]
```

### 23.3 FinOps Dashboard

Every organization has access to a cost dashboard showing real-time spend broken down by project/team/resource-type, forecasted month-end spend based on current trajectory, and AI Cost Optimizer recommendations (Section 17). Enterprise customers additionally get cost-center tagging and exportable, GL-code-mappable billing detail for their own finance systems.

### 23.4 Design Rationale: Why Sub-Hour Metering Granularity

Coarser (e.g., hourly-minimum) billing granularity, common in older cloud VM pricing, materially disadvantages the platform's own core value proposition — Creative Caleb (P2) and Studio Sam (P6) personas specifically benefit from paying for GPU access in small, precise increments matching their actual bursty usage pattern (Section 3.3, Section 6.2). Sub-hour (per-second, rounded to a small minimum billing increment to bound metering overhead) granularity is therefore treated as a product requirement, not just a billing implementation detail.

## 24. Scalability

### 24.1 Scale Milestones and Bottleneck Analysis

| Scale | Primary Bottleneck Risk | Mitigation |
|---|---|---|
| 10 users | None (any reasonable single-region deployment handles this trivially) | N/A — this scale validates functional correctness, not scale |
| 100 users | Still no meaningful infra bottleneck; risk is entirely in application-level bugs and manual-process gaps (e.g., manual certification review of marketplace apps) | Automate what can be automated early even at low volume, to validate automation correctness before it's load-bearing |
| 10,000 users | Control-plane database (single Postgres primary) approaches write-throughput limits for session/telemetry-adjacent writes if not carefully separated from the core transactional path; naive single-region GPU capacity planning starts to matter | Separate high-volume telemetry/session-event writes onto the Kafka/ClickHouse path (Section 23.2) from day one rather than writing them into the transactional Postgres store; begin real capacity forecasting |
| 1,000,000 users | Single-region control plane becomes a real risk (blast radius of a regional incident, and raw request volume); Postgres primary write throughput becomes a genuine constraint for org/billing-critical transactional data even with read replicas | Multi-region control-plane deployment with regional autonomy for session/scheduling decisions (Section 12) so a single region's control plane never needs global synchronous coordination for routine placement decisions; begin Vitess-based sharding of the Postgres billing/org tables by tenant |
| 100,000,000 users | Global identity/session-token validation must be effectively zero-latency-overhead and infinitely horizontally scalable; storage layer must operate at genuine exabyte scale with proven multi-region erasure coding; GPU supply chain becomes a strategic-partnership-level constraint, not an engineering problem | Fully regionalized control planes with only eventually-consistent, asynchronous cross-region reconciliation for non-critical-path data (e.g., global marketplace catalog sync); token validation via stateless, cryptographically self-contained session tokens (JWT-style) validated locally at every edge PoP with no per-request central lookup; long-term GPU supply strategy including possible direct OEM/manufacturer partnerships (Section 29) |

### 24.2 Control Plane Scaling Strategy

The control plane is designed from day one with a **regional-autonomy** principle: each region's scheduler, session registry, and gateway can make placement and session-continuity decisions using only regionally-local data for the overwhelming majority of requests, with global services (billing aggregation, cross-region marketplace catalog, org/identity source-of-truth) operating on relaxed, asynchronous consistency. This avoids the classic scaling trap of a "globally synchronous" control plane where every region's user-facing latency is bounded by the slowest or most congested region.

### 24.3 Data Layer Scaling Path

1. **Phase 1–2**: single-region Postgres primary + read replicas, sufficient for early scale (validated against 24.1's 10K-user bottleneck analysis).
2. **Phase 3**: introduce Vitess sharding for the billing/usage-adjacent tables specifically (highest write volume, most naturally shardable by tenant ID), while org/identity core tables remain on a smaller, less write-heavy Postgres cluster for longer.
3. **Phase 4+**: full multi-region active-active for read-heavy paths (session lookup, catalog), with a clearly defined, deliberately small set of genuinely global-consistency-requiring operations (e.g., preventing double-spend on committed-use discount application) isolated to a dedicated, carefully-designed global-consensus service rather than forcing the entire data layer into that consistency model.

## 25. Disaster Recovery

### 25.1 Failure Domains

| Failure Domain | Example | Recovery Strategy |
|---|---|---|
| Single host failure | Hardware fault on one bare-metal node | Kubernetes/KubeVirt reschedules affected pods/VMs to healthy hosts; for active sessions, triggers migration (Section 11.3) from the most recent checkpoint rather than a cold restart |
| Rack/row power or network failure | PDU or top-of-rack switch failure | Affected hosts marked unhealthy, workloads rescheduled within the region across unaffected racks; redundant power/network paths at the data-center design level minimize blast radius |
| Full regional outage | Regional data center loses connectivity or suffers a catastrophic event | Gateway layer (Section 14.4) redirects new session admission to next-best healthy region; active sessions attempt cross-region migration where checkpoint data was replicated (Section 15.4 opt-in cross-region replication) — sessions without cross-region replication opted in are recovered from the most recent object-storage-persisted checkpoint after a brief outage window |
| Control-plane software failure/bad deploy | A control-plane service regression | Standard progressive-rollout deployment strategy (Section 28) with automated rollback on health-check regression; multi-region deployment means a bad regional control-plane deploy does not necessarily take down other regions |
| Storage layer failure | Ceph OSD/node failures beyond replication tolerance (rare, given erasure coding design) | Cross-AZ erasure coding tolerates multiple simultaneous node failures without data loss (Section 15, NFR-4); cross-region replication (opt-in/mandatory per Section 15.4) provides an additional recovery tier for catastrophic regional loss |

### 25.2 Recovery Objectives

| Metric | Target |
|---|---|
| RPO (Recovery Point Objective) — control-plane transactional data | ≤ 1 minute (synchronous replication within region, near-real-time cross-region log shipping) |
| RPO — user session state (checkpointed workloads) | ≤ time since last auto-checkpoint (default auto-checkpoint interval: every 60–120 seconds for active T2/T3 sessions, tunable) |
| RTO (Recovery Time Objective) — single host/rack failure | ≤ 30 seconds for affected sessions to resume elsewhere (dominated by migration/restore time, Section 11.3) |
| RTO — full regional outage | ≤ 5 minutes for new-session admission to fail over to another region; active-session recovery time varies by whether cross-region replication was enabled |

### 25.3 Disaster Recovery Testing

Regular, automated chaos-engineering exercises (simulated host failures, simulated regional network partitions, simulated storage-node loss) are run in a dedicated non-production environment continuously, and in production via carefully scoped, opt-in "game day" exercises at a cadence defined by the SRE organization — this is standard, well-precedented practice (in the tradition of Netflix's Chaos Monkey and similar tooling) rather than a novel proposal, and is treated as a required, ongoing operational discipline rather than a one-time pre-launch checklist item.

## 26. Monitoring

### 26.1 Observability Stack

| Signal Type | Tooling | Notes |
|---|---|---|
| Metrics | Prometheus (collection) + Grafana (visualization) | Standard cloud-native stack; long-term metrics storage via a Prometheus-compatible remote-write backend sized for platform scale |
| Tracing | OpenTelemetry (instrumentation standard, vendor-neutral) | Distributed traces span client -> edge -> control plane -> data plane for full request-path visibility, essential given the number of hops in the placement/migration flows (Section 9.2, 11.3) |
| Logging | Structured logging shipped via OpenTelemetry Collector to a centralized log store | Correlated with trace IDs for cross-referencing logs and traces during incident investigation |
| Alerting | Prometheus Alertmanager + on-call paging integration | Alert rules tiered by severity, with automated escalation policies |
| Health Monitoring | Synthetic health checks (per-region, per-service) plus real-user-monitoring signals from the client | Feeds directly into Section 12's scheduler capacity/health signals and Section 25's failover triggers |
| AI Incident Detection | ML-based anomaly detection over the metrics/tracing corpus (Section 17) | Flags statistically anomalous patterns (e.g., a region's migration failure rate spiking) ahead of threshold-based alerting catching the same issue, shortening MTTD (NFR-10) |

### 26.2 Golden Signals Tracked Per Subsystem

Consistent with standard SRE practice, every service tracks latency, traffic, errors, and saturation ("the four golden signals") at minimum, with subsystem-specific additions:

- **Scheduler**: decision latency (Section 12.4), decision-to-outcome accuracy (did the placement avoid a subsequent migration within N minutes — a proxy for placement quality).
- **Migration engine**: migration success rate, convergence time (Section 11.3), rollback rate (Section 11.6).
- **GPU fleet**: utilization (NFR-12), fractional-allocation packing efficiency, thermal/power headroom.
- **Storage**: erasure-coding repair backlog, replication lag (cross-region), sync conflict rate (Section 15.3).
- **Billing/metering**: event-ingestion lag (time from billable event to reflected usage counter), invoice-generation accuracy (reconciliation checks against raw event totals).

## 27. Cost Optimization

### 27.1 Platform-Side Cost Levers

| Lever | Mechanism | Cross-Reference |
|---|---|---|
| GPU fractional allocation | MIG/vGPU slicing to avoid dedicating a full GPU to workloads that don't need one | Section 13.2, 21.1, 22.2 |
| Diurnal/segment cross-subsidization | Gaming-peak capacity reused for business-hours AI/render batch work | Section 3.3, 21.2 |
| Spot/interruptible capacity | Sold at a discount for workloads tolerant of preemption (batch rendering, ML training checkpointed appropriately) | Section 19.1, 23.1 |
| Golden-snapshot caching | Reduces cold-start compute waste and repeated setup work | Section 22.2 |
| Regional/edge placement optimization | Avoids unnecessary long-haul bandwidth costs and backbone congestion | Section 13.1, 14 |
| Storage lifecycle tiering | Automatic movement of cold data to cheaper storage tiers | Section 15.4 |
| AI Cost Optimizer | Continuous, automated identification of over-provisioned or misplaced resources | Section 17 |

### 27.2 Customer-Facing Cost Optimization Tools

The FinOps dashboard (Section 23.3), AI Resource Optimizer recommendations (Section 17), budget alerts/hard caps (org-configurable spend ceilings that can either warn or hard-stop provisioning), and committed-use discount planning tools (usage-history-based recommendations for how much committed capacity a customer should purchase) collectively give customers the same category of cost-governance tooling enterprise customers expect from hyperscaler FinOps tooling (e.g., AWS Cost Explorer/Savings Plans-style guidance), applied to this platform's specific resource model.

## 28. Deployment Strategy

### 28.1 Software Delivery Pipeline (Platform's Own Services)

```
 [Developer commits code] --> [CI: build, unit/integration tests,
                                 SBOM generation, image signing]
                                          |
                                          v
                              [ArgoCD: GitOps-based continuous
                               delivery -- desired state in Git,
                               ArgoCD reconciles cluster state to
                               match]
                                          |
                                          v
                       [Progressive rollout: canary a small % of
                        traffic/regions first, automated health-
                        check-gated promotion to full rollout,
                        automatic rollback on regression]
                                          |
                                          v
                          [Full deployment across all regions,
                           staggered to avoid simultaneous global
                           risk from any single bad change]
```

### 28.2 Infrastructure Provisioning

Physical/cloud infrastructure itself (the "Layer 1" hosts, networking, and the Kubernetes clusters running on top of them) is provisioned via OpenTofu (the open-source Terraform fork) with Crossplane managing higher-level, Kubernetes-API-native provisioning of cloud-style resources — this combination lets the platform team manage both raw infrastructure (OpenTofu) and composed, higher-level platform resources (Crossplane, exposing custom resources like "GPU-backed session pool" as native Kubernetes objects) through consistent, GitOps-compatible tooling.

### 28.3 Policy Enforcement in the Pipeline

Kyverno (Kubernetes-native policy engine) enforces admission-time policies (image signature verification per Section 16.6, resource quota compliance, required labels for cost-allocation tracing) before any workload — first-party platform service or customer workload — is admitted to a cluster.

### 28.4 Release Cadence

- **Control plane services**: continuous deployment, multiple releases per day per service, gated entirely by automated testing and progressive rollout health checks (no fixed release-train schedule for backend services).
- **Client application**: a more conservative, versioned release cadence (targeting bi-weekly to monthly stable releases) given the client is user-installed software where update friction and regression tolerance are different from a backend service — with a staged rollout (percentage-based auto-update rollout) mirroring the same progressive-rollout philosophy applied to a different delivery mechanism.


## 29. Roadmap

### 29.1 Phase 1 — Foundation (Months 0–9)

| Aspect | Detail |
|---|---|
| Goals | Prove the core Hybrid Execution Engine concept end-to-end for a narrow set of workloads; ship a functional client for one OS first (recommend Windows given target persona overlap with Section 6), single core region |
| Architecture | Control plane MVP (identity, basic scheduler Layer 1/2 only, no AI Layer 3 yet), single-region Kubernetes/KubeVirt cluster, object storage (Ceph) MVP, basic Cloud OS shell (window manager + launcher + file explorer, no time-travel/snapshot yet) |
| Resources | Core platform engineering team (~25–35 engineers: control plane, client, infra, security), 1 core region built or leased |
| Budget estimate | **Assumption A-8**: Order-of-magnitude estimate only, pending real vendor quotes: $15–25M covering initial data center buildout/lease, GPU procurement for the pilot fleet, and 9 months of engineering headcount |
| Risks | GPU procurement lead times; underestimating migration-engine complexity (Section 11 is the highest-risk component) |
| Dependencies | GPU vendor supply agreements; initial data-center site selection/lease finalized |
| Milestones | M1: local-only Cloud OS shell functional; M2: first successful cloud placement + migration of a T1 workload; M3: closed pilot with internal/friendly users |

### 29.2 Phase 2 — Private Beta (Months 9–18)

| Aspect | Detail |
|---|---|
| Goals | Expand to macOS/Linux clients; add creative-platform certified environments (Blender first, given open-source licensing simplicity relative to Adobe/Autodesk); add basic gaming platform pilot; introduce AI Layer 3 scheduler refinement |
| Architecture | Multi-region control plane (2–3 regions), fractional GPU (MIG/vGPU) rollout, file sync backend (Section 15.3) production-ready, developer platform CLI/API GA |
| Resources | Scale to ~60–90 engineers; add dedicated SRE/security functions |
| Budget estimate | **Assumption A-8 (cont.)**: $40–60M covering additional regions, GPU fleet expansion, and headcount growth |
| Risks | Multi-region control-plane complexity; creative-platform ISV licensing negotiations (Adobe/Autodesk) taking longer than engineering readiness |
| Dependencies | SOC 2 Type I readiness for early enterprise pilot conversations; initial ISV licensing agreements |
| Milestones | M4: private beta live across 3 personas (Ana/Caleb/Devi); M5: first enterprise pilot customer live; M6: gaming platform closed pilot |

### 29.3 Phase 3 — General Availability (Months 18–30)

| Aspect | Detail |
|---|---|
| Goals | Public GA across consumer, creative, developer, and gaming segments; enterprise tier launch; SOC 2 Type II and ISO 27001 achieved; marketplace opens to third-party ISVs |
| Architecture | 6+ core regions, edge PoP expansion, Vitess sharding introduced for billing data, full AI integration suite (Section 17) live |
| Resources | Scale to ~150–220 engineers plus a growing go-to-market/support organization |
| Budget estimate | **Assumption A-8 (cont.)**: $100–160M covering GPU fleet scale-up (largest single line item given GPU capital cost), regional expansion, and compliance program cost |
| Risks | GPU supply constraints at scale (Section 31); competitive response from incumbents; unit economics validation at real scale (utilization assumptions in NFR-12 must hold) |
| Dependencies | Enterprise compliance certifications complete; marketplace certification pipeline (Section 20.2) proven at volume |
| Milestones | M7: public GA launch; M8: first $10M ARR month; M9: 100K MAU across all personas |

### 29.4 Phase 4 — Scale & Enterprise Depth (Months 30–48)

| Aspect | Detail |
|---|---|
| Goals | HIPAA-tier compliance offering; confidential computing tier; deeper enterprise features (device posture, cost-center allocation at scale); international expansion (additional regions, data residency coverage) |
| Architecture | Full multi-region active-active for read paths (Section 24.3 Phase 4 step), confidential computing (SEV-SNP/TDX) support, CXL-based memory pooling adoption in new data-center builds (Section 11.8.4) |
| Resources | Continued organizational scale-up; dedicated compliance/legal function matured |
| Budget estimate | **Assumption A-8 (cont.)**: $200–300M, dominated by continued GPU/data-center capital expenditure and international expansion cost |
| Risks | Regulatory complexity across new jurisdictions; confidential-computing performance overhead affecting unit economics for that tier |
| Milestones | M10: HIPAA-tier customer live; M11: 1M concurrent peak gaming sessions (B-6 target); M12: enterprise NRR ≥130% (B-7 target) achieved |

### 29.5 Phase 5 — Platform Maturity & Innovation (Months 48+)

| Aspect | Detail |
|---|---|
| Goals | Evaluate in-house foundation model investment (revisit Assumption A-6) if usage scale justifies it; evaluate custom silicon/ASIC partnership for cost structure improvement at hyperscale; explore direct OEM GPU supply partnerships to de-risk procurement (Section 31) |
| Architecture | Continued evolution per Section 32 (Future Innovations) |
| Budget estimate | To be planned against actual Phase 3/4 financial performance rather than projected years in advance |
| Milestones | Sustained gross margin targets (B-4: ≥65%) achieved; platform recognized as a top-3 alternative in at least two of its four converged categories (Section 5) |

## 30. Competitive Analysis

### 30.1 Comparison Matrix

| Competitor | Category | Strength vs. \<Project Name\> | Weakness vs. \<Project Name\> |
|---|---|---|---|
| AWS | Hyperscale IaaS/PaaS | Unmatched breadth, reliability track record, enterprise trust | No consumer-facing product, no unified Cloud OS/hybrid-execution concept, no gaming/creative consumer story |
| Azure | Hyperscale IaaS/PaaS + Windows 365/AVD | Closest competitor structurally (owns DaaS + cloud + partial gaming via Xbox Cloud Gaming) | Products remain siloed (no automatic hybrid workload placement between them); enterprise-first, not consumer-first design |
| Google Cloud | Hyperscale IaaS/PaaS | Strong AI/ML infrastructure | Weakest consumer-facing compute product history (Stadia's shutdown is a notable cautionary precedent for the category), no DaaS product |
| Cloudflare | Edge/network, Workers | Best-in-class edge network breadth and developer mindshare for edge compute | Not a GPU/desktop/gaming platform at all — different market, though a potential long-term infra partner/competitor for the edge layer specifically |
| Windows 365 / AVD | DaaS | Deep Windows/AD integration, enterprise incumbency | Session-monolithic architecture, no dynamic hybrid placement, not consumer-priced |
| VMware Horizon / Citrix | Enterprise VDI | Deep enterprise VDI incumbency, broad peripheral/legacy app support | Legacy architecture assumptions (persistent VM per user), weak/no consumer or gaming story |
| Shadow PC | Consumer cloud PC | Closest conceptual product analog | Legacy fixed-VM-per-user model rather than dynamic hybrid execution; historically constrained GPU tier options and capacity |
| GeForce NOW | Cloud gaming | Best-in-class GPU streaming pipeline maturity, deep game-publisher licensing relationships | Single-purpose (gaming only), no general compute/creative/dev story |
| Xbox Cloud Gaming / Amazon Luna | Cloud gaming | Strong first-party content (Xbox) / distribution reach (Amazon) | Single-purpose, tied to specific ecosystems/storefronts |
| Steam Remote Play | Cloud/local streaming hybrid | Huge existing user base and library | Not truly "cloud" for most users (typically streams from the user's own home PC, not data-center GPUs) — different problem being solved |
| Paperspace / RunPod / Lambda Labs | GPU-specialist IaaS | Strong price/performance for ML-engineer audience, fast iteration | Narrow (ML/dev audience only), no consumer Cloud OS, no gaming |
| Oracle Cloud, DigitalOcean | General IaaS | Cost-competitive general compute | No differentiated hybrid-execution or consumer story |
| Render, Fly.io, Railway, Vercel, Netlify | Modern PaaS | Excellent developer experience for web/app deployment | Narrow scope (web apps/functions), no GPU/desktop/gaming ambition |

### 30.2 Sustainable Differentiation Summary

No competitor listed combines (a) transparent, dynamic hybrid local/cloud execution at the process level, (b) a genuinely novel Cloud OS shell rather than a remote-desktop-style session window, and (c) a single identity/billing surface spanning consumer desktop, gaming, creative workstation, and full IaaS/developer platform. The nearest structural analog (Microsoft's portfolio) achieves category breadth through separate, non-integrated products; \<Project Name\>'s core bet is that the *integration* — specifically the Hybrid Execution Engine's transparent placement and migration — is itself the defensible product, not any single component in isolation.


## 31. Risks

### 31.1 Risk Register

| Category | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Technical | Hybrid Execution Engine (Section 11) proves more complex/less reliable than projected, particularly T3 (GPU-resident) migration | Medium-High | High | Phase 1 explicitly scopes a narrow workload set to prove the concept before broad expansion; T3 migration pause-duration limitations are disclosed as a real constraint (Section 11.3.1) rather than assumed away |
| Technical | Live migration convergence failures for high-dirty-rate workloads degrade user experience | Medium | Medium | Fallback stop-and-copy strategy (Section 11.3) with bounded worst-case pause, continuously monitored (Section 26.2) |
| Business | Slower-than-planned ISV licensing negotiations (Adobe/Autodesk-class vendors) delay creative-platform breadth | Medium | Medium | Prioritize open-source/permissively-licensed tools (Blender) for early phases; treat major ISV licensing as a parallel business-development workstream starting in Phase 1, not a Phase 2 afterthought |
| Legal/Regulatory | Multi-jurisdiction data residency and compliance requirements (GDPR, and eventually HIPAA/sector-specific regimes) expand faster than compliance program maturity | Medium | High | Data residency architecture (Section 15.4) designed as a first-class, per-bucket configurable control from Phase 1, not retrofitted later |
| Security | Multi-tenant GPU/compute isolation failure (a cross-tenant side-channel or escape) | Low | Very High | Defense-in-depth isolation strategy (Section 16.3) explicitly avoids weaker isolation primitives (shared-kernel-only containers) for any untrusted multi-tenant workload; regular third-party penetration testing and a security bug-bounty program |
| Financial | Unit economics (GPU utilization targets, NFR-12) fail to materialize at real-world scale, compressing gross margin below plan (B-4) | Medium | High | Cross-subsidization strategy (Section 3.3) and fractional GPU allocation (Section 13.2) are core mitigations designed in from the start rather than optimizations bolted on later; continuous FinOps-style internal monitoring of actual vs. planned utilization |
| Operational | Regional data-center buildout/lease timelines slip, delaying capacity needed for growth milestones | Medium | Medium | Blend owned and leased/colo capacity (Section 13.1) specifically to reduce dependency on any single buildout timeline |
| Scalability | Control-plane data layer (Postgres) scaling path (Section 24.3) requires a harder-than-planned migration to sharding under real production load | Medium | Medium | Early, deliberate separation of high-volume telemetry/billing-event data onto the Kafka/ClickHouse path (Section 23.2) specifically to delay and de-risk the harder transactional-data sharding migration |
| Vendor/Supply | GPU shortages during industry-wide demand spikes (a recurring pattern in recent GPU market cycles) constrain fleet growth exactly when user growth most needs it | Medium-High | High | Diversify across GPU vendors (NVIDIA primary, AMD/Intel evaluated as secondary options per Section "GPU Infrastructure" below); pursue committed, forward-dated supply agreements ahead of demand rather than reactive procurement; Phase 5 considers direct OEM partnership as a longer-term structural mitigation |
| Vendor Lock-in | Deep dependency on a single cloud-hardware/software vendor ecosystem (e.g., one GPU vendor's proprietary virtualization stack) constrains future negotiating leverage and technical flexibility | Medium | Medium | Architecture favors open, portable primitives where viable (Kubernetes, KVM/Firecracker, OCI) specifically to keep the orchestration and workload-portability layer vendor-neutral even where underlying GPU hardware is necessarily vendor-specific |
| Latency/Physics | Speed-of-light-bound latency floor makes certain workload classes (ultra-low-latency competitive gaming, real-time professional audio monitoring) fundamentally unsuitable for users far from any regional PoP | High (for the specific affected workload/geography combinations) | Medium (bounded — affects a known subset of use cases, not the platform broadly) | Explicit, honest product positioning: these workload classes are flagged in-product as "local execution recommended" rather than the platform pretending it can serve them equally well from the cloud; continued edge PoP densification over time narrows, but does not eliminate, the affected population |
| Regional Failure | A major regional outage during peak demand affects a disproportionate share of active sessions | Low | High | Disaster recovery architecture (Section 25) with defined RPO/RTO targets; regional-autonomy control-plane design (Section 24.2) limits blast radius of any single region's failure on other regions |


## 32. Future Innovations

### 32.1 Near-Term (Phase 4–5 Horizon)

- **CXL-based rack-scale memory pooling** in new data-center builds, improving cloud-side GPU/CPU memory elasticity (Section 11.8.4).
- **Confidential computing as a default**, not just a premium tier, as hardware TEE performance overhead continues to shrink with successive silicon generations.
- **Expanded local execution capability** for Android app compatibility and other currently cloud-default workload classes, as local device NPUs/GPUs become more capable — the scheduler's Layer 1 admissible-set logic (Section 12.3) is explicitly designed to absorb new local capability without a redesign, since "local capability" is already a first-class, continuously re-evaluated input rather than a static assumption.
- **Predictive pre-warming** maturation: using the AI Scheduler's historical-pattern model (Section 12.3, Layer 3) not just to refine placement of a workload already being launched, but to proactively pre-warm golden-snapshot environments (Section 22.2) before the user even initiates launch, based on time-of-day/day-of-week usage patterns.

### 32.2 Medium-Term Exploratory Directions

- **Custom silicon partnership evaluation** (Phase 5, Section 29.5): a co-designed accelerator optimized specifically for the platform's session-compositor encode pipeline and/or fractional-GPU virtualization overhead could materially improve unit economics at sufficient scale, following a similar strategic logic to hyperscalers' own custom-silicon investments (e.g., custom video-transcode ASICs and custom AI accelerators pursued by major cloud providers) — evaluated only once usage scale justifies the capital and design-cycle investment.
- **Direct OEM/GPU-manufacturer supply partnerships** to reduce exposure to general market GPU shortages (Section 31), potentially including co-investment in dedicated capacity.
- **In-house foundation model investment** (revisiting Assumption A-6) if AI-feature usage scale and differentiation needs justify moving off third-party model APIs for some or all AI Integration surfaces (Section 17).

### 32.3 Long-Term, Speculative Directions (Explicitly Flagged as Beyond This Document's Firm Planning Horizon)

- Wide-area memory/compute disaggregation technology beyond CXL's current rack-scale limits, should a future networking/memory-fabric technology genuinely close the WAN latency gap discussed in Section 11.8 — we do not plan around this occurring within a 5–7 year horizon (Assumption A-5) but note it as the one development that would most fundamentally change this architecture's core constraints if it occurred.
- Fully autonomous, closed-loop AI infrastructure management (auto-scaling, auto-remediation, auto-cost-optimization operating with minimal human-in-the-loop oversight) — approached incrementally and cautiously given the explainability and safety principles established in Section 12.3 and Section 17, not adopted wholesale simply because it becomes technically possible.

## 33. Conclusion

\<Project Name\> represents a genuine architectural departure from both the "remote desktop" model (Windows 365, Horizon, Citrix) and the "single-purpose cloud compute" model (pure IaaS providers, single-purpose cloud gaming services). Its central engineering bet — that workload placement between local and cloud execution venues can be made transparent, continuous, and reliable through a combination of a layered, explainable scheduling engine (Section 12) and a robust, tiered checkpoint/migration architecture (Section 11) — is ambitious but is built on individually proven component technologies (Firecracker/Kata micro-VM isolation, Kubernetes/KubeVirt orchestration, MIG/vGPU fractional GPU sharing, QUIC transport, CRIU-style checkpointing) rather than unproven primitives, which materially de-risks the engineering execution relative to the product ambition.

This document has been explicit, throughout, about where the architecture depends on stated assumptions (A-1 through A-8) and where physical/vendor-API constraints impose real limits that the product experience is designed to gracefully absorb rather than falsely promise away — most notably the GPU live-migration pause-duration constraint (Section 11.3.1) and the fundamental WAN memory-latency gap (Section 11.8). We consider this candor a strength of the architecture, not a weakness to be smoothed over for a pitch: a platform of this ambition and technical depth is best served by an implementation plan that engineering leadership can trust at face value.

The phased roadmap (Section 29) sequences risk deliberately — proving the hardest, most novel component (the Hybrid Execution Engine) first, at narrow scope, before committing the larger capital expenditure (GPU fleet, multi-region buildout) that only makes sense once that core bet is validated. Combined with a business model (Section 3, Section 23) designed from the outset around fractional GPU utilization and cross-subsidized demand curves rather than assuming favorable unit economics will simply emerge at scale, \<Project Name\> is positioned to pursue a large, converging market opportunity (Section 4, Section 5) with an architecture built to be defensible on genuine technical integration, not on any single component that a well-resourced competitor could trivially replicate.


---

## Appendix A: Kubernetes & Orchestration Strategy Deep Dive

### A.1 Should Kubernetes Be the Foundation?

**Decision: Yes, Kubernetes (extended with KubeVirt) is the foundational orchestration layer for both the Data Plane and the IaaS Platform**, with narrowly-scoped exceptions described below.

The alternative orchestration technologies evaluated, and why each was not chosen as the foundation, are summarized here:

| Technology | Role Considered | Verdict |
|---|---|---|
| Kubernetes + KubeVirt | Foundation for all container and VM workload orchestration | **Selected.** Mature scheduler, device-plugin model extensible for GPU/MIG allocation, enormous ecosystem (Helm charts, operators, CNCF tooling) directly reusable, and KubeVirt specifically closes the gap of running VMs (necessary for Windows guest sessions, Section 20.1, and user-provisioned IaaS VMs, Section 19.1) as first-class Kubernetes objects rather than requiring a second, disconnected orchestration system |
| OpenStack | Foundation for VM-centric IaaS instead of Kubernetes | **Not selected as foundation.** OpenStack is mature and proven for VM-centric private/public cloud, but maintaining two separate orchestration stacks (OpenStack for VMs, Kubernetes for containers) doubles operational surface area, doubles the scheduling/bin-packing logic that must be kept consistent with the platform's own Hybrid Execution Engine scheduler (Section 12), and creates two separate device-plugin/GPU-allocation models to maintain. KubeVirt-on-Kubernetes achieves VM support without this duplication |
| Nomad | Foundation for general workload orchestration | **Not selected.** Nomad is a legitimate, simpler alternative for pure-container/batch workloads, but its GPU-scheduling and VM-workload ecosystem maturity is meaningfully behind Kubernetes' device-plugin and KubeVirt ecosystem specifically for this platform's GPU-heavy, VM-inclusive requirements; the operational simplicity Nomad offers over Kubernetes was judged not to outweigh the ecosystem gap for this specific workload mix |
| Bespoke/custom orchestrator | Full custom build | **Not selected.** Rejected as an unjustified multi-year reinvestment in solved problems (bin-packing, scheduling, health-checking, rolling upgrades) that Kubernetes already solves robustly and that the platform's actual differentiation (the Hybrid Execution Engine, Section 11–12) sits *on top of*, not *instead of* |

### A.2 Where Kubernetes Is Deliberately Not the Direct Mechanism

- **Client-side/local execution** (Section 11.7 T0/T1 local placements) is not Kubernetes-orchestrated at all — it is simply a native OS process managed by the client's local execution runtime, since introducing a Kubernetes node concept onto every end-user's laptop would be architecturally inappropriate overhead for that use case.
- **User-owned Kubernetes clusters** provisioned via the Managed Kubernetes IaaS offering (Section 19.1) run their own independent scheduling for the customer's own workloads; the platform's Hybrid Execution Engine does not reach *into* a customer's own cluster to make placement decisions for their pods — that would violate the customer's expectation of standard, unmodified Kubernetes semantics for infrastructure they explicitly provisioned as "just Kubernetes."

### A.3 Micro-VM and Container Runtime Choices Within Kubernetes

| Runtime | Isolation Model | Where Used |
|---|---|---|
| Firecracker (via KubeVirt/a Firecracker-based VMM integration) | Hardware-virtualization-backed micro-VM | Default for Cloud OS sessions and IaaS VMs requiring strongest isolation and/or a non-Linux guest (Windows) |
| Kata Containers | VM-grade isolation with OCI/container-API compatibility | Container-shaped workloads (builds, dev containers, some IaaS container offerings) wanting VM-grade isolation without a full VM-management UX |
| gVisor | User-space kernel interception | Lower-trust, high-density, latency-tolerant workloads (some edge functions) where full VM overhead is unjustified |
| runc (standard OCI, namespaces/cgroups only) | Shared-kernel container | Restricted to first-party, fully-trusted internal platform services only — never a tenant-workload isolation boundary (Section 16.3) |

## Appendix B: GPU Infrastructure Deep Dive

### B.1 Vendor Landscape

| Vendor | Role in Fleet | Rationale |
|---|---|---|
| NVIDIA | Primary GPU vendor across all fleet classes (Section 13.2) | Most mature virtualization stack (MIG on Ampere/Hopper/Blackwell-class parts, vGPU licensing/software stack), deepest CUDA software ecosystem coverage for the AI/creative workload classes the platform targets, broadest game-engine driver support for the gaming fleet |
| AMD | Secondary/diversification vendor, evaluated for specific fleet segments (general CPU already AMD EPYC-heavy per Section 13.2; GPU diversification via ROCm-supported parts considered for cost-sensitive fractional-inference and some rendering workloads) | Supply diversification (Section 31 mitigation) and competitive pricing leverage; ROCm ecosystem maturity gap versus CUDA is real and is why AMD is positioned as secondary rather than primary for the initial fleet |
| Intel | Evaluated opportunistically (data-center GPU line, and oneAPI/DirectML-path workloads) | Additional diversification option; smaller near-term fleet role given earlier-stage data-center GPU ecosystem maturity relative to NVIDIA/AMD at this document's writing |

### B.2 GPU Virtualization Technology Comparison

| Technology | Granularity | Isolation Strength | Used For |
|---|---|---|---|
| NVIDIA MIG (Multi-Instance GPU) | Hardware-partitioned fixed slices (e.g., 1/7th-GPU instances on supported parts) | Strong — genuine hardware-level partition (dedicated memory and compute slice, not just time-sliced) | Fractional GPU tiers (Section 13.2, 21.1, 22.2) on MIG-capable parts, where predictable performance isolation matters most |
| NVIDIA vGPU (software-licensed virtual GPU) | Flexible, software-defined slices, broader compatibility across GPU generations than MIG | Good — time-sliced/software-partitioned, slightly weaker isolation guarantee than MIG's hardware partitioning, but far more flexible in slice-size configuration | Fractional allocation on GPU parts/generations without MIG support, and where flexible slice sizing outweighs MIG's stricter partitioning |
| SR-IOV (PCIe-level device virtualization, vendor-agnostic mechanism) | PCIe function-level partitioning | Strong, hardware-assisted | Underlying PCIe passthrough mechanism supporting both the MIG and vGPU models' delivery into guest VMs |
| Full GPU passthrough (no sharing) | Whole discrete GPU | Strongest (dedicated hardware, no sharing at all) | "Pro" creative tier (Section 22.2) and top-tier/competitive gaming (Section 21) where maximum, unshared performance is the explicit product promise |

### B.3 GPU Scheduling Within Kubernetes

GPU allocation is exposed to the Kubernetes scheduler via the standard Kubernetes device-plugin framework, extended with a custom device plugin that understands MIG-slice and vGPU-profile granularity (rather than only whole-GPU allocation, which is the out-of-the-box Kubernetes GPU story) — this custom device plugin is one of the platform's genuinely novel pieces of infrastructure software, since off-the-shelf Kubernetes GPU scheduling historically assumes whole-device allocation and fractional-GPU-aware scheduling at this platform's required flexibility is not a solved, off-the-shelf capability.

### B.4 AI Workload Scheduling Considerations

AI training and inference workloads (both the platform's own AI Integration features, Section 17, and customer-facing AI/LLM hosting, Section 19.1) have distinct scheduling needs from interactive sessions: they tolerate higher scheduling latency and even preemption (particularly training workloads using checkpoint-based resume, a natural fit for the same checkpoint infrastructure described in Section 11.4), and benefit from being bin-packed for throughput/utilization rather than latency. The scheduler's Layer 2 scoring weights (Section 12.3) are configured differently for these workload classes — heavily cost/utilization-weighted rather than latency-weighted — which is a direct, practical example of why the scheduler's weighting system is org/workload-configurable rather than a single fixed formula.

## Appendix C: Additional Architecture Diagrams

### C.1 Authentication Flow

```
 [Client] --1. login request-->[Identity Service]
                                        |
                              2. redirect to enterprise
                                 IdP (if federated) or
                                 present native login
                                        |
                                        v
                              [Enterprise IdP / Native Auth]
                                        |
                              3. SAML assertion / OIDC token
                                        |
                                        v
                              [Identity Service validates,
                               issues short-lived session JWT
                               + refresh token]
                                        |
                                        v
 [Client] <--4. tokens returned-------- 
      |
      5. every subsequent API call includes JWT in Authorization
         header; validated independently at each edge PoP
         (stateless validation, Section 24.1 100M-user mitigation)
```

### C.2 Billing/Metering Data Flow (Companion to Section 23.2's Narrative Description)

```
[Session/Resource Events] -> [Kafka topic, partitioned by tenant]
        |                              |
        |                    [Real-time aggregator]
        |                              |
        |                              v
        |                    [ClickHouse: usage facts]
        |                              |
        v                              v
[Cold audit/replay storage]   [Billing service: applies
 (object storage, for          rates, credits, discounts]
  dispute resolution and                |
  compliance retention)                 v
                              [Invoice / usage dashboard API]
```

### C.3 Developer Deployment Pipeline (Companion to Section 18.2)

```
[git push] -> [Webhook to Build Service] -> [Containerized build,
                                              cached layers]
                                                    |
                                                    v
                                        [Image signed, scanned,
                                         pushed to Harbor registry]
                                                    |
                                                    v
                                        [Deployment manifest applied
                                         -> Orchestration API ->
                                         Kubernetes admission
                                         (Kyverno policy check) ->
                                         scheduled onto Data Plane]
                                                    |
                                                    v
                                        [Health checks pass ->
                                         traffic cutover (for
                                         services) or session
                                         ready (for interactive
                                         workloads)]
```

## Appendix D: Consolidated Technology Recommendation Reference

This appendix consolidates the technology choices discussed throughout the document into a single reference table, with the primary justification restated for quick lookup.

| Technology | Category | Primary Justification (Detailed Rationale Cross-Referenced) |
|---|---|---|
| Rust | Client runtime, performance-critical control-plane services, session compositor | Memory safety without garbage-collection pause unpredictability, strong concurrency story — appropriate for the client and any latency-critical hot path |
| Go | Majority of control-plane microservices, CLI | Strong standard library for networked services, fast compilation, mature Kubernetes-ecosystem tooling (much of Kubernetes itself, and adjacent tooling like ArgoCD, is Go) |
| TypeScript | Cloud OS web-adjacent surfaces (marketing/dashboard web app, GraphQL API consumers) | Ecosystem fit for web-facing dashboard and developer-portal surfaces |
| C++ | GPU/video encode pipeline, low-level session compositor internals where direct hardware API access is required | Necessary for direct interaction with vendor GPU/video encode SDKs where Rust/Go bindings are immature or nonexistent |
| Linux (hardened, minimal, immutable host images) | Host OS for all data-plane and control-plane infrastructure | Universal industry standard for this workload class; immutable image approach reduces configuration drift and attack surface |
| Kubernetes | Core orchestration substrate | Section 9.3, Appendix A |
| KubeVirt | VM orchestration atop Kubernetes | Appendix A |
| OpenStack | Not adopted as foundation; not otherwise used | Appendix A |
| Ceph | Object/block storage backend | Section 15.2 |
| MinIO | Not selected as primary; not otherwise used | Section 15.2 |
| PostgreSQL | Primary transactional datastore | Section 9.3 |
| ClickHouse | Analytical/telemetry datastore | Section 9.3, Section 23.2 |
| Redis / Valkey | Cache/ephemeral tier, managed DB IaaS offering | Section 15.1 |
| NATS (JetStream) | Lightweight control-plane event bus | Section 9.3 |
| Kafka | High-throughput billing/telemetry event backbone | Section 9.3, Section 23.2 |
| Temporal | Durable workflow orchestration for migrations, provisioning, billing runs | Section 9.3 |
| Vitess | Horizontal sharding layer for Postgres at scale | Section 9.3, Section 24.3 |
| OpenTelemetry | Observability instrumentation standard | Section 26.1 |
| Envoy | L7 proxy/data-plane component underlying the service mesh and gateway layer | Standard, CNCF-mature choice for the gateway/mesh data plane |
| Cilium | Kubernetes networking/CNI, eBPF-based network policy enforcement | Section 19.1 |
| eBPF | Underlying kernel-level observability/networking mechanism (via Cilium and direct use in host-level monitoring) | Enables low-overhead, kernel-level visibility and policy enforcement without kernel modification |
| Firecracker | Micro-VM isolation | Section 16.3, Appendix A |
| Kata Containers | VM-grade container isolation | Section 16.3, Appendix A |
| Cloud Hypervisor | Alternative/complementary VMM to Firecracker for certain guest configurations (e.g., broader device-model needs) | Used where Firecracker's minimal device model is insufficient for a specific guest requirement |
| WireGuard | VPN/zero-trust tunnel transport | Section 14.3, 14.5 |
| Linkerd | Considered as a lightweight service-mesh alternative | Evaluated; Envoy-based mesh (via a standard Envoy-based control plane) selected instead given tighter fit with the gateway layer's existing Envoy usage, avoiding running two different proxy technologies for overlapping purposes |
| Istio | Considered as full-featured service-mesh option | Evaluated; judged heavier-weight than needed for internal service-to-service mTLS/traffic management given gRPC+Envoy already covers the core requirement without Istio's additional control-plane complexity |
| Prometheus | Metrics collection | Section 26.1 |
| Grafana | Metrics visualization | Section 26.1 |
| ArgoCD | GitOps continuous delivery | Section 28.1 |
| Crossplane | Kubernetes-native higher-level infrastructure composition | Section 28.2 |
| OpenTofu | Infrastructure-as-code provisioning (Terraform fork) | Section 28.2 |
| Harbor | Container registry, image scanning/signing | Section 16.6 |
| Keycloak | Evaluated as an open-source IdP component; the platform's Identity Service (Section 16.2) may build on Keycloak-derived components for the native-auth path rather than the enterprise-federation path, which relies on the customer's own IdP | Reduces the scope of custom-built authentication code for the native (non-federated) account path |
| OpenBao | Secrets management | Section 16.4, Section 19.1 |
| OPA (Open Policy Agent) | Policy engine for RBAC/compliance/placement constraints | Section 12.3, Section 16.2 |
| Kyverno | Kubernetes-native admission policy enforcement | Section 16.6, Section 28.3 |
| Longhorn | Evaluated as a lightweight distributed block-storage option | Evaluated for edge/smaller-footprint deployments where a full Ceph cluster is disproportionate; not the primary block-storage backend for core regions, which use the Ceph-based system described in Section 15 |
| Velero | Kubernetes backup/restore tooling | Used for backing up Kubernetes-object-level cluster state (as distinct from the platform's own workload-level checkpointing described in Section 11.4, which is a purpose-built system, not Velero-based) |

