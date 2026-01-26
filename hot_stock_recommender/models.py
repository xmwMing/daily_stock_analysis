# -*- coding: utf-8 -*-
"""
热门股票推荐系统 - 数据模型

定义系统中使用的核心数据结构：
1. StockInfo - 股票基本信息
2. Recommendation - 推荐结果
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class StockInfo:
    """
    股票基本信息
    
    包含股票的基本交易数据和市场指标，用于热门股票发现和过滤。
    
    Attributes:
        code: 股票代码（如"600519"）
        name: 股票名称
        price: 当前价格（元）
        change_pct: 涨跌幅（%）
        volume: 成交量（手）
        amount: 成交额（元）
        turnover_rate: 换手率（%）
        market_cap: 总市值（元）
        list_days: 上市天数
        pe_ratio: 市盈率（可选）
    """
    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    amount: float
    turnover_rate: float
    market_cap: float
    list_days: int
    pe_ratio: Optional[float] = None
    
    def __post_init__(self):
        """数据验证"""
        if not self.code:
            raise ValueError("股票代码不能为空")
        if not self.name:
            raise ValueError("股票名称不能为空")
        if self.price < 0:
            raise ValueError(f"股票价格不能为负数: {self.price}")
        if self.volume < 0:
            raise ValueError(f"成交量不能为负数: {self.volume}")
        if self.amount < 0:
            raise ValueError(f"成交额不能为负数: {self.amount}")
        if self.market_cap < 0:
            raise ValueError(f"总市值不能为负数: {self.market_cap}")
        if self.list_days < 0:
            raise ValueError(f"上市天数不能为负数: {self.list_days}")


@dataclass
class Recommendation:
    """
    推荐结果
    
    包含股票的完整推荐信息，包括基本信息、趋势分析结果、评分、分类和风险评估。
    
    Attributes:
        stock_info: 股票基本信息
        trend_result: 趋势分析结果（来自 StockTrendAnalyzer）
        score: 综合评分（0-100）
        category: 股票分类（强势股、回调股、突破股、价值股、潜力股）
        risk_level: 风险等级（低、中、高）
        reasons: 推荐理由列表
        risk_warnings: 风险提示列表
    """
    stock_info: StockInfo
    trend_result: Any  # TrendAnalysisResult 类型，避免循环导入
    score: int
    category: str
    risk_level: str
    reasons: List[str] = field(default_factory=list)
    risk_warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.score <= 100:
            raise ValueError(f"评分必须在0-100之间: {self.score}")
        
        valid_categories = ["强势股", "回调股", "突破股", "价值股", "潜力股"]
        if self.category not in valid_categories:
            raise ValueError(f"无效的股票分类: {self.category}，必须是 {valid_categories} 之一")
        
        valid_risk_levels = ["低", "中", "高"]
        if self.risk_level not in valid_risk_levels:
            raise ValueError(f"无效的风险等级: {self.risk_level}，必须是 {valid_risk_levels} 之一")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            包含所有推荐信息的字典
        """
        return {
            "stock_code": self.stock_info.code,
            "stock_name": self.stock_info.name,
            "price": self.stock_info.price,
            "change_pct": self.stock_info.change_pct,
            "volume": self.stock_info.volume,
            "amount": self.stock_info.amount,
            "turnover_rate": self.stock_info.turnover_rate,
            "market_cap": self.stock_info.market_cap,
            "pe_ratio": self.stock_info.pe_ratio,
            "score": self.score,
            "category": self.category,
            "risk_level": self.risk_level,
            "reasons": self.reasons,
            "risk_warnings": self.risk_warnings,
            # 趋势分析结果的关键指标
            "ma5": getattr(self.trend_result, 'ma5', None),
            "ma10": getattr(self.trend_result, 'ma10', None),
            "ma20": getattr(self.trend_result, 'ma20', None),
            "trend_status": getattr(self.trend_result, 'trend_status', None),
            "signal_score": getattr(self.trend_result, 'signal_score', None),
        }
