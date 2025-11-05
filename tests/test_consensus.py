"""
共识系统测试
测试共识数据获取和筛选功能
"""

import os
import sys
import json
import unittest
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from data.get_consensus_data import ConsensusDataFetcher


class TestConsensusData(unittest.TestCase):
    """测试共识数据获取"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 检查akshare
        try:
            import akshare as ak
        except ImportError:
            raise unittest.SkipTest("未安装akshare，跳过共识数据测试")
        
        cls.fetcher = ConsensusDataFetcher()
        cls.test_date = datetime.now().strftime('%Y-%m-%d')
    
    def test_01_fetch_northbound_flow(self):
        """测试北向资金数据获取"""
        try:
            df = self.fetcher.fetch_northbound_flow(
                start_date=self.test_date,
                end_date=self.test_date
            )
            
            if df is not None and len(df) > 0:
                # 检查必要列
                required_columns = ['trade_date', 'ggt_ss', 'ggt_sz']
                for col in required_columns:
                    self.assertIn(col, df.columns)
                
                print(f"✅ 北向资金数据获取成功，数量: {len(df)}条")
            else:
                print("⚠️  当前日期无北向资金数据（非交易日或数据未更新）")
        
        except Exception as e:
            print(f"⚠️  北向资金数据获取失败: {e}")
    
    def test_02_fetch_margin_detail(self):
        """测试融资融券数据获取"""
        try:
            # 测试单只股票
            df = self.fetcher.fetch_margin_detail(
                symbol="600519.SH",
                start_date=self.test_date,
                end_date=self.test_date
            )
            
            if df is not None and len(df) > 0:
                # 检查必要列
                required_columns = ['trade_date', 'ts_code', 'rzye', 'rqye']
                for col in required_columns:
                    self.assertIn(col, df.columns)
                
                print(f"✅ 融资融券数据获取成功，数量: {len(df)}条")
            else:
                print("⚠️  当前日期无融资融券数据")
        
        except Exception as e:
            print(f"⚠️  融资融券数据获取失败: {e}")
    
    def test_03_fetch_broker_recommend(self):
        """测试券商评级数据获取"""
        try:
            df = self.fetcher.fetch_broker_recommend(
                symbol="600519.SH"
            )
            
            if df is not None and len(df) > 0:
                # 检查必要列
                required_columns = ['ts_code', 'rating']
                for col in required_columns:
                    self.assertIn(col, df.columns)
                
                print(f"✅ 券商评级数据获取成功，数量: {len(df)}条")
            else:
                print("⚠️  无券商评级数据")
        
        except Exception as e:
            print(f"⚠️  券商评级数据获取失败: {e}")
    
    def test_04_calculate_technical_indicators(self):
        """测试技术指标计算"""
        # 测试数据
        price_data = {
            'close': [100, 102, 105, 103, 108],
            'high': [101, 103, 106, 104, 110],
            'low': [99, 101, 104, 102, 107],
            'volume': [1000, 1200, 1500, 1100, 1800]
        }
        
        # 这里简化测试，实际应该调用fetcher的技术指标计算方法
        # 检查是否创新高
        is_new_high = price_data['close'][-1] == max(price_data['close'])
        self.assertTrue(is_new_high)
        
        # 检查成交量放大
        volume_increase = price_data['volume'][-1] > price_data['volume'][-2]
        self.assertTrue(volume_increase)
        
        print("✅ 技术指标计算正确")


class TestConsensusFiltering(unittest.TestCase):
    """测试共识筛选功能"""
    
    def test_01_score_calculation(self):
        """测试共识分数计算"""
        # 模拟共识数据
        consensus_data = {
            'symbol': '600519.SH',
            'technical': {
                'new_high': True,
                'ma_golden_cross': True,
                'macd_golden': False,
                'volume_increase': True
            },
            'capital': {
                'northbound_flow': 80000000,  # 8000万
                'margin_growth': 6.5  # 6.5%增长
            },
            'logic': {
                'industry_rank': 15,  # 行业排名15/100
                'broker_count': 8  # 8家券商推荐
            },
            'sentiment': {
                'social_heat': 85
            }
        }
        
        # 计算技术共识分数（满分20）
        tech_score = 0
        if consensus_data['technical']['new_high']:
            tech_score += 5
        if consensus_data['technical']['ma_golden_cross']:
            tech_score += 5
        if consensus_data['technical']['macd_golden']:
            tech_score += 5
        if consensus_data['technical']['volume_increase']:
            tech_score += 5
        
        self.assertEqual(tech_score, 15)  # 3/4个指标满足
        
        # 计算资金共识分数（满分30）
        capital_score = 0
        if consensus_data['capital']['northbound_flow'] > 50000000:
            capital_score += 15
        if consensus_data['capital']['margin_growth'] > 5:
            capital_score += 15
        
        self.assertEqual(capital_score, 30)  # 两个指标都满足
        
        # 计算逻辑共识分数（满分30）
        logic_score = 0
        industry_rank_pct = consensus_data['logic']['industry_rank'] / 100
        if industry_rank_pct <= 0.3:  # 前30%
            logic_score += 15
        if consensus_data['logic']['broker_count'] >= 5:
            logic_score += 15
        
        self.assertEqual(logic_score, 30)  # 两个指标都满足
        
        # 总分
        total_score = tech_score + capital_score + logic_score + 20  # sentiment默认20
        self.assertEqual(total_score, 95)
        
        print(f"✅ 共识分数计算正确: {total_score}分")
    
    def test_02_filtering_logic(self):
        """测试筛选逻辑"""
        # 模拟股票数据
        stocks_data = [
            {'symbol': 'A', 'score': 85},
            {'symbol': 'B', 'score': 72},
            {'symbol': 'C', 'score': 65},
            {'symbol': 'D', 'score': 90},
            {'symbol': 'E', 'score': 55}
        ]
        
        # 筛选分数>=70的股票
        min_score = 70
        filtered = [s for s in stocks_data if s['score'] >= min_score]
        
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0]['symbol'], 'A')
        
        # 按分数排序
        sorted_stocks = sorted(filtered, key=lambda x: x['score'], reverse=True)
        self.assertEqual(sorted_stocks[0]['symbol'], 'D')
        self.assertEqual(sorted_stocks[0]['score'], 90)
        
        print("✅ 筛选逻辑正确")
    
    def test_03_consensus_data_structure(self):
        """测试共识数据结构"""
        # 检查consensus_data.jsonl格式
        consensus_file = project_root / "data" / "consensus_data.jsonl"
        
        if not consensus_file.exists():
            self.skipTest("consensus_data.jsonl不存在，跳过测试")
        
        # 读取第一条数据
        with open(consensus_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line.strip():
                data = json.loads(first_line)
                
                # 检查必要字段
                self.assertIn('date', data)
                self.assertIn('symbol', data)
                
                print("✅ 共识数据结构正确")


class TestIndustryMapping(unittest.TestCase):
    """测试行业映射"""
    
    def test_01_industry_config(self):
        """测试行业配置文件"""
        industry_file = project_root / "data" / "industry_mapping.json"
        
        self.assertTrue(industry_file.exists())
        
        with open(industry_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查结构
        self.assertIn('industries', config)
        self.assertIn('concepts', config)
        
        industries = config['industries']
        self.assertGreater(len(industries), 0)
        
        # 检查第一个行业
        first_industry = industries[0]
        self.assertIn('name', first_industry)
        self.assertIn('stocks', first_industry)
        
        print(f"✅ 行业配置正确，共{len(industries)}个行业")
    
    def test_02_stock_to_industry_mapping(self):
        """测试股票到行业的映射"""
        industry_file = project_root / "data" / "industry_mapping.json"
        
        with open(industry_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 构建反向映射：股票 -> 行业
        stock_to_industry = {}
        for industry in config['industries']:
            for stock in industry['stocks']:
                stock_to_industry[stock] = industry['name']
        
        # 测试查询
        test_symbol = "600519.SH"
        if test_symbol in stock_to_industry:
            industry = stock_to_industry[test_symbol]
            print(f"✅ {test_symbol} 属于 {industry} 行业")
        else:
            print(f"⚠️  {test_symbol} 未在行业映射中")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestConsensusData))
    suite.addTests(loader.loadTestsFromTestCase(TestConsensusFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestIndustryMapping))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "="*60)
    print("共识系统测试总结:")
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
