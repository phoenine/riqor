# 自动化转换与分级规则

用于把测试用例、验收 cases 或回归计划转成自动化落地计划。

## 边界

- `agent-next` 负责理解、分类、计划、生成可审查草稿和记录追溯。
- 最终可运行代码进入 `repositories/test/` 中的长期自动化仓库。
- `outputs/` 只放需求、用例、分类结果、转换计划、执行记录等交付物；**不要**在 `outputs/**/auto/` 下维护自动化仓库副本。
- 数据准备能力进入 `repositories/tools/`。
- 不把 Markdown 解析、分类器、转换计划维护逻辑塞进自动化测试仓库。

## 产品线分支

Web/UI 自动化仓库 `envision-webtest` 按 run state `product_line` 切换分支后再写 case 或执行：

| product_line | 分支 | 典型前端栈 |
|---|---|---|
| `v1` | `hermes-cases` | Angular / Gallery |
| `v2` | `hermes-2.0` | React / newepvs-demo |

规则：

1. 从 ePVS Project Profile 的 automation repository 配置读取分支映射。
2. 在 `repositories/test/envision-webtest/` 检出对应分支。
3. 用 `tools/run_state.py --repository ...branch=<branch>` 记录当前分支。
4. 未确认 `product_line` 前不要写自动化 case。

API 自动化仓库 `envision-apitest` 使用固定工作分支：

| 仓库 | 工作分支 | 禁止直合 |
|---|---|---|
| `envision-apitest` | `dev` | `main` |

规则：

1. 从 ePVS Project Profile 的 automation repository 配置读取工作分支。
2. 在 `repositories/test/envision-apitest/` 检出 `dev` 后再写 case 或执行。
3. 禁止向 `main` 直接提交、推送或合并；合入 `main` 由人工评审流程处理。
4. 用 `tools/run_state.py --repository ...branch=dev` 记录当前分支。

## 自动化分级

| 等级 | 含义 | 处理 |
|---|---|---|
| A0 | selector/接口/数据稳定，可直接自动化 | 可进入实现或执行计划 |
| A1 | 可自动化，但缺 selector、fixture、PageObject 或上下文参数 | 先补支撑能力 |
| M0 | 半自动，需要截图、图表、视觉或人工判断 | 生成辅助步骤和证据 |
| N0 | 不适合自动化或风险过高 | 保留手工并记录原因 |

## 目标轨道

| target | 含义 | 仓库 |
|---|---|---|
| web | 浏览器 UI 自动化 | `repositories/test/envision-webtest/` |
| hybrid | UI 路径 + Network/API 观察 | `repositories/test/envision-webtest/` |
| api | 直接接口、契约、数据校验 | `repositories/test/envision-apitest/` |
| manual | 人工验证 | 不进入自动化仓库 |

`target` 与 `level` 正交，例如 `A1 + api` 表示可做接口自动化但还缺认证或数据 fixture。

## 转换纪律

- 先小试点，选择一个稳定 cases 文件，不默认批量转换全部资产。
- 先输出 conversion plan，再实现自动化。
- selector 不散落在测试脚本中，优先 PageObject / ComponentObject 封装。
- UI 中观察 Network 的契约验收属于 `hybrid`，不要误判为纯 `api`。
- 自动化执行前检查环境、账号、数据、回滚影响和用户确认。
- 失败结果必须归因，不只报告 pass/fail。

## 解析要求

结构化测试用例时保留：

- source artifact、case ID、标题、优先级、外部 ID。
- 前置条件、步骤、预期结果、备注。
- 上游需求/风险/测试点引用。
- warnings/errors，例如空外部 ID、步骤/预期数量不一致。

解析阶段只做结构化，不做自动化推断；分类阶段再判断 level 和 target。
