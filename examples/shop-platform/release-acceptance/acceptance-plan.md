# Release Acceptance Plan — v2026.09.0

## 1. 发布基线

| 项 | 内容 |
|---|---|
| Release Version | v2026.09.0 |
| Previous Tag | v2026.08.0 |
| Current Tag | v2026.09.0 |
| Planned Release Time | 2026-09-18 20:00 CST |
| Target Environment | staging |

## 2. Release Bundle

| Track | Included Repos | Requirements / Bugs | Migrations | Config / Dependency Changes |
|---|---|---|---|---|
| web | shop-web | REQ-checkout-001 | 无 | 无 |
| backend | shop-api | REQ-checkout-001 | 无 | payment timeout=10s |
| shared | 无 | 无 | 无 | 无 |

## 3. 范围

### Tracks

web、backend。

### 范围内

- 结算页提交订单的超时提示与重试入口。
- 支付服务超时配置调整。

### 范围外

- 支付渠道接入和订单结算规则变更。

## 4. 范围对账

| 来源 | Item | Track | 是否纳入 | 差异 / 处理 |
|---|---|---|---|---|
| Tag Diff | 结算提交超时提示 | web | 是 | 与需求一致 |
| Tag Diff | 支付超时配置 | backend | 是 | 与需求一致 |

### Scope Gap

| Gap | 影响 | 处理 |
|---|---|---|
| 无 | 无 | 无 |

## 5. 优先级与风险

| Item | Track | Change Type | Risk | Acceptance Priority | 依据 |
|---|---|---|---|---|---|
| 提交订单超时提示 | web | feature | High | P0 | 用户下单主链路 |
| 支付超时配置 | backend | config | High | P0 | 影响请求失败边界 |

## 6. 验收侧重点

### 本版本变更重点

超时场景下保留订单状态一致性，并向用户提供可操作的重试入口。

### 业务主链路

正常提交、超时提示、恢复后重试、重复提交防护。

### 回归重点

优惠、库存预占和订单状态查询。

### 数据正确性

超时前后订单与支付状态不可出现相互矛盾。

### 权限与配置

确认 staging 使用本 Release 声明的超时配置。

### 前后端契约

前端按照 `PAYMENT_TIMEOUT` 错误码展示重试入口。

### 部署 / 配置 / Migration

部署后读取生效配置；无 Migration。

## 7. 性能与稳定性

| 指标 | 阈值 | 场景 | 证据 |
|---|---|---|---|
| 下单接口错误率 | 小于 1% | 10 分钟稳定性观察 | monitoring:checkout-staging-window |

## 8. 验收覆盖与测试资产

| Release Item | Track | Risk / Priority | TP | TC | Automation | Execution |
|---|---|---|---|---|---|---|
| 超时提示与重试 | web | High / P0 | TP-checkout-01 | TC-checkout-01, TC-checkout-02 | Web smoke | Pending |
| 支付超时配置 | backend | High / P0 | TP-payment-01 | TC-payment-01 | API regression | Pending |

## 9. 自动化计划

- API：执行订单提交与超时错误码回归。
- Web：执行结算主链路 smoke；超时注入场景由手工验证补充。

## 10. 手工回归计划

- 在受控超时注入下确认提示、重试和订单状态。
- 核对部署后配置及稳定性观察结果。

## 10.1 未执行范围与覆盖缺口

| Release Item / Scope | 未执行原因 | 风险影响 | 已接受风险 / 豁免 | Owner / Follow-up |
|---|---|---|---|---|
| 弱网下的移动端展示 | 本 Release 未包含移动端构建 | 中：移动端体验未验证 | Not accepted | Mobile QA；下个移动端 Release 前补测 |

## 11. 回滚 / 恢复准备

恢复上一版本配置并回滚服务镜像；回滚后执行订单提交 smoke。

## 12. 验收阈值 / Exit Criteria

| Gate | Exit Criteria | Status | Waiver |
|---|---|---|---|
| P0 | 100% 执行且通过 | Pending | |
| P1 | 无未解决阻塞问题 | Pending | |
| Critical Risk | 必须有覆盖和执行证据 | Pending | |
| Migration | 必须验证成功 | Not applicable | 无 Migration |
| Rollback | 必须验证或有批准豁免 | Pending | |
| Performance | 达到定义阈值 | Pending | |

## 13. 发布阻塞项

P0 用例失败、订单状态不一致、未批准的覆盖缺口均阻塞发布。

## 14. 测试管理平台验收单

| 项 | 内容 |
|---|---|
| 是否创建 / 更新 | 已创建 |
| 验收测试单 ID | TM-ACC-example-2026-09 |
| 关联既有测试用例 | TC-checkout-01, TC-checkout-02, TC-payment-01 |
| 回填状态 | 未回填 |

## 15. Release Decision

| 项 | 预期 / 计划 |
|---|---|
| Decision Gate | READY / CONDITIONAL / BLOCKED |
| 未解决 P0 | 0 |
| 未解决 P1 | 0 |
| Coverage Gap | 移动端弱网场景未覆盖，未接受 |
| Accepted Risk / Waiver | 无 |
| 决策依据 | 以执行记录与验收报告为准 |

## 16. 可追溯关系

`REQ-checkout-001 → RISK-checkout-001 → TP/TC → execution-record → acceptance-report`
