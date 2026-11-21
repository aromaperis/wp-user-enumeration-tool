from src.tools.check_rest_api import check_rest_api
from src.tools.check_author_archives import check_author_archives
from src.tools.check_error_leak import check_error_leak

TOOL_MAP = {
    "check_rest_api": check_rest_api,
    "check_author_archives": check_author_archives,
    "check_error_leak": check_error_leak
}