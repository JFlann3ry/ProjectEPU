import asyncio
import logging

from app.api.billing import _schedule_webhook_task


async def _ok_side_effect():
    return None


async def _failing_side_effect():
    raise RuntimeError("side effect failure")


def test_schedule_webhook_task_success_no_error_log(caplog):
    async def _run():
        _schedule_webhook_task(
            _ok_side_effect(),
            label="ok_email",
            user_id=1,
            reference="sess_ok",
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    with caplog.at_level(logging.ERROR, logger="audit"):
        asyncio.run(_run())

    assert "background task failed" not in caplog.text


def test_schedule_webhook_task_failure_is_logged(caplog):
    async def _run():
        _schedule_webhook_task(
            _failing_side_effect(),
            label="failed_email",
            user_id=2,
            reference="sess_fail",
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    with caplog.at_level(logging.ERROR, logger="audit"):
        asyncio.run(_run())

    assert "background task failed" in caplog.text
    assert "failed_email" in caplog.text
    assert "sess_fail" in caplog.text
