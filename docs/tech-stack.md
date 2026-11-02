# CNCP Technology Stack

This split follows the architecture documents, especially Appendix D of
`ciago_cncp_architecture.md` and the repository structure in Part 6.

## Language responsibilities

- **Rust**: native desktop runtime, local execution, session compositor, and
  latency-sensitive scheduling or control-plane libraries.
- **Go**: most control-plane services, gateway/signaling services, Kubernetes
  integrations, operators, and the `cncp` CLI.
- **TypeScript**: admin console, dashboard, developer portal, and other
  browser-facing Cloud OS surfaces.
- **Python**: AI orchestration and advisor services using LangGraph, Mem0, and
  model-serving integrations.
- **C++**: narrowly scoped GPU/video codec adapters only where vendor SDKs do
  not have mature Rust or Go bindings. Keep this behind a stable FFI boundary.

## Platform choices

- **Kubernetes + KubeVirt** for container and VM orchestration.
- **Firecracker/Kata Containers** for workload isolation where appropriate.
- **PostgreSQL** for transactions and **ClickHouse** for telemetry/analytics.
- **NATS** for control-plane events and **Kafka** for high-volume billing and
  telemetry streams.
- **Temporal** for durable provisioning, migration, and billing workflows.
- **Cilium/eBPF + Envoy** for networking, policy, and gateway/mesh traffic.
- **OpenTelemetry + Prometheus/Grafana/Loki/Tempo** for observability.
- **OpenTofu + Crossplane + Argo CD** for infrastructure and GitOps.

The initial implementation should keep the language count deliberately small:
Rust, Go, TypeScript, and Python. C++ should be introduced only behind a
measured hardware-integration need.
