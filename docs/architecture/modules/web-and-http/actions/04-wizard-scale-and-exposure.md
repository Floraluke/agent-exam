# 任务 04：三步向导的新规模动线与网页读取面暴露扫描（B 切片）

> 状态：**B 切片已完成并合入 `main`**（2026-09-21）。六题×两配置向导、`continuous(1–20)` 动线与网页读取面暴露扫描均已验证；任务 04 当前等待人工确认。
>
> 任务 04 的整体 DRI 是 **C**；本文件只维护 issue 明确划给 **B** 的两项——"三步向导浏览器动线归 B"、"12 个公开读取面全量扫描…网页面归 B"。`HTTP_API.md` 经确认**本轮不改**。
>
> 门槛同任务 03：写代码前按[实现地图 2.1 节](../../../../../.scratch/ui-catalog-providers/implementation-map.md)补齐逐控件契约。

## 1. 情况说明与现存事实

规模侧由 D 实现、目录侧由 C 实现并已合入 `main`（`361998b`）。B 侧要验证的是**这两者通过既有 Web 面是否真的可用、且不泄漏**。

已核实（2026-09-21，读 `main` 的代码）：

- `delivery/job_presets.py:29` 已有 `BatchPreset("continuous", 1, 20)`；`delivery/catalog_presets.py` 的 `TASK_PRESETS` 已是六条（旧题 + 五道新题）。
- **向导是完全服务端驱动的**：任务来自 `tasks?limit=100`、配置来自 `agent-configurations?agent_type=codex&enabled=true&limit=100`、批次与限制来自 `job-options`；`wizard/view.tsx:50-55` 只在服务端选项里校验当前选择是否仍有效，不写死任何规模。
- `jobs/controls.tsx:44` 已经渲染 `{preset}（{min}–{max} 题）`，因此 `continuous（1–20 题）` 会自动出现，六道题也会自动出现在第一步。
- **向导没有前端 min/max 校验**：`count = 选中题数 × 配置数`，提交按钮只要求 `count > 0`；规模不符由服务端拒绝并返回稳定错误 `BATCH_PRESET_EXCEEDED`（文案"任务或配置数量不符合所选批次规模。"），向导会把它显示在 `role="alert"` 里。这是刻意的服务端权威设计，**本轮不改成前端拦截**。

## 2. 逐控件契约表（B 切片部分）

### 2.1 三步向导在新规模下的动线

| 页面与控件 | 前端处理 / URL | HTTP Interface | 后端与权限 / 完成后状态 | 验证 |
|---|---|---|---|---|
| 向导：任务勾选（第一步） | 列表来自服务端；六道题应全部可勾；`aria-label="任务 {instance_id}"` | `GET /api/v1/tasks?limit=100`（既有） | Task Catalog；已登录用户 | 六道题全部出现且可勾；不出现参考补丁/隐藏测试字段 |
| 向导：配置勾选（第二步） | 同上，`aria-label="配置 {display_name}"` | `GET /api/v1/agent-configurations?...enabled=true`（既有） | Agent Registry | 多配置可同时勾选；停用配置不出现 |
| 向导：批次规模 | 下拉项文本 `{preset}（{min}–{max} 题）`；选择只改本机会话状态 | `GET /api/v1/job-options`（既有） | 选项由服务端 preset 提供，前端不硬编码 | `continuous（1–20 题）` 可见可选；切换后仍能提交 |
| 向导：组合数量（第二步） | 显示 `组合数量：{tasks × agents}` | **无** | 前端重算，仅提示 | 数字随勾选变化；不冒充服务端结论 |
| 向导：核对与提交（第三步） | 显示 `{n} 道题 × {m} 个配置 = {k} 个 Run`；提交用同一未决正文复用幂等键 | `POST /api/v1/jobs` + `Idempotency-Key`（既有） | Job Submission → Repository；只创建 `AWAITING_OWNER_APPROVAL` | 提交后详情显示等待批准；规模不符时显示稳定错误而非假成功 |
| 向导：规模不符的反馈 | 服务端拒绝后错误出现在 `role="alert"`，不改变已选状态 | 400 `BATCH_PRESET_EXCEEDED` | Job Submission 在创建前拒绝 | 选超出 `demo` 上限的题数时看到该错误；重新放宽后能成功 |

### 2.2 网页面读取面暴露扫描

| 对象 | 断言 | 依据 |
|---|---|---|
| 向导、目录、列表、详情、报告、证据、排行榜各页面 | 页面文本中**不出现** `HIDDEN_ANSWER`、`hidden_test`、`hidden_pass`、`private-test-reference` 等哨兵值 | C 已在 12 个 HTTP 公开读取面做过同类扫描（`tests/catalog/test_security.py::test_hidden_evaluation_fields_never_reach_public_surfaces`）；**网页渲染面归 B** |
| 同上 | 页面不出现 `gold_patch`/`test_patch` 之类的字段名，也不出现 MinIO `object_key` | §10.4/§9 的契约边界；Web 只消费公开 DTO |

## 3. 待确认的决策：浏览器夹具要不要扩到六题

**现状**：`apps/backend/tests/identity/browser_server.py`（Web 套件的合成后端夹具）只种 **2 道题 + 1 个配置**（`example__repo-1/2` + `Synthetic Codex`）。而任务 04 验收要求"六题×三配置的合成提交"。

**两份事实的分工**：C 已在 **HTTP 层**验证"6 题 × 2 配置提交"（`tests/catalog/test_catalog_job_flow.py`），D 已覆盖规模边界（4/6/9 通过、0/21 拒绝、20×3=60 允许）。所以**浏览器端不扩夹具也不会造成"六题未被验证"**，只是浏览器动线本身仍停在 2 题。

**本次选择**：**扩夹具到 6 题 + 2 配置**，理由是浏览器动线要证明的正是"六道题在多选与多配置下可用"，2 题证明不了勾选与组合数量的规模化行为。夹具是 Web 套件的测试脚手架（非产品代码），扩的是种子数据、不动任何接口。**若扩夹具导致既有 spec 断言失效，则回退为 2 题并如实记录限制**——不为通过而改既有断言。

## 4. 实施措施

1. 扩 `browser_server.py` 夹具：4 道新题的 `task_bundle` 与 `task_presets` 条目（→ 6 题）、1 个新配置（→ 2 个），保持既有两条 preset id 不变（`swe-gym-lite-example-1/2` 已被既有 spec 依赖）。
2. 新增浏览器用例 `tests/jobs/wizard-scale.spec.ts`：六题全可选、切到 `continuous` 提交成功并停在等待批准、`demo` 下超上限时显示稳定错误、页面暴露扫描。
3. 回归：`npm run typecheck`、`npm run build`、`npm run test:e2e`（全量，确认扩夹具没有破坏既有 spec）。
4. 把结果写回本文件第 6 节。

## 5. 预估修改文件

```text
apps/backend/tests/identity/browser_server.py   # 修改：夹具种子扩到 6 题 + 2 配置（测试脚手架，非产品代码）
apps/web/tests/jobs/wizard-scale.spec.ts        # 新增：新规模动线 + 暴露扫描
docs/architecture/modules/web-and-http/actions/04-wizard-scale-and-exposure.md  # 本文件
```

**不改**：任何产品代码、`HTTP_API.md`、C 的目录实现与测试、D 的规模测试。

## 6. 自验证情况

2026-09-21 在本机执行并检查输出：

- `ruff check`（改动文件）→ All checks passed；`ruff format --check` 起初报需重排，已跑 `ruff format` 并在其后复跑用例确认行为未变。
- `npm run typecheck` → 退出码 0。
- `npm run build`（`next build`）→ 退出码 0，`Compiled successfully`。
- `npm run test:e2e -- wizard-scale.spec.ts` → **2 passed**：
  - `six tasks and two configs submit under the continuous scale`：六道题全部出现且可勾；`continuous（1–20 题）` 由服务端提供并可选；第三步显示"6 道题 × 2 个配置 = 12 个 Run"；提交后停在"等待所有者批准"；任务目录与配置目录的页面文本中 7 个哨兵值（`HIDDEN_ANSWER`/`hidden_test`/`hidden_pass`/`private-test-reference`/`gold_patch`/`test_patch`/`object_key`）**零命中**。
  - `a scale above the selected preset is refused with a stable error`：`demo` 下选 4 题提交 → 向导区域内 `role="alert"` 显示稳定文案"任务或配置数量不符合所选批次规模。"且不进入详情页；改选 `continuous` 后**同一选择提交成功**。这证明超限是服务端权威、错误可解释、且不是"选项本身不可用"。
- `npm run test:e2e`（**全量**，含夹具扩展）→ **退出码 0，18 个 spec 全绿**；扩夹具**没有破坏任何既有断言**（夹具的 preset 是按需登记，既有 spec 只登记前两个，因此看到的数量不变）。

**未覆盖（如实记录）**：

- "0 题 / 21 题、0/4 配置、20×3=60" 这些边界**在浏览器里打不到**（夹具六题、产品当前只有一个配置 preset），由 D 的规模测试与 C 的目录测试在服务端覆盖；浏览器侧只覆盖了"超过所选 preset 上限"这一条用户可见路径。
- 第二个配置 `Synthetic Terra` 是为多配置动线造的**合成值**，不是产品目录里的真实配置。
- 网页面扫描只覆盖任务目录与配置目录（本轮动线可达的公开页）；报告/证据/排行榜页面渲染的是既有 DTO，未在本轮重复扫描。
- 前端仍然**没有**规模拦截（刻意保留服务端权威），因此"超限"总是先发请求再显示错误。

## 7. 明确不做

- 不在前端加规模拦截（服务端权威 + 稳定错误已足够；改了反而与"服务器权限不依赖隐藏按钮"的既有约定冲突）。
- 不重复实现或改写 D 的规模测试、C 的目录测试。
- 不改 `HTTP_API.md`（本轮经确认不改）。

## 8. 指标例外：夹具文件超 200 行（**需确认**）

`apps/backend/tests/identity/browser_server.py` 从 **198 行 → 225 行**（净增 27），超过"单个源代码文件默认不超过 200 行"的指标。

**为什么只能加在这个文件里**：夹具基线是 **198/200，没有任何余量**——即使只种 4 道题、不加第二个配置，也会到 206 行。要覆盖"六题动线"与"超过 preset 上限的用户可见错误"两条，只能扩这个文件的种子数据。

**风险**：该文件同时服务全部 18 个 Web spec，改动面比一般测试文件大；继续增长会降低可读性。

**拆分评估（建议、本次未实施）**：把种子表（任务 bundle 与 preset 映射、Agent 配置）抽到同目录的新文件 `tests/identity/browser_presets.py`，`browser_server.py` 只留装配，可回落到 200 行以内；`tests/identity/` 当前 8 个条目、加 1 个仍 ≤8，**不需要新目录**。本次倾向不抽——种子表与装配逻辑一一对应，拆开后读代码要跳文件，且这次只动数据不动结构；拆分是可逆的，代价是以后越晚越贵。

**另一条路（若选择不超指标）**：把夹具退回 2 题 1 配置，并删掉本文件第 6 节第 1 条用例与第 2 条的超限部分——代价是浏览器侧不再覆盖六题动线与超限错误，这两项改由 C 的 HTTP 层用例（六题×两配置）与服务端规模测试承担。

**用户已确认（2026-09-21）**：按例外继续——本次保留 225 行，**不做拆分**。理由采纳"种子数据与装配逻辑一一对应、本次只动数据不动结构"；拆分评估保留在上一段，作为后续可选（若该文件再增长，优先执行拆分到 `tests/identity/browser_presets.py`）。
