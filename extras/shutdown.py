import asyncio
from utils import logger, logInfo


@logger.catch
async def shutdown(signal, loop):
    logInfo(f"收到退出信號 {signal.name}...")

    # close the music player instances
    # mp = MusicPlayer()
    # await mp.shutdown()

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    [task.cancel() for task in tasks]

    logInfo(f"取消 {len(tasks)} 未完成的任務")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
