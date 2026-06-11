from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

try:
    from loguru import logger
except Exception:
    class _FallbackLogger:
        def warning(self, *args, **kwargs):
            return None

    logger = _FallbackLogger()

from utils.time_utils import LOCAL_TIMEZONE


def _mask_summary_error(value: Any) -> str:
    text = str(value or "")
    for marker in ("token", "cookie", "password", "secret"):
        text = text.replace(marker, "***")
        text = text.replace(marker.upper(), "***")
    return text[:200]


def _health_summary_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def _health_summary_failure_status(status_value: Any) -> bool:
    normalized = str(status_value or "").strip().lower()
    return normalized in {
        "failed",
        "failure",
        "error",
        "exception",
        "cookie_expired",
        "missing_template",
        "timeout",
        "pending",
        "processing",
        "unresolved",
    }


def _health_summary_task_failure_status(status_value: Any) -> bool:
    normalized = str(status_value or "").strip().lower()
    return normalized in {
        "failed",
        "failure",
        "error",
        "exception",
        "cookie_expired",
        "missing_template",
        "timeout",
    }


def _health_summary_task_entry(log: Dict[str, Any], source: str) -> Dict[str, Any]:
    return {
        "source": source,
        "id": log.get("id"),
        "task_type": log.get("task_type") or log.get("event_type") or source,
        "cookie_id": str(log.get("cookie_id") or ""),
        "status": log.get("status") or log.get("processing_status") or "",
        "created_at": log.get("updated_at") or log.get("created_at") or "",
    }


def _normalize_summary_cookie_ids(cookie_ids: Optional[List[str]]) -> Optional[Set[str]]:
    if cookie_ids is None:
        return None

    normalized: Set[str] = set()
    for cookie_id in cookie_ids:
        account_id = str(cookie_id or "").strip()
        if account_id:
            normalized.add(account_id)
    return normalized


def _safe_get_cookie_status(db_manager: Any, account_id: str, details: Dict[str, Any]) -> bool:
    try:
        return bool(db_manager.get_cookie_status(account_id))
    except Exception as exc:
        logger.warning(f"health summary cookie status failed: {_mask_summary_error(exc)}")

    enabled = details.get("enabled")
    if enabled is None:
        return True
    return _health_summary_bool(enabled)


def _captcha_session_in_scope(
    session_id: Any,
    session_data: Dict[str, Any],
    user_id: Optional[int],
    cookie_ids: Set[str],
) -> bool:
    if user_id is None:
        return True

    user_text = str(user_id or "").strip()
    if user_text and str(session_id or "").strip() == user_text:
        return True

    if not isinstance(session_data, dict):
        return False

    for field_name in ("user_id", "owner_user_id"):
        if user_text and str(session_data.get(field_name) or "").strip() == user_text:
            return True

    session_cookie_id = str(
        session_data.get("cookie_id") or session_data.get("account_id") or ""
    ).strip()
    return bool(session_cookie_id and session_cookie_id in cookie_ids)


def _action_item(
    item_type: str,
    priority: str,
    title: str,
    description: str,
    action: str,
    label: str,
    cookie_id: str = "",
    source_id: Any = None,
) -> Dict[str, Any]:
    return {
        "type": item_type,
        "priority": priority,
        "title": title,
        "description": description,
        "cookie_id": str(cookie_id or ""),
        "source_id": source_id,
        "action": action,
        "action_label": label,
    }


def build_admin_health_summary(
    current_user: Dict[str, Any],
    db_manager: Any,
    runtime_status_builder: Callable[[str], Dict[str, Any]],
    captcha_controller: Any = None,
    user_id: Optional[int] = None,
    cookie_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a dashboard health snapshot without exposing secrets."""
    cookies = db_manager.get_all_cookies(user_id)
    if not isinstance(cookies, dict):
        cookies = {}

    scoped_cookie_ids = _normalize_summary_cookie_ids(cookie_ids)
    if scoped_cookie_ids is not None:
        cookies = {
            cookie_id: cookie_value
            for cookie_id, cookie_value in cookies.items()
            if str(cookie_id or "").strip() in scoped_cookie_ids
        }

    account_ids = [
        str(cookie_id or "").strip()
        for cookie_id in cookies.keys()
        if str(cookie_id or "").strip()
    ]
    account_id_set = set(account_ids)

    accounts = []
    online_count = 0
    enabled_count = 0
    disabled_count = 0
    suspected_expired_count = 0

    for account_id in account_ids:
        try:
            details = db_manager.get_cookie_details(account_id) or {}
        except Exception as exc:
            logger.warning(f"health summary cookie detail failed: {_mask_summary_error(exc)}")
            details = {}

        try:
            runtime_status = runtime_status_builder(account_id) or {}
        except Exception as exc:
            logger.warning(f"health summary runtime failed: {_mask_summary_error(exc)}")
            runtime_status = {}

        enabled = _safe_get_cookie_status(db_manager, account_id, details)
        running = bool(runtime_status.get("running"))
        stream_ready = bool(runtime_status.get("message_stream_ready"))
        token_ready = bool(runtime_status.get("has_current_token"))
        status_note = str(details.get("status_note") or "").strip()
        token_attention = bool(enabled and (status_note or (running and not token_ready)))
        username_ready = bool(str(details.get("username") or "").strip())
        password_ready = bool(str(details.get("password") or "").strip())
        proxy_type = str(details.get("proxy_type") or "none").strip().lower()
        proxy_enabled = bool(
            proxy_type not in {"", "none", "direct"}
            and str(details.get("proxy_host") or "").strip()
        )

        if enabled:
            enabled_count += 1
        if enabled and running and stream_ready:
            online_count += 1
        if not enabled:
            disabled_count += 1
        if token_attention:
            suspected_expired_count += 1

        accounts.append({
            "id": account_id,
            "remark": str(details.get("remark") or "").strip(),
            "enabled": enabled,
            "running": running,
            "connection_state": runtime_status.get("connection_state") or "",
            "message_stream_ready": stream_ready,
            "message_stream_status": runtime_status.get("message_stream_status") or "",
            "token_ready": token_ready,
            "token_attention": token_attention,
            "has_login_credentials": username_ready and password_ready,
            "proxy_enabled": proxy_enabled,
            "proxy_type": proxy_type if proxy_enabled else "none",
            "status_note": _mask_summary_error(status_note),
        })

    captcha_sessions = getattr(captcha_controller, "active_sessions", {}) if captcha_controller else {}
    if not isinstance(captcha_sessions, dict):
        captcha_sessions = {}
    pending_captcha = []
    for session_id, data in captcha_sessions.items():
        if not isinstance(data, dict) or data.get("completed"):
            continue
        if not _captcha_session_in_scope(session_id, data, user_id, account_id_set):
            continue
        pending_captcha.append({
            "session_id": str(session_id),
            "completed": False,
        })

    recent_failures: List[Dict[str, Any]] = []
    try:
        task_logs = db_manager.get_scheduled_task_logs(
            user_id=user_id,
            task_type=None,
            limit=50,
            offset=0,
        )
        for log in task_logs or []:
            if _health_summary_task_failure_status(log.get("status")):
                recent_failures.append(_health_summary_task_entry(log, "scheduled_task"))
    except Exception as exc:
        logger.warning(f"health summary task log failed: {_mask_summary_error(exc)}")

    try:
        for account_id in account_ids[:50]:
            risk_logs = db_manager.get_risk_control_logs(cookie_id=str(account_id), limit=5)
            for log in risk_logs or []:
                if _health_summary_failure_status(log.get("processing_status")):
                    recent_failures.append(_health_summary_task_entry(log, "risk_control"))
    except Exception as exc:
        logger.warning(f"health summary risk log failed: {_mask_summary_error(exc)}")

    recent_failures.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    recent_failures = recent_failures[:10]
    action_items: List[Dict[str, Any]] = []
    action_keys: Set[str] = set()

    def add_action(item: Dict[str, Any]) -> None:
        action_key = ":".join([
            str(item.get("type") or ""),
            str(item.get("cookie_id") or ""),
            str(item.get("source_id") or ""),
        ])
        if action_key in action_keys:
            return
        action_keys.add(action_key)
        action_items.append(item)

    for account in accounts:
        account_id = str(account.get("id") or "")
        if account.get("enabled") and account.get("token_attention"):
            status_note = str(account.get("status_note") or "").strip()
            description = (
                f"账号状态提示：{status_note}"
                if status_note
                else "当前运行中但 Token 未就绪，建议重新登录或刷新会话。"
            )
            add_action(_action_item(
                "token_unready",
                "high",
                f"账号 {account_id} 登录状态需处理",
                description,
                "open_account",
                "打开账号",
                cookie_id=account_id,
            ))
        if account.get("enabled") and not account.get("running"):
            add_action(_action_item(
                "account_offline",
                "medium",
                f"账号 {account_id} 自动化未运行",
                "该账号已启用，但当前没有运行中的监听实例，自动回复可能无法生效。",
                "open_account",
                "打开账号",
                cookie_id=account_id,
            ))
        elif account.get("enabled") and not account.get("message_stream_ready"):
            add_action(_action_item(
                "message_stream_disconnected",
                "medium",
                f"账号 {account_id} 消息流未连接",
                "自动回复和在线客服可能无法及时接收新消息。",
                "open_account",
                "打开账号",
                cookie_id=account_id,
            ))

    for session in pending_captcha[:5]:
        add_action(_action_item(
            "captcha_pending",
            "high",
            "存在待处理验证",
            "有滑块、扫码、人脸或短信验证会话尚未完成。",
            "open_risk_logs",
            "查看风控",
            source_id=session.get("session_id"),
        ))

    for failure in recent_failures:
        source = failure.get("source")
        task_type = str(failure.get("task_type") or "")
        if source == "risk_control":
            add_action(_action_item(
                "risk_control_pending",
                "high",
                f"账号 {failure.get('cookie_id') or '-'} 风控待处理",
                f"风控事件 {task_type or 'unknown'} 当前状态为 {failure.get('status') or '-'}。",
                "open_risk_logs",
                "查看风控",
                cookie_id=failure.get("cookie_id") or "",
                source_id=failure.get("id"),
            ))
        elif source == "scheduled_task":
            is_auto_delivery = task_type == "auto_delivery"
            add_action(_action_item(
                "auto_delivery_failed" if is_auto_delivery else "scheduled_task_failed",
                "high" if is_auto_delivery else "medium",
                "自动发货任务失败" if is_auto_delivery else "计划任务执行失败",
                "近期自动发货任务失败，请查看任务日志定位原因。"
                if is_auto_delivery
                else f"近期 {task_type or '任务'} 执行失败，请查看任务日志定位原因。",
                "open_task_logs",
                "查看任务",
                cookie_id=failure.get("cookie_id") or "",
                source_id=failure.get("id"),
            ))

    action_items = action_items[:20]
    offline_count = max(0, enabled_count - online_count)
    health_level = "healthy"
    if action_items:
        health_level = "warning"
    if enabled_count and online_count == 0:
        health_level = "critical"

    return {
        "success": True,
        "generated_at": datetime.now(LOCAL_TIMEZONE).isoformat(),
        "scope": {
            "type": "user" if user_id is not None else "admin",
            "user_id": user_id,
        },
        "summary": {
            "level": health_level,
            "issues": len(action_items),
        },
        "accounts": {
            "total": len(accounts),
            "enabled": enabled_count,
            "online": online_count,
            "offline": offline_count,
            "disabled": disabled_count,
            "items": accounts[:20],
        },
        "credentials": {
            "suspected_expired": suspected_expired_count,
            "token_unready": len([
                account for account in accounts
                if account.get("enabled") and account.get("running") and not account.get("token_ready")
            ]),
            "password_login_ready": len([
                account for account in accounts
                if account.get("enabled") and account.get("has_login_credentials")
            ]),
        },
        "captcha": {
            "active": len(captcha_sessions),
            "pending": len(pending_captcha),
            "sessions": pending_captcha[:10],
        },
        "recent_failures": {
            "count": len(recent_failures),
            "items": recent_failures,
        },
        "action_items": {
            "count": len(action_items),
            "items": action_items,
        },
    }
