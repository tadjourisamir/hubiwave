from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
import os

from core.scheduler_service import validate_and_schedule_tasks
from core.utils import load_hosts

class SchedulerFileChangeHandler(FileSystemEventHandler):
    def __init__(self, scheduler, callback, debounce_delay=2.0):
        super().__init__()
        self.scheduler = scheduler
        self.callback = callback
        self.last_modified = 0
        self.debounce_delay = debounce_delay
        self.lock = threading.Lock()

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith("scheduled_events.json"):
            return

        now = time.time()
        if now - self.last_modified < self.debounce_delay:
            return

        self.last_modified = now

        if not self.lock.acquire(blocking=False):
            print("⚠️ Rescheduling already in progress — ignored.")
            return

        def refresh():
            try:
                print("🔁 [Watcher] Change detected — rescheduling...")
                hosts = load_hosts()
                validate_and_schedule_tasks(self.scheduler, self.callback, hosts)
            except Exception as e:
                print(f"❌ [Watcher] Failed to reschedule: {e}")
            finally:
                self.lock.release()

        threading.Thread(target=refresh, daemon=True).start()

def start_file_watcher(scheduler, callback, path="modules/scheduler/data"):
    def run():
        observer = Observer()
        handler = SchedulerFileChangeHandler(scheduler, callback)
        observer.schedule(handler, path=path, recursive=False)
        observer.start()
        print("👁️ [Watcher] File watcher started on:", path)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
