"""
测试数据生成脚本

用于生成A股市场适配测试所需的示例数据文件。
运行此脚本可快速创建测试环境所需的所有数据文件。

使用方法:
    python tests/generate_test_data.py

生成的文件:
    - tests/test_data/astock_list_sample.json
    - tests/test_data/merged_sample.jsonl
    - tests/test_data/consensus_sample.jsonl
    - tests/test_data/backtest_config_sample.json
"""

import json
import os
from datetime import datetime, timedelta


def ensure_test_data_dir():
    """确保测试数据目录存在"""
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
    os.makedirs(test_data_dir, exist_ok=True)
    return test_data_dir


def generate_astock_list_sample():
    """
    生成示例股票列表
    
    包含不同类型的股票:
    - 主板股票
    - ST股票
    - 科创板股票
    - 创业板股票
    """
    stocks = [
        {
            "symbol": "600519.SH",
            "name": "贵州茅台",
            "industry": "白酒",
            "market": "主板",
            "list_date": "2001-08-27",
            "is_st": False,
            "status": "normal"
        },
        {
            "symbol": "600001.SH",
            "name": "邯郸钢铁",
            "industry": "钢铁",
            "market": "主板",
            "list_date": "1992-05-08",
            "is_st": False,
            "status": "normal"
        },
        {
            "symbol": "600005.SH",
            "name": "ST东凌",
            "industry": "食品加工",
            "market": "主板",
            "list_date": "1996-12-18",
            "is_st": True,
            "status": "normal"
        },
        {
            "symbol": "688001.SH",
            "name": "华兴源创",
            "industry": "电子设备",
            "market": "科创板",
            "list_date": "2019-07-22",
            "is_st": False,
            "status": "normal"
        },
        {
            "symbol": "300001.SZ",
            "name": "特锐德",
            "industry": "电气设备",
            "market": "创业板",
            "list_date": "2009-10-30",
            "is_st": False,
            "status": "normal"
        },
        {
            "symbol": "000001.SZ",
            "name": "平安银行",
            "industry": "银行",
            "market": "主板",
            "list_date": "1991-04-03",
            "is_st": False,
            "status": "normal"
        },
        {
            "symbol": "600036.SH",
            "name": "*ST招华",
            "industry": "银行",
            "market": "主板",
            "list_date": "2001-09-18",
            "is_st": True,
            "status": "normal"
        }
    ]
    
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(stocks),
        "stocks": stocks
    }
    
    test_data_dir = ensure_test_data_dir()
    file_path = os.path.join(test_data_dir, "astock_list_sample.json")
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 生成股票列表样本: {file_path}")
    print(f"  - 包含 {len(stocks)} 只股票")
    print(f"  - ST股票: {sum(1 for s in stocks if s['is_st'])} 只")
    return file_path


def generate_merged_sample():
    """
    生成示例行情数据(含不同状态)
    
    包含:
    - 正常交易日
    - 停牌日
    - 涨停日
    - 跌停日
    """
    data_lines = []
    
    # 贵州茅台 - 正常交易日
    data_lines.append({
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
        "status": "normal",
        "suspend_reason": None
    })
    
    # 贵州茅台 - 停牌日
    data_lines.append({
        "symbol": "600519.SH",
        "date": "2024-01-16",
        "open": 1880.00,
        "close": 1880.00,
        "high": 1880.00,
        "low": 1880.00,
        "volume": 0,
        "amount": 0,
        "prev_close": 1880.00,
        "change_pct": 0.00,
        "status": "suspended",
        "suspend_reason": "重大事项停牌"
    })
    
    # 贵州茅台 - 涨停日
    data_lines.append({
        "symbol": "600519.SH",
        "date": "2024-01-17",
        "open": 2050.00,
        "close": 2068.00,
        "high": 2068.00,
        "low": 2050.00,
        "volume": 98765432,
        "amount": 987654321.00,
        "prev_close": 1880.00,
        "change_pct": 10.00,
        "status": "limit_up",
        "suspend_reason": None
    })
    
    # ST东凌 - 正常交易日(ST股票)
    data_lines.append({
        "symbol": "600005.SH",
        "date": "2024-01-15",
        "open": 2.05,
        "close": 2.08,
        "high": 2.10,
        "low": 2.03,
        "volume": 5678901,
        "amount": 11765432.10,
        "prev_close": 2.00,
        "change_pct": 4.00,
        "status": "normal",
        "suspend_reason": None
    })
    
    # ST东凌 - 涨停日(5%涨停)
    data_lines.append({
        "symbol": "600005.SH",
        "date": "2024-01-16",
        "open": 2.10,
        "close": 2.10,
        "high": 2.10,
        "low": 2.08,
        "volume": 8901234,
        "amount": 18765432.10,
        "prev_close": 2.00,
        "change_pct": 5.00,
        "status": "limit_up",
        "suspend_reason": None
    })
    
    # 华兴源创 - 科创板正常交易
    data_lines.append({
        "symbol": "688001.SH",
        "date": "2024-01-15",
        "open": 48.50,
        "close": 50.20,
        "high": 51.00,
        "low": 48.00,
        "volume": 3456789,
        "amount": 171234567.89,
        "prev_close": 48.00,
        "change_pct": 4.58,
        "status": "normal",
        "suspend_reason": None
    })
    
    # 华兴源创 - 科创板涨停(20%)
    data_lines.append({
        "symbol": "688001.SH",
        "date": "2024-01-16",
        "open": 55.00,
        "close": 57.60,
        "high": 57.60,
        "low": 54.00,
        "volume": 6789012,
        "amount": 378901234.56,
        "prev_close": 48.00,
        "change_pct": 20.00,
        "status": "limit_up",
        "suspend_reason": None
    })
    
    # 平安银行 - 跌停日
    data_lines.append({
        "symbol": "000001.SZ",
        "date": "2024-01-15",
        "open": 12.50,
        "close": 11.70,
        "high": 12.60,
        "low": 11.70,
        "volume": 45678901,
        "amount": 545678901.23,
        "prev_close": 13.00,
        "change_pct": -10.00,
        "status": "limit_down",
        "suspend_reason": None
    })
    
    test_data_dir = ensure_test_data_dir()
    file_path = os.path.join(test_data_dir, "merged_sample.jsonl")
    
    with open(file_path, "w", encoding="utf-8") as f:
        for line in data_lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    
    print(f"✓ 生成行情数据样本: {file_path}")
    print(f"  - 包含 {len(data_lines)} 条记录")
    print(f"  - 正常: {sum(1 for d in data_lines if d['status'] == 'normal')}")
    print(f"  - 停牌: {sum(1 for d in data_lines if d['status'] == 'suspended')}")
    print(f"  - 涨停: {sum(1 for d in data_lines if d['status'] == 'limit_up')}")
    print(f"  - 跌停: {sum(1 for d in data_lines if d['status'] == 'limit_down')}")
    return file_path


def generate_consensus_sample():
    """
    生成示例共识数据(含数据缺失情况)
    
    包含:
    - 完整数据
    - 部分数据缺失
    - 全部数据缺失
    """
    data_lines = []
    
    # 贵州茅台 - 完整数据
    data_lines.append({
        "symbol": "600519.SH",
        "date": "2024-01-15",
        "northbound": {
            "net_flow": 100000000.0,
            "buy_amount": 150000000.0,
            "sell_amount": 50000000.0
        },
        "margin": {
            "net_buy": 80000000.0,
            "rzye": 1500000000.0,
            "rzmre": 80000000.0
        },
        "rating": {
            "recommend_count": 15,
            "rating": "买入",
            "target_price": 2100.0
        },
        "industry": {
            "industry_name": "白酒",
            "rank": 3,
            "money_flow": 500000000.0,
            "avg_change": 2.5
        }
    })
    
    # ST东凌 - 部分数据缺失(无券商评级和行业热度)
    data_lines.append({
        "symbol": "600005.SH",
        "date": "2024-01-15",
        "northbound": None,  # 北向资金数据缺失
        "margin": {
            "net_buy": 1000000.0,
            "rzye": 50000000.0,
            "rzmre": 1000000.0
        },
        "rating": None,  # 券商评级缺失
        "industry": {
            "industry_name": "食品加工",
            "rank": 25,
            "money_flow": 10000000.0,
            "avg_change": -0.5
        }
    })
    
    # 华兴源创 - 只有北向资金数据
    data_lines.append({
        "symbol": "688001.SH",
        "date": "2024-01-15",
        "northbound": {
            "net_flow": 50000000.0,
            "buy_amount": 60000000.0,
            "sell_amount": 10000000.0
        },
        "margin": None,  # 融资融券缺失
        "rating": None,  # 券商评级缺失
        "industry": None  # 行业热度缺失
    })
    
    # 平安银行 - 数据完整
    data_lines.append({
        "symbol": "000001.SZ",
        "date": "2024-01-15",
        "northbound": {
            "net_flow": -30000000.0,
            "buy_amount": 20000000.0,
            "sell_amount": 50000000.0
        },
        "margin": {
            "net_buy": -20000000.0,
            "rzye": 800000000.0,
            "rzmre": 30000000.0
        },
        "rating": {
            "recommend_count": 8,
            "rating": "增持",
            "target_price": 15.0
        },
        "industry": {
            "industry_name": "银行",
            "rank": 15,
            "money_flow": 100000000.0,
            "avg_change": -1.2
        }
    })
    
    # 特锐德 - 全部数据缺失
    data_lines.append({
        "symbol": "300001.SZ",
        "date": "2024-01-15",
        "northbound": None,
        "margin": None,
        "rating": None,
        "industry": None
    })
    
    test_data_dir = ensure_test_data_dir()
    file_path = os.path.join(test_data_dir, "consensus_sample.jsonl")
    
    with open(file_path, "w", encoding="utf-8") as f:
        for line in data_lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    
    print(f"✓ 生成共识数据样本: {file_path}")
    print(f"  - 包含 {len(data_lines)} 条记录")
    
    # 统计数据完整性
    complete_count = sum(1 for d in data_lines if all([
        d.get('northbound'), d.get('margin'), d.get('rating'), d.get('industry')
    ]))
    partial_count = len(data_lines) - complete_count - sum(1 for d in data_lines if all([
        not d.get('northbound'), not d.get('margin'), not d.get('rating'), not d.get('industry')
    ]))
    empty_count = sum(1 for d in data_lines if all([
        not d.get('northbound'), not d.get('margin'), not d.get('rating'), not d.get('industry')
    ]))
    
    print(f"  - 完整数据: {complete_count}")
    print(f"  - 部分缺失: {partial_count}")
    print(f"  - 全部缺失: {empty_count}")
    return file_path


def generate_backtest_config_sample():
    """生成示例回测配置"""
    configs = {
        "hs300_conservative": {
            "name": "沪深300稳健策略",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "initial_cash": 1000000,
            "stock_pool": "HS300",
            "max_position_per_stock": 0.20,
            "max_total_position": 0.80,
            "consensus_filter": {
                "enabled": True,
                "min_score": 80,
                "min_data_completeness": 0.75
            },
            "risk_control": {
                "stop_loss": 0.10,
                "take_profit": 0.20,
                "max_drawdown": 0.15
            },
            "transaction_cost": {
                "commission_rate": 0.00025,
                "stamp_tax_rate": 0.001,
                "slippage_rate": 0.005
            }
        },
        "kc50_aggressive": {
            "name": "科创50激进策略",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "initial_cash": 1000000,
            "stock_pool": "KC50",
            "max_position_per_stock": 0.30,
            "max_total_position": 0.95,
            "consensus_filter": {
                "enabled": True,
                "min_score": 70,
                "min_data_completeness": 0.50
            },
            "risk_control": {
                "stop_loss": 0.15,
                "take_profit": 0.30,
                "max_drawdown": 0.25
            },
            "transaction_cost": {
                "commission_rate": 0.00025,
                "stamp_tax_rate": 0.001,
                "slippage_rate": 0.005
            }
        },
        "custom_stocks": {
            "name": "自定义股票池策略",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "initial_cash": 500000,
            "stock_pool": ["600519.SH", "000001.SZ", "688001.SH"],
            "max_position_per_stock": 0.35,
            "max_total_position": 1.00,
            "consensus_filter": {
                "enabled": False
            },
            "risk_control": {
                "stop_loss": 0.08,
                "take_profit": 0.15,
                "max_drawdown": 0.12
            },
            "transaction_cost": {
                "commission_rate": 0.00025,
                "stamp_tax_rate": 0.001,
                "slippage_rate": 0.003
            }
        }
    }
    
    test_data_dir = ensure_test_data_dir()
    
    generated_files = []
    for name, config in configs.items():
        file_path = os.path.join(test_data_dir, f"{name}_config.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        generated_files.append(file_path)
    
    print(f"✓ 生成回测配置样本: {len(generated_files)} 个")
    for fp in generated_files:
        print(f"  - {os.path.basename(fp)}")
    
    return generated_files


def generate_all():
    """生成所有测试数据"""
    print("=" * 60)
    print("开始生成A股市场适配测试数据")
    print("=" * 60)
    print()
    
    try:
        # 生成股票列表
        generate_astock_list_sample()
        print()
        
        # 生成行情数据
        generate_merged_sample()
        print()
        
        # 生成共识数据
        generate_consensus_sample()
        print()
        
        # 生成回测配置
        generate_backtest_config_sample()
        print()
        
        print("=" * 60)
        print("✅ 所有测试数据生成完成!")
        print("=" * 60)
        print()
        print("生成的文件:")
        test_data_dir = ensure_test_data_dir()
        print(f"  目录: {test_data_dir}")
        print(f"  - astock_list_sample.json (股票列表)")
        print(f"  - merged_sample.jsonl (行情数据)")
        print(f"  - consensus_sample.jsonl (共识数据)")
        print(f"  - hs300_conservative_config.json (回测配置)")
        print(f"  - kc50_aggressive_config.json (回测配置)")
        print(f"  - custom_stocks_config.json (回测配置)")
        print()
        print("提示:")
        print("  这些文件可用于单元测试、集成测试和回测系统开发")
        print("  请参考 docs/TEST_IMPLEMENTATION.md 了解如何使用这些数据")
        
    except Exception as e:
        print(f"❌ 生成测试数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = generate_all()
    exit(0 if success else 1)
