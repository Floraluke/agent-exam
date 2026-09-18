# 数据模型图中文辅助标签

## 状态与情况说明

- 状态：已完成；存在下述本机视觉渲染验证限制。
- 来源：用户要求为 `docs/architecture/DATA_MODEL.md` 的数据模型图和状态流转图，在英文字段或状态后补充中文名称与简短解释，并避免文字溢出图框。
- 当前事实：目标文件包含一张 Mermaid `erDiagram`，以及 Job、Run 两张 Mermaid `stateDiagram-v2`；实体、字段与状态语义已由同文件表级契约、状态规则和根目录 `CONTEXT.md` 定义。核对时发现 ER 图写 `patch_applied`，而同文件表级契约和 SWE-Bench 原始报告字段写 `patch_successfully_applied`；当前 Python 领域结果的 `patch_applied` 是应用层映射名，数据库尚未实现。
- 已确认做法：保留英文数据库字段和状态 ID；ER 字段使用 Mermaid 官方支持的短 attribute comment，状态使用稳定 ID 加显示别名，不改变实体关系、字段类型、主外键或状态转换。ER 图的 `patch_applied` 同步为表级契约字段 `patch_successfully_applied`，只消除同一权威文档内部的命名冲突。
- 明确排除：不修改代码、数据库 schema、业务规则、状态边、其他图、模型调用、运行环境或 Git 远端。

## 实施措施

1. 从 `DATA_MODEL.md` 的表级契约、状态说明和 `CONTEXT.md` 提取中文名称与最短必要解释。
2. 为 ER 图实体与字段补充短中文注释；为 Job/Run 状态声明中英双语显示名，保留英文 ID 供状态边引用。
3. 控制单条中文说明长度；优先短名称和短职责，不把表级契约全文复制进图。
4. 核对 Mermaid 语法、字段覆盖、状态边未变化和 Markdown 差异质量；若本机有可用 Mermaid 渲染器，再执行实际渲染检查，否则如实记录限制。

完成标准：三张目标图中的英文项均有就近中文辅助说明；实体字段、键标记和状态转换与修改前一致；Markdown 和 Mermaid 语法检查无已知错误，图中文字采用短标签且无明显越框风险。

## 受影响文件树

```text
docs/
├─ actions/
│  └─ 2026-09-09-data-model-diagram-chinese-labels.md  # Action Document：记录本次范围、措施与验证结果
└─ architecture/
   └─ DATA_MODEL.md                                    # 数据模型权威文档：为 ER 与 Job/Run 状态图补充中文辅助标签
```

本次不改变现有 Module、Interface 或 Adapter，也不引入设计模式；图仍是既有数据模型和状态契约的可视化表示。

## 自验证方式

1. `git diff --check -- docs/architecture/DATA_MODEL.md docs/actions/2026-09-09-data-model-diagram-chinese-labels.md`：预期无空白或补丁格式错误。
2. 对比修改前后的 ER 字段声明与两张状态图的转换边：预期英文标识、类型、PK/FK 标记和全部转换保持不变，仅增加显示说明。
3. 检查每个 ER attribute 均有简短中文 comment，每个 Job/Run 状态均有一次中文显示声明。
4. 使用本机已有、无需下载的 Mermaid 渲染能力渲染三张图并检查节点文本；若无渲染器，记录未执行及其限制，不声称视觉验证通过。

## 自验证结果

1. 已运行 `git diff --check -- docs/architecture/DATA_MODEL.md docs/actions/2026-09-09-data-model-diagram-chinese-labels.md`，退出码为 `0`；Git 仅提示当前工作副本未来可能将 LF 转为 CRLF，没有空白或补丁格式错误。
2. 结构检查确认 ER 图共有 94 个字段声明，94 个均以短中文 comment 收尾；Job/Run 两张状态图共有 20 个中英双语状态别名。
3. 从 Git 基线与当前文件提取状态转换，前后均为 40 条且 `Compare-Object` 差异为 0；没有增加、删除或改写状态边。
4. ER 字段标注的最长源码行 53 字符，状态别名最长 77 字符；实体名和状态名使用 `<br/>` 主动换行，中文说明保持短句，以降低窄视图中的越框风险。
5. 已按 Mermaid 官方语法核对：ER attribute 使用行尾双引号 comment，实体使用 alias；状态保留稳定 ID 并使用 description alias。当前主机没有 `mmdc`，已有工作区 Node 依赖也不包含 Mermaid，因此未执行实际 SVG/PNG 渲染，不能声称已经完成像素级越框验证。最终显示仍受阅读器所用 Mermaid 版本和字体影响。
6. 对照同文件表级契约、当前领域结果和 SWE-Bench-Fork 映射，确认原 ER 图的 `patch_applied` 与表级契约命名不一致；现已只在 ER 图同步为数据库候选字段 `patch_successfully_applied`，应用层 `DeterministicResult.patch_applied` 未改。
7. 未运行代码测试、Docker、Harbor 或模型；本次没有代码、数据库迁移或运行环境变更。
