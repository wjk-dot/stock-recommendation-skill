---
name: stock-recommendation-gui
description: 把 Codex 的 A 股推荐结果打包成可交互的 HTML 量化回测 GUI，包含推荐展示区、模拟交易区、涨跌预测区。行情数据来源于 a-stock-analysis skill（仅当日，不引入历史数据）。Use when: (1) 用户希望可视化 Codex 的 A 股推荐结果并查看推荐理由, (2) 用户希望做模拟盘演练（输入资金、模拟买入、查看当日浮动盈亏）, (3) 用户希望对推荐股票做当日涨跌方向+目标幅度的预测与校验。
---

# Stock Recommendation GUI (A 股)

把 Codex 选出来的 A 股推荐结果，连同推荐理由、风险提示、分时量能等当日数据，渲染成一个自包含、可直接在浏览器里打开的交互式 HTML 页面。页面在浏览器侧用 JavaScript 模拟交易、记录涨跌预测，状态用 localStorage 持久化，不需要任何后端。

> 数据源：本 skill 不直接联网，所有行情数据来自上游 a-stock-analysis skill 在 Codex 内采集到的当日实时行情 + 分时量能分析。

## 工作流（Codex 侧）

1. 用 a-stock-analysis 采集候选股票当日数据：
   ```bash
   uv run {baseDir of a-stock-analysis}/scripts/analyze.py 600789 002446 300750 --json --minute
   ```
   - 加 --json 输出结构化数据
   - 加 --minute 拉分时量能（推荐区需要展示早盘/尾盘占比）
2. Codex 解读采集结果，给每只候选股票打上推荐标签（strong_buy / buy / watch / caution / avoid），撰写推荐理由与风险提示。
3. Codex 把以上结果封装成 JSON（schema 见 references/data-schema.md），写入临时文件（例如 recommendations.json）。
4. Codex 调用本 skill 生成 GUI：
   ```bash
   uv run {baseDir}/scripts/render_gui.py recommendations.json --output recommendations.html
   ```
5. Codex 把生成的 HTML 路径（或 file:// 链接）返回给用户，让用户在浏览器中打开。
6. 用户在浏览器里进行含交易费用的模拟买卖、做涨跌预测；页面状态保存在 localStorage。

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
