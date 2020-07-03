#!/usr/bin/python3

from subprocess import call
import time

if __name__ == "__main__":
    while True:
        call(["python3", "/home/pptruser/.lib/netsniff/netsniff.py"])
        time.sleep(300)
