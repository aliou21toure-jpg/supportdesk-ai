"""Run the background worker:  python -m app.worker"""

import logging

from rq import Worker

from app.queue import get_queue

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    queue = get_queue()
    Worker([queue], connection=queue.connection).work(with_scheduler=True)
