# TODO: comments

import time
import threading
import schedule
import queue

from .models import OperationPlan
from django.utils import timezone


class JobQueue:

    def __init__(self, thread_count: int = 1, sleep_time: int = 5):
        self.thread_count = thread_count
        self.sleep_time = sleep_time

        self._queue = queue.Queue()
        self._watcher_thread = None
        self._threads = None
        self._stop = False

    def _watch(self):
        while not self._stop:
            #print('Watching.')
            schedule.run_pending()
            #print('Sleeping.')
            time.sleep(self.sleep_time)

    def _work(self):
        while not self._stop:
            try:
                job = self._queue.get(block=False)
                job()
                self._queue.task_done()
            except queue.Empty:
                time.sleep(self.sleep_time)

    def start(self):
        self._watcher_thread = threading.Thread(target=self._watch)
        self._watcher_thread.start()

        self._threads = []
        for i in range(self.thread_count):
            t = threading.Thread(target=self._work)
            self._threads.append(t)
            t.start()

    def __del__(self):
        self.stop()

    def stop(self):
        self._stop = True

        #print('Joining watcher thread.')
        if self._watcher_thread is not None and self._watcher_thread.is_alive():
            self._watcher_thread.join()

        #print('Joining worker threads.')
        if self._threads:
            for t in self._threads:
                if t.is_alive():
                    #print(f'Joining {t.getName()}')
                    t.join()
        
        self._watcher_thread = None
        self._threads = None

        


class OperationPlanner(JobQueue):

    def __init__(self, time_str: str = '00:00', thread_count: int = 4, sleep_time: int = 5):
        super().__init__(thread_count, sleep_time)
        self.time_str = time_str

    def _plan_operations(self):
        #print('Planning operations.')
        qset = OperationPlan.objects.filter(
            next_date__gte=timezone.now().date())
        #print(qset)

        if qset.count() == 0:
            return

        for plan in qset.values:
            #print(plan)
            self._queue.put(plan.create_operation)

    def start(self):
        schedule.every().day.at(self.time_str).do(
            self._queue.put, self._plan_operations)

        #print(schedule.get_jobs())

        super().start()
