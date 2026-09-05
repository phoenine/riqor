# Riqor 开源宣传帖

最近把做了一段时间的测试 Agent 工作台开源了，名字叫 **Riqor**。

它不是再写一个更长的 Prompt，也不只是把 PRD 转成测试用例。Riqor 更关心测试工作里容易被忽略的部分：现有资产能不能复用、需求变化后哪些产物已经过期、一条风险结论由什么证据支撑，以及用例不合格时流程能不能真的停下来。

你可以从 PRD、Bug、代码变更、发布基线或已有用例中的任意位置开始，告诉它最终想得到什么。Agent 负责分析，`agent-next` CLI 负责盘点依赖、记录 Run State、维护产物关系并执行 Stage Gate。

目前仓库提供三条通用流程：

- 新功能测试
- Bug 回归
- 发布验收

项目自己的仓库、Track、知识和环境策略通过 Project Profile 配置，不需要修改 Core。远程写入、共享环境执行和数据修改仍然保留明确的人工确认边界。

仓库里带了一个可以直接运行的 Shop Platform 示例。当前版本共运行 228 项单元测试，全部通过；示例项目检查覆盖 18 个 Capability 和 16 个 Artifact Template。

项目仍处于 `0.1.0.dev0`，离“一键完成所有测试”很远。但如果你也在研究怎样让测试 Agent 从「会写」走到「结果可检查、过程可追溯」，欢迎试用或提 Issue。

GitHub：[github.com/phoenine/Riqor](https://github.com/phoenine/Riqor)

#软件测试 #AIAgent #开源项目 #测试工程
