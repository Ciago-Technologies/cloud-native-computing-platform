# Cloud Native Computing Platform (CNCP)
## Enterprise Architecture & Implementation Blueprint — Part 5
### Ciago Technologies — Confidential

**Covers:** Chapter 27 (Cloud/App Marketplace), Chapter 28 (AI Agent Marketplace), Chapter 29 (GPU Marketplace), Chapter 19 (Infrastructure as Code Marketplace), Chapter 30 (Billing), Chapter 31 (Multi-Tenancy)

**Continuity note:** Part 5 of a multi-part master blueprint. Parts 1-4 covered Chapters 1-26. See Part 1 for the Document Delivery Plan.

---

# Chapter 27 — Cloud Marketplace (Applications, Templates, Plugins)

## 27.1 One Marketplace, Multiple Content Types

The original brief describes several "marketplaces" (application, AI agent, GPU, infrastructure-as-code). Architecturally these should **not** be four separate systems — they are four **content-type extensions of one Marketplace platform** (catalog, review pipeline, billing integration, reputation system), because building four independent marketplaces would quadruple the maintenance burden of listing, search, payment, and moderation infrastructure for no product benefit. This chapter (27) defines the shared Marketplace platform; Chapters 28-29 and 19 define the content-type-specific rules layered on top.

## 27.2 Marketplace Platform Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Marketplace Platform Core                       │
│  Catalog (OpenSearch, reused from Ch.25.2) │ Review Pipeline        │
│  Reputation/Rating System │ Revenue Split & Payout Engine           │
│  Content Signing/Verification (Sigstore, reused from Ch.16.7)       │
└───────┬─────────────┬─────────────┬─────────────┬─────────────────┘
        ▼             ▼             ▼             ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────────┐
│  App/Container ││  AI Agents    ││  GPU Capacity ││  IaC Templates/   │
│  Listings      ││  (Ch.28)      ││  (Ch.29)      ││  Operators (Ch.19)│
│  (Ch.20        ││                ││                ││                    │
│   integration) ││                ││                ││                    │
└──────────────┘└──────────────┘└──────────────┘└──────────────────┘
```

## 27.3 Review/Moderation Pipeline

Every listing (regardless of content type) passes through a common pipeline before publication:

```
Submission → Static Scan → Sandbox Trial Run → Human/AI-Assisted Review → Publish (staged rollout)
```

| Stage | Mechanism |
|---|---|
| Static scan | SBOM generation + vulnerability scan (Syft/Grype, reused from Ch.16.7) for any container/binary content; for AI agents (Ch.28), static analysis of declared tool/capability manifests |
| Sandbox trial run | Executed inside a Firecracker microVM (reused from Ch.13) with no network egress beyond an explicitly declared allowlist, observing actual runtime behavior against the declared manifest — catches "manifest says X, behavior does Y" mismatches before publication |
| Human/AI-assisted review | Deployment AI (Ch.17.4) risk-scores the submission; scores above a threshold require mandatory human review; all publisher-tier-1 (unverified/new publisher) content requires human review regardless of AI risk score |
| Staged rollout | New listings ship to a small percentage of eligible users first (progressive rollout, using the same pattern as Argo Rollouts-style canary deployment, adopted rather than built, Ch.9.1/18.4), with automatic halt if error/uninstall rates spike |

## 27.4 Data Model

```sql
CREATE TABLE marketplace_listing (
    id                  UUID PRIMARY KEY,
    publisher_account_id UUID NOT NULL REFERENCES account(id),
    content_type        TEXT NOT NULL CHECK (content_type IN
                          ('app','container_stack','ai_agent','gpu_offer','iac_template')),
    name                TEXT NOT NULL,
    current_version_id  UUID,
    review_status       TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN
                          ('pending','sandboxed','human_review','published','rejected','suspended')),
    risk_score          NUMERIC,               -- from Deployment AI (Ch.17.4)
    reputation_score     NUMERIC NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE marketplace_listing_version (
    id                UUID PRIMARY KEY,
    listing_id        UUID NOT NULL REFERENCES marketplace_listing(id),
    version_string    TEXT NOT NULL,
    content_ref       TEXT NOT NULL,   -- content-addressed reference (Ch.15b pattern) or OCI digest
    sbom_ref          TEXT,
    signature_ref     TEXT NOT NULL,   -- Sigstore/cosign signature reference
    published_at      TIMESTAMPTZ,
    rollout_percentage NUMERIC NOT NULL DEFAULT 0
);
```

## 27.5 Revenue Split & Payout

Standard marketplace economics — configurable platform fee (illustrative default 20-30%, consistent with industry app-store norms, exact figure a business decision outside this document's scope), payouts processed through the same PCI-scope-outsourced payment processor referenced in Chapter 16.6 (Stripe or equivalent), avoiding CNCP handling raw payment instrument data. Payout ledger entries are append-only (never mutated, only reversed via explicit compensating entries), a standard financial-integrity pattern.

## 27.6 Build vs Adopt vs Modify — Marketplace Core

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Catalog search | ❌ | ✅ OpenSearch (reused, Ch.25.2) | ✅ (marketplace-specific indices/ranking) | Avoid a third search technology; reuse |
| Sandboxed trial execution | ❌ | ✅ Firecracker (reused, Ch.13) | ✅ (trial-run harness/observability) | Reuse isolation primitive |
| Content signing | ❌ | ✅ Sigstore/cosign (reused, Ch.16.7) | ❌ | Reuse supply-chain tooling |
| Staged rollout | ❌ | ✅ (Argo Rollouts patterns, reused from Ch.18.4's Argo CD adoption) | ✅ (marketplace-specific rollout triggers) | Reuse progressive-delivery tooling |
| Review pipeline orchestration | ✅ | Adopt substrate (Temporal, reused) | — | Business-process logic, CNCP-specific |
| Payout/revenue-split engine | ✅ | Adopt substrate (payment processor) | — | Business-specific ledger logic |

## 27.7 Testing Matrix — Marketplace Core

| Feature | Local | Kind | Staging | Production |
|---|---|---|---|---|
| Review pipeline (all stages) | ✅ (mocked scan/sandbox results) | ✅ | ✅ (real malicious-submission red-team suite) | ✅ (continuous) |
| Staged rollout halt-on-regression | ✅ | ✅ | ✅ (injected regression test) | ✅ |
| Payout ledger correctness (append-only, reconciliation) | ✅ (property-based tests: no entry ever mutated) | N/A | ✅ | ✅ (audited) |

---

# Chapter 28 — AI Agent Marketplace

## 28.1 Agent Categories (Per Original Brief)

Security, DevOps, database, performance, architecture, finance, support, engineering, deployment — each maps to an "advisor skill" pattern already established in Chapter 17.4, but marketplace agents are **third-party-authored**, which changes the trust model materially from CNCP's own first-party advisor skills.

## 28.2 Execution Isolation for Third-Party Agents

Third-party AI agents run as LangGraph-registered skills (Ch.17.2/17.3) but with a **strictly reduced default capability grant** compared to first-party advisors:

| Capability | First-Party Advisor (Ch.17.4) | Third-Party Marketplace Agent (default) |
|---|---|---|
| Read access to user's own data (scoped) | Yes, per subsystem | Yes, but only to data the user explicitly grants at install time (OAuth-style consent screen, per-scope) |
| Write access | Per Ch.17.4's advisory-by-default governance | Never direct write access; all actions are proposed and require explicit user confirmation, with no exceptions (stricter than the first-party bar, since third-party code has not been through CNCP's own engineering review) |
| Cross-agent memory access | N/A | Explicitly denied — a marketplace agent cannot read another agent's memory/context, enforced by the same scope-isolation mechanism as Ch.25.5 |
| Network egress | N/A (first-party, trusted) | Declared allowlist only, enforced at the WASM/sandbox boundary (Ch.20.4 pattern, reused) |

## 28.3 Agent Manifest & Permission Model

```yaml
# ai-agent-manifest.yaml (illustrative)
agent_id: com.examplevendor.db-performance-advisor
display_name: Database Performance Advisor
category: database
requested_scopes:
  - read:workspace.postgres.query_logs
  - read:workspace.postgres.schema
declared_egress:
  - api.examplevendor.com   # for the vendor's own model inference, if not using CNCP-hosted routing (Ch.17.5)
write_capability: proposal_only   # cannot be anything else; enforced platform-side, not just declared
pricing_model: subscription | per_invocation | free
```

Note `write_capability: proposal_only` is not merely a manifest declaration the platform trusts — it is **structurally enforced** by the capability grant at the sandbox boundary (28.2/20.4), so a malicious or buggy third-party agent cannot escalate beyond proposal-only regardless of what it attempts, which is the correct security posture (never rely solely on a self-declared manifest for a security boundary).

## 28.4 Monetization Models

Subscription (recurring), per-invocation (metered, integrates with Ch.30 Billing), and free (publisher-subsidized, e.g., a vendor offering a free advisor agent to drive adoption of their own paid product). All three route through the same revenue-split engine (Ch.27.5).

## 28.5 Build vs Adopt vs Modify — AI Agent Marketplace

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Agent execution runtime | ❌ | ✅ (same LangGraph + WASM sandbox as Ch.17/20.4) | ✅ (reduced capability profile, 28.2) | Reuse, tightened for third-party trust level |
| Permission/consent UX | ✅ | — | — | Product-specific, security-critical, must be built and reviewed carefully |
| Manifest schema & enforcement | ✅ | — | — | CNCP-specific, extends Ch.11.1/20.1 manifest patterns |

## 28.6 Testing Matrix — AI Agent Marketplace

| Feature | Local | Kind | Staging | Production |
|---|---|---|---|---|
| Scope-consent enforcement | ✅ (adversarial: agent attempts undeclared scope access) | ✅ | ✅ | ✅ (continuous) |
| write_capability=proposal_only structural enforcement | ✅ (attempt direct write, assert blocked at sandbox layer, not just app layer) | ✅ | ✅ | ✅ |
| Cross-agent memory isolation | ✅ | ✅ | ✅ | ✅ |

---

# Chapter 29 — GPU Marketplace

## 29.1 Concept: Idle GPU Capacity Rental

Organizations (and eventually individuals with home-lab/workstation GPUs, subject to a separate trust tier) can offer idle GPU capacity into a shared pool, earning revenue when CNCP schedules workloads onto it, and CNCP's own workloads gain elastic burst capacity beyond owned/leased datacenter GPUs. This is explicitly **Phase 4-5** scope (Part 7 roadmap) — it introduces a materially harder trust and verification problem than CNCP's own operated infrastructure and should not be on the critical path for earlier phases.

## 29.2 Trust Tiers

| Tier | Provider Type | Verification Requirement | Workload Eligibility |
|---|---|---|---|
| Tier 0 (CNCP-operated) | CNCP's own datacenter/colocated capacity | N/A (fully trusted) | All workload classes |
| Tier 1 (Verified enterprise partner) | Data-center-grade partner with audited physical/network security (contractual + periodic audit) | Formal audit, SLA contract | Most workload classes except the highest-compliance-tier enterprise workloads (Ch.16.6) |
| Tier 2 (Verified individual/home-lab) | Individual/small business offering workstation GPU capacity | Automated hardware attestation (remote attestation, Ch.16.5-adjacent) + reputation history | Only the lowest-sensitivity workload classes (e.g., non-sensitive batch render jobs, Ch.22.3 render farm bursts) — never workloads carrying user personal data, secrets, or requiring the isolation guarantees of Ch.16.1's threat model |

**Assumption stated explicitly**: Tier 2 (home-lab) capacity is architecturally interesting but carries real risk (an untrusted physical host has far more attack surface than a CNCP-operated node — e.g., a malicious host operator with physical GPU access has meaningfully more opportunity to attempt side-channel attacks against co-located workloads or to tamper with results). This document scopes Tier 2 usage conservatively (batch/render-only, never GPU-passthrough sessions carrying sensitive session state) as the responsible default; broadening this scope would require a dedicated security review beyond this blueprint's scope.

## 29.3 Discovery, Pricing, Scheduling

```
Provider registers GPU capacity → Automated benchmark (standardized workload,
verifies claimed spec matches actual performance) → Listed in GPU Marketplace
(Ch.27 core) with tier, benchmark score, spot price →
Scheduler (Ch.12) treats marketplace capacity as an additional placement
candidate pool, filtered by workload's trust-tier requirement (29.2) →
Winning bid/allocation → Session runs → Metering (Ch.30) → Payout (Ch.27.5)
```

Pricing follows a **spot-market model** (bid/ask, similar in spirit to AWS Spot Instances — a well-understood, adoptable pattern rather than a novel auction mechanism CNCP would need to design and validate from scratch) with a CNCP-set price floor to prevent races-to-the-bottom that would undermine provider participation incentives.

## 29.4 GPU Isolation & Result Verification

For Tier 2 in particular, CNCP cannot rely on physical/hardware-level trust to the same degree as its own datacenters, so verification shifts partly to **software-level attestation and output verification**:

- Hardware attestation at registration and periodically thereafter (remote attestation techniques, Ch.16.5).
- For render/batch workloads (the primary Tier 2 use case, 29.2), optional **redundant execution with result comparison** for high-value jobs — running the same batch job on two independent providers and comparing outputs, at additional cost, offered as an opt-in verification tier for users who want it, not a default (since redundant execution doubles cost and most render jobs don't need this level of assurance).

## 29.5 Build vs Adopt vs Modify — GPU Marketplace

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Marketplace listing/catalog | ❌ | ✅ (Ch.27 core, reused) | ✅ (GPU-offer-specific fields) | Reuse marketplace platform |
| Benchmark/verification harness | ✅ | Adopt substrate (standard GPU benchmark suites, e.g., MLPerf-style benchmarks as the reference workload) | — | The harness orchestration is CNCP-specific; the benchmark workload itself can reuse established industry benchmarks rather than inventing a new one |
| Spot pricing/bidding | ✅ (business logic) | Reference AWS Spot's model (not literally adoptable code, but adoptable design pattern) | — | Pricing mechanism design is CNCP-specific, informed by well-precedented patterns |
| Remote attestation | ❌ | ✅ (TPM-based attestation tooling, Keylime or similar OSS attestation projects) | Partial (integration) | Established attestation tooling exists; don't reinvent |

## 29.6 Testing Matrix — GPU Marketplace

| Feature | Local | Kind | Staging | Production |
|---|---|---|---|---|
| Benchmark verification (claimed vs actual spec mismatch detection) | ✅ (mocked provider claims) | N/A | ✅ (real hardware test across provider tiers) | ✅ (continuous re-benchmarking) |
| Trust-tier workload filtering (Tier 2 never receives sensitive workloads) | ✅ (policy unit tests) | ✅ | ✅ (adversarial: attempt to force sensitive workload onto Tier 2) | ✅ (continuous) |
| Redundant execution result comparison | ✅ | N/A | ✅ | ✅ (opt-in feature, monitored for divergence rate) |

---

# Chapter 19 — Infrastructure as Code Marketplace

## 19.1 Content Types

Reusable infrastructure templates, Kubernetes operators, Helm charts, **OpenTofu** modules, **Crossplane** compositions, and complete application stacks with one-click deployment — this is a content-type extension of the Chapter 27 marketplace core, specifically for the "Developer Mode"/"Infrastructure Mode" audience (Ch.24.4's escape-hatch users).

## 19.2 Why OpenTofu (Not Terraform) and Crossplane

- **OpenTofu** adopted over HashiCorp Terraform specifically because of its OSS license (MPL 2.0, community-governed under the Linux Foundation) versus Terraform's post-BUSL licensing change — consistent with the platform's stated open-source-first, non-vendor-lock-in posture (Ch.2.2 data-sovereignty commitment) and directly analogous to the OpenBao-over-Vault decision already made in Chapter 16.4 for the same licensing reason. The Terraform *provider* built in Chapter 18.2 is written against the standard Terraform Plugin Protocol, which OpenTofu remains compatible with, so this is not a forked/incompatible ecosystem choice.
- **Crossplane** adopted for Kubernetes-native infrastructure composition (defining infrastructure as Kubernetes custom resources, reconciled continuously like any other K8s object) — complementary to OpenTofu/Helm rather than competing: Crossplane is the right tool when infrastructure should be *continuously reconciled* (drift-corrected automatically, GitOps-native, fitting naturally with the Argo CD adoption in Ch.18.4), whereas OpenTofu is the right tool for *plan-then-apply* workflows more familiar to traditional infra teams. Both are offered because different enterprise customers and internal use cases genuinely prefer different operational models, and forcing one onto users who prefer the other would hurt adoption for no technical reason.

## 19.3 One-Click Deployment Flow

```
User browses IaC Marketplace listing → selects "Deploy" →
CNCP resolves required inputs (parameterized template, e.g., region,
sizing tier) via a generated form (derived from the OpenTofu variables.tf /
Crossplane composition schema — auto-generated UI, not hand-built per template) →
Submits as a Kubernetes-native GitOps commit (for Crossplane compositions,
directly; for OpenTofu modules, via a CNCP-operated OpenTofu-run controller
that executes plan/apply and commits state to the user's Personal Cloud,
Ch.24) → Argo CD (Ch.18.4) reconciles → Deployed
```

This ties directly back into the Personal Cloud's zero-configuration default (Ch.24.4) — a non-expert user "one-clicking" an IaC Marketplace template never sees the underlying `.tf`/Crossplane YAML unless they explicitly enter Developer/Infrastructure Mode, even though the same template is fully inspectable/editable for users who do want that.

## 19.4 Build vs Adopt vs Modify — IaC Marketplace

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| IaC execution engines | ❌ | ✅ OpenTofu, Crossplane | ❌ | Mature, community-governed, license-aligned with platform philosophy |
| Auto-generated deployment forms | ✅ | Adopt substrate (schema-to-form generation is a fairly standard pattern; use an existing form-generation library rather than a bespoke one) | — | CNCP-specific glue over a solved sub-problem |
| OpenTofu-run controller | ✅ | Adopt substrate (similar in spirit to existing OSS "Terraform Operator" patterns, e.g., prior art from projects like `terraform-k8s` — reviewed and adapted rather than built fully from scratch) | ✅ | Some existing prior art to build from, but CNCP-specific state-handling/Personal-Cloud integration is necessarily custom |

## 19.5 Testing Matrix — IaC Marketplace

| Feature | Local | Kind | Staging | Production |
|---|---|---|---|---|
| OpenTofu plan/apply via controller | ✅ (local OpenTofu against DevStack/MicroStack per Part 6) | ✅ | ✅ | ✅ |
| Crossplane composition reconciliation | N/A | ✅ (Crossplane on Kind) | ✅ | ✅ |
| Auto-generated form correctness across varied module schemas | ✅ (schema fixture suite) | N/A | ✅ | ✅ |

---

# Chapter 30 — Billing

## 30.1 Metering Architecture

Per FR-BILL-1 (Ch.7.4): CPU-seconds, GPU-seconds (by class), GB-months storage, GB egress, all attributed and visible pre- and post-hoc with sub-60s lag (Ch.8 NFR).

```
┌────────────────────────────────────────────────────────────────┐
│                     Metering Event Sources                        │
│  K8s resource usage (Prometheus, Ch.31/Part 6) │ MinIO storage     │
│  metrics (Ch.15) │ GPU utilization (Ch.13.4 device plugins) │      │
│  Egress counters (Ch.14 gateway) │ Marketplace invocations (Ch.27) │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
                    ┌──────────────────┐
                    │  OpenMeter          │  ← adopted usage-metering
                    │  (event ingestion,   │     engine, purpose-built
                    │   aggregation,        │     for exactly this
                    │   real-time balance)  │
                    └────────┬──────────┘
                             ▼
                    ┌──────────────────┐
                    │  Billing Service     │  ← CNCP-specific: plan
                    │  (invoicing, quota    │     rules, budget ceilings,
                    │   enforcement, FinOps │     enterprise contract
                    │   dashboard)          │     terms
                    └──────────────────┘
```

## 30.2 Why OpenMeter

OpenMeter is adopted specifically because usage-based metering at CNCP's required granularity (per-second GPU billing, real-time balance for hard budget ceilings, Ch.2.2 commitment #4) is a genuinely hard, well-scoped problem that a purpose-built OSS project solves better than a bespoke implementation on top of, say, raw Prometheus aggregation — building this in-house would consume significant engineering time on a component that is not part of CNCP's differentiated value proposition (Ch.1's "spend capital on the 20% that's differentiated" principle, applied again here).

## 30.3 Budget Ceilings & Real-Time Enforcement

Hard budget ceilings (Ch.2.2 commitment #4) require metering data to flow back into the **Scheduler** (Ch.12.2's signal inputs already include "user's subscription tier / remaining quota") with low enough latency that a workload approaching its budget ceiling can be flagged *before* overrun, not just billed after the fact. This is implemented as a **soft warning at 80% of ceiling** (in-session notification, non-blocking) and a **hard stop at 100%** (workload paused/migrated to a free/local-only tier where possible, per Ch.11's local-fallback mechanics, rather than abruptly killed) — the hard-stop behavior deliberately reuses the graceful-migration mechanics of Chapter 11.4 rather than introducing a separate "kill the workload" code path, both for engineering reuse and because an abrupt kill on hitting a budget ceiling would violate the "never lose user data" reliability commitment established in Chapter 11.5.

## 30.4 Data Model

```sql
CREATE TABLE billing_plan (
    id              UUID PRIMARY KEY,
    name            TEXT NOT NULL,
    plan_type       TEXT NOT NULL CHECK (plan_type IN ('free','consumer','pro','enterprise')),
    rate_card       JSONB NOT NULL   -- per-unit rates: cpu_second, gpu_second_by_class, gb_month_storage, gb_egress
);

CREATE TABLE account_budget (
    account_id       UUID PRIMARY KEY REFERENCES account(id),
    plan_id          UUID NOT NULL REFERENCES billing_plan(id),
    period_start     DATE NOT NULL,
    period_end       DATE NOT NULL,
    ceiling_amount   NUMERIC,          -- null = no hard ceiling (e.g., enterprise contract billing)
    current_spend    NUMERIC NOT NULL DEFAULT 0,   -- kept near-real-time via OpenMeter balance queries
    warned_at_80pct  BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE metering_event (
    id              UUID PRIMARY KEY,
    account_id      UUID NOT NULL REFERENCES account(id),
    resource_type   TEXT NOT NULL,   -- cpu_second|gpu_second|storage_gb_month|egress_gb
    resource_class  TEXT,            -- e.g. gpu tier (Ch.13.4)
    quantity        NUMERIC NOT NULL,
    unit_cost       NUMERIC NOT NULL,
    workload_ref    UUID,            -- traceability to the specific workload/workspace for cost attribution (FR-SCHED-5-adjacent transparency)
    occurred_at     TIMESTAMPTZ NOT NULL
);
```

## 30.5 Reserved Capacity & Spot Pricing (FinOps)

Enterprise customers can pre-purchase reserved GPU capacity (discounted rate vs. on-demand) for predictable workloads (e.g., a studio's render farm baseline load), while burst above the reserved baseline draws from on-demand or GPU Marketplace (Ch.29) spot capacity — a standard cloud FinOps pattern (directly analogous to AWS Reserved Instances + Spot), not novel to CNCP, and the FinOps dashboard surfaces reserved-vs-on-demand-vs-spot cost breakdown to help customers optimize their own commitment level, which is a customer-trust feature (transparent cost optimization guidance) as much as a revenue feature.

## 30.6 Build vs Adopt vs Modify — Billing

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| Usage metering/aggregation | ❌ | ✅ OpenMeter | ✅ (CNCP-specific event schema/sources) | Purpose-built for this problem |
| Invoicing/payment | ❌ | ✅ (Stripe Billing or equivalent) | Partial (integration) | PCI-scope-outsourcing, established pattern (Ch.16.6) |
| Budget-ceiling enforcement logic | ✅ | Adopt substrate (OpenMeter balance API, Ch.11.4 migration mechanics) | — | CNCP-specific policy on top of adopted metering and reused migration primitives |
| FinOps dashboard | ✅ (UI/aggregation views) | Adopt substrate (data already in OpenMeter/Postgres) | — | Product-specific presentation layer |

## 30.7 Testing Matrix — Billing

| Feature | Local | Kind | Staging | Production |
|---|---|---|---|---|
| Metering accuracy (event → OpenMeter → balance) | ✅ (synthetic event injection, assert balance correctness) | ✅ | ✅ (real workload cost reconciliation against expected) | ✅ (continuous reconciliation job, alerts on drift) |
| Budget ceiling soft-warn/hard-stop | ✅ | ✅ | ✅ (real workload driven to ceiling in staging) | ✅ |
| Invoice generation correctness | ✅ | N/A | ✅ | ✅ (audited, matched against Ch.27.5 payout ledger for marketplace revenue share) |

---

# Chapter 31 — Multi-Tenancy

## 31.1 Hierarchy

```
Organization
  └── Team
        └── Project
              └── Workspace (Ch.23)
```

RBAC inherits down this hierarchy by default (an org-level "Viewer" role sees all teams/projects/workspaces read-only unless a project explicitly restricts further), with explicit override capability at each level — this reuses the same RBAC engine (Keycloak + OPA, Ch.16.2/16.3) already established platform-wide, rather than a bespoke multi-tenancy permission system.

## 31.2 Data Model

```sql
CREATE TABLE organization (
    id           UUID PRIMARY KEY,
    name         TEXT NOT NULL,
    billing_plan_id UUID NOT NULL REFERENCES billing_plan(id)
);

CREATE TABLE team (
    id              UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organization(id),
    name            TEXT NOT NULL
);

CREATE TABLE project (
    id       UUID PRIMARY KEY,
    team_id  UUID NOT NULL REFERENCES team(id),
    name     TEXT NOT NULL,
    quota_override JSONB   -- optional per-project resource quota, else inherits team/org default
);

CREATE TABLE membership (
    id             UUID PRIMARY KEY,
    account_id     UUID NOT NULL REFERENCES account(id),
    scope_type     TEXT NOT NULL CHECK (scope_type IN ('organization','team','project')),
    scope_id       UUID NOT NULL,
    role           TEXT NOT NULL,   -- resolved against Keycloak realm roles, Ch.16.2
    granted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_membership_account ON membership(account_id);
CREATE INDEX idx_membership_scope ON membership(scope_type, scope_id);
```

## 31.3 Quotas & Namespace Isolation

Every project maps to a distinct Kubernetes namespace (reusing the Ch.13/18.1 provisioning pattern) with **ResourceQuota** and **LimitRange** objects (native Kubernetes primitives, adopted not built) enforcing CPU/memory/GPU-count ceilings per project, layered under the account-level billing budget ceiling (Ch.30.3) — two independent enforcement layers (K8s resource quota for infrastructure-level protection against runaway consumption regardless of billing state, and billing budget ceiling for cost control) deliberately kept separate, since a project could theoretically be within its billing budget but still need a hard resource ceiling to protect cluster-wide fairness against other tenants (noisy-neighbor protection), which is a distinct concern from cost.

## 31.4 Policy Enforcement (Org-Level Constraints)

Org admins can set policies (data residency, Ch.16.6 GDPR-relevant; allowed marketplace content tiers, Ch.27; mandatory self-hosted-only AI routing, Ch.17.5) that apply across all teams/projects/workspaces in the org, enforced via the same OPA policy engine referenced throughout (Ch.12.6, 16, 17.6) — this is the single most repeated architectural pattern in this document and is worth stating explicitly here: **CNCP has exactly one policy engine (OPA), used for scheduler placement constraints, security access control, AI action governance, and multi-tenant org policy.** This consolidation is a deliberate design principle, not a coincidence — a platform with N different policy/rules engines for N different subsystems would be both harder to audit (compliance teams would need to understand N systems) and harder to reason about for correctness (policy conflicts across systems are a real source of security bugs).

## 31.5 Build vs Adopt vs Modify — Multi-Tenancy

| Component | Build | Adopt | Modify | Reasoning |
|---|---|---|---|---|
| RBAC engine | ❌ | ✅ (Keycloak + OPA, reused throughout) | ✅ (org/team/project/workspace-specific policies) | Consolidation principle (31.4) |
| Namespace/quota enforcement | ❌ | ✅ (native K8s ResourceQuota/LimitRange) | ❌ | Solved problem |
| Org/team/project hierarchy model | ✅ | Adopt substrate (Postgres) | — | CNCP-specific business/product hierarchy |

## 31.6 Testing Matrix — Multi-Tenancy

| Feature | Local | Kind | Staging | Production |
|---|---|---|---|---|
| RBAC inheritance correctness across hierarchy | ✅ | ✅ | ✅ (permission-matrix regression suite) | ✅ (continuous) |
| Quota enforcement (resource ceiling independent of billing state) | ✅ | ✅ (real ResourceQuota tests) | ✅ | ✅ |
| Org policy propagation (data residency, marketplace restrictions) | ✅ | ✅ | ✅ | ✅ (continuous compliance audit) |

---

## End of Part 5

Part 5 has covered the Marketplace ecosystem as a single platform (Chapter 27) with four content-type extensions — Applications (27, tied to Ch.20), AI Agents (Chapter 28, with a structurally-enforced, stricter-than-first-party trust model), GPU capacity (Chapter 29, with explicit trust tiers and a conservative default scope for untrusted home-lab capacity), and Infrastructure-as-Code (Chapter 19, OpenTofu + Crossplane, chosen partly for license alignment with the platform's OpenBao precedent) — followed by Billing (Chapter 30, OpenMeter-based metering with budget-ceiling enforcement that reuses the Hybrid Execution Engine's graceful-migration mechanics rather than a separate kill-path) and Multi-Tenancy (Chapter 31, which makes explicit the one-policy-engine consolidation principle running throughout the entire document).

**Next:** Part 6 will cover the full Open Source Technology Stack matrix (consolidating every adoption decision made across Parts 1-5 into one reference table), the Local Development Environment (Docker Compose/Kind-based, 100% free), Testing Strategy, and Repository Structure.

Reply **"continue with Part 6"** to proceed.
