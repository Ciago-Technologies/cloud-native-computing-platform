# Cloud Native Computing Platform (CNCP)
## Enterprise Architecture & Implementation Blueprint — Part 4
### Ciago Technologies — Confidential

**Covers:** Chapter 20 (Application Platform), Chapter 21 (Cloud Gaming), Chapter 22 (Creative Workstations), Chapter 23 (Workspace Virtualization), Chapter 24 (Personal Cloud)

**Continuity note:** Part 4 of a multi-part master blueprint. Parts 1-3 covered Chapters 1-18, 25-26. See Part 1 for the Document Delivery Plan.

---

# Chapter 20 — Application Platform

## 20.1 Application Classes & Universal Runtime

CNCP must run software that was never written with CNCP in mind — this is the "Universal Runtime" requirement from the original brief. The platform supports five distinct application delivery mechanisms, unified under one App Center (Ch.10.1) and one manifest schema (extending the format introduced in Ch.11.1):

| Class | Delivery Mechanism | Execution Locus |
|---|---|---|
| **Native local apps** | Platform-native packages (`.exe`/`.dmg`/`.deb`/Flatpak) installed on the host OS by the client agent | Local (or hybrid, per Ch.11) |
| **Container apps** | OCI images, run in the user's Kubernetes namespace (Ch.13/18) | Cloud (containers are inherently cloud-plane, by definition of the compute substrate, Ch.13.1) |
| **Web apps / PWA** | Standard web delivery, optionally wrapped for desktop-app-like presentation in the Cloud OS shell | Local browser engine, or cloud-rendered if the client device has no capable browser engine (rare edge case, e.g., extremely constrained embedded clients) |
| **Streamed VM/microVM apps** | Full OS-level app running inside a KubeVirt VM or Firecracker microVM (Ch.13), streamed via the Ch.14 transport | Cloud-only |
| **WebAssembly modules** | WASM/WASI-compliant modules, for lightweight sandboxed execution (plugins, Ch.20.4; some Marketplace content, Part 5) | Local (via a WASM runtime embedded in the client) or cloud, portable either way — this is precisely WASM's value proposition for CNCP |

## 20.2 Windows/Linux/macOS/Android Compatibility

This section makes explicit, deliberate scoping decisions, because "run everything everywhere" is not honestly achievable and claiming otherwise would set the platform up to fail its own trust commitments (Ch.2.2).

| Target | Mechanism | Fidelity |
|---|---|---|
| Windows apps on a Windows client | Native execution | Full |
| Windows apps on a macOS/Linux client, or cloud-streamed regardless of client OS | Cloud-hosted Windows VM (KubeVirt, licensed Windows guest OS — a real commercial licensing cost line item, flagged explicitly for the cost model in Part 7) streamed via Ch.14 | Full fidelity, at the cost of a Windows guest OS license and the latency/bandwidth budget of streaming |
| Linux apps on a Linux client | Native execution | Full |
| Linux apps on Windows/macOS clients | Cloud-hosted Linux VM/container streamed, OR local execution via WSL2 (Windows)/Linux VM (macOS) where the client agent detects and can leverage those — offered as a *faster, free* local alternative to cloud streaming when available, which is a direct instance of the Scheduler's local-preference logic (Ch.12.4) | Full fidelity either path |
| macOS compatibility | **Explicitly NOT full macOS app execution on non-Apple hardware** — Apple's software license terms restrict virtualizing macOS to Apple hardware. CNCP's "macOS compatibility" claim is therefore scoped to: (a) native execution on macOS clients, and (b) cloud-hosted macOS sessions run on Apple-silicon datacenter hardware (e.g., colocated Mac minis/Mac Pros — a real, distinct hardware SKU CNCP must operationally support, unlike the otherwise-uniform x86/ARM Linux fleet) for macOS-specific workloads (iOS app builds, Xcode) accessed from any client | Full fidelity, but with a materially different (and more expensive, less elastic) backing infrastructure than the rest of the platform — flagged as a cost/ops outlier, not glossed over |
| Android apps | Android emulation (Waydroid or an Android Virtual Device via the Android Open Source Project emulator), hybrid-eligible per Ch.11.2 | Full fidelity for the vast majority of apps; apps requiring specific Google Play Services deep integration may need Google-certified emulation options, a separate licensing consideration |

**Assumption stated explicitly**: the macOS-on-non-Apple-hardware limitation above is a real legal constraint (Apple's SLA), not an engineering choice, and must not be represented in product marketing as "run macOS apps anywhere" without this caveat.

## 20.3 App Store / Package Manager (Cloud Package Manager, Ch.13 of original brief numbering)

```
┌────────────────────────────────────────────────────────────────┐
│                    CNCP Package Manager (`cncp install <pkg>`)   │
└──────────┬─────────────┬──────────────┬─────────────┬──────────┘
           ▼             ▼              ▼             ▼
   Native app       Container/K8s   Infrastructure   AI model
   packages         stack (Helm     stack (Chapter    packages
   (wraps existing  chart / Helm    19 IaC Marketplace,(Ollama/
   OS package       release)        Part 5)            HuggingFace-
   managers:                                            format,
   winget/brew/apt) 	                                  routed via
                                                          Ch.17 model
                                                          routing)
```

**Build vs Adopt decision**: CNCP does **not** build a new package format or a new package manager engine from scratch. Instead, `cncp install` is a **unified CLI front-end** that dispatches to the correct existing, mature package manager per package class:
- Native apps → wraps `winget` (Windows), `brew` (macOS), `apt`/Flatpak (Linux) — CNCP maintains a curated, moderated catalog *metadata* layer (which packages are known-good, their manifest data per Ch.11.1) on top of these, rather than re-implementing package installation.
- Container/K8s stacks → Helm (the de facto standard Kubernetes package format) — `cncp install` is effectively `helm install` with CNCP-specific defaults and marketplace integration (Part 5).
- Infrastructure stacks → OpenTofu modules / Crossplane compositions (Chapter 19 IaC Marketplace, Part 5).

This "unify, don't replace" approach is the single most important Build vs Adopt decision in the Application Platform chapter, since building a competing package manager format would fragment the ecosystem CNCP depends on and create massive ongoing maintenance burden with no user-facing benefit over wrapping the existing, trusted tools.

## 20.4 Plugin Architecture

Plugins extend: scheduler (custom scoring inputs, Ch.12.4), storage (custom lifecycle policies), networking, AI (custom advisor skills, Ch.17.4), monitoring, security, marketplace, billing, UI, developer tools. All plugins execute in a **WASM sandbox** (20.1) regardless of extension point, for a uniform security model — a UI plugin and a scheduler-input plugin have wildly different privilege needs, but both run inside the same capability-scoped WASM runtime, with the *capabilities granted* (not the *isolation mechanism*) differing per extension point. This is a deliberate simplification: one sandboxing technology, many capability profiles, rather than a different isolation mechanism per plugin type.

| Extension Point | Granted Capabilities (example) | Denied by Default |
|---|---|---|
| Scheduler input plugin | Read-only telemetry access, write to a scoped "custom signal" channel feeding Ch.12.2 | No direct placement override |
| UI plugin | DOM-scoped rendering within a plugin panel | No access to other apps' windows/data |
| AI advisor skill plugin | Read access to declared data sources, LangGraph tool registration (Ch.17.2) | No unscoped filesystem/network access |
| Billing plugin | Read-only metering data access for custom dashboards | No write access to billing records |

## 20.5 Build vs Adopt vs Modify — Application Platform

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Native package dispatch | ✅ (thin dispatcher + catalog metadata) | ✅ (winget/brew/apt/Flatpak as the actual installers) | — | Do not replace mature, trusted OS package managers |
| Container package format | ❌ | ✅ Helm | ✅ (CNCP defaults/marketplace UX layer) | Kubernetes ecosystem standard |
| Plugin sandbox runtime | ❌ | ✅ (a WASM runtime, e.g., Wasmtime) | ✅ (CNCP capability-grant layer) | Mature, secure-by-design sandboxing technology; the capability model is CNCP-specific |
| Android emulation | ❌ | ✅ Waydroid / AOSP emulator | Partial (scheduler/hybrid integration) | Mature existing emulation projects |
| WSL2/local-Linux-on-Windows integration | ❌ | ✅ (Microsoft's WSL2) | ❌ | Reuse the OS vendor's own solution rather than duplicating it |

## 20.6 Testing Matrix — Application Platform

| Feature | Local | Docker/Kind | Staging | Production |
|---|---|---|---|---|
| Native package install/uninstall (all 3 OSes) | ✅ (per-OS CI runners) | N/A | ✅ | ✅ |
| Helm-based container app install | N/A | ✅ | ✅ | ✅ |
| WASM plugin sandbox capability enforcement | ✅ (unit tests, adversarial capability-escape attempts) | ✅ | ✅ | ✅ (continuous) |
| Windows-app-on-cloud-VM streaming | N/A | N/A | ✅ (requires licensed Windows guest) | ✅ |

---

# Chapter 21 — Cloud Gaming

## 21.1 Positioning vs. Incumbents (Cross-reference Ch.5)

Unlike GeForce NOW/Xbox Cloud Gaming/Amazon Luna, CNCP's gaming sessions run on the **same underlying compute substrate, transport, and Scheduler** as every other workload class (Ch.13/14/12) rather than a dedicated, separately-engineered gaming stack. This is both an efficiency argument (one substrate to operate, not two) and a product argument (a game session and a creative-app session can, in principle, share GPU pool capacity planning, Ch.13.4).

## 21.2 Gaming-Specific Requirements Beyond General Hybrid Execution

| Requirement | Design Response |
|---|---|
| Controller support (gamepad, racing wheel, HOTAS) | Raw HID input forwarded over the low-latency WebRTC DataChannel (Ch.14.3) with device descriptor negotiation at session start so the cloud-side virtual input device matches the physical controller's capability |
| Sub-frame input latency budget | Gaming sessions get the tightest scheduler placement constraint — nearest-region-only candidate set (no cross-region fallback for gaming, unlike other workload classes where a slightly-further region might be acceptable) |
| Anti-cheat compatibility | Kernel-level anti-cheat systems (common in competitive titles) require the guest VM to present as a "normal" gaming PC to the anti-cheat driver — achieved via full VM (KubeVirt with GPU passthrough, not a container), since anti-cheat systems are broadly hostile to containerized/virtualized environments that don't look like consumer hardware; this is a real constraint that rules out the lighter-weight Firecracker microVM path (Ch.13.1) for anti-cheat-protected titles specifically |
| Cloud saves | Standard Distributed Filesystem (Ch.15b) integration — game save data is just another file class, no special-cased storage system needed |
| Regional GPU clusters sized for gaming's peak-concurrency pattern (evening/weekend spikes, very different from developer-platform's business-hours pattern) | Capacity planning must model gaming and developer/creative workloads as separate demand curves feeding the same shared pool (Ch.13.4), with gaming's spikier pattern informing reserved-vs-burst capacity ratios (Part 7 cost model) |

## 21.3 Session Architecture

```
┌──────────┐                  ┌──────────────────────┐
│  Client   │◄── WebRTC (AV1/  │  KubeVirt VM, GPU        │
│  (gamepad │    H.264, gaming-│  passthrough, vGPU        │
│   input)  │    tuned encoder │  profile sized for the    │
│           │    settings) ────│  specific title's min-spec│
└──────────┘                  │  Anti-cheat-compatible     │
                                │  full-VM isolation         │
                                └──────────────────────┘
```

- **Encoder settings tuned differently from creative-app streaming** (Ch.14.4): gaming prioritizes low latency over maximum visual fidelity at the margin (lower encoder complexity preset, smaller GOP size) versus a creative app like DaVinci Resolve's color-grading view, which can tolerate a few extra milliseconds of encode latency in exchange for better visual fidelity for color-critical work. This is a per-session-type encoder profile, not a platform-wide constant.

## 21.4 Multiplayer & Voice Chat

Multiplayer networking (game-to-game-server traffic) is **not** proxied through CNCP's transport layer — the cloud-hosted game VM connects directly to the game's own multiplayer infrastructure (the publisher's servers) exactly as a normal gaming PC would, since CNCP's session is, from the game's perspective, just a very well-connected gaming PC sitting in a datacenter. Voice chat is likewise handled by the game/platform's own voice system (or a CNCP-provided voice channel over the same WebRTC infrastructure, Ch.14.3, for CNCP-native multiplayer features if built later) — CNCP does not intermediate third-party game-network traffic, both because doing so would add latency for no benefit and because it isn't CNCP's traffic to intermediate.

## 21.5 Mods

Mod support follows the standard local filesystem convention of each game (mods typically live in a game's install directory or a documented mod folder) — since the game itself runs in a full VM (21.2), mod installation works exactly as it would on a physical gaming PC, with the Distributed Filesystem (Ch.15b) providing the persistence layer so mods survive VM rescheduling (the VM's mod-containing disk volume is a Ceph RBD volume, Ch.15.1, reattached on reschedule, not baked into an ephemeral VM image).

## 21.6 Build vs Adopt vs Modify — Cloud Gaming

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Game session VM substrate | ❌ | ✅ (same KubeVirt substrate as Ch.13) | ✅ (gaming-specific vGPU profiles) | Reuse the general compute substrate rather than a parallel gaming-only stack |
| Streaming transport | ❌ | ✅ (same WebRTC substrate as Ch.14) | ✅ (gaming-tuned encoder presets) | Same reasoning — one transport layer, profile-tuned |
| Controller input forwarding | ✅ | Adopt (`libusb`/platform HID APIs for capture) | — | The forwarding protocol/negotiation is CNCP-specific; low-level HID capture uses existing OS APIs |
| Anti-cheat compatibility engineering | ✅ (integration/validation work per title, ongoing) | — | — | Inherently case-by-case, cannot be "adopted" from elsewhere; this is real, ongoing operational effort worth flagging as a resourcing line item (Part 7) |

## 21.7 Testing Matrix — Cloud Gaming

| Feature | Local | Kind (VM sim) | Staging (real GPU) | Production |
|---|---|---|---|---|
| Input latency (controller round-trip) | ⚠️ needs real GPU node, not fully local-testable | N/A | ✅ (instrumented latency measurement rig) | ✅ (continuous synthetic probes) |
| Anti-cheat compatibility per title | N/A | N/A | ✅ (title-by-title validation suite) | ✅ (regression suite on title updates) |
| Adaptive bitrate under contested network | ✅ (`netem`) | N/A | ✅ | Monitored |

---

# Chapter 22 — Creative Workstations

## 22.1 Supported Application Classes

Blender, Adobe Suite, Autodesk (Maya/3ds Max/AutoCAD), CAD tools, video editing (DaVinci Resolve, Premiere), music production (DAWs — Ableton, Logic, FL Studio), AI image/video generation tooling, simulation software, architecture/engineering (Revit, ArchiCAD), medical imaging viewers.

## 22.2 GPU Allocation Strategy for Creative Workloads

Unlike gaming (Ch.21, fixed-title min-spec, latency-dominant) and ML training (Part 3-adjacent, throughput-dominant, batch-tolerant), creative workstation GPU needs are **bursty and fidelity-dominant**: a Blender viewport session needs modest GPU most of the time but a large burst for final render; a DaVinci Resolve session needs sustained but moderate GPU for playback/color, with occasional heavy bursts for export.

| App Category | Steady-State GPU Need | Burst Pattern | Placement Strategy |
|---|---|---|---|
| Blender (viewport) | Low-mid (vGPU/MIG slice sufficient) | High, short (final render) — candidate for a **separate render-farm burst request** distinct from the interactive session (see 22.3) | Interactive: hybrid, local-capable on mid GPUs. Render burst: always cloud-offloaded to a batch-oriented GPU pool, decoupled from the interactive session's own GPU allocation |
| DaVinci Resolve (color/edit) | Mid-high sustained | Moderate (export) | Cloud, dedicated vGPU slice for the session duration (color-critical work is latency- and consistency-sensitive, less tolerant of the shared/time-sliced allocation used for lower-tier workloads, Ch.13.4) |
| Adobe Suite (Photoshop/Premiere) | Low-mid | Moderate | Hybrid; many Adobe workflows are viable on modest local GPUs, cloud-offload primarily for large-file/complex-composite scenarios |
| AI image/video generation | High, request-shaped (inference bursts) | N/A (each generation is itself the burst) | Cloud-only, routed through the same vLLM/GPU-inference substrate as Ch.17, not a separate creative-specific inference path |

## 22.3 Render Farm Pattern (Blender/Maya/3ds Max Final Render)

Final rendering is architecturally distinct from the interactive session — it is a **batch job**, not a live migration target (Ch.11.3's live-migration mechanics don't apply; this is closer to a traditional render-farm submission):

```
Interactive Session (KubeVirt VM,           Render Farm (Kubernetes Jobs,
 vGPU slice, Ch.13.4)                        batch GPU pool, spot-priced
                                              where available)
      │  "Render" action                            │
      │──scene file (already in Ch.15b               │
      │   Distributed FS) + job spec ────────────────►│
      │                                                │  parallel frame
      │                                                │  render across N
      │                                                │  workers (K8s Job
      │                                                │  with parallelism)
      │◄────────rendered frames written to            │
      │         object storage (Ch.15), progress       │
      │         streamed back to session UI             │
```

This reuses the standard Kubernetes Job/batch primitives (adopted, not built) and the object storage tier (Ch.15) for output — no new infrastructure primitive is needed, only the CNCP-specific job-submission glue connecting the creative app's "render" action to a K8s Job spec.

## 22.4 Build vs Adopt vs Modify — Creative Workstations

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Interactive session substrate | ❌ | ✅ (same KubeVirt substrate, Ch.13) | ✅ (creative-tuned vGPU profiles) | Reuse, profile-tune |
| Render farm job submission | ✅ (glue/integration layer) | ✅ (Kubernetes Jobs/Batch API) | — | Standard batch primitive, only the app-to-job translation is CNCP-specific |
| Blender/Maya/Adobe integration | ✅ (per-app manifest + telemetry hooks, Ch.11.1) | — | — | Necessarily app-specific integration work, not adoptable |

## 22.5 Testing Matrix — Creative Workstations

| Feature | Local | Kind | Staging (real GPU) | Production |
|---|---|---|---|---|
| Interactive session GPU allocation | ⚠️ needs real GPU | ✅ (allocation logic testable without real GPU via mocked device plugin) | ✅ | ✅ |
| Render farm job submission/scaling | N/A | ✅ (K8s Job scaling logic) | ✅ (real render benchmark) | ✅ |
| Live migration mid-edit (viewport session, Ch.11.4) | N/A | ✅ (simulated) | ✅ | ✅ |

---

# Chapter 23 — Workspace Virtualization

## 23.1 Workspace-Level, Not VM-Level

This is a deliberate departure from traditional VDI (Chapter 5's competitive positioning), where the unit of virtualization is a whole VM/session. CNCP's unit is the **workspace** — a logical collection of: open browser tabs, terminal sessions, running Docker containers, K8s cluster context, application windows (local and streamed, Ch.10.2), window layout, and clipboard state — that spans *multiple underlying execution loci simultaneously* (some apps local, some cloud, per Ch.11).

## 23.2 Workspace State Model

```sql
CREATE TABLE workspace (
    id                UUID PRIMARY KEY,
    owner_account_id  UUID NOT NULL REFERENCES account(id),
    name              TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at    TIMESTAMPTZ NOT NULL
);

CREATE TABLE workspace_component (
    id                UUID PRIMARY KEY,
    workspace_id      UUID NOT NULL REFERENCES workspace(id),
    component_type    TEXT NOT NULL CHECK (component_type IN
                        ('browser_tab','terminal_session','container','k8s_context',
                         'app_window','clipboard_state')),
    execution_locus   TEXT NOT NULL CHECK (execution_locus IN ('local','cloud')),
    state_ref         JSONB NOT NULL,   -- component-specific state payload/pointer
    window_geometry   JSONB,            -- position/size for app_window/browser_tab types
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workspace_component_workspace ON workspace_component(workspace_id);
```

This extends (does not duplicate) the Workspace Snapshot schema previewed in Chapter 10.4 — a `workspace_snapshot` is a versioned, point-in-time capture of a `workspace`'s `workspace_component` rows; the live `workspace` tables above are the always-current state, and snapshots are immutable copies taken on demand or on a schedule.

## 23.3 Versioning, Branching, Sharing

- **Versioning**: every snapshot (Ch.10.4) is an immutable version; a workspace's history is the ordered list of its snapshots, browsable like a version-control log.
- **Branching**: a user can create a new workspace *from* a specific snapshot without disturbing the original — implemented as a manifest copy-on-write (the new workspace's `workspace_component` rows are seeded from the snapshot's manifest, but the underlying file content reference (Ch.15b content-addressing) is only actually duplicated in storage if/when it diverges, i.e., true copy-on-write at the content layer, not a naive full copy).
- **Sharing**: a workspace (or a specific snapshot) can be shared read-only or fork-only with another account/org member, subject to the same RBAC model as other resources (Ch.16.2), with shared workspaces never granting the recipient direct access to the owner's other private workspaces or personal cloud resources — sharing is scoped strictly to the shared object.

## 23.4 Build vs Adopt vs Modify — Workspace Virtualization

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Workspace state model & snapshot engine | ✅ | Adopt substrate (Postgres, Ch.15b content-addressing) | — | No existing OSS project models "workspace" at this granularity (spanning local+cloud, multiple component types); this is core CNCP product surface |
| Copy-on-write branching | ✅ (orchestration logic) | ✅ (content-addressed storage primitives already adopted, Ch.15b) | — | The COW *mechanism* relies on existing content-addressing; the branching *semantics* are CNCP product logic |

## 23.5 Testing Matrix — Workspace Virtualization

| Feature | Local | Kind | Staging | Production |
|---|---|---|---|---|
| Snapshot/restore round-trip fidelity | ✅ | ✅ | ✅ (real multi-app workspace test suite) | ✅ |
| Branching correctness (COW, no cross-branch mutation) | ✅ | ✅ | ✅ | ✅ |
| Sharing RBAC boundary enforcement | ✅ | ✅ | ✅ (adversarial: attempt to access unshared sibling workspace) | ✅ (continuous) |

---

# Chapter 24 — Personal Cloud

## 24.1 What Every Account Gets

Per the original brief, every user receives a complete private cloud: storage, compute, GPU (on-demand, metered), databases, AI, secrets, networking, containers, Kubernetes, identity, billing — **all of these are compositions of subsystems already specified in Parts 1-3**, not new infrastructure. The Personal Cloud chapter's job is to define the **provisioning boundary and isolation guarantees**, not reintroduce new technology.

## 24.2 Personal Cloud = Tenant Boundary

```
┌───────────────────────────────────────────────────────────────┐
│                     Account (Personal Cloud)                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ K8s namespace │ │ Postgres      │ │ MinIO bucket  │  (Ch.18.1  │
│  │ (Ch.13, RBAC  │ │ instance      │ │ + IAM policy  │   pattern, │
│  │  scoped,      │ │ (CNPG)        │ │ (Ch.15)       │   same     │
│  │  Ch.16.2)     │ │               │ │               │   provisioning│
│  └──────────────┘ └──────────────┘ └──────────────┘   orchestrator)│
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ OpenBao        │ │ Metered GPU   │ │ Digital Twin  │            │
│  │ secrets path   │ │ allocation    │ │ manifest      │            │
│  │ (Ch.16.4)      │ │ (Ch.13.4,     │ │ (Ch.26)       │            │
│  │                │ │  billed via   │ │               │            │
│  │                │ │  Ch.7 FR-BILL)│ │               │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└───────────────────────────────────────────────────────────────┘
```

The Personal Cloud is, precisely, the **tenant boundary** referenced throughout Parts 1-3 (Ch.16.2 RBAC, Ch.16.1 cross-tenant isolation threat model, Ch.25.5 memory scope isolation) — every isolation guarantee already specified for "an account" or "a tenant" in prior chapters *is* the Personal Cloud's isolation guarantee. This chapter does not introduce new isolation mechanisms; it names and consolidates the ones already built.

## 24.3 Provisioning Reuses Chapter 18.1's Orchestrator

The same Temporal-based onboarding workflow (Chapter 18.1) that provisions a *developer's* environment is the general-purpose Personal Cloud provisioning workflow — a non-developer consumer account provisions a strict subset of the same components (storage + AI + identity, without necessarily a Kubernetes namespace being user-visible, though it may still exist under the hood for platform-internal reasons like running the user's cloud-executed apps per Ch.13). This reuse is deliberate: one provisioning orchestrator, parameterized by account tier, rather than a separate "consumer provisioning" and "developer provisioning" system.

## 24.4 Free-Tier / Zero-Configuration Guarantee (FR cross-reference)

Ties directly to Chapter 7's "Zero Configuration Cloud" requirement from the original brief: a non-technical user never sees VPC/networking/certificate/load-balancer/Kubernetes concepts. This is achieved architecturally, not just via UI hiding — the provisioning orchestrator (24.3) makes all networking/certificate/ingress decisions using platform-wide sane defaults (a per-account subdomain with automatic TLS via a certificate automation tool, e.g., cert-manager, adopted rather than built) with **no user-facing control surface for these concerns at all** in the default experience; they only become visible/editable when the user explicitly enables "Developer Mode" or "Infrastructure Mode" (Ch.10.1), which is the deliberate escape hatch for the minority of users (Marcus, Dr. Chen personas, Ch.6) who do want that control.

## 24.5 Build vs Adopt vs Modify — Personal Cloud

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Tenant provisioning orchestration | ✅ (reuses Ch.18.1) | Adopt substrate (Temporal) | — | Already covered; Personal Cloud is a naming/consolidation chapter, not a new build |
| TLS/certificate automation | ❌ | ✅ (cert-manager) | ❌ | Solved problem, mature CNCF project |
| Per-account subdomain routing | ✅ (thin) | ✅ (ingress controller, e.g., built on the same Cilium/Envoy substrate as Ch.14) | — | Standard pattern on top of adopted ingress tooling |

## 24.6 Testing Matrix — Personal Cloud

| Feature | Local | Kind | Staging | Production |
|---|---|---|---|---|
| Zero-config provisioning (consumer tier) | ✅ | ✅ | ✅ (end-to-end new-account timing test against the 60s SLA) | ✅ (continuous SLO monitoring) |
| Tenant isolation (cross-account access attempts) | ✅ | ✅ | ✅ (adversarial suite, shared with Ch.16.8) | ✅ (continuous) |
| Developer-Mode escape hatch reveals correct underlying resources | ✅ | ✅ | ✅ | ✅ |

---

## End of Part 4

Part 4 has covered the Application Platform (Chapter 20 — universal runtime with explicit, honest scoping of macOS/Windows/Android compatibility limits, and the "unify don't replace" package manager decision), Cloud Gaming (Chapter 21 — built on the *same* substrate as every other workload class, with gaming-specific profile tuning rather than a parallel stack), Creative Workstations (Chapter 22 — the interactive-session-vs-render-farm distinction), Workspace Virtualization (Chapter 23 — the workspace-not-VM unit of virtualization, with COW branching), and Personal Cloud (Chapter 24 — explicitly framed as the consolidation of tenant-boundary guarantees already established in earlier chapters, not new infrastructure).

**Next:** Part 5 will cover the Marketplace ecosystem (App/AI Agent/GPU/Infrastructure-as-Code marketplaces), Billing, and Multi-Tenancy.

Reply **"continue with Part 5"** to proceed.
