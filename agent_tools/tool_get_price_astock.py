"""
A股价格查询工具 - 增强版

在原有tool_get_price_local.py基础上增加A股特有功能:
1. 股票代码验证
2. 停牌状态检测
3. 涨跌停判断
4. ST股票识别
5. 价格精度处理

作者: AI-Trader Team
日期: 2025-11-03
参考: docs/DESIGN_DEFECTS_FIX.md §1, §2
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from fastmcp import FastMCP

mcp = FastMCP("AStockPrices")


def _workspace_data_path(filename: str) -> Path:
    """获取数据文件路径"""
    base_dir = Path(__file__).resolve().parents[1]
    return base_dir / "data" / filename


def calculate_limit_prices(symbol: str, prev_close: float, is_st: bool = False) -> dict:
    """
    计算涨跌停价格(精确到分)
    
    板块规则:
    - 主板/中小板: ±10%
    - 科创板(688xxx)/创业板(300xxx): ±20%
    - ST股票: ±5%
    
    Args:
        symbol: 股票代码 (如 "600519.SH")
        prev_close: 前收盘价
        is_st: 是否为ST股票
        
    Returns:
        {
            "limit_up": 涨停价,
            "limit_down": 跌停价
        }
        
    参考: docs/DESIGN_DEFECTS_FIX.md §1
    """
    # 判断板块
    if symbol.startswith("688") or symbol.startswith("300"):
        # 科创板(688xxx)或创业板(300xxx) - 20%涨跌幅
        limit_ratio = 1.20
    elif is_st:
        # ST股票 - 5%涨跌幅
        limit_ratio = 1.05
    else:
        # 主板/中小板 - 10%涨跌幅
        limit_ratio = 1.10
    
    # 精确到分(小数点后2位)
    limit_up = round(prev_close * limit_ratio, 2)
    limit_down = round(prev_close * (2 - limit_ratio), 2)
    
    return {
        "limit_up": limit_up,
        "limit_down": limit_down
    }


def is_limit_up(symbol: str, current_price: float, prev_close: float, is_st: bool = False) -> bool:
    """
    判断是否涨停
    
    Args:
        symbol: 股票代码
        current_price: 当前价格
        prev_close: 前收盘价
        is_st: 是否为ST股票
        
    Returns:
        True: 涨停
        False: 未涨停
    """
    limits = calculate_limit_prices(symbol, prev_close, is_st)
    # 使用 >= 判断,因为盘中价格可能略超涨停价(如集合竞价)
    return current_price >= limits["limit_up"]


def is_limit_down(symbol: str, current_price: float, prev_close: float, is_st: bool = False) -> bool:
    """
    判断是否跌停
    
    Args:
        symbol: 股票代码
        current_price: 当前价格
        prev_close: 前收盘价
        is_st: 是否为ST股票
        
    Returns:
        True: 跌停
        False: 未跌停
    """
    limits = calculate_limit_prices(symbol, prev_close, is_st)
    return current_price <= limits["limit_down"]


def validate_stock_symbol(symbol: str) -> dict:
    """
    验证股票代码是否有效
    
    从astock_list.json中查找股票信息
    
    Args:
        symbol: 股票代码 (如 "600519.SH")
        
    Returns:
        {
            "valid": True/False,
            "stock_info": {...} or None,
            "reason": "错误原因"
        }
        
    参考: docs/ASTOCK_IMPLEMENTATION_ROADMAP.md §阶段1-任务1.2
    """
    try:
        list_path = _workspace_data_path("astock_list.json")
        
        if not list_path.exists():
            return {
                "valid": False,
                "stock_info": None,
                "reason": "股票列表文件不存在,请先运行 data/get_astock_data.py 获取数据"
            }
        
        with open(list_path, "r", encoding="utf-8") as f:
            stock_list = json.load(f)
        
        # 查找股票
        for stock in stock_list.get("stocks", []):
            if stock["symbol"] == symbol:
                return {
                    "valid": True,
                    "stock_info": stock,
                    "reason": ""
                }
        
        return {
            "valid": False,
            "stock_info": None,
            "reason": f"股票代码 {symbol} 不存在或未在股票池中"
        }
        
    except Exception as e:
        return {
            "valid": False,
            "stock_info": None,
            "reason": f"验证股票代码时出错: {e}"
        }


@mcp.tool()
def get_price_astock(symbol: str, date: str) -> Dict[str, Any]:
    """
    获取A股价格数据(增强版)
    
    在原有功能基础上增加:
    - 股票代码验证
    - 停牌状态检测
    - 涨跌停判断
    - ST股票识别
    - 涨跌停价格计算
    
    Args:
        symbol: 股票代码 (如 "600519.SH")
        date: 日期 (格式: "YYYY-MM-DD")
        
    Returns:
        {
            "symbol": "600519.SH",
            "date": "2024-01-15",
            "open": 1860.00,
            "close": 1880.00,
            "high": 1890.00,
            "low": 1855.00,
            "volume": 12345678,
            "prev_close": 1850.00,
            "status": "normal",  # normal, limit_up, limit_down, suspended
            "limit_prices": {
                "limit_up": 2035.00,
                "limit_down": 1665.00
            },
            "is_st": False,
            "market": "主板"
        }
        
    参考: docs/DESIGN_DEFECTS_FIX.md §1, §2
    """
    # 1. 验证股票代码
    validation = validate_stock_symbol(symbol)
    if not validation["valid"]:
        return {
            "error": validation["reason"],
            "symbol": symbol,
            "date": date
        }
    
    stock_info = validation["stock_info"]
    is_st = stock_info.get("is_st", False)
    market = stock_info.get("market", "未知")
    
    # 2. 读取价格数据
    try:
        data_path = _workspace_data_path("merged.jsonl")
        
        if not data_path.exists():
            return {
                "error": "行情数据文件不存在,请先运行 data/get_astock_data.py 下载数据",
                "symbol": symbol,
                "date": date
            }
        
        # 查找数据
        found_data = None
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("symbol") == symbol and record.get("date") == date:
                    found_data = record
                    break
        
        if not found_data:
            return {
                "error": f"未找到 {symbol} 在 {date} 的数据",
                "symbol": symbol,
                "date": date
            }
        
        # 3. 提取价格数据
        close_price = found_data.get("close", 0)
        prev_close = found_data.get("prev_close", close_price)
        status = found_data.get("status", "normal")
        
        # 4. 计算涨跌停价格
        limits = calculate_limit_prices(symbol, prev_close, is_st)
        
        # 5. 判断涨跌停状态(如果status未标记)
        if status == "normal" and close_price > 0:
            if is_limit_up(symbol, close_price, prev_close, is_st):
                status = "limit_up"
            elif is_limit_down(symbol, close_price, prev_close, is_st):
                status = "limit_down"
        
        # 6. 返回完整数据
        return {
            "symbol": symbol,
            "date": date,
            "open": round(found_data.get("open", 0), 2),
            "close": round(close_price, 2),
            "high": round(found_data.get("high", 0), 2),
            "low": round(found_data.get("low", 0), 2),
            "volume": found_data.get("volume", 0),
            "amount": found_data.get("amount", 0),
            "prev_close": round(prev_close, 2),
            "change_pct": round(found_data.get("change_pct", 0), 2),
            "status": status,
            "suspend_reason": found_data.get("suspend_reason"),
            "limit_prices": limits,
            "is_st": is_st,
            "market": market
        }
        
    except Exception as e:
        return {
            "error": f"读取价格数据时出错: {e}",
            "symbol": symbol,
            "date": date
        }


if __name__ == "__main__":
    # 测试用例
    print("A股价格查询工具测试")
    print("=" * 60)
    
    # 测试涨跌停价格计算
    print("\n1. 测试涨跌停价格计算:")
    print("主板股票(前收盘100元):", calculate_limit_prices("600519.SH", 100.00, False))
    print("科创板股票(前收盘50元):", calculate_limit_prices("688001.SH", 50.00, False))
    print("ST股票(前收盘2元):", calculate_limit_prices("600005.SH", 2.00, True))
    
    # 测试价格精度
    print("\n2. 测试价格精度(前收盘9.99元):")
    limits = calculate_limit_prices("600001.SH", 9.99, False)
    print(f"涨停价应为10.99: {limits['limit_up']}")
    print(f"跌停价应为8.99: {limits['limit_down']}")
    
    # 测试涨跌停判断
    print("\n3. 测试涨跌停判断:")
    print(f"110元是否涨停(前收盘100): {is_limit_up('600519.SH', 110.00, 100.00, False)}")
    print(f"90元是否跌停(前收盘100): {is_limit_down('600519.SH', 90.00, 100.00, False)}")
