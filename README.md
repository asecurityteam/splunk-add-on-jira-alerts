# JIRA Alert Add-on

## Introduction

This add-on allows Splunk to create JIRA issues as an alert action.

This add-on was produced as part of the
[Developer Guidance](http://dev.splunk.com/goto/alerting) project. Read our
guide to learn more about creating custom actions that can be performed when an
alert triggers.

## Installation

Once the app is installed (through [Splunkbase](https://splunkbase.splunk.com),
`Install app from file`, or by copying this directory to the etc/apps/ directory
of your Splunk installation), go to the app management page in the Splunk
interface. Click `Set up` in the JIRA Ticket Creation row. Fill out the required
attributes for your JIRA installation and you are ready to go.

To add a JIRA action to an alert, go to the `Alerts` tab in the `Search` app and
find the alert for which you want to add JIRA tickets. Click `Edit`, and select
`Edit Actions`. Click `+ Add Actions` and select JIRA. Fill out the attributes
for the artifact you wish to create in JIRA when the associated search returns
results, and Splunk will start logging bugs for you.

### Setup Defaults
Setup defaults will get inherited on each saved search should you leave any of those options out.

* hostname (not exposed in UI): tries the following in order
** app's alert_actions.conf
    [jira]
    param.hostname = awurster.office.test.com:8443
** system alert_actions.conf email server hostname
    [email]
    hostname = awurster.test.com:8000
** system's hostname (using python's socket module)
    ± laptop → hostname
    syd-awurster


## Issue Settings
Each saved search or alert gets its own settings for how / where to raise a JIRA ticket.

### Description Templates
These are rendered using [Jinja2 templates](http://jinja.pocoo.org/docs/dev/templates/).  This means that all built in filters and looping capabilities are exposed to you when generating the JIRA `description` contents.  The same also applies to building the `comment` and `summary` fields (although summaries should not be so complex in general).

_Important to note_ that we use `${` and `}$` as start and stop tokens (as in `${var}$`) to generate the templates!  This hybrid between Splunk's `$` delimiter and Jinja defaults `{{ }}` avoids overescaping within JIRA templating.

#### Default Description Template
Here's a basic one to get you going.

    h3. ${search_name}$
    \\
    h6. Event Data ASCII
    {noformat}{% for row in results_ascii %}${row}${% endfor %}{noformat}
    \\
    h6.Event Details
    {color:#707070}
    ~*Triggered*: {{${trigger_time_rendered}$}} | *Expires*: {{${expiration_time_rendered}$}}~
    \\
    ~*\# Results*: {{${result_count}$}} | *\# Events*: {{${event_count}$}} | *Hash*: {{${event_hash}$}} | *Results Link*: {{_[Results|${results_link}$]_}}~
    \\
    ~*Unique Values*: {{${results_unique}$}}~
    {color}
    \\ \\
    Search Query
    \\
    {color:#707070}~*App Name*: {{${app}$}} | *Owner*: ${owner_rendered}$~{color}
    {noformat}${search_string}${noformat}

### Comment Templates

### Summary Templates
It can be useful to align your saved search names with the issue summary, although the templating allows.  For example, setting `summary` to the following string prepends the saved search's name with `[JIRA Add-on]` and then adds the first row of `host` column in the results:

    [JIRA Add-on] ${search_name}$: ${results[host][0]}$
For example that would render to:

    [JIRA Add-on] JIRA Modular Alerts Add-on Saved Search: awurster-syd-test


## License
The Splunk Add-on for Atlassian JIRA Alerts is licensed under the Apache License 2.0. Details can be found in the [LICENSE page](http://www.apache.org/licenses/LICENSE-2.0).
