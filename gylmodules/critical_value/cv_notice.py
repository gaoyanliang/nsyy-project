import concurrent.futures
import logging

import redis
import requests
from ping3 import ping as sync_ping

from gylmodules import global_config
from gylmodules.critical_value import cv_config

logger = logging.getLogger(__name__)
pool = redis.ConnectionPool(host=global_config.REDIS_HOST, port=global_config.REDIS_PORT,
                            db=global_config.REDIS_DB, decode_responses=True)

# 全局复用，模块级只创建一次
_ALERT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=32,thread_name_prefix="cv-alert",)

_PING_TIMEOUT = 1        # 秒
_HTTP_TIMEOUT = 3        # 秒
_ALERT_TOTAL_WAIT = 8    # 同步等待所有站点通知完成的总超时



def _ping_ok(ip: str) -> bool:
    try:
        return sync_ping(ip, timeout=_PING_TIMEOUT) is not None
    except Exception:
        return False


def _send_popup(ip: str, msg: str) -> bool:
    try:
        resp = requests.post(
            f"http://{ip}:8085/opera_wiki",
            json={"type": "popup", "wiki_info": msg},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.debug("popup 失败 ip=%s err=%s", ip, e)
        return False


def _try_auto_start(ip: str) -> bool:
    try:
        resp = requests.post(
            f"http://{ip}:8091/opera_wiki",   # 沿用原来 8085→8091 的规则
            json={"type": "popup", "wiki_info": ""},   # 按你原来的 payload 调整
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.debug("auto_start 失败 ip=%s err=%s", ip, e)
        return False


def _notify_one_site(ip: str, msg: str) -> None:
    """对一个站点发通知：先 ping，再 popup，popup 失败则尝试拉起自动启动程序。"""
    if not _ping_ok(ip):
        logger.debug("站点不可达 ip=%s", ip)
        return
    if _send_popup(ip, msg):
        return
    # popup 失败，尝试自动启动客户端程序
    if not _try_auto_start(ip):
        # 记录失败，供 re_alert_fail_ip_log 后续重试
        try:
            from gylmodules.critical_value.critical_value import write_alert_fail_log
            write_alert_fail_log([ip], "通知失败")
        except Exception:
            logger.exception("write_alert_fail_log 失败 ip=%s", ip)


def alert_notice(dept_id, ward_id, msg: str) -> None:
    """
    同步函数。内部对多个站点并行发通知，最多阻塞 _ALERT_TOTAL_WAIT 秒。
    可以在任何线程里直接调用，不需要事件循环。
    """
    try:
        redis_client = redis.Redis(connection_pool=pool)
        sites = set()
        if dept_id and str(dept_id).strip().isdigit() and int(dept_id):
            sites |= redis_client.smembers(
                cv_config.CV_SITES_REDIS_KEY[2].format(str(dept_id))
            )
        if ward_id and str(ward_id).strip().isdigit() and int(ward_id):
            sites |= redis_client.smembers(
                cv_config.CV_SITES_REDIS_KEY[1].format(str(ward_id))
            )
    except Exception:
        logger.exception("alert: 读取站点失败 dept=%s ward=%s", dept_id, ward_id)
        return

    if not sites:
        return

    ips = [ip.decode() if isinstance(ip, bytes) else ip for ip in sites]

    futures = [_ALERT_EXECUTOR.submit(_notify_one_site, ip, msg) for ip in ips]

    # 不需要 as_completed，全部并行提交后统一等待
    done, not_done = concurrent.futures.wait(
        futures, timeout=_ALERT_TOTAL_WAIT
    )
    if not_done:
        logger.warning("alert: %d/%d 个站点通知超时", len(not_done), len(futures))
        for f in not_done:
            f.cancel()   # 已开始的不会真的取消，但语义清晰


_DISPATCH_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="cv-alert-dispatch"
)


def alert_async(dept_id, ward_id, msg):
    if not dept_id and not ward_id:
        return
    fut = _DISPATCH_EXECUTOR.submit(alert_notice, dept_id, ward_id, msg)
    fut.add_done_callback(_log_alert_result)

def _log_alert_result(fut):
    exc = fut.exception()
    if exc:
        logger.error("alert 后台任务异常: %r", exc)





