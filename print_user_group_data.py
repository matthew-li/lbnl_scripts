#!/usr/bin/env python

import operator
import os

"""A script that prints mappings from users to groups and groups to users."""

__author__ = "Matthew E. Li"

GROUP_FILE_PATH = ""
PASSWD_FILE_PATH = ""

def main():
    if not file_exists(GROUP_FILE_PATH):
        print("The group file {} does not exist.".format(GROUP_FILE_PATH))
        return
    if not file_exists(PASSWD_FILE_PATH):
        print("The password file {} does not exist.".format(PASSWD_FILE_PATH))
        return
    group_data = get_group_data(GROUP_FILE_PATH)
    user_data = get_user_data(PASSWD_FILE_PATH)
    user_group_pairs = get_user_group_pairs(user_data, group_data)
    (user_groups, group_users) = get_mappings(group_data, user_data, user_group_pairs)
    print("User Groups:")
    for user_username in user_groups.keys():
        print("{}: {}".format(user_username, ", ".join(user_groups[user_username])))
    print("\nGroup Users:")
    for group_name in group_users.keys():
        print("{}: {}".format(group_name, ", ".join(group_users[group_name])))

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

def get_group_data(group_file_path):
    """Parses the group file at the given path and returns valid group data in a mapping from 
    group_id to (group_id, group_name, group_members). Each line of the group file has 4 entries 
    delimited by ":". The first is the group's name. The second is the letter "x". The third is a 
    non-negative group ID. The fourth is a comma-separated list of usernames of members belonging 
    to the group.

    Keyword Arguments:
    group_file_path -- the path to the group file
    """
    group_data = {}
    if file_exists(group_file_path):
        with open(group_file_path, "r") as group_file:
            for line in group_file:
                fields = [field.strip() for field in line.rstrip().split(":")]
                if len(fields) != 4:
                    print("The group {} does not have 4 fields.".format(fields))
                    continue
                group_name = fields[0].strip()
                if not group_name:
                    print("The group {} is missing a name.".format(fields))
                    continue
                try:
                    group_id = int(fields[2].strip())
                    if group_id < 0:
                        raise ValueError("The group_id {} is invalid.".format(group_id))
                except (TypeError, ValueError) as e:
                    parameters = (fields, group_id)
                    print("The group {} has an invalid group ID: {}.".format(parameters))
                    continue
                group_members = [group_member.strip() for group_member in fields[3].split(",")]
                if not group_members:
                    print("The group {} has no members.".format(fields))
                group_data[group_id] = (group_id, group_name, group_members)
    return group_data

def get_mappings(group_data, user_data, user_group_pairs):
    """Returns a pair of mappings from user usernames to group names and group names to user 
    usernames.

    Keyword Arguments:
    group_data -- group_name --> (group_name, group_id, group_members)
    user_data -- user_id --> (user_id, user_username, user_group_id, user_name, user_email)
    user_group_pairs -- a list of unique pairs of the form (user_id, group_id)
    """
    user_groups = {}
    group_users = {}
    for (user_id, group_id) in user_group_pairs:
        if user_id in user_groups.keys():
            user_groups[user_id].append(group_id)
        else:
            user_groups[user_id] = [group_id]
        if group_id in group_users.keys():
            group_users[group_id].append(user_id)
        else:
            group_users[group_id] = [user_id]
    user_groups_by_name = {}
    for user_id in user_groups:
        user_username = user_data[user_id][1]
        group_names = [group_data[group_id][1] for group_id in user_groups[user_id]]
        user_groups_by_name[user_username] = group_names
    group_users_by_name = {}
    for group_id in group_users:
        group_name = group_data[group_id][1]
        user_usernames = [user_data[user_id][1] for user_id in group_users[group_id]]
        group_users_by_name[group_name] = user_usernames
    return (user_groups_by_name, group_users_by_name)

def get_user_data(password_file_path):
    """Parses the password file at the given path and returns valid user data in a mapping from 
    user_id to (user_id, user_username, user_group_id, user_name, user_email). Each line of 
    the password file has 7 entries delimited by ":". The first is the user's username. The second 
    is the letter "x". The third is a non-negative user ID. The fourth is a non-negative group ID. 
    The fifth is a comma-separated pair containing the user's name and e-mail. The sixth is the 
    user's home directory. The seventh determines whether or not a user can log in.

    Keyword Arguments:
    password_file_path -- the path to the password file
    """
    user_data = {}
    if file_exists(password_file_path):
        with open(password_file_path, "r") as password_file:
            for line in password_file:
                fields = [field.strip() for field in line.rstrip().split(":")]
                if len(fields) != 7:
                    print("The user {} does not have 7 fields.".format(fields))
                    continue
                user_username = fields[0].strip()
                if not user_username:
                    print("The user {} is missing a username.".format(fields))
                    continue
                try:
                    user_id = int(fields[2].strip())
                    if user_id < 0:
                        raise ValueError("The user_id {} is invalid.".format(user_id))
                except (TypeError, ValueError) as e:
                    parameters = (fields, user_id)
                    print("The user {} has an invalid user ID: {}.".format(parameters))
                    continue
                try:
                    user_group_id = int(fields[3].strip())
                    if user_group_id < 0:
                        raise ValueError("The user_group_id {} is invalid.".format(user_group_id))
                except (TypeError, ValueError) as e:
                    print("The user {} has an invalid group ID.".format(fields))
                    continue
                user_name_email_pair = fields[4].strip()
                if not user_name_email_pair or "," not in user_name_email_pair:
                    print("The user {} has an invalid (name, email) pair.".format(fields))
                    continue
                (user_name, user_email) = user_name_email_pair.split(",")[:2]
                user_data[user_id] = (user_id, user_username, user_group_id, user_name, user_email)
    return user_data

def get_user_group_pairs(user_data, group_data):
    """Returns a list of unique pairs of the form (user_id, group_id), sorted first by user_id and 
    then by group_id. The subset of the list relating to a given user is comprised of the user's 
    user_group_id and the group_ids for groups having the user for a member.

    Keyword Arguments:
    user_data -- user_id --> (user_id, user_username, user_group_id, user_name, user_email)
    group_data -- group_name --> (group_name, group_id, group_members)
    """
    user_group_pairs = set()
    for user_username in user_data.keys():
        (user_id, user_username, user_group_id, user_name, user_email) = user_data[user_username]
        user_group_pairs.add((user_id, user_group_id))
        for group_name in group_data.keys():
            (group_id, group_name, group_members) = group_data[group_name]
            if user_username in group_members:
                user_group_pairs.add((user_id, group_id))
    return sorted(list(user_group_pairs), key=operator.itemgetter(0, 1))
