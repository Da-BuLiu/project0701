# virtual-lower-controller

137 壳体自动检测线的 C# 虚拟下位机项目。

## 当前工作位置

本项目的主工作环境是当前服务器：

    /home/ubuntu/disk/wj/virtual-lower-controller

我会直接在此目录完成文档、C# 代码、测试、Git 初始化和 CI 配置。你的 Windows 本地电脑只在中台 Docker 联调阶段使用。

## 目录说明

| 目录 | 用途 |
|---|---|
| docs | 项目说明、字段表、状态机、报警表 |
| specs | Speckit 生成的规格、计划、任务 |
| openapi | 中台调用接口合同 |
| config | 工位、资源、节拍配置 |
| reference/requirements | 原始协议、需求说明、节拍分析文件 |
| ../measurement-analysis | 与本项目同级的独立测量资料目录：脚本、样本、分析结果和缓存 |
| src | C# 正式代码 |
| tests | C# 自动测试 |
| .github/workflows | GitHub Actions CI |

## 当前状态

- Git 本地仓库、项目合同和 Spec Kit 工作流已建立。
- 原始资料已完成分类移动，未删除。
- 服务器已安装 .NET 8 SDK（8.0.129）；尚未创建 C# 工程，避免在合同未冻结前过早编码。
- Docker 只在本地中台联调阶段使用。

## 项目合同

- [规范文档使用指南](docs/规范文档使用指南.md)：不确定该看或该修改哪份文件时，从这里开始。
- [PLC / 中台字段表](docs/plc-field-table.md)
- [设备与工件状态机](docs/state-machine.md)
- [报警目录](docs/alarm-catalog.md)
- [中台 API 合同](openapi/openapi.yaml)
- [节拍与资源配置](config/takt-plan.json)

所有缺少现场依据的项目均明确标注为“待确认”或“临时”，不作为最终 PLC 或验收事实。
