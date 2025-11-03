"""
回测运行示例脚本
演示如何使用BacktestEngine和BacktestAgent进行完整回测
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from tools.backtest_engine import BacktestEngine
from agent.base_agent.backtest_agent import BacktestAgent
from tools.backtest_visualizer import BacktestVisualizer


def example1_simple_backtest():
    """示例1：简单的买入持有策略回测"""
    print("\n" + "="*60)
    print("示例1：简单买入持有策略")
    print("="*60)
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    # 定义简单策略：第一天买入，持有到最后
    def buy_and_hold_strategy(date, portfolio_state):
        """买入持有策略"""
        # 仅第一天买入
        if portfolio_state['cash'] > 50000 and not portfolio_state['positions']:
            return [
                {"symbol": "600519.SH", "action": "buy", "shares": 100}
            ]
        return []
    
    # 运行回测
    try:
        results = engine.run(agent_callback=buy_and_hold_strategy)
        
        # 生成报告
        report_path = engine.generate_report(output_name="buy_and_hold")
        
        print(f"\n✅ 回测完成！")
        print(f"📊 报告路径: {report_path}")
        
        # 生成可视化报告
        visualizer = BacktestVisualizer(report_path)
        visualizer.generate_full_report()
        
    except Exception as e:
        print(f"❌ 回测失败: {e}")


def example2_momentum_strategy():
    """示例2：动量策略回测"""
    print("\n" + "="*60)
    print("示例2：动量策略")
    print("="*60)
    
    engine = BacktestEngine()
    
    # 动量策略：追涨
    def momentum_strategy(date, portfolio_state):
        """简单动量策略：买入近期涨幅大的股票"""
        decisions = []
        
        # 这里可以添加更复杂的逻辑
        # 例如：计算股票动量、选择前N只股票等
        
        return decisions
    
    try:
        results = engine.run(agent_callback=momentum_strategy)
        report_path = engine.generate_report(output_name="momentum_strategy")
        
        print(f"\n✅ 回测完成！")
        print(f"📊 报告路径: {report_path}")
        
    except Exception as e:
        print(f"❌ 回测失败: {e}")


async def example3_ai_agent_backtest():
    """示例3：使用AI Agent进行回测"""
    print("\n" + "="*60)
    print("示例3：AI Agent智能交易回测")
    print("="*60)
    
    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  警告：未设置OPENAI_API_KEY，跳过AI Agent回测")
        return
    
    # 首先运行BacktestEngine加载数据
    engine = BacktestEngine()
    
    if not engine.load_historical_data():
        print("❌ 数据加载失败")
        return
    
    engine.load_consensus_data()
    
    # 创建BacktestAgent
    agent = BacktestAgent(
        signature="backtest_ai_agent",
        basemodel="gpt-4o-mini",
        historical_data=engine.historical_data,
        consensus_data=engine.consensus_data,
        initial_cash=100000.0,
        init_date=engine.start_date
    )
    
    try:
        # 初始化Agent
        await agent.initialize()
        
        # 定义Agent决策回调
        async def ai_decision_callback(date, portfolio_state):
            """AI Agent决策回调"""
            # 运行Agent的交易决策
            decision = await agent.run_trading_session(date)
            
            # 从决策中提取交易指令
            # 注：这里需要解析Agent的输出，转换为标准的交易指令格式
            # 实际实现需要根据Agent的输出格式进行适配
            
            return decision.get('actions', [])
        
        # 运行回测（使用异步Agent）
        all_decisions = await agent.run_backtest_date_range(
            start_date=engine.start_date,
            end_date=engine.end_date
        )
        
        print(f"\n✅ AI Agent回测完成！")
        print(f"📊 共处理 {len(all_decisions)} 个交易日")
        
        # 注：由于Agent独立运行，需要单独分析其position.jsonl
        # 这里可以添加对Agent持仓文件的分析逻辑
        
    except Exception as e:
        print(f"❌ AI Agent回测失败: {e}")
        import traceback
        traceback.print_exc()


def example4_data_validation():
    """示例4：数据完整性检查"""
    print("\n" + "="*60)
    print("示例4：数据完整性验证")
    print("="*60)
    
    engine = BacktestEngine()
    
    # 加载数据
    if not engine.load_historical_data():
        print("❌ 数据加载失败")
        return
    
    # 统计数据
    total_stocks = len(engine.historical_data)
    print(f"✅ 成功加载 {total_stocks} 只股票的历史数据")
    
    # 检查每只股票的数据完整性
    from datetime import datetime, timedelta
    
    start_dt = datetime.strptime(engine.start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(engine.end_date, '%Y-%m-%d')
    
    expected_days = (end_dt - start_dt).days + 1
    
    print(f"\n日期范围: {engine.start_date} 至 {engine.end_date}")
    print(f"预期天数: {expected_days} 天")
    
    incomplete_stocks = []
    
    for symbol, data in engine.historical_data.items():
        actual_days = len(data)
        coverage = actual_days / expected_days * 100
        
        if coverage < 80:  # 数据覆盖率低于80%
            incomplete_stocks.append((symbol, actual_days, coverage))
    
    if incomplete_stocks:
        print(f"\n⚠️  发现 {len(incomplete_stocks)} 只股票数据不完整（覆盖率<80%）:")
        for symbol, days, coverage in incomplete_stocks[:10]:
            print(f"  - {symbol}: {days}天 ({coverage:.1f}%)")
        if len(incomplete_stocks) > 10:
            print(f"  ... 还有 {len(incomplete_stocks) - 10} 只")
    else:
        print(f"\n✅ 所有股票数据完整性检查通过")
    
    # 检查共识数据
    engine.load_consensus_data()
    
    if engine.consensus_data:
        consensus_days = len(engine.consensus_data)
        print(f"\n共识数据: 共 {consensus_days} 个交易日")
        
        # 统计每日有共识数据的股票数量
        avg_stocks_per_day = sum(len(stocks) for stocks in engine.consensus_data.values()) / consensus_days
        print(f"平均每日有共识数据的股票: {avg_stocks_per_day:.1f} 只")
    else:
        print(f"\n⚠️  未找到共识数据")


def example5_time_travel_test():
    """示例5：时间旅行测试（防止未来数据泄露）"""
    print("\n" + "="*60)
    print("示例5：时间旅行防护测试")
    print("="*60)
    
    engine = BacktestEngine()
    
    if not engine.load_historical_data():
        print("❌ 数据加载失败")
        return
    
    # 设置当前回测日期
    test_date = "2024-06-15"
    engine.current_date = test_date
    
    print(f"当前回测日期: {test_date}")
    
    # 测试1：尝试使用未来日期的数据
    print("\n测试1：尝试访问未来数据...")
    future_date = "2024-06-20"
    
    valid, error = engine.check_trade_validity(
        symbol="600519.SH",
        action="buy",
        shares=100,
        date=future_date
    )
    
    if not valid:
        print(f"✅ 时间旅行防护生效: {error}")
    else:
        print(f"❌ 时间旅行防护失败：应该阻止未来数据访问")
    
    # 测试2：使用当天数据（应该允许）
    print("\n测试2：访问当天数据...")
    
    valid, error = engine.check_trade_validity(
        symbol="600519.SH",
        action="buy",
        shares=100,
        date=test_date
    )
    
    if valid:
        print(f"✅ 当天数据访问正常")
    else:
        print(f"❌ 当天数据访问被阻止: {error}")
    
    # 测试3：使用历史数据（应该允许）
    print("\n测试3：访问历史数据...")
    past_date = "2024-06-10"
    
    valid, error = engine.check_trade_validity(
        symbol="600519.SH",
        action="buy",
        shares=100,
        date=past_date
    )
    
    if valid:
        print(f"✅ 历史数据访问正常")
    else:
        print(f"❌ 历史数据访问被阻止: {error}")
    
    print("\n✅ 时间旅行防护测试完成")


def main():
    """主函数：运行所有示例"""
    print("\n" + "="*80)
    print(" "*20 + "AI-Trader 回测系统示例")
    print("="*80)
    
    # 显示菜单
    print("\n请选择要运行的示例:")
    print("1. 简单买入持有策略回测")
    print("2. 动量策略回测")
    print("3. AI Agent智能交易回测（需要OpenAI API）")
    print("4. 数据完整性验证")
    print("5. 时间旅行防护测试")
    print("6. 运行所有示例")
    print("0. 退出")
    
    choice = input("\n请输入选项 (0-6): ").strip()
    
    if choice == "1":
        example1_simple_backtest()
    elif choice == "2":
        example2_momentum_strategy()
    elif choice == "3":
        asyncio.run(example3_ai_agent_backtest())
    elif choice == "4":
        example4_data_validation()
    elif choice == "5":
        example5_time_travel_test()
    elif choice == "6":
        print("\n运行所有示例...\n")
        example4_data_validation()
        example5_time_travel_test()
        example1_simple_backtest()
        # example2_momentum_strategy()
        # asyncio.run(example3_ai_agent_backtest())
    elif choice == "0":
        print("退出")
        return
    else:
        print("无效选项")
    
    print("\n" + "="*80)
    print("示例运行完成！")
    print("="*80)


if __name__ == "__main__":
    main()
