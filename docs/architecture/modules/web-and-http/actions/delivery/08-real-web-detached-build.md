# 行动：用真实 apps/web 组件做脱离版单文件（取代 06）

> 状态：**已完成**（2026-09-21）。本行动**取代** [06-full-web-standalone-prototype.md](06-full-web-standalone-prototype.md)——那份记录的是被 A 否决并已删除的"自造外观"原型。

## 1. 情况说明

**来源**：A 看过自造原型后明确否决："刚做的页面很差，要根据拉取到的 web 文件夹里现有的前端进行修改，旧的完全不行，不要了"。B 随即删除 `runtime/prototype/ui-full-web-20260921/`（含 5 张截图；`runtime/tests/` 下的通用工具保留）。

**新路线**：不再仿造外观，而是**把 `apps/web` 的真实组件打成脱离版**，**不改动 `apps/web` 任何文件**。可行性依据（全部经代码核实）：

| 事实 | 依据 |
|---|---|
| 真实前端只有一个路由 | `src/app/page.tsx` 渲染 `<SessionPanel />`，其余是组件内视图切换 |
| 全仓只有一处 `fetch(` | `src/lib/api-client.ts:43`，全部客户端都经它 |
| 无 Next 运行时导入 | 除 `layout.tsx` 的 `Metadata` 类型外，无 `next/link`、`next/navigation`、`next/font` 等 |
| 无服务端专属能力 | 无 `cookies()`/`headers()`/`next/headers` |
| 无外部资源 | `globals.css` 与 `layout.tsx` 无字体、图片、CDN 引用 |

**做法**：外层壳（`harness/`）挂载真实 `SessionPanel` 与真实 `globals.css`，把 `window.fetch` 换成对**录制响应**的回放；用 esbuild 打成单文件 HTML。数据不是我造的——**从仓库自带的合成后端 `apps/backend/tests/identity/browser_server.py` 录制**。

**明确不做**：不改 `apps/web`（0 个字节）；不改后端；不引入新的产品接口；原型不进入仓库（`runtime/` 被 `.gitignore:55` 忽略）。

## 2. 实施措施

1. 删掉被否决的原型与其截图。
2. 摸底真实前端结构，确认上述可行性事实。
3. **录制**：子代理写一次性 Playwright 用例 `apps/web/tests/zz-record-api.spec.ts`（用现成配置启动夹具后端与前端 dev），登录 owner 后走遍所有视图、筛选、分页、钻取，抓 `/api/v1/**` 的真实响应；跑完删除该临时用例。第二轮补录把**列表里每个批次都点开一遍**，并让 `members`/`invitations` 以"最终态"为准。
4. **构建**：`build.mjs` 用本地 esbuild（原型目录内 `npm install`，不入仓库）打包 `harness/entry.tsx`，把 CSS 与 JS 内联成 `standalone.html`。
5. **实测**：一次性探针打开 `file://` 与 `http://` 两种入口，逐视图做**内容级断言**、点击动线、窄屏溢出检查与截图。

**完成标准**：8 个视图与批次详情、对比矩阵都渲染出真实内容；回放无"未录到"；无脚本报错；390px 不横向溢出。

## 3. 实际文件树（`runtime/prototype/real-web-detached-20260921/`，**gitignored**）

| 路径 | 职责 |
|---|---|
| `harness/entry.tsx` | 脱离版入口：挂载真实 `SessionPanel` 与真实 `globals.css` |
| `harness/mock-api.js` | 回放层：假 `fetch`（精确→最接近→503）、`file://` 的 history 垫片、制品下载拦截 |
| `mock/responses.json` | **录制的真实响应**：141 条，32 个端点族，含 27 个批次详情 |
| `build.mjs` | esbuild 打包 + 内联成单文件（`--minify` 为交付版） |
| `standalone.html` | **交付物**：542 KB，双击即开 |
| `serve/index.html` | 同一交付物的服务副本（供在线查看，非交付物） |
| `package.json` / `node_modules/` | 只装 esbuild，仅供构建 |

验证工具留在 `runtime/tests/`：`zz-detached-realweb-probe.mjs`（本行动）、`build-standalone.mjs`、`check-links.py`。

## 4. 自验证方式

```bash
node runtime/prototype/real-web-detached-20260921/build.mjs --minify
node runtime/tests/zz-detached-realweb-probe.mjs "http://127.0.0.1:8899/index.html"
node runtime/tests/zz-detached-realweb-probe.mjs   # 默认跑 file:// 入口
```

**成功标准**：输出"全部检查通过"；回放统计中"未录到"必须为 0；不得出现 `pageerror`/`console error`。

## 5. 自验证情况

**实跑结果**：`file://` 与 `http://` 两个入口**均"全部检查通过"**：

```text
真实外壳渲染成功，主导航 8 项
8 个视图内容断言全过（工作台"待处理审批"、评测"状态筛选"、任务目录 example__repo-1、
配置目录 Synthetic Codex/Terra、成员管理 邀请码/协作者、排行榜 查询排行榜、向导 三步提交…）
批次详情：934 字，含 冻结运行数/批次/限制/任务/配置/网络策略/工具策略/冻结版本/所有者决定
对比矩阵：勾选两个批次后出现 未解决/缺失（五档结果词）
回放统计：精确命中 22 · 最接近回放 0 · 未录到 0
窄屏 390px：无横向溢出
```

**过程中修掉的三个真缺陷**（都只有实测才会暴露，且都会让页面看起来"坏了"）：

| # | 现象 | 根因 | 处理 |
|---|---|---|---|
| 1 | 所有页面变成"暂时无法连接平台" | `file:///D:/api/v1/...` 的 `pathname` 带盘符，前缀判断 `startsWith("/api/v1/")` 不命中，请求漏到真实网络被 CORS 拦 | 改为在路径中定位 `/api/v1/` 标记后截取 |
| 2 | **批次详情整页只剩标题** | 真实代码调 `pushState(null, "", url)` 传的是 **URL 对象**，垫片只认字符串 → 写进去的 `?job=` 从未被记住 → 详情组件读到空参数，一个请求都不发 | 垫片同时接受字符串与 `URL` 对象 |
| 3 | 制品"下载"点了没反应 | 下载链接是 `<a href="/api/v1/artifacts/{id}/content">`，`file://` 下会去取本地文件 | 拦下点击，把录到的真实正文做成浏览器下载 |

**探针加固（重要教训）**：第一轮探针只断言"文本长度 ≥ N 字"，因此**放过了 #2（整页只剩标题也一样够长）**。已改为**内容级断言**（每页必须出现指定真实字符串、详情必须存在 `article[aria-label=评测批次详情]` 且含"冻结运行数/限制/任务/配置"、对比页勾选后必须出现五档结果词）。改完立刻抓出了数据缺口（见下）。

**数据覆盖**：第一轮录制只有 6 个批次详情，而列表第一页是录制时程序化创建的批次 → 点开即空。已让子代理**逐页逐行点开列表里全部 27 个批次**重录，自查"列表 27 个 job_id ↔ 27 条详情，缺失 0"。

**未验证 / 局限（如实记录）**：

- 写操作（批准/取消/提交/建邀请码/停用成员）**只回放录到的响应，不改变状态**；页面底部有常驻说明。
- 录制里含夹具的真实异常：2 个批次的 `reports/jobs/{id}` 返回 **500**、2 个 Run 的轨迹返回 **409 `ARTIFACT_NOT_READY`**——按原样回放，不是缺陷。
- 详情快照遵循"首次为准"，被拒绝/取消的批次显示的是**决策前**的状态。
- 未录到的组合（`加载更多轨迹`、各列表的 `cursor=` 变体）会回落到同路径最接近的一次真实响应；排行榜需先填条件再查询（真实 UX）。
- 只在系统 Chrome 无头下验证；未做无障碍审计；未在真机触屏验证。
