# -*- coding: utf-8 -*-
"""
===================================
Web 处理器层 - 请求处理
===================================

职责：
1. 处理各类 HTTP 请求
2. 调用服务层执行业务逻辑
3. 返回响应数据

处理器分类：
- PageHandler: 页面请求处理
- ApiHandler: API 接口处理
"""

from __future__ import annotations

import json
import re
import logging
from http import HTTPStatus
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

from web.services import get_config_service, get_analysis_service
from web.templates import render_config_page
from src.enums import ReportType

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


# ============================================================
# 响应辅助类
# ============================================================

class Response:
    """HTTP 响应封装"""
    
    def __init__(
        self,
        body: bytes,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str = "text/html; charset=utf-8"
    ):
        self.body = body
        self.status = status
        self.content_type = content_type
    
    def send(self, handler: 'BaseHTTPRequestHandler') -> None:
        """发送响应到客户端"""
        handler.send_response(self.status)
        handler.send_header("Content-Type", self.content_type)
        handler.send_header("Content-Length", str(len(self.body)))
        handler.end_headers()
        handler.wfile.write(self.body)


class JsonResponse(Response):
    """JSON 响应封装"""
    
    def __init__(
        self,
        data: Dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK
    ):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        super().__init__(
            body=body,
            status=status,
            content_type="application/json; charset=utf-8"
        )


class HtmlResponse(Response):
    """HTML 响应封装"""
    
    def __init__(
        self,
        body: bytes,
        status: HTTPStatus = HTTPStatus.OK
    ):
        super().__init__(
            body=body,
            status=status,
            content_type="text/html; charset=utf-8"
        )


# ============================================================
# 页面处理器
# ============================================================

class PageHandler:
    """页面请求处理器"""
    
    def __init__(self):
        self.config_service = get_config_service()
    
    def handle_index(self) -> Response:
        """处理首页请求 GET /"""
        stock_list = self.config_service.get_stock_list()
        env_filename = self.config_service.get_env_filename()
        body = render_config_page(stock_list, env_filename)
        return HtmlResponse(body)
    
    def handle_update(self, form_data: Dict[str, list]) -> Response:
        """
        处理配置更新 POST /update
        
        Args:
            form_data: 表单数据
        """
        stock_list = form_data.get("stock_list", [""])[0]
        normalized = self.config_service.set_stock_list(stock_list)
        env_filename = self.config_service.get_env_filename()
        body = render_config_page(normalized, env_filename, message="已保存")
        return HtmlResponse(body)


# ============================================================
# API 处理器
# ============================================================

class ApiHandler:
    """API 请求处理器"""
    
    def __init__(self):
        self.analysis_service = get_analysis_service()
    
    def handle_health(self) -> Response:
        """
        健康检查 GET /health
        
        返回:
            {
                "status": "ok",
                "timestamp": "2026-01-19T10:30:00",
                "service": "stock-analysis-webui"
            }
        """
        data = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "service": "stock-analysis-webui"
        }
        return JsonResponse(data)
    
    def handle_analysis(self, query: Dict[str, list]) -> Response:
        """
        触发股票分析 GET /analysis?code=xxx
        
        Args:
            query: URL 查询参数
            
        返回:
            {
                "success": true,
                "message": "分析任务已提交",
                "code": "600519",
                "task_id": "600519_20260119_103000"
            }
        """
        # 获取股票代码参数
        code_list = query.get("code", [])
        if not code_list or not code_list[0].strip():
            return JsonResponse(
                {"success": False, "error": "缺少必填参数: code (股票代码)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        code = code_list[0].strip()

        # 验证股票代码格式：A股(6位数字) / 港股(HK+5位数字) / 美股(1-5个大写字母+.+2个后缀字母)
        code = code.upper()
        is_a_stock = re.match(r'^\d{6}$', code)
        is_hk_stock = re.match(r'^HK\d{5}$', code)
        is_us_stock = re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', code.upper())

        if not (is_a_stock or is_hk_stock or is_us_stock):
            return JsonResponse(
                {"success": False, "error": f"无效的股票代码格式: {code} (A股6位数字 / 港股HK+5位数字 / 美股1-5个字母)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        # 获取报告类型参数（默认精简报告）
        report_type_str = query.get("report_type", ["simple"])[0]
        report_type = ReportType.from_str(report_type_str)
        
        # 是否保存上下文快照（可选，默认读取配置）
        save_snapshot = None
        if "save_context_snapshot" in query:
            save_snapshot = self._parse_bool(query.get("save_context_snapshot", [""])[0])

        # 提交异步分析任务
        try:
            result = self.analysis_service.submit_analysis(
                code,
                report_type=report_type,
                save_context_snapshot=save_snapshot
            )
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"[ApiHandler] 提交分析任务失败: {e}")
            return JsonResponse(
                {"success": False, "error": f"提交任务失败: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

    def handle_analysis_history(self, query: Dict[str, list]) -> Response:
        """
        查询分析历史 GET /analysis/history

        Args:
            query: URL 查询参数 (code, query_id, days, limit)
        """
        code = query.get("code", [""])[0].strip() or None
        query_id = query.get("query_id", [""])[0].strip() or None

        try:
            days = int(query.get("days", ["30"])[0])
        except ValueError:
            days = 30

        try:
            limit = int(query.get("limit", ["50"])[0])
        except ValueError:
            limit = 50

        history = self.analysis_service.get_analysis_history(
            code=code,
            query_id=query_id,
            days=days,
            limit=limit
        )

        return JsonResponse({
            "success": True,
            "records": history,
            "count": len(history)
        })

    @staticmethod
    def _parse_bool(value: str) -> Optional[bool]:
        """
        解析布尔参数
        """
        text = (value or "").strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
        return None
    
    def handle_tasks(self, query: Dict[str, list]) -> Response:
        """
        查询任务列表 GET /tasks
        
        Args:
            query: URL 查询参数 (可选 limit)
            
        返回:
            {
                "success": true,
                "tasks": [...]
            }
        """
        limit_list = query.get("limit", ["20"])
        try:
            limit = int(limit_list[0])
        except ValueError:
            limit = 20
        
        tasks = self.analysis_service.list_tasks(limit=limit)
        return JsonResponse({"success": True, "tasks": tasks})
    
    def handle_task_status(self, query: Dict[str, list]) -> Response:
        """
        查询单个任务状态 GET /task?id=xxx
        
        Args:
            query: URL 查询参数
        """
        task_id_list = query.get("id", [])
        if not task_id_list or not task_id_list[0].strip():
            return JsonResponse(
                {"success": False, "error": "缺少必填参数: id (任务ID)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        task_id = task_id_list[0].strip()
        task = self.analysis_service.get_task_status(task_id)
        
        if task is None:
            return JsonResponse(
                {"success": False, "error": f"任务不存在: {task_id}"},
                status=HTTPStatus.NOT_FOUND
            )
        
        return JsonResponse({"success": True, "task": task})


# ============================================================
# Bot Webhook 处理器
# ============================================================

class BotHandler:
    """
    机器人 Webhook 处理器
    
    处理各平台的机器人回调请求。
    """
    
    def handle_webhook(self, platform: str, form_data: Dict[str, list], headers: Dict[str, str], body: bytes) -> Response:
        """
        处理 Webhook 请求
        
        Args:
            platform: 平台名称 (feishu, dingtalk, wecom, telegram)
            form_data: POST 数据（已解析）
            headers: HTTP 请求头
            body: 原始请求体
            
        Returns:
            Response 对象
        """
        try:
            from bot.handler import handle_webhook
            from bot.models import WebhookResponse
            
            # 调用 bot 模块处理
            webhook_response = handle_webhook(platform, headers, body)
            
            # 转换为 web 响应
            return JsonResponse(
                webhook_response.body,
                status=HTTPStatus(webhook_response.status_code)
            )
            
        except ImportError as e:
            logger.error(f"[BotHandler] Bot 模块未正确安装: {e}")
            return JsonResponse(
                {"error": "Bot module not available"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"[BotHandler] 处理 {platform} Webhook 失败: {e}")
            return JsonResponse(
                {"error": str(e)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )


# ============================================================
# 处理器工厂
# ============================================================

_page_handler: PageHandler | None = None
_api_handler: ApiHandler | None = None
_bot_handler: BotHandler | None = None


def get_page_handler() -> PageHandler:
    """获取页面处理器实例"""
    global _page_handler
    if _page_handler is None:
        _page_handler = PageHandler()
    return _page_handler


def get_api_handler() -> ApiHandler:
    """获取 API 处理器实例"""
    global _api_handler
    if _api_handler is None:
        _api_handler = ApiHandler()
    return _api_handler


def get_bot_handler() -> BotHandler:
    """获取 Bot 处理器实例"""
    global _bot_handler
    if _bot_handler is None:
        _bot_handler = BotHandler()
    return _bot_handler
