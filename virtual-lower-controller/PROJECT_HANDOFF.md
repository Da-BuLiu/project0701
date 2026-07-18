# 虚拟下位机项目交接记忆（新对话直接提供此文件）

## 1. 当前目标

开发“137 壳体自动检测线”的 C# 虚拟下位机。

真实 PLC、机器人、相机、传感器和螺纹设备尚未就绪。当前先开发一个可由中台调用的仿真服务：

    中台
      ↕ HTTP / SignalR（稳定的业务接口）
    虚拟下位机
      ↕ 未来 PLC 适配器
    真实 PLC 与现场设备

虚拟下位机要模拟：设备状态、SN 工件流转、OP10～OP80、资源互斥、多件流水线、报警、OK/NG、事件和历史数据。真实 PLC 到位后，应只替换底层 PLC 适配器，不改中台接口。

## 2. 已确认的工作方式

- 服务器是主开发环境：所有文档、C# 代码、测试、Git、Speckit、CI 配置均在服务器完成。
- 当前服务器工作区：/home/ubuntu/disk/wj。
- 项目根目录：/home/ubuntu/disk/wj/virtual-lower-controller。
- 用户本地 Windows 电脑只在后期中台 Docker 联调阶段使用 Docker Desktop。
- 当前不在服务器安装 Docker；Docker 不是第一阶段依赖。
- 用户是 C#/.NET 零基础。每完成一个任务后，必须说明：
  1. 完成结果；
  2. 文件变化；
  3. 本任务涉及的 C#/.NET 概念；
  4. 如何验证；
  5. 下一步为什么做它。

## 3. 当前服务器环境

- OS：Ubuntu 24.04.4 LTS，x86_64。
- .NET SDK：已安装并验证，版本 8.0.129。
- ASP.NET Core Runtime：8.0.29。
- Git：已安装，版本 2.43.0。
- Spec Kit CLI：已安装，命令 specify，版本 0.12.10。
- Docker：服务器当前不使用，未安装/未运行。
- 磁盘：约 21 GB 可用；.NET SDK 安装额外使用约 496 MB。

## 4. 当前目录结构

    /home/ubuntu/disk/wj/
    ├── measurement-analysis/                 # 独立测量资料，不能删除或混入 C# 源码
    │   ├── scripts/                          # measure_lengths.py、geometry_measurement_upgrade
    │   ├── source-data/                      # sample_1、sample_2、s1_label.*
    │   ├── analysis/                         # output、list.md、question_analysis.md 等
    │   └── cache/                            # 原 Python __pycache__
    ├── virtual-lower-controller/             # 本项目
    │   ├── README.md
    │   ├── PROJECT_HANDOFF.md
    │   ├── docs/
    │   │   └── 虚拟下位机CSharp保姆级开发指导书.md
    │   ├── reference/
    │   │   └── requirements/                 # 原始需求、协议、节拍表；只读参考
    │   ├── config/
    │   ├── openapi/
    │   ├── specs/
    │   ├── src/
    │   │   ├── VirtualLowerController.Api/
    │   │   ├── VirtualLowerController.Domain/
    │   │   └── VirtualLowerController.Infrastructure/
    │   ├── tests/VirtualLowerController.Tests/
    │   └── .github/workflows/
    └── 第四轮论文创新点指导_2026_07/       # 无关论文资料，未动

原始测量文件没有删除，只是按用户要求移到与项目同级的 measurement-analysis 中。

## 5. 已阅读的关键资料与结论

项目需求资料位于 reference/requirements：

- ER-PM-001 技术协议-137壳体_0703.docx
- 软件需求规格说明书.docx
- 137壳体项目理解与螺纹检测说明.md
- 137壳体项目需求澄清提问清单.md
- 壳体检测节拍分析260306.xlsx

节拍表的关键结论：

- 首件完整检测约 125 秒；
- 第一件进入螺纹检测平台后，约第 65 秒可开始第二件；
- 稳定连续生产目标约 65 秒/件；
- 必须支持多件工件同时在不同工位，不能做成单件串行。

已识别工序：

| 工序 | 内容 |
|---|---|
| OP10 | 上料机器人取料 |
| OP20 | 气缸二次定位 |
| OP30 | 端面检测、料号/SN 识别 |
| OP40 | 全长检测 |
| OP50 | 柱面及端面检测、旋转角度定位 |
| OP60 | 同轴线光谱检测 |
| OP70 | 内窥镜检测 |
| OP80 | 螺纹检测、OK/NG 下料 |

需要模拟资源互斥，例如：Robot、TransferModule、Conveyor、EndFaceCamera、LengthCamera、CylinderCamera、LineSpectrometer、Endoscope、ThreadPlatform。

## 6. 已确定的架构原则

1. 中台不直接访问 PLC 寄存器或数据块。
2. 中台通过版本化 HTTP API + SignalR 事件调用虚拟下位机。
3. PLC 细节隔离在 IPlcAdapter 后：

    IPlcAdapter
      ├─ SimulatedPlcAdapter（当前）
      └─ ModbusPlcAdapter / OpcUaPlcAdapter / 厂商适配器（未来）

4. 设备状态和工件状态分开。
5. 命令必须有 commandId，保证网络重试时幂等。
6. 停止后在制品为 Aborted；回原点后才能重新开始。
7. 虚拟急停/报警仅模拟状态，绝不替代硬件安全功能。
8. 节拍、工位和资源必须配置化，不能硬编码为不可修改逻辑。

初始设备状态机：

    Idle ──Start──> Running
    Running ──Pause──> Paused
    Paused ──Resume──> Running
    Running / Paused ──Stop──> Stopped
    Stopped ──HomeComplete──> Idle
    Running / Paused ──Fault──> Alarm
    Alarm ──Reset──> Idle 或 Stopped

## 7. 还没有做的事情

- 已在 virtual-lower-controller 中执行 `git init --initial-branch=main`，但尚未创建首个提交或关联 GitHub/Gitee 私有远程仓库。
- 尚未创建 GitHub/Gitee 私有远程仓库。
- 已初始化 Spec Kit（Codex 集成），并完成 constitution → specify → clarify → plan → tasks。
- 尚未创建任何 .sln、.csproj 或 C# 源码。
- 已创建并验证以下项目合同：
  - `docs/plc-field-table.md`
  - `docs/state-machine.md`
  - `docs/alarm-catalog.md`
  - `openapi/openapi.yaml`
  - `config/takt-plan.json`
- 已创建可执行规格与任务：`specs/001-virtual-line-simulation/`（含 spec、plan、research、data-model、contracts、quickstart、tasks）。
- 尚未安装服务器 Docker，也未构建 Docker 镜像。

## 8. 下一步

阶段 1（项目合同与规划）已经完成，且完成了 JSON/YAML 语法检查、无遗留模板占位符检查和 43 条任务格式检查。

下一步进入阶段 2，但仍不直接实现复杂业务逻辑：

1. 请用户审阅阶段 1 的合同和 `specs/001-virtual-line-simulation/tasks.md`，尤其确认当前临时假设和待确认项已被清楚标识；
2. 审阅通过后执行任务 T001～T005：创建 .NET 8 解决方案、三个生产项目和一个测试项目；
3. 只实现健康检查和初始 Idle 状态，再逐项执行状态机自动测试；
4. 每完成一项，向用户进行零基础解释；
5. 暂不安装服务器 Docker、暂不实现真实 PLC/机器人/相机通信。

## 9. 重要协作要求

- 用户明确要求：不要删除其测量资料；移动前必须说明目标位置。
- 对真实 PLC 品牌、IP、端口、字段地址、最终报警码、OK/NG 汇总规则等未知信息，标记“待确认”，不可凭空假设为最终事实。
- 需要安装新软件或执行会显著改变服务器环境的操作时，先说明用途和空间影响；本次 .NET SDK 已获授权并完成。
- 使用 apply_patch 编辑文本文件。
