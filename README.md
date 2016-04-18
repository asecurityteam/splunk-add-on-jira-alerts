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
Here's a basic one to get you going with an ASCII-style table.

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

And here's another one with JIRA-style result tables:

    h3. ${search_name}$
    \\
    Event Data
    \\
    {% for row in results_jira %}${row}${% endfor %}
    \\
    Event Details
    \\
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

### Available Variables
All variables are available in Jinja using format `${<variable>}$`.  Below is a list of all vars which are currently implemented.

#### Splunk event data fields

        search_name = the actual search title or name
        search_string = the search string which generated the results (i.e. 'index=foo sourcetype=foobar | stats count by host')
        owner = username of Splunk search owner (i.e. 'awurster')
        app = the Splunk app which the search is saved under (i.e. 'search' or 'Splunk on Splunk')
        sid = the long search ID (used to generate the callback URL to the search results)
        results = dictionary of the results.  can reference individual values like 'results.field[1]' 
        results_unique = unique values of any given results field, like 'results_unique.variable'
        results_simple = a 'noformat'or plain text style rendering of the results.
        results_file = payload['results_file']
        results_link = a URL pointing back to the results
        trigger_time = the UNIX style timestamp for the trigger time of the results
        trigger_time_rendered = trigger time printed in human readable format
        expiration_time_rendered = expiration time rendered in human readable format
        ttl = number of seconds before the results expire (i.e. 86400)
        keywords = dictionary of search terms from the original search string.  good for printing metadata in raw form for free text reference ('index::foo sourcetype::bar')
        fields = list of all fields in the results (best for stats style outputs)
        event_count = number of events in the data.
        result_count = number of results output from the event.

#### JIRA issue fields
See the REST API guides from Atlassian for all available fields and descriptions.
https://developer.atlassian.com/jiradev/jira-apis/jira-rest-apis/jira-rest-api-tutorials/jira-rest-api-example-discovering-meta-data-for-creating-issues

        project = the 'project_key' of an issue (i.e. 'SEC' or 'ABC')
        id = the shortcode for the issue (i.e. 'ABC-12345')
        issuetype = the type of issue (i.e. 'My Project Alert' or 'Helpdesk Ticket')
        labels = comma-separated list of labels for an issue
        summary = the summary or title of the issue
        description = the rendered event description, including any JIRA rendering syntax
        comment = similar to description, but for updating already-open issues

#### Meta fields

        hostname = hostname from either server.conf or localhost, used to prepare callback URLs
        event_hash = a md5 hash of the event data, used to group similar alerts together
        index = index the data is written to.  defaults to "alerts".

## License
The Splunk Add-on for Atlassian JIRA Alerts is licensed under the Apache License 2.0. Details can be found in the [LICENSE page](http://www.apache.org/licenses/LICENSE-2.0).
