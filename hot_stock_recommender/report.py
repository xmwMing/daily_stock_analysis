# -*- coding: utf-8 -*-
"""
热门股票推荐报告生成器

职责：
1. 将推荐结果格式化为 Markdown 报告
2. 生成适合推送的报告格式
3. 处理空推荐列表的情况
"""

import logging
from typing import List
from datetime import datetime

from .models import Recommendation

logger = logging.getLogger(__name__)


class RecommendationReport:
    """
    推荐报告生成器

    将推荐结果格式化为 Markdown 格式的报告
    """

    @staticmethod
    def generate(recommendations: List[Recommendation], report_date: str = None, finder_stats: dict = None) -> str:
        """
        生成推荐报告

        Args:
            recommendations: 推荐列表
            report_date: 报告日期（默认今天）
            finder_stats: 热门股票发现器的统计信息

        Returns:
            Markdown 格式的报告内容
        """
        if report_date is None:
            report_date = datetime.now().strftime('%Y-%m-%d')

        # 处理空推荐列表
        if not recommendations:
            return RecommendationReport._generate_empty_report(report_date, finder_stats)

        # 生成完整报告
        report_lines = [
            f"# 🔥 {report_date} 热门股票推荐",
            "",
            f"> 共推荐 **{len(recommendations)}** 只热门股票",
            "",
        ]

        # 添加股票列表
        if recommendations:
            stock_list_lines = ["> 推荐股票列表:"]
            for i, rec in enumerate(recommendations, 1):
                stock = rec.stock_info
                stock_list_lines.append(f"> {i}. {stock.name} ({stock.code})")
            stock_list_lines.append("")
            report_lines.extend(stock_list_lines)

        # 添加统计信息
        if finder_stats:
            report_lines.extend([
                "## 📈 数据统计",
                "",
                "| 统计项 | 数量 |",
                "|--------|------|",
                f"| 飙升榜获取 | {finder_stats.get('gainers_count', 0)} 只 |",
                f"| 人气榜获取 | {finder_stats.get('turnover_count', 0)} 只 |",
                f"| 讨论榜获取 | {finder_stats.get('deal_count', finder_stats.get('volume_count', 0))} 只 |",
                f"| 过滤后剩余 | {finder_stats.get('total_after_filter', 0)} 只 |",
                "",
                "---",
                "",
            ])
        else:
            report_lines.extend([
                "---",
                "",
            ])

        # 逐个股票的推荐卡片
        for i, rec in enumerate(recommendations, 1):
            card = RecommendationReport._format_stock_card(rec, index=i)
            report_lines.append(card)
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")

        # 底部说明
        report_lines.extend([
            "## 📋 说明",
            "",
            "- **评分范围**: 0-100分，60分以上为推荐买入",
            "- **股票分类**:",
            "  - 强势股：多头排列且涨幅较大",
            "  - 回调股：多头排列但价格回调至均线附近",
            "  - 突破股：均线刚突破形成多头排列",
            "  - 价值股：多头排列且估值合理",
            "  - 潜力股：其他符合条件的股票",
            "- **风险等级**: 基于换手率、涨幅和波动率综合判断",
            "",
            f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])

        return "\n".join(report_lines)

    @staticmethod
    def _generate_empty_report(report_date: str, finder_stats: dict = None) -> str:
        """
        生成空推荐报告

        Args:
            report_date: 报告日期
            finder_stats: 热门股票发现器的统计信息

        Returns:
            空报告内容
        """
        report_lines = [
            f"# 🔥 {report_date} 热门股票推荐",
            "",
            "> 当前市场无合适推荐",
            "",
        ]

        # 添加统计信息
        if finder_stats:
            report_lines.extend([
                "## 📈 数据统计",
                "",
                "| 统计项 | 数量 |",
                "|--------|------|",
                f"| 飙升榜获取 | {finder_stats.get('gainers_count', 0)} 只 |",
                f"| 人气榜获取 | {finder_stats.get('turnover_count', 0)} 只 |",
                f"| 讨论榜获取 | {finder_stats.get('deal_count', finder_stats.get('volume_count', 0))} 只 |",
                f"| 过滤后剩余 | {finder_stats.get('total_after_filter', 0)} 只 |",
                "",
            ])

        report_lines.extend([
            "## 📊 市场状况",
            "",
            "当前市场环境下，暂无符合推荐条件的热门股票。",
            "",
            "可能的原因：",
            "- 市场整体处于调整期",
            "- 热门股票涨幅过大（乖离率 > 5%）",
            "- 未形成多头排列（MA5 > MA10 > MA20）",
            "- 评分未达到推荐标准（< 60分）",
            "",
            "建议：",
            "- 保持观望，等待更好的买入时机",
            "- 关注已持仓股票的走势",
            "- 避免追高，控制风险",
            "",
            f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])

        return "\n".join(report_lines)

    @staticmethod
    def _format_stock_card(rec: Recommendation, index: int) -> str:
        """
        格式化单只股票的推荐卡片

        Args:
            rec: 推荐对象
            index: 序号

        Returns:
            格式化的卡片内容
        """
        stock = rec.stock_info
        trend = rec.trend_result

        # 风险等级 emoji
        risk_emoji = {
            '低': '🟢',
            '中': '🟡',
            '高': '🔴'
        }.get(rec.risk_level, '⚪')

        # 分类 emoji
        category_emoji = {
            '强势股': '🚀',
            '回调股': '📉',
            '突破股': '💥',
            '价值股': '💎',
            '潜力股': '⭐'
        }.get(rec.category, '📊')

        lines = [
            f"## {index}. {category_emoji} {stock.name} ({stock.code})",
            "",
            f"**综合评分**: {rec.score:.1f}分 | **分类**: {rec.category} | **风险**: {risk_emoji} {rec.risk_level}",
            "",
        ]

        # 推荐理由
        if hasattr(rec, 'reasons') and rec.reasons:
            reasons_text = rec.reasons if isinstance(rec.reasons, str) else "\n".join(rec.reasons)
            lines.extend([
                "### 💡 推荐理由",
                "",
                reasons_text,
                "",
            ])
        elif hasattr(rec, 'reason') and rec.reason:
            reason_text = rec.reason if isinstance(rec.reason, str) else "\n".join(rec.reason)
            lines.extend([
                "### 💡 推荐理由",
                "",
                reason_text,
                "",
            ])

        # 基本信息
            lines.extend([
                "### 📊 基本信息",
                "",
                "| 指标 | 数值 |",
                "|------|------|",
                f"| 当前价 | {stock.price:.2f} 元 |",
                f"| 涨跌幅 | {stock.change_pct:+.2f}% |",
                f"| 成交量 | {stock.volume / 10000:.2f} 万手 |",
                f"| 成交额 | {stock.amount / 100000000:.2f} 亿元 |",
                f"| 换手率 | {stock.turnover_rate:.2f}% |",
            ])

        # 添加市盈率（如果有）
        if stock.pe_ratio and stock.pe_ratio > 0:
            lines.append(f"| 市盈率 | {stock.pe_ratio:.2f} |")

        lines.append("")

        # 趋势分析
        if trend:
            lines.extend([
                "### 📈 趋势分析",
                "",
                f"**趋势状态**: {trend.trend_status.value}",
                "",
                f"**均线排列**: {trend.ma_alignment}",
                "",
                f"**买入信号**: {trend.buy_signal.value} (评分: {trend.signal_score}分)",
                "",
            ])

            # 信号原因
            if trend.signal_reasons:
                lines.append("**信号原因**:")
                for reason in trend.signal_reasons:
                    # 确保reason是字符串
                    if isinstance(reason, list):
                        # 如果reason是列表，将其元素连接为字符串
                        reason_str = " ".join(str(item) for item in reason)
                        lines.append(f"- {reason_str}")
                    else:
                        lines.append(f"- {str(reason)}")
                lines.append("")

        # 风险提示
        if hasattr(rec, 'risk_warnings') and rec.risk_warnings:
            risk_text = rec.risk_warnings if isinstance(rec.risk_warnings, str) else "\n".join(rec.risk_warnings)
            lines.extend([
                "### ⚠️ 风险提示",
                "",
                risk_text,
                "",
            ])
        elif hasattr(rec, 'risk_warning') and rec.risk_warning:
            risk_text = rec.risk_warning if isinstance(rec.risk_warning, str) else "\n".join(rec.risk_warning)
            lines.extend([
                "### ⚠️ 风险提示",
                "",
                risk_text,
                "",
            ])

        return "\n".join(lines)
