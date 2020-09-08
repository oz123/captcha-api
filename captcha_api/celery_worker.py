import os

from celery.schedules import crontab

from captcha_api.app_factory import celery, create_app
from captcha_api.tasks import delete_old_captchas

app = create_app()


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes every hour the delete old captchas task
    sender.add_periodic_task(
        crontab(hour="*/1"),
        delete_old_captchas.s(),
    )
