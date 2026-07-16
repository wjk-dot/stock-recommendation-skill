# 推荐会话发布流程

统一量化工作台不再直接读取某个浏览器本地文件。Skill 完成荐股后，将结构化结果发布给 Docker 后端；工作台读取最新推荐会话，再把用户点击的股票带入 K 线、回测和资金流研究区。

当前统一工作台已经包含：

- 推荐中心：推荐原因、风险提示和用户画像；
- 个股研究：日线 K 线、MA5/MA20；
- 历史回测：均线交叉策略，佣金、最低佣金、印花税、过户费和滑点均计入；
- 模拟盘：A 股 100 股整手、买入/卖出费用、可用现金、持仓净值与盈亏；
- 涨跌预测：记录看涨/看跌方向与目标幅度；
- 市场资金流：可用时展示行业资金流，数据源不可用时不伪造结果。

模拟盘和预测记录仅保存在当前浏览器 `localStorage`。每次发布一个新的推荐会话时，模拟账户会按新会话的用户资金重新初始化，避免不同荐股轮次的资金和持仓混在一起。
## 涨跌预测的自动验算

预测记录也只保存在浏览器 `localStorage`，不会上传到后端。新建预测时，工作台会固化以下信息：

- 推荐会话 ID、股票代码与名称；
- 看涨 / 看跌方向和用户填写的目标幅度；
- **建立时的推荐报价**；
- 推荐会话生成日（作为预测基准交易日）。

点击“刷新验算”或重新加载推荐会话后，页面会调用已有的：

```text
GET /api/stocks/{symbol}/daily?start=基准日期&end=当天
```

验算只使用基准交易日之后的最近一个可用日线收盘价：

```text
实际收益 = (后续收盘价 / 建立时推荐报价 - 1) × 100%
```

- 看涨方向命中：实际收益 `> 0`；看跌方向命中：实际收益 `< 0`；
- 看涨目标命中：实际收益 `>= 目标幅度`；看跌目标命中：实际收益 `<= -目标幅度`；
- 方向命中与目标命中是两个独立结果；没有后续交易日时显示“等待后续行情”；
- 行情接口不可用时显示明确错误，不会用推荐报价或当前页面数据伪造结果；
- 旧版本预测没有保存基准报价和交易日，显示“无法自动验算”，必须新建预测记录。

这只是对已记录观点的机械核对，不代表任何投资建议或收益承诺。

## 前置条件

在项目根目录启动本地服务：

```powershell
.\scripts\start-docker.ps1
```

服务地址：

- API：`http://127.0.0.1:8765/api`
- 统一工作台（后续页面）：`http://127.0.0.1:8765/templates/workbench.html`

## Skill 调用链

```text
a-stock-analysis 当日行情
        ↓
scripts/capture_analysis.py（统一 UTF-8）
        ↓
scripts/pack_recommendations.py（行情 + Codex 理由 + 用户画像）
        ↓
recommendations.json
        ↓
scripts/publish_recommendations.py
        ↓
POST /api/recommendations
        ↓
工作台 GET /api/recommendations/latest
```

## 发布命令

先生成 `recommendations.json`：

```powershell
python scripts\pack_recommendations.py `
  --analysis analysis.json `
  --annotations annotations.json `
  --profile profile.json `
  --output recommendations.json
```

再发布：

```powershell
python scripts\publish_recommendations.py recommendations.json
```

如本机 Python 命令未配置，可使用已有虚拟环境解释器：

```powershell
& .\backend\.venv\Scripts\python.exe scripts\publish_recommendations.py recommendations.json
```

只校验 JSON 结构且不写入后端：

```powershell
python scripts\publish_recommendations.py recommendations.json --dry-run
```

脚本会输出会话 ID 和统一工作台 URL。它按 UTF-8 原始字节读写 JSON，避免 PowerShell 文本重定向导致股票中文名称乱码。

## API 约定

- `POST /api/recommendations`：新建一份推荐会话；每只股票必须带 6 位数字 `code`。
- `GET /api/recommendations/latest`：读取最新会话。
- `GET /api/recommendations/{session_id}`：读取指定历史会话。

运行时会话文件保存在 `data/recommendations/`，该目录不会提交到 Git，也不会上传真实用户资金或推荐数据。

若尚未发布会话，`GET /latest` 会返回 `404` 与结构化错误码 `recommendation_session_missing`。
