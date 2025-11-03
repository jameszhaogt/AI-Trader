"""
A股共识数据获取脚本
获取北向资金、融资融券、券商评级等A股特色数据
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    import tushare as ts
    import pandas as pd
    import numpy as np
except ImportError:
    print("错误：缺少必要的依赖包，请运行: pip install tushare pandas numpy")
    sys.exit(1)


class ConsensusDataFetcher:
    """共识数据获取器"""
    
    def __init__(self, token: Optional[str] = None):
        """初始化
        
        Args:
            token: Tushare API token
        """
        self.token = token or os.getenv("TUSHARE_TOKEN")
        if not self.token:
            raise ValueError("请设置 TUSHARE_TOKEN 环境变量")
        
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        
        self.data_dir = project_root / "data"
        self.output_file = self.data_dir / "consensus_data.jsonl"
        
    def get_northbound_flow(self, trade_date: str, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取北向资金流向
        
        Args:
            trade_date: 交易日期 'YYYYMMDD'
            symbols: 股票代码列表（可选）
            
        Returns:
            北向资金数据字典
        """
        try:
            # 获取沪股通/深股通数据
            df = self.pro.moneyflow_hsgt(trade_date=trade_date)
            
            if df is None or df.empty:
                return {}
            
            # 汇总数据
            total_net_buy = df['hgt_buy'].sum() + df['sgt_buy'].sum() - \
                           df['hgt_sell'].sum() - df['sgt_sell'].sum()
            
            result = {
                "date": trade_date,
                "total_net_buy": float(total_net_buy) if not pd.isna(total_net_buy) else 0,
                "hgt_net_buy": float(df['hgt_buy'].sum() - df['hgt_sell'].sum()) if len(df) > 0 else 0,
                "sgt_net_buy": float(df['sgt_buy'].sum() - df['sgt_sell'].sum()) if len(df) > 0 else 0,
            }
            
            # 如果指定了股票，获取个股数据
            if symbols:
                stock_flows = {}
                for symbol in symbols:
                    stock_df = self.pro.moneyflow_hsgt(ts_code=symbol, start_date=trade_date, end_date=trade_date)
                    if stock_df is not None and not stock_df.empty:
                        net_buy = stock_df.iloc[0]['net_buy'] if 'net_buy' in stock_df.columns else 0
                        stock_flows[symbol] = float(net_buy) if not pd.isna(net_buy) else 0
                
                result['stock_flows'] = stock_flows
            
            return result
            
        except Exception as e:
            print(f"获取北向资金数据失败 {trade_date}: {e}")
            return {}
    
    def get_margin_info(self, trade_date: str, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取融资融券数据
        
        Args:
            trade_date: 交易日期 'YYYYMMDD'
            symbols: 股票代码列表（可选）
            
        Returns:
            融资融券数据字典
        """
        try:
            # 获取市场整体融资融券数据
            df = self.pro.margin(trade_date=trade_date)
            
            if df is None or df.empty:
                return {}
            
            result = {
                "date": trade_date,
                "total_margin_balance": float(df['rzye'].sum()) if 'rzye' in df.columns else 0,
                "total_short_balance": float(df['rqye'].sum()) if 'rqye' in df.columns else 0,
            }
            
            # 如果指定了股票，获取个股数据
            if symbols:
                stock_margins = {}
                for symbol in symbols:
                    stock_df = self.pro.margin_detail(ts_code=symbol, trade_date=trade_date)
                    if stock_df is not None and not stock_df.empty:
                        row = stock_df.iloc[0]
                        stock_margins[symbol] = {
                            "margin_balance": float(row['rzye']) if 'rzye' in row and not pd.isna(row['rzye']) else 0,
                            "margin_buy": float(row['rzmre']) if 'rzmre' in row and not pd.isna(row['rzmre']) else 0,
                            "margin_repay": float(row['rzche']) if 'rzche' in row and not pd.isna(row['rzche']) else 0,
                        }
                
                result['stock_margins'] = stock_margins
            
            return result
            
        except Exception as e:
            print(f"获取融资融券数据失败 {trade_date}: {e}")
            return {}
    
    def get_broker_ratings(self, symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """获取券商评级
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
            
        Returns:
            券商评级数据字典
        """
        try:
            df = self.pro.broker_recommend(ts_code=symbol, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                return {"symbol": symbol, "recommend_count": 0}
            
            # 统计评级
            buy_count = len(df[df['rating'] == '买入']) if 'rating' in df.columns else 0
            hold_count = len(df[df['rating'] == '持有']) if 'rating' in df.columns else 0
            sell_count = len(df[df['rating'] == '卖出']) if 'rating' in df.columns else 0
            
            return {
                "symbol": symbol,
                "recommend_count": len(df),
                "buy_count": buy_count,
                "hold_count": hold_count,
                "sell_count": sell_count,
                "latest_rating": df.iloc[0]['rating'] if len(df) > 0 and 'rating' in df.columns else None,
            }
            
        except Exception as e:
            print(f"获取券商评级失败 {symbol}: {e}")
            return {"symbol": symbol, "recommend_count": 0}
    
    def get_industry_heat(self, trade_date: str) -> Dict[str, float]:
        """获取行业热度
        
        Args:
            trade_date: 交易日期 'YYYYMMDD'
            
        Returns:
            行业热度字典 {行业名: 热度分数}
        """
        try:
            # 获取申万行业指数
            df = self.pro.index_daily(trade_date=trade_date)
            
            if df is None or df.empty:
                return {}
            
            # 筛选行业指数（申万一级行业）
            industry_df = df[df['ts_code'].str.startswith('801')]
            
            if industry_df.empty:
                return {}
            
            # 计算热度（基于涨幅和成交量）
            heat_scores = {}
            for _, row in industry_df.iterrows():
                pct_chg = row['pct_chg'] if 'pct_chg' in row and not pd.isna(row['pct_chg']) else 0
                vol = row['vol'] if 'vol' in row and not pd.isna(row['vol']) else 0
                
                # 简单热度计算：涨幅权重0.7 + 成交量权重0.3
                heat = pct_chg * 0.7 + (vol / 1000000) * 0.3
                heat_scores[row['ts_code']] = float(heat)
            
            return heat_scores
            
        except Exception as e:
            print(f"获取行业热度失败 {trade_date}: {e}")
            return {}
    
    def collect_daily_consensus(self, trade_date: str, symbols: List[str]) -> List[Dict[str, Any]]:
        """收集指定日期的所有共识数据
        
        Args:
            trade_date: 交易日期 'YYYYMMDD'
            symbols: 股票代码列表
            
        Returns:
            共识数据列表
        """
        print(f"收集 {trade_date} 的共识数据...")
        
        # 获取北向资金
        northbound = self.get_northbound_flow(trade_date, symbols)
        
        # 获取融资融券
        margin = self.get_margin_info(trade_date, symbols)
        
        # 获取行业热度
        industry_heat = self.get_industry_heat(trade_date)
        
        # 组合数据
        consensus_records = []
        for symbol in symbols:
            record = {
                "date": datetime.strptime(trade_date, '%Y%m%d').strftime('%Y-%m-%d'),
                "symbol": symbol,
                "northbound_flow": northbound.get('stock_flows', {}).get(symbol, 0),
                "margin_balance": margin.get('stock_margins', {}).get(symbol, {}).get('margin_balance', 0),
                "margin_balance_chg": 0,  # 需要对比前一日计算
                "broker_recommend_count": 0,  # 需要单独查询
                "industry_heat": 0,  # 需要根据股票所属行业匹配
            }
            consensus_records.append(record)
        
        return consensus_records
    
    def download_consensus_data(self, start_date: str, end_date: str, symbols: List[str]) -> None:
        """批量下载共识数据
        
        Args:
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            symbols: 股票代码列表
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        current_dt = start_dt
        all_records = []
        
        while current_dt <= end_dt:
            trade_date = current_dt.strftime('%Y%m%d')
            
            records = self.collect_daily_consensus(trade_date, symbols)
            all_records.extend(records)
            
            current_dt += timedelta(days=1)
        
        # 保存数据
        print(f"\n保存共识数据到 {self.output_file} ...")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for record in all_records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"完成！共 {len(all_records)} 条记录")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='A股共识数据获取工具')
    parser.add_argument('--start', type=str, default='2024-01-01',
                       help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-01-31',
                       help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--symbols', type=str, nargs='+',
                       default=['600519.SH', '000858.SZ'],
                       help='股票代码列表')
    
    args = parser.parse_args()
    
    try:
        fetcher = ConsensusDataFetcher()
        
        print(f"\n========== A股共识数据获取 ==========")
        print(f"日期范围: {args.start} ~ {args.end}")
        print(f"股票列表: {args.symbols}")
        print("="*40)
        
        fetcher.download_consensus_data(args.start, args.end, args.symbols)
        
    except Exception as e:
        print(f"\n错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
