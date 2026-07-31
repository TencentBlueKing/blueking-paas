## Context

You are working on `bkpaas-app-operator`, a Go/Kubebuilder operator that manages BlueKing PaaS applications on Kubernetes.

`README.md` is the source of truth for development workflow, error handling, log levels and Kubebuilder background. Read it instead of guessing, and do not duplicate its content here.

Before changing code, inspect the surrounding implementation and tests. Prefer the smallest change that follows existing patterns over introducing a new abstraction.

## Project layout

- `api/v1alpha1`, `api/v1alpha2`: CRD types, conversion, defaulting and validation webhooks.
- `controllers/`: top-level controllers; `controllers/base` defines the shared `Reconciler` interface and the `Result` requeue/abort helpers.
- `pkg/controllers/bkapp`, `pkg/controllers/dgroupmapping`: domain reconciliation logic and Kubernetes resource builders.
- `pkg/kubeutil`, `pkg/health`, `pkg/metrics`: shared Kubernetes, health and metrics helpers.
- `pkg/config`, `pkg/platform`, `pkg/components`: runtime configuration and platform integrations.
- `pkg/utils/{hash,quota,stringx}`: small generic helpers. Look here before writing a new utility.
- `pkg/testing`: shared test fixtures (`bkapp.go`, `config.go`).
- `config/`: generated CRDs/RBAC/webhooks plus deployment overlays and samples.
- `hack/`, `scripts/`: generation boilerplate and helm-chart update script. `bin/`: locally installed dev tools (git-ignored).
- `main.go`: manager setup, schemes, controllers, webhooks, health checks and process wiring.

## Working principles

- Understand the reconciliation path before editing: API type or event -> top-level controller -> reconciler -> resource builder or Kubernetes client -> status update.
- Keep top-level controllers thin; domain reconciliation and resource construction belong in `pkg/controllers/`.
- Keep reconcilers idempotent and deterministic. Repeated reconciliation of unchanged input must not cause writes, restarts or event loops.
- Distinguish expected lifecycle states such as `NotFound` from real failures. Requeue deliberately; never sleep inside reconciliation.
- Set ownership, labels and annotations consistently with nearby resource builders. Deep-copy objects fetched from the shared cache before mutating them.
- Update status only when its semantic value changes, and keep status mutations separate from spec/resource mutations where practical.
- CRD fields, defaults, validation rules, conditions, phases, reasons, annotations and finalizers are externally observable interfaces. Do not change them incidentally.

## Go conventions

- Every new `.go` file needs the license header from `hack/boilerplate.go.txt`; `make generate` only adds it to generated files.
- `revive`'s `exported` rule is enabled (`.golangci.yaml`), so exported types and functions require a doc comment starting with the symbol name. Other comments should explain non-obvious intent rather than restate code.
- `make fmt` runs `golines -m 119` plus `gofumpt`, so keep lines within 119 characters.
- Follow the error conventions in README's "项目 Error 使用指南": `github.com/pkg/errors` everywhere, and no extra `WithStack` on errors returned by the traced client in `pkg/kubeutil`.
- Follow the log-level conventions in README's "选择日志级别": default level `0` for normal events, `V(1)` for frequent debug details. Log from the context logger and include namespace, name and kind. Never log secrets or credentials.

## API compatibility

- `v1alpha2` is the hub and storage version (`// +kubebuilder:storageversion` and `Hub()` in `api/v1alpha2/bkapp_types.go`). Add new fields there first.
- `api/v1alpha1/bkapp_conversion.go` implements `ConvertTo`/`ConvertFrom`. Any field change must be checked for round-trip loss between served versions, with a conversion test.
- When adding or changing a field, review JSON tags, optionality, zero-value behavior, Kubebuilder markers, deep-copy generation and both API versions.
- Do not silently change defaults or reject previously valid stored objects. Keep defaulting and validation in the webhooks instead of duplicating the logic in reconcilers, and make validation errors actionable and stable.

## Tests

- Tests live beside source files and use Ginkgo/Gomega. Add or update tests for every behavior change; a regression test must fail before the fix and pass after it.
- Prefer package-level tests. `controllers/`, `api/v1alpha1` and `api/v1alpha2` suites need envtest, so use them only when behavior depends on API-server semantics or reconciliation wiring.
- Use `DescribeTable` when several inputs share behavior. Cover success, invalid input, missing resources and error paths.
- Reuse fixtures from `pkg/testing` and adjacent test files. Keep tests deterministic: no ordering assumptions, wall-clock sleeps or live cluster.
- Assert observable behavior such as generated resources, status and errors rather than internal implementation details.

## Generated files, manifests and helm chart

- Do not hand-edit `zz_generated.deepcopy.go` or generated manifests. Change source types or markers, then run `make generate` and `make manifests`, and include all resulting outputs.
- After changing CRDs, RBAC or webhooks, the helm chart must be regenerated with `make update-helm-chart HELM_CHART_TARGET_DIR=...`, and `values.yaml` still needs a manual review. The target directory lives outside this repository, so do not attempt it yourself: call it out explicitly in your summary as a follow-up for a human.
- Prefer the standard library and existing dependencies. Add one only for clear value, update `go.mod` and `go.sum` together, and run `go mod tidy` only when module requirements actually change.

## Validation

Install the dev tools once (they land in `bin/`):

```bash
make ginkgo envtest
```

Run the narrowest useful checks first. Plain `go test` works for pure unit packages, but envtest suites need `KUBEBUILDER_ASSETS`:

```bash
go test ./pkg/utils/...
KUBEBUILDER_ASSETS="$(bin/setup-envtest use 1.24.1 -p path)" bin/ginkgo ./controllers/...
make fmt
make lint
```

Before finishing API, controller or generated-resource changes, run the full suite:

```bash
make test
```

Note that `make test` depends on `manifests generate fmt vet`, so it can rewrite generated and formatted files; `make fmt` and `make build` do too. Inspect the working tree afterwards. Use `make build` when changing startup, wiring, dependencies or build behavior.

Before finishing, review `git diff` and confirm that only intended files changed, tests cover the behavior, generated artifacts are current and no temporary files remain.

Cluster-changing commands such as `make install`, `make deploy`, `make uninstall`, `make undeploy` and `make run` must not be used as routine validation. Never assume the current kube-context is safe.
