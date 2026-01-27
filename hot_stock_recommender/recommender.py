# -*- coding: utf-8 -*-
"""
热门股票推荐系统 - 股票推荐器

职责：
1. 获取股票历史数据
2. 调用趋势分析器进行分析
3. 计算综合评分
4. 股票分类和风险评估
5. 生成推荐列表

Requirements:
- 3.1-3.4: 获取历史数据和趋势分析
- 4.1-4.5: 趋势分析和评分
- 5.1-5.5: 股票分类
- 6.1-6.4: 风险评估
- 7.1: 推荐列表生成
- 9.3-9.4: 并发控制
- 10.2-10.4: 错误处理和日志
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np

from .models import StockInfo, Recommendation
from data_provider.base import DataFetcherManager
from src.stock_analyzer import StockTrendAnalyzer, TrendAnalysisResult
from src.config import HOT_STOCK_CONFIG

logger = logging.getLogger(__name__)


class StockRecommender:
    """
    股票推荐器
    
    基于趋势分析和市场热度对热门股票进行评分和推荐。
    
    Attributes:
        data_manager: 数据管理器（用于获取历史数据）
        trend_analyzer: 趋势分析器（用于趋势分析）
        max_concurrent: 最大并发数
        history_days: 历史数据天数
        min_history_days: 最少历史数据天数
        min_score: 最低评分阈值
        trend_weight: 趋势评分权重
        market_heat_weight: 市场热度评分权重
    """
    
    def __init__(
        self,
        data_manager: DataFetcherManager,
        trend_analyzer: StockTrendAnalyzer,
        max_concurrent: int = 10
    ):
        """
        初始化推荐器
        
        Args:
            data_manager: 数据管理器
            trend_analyzer: 趋势分析器
            max_concurrent: 最大并发数
        """
        self.data_manager = data_manager
        self.trend_analyzer = trend_analyzer
        self.max_concurrent = max_concurrent
        
        # 从配置加载参数
        self.history_days = HOT_STOCK_CONFIG.get('history_days', 60)
        self.min_history_days = HOT_STOCK_CONFIG.get('min_history_days', 30)
        self.min_score = HOT_STOCK_CONFIG.get('min_score', 60)
        
        # 评分权重
        score_weights = HOT_STOCK_CONFIG.get('score_weights', {})
        self.trend_weight = score_weights.get('trend', 0.6)
        self.market_heat_weight = score_weights.get('market_heat', 0.4)
        
        logger.info(f"StockRecommender 初始化完成: "
                   f"历史数据={self.history_days}天, "
                   f"最低评分={self.min_score}, "
                   f"最大并发={self.max_concurrent}, "
                   f"评分权重=[趋势:{self.trend_weight}, 市场热度:{self.market_heat_weight}]")
    
    def recommend(
        self,
        hot_stocks: List[StockInfo],
        top_n: int = 5
    ) -> List[Recommendation]:
        """
        生成推荐列表
        
        流程：
        1. 并发分析所有热门股票
        2. 过滤评分低于阈值的股票
        3. 按评分降序排序
        4. 选择前N只股票
        
        Args:
            hot_stocks: 热门股票列表
            top_n: 推荐数量
            
        Returns:
            List[Recommendation]: 推荐股票列表（按评分降序）
            
        Requirements:
            - 7.1: 推荐列表生成
            - 9.3-9.4: 并发控制
            - 10.3-10.4: 错误处理和日志
        """
        if not hot_stocks:
            logger.warning("热门股票列表为空，无法生成推荐")
            return []
        
        logger.info("=" * 60)
        logger.info(f"开始分析 {len(hot_stocks)} 只热门股票...")
        start_time = time.time()
        
        # 并发分析所有股票
        recommendations = []
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # 提交所有分析任务
            future_to_stock = {
                executor.submit(self._analyze_stock, stock): stock
                for stock in hot_stocks
            }
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_stock):
                stock = future_to_stock[future]
                completed += 1
                
                try:
                    recommendation = future.result()
                    if recommendation:
                        recommendations.append(recommendation)
                        logger.info(f"[{completed}/{len(hot_stocks)}] {stock.code} {stock.name} "
                                  f"分析完成: 评分={recommendation.score}, "
                                  f"分类={recommendation.category}, "
                                  f"风险={recommendation.risk_level}")
                    else:
                        logger.warning(f"[{completed}/{len(hot_stocks)}] {stock.code} {stock.name} "
                                     f"分析失败或评分不足")
                except Exception as e:
                    logger.error(f"[{completed}/{len(hot_stocks)}] {stock.code} {stock.name} "
                               f"分析异常: {e}", exc_info=True)
        
        # 过滤评分低于阈值的股票
        filtered_recommendations = [
            rec for rec in recommendations
            if rec.score >= self.min_score
        ]
        
        logger.info(f"分析完成: 共 {len(recommendations)} 只股票通过分析, "
                   f"{len(filtered_recommendations)} 只评分 >= {self.min_score}")
        
        # 按评分降序排序
        filtered_recommendations.sort(key=lambda x: x.score, reverse=True)
        
        # 选择前N只
        top_recommendations = filtered_recommendations[:top_n]
        
        elapsed = time.time() - start_time
        logger.info(f"推荐列表生成完成: 推荐 {len(top_recommendations)} 只股票, "
                   f"耗时 {elapsed:.2f}秒")
        logger.info("=" * 60)
        
        return top_recommendations
    
    def _analyze_stock(self, stock: StockInfo) -> Optional[Recommendation]:
        """
        分析单只股票
        
        流程：
        1. 获取历史数据
        2. 验证数据有效性
        3. 调用趋势分析器
        4. 计算综合评分
        5. 股票分类
        6. 风险评估
        7. 生成推荐理由和风险提示
        
        Args:
            stock: 股票信息
            
        Returns:
            Recommendation 对象，失败返回 None
            
        Requirements:
            - 3.1-3.4: 获取历史数据和趋势分析
            - 4.1-4.5: 趋势分析和评分
            - 5.1-5.5: 股票分类
            - 6.1-6.4: 风险评估
        """
        try:
            # Step 1: 获取历史数据
            logger.debug(f"获取 {stock.code} {stock.name} 历史数据...")
            
            df, source = self.data_manager.get_daily_data(
                stock_code=stock.code,
                days=self.history_days
            )
            
            # Step 2: 验证数据有效性
            if df is None or df.empty:
                logger.warning(f"{stock.code} {stock.name} 历史数据为空")
                return None
            
            if len(df) < self.min_history_days:
                logger.warning(f"{stock.code} {stock.name} 历史数据不足: "
                             f"{len(df)}天 < {self.min_history_days}天")
                return None
            
            # 验证必需字段
            required_fields = ['date', 'open', 'close', 'high', 'low', 'volume']
            missing_fields = [f for f in required_fields if f not in df.columns]
            if missing_fields:
                logger.warning(f"{stock.code} {stock.name} 缺少必需字段: {missing_fields}")
                return None
            
            logger.debug(f"{stock.code} {stock.name} 历史数据获取成功: "
                        f"{len(df)}天, 数据源={source}")
            
            # Step 3: 调用趋势分析器
            trend_result = self.trend_analyzer.analyze(df, stock.code)
            
            # Step 4: 计算综合评分
            score = self._calculate_score(trend_result, stock)
            
            # 过滤评分低于阈值的股票
            if score < self.min_score:
                logger.debug(f"{stock.code} {stock.name} 评分不足: {score} < {self.min_score}")
                return None
            
            # Step 5: 股票分类
            category = self._classify_stock(trend_result, stock)
            
            # Step 6: 风险评估
            risk_level = self._assess_risk(stock, trend_result, df)
            
            # Step 7: 生成推荐理由和风险提示
            reasons = self._generate_reasons(trend_result, stock, category)
            risk_warnings = self._generate_risk_warnings(stock, trend_result, risk_level)
            
            # 创建推荐对象
            recommendation = Recommendation(
                stock_info=stock,
                trend_result=trend_result,
                score=score,
                category=category,
                risk_level=risk_level,
                reasons=reasons,
                risk_warnings=risk_warnings
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"{stock.code} {stock.name} 分析失败: {e}", exc_info=True)
            return None
    
    def _calculate_score(
        self,
        trend_result: TrendAnalysisResult,
        stock_info: StockInfo
    ) -> int:
        """
        计算综合评分（0-100）
        
        综合评分 = 趋势评分 × 0.6 + 市场热度评分 × 0.4
        
        趋势评分：来自 StockTrendAnalyzer.signal_score（0-100）
        市场热度评分：基于涨幅、换手率、成交额（0-100）
        
        Args:
            trend_result: 趋势分析结果
            stock_info: 股票信息
            
        Returns:
            综合评分（0-100）
            
        Requirements:
            - 4.4: 计算综合趋势评分
        """
        # 趋势评分（来自趋势分析器）
        trend_score = trend_result.signal_score
        
        # 市场热度评分（40分）
        market_heat_score = self._calculate_market_heat_score(stock_info)
        
        # 综合评分
        final_score = int(
            trend_score * self.trend_weight +
            market_heat_score * self.market_heat_weight
        )
        
        # 确保在0-100范围内
        final_score = max(0, min(100, final_score))
        
        logger.debug(f"{stock_info.code} 评分: 趋势={trend_score}, "
                    f"市场热度={market_heat_score}, 综合={final_score}")
        
        return final_score
    
    def _calculate_market_heat_score(self, stock_info: StockInfo) -> int:
        """
        计算市场热度评分（0-100）
        
        评分维度：
        - 涨幅（50分）：3% < 涨幅 < 8% 得分高
        - 换手率（25分）：5% < 换手率 < 15% 得分高
        - 成交额（25分）：成交额越大得分越高
        
        Args:
            stock_info: 股票信息
            
        Returns:
            市场热度评分（0-100）
        """
        score = 0
        
        # === 涨幅评分（50分）===
        change_pct = stock_info.change_pct
        if 3 <= change_pct <= 8:
            # 理想涨幅区间，满分
            score += 50
        elif 1 <= change_pct < 3:
            # 温和上涨
            score += 40
        elif 8 < change_pct <= 10:
            # 涨幅较大，略有风险
            score += 35
        elif 0 <= change_pct < 1:
            # 微涨
            score += 25
        elif change_pct > 10:
            # 涨幅过大，追高风险
            score += 15
        else:
            # 下跌
            score += 0
        
        # === 换手率评分（25分）===
        turnover = stock_info.turnover_rate
        if 5 <= turnover <= 15:
            # 理想换手率区间
            score += 25
        elif 3 <= turnover < 5:
            # 换手率偏低
            score += 20
        elif 15 < turnover <= 20:
            # 换手率偏高
            score += 18
        elif 1 <= turnover < 3:
            # 换手率很低
            score += 12
        elif turnover > 20:
            # 换手率过高，风险大
            score += 8
        else:
            # 换手率异常低
            score += 5
        
        # === 成交额评分（25分）===
        # 成交额越大，市场关注度越高
        amount_billion = stock_info.amount / 1e8  # 转换为亿元
        if amount_billion >= 50:
            score += 25
        elif amount_billion >= 20:
            score += 20
        elif amount_billion >= 10:
            score += 15
        elif amount_billion >= 5:
            score += 10
        else:
            score += 5
        
        return score
    
    def _classify_stock(
        self,
        trend_result: TrendAnalysisResult,
        stock_info: StockInfo
    ) -> str:
        """
        股票分类
        
        分类规则：
        1. 强势股：多头排列 AND 涨幅 > 5%
        2. 回调股：多头排列 AND MA10 < 价格 < MA5
        3. 突破股：MA5刚突破MA10（3日内）AND MA10刚突破MA20（3日内）
        4. 价值股：多头排列 AND 市盈率 < 行业平均（如果有数据）
        5. 潜力股：不满足以上条件但评分 > 60
        
        Args:
            trend_result: 趋势分析结果
            stock_info: 股票信息
            
        Returns:
            股票分类字符串
            
        Requirements:
            - 5.1-5.5: 股票分类
        """
        from src.stock_analyzer import TrendStatus
        
        price = trend_result.current_price
        ma5 = trend_result.ma5
        ma10 = trend_result.ma10
        ma20 = trend_result.ma20
        change_pct = stock_info.change_pct
        
        # 判断是否多头排列
        is_bull = trend_result.trend_status in [
            TrendStatus.STRONG_BULL,
            TrendStatus.BULL
        ]
        
        # 1. 强势股：多头排列 AND 涨幅 > 5%
        if is_bull and change_pct > 5:
            return "强势股"
        
        # 2. 回调股：多头排列 AND MA10 < 价格 < MA5
        if is_bull and ma10 < price < ma5:
            return "回调股"
        
        # 3. 突破股：MA5刚突破MA10 AND MA10刚突破MA20
        # 简化判断：MA5 > MA10 > MA20 且价格接近MA5（乖离率小于3%）
        if ma5 > ma10 > ma20 and abs(trend_result.bias_ma5) < 3:
            return "突破股"
        
        # 4. 价值股：多头排列 AND 市盈率 < 30（简化判断）
        if is_bull and stock_info.pe_ratio and 0 < stock_info.pe_ratio < 30:
            return "价值股"
        
        # 5. 潜力股：其他情况
        return "潜力股"
    
    def _assess_risk(
        self,
        stock_info: StockInfo,
        trend_result: TrendAnalysisResult,
        df: pd.DataFrame
    ) -> str:
        """
        风险评估
        
        基础风险等级：
        - 高风险：换手率 > 15% AND 涨幅 > 8%
        - 中风险：5% < 换手率 < 15% AND 3% < 涨幅 < 8%
        - 低风险：换手率 < 5% AND 涨幅 < 3%
        
        风险调整：
        - 如果价格波动率（最近10日标准差/均值）> 0.05，风险等级提高一档
        
        Args:
            stock_info: 股票信息
            trend_result: 趋势分析结果
            df: 历史数据
            
        Returns:
            风险等级字符串（"低"、"中"、"高"）
            
        Requirements:
            - 6.1-6.4: 风险评估
        """
        turnover = stock_info.turnover_rate
        change_pct = stock_info.change_pct
        
        # 基础风险等级判断
        if turnover > 15 and change_pct > 8:
            risk_level = "高"
        elif 5 <= turnover <= 15 and 3 <= change_pct <= 8:
            risk_level = "中"
        elif turnover < 5 and change_pct < 3:
            risk_level = "低"
        else:
            # 其他情况，根据换手率和涨幅综合判断
            if turnover > 15 or change_pct > 8:
                risk_level = "高"
            elif turnover > 10 or change_pct > 5:
                risk_level = "中"
            else:
                risk_level = "低"
        
        # 计算价格波动率（最近10日）
        if len(df) >= 10:
            recent_prices = df['close'].tail(10)
            volatility = recent_prices.std() / recent_prices.mean()
            
            # 如果波动率 > 0.05，风险等级提高一档
            if volatility > 0.05:
                if risk_level == "低":
                    risk_level = "中"
                elif risk_level == "中":
                    risk_level = "高"
                
                logger.debug(f"{stock_info.code} 波动率={volatility:.4f} > 0.05, "
                           f"风险等级提升")
        
        return risk_level
    
    def _generate_reasons(
        self,
        trend_result: TrendAnalysisResult,
        stock_info: StockInfo,
        category: str
    ) -> List[str]:
        """
        生成推荐理由
        
        Args:
            trend_result: 趋势分析结果
            stock_info: 股票信息
            category: 股票分类
            
        Returns:
            推荐理由列表
        """
        reasons = []
        
        # 添加趋势分析的推荐理由
        if trend_result.signal_reasons:
            reasons.extend(trend_result.signal_reasons)
        
        # 添加分类相关的理由
        if category == "强势股":
            reasons.append(f"✅ 强势股，涨幅{stock_info.change_pct:.2f}%，市场关注度高")
        elif category == "回调股":
            reasons.append("✅ 回调股，价格回踩MA5-MA10区间，介入时机好")
        elif category == "突破股":
            reasons.append("✅ 突破股，均线刚形成多头排列，趋势向上")
        elif category == "价值股":
            reasons.append(f"✅ 价值股，市盈率{stock_info.pe_ratio:.2f}，估值合理")
        
        # 添加市场热度相关的理由
        if 5 <= stock_info.turnover_rate <= 15:
            reasons.append(f"✅ 换手率{stock_info.turnover_rate:.2f}%，筹码活跃度适中")
        
        if stock_info.amount / 1e8 >= 10:
            reasons.append(f"✅ 成交额{stock_info.amount/1e8:.2f}亿，市场关注度高")
        
        return reasons
    
    def _generate_risk_warnings(
        self,
        stock_info: StockInfo,
        trend_result: TrendAnalysisResult,
        risk_level: str
    ) -> List[str]:
        """
        生成风险提示
        
        Args:
            stock_info: 股票信息
            trend_result: 趋势分析结果
            risk_level: 风险等级
            
        Returns:
            风险提示列表
        """
        warnings = []
        
        # 添加趋势分析的风险因素
        if trend_result.risk_factors:
            warnings.extend(trend_result.risk_factors)
        
        # 添加风险等级相关的提示
        if risk_level == "高":
            warnings.append("⚠️ 风险等级：高，建议谨慎操作，控制仓位")
        elif risk_level == "中":
            warnings.append("⚠️ 风险等级：中，建议适度参与，注意止损")
        
        # 添加市场热度相关的风险
        if stock_info.change_pct > 8:
            warnings.append(f"⚠️ 短期涨幅较大({stock_info.change_pct:.2f}%)，注意回调风险")
        
        if stock_info.turnover_rate > 15:
            warnings.append(f"⚠️ 换手率过高({stock_info.turnover_rate:.2f}%)，资金博弈激烈")
        
        # 如果没有风险提示，添加一个通用提示
        if not warnings:
            warnings.append("💡 风险等级：低，但仍需关注市场变化")
        
        return warnings


if __name__ == "__main__":
    # 测试代码
    import sys
    sys.path.insert(0, '..')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试数据
    from hot_stock_recommender.models import StockInfo
    
    test_stocks = [
        StockInfo(
            code="600519",
            name="贵州茅台",
            price=1650.0,
            change_pct=3.5,
            volume=50000,
            amount=8.25e8,
            turnover_rate=8.5,
            market_cap=2.07e12,
            list_days=5000,
            pe_ratio=35.0
        ),
    ]
    
    # 创建推荐器
    data_manager = DataFetcherManager()
    trend_analyzer = StockTrendAnalyzer()
    recommender = StockRecommender(data_manager, trend_analyzer)
    
    # 生成推荐
    recommendations = recommender.recommend(test_stocks, top_n=5)
    
    print(f"\n生成 {len(recommendations)} 条推荐:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec.stock_info.code} {rec.stock_info.name}")
        print(f"   评分: {rec.score}/100")
        print(f"   分类: {rec.category}")
        print(f"   风险: {rec.risk_level}")
        print(f"   推荐理由:")
        for reason in rec.reasons:
            print(f"     {reason}")
        if rec.risk_warnings:
            print(f"   风险提示:")
            for warning in rec.risk_warnings:
                print(f"     {warning}")
