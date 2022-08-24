import argparse
import json
import os
import re
import subprocess


"""A script that stores a mapping from LBL employee ID to an object
containing the email and full name of the employee."""


def main():
    args = parse_args()

    employee_ids = load_employee_ids(args.user_data_file)
    mapping = load_initial_mapping(args.mapping_file)

    for employee_id in employee_ids:
        if employee_id not in mapping:
            try:
                user_data = lookup_user_data_for_employee_id(employee_id)
            except Exception as e:
                print(f'Failed to lookup user data for "{employee_id}".')
                continue
            if 'full_name' not in user_data or 'email' not in user_data:
                print(f'Failed to lookup user data for "{employee_id}".')
                continue
            mapping[employee_id] = user_data

    with open(args.mapping_file, 'w') as f:
        json.dump(mapping, f, indent=4)


def load_employee_ids(user_data_file):
    assert os.path.isfile(user_data_file)

    # Each line in the file is colon-separated and should have eight entries.
    # The sixth entry (one-indexed) should be an LBL employee ID.
    num_entries = 8
    employee_id_index = 5
    employee_id_regex = re.compile('^\d{6}$')

    employee_ids = set()
    with open(user_data_file, 'r') as f:
        for line in f:
            line = line.strip()
            fields = [field.strip() for field in line.rstrip().split(':')]
            assert len(fields) == num_entries
            employee_id = fields[employee_id_index]
            if not employee_id_regex.match(employee_id):
                print(f'Invalid employee ID "{employee_id}" in line: "{line}"')
                continue
            employee_ids.add(employee_id)
    return employee_ids


def load_initial_mapping(mapping_file):
    if os.path.exists(mapping_file):
        assert os.path.isfile(mapping_file)
        with open(mapping_file, 'r') as f:
            return json.load(f)
    return {}


def lookup_user_data_for_employee_id(employee_id):
    command = (
        f'ldapsearch -LLL -x -h identity.lbl.gov -b "ou=people,dc=lbl,dc=gov" '
        f'lblempnum={employee_id} cn mail')
    output = subprocess.check_output(command, shell=True)
    # output is a byte string of the form:
    # b'dn: lblEmpNum=123456,ou=People,dc=lbl,dc=gov\ncn: First Middle Last\nmail: EMail@lbl.gov\n\n'
    # The desired return value is {'full_name': 'First Middle Last', 'email': 'email@lbl.gov'}.
    lines = output.decode('utf-8').strip().split('\n')
    user_data = {}
    for line in lines:
        full_name_prefix = 'cn: '
        if line.startswith(full_name_prefix):
            user_data['full_name'] = line[len(full_name_prefix):].strip().title()
            continue
        email_prefix = 'mail: '
        if line.startswith(email_prefix):
            user_data['email'] = line[len(email_prefix):].strip().lower()
            continue
    return user_data


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            'Create a mapping from LBL employee ID to an object containing '
            'the user\'s LBL email address and full name.'))
    parser.add_argument(
        'user_data_file',
        help='The path to the file containing employee IDs.',
        type=str)
    parser.add_argument(
        'mapping_file',
        help=(
            'The path to the JSON file to write the mapping to. If the file '
            'already exists, load in the existing mapping to avoid redundant '
            'lookups.'),
        type=str)
    return parser.parse_args()


if __name__ == '__main__':
    main()
