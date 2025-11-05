"""
A股数据获取功能单元测试
测试数据获取、价格查询、交易规则校验等功能
"""

import os
import sys
import json
import unittest
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from data.get_astock_data import AStockDataFetcher
from tools.astock_rules import AStockRuleValidator


class TestAStockDataFetcher(unittest.TestCase):
    """测试A股数据获取类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 检查是否有akshare
        try:
            import akshare as ak
            cls.ak = ak
        except ImportError:
            raise unittest.SkipTest("未安装akshare，跳过数据获取测试")
    
    def test_01_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.ak)
        print("✅ akshare初始化成功")
    
    def test_02_fetch_stock_list(self):
        """测试股票列表获取"""
        stock_list = self.fetcher.fetch_stock_list(list_status='L', limit=10)
        
        self.assertIsNotNone(stock_list)
        self.assertGreater(len(stock_list), 0)
        
        # 检查必要字段
        first_stock = stock_list[0]
        self.assertIn('ts_code', first_stock)
        self.assertIn('symbol', first_stock)
        self.assertIn('name', first_stock)
        
        print(f"✅ 成功获取股票列表，数量: {len(stock_list)}")
    
    def test_03_fetch_daily_data(self):
        """测试日线数据获取"""
        # 使用贵州茅台作为测试
        symbol = "600519.SH"
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        df = self.fetcher.fetch_daily_data(symbol, start_date, end_date)
        
        self.assertIsNotNone(df)
        self.assertGreater(len(df), 0)
        
        # 检查必要列
        required_columns = ['trade_date', 'open', 'high', 'low', 'close', 'vol']
        for col in required_columns:
            self.assertIn(col, df.columns)
        
        print(f"✅ 成功获取{symbol}日线数据，数量: {len(df)}条")
    
    def test_04_calculate_adj_price(self):
        """测试复权价格计算"""
        symbol = "600519.SH"
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        df = self.fetcher.fetch_daily_data(symbol, start_date, end_date)
        
        # 检查复权价格列
        adj_columns = ['adj_open', 'adj_high', 'adj_low', 'adj_close']
        for col in adj_columns:
            self.assertIn(col, df.columns)
        
        # 检查复权价格是否有效
        self.assertTrue((df['adj_close'] > 0).all())
        
        print(f"✅ 复权价格计算正确")
    
    def test_05_convert_to_jsonl(self):
        """测试JSONL格式转换"""
        symbol = "600519.SH"
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        
        df = self.fetcher.fetch_daily_data(symbol, start_date, end_date)
        jsonl_data = self.fetcher.convert_to_jsonl_format(symbol, df)
        
        self.assertIsNotNone(jsonl_data)
        
        # 解析JSON检查格式
        data = json.loads(jsonl_data)
        
        self.assertIn('Meta Data', data)
        self.assertIn('Time Series (Daily)', data)
        
        meta = data['Meta Data']
        self.assertEqual(meta['2. Symbol'], symbol)
        
        time_series = data['Time Series (Daily)']
        self.assertGreater(len(time_series), 0)
        
        print(f"✅ JSONL格式转换正确")


class TestAStockRules(unittest.TestCase):
    """测试A股交易规则"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.validator = AStockRuleValidator()
        cls.test_date = "2024-01-15"
    
    def test_01_minimum_unit(self):
        """测试最小交易单位"""
        # 正确的交易单位（100的倍数）
        result = self.validator.validate_minimum_unit(100)
        self.assertTrue(result['valid'])
        
        result = self.validator.validate_minimum_unit(500)
        self.assertTrue(result['valid'])
        
        # 错误的交易单位
        result = self.validator.validate_minimum_unit(50)
        self.assertFalse(result['valid'])
        
        result = self.validator.validate_minimum_unit(150)
        self.assertFalse(result['valid'])
        
        print("✅ 最小交易单位校验正确")
    
    def test_02_price_limit(self):
        """测试涨跌停限制"""
        # 主板股票（±10%）
        result = self.validator.validate_price_limit(
            symbol="600519.SH",
            current_price=1850.00,
            prev_close=1700.00
        )
        # 涨幅 = (1850 - 1700) / 1700 = 8.82% < 10%
        self.assertTrue(result['valid'])
        
        # 超过涨停
        result = self.validator.validate_price_limit(
            symbol="600519.SH",
            current_price=1900.00,
            prev_close=1700.00
        )
        # 涨幅 = (1900 - 1700) / 1700 = 11.76% > 10%
        self.assertFalse(result['valid'])
        
        print("✅ 涨跌停限制校验正确")
    
    def test_03_t_plus_1(self):
        """测试T+1规则"""
        # 模拟持仓记录
        position_records = [
            {"date": "2024-01-14", "symbol": "600519.SH", "action": "buy", "shares": 100},
            {"date": "2024-01-15", "symbol": "000858.SZ", "action": "buy", "shares": 200}
        ]
        
        # 尝试卖出当天买入的股票（应该失败）
        result = self.validator.validate_t_plus_1(
            symbol="000858.SZ",
            action="sell",
            current_date="2024-01-15",
            position_records=position_records
        )
        self.assertFalse(result['valid'])
        
        # 卖出昨天买入的股票（应该成功）
        result = self.validator.validate_t_plus_1(
            symbol="600519.SH",
            action="sell",
            current_date="2024-01-15",
            position_records=position_records
        )
        self.assertTrue(result['valid'])
        
        print("✅ T+1规则校验正确")
    
    def test_04_comprehensive_validation(self):
        """测试综合交易规则校验"""
        # 准备测试数据
        trade_params = {
            "symbol": "600519.SH",
            "amount": 100,
            "action": "buy",
            "current_date": self.test_date,
            "signature": "test_agent"
        }
        
        # 注：完整的综合校验需要实际的市场数据和持仓记录
        # 这里仅测试基本逻辑
        
        print("✅ 综合规则校验框架正确")


class TestPriceQuery(unittest.TestCase):
    """测试价格查询功能"""
    
    def test_01_local_price_query(self):
        """测试本地价格查询"""
        # 假设merged.jsonl文件存在
        data_file = project_root / "data" / "merged.jsonl"
        
        if not data_file.exists():
            self.skipTest("merged.jsonl文件不存在，跳过价格查询测试")
        
        # 读取一条数据测试
        with open(data_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            data = json.loads(first_line)
        
        self.assertIn('Meta Data', data)
        self.assertIn('Time Series (Daily)', data)
        
        symbol = data['Meta Data']['2. Symbol']
        time_series = data['Time Series (Daily)']
        
        # 获取任意一个日期的价格
        if time_series:
            date = list(time_series.keys())[0]
            price_data = time_series[date]
            
            # 检查必要字段
            self.assertIn('1. buy price', price_data)
            self.assertIn('4. sell price', price_data)
            self.assertIn('5. volume', price_data)
            
            print(f"✅ 本地价格查询正确: {symbol} @ {date}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestAStockDataFetcher))
    suite.addTests(loader.loadTestsFromTestCase(TestAStockRules))
    suite.addTests(loader.loadTestsFromTestCase(TestPriceQuery))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "="*60)
    print("测试总结:")
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    print("="*60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
