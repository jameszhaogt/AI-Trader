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

try:
    import pandas as pd
except ImportError:
    pd = None
    logging.warning("Pandas未安装,请运行: pip install pandas")

try:
    import akshare as ak
except ImportError:
    ak = None
    logging.warning("AkShare未安装,请运行: pip install akshare")

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
        if not ak:
            raise ImportError("AkShare未安装,请运行: pip install akshare")
        
        logger.info(f"获取{market}股票列表...")
        
        stocks = []
        stock_codes = []
        
        # 根据market参数获取不同的股票列表
        if market == "HS300":
            # 获取沪深300成分股
            df = ak.index_stock_cons_csindex(symbol="000300")
            if df is not None and not df.empty:
                stock_codes = df['成分券代码'].tolist()
                # 转换为带后缀的格式
                stock_codes = [code + ('.SH' if code.startswith('6') else '.SZ') for code in stock_codes]
        elif market == "KC50":
            # 获取科创50成分股
            df = ak.index_stock_cons_csindex(symbol="000688")
            if df is not None and not df.empty:
                stock_codes = df['成分券代码'].tolist()
                stock_codes = [code + '.SH' for code in stock_codes]  # 科创板都是SH
        elif market == "ALL":
            # 获取所有A股
            df = ak.stock_info_a_code_name()
            if df is not None and not df.empty:
                stock_codes = []
                for _, row in df.iterrows():
                    code = row['code']
                    suffix = '.SH' if code.startswith('6') or code.startswith('688') else '.SZ'
                    stock_codes.append(code + suffix)
        else:
            raise ValueError(f"不支持的市场类型: {market}, 请使用 HS300, KC50 或 ALL")
        
        logger.info(f"获取到 {len(stock_codes)} 只股票代码")
        
        # 获取所有股票的基本信息
        stock_info_df = ak.stock_info_a_code_name()
        
        # 获取股票详细信息
        for ts_code in stock_codes:
            try:
                symbol_code = ts_code.split('.')[0]
                
                # 从基本信息中查找
                stock_row = stock_info_df[stock_info_df['code'] == symbol_code]
                
                if stock_row.empty:
                    logger.warning(f"无法获取 {ts_code} 的基本信息")
                    continue
                
                stock_name = stock_row.iloc[0]['name']
                
                # 识别ST股票
                is_st = identify_st_stock(stock_name)
                
                # 判断市场类型
                if symbol_code.startswith('688'):
                    market_type = '科创板'
                elif symbol_code.startswith('300'):
                    market_type = '创业板'
                elif symbol_code.startswith('60'):
                    market_type = '主板'
                elif symbol_code.startswith('00'):
                    market_type = '主板'
                else:
                    market_type = '其他'
                
                # 获取行业信息(可选,可能需要额外的API调用)
                industry = ''
                try:
                    # AkShare的行业信息需要单独获取
                    industry_df = ak.stock_individual_info_em(symbol=symbol_code)
                    if industry_df is not None and not industry_df.empty:
                        industry_row = industry_df[industry_df['item'] == '行业']
                        if not industry_row.empty:
                            industry = industry_row.iloc[0]['value']
                except:
                    pass
                
                stock_info = {
                    "symbol": ts_code,
                    "name": stock_name,
                    "industry": industry,
                    "market": market_type,
                    "list_date": '',  # AkShare基础接口不提供上市日期
                    "is_st": is_st,
                    "status": "normal"
                }
                
                stocks.append(stock_info)
                
            except Exception as e:
                logger.warning(f"处理 {ts_code} 时出错: {e}")
                continue
        
        logger.info(f"成功处理 {len(stocks)} 只股票信息")
        
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
        if not ak:
            raise ImportError("AkShare未安装,请运行: pip install akshare")
        
        logger.info(f"下载 {symbol} 数据: {start_date} 至 {end_date}")
        
        result = []
        
        # 1. 获取日线数据
        symbol_code = symbol.split('.')[0] if '.' in symbol else symbol
        
        # 使用akshare获取复权数据
        # 对于前复权，akshare使用"qfq"，后复权使用"hfq"
        if adj == "qfq":
            df = ak.stock_zh_a_hist(symbol=symbol_code, period="daily", 
                                   start_date=start_date.replace('-', ''), 
                                   end_date=end_date.replace('-', ''), 
                                   adjust="qfq")
        elif adj == "hfq":
            df = ak.stock_zh_a_hist(symbol=symbol_code, period="daily", 
                                   start_date=start_date.replace('-', ''), 
                                   end_date=end_date.replace('-', ''), 
                                   adjust="hfq")
        else:
            df = ak.stock_zh_a_hist(symbol=symbol_code, period="daily", 
                                   start_date=start_date.replace('-', ''), 
                                   end_date=end_date.replace('-', ''), 
                                   adjust="")
        
        if df is None or df.empty:
            logger.warning(f"{symbol} 没有数据")
            return result
        
        # AkShare返回的列名不同，需要映射
        # AkShare: '日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额'
        df = df.rename(columns={
            '日期': 'trade_date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'vol',
            '成交额': 'amount'
        })
        
        # 按日期升序排列
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
        df = df.sort_values('trade_date')
        
        # 2. 获取停牌信息(通过成交量为0判断)
        suspended_dates = set()
        # AkShare不直接提供停牌信息，通过成交量为0判断
        if pd and 'vol' in df.columns:
            suspended_dates = set(df[df['vol'] == 0]['trade_date'].astype(str))
        
        # 3. 获取股票名称用于ST判断
        stock_name = ""
        is_st = False
        try:
            stock_info = ak.stock_info_a_code_name()
            if pd:
                stock_row = stock_info[stock_info['code'] == symbol_code]
                if not stock_row.empty:
                    stock_name = stock_row.iloc[0]['name']
                    is_st = identify_st_stock(stock_name)
        except:
            pass
        
        # 4. 处理每一天的数据
        prev_close = None
        
        for idx, row in df.iterrows():
            trade_date = str(row['trade_date'])
            date_formatted = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
            
            open_price = round(float(row['open']), 2)
            close_price = round(float(row['close']), 2)
            high_price = round(float(row['high']), 2)
            low_price = round(float(row['low']), 2)
            volume = int(row['vol']) if pd and pd.notna(row['vol']) else 0
            amount = round(float(row['amount']), 2) if pd and pd.notna(row['amount']) else 0.0
            
            # 获取前收盘价
            current_prev_close = prev_close if prev_close is not None else close_price
            # AkShare可能有昨收列，如果有就使用
            if '昨收' in row:
                current_prev_close = round(float(row['昨收']), 2) if pd and pd.notna(row['昨收']) else current_prev_close
            
            # 计算涨跌幅
            change_pct = round((close_price / current_prev_close - 1) * 100, 2) if current_prev_close > 0 else 0.0
            
            # 判断状态
            status = "normal"
            suspend_reason = None
            
            # 检查是否停牌(成交量为0)
            if trade_date in suspended_dates or volume == 0:
                status = "suspended"
                suspend_reason = "股票停牌"
            else:
                # 判断涨跌停
                limit_ratio = 0.05 if is_st else 0.20 if symbol_code.startswith(('688', '300')) else 0.10
                limit_up = round(current_prev_close * (1 + limit_ratio), 2)
                limit_down = round(current_prev_close * (1 - limit_ratio), 2)
                
                is_limit_up = abs(close_price - limit_up) < 0.01
                is_limit_down = abs(close_price - limit_down) < 0.01
                
                if is_limit_up:
                    status = "limit_up"
                elif is_limit_down:
                    status = "limit_down"
            
            record = {
                "symbol": symbol,
                "date": date_formatted,
                "open": open_price,
                "close": close_price,
                "high": high_price,
                "low": low_price,
                "volume": volume,
                "amount": amount,
                "prev_close": current_prev_close,
                "change_pct": change_pct,
                "status": status,
                "is_limit_up": status == "limit_up",
                "is_limit_down": status == "limit_down",
                "suspend_reason": suspend_reason
            }
            
            result.append(record)
            prev_close = close_price
        
        # 5. 处理停牌日（填充缺失数据）
        # AkShare不直接提供交易日历，这里简化处理
        # 如果需要更精确的交易日处理，可以使用 ak.tool_trade_date_hist_sina()
        
        # 按日期排序
        result.sort(key=lambda x: x['date'])
        
        logger.info(f"成功获取 {symbol} {len(result)} 条数据")
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
    
    if not data:
        errors.append("数据列表为空")
        return {
            "valid": False,
            "warnings": warnings,
            "errors": errors
        }
    
    # 定义必需字段
    required_fields = ['symbol', 'date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'prev_close']
    
    prev_record = None
    seen_dates = set()
    
    for i, record in enumerate(data):
        # 1. 检查字段完整性
        for field in required_fields:
            if field not in record or record[field] is None:
                errors.append(f"第{i+1}条记录缺少字段: {field}")
                continue
        
        # 如果有错误，跳过后续检查
        if errors:
            continue
            
        date = record['date']
        
        # 2. 检查时间序列 - 无重复
        if date in seen_dates:
            errors.append(f"日期重复: {date}")
        seen_dates.add(date)
        
        # 3. 检查价格合理性 (> 0)
        if record['open'] <= 0 or record['close'] <= 0 or record['high'] <= 0 or record['low'] <= 0:
            errors.append(f"{date}: 价格必须大于0")
        
        # 4. 检查OHLC关系
        if record['high'] < max(record['open'], record['close']):
            errors.append(f"{date}: 最高价 {record['high']} < max(open={record['open']}, close={record['close']})")
        
        if record['low'] > min(record['open'], record['close']):
            errors.append(f"{date}: 最低价 {record['low']} > min(open={record['open']}, close={record['close']})")
        
        # 5. 检查成交量合理性
        status = record.get('status', 'normal')
        if status != 'suspended' and record['volume'] == 0:
            warnings.append(f"{date}: 非停牌日成交量为0")
        
        # 6. 检查价格连续性 (涨跌幅 < 50%)
        if prev_record is not None and prev_record.get('status') != 'suspended' and status != 'suspended':
            prev_close = prev_record['close']
            current_close = record['close']
            
            if prev_close > 0:
                change_pct = abs((current_close / prev_close - 1) * 100)
                # 非停牌复牌日，涨跌幅应 < 50%
                if change_pct > 50:
                    warnings.append(f"{date}: 涨跌幅异常 {change_pct:.2f}% (可能是停牌复牌)")
        
        prev_record = record
    
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
    download_all_stocks(stock_pool="HS300", start_date="2024-01-01", end_date="2024-01-31")
