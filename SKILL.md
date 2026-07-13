---
name: stock-recommendation-gui
description: 把 Codex 的 A 股推荐结果打包成可交互的 HTML 量化回测 GUI，包含推荐展示区、模拟交易区、涨跌预测区，并在正式荐股前通过简短问答收集资金、费率、市场范围和持有周期，提升推荐个性化。行情数据来源于 a-stock-analysis skill（仅当日，不引入历史数据）。Use when: (1) 用户希望可视化 Codex 的 A 股推荐结果并查看推荐理由, (2) 用户希望做模拟盘演练（输入资金、模拟买入、查看当日浮动盈亏）, (3) 用户希望对推荐股票做当日涨跌方向+目标幅度的预测与校验, (4) 用户要求推荐 A 股并希望结合资金、板块范围或持有周期进行筛选。
---

# Stock Recommendation GUI (A 股)

把 Codex 选出来的 A 股推荐结果，连同推荐理由、风险提示、分时量能等当日数据，渲染成一个自包含、可直接在浏览器里打开的交互式 HTML 页面。页面在浏览器侧用 JavaScript 模拟交易、记录涨跌预测，状态用 localStorage 持久化，不需要任何后端。

> 数据源：本 skill 不直接联网，所有行情数据来自上游 a-stock-analysis skill 在 Codex 内采集到的当日实时行情 + 分时量能分析。

## 个性化问答阶段（必须先做）

每次本 skill 被用于“荐股”或“模拟交易”时，在调用 a-stock-analysis 采集行情前，先明确告诉用户：

> 在开始分析前，我会用 4 个很短的问题确认你的交易边界。目的是让推荐结果、可买数量和模拟盘费用更贴合你的实际情况；每题只需一句话回答，也可以回复“跳过”，我会使用默认值继续。

然后一次只问一个问题，等待用户回答后再问下一题。不要把 4 个问题一次性堆给用户，也不要在用户没有回答资金问题时直接假定其资金规模。推荐使用下面的顺序和简短措辞：

1. `这次计划用于买入的资金大约是多少？请填人民币金额，例如 1000；如果只想看推荐，也可以回复“只看推荐”。`
2. `你的券商费率知道吗？可直接填“万三/最低 5 元”，或回复“按常见默认费率”。`
3. `股票范围包括哪些？可选“沪深主板”“加创业板”“加科创板”“加北交所（北京市场）”，也可以回复“全部”。`
4. `你更偏向哪种持有方式？“短线（1-5 个交易日）”“波段（几周）”还是“长线（数月以上）”？`

必要时可追加一个风险确认问题，但只有在用户没有表达风险偏好、且候选股票波动明显时追加：`你能接受多大波动？“稳健”“均衡”还是“激进”？` 不超过 5 个问题。

### 问答标准化

Codex 收齐回答后，先用一行复述确认，例如：`我将按 1000 元、默认费率、沪深主板、短线来筛选，确认后开始采集当日行情。` 用户确认或没有纠正后，才调用 a-stock-analysis。

将回答整理为 `user_profile`，并传入本 skill 的输入 JSON：

```json
{
  "capital_cny": 1000,
  "only_recommendations": false,
  "fees": {
    "commission_rate": 0.0003,
    "min_commission_cny": 5,
    "stamp_duty_rate": 0.0005,
    "transfer_rate": 0.00001
  },
  "markets": ["sh_main", "sz_main"],
  "horizon": "short",
  "risk_level": "balanced",
  "confirmed": true
}
```

默认值：资金未提供时使用 `100000` 元仅用于页面演示，并明确标注“演示资金”；费率使用页面默认的佣金万三、最低 5 元、印花税卖出 0.05%、过户费双向 0.001%；市场范围默认沪深主板；持有周期默认波段；风险等级默认均衡。若用户回答“只看推荐”，仍需获取市场范围和持有周期，但 GUI 模拟交易区可以使用演示资金。用户说“跳过”不等于授权使用其真实资金，必须在复述时明确哪些字段采用了默认值。

### 个性化筛选规则

- 只把 `user_profile.markets` 允许的股票代码交给 a-stock-analysis；不要先分析再把不符合市场范围的股票当作推荐结果展示。
- `short` 优先选择当日量价、早盘/尾盘量能和主力动向清晰的标的；`swing` 增加板块强弱和支撑/压力位解释；`long` 降低对单日异动的权重，并明确说明仅凭当日数据不能替代长期基本面研究。
- 推荐理由必须引用 a-stock-analysis 返回的当日数据，不能因为用户偏好而编造历史业绩、财务数据或未来确定收益。
- 资金不足以买入 1 手时，不要硬凑推荐；在理由中标明“按当前价格和费用，资金不足以买入 100 股”，并优先给出价格更低且符合用户范围的候选。
- 费率会影响推荐排序和模拟买入能力，但不改变行情原始数据。页面必须把用户费率带入模拟盘，并允许用户在页面中修正。

## 工作流（Codex 侧）

1. 完成上面的个性化问答并生成 `user_profile`。
2. 按市场范围与持有周期筛选候选代码，用 a-stock-analysis 采集候选股票当日数据：
   ```bash
   uv run {baseDir of a-stock-analysis}/scripts/analyze.py 600789 002446 300750 --json --minute
   ```
   Windows 下不要使用 PowerShell 的 `>` 重定向保存这段输出。请使用捕获脚本，它会从原始字节解码上游 GBK 输出并统一写成 UTF-8：
   ```bash
   uv run {baseDir}/scripts/capture_analysis.py 600789 002446 300750 --minute --upstream "{baseDir of a-stock-analysis}/scripts/analyze.py" --output analysis.json
   ```
   打包器和渲染器会拒绝 `�`、`锟斤拷` 等不可恢复乱码；出现提示时请重新采集 `analysis.json`。
   - 加 --json 输出结构化数据
   - 加 --minute 拉分时量能（推荐区需要展示早盘/尾盘占比）
3. Codex 解读采集结果，结合 `user_profile` 给每只候选股票打上推荐标签（strong_buy / buy / watch / caution / avoid），撰写推荐理由与风险提示。
4. Codex 把以上结果和 `user_profile` 封装成 JSON（schema 见 references/data-schema.md），写入临时文件（例如 recommendations.json）。
5. Codex 调用本 skill 生成 GUI：
   ```bash
   uv run {baseDir}/scripts/render_gui.py recommendations.json --output recommendations.html
   ```

   若使用 `pack_recommendations.py`，可把问答结果单独保存为 `profile.json`，并加入 `--profile profile.json`：
   ```bash
   uv run {baseDir}/scripts/pack_recommendations.py --analysis analysis.json --annotations annotations.json --profile profile.json --output recommendations.json
   ```
6. Codex 把生成的 HTML 路径（或 file:// 链接）返回给用户，让用户在浏览器中打开。
7. 用户在浏览器里进行含交易费用的模拟买卖、做涨跌预测；页面状态保存在 localStorage。

## 触发条件

满足以下任一情况时，Codex 应该考虑调用本 skill：
- 用户说"推荐几只股票"、"看看哪些股今天有机会"、"做个量化回测看推荐"
- 用户说"模拟盘"、"模拟交易"、"用 X 万资金演练"
- 用户说"预测一下明天涨跌"、"做个涨跌预测"、"赌一把方向"
- 用户已经收到 Codex 的 A 股推荐列表，主动想要可视化/可交互版本

## 关键约定

- 颜色：A 股惯例——红色表示上涨/买入、绿色表示下跌/卖出。严禁反色。
- 货币：所有金额用人民币元（CNY）展示，大额自动切万/亿。
- 时间：默认使用 Asia/Shanghai，生成时间戳取 Codex 调用本 skill 的瞬间。
- 数据新鲜度：模板顶部会显示数据时间戳和延迟提示。一旦标的接近涨停/跌停，推荐理由里要写明封板状态。
- 本地持久化：持仓、预测、模拟账户余额和费率设置都存在 localStorage，键名前缀 stockRecGui.*。下次打开同一 HTML 仍在。
- 个性化配置：页面会显示本次筛选的资金、市场范围、持有周期和风险等级；资金与费率会作为模拟盘初始值。用户在页面修改费率后，以页面修改值为准。

## 模拟交易费用口径

- 佣金：买入、卖出双向收取，默认费率 0.03%（万三），单笔最低 5 元。
- 印花税：仅卖出收取，默认费率 0.05%。
- 过户费：买入、卖出双向收取，默认费率 0.001%。
- 金额精度：每项费用按人民币分四舍五入，再汇总为总费用。
- 买入校验：买入总支出 = 成交金额 + 佣金 + 过户费；仓位快捷按钮按含费后的可用资金计算最大整手数量。
- 持仓盈亏：按当前价全部卖出的净到账估值，已预扣预计卖出佣金、印花税和过户费。
- 卖出结算：卖出净到账 = 成交金额 - 佣金 - 印花税 - 过户费；净到账进入可用资金。
- 费率可在页面中修改并持久化。默认值仅为常见估算，实际费用以开户券商为准。

## 输出文件结构

- recommendations.html：单文件 HTML，包含嵌入的 JSON 数据 + CSS + JS；双击或浏览器打开即可用。

## 失败回退

- 如果 a-stock-analysis 拉不到数据，对应股票卡片渲染为"数据缺失"占位，提示用户重试或跳过该股，不要凭空生成价格。
- 如果 JSON 字段缺失，GUI 应优雅降级（如隐藏迷你 K 线、隐藏成交量分布柱），不要崩溃。

## 子文件

- references/data-schema.md：输入 JSON 的字段说明与示例
- scripts/render_gui.py：把 JSON 渲染成 HTML 的入口
- scripts/pack_recommendations.py：辅助脚本：把 a-stock-analysis --json 的输出 + Codex 的标注，自动打包成 skill 输入 JSON
- examples/sample_input.json：一份可直接喂给渲染器的样例数据
