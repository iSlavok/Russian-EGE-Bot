import sys

from loguru import logger


def setup_logging() -> None:
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        colorize=True,
    )

    logger.add(
        "logs/bot.log",
        format=log_format,
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
    )

    logger.add(
        "logs/errors.log",
        format=log_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )
