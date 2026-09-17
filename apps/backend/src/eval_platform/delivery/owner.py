"""Local-only owner maintenance. No HTTP registration or recovery route."""

import argparse
import getpass
import sys
import warnings

from eval_platform.adapters.identity.passwords import Argon2Passwords
from eval_platform.adapters.persistence.bootstrap import initialize_empty_database
from eval_platform.adapters.persistence.identity import PostgresIdentityRepository
from eval_platform.adapters.persistence.membership import PostgresMembershipRepository
from eval_platform.application.identity import IdentityService
from eval_platform.delivery.http.config import database_url
from eval_platform.domain.identity import IdentityConflict, IdentityUnavailable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentExam 本机所有者维护")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init-db", help="仅在明确的空白专属数据库建立全部表")
    subcommands.add_parser("upgrade-members", help="仅为现有专属身份库补充邀请表")
    for command in ("bootstrap", "recover"):
        subcommands.add_parser(command).add_argument("username")
    arguments = parser.parse_args(argv)
    try:
        if arguments.command in {"bootstrap", "recover"} and not sys.stdin.isatty():
            raise ValueError("密码只能从本机交互终端输入，不接受管道或参数")
        dsn = database_url()
        repository = PostgresIdentityRepository(dsn)
        if arguments.command == "upgrade-members":
            PostgresMembershipRepository(dsn).initialize_schema()
            print("邀请表已建立；未创建账号或修改既有会话。")
            return 0
        if arguments.command == "init-db":
            initialize_empty_database(dsn)
            print("平台全部表已建立；未创建账号、任务、Job 或文件。")
            return 0
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("新密码（15–128 个字符，不回显）：")
            if password != getpass.getpass("再次输入新密码："):
                raise ValueError("两次密码不一致，未修改账号")
        service = IdentityService(repository, Argon2Passwords())
        if arguments.command == "bootstrap":
            service.bootstrap_owner(arguments.username, password)
        else:
            service.recover_owner(arguments.username, password)
        print("所有者维护完成；恢复操作会使旧会话失效。")
        return 0
    except (ValueError, getpass.GetPassWarning):
        print("输入或配置无效；请使用本机交互终端与专属数据库配置。", file=sys.stderr)
    except IdentityConflict:
        print("所有者已存在，或恢复目标不是已有所有者。", file=sys.stderr)
    except IdentityUnavailable:
        print("身份存储操作失败；未确认成功，不输出连接或凭据信息。", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
