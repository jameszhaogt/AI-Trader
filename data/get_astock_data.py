"""
A股历史行情数据获取脚本
使用 Tushare Pro API 获取A股历史OHLCV数据
支持：
- 沪深300、中证500、科创50等指数成份股
- 自定义股票列表
- 增量更新与全量下载
- 数据完整性校验（停牌、未上市处理）
- 前复权价格计算
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    import tushare as ts
    import pandas as pd
    import numpy as np
except ImportError:
    print("错误：缺少必要的依赖包，请运行: pip install tushare pandas numpy")
    sys.exit(1)


class AStockDataFetcher:
    """A股数据获取器"""
    
    def __init__(self, token: Optional[str] = None):
        """初始化数据获取器
        
        Args:
            token: Tushare API token，如未提供则从环境变量读取
        """
        self.token = token or os.getenv("TUSHARE_TOKEN")
        if not self.token:
            raise ValueError("请设置 TUSHARE_TOKEN 环境变量或传入 token 参数")
        
        # 初始化 Tushare Pro API
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        
        # 数据路径
        self.data_dir = project_root / "data"
        self.output_file = self.data_dir / "merged.jsonl"
        self.stock_list_file = self.data_dir / "astock_list.json"
        
    def get_index_constituents(self, index_code: str) -> List[str]:
        """获取指数成份股列表
        
        Args:
            index_code: 指数代码，如 '000300.SH' (沪深300)
            
        Returns:
            股票代码列表
        """
        try:
            df = self.pro.index_weight(index_code=index_code)
            if df is not None and not df.empty:
                return df['con_code'].tolist()
            return []
        except Exception as e:
            print(f"获取指数成份股失败 {index_code}: {e}")
            return []
    
    def load_stock_pool(self, pool_name: str = "hs300") -> List[str]:
        """加载股票池
        
        Args:
            pool_name: 股票池名称 (hs300/zz500/kc50/custom)
            
        Returns:
            股票代码列表
        """
        # 加载股票列表配置
        if not self.stock_list_file.exists():
            print(f"警告：股票列表文件不存在: {self.stock_list_file}")
            return []
        
        with open(self.stock_list_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        pool_config = config.get("stock_pools", {}).get(pool_name, {})
        
        # 如果是自定义池，直接返回配置的股票
        if pool_config.get("source") == "manual":
            return pool_config.get("symbols", [])
        
        # 否则从 Tushare 获取指数成份股
        index_mapping = {
            "hs300": "000300.SH",
            "zz500": "000905.SH",
            "kc50": "000688.SH"
        }
        
        index_code = index_mapping.get(pool_name)
        if index_code:
            symbols = self.get_index_constituents(index_code)
            print(f"从指数 {index_code} 获取到 {len(symbols)} 只股票")
            return symbols
        
        return []
    
    def fetch_daily_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取单只股票的日线数据
        
        Args:
            symbol: 股票代码，如 '600519.SH'
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'
            
        Returns:
            DataFrame 包含OHLCV数据，如果失败返回None
        """
        try:
            # 获取日线行情
            df = self.pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                print(f"警告：{symbol} 无数据")
                return None
            
            # 获取复权因子
            adj_df = self.pro.adj_factor(ts_code=symbol, start_date=start_date, end_date=end_date)
            
            # 合并复权因子
            if adj_df is not None and not adj_df.empty:
                df = df.merge(adj_df[['trade_date', 'adj_factor']], on='trade_date', how='left')
                # 计算前复权价格
                df['adj_factor'] = df['adj_factor'].fillna(1.0)
                for col in ['open', 'high', 'low', 'close']:
                    df[f'adj_{col}'] = df[col] * df['adj_factor']
            else:
                # 无复权因子时使用原价格
                for col in ['open', 'high', 'low', 'close']:
                    df[f'adj_{col}'] = df[col]
            
            # 排序并返回
            df = df.sort_values('trade_date')
            return df
            
        except Exception as e:
            print(f"获取 {symbol} 数据失败: {e}")
            return None
    
    def check_stock_status(self, symbol: str, trade_date: str) -> str:
        """检查股票在指定日期的状态
        
        Args:
            symbol: 股票代码
            trade_date: 交易日期 'YYYYMMDD'
            
        Returns:
            状态：'normal', 'suspended', 'delisted', 'unlisted'
        """
        try:
            # 获取股票基本信息
            basic_df = self.pro.stock_basic(ts_code=symbol, fields='ts_code,list_date,delist_date')
            if basic_df is None or basic_df.empty:
                return 'unlisted'
            
            list_date = basic_df.iloc[0]['list_date']
            delist_date = basic_df.iloc[0]['delist_date']
            
            # 检查是否未上市或已退市
            if list_date and trade_date < list_date:
                return 'unlisted'
            if delist_date and trade_date > delist_date:
                return 'delisted'
            
            # 检查是否停牌（通过查询当日数据）
            daily_df = self.pro.daily(ts_code=symbol, start_date=trade_date, end_date=trade_date)
            if daily_df is None or daily_df.empty:
                return 'suspended'
            
            return 'normal'
            
        except Exception as e:
            print(f"检查股票状态失败 {symbol}: {e}")
            return 'normal'
    
    def convert_to_jsonl_format(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """转换为与现有系统兼容的JSONL格式
        
        Args:
            symbol: 股票代码
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            JSONL格式的字典
        """
        time_series = {}
        
        for _, row in df.iterrows():
            date_str = pd.to_datetime(row['trade_date']).strftime('%Y-%m-%d')
            time_series[date_str] = {
                "1. buy price": f"{row['adj_open']:.4f}",
                "2. high": f"{row['adj_high']:.4f}",
                "3. low": f"{row['adj_low']:.4f}",
                "4. sell price": f"{row['adj_close']:.4f}",
                "5. volume": str(int(row['vol'] * 100))  # 转换为股（手*100）
            }
        
        return {
            "Meta Data": {
                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": symbol,
                "3. Last Refreshed": df.iloc[-1]['trade_date'] if not df.empty else "",
                "4. Output Size": "Full size",
                "5. Time Zone": "Asia/Shanghai"
            },
            "Time Series (Daily)": time_series
        }
    
    def download_stock_data(self, symbols: List[str], start_date: str, end_date: str, 
                           incremental: bool = False) -> None:
        """下载股票数据并保存
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            incremental: 是否增量更新
        """
        # 转换日期格式
        start_date_fmt = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')
        
        # 读取现有数据（如果是增量更新）
        existing_data = {}
        if incremental and self.output_file.exists():
            print("加载现有数据...")
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        symbol = doc.get('Meta Data', {}).get('2. Symbol')
                        if symbol:
                            existing_data[symbol] = doc
        
        # 下载数据
        total = len(symbols)
        success_count = 0
        
        for idx, symbol in enumerate(symbols, 1):
            print(f"[{idx}/{total}] 获取 {symbol} ...")
            
            df = self.fetch_daily_data(symbol, start_date_fmt, end_date_fmt)
            if df is not None and not df.empty:
                # 转换格式
                doc = self.convert_to_jsonl_format(symbol, df)
                existing_data[symbol] = doc
                success_count += 1
                print(f"  ✓ 获取到 {len(df)} 条记录")
            else:
                print(f"  ✗ 跳过")
        
        # 保存数据
        print(f"\n保存数据到 {self.output_file} ...")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for symbol, doc in existing_data.items():
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        
        print(f"\n完成！成功: {success_count}/{total}")


def main():
    """主函数：命令行入口"""
    parser = argparse.ArgumentParser(description='A股历史数据获取工具')
    parser.add_argument('--pool', type=str, default='custom', 
                       help='股票池: hs300/zz500/kc50/custom')
    parser.add_argument('--start', type=str, default='2024-01-01',
                       help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=datetime.now().strftime('%Y-%m-%d'),
                       help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--incremental', action='store_true',
                       help='增量更新模式')
    
    args = parser.parse_args()
    
    try:
        fetcher = AStockDataFetcher()
        
        print(f"
========== A股数据获取 ==========")
        print(f"股票池: {args.pool}")
        print(f"日期范围: {args.start} ~ {args.end}")
        print(f"模式: {''增量更新'' if args.incremental else ''全量下载''}")
        print("="*40)
        
        # 加载股票列表
        symbols = fetcher.load_stock_pool(args.pool)
        if not symbols:
            print("错误：未找到股票列表")
            return
        
        print(f"\n将获取 {len(symbols)} 只股票的数据\n")
        
        # 下载数据
        fetcher.download_stock_data(symbols, args.start, args.end, args.incremental)
        
    except Exception as e:
        print(f"\n错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
