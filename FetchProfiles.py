#!/usr/bin/python2.7
'''
One by one, fetch profile pages for OKCupid users. The input to this script
is a file with a list of usernames of profiles to pull,

Original version created on Jun 25, 2012

@author: Everett Wetchler (evee746)
'''

import csv
import datetime
import random
import sys
import time

from BeautifulSoup import BeautifulSoup, UnicodeDammit
import gflags
import requests

DEFAULT_COOKIE = '1780687262307760404%3a151924852332704912'
FLAGS = gflags.FLAGS
gflags.DEFINE_string('outfile', 'profiles.csv', 'Filename for output')
gflags.DEFINE_boolean('pull_essays', False,
                      'If True, pulls free responses sections. If False, '
                      'just basic profile details.')
gflags.DEFINE_string('session_cookie', DEFAULT_COOKIE, '')
gflags.DEFINE_string(
    'usernames_file', 'usernames.csv', 'File with usernames to fetch')
gflags.DEFINE_string(
    'completed_usernames_file', 'completed_usernames.csv',
    'File with usernames we have already fetched')


SLEEP_BETWEEN_QUERIES = 2
PROFILE_URL = "http://www.okcupid.com/profile/%s"


def pull_profile_and_essays(username):
    '''Given a username, fetches the profile page and parses it.'''
    url = PROFILE_URL % username
    print "Fetching profile HTML for", username + "... ",
    html = None
    for i in range(3):
        if i > 0:
            print "Retrying...",
        try:
            r = requests.get(url, cookies={'session': FLAGS.session_cookie})
            if r.status_code != 200:
                print "Error, HTTP status code was %d, not 200" % r.status_code
            else:
                html = r.content
                break
        except requests.exceptions.RequestException, e:
            print "Error completing HTTP request:", e
    if not html:
        print "Giving up."
        return None, None
    print "Parsing..."
    profile, essays = parse_profile_html(html)
    return profile, essays


def parse_profile_html(html):
    '''Parses a user profile page into the data fields and essays.

    It turns out parsing HTML, with all its escaped characters, and handling
    wacky unicode characters, and writing them all out to a CSV file (later),
    is a pain in the ass because everything that is not ASCII goes out of its
    way to make your life hard.

    During this function, we handle unescaping of html special
    characters. Later, before writing to csv, we force everything to ASCII,
    ignoring characters that don't play well.
    '''
    html = html.lower()
    soup = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES)
    NA = 'NA'
    basics_soup = soup.find(name = 'div', attrs = {'id': 'basic_info'})
    details_soup = soup.find(name='div', attrs={'id':'profile_details'})
    essays_soup = soup.find(name='div', attrs={'id':'main_column'})
    if not (basics_soup and details_soup and essays_soup):
        print 'Profile likely deleted. Missing expected html structure.'
        return None, None
    profile = {}
    # Extract top-line profile data (age, gender, city) from tags like
    # <span id='ajax_gender'>Female</span>
    for tag in basics_soup.findAll(name = 'span')[1:]:  # Skip 'Last Online'
        feature, value = tag['id'].split('_', 1)[1], tag.text.strip()
        print feature, value
        profile[feature] = value
    # Extract personal data items from tags like
    # <dd id='ajax_bodytype'>Female</span>
    for tag in details_soup.findAll(name = 'dd'):
        try:
            feature, value = tag['id'].split('_', 1)[1], tag.text.strip()
            if feature == 'height':
                # Special case height to parse into inches
                print value
                feet, inches = [int(x[:-1]) for x in value.split()[:2]]
                value = str(int(feet) * 12 + int(inches))
            print feature, value
            profile[feature] = value
        except KeyError:
            continue
    # Essays
    essays = {}
    for e in essays_soup.findAll('div', recursive=False):
        if e['id'].startswith('essay_'):
            essay_id = int(e['id'].split('essay_')[1])
            title = e.a.text
            user_response = ''.join(
                str(x) for x in e.div.div.contents).replace('<br />', '').strip()
            essays[essay_id] = (title, user_response)
        elif e['id'] == 'what_i_want':
            # These are high-level details about what the user wants in a date
            # TODO: parse and incorporate these as profile features
            pass
    return profile, essays


TIMING_MSG = '''%(elapsed)ds elapsed, %(completed)d profiles fetched, \
%(skipped)d skipped, \
%(remaining)d left, %(secs_per_prof).1fs per profile, \
%(prof_per_hour).0f profiles per hour, \
%(est_hours_left).1f hours left'''


def compute_elapsed_seconds(elapsed):
    '''Given a timedelta, returns a float of total seconds elapsed.'''
    return (elapsed.days * 60 * 60 * 24 +
            elapsed.seconds + elapsed.microseconds / 1.0e6)


def read_usernames(filename):
    '''Extracts usernames from the given file, returning a sorted list.

    The file should either be:
        1) A list of usernames, one per line
        2) A CSV file with a 'username' column (specified in its header line)
    '''
    try:
        rows = [r for r in csv.reader(open(filename))]
        try:
            idx = rows[0].index('username')
            unames = [row[idx].lower() for row in rows[1:]]
        except ValueError:
            unames = [r[0] for r in rows]
        return sorted(set(unames))
    except IOError, e:
        # File doesn't exist
        return []


def prepare_flags(argv):
    '''Set up flags. Returns true if the flag settings are acceptable.'''
    try:
        argv = FLAGS(argv)  # parse flags
    except gflags.FlagsError, e:
        return False
    return FLAGS.session_cookie and FLAGS.usernames_file and FLAGS.outfile


def main(argv):
    if not prepare_flags(argv):
        print 'Usage: %s ARGS\\n%s' % (sys.argv[0], FLAGS)
        sys.exit(1)

    usernames_to_fetch = read_usernames(FLAGS.usernames_file)
    if not usernames_to_fetch:
        print 'Failed to load usernames from %s' % FLAGS.usernames_file
        sys.exit(1)
    print 'Read %d usernames to fetch' % len(usernames_to_fetch)

    completed = read_usernames(FLAGS.completed_usernames_file)
    if completed:
        usernames_to_fetch = sorted(set(usernames_to_fetch) - set(completed))
        print '%d usernames were already fetched, leaving %d to do' % (
            len(completed), len(usernames_to_fetch))

    start = datetime.datetime.now()
    last = start
    headers_written = bool(completed)  # Only write headers if file is empty
    skipped = 0
    profile_writer = csv.writer(open(FLAGS.outfile, 'ab'))
    completed_usernames_writer = open(FLAGS.completed_usernames_file, 'ab')
    N = len(usernames_to_fetch)
    # Fetch profiles
    for i, username in enumerate(usernames_to_fetch):
        # ** Critical ** so OKC servers don't notice and throttle us
        if i > 0:
            print "Sleeping..."
            # elapsed = datetime.datetime.now() - last
            # elapsed_sec = elapsed.seconds * 1.0 + elapsed.microseconds / 1.0e6
            # time.sleep(max(0, SLEEP_BETWEEN_QUERIES - elapsed_sec))
            time.sleep(SLEEP_BETWEEN_QUERIES)
        # Go ahead
        last = datetime.datetime.now()
        profile, essays = pull_profile_and_essays(username)
        # TODO: Save essays to separate CSV (ignoring for now)
        if not profile:
            skipped += 1
        else:
            if not headers_written:
                header_row = ['username'] + list(sorted(profile))
                profile_writer.writerow(
                    [x.encode('ascii', 'ignore') for x in header_row])
                headers_written = True
            row = tuple([username] + [profile[k] for k in sorted(profile)])
            row = [field.encode('ascii', 'ignore') for field in row]
            print row
            profile_writer.writerow(row)
        print >>completed_usernames_writer, username
        completed_usernames_writer.flush()
        if i % 10 == 0:
            elapsed = datetime.datetime.now() - start
            secs = compute_elapsed_seconds(elapsed)
            profiles_per_hour = (i+1.0)*3600/secs
            print '\n' + TIMING_MSG % {
                'elapsed': secs,
                'completed': i + 1,
                'skipped': skipped,
                'remaining': N - i - 1,
                'secs_per_prof': secs/(i+1.0),
                'prof_per_hour': profiles_per_hour,
                'est_hours_left': (N - i)/profiles_per_hour,
            }



if __name__ == '__main__':
        main(sys.argv)


