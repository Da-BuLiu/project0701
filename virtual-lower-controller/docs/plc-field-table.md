# PLC / 中台字段表（初版）

## 目的与适用范围

本表定义中台与虚拟下位机之间的**业务字段**，而不是最终 PLC 寄存器地址表。当前真实 PLC 品牌、通信协议、地址、位宽和数据块均未确认，因此所有 `PLC 地址` 均为“待确认”。

中台只调用版本化 HTTP API 和订阅 SignalR 事件；未来 `IPlcAdapter` 负责将这些业务字段映射到真实 PLC，不能让中台直接读写 PLC 地址。

## 约定

- `中台→下位机` 为命令输入；`下位机→中台` 为状态、事件或结果输出。
- 命令使用 `commandId` 做幂等键：同一 ID 的重试不得重复执行。
- 请求型布尔字段采用“下位机已接收后确认/清除”的语义；HTTP 调用的响应本身不代表物理动作已完成，完成状态由设备状态和事件确认。
- 未确认的真实 PLC 映射不得作为现场实施依据。

## 命令字段

| 业务字段 | 方向 | 类型 | 默认值 | 写入者 | 消费/清除条件 | 超时/异常处理 | PLC 地址 |
|---|---|---|---|---|---|---|---|
| `commandId` | 中台→下位机 | string (UUID) | 无 | 中台 | 永久保存幂等结果；保留期待确认 | 格式非法则拒绝；同 ID 且载荷不同则冲突 | 待确认 |
| `commandType` | 中台→下位机 | enum | 无 | 中台 | 下位机接收后进入命令处理流程 | 未知命令拒绝 | 待确认 |
| `StartRequest` | 中台→下位机 | bool | false | 中台/业务 API | 仅 Idle 接收；受理后清除请求 | 非 Idle 时拒绝，返回当前状态 | 待确认 |
| `PauseRequest` | 中台→下位机 | bool | false | 中台/业务 API | 仅 Running 接收；进入 Paused 后清除 | 非 Running 时拒绝 | 待确认 |
| `ResumeRequest` | 中台→下位机 | bool | false | 中台/业务 API | 仅 Paused 接收；进入 Running 后清除 | 非 Paused 时拒绝 | 待确认 |
| `StopRequest` | 中台→下位机 | bool | false | 中台/业务 API | Running/Paused 接收；在制品标记 Aborted 后清除 | 终止超时产生报警，保持 Stopped/Alarm | 待确认 |
| `ResetRequest` | 中台→下位机 | bool | false | 中台/业务 API | 仅 Alarm 接收；故障条件消失且确认后清除 | 故障仍存在则拒绝/保持 Alarm | 待确认 |
| `HomeRequest` | 中台→下位机 | bool | false | 中台/业务 API | 仅 Stopped 接收；回原点完成后清除 | 回原点超时产生报警 | 待确认 |
| `requestedBy` | 中台→下位机 | string | 无 | 中台 | 随命令归档 | 缺失时按 API 鉴权主体补齐（鉴权方案待确认） | 不适用 |

## 设备状态字段

| 业务字段 | 方向 | 类型 | 默认值 | 写入者 | 更新/清除条件 | 超时/异常处理 | PLC 地址 |
|---|---|---|---|---|---|---|---|
| `deviceMode` | 下位机→中台 | enum | `Idle` | 下位机 | 每次状态转换立即更新 | 不可识别状态视为通信/映射报警 | 待确认 |
| `stateChangedAt` | 下位机→中台 | UTC ISO 8601 | 启动时写入 | 下位机 | 每次状态转换更新 | 时钟源待确认 | 不适用 |
| `activeCommandId` | 下位机→中台 | string/null | null | 下位机 | 命令处理完毕清空 | 卡住超过命令超时触发报警 | 待确认 |
| `currentAlarmCode` | 下位机→中台 | string/null | null | 下位机 | 无活动报警时清空 | 未知码记录为 `ALM-UNKNOWN` | 待确认 |
| `currentAlarmSeverity` | 下位机→中台 | enum/null | null | 下位机 | 与当前报警同步 | 待确认 | 不适用 |
| `plcConnectionState` | 下位机→中台 | enum | `Simulated` | PLC 适配器 | 连接状态变化时更新 | 真实 PLC 断线应报警；仿真模式不模拟硬件安全 | 待确认 |
| `safetyState` | 下位机→中台 | enum | `Unknown` | PLC 适配器 | 安全回路状态变化更新 | 当前仅预留；不得以软件模拟代替硬件安全 | 待确认 |

## 工件与工序字段

| 业务字段 | 方向 | 类型 | 默认值 | 写入者 | 更新/清除条件 | 超时/异常处理 | PLC 地址 |
|---|---|---|---|---|---|---|---|
| `workpieceId` | 下位机→中台 | string | 无 | 下位机 | 工件创建时写入，完成后归档 | 生成规则待确认 | 不适用 |
| `sn` | 双向 | string/null | null | 读码设备/下位机 | OP30 识别后绑定；不可覆盖原始读码值 | 读码失败产生报警/NG 处置待确认 | 待确认 |
| `workpieceStatus` | 下位机→中台 | enum | `Waiting` | 下位机 | 生命周期中更新 | Stop 时所有在制品置 `Aborted` | 不适用 |
| `currentOperation` | 下位机→中台 | enum/null | null | 下位机 | 工件进入/离开工序时更新 | 工序超时产生对应报警 | 待确认 |
| `operationStartedAt` | 下位机→中台 | UTC ISO 8601/null | null | 下位机 | 进入工序时写入 | 用于节拍和超时判断 | 不适用 |
| `operationResult` | 下位机→中台 | enum/null | null | 下位机/设备适配器 | 工序完成时写入 | `Timeout`/`Error` 须关联报警 | 待确认 |
| `occupiedResourceIds` | 下位机→中台 | string[] | [] | 下位机 | 资源获取/释放时更新 | 互斥冲突拒绝调度并记录诊断 | 不适用 |
| `cycleResult` | 下位机→中台 | enum/null | null | 下位机 | OP80 完成后写 `OK`/`NG`；停止写 `Aborted` | 汇总规则待确认，当前不假设螺纹结果规则 | 待确认 |

## 结果与诊断字段

| 业务字段 | 方向 | 类型 | 默认值 | 写入者 | 更新/清除条件 | 超时/异常处理 | PLC 地址 |
|---|---|---|---|---|---|---|---|
| `measurementResults` | 下位机→中台 | array | [] | 设备适配器/下位机 | 工序结果到达后追加，原始值不可覆盖 | 迟到结果按 SN 关联并保留审计；规则待确认 | 不适用 |
| `threadResults` | 下位机→中台 | array | [] | 螺纹设备适配器 | 螺纹模块回传后追加 | 字典、SN 匹配与超时均待确认 | 待确认 |
| `alarmCode` | 下位机→中台 | string/null | null | 下位机/适配器 | 报警激活时写入，复位条件满足后清除 | 见《报警目录》 | 待确认 |
| `eventId` | 下位机→中台 | string (UUID) | 无 | 下位机 | 每个 SignalR 事件唯一 | 事件可按序号重放的策略待确认 | 不适用 |
| `occurredAt` | 下位机→中台 | UTC ISO 8601 | 无 | 下位机 | 事件发生时写入 | 时钟同步方案待确认 | 不适用 |

## 待确认清单

1. PLC 品牌、协议、IP/端口、数据块、地址、字节序与读写周期。
2. 启动、暂停、停止、复位、回原点和报警确认的真实电气时序与权限。
3. SN 来源、格式、重复 SN 策略与读码失败后的分流方式。
4. 52 项检测结果字段、最终 OK/NG 汇总规则，以及螺纹结果是否参与汇总。
5. 命令幂等记录和事件重放的保留期、认证和审计要求。
