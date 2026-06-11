from __future__ import annotations

import asyncio
import os
import random
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Tuple

from loguru import logger

from config import config


class TaskRateLimiter:
    ACTION_LABELS = {
        "send_message": "message",
        "publish": "publish",
        "polish": "polish",
        "auto_rate": "auto_rate",
        "red_flower": "red_flower",
        "auto_delivery": "auto_delivery",
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_global_at = 0.0
        self._last_account_at: Dict[str, float] = {}
        self._last_action_account_at: Dict[Tuple[str, str], float] = {}
        self._events_lock = threading.Lock()
        self._recent_events = []

    @staticmethod
    def _normalize_action(action_type: str) -> str:
        action = str(action_type or "").strip().lower()
        return action or "default"

    @staticmethod
    def _normalize_account(account_id: Any) -> str:
        account = str(account_id or "").strip()
        return account or "unknown"

    @staticmethod
    def _env_name(path: str) -> str:
        return path.upper().replace(".", "_")

    @staticmethod
    def _to_bool(value: Any, default: bool = True) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    @staticmethod
    def _to_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _config_bool(self, path: str, default: bool) -> bool:
        env_value = os.getenv(self._env_name(path))
        if env_value is not None:
            return self._to_bool(env_value, default)
        return self._to_bool(config.get(path, default), default)

    def _config_float(self, path: str, default: float) -> float:
        env_value = os.getenv(self._env_name(path))
        if env_value is not None:
            return max(0.0, self._to_float(env_value, default))
        return max(0.0, self._to_float(config.get(path, default), default))

    def is_enabled(self) -> bool:
        risk_safe_default = self._to_bool(config.get("RISK_CONTROL.safe_mode_enabled", True), True)
        return self._config_bool("TASK_RATE_LIMITER.enabled", risk_safe_default)

    def _record_event(self, action: str, account: str, object_key: str, wait_seconds: float) -> None:
        event = {
            "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "label": self.ACTION_LABELS.get(action, action),
            "account": account,
            "object_id": object_key or "-",
            "wait_seconds": round(float(wait_seconds), 1),
        }
        with self._events_lock:
            self._recent_events.insert(0, event)
            self._recent_events = self._recent_events[:50]

    def snapshot(self) -> Dict[str, Any]:
        with self._events_lock:
            recent_events = list(self._recent_events)
        return {
            "enabled": self.is_enabled(),
            "recent_events": recent_events,
        }

    def _action_profile(self, action_type: str) -> Dict[str, float]:
        action = self._normalize_action(action_type)
        risk_global_interval = self._config_float("RISK_CONTROL.global_account_min_interval_seconds", 12)
        global_min_interval = self._config_float("TASK_RATE_LIMITER.global_min_interval_seconds", 3)
        account_min_interval = self._config_float(
            "TASK_RATE_LIMITER.account_min_interval_seconds",
            risk_global_interval,
        )

        order_delay_min = self._config_float(
            "TASK_RATE_LIMITER.order_action_delay_min_seconds",
            self._config_float("RISK_CONTROL.auto_order_action_delay_min_seconds", 15),
        )
        order_delay_max = self._config_float(
            "TASK_RATE_LIMITER.order_action_delay_max_seconds",
            self._config_float("RISK_CONTROL.auto_order_action_delay_max_seconds", 45),
        )

        default_delay_min = 1.0
        default_delay_max = 3.0
        if action == "send_message":
            default_delay_min = self._config_float("TASK_RATE_LIMITER.send_message_delay_min_seconds", 2)
            default_delay_max = self._config_float("TASK_RATE_LIMITER.send_message_delay_max_seconds", 6)
        elif action == "publish":
            default_delay_min = self._config_float(
                "TASK_RATE_LIMITER.publish_delay_min_seconds",
                self._config_float("RISK_CONTROL.publish_action_delay_min_seconds", 30),
            )
            default_delay_max = self._config_float(
                "TASK_RATE_LIMITER.publish_delay_max_seconds",
                self._config_float("RISK_CONTROL.publish_action_delay_max_seconds", 90),
            )
        elif action == "polish":
            default_delay_min = self._config_float(
                "TASK_RATE_LIMITER.polish_delay_min_seconds",
                self._config_float("RISK_CONTROL.item_polish_delay_min_seconds", 20),
            )
            default_delay_max = self._config_float(
                "TASK_RATE_LIMITER.polish_delay_max_seconds",
                self._config_float("RISK_CONTROL.item_polish_delay_max_seconds", 60),
            )
        elif action == "auto_rate":
            default_delay_min = self._config_float("TASK_RATE_LIMITER.auto_rate_delay_min_seconds", order_delay_min)
            default_delay_max = self._config_float("TASK_RATE_LIMITER.auto_rate_delay_max_seconds", order_delay_max)
        elif action == "red_flower":
            default_delay_min = self._config_float("TASK_RATE_LIMITER.red_flower_delay_min_seconds", order_delay_min)
            default_delay_max = self._config_float("TASK_RATE_LIMITER.red_flower_delay_max_seconds", order_delay_max)
        elif action == "auto_delivery":
            default_delay_min = self._config_float("TASK_RATE_LIMITER.auto_delivery_delay_min_seconds", order_delay_min)
            default_delay_max = self._config_float("TASK_RATE_LIMITER.auto_delivery_delay_max_seconds", order_delay_max)

        if default_delay_max < default_delay_min:
            default_delay_max = default_delay_min

        return {
            "global_min_interval": global_min_interval,
            "account_min_interval": account_min_interval,
            "action_min_interval": self._config_float("TASK_RATE_LIMITER.action_min_interval_seconds", 0),
            "delay_min": default_delay_min,
            "delay_max": default_delay_max,
        }

    def _acquire_sync(self, action_type: str, account_id: Any, object_id: Any = "") -> Dict[str, Any]:
        action = self._normalize_action(action_type)
        account = self._normalize_account(account_id)
        object_key = str(object_id or "").strip()
        self._lock.acquire()
        try:
            profile = self._action_profile(action)
            now = time.monotonic()
            earliest_at = max(
                now,
                self._last_global_at + profile["global_min_interval"],
                self._last_account_at.get(account, 0.0) + profile["account_min_interval"],
                self._last_action_account_at.get((action, account), 0.0) + profile["action_min_interval"],
            )
            random_delay = random.uniform(profile["delay_min"], profile["delay_max"]) if profile["delay_max"] > 0 else 0.0
            wait_seconds = max(0.0, earliest_at + random_delay - now)

            if wait_seconds > 0:
                logger.info(
                    f"[task_rate_limiter] queued action={self.ACTION_LABELS.get(action, action)} "
                    f"account={account} object={object_key or '-'} wait={wait_seconds:.1f}s"
                )
                self._record_event(action, account, object_key, wait_seconds)
                time.sleep(wait_seconds)

            started_at = time.monotonic()
            self._last_global_at = started_at
            self._last_account_at[account] = started_at
            self._last_action_account_at[(action, account)] = started_at
            return {
                "enabled": True,
                "acquired": True,
                "action": action,
                "account": account,
                "object_id": object_key,
                "wait_seconds": wait_seconds,
                "started_at": started_at,
            }
        except Exception:
            self._lock.release()
            raise

    async def acquire(self, action_type: str, account_id: Any = "", object_id: Any = "") -> Dict[str, Any]:
        if not self.is_enabled():
            return {
                "enabled": False,
                "acquired": False,
                "action": self._normalize_action(action_type),
                "account": self._normalize_account(account_id),
                "object_id": str(object_id or "").strip(),
                "wait_seconds": 0.0,
            }

        loop = asyncio.get_running_loop()
        acquire_future = loop.run_in_executor(None, self._acquire_sync, action_type, account_id, object_id)
        try:
            return await asyncio.shield(acquire_future)
        except asyncio.CancelledError:
            def release_when_ready(done_future: asyncio.Future) -> None:
                try:
                    state = done_future.result()
                    if state.get("acquired"):
                        self.release(state)
                except Exception as exc:
                    logger.warning(f"[task_rate_limiter] cleanup after cancelled acquire failed: {exc}")

            acquire_future.add_done_callback(release_when_ready)
            raise

    def release(self, state: Dict[str, Any]) -> None:
        if not state or not state.get("acquired"):
            return

        action = self._normalize_action(state.get("action"))
        account = self._normalize_account(state.get("account"))
        finished_at = time.monotonic()
        self._last_global_at = finished_at
        self._last_account_at[account] = finished_at
        self._last_action_account_at[(action, account)] = finished_at
        state["acquired"] = False
        self._lock.release()

    @asynccontextmanager
    async def throttle(self, action_type: str, account_id: Any = "", object_id: Any = "") -> AsyncIterator[Dict[str, Any]]:
        state = await self.acquire(action_type, account_id, object_id)
        try:
            yield state
        finally:
            self.release(state)

    async def wait_for_turn(self, action_type: str, account_id: Any = "", object_id: Any = "") -> Dict[str, Any]:
        async with self.throttle(action_type, account_id, object_id) as state:
            return state


task_rate_limiter = TaskRateLimiter()
