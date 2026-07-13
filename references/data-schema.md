# 输入 JSON 数据 Schema

`render_gui.py` 接收的 JSON 必须遵循下述结构。所有字段尽量"少而精"——只放当天能用的数据，不引入历史 K 线。

## 顶层结构

```json
{
  "meta": { ... },
  "stocks": [ ... ],
  "market_overview": { ... }   // 可选
}
```

## meta（元信息）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 页面标题，默认 "Codex 量化推荐控制台" |
| `subtitle` | string | 否 | 副标题，例如 "2026-07-13 收盘复盘" |
| `generated_at` | string (ISO 8601) | 否 | 生成时间；缺省用服务器当下时间 |
| `analyst` | string | 否 | 推荐人/模型，默认 "Codex" |
| `market_status` | string | 否 | "open" / "closed" / "pre_market"，影响顶部状态灯 |

## stocks（推荐列表）

每只股票一个对象：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | string | 是 | 6 位代码，如 "600789" |
| `name` | string | 是 | 中文名 |
| `price` | number | 是 | 当前价 |
| `open` | number | 否 | 今开 |
| `pre_close` | number | 否 | 昨收 |
| `high` | number | 否 | 最高 |
| `low` | number | 否 | 最低 |
| `volume_lots` | number | 否 | 成交量（手） |
| `amount_cny` | number | 否 | 成交额（元） |
| `change_pct` | number | 否 | 涨跌幅 %（已计算好） |
| `change_amt` | number | 否 | 涨跌额（元） |
| `recommendation` | string | 是 | strong_buy / buy / watch / caution / avoid |
| `confidence` | number (0-1) | 否 | 推荐置信度，决定徽章颜色深浅 |
| `sector` | string | 否 | 行业/板块标签 |
| `reasons` | string[] | 是 | 推荐理由，至少 1 条 |
| `risk_factors` | string[] | 否 | 风险提示 |
| `volume_distribution` | object | 否 | 分时量能，见下表 |
| `top_volumes` | object[] | 否 | 放量 TOP 列表，每条 { time, price, volume_lots, amount_cny } |
| `signals` | string[] | 否 | 上游已识别的主力动向信号 |

### volume_distribution

| 字段 | 类型 | 说明 |
|------|------|------|
| `open_30min` | number (0-100) | 早盘 30 分钟成交量占比 % |
| `mid_am` | number | 上午中段占比 % |
| `mid_pm` | number | 下午中段占比 % |
| `close_30min` | number | 尾盘 30 分钟占比 % |

四者之和应接近 100；不要求严格相等，渲染器做归一化。

## market_overview（可选）

大盘概览卡片。可包含：
- `sh_index` / `sz_index` / `cyb_index`: { price, change_pct }
- `up_count`, `down_count`, `limit_up_count`, `limit_down_count`

## 完整示例

见 `examples/sample_input.json`。
