"""
A股数据获取模块

功能:
1. 获取股票列表(沪深300/科创50)
2. 下载历史日线数据
3. 复权处理
4. 停牌日处理
5. 数据质量校验
6. ST股票识别

作者: AI-Trader Team
日期: 2025-11-03
参考: docs/DESIGN_DEFECTS_FIX.md §2, §4
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def identify_st_stock(stock_name: str) -> bool:
    """
    判断是否为ST股票
    
    识别规则:
    - ST开头 -> True
    - *ST开头 -> True
    - SST开头 -> True
    - 其他 -> False
    
    Args:
        stock_name: 股票名称 (如 "ST东凌", "*ST保千", "中国平安")
        
    Returns:
        True: ST股票 (5%涨跌幅)
        False: 非ST股票
        
    参考: docs/DESIGN_DEFECTS_FIX.md §2
    """
    name = stock_name.strip()
    st_prefixes = ["ST", "*ST", "SST", "S*ST"]
    return any(name.startswith(prefix) for prefix in st_prefixes)


def fetch_stock_list(market: str = "HS300", update: bool = True) -> dict:
    """
    获取股票列表
    
    Args:
        market: 市场类型 ("HS300"=沪深300, "KC50"=科创50, "ALL"=全部)
        update: 是否更新已有列表
        
    Returns:
        {
            "update_time": "2024-01-15 15:00:00",
            "total_count": 300,
            "stocks": [
                {
                    "symbol": "600519.SH",
                    "name": "贵州茅台",
                    "industry": "白酒",
                    "market": "主板",
                    "list_date": "2001-08-27",
                    "is_st": False,
                    "status": "normal"
                }
            ]
        }
        
    参考: docs/ASTOCK_IMPLEMENTATION_ROADMAP.md §阶段1-任务1.1
    """
    try:
        import tushare as ts
        
        # 获取Token
        token = os.getenv("TUSHARE_TOKEN")
        if not token:
            raise ValueError("未配置TUSHARE_TOKEN环境变量,请在.env文件中配置")
        
        pro = ts.pro_api(token)
        
        # TODO: 实现股票列表获取逻辑
        # 1. 调用Tushare API获取股票列表
        # 2. 根据market参数筛选
        # 3. 识别ST股票
        # 4. 保存到data/astock_list.json
        
        logger.info(f"获取{market}股票列表...")
        
        # 示例实现(需要替换为实际逻辑)
        stocks = []
        
        result = {
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_count": len(stocks),
            "stocks": stocks
        }
        
        # 保存到文件
        output_path = "data/astock_list.json"
        os.makedirs("data", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 股票列表已保存到 {output_path}")
        return result
        
    except ImportError:
        logger.error("未安装tushare,请运行: pip install tushare")
        raise
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise


def fetch_daily_data(
    symbol: str,
    start_date: str,
    end_date: str,
    adj: str = "qfq"
) -> List[Dict]:
    """
    下载历史日线数据并处理停牌日
    
    Args:
        symbol: 股票代码 (如 "600519.SH")
        start_date: 开始日期 (如 "2024-01-01")
        end_date: 结束日期 (如 "2024-12-31")
        adj: 复权类型 ("qfq"=前复权, "hfq"=后复权, None=不复权)
        
    Returns:
        [
            {
                "symbol": "600519.SH",
                "date": "2024-01-15",
                "open": 1860.00,
                "close": 1880.00,
                "high": 1890.00,
                "low": 1855.00,
                "volume": 12345678,
                "amount": 231234567.89,
                "prev_close": 1850.00,
                "change_pct": 1.62,
                "status": "normal",  # normal, suspended, limit_up, limit_down
                "suspend_reason": None
            }
        ]
        
    参考: docs/DESIGN_DEFECTS_FIX.md §4 (停牌日处理)
    """
    try:
        import tushare as ts
        
        token = os.getenv("TUSHARE_TOKEN")
        pro = ts.pro_api(token)
        
        logger.info(f"下载 {symbol} 数据: {start_date} 至 {end_date}")
        
        # TODO: 实现数据下载逻辑
        # 1. 调用Tushare API获取日线数据
        # 2. 获取停牌信息
        # 3. 处理停牌日(使用前收盘价填充)
        # 4. 判断涨跌停状态
        # 5. 数据质量校验
        
        result = []
        
        # 示例实现(需要替换为实际逻辑)
        
        return result
        
    except Exception as e:
        logger.error(f"下载数据失败: {e}")
        raise


def validate_data_quality(data: List[Dict]) -> Dict:
    """
    数据质量校验
    
    校验项:
    - 价格连续性(涨跌幅<50%)
    - 成交量合理性(volume>0)
    - 数据完整性(OHLCV字段非空)
    - 时间序列连续性(无未来日期)
    
    Args:
        data: 数据列表
        
    Returns:
        {
            "valid": True/False,
            "warnings": ["2024-01-15: 涨跌幅异常50.5%"],
            "errors": []
        }
    """
    warnings = []
    errors = []
    
    # TODO: 实现数据质量校验逻辑
    
    return {
        "valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors
    }


def download_all_stocks(
    stock_pool: str = "HS300",
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31"
) -> None:
    """
    批量下载所有股票数据
    
    Args:
        stock_pool: 股票池 ("HS300", "KC50")
        start_date: 开始日期
        end_date: 结束日期
        
    存储格式:
    - data/astock_list.json - 股票列表
    - data/merged.jsonl - 行情数据(追加模式)
    """
    logger.info(f"批量下载 {stock_pool} 股票数据...")
    
    # 1. 获取股票列表
    stock_list = fetch_stock_list(market=stock_pool)
    
    # 2. 逐个下载数据
    for stock in stock_list["stocks"]:
        symbol = stock["symbol"]
        
        try:
            # 下载数据
            data = fetch_daily_data(symbol, start_date, end_date)
            
            # 数据质量校验
            validation = validate_data_quality(data)
            if not validation["valid"]:
                logger.warning(f"{symbol} 数据质量问题: {validation['errors']}")
            
            # 保存到merged.jsonl
            output_path = "data/merged.jsonl"
            with open(output_path, "a", encoding="utf-8") as f:
                for record in data:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
            logger.info(f"✓ {symbol} 数据已保存 ({len(data)}条记录)")
            
            # API限流控制
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"✗ {symbol} 下载失败: {e}")
            continue


if __name__ == "__main__":
    # 使用示例
    print("A股数据获取模块")
    print("=" * 60)
    
    # 测试ST股票识别
    print("\n测试ST股票识别:")
    print(f"ST东凌: {identify_st_stock('ST东凌')}")  # True
    print(f"*ST保千: {identify_st_stock('*ST保千')}")  # True
    print(f"中国平安: {identify_st_stock('中国平安')}")  # False
    
    # TODO: 取消注释以执行实际下载
    # download_all_stocks(stock_pool="HS300", start_date="2024-01-01", end_date="2024-01-31")
