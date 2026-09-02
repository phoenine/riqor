# Test Case Examples

Use these examples to keep cases executable, concise, and traceable. They are
examples only; concrete values and expected behavior must come from the active
workflow evidence.

## Simple TP To TC

```markdown
Upstream TP: TP-001 Enabled status is visible after turning on the setting.

### TC-001：启用配置后页面显示启用状态

优先级：P2
外部用例ID：未同步
用例类型：功能测试
可追溯关系：TP-001

前置条件：

1. 当前用户有配置编辑权限。

测试数据：

操作步骤：

1. 打开配置页面，将目标配置切换为启用并保存。
2. 刷新页面。

预期结果：

1. 保存后该配置状态显示为“启用”。
2. 刷新页面后该配置仍显示为“启用”。
```

## BVA TP To TC

```markdown
Upstream TP: TP-003 Cycle Time minimum boundary behavior.

Coverage Gap: TP-003 requires minimum-boundary instantiation, but the minimum
Cycle Time value is not available in the requirement, risk analysis, source
evidence, or knowledge base.
```

When the minimum is known, instantiate representative values such as `min-1`,
`min`, and `min+1`. Split success and failure outcomes into separate cases when
the expected result differs.

## Decision Table TP To TC

```markdown
Upstream TP: TP-007 Sync rule priority across R1, R2, R3.

### TC-004：同步条件命中一般值规则时按指定同步词更新

优先级：P1
外部用例ID：未同步
用例类型：功能测试
可追溯关系：TP-007 / Rule R2

前置条件：

1. 已存在包含基准词和一般词的同步词配置。
2. 测试设备组满足 R2 条件。

测试数据：

| 场景 | 输入值 | 说明 |
|---|---|---|
| R2 命中设备组 | 设备组 A | 满足 R2 条件且不满足 R1 / R3 |

操作步骤：

1. 执行同步更新。
2. 查看同步结果明细。

预期结果：

1. 结果明细显示命中 R2。
2. 一般值按 R2 对应同步词更新，且不显示 R1 或 R3 的命中结果。
```

## State Transition TP To TC

```markdown
Upstream TP: TP-011 Enabled -> Disabled transition.

### TC-006：已启用配置停用后不再参与自动执行

优先级：P1
外部用例ID：未同步
用例类型：功能测试
可追溯关系：TP-011

前置条件：

1. 已存在启用状态的配置。

测试数据：

操作步骤：

1. 停用该配置并查看配置状态。
2. 触发一次自动执行并查看执行结果。

预期结果：

1. 配置状态显示为“停用”。
2. 本次自动执行结果中不包含该配置。
```

## Coverage Gap

```text
Coverage Gap: TP-014 requires role and scope combination instantiation, but the
available requirement only names “administrator” and does not define ordinary
user scope or expected denial behavior.
```
