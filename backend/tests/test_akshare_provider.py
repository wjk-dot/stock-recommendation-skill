from types import SimpleNamespace

import pandas as pd

from app.data.akshare_provider import AkShareProvider


def test_ths_market_flow_converts_yi_to_cny_and_keeps_both_directions():
    frame = pd.DataFrame(
        [
            {"行业": "流入行业", "净额": 12.5, "行业-涨跌幅": 2.1},
            {"行业": "流出行业", "净额": -3.25, "行业-涨跌幅": -1.2},
        ]
    )
    fake_akshare = SimpleNamespace(stock_fund_flow_industry=lambda symbol: frame)

    result = AkShareProvider()._get_ths_industry_flow(fake_akshare)

    assert result.source == "akshare/10jqka"
    assert result.net_inflow_cny == 925_000_000
    assert [sector["name"] for sector in result.sectors] == ["流入行业", "流出行业"]
    assert result.sectors[0]["net_inflow_cny"] == 1_250_000_000
    assert result.sectors[1]["net_inflow_cny"] == -325_000_000


def test_number_understands_explicit_chinese_units():
    provider = AkShareProvider()

    assert provider._number("1.5亿") == 150_000_000
    assert provider._number("230万") == 2_300_000
    assert provider._number("12.5%") == 12.5
