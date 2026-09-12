"""Explicit local catalog schema upgrade; no implicit startup migrations."""

import argparse
import sys

from eval_platform.adapters.persistence.catalog import initialize_schema
from eval_platform.delivery.http.config import database_url
from eval_platform.domain.catalog import CatalogError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentExam 本机目录升级")
    parser.add_argument("command", choices=["init-db"])
    parser.parse_args(argv)
    try:
        initialize_schema(database_url())
        print("目录三表已建立；未登记任务、创建账号或运行评测。")
        return 0
    except (ValueError, CatalogError):
        print("目录升级未确认成功；不输出连接或凭据信息。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
