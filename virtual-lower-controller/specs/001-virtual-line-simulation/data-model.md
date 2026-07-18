# Data Model: 137 壳体虚拟下位机基线

## 关系概览

```text
Device 1 ── * CommandRecord
Device 1 ── * Alarm
Device 1 ── * WorkpieceSession
WorkpieceSession 1 ── * OperationExecution
WorkpieceSession * ── * ResourceLease
ProductionEvent ──> Device / WorkpieceSession / Alarm / CommandRecord
```

## Entities

### Device

| 字段 | 规则 |
|---|---|
| `mode` | `Idle`、`Running`、`Paused`、`Stopped`、`Alarm` 之一 |
| `stateChangedAt` | 每次状态迁移更新的 UTC 时间 |
| `activeCommandId` | 正在处理的命令；无则为空 |
| `plcConnectionState` | 基线为 `Simulated`；真实适配器可报告 Connected/Disconnected/Faulted |
| `safetyState` | 只读诊断值；不驱动软件安全控制 |
| `activeAlarmIds` | 当前未恢复报警的集合 |

状态转换必须服从 `docs/state-machine.md`。

### CommandRecord

| 字段 | 规则 |
|---|---|
| `commandId` | 全局唯一；同 ID 载荷必须完全一致 |
| `commandType` | Start、Pause、Resume、Stop、Reset、Home |
| `requestedBy` | 调用者标识；鉴权策略待确认 |
| `receivedAt` | UTC 时间 |
| `outcome` | Accepted、Rejected、Completed、Conflict 之一 |
| `reasonCode` | 拒绝/冲突时的业务原因 |

`commandId` 是幂等键；不允许以新命令覆盖原记录。

### WorkpieceSession

| 字段 | 规则 |
|---|---|
| `workpieceId` | 生成后不可变的唯一标识 |
| `sn` | OP30 识别后可关联；来源、格式和重复规则待确认 |
| `status` | Waiting、InProcess、Completed、Failed、Aborted |
| `currentOperationId` | 当前工序，未开始/已结束时为空 |
| `cycleResult` | OK、NG、Aborted、Unknown 或空；未知不得自动转为 OK |
| `createdAt` / `completedAt` | UTC 时间线 |
| `operationExecutions` | OP10～OP80 的有序执行集合 |
| `resourceLeases` | 当前/历史资源占用记录 |

Stop 会将所有 `Waiting` 或 `InProcess` 工件置为 `Aborted`；终态工件不再推进。

### OperationExecution

| 字段 | 规则 |
|---|---|
| `operationId` | OP10、OP20、OP30、OP40、OP50、OP60、OP70、OP80 |
| `status` | Pending、Running、Passed、Failed、TimedOut、Aborted |
| `startedAt` / `completedAt` | UTC 时间 |
| `configuredDuration` / `timeout` | 来自经验证的节拍配置 |
| `resultReference` | 结果/诊断的可追溯引用 |

工序仅可按顺序开始；失败、超时或中止后不得继续下一工序。

### ResourceDefinition and ResourceLease

| 字段 | 规则 |
|---|---|
| `resourceId` | 配置中的资源 ID，例如 Robot、Conveyor、ThreadPlatform |
| `capacity` | 正整数；初始资源均为 1 |
| `workpieceId` / `operationId` | 当前或历史的占用者 |
| `acquiredAt` / `releasedAt` | 占用时间线 |

一次工序必须原子性获取其列出的全部资源。容量为 1 的资源同一时刻仅有一个有效租约。

### Alarm

| 字段 | 规则 |
|---|---|
| `alarmId` | 唯一标识 |
| `code` / `severity` | 必须来自 `docs/alarm-catalog.md` 的业务分类，或标记为 ALM-UNKNOWN |
| `source` / `rawSourceCode` | 产生者与可选的真实设备原码 |
| `workpieceId` / `operationId` | 可用时关联上下文 |
| `occurredAt` / `recoveredAt` | UTC 时间线 |
| `requiresHome` | 由报警目录和未来现场确认决定 |

### ProductionEvent

| 字段 | 规则 |
|---|---|
| `eventId` | 唯一标识 |
| `eventType` | DeviceStateChanged、WorkpieceChanged、AlarmRaised、CommandCompleted |
| `occurredAt` | UTC 时间 |
| `correlationId` | 命令或工件关联标识 |
| `payload` | 与事件类型匹配的只读快照 |

事件用于通知；重连后的权威状态由查询接口返回。事件重放留存期待确认。
