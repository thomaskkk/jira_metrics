# Jira metrics
A simple python script that allows you to extract three main team metrics from Jira Cloud API and print them in a google slide:
* Throughput
* Cycle time
* Monte Carlo forecast

Before run the script you'll need:
* Jira API Token
* Google Slides API credentials
* One or multiple config files in the config folder

## Jira API Token
* Go to the url https://id.atlassian.com/manage-profile/security/api-tokens
* Click on the button "Create API Token", add any label you wish to identify the application (Ex.: jira_metrics)
* Copy the token store in a safe location 
* Copy the token to each of your config files

## Google Slides API credentials
* Go to your Google Cloud Platform and check if the **Google slides API** is enabled, if not enable it at: https://console.cloud.google.com/apis/api/slides.googleapis.com/
* Create a credential in API & Services -> Credentials at https://console.cloud.google.com/apis/credentials
* Select "Service account" and give the account a name (Ex.: sevice_name@project_name.iam.gserviceaccount.com)
* Go to your newly created service account and click on ADD KEY -> Create new key -> JSON -> Create
* Your browser will download a Json, change the filename to "service_credentials.json"and add to a hidden directory called ".credentials/" on your HOME
* Go to your google slide template and add the email "Service account" (Ex.: sevice_name@project_name.iam.gserviceaccount.com) as one of the editors of your document

## Config files
Check the file config_example.yml you need a config file in the /config folder for each team/squad/slide that you want to extract metrics from.
You can have multiple config files in the config folder, and if you want multiple directories to organize your config files.

## Running the script
You should run on Python 3.7, to check your python version:
```shell
python3 --version
```
Make sure you had the requirementes.txt installed (Docker container is comming soon):
```shell
pip install -r requirements.txt
```
You can run the script with the command:
```shell
./app/jira_metrics.py
```