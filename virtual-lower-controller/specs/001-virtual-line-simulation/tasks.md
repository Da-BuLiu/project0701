# Tasks: 137 壳体虚拟下位机基线

**Input**: Design documents from `/specs/001-virtual-line-simulation/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required by Constitution III. For each behavior task, write the named test first, run it
to observe failure, then implement the smallest change that makes it pass.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested as
an independently demonstrable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: May run in parallel after dependencies are complete and files do not overlap.
- **[Story]**: Maps to a user story in [spec.md](spec.md).
- Every task names the concrete target path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the .NET 8 solution and make project contracts/configuration available to code.

- [ ] T001 Create `VirtualLowerController.sln` and .NET 8 projects in `src/VirtualLowerController.Api/`, `src/VirtualLowerController.Domain/`, `src/VirtualLowerController.Infrastructure/`, and `tests/VirtualLowerController.Tests/`.
- [ ] T002 Add project references so `VirtualLowerController.Api` references Domain and Infrastructure, Infrastructure references Domain, and `tests/VirtualLowerController.Tests/` references all required projects.
- [ ] T003 [P] Add baseline test packages and test discovery configuration in `tests/VirtualLowerController.Tests/VirtualLowerController.Tests.csproj`.
- [ ] T004 [P] Copy/runtime-link the validated configuration in `config/takt-plan.json` through `src/VirtualLowerController.Api/VirtualLowerController.Api.csproj` without placing a second authoritative configuration copy in source.
- [ ] T005 [P] Add the solution build/test commands and .NET 8 SDK prerequisite to `README.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish domain rules and infrastructure that every user story needs.

**⚠️ CRITICAL**: Complete this phase before implementing user-story endpoints.

- [ ] T006 [P] Define shared device, command, workpiece, operation, result, resource, alarm and event value types in `src/VirtualLowerController.Domain/Abstractions/` according to `specs/001-virtual-line-simulation/data-model.md`.
- [ ] T007 Write state-transition unit tests in `tests/VirtualLowerController.Tests/Unit/DeviceStateMachineTests.cs` for all legal and illegal transitions in `docs/state-machine.md`.
- [ ] T008 Implement the state machine in `src/VirtualLowerController.Domain/Devices/DeviceStateMachine.cs` so T007 passes.
- [ ] T009 Write atomic resource-acquisition/release tests in `tests/VirtualLowerController.Tests/Unit/ResourceManagerTests.cs`, including no double allocation for capacity-one resources.
- [ ] T010 Implement resource capacity and atomic lease handling in `src/VirtualLowerController.Domain/Scheduling/ResourceManager.cs` so T009 passes.
- [ ] T011 Write configuration validation tests in `tests/VirtualLowerController.Tests/Unit/TaktPlanValidatorTests.cs` for operation order, resource references, positive capacities/durations/timeouts, and temporary timing labels.
- [ ] T012 Implement configuration loading and validation in `src/VirtualLowerController.Infrastructure/Configuration/TaktPlanLoader.cs` and `src/VirtualLowerController.Infrastructure/Configuration/TaktPlanValidator.cs` so T011 passes.
- [ ] T013 [P] Define repository and clock abstractions in `src/VirtualLowerController.Domain/Abstractions/` for command records, workpiece sessions, alarms, events and deterministic time.
- [ ] T014 [P] Implement in-memory repositories and a testable clock in `src/VirtualLowerController.Infrastructure/Persistence/`.
- [ ] T015 Define `IPlcAdapter` and simulation-safe connection/safety diagnostics in `src/VirtualLowerController.Domain/Abstractions/IPlcAdapter.cs` and `src/VirtualLowerController.Infrastructure/Plc/SimulatedPlcAdapter.cs`.
- [ ] T016 Configure dependency injection, structured request/error logging, configuration validation at startup, and Problem Details mapping in `src/VirtualLowerController.Api/Program.cs`.

**Checkpoint**: The solution builds; domain rules have tests; an invalid takt plan prevents startup;
all external-device access is behind `IPlcAdapter`.

---

## Phase 3: User Story 1 - 控制并确认设备状态 (Priority: P1) 🎯 MVP

**Goal**: 中台可以用幂等命令控制设备，并从 API 和事件确认合法的状态转换。

**Independent Test**: 从 Idle 执行 Start → Pause → Resume → Stop → Home，验证每个状态、非法命令、
重复命令和停止后的 Aborted 语义。

- [ ] T017 [P] [US1] Write command idempotency and conflict tests in `tests/VirtualLowerController.Tests/Unit/CommandProcessorTests.cs`.
- [ ] T018 [P] [US1] Write HTTP contract tests for health, device-state, command 202/409/422 responses in `tests/VirtualLowerController.Tests/Contract/DeviceApiContractTests.cs` using `openapi/openapi.yaml`.
- [ ] T019 [P] [US1] Write SignalR notification tests for device state and command completion in `tests/VirtualLowerController.Tests/Integration/DeviceEventTests.cs`.
- [ ] T020 [US1] Implement command validation, idempotent command records, and Stop-to-Aborted handling in `src/VirtualLowerController.Domain/Devices/CommandProcessor.cs`.
- [ ] T021 [US1] Implement device state snapshot queries in `src/VirtualLowerController.Domain/Devices/DeviceStateService.cs`.
- [ ] T022 [US1] Implement health, device-state and command endpoints plus request/response DTOs in `src/VirtualLowerController.Api/Endpoints/` and `src/VirtualLowerController.Api/Contracts/`.
- [ ] T023 [US1] Implement the production event hub and device/command event publication in `src/VirtualLowerController.Api/Hubs/ProductionEventsHub.cs` and `src/VirtualLowerController.Infrastructure/`.

**Checkpoint**: US1 is independently usable through HTTP and SignalR; legal transitions pass, invalid
commands do not mutate state, and three identical retries cause one transition.

---

## Phase 4: User Story 2 - 观察并行工件流转 (Priority: P2)

**Goal**: 工件按 OP10～OP80 配置推进，支持多件流水线和资源互斥。

**Independent Test**: 连续接纳三件工件，观察至少两个不同工序同时存在，且任一单容量资源没有双重
占用。

- [ ] T024 [P] [US2] Write workpiece lifecycle and operation-order tests in `tests/VirtualLowerController.Tests/Unit/WorkpieceLifecycleTests.cs`.
- [ ] T025 [P] [US2] Write multi-workpiece, pause-boundary, release-interval, and resource-contention tests in `tests/VirtualLowerController.Tests/Integration/SimulationSchedulerTests.cs`.
- [ ] T026 [P] [US2] Write workpiece list/detail HTTP contract tests in `tests/VirtualLowerController.Tests/Contract/WorkpieceApiContractTests.cs` using `openapi/openapi.yaml`.
- [ ] T027 [US2] Implement workpiece sessions and operation execution transitions in `src/VirtualLowerController.Domain/Workpieces/`.
- [ ] T028 [US2] Implement the configuration-driven simulation scheduler, admission rule, timeout checks, and resource release in `src/VirtualLowerController.Infrastructure/Scheduling/SimulationScheduler.cs`.
- [ ] T029 [US2] Implement workpiece query endpoints and workpiece-change event publication in `src/VirtualLowerController.Api/Endpoints/WorkpieceEndpoints.cs` and `src/VirtualLowerController.Api/Hubs/ProductionEventsHub.cs`.

**Checkpoint**: US2 independently shows multiple in-process workpieces and validates no resource
double allocation; the UI/API can inspect every current operation and resource lease.

---

## Phase 5: User Story 3 - 处理报警与异常结果 (Priority: P3)

**Goal**: 超时、配置、命令和模拟设备异常形成可追溯报警，并遵守 Reset/Home 恢复规则。

**Independent Test**: 注入工序超时与配置异常，检查报警字段、Alarm 状态、故障未恢复时的 Reset 拒绝
以及需要 Home 的恢复路径。

- [ ] T030 [P] [US3] Write alarm lifecycle and Reset/Home state tests in `tests/VirtualLowerController.Tests/Unit/AlarmServiceTests.cs`.
- [ ] T031 [P] [US3] Write alarm HTTP/SignalR contract tests in `tests/VirtualLowerController.Tests/Integration/AlarmEventTests.cs`.
- [ ] T032 [US3] Implement alarm catalog lookup, active/recovered lifecycle, and workpiece/operation correlation in `src/VirtualLowerController.Domain/Alarms/AlarmService.cs`.
- [ ] T033 [US3] Connect scheduler timeouts, adapter faults, configuration faults, and command conflicts to alarm publication in `src/VirtualLowerController.Infrastructure/`.
- [ ] T034 [US3] Expose active alarms in device snapshots and publish `alarmRaised` events in `src/VirtualLowerController.Api/`.

**Checkpoint**: US3 emits traceable alarms, never portrays software state as a safety function, and
does not allow Reset to bypass an unrecovered condition.

---

## Phase 6: User Story 4 - 查询生产记录和结果 (Priority: P4)

**Goal**: 中台按工件标识查看完成、失败和中止的生产记录以及形成结果的时间线。

**Independent Test**: 查询一件 Completed、Failed 和 Aborted 工件，确认不同终态、工序记录、报警
关联和 Unknown 结果均保留且没有被改写为 OK。

- [ ] T035 [P] [US4] Write final result aggregation and immutable terminal-state tests in `tests/VirtualLowerController.Tests/Unit/ResultAggregationTests.cs`.
- [ ] T036 [P] [US4] Write workpiece history response tests in `tests/VirtualLowerController.Tests/Integration/WorkpieceHistoryTests.cs`.
- [ ] T037 [US4] Implement result-basis capture and safe OK/NG/Unknown/Aborted aggregation in `src/VirtualLowerController.Domain/Workpieces/ResultAggregationService.cs`.
- [ ] T038 [US4] Complete in-memory history queries and workpiece detail mapping in `src/VirtualLowerController.Infrastructure/Persistence/` and `src/VirtualLowerController.Api/Endpoints/WorkpieceEndpoints.cs`.

**Checkpoint**: US4 makes each terminal workpiece record queryable with time-ordered evidence and
never treats an unconfirmed measurement/thread result as OK.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verify the contract, configuration and documentation as one deliverable.

- [ ] T039 [P] Validate JSON syntax and semantic constraints of `config/takt-plan.json` in `tests/VirtualLowerController.Tests/Unit/TaktPlanValidatorTests.cs`.
- [ ] T040 [P] Validate implemented endpoint payloads against `openapi/openapi.yaml` in `tests/VirtualLowerController.Tests/Contract/`.
- [ ] T041 Update completed API examples, known external dependencies, and verification evidence in `README.md`, `docs/`, and `specs/001-virtual-line-simulation/quickstart.md`.
- [ ] T042 Run `dotnet format --verify-no-changes`, `dotnet build`, `dotnet test`, and every scenario in `specs/001-virtual-line-simulation/quickstart.md`; record results in `specs/001-virtual-line-simulation/`.
- [ ] T043 Review `docs/plc-field-table.md`, `docs/state-machine.md`, `docs/alarm-catalog.md`, `openapi/openapi.yaml`, and `config/takt-plan.json` for compatibility with the implementation before the first commit.

## Dependencies & Execution Order

```text
Phase 1 Setup
  → Phase 2 Foundation
    → US1 Device control (MVP)
      → US2 Multi-workpiece flow
        → US3 Alarm handling
          → US4 Workpiece history
            → Phase 7 Contract/configuration validation
```

- Phase 2 blocks every user story.
- US1 must precede US2 because the scheduler requires controlled Running/Paused/Stopped states.
- US3 and US4 use the shared foundations and may begin after US2 is stable; they are listed
  sequentially to reduce changes to shared workpiece/event code.
- The `[P]` items within a phase can be split across developers once their predecessors finish.

## Parallel Example: Foundation and US2

```text
After T006 is complete, run in parallel:
- T007 state-machine tests
- T009 resource-manager tests
- T011 takt-plan validator tests
- T013 repository/clock abstractions

After US1 is complete, run in parallel:
- T024 workpiece lifecycle tests
- T025 scheduler integration tests
- T026 workpiece API contract tests
```

## Implementation Strategy

### MVP First

1. Complete T001–T016.
2. Complete T017–T023 (US1).
3. Run the US1 portion of [quickstart.md](quickstart.md) and demonstrate health, state, legal
   commands, invalid commands, idempotent retry, Stop and Home.
4. Do not start real PLC integration, Docker or the 52-item measurement implementation.

### Incremental Delivery

1. Add US2 to demonstrate the 125-second/65-second simulation and resource arbitration.
2. Add US3 to validate fault/recovery semantics before external devices exist.
3. Add US4 to give the middle platform queryable virtual production history.
4. Only after these paths are tested, create separate controlled work for persistent storage,
   real PLC adapters, external device ICDs, Docker, CI, and field acceptance.
