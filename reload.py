# reload.py
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import time

class RestartHandler(FileSystemEventHandler):
    def __init__(self, script_path: str):
        self.script_path = script_path
        self.process = self.start_bot()

    def start_bot(self):
        print("🔄 Starting bot...")
        return subprocess.Popen([sys.executable, self.script_path])

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            print("🔁 Change detected, restarting bot...")
            self.process.kill()
            self.process = self.start_bot()

def main():
    script = "main.py"  # your aiogram entry file
    event_handler = RestartHandler(script)
    observer = Observer()
    observer.schedule(event_handler, path=str(Path.cwd()), recursive=True)
    observer.start()

    print("👀 Watching for changes... Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Stopping watcher...")
        observer.stop()
        event_handler.process.kill()

    observer.join()

if __name__ == "__main__":
    main()