from __future__ import annotations

import time

import mcp.types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult

from . import get_session_logger


class ToolRecorderMiddleware(Middleware):
    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        session_logger = get_session_logger()
        if session_logger is None:
            return await call_next(context)

        tool_name = context.message.name
        arguments = context.message.arguments or {}
        start = time.perf_counter()

        try:
            result = await call_next(context)
            duration_ms = (time.perf_counter() - start) * 1000
            session_logger.tool_call(
                tool_name=tool_name,
                duration_ms=duration_ms,
                success=True,
                params=arguments,
                response=str(result),
            )
            return result
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            session_logger.tool_call(
                tool_name=tool_name,
                duration_ms=duration_ms,
                success=False,
                error=str(e),
            )
            raise
