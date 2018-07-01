#!/usr/bin/env python3

import argparse
import os
import shlex
import subprocess
import sys
from multiprocessing import Pool

"""This code helps in diagnosing the slowness of currently mounted file systems by running "df -h" 
on paths found in /etc/mtab. If the command hangs for a given file system for longer than some 
timeout, it is possible that the system has issues.

"""

__author__ = "Matthew E. Li"
__email__ = "meli@lbl.gov"

# The default timeout for running "df -h", in seconds.
DF_TIMEOUT = 10
# The path to file in which currently mounted file systems are stored.
ETC_MTAB_PATH = "/etc/mtab"
# Whether or not to print successes.
VERBOSE = False

def check_cmd(command, timeout):
    """Run the given command with the given timeout and return None if it ran successfully and an 
    error message otherwise.

    Keyword Arguments:
    command -- the command to run
    timeout -- the amount of time the command is allowed to run before erroring out
    """
    try:
        subprocess.check_output(shlex.split(command), timeout=timeout)
        return None
    except subprocess.CalledProcessError as e:
        error = "\"{cmd}\" had a bad return code of {ret}.".format(cmd=command, ret=e.returncode)
        raise ValueError(err)
    except subprocess.TimeoutExpired as e:
        error = "\"{cmd}\" exceeded the timeout of {t} seconds.".format(cmd=command, t=timeout)
        raise TimeoutError(error)

def df_status(path):
    """Return the status of running "df -h" on the given path with timeout set to DF_TIMEOUT.

    Keyword Arguments:
    path -- the path to run the command on
    """
    try:
        check_cmd("df -h {path}".format(path=path), DF_TIMEOUT)
        if VERBOSE:
            return "{path}: Success".format(path=path)
    except TimeoutError as e:
        return "{path}: {e}".format(path=path, e=e)
    except ValueError as e:
        return "{path}: {e}".format(path=path, e=e)

def dir_exists(dir_path):
    """Check whether or not the object at the given path is an existing directory.

    Keyword Arguments:
    dir_path -- the path to check
    """
    return os.path.exists(dir_path) and os.path.isdir(dir_path)

def file_exists(file_path):
    """Check whether or not the object at the given path is an existing file.

    Keyword Arguments:
    file_path -- the path to check
    """
    return os.path.exists(file_path) and os.path.isfile(file_path)

def main():
    global DF_TIMEOUT, VERBOSE
    parser = argparse.ArgumentParser(description="Return mounts in /etc/mtab that hang on 'df -h'.")
    parser.add_argument("--timeout", type=int, help="Define a timeout in seconds. Default: 30.")
    parser.add_argument("-v", action="store_true", help="Print successes.")
    args = parser.parse_args()
    if args.timeout is not None:
        DF_TIMEOUT = args.timeout
    VERBOSE = args.v
    if not file_exists(ETC_MTAB_PATH):
        raise FileNotFoundError(ETC_MTAB_PATH)
    paths = set()
    with open(ETC_MTAB_PATH, "r") as mtab_file:
        for line in mtab_file:
            path = line.strip().split(" ")[1]
            if dir_exists(path):
                paths.add(path)
            else:
                print("{path} is not a directory.".format(path=path))
    if bool(paths):
        with Pool(len(paths)) as pool:
            print("\n".join([status for status in pool.map(df_status, paths) if status]))

if __name__ == "__main__":
    main()
