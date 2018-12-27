#!/usr/bin/env python

import argparse
import os
import socket
import subprocess
import time

"""This code provides the URL for remotely accessing the cluster's instance of Jupyter notebook."""

__author__ = "Matthew E. Li"
__email__ = "meli@lbl.gov"

HELP_TEXT = "show jupyter output"
HOSTNAME = "localhost"
JUPYTER_CMD = "jupyter notebook --no-browser --ip=\"*\""
MODULE_LOAD_CMD = "module load python/{}".format("3.6")
TIMEOUT = 5
TMP_FILE_PATH = "jupyter.tmp"
URL_PREFIX = "http://{}:".format(HOSTNAME)

def main():
    """Loads Python, launches Jupyter Notebook, and prints the URL for remote access."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbosity", help=HELP_TEXT)
    with open(TMP_FILE_PATH, "w") as tmp_file:
        commands = "; ".join([MODULE_LOAD_CMD, JUPYTER_CMD])
        subprocess.Popen(commands, stdout=tmp_file, stderr=tmp_file, shell=True)
    time.sleep(TIMEOUT)
    with open(TMP_FILE_PATH) as tmp_file:
        for line in tmp_file:
            if parser.parse_args().verbosity:
                print(line)
            line = line.strip()
            if line.find(URL_PREFIX) == 0:
                url = line.replace(HOSTNAME, socket.gethostname(), 1)
                print("Your Jupyter Notebook instance is online at:\n{}".format(url))
                return os.remove(TMP_FILE_PATH)
    print("There was an error starting Jupyter. See {} for details.".format(TMP_FILE_PATH))

if __name__ == "__main__":
    main()
