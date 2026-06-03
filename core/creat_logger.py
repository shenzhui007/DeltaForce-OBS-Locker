"""
日志模块 — 自动创建 logs/ 目录并写入日志，保持根目录整洁。

用法:
    from logger import get_logger

    logger = get_logger(__name__)                # 默认：同时输出到控制台 + logs/app.log
    logger = get_logger("my_module")             # 按模块名获取 logger
    logger = get_logger(__name__, level="DEBUG") # 自定义日志级别

    logger.info("这是一条 info 日志")
    logger.debug("这是一条 debug 日志")
    logger.error("这是一条 error 日志", exc_info=True)

    # 按天轮转的日志文件
    logger = get_logger(__name__, when="D", backup_count=7)  # 保留 7 天

    # 自定义日志文件路径
    logger = get_logger(__name__, log_file="logs/my_app.log")

配置:
    可通过 setup_logging() 进行全局配置，或在调用 get_logger() 时单独配置。
"""

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

# ---------------------------------------------------------------------------
# 默认配置
# ---------------------------------------------------------------------------
DEFAULT_LOG_DIR: str = "logs"
DEFAULT_LOG_FILE: str = "app.log"
DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_LOG_FORMAT: str = (
    "[%(asctime)s] [%(levelname)-8s] [%(name)s:%(lineno)d] %(message)s"
)
DEFAULT_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# 控制台格式（可以更简洁）
DEFAULT_CONSOLE_FORMAT: str = "[%(levelname)-8s] %(name)s — %(message)s"

# 已初始化的处理器缓存，避免重复添加
_handlers_cache: dict = {}


def ensure_log_dir(log_dir: str = DEFAULT_LOG_DIR) -> Path:
    """确保日志目录存在，不存在则自动创建。"""
    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    # 在日志目录里放一个 .gitkeep，方便纳入版本控制
    gitkeep = path / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    return path


def _build_file_handler(
    log_path: Union[str, Path],
    level: str = DEFAULT_LOG_LEVEL,
    fmt: Optional[str] = None,
    datefmt: Optional[str] = None,
    when: Optional[str] = None,
    backup_count: int = 30,
    max_bytes: Optional[int] = None,
    encoding: str = "utf-8",
) -> logging.Handler:
    """构建文件 Handler：支持按时间轮转、按大小轮转、或普通文件。"""

    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)  # 确保父目录存在

    formatter = logging.Formatter(
        fmt=fmt or DEFAULT_LOG_FORMAT,
        datefmt=datefmt or DEFAULT_DATE_FORMAT,
    )

    if when:  # 按时间轮转
        handler = TimedRotatingFileHandler(
            filename=str(log_path),
            when=when,
            interval=1,
            backupCount=backup_count,
            encoding=encoding,
        )
        handler.suffix = "%Y-%m-%d"
    elif max_bytes:  # 按大小轮转
        handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
        )
    else:
        handler = logging.FileHandler(
            filename=str(log_path),
            encoding=encoding,
        )

    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler.setFormatter(formatter)
    return handler


def _build_console_handler(
    level: str = DEFAULT_LOG_LEVEL,
    fmt: Optional[str] = None,
    datefmt: Optional[str] = None,
) -> logging.Handler:
    """构建控制台 Handler。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler.setFormatter(
        logging.Formatter(
            fmt=fmt or DEFAULT_CONSOLE_FORMAT,
            datefmt=datefmt or DEFAULT_DATE_FORMAT,
        )
    )
    return handler


def setup_logging(
    log_dir: str = DEFAULT_LOG_DIR,
    log_file: str = DEFAULT_LOG_FILE,
    level: str = DEFAULT_LOG_LEVEL,
    console: bool = True,
    file_fmt: Optional[str] = None,
    console_fmt: Optional[str] = None,
    datefmt: Optional[str] = None,
    when: Optional[str] = None,
    backup_count: int = 30,
    max_bytes: Optional[int] = None,
) -> None:
    """
    全局日志配置 — 配置 root logger。

    参数:
        log_dir:      日志目录，默认 "logs/"
        log_file:     日志文件名，默认 "app.log"
        level:        日志级别：DEBUG / INFO / WARNING / ERROR / CRITICAL
        console:      是否同时输出到控制台
        file_fmt:     文件日志格式（None 则用默认）
        console_fmt:  控制台日志格式（None 则用默认）
        datefmt:      时间格式
        when:         轮转周期："S"秒 / "M"分 / "H"时 / "D"天 / "W0"-"W6"周 / "midnight"
        backup_count: 保留的旧日志数量
        max_bytes:    单个日志文件最大字节数（设置后按大小轮转，优先级低于 when）
    """
    ensure_log_dir(log_dir)

    log_level = getattr(logging, level.upper(), logging.INFO)
    log_path = Path(log_dir) / log_file

    # 配置 root logger
    root = logging.getLogger()
    root.setLevel(log_level)

    # 清除已有 handlers（避免重复）
    root.handlers.clear()

    # 文件 handler
    file_handler = _build_file_handler(
        log_path=log_path,
        level=level,
        fmt=file_fmt,
        datefmt=datefmt,
        when=when,
        backup_count=backup_count,
        max_bytes=max_bytes,
    )
    root.addHandler(file_handler)

    # 控制台 handler
    if console:
        console_handler = _build_console_handler(
            level=level,
            fmt=console_fmt,
            datefmt=datefmt,
        )
        root.addHandler(console_handler)

    # 降低第三方库日志噪音
    for lib in ("urllib3", "requests", "matplotlib", "PIL"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_dir: str = DEFAULT_LOG_DIR,
    console: bool = True,
    when: Optional[str] = None,
    backup_count: int = 30,
    max_bytes: Optional[int] = None,
) -> logging.Logger:
    """
    获取一个已配置好的 logger。

    首次调用时会自动创建日志目录。如果 root logger 还没有 handler，
    则自动调用 setup_logging() 初始化（延迟初始化，避免空跑时也建目录）。

    参数:
        name:         logger 名称（建议传 __name__）
        level:        日志级别（默认取 root 级别）
        log_file:     指定独立的日志文件（默认写入公共 logs/app.log）
        log_dir:      日志目录（仅 log_file 未指定时生效）
        console:      是否输出到控制台
        when:         日志轮转周期
        backup_count: 保留的旧日志数量
        max_bytes:    按大小轮转的阈值

    返回:
        logging.Logger
    """
    # 延迟初始化：如果 root 还没有 handler，自动配一下
    root = logging.getLogger()
    if not root.handlers:
        setup_logging(
            log_dir=log_dir,
            log_file=DEFAULT_LOG_FILE,
            level=level or DEFAULT_LOG_LEVEL,
            console=console,
            when=when,
            backup_count=backup_count,
            max_bytes=max_bytes,
        )

    logger = logging.getLogger(name)

    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 如果指定了独立的 log_file，为这个 logger 单独挂一个文件 handler
    if log_file:
        log_path = Path(log_file)
        cache_key = str(log_path.resolve())
        if cache_key not in _handlers_cache:
            handler = _build_file_handler(
                log_path=log_path,
                level=level or DEFAULT_LOG_LEVEL,
                when=when,
                backup_count=backup_count,
                max_bytes=max_bytes,
            )
            _handlers_cache[cache_key] = handler
        logger.addHandler(_handlers_cache[cache_key])
        logger.propagate = False  # 避免重复输出到 root handler

    return logger


# ---------------------------------------------------------------------------
# 便捷函数：直接输出到 logs/ 目录的快捷方式
# ---------------------------------------------------------------------------
def create_daily_logger(name: str) -> logging.Logger:
    """创建一个按天轮转的 logger，保留最近 7 天。"""
    return get_logger(name, when="D", backup_count=7)


def create_hourly_logger(name: str) -> logging.Logger:
    """创建一个按小时轮转的 logger，保留最近 24 个文件。"""
    return get_logger(name, when="H", backup_count=24)


# ---------------------------------------------------------------------------
# 自测
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ensure_log_dir("logs")
    print(f"✅ 日志目录已就绪: {Path('logs').resolve()}")

    logger = get_logger("demo")

    logger.debug("这是一条 DEBUG 日志")
    logger.info("这是一条 INFO 日志")
    logger.warning("这是一条 WARNING 日志")
    logger.error("这是一条 ERROR 日志")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("捕获到异常")

    print("✅ 日志写入测试完成，请检查 logs/ 目录")
