# Quickstart: 验证虚拟下位机基线

本指南在实现任务完成后使用。它验证中台可见的业务结果，不连接真实 PLC 或安全硬件。

## 前置条件

- 在项目根目录运行；`.NET SDK` 显示 8.0.129 或兼容的 .NET 8 SDK。
- 已完成 `tasks.md` 中 MVP（US1）所需任务；完整演示再完成 US2～US4。
- `config/takt-plan.json` 可解析，且资源 ID、工序顺序、正数时长和超时配置通过启动校验。

## 构建和测试

```bash
dotnet restore
dotnet build --no-restore
dotnet test --no-build
dotnet run --project src/VirtualLowerController.Api
```

预期：构建和测试成功；服务启动后，健康检查返回 Healthy，PLC 连接状态为 Simulated，设备状态为
Idle。具体本地端口以启动日志为准。

## 验证 US1：设备控制

1. 查询 `GET /api/v1/device/state`，确认初始为 Idle。
2. 使用新的 UUID 作为 `commandId` 提交 Start；确认受理后状态变为 Running。
3. 以不同 UUID 提交 Pause、Resume；确认 Paused 期间不开始下一工序。
4. 用相同的 Start `commandId` 和相同载荷重试至少三次；确认不产生额外状态转换。
5. 提交 Stop；确认状态为 Stopped，随后在 Home 完成前 Start 被拒绝。

## 验证 US2：多工件与资源

1. 从 Idle 启动连续仿真并观察工件查询或 `workpieceChanged` 事件。
2. 当至少三件工件已被接纳时，确认至少两件同时位于不同工序。
3. 在任一快照中检查同一资源（尤其 Conveyor、Robot、ThreadPlatform）不属于两件工件。
4. 核对首件目标约 125 秒、后续投料目标约 65 秒；报告中注明该值来自临时仿真配置。

## 验证 US3：报警与恢复

1. 使用测试控制入口或配置使一个工序超时；确认收到 `alarmRaised`，其中有报警码、级别、时间、
   工件和工序关联。
2. 尝试在故障恢复前 Reset；确认服务保持 Alarm 或拒绝复位。
3. 排除模拟故障并 Reset；若报警要求回原点，完成 Home 后确认返回 Idle。

## 验证 US4：工件记录

1. 分别完成一件正常工件、制造一件失败工件、并 Stop 一件在制工件。
2. 逐件查询详情；确认保留对应的 Completed/Failed/Aborted 状态、时间线和结果依据。
3. 确认 Unknown 的测量或螺纹结果不会被显示为 OK。

## 不在本次验证范围内

真实 PLC 通信、机器人/相机控制、安全回路、52 项实测、螺纹模块 ICD、持久化追溯、用户权限、
Docker 和 MES/ERP 集成均需后续受控任务和现场资料。
