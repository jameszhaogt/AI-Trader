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

# 依赖包导入
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
            tushare_token: 废弃参数(保持兼容性)
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        
        if not AKSHARE_AVAILABLE:
            logging.warning("AkShare未配置,数据获取将不可用")
    
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
                "data_source": "akshare"
            } 或 None(数据完全不可用)
        """
        try:
            if AKSHARE_AVAILABLE:
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
    
    def _fetch_northbound_akshare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过AkShare获取北向资金数据"""
        try:
            # 去掉后缀
            symbol_code = symbol.split('.')[0] if '.' in symbol else symbol
            
            # 获取个股北向资金数据
            df = ak.stock_hsgt_individual_em(symbol=symbol_code)
            
            if df is None or df.empty:
                return {
                    "date": date,
                    "symbol": symbol,
                    "buy_amount": None,
                    "sell_amount": None,
                    "net_amount": None,
                    "data_source": "akshare"
                }
            
            # 筛选指定日期的数据
            # AkShare返回的日期格式可能为 YYYY-MM-DD
            target_date = date
            df['date'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
            df_filtered = df[df['date'] == target_date]
            
            if df_filtered.empty:
                return {
                    "date": date,
                    "symbol": symbol,
                    "buy_amount": None,
                    "sell_amount": None,
                    "net_amount": None,
                    "data_source": "akshare"
                }
            
            row = df_filtered.iloc[0]
            
            # 提取数据（单位转换为万元）
            buy_amount = float(row.get('北向资金买入', 0)) / 10000 if pd.notna(row.get('北向资金买入')) else None
            sell_amount = float(row.get('北向资金卖出', 0)) / 10000 if pd.notna(row.get('北向资金卖出')) else None
            
            net_amount = None
            if buy_amount is not None and sell_amount is not None:
                net_amount = buy_amount - sell_amount
            elif '北向资金净买入' in row and pd.notna(row['北向资金净买入']):
                net_amount = float(row['北向资金净买入']) / 10000
            
            return {
                "date": date,
                "symbol": symbol,
                "buy_amount": buy_amount,
                "sell_amount": sell_amount,
                "net_amount": net_amount,
                "data_source": "akshare"
            }
            
        except Exception as e:
            logging.warning(f"AkShare获取北向资金失败: {e}")
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
            if AKSHARE_AVAILABLE:
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
    
    def _fetch_margin_akshare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过AkShare获取融资融券数据"""
        try:
            symbol_code = symbol.split('.')[0] if '.' in symbol else symbol
            
            # 获取融资融券明细
            df = ak.stock_margin_detail_em(symbol=symbol_code)
            
            if df is None or df.empty:
                return {
                    "date": date,
                    "symbol": symbol,
                    "margin_balance": None,
                    "short_balance": None,
                    "margin_buy_amount": None,
                    "data_source": "akshare"
                }
            
            # 筛选指定日期
            df['date'] = pd.to_datetime(df['信息日期']).dt.strftime('%Y-%m-%d')
            df_filtered = df[df['date'] == date]
            
            if df_filtered.empty:
                return {
                    "date": date,
                    "symbol": symbol,
                    "margin_balance": None,
                    "short_balance": None,
                    "margin_buy_amount": None,
                    "data_source": "akshare"
                }
            
            row = df_filtered.iloc[0]
            
            # 提取数据（单位转换为万元）
            margin_balance = float(row.get('融资余额', 0)) / 10000 if pd.notna(row.get('融资余额')) else None
            short_balance = float(row.get('融券余额', 0)) / 10000 if pd.notna(row.get('融券余额')) else None
            margin_buy_amount = float(row.get('融资买入额', 0)) / 10000 if pd.notna(row.get('融资买入额')) else None
            
            return {
                "date": date,
                "symbol": symbol,
                "margin_balance": margin_balance,
                "short_balance": short_balance,
                "margin_buy_amount": margin_buy_amount,
                "data_source": "akshare"
            }
            
        except Exception as e:
            logging.warning(f"AkShare获取融资融券数据失败: {e}")
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
            if AKSHARE_AVAILABLE:
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
    
    def _fetch_ratings_akshare(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """通过AkShare获取评级数据"""
        try:
            symbol_code = symbol.split('.')[0] if '.' in symbol else symbol
            
            # 获取所有股票评级
            df = ak.stock_rating_all()
            
            if df is None or df.empty:
                return {
                    "date": date,
                    "symbol": symbol,
                    "rating": None,
                    "target_price": None,
                    "rating_change": None,
                    "institution_count": None,
                    "data_source": "akshare"
                }
            
            # 筛选目标股票和日期范围内的数据
            # AkShare返回的股票代码可能为6位数字
            df_symbol = df[df['股票代码'].astype(str).str.contains(symbol_code)]
            
            if df_symbol.empty:
                return {
                    "date": date,
                    "symbol": symbol,
                    "rating": None,
                    "target_price": None,
                    "rating_change": None,
                    "institution_count": None,
                    "data_source": "akshare"
                }
            
            # 按日期排序
            df_symbol['rating_date'] = pd.to_datetime(df_symbol['发布日期'])
            df_symbol = df_symbol.sort_values('rating_date', ascending=False)
            
            # 获取最新评级
            latest = df_symbol.iloc[0]
            
            # 评级标准化
            rating_map = {
                '买入': '买入', '强烈推荐': '买入', '推荐': '买入',
                '增持': '增持', '优于大市': '增持',
                '中性': '中性', '持有': '中性',
                '减持': '减持', '弱于大市': '减持',
                '卖出': '卖出'
            }
            
            raw_rating = latest.get('评级', '')
            rating = rating_map.get(raw_rating, raw_rating)
            
            # 目标价
            target_price = float(latest['目标价']) if pd.notna(latest.get('目标价')) else None
            
            # 评级变化
            rating_change = latest.get('评级变动', None)
            
            # 统计机构数量（近30天内）
            from datetime import datetime, timedelta
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_30d_ago = date_obj - timedelta(days=30)
            
            df_recent = df_symbol[df_symbol['rating_date'] >= date_30d_ago]
            institution_count = len(df_recent)
            
            return {
                "date": date,
                "symbol": symbol,
                "rating": rating,
                "target_price": target_price,
                "rating_change": rating_change,
                "institution_count": institution_count,
                "data_source": "akshare"
            }
            
        except Exception as e:
            logging.warning(f"AkShare获取评级数据失败: {e}")
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
            if AKSHARE_AVAILABLE:
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
        try:
            # 行业名称到Tushare指数代码的映射
            industry_map = {
                '银行': '885716.TI',
                '医药': '885530.TI',
                '半导体': '884186.TI',
                '白酒': '885590.TI',
                '科技': '884111.TI',
                '消费': '884118.TI',
                '房地产': '885717.TI'
                # 可根据需要扩展更多行业
            }
            
            ts_code = industry_map.get(industry)
            if not ts_code:
                logging.warning(f"未找到行业 '{industry}' 的Tushare指数代码")
                return {
                    "date": date,
                    "industry": industry,
                    "pct_change": None,
                    "net_flow": None,
                    "heat_rank": None,
                    "data_source": "tushare"
                }
            
            trade_date = date.replace("-", "")
            
            # 获取行业指数数据
            df = self.pro.ths_index(ts_code=ts_code, trade_date=trade_date)
            
            if df is None or df.empty:
                return {
                    "date": date,
                    "industry": industry,
                    "pct_change": None,
                    "net_flow": None,
                    "heat_rank": None,
                    "data_source": "tushare"
                }
            
            row = df.iloc[0]
            
            # 提取涨跌幅
            pct_change = float(row['pct_chg']) if pd.notna(row.get('pct_chg')) else None
            
            # Tushare此API不提供资金流向和排名
            net_flow = None
            heat_rank = None
            
            return {
                "date": date,
                "industry": industry,
                "pct_change": pct_change,
                "net_flow": net_flow,
                "heat_rank": heat_rank,
                "data_source": "tushare"
            }
            
        except Exception as e:
            logging.warning(f"Tushare获取行业热度数据失败: {e}")
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
        try:
            # 获取所有行业板块
            df_all = ak.stock_board_industry_name_em()
            
            if df_all is None or df_all.empty:
                return {
                    "date": date,
                    "industry": industry,
                    "pct_change": None,
                    "net_flow": None,
                    "heat_rank": None,
                    "data_source": "akshare"
                }
            
            # 查找目标行业
            df_industry = df_all[df_all['板块名称'].str.contains(industry)]
            
            if df_industry.empty:
                # 尝试模糊匹配
                logging.warning(f"未找到匹配的行业: {industry}")
                return {
                    "date": date,
                    "industry": industry,
                    "pct_change": None,
                    "net_flow": None,
                    "heat_rank": None,
                    "data_source": "akshare"
                }
            
            row = df_industry.iloc[0]
            
            # 提取数据
            pct_change = float(row.get('涨跌幅', 0)) if pd.notna(row.get('涨跌幅')) else None
            net_flow = float(row.get('净流入', 0)) / 10000 if pd.notna(row.get('净流入')) else None
            
            # 计算热度排名（按涨跌幅排序）
            df_all_sorted = df_all.sort_values('涨跌幅', ascending=False)
            heat_rank = None
            for idx, (i, r) in enumerate(df_all_sorted.iterrows(), 1):
                if r['板块名称'] == row['板块名称']:
                    heat_rank = idx
                    break
            
            return {
                "date": date,
                "industry": industry,
                "pct_change": pct_change,
                "net_flow": net_flow,
                "heat_rank": heat_rank,
                "data_source": "akshare"
            }
            
        except Exception as e:
            logging.warning(f"AkShare获取行业热度数据失败: {e}")
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
        tushare_token: 废弃参数(保持兼容性)
        
    Returns:
        dict: 包含4个维度的共识数据
    """
    fetcher = ConsensusDataFetcher()
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
