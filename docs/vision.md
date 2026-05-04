# IRMDS Vision

IRMDS is a personal open-source systems project exploring a simple question:

> What would a small, dependable runtime for intelligent physical-space
> monitoring look like?

The current answer is intentionally modest: a kernel, a module contract, an
event bus, alert handling, metrics, persistence, an API, and reference modules
for four very different domains.

## Present-Day Positioning

Use this phrase for the current repo:

> open-source runtime for intelligent physical-space monitoring

Avoid claiming real autonomous control or industrial safety readiness. v0 is a
monitoring and simulation system.

## Long-Term North Star

The long-term direction is a "physical-space runtime":

- a small core that manages modules, events, metrics, alerts, and sessions
- a stable SDK that makes new modules easy to write
- reference modules for vision, network, finance, and infrastructure
- safe dry-run command simulation before any real actuation
- future policy, audit, authentication, and simulation layers

This is adjacent to the "Linux for physical spaces" idea, but the project should
earn that language over time through reliability, contributor experience, and
real deployments.

## Safety Principle

Software should never be the only safety layer for physical systems.

Real control belongs behind:

- explicit authentication and authorization
- signed command records
- policy checks
- simulation or dry-run validation
- audit logs
- hardware interlocks and certified safety mechanisms

v0 deliberately stops at simulated command execution.

## Growth Strategy

Do not build 100 modules first. Build the runtime so well that modules become
easy.

Recommended path:

1. make v0 reliable and easy to run
2. document the module contract clearly
3. ship Docker and CI
4. add a module starter template
5. improve dashboard and operator workflows
6. then expand into higher-value modules

The value is the kernel pattern:

```text
Module -> EventBus -> AlertManager/Metrics -> API -> Dashboard
```
