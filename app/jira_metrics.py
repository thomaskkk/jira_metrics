#!/usr/bin/env python

from jira import JIRA
import yaml


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


def convert_cfd_table(issues_obj):
    """Convert the issues obj into a dictionary on the cfd format"""
    cfd_table = {}
    for issue in issues_obj:
        for history in issue.changelog.histories:
            for item in history.items:
                if item.field == 'status':
                    print("Issue: {} on {} moved from [{}] to [{}]".format(issue.key, history.created, item.fromString, item.toString))


def config_reader(yaml_file):
    """Open the yaml file with all config and return as a dictionary"""
    with open(yaml_file) as file:
        return yaml.load(file, Loader=yaml.FullLoader)


if __name__ == "__main__":
    yaml_file = "../config_test.yml"
    config = config_reader(yaml_file)
    jira = atlassian_auth(config)
    jira = jql_search(jira)
    dictio = convert_cfd_table(jira)
    # print(dictio.__dict__)
