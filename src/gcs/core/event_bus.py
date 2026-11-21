import logging
import queue
import threading

log = logging.getLogger(__name__)

class EventBus:
    def __init__(self,queue_size=1000):
        self.subscribers={}
        self._queue = queue.Queue(maxsize=queue_size)
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    def subscribe(self,event_name,callback):
        with self._lock:
            self.subscribers.setdefault(event_name,[]).append(callback)

    def unsubscribe(self, event_name, callback):
        with self._lock:
            callbacks = self.subscribers.get(event_name, [])
            if callback in callbacks:
                callbacks.remove(callback)

    def publish(self, event_name, data=None):
        try:
            self._queue.put_nowait((event_name, data))
        except queue.Full:
            log.warning("bus queue full, dropped event %s", event_name)

    def start(self):
        self._thread = threading.Thread(target=self._run, name="bus", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self):
        while not self._stop.is_set():
            try:
                event_name, data = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            with self._lock:
                callbacks = list(self.subscribers.get(event_name, []))
            for callback in callbacks:
                try:
                    callback(data)
                except Exception:
                    log.exception("subscriber failed for %s", event_name)
