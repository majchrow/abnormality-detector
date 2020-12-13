import asyncio
import sys
import traceback

from ..config import Config


def report(stuff: str):
    sys.stdout.write(stuff + '\n')
    sys.stdout.flush()


async def run(setup, teardown, config):
    worker = await setup(config)

    try:
        await worker.start()
    except Exception as e:
        raise e
    finally:
        await teardown(worker)


def handle_exception(loop, context):
    if e := context.get('exception', None):
        msg = ''.join(traceback.format_tb(e.__traceback__))
    msg += context["message"]

    report('--- ERROR ---')
    report(msg)

    asyncio.create_task(shutdown(loop))


async def shutdown(loop):
    report('Shutdown initiated...')

    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    [task.cancel() for task in tasks]

    report(f"Cancelling {len(tasks)} outstanding tasks...")
    await asyncio.gather(*tasks, return_exceptions=True)
    report('Shutdown complete.')
    loop.stop()


def main(setup, teardown):
    config = Config()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    try:
        loop.create_task(run(setup, teardown, config))
        loop.run_forever()
    finally:
        loop.close()
