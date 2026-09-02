# 禅道同步规则

用于把本地需求、测试点、测试用例、Bug 或执行结论同步到禅道。

## 写操作门禁

以下动作必须先获得用户确认，并记录到 run state `confirmations[]`：

- 创建、更新、删除、上传测试用例。
- 创建、关闭、重开、更新 Bug。
- 修改需求、任务、状态、评论或附件。
- 批量回填 ID 或批量替换字段。

读取禅道可用于 intake，但读取失败不能当作对象不存在的证据。

## 用例标题前缀

上传到禅道时，测试用例 title 可按模块加前缀，便于筛选。

前缀与模块映射必须来自 Project Profile 的 integration config 或用户确认，
本 Skill 不提供默认产品、模块或前缀。

规则：

- 前缀只加在上传到禅道的 title。
- 本地 Markdown 标题不加模块前缀。
- 上传 title 去掉本地 `TC-001：` 前缀后再加模块前缀。

示例：

```text
本地：TC-001：用户登录页面验证
禅道：【administration】用户登录页面验证
```

## 更新操作（zentao-cli v0.1.7+）

当前环境应使用 **zentao-cli ≥ 0.1.7**（本地验证版为 0.1.8）。`update` 会先 GET 当前对象，再把未显式传入的字段用现值填充后 PUT，避免禅道 PUT 清空未提交字段。

规则：

- 一般对象：只需传**想改**的字段。
- `testcase update`：**仍必须传 `--title`**（即使标题不变）；`steps` / `expects` / `stepType` / `precondition` / `pri` / `type` 等未传字段会自动保留，不必全量重传。
- v0.1.6 及以下没有自动补全；若被迫使用旧版，用例更新必须同时传全量字段，避免空写。不要假设旧 CLI 与本仓库规则一致。
- 更新成功后抽查：`zentao testcase <id> --pick=id,title,pri,type,precondition --format=json`（需要步骤时再查完整详情，避免默认拉全量）。

## 测试用例上传 payload

上传测试用例时必须按当前安装的 `zentao-cli` schema 组织步骤字段。升级 CLI
后先用只读命令和 `--help` 核对字段，再执行写操作。

关键定义：

```js
steps: {
  type: "array",
  items: { type: "string" },
  description: "用例步骤"
},
expects: {
  type: "array",
  items: { type: "string" },
  description: "用例步骤期望"
},
stepType: {
  type: "array",
  items: { type: "string" },
  description: "用例步骤类型(step 步骤 | group 父级步骤)"
},
type: {
  description: "用例类型(unit 单元测试 | interface 接口测试 | feature 功能测试 | install 安装部署 | config 配置相关 | performance 性能测试 | security 安全相关 | other 其他)"
}
```

规则：

- `steps` 不是对象数组，不能传 `[{"desc": "...", "expect": "..."}]`；否则禅道可能保存为 `[object Object]`。
- `steps`、`expects`、`stepType` 必须是三个独立的字符串数组，并按数组索引一一对应。
- 普通步骤的 `stepType` 使用 `"step"`；只有确实需要父级分组步骤时才使用 `"group"`。
- 本地 Markdown 中 `操作步骤` 的第 N 条映射到 `steps[N-1]`，`预期结果` 的第 N 条映射到 `expects[N-1]`。
- 上传前确认步骤数和预期结果数一致；不一致时先修本地用例，不要上传。
- `type` 必须使用禅道 schema 枚举值，不要自造英文值。
- `type` 来自本地 `用例类型`：`功能测试` → `"feature"`，`接口测试` → `"interface"`，`单元测试` → `"unit"`，`安装部署` → `"install"`，`配置相关` → `"config"`，`性能测试` → `"performance"`，`安全相关` → `"security"`，`其他` → `"other"`。

错误示例：

```json
{
  "steps": [
    {"desc": "步骤1", "expect": "结果1"}
  ]
}
```

正确示例：

```json
{
  "productID": 42,
  "title": "库存不足时提交订单应提示缺货商品",
  "precondition": "已登录；购物车中商品库存不足",
  "steps": ["提交购物车订单"],
  "expects": ["页面提示库存不足并标识对应商品"],
  "stepType": ["step"],
  "pri": 1,
  "type": "feature"
}
```

推荐上传命令：

```bash
zentao create testcase --product 42 --data '{"productID":42,"title":"库存不足时提交订单应提示缺货商品","precondition":"已登录；购物车中商品库存不足","steps":["提交购物车订单"],"expects":["页面提示库存不足并标识对应商品"],"stepType":["step"],"pri":1,"type":"feature"}'
```

## 同步纪律

- 上传前检查本地 artifact metadata 和 traceability。
- 已有禅道数字 ID 的用例默认跳过，除非用户要求更新。
- 上传成功后立即回填返回 ID；未回填视为流程未完成。
- 回填必须用唯一上下文，禁止把所有 `未上传` 替换成同一个 ID。
- 上传 / 更新后抽查禅道记录，确认 title、precondition、steps、expects 未丢失或误清空。
- `precondition` 避免真实换行；多条件用中文分号分隔（换行会在 shell 里截断参数，导致禅道前置条件为空）。

## 失败处理

- token 过期或权限错误时，记录环境阻塞，不继续假设同步成功。
- 搜索无结果时，记录 search evidence；不要断言对象不存在。
- 批量写入部分失败时，保留成功 ID、失败原因和重试计划。
