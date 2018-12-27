#!/usr/bin/env python

import fileinput
import os
import re
import sys

"""This code adds an entry to various locations in a configuration file. Currently, the clusters 
entries are added to are: lawrencium, lr2, lr3, lr4, lr5, lr_amd, lr_bigmem, lr_manycore, mako, 
mako_manycore, cf1, and lrc.

Entries are added to the end of each cluster, generating a new ID, incremented from the previously 
highest ID.

"""

__author__ = "Matthew E. Li"

# A list of the clusters to which entries should be added, in the order that they appear.
CLUSTERS = ("[lawrencium]", "[lr2]", "[lr3]", "[lr4]", "[lr5]", "[lr_amd]", "[lr_bigmem]", 
            "[lr_manycore]", "[mako]", "[mako_manycore]", "[cf1]", "[lrc]")
# The cost for each project prefix.
PREFIX_COSTS = {
    "ac_": "1.0",
    "lr_": "0.0",
    "pc_": "0.0"
}
# A common string to be matched against.
ACCOUNT = "account_"
# A match for a string that begins with "account_", has 3-4 digits, "=", and one of the prefixes.
LRC_PATTERN = ACCOUNT + "\d{3,4}=" + "(" + "|".join(PREFIX_COSTS.keys()) + ").*?"
# A dictionary of possible error messages.
ERROR_MESSAGES = {
    "ACCOUNT_ID_INVALID": lambda x: "ERROR: An entry with account ID == " + str(x) + " and not " + 
                                    "beginning with one of " + ", ".join(PREFIX_COSTS.keys()) + 
                                    "already exists in at least one of the clusters, so parts " + 
                                    "of the file may not have been updated.",
    "ACCOUNT_ID_ORDER": lambda x: "ERROR: An ordering issue arose when attempting to add " + 
                                  str(x) + ", so parts of the file may not have been updated.",
    "ACCOUNT_ID_VALID": lambda x: "ERROR: An entry with account ID >= " + str(x) + " and " + 
                                  "beginning with one of " + ", ".join(PREFIX_COSTS.keys()) + 
                                  "already exists in at least one of the clusters, so parts of " + 
                                  "the file may not have been updated.",
    "EXISTENCE": lambda x: "ERROR: Cannot open " + str(x) + "."
}

def add_entry(config_path, entry):
    """Add an entry with the given parameters to the designated clusters in the configuration 
    file, modifying it in place.

    Keyword Arguments:
    entry -- the string to be added to each cluster
    """
    new_account_id = get_account_id(entry)
    if file_exists(config_path) and new_account_id:
        # Whether or not the current line is under a cluster; set to False when an entry is added.
        in_cluster = False
        # The previous line, used for inserting entries before entries without a valid prefix.
        prev_line = None
        # A list of errors, causing the file's original contents to be written back when not empty.
        errors = []
        for line in fileinput.input(config_path, inplace=True, mode="r"):
            # Standard output is redirected to the input file.
            stripped_line = line.rstrip().strip()
            if errors:
                # Write the line back as it was.
                print(stripped_line)
                continue
            if in_cluster:
                if stripped_line:
                    # The line is not empty.
                    entry_account_id = get_account_id(stripped_line)
                    id_difference = int(entry_account_id) - int(new_account_id)
                    if re.search(re.compile(LRC_PATTERN), stripped_line):
                        # The line is valid, so its account ID should be strictly smaller.
                        if id_difference >= 0:
                            errors.append(ERROR_MESSAGES["ACCOUNT_ID_VALID"](new_account_id))
                    else:
                        # The line is not valid, so its account ID can be greater, but not equal.
                        if id_difference == 0:
                            errors.append(ERROR_MESSAGES["ACCOUNT_ID_INVALID"](new_account_id))
                        elif id_difference > 0:
                            # If the previous line is also not valid, error out. Remove this check 
                            # to be able to insert valid entries after invalid ones.
                            if not re.search(re.compile(LRC_PATTERN), prev_line):
                                errors.append(ERROR_MESSAGES["ACCOUNT_ID_ORDER"](new_account_id))
                            else:
                                # Insert the new entry between the two.
                                print(entry)
                                in_cluster = False
                    # Always write the line back, whether or not insertion or errors, occur.
                    print(stripped_line)
                else:
                    # If the entry has not been added by the end of the cluster, add it now.
                    print(entry + "\n")
                    in_cluster = False
                prev_line = stripped_line
            else:
                if stripped_line in CLUSTERS:
                    in_cluster = True
                    prev_line = stripped_line
                # Write the original line back to the file.
                print(stripped_line)
        # Print errors to the actual standard output.
        for error in errors:
            print(error)

def entry_str(account_id, project_name, project_id, pi_dept, pi_name, pi_email, pi_id, cost):
    """Return the string to be added to the configuration file for a given new account.

    Keyword Arguments:
    account_id -- the account ID of the project
    project_name -- the name of the project
    project_id -- the ID of the project
    pi_dept -- the department under which the project is run
    pi_name -- the name of the PI
    pi_email -- the e-mail address of the PI
    pi_id -- the employee ID of the PI
    cost -- the cost for use of resources
    """
    return (ACCOUNT + str(account_id) + "=" + str(project_name) + ":" + str(project_id) + ":" + 
           str(pi_dept) + ":" + str(pi_name) + " <" + str(pi_email) + ">:" + str(pi_id) + "::" + 
           str(cost))

def file_exists(file_path):
    """Check whether or not the object at the given path is an existing file.

    Keyword Arguments:
    file_path -- the path to check
    """
    return os.path.exists(file_path) and os.path.isfile(file_path)

def generate_new_account_id(config_path):
    """Return a new account ID, in string format, to be added to the configuration file, 
    determined by the entires already existing in the first cluster.

    Keyword Arguments:
    config_path -- the path to the configuration file
    """
    if file_exists(config_path):
        with open(config_path, "r") as config_file:
            in_cluster = False
            prev_line = None
            for line in config_file:
                stripped_line = line.rstrip().strip()
                if in_cluster:
                    if not stripped_line:
                        break
                    else:
                        if re.search(re.compile(LRC_PATTERN), stripped_line):
                            prev_line = stripped_line
                else:
                    if stripped_line == CLUSTERS[0]:
                        in_cluster = True
                        prev_line = stripped_line
            return increment_account_id(get_account_id(prev_line))
    return None

def get_account_id(entry):
    """Return the account_id of the given entry or None if the string is not valid.

    Keyword Arguments:
    entry -- a string whose account_id is being retrieved
    """
    start = entry.find("_")
    end = entry.find("=")
    if not bool(start and end):
        return None
    return entry[start + 1:end]

def get_project_prefix(project_name):
    """Return the project prefix for the given project name, or None if the name does not begin 
    with a valid prefix.

    Keyword Arguments:
    project_name -- the name of the project to check
    """
    for prefix in PREFIX_COSTS.keys():
        if project_name.startswith(prefix):
            return prefix
    return None

def increment_account_id(account_id):
    """Return the given account ID plus one in string format, with the leading zeroes preserved.

    Keyword Arguments:
    account_id -- the account ID to increment
    """
    return str(int(account_id) + 1).zfill(len(account_id))

def usage():
    """Usage."""
    print("Usage: python add_account.py config_path project_name project_id pi_dept pi_name " + 
          "pi_email pi_id")
    print("project_name must begin with one of: " + ", ".join(PREFIX_COSTS.keys()) + ".")
    print("Use quotes to enclose multi-word arguments.")

def main():
    """Add a new entry to the configuration file."""
    args = sys.argv[1:]
    if len(args) != 7:
        usage()
        return
    config_path = args[0].strip()
    if file_exists(config_path):
        project_name = args[1].strip()
        project_prefix = get_project_prefix(project_name)
        if not project_prefix:
            usage()
            return
        project_id = args[2].strip()
        pi_dept = args[3].strip()
        pi_name = args[4].strip()
        pi_email = args[5].strip()
        pi_id = args[6].strip()
        cost = PREFIX_COSTS[project_prefix]
        account_id = generate_new_account_id(config_path)
        add_entry(config_path, entry_str(account_id, project_name, project_id, pi_dept, pi_name, 
                                         pi_email, pi_id, cost))
    else:
        print(ERROR_MESSAGES["EXISTENCE"](config_path))
        return

if __name__ == "__main__":
    main()
