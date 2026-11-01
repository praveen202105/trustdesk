import time

from .jobs import run_once


def main():
    while True:
        if not run_once():
            time.sleep(0.5)

if __name__ == "__main__":
    main()
