import sys
import traceback
import subprocess
from subprocess import CalledProcessError

# logging setup
import logging
from logging import handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        handlers.RotatingFileHandler('updater.log', maxBytes=(1048576*5), backupCount=7)
    ])
log = logging.getLogger(__name__)

# github setup
from github import Github
from config import gh_token, gh_user
github = Github(gh_token)
bounties_repo_name = 'bounties'
bounties_repo = github.get_repo('%s/%s' % (gh_user, bounties_repo_name))

# mongodb setup
import pymongo
from config import mongo_connection_string
log.info('Connecting to database...')
client = pymongo.MongoClient(mongo_connection_string, connect=False)
log.info('Connected.')
database = client.github
c_issues = database.issues # index id
c_issue_tips = database.issue_tips # index address
c_pulls = database.pulls # index id
c_variables = database.variables


def ctu(url):
    return url.replace('https://github.com', 'http://github.chaintip.org')

price = c_variables.find_one({})['bch_price']
readme = """This repository tracks bounties on issues tipped using the ChainTip bot. 

Each open issue here gives information about a bounty available on an issue in another repository.


## Available Bounties

[How do I claim a bounty?](http://www.chaintip.org/github#claim-bounty) |  [How do I create or add to a bounty?](http://www.chaintip.org/github#tip-issue) | [www.chaintip.org](http://www.chaintip.org/)

Bounty | Issue | Repository | Fixing PRs
---: | --- | :---: | :---:
"""
for issue in bounties_repo.get_issues(state='open'):
    i = c_issues.find_one({'bounties_issue_number': issue.number})
    if i:
        pulls = []
        if 'pulls' in i:
            pulls = c_pulls.find({'id': {'$in': i['pulls']}})
        pulls_string = ''
        for pull in pulls:
            if len(pulls_string) > 0:
                pulls_string += ', '
            pulls_string += '[#%s](%s)' % (pull['number'], ctu(pull['url']))

        split = i['repo_full_name'].split('/')
        repo_string = "[%s](%s)" % (split[0], ctu('https://github.com/' + split[0]))
        repo_string += " /"
        repo_string += " " if (len(split[0]) + len(split[1])) < 23 else "<br>"
        repo_string += "[%s](%s)" % (split[1], ctu(i['repo_url']))
        amount_usd = float(i['amount']) * price
        if amount_usd > 0:
            readme += """[$%s](%s) | %s [#%s](%s) | %s | %s
""" % (round(amount_usd, 2), ctu(issue.html_url), i['title'], i['number'], ctu(i['url']), repo_string, pulls_string)

readme += """
## Collected Bounties

Bounty | Issue | Repository | Fixed By PR
---: | --- | :---: | :---:
"""
for issue in bounties_repo.get_issues(state='closed'):
    i = c_issues.find_one({'bounties_issue_number': issue.number})
    if i:
        if 'linked_pull_id' in i:
            pull = c_pulls.find_one({'id': i['linked_pull_id']})
            pull_string = '[#%s](%s)' % (pull['number'], ctu(pull['url']))
            split = i['repo_full_name'].split('/')
            repo_string = "[%s](%s)" % (split[0], ctu('https://github.com/' + split[0]))
            repo_string += " /"
            repo_string += " " if (len(split[0]) + len(split[1])) < 23 else "<br>"
            repo_string += "[%s](%s)" % (split[1], ctu(i['repo_url']))
            amount_usd = float(i['amount']) * price
            readme += """[$%s](%s) | %s [#%s](%s) | %s | %s
""" % (round(amount_usd, 2), ctu(issue.html_url), i['title'], i['number'], ctu(i['url']), repo_string, pull_string)

readme += """
## Expired Bounties

Bounty | Issue | Repository | Fixed By PR
---: | --- | :---: | :---:
"""
for issue in bounties_repo.get_issues(state='open'):
    i = c_issues.find_one({'bounties_issue_number': issue.number})
    if i:
        pulls = []
        if 'pulls' in i:
            pulls = c_pulls.find({'id': {'$in': i['pulls']}})
        pulls_string = ''
        for pull in pulls:
            if len(pulls_string) > 0:
                pulls_string += ', '
            pulls_string += '[#%s](%s)' % (pull['number'], ctu(pull['url']))

        split = i['repo_full_name'].split('/')
        repo_string = "[%s](%s)" % (split[0], ctu('https://github.com/' + split[0]))
        repo_string += " /"
        repo_string += " " if (len(split[0]) + len(split[1])) < 23 else "<br>"
        repo_string += "[%s](%s)" % (split[1], ctu(i['repo_url']))
        amount_usd = float(i['amount']) * price
        if amount_usd == 0:
            readme += """[$%s](%s) | %s [#%s](%s) | %s | %s
""" % (round(amount_usd, 2), ctu(issue.html_url), i['title'], i['number'], ctu(i['url']), repo_string, pulls_string)

with open("README.md", "w") as readme_file:
    print(readme, file = readme_file)

log.info(subprocess.check_output(['git','add', '.']))
try:
    log.info(subprocess.check_output(['git','commit', '-m', 'Auto update']))
except CalledProcessError:
    print('Error commiting')

log.info(subprocess.check_output(['git','push']))
