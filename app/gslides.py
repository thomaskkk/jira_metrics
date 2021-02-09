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
    months_after = (dt.datetime.now().month - 1) % 3
    quarter = ((dt.datetime.now().month - 1) // 3) + 1

    kanban_data = gather_metrics_data(jql_search_range(last_quarter=True))
    ct = jm.calc_cycletime_percentile(kanban_data, 85)
    ct = ct.div(60).div(24)
    
    tp = jm.calc_throughput(kanban_data)
    mc = jm.simulate_montecarlo(tp)
    tp = tp.sum(axis=0)
    text_replace = {
            "[s_squad_name]": cfg['Smallsquadname'].get(),
            "[squad_name]": cfg['Squadname'].get(),
            "[quarter]": "Q" + str(quarter),
            "[thpqs]": "{}".format(tp.Story),
            "[thpqt]": "{}".format(tp.Task),
            "[thpqb]": "{}".format(tp.Bug),
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
        text_replace["[th1s]"] = ""
        text_replace["[th1t]"] = ""
        text_replace["[th1b]"] = ""
        text_replace["[th_1_tot]"] = ""
        text_replace["[ct1s]"] = ""
        text_replace["[ct1t]"] = ""
        text_replace["[ct1b]"] = ""
        text_replace["[ct_1_tot]"] = ""
        text_replace["[mc_2_95]"] = ""
        text_replace["[mc_2_85]"] = ""
        text_replace["[mc_2_50]"] = ""

    if months_after >= 2:
        text_replace["[th2s]"] = ""
        text_replace["[th2t]"] = ""
        text_replace["[th2b]"] = ""
        text_replace["[th_2_tot]"] = ""
        text_replace["[ct2s]"] = ""
        text_replace["[ct2t]"] = ""
        text_replace["[ct2b]"] = ""
        text_replace["[ct_2_tot]"] = ""
        text_replace["[mc_3_95]"] = ""
        text_replace["[mc_3_85]"] = ""
        text_replace["[mc_3_50]"] = ""

    if months_after >= 3:
        text_replace["[th3s]"] = ""
        text_replace["[th3t]"] = ""
        text_replace["[th3b]"] = ""
        text_replace["[th_3_tot]"] = ""
        text_replace["[thcqs]"] = ""
        text_replace["[thcqt]"] = ""
        text_replace["[thcqb]"] = ""
        text_replace["[th_cq_tot]"] = ""
        text_replace["[ct3s]"] = ""
        text_replace["[ct3t]"] = ""
        text_replace["[ct3b]"] = ""
        text_replace["[ct_3_tot]"] = ""
        text_replace["[mc_nq_95]"] = ""
        text_replace["[mc_nq_85]"] = ""
        text_replace["[mc_nq_50]"] = ""

    return text_replace


def jql_search_range(last_quarter=False):
    """Return the jql string starting from the 1st day 3 months back and ending in the 1st of the current month"""
    
    start_month = -3
    end_month = -1

    if last_quarter is True:
        months_to_past_quarter = (dt.datetime.now().month - 1) % 3
        start_month -= months_to_past_quarter
        end_month -= months_to_past_quarter

    start_date = dt.datetime.now() + relativedelta(day=1, months=start_month)
    start_date = start_date.strftime('%Y-%m-%d')

    end_date = dt.datetime.now() + relativedelta(day=31, months=end_month)
    end_date = end_date.strftime('%Y-%m-%d')

    return 'AND resolutiondate >= "{}" AND resolutiondate <= "{}"'.format(start_date, end_date)


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
