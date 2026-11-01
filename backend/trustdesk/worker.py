import time

from sqlalchemy.exc import SQLAlchemyError

from .jobs import run_once


def main():
    print("TrustDesk worker ready; polling durable jobs", flush=True)
    while True:
        try:
            progressed = run_once()
        except SQLAlchemyError:
            print("Worker database temporarily unavailable; retrying safely", flush=True)
            time.sleep(2)
            continue
        if not progressed:
            time.sleep(0.5)


if __name__ == "__main__":
    main()
