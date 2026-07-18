# HTTP / SignalR Contract Map

本文件是基线功能的接口实现对照。规范的机器可读来源始终是
[`openapi/openapi.yaml`](../../../openapi/openapi.yaml)；修改接口时必须同步更新该文件、字段表和
本文件。

## HTTP

| 合同 | 用途 | 服务故事 |
|---|---|---|
| `GET /api/v1/health` | 读取服务和 PLC 适配器健康状态 | US1 |
| `GET /api/v1/device/state` | 拉取设备权威快照和活动报警 | US1、US3 |
| `POST /api/v1/commands` | 提交含 `commandId` 的设备控制命令 | US1 |
| `GET /api/v1/workpieces` | 查询在制或历史工件 | US2、US4 |
| `GET /api/v1/workpieces/{workpieceId}` | 查询单件工序时间线、资源和结果 | US2、US4 |

命令返回 `202 Accepted` 仅表示服务已受理或确认幂等重试；调用方必须查询设备状态或等待
`commandCompleted` 事件来确认完成。`422` 表示当前状态不允许，`409` 表示命令标识与首次载荷冲突。

## SignalR

Hub 路径：`/hubs/events`。

| 事件名 | 最小内容 | 用途 |
|---|---|---|
| `deviceStateChanged` | `eventId`、`occurredAt`、设备状态快照 | 确认状态转换 |
| `workpieceChanged` | `eventId`、`occurredAt`、工件快照 | 显示并行工件流转 |
| `alarmRaised` | `eventId`、`occurredAt`、报警快照 | 显示异常与恢复条件 |
| `commandCompleted` | `eventId`、`occurredAt`、命令结果 | 异步命令完成通知 |

SignalR 事件必须携带唯一事件标识与 UTC 发生时间。事件通知丢失或客户端重连后，调用方通过 HTTP
快照重新同步。鉴权、授权、协商限制和事件重放策略待中台联调前确认。

## Compatibility Rules

1. 中台不得以 PLC 地址、寄存器、线圈或数据块作为接口。
2. 既有字段的破坏性变更必须引入新 API 版本，或取得书面迁移确认。
3. 真实 PLC 适配器只映射内部业务命令、状态和报警；它不得改变 HTTP 路径、命令幂等语义或事件名称。
4. SN、52 项测量、螺纹结果和最终 OK/NG 规则加入合同前，必须有受控字段字典和验收规则。
