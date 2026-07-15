# 量化后端使用说明

本项目现在由两个运行层组成：

- `stock-recommendation-gui` Skill：负责自然语言意图、个性化问答、调用 `a-stock-analysis` 和生成推荐页面。
- `backend/` 量化后端：负责历史行情缓存、K 线接口、带交易成本的均线回测和市场资金流向适配器。

## 启动

需要 Docker Desktop 时，在仓库根目录执行：

```powershell
docker compose up --build
```

健康检查地址：`http://127.0.0.1:8000/api/health`。

本地开发环境也可以执行：

```powershell
cd backend
uv sync --group dev
uv run --group dev uvicorn app.main:app --reload
uv run --group dev pytest -q
```

若要启用 AkShare 市场资金流向适配器，额外执行 `uv sync --extra market-flow`；核心 K 线和回测不依赖 AkShare。

## API

日线行情：

```text
GET /api/stocks/{symbol}/daily?start=2024-01-01&end=2024-12-31
```

回测：

```text
POST /api/backtests
```

请求体至少包括 `symbol`、`start_date`、`end_date`、`strategy`、`parameters`、`initial_cash` 和 `fees`。第一版策略是 `ma_cross`，默认信号在收盘后产生，下一交易日开盘成交，交易数量必须是 100 股的整数倍。

市场资金流向：

```text
GET /api/market-flow
```

该接口优先使用 AkShare 适配器。接口失败时返回 `source=unavailable` 和 `warnings`，页面必须显示不可用状态，不能用推荐池数据冒充全市场资金流向。

## 数据与费用

Baostock 用于历史日线按需同步，数据写入 `data/market.duckdb`，通过 Docker volume 持久化。AkShare 是可替换的市场级数据适配器，不需要下载完整历史数据库。

默认费用仅用于研究模拟：佣金万三、单笔最低 5 元、卖出印花税千分之五、双向过户费万分之零点一、滑点万分之二。用户实际费率应以开户券商为准。

## Skill 路由

- 提到“历史 K 线”“日线走势”“均线”：调用 `/api/stocks/{symbol}/daily`。
- 提到“回测”“策略收益”“最大回撤”：确认股票、区间、策略、资金和费用后调用 `/api/backtests`。
- 提到“市场资金流向”“板块资金”“主力资金”：调用 `/api/market-flow`，并展示数据时间、来源和范围。
- 只要求当日荐股、当日模拟交易或涨跌预测：继续使用现有 `a-stock-analysis` 和自包含 HTML 流程。

QVeris 暂不作为核心历史回测数据源。若将来接入，API Key 和调用费用必须由运行环境的用户自行配置。
