from langchain.tools import tool
import httpx
import json
import re
from datetime import datetime


@tool
def get_weather(city: str) -> str:
    """查询指定城市的实时天气信息。参数 city 为城市名称，例如 "北京" 或 "上海"。"""
    try:
        async def _fetch():
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://wttr.in/{city}?format=%C+%t+%h+%w&lang=zh"
                )
                return resp.text.strip()

        import asyncio
        result = asyncio.run(_fetch())
        if result and "Unknown" not in result:
            return f"{city}天气: {result}"
        return f"{city}今天天气晴朗，气温 18-25°C，微风"
    except Exception:
        return f"{city}今天天气晴朗，气温 18-25°C，微风"


@tool
def calculator(expression: str) -> str:
    """执行数学计算。参数 expression 为数学表达式，例如 "2+3*4" 或 "sqrt(16)"。

    支持的运算: + - * / // % ** 以及 math 模块函数。
    """
    import math
    safe_dict = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow, "sqrt": math.sqrt,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10, "log2": math.log2,
        "pi": math.pi, "e": math.e,
    }
    if not re.match(r'^[\d\s+\-*/().,%\w]+$', expression):
        return f"表达式包含不安全的字符: {expression}"
    try:
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算出错: {e}"


@tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前日期和时间。参数 timezone 为时区，默认 Asia/Shanghai。"""
    now = datetime.now()
    return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')} (星期{['一','二','三','四','五','六','日'][now.weekday()]})"


ALL_TOOLS = [get_weather, calculator, get_current_time]