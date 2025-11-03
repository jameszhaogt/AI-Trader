"""
回测可视化工具
生成资金曲线、回撤图、持仓分布等可视化报告
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.font_manager import FontProperties
except ImportError:
    print("错误：缺少依赖包，请运行: pip install pandas numpy matplotlib")
    sys.exit(1)


# 设置中文字体
def setup_chinese_font():
    """配置中文字体"""
    # 尝试多种中文字体
    chinese_fonts = [
        'SimHei',  # 黑体
        'Microsoft YaHei',  # 微软雅黑
        'STSong',  # 华文宋体
        'Arial Unicode MS',
    ]
    
    for font in chinese_fonts:
        try:
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False
            return
        except:
            continue
    
    print("警告：未找到中文字体，图表可能显示乱码")


class BacktestVisualizer:
    """回测可视化类"""
    
    def __init__(self, backtest_results_path: str):
        """初始化可视化器
        
        Args:
            backtest_results_path: 回测结果目录路径
        """
        self.results_path = Path(backtest_results_path)
        
        # 加载数据
        self.metrics = self._load_metrics()
        self.daily_positions = self._load_daily_positions()
        self.trades = self._load_trades()
        
        # 设置中文字体
        setup_chinese_font()
    
    def _load_metrics(self) -> Dict[str, Any]:
        """加载绩效指标"""
        metrics_file = self.results_path / "metrics.json"
        if not metrics_file.exists():
            return {}
        
        with open(metrics_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_daily_positions(self) -> List[Dict[str, Any]]:
        """加载每日持仓"""
        positions_file = self.results_path / "daily_positions.jsonl"
        if not positions_file.exists():
            return []
        
        positions = []
        with open(positions_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    positions.append(json.loads(line))
        
        return positions
    
    def _load_trades(self) -> List[Dict[str, Any]]:
        """加载交易明细"""
        trades_file = self.results_path / "trades.jsonl"
        if not trades_file.exists():
            return []
        
        trades = []
        with open(trades_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    trades.append(json.loads(line))
        
        return trades
    
    def plot_portfolio_value(self, save_path: Optional[str] = None):
        """绘制资金曲线
        
        Args:
            save_path: 保存路径，None则显示
        """
        if not self.daily_positions:
            print("无每日持仓数据")
            return
        
        # 提取数据
        dates = [record['date'] for record in self.daily_positions]
        values = [record['portfolio_value'] for record in self.daily_positions]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 绘制曲线
        ax.plot(dates, values, linewidth=2, color='#1f77b4', label='组合价值')
        
        # 添加基准线
        initial_value = values[0]
        ax.axhline(y=initial_value, color='gray', linestyle='--', 
                   linewidth=1, label=f'初始资金: {initial_value:,.0f}')
        
        # 设置标题和标签
        ax.set_title('回测资金曲线', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('资产价值 (元)', fontsize=12)
        
        # 格式化y轴
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # 设置x轴日期格式
        if len(dates) > 60:
            # 超过60天，每月显示
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        else:
            # 少于60天，每周显示
            ax.xaxis.set_major_locator(mdates.WeekdayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.xticks(rotation=45)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 添加图例
        ax.legend(loc='best', fontsize=10)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"资金曲线已保存: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_drawdown(self, save_path: Optional[str] = None):
        """绘制回撤曲线
        
        Args:
            save_path: 保存路径，None则显示
        """
        if not self.daily_positions:
            print("无每日持仓数据")
            return
        
        # 提取数据
        dates = [record['date'] for record in self.daily_positions]
        values = [record['portfolio_value'] for record in self.daily_positions]
        
        # 计算回撤
        df = pd.DataFrame({'date': dates, 'value': values})
        df['cummax'] = df['value'].cummax()
        df['drawdown'] = (df['value'] - df['cummax']) / df['cummax'] * 100
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 绘制回撤曲线
        ax.fill_between(df['date'], df['drawdown'], 0, 
                        color='#d62728', alpha=0.3, label='回撤')
        ax.plot(df['date'], df['drawdown'], linewidth=1.5, color='#d62728')
        
        # 标注最大回撤点
        max_dd_idx = df['drawdown'].idxmin()
        max_dd_value = df.loc[max_dd_idx, 'drawdown']
        max_dd_date = df.loc[max_dd_idx, 'date']
        
        ax.plot(max_dd_date, max_dd_value, 'ro', markersize=8, 
               label=f'最大回撤: {max_dd_value:.2f}%')
        ax.annotate(f'{max_dd_value:.2f}%', 
                   xy=(max_dd_date, max_dd_value),
                   xytext=(10, -10), textcoords='offset points',
                   fontsize=10, color='red',
                   bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7))
        
        # 设置标题和标签
        ax.set_title('回撤分析', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('回撤 (%)', fontsize=12)
        
        # 设置x轴日期格式
        if len(dates) > 60:
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        else:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.xticks(rotation=45)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        
        # 添加图例
        ax.legend(loc='best', fontsize=10)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"回撤曲线已保存: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_positions_distribution(self, save_path: Optional[str] = None):
        """绘制持仓分布饼图
        
        Args:
            save_path: 保存路径，None则显示
        """
        if not self.daily_positions:
            print("无每日持仓数据")
            return
        
        # 获取最后一天的持仓
        last_position = self.daily_positions[-1]
        positions = last_position.get('positions', {})
        
        # 过滤掉现金和0持仓
        stock_positions = {k: v for k, v in positions.items() 
                          if k != 'CASH' and v > 0}
        
        if not stock_positions:
            print("无股票持仓")
            return
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 准备数据
        symbols = list(stock_positions.keys())
        shares = list(stock_positions.values())
        
        # 绘制饼图
        colors = plt.cm.Set3(range(len(symbols)))
        wedges, texts, autotexts = ax.pie(shares, labels=symbols, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        
        # 设置标题
        ax.set_title(f'持仓分布 ({last_position["date"]})', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # 美化文本
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        # 添加图例
        ax.legend(wedges, symbols, title="股票代码",
                 loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        
        # 调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"持仓分布已保存: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_trades_timeline(self, save_path: Optional[str] = None):
        """绘制交易时间线
        
        Args:
            save_path: 保存路径，None则显示
        """
        if not self.trades:
            print("无交易记录")
            return
        
        # 提取交易数据
        df_trades = pd.DataFrame(self.trades)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 分别绘制买入和卖出
        buys = df_trades[df_trades['action'] == 'buy']
        sells = df_trades[df_trades['action'] == 'sell']
        
        if not buys.empty:
            ax.scatter(buys['date'], buys['price'], 
                      c='green', marker='^', s=100, 
                      alpha=0.6, label='买入', edgecolors='darkgreen')
        
        if not sells.empty:
            ax.scatter(sells['date'], sells['price'], 
                      c='red', marker='v', s=100, 
                      alpha=0.6, label='卖出', edgecolors='darkred')
        
        # 设置标题和标签
        ax.set_title('交易时间线', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价格 (元)', fontsize=12)
        
        # 设置x轴日期格式
        dates = df_trades['date'].tolist()
        if len(dates) > 60:
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        else:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.xticks(rotation=45)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 添加图例
        ax.legend(loc='best', fontsize=10)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"交易时间线已保存: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_full_report(self, output_dir: Optional[str] = None):
        """生成完整的可视化报告
        
        Args:
            output_dir: 输出目录，None则使用回测结果目录
        """
        if output_dir is None:
            output_dir = self.results_path
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n生成可视化报告...")
        
        # 1. 资金曲线
        self.plot_portfolio_value(save_path=output_dir / "portfolio_value.png")
        
        # 2. 回撤曲线
        self.plot_drawdown(save_path=output_dir / "drawdown.png")
        
        # 3. 持仓分布
        self.plot_positions_distribution(save_path=output_dir / "positions_distribution.png")
        
        # 4. 交易时间线
        if self.trades:
            self.plot_trades_timeline(save_path=output_dir / "trades_timeline.png")
        
        print(f"\n✅ 可视化报告生成完成: {output_dir}")
        
        # 生成HTML摘要
        self._generate_html_summary(output_dir)
    
    def _generate_html_summary(self, output_dir: Path):
        """生成HTML报告摘要"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>回测报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #1f77b4; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .metric-label {{ font-size: 14px; opacity: 0.9; }}
        .metric-value {{ font-size: 28px; font-weight: bold; margin-top: 5px; }}
        img {{ max-width: 100%; height: auto; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .timestamp {{ color: #999; font-size: 12px; text-align: right; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 AI-Trader 回测报告</h1>
        
        <h2>绩效指标</h2>
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">总收益率</div>
                <div class="metric-value">{self.metrics.get('total_return', 0):.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">年化收益率</div>
                <div class="metric-value">{self.metrics.get('annual_return', 0):.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">最大回撤</div>
                <div class="metric-value">{self.metrics.get('max_drawdown', 0):.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">夏普比率</div>
                <div class="metric-value">{self.metrics.get('sharpe_ratio', 0):.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">总交易次数</div>
                <div class="metric-value">{self.metrics.get('total_trades', 0)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">交易天数</div>
                <div class="metric-value">{self.metrics.get('trading_days', 0)}</div>
            </div>
        </div>
        
        <h2>资金曲线</h2>
        <img src="portfolio_value.png" alt="资金曲线">
        
        <h2>回撤分析</h2>
        <img src="drawdown.png" alt="回撤曲线">
        
        <h2>持仓分布</h2>
        <img src="positions_distribution.png" alt="持仓分布">
        
        {"<h2>交易时间线</h2><img src='trades_timeline.png' alt='交易时间线'>" if self.trades else ""}
        
        <div class="timestamp">
            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
        
        html_file = output_dir / "report.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML报告已生成: {html_file}")


def main():
    """示例：生成可视化报告"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成回测可视化报告')
    parser.add_argument('--results_dir', type=str, required=True,
                       help='回测结果目录路径')
    parser.add_argument('--output_dir', type=str, default=None,
                       help='输出目录（可选，默认为结果目录）')
    
    args = parser.parse_args()
    
    # 创建可视化器
    visualizer = BacktestVisualizer(args.results_dir)
    
    # 生成完整报告
    visualizer.generate_full_report(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
