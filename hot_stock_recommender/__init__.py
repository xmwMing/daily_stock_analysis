# -*- coding: utf-8 -*-
"""
热门股票推荐系统

该模块负责从市场中发现热门股票，基于趋势分析和交易理念进行智能筛选，
并在每日分析报告中推荐最值得关注的5只股票。

主入口模块，整合热门股票发现、推荐和报告生成功能
"""

import logging
from typing import List, Optional

from data_provider import DataFetcherManager
from src.stock_analyzer import StockTrendAnalyzer

from .models import Recommendation
from .finder import HotStockFinder
from .recommender import StockRecommender
from .report import RecommendationReport

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


class HotStockRecommender:
    """
    热门股票推荐系统主入口
    
    整合热门股票发现、推荐和报告生成功能
    
    使用示例:
        recommender = HotStockRecommender()
        report = recommender.run()
        print(report)
    """
    
    def __init__(
        self,
        data_fetcher: Optional[DataFetcherManager] = None,
        trend_analyzer: Optional[StockTrendAnalyzer] = None
    ):
        """
        初始化推荐系统
        
        Args:
            data_fetcher: 数据获取管理器（可选，默认创建新实例）
            trend_analyzer: 趋势分析器（可选，默认创建新实例）
        """
        self.data_fetcher = data_fetcher or DataFetcherManager()
        self.trend_analyzer = trend_analyzer or StockTrendAnalyzer()
        
        # 初始化各组件
        self.finder = HotStockFinder()
        self.recommender = StockRecommender(
            data_manager=self.data_fetcher,
            trend_analyzer=self.trend_analyzer
        )
        
        logger.info("热门股票推荐系统初始化完成")
    
    def run(self) -> str:
        """
        执行完整的推荐流程
        
        流程：
        1. 发现热门股票
        2. 分析并推荐
        3. 生成报告
        
        Returns:
            Markdown 格式的推荐报告
        """
        try:
            logger.info("========== 开始热门股票推荐流程 ==========")
            
            # Step 1: 发现热门股票
            logger.info("Step 1: 发现热门股票...")
            hot_stocks = self.finder.find_hot_stocks()
            
            if not hot_stocks:
                logger.warning("未发现符合条件的热门股票")
                return RecommendationReport.generate([])
            
            logger.info(f"发现 {len(hot_stocks)} 只热门股票")
            
            # Step 2: 分析并推荐
            logger.info("Step 2: 分析并推荐...")
            recommendations = self.recommender.recommend(hot_stocks)
            
            if not recommendations:
                logger.warning("未生成推荐结果")
                return RecommendationReport.generate([])
            
            logger.info(f"生成 {len(recommendations)} 条推荐")
            
            # Step 3: 生成报告
            logger.info("Step 3: 生成推荐报告...")
            report = RecommendationReport.generate(recommendations)
            
            logger.info("========== 热门股票推荐流程完成 ==========")
            
            return report
            
        except Exception as e:
            logger.error(f"热门股票推荐流程失败: {e}")
            logger.exception("详细错误信息:")
            # 返回空报告，确保不影响其他任务
            return RecommendationReport.generate([])
    
    def get_recommendations(self) -> List[Recommendation]:
        """
        获取推荐列表（不生成报告）
        
        Returns:
            推荐列表
        """
        try:
            hot_stocks = self.finder.find_hot_stocks()
            if not hot_stocks:
                return []
            
            recommendations = self.recommender.recommend(hot_stocks)
            return recommendations
            
        except Exception as e:
            logger.error(f"获取推荐列表失败: {e}")
            return []


__all__ = [
    'HotStockRecommender',
    'HotStockFinder',
    'StockRecommender',
    'RecommendationReport',
    'Recommendation',
]
