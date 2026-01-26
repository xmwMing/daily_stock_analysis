# -*- coding: utf-8 -*-
"""
===================================
WebUI 入口文件 (向后兼容)
===================================

本文件保持向后兼容，实际实现已迁移到 web/ 包

结构说明:
    web/
    ├── __init__.py    - 包初始化
    ├── server.py      - HTTP 服务器
    ├── router.py      - 路由分发
    ├── handlers.py    - 请求处理器
    ├── services.py    - 业务服务层
    └── templates.py   - HTML 模板

API Endpoints:
  GET  /              - 配置页面
  GET  /health        - 健康检查
  GET  /analysis?code=xxx - 触发单只股票异步分析
  GET  /tasks         - 查询任务列表
  GET  /task?id=xxx   - 查询任务状态
  POST /update        - 更新配置

Usage:
  python webui.py
  WEBUI_HOST=0.0.0.0 WEBUI_PORT=8000 python webui.py
"""

from __future__ import annotations

import os
import logging

# 从 web 包导入（新架构）
from web.server import WebServer, run_server_in_thread, run_server
from web.router import Router, get_router
from web.services import ConfigService, AnalysisService, get_config_service, get_analysis_service
from web.handlers import PageHandler, ApiHandler
from web.templates import render_config_page, render_error_page

logger = logging.getLogger(__name__)

# 导出所有公共接口（保持向后兼容）
__all__ = [
    # 服务器
    'WebServer',
    'run_server_in_thread',
    'run_server',
    # 路由
    'Router',
    'get_router',
    # 服务
    'ConfigService',
    'AnalysisService',
    'get_config_service',
    'get_analysis_service',
    # 处理器
    'PageHandler',
    'ApiHandler',
    # 模板
    'render_config_page',
    'render_error_page',
]


def _start_bot_stream_clients() -> None:
    """启动 Bot Stream 模式客户端（如果已配置）"""
    from src.config import get_config
    config = get_config()
    
    # 钉钉 Stream 模式
    if config.dingtalk_stream_enabled:
        try:
            from bot.platforms import start_dingtalk_stream_background, DINGTALK_STREAM_AVAILABLE
            if DINGTALK_STREAM_AVAILABLE:
                if start_dingtalk_stream_background():
                    logger.info("[WebUI] 钉钉 Stream 客户端已在后台启动")
                else:
                    logger.warning("[WebUI] 钉钉 Stream 客户端启动失败")
            else:
                logger.warning("[WebUI] 钉钉 Stream 模式已启用但 SDK 未安装")
                logger.warning("[WebUI] 请运行: pip install dingtalk-stream")
        except Exception as e:
            logger.error(f"[WebUI] 启动钉钉 Stream 客户端失败: {e}")

    # 飞书 Stream 模式
    if getattr(config, 'feishu_stream_enabled', False):
        try:
            from bot.platforms import start_feishu_stream_background, FEISHU_SDK_AVAILABLE
            if FEISHU_SDK_AVAILABLE:
                if start_feishu_stream_background():
                    logger.info("[WebUI] 飞书 Stream 客户端已在后台启动")
                else:
                    logger.warning("[WebUI] 飞书 Stream 客户端启动失败")
            else:
                logger.warning("[WebUI] 飞书 Stream 模式已启用但 SDK 未安装")
                logger.warning("[WebUI] 请运行: pip install lark-oapi")
        except Exception as e:
            logger.error(f"[WebUI] 启动飞书 Stream 客户端失败: {e}")


def main() -> int:
    """
    主入口函数
    
    支持环境变量配置:
        WEBUI_HOST: 监听地址 (默认 127.0.0.1)
        WEBUI_PORT: 监听端口 (默认 8000)
    """
    host = os.getenv("WEBUI_HOST", "127.0.0.1")
    port = int(os.getenv("WEBUI_PORT", "8000"))
    
    print(f"WebUI running: http://{host}:{port}")
    print("API Endpoints:")
    print("  GET  /              - 配置页面")
    print("  GET  /health        - 健康检查")
    print("  GET  /analysis?code=xxx - 触发分析")
    print("  GET  /tasks         - 任务列表")
    print("  GET  /task?id=xxx   - 任务状态")
    print("  POST /update        - 更新配置")
    print()
    print("Bot Webhooks:")
    print("  POST /bot/feishu    - 飞书机器人")
    print("  POST /bot/dingtalk  - 钉钉机器人")
    print("  POST /bot/wecom     - 企业微信机器人")
    print("  POST /bot/telegram  - Telegram 机器人")
    print()
    
    # 启动 Bot Stream 客户端（如果配置了）
    _start_bot_stream_clients()
    
    try:
        run_server(host=host, port=port)
    except KeyboardInterrupt:
        pass
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
