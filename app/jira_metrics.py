#!/usr/bin/env python

import confuse
from jira import JIRA
from datetime import datetime as dt
import numpy as np
import math
import pandas as pd

cfg = confuse.Configuration('JiraMetrics', __name__)
cfg.set_file('config_test.yml')


def atlassian_auth():
    """Authenticate on the Jira Cloud instance"""
    username = cfg['Connection']['Username'].get()
    api = cfg['Connection']['ApiKey'].get()

    jira = JIRA(
        server=cfg['Connection']['Domain'].get(),
        basic_auth=(username, api)
    )
    return jira


def jql_search(jira_obj):
    """Run a JQL search and return the jira object with results"""
    sfields = [
        "created",
        "issuetype"
    ]
    issues = jira.search_issues(
        cfg['Query'].get(),
        fields=sfields,
        maxResults=99999,
        expand='changelog'
    )
    return issues


def convert_cfd_table(issues_obj):
    """Convert the issues obj into a dictionary on the cfd format"""
    cfd_table = []
    for issue in issues_obj:
        # start creating our line of the table with field: value
        cfd_line = {}
        cfd_line["issue"] = issue.key
        cfd_line["issuetype"] = group_issuetype(issue.fields.issuetype.name)
        cfd_line["cycletime"] = 0
        cfd_line["final_datetime"] = 0

        # create other columns according to workflow in cfg
        workflows = cfg['Workflow'].get()
        for key, value in workflows.items():
            cfd_line[key.lower()] = 0

        # store final status
        fstatus = list(cfd_line.keys())[-1]

        # create a mini dict to organize itens
        # (issue_time, history_time, from_status, to_status)
        status_table = []
        for history in issue.changelog.histories:
            for item in history.items:
                # only items that are status change are important to us
                if item.field == 'status':
                    status_line = {}
                    status_line["history_datetime"] = history.created
                    status_line["from_status"] = group_status(item.fromString)
                    status_line["to_status"] = group_status(item.toString)
                    status_table.append(status_line)
                    # store in finaldatetime the highest timestamp to fix
                    # items with many 'done' transitions
                    stamp_created = convert_jira_datetime(history.created)
                    if (group_status(item.toString) == fstatus and
                            stamp_created > cfd_line["final_datetime"]):
                        cfd_line["final_datetime"] = stamp_created

        # send the mini dict to be processed and return the workflow times
        cfd_line = process_status_table(status_table, cfd_line)
        # special case: time on the first status should be compared to when
        # the issue was created it is always the last line of the status table
        cfd_line[status_table[-1]['from_status']] = calc_diff_date_to_unix(
            issue.fields.created,
            status_table[-1]['history_datetime']
        )
        # add line to table
        cfd_table.append(cfd_line)

    return cfd_table


def process_status_table(status_table, cfd_line):
    # everytime that I have fromString(enddatetime)
    # I should find a toString(startdatetime)
    for item1 in status_table:
        for item2 in status_table:
            if item2['to_status'] == item1['from_status']:
                # send to calc
                # add the time to the column corresponding the enddatetime
                cfd_line[item1['from_status']] += calc_diff_date_to_unix(
                    item2['history_datetime'], item1['history_datetime'])

                # lowercase cfg to match lowercase status keys
                list_lower = {v.lower() for v in cfg['Cycletime'].get()}
                # add to cycletime if field set on config
                if item1['from_status'] in list_lower:
                    cfd_line["cycletime"] += cfd_line[item1['from_status']]

    return cfd_line


def group_issuetype(issuetype):
    types = cfg['Issuetype'].get()
    for key1, value1 in types.items():
        if type(value1) == list:
            for value2 in types[key1]:
                if value2 == issuetype:
                    return key1
        else:
            if value1 == issuetype:
                return key1


def group_status(status):
    workflows = cfg['Workflow'].get()
    for key1, value1 in workflows.items():
        if type(value1) == list:
            for value2 in workflows[key1]:
                if value2.lower() == status.lower():
                    return key1.lower()
        else:
            if value1.lower() == status.lower():
                return key1.lower()


def calc_diff_date_to_unix(start_datetime, end_datetime):
    """Given the start and end datetime
    return the difference in unix timestamp format"""
    start = convert_jira_datetime(start_datetime)
    end = convert_jira_datetime(end_datetime)
    timedelta = end - start
    minutes = math.ceil(timedelta/60)
    return minutes


def convert_jira_datetime(datetime_str):
    """Convert Jira datetime format to unix timestamp"""
    time = dt.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f%z')
    return dt.timestamp(time)


def calc_cycletime_percentile(dictio):
    """Calculate cycletime percentiles on cfg with all dict entries"""
    # auxiliary dict with the colums that should be added to cycletime calc
    cycletime = []
    for entry in dictio:
        cycletime.append(entry['cycletime'])

    if len(dictio) >= 1 and len(cycletime) >= 1:
        print("Your throughput is of {} items".format(len(dictio)))
        for percentile in cfg['Percentiles'].get():
            minutes = np.percentile(cycletime, percentile)
            minutes_in_day = 60 * 24
            minutes_in_hour = 60

            days = math.ceil(minutes // minutes_in_day)
            hours = math.ceil(
                (minutes - (days*minutes_in_day))
                // minutes_in_hour
            )
            minutes = math.ceil(
                (minutes -
                    (days * minutes_in_day) - (hours * minutes_in_hour))
            )
            print(
                "Cycletime Percentile of {}% is {} days {} hours {} minutes"
                .format(percentile, days, hours, minutes)
            )
    else:
        print("No items from query or to calculate percentiles")


def read_dates(dictio):
    kanban_data = pd.DataFrame.from_dict(dictio)
    kanban_data.final_datetime = pd.to_datetime(
        kanban_data.final_datetime, unit='s'
    ).dt.date
    # pd.set_option("display.max_rows", None, "display.max_columns", None)
    return kanban_data


def calc_throughput(kanban_data):
    """Change the pandas DF to a Troughput per day format"""
    # Calculate Throughput
    throughput = pd.crosstab(
        kanban_data.final_datetime, kanban_data.issuetype, colnames=[None]
    ).reset_index()
    # Sum Throughput per day
    throughput['Throughput'] = 0
    if 'Story' in throughput:
        throughput['Throughput'] += throughput.Story
    if 'Bug' in throughput:
        throughput['Throughput'] += throughput.Bug
    if 'Task' in throughput:
        throughput['Throughput'] += throughput.Task

    date_range = pd.date_range(
        start=throughput.final_datetime.min(),
        end=throughput.final_datetime.max()
    )
    throughput = throughput.set_index(
        'final_datetime'
    ).reindex(date_range).fillna(0).astype(int).rename_axis('Date')
    # throughput_per_week = pd.DataFrame(throughput['Throughput']
    # .resample('W-Mon').sum()).reset_index()
    return throughput


def simulate_montecarlo(throughput):
    """Run monte carlo simulation with the result of how many itens will
     be delivered in a set of days """

    simul = cfg['Montecarlo']['Simulations'].get()
    simul_days = calc_simul_days()
    source = cfg['Montecarlo']['Source'].get()

    dataset = throughput[['Story']].reset_index(drop=True)

    samples = [dataset.sample(
        n=simul_days, replace=True
    ).sum().Story for i in range(simul)]
    
    samples = pd.DataFrame(samples, columns=['Items'])

    distribution = samples.groupby(['Items']).size().reset_index(
        name='Frequency'
    )
    distribution = distribution.sort_index(ascending=False)
    distribution['Probability'] = (
            100*distribution.Frequency.cumsum()
        ) / distribution.Frequency.sum()

    # Get nearest result
    for percentil in cfg['Percentiles'].get():
        result_index = distribution['Probability'].sub(percentil).abs()\
            .idxmin()
        print(
            "For {}% -> Items: {} ({}%)"
            .format(
                str(percentil),
                distribution.loc[result_index, 'Items'],
                distribution.loc[result_index, 'Probability']
            )
        )

    return distribution


def calc_simul_days():
    start = cfg['Montecarlo']['Simulation Start Date'].get()
    end = cfg['Montecarlo']['Simulation End Date'].get()
    return (end - start).days


if __name__ == "__main__":
    jira = atlassian_auth()
    issue = jql_search(jira)
    dictio = convert_cfd_table(issue)
    calc_cycletime_percentile(dictio)
    kanban_data = read_dates(dictio)
    tp = calc_throughput(kanban_data)
    dist = simulate_montecarlo(tp)
