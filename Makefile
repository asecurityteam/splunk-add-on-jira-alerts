# Use this to deploy locally for testing.
.PHONY = deploy test

APP_NAME = atlassian-add-on-jira-alerts
SPLUNK_HOME = /Applications/Splunk
SPLUNK_APPS = $(SPLUNK_HOME)/etc/apps

deploy:
	mkdir -p $(SPLUNK_APPS)/$(APP_NAME)
#	cp -rf ./addons $(SPLUNK_APPS)/$(APP_NAME)/
	cp -rf ./bin $(SPLUNK_APPS)/$(APP_NAME)/
	cp -rf ./default $(SPLUNK_APPS)/$(APP_NAME)/
	cp -rf ./metadata $(SPLUNK_APPS)/$(APP_NAME)/
	cp -rf ./static $(SPLUNK_APPS)/$(APP_NAME)/

restart:
	$(SPLUNK_HOME)/bin/splunk restart -f

test:
	python -m pytest tests/ -vv

all:
	make deploy
	make restart