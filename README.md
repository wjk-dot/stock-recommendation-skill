# Stock Recommendation GUI

一个用于 Codex 的 A 股推荐与模拟交易 GUI skill。

本 skill 会读取上游 `a-stock-analysis` skill 提供的当日 A 股行情和分时量能数据，然后生成一个可直接在浏览器中打开的自包含 HTML 页面。页面包含：

- A 股推荐结果、推荐理由和风险提示
- 当日价格、涨跌幅、成交量、成交额和分时量能
- 支持佣金、印花税、过户费的模拟买入和卖出
- 模拟账户、持仓、浮动盈亏和净收益率
- 涨跌方向与目标幅度预测，以及结果校验

> 本项目只使用当日行情数据，不构成投资建议，也不保证收益。模拟交易不连接真实券商账户。

## 依赖关系

安装顺序如下：

1. 先安装上游 `a-stock-analysis` skill，用于获取当日行情和分时数据。
2. 再安装本仓库的 `stock-recommendation-gui` skill，用于筛选结果和生成模拟交易页面。

如果没有安装 `a-stock-analysis`，本 skill 无法获取实时行情，也不应自行编造价格、成交量或推荐理由。

## 安装

### 方式一：通过 Codex 安装

在 Codex 中依次发送：

```text
请从 GitHub 安装 a-stock-analysis skill。
```

确认上游 skill 安装完成后，再发送：

```text
请从 GitHub 安装 wjk-dot/stock-recommendation-skill，并启用其中的 stock-recommendation-gui skill。
```

安装完成后，重启或刷新 Codex，使新 skill 被加载。

### 方式二：手动从 GitHub 下载

以下命令将 skill 安装到 Codex 常用的本地 skill 目录。`CODEX_HOME` 未设置时，Windows 默认目录通常为 `%USERPROFILE%\.codex`，也可以根据本机 Codex 配置调整路径。

先安装上游依赖：

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $env:USERPROFILE ".codex\skills" }
git clone <A_STOCK_ANALYSIS_GITHUB_URL> (Join-Path $skills "a-stock-analysis")
```

再安装本 skill：

```powershell
$skills = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME "skills" } else { Join-Path $env:USERPROFILE ".codex\skills" }
git clone https://github.com/wjk-dot/stock-recommendation-skill.git (Join-Path $skills "stock-recommendation-gui")
```

`<A_STOCK_ANALYSIS_GITHUB_URL>` 应替换为上游 `a-stock-analysis` 项目的 GitHub 地址。由于行情采集 skill 是独立项目，建议从其官方仓库安装，以便获得对应版本和更新说明。

如果本地已经存在同名目录，可以使用 `git pull` 更新，而不是再次 `git clone`：

```powershell
git -C (Join-Path $skills "a-stock-analysis") pull
git -C (Join-Path $skills "stock-recommendation-gui") pull
```

### 环境要求

- Python 3.10 或更高版本
- `uv`，用于运行行情分析脚本
- 可访问行情数据接口的网络环境
- 可打开本地 HTML 文件的现代浏览器

## 使用方式

安装完成后，直接在 Codex 中发送自然语言请求即可：

```text
调用 stock-recommendation-gui，我有 1000 元，帮我推荐适合短线交易的 A 股，并生成模拟交易页面。
```

推荐流程会依次确认：

1. 计划投入资金
2. 券商佣金和最低佣金
3. 股票市场范围，例如沪深主板、创业板、科创板或全部市场
4. 持有周期，例如短线、波段或长线
5. 必要时确认风险偏好

收到确认后，Codex 会：

1. 根据市场范围和持有周期筛选候选代码。
2. 调用 `a-stock-analysis` 获取候选股票的当日行情和分时量能。
3. 结合用户资金、费率和风险偏好生成推荐标注。
4. 将行情、推荐理由、风险提示和用户配置打包成 JSON。
5. 渲染自包含 HTML 模拟交易页面并返回打开路径。

## 手动生成页面

### 1. 准备用户配置

创建 `profile.json`：

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

其中：

- `commission_rate`：佣金费率，例如万三为 `0.0003`，万五为 `0.0005`
- `min_commission_cny`：单笔最低佣金
- `stamp_duty_rate`：卖出印花税
- `transfer_rate`：买卖双向过户费
- `markets`：可选 `sh_main`、`sz_main`、`chinext`、`star`、`beijing`
- `horizon`：可选 `short`、`swing`、`long`
- `risk_level`：可选 `conservative`、`balanced`、`aggressive`

### 2. 采集上游行情

推荐使用仓库自带的 `capture_analysis.py`。它会安全处理 Windows 控制台编码，避免 PowerShell 重定向导致中文行情字段损坏：

```powershell
python scripts\capture_analysis.py 000001 600000 --minute `
  --upstream "C:\path\to\a-stock-analysis\scripts\analyze.py" `
  --output analysis.json
```

也可以直接调用上游脚本：

```powershell
uv run C:\path\to\a-stock-analysis\scripts\analyze.py `
  000001 600000 --json --minute
```

Windows 下不要使用 PowerShell 的 `>` 保存上游输出。若需要保存 JSON，请使用 `capture_analysis.py`，否则可能出现中文乱码。

### 3. 编写推荐标注

创建 `annotations.json`，按股票代码填写推荐等级、理由和风险：

```json
{
  "600000": {
    "recommendation": "buy",
    "confidence": 0.75,
    "sector": "银行",
    "reasons": [
      "当日涨跌幅和成交量支持短线观察"
    ],
    "risk_factors": [
      "短线信号可能在下一交易日失效"
    ]
  }
}
```

支持的推荐等级：`strong_buy`、`buy`、`watch`、`caution`、`avoid`。

### 4. 打包并渲染

```powershell
python scripts\pack_recommendations.py `
  --analysis analysis.json `
  --annotations annotations.json `
  --profile profile.json `
  --output recommendations.json

python scripts\render_gui.py `
  recommendations.json `
  --output dashboard.html
```

生成后的 `dashboard.html` 是自包含页面，不需要后端服务。双击文件即可打开，也可以使用本地静态服务器：

```powershell
python -m http.server 8765 --directory .
```

然后访问 <http://127.0.0.1:8765/dashboard.html>。

## 模拟交易费用

页面默认使用常见估算费率，实际费用以开户券商为准：

- 佣金：买卖双向收取，默认万三，单笔最低 5 元
- 印花税：仅卖出收取，默认 0.05%
- 过户费：买卖双向收取，默认 0.001%
- A 股买入数量：必须是 100 股的整数倍

页面允许修改资金和费率，并使用修改后的值计算买入成本、卖出净到账和持仓盈亏。交易状态、预测记录和费率设置保存在浏览器 `localStorage` 中。

## 数据和安全边界

- `a-stock-analysis` 只负责采集当日行情和分时量能。
- `stock-recommendation-gui` 负责用户画像、推荐标注、费用计算和页面渲染。
- 本项目不引入历史 K 线，不承诺未来收益，也不连接真实交易账户。
- 如果上游接口无法返回数据，页面应显示数据缺失，而不是生成虚构价格。
- 推荐理由必须引用上游返回的当日数据，不能编造历史业绩、财务指标或确定性收益。

## 项目结构

```text
stock-recommendation-skill/
├── SKILL.md
├── README.md
├── examples/sample_input.json
├── references/data-schema.md
├── scripts/capture_analysis.py
├── scripts/pack_recommendations.py
├── scripts/render_gui.py
└── templates/dashboard.html
```

## 许可证

请以仓库中的许可证文件和上游 `a-stock-analysis` 项目许可证为准。
