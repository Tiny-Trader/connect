# Plugin Architecture Plan (Core + Broker Extensions)

This document proposes a package split to keep `tt-connect` lean and elegant:

- Keep a small, stable core engine in `tt-connect`
- Move broker-specific integrations into separate extension packages
- Support optional convenience installs such as `tt-connect[angel,zerodha]`

The goal is lower bloat, clearer ownership, and additive extensibility.

## Why This Split

A single package that includes all brokers tends to grow into:
- heavier dependency graph
- wider test surface for every change
- frequent core releases for broker-only changes
- abstraction leaks from broker specifics into core APIs

Core + plugins reduces this by isolating broker code into separately versioned
packages while preserving one canonical API for users.

## Target Model

## 1) Core Package: `tt-connect`

Core should contain only broker-agnostic components:

- Canonical public API and lifecycle
- Domain models and enums
- Exception hierarchy
- Capability and contract interfaces
- Instrument manager + resolver
- Plugin discovery/registry

Core should not contain:
- broker auth logic
- broker REST endpoints
- broker parsers/transformers
- broker websocket implementations

## 2) Broker Plugin Packages

Create one package per broker:

- `tt-connect-zerodha`
- `tt-connect-angel`

Each plugin contains:
- adapter implementation
- auth implementation
- transformer
- instrument parser
- optional broker websocket adapter

Each plugin registers itself with core through entry points.

## Install UX Options

## Preferred explicit installs

```bash
pip install tt-connect
pip install tt-connect-zerodha
```

Pros:
- explicit dependency ownership
- clearer production bill of materials

## Convenience extras on core (optional)

```bash
pip install "tt-connect[zerodha]"
pip install "tt-connect[angel,zerodha]"
pip install "tt-connect[all]"
```

Here extras in core only point to plugin wheels; broker code still lives outside
core.

This means bracket notation is fully supported for:
- single broker extra
- multiple broker extras (comma-separated)
- all brokers via a dedicated `all` extra

## Technical Design

## 1) Entry point based broker registration

Use Python package entry points to avoid import side effects.

Core discovery:

```python
# tt_connect/plugin_loader.py
from importlib.metadata import entry_points
from tt_connect.adapters.base import BrokerAdapter

def load_broker_plugins() -> dict[str, type[BrokerAdapter]]:
    registry: dict[str, type[BrokerAdapter]] = {}
    eps = entry_points(group="tt_connect.brokers")
    for ep in eps:
        adapter_cls = ep.load()
        registry[ep.name] = adapter_cls
    return registry
```

Plugin declaration example:

```toml
# tt-connect-zerodha pyproject.toml
[project.entry-points."tt_connect.brokers"]
zerodha = "tt_connect_zerodha.adapter:ZerodhaAdapter"
```

Benefits:
- deterministic registration
- no hidden import magic
- plugins are optional and independently installable

## 2) Core adapter contract stays strict

Core defines typed interfaces/protocols only:

- `BrokerAdapter` abstract contract
- `Transformer` protocol
- auth/session contract
- websocket contract (optional feature gate)

Plugins must satisfy these contracts.

## 3) Capability and feature gates

Core should expose clear behavior when broker plugin lacks a feature:
- raise `UnsupportedFeatureError`
- avoid silent no-ops

Feature categories:
- auth modes
- order types/products
- segments
- streaming support

## 4) Version compatibility strategy

Main risk in plugin ecosystems is version skew.

Recommended policy:
- core uses semver
- plugins declare compatible core range

Example plugin dependency:

```toml
# tt-connect-zerodha pyproject.toml
[project]
dependencies = ["tt-connect>=0.3,<0.4"]
```

Compatibility controls:
- CI matrix that tests each plugin against supported core versions
- contract tests in core that plugins must pass

## 5) Testing strategy after split

Core CI:
- unit/integration tests for broker-agnostic behavior
- mock adapter tests for contract compliance

Plugin CI:
- broker-specific parser/transformer/auth tests
- optional live tests (manual/flagged)

Cross-repo or monorepo matrix:
- run plugin tests against latest core and lowest supported core

## Repository Structure Options

## Option A: Multi-repo (clean ownership)

- `tt-connect` (core)
- `tt-connect-zerodha`
- `tt-connect-angel`

Pros:
- independent release cadence
- clean separation

Cons:
- cross-repo coordination overhead

## Option B: Monorepo with multiple distributables

```text
repo/
  packages/
    tt-connect/          # core
    tt-connect-zerodha/  # plugin
    tt-connect-angel/    # plugin
```

Pros:
- easier coordinated refactors
- shared CI tooling

Cons:
- requires packaging discipline to keep boundaries strict

Given current codebase maturity, monorepo multi-package is usually the easiest
first transition.

## Proposed Core Public API Shape

Keep core surface minimal and stable:

- `TTConnect` / `AsyncTTConnect` lifecycle + canonical operations
- request/response models (no broker kwargs in public signatures)
- plugin selection by broker id

Example:

```python
from tt_connect import AsyncTTConnect

async with AsyncTTConnect("zerodha", config) as broker:
    profile = await broker.get_profile()
```

If plugin missing:

```text
UnsupportedFeatureError: Broker 'zerodha' is not installed.
Install with: pip install tt-connect-zerodha
```

## Migration Plan (Phased)

## Phase 1: Internal plugin loader in current repo

- Add loader based on entry points
- Keep existing adapters in-tree temporarily
- Remove import side-effect registration from package init

## Phase 2: Extract first plugin (Zerodha)

- Move `tt_connect/adapters/zerodha/*` to plugin package
- publish `tt-connect-zerodha`
- keep compatibility shim for one release cycle

## Phase 3: Extract AngelOne plugin

- move AngelOne adapter/auth/parser/ws to `tt-connect-angel`
- publish plugin
- wire optional extra in core

## Phase 4: Harden contracts and remove shims

- enforce strict typed contracts in core
- remove deprecated in-tree broker imports
- require plugin installation for broker usage

## Packaging Examples

## Core `pyproject.toml` (concept)

```toml
[project]
name = "tt-connect"
version = "0.3.0"
dependencies = [
  "pydantic>=2.0",
  "httpx>=0.27",
  "aiosqlite>=0.20",
]

[project.optional-dependencies]
zerodha = ["tt-connect-zerodha>=0.3,<0.4"]
angel = ["tt-connect-angel>=0.3,<0.4"]
all = ["tt-connect-zerodha>=0.3,<0.4", "tt-connect-angel>=0.3,<0.4"]
```

Bracket notation support from this mapping:

- single extra: `pip install "tt-connect[zerodha]"`
- multiple extras: `pip install "tt-connect[angel,zerodha]"`
- all extras: `pip install "tt-connect[all]"`

## Zerodha plugin `pyproject.toml` (concept)

```toml
[project]
name = "tt-connect-zerodha"
version = "0.3.0"
dependencies = ["tt-connect>=0.3,<0.4"]

[project.entry-points."tt_connect.brokers"]
zerodha = "tt_connect_zerodha.adapter:ZerodhaAdapter"
```

## Operational Guidance

- Prefer explicit plugin installs in production for tighter control.
- Keep extras as developer convenience, not as the only path.
- Publish clear compatibility table:
  - core version
  - plugin version
  - supported Python versions

## Risks and Mitigations

1. Plugin/core incompatibility
- Mitigation: strict version ranges + CI matrix + contract tests.

2. User confusion about install commands
- Mitigation: clear runtime error messages with exact install command.

3. Release overhead
- Mitigation: automate release pipelines and changelog generation per package.

4. Boundary erosion in monorepo
- Mitigation: import lint rules preventing plugin->core-private imports.

## Decision Summary

Recommended:

1. Keep `tt-connect` as a small broker-agnostic core.
2. Move each broker into its own plugin package.
3. Use entry points for discovery.
4. Offer optional extras (`[angel]`, `[zerodha]`) as convenience only.
5. Enforce semver compatibility and plugin contract tests.

This model keeps the core elegant by construction and makes broker growth
additive instead of bloating the center.

## Maintainer Decision (Current)

Chosen target architecture: **Option A (Multi-repo)**.

Rationale:
- single maintainer with strong preference for strict boundaries
- long-term ecosystem growth with broker-specific release cadence
- desire to avoid core bloat by construction

Regression policy:
- "If it works, do not touch it" guides migration sequencing.
- move in small waves, preserve behavior first, refactor second.

## Least-Regression Rollout to Option A

The target remains multi-repo, but migration is staged to minimize risk.

### Wave 0: Stabilize and freeze contracts

- freeze current core public API signatures for one cycle
- lock broker contract tests (auth, profile, funds, holdings, positions, orders)
- add golden fixtures for parser/transformer outputs

### Wave 1: Extract Zerodha first (behavior-preserving)

- create `tt-connect-zerodha` repo
- move code with minimal structural edits
- register with entry point group `tt_connect.brokers`
- keep compatibility shim in core for one cycle (no user breakage)

### Wave 2: Validate parity and release

- run identical contract suite against old path and plugin path
- publish plugin with strict dependency: `tt-connect>=X,<Y`
- release core with plugin discovery and compatibility shim enabled

### Wave 3: Extract Angel with same process

- repeat Wave 1/2 pattern for `tt-connect-angel`
- do not batch additional refactors during extraction

### Wave 4: Remove shims after stability window

- remove in-core broker code paths only after one stable cycle
- keep migration notes and explicit install errors

## Guardrails for Safe Migration

1. No behavior changes in extraction PRs.
2. No refactor + move in same change set.
3. Contract tests must pass before publish.
4. Runtime error for missing plugin must include exact install command.
5. Core and plugin version ranges must be strict and tested.

## Versioning Rules for Option A

- Core and each plugin use semver.
- Plugins pin compatible core range:
  - example: `tt-connect>=0.3,<0.4`
- Breaking core contract change requires coordinated plugin major/minor updates.

## Operational Notes for Solo Maintainer

- Keep release checklist templates per repo (core and each plugin).
- Automate publish/test workflows early to reduce manual regression risk.
- Prefer small frequent releases over large migration drops.
