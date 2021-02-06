#!/usr/bin/env python

from jira import JIRA
import yaml
from datetime import datetime as dt
import numpy as np
import math


def config_reader(yaml_file):
    """Open the yaml file with all config and return as a dictionary"""
    with open(yaml_file) as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def atlassian_auth(cfg):
    """Authenticate on the Jira Cloud instance"""
    jira = JIRA(
        server=cfg['Connection']['Domain'],
        basic_auth=(cfg['Connection']['Username'], cfg['Connection']['ApiKey'])
    )
    return jira


def jql_search(jira_obj):
    """Run a JQL search and return the jira object with results"""
    issues = jira.search_issues(config['Query'], maxResults=9999, expand='changelog')
    return issues


def convert_cfd_table(issues_obj, jira_obj, cfg):
    """Convert the issues obj into a dictionary on the cfd format"""
    cfd_table = []
    for issue in issues_obj:
        # start creating our line of the table with field: value
        cfd_line = {}
        cfd_line["issue"] = issue.key
        cfd_line["issuetype"] = issue.fields.issuetype.name
        cfd_line["cycletime"] = 0
        cfd_line["final_datetime"] = 0

        # create other columns according to workflow in cfg
        for line_item in cfg['Workflow']:
            cfd_line[line_item.lower()] = 0
        # store final status
        final_status = list(cfg['Workflow'])[-1].lower()

        # create a mini dict to organize itens (issue_time, history_time, from_status, to_status)
        status_table = []
        for history in issue.changelog.histories:
            for item in history.items:
                # only items that are status change are important to us
                if item.field == 'status':
                    status_line = {}
                    status_line["history_datetime"] = history.created
                    status_line["from_status"] = item.fromString.lower()
                    status_line["to_status"] = item.toString.lower()
                    status_table.append(status_line)
                    # store in finaldatetime the highest timestamp to fix items with many 'done' transitions
                    if item.toString.lower() == final_status and convert_jira_datetime(history.created) > cfd_line["final_datetime"]:
                        cfd_line["final_datetime"] = convert_jira_datetime(history.created)

        # send the mini dict to be processed and return the workflow times
        cfd_line = process_status_table(status_table, cfd_line, cfg)
        # adding a special case: time on the first status should be compared to when the issue was created
        # it is always the last line of the status table
        cfd_line[status_table[-1]['from_status']] = calc_diff_date_to_unix(issue.fields.created, status_table[-1]['history_datetime'])
        # add line to table
        cfd_table.append(cfd_line)

    return cfd_table


def process_status_table(status_table, cfd_line, cfg):
    # everytime that I have fromString(enddatetime) I should find a toString(startdatetime)
    for item1 in status_table:
        for item2 in status_table:
            if item2['to_status'] == item1['from_status']:
                # send to calc
                # add the time to the column corresponding the enddatetime
                cfd_line[item1['from_status']] += calc_diff_date_to_unix(item2['history_datetime'], item1['history_datetime'])

                # lowercase cfg to match lowercase status keys
                dict_lower = {k.lower(): v.lower() for k, v in cfg['Cycletime'].items()}
                # add to cycletime if field set on config
                if item1['from_status'] in dict_lower:
                    cfd_line["cycletime"] += cfd_line[item1['from_status']]

    return cfd_line


def calc_diff_date_to_unix(start_datetime, end_datetime):
    """Given the start and end datetime return the difference in unix timestamp format"""
    start = convert_jira_datetime(start_datetime)
    end = convert_jira_datetime(end_datetime)
    timedelta = end - start
    minutes = math.ceil(timedelta/60)
    return minutes

def convert_jira_datetime(datetime_str):
    """Convert Jira datetime format to unix timestamp"""
    time = dt.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f%z')
    return dt.timestamp(time)


def calc_cycletime_percentile(dictio, cfg):
    """Calculate cycletime percentiles on cfg with all dict entries"""
    # auxiliary dict with the colums that should be added to cycletime calc
    cycletime = []
    for entry in dictio:
        cycletime.append(entry['cycletime'])

    if len(dictio) >= 1 and len(cycletime) >= 1:
        print("Your throughput is of {} items".format(len(dictio)))
        for percentile in cfg['Percentiles']:
            minutes = np.percentile(cycletime, percentile)
            minutes_in_day = 60 * 24
            minutes_in_hour = 60

            days = math.ceil(minutes // minutes_in_day)
            hours = math.ceil((minutes - (days * minutes_in_day)) // minutes_in_hour)
            minutes = math.ceil((minutes - (days * minutes_in_day) - (hours * minutes_in_hour)))

            print("Cycletime Percentile of {}% is {} days {} hours {} minutes".format(percentile, days, hours, minutes))
    else:
        print("No items from query or to calculate percentiles")


if __name__ == "__main__":
    yaml_file = "config_test.yml"
    config = config_reader(yaml_file)
    jira = atlassian_auth(config)
    issue = jql_search(jira)
    dictio = convert_cfd_table(issue, jira, config)
    # print(dictio)
    calc_cycletime_percentile(dictio, config)
