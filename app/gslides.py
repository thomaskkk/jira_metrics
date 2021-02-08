#!/usr/bin/env python

import GoogleApiSupport.slides as slides

month_start =  {
            "[s_squad_name]": "ACTIVATION",
            "[squad_name]": "Activation",
            "[quarter]": "Q1",
            "[thpqs]": "",
            "[thpqt]": "",
            "[thpqb]": "",
            "[th_pq_tot]": "XX items",
            "[ctpqs]": "XXd",
            "[ctpqt]": "",
            "[ctpqb]": "",
            "[ct_pq_tot]": "XXd (85%)",
            "[mc_1_95]": "XX items (US only)",
            "[mc_1_85]": "",
            "[mc_1_50]": "",
            "[notes]": "* Todas as métricas desta squad usam o histórico de"
        }

month_1 =  {
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
        }

month_2 =  {
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
        }

month_3 =  {
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
        }


def fill_metrics():
    slide_id = "1F_HyJ_FV8A-wafXVyniAlw7gQsTUcE5pa10QjrWTB5o"
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
    gslides = fill_metrics()
