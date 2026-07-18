# 设备与工件状态机（初版）

## 范围

本文件定义虚拟下位机的业务状态，不定义真实安全回路。急停、门禁和安全光栅必须由经验证的硬件安全系统处理；本服务最多显示或转发其状态。

设备状态和工件状态分开维护：设备可以在 `Running` 时同时有多件工件位于不同工序，不能把整条产线建模为单件串行流程。

## 设备状态

| 状态 | 含义 | 允许命令 | 禁止/结果 |
|---|---|---|---|
| `Idle` | 已回原点，可接收新的生产启动 | Start | Pause、Resume、Home、Reset 拒绝；Stop 为幂等无操作（暂定） |
| `Running` | 自动生产中；工件可在资源许可时推进 | Pause、Stop | Start、Resume、Home、Reset 拒绝 |
| `Paused` | 新的工序推进被冻结；在制品与资源状态保留 | Resume、Stop | Start、Pause、Home、Reset 拒绝 |
| `Stopped` | 已停止；所有在制品均为 `Aborted`，需回原点 | Home | Start、Pause、Resume、Reset 拒绝 |
| `Alarm` | 存在未恢复的故障或联锁异常 | Reset（故障已消失时） | Start、Pause、Resume、Stop、Home 拒绝；Stop 的硬件语义待确认 |

## 设备状态转换

```text
Idle ──Start──> Running
Running ──Pause──> Paused
Paused ──Resume──> Running
Running / Paused ──Stop──> Stopped
Stopped ──HomeComplete──> Idle
Running / Paused ──Fault──> Alarm
Alarm ──ResetComplete──> Idle 或 Stopped
```

| 触发 | 前置状态 | 后置状态 | 处理规则 |
|---|---|---|---|
| Start | Idle | Running | 验证无活动报警、已回原点、必要资源可用；具体现场联锁待确认 |
| Pause | Running | Paused | 禁止调度新的工序；正在执行的原子动作如何安全暂停，待 PLC/设备协议确认 |
| Resume | Paused | Running | 仅在暂停条件已解除且无报警时继续调度 |
| Stop | Running/Paused | Stopped | 停止调度；释放可安全释放的资源；所有在制品记录为 `Aborted`；等待真实设备停止确认的时序待确认 |
| HomeComplete | Stopped | Idle | 所有需要回原点的设备确认完成，且无未清除报警 |
| Fault | Running/Paused | Alarm | 冻结调度，记录报警与发生时刻；在制品处置规则按报警类型待确认 |
| ResetComplete | Alarm | Idle 或 Stopped | 仅在故障源已恢复并确认后；是否必须回原点由报警目录的 `requiresHome` 决定 |

## 命令幂等与并发规则

- 每个命令必须提供唯一 `commandId`。
- 相同 `commandId` 与完全相同的命令载荷：返回首次处理结果，不重复触发状态转换。
- 相同 `commandId` 但载荷不同：拒绝并返回冲突错误。
- 同一时刻只处理一个状态转换命令；后到命令按接收顺序验证当时状态。
- HTTP `202 Accepted` 表示已受理，不表示设备已完成动作；中台应读取设备状态或订阅事件确认。

## 工件状态

| 状态 | 含义 | 可迁移到 |
|---|---|---|
| `Waiting` | 已排队，尚未进入 OP10 | `InProcess`、`Aborted` |
| `InProcess` | 正在 OP10～OP80 中的某一工序或等待资源 | `Completed`、`Failed`、`Aborted` |
| `Completed` | 所有需要的工序完成，已形成 `OK`/`NG` 结果 | 无（仅允许追加复检/审计记录，规则待确认） |
| `Failed` | 因工序异常、超时或无法判定而结束 | 无（复检规则待确认） |
| `Aborted` | 因 Stop 被终止 | 无；重新检测必须创建新的工件会话，SN 重用规则待确认 |

## 工序与资源规则

1. 工件顺序为 OP10 → OP20 → OP30 → OP40 → OP50 → OP60 → OP70 → OP80；OP50 内部子步骤见节拍配置。
2. 工件进入工序前，必须原子性获取该工序声明的全部资源；若任一资源被占用，则保持等待，不能部分占用。
3. 一个资源同一时刻只能属于一个工件；工序结束、失败或终止时必须释放。
4. `Paused` 时不得开始下一工序；正在执行的动作是否可中断必须按具体设备确认，当前仿真版以“工序边界暂停”为临时策略。
5. `Stopped` 时所有在制品转为 `Aborted`，不得再推进；只有 HomeComplete 回到 Idle 后才可新开生产。

## 已知待确认项

- Pause/Stop 对机器人、输送线、相机、内窥镜和螺纹平台的真实安全停机语义。
- Fault 后在制品是 `Failed`、`Aborted`、等待人工，还是可恢复；不同报警可不同。
- Reset 后何时回 Idle、何时必须先 Home，以及 Alarm 状态中 Stop 的实际处理。
- 入料触发、SN 读码失败、重复 SN、NG 分流和螺纹迟到结果的业务规则。
