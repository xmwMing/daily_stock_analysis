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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import pandas as pd

from data_provider import DataFetcherManager
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

    def __init__(
        self,
        cache_ttl: int = 1800,
        data_manager: Optional[DataFetcherManager] = None,
        enrich_workers: Optional[int] = None,
    ):
        """
        初始化发现器

        Args:
            cache_ttl: 缓存有效期（秒），默认30分钟
        """
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self.data_manager = data_manager or DataFetcherManager()

        # 从配置加载过滤条件
        filter_config = HOT_STOCK_CONFIG.get('filter', {})
        self.min_price = filter_config.get('min_price', 3.0)
        self.max_price = filter_config.get('max_price', 300.0)
        self.min_list_days = filter_config.get('min_list_days', 90)
        self.include_star_stock = filter_config.get('include_star_stock', True)

        # 从配置加载获取数量
        self.fetch_count = HOT_STOCK_CONFIG.get('fetch_count', 30)
        self.top_n = int(HOT_STOCK_CONFIG.get('top_n', 5))
        self.enrich_limit = max(self.top_n * 4, 20)
        configured_workers = int(HOT_STOCK_CONFIG.get('max_concurrent', 10))
        self.enrich_workers = enrich_workers if enrich_workers is not None else max(1, min(configured_workers, 6))

        # 统计信息
        self.stats = {
            'gainers_count': 0,
            'volume_count': 0,
            'deal_count': 0,
            'turnover_count': 0,
            'total_before_filter': 0,
            'total_after_filter': 0
        }

        logger.info(f"HotStockFinder 初始化完成: 缓存TTL={cache_ttl}秒, "
                   f"每个榜单获取{self.fetch_count}只, enrich并发={self.enrich_workers}, enrich候选上限={self.enrich_limit}, "
                   f"过滤条件=[价格:{self.min_price}-{self.max_price}元, "
                   f"上市>={self.min_list_days}天, "
                   f"科创板/创业板股票={self.include_star_stock}]")

    def find_hot_stocks(self) -> List[StockInfo]:
        """
        发现热门股票

        流程：
        1. 获取人气榜和飙升榜前N只股票（N由配置决定）
        2. 合并并去重
        3. 使用DataFetcherManager获取详细实时行情数据
        4. 应用过滤条件

        Returns:
            List[StockInfo]: 过滤后的热门股票列表

        Requirements:
            - 1.1, 1.2: 获取人气榜和飙升榜
            - 1.5: 去重逻辑
            - 2.1-2.5: 应用过滤条件
        """
        logger.info("=" * 60)
        logger.info("开始发现热门股票...")
        start_time = time.time()

        try:
            # 获取热门榜单数据（并行抓取，减少总耗时）
            popularity_df = None
            surge_df = None
            deal_df = None

            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_name = {
                    executor.submit(self._fetch_popularity_ranking, self.fetch_count): 'popularity',
                    executor.submit(self._fetch_surge_ranking, self.fetch_count): 'surge',
                    executor.submit(self._fetch_deal_ranking, self.fetch_count): 'deal',
                }

                for future in as_completed(future_to_name):
                    name = future_to_name[future]
                    try:
                        df = future.result()
                    except Exception as e:
                        logger.error(f"获取榜单失败: {name}, error={e}", exc_info=True)
                        df = None

                    if name == 'popularity':
                        popularity_df = df
                    elif name == 'surge':
                        surge_df = df
                    elif name == 'deal':
                        deal_df = df

            # 更新统计信息
            self.stats['gainers_count'] = len(surge_df) if surge_df is not None and not surge_df.empty else 0
            self.stats['volume_count'] = len(deal_df) if deal_df is not None and not deal_df.empty else 0
            self.stats['deal_count'] = self.stats['volume_count']
            self.stats['turnover_count'] = len(popularity_df) if popularity_df is not None and not popularity_df.empty else 0

            # 合并两个榜单
            all_stocks = []
            stock_codes_seen = set()

            # 处理飙升榜
            if surge_df is not None and not surge_df.empty:
                for _, row in surge_df.iterrows():
                    code = str(row.get('代码', ''))
                    if code and code not in stock_codes_seen:
                        stock_info = self._row_to_stock_info(row)
                        if stock_info:
                            all_stocks.append(stock_info)
                            stock_codes_seen.add(code)

            # 处理人气榜
            if popularity_df is not None and not popularity_df.empty:
                for _, row in popularity_df.iterrows():
                    code = str(row.get('代码', ''))
                    if code and code not in stock_codes_seen:
                        stock_info = self._row_to_stock_info(row)
                        if stock_info:
                            all_stocks.append(stock_info)
                            stock_codes_seen.add(code)

            # 处理讨论热榜
            if deal_df is not None and not deal_df.empty:
                for _, row in deal_df.iterrows():
                    code = str(row.get('代码', ''))
                    if code and code not in stock_codes_seen:
                        stock_info = self._row_to_stock_info(row)
                        if stock_info:
                            all_stocks.append(stock_info)
                            stock_codes_seen.add(code)

            # 更新总数量统计
            self.stats['total_before_filter'] = len(all_stocks)

            logger.info(f"合并两个榜单后共获得 {len(all_stocks)} 只不重复的热门股票")
            logger.info(
                f"各榜单获取数量: 飙升榜={self.stats['gainers_count']}, "
                f"人气榜={self.stats['turnover_count']}, 讨论榜={self.stats['deal_count']}"
            )

            # 先做轻量过滤，再限制 enrich 候选，避免对大池逐个请求实时行情
            prefiltered_stocks = self._apply_prefilters(all_stocks)
            enrich_candidates = self._select_enrich_candidates(prefiltered_stocks)
            logger.info(
                "热门池轻量过滤后 %s 只，进入实时 enrich 候选 %s 只",
                len(prefiltered_stocks),
                len(enrich_candidates),
            )

            # 使用DataFetcherManager获取详细实时行情数据
            all_stocks = self._enrich_stock_data(enrich_candidates)

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

    def _enrich_stock_data(self, stocks: List[StockInfo]) -> List[StockInfo]:
        """
        使用DataFetcherManager丰富股票数据，获取缺失的关键指标

        Args:
            stocks: 股票列表

        Returns:
            丰富数据后的股票列表
        """
        logger.info("[步骤] 丰富股票数据，获取缺失的关键指标...")

        try:
            if not stocks:
                return []

            workers = min(self.enrich_workers, len(stocks))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                enriched_stocks = list(executor.map(self._enrich_single_stock, stocks))

            logger.info(f"[步骤] 成功丰富 {len(enriched_stocks)} 只股票的数据")
            return enriched_stocks

        except Exception as e:
            logger.error(f"[步骤] 丰富股票数据失败: {e}")
            # 如果失败，返回原始股票列表
            return stocks

    def _enrich_single_stock(self, stock: StockInfo) -> StockInfo:
        """Fetch realtime quote and merge into StockInfo."""
        try:
            code = stock.code.replace('SH', '').replace('SZ', '')
            logger.debug(f"[获取数据] 处理股票: {code} - {stock.name}")
            quote = self._get_realtime_quote_for_hot_pool(code)

            if quote:
                stock.price = quote.price or stock.price
                stock.change_pct = quote.change_pct or stock.change_pct
                stock.volume = quote.volume or stock.volume
                stock.amount = quote.amount or stock.amount
                stock.turnover_rate = quote.turnover_rate or stock.turnover_rate
                stock.market_cap = quote.total_mv or stock.market_cap

                debug_info = f"[更新数据] {code} {stock.name}: "
                debug_info += f"价格={stock.price}, 涨跌={stock.change_pct}%, "
                debug_info += f"成交量={stock.volume}, 成交额={stock.amount}, "
                debug_info += f"换手率={stock.turnover_rate}%"

                if stock.market_cap and stock.market_cap > 0:
                    debug_info += f", 市值={stock.market_cap}"
                logger.debug(debug_info)
            else:
                logger.warning(f"[获取失败] 未获取到 {code} 的实时行情")

            return stock

        except Exception as e:
            logger.error(f"[获取错误] 处理 {stock.code} 时出错: {e}")
            return stock

    def _get_realtime_quote_for_hot_pool(self, stock_code: str):
        """Prefer Sina realtime quote for hot-pool enrichment, fallback to manager routing."""
        try:
            # 热门池 enrich 优先尝试新浪接口（单股场景通常比腾讯更稳定）
            fetchers = self.data_manager._get_fetchers_snapshot()
            for fetcher in fetchers:
                if fetcher.name != 'AkshareFetcher':
                    continue
                if not hasattr(fetcher, 'get_realtime_quote'):
                    break
                quote = self.data_manager._call_fetcher_method(
                    fetcher,
                    'get_realtime_quote',
                    stock_code,
                    source='sina',
                )
                if quote is not None:
                    return quote
                break
        except Exception as exc:
            logger.debug("热门池新浪实时行情尝试失败，改用默认路由: %s", exc)

        return self.data_manager.get_realtime_quote(stock_code)

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

    def _fetch_popularity_ranking(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        获取人气榜前N只股票

        使用 akshare 的 stock_hot_follow_xq() 获取雪球关注热榜数据。

        Args:
            limit: 获取数量，默认100

        Returns:
            DataFrame 包含人气榜数据，失败返回 None
        """
        cache_key = f"popularity_{limit}_{date.today()}"

        # 检查缓存
        if self._is_cache_valid(cache_key):
            logger.info(f"[缓存命中] 使用缓存的人气榜数据")
            return self._cache[cache_key]

        try:
            import akshare as ak

            logger.info(f"[API调用] ak.stock_hot_follow_xq() 获取人气榜...")

            # 获取人气榜数据
            df = ak.stock_hot_follow_xq()

            if df is None or df.empty:
                logger.warning("[API返回] 人气榜数据为空")
                return None

            # 取前N只
            df = self._normalize_xq_hot_df(df).head(limit)

            logger.info(f"[API返回] 人气榜获取成功: 返回 {len(df)} 只股票")

            # 更新缓存
            self._update_cache(cache_key, df)

            return df

        except Exception as e:
            logger.error(f"[API错误] 获取人气榜失败: {e}", exc_info=True)
            return None

    def _fetch_surge_ranking(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        获取飙升榜前N只股票

        使用 akshare 的 stock_hot_tweet_xq() 获取雪球讨论飙升榜数据。

        Args:
            limit: 获取数量，默认100

        Returns:
            DataFrame 包含飙升榜数据，失败返回 None
        """
        cache_key = f"surge_{limit}_{date.today()}"

        # 检查缓存
        if self._is_cache_valid(cache_key):
            logger.info(f"[缓存命中] 使用缓存的飙升榜数据")
            return self._cache[cache_key]

        try:
            import akshare as ak

            logger.info(f"[API调用] ak.stock_hot_tweet_xq() 获取飙升榜...")

            # 获取飙升榜数据
            df = ak.stock_hot_tweet_xq()

            if df is None or df.empty:
                logger.warning("[API返回] 飙升榜数据为空")
                return None

            # 取前N只
            df = self._normalize_xq_hot_df(df).head(limit)

            logger.info(f"[API返回] 飙升榜获取成功: 返回 {len(df)} 只股票")

            # 更新缓存
            self._update_cache(cache_key, df)

            return df

        except Exception as e:
            logger.error(f"[API错误] 获取飙升榜失败: {e}", exc_info=True)
            return None

    def _fetch_deal_ranking(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch Xueqiu deal hot ranking as an additional hot source."""
        cache_key = f"deal_{limit}_{date.today()}"

        if self._is_cache_valid(cache_key):
            logger.info(f"[缓存命中] 使用缓存的讨论榜数据")
            return self._cache[cache_key]

        try:
            import akshare as ak

            logger.info(f"[API调用] ak.stock_hot_deal_xq() 获取讨论榜...")
            df = ak.stock_hot_deal_xq()

            if df is None or df.empty:
                logger.warning("[API返回] 讨论榜数据为空")
                return None

            df = self._normalize_xq_hot_df(df).head(limit)
            logger.info(f"[API返回] 讨论榜获取成功: 返回 {len(df)} 只股票")

            self._update_cache(cache_key, df)
            return df

        except Exception as e:
            logger.error(f"[API错误] 获取讨论榜失败: {e}", exc_info=True)
            return None

    @staticmethod
    def _normalize_xq_hot_df(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Xueqiu hot ranking fields to internal schema."""
        if df is None or df.empty:
            return df

        rename_map = {
            '股票代码': '代码',
            '股票简称': '名称',
            '最新价': '最新价',
            '关注': '热度',
        }
        normalized = df.rename(columns=rename_map).copy()
        return normalized

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

            # 打印行数据，了解数据结构
            logger.debug(f"[API返回] 行数据: {row.to_dict()}")

            # 尝试不同的列名组合，确保能够从不同 API 响应中提取数据
            code = str(
                row.get('代码', '')
                or row.get('股票代码', '')
                or row.get('证券代码', '')
                or row.get('code', '')
                or row.get('stock_code', '')
            )
            name = str(
                row.get('股票名称', '')
                or row.get('股票简称', '')
                or row.get('名称', '')
                or row.get('证券名称', '')
                or row.get('name', '')
                or row.get('stock_name', '')
            )
            price = safe_float(row.get('最新价') or row.get('price', '') or row.get('最新价(元)', '') or row.get('current_price', ''))
            change_pct = safe_float(row.get('涨跌幅') or row.get('涨跌幅(%)', '') or row.get('change_pct', '') or row.get('涨跌幅%', ''))
            volume = safe_float(row.get('成交量') or row.get('volume', '') or row.get('成交量(手)', '') or row.get('vol', ''))
            amount = safe_float(row.get('成交额') or row.get('amount', '') or row.get('成交额(万元)', '') or row.get('turnover', ''))
            turnover_rate = safe_float(row.get('换手率') or row.get('turnover_rate', '') or row.get('换手率(%)', '') or row.get('turnover%', ''))
            market_cap = safe_float(row.get('总市值') or row.get('market_cap', '') or row.get('总市值(亿元)', '') or row.get('market_value', ''))
            pe_ratio = safe_float(row.get('市盈率-动态') or row.get('pe_ratio', '') or row.get('市盈率', '') or row.get('pe', '')) if any(key in row for key in ['市盈率-动态', 'pe_ratio', '市盈率', 'pe']) else None

            # 打印提取的股票信息
            logger.debug(f"[API返回] 提取的股票信息: code={code}, name={name}, price={price}")

            # 检查股票名称是否为空
            if not name:
                logger.warning(f"跳过无名称的股票: 代码={code}")
                return None

            # 检查股票代码是否为空
            if not code:
                logger.warning(f"跳过无代码的股票: 名称={name}")
                return None

            try:
                stock_info = StockInfo(
                    code=code,
                    name=name,
                    price=price,
                    change_pct=change_pct,
                    volume=volume,
                    amount=amount,
                    turnover_rate=turnover_rate,
                    market_cap=market_cap,
                    list_days=list_days,
                    pe_ratio=pe_ratio,
                )

                return stock_info
            except Exception as e:
                logger.warning(f"转换股票信息失败: {e}, 代码={code}, 名称={name}")
                return None

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
            'star_stock': 0,
        }

        for stock in stocks:
            # 过滤 ST 股票
            if self._is_st_stock(stock.name):
                filter_stats['st_stock'] += 1
                logger.debug(f"过滤ST股票: {stock.code} {stock.name}")
                continue

            # 过滤科创板和创业板股票
            if not self.include_star_stock and self._is_filtered_board_stock(stock.code):
                filter_stats['star_stock'] += 1
                logger.debug(f"过滤科创板/创业板股票: {stock.code} {stock.name}")
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

            # 取消市值过滤条件

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
                   f"新股={filter_stats['newly_listed']}, "
                   f"科创板股票={filter_stats['star_stock']}")

        return filtered

    def _apply_prefilters(self, stocks: List[StockInfo]) -> List[StockInfo]:
        """Apply cheap local filters before realtime enrichment."""
        if not stocks:
            return []

        prefiltered: List[StockInfo] = []
        for stock in stocks:
            if self._is_st_stock(stock.name):
                continue
            if not self.include_star_stock and self._is_filtered_board_stock(stock.code):
                continue
            if stock.list_days > 0 and stock.list_days < self.min_list_days:
                continue
            if stock.price > 0:
                if stock.price < self.min_price or stock.price > self.max_price:
                    continue
            prefiltered.append(stock)
        return prefiltered

    def _select_enrich_candidates(self, stocks: List[StockInfo]) -> List[StockInfo]:
        """Keep the hottest candidates for realtime quote enrichment."""
        if len(stocks) <= self.enrich_limit:
            return stocks

        ranked = sorted(
            stocks,
            key=lambda s: (
                float(s.amount or 0.0),
                float(s.turnover_rate or 0.0),
                float(s.volume or 0.0),
                abs(float(s.change_pct or 0.0)),
            ),
            reverse=True,
        )
        return ranked[: self.enrich_limit]

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

    def _is_filtered_board_stock(self, code: str) -> bool:
        """
        判断是否为科创板或创业板股票

        科创板股票特征：
        - 股票代码以 688 开头
        创业板股票特征：
        - 股票代码以 300 或 301 开头

        Args:
            code: 股票代码

        Returns:
            True 表示是科创板或创业板股票，False 表示不是
        """
        if not code:
            return False

        # 清理股票代码，移除前缀
        clean_code = code.replace('SH', '').replace('SZ', '')

        # 检查是否以 688 (科创板) 或 300/301 (创业板) 开头
        return clean_code.startswith('688') or clean_code.startswith('300') or clean_code.startswith('301')

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
        # 构建输出信息，根据实际数据情况显示
        output_info = f"{i}. {stock.code} {stock.name}: "
        output_info += f"价格={stock.price:.2f}元, 涨幅={stock.change_pct:.2f}%, "
        output_info += f"换手率={stock.turnover_rate:.2f}%"

        # 只在市值有有效数据时显示
        if stock.market_cap and stock.market_cap > 0:
            output_info += f", 市值={stock.market_cap/1e8:.2f}亿"

        print(output_info)
