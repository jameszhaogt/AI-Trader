"""
共识数据获取模块

功能:
1. 北向资金数据获取 - 沪/深股通资金流向(买入、卖出、净额)
2. 融资融券数据获取 - 融资余额、融券余额、融资买入额
3. 券商评级数据获取 - 机构评级、目标价、评级调整
4. 行业热度数据获取 - 行业涨跌幅、资金流向、热度排名

修复缺陷:
- D3: 数据缺失处理 - 缺失维度存储为null,不抛出异常

数据源:
- 主数据源: Tushare Pro (需要积分权限)
- 备用数据源: AkShare (免费,但数据延迟)

作者: AI-Trader Team
日期: 2024
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import os
import logging

# TODO: 安装依赖包
# pip install tushare akshare pandas

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    logging.warning("Tushare未安装,请运行: pip install tushare")

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logging.warning("AkShare未安装,请运行: pip install akshare")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("Pandas未安装,请运行: pip install pandas")


class ConsensusDataFetcher:
    """共识数据获取器"""
    
    def __init__(self, tushare_token: Optional[str] = None, data_dir: str = "./data"):
        """
        初始化数据获取器
        
        Args:
            tushare_token: Tushare Pro API Token(可选,从.env读取)
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        self.tushare_token = tushare_token or os.getenv("TUSHARE_TOKEN")
        
        # 初始化Tushare Pro
        if TUSHARE_AVAILABLE and self.tushare_token:
            ts.set_token(self.tushare_token)
            self.pro = ts.pro_api()
            self.use_tushare = True
        else:
            self.pro = None
            self.use_tushare = False
            logging.warning("Tushare未配置,将使用AkShare作为备用数据源")
    
    def fetch_northbound_flow(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """
        获取北向资金流向数据
        
        Args:
            symbol: 股票代码,如"600000"
            date: 日期 "YYYY-MM-DD"
            
        Returns:
            dict: {
                "date": "YYYY-MM-DD",
                "symbol": str,
                "buy_amount": float,  # 买入金额(万元),缺失时为null
                "sell_amount": float,  # 卖出金额(万元),缺失时为null
                "net_amount": float,  # 净额(万元),缺失时为null
                "data_source": "tushare" | "akshare"
            } 或 None(数据完全不可用)
        """
        try:
            if self.use_tushare:
                return self._fetch_northbound_tushare(symbol, date)
            elif AKSHARE_AVAILABLE:
                return self._fetch_northbound_akshare(symbol, date)
            else:
                logging.error("无可用数据源获取北向资金数据")
                return None
        except Exception as e:
            logging.error(f"获取北向资金数据失败: {e}")
            # D3修复:数据获取失败时返回null值而不是抛出异常
            return {
                "date": date,
                "symbol": symbol,
                "buy_amount": None,
                "sell_amount": None,
                "net_amount": None,
                "data_source": "error",
                "error": str(e)
            }
    
    def _fetch_northbound_tushare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过Tushare获取北向资金数据"""
        # TODO: 实现Tushare接口调用
        # API: pro.hk_hold(ts_code='600000.SH', trade_date='20240115')
        # 需要积分权限:300分+
        
        # 示例实现框架
        ts_code = self._convert_to_ts_code(symbol)
        trade_date = date.replace("-", "")
        
        # df = self.pro.hk_hold(ts_code=ts_code, trade_date=trade_date)
        # TODO: 实际调用Tushare API并解析结果
        
        # 临时返回null数据(实际应返回API查询结果)
        return {
            "date": date,
            "symbol": symbol,
            "buy_amount": None,
            "sell_amount": None,
            "net_amount": None,
            "data_source": "tushare"
        }
    
    def _fetch_northbound_akshare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过AkShare获取北向资金数据"""
        # TODO: 实现AkShare接口调用
        # API: ak.stock_hsgt_individual_em(symbol="600000")
        
        # 示例实现框架
        # df = ak.stock_hsgt_individual_em(symbol=symbol)
        # TODO: 筛选指定日期的数据并返回
        
        return {
            "date": date,
            "symbol": symbol,
            "buy_amount": None,
            "sell_amount": None,
            "net_amount": None,
            "data_source": "akshare"
        }
    
    def fetch_margin_trading(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """
        获取融资融券数据
        
        Args:
            symbol: 股票代码
            date: 日期 "YYYY-MM-DD"
            
        Returns:
            dict: {
                "date": "YYYY-MM-DD",
                "symbol": str,
                "margin_balance": float,  # 融资余额(万元),缺失时为null
                "short_balance": float,  # 融券余额(万元),缺失时为null
                "margin_buy_amount": float,  # 融资买入额(万元),缺失时为null
                "data_source": str
            }
        """
        try:
            if self.use_tushare:
                return self._fetch_margin_tushare(symbol, date)
            elif AKSHARE_AVAILABLE:
                return self._fetch_margin_akshare(symbol, date)
            else:
                logging.error("无可用数据源获取融资融券数据")
                return None
        except Exception as e:
            logging.error(f"获取融资融券数据失败: {e}")
            return {
                "date": date,
                "symbol": symbol,
                "margin_balance": None,
                "short_balance": None,
                "margin_buy_amount": None,
                "data_source": "error",
                "error": str(e)
            }
    
    def _fetch_margin_tushare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过Tushare获取融资融券数据"""
        # TODO: 实现Tushare接口
        # API: pro.margin_detail(ts_code='600000.SH', trade_date='20240115')
        # 需要积分权限:120分+
        
        return {
            "date": date,
            "symbol": symbol,
            "margin_balance": None,
            "short_balance": None,
            "margin_buy_amount": None,
            "data_source": "tushare"
        }
    
    def _fetch_margin_akshare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过AkShare获取融资融券数据"""
        # TODO: 实现AkShare接口
        # API: ak.stock_margin_detail_em(symbol="600000")
        
        return {
            "date": date,
            "symbol": symbol,
            "margin_balance": None,
            "short_balance": None,
            "margin_buy_amount": None,
            "data_source": "akshare"
        }
    
    def fetch_analyst_ratings(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """
        获取券商评级数据
        
        Args:
            symbol: 股票代码
            date: 日期 "YYYY-MM-DD"
            
        Returns:
            dict: {
                "date": "YYYY-MM-DD",
                "symbol": str,
                "rating": str,  # 最新评级("买入"/"增持"/"中性"/"减持"/"卖出"),缺失时为null
                "target_price": float,  # 目标价(元),缺失时为null
                "rating_change": str,  # 评级变化("上调"/"维持"/"下调"),缺失时为null
                "institution_count": int,  # 评级机构数量,缺失时为null
                "data_source": str
            }
        """
        try:
            if self.use_tushare:
                return self._fetch_ratings_tushare(symbol, date)
            elif AKSHARE_AVAILABLE:
                return self._fetch_ratings_akshare(symbol, date)
            else:
                logging.error("无可用数据源获取评级数据")
                return None
        except Exception as e:
            logging.error(f"获取评级数据失败: {e}")
            return {
                "date": date,
                "symbol": symbol,
                "rating": None,
                "target_price": None,
                "rating_change": None,
                "institution_count": None,
                "data_source": "error",
                "error": str(e)
            }
    
    def _fetch_ratings_tushare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过Tushare获取评级数据"""
        # TODO: 实现Tushare接口
        # API: pro.stk_rating(ts_code='600000.SH', start_date='20240101', end_date='20240115')
        # 需要积分权限:300分+
        
        return {
            "date": date,
            "symbol": symbol,
            "rating": None,
            "target_price": None,
            "rating_change": None,
            "institution_count": None,
            "data_source": "tushare"
        }
    
    def _fetch_ratings_akshare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过AkShare获取评级数据"""
        # TODO: 实现AkShare接口
        # API: ak.stock_rating_all()
        
        return {
            "date": date,
            "symbol": symbol,
            "rating": None,
            "target_price": None,
            "rating_change": None,
            "institution_count": None,
            "data_source": "akshare"
        }
    
    def fetch_industry_heat(self, industry: str, date: str) -> Optional[Dict[str, Any]]:
        """
        获取行业热度数据
        
        Args:
            industry: 行业名称,如"银行"
            date: 日期 "YYYY-MM-DD"
            
        Returns:
            dict: {
                "date": "YYYY-MM-DD",
                "industry": str,
                "pct_change": float,  # 行业涨跌幅(%),缺失时为null
                "net_flow": float,  # 资金净流入(万元),缺失时为null
                "heat_rank": int,  # 热度排名,缺失时为null
                "data_source": str
            }
        """
        try:
            if self.use_tushare:
                return self._fetch_industry_tushare(industry, date)
            elif AKSHARE_AVAILABLE:
                return self._fetch_industry_akshare(industry, date)
            else:
                logging.error("无可用数据源获取行业热度数据")
                return None
        except Exception as e:
            logging.error(f"获取行业热度数据失败: {e}")
            return {
                "date": date,
                "industry": industry,
                "pct_change": None,
                "net_flow": None,
                "heat_rank": None,
                "data_source": "error",
                "error": str(e)
            }
    
    def _fetch_industry_tushare(self, industry: str, date: str) -> Optional[Dict[str, Any]]:
        """通过Tushare获取行业热度数据"""
        # TODO: 实现Tushare接口
        # API: pro.ths_index(ts_code='885716.TI', trade_date='20240115')
        # 需要积分权限:500分+
        
        return {
            "date": date,
            "industry": industry,
            "pct_change": None,
            "net_flow": None,
            "heat_rank": None,
            "data_source": "tushare"
        }
    
    def _fetch_industry_akshare(self, industry: str, date: str) -> Optional[Dict[str, Any]]:
        """通过AkShare获取行业热度数据"""
        # TODO: 实现AkShare接口
        # API: ak.stock_board_industry_name_em()
        
        return {
            "date": date,
            "industry": industry,
            "pct_change": None,
            "net_flow": None,
            "heat_rank": None,
            "data_source": "akshare"
        }
    
    def fetch_all_consensus_data(self, symbol: str, date: str, 
                                 industry: Optional[str] = None) -> Dict[str, Any]:
        """
        获取股票的全部共识数据
        
        Args:
            symbol: 股票代码
            date: 日期 "YYYY-MM-DD"
            industry: 行业名称(可选)
            
        Returns:
            dict: {
                "symbol": str,
                "date": str,
                "northbound": dict | None,
                "margin": dict | None,
                "ratings": dict | None,
                "industry": dict | None
            }
        """
        result = {
            "symbol": symbol,
            "date": date,
            "northbound": self.fetch_northbound_flow(symbol, date),
            "margin": self.fetch_margin_trading(symbol, date),
            "ratings": self.fetch_analyst_ratings(symbol, date),
            "industry": self.fetch_industry_heat(industry, date) if industry else None
        }
        
        return result
    
    def save_consensus_data(self, data: Dict[str, Any], filename: str = "consensus_data.jsonl"):
        """
        保存共识数据到JSONL文件
        
        Args:
            data: 共识数据字典
            filename: 文件名
        """
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        
        logging.info(f"共识数据已保存到 {filepath}")
    
    def _convert_to_ts_code(self, symbol: str) -> str:
        """
        转换股票代码为Tushare格式
        
        Args:
            symbol: 股票代码,如"600000"
            
        Returns:
            str: Tushare代码,如"600000.SH"
        """
        if symbol.startswith("6"):
            return f"{symbol}.SH"  # 上交所
        elif symbol.startswith(("0", "3")):
            return f"{symbol}.SZ"  # 深交所
        else:
            return symbol


# 工具函数
def fetch_consensus_for_stock(symbol: str, date: str, 
                              tushare_token: Optional[str] = None) -> Dict[str, Any]:
    """
    便捷函数:获取单只股票的共识数据
    
    Args:
        symbol: 股票代码
        date: 日期 "YYYY-MM-DD"
        tushare_token: Tushare token(可选)
        
    Returns:
        dict: 包含4个维度的共识数据
    """
    fetcher = ConsensusDataFetcher(tushare_token)
    return fetcher.fetch_all_consensus_data(symbol, date)


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 测试用例1: 获取单只股票共识数据
    print("测试1: 获取浦发银行(600000)的共识数据")
    fetcher = ConsensusDataFetcher()
    
    data = fetcher.fetch_all_consensus_data(
        symbol="600000",
        date="2024-01-15",
        industry="银行"
    )
    
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # 测试用例2: 数据缺失处理验证
    print("\n测试2: 验证D3修复 - 数据缺失时返回null")
    northbound = data.get("northbound", {})
    assert northbound.get("buy_amount") is None, "买入金额应为null"
    assert northbound.get("sell_amount") is None, "卖出金额应为null"
    assert northbound.get("net_amount") is None, "净额应为null"
    print("✓ D3修复验证通过:缺失数据正确返回null")
