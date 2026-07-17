# -*- coding: utf-8 -*-
"""StrategicContext / StrategyContextBuilder 测试。"""
from unittest.mock import patch

from core.strategic_context import StrategicContext, StrategyContextBuilder


class TestStrategicContextBuilder:
    def test_build_with_mock_mcp(self):
        builder = StrategyContextBuilder(dim_info="c", year="2025")

        with patch("models.idste.sp_team_info", return_value={"company": "Test"}):
            with patch("models.idste.sp_dimension", return_value="c"):
                with patch("models.idste.sp_data_menu", return_value=[]):
                    with patch("models.idste._find_table_keys", return_value=[]):
                        ctx = builder.build()

        assert isinstance(ctx, StrategicContext)
        assert ctx.dim_info == "c"
        assert ctx.year == "2025"

    def test_build_target_tables_subset(self):
        builder = StrategyContextBuilder(dim_info="c", year="2025")

        fake_tables = [
            {"table_key": "tk1", "name": "财务数据"},
            {"table_key": "tk2", "name": "项目数据"},
        ]

        with patch("models.idste.sp_team_info", return_value={}):
            with patch("models.idste.sp_dimension", return_value="c"):
                with patch("models.idste.sp_data_menu", return_value={}):
                    with patch("models.idste._find_table_keys", return_value=fake_tables):
                        with patch("models.idste.sp_data", return_value={"rows": []}) as mock_sp_data:
                            ctx = builder.build(target_tables=["财务数据"])

        assert "财务数据" in ctx.mcp_data
        mock_sp_data.assert_called_once()

    def test_build_empty_target_tables(self):
        builder = StrategyContextBuilder(dim_info="c", year="2025")

        with patch("models.idste.sp_team_info", return_value={}):
            with patch("models.idste.sp_dimension", return_value="c"):
                with patch("models.idste.sp_data_menu", return_value={}):
                    with patch("models.idste._find_table_keys", return_value=[]):
                        ctx = builder.build(target_tables=[])

        assert ctx.mcp_data == {}
