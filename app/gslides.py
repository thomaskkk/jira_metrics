#!/usr/bin/env python

import GoogleApiSupport.slides as slides
import jira_metrics as jm
import datetime as dt
from dateutil.relativedelta import *
import confuse
import math

cfg = confuse.Configuration('JiraMetrics', __name__)
cfg.set_file('config_test.yml')


def gather_metrics_data(jql_date_append):
    jira = jm.atlassian_auth()
    issue = jm.jql_search(jira, jql_date_append)
    dictio = jm.convert_cfd_table(issue)
    kanban_data = jm.read_dates(dictio)

    return kanban_data


def metrics_by_month():
    current_month = dt.datetime.now().month
    months_after = (current_month - 1) % 3
    quarter = ((current_month - 1) // 3) + 1

    kanban_data = gather_metrics_data(jql_search_range(1))
    ct = jm.calc_cycletime_percentile(kanban_data, 85)
    ct = ct.div(60).div(24)
    tp = jm.calc_throughput(kanban_data)
    mc = jm.simulate_montecarlo(tp, sources=['Story'], simul=10000, simul_days=simul_days_range(1))
    tp = tp.sum(axis=0)
    text_replace = {
            "[s_squad_name]": cfg['Smallsquadname'].get(),
            "[squad_name]": cfg['Squadname'].get(),
            "[quarter]": "Q" + str(quarter),
            "[thpqs]": str(tp.Story),
            "[thpqt]": str(tp.Task),
            "[thpqb]": str(tp.Bug),
            "[th_pq_tot]": "{} items".format(tp.Throughput),
            "[ctpqs]": "{}d".format(math.ceil(ct.Story)),
            "[ctpqt]": "{}d".format(math.ceil(ct.Task)),
            "[ctpqb]": "{}d".format(math.ceil(ct.Bug)),
            "[ct_pq_tot]": "{}d (85%)".format(math.ceil(ct.Total)),
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
            "[notes]": cfg['Notes'].get()
        }

    if months_after >= 1:
        kanban_data = gather_metrics_data(jql_search_range(2))
        ct = jm.calc_cycletime_percentile(kanban_data, 85)
        ct = ct.div(60).div(24)
        tp = jm.calc_throughput(kanban_data)
        mc = jm.simulate_montecarlo(tp, sources=['Story'], simul=10000, simul_days=simul_days_range(2))
        tp = tp.sum(axis=0)
        text_replace["[th1s]"] = str(tp.Story)
        text_replace["[th1t]"] = str(tp.Task)
        text_replace["[th1b]"] = str(tp.Bug)
        text_replace["[th_1_tot]"] = "{} items".format(tp.Throughput)
        text_replace["[ct1s]"] = "{}d".format(math.ceil(ct.Story))
        text_replace["[ct1t]"] = "{}d".format(math.ceil(ct.Task))
        text_replace["[ct1b]"] = "{}d".format(math.ceil(ct.Bug))
        text_replace["[ct_1_tot]"] = "{}d (85%)".format(math.ceil(ct.Total))
        text_replace["[mc_2_95]"] = "{} items (US only)".format(mc['Story'][95])
        text_replace["[mc_2_85]"] = "{} items (US only)".format(mc['Story'][85])
        text_replace["[mc_2_50]"] = "{} items (US only)".format(mc['Story'][50])

    if months_after >= 2:
        kanban_data = gather_metrics_data(jql_search_range(3))
        ct = jm.calc_cycletime_percentile(kanban_data, 85)
        ct = ct.div(60).div(24)
        tp = jm.calc_throughput(kanban_data)
        mc = jm.simulate_montecarlo(tp, sources=['Story'], simul=10000, simul_days=simul_days_range(3))
        tp = tp.sum(axis=0)
        text_replace["[th2s]"] = str(tp.Story)
        text_replace["[th2t]"] = str(tp.Task)
        text_replace["[th2b]"] = str(tp.Bug)
        text_replace["[th_2_tot]"] = "{} items".format(tp.Throughput)
        text_replace["[ct2s]"] = "{}d".format(math.ceil(ct.Story))
        text_replace["[ct2t]"] = "{}d".format(math.ceil(ct.Task))
        text_replace["[ct2b]"] = "{}d".format(math.ceil(ct.Bug))
        text_replace["[ct_2_tot]"] = "{}d (85%)".format(math.ceil(ct.Total))
        text_replace["[mc_3_95]"] = "{} items (US only)".format(mc['Story'][95])
        text_replace["[mc_3_85]"] = "{} items (US only)".format(mc['Story'][85])
        text_replace["[mc_3_50]"] = "{} items (US only)".format(mc['Story'][50])

    if months_after >= 3:
        text_replace["[th3s]"] = ""
        text_replace["[th3t]"] = ""
        text_replace["[th3b]"] = ""
        text_replace["[th_3_tot]"] = ""
        # text_replace["[thcqs]"] = ""
        # text_replace["[thcqt]"] = ""
        # text_replace["[thcqb]"] = ""
        # text_replace["[th_cq_tot]"] = ""
        # text_replace["[mc_nq_95]"] = ""
        # text_replace["[mc_nq_85]"] = ""
        # text_replace["[mc_nq_50]"] = ""

    return text_replace


def jql_search_range(metrics_quarter):
    """Return the jql string starting from the 1st day 3 months back and ending in the 1st of the current month"""
    today = dt.date.today()
    months_to_past_quarter = (today.month - metrics_quarter) % 3
    start_month = (-3) - months_to_past_quarter
    end_month = (-1) - months_to_past_quarter

    start_date = today + relativedelta(day=1, months=start_month)
    end_date = today + relativedelta(day=31, months=end_month)

    return 'AND resolutiondate >= "{}" AND resolutiondate <= "{}"'.format(start_date, end_date)


def simul_days_range(metrics_quarter):
    """Return the number of days from current date until the end of the quarter"""
    today = dt.date.today()
    months_to_past_quarter = - ((today.month - metrics_quarter) % 3)
    months_to_next_quarter = 2 - (today.month - 1) % 3

    start_date = today + relativedelta(day=1, months=months_to_past_quarter)
    end_date = today + relativedelta(day=31, months=months_to_next_quarter)

    return (end_date - start_date).days


def fill_metrics(text_replace):
    slide_id = cfg['Slideid'].get()
    response = batch_text_replace(text_replace, slide_id)
    return response


def batch_text_replace(text_mapping: dict, presentation_id: str, pages=None):
    if pages is None:
        pages = list()

    requests = []
    for placeholder_text, new_value in text_mapping.items():
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


if __name__ == "__main__":
    text_replace = metrics_by_month()
    response = fill_metrics(text_replace)
    print(response)
