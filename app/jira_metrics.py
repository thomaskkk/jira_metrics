#!/usr/bin/env python

import confuse
from jira import JIRA
import datetime as dt
import math
import pandas as pd
from dateutil.relativedelta import relativedelta
import uuid
import os
import GoogleApiSupport.slides as slides


cfg = confuse.Configuration('JiraMetrics', __name__)
cfg.set_file('config_test.yml')


def atlassian_auth(override_config_filename=None):
    """Authenticate on the Jira Cloud instance"""

    if override_config_filename is not None:
        cfg.set_file(override_config_filename)

    username = cfg['Connection']['Username'].get()
    api = cfg['Connection']['ApiKey'].get()

    jira = JIRA(
        server=cfg['Connection']['Domain'].get(),
        basic_auth=(username, api)
    )
    return jira


def jql_search(jira_obj, jql_query=None):
    """Run a JQL search and return the jira object with results"""
    sfields = [
        "created",
        "issuetype"
    ]
    if jql_query is None:
        jql_query = cfg['Query'].get()

    issues = jira_obj.search_issues(
        jql_query,
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
                list_lower = {
                    v.lower() for v in cfg['Cycletime']['Status'].get()}
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
    raise Exception("Can't find issue in config file: {}".format(issuetype))


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

    raise Exception("Can't find status in config file: {}".format(status))


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
    time = dt.datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f%z')
    return dt.datetime.timestamp(time)


def calc_cycletime_percentile(kanban_data, percentile=None):
    """Calculate cycletime percentiles on cfg with all dict entries"""
    if percentile is not None:
        issuetype = kanban_data.groupby('issuetype').cycletime.quantile(
            percentile / 100)
        issuetype['Total'] = kanban_data.cycletime.quantile(percentile / 100)
        return issuetype
    else:
        for cfg_percentile in cfg['Cycletime']['Percentiles'].get():
            cycletime = kanban_data.groupby('issuetype').cycletime.quantile(
                cfg_percentile / 100)
            cycletime['Total'] = kanban_data.cycletime.quantile(
                cfg_percentile / 100)
            cycletime = cycletime.div(60).div(24)
            print("Cycletime {}% (in days):".format(cfg_percentile))
            print(cycletime)


def read_dates(dictio):
    kanban_data = pd.DataFrame.from_dict(dictio)
    kanban_data.final_datetime = pd.to_datetime(
        kanban_data.final_datetime, unit='s'
    ).dt.date
    # Remove items with cycletime == 0
    kanban_data = kanban_data[kanban_data.cycletime != 0]
    return kanban_data


def calc_throughput(kanban_data, start_date=None, end_date=None):
    """Change the pandas DF to a Troughput per day format"""
    if start_date is not None:
        kanban_data = kanban_data[~(
            kanban_data['final_datetime'] <= start_date)]
    if end_date is not None:
        kanban_data = kanban_data[~(
            kanban_data['final_datetime'] >= end_date)]

    # Reorganize DataFrame
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
    return throughput


def simulate_montecarlo(throughput, sources=None, simul=None, simul_days=None):

    if sources is None:
        sources = cfg['Montecarlo']['Source'].get()
    if simul is None:
        simul = cfg['Montecarlo']['Simulations'].get()
    if simul_days is None:
        simul_days = calc_simul_days()

    mc = {}
    for source in sources:
        mc[source] = run_simulation(throughput, source, simul, simul_days)

    return mc


def run_simulation(throughput, source, simul, simul_days):
    """Run monte carlo simulation with the result of how many itens will
    be delivered in a set of days """

    dataset = throughput[[source]].reset_index(drop=True)

    samples = [getattr(dataset.sample(
        n=simul_days, replace=True
    ).sum(), source) for i in range(simul)]

    samples = pd.DataFrame(samples, columns=['Items'])

    distribution = samples.groupby(['Items']).size().reset_index(
        name='Frequency'
    )
    distribution = distribution.sort_index(ascending=False)
    distribution['Probability'] = (
            100*distribution.Frequency.cumsum()
        ) / distribution.Frequency.sum()

    print(" - For {}:".format(source))
    mc_results = {}
    # Get nearest neighbor result
    for percentil in cfg['Montecarlo']['Percentiles'].get():
        result_index = distribution['Probability'].sub(percentil).abs()\
            .idxmin()
        mc_results[percentil] = distribution.loc[result_index, 'Items']
        print(
            "For {}% -> Items: {} ({}%)"
            .format(
                str(percentil),
                distribution.loc[result_index, 'Items'],
                distribution.loc[result_index, 'Probability']
            )
        )

    return mc_results


def calc_simul_days():
    start = cfg['Montecarlo']['Simulation Start Date'].get()
    end = cfg['Montecarlo']['Simulation End Date'].get()
    return (end - start).days


def gather_metrics_data(jql_query):
    jira = atlassian_auth()
    issue = jql_search(jira, jql_query)
    dictio = convert_cfd_table(issue)
    kanban_data = read_dates(dictio)

    return kanban_data


def metrics_by_month():
    current_month = dt.datetime.now().month
    months_after = (current_month - 1) % 3
    quarter = ((current_month - 1) // 3) + 1
    jql_query = str(cfg['Query'])
    simulations = cfg['Montecarlo']['Simulations'].get()
    mc_sources = cfg['Montecarlo']['Source'].get()

    # Past quarter results and 1st month forecast
    kanban_data = gather_metrics_data(jql_query + jql_search_range(0))
    ct = calc_cycletime_percentile(kanban_data, 85)
    ct = ct.div(60).div(24)
    tp = calc_throughput(kanban_data)
    mc = simulate_montecarlo(
        tp, sources=mc_sources,
        simul=simulations,
        simul_days=simul_days_range(0))
    tp = tp.sum(axis=0)
    text_replace = {
            "[s_squad_name]": cfg['Gslides']['Smallsquadname'].get(),
            "[squad_name]": cfg['Gslides']['Squadname'].get(),
            "[quarter]": "Q" + str(quarter),
            "[thpqs]": str(getattr(tp, "Story", 0)),
            "[thpqt]": str(getattr(tp, "Task", 0)),
            "[thpqb]": str(getattr(tp, "Bug", 0)),
            "[th_pq_tot]": "{} items".format(getattr(tp, "Throughput", 0)),
            "[ctpqs]": "{}d".format(math.ceil(getattr(ct, "Story", 0))),
            "[ctpqt]": "{}d".format(math.ceil(getattr(ct, "Task", 0))),
            "[ctpqb]": "{}d".format(math.ceil(getattr(ct, "Bug", 0))),
            "[ct_pq_tot]": "{}d (85%)".format(
                math.ceil(getattr(ct, "Total", 0))),
            "[mc_1_95]": "{} items (US only)".format(mc['Story'][95]),
            "[mc_1_85]": "{} items (US only)".format(mc['Story'][85]),
            "[mc_1_50]": "{} items (US only)".format(mc['Story'][50]),
            "[th1s]": "",
            "[th1t]": "",
            "[th1b]": "",
            "[th_1_tot]": "",
            "[ct1s]": "",
            "[ct1t]": "",
            "[ct1b]": "",
            "[ct_1_tot]": "",
            "[mc_2_95]": "",
            "[mc_2_85]": "",
            "[mc_2_50]": "",
            "[th2s]": "",
            "[th2t]": "",
            "[th2b]": "",
            "[th_2_tot]": "",
            "[ct2s]": "",
            "[ct2t]": "",
            "[ct2b]": "",
            "[ct_2_tot]": "",
            "[mc_3_95]": "",
            "[mc_3_85]": "",
            "[mc_3_50]": "",
            "[th3s]": "",
            "[th3t]": "",
            "[th3b]": "",
            "[th_3_tot]": "",
            "[thcqs]": "",
            "[thcqt]": "",
            "[thcqb]": "",
            "[th_cq_tot]": "",
            "[ct3s]": "",
            "[ct3t]": "",
            "[ct3b]": "",
            "[ct_3_tot]": "",
            "[mc_nq_95]": "",
            "[mc_nq_85]": "",
            "[mc_nq_50]": "",
            "[notes]": cfg['Gslides']['Notes'].get()
        }

    thcqs = 0
    thcqt = 0
    thcqb = 0
    th_cq_tot = 0

    # 1st month results and 2st month forecast
    kanban_data = gather_metrics_data(jql_query + jql_search_range(1))
    ct = calc_cycletime_percentile(kanban_data, 85)
    ct = ct.div(60).div(24)
    mctp = calc_throughput(kanban_data)
    mc = simulate_montecarlo(
        mctp, sources=mc_sources,
        simul=simulations,
        simul_days=simul_days_range(1))
    tp_start, tp_end = throughput_range(1)
    tp = calc_throughput(kanban_data, start_date=tp_start, end_date=tp_end)
    tp = tp.sum(axis=0)
    text_replace["[th1s]"] = str(getattr(tp, "Story", 0))
    thcqs += int(getattr(tp, "Story", 0))
    text_replace["[th1t]"] = str(getattr(tp, "Task", 0))
    thcqt += int(getattr(tp, "Task", 0))
    text_replace["[th1b]"] = str(getattr(tp, "Bug", 0))
    thcqb += int(getattr(tp, "Bug", 0))
    text_replace["[th_1_tot]"] = "{} items".format(
        getattr(tp, "Throughput", 0))
    th_cq_tot += int(getattr(tp, "Throughput", 0))
    text_replace["[ct1s]"] = "{}d".format(math.ceil(getattr(ct, "Story", 0)))
    text_replace["[ct1t]"] = "{}d".format(math.ceil(getattr(ct, "Task", 0)))
    text_replace["[ct1b]"] = "{}d".format(math.ceil(getattr(ct, "Bug", 0)))
    text_replace["[ct_1_tot]"] = "{}d (85%)".format(
        math.ceil(getattr(ct, "Total", 0)))
    text_replace["[mc_2_95]"] = "{} items (US only)".format(
        mc['Story'][95]
        )
    text_replace["[mc_2_85]"] = "{} items (US only)".format(
        mc['Story'][85]
        )
    text_replace["[mc_2_50]"] = "{} items (US only)".format(
        mc['Story'][50]
        )

    if months_after >= 1:
        # 2nd month results and 3rd month forecast
        kanban_data = gather_metrics_data(jql_query + jql_search_range(2))
        ct = calc_cycletime_percentile(kanban_data, 85)
        ct = ct.div(60).div(24)
        mctp = calc_throughput(kanban_data)
        mc = simulate_montecarlo(
            mctp, sources=mc_sources,
            simul=simulations,
            simul_days=simul_days_range(2))
        tp_start, tp_end = throughput_range(2)
        tp = calc_throughput(kanban_data, start_date=tp_start, end_date=tp_end)
        tp = tp.sum(axis=0)
        text_replace["[th2s]"] = str(getattr(tp, "Story", 0))
        thcqs += int(getattr(tp, "Story", 0))
        text_replace["[th2t]"] = str(getattr(tp, "Task", 0))
        thcqt += int(getattr(tp, "Task", 0))
        text_replace["[th2b]"] = str(getattr(tp, "Bug", 0))
        thcqb += int(getattr(tp, "Bug", 0))
        text_replace["[th_2_tot]"] = "{} items".format(
            getattr(tp, "Throughput", 0))
        th_cq_tot += int(getattr(tp, "Throughput", 0))
        text_replace["[ct2s]"] = "{}d".format(
            math.ceil(getattr(ct, "Story", 0)))
        text_replace["[ct2t]"] = "{}d".format(
            math.ceil(getattr(ct, "Task", 0)))
        text_replace["[ct2b]"] = "{}d".format(
            math.ceil(getattr(ct, "Bug", 0)))
        text_replace["[ct_2_tot]"] = "{}d (85%)".format(
            math.ceil(getattr(ct, "Total", 0)))
        text_replace["[mc_3_95]"] = "{} items (US only)".format(
            mc['Story'][95]
            )
        text_replace["[mc_3_85]"] = "{} items (US only)".format(
            mc['Story'][85]
            )
        text_replace["[mc_3_50]"] = "{} items (US only)".format(
            mc['Story'][50]
            )

    if months_after >= 2:
        # 3rd month results, quarter totals and next forecast
        kanban_data = gather_metrics_data(jql_query + jql_search_range(3))
        ct = calc_cycletime_percentile(kanban_data, 85)
        ct = ct.div(60).div(24)
        mctp = calc_throughput(kanban_data)
        mc = simulate_montecarlo(
            mctp, sources=mc_sources,
            simul=simulations,
            simul_days=simul_days_range(3))
        tp_start, tp_end = throughput_range(3)
        tp = calc_throughput(kanban_data, start_date=tp_start, end_date=tp_end)
        tp = tp.sum(axis=0)
        text_replace["[th3s]"] = str(getattr(tp, "Story", 0))
        thcqs += int(getattr(tp, "Story", 0))
        text_replace["[th3t]"] = str(getattr(tp, "Task", 0))
        thcqt += int(getattr(tp, "Task", 0))
        text_replace["[th3b]"] = str(getattr(tp, "Bug", 0))
        thcqb += int(getattr(tp, "Bug", 0))
        text_replace["[th_3_tot]"] = "{} items".format(
            getattr(tp, "Throughput", 0))
        th_cq_tot += int(getattr(tp, "Throughput", 0))
        text_replace["[mc_nq_95]"] = "{} items (US only)".format(
            mc['Story'][95]
            )
        text_replace["[mc_nq_85]"] = "{} items (US only)".format(
            mc['Story'][85]
            )
        text_replace["[mc_nq_50]"] = "{} items (US only)".format(
            mc['Story'][50]
            )

    # Fill quarter totals
    text_replace["[thcqs]"] = str(thcqs)
    text_replace["[thcqt]"] = str(thcqt)
    text_replace["[thcqb]"] = str(thcqb)
    text_replace["[th_cq_tot]"] = "{} items".format(str(th_cq_tot))

    return text_replace


def jql_search_range(metrics_month):
    """Return the jql string starting from the 1st day 3 months back
    and ending in the 1st of the current month"""

    today = dt.date.today()
    months_to_past_quarter = ((today.month - 1) % 3)
    start_month = (metrics_month - months_to_past_quarter) - 3
    end_month = (metrics_month - months_to_past_quarter) - 1

    start_date = today + relativedelta(day=1, months=start_month)
    end_date = today + relativedelta(day=31, months=end_month)

    return 'AND resolutiondate >= "{}" AND resolutiondate <= "{}"'.format(
        start_date, end_date
        )


def throughput_range(metrics_month):
    """Return two objects with date range of the current metrics month"""

    today = dt.date.today()
    months_to_past_quarter = ((today.month - 1) % 3)
    start_month = (metrics_month - months_to_past_quarter) - 1
    end_month = (metrics_month - months_to_past_quarter) - 1

    start_date = today + relativedelta(day=1, months=start_month)
    end_date = today + relativedelta(day=31, months=end_month)

    return start_date, end_date


def simul_days_range(metrics_month):
    """Return the number of days from current month until
    the end of the quarter """

    today = dt.date.today()
    months_to_past_quarter = ((today.month - 1) % 3)
    start_month = ((metrics_month + 1) - months_to_past_quarter) - 1
    months_to_next_quarter = 2 - (today.month - 1) % 3
    # If asked to forecast next quarter we should add 3 months
    if metrics_month == 3:
        months_to_next_quarter += 3

    start_date = today + relativedelta(day=1, months=start_month)
    end_date = today + relativedelta(day=31, months=months_to_next_quarter)

    return (end_date - start_date).days


def fill_metrics(text_replace, pages=None):
    presentation_id = cfg['Gslides']['Presentationid'].get()
    if pages is None:
        pages = list()

    requests = []
    for placeholder_text, new_value in text_replace.items():
        if type(new_value) is str:
            requests += [
                {
                    "replaceAllText": {
                        "containsText": {
                            "text":  placeholder_text,
                            "matchCase": True
                        },
                        "replaceText": new_value,
                        "pageObjectIds": pages
                    }
                }
            ]
        else:
            raise Exception(
                'The text from key {} is not a string'.format(placeholder_text)
            )
    return slides.execute_batch_update(requests, presentation_id)


def copy_slide(page_id=None):
    presentation_id = cfg['Gslides']['Presentationid'].get()

    if page_id is None:
        slideobj = slides.get_presentation_slides(presentation_id)
        for object in slideobj:
            page_id = object['objectId']
            break

    new_objectid = str(uuid.uuid4())
    requests = [
        {
            "duplicateObject": {
                "objectId": page_id,
                "objectIds": {
                    page_id: new_objectid,
                }
            }
        }
    ]

    slides.execute_batch_update(requests, presentation_id)
    return new_objectid


def main():
    for root, dirs, files in os.walk("config"):
        for name in files:
            cfg.set_file(os.path.join(root, name))
            print("Processing: {}".format(os.path.join(root, name)))
            text_replace = metrics_by_month()
            page_id = copy_slide()
            response = fill_metrics(text_replace, pages=[page_id])
            print(response)


if __name__ == "__main__":
    main()
