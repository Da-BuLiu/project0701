<!--
Sync Impact Report
- Version change: template → 1.0.0
- Modified principles: template placeholders → I. Contract-First Integration;
  II. Safety Boundary and PLC Isolation; III. Testable State and Resource Rules;
  IV. Traceability and Idempotency; V. Configuration and Evidence Discipline.
- Added sections: Technical Constraints; Development Workflow and Quality Gates.
- Removed sections: none.
- Templates requiring updates: ✅ .specify/templates/plan-template.md (existing Constitution
  Check supports these gates); ✅ .specify/templates/spec-template.md (requirements and
  assumptions support contract-first scope); ✅ .specify/templates/tasks-template.md
  (test tasks and validation steps support the principles).
- Follow-up TODOs: final PLC mapping, safety sequence, product-result rules, and external
  device ICDs remain explicitly pending in project documents.
-->

# 137 壳体虚拟下位机 Constitution

## Core Principles

### I. Contract-First Integration

The versioned HTTP and SignalR business contracts, field table, state machine, alarm catalog,
and takt configuration MUST be updated before an incompatible behavior change is implemented.
The middle platform MUST NOT access PLC registers or data blocks directly. Future physical PLC
integration MUST preserve the business contract so that only the adapter changes.

### II. Safety Boundary and PLC Isolation

The service MUST treat emergency stop, door interlocks, light curtains, and other personnel
safety functions as hardware-safety concerns. Simulation, UI controls, logs, and API responses
MUST NEVER be represented as safety controls. PLC and vendor-specific communication MUST stay
behind an adapter interface, with a simulated adapter available for offline development.

### III. Testable State and Resource Rules

Every device-state transition, command validation, workpiece lifecycle transition, resource
acquisition/release, and takt timeout MUST have automated tests before it is considered
complete. The design MUST support multiple workpieces in different operations at once, and a
resource with capacity one MUST NOT be allocated to two workpieces simultaneously.

### IV. Traceability and Idempotency

All externally submitted commands MUST carry a unique `commandId` and safely return the original
outcome when retried. Workpiece processing MUST be traceable by workpiece identity and SN when
available. Alarm, state, command, and result events MUST carry timestamps and correlation data;
raw measurements and user changes MUST be append-only or auditable rather than silently
overwritten.

### V. Configuration and Evidence Discipline

Stations, resource capacities, simulated timings, timeout values, and alarm mappings MUST be
configuration or documented contract data, not hidden implementation constants. A value absent
from approved source material MUST be labeled `待确认` or `temporary`; it MUST NOT be presented
as a final field address, product-quality rule, alarm code, or acceptance target.

## Technical Constraints

- The first implementation targets .NET 8 and a C# web service; Docker is not a first-phase
  server dependency.
- API versions start at `/api/v1`; breaking API changes require a new version or a documented,
  approved migration.
- The 125-second first-piece target and 65-second steady release interval are current planning
  inputs. The reported 180-second acceptance limit has a start/end-boundary conflict and MUST be
  reconciled before acceptance claims are made.
- Unknown PLC, robot, camera, endoscope, and thread-module protocols, addresses, and final
  result dictionaries require a written interface-control document before a real adapter is
  implemented.

## Development Workflow and Quality Gates

1. Create or amend the specification, contract documents, plan, and task list before a feature.
2. Implement the smallest independently testable vertical slice, beginning with health and
   device-state behavior before production simulation.
3. Run formatting, build, unit tests, and contract/configuration validation before declaring a
   task complete. Integration tests are required for external API contracts and adapter behavior.
4. Preserve reference requirements and measurement-analysis materials; do not delete or mix them
   with source code.
5. Record any changed assumption, deferred decision, or contract incompatibility in the relevant
   project document and review it before merging.

## Governance

This constitution supersedes conflicting repository conventions. Every implementation plan and
code review MUST verify the five core principles. Amendments require an explicit rationale,
impact on contracts/configuration/tests, and a semantic-version update: MAJOR for incompatible
principle redefinition or removal, MINOR for a new material principle or constraint, PATCH for
clarifications that do not change required behavior. The project guidance and current contract
documents are the operational reference for this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-07-18 | **Last Amended**: 2026-07-18
