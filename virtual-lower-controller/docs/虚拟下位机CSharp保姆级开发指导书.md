# 137 壳体虚拟下位机（C#）零基础开发指导书

> 这是一份“从哪里开始、在哪台机器做、每一步为什么做”的项目手册。
>
> 项目目标：真实 PLC 尚未完成前，先交付一个可让中台调用的虚拟下位机。它模拟设备状态、工件流转、8 个工序、报警、OK/NG 和节拍。真实 PLC 就绪后，不改中台接口，只替换底层 PLC 通信适配器。

## 0. 先记住这张总图

    需求文档、节拍表
          │
          ▼
    项目文档（字段表、状态机、接口合同）
          │
          ▼
    C# 虚拟下位机代码
          │
          ├─ 本地直接运行：开发和调试
          ├─ Docker 运行：中台联调和交付演示
          └─ CI 自动运行：每次提交都检查代码和测试
          │
          ▼
    未来 PLC 通信适配器
          │
          ▼
    真实 PLC、机器人、相机、传感器、螺纹设备

你不需要一开始把所有名词学会。项目按阶段推进；每个阶段只接触当前必要的工具。

## 1. 三个环境分别做什么

本项目有三类环境，不能混淆。

| 环境 | 是什么 | 做什么 | 现在是否使用 |
|---|---|---|---|
| 服务器开发环境 | 当前 Ubuntu 服务器：/home/ubuntu/disk/wj/virtual-lower-controller | 写 C#、运行测试、保存唯一工作副本 | 是，主环境 |
| 本地 Docker 环境 | 你的 Windows 电脑 | 仅在中台联调阶段运行 Docker 镜像 | 第五阶段才使用 |
| 最终部署环境 | 未来 Windows 11 IoT 工控机 | 最终运行虚拟/真实下位机 | 以后才用 |
| Git 远程仓库 | GitHub/Gitee 的私有仓库 | 保存“唯一可信版本”，供电脑、服务器、CI 同步 | 第一阶段建立 |

### 1.1 本次项目的明确选择

**主要开发地点：当前 Ubuntu 服务器。**

理由：

- 我可以直接创建、修改、检查和测试服务器中的项目文件；
- 你只需在本地 Docker 联调阶段下载或克隆项目并运行镜像；
- 服务器当前没有 .NET SDK，因此在开始编译 C# 前需先安装 .NET SDK；
- Docker 不在服务器上作为第一阶段依赖，本地 Docker Desktop 只在中台联调阶段使用。

### 1.2 项目文件放在哪里

项目已经建立在服务器中的专门目录：

    /home/ubuntu/disk/wj/virtual-lower-controller

测量资料已移入与本项目同级的 ../measurement-analysis；需求、协议和节拍表已移入 reference/requirements。后续 C# 代码只写在 src，不能与参考资料混放。

项目内部最终长这样：

    virtual-lower-controller/
    ├── docs/                         说明书和接口约定
    ├── specs/                        Speckit 生成的规格、计划、任务
    ├── openapi/                      中台接口合同
    ├── config/                       节拍和工位配置
    ├── src/
    │   ├── VirtualLowerController.Api/
    │   ├── VirtualLowerController.Domain/
    │   └── VirtualLowerController.Infrastructure/
    ├── tests/VirtualLowerController.Tests/
    ├── .github/workflows/            CI 配置
    ├── Dockerfile
    ├── compose.yaml
    └── VirtualLowerController.sln

## 2. 每个工具是什么、什么时候用

### 2.1 C#、.NET、Visual Studio

- **C#**：你写业务逻辑所使用的编程语言。
- **.NET**：让 C# 程序能编译和运行的平台；可理解为 C# 程序的“发动机、标准库和运行环境”。
- **.NET SDK**：开发用工具，提供 dotnet 命令，可新建工程、编译、运行、测试。
- **Visual Studio Community**：Windows 上适合初学者的 C# 开发软件，能打开项目、写代码、按 F5 调试、看报错。

使用阶段：**第一阶段安装，之后每个写代码阶段都使用。**

本地需要安装：

1. Visual Studio Community；
2. 安装时勾选“ASP.NET 和 Web 开发”工作负载；
3. .NET 8 SDK。

安装后在 PowerShell 输入：

    dotnet --version

能显示版本号，说明 C# 开发环境就绪。

### 2.2 Git 和 Git 远程仓库

Git 是代码的“时间机器”：每完成一个小功能就保存一个可回退版本。GitHub/Gitee 是保存这些版本的远程位置。

使用阶段：**第一阶段建立，从第一天开始使用。**

建议：

    本地电脑：写代码、git commit、git push
    GitHub/Gitee 私有仓库：保存主版本
    CI：从远程仓库自动取代码并测试
    当前服务器：以后若需要，可 git clone 同一个仓库

Git 不等于服务器；Git 仓库也不等于 Docker。

### 2.3 Speckit

Speckit 是“先写清需求再写代码”的工作流工具。它不会替你运行 PLC，也不是 C# 编译器。

它帮我们生成并维护：

    constitution：项目长期规则
    specify：本功能要做什么
    clarify：发现不清楚的地方
    plan：技术方案
    tasks：可逐项完成的开发任务

使用阶段：**文档和规划阶段，以及每个大功能开始前。**

你不需要先掌握 Speckit。每次我会给你完整可粘贴的指令，并解释生成的文件要看什么。

### 2.4 Docker

Docker 是把程序及其运行环境“装进一个标准盒子”的工具。

它不是写代码的地方，也不是第一天必须使用的工具。第一阶段直接在 Visual Studio 运行程序最快。

使用阶段：

| 阶段 | 是否用 Docker | 为什么 |
|---|---|---|
| 建文档、搭项目、写状态机 | 不用 | 先减少复杂度 |
| API 和测试跑通 | 不用 | Visual Studio 直接调试最快 |
| 中台需要联调 | 开始使用 | 中台可用一条命令启动固定版本 |
| CI | 使用 Docker 构建检查 | 确保镜像始终能打包 |
| 工控机部署 | 后续决定 | 可用 Docker，也可直接发布 Windows 程序 |

你的本地 Docker 用法将在第四阶段出现：

    docker compose up --build

它会读取项目根目录中的 Dockerfile 和 compose.yaml，启动虚拟下位机。中台此时用 HTTP 地址访问它。

### 2.5 CI

CI 是“自动检查员”。每次你把代码推送到 GitHub/Gitee，它自动执行：

    编译 C#
    运行测试
    检查代码格式
    构建 Docker 镜像

CI 不写业务功能，也不连接真实 PLC。它防止我们后面改代码时把已完成的状态机、节拍或接口改坏。

使用阶段：**当第一个 C# 工程可以编译和测试时接入。**

## 3. 项目完整阶段地图

| 阶段 | 目标 | 你在哪里做 | 此阶段使用的工具 | 产物 |
|---|---|---|---|---|
| 0 | 准备服务器开发环境 | 当前 Ubuntu 服务器 | .NET SDK、Git、Speckit | 可运行 dotnet，能提交 Git |
| 1 | 冻结项目约定 | 服务器项目目录 | Git、Speckit、Markdown | 状态机、字段表、OpenAPI 草案 |
| 2 | 搭 C# 空工程 | 服务器项目目录 | .NET | 可启动的 Web API、健康检查 |
| 3 | 做核心规则 | 服务器项目目录 | C#、xUnit | 启停/暂停/停止/回原点状态机 |
| 4 | 做工件和节拍仿真 | 服务器项目目录 | C#、JSON 配置、xUnit | OP10～OP80、多件流水线 |
| 5 | 给中台联调 | 服务器开发 + Windows Docker | HTTP、SignalR、Docker | 稳定接口、事件、Docker 启动方式 |
| 6 | 自动质量检查 | GitHub/Gitee | CI、Docker | 每次提交自动测试 |
| 7 | 对接真实 PLC | 工控机/现场 | PLC 协议、适配器 | 替换仿真 PLC，不改中台 API |

**现在只做阶段 0 和阶段 1。不要跳到 Docker、PLC、CI。**

## 4. 阶段 0：准备本地开发环境

### 4.1 你要做的事情

服务器端需要安装或确认：

- .NET 8 SDK；
- Git；
- Speckit；

Windows 本机保留 Docker Desktop 即可，此阶段不需要安装 Visual Studio，也不需要运行 Docker。

### 4.2 如何检查

在服务器终端：

    dotnet --version
    git --version
    specify --version

预期：

- dotnet 显示 8.x 版本；
- git 显示版本号；
- specify 显示版本号。

### 4.3 本阶段结束条件

你把上面三条命令的输出发给我，或确认都成功。我会根据你的实际环境给出下一条命令。

## 5. 阶段 1：建立项目和写项目合同

### 5.1 在哪里做

在**服务器项目目录**中做：

    cd /home/ubuntu/disk/wj/virtual-lower-controller
    git init

然后在 GitHub/Gitee 创建一个私有空仓库，再将服务器仓库关联远程。具体命令等远程仓库地址确定后再执行。

### 5.2 为什么先写文档，不先堆代码

因为当前有四件最容易导致返工的事尚未完全确定：

1. **字段表**：中台和 PLC 分别传什么；
2. **状态机**：启动、暂停、停止、报警时允许什么；
3. **OpenAPI**：中台具体调用什么地址、传什么 JSON；
4. **节拍和资源表**：工件怎样并行、哪些设备会互相等待。

如果先写代码，极容易发生：

    中台认为 start 表示“已经启动”
    下位机认为 start 表示“请求启动”
    中台按单件串行调用
    现场按第 65 秒启动第二件
    PLC 字段一出来，接口和程序全部重写

文档不是额外工作；它是后续 C# 代码的“施工图”。

### 5.3 本阶段要写的文件

在项目目录创建：

    docs/plc-field-table.md
    docs/state-machine.md
    docs/alarm-catalog.md
    openapi/openapi.yaml
    config/takt-plan.json

这五个文件分别回答：

| 文件 | 回答的问题 |
|---|---|
| plc-field-table.md | 哪些字段谁写、谁读、何时清零 |
| state-machine.md | 每个状态能做什么、能转去哪里 |
| alarm-catalog.md | 有哪些报警、代码和恢复方式 |
| openapi.yaml | 中台怎样调用虚拟下位机 |
| takt-plan.json | OP10～OP80 的顺序、时长、资源 |

### 5.4 节拍的正式模型

参考现有节拍表：

    首件约 125 秒；
    稳定生产约 65 秒/件；
    第一件进入 OP80 后，第二件可在前段继续。

因此虚拟下位机必须支持：

    工件 A：OP80，ThreadPlatform 正在使用
    工件 B：OP50，CylinderCamera 正在使用
    工件 C：等待上料

不能写成“工件 A 完成后才允许工件 B 进入”。

### 5.5 PLC 字段通信的初始表

真实 PLC 地址没确定时，地址写“待确认”，绝不凭空填写。

| 字段 | 方向 | 类型 | 含义 |
|---|---|---|---|
| StartRequest | 中台→下位机 | bool | 请求启动 |
| PauseRequest | 中台→下位机 | bool | 请求暂停 |
| ResumeRequest | 中台→下位机 | bool | 请求继续 |
| StopRequest | 中台→下位机 | bool | 停止，当前件作废 |
| ResetRequest | 中台→下位机 | bool | 请求复位 |
| HomeRequest | 中台→下位机 | bool | 请求回原点 |
| CommandId | 中台→下位机 | string | 命令唯一编号 |
| DeviceMode | 下位机→中台 | enum | Idle/Running 等状态 |
| CurrentSn | 下位机→中台 | string/null | 当前 SN |
| CurrentOperation | 下位机→中台 | string/null | 当前 OP |
| AlarmCode | 下位机→中台 | string/null | 当前报警码 |
| CycleResult | 下位机→中台 | enum/null | OK/NG/ABORTED |

每个字段还要补默认值、写入者、清零条件和超时处理。

### 5.6 状态机初稿

    Idle ──Start──> Running
    Running ──Pause──> Paused
    Paused ──Resume──> Running
    Running / Paused ──Stop──> Stopped
    Stopped ──HomeComplete──> Idle
    Running / Paused ──Fault──> Alarm
    Alarm ──Reset──> Idle 或 Stopped

固定规则：

    停止后，所有在制品变为 Aborted；
    Stopped 时禁止 Start；
    Home 成功后才回到 Idle；
    Paused 时工件不能推进；
    同一 commandId 重发只能生效一次；
    同一资源不能被两件工件同时占用。

### 5.7 Speckit 在本阶段怎么用

在项目根目录安装或运行 Speckit。若你的本机还没装，先安装：

    uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@vX.Y.Z
    specify init . --here

依次在 AI 编程工具中使用：

1. /speckit.constitution：写长期不可违反的规则；
2. /speckit.specify：写虚拟下位机要实现的行为；
3. /speckit.clarify：把不确定项标为待确认或临时假设；
4. /speckit.plan：生成 C# 技术设计；
5. /speckit.tasks：拆成能逐项完成的任务。

我会逐条给你可复制的内容，并在每次生成后解释文件。

### 5.8 本阶段结束条件

完成以下内容才进入代码：

- [ ] Git 本地仓库建立；
- [ ] GitHub/Gitee 私有远程仓库建立；
- [ ] 五份基础文档建立；
- [ ] Speckit 生成规格、计划、任务；
- [ ] 明确哪些是真实已知、哪些是临时假设。

## 6. 阶段 2：创建第一个 C# 工程

### 6.1 在哪里做

仍在**服务器项目目录**中做，不用 Docker。

### 6.2 创建命令

    dotnet new sln -n VirtualLowerController
    dotnet new webapi -n VirtualLowerController.Api -o src/VirtualLowerController.Api
    dotnet new classlib -n VirtualLowerController.Domain -o src/VirtualLowerController.Domain
    dotnet new classlib -n VirtualLowerController.Infrastructure -o src/VirtualLowerController.Infrastructure
    dotnet new xunit -n VirtualLowerController.Tests -o tests/VirtualLowerController.Tests

    dotnet sln add src/VirtualLowerController.Api
    dotnet sln add src/VirtualLowerController.Domain
    dotnet sln add src/VirtualLowerController.Infrastructure
    dotnet sln add tests/VirtualLowerController.Tests

初学者解释：

- Api：中台通过 HTTP 调用这里；
- Domain：最重要的业务规则放这里，例如状态机；
- Infrastructure：SQLite、仿真 PLC、以后真实 PLC 通信放这里；
- Tests：自动验证规则有没有写错；
- sln：Visual Studio 用来一次打开全部项目的解决方案文件。

### 6.3 第一段代码只做什么

只做两个接口：

    GET /api/v1/health
    GET /api/v1/device/state

第一个返回“服务是否活着”，第二个返回初始 Idle 状态。

此时不做 PLC、不做 8 工位、不做 Docker。先让 C# 工程能运行。

### 6.4 如何运行和验证

在服务器终端运行：

    dotnet run --project src/VirtualLowerController.Api

浏览器访问接口文档页面或 health 地址。具体地址由运行窗口显示。

### 6.5 本阶段结束条件

- [ ] Visual Studio 可以启动项目；
- [ ] health 返回成功；
- [ ] state 返回 Idle；
- [ ] 第一次 git commit 并推送远程仓库。

## 7. 阶段 3：实现设备状态机

### 7.1 目标

先不处理工件，只让虚拟设备正确理解：

    Start
    Pause
    Resume
    Stop
    Home
    Reset

### 7.2 为什么先做它

设备状态机是整个项目的交通规则。以后工件、报警、相机、PLC 都必须服从它。状态机错了，后面功能越多越难改。

### 7.3 自动测试

先写测试，再写 C#：

    Start 后从 Idle 进入 Running；
    Pause 后进入 Paused；
    Resume 后回到 Running；
    Stop 后进入 Stopped；
    Stopped 未 Home 时不得 Start；
    Home 成功后回到 Idle；
    相同 commandId 不能重复执行。

### 7.4 本阶段结束条件

- [ ] 命令 API 可调用；
- [ ] 状态转换正确；
- [ ] 自动测试通过；
- [ ] 我会向你解释 enum、class、interface、单元测试分别是什么。

## 8. 阶段 4：工件、工序、资源与节拍

### 8.1 目标

完成一个 SN 从 OP10 到 OP80 的模拟，随后实现多件并行。

配置文件 tak-plan.json 的初始内容：

    {
      "targetCycleTimeSeconds": 65,
      "firstPieceTotalSeconds": 125,
      "stations": [
        { "operationCode": "OP10", "resource": "Robot", "durationSeconds": 6 },
        { "operationCode": "OP20", "resource": "TransferModule", "durationSeconds": 2 },
        { "operationCode": "OP30", "resource": "EndFaceCamera", "durationSeconds": 6 },
        { "operationCode": "OP40", "resource": "LengthCamera", "durationSeconds": 3 },
        { "operationCode": "OP50", "resource": "CylinderCamera", "durationSeconds": 11 },
        { "operationCode": "OP60", "resource": "LineSpectrometer", "durationSeconds": 15 },
        { "operationCode": "OP70", "resource": "Endoscope", "durationSeconds": 16 },
        { "operationCode": "OP80", "resource": "ThreadPlatform", "durationSeconds": 52 }
      ]
    }

这些是仿真初始值，不是最终工艺承诺；后续应由工艺人员确认并调整。

### 8.2 先后顺序

1. 单件正常完成并输出 OK；
2. 资源互斥：同一资源不能双占用；
3. 多件并行：A 在 OP80 时 B 进入前段；
4. 按约 65 秒节拍投入新件；
5. 记录每件的开始/结束时间和各工序事件；
6. 加 NG、超时、读码失败等故障。

### 8.3 本阶段结束条件

- [ ] 可以投入 SN；
- [ ] 可查询当前 OP；
- [ ] 两件工件能正确并行；
- [ ] 资源不会冲突；
- [ ] 有测试证明第二件不必等待第一件全部完成。

## 9. 阶段 5：中台联调与 Docker

### 9.1 什么时候开始 Docker

只有以下功能完成才使用 Docker：

- API 已稳定；
- 状态机、单件流程、基本节拍测试已通过；
- 中台需要一套“任何电脑都可启动”的联调服务。

因此 Docker 是第五阶段工具，不是第一阶段工具。

### 9.2 Docker 在哪里使用

在第五阶段，将服务器项目通过 Git clone 或打包下载到你的 Windows 本地电脑，再在本地 Docker Desktop 的项目根目录使用：

    docker compose up --build

它会根据 Dockerfile 打包 C# 服务，并按 compose.yaml 启动。中台开发者拿到同一仓库后，也可用相同命令启动。

Docker 默认会保存镜像和缓存。虚拟下位机代码占很小；单个镜像常见为几百 MB。定期清理未使用镜像即可，不会因为项目源码撑爆电脑或服务器。

### 9.3 中台接口

中台通过 HTTP 调用：

    GET  /api/v1/health
    GET  /api/v1/device/state
    POST /api/v1/commands
    POST /api/v1/workpieces
    GET  /api/v1/workpieces/{sn}
    GET  /api/v1/resources

状态变化通过 SignalR 推送。HTTP 返回“命令已接收”，不等同于设备动作已经完成；中台需看状态或事件确认。

## 10. 阶段 6：CI

### 10.1 CI 在哪里运行

CI 在 GitHub/Gitee 的自动运行机器上执行，不在你的本机手工执行；服务器只负责提交代码。

配置文件放在项目里：

    .github/workflows/ci.yml

### 10.2 CI 做什么

每次 git push 或提交 Pull Request，自动：

    dotnet restore
    dotnet format --verify-no-changes
    dotnet build --configuration Release --no-restore
    dotnet test --configuration Release --no-build
    docker build -t virtual-lower-controller .

CI 不能替代中台联调，不能连接真实 PLC；它负责保证“已经通过的规则不会被后续修改破坏”。

## 11. 阶段 7：真实 PLC 到位后

真实 PLC 设备就绪后，先得到书面接口资料：

    PLC 品牌和型号
    通信协议
    IP、端口
    字段/寄存器/数据块表
    读写权限
    命令确认方式
    报警码
    超时和断线规则

然后新增一个真实适配器：

    IPlcAdapter
      ├─ SimulatedPlcAdapter：当前已完成的仿真实现
      └─ ModbusPlcAdapter / OpcUaPlcAdapter / 厂商适配器：现场实现

业务代码、中台 API、状态机、SQLite 数据结构都应保持不变。

## 12. 我与您的协作方式

我是本项目的主实施与分解者。在每一个任务完成后，我会固定给你：

1. **完成结果**：这一任务做成了什么；
2. **文件变化**：新增或修改了哪些文件；
3. **概念解释**：只解释当前涉及的 C#/.NET 概念；
4. **你如何验证**：给你一条或几条可执行命令；
5. **下一步原因**：为什么下一步先做它。

你不需要在不理解的情况下独自决定架构；但涉及真实 PLC 品牌、现场 IP、最终部署机器、客户验收规则时，我会明确标记为需要你或现场方确认，不能凭空替你决定。

## 13. 你现在只需要做的一件事

不要先用 Docker、不要先写 C#。项目目录和参考资料已经由我建立完成。

下一步是在服务器安装 .NET SDK。安装会改变服务器环境，因此需先获得你的确认；完成后我会执行安装并验证：

    dotnet --version
    git --version
    specify --version

之后我会只带你做“阶段 1：初始化 Git 和完成项目合同”，并逐项解释。
