# Implementation Plan: 137 壳体虚拟下位机基线

**Branch**: `001-virtual-line-simulation` | **Date**: 2026-07-18 | **Spec**:
[spec.md](spec.md)

## Summary

交付一个可由中台调用的虚拟下位机：提供受状态机约束且幂等的设备控制、工件 OP10～OP80
并行流转、资源互斥、配置驱动节拍、报警与事件、工件查询。接口合同保持稳定，未来将
`SimulatedPlcAdapter` 替换为真实 PLC 适配器而不改变中台调用方式。

## Technical Context

**Language/Version**: C# 12 / .NET 8（服务器已验证 SDK 8.0.129）

**Primary Dependencies**: ASP.NET Core Web API、SignalR、内置依赖注入/配置/日志、xUnit

**Storage**: 基线阶段为进程内状态与可替换仓储接口；SQLite 持久化、图片/点云归档不在本功能范围

**Testing**: xUnit 单元测试、Web API 集成测试、OpenAPI/JSON 配置解析验证

**Target Platform**: Ubuntu 24.04 开发环境；后续可部署至 Windows 11 IoT 工控机

**Project Type**: 后端 Web 服务

**Performance Goals**: 命令受理和状态查询在本地仿真环境中 1 秒内返回；连续三件工件能够并行推进，
容量为一的资源双重占用次数为零

**Constraints**: .NET 8；中台仅访问 `/api/v1` 业务接口和事件 Hub；不在服务器使用 Docker；不接入
真实 PLC/机器人/相机；软件不得承担人员安全功能

**Scale/Scope**: 8 个主工序、9 个初始互斥资源、至少 3 件并行在制品；字段地址、52 项结果、螺纹
结果字典、鉴权与持久化策略待后续接口控制文档确认

## Constitution Check

| 原则 | 计划中的满足方式 | 结果 |
|---|---|---|
| Contract-First Integration | 将 `openapi/openapi.yaml`、字段表、状态机、报警表和节拍配置作为实现与测试依据；API 变更同步更新合同 | Pass |
| Safety Boundary and PLC Isolation | 设计 `IPlcAdapter`、`SimulatedPlcAdapter`；安全状态仅展示/转发，不实现软件安全控制 | Pass |
| Testable State and Resource Rules | 先为状态转换、命令幂等、资源互斥、暂停/停止和超时建立 xUnit 测试 | Pass |
| Traceability and Idempotency | 命令记录、工件会话、报警和事件都保留 ID、时间、关联上下文 | Pass |
| Configuration and Evidence Discipline | 加载并验证 `config/takt-plan.json`；所有临时参数保持可追溯的 `temporary` 标记 | Pass |

**Post-design re-check**: Pass。设计没有新增直接 PLC 地址访问、软件安全功能或不可配置的站点/资源常量。

## Project Structure

### Documentation (this feature)

```text
specs/001-virtual-line-simulation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── http-signalr-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── VirtualLowerController.Api/
│   ├── Endpoints/
│   ├── Hubs/
│   ├── Contracts/
│   └── Program.cs
├── VirtualLowerController.Domain/
│   ├── Devices/
│   ├── Workpieces/
│   ├── Scheduling/
│   ├── Alarms/
│   └── Abstractions/
└── VirtualLowerController.Infrastructure/
    ├── Plc/
    ├── Scheduling/
    ├── Configuration/
    └── Persistence/

tests/
└── VirtualLowerController.Tests/
    ├── Unit/
    ├── Integration/
    └── Contract/
```

**Structure Decision**: 三个生产项目分别隔离中台 API、无框架依赖的业务规则和外部适配器；测试项目
覆盖领域规则、HTTP/SignalR 合同和端到端仿真。该边界直接支持后续 PLC 适配器替换。

## Complexity Tracking

无宪章违规。三个项目对应 API、领域和基础设施三个不可互换的职责；合并会使 PLC 细节渗入中台合同，
违反适配器隔离原则。
