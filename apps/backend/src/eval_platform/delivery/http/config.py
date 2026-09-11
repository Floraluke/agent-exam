import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class HttpConfig:
    public_origin: str
    allow_insecure_loopback: bool = False

    def __post_init__(self) -> None:
        origin = urlsplit(self.public_origin)
        if (
            not origin.hostname
            or origin.username
            or origin.password
            or origin.path
            or origin.query
            or origin.fragment
        ):
            raise ValueError("公开 Origin 必须为不含路径或凭据的绝对地址")
        if origin.scheme != "https" and not (
            self.allow_insecure_loopback
            and origin.scheme == "http"
            and origin.hostname in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError("必须使用 HTTPS；HTTP 仅限显式启用的本机回环开发")

    @property
    def secure_cookie(self) -> bool:
        return self.public_origin.startswith("https://")

    @property
    def cookie_name(self) -> str:
        if self.secure_cookie:
            return "__Host-agentexam_session"
        return "agentexam_development_session"

    @classmethod
    def from_environment(cls) -> "HttpConfig":
        return cls(
            os.environ.get("AGENTEXAM_PUBLIC_ORIGIN", ""),
            os.environ.get("AGENTEXAM_ALLOW_INSECURE_LOOPBACK") == "1",
        )


def database_url() -> str:
    value = os.environ.get("AGENTEXAM_DATABASE_URL", "")
    if not value:
        raise ValueError("未配置应用专属 PostgreSQL 连接")
    return value
