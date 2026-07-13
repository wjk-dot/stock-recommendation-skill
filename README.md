# Stock Recommendation Skill

一个用于 Codex 的 A 股荐股与模拟交易 GUI skill。

它会调用上游的 `a-stock-analysis` skill 获取当日行情和分时量能数据，然后生成一个可以直接在浏览器打开的 HTML 页面，页面包含：

- Codex 推荐股票及推荐理由
- 交易费用设置
- 含佣金、印花税、过户费的模拟买入和卖出
- 资金、持仓、净盈亏和净收益率统计
- 股票涨跌预测与结果校验

本项目只使用当日行情数据，不构成投资建议，也不会保证收益。

## 一、如何调用

确保这个 skill 已经安装或配置到 Codex 后，直接在 Codex 对话中使用自然语言调用即可。

最简单的说法：

```text
调用 stock-recommendation-gui，帮我推荐几只 A 股。
```

也可以直接说明需求：

```text
调用 stock-recommendation-gui，我有 1000 元，帮我推荐适合短线交易的 A 股，并生成模拟交易页面。
```

或者：

```text
请使用 stock-recommendation-gui，分析几只沪深主板股票，包含推荐理由、交易费用和模拟买入功能。
```

如果用户直接说下面这些话，Codex 也应该考虑调用本 skill：

- `帮我推荐几只 A 股`
- `我有 1000 元，适合买什么股票？`
- `帮我做一个 A 股模拟盘`
- `分析今天哪些股票有机会，并生成 GUI`
- `预测这些股票明天涨跌`

## 二、调用后会发生什么

调用荐股功能后，skill 会先向用户说明：

```text
在开始分析前，我会用 4 个很短的问题确认你的交易边界。
目的是让推荐结果、可买数量和模拟盘费用更贴合你的实际情况。
每题只需一句话回答，也可以回复“跳过”，使用默认值继续。
```

随后会一次询问一个问题，不会把所有问题一次性发出来：

1. 计划用于买入的资金，例如 `1000 元`
2. 券商费率，例如 `万三，最低 5 元`
3. 股票范围，例如 `沪深主板`、`全部`、`加创业板`
4. 持有周期，例如 `短线`、`波段` 或 `长线`

如果用户没有明确风险偏好，候选股票波动又比较大，skill 可能会追加一个问题：`稳健、均衡还是激进？`

用户可以在任意问题中回复 `跳过`。此时会采用默认值，并在开始分析前明确告诉用户哪些内容使用了默认设置。

## 三、推荐对话示例

```text
用户：调用 stock-recommendation-gui，帮我推荐几只 A 股。

Codex：在开始分析前，我会用 4 个很短的问题确认你的交易边界。
      目的是让推荐结果、可买数量和模拟盘费用更贴合你的实际情况。
      每题只需一句话回答，也可以回复“跳过”。
      这次计划用于买入的资金大约是多少？

用户：1000 元

Codex：你的券商费率知道吗？例如“万三，最低 5 元”，也可以回复“按默认费率”。

用户：按默认费率

Codex：股票范围包括哪些？沪深主板、创业板、科创板、北交所，还是全部？

用户：沪深主板

Codex：你更偏向短线、波段还是长线？

用户：短线

Codex：我将按 1000 元、默认费率、沪深主板、短线来筛选，开始采集当日行情。
```

之后 Codex 会调用 `a-stock-analysis` 获取当日数据，结合用户画像进行筛选，并生成 HTML GUI。

## 四、生成的页面怎么用

生成后，Codex 会返回 HTML 文件路径。双击该文件，或用浏览器打开即可。

页面主要分为三个区域：

### 推荐展示

查看每只股票的：

- 当前价格、涨跌幅、成交量和成交额
- 推荐等级和置信度
- 推荐原因
- 风险提示
- 早盘、午盘和尾盘量能分布

### 模拟交易

1. 确认初始资金和交易费用设置。
2. 选择股票和买入价格。
3. 输入数量，数量必须是 `100` 股的倍数。
4. 点击 `满仓`、`半仓` 等快捷按钮，或手动输入数量。
5. 点击 `买入`，系统会检查成交金额加交易费用是否超过可用资金。
6. 卖出时会扣除佣金、印花税和过户费，并计算实际净盈亏。

默认费用为：佣金万三、单笔最低佣金 5 元、印花税卖出 0.05%、过户费双向 0.001%。实际费用以用户开户券商为准，可以在页面中修改。

### 涨跌预测

用户可以为每只推荐股票提交：

- 涨或跌
- 目标涨跌幅
- 预测信心

点击 `一键校验` 后，页面会使用当前输入数据中的涨跌幅进行结果校验。

## 五、手动生成 GUI

通常不需要手动执行脚本，Codex 会自动完成。如果需要自己生成页面，可以使用下面的命令。

### 直接渲染推荐 JSON

```powershell
python scripts\render_gui.py examples\sample_input.json --output dashboard.html
```

生成后打开项目目录中的 `dashboard.html`。

### 使用独立的用户画像

可以把荐股前问答结果保存为 `profile.json`：

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

然后使用打包脚本：

```powershell
python scripts\capture_analysis.py 000001 600000 --minute `
  --upstream "C:\path\to\a-stock-analysis\scripts\analyze.py" `
  --output analysis.json

python scripts\pack_recommendations.py `
  --analysis analysis.json `
  --annotations annotations.json `
  --profile profile.json `
  --output recommendations.json

python scripts\render_gui.py `
  recommendations.json `
  --output recommendations.html
```

其中：

- `analysis.json` 是 `a-stock-analysis --json --minute` 的输出。
- `annotations.json` 是 Codex 对股票的推荐等级、推荐理由和风险提示。
- `profile.json` 是荐股前个性化问答的结果。

## 六、依赖关系

- 上游数据 skill：`a-stock-analysis`
- Python：`3.10` 或更高版本
- GUI：浏览器即可，无需后端服务
- 页面状态：保存在浏览器 `localStorage` 中

详细输入字段请查看：[references/data-schema.md](references/data-schema.md)

详细 skill 工作流请查看：[SKILL.md](SKILL.md)
