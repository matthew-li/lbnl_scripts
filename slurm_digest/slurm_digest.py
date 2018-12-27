#!/usr/bin/env python

import os
import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from lxml import etree, html

"""This code condenses SLURM changes, stored in a change file, into an e-mail digest."""

__author__ = "Matthew E. Li"
__email__ = "meli@lbl.gov"

# The path to the change file.
CHANGE_FILE = "~/Desktop/slurm/digest/change_file"
# A dictionary of indices into each line of the change file for each entry.
FIELDS = {
    "NOTIFICATION TYPE": 0,
    "SERVICE": 1,
    "HOST": 2,
    "ADDRESS": 3,
    "STATE": 4,
    "DATE/TIME": 5,
    "ADDITIONAL INFO": 6
}
# A regex expression that compute nodes conform to.
COMPUTE_PATTERN = "n0\d\d\d.[a-z0-9]+$"
# The number of digits in a node number.
NODE_NUM_DIGITS = 4
# A dictionary of SLURM categories.
SLURM_CATEGORIES = {
    "HW": "Hardware",
    "NHC": "NHC",
    "SW": "Software"
}

def digest_slurm_problems_html(slurm_rows):
    """Return email digest text regarding SLURM problems, formatted in HTML.

    Keyword Arguments:
    slurm_rows -- rows with SLURM problems
    """
    html = "<h2>SLURM Problems</h2>"
    html += "<table border=\"1\">"
    for category in slurm_rows.keys():
        html += "<tr>"
        slurm_category_rows = slurm_rows[category]
        if category in SLURM_CATEGORIES.keys():
            html += "<th colspan=\"2\">" + SLURM_CATEGORIES[category] + " Issues</th>"
        else:
            html += "<th colspan=\"2\">Other Issues</th>"
        html += "</tr>"
        reasons = get_rows_by_slurm_reason(slurm_category_rows)
        for reason in sorted(reasons.keys(), key=lambda x: x.lower()):
            html += "<tr>"
            html += "<td><b>" + reason + "</b></td>"
            clusters = get_nodes_by_cluster(reasons[reason])
            html += "<td>"
            for cluster in sorted(clusters.keys()):
                html += "<b>" + cluster + "</b>" + ": " + get_node_list_string(clusters[cluster])
                html += "<br>"
            html += "</td>"
            html += "</tr>"
    html += "</table>"
    return html

def digest_slurm_problems_text(slurm_rows):
    """Return email digest text regarding SLURM problems, in plaintext.

    Keyword Arguments:
    slurm_rows -- rows with SLURM problems
    """
    text = "\nSLURM Problems\n"
    for category in slurm_rows.keys():
        slurm_category_rows = slurm_rows[category]
        if category in SLURM_CATEGORIES.keys():
            text += "\n\t" + SLURM_CATEGORIES[category] + " Issues\n"
        else:
            text += "\tOther Issues\n"
        reasons = get_rows_by_slurm_reason(slurm_category_rows)
        for reason in sorted(reasons.keys(), key=lambda x: x.lower()):
            text += "\t\t" + reason + "\n"
            clusters = get_nodes_by_cluster(reasons[reason])
            for cluster in sorted(clusters.keys()):
                text += "\t\t\t" + cluster + ": " + get_node_list_string(clusters[cluster])
                text += "\n"
    return text

def get_digest_html(problem_rows, recovery_rows, other_rows):
    """Return the text of the email digest for the various notification types, formatted with HTML.

    Keyword Arguments:
    problem_rows -- input data, where each row represents a problem
    recovery_rows -- input data, where each row represents a recovery
    other_rows -- input data, where each row represents some other change
    """
    headers = FIELDS.keys()
    phrases = [" new problems:", " new recoveries:", " other new changes:"]
    html = "<html>"
    html += "<head></head>"
    html += "<body>"
    html += "<h1>SLURM Digest</h1>"
    html += "<hr>"
    service_rows = get_rows_by_service(problem_rows)
    slurm_rows = get_rows_by_slurm_category(service_rows["SLURM"])
    html += digest_slurm_problems_html(slurm_rows)
    html += "<hr>"
    html += "<h2>Raw Output</h2>"
    i = 0
    for notification_type in [problem_rows, recovery_rows, other_rows]:
        html += "<p>There are " + str(len(notification_type)) + phrases[i] + "</p>"
        html += "<table>"
        html += "<tr>"
        for header in headers:
            html += "<th>" + header + "</th>"
        html += "</tr>"
        for line in notification_type:
            html += "<tr>"
            for j in range(len(headers)):
                html += "<td>" + line[j] + "</td>"
            html += "</tr>"
        html += "</table>"
        i += 1
    html += "</body>"
    html += "</html>"
    return prettify_html(html)

def get_digest_text(problem_rows, recovery_rows, other_rows):
    """Return the text of the email digest for the various notification types, in plaintext.

    Keyword Arguments:
    problem_rows -- input data, where each row represents a problem
    recovery_rows -- input data, where each row represents a recovery
    other_rows -- input data, where each row represents some other change
    """
    headers = FIELDS.keys()
    phrases = [" new problems:", " new recoveries:", " other new changes:"]
    text = "SLURM Digest\n"
    service_rows = get_rows_by_service(problem_rows)
    slurm_rows = get_rows_by_slurm_category(service_rows["SLURM"])
    text += digest_slurm_problems_text(slurm_rows)
    text += "\nRaw Output\n"
    i = 0
    for notification_type in [problem_rows, recovery_rows, other_rows]:
        text += "\nThere are " + str(len(notification_type)) + phrases[i] + "\n"
        text += ", ".join(headers) + "\n"
        for line in notification_type:
            text += ", ".join(line) + "\n"
        i += 1
    return text

def file_exists(file_path):
    """Check whether or not the object at the given path is an existing file.

    Keyword Arguments:
    file_path -- the path to check
    """
    return os.path.exists(file_path) and os.path.isfile(file_path)

def get_nodes_by_cluster(rows):
    """Return a dictionary mapping from cluster name to a list of integer node numbers.

    Keyword Arguments:
    rows -- input data, where one of the columns pertains to a host name with number and cluster
    """
    cluster_nodes = {}
    for row in rows:
        host = row[FIELDS["HOST"]]
        if re.search(re.compile(COMPUTE_PATTERN), host):
            number, cluster = [field.strip() for field in host.split(".")]
            integer = int(number[1:])
            if cluster not in cluster_nodes.keys():
                cluster_nodes[cluster] = []
            cluster_nodes[cluster].append(integer)
    return cluster_nodes

def get_node_list_string(node_list):
    """Return a list of integer node numbers as a comma-separated string, with consecutive nodes 
    condensed to a single entry with " - " separating the start and end of the range of nodes.

    Keyword Arguments:
    node_list -- a list of integer node numbers
    """

    def get_consecutive_string(consecutive):
        """Get the string representation of the consecutive tuple.

        Keyword Arguments:
        consecutive -- a tuple of the form (start, end)
        """
        str_form = lambda number: "n" + str(number).zfill(NODE_NUM_DIGITS)
        if consecutive[0] == consecutive[1]:
            return str_form(consecutive[0])
        else:
            return "-".join([str_form(consecutive[0]), str_form(consecutive[1])])

    node_list_entries = []
    node_list = sorted(list(set(node_list)))
    consecutive = ()
    for node_number in node_list:
        if not consecutive:
            consecutive = (node_number, node_number)
        elif node_number == consecutive[1] + 1:
            consecutive = (consecutive[0], node_number)
        else:
            node_list_entries.append(get_consecutive_string(consecutive))
            consecutive = (node_number, node_number)
    node_list_entries.append(get_consecutive_string(consecutive))
    return ", ".join(node_list_entries)

def get_rows_by_host_type(rows):
    """Return a dictionary containing two subsets of the given rows, where each contains rows 
    with host type conforming to the COMPUTE_PATTERN or to something else.

    Keyword Arguments:
    rows -- input data, where one of the columns pertains to the host
    """
    compute, other = ([] for i in range(2))
    for row in rows:
        if re.search(re.compile(COMPUTE_PATTERN), row[FIELDS["HOST"]]):
            compute.append(row)
        else:
            other.append(row)
    return {"COMPUTE": compute, "OTHER": other}

def get_rows_by_notification_type(rows):
    """Return a dictionary containing three subsets of the given rows, where each contains rows 
    with notification type "PROBLEM", "RECOVERY", or something else.

    Keyword Arguments:
    rows -- input data, where one of the columns pertains to the notification type
    """
    problem, recovery, other = ([] for i in range(3))
    for row in rows:
        notification_type = row[FIELDS["NOTIFICATION TYPE"]]
        if notification_type == "PROBLEM":
            problem.append(row)
        elif notification_type == "RECOVERY":
            recovery.append(row)
        else:
            other.append(row)
    return {"PROBLEM": problem, "RECOVERY": recovery, "OTHER": other}

def get_rows_by_service(rows):
    """Return a dictionary containing two subsets of the given rows, where each contains rows with 
    service "SLURM" or something else.

    Keyword Arguments:
    rows -- input data, where one of the columns pertains to the service
    """
    slurm, other = ([] for i in range(2))
    for row in rows:
        service = row[FIELDS["SERVICE"]]
        if service == "SLURM":
            slurm.append(row)
        else:
            other.append(row)
    return {"SLURM": slurm, "OTHER": other}

def get_rows_by_slurm_category(rows):
    """Return a dictionary containing four subsets of the given rows of the "SLURM" service, where 
    each contains rows with additional information that begins with "Hardware", "NHC", "Software", 
    or something else.

    Keyword Arguments:
    rows -- input data, where one of the columns pertains to the service and another to the info
    """
    hardware, nhc, software, other = ([] for i in range(4))
    for row in rows:
        if row[FIELDS["SERVICE"]] == "SLURM":
            additional_info = row[FIELDS["ADDITIONAL INFO"]]
            if additional_info.startswith(SLURM_CATEGORIES["HW"] + ":"):
                hardware.append(row)
            elif additional_info.startswith(SLURM_CATEGORIES["NHC"] + ":"):
                nhc.append(row)
            elif additional_info.startswith(SLURM_CATEGORIES["SW"] + ":"):
                software.append(row)
            else:
                other.append(row)
    return {"HW": hardware, "NHC": nhc, "SW": software, "OTHER": other}

def get_rows_by_slurm_reason(rows):
    """Return a dictionary containing some number of subsets of the given rows of the "SLURM" 
    service, where each contains rows with additional information that ends with the same reason.

    Keyword Arguments:
    rows -- input data, where one of the columns pertains to the service and another to the info
    """
    reasons = {}
    for row in rows:
        if row[FIELDS["SERVICE"]] == "SLURM":
            additional_info = row[FIELDS["ADDITIONAL INFO"]]
            if (additional_info.startswith((SLURM_CATEGORIES["HW"] + ":", 
                                            SLURM_CATEGORIES["NHC"] + ":", 
                                            SLURM_CATEGORIES["SW"] + ":"))):
                reason = additional_info[additional_info.find(":") + 1:].strip()
            else:
                reason = additional_info.strip()
            reason = " ".join(reason.split())
            if reason.lower() not in reasons.keys():
                reasons[reason.lower()] = []
            reasons[reason.lower()].append((reason, row))
    output_reasons = {}
    for reason in reasons.keys():
        pairs = reasons[reason]
        new_key = pairs[0][0]
        if new_key not in output_reasons.keys():
            output_reasons[new_key] = []
        for pair in pairs:
            output_reasons[new_key].append(pair[1])
    return output_reasons

def parse_change_file(file_path, delimeter):
    """Parse the file, assuming that it exists, at the given path line-by-line, where fields in 
    each line are delimited by the given delimeter, into a matrix where the columns correspond to 
    the fields in the global variable FIELDS.

    Keyword Arguments:
    file_path -- the path at which the file is located
    """
    parsed_file = []
    with open(file_path, "r") as change_file:
        for line in change_file:
            parsed_line = []
            field_values = line.split(delimeter)
            for field in FIELDS.keys():
                parsed_line.append(field_values[FIELDS[field]].strip())
            parsed_file.append(parsed_line)
    return parsed_file

def prettify_html(html_string):
    """Return a properly indented version of the given HTML string.

    Keyword Arguments:
    html_string -- the html to format
    """
    return etree.tostring(html.fromstring(html_string), encoding="unicode", pretty_print=True)

def send_email_html(host, subject, sender, recipients, html, text):
    """Send an e-mail with the given parameters, formatted with HTML and with an alternative 
    plaintext version.

    Keyword Arguments:
    host -- the SMTP server to use
    subject -- the subject line of the e-mail
    sender -- the sending e-mail address
    recipients -- the receiving e-mail addresses
    html -- the content of the e-mail, in HTML format
    text -- the content of the e-mail, in plaintext format
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    s = smtplib.SMTP(host)
    s.sendmail(sender, recipients, msg.as_string())
    s.quit()

def send_email_text(host, subject, sender, recipients, text):
    """Send a plaintext e-mail with the given parameters.

    Keyword Arguments:
    host -- the SMTP server to use
    subject -- the subject line of the e-mail
    sender -- the sending e-mail address
    recipients -- the receiving e-mail addresses
    text -- the text of the e-mail
    """
    msg = MIMEText(text)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    s = smtplib.SMTP(host)
    s.sendmail(sender, recipients, msg.as_string())
    s.quit()

def main():
    """Send an e-mail digest from the change file."""
    if not file_exists(CHANGE_FILE):
        print("Cannot read " + CHANGE_FILE + ".")
        sys.exit(0)
    elif os.path.getsize(CHANGE_FILE) == 0:
        print("No changes in " + CHANGE_FILE + ".")
        sys.exit(0)
    parsed_file = parse_change_file(CHANGE_FILE, ",")
    host_type_rows = get_rows_by_host_type(parsed_file)
    notification_type_rows = get_rows_by_notification_type(host_type_rows["COMPUTE"])
    problem_rows = notification_type_rows["PROBLEM"]
    recovery_rows = notification_type_rows["RECOVERY"]
    other_rows = notification_type_rows["OTHER"]
    email_html = get_digest_html(problem_rows, recovery_rows, other_rows)
    email_text = get_digest_text(problem_rows, recovery_rows, other_rows)
    send_email_html("smtp.lbl.gov", "SLURM Digest", "meli@lbl.gov", ["meli@lbl.gov"], 
                    email_html, email_text)
    open(CHANGE_FILE, "w").close()

if __name__ == "__main__":
    main()
