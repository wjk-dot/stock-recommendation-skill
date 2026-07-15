# A 股推荐与量化研究平台实施计划

> **For Codex:** 本计划用于逐项实施本项目。每完成一个阶段，都要运行对应测试并记录验证结果。

**目标：** 将现有 `stock-recommendation-gui` Skill 升级为一个可本地运行、可逐步部署的 A 股推荐、K 线、历史回测、模拟交易和市场资金流向平台。

**架构：** Skill 继续负责自然语言意图识别、个性化提问、调用 `a-stock-analysis` 和组织结果。新增的 FastAPI 后端负责行情数据、缓存、回测计算和统一 JSON API。历史行情优先由 Baostock 同步并保存到 DuckDB，实时行情和市场资金流向由可替换的 AkShare 适配器提供；前端先复用现有自包含 HTML，逐步增加后端驱动的 K 线和回测页面。

**技术栈：** Python 3.10+、FastAPI、Pydantic、DuckDB、Pandas、Baostock、AkShare（可选）、ECharts 或轻量 Canvas 图表、Docker Compose、pytest。

---

## 交付边界

### 第一阶段：可运行垂直闭环

- `GET /api/health` 健康检查。
- `GET /api/stocks/{symbol}/daily` 查询日线数据。
- 单股 K 线、成交量和均线展示。
- 单股均线交叉历史回测。
- 回测支持初始资金、佣金、最低佣金、印花税、过户费、滑点、100 股整数交易单位。
- 输出收益、最大回撤、交易次数、交易明细和资金曲线。
- 没有网络或数据源不可用时，不伪造价格，返回明确错误。

### 第二阶段：平台能力

- 将推荐 GUI 的第四个板块接入市场资金流向。
- AkShare 市场级数据适配器和短期缓存。
- 推荐池资金动向与全市场资金流向分开展示。
- 现有模拟交易规则迁移为后端可复用的成本模型。
- Docker Compose 本地一键启动。

### 暂缓项

- 实盘交易和券商账户接入。
- 高频行情和分钟级真实回测。
- 参数优化、机器学习选股和多用户鉴权。
- 将 QVeris 作为核心历史数据仓库。

## 目录规划

```text
stock-recommendation-skill/
├── SKILL.md                         # Agent 入口、意图路由和人工配置说明
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 应用
│   │   ├── config.py                # 环境变量和数据目录
│   │   ├── models.py                # 请求/响应模型
│   │   ├── api/                     # health, stocks, backtest, market_flow
│   │   ├── data/                    # provider、清洗、DuckDB 仓储
│   │   └── backtest/                # 成本模型和策略引擎
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── data/                            # 运行时数据，通过 volume 持久化
├── docker-compose.yml
├── docs/plans/
├── scripts/                         # 现有 Skill 脚本
├── templates/                       # 现有自包含推荐 GUI
└── tests/                           # 现有 Skill 测试
```

## 数据契约

统一日线字段：`symbol`, `trade_date`, `open`, `high`, `low`, `close`, `volume`, `amount`, `adjust_factor`。

回测必须声明：复权方式、成交时点、费用参数、滑点、涨跌停和停牌处理。第一版采用前复权研究数据，信号在收盘后产生，下一交易日开盘成交；缺失数据、停牌和无法成交的记录必须进入 `warnings`，不得静默填充。

市场资金流向必须标记 `source`、`as_of`、`scope` 和统计口径。若只有推荐池数据，页面只能命名为“推荐池资金动向”，不能冒充全市场数据。

## API 草案

```text
GET  /api/health
GET  /api/stocks/{symbol}/daily?start=2020-01-01&end=2025-12-31&adjust=前复权
POST /api/backtests
GET  /api/backtests/{job_id}
GET  /api/market-flow
```

回测请求至少包含：`symbol`、`start_date`、`end_date`、`strategy`、`parameters`、`initial_cash` 和 `fees`。回测响应包含：`total_return`、`annual_return`、`max_drawdown`、`trade_count`、`equity_curve`、`trades` 和 `warnings`。

## 验收标准

1. 在无 Docker 的本地 Python 环境中可运行后端测试。
2. 使用固定 fixture 数据时，回测结果可重复并能人工核算交易成本。
3. API 不会把缺失行情转换成 0 或虚构价格。
4. 前端能显示 K 线、买卖点、收益曲线和回测摘要。
5. 现有推荐、费用模拟和预测功能不回归。
6. Docker Compose 启动后，健康检查接口返回成功。
7. README 明确区分 Skill、后端、数据源和 Docker 的职责，并列出必须由用户手动提供的配置。

## 必须由用户手动完成的事项

- 若使用 AkShare 的市场资金流向接口，用户需要允许运行环境联网；不需要下载海量历史数据。
- 若部署到云服务器，用户需要提供服务器、域名或反向代理配置；本地开发不需要。
- 若使用 QVeris 作为可选备用数据源，用户需要自行申请并配置 `QVERIS_API_KEY`，调用可能消耗 credits。
- 真实券商费率只能由用户根据自己的开户券商确认，页面默认值仅用于模拟研究。

