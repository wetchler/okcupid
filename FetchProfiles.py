#!/usr/bin/python2.7
'''
Created on Jun 25, 2012

@author: Everett Wetchler (evee746)
'''

import csv
import datetime
import gflags
import random
import requests
import sys
import time

DEFAULT_COOKIE = '1780687262307760404%3a151924852332704912'
FLAGS = gflags.FLAGS
gflags.DEFINE_boolean('pull_essays', False,
                      'If True, pulls free responses sections. If False, '
                      'just basic form details.')
gflags.DEFINE_string('session_cookie', DEFAULT_COOKIE, '')
gflags.DEFINE_string('outfile', '', '')
gflags.DEFINE_string('usernames_file', '', '')


SLEEP_BETWEEN_QUERIES = 2.5
PROFILE_URL = "http://www.okcupid.com/profile/%s"


def GetProfile(username, opener):
    url = PROFILE_URL % username
    print "Fetching profile HTML for", username + "... ",
    html = None
    for i in range(3):
        if i > 0:
            print "Retrying...",
        try:
            r = requests.get(url, cookies={'session': FLAGS.session_cookie})
            break
        except urllib2.URLError, e:
            print "Error fetching profile:", e
    if not html:
        print "Giving up."
        return None
    print "Parsing...",
    profile = ParseProfileHtml(html, username)
    return profile


def ParseProfileHtml(html, username):
    html = html.replace('\xe2\x80\x99', '\'')
    html = "".join([x for x in html if ord(x)<128])
    html = html.lower()
    # Sanity check that this is the right profile
    expected_tag = '<p class="username">%s</p>' % username.lower()
    idx = html.find(expected_tag)
    if idx < 0:
        print ("Bad or no-longer-existant profile. "
               "HTML did not contain username tag: %s" % expected_tag)
        f = open("badprofile_" + username + ".html", 'w')
        print >>f, html
        f.close()
        return None
    # Find the tag for basic info
    basics_tag = '<p class="info">'
    idx = html.find(basics_tag, idx)
    if idx < 0:
        print "Bad profile. Did not contain basic info tag: %s" % basics_tag
        f = open("badprofile_" + username + ".html", 'w')
        print >>f, html
        f.close()
        return None
    start = idx + len(basics_tag)
    end = html.find("<", start)
    basic_info = html[start:end]    # '26 / M / Straight / Single / San Francisco, California'
    age, sex, orientation, status, location = [x.strip() for x in basic_info.split("/")]
    profile = {}
    profile['age'] = int(age)
    profile['sex'] = sex
    profile['orientation'] = orientation
    profile['status'] = status
    profile['location'] = location
    # Structured details
    details_tag = '<div id="profile_details">'
    idx = html.find(details_tag, end)
    if idx < 0:
        print "Bad profile. Did not contain details tag: %s" % details_tag
        f = open("badprofile_" + username + ".html", 'w')
        print >>f, html
        f.close()
        return None
    details_section = html[(idx + len(details_tag)):html.find("</div>", idx)]
    ExtractDetails(details_section, profile)
    # Essays
    if FLAGS.essays:
        ExtractEssays(html, profile)
    return profile

def ExtractDetails(html, profile):
    idx = html.find("<dt>")
    while idx > 0:
        start = idx + 4
        end = html.find("</dt>", start)
        category = html[start:end].strip()
        start = html.find("<dd", end) + 3
        # Sometimes it's <dd>, sometimes its <dd id="foo">
        start = html.find(">", start) + 1
        end = html.find("</dd>", start)
        value = html[start:end].strip()
        if category != "looking for":    # For some reason this one is commented out in HTML
            profile[category] = Reformat(category, value)
        idx = html.find("<dt>", end + 5)

def Reformat(category, value):
    INCOME_UNLISTED = -1
    if value == '&mdash;':
        if category == "income":
            return INCOME_UNLISTED
        return ""
    if category == "last online":
        if value == "online now!":
            dt = datetime.datetime.now()
        else:
            # value should look like this:
            # <span class="fancydate" id="fancydate_134068580564486"></span><script> FancyDate.add('fancydate_134068580564486', 1340607978, ''); </script> 
            # so if this doesn't change, we can cheat and just split by commas
            ts = value.split('fancydate')[-1].split(",")[1].strip()
            dt = datetime.datetime.fromtimestamp(int(ts))
        return dt.strftime("%Y-%m-%d-%H-%M")
    elif category == "height":
        # value should look like:
        # 6&prime; 3&Prime; (1.91m).
        feet = int(value.split("&")[0])
        inches = int(value.split()[1].split("&")[0])
        value = feet*12 + inches
    elif category == "income":
        # These are formatted as '$50,000&ndash;$60,000' or 'less than $20,000'
        # We'll just take the first dollar value as a good-enough proxy.
        value = value.replace(",", "")
        start = value.find("$") + 1
        if start <= 0:
            return INCOME_UNLISTED
        end = value.find("&ndash;")
        if end < 0:
            return int(value[start:])
        else:
            return int(value[start:end])
    return value

def ExtractEssays(html, profile):
    for i in range(10):
        profile["essay%d" % i] = ""
    # Essays should appear inside divs that look like:
    # <div id="essay_text_0" class="nostyle"> Essay content here </div>
    tag = "<div id=\"essay_text_"
    idx = html.find(tag)
    while idx >= 0:
        idx += len(tag)
        num = int(html[idx])
        start = html.find(">", idx) + 1
        end = html.find("</div>", start)
        profile["essay%d" % num] = html[start:end].strip()
        idx = html.find(tag, end)


FETCH_STATUS = '''%(elapsed)ds elapsed, %(completed)d profiles fetched, \
%(deleted)d deleted, \
%(remaining)d left, %(secs_per_prof).1fs per profile, \
%(prof_per_hour).0f profiles per hour, \
%(est_hours_left).1f hours left'''


def FetchProfilesWriteCSV(opener, usernames, randomize=True):
    deleted_profiles = []
    if randomize:
        random.shuffle(usernames)
    start = datetime.datetime.now()
    last = start
    first = True
    with open('profiles.csv', 'wb') as f:
        csv_writer = csv.writer(f)
        for i,u in enumerate(usernames):
            # ** Critical ** so OKC servers don't notice and throttle us
            print "Sleeping..."
            elapsed = datetime.datetime.now() - last
            elapsed_sec = elapsed.seconds * 1.0 + elapsed.microseconds / 1.0e6
            time.sleep(max(0, FLAGS.secs_between_queries - elapsed_sec))
            # Go ahead
            last = datetime.datetime.now()
            profile = GetProfile(u, opener)
            if not profile:
                deleted_profiles.append(u)
                skipped += 1
                continue
            row = tuple([u] + [profile[k] for k in sorted(profile)])
            if first:
                csv_writer.writerow(['username'] + list(sorted(profile)))
                first = False
            csv_writer.writerow(row)
            if i % 10 == 0:
                elapsed = datetime.datetime.now() - start
                secs = elapsed.days*60*60*24 + elapsed.seconds
                profiles_per_hour = (i+1.0)*3600/secs
                print '\n' + FETCH_STATUS % {
                    'elapsed': secs,
                    'completed': i + 1,
                    'deleted': len(deleted_profiles),
                    'remaining': len(usernames) - i - 1,
                    'secs_per_prof': secs/(i+1.0),
                    'prof_per_hour': profiles_per_hour,
                    'est_hours_left': (len(usernames) - i)/profiles_per_hour,
                }


def ReadUsernames():
    rows = [r for r in csv.reader(open(FLAGS.usernames_file))]
    idx = rows[0].index('usernames')
    return [row[idx] for row in rows[1:]]


def PrepareFlags(argv):
    '''Set up flags. Returns true if the flag settings are acceptable.'''
    try:
        argv = FLAGS(argv)  # parse flags
    except gflags.FlagsError, e:
        return False
    return FLAGS.session_cookie and FLAGS.usernames_file and FLAGS.outfile


def main(argv):
    if not PrepareFlags(argv):
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    usernames = ReadUsernames()
    if not usernames:
        print 'Failed to load usernames from %s' % FLAGS.usernames_file
        sys.exit(1)

    FetchProfilesWriteCSV(usernames)


if __name__ == '__main__':
        main(sys.argv)


