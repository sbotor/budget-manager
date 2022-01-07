# TODO: maybe create a class

# TODO: comments

import time
import threading
import schedule
import queue

from .models import OperationPlan
from django.utils import timezone

jobqueue = queue.Queue()

def worker_main():
    while True:
        job_func = jobqueue.get()
        job_func()
        jobqueue.task_done()

def plan_operations(thread_count: int = 4):

    qset = OperationPlan.objects.filter(next_date=timezone.now().date())
    for plan in qset.values:
        jobqueue.put(plan.create_operation)
            
    for i in range(thread_count):
        threading.Thread(target=worker_main).start()

def watch(sleep_time: int = 5):
    while True:
        schedule.run_pending()
        time.sleep(sleep_time)

def register_jobs(thread_count: int = 4):

    schedule.every().day.at('00:00').do(jobqueue.put, plan_operations, thread_count)
    
    watcher_thread = threading.Thread(target=watch, args=(5))
    watcher_thread.run()

