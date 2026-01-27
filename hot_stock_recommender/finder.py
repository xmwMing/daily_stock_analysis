# -*- coding: utf-8 -*-
"""
热门股票推荐系统 - 热门股票发现器

职责：
1. 从市场数据源获取热门股票列表（涨幅榜、成交额榜、换手率榜）
2. 应用过滤条件筛选合格股票
3. 数据缓存和去重

Requirements:
- 1.1, 1.2, 1.3: 获取涨幅榜、成交额榜、换手率榜前100只股票
- 1.4: 错误处理和日志记录
- 1.5: 去重逻辑
- 2.1-2.5: 过滤条件（ST股票、价格范围、市值、上市时间）
- 9.1, 9.2: 缓存机制
- 10.1: 错误处理
"""

import logging
import time
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import pandas as pd

from .models import StockInfo
from src.config import HOT_STOCK_CONFIG

logger = logging.getLogger(__name__)


class HotStockFinder:
    """
    热门股票发现器

    从市场数据源获取热门股票并应用过滤条件。

    Attributes:
        cache_ttl: 缓存有效期（秒），默认30分钟
        _cache: 缓存字典，存储榜单数据
        _cache_timestamps: 缓存时间戳字典
    """

    def __init__(self, cache_ttl: int = 1800):
        """
        初始化发现器

        Args:
            cache_ttl: 缓存有效期（秒），默认30分钟
        """
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # 从配置加载过滤条件
        filter_config = HOT_STOCK_CONFIG.get('filter', {})
        self.min_price = filter_config.get('min_price', 3.0)
        self.max_price = filter_config.get('max_price', 300.0)
        self.min_market_cap = filter_config.get('min_market_cap', 5e9)
        self.min_list_days = filter_config.get('min_list_days', 90)

        # 从配置加载获取数量
        self.fetch_count = HOT_STOCK_CONFIG.get('fetch_count', 30)

        # 统计信息
        self.stats = {
            'gainers_count': 0,
            'volume_count': 0,
            'turnover_count': 0,
            'total_before_filter': 0,
            'total_after_filter': 0
        }

        logger.info(f"HotStockFinder 初始化完成: 缓存TTL={cache_ttl}秒, "
                   f"每个榜单获取{self.fetch_count}只, "
                   f"过滤条件=[价格:{self.min_price}-{self.max_price}元, "
                   f"市值>={self.min_market_cap/1e8:.0f}亿, "
                   f"上市>={self.min_list_days}天]")

    def find_hot_stocks(self) -> List[StockInfo]:
        """
        发现热门股票

        流程：
        1. 获取涨幅榜、成交额榜、换手率榜前N只股票（N由配置决定）
        2. 合并并去重
        3. 应用过滤条件

        Returns:
            List[StockInfo]: 过滤后的热门股票列表

        Requirements:
            - 1.1, 1.2, 1.3: 获取三个榜单
            - 1.5: 去重逻辑
            - 2.1-2.5: 应用过滤条件
        """
        logger.info("=" * 60)
        logger.info("开始发现热门股票...")
        start_time = time.time()

        try:
            # 获取三个榜单的数据（使用配置的数量）
            gainers_df = self._fetch_top_gainers(limit=self.fetch_count)
            volume_df = self._fetch_top_volume(limit=self.fetch_count)
            turnover_df = self._fetch_top_turnover(limit=self.fetch_count)

            # 更新统计信息
            self.stats['gainers_count'] = len(gainers_df) if gainers_df is not None and not gainers_df.empty else 0
            self.stats['volume_count'] = len(volume_df) if volume_df is not None and not volume_df.empty else 0
            self.stats['turnover_count'] = len(turnover_df) if turnover_df is not None and not turnover_df.empty else 0

            # 合并三个榜单
            all_stocks = []
            stock_codes_seen = set()

            # 处理涨幅榜
            if gainers_df is not None and not gainers_df.empty:
                for _, row in gainers_df.iterrows():
                    code = str(row.get('代码', ''))
                    if code and code not in stock_codes_seen:
                        stock_info = self._row_to_stock_info(row)
                        if stock_info:
                            all_stocks.append(stock_info)
                            stock_codes_seen.add(code)

            # 处理成交额榜
            if volume_df is not None and not volume_df.empty:
                for _, row in volume_df.iterrows():
                    code = str(row.get('代码', ''))
                    if code and code not in stock_codes_seen:
                        stock_info = self._row_to_stock_info(row)
                        if stock_info:
                            all_stocks.append(stock_info)
                            stock_codes_seen.add(code)

            # 处理换手率榜
            if turnover_df is not None and not turnover_df.empty:
                for _, row in turnover_df.iterrows():
                    code = str(row.get('代码', ''))
                    if code and code not in stock_codes_seen:
                        stock_info = self._row_to_stock_info(row)
                        if stock_info:
                            all_stocks.append(stock_info)
                            stock_codes_seen.add(code)

            # 更新总数量统计
            self.stats['total_before_filter'] = len(all_stocks)

            logger.info(f"合并三个榜单后共获得 {len(all_stocks)} 只不重复的热门股票")
            logger.info(f"各榜单获取数量: 涨幅榜={self.stats['gainers_count']}, 成交额榜={self.stats['volume_count']}, 换手率榜={self.stats['turnover_count']}")

            # 应用过滤条件
            filtered_stocks = self._apply_filters(all_stocks)

            # 更新过滤后数量统计
            self.stats['total_after_filter'] = len(filtered_stocks)

            elapsed = time.time() - start_time
            logger.info(f"热门股票发现完成: 过滤后剩余 {len(filtered_stocks)} 只股票, 耗时 {elapsed:.2f}秒")
            logger.info("=" * 60)

            return filtered_stocks

        except Exception as e:
            logger.error(f"发现热门股票失败: {e}", exc_info=True)
            return []

    def _fetch_top_gainers(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        获取涨幅榜前N只股票

        使用 akshare 的 stock_zh_a_spot_em() 获取实时行情，按涨跌幅排序。

        Args:
            limit: 获取数量，默认100

        Returns:
            DataFrame 包含涨幅榜数据，失败返回 None

        Requirements:
            - 1.1: 获取涨幅榜前100只股票
            - 1.4: 错误处理和日志记录
            - 9.1, 9.2: 缓存机制
        """
        cache_key = f"gainers_{limit}_{date.today()}"

        # 检查缓存
        if self._is_cache_valid(cache_key):
            logger.info(f"[缓存命中] 使用缓存的涨幅榜数据")
            return self._cache[cache_key]

        try:
            import akshare as ak

            logger.info(f"[API调用] ak.stock_zh_a_spot_em() 获取涨幅榜...")

            # 获取全部A股实时行情
            df = ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                logger.warning("[API返回] 涨幅榜数据为空")
                return None

            # 按涨跌幅降序排序，取前N只
            df = df.sort_values(by='涨跌幅', ascending=False).head(limit)

            logger.info(f"[API返回] 涨幅榜获取成功: 返回 {len(df)} 只股票")
            logger.debug(f"[API返回] 涨幅榜前5只: {df.head(5)[['代码', '名称', '涨跌幅']].to_dict('records')}")

            # 更新缓存
            self._update_cache(cache_key, df)

            return df

        except Exception as e:
            logger.error(f"[API错误] 获取涨幅榜失败: {e}", exc_info=True)
            return None

    def _fetch_top_volume(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        获取成交额榜前N只股票

        使用 akshare 的 stock_zh_a_spot_em() 获取实时行情，按成交额排序。

        Args:
            limit: 获取数量，默认100

        Returns:
            DataFrame 包含成交额榜数据，失败返回 None

        Requirements:
            - 1.2: 获取成交额榜前100只股票
            - 1.4: 错误处理和日志记录
            - 9.1, 9.2: 缓存机制
        """
        cache_key = f"volume_{limit}_{date.today()}"

        # 检查缓存
        if self._is_cache_valid(cache_key):
            logger.info(f"[缓存命中] 使用缓存的成交额榜数据")
            return self._cache[cache_key]

        try:
            import akshare as ak

            logger.info(f"[API调用] ak.stock_zh_a_spot_em() 获取成交额榜...")

            # 获取全部A股实时行情
            df = ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                logger.warning("[API返回] 成交额榜数据为空")
                return None

            # 按成交额降序排序，取前N只
            df = df.sort_values(by='成交额', ascending=False).head(limit)

            logger.info(f"[API返回] 成交额榜获取成功: 返回 {len(df)} 只股票")
            logger.debug(f"[API返回] 成交额榜前5只: {df.head(5)[['代码', '名称', '成交额']].to_dict('records')}")

            # 更新缓存
            self._update_cache(cache_key, df)

            return df

        except Exception as e:
            logger.error(f"[API错误] 获取成交额榜失败: {e}", exc_info=True)
            return None

    def _fetch_top_turnover(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        获取换手率榜前N只股票

        使用 akshare 的 stock_zh_a_spot_em() 获取实时行情，按换手率排序。

        Args:
            limit: 获取数量，默认100

        Returns:
            DataFrame 包含换手率榜数据，失败返回 None

        Requirements:
            - 1.3: 获取换手率榜前100只股票
            - 1.4: 错误处理和日志记录
            - 9.1, 9.2: 缓存机制
        """
        cache_key = f"turnover_{limit}_{date.today()}"

        # 检查缓存
        if self._is_cache_valid(cache_key):
            logger.info(f"[缓存命中] 使用缓存的换手率榜数据")
            return self._cache[cache_key]

        try:
            import akshare as ak

            logger.info(f"[API调用] ak.stock_zh_a_spot_em() 获取换手率榜...")

            # 获取全部A股实时行情
            df = ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                logger.warning("[API返回] 换手率榜数据为空")
                return None

            # 按换手率降序排序，取前N只
            df = df.sort_values(by='换手率', ascending=False).head(limit)

            logger.info(f"[API返回] 换手率榜获取成功: 返回 {len(df)} 只股票")
            logger.debug(f"[API返回] 换手率榜前5只: {df.head(5)[['代码', '名称', '换手率']].to_dict('records')}")

            # 更新缓存
            self._update_cache(cache_key, df)

            return df

        except Exception as e:
            logger.error(f"[API错误] 获取换手率榜失败: {e}", exc_info=True)
            return None

    def _row_to_stock_info(self, row: pd.Series) -> Optional[StockInfo]:
        """
        将 DataFrame 行转换为 StockInfo 对象

        Args:
            row: DataFrame 的一行数据

        Returns:
            StockInfo 对象，转换失败返回 None
        """
        try:
            # 安全获取字段值
            def safe_float(val, default=0.0):
                try:
                    if pd.isna(val):
                        return default
                    return float(val)
                except:
                    return default

            def safe_int(val, default=0):
                try:
                    if pd.isna(val):
                        return default
                    return int(val)
                except:
                    return default

            # 计算上市天数（如果有上市日期）
            list_days = 0
            if '上市时间' in row and not pd.isna(row['上市时间']):
                try:
                    list_date_str = str(row['上市时间'])
                    # 尝试解析日期格式
                    if len(list_date_str) == 8:  # YYYYMMDD
                        list_date = datetime.strptime(list_date_str, '%Y%m%d').date()
                    elif len(list_date_str) == 10:  # YYYY-MM-DD
                        list_date = datetime.strptime(list_date_str, '%Y-%m-%d').date()
                    else:
                        list_date = None

                    if list_date:
                        list_days = (date.today() - list_date).days
                except:
                    list_days = 0

            stock_info = StockInfo(
                code=str(row.get('代码', '')),
                name=str(row.get('名称', '')),
                price=safe_float(row.get('最新价')),
                change_pct=safe_float(row.get('涨跌幅')),
                volume=safe_float(row.get('成交量')),
                amount=safe_float(row.get('成交额')),
                turnover_rate=safe_float(row.get('换手率')),
                market_cap=safe_float(row.get('总市值')),
                list_days=list_days,
                pe_ratio=safe_float(row.get('市盈率-动态')) if '市盈率-动态' in row else None,
            )

            return stock_info

        except Exception as e:
            logger.warning(f"转换股票信息失败: {e}")
            return None

    def _apply_filters(self, stocks: List[StockInfo]) -> List[StockInfo]:
        """
        应用过滤条件

        过滤规则：
        1. 不是ST股票或*ST股票
        2. 价格在3元到300元之间
        3. 总市值大于等于50亿元
        4. 上市天数大于等于90天

        Args:
            stocks: 股票列表

        Returns:
            过滤后的股票列表

        Requirements:
            - 2.1: 过滤ST股票
            - 2.2: 过滤价格低于3元的股票
            - 2.3: 过滤价格高于300元的股票
            - 2.4: 过滤市值小于50亿的股票
            - 2.5: 过滤上市时间少于90天的新股
        """
        if not stocks:
            return []

        logger.info(f"开始应用过滤条件，初始股票数: {len(stocks)}")

        filtered = []
        filter_stats = {
            'st_stock': 0,
            'price_too_low': 0,
            'price_too_high': 0,
            'market_cap_too_small': 0,
            'newly_listed': 0,
        }

        for stock in stocks:
            # 过滤 ST 股票
            if self._is_st_stock(stock.name):
                filter_stats['st_stock'] += 1
                logger.debug(f"过滤ST股票: {stock.code} {stock.name}")
                continue

            # 过滤价格范围
            if stock.price < self.min_price:
                filter_stats['price_too_low'] += 1
                logger.debug(f"过滤低价股: {stock.code} {stock.name} 价格={stock.price}元")
                continue

            if stock.price > self.max_price:
                filter_stats['price_too_high'] += 1
                logger.debug(f"过滤高价股: {stock.code} {stock.name} 价格={stock.price}元")
                continue

            # 过滤市值
            if stock.market_cap < self.min_market_cap:
                filter_stats['market_cap_too_small'] += 1
                logger.debug(f"过滤小市值股: {stock.code} {stock.name} 市值={stock.market_cap/1e8:.2f}亿")
                continue

            # 过滤上市时间
            if stock.list_days > 0 and stock.list_days < self.min_list_days:
                filter_stats['newly_listed'] += 1
                logger.debug(f"过滤新股: {stock.code} {stock.name} 上市{stock.list_days}天")
                continue

            # 通过所有过滤条件
            filtered.append(stock)

        # 记录过滤统计
        logger.info(f"过滤完成: 剩余 {len(filtered)} 只股票")
        logger.info(f"过滤统计: ST股票={filter_stats['st_stock']}, "
                   f"低价股={filter_stats['price_too_low']}, "
                   f"高价股={filter_stats['price_too_high']}, "
                   f"小市值={filter_stats['market_cap_too_small']}, "
                   f"新股={filter_stats['newly_listed']}")

        return filtered

    def _is_st_stock(self, name: str) -> bool:
        """
        判断是否为ST股票

        ST股票特征：
        - 名称包含 "ST"
        - 名称包含 "*ST"
        - 名称包含 "S*ST"
        - 名称包含 "SST"

        Args:
            name: 股票名称

        Returns:
            True 表示是ST股票，False 表示不是

        Requirements:
            - 2.1: 过滤ST股票和*ST股票
        """
        if not name:
            return False

        # 检查是否包含ST标记
        st_markers = ['ST', '*ST', 'S*ST', 'SST']
        for marker in st_markers:
            if marker in name.upper():
                return True

        return False

    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        检查缓存是否有效

        Args:
            cache_key: 缓存键

        Returns:
            True 表示缓存有效，False 表示缓存过期或不存在
        """
        if cache_key not in self._cache:
            return False

        if cache_key not in self._cache_timestamps:
            return False

        elapsed = time.time() - self._cache_timestamps[cache_key]
        return elapsed < self.cache_ttl

    def _update_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """
        更新缓存

        Args:
            cache_key: 缓存键
            data: 缓存数据
        """
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()
        logger.debug(f"缓存已更新: {cache_key}")

    def clear_cache(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("缓存已清空")


if __name__ == "__main__":
    # 测试代码
    import sys
    sys.path.insert(0, '..')
    from hot_stock_recommender.models import StockInfo

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    finder = HotStockFinder()
    hot_stocks = finder.find_hot_stocks()

    print(f"\n发现 {len(hot_stocks)} 只热门股票:")
    for i, stock in enumerate(hot_stocks[:10], 1):
        print(f"{i}. {stock.code} {stock.name}: "
              f"价格={stock.price:.2f}元, 涨幅={stock.change_pct:.2f}%, "
              f"换手率={stock.turnover_rate:.2f}%, "
              f"市值={stock.market_cap/1e8:.2f}亿")
