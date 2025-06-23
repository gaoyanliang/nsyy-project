import asyncio
import threading
import atexit


class GlobalEventLoop:
    _instance = None
    _lock = threading.Lock()
    _loop = None  # 显式声明
    _thread = None  # 显式声明

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._loop = asyncio.new_event_loop()
                cls._thread = threading.Thread(
                    target=cls._run_forever,
                    daemon=True,
                    name="GlobalEventLoopThread"
                )
                cls._thread.start()
                atexit.register(cls.shutdown)
        return cls._instance

    @classmethod
    def _run_forever(cls):
        asyncio.set_event_loop(cls._loop)
        try:
            cls._loop.run_forever()
        finally:
            cls._loop.close()

    def get_loop(self):
        if self.__class__._loop is None:
            raise RuntimeError("Event loop is not initialized")
        return self.__class__._loop

    @classmethod
    def shutdown(cls):
        with cls._lock:  # 加锁保护
            if cls._loop is None:
                return

        loop = cls._loop
        # 1. 取消所有任务
        tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
        for task in tasks:
            task.cancel()

        # 2. 停止事件循环（非阻塞方式）
        if loop.is_running():
            loop.call_soon_threadsafe(loop.stop)

        # 3. 等待线程结束
        if cls._thread and cls._thread.is_alive():
            cls._thread.join(timeout=1.0)

        # 4. 清理资源（仅在循环已停止时）
        if not loop.is_running():
            loop.close()
            cls._loop = None
            cls._thread = None
            cls._instance = None

