#!/usr/bin/python2.7
'''

First version created on 2012-06-25
@author: Everett Wetchler (evee746)
'''

# Native libraries
import csv
import datetime
import sys
import time

# Third party libraries
from BeautifulSoup import BeautifulSoup
import gflags
import requests


DEFAULT_COOKIE = '1780687262307760404%3a151924852332704912'
FLAGS = gflags.FLAGS
gflags.DEFINE_string('location', '94123', 'Zip or city name')
gflags.DEFINE_integer('age_min', 21, 'Minimum age to pull')
gflags.DEFINE_integer('age_max', 40, 'Maximum age to pull')
gflags.DEFINE_string(
    'session_cookie', DEFAULT_COOKIE,
    'See comments at the top for how to find your OKC session cookie.')


def prepare_flags(argv):
    '''Set up flags. Returns true if the flag settings are acceptable.'''
    try:
        argv = FLAGS(argv)  # parse flags
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        return False
    if not FLAGS.session_cookie:
        print 'Please specify --session_cookie'
        return False
    return True


def fetch_location(location):
    '''Queries OKCupid to get their location identifier number.

    The match search GET params require a "location id", which is an integer
    that represents a geographic area. We need to look up this id from the name
    of the city or region. For example, as of this writing,
    San Francisco will map to 4265540, NYC to 4335338.
    '''
    url = 'http://www.okcupid.com/locquery'
    params = {
        'func': 'query',
        'query': location,
    }
    r = requests.get(url, params=params).json()
    name = r['results'][0]['text']
    locid = r['results'][0]['locid']
    print 'Ahhh %s. Location id is %d' % (name, locid)
    return name, locid


def extract_usernames(html):
    '''Parse the match search result page for usernames.'''
    soup = BeautifulSoup(html)
    usernames = soup.findAll(name='div', attrs={'class': 'username'})
    usernames = [u.a.text for u in usernames]
    plaintext_usernames = []
    for u in usernames:
        try:
            plaintext_usernames.append(str(u))
        except UnicodeError, e:
            print 'Skipping funky username', u
    print 'Found %d viable usernames' % len(plaintext_usernames)
    # print plaintext_usernamess
    return plaintext_usernames


#####################################################################
# Some constants to help us build the correct query parameters
#####################################################################


HEIGHT_MAX = 99999
# The height param is in 254ths of an inch. 10,000ths of a meter. Yeah WTF.
INCH = 254
GENDER_HEIGHT_RANGES = [
    (60 * INCH, 70 * INCH),  # Lump all women < 5'0" or > 5'10"
    (64 * INCH, 75 * INCH),  # Lump all men < 5'4" or > 6'3"
]
# You can search by gender x orientation, each one having a bit. We can just
# lump all men and all women, since straight people are the large majority.
GENDER_TO_ORIENTATION_PARAM = [0b101010, 0b010101]  # Women, Men
WOMEN = 0
MEN = 1
GENDER_TO_STRING = ['Women', 'Men']
MATCH_DEFAULT_FILTERS = [
    '1,1',  # Have photos
    '3,25',  # Within 25 miles of location
    '5,604800',  # Online in the last week (604800 seconds)
    '35,2',  # Are single
]
MATCH_URL = 'http://www.okcupid.com/match'

#####################################################################
# Iterator to produce all the query slices we need
#####################################################################


class SliceGenerator():
    def __init__(self, locid):
        self.locid = locid
        self.age = FLAGS.age_min
        self.gender = WOMEN
        self.height_low = 0
        self.height_high = 0
        self.reset_height()
        self.stop = False

    def reset_height(self):
        self.height_low = 0
        self.height_high = GENDER_HEIGHT_RANGES[self.gender][0]

    def __iter__(self):
        return self

    def next(self):
        if self.stop:
            raise StopIteration
        filters = MATCH_DEFAULT_FILTERS + [
            '0,%d' % GENDER_TO_ORIENTATION_PARAM[self.gender],
            '2,%d,%d' % (self.age, self.age),  # Min and max age
            '10,%d,%d' % (self.height_low, self.height_high),
        ]
        print 'Filters: %s' % ' '.join(
            sorted(filters, key=lambda x: int(x.split(',', 1)[0])))
        params = {
            'locid': self.locid,
            'count': 1000, # Results to fetch (1000 is the max it tolerates)
        }
        for i, f in enumerate(filters):
            params['filter%d' % (i + 1)] = f
        print 'Next slice: %s, age %d, height (%d-%d"]' % (
            GENDER_TO_STRING[self.gender], self.age,
            self.height_low / INCH, self.height_high / INCH)
        # Move to the next position
        if self.height_high != HEIGHT_MAX:
            # Bump height
            self.height_low = self.height_high + 1
            self.height_high += INCH
            if self.height_high > GENDER_HEIGHT_RANGES[self.gender][1]:
                self.height_high = HEIGHT_MAX
        elif self.age != FLAGS.age_max:
            # Bump age, reset height to minimum
            self.age += 1
            self.reset_height()
        elif self.gender == WOMEN:
            # Done with women, move on to men. Reset age, height.
            self.gender = MEN
            self.age = FLAGS.age_min
            self.reset_height()
        else:
            # Done with everything
            self.stop = True
        return params, self.age, 'm' if self.gender else 'f'

    def calibrate(self, num_results):
        # TODO(everett): Smart adjustment of chunk sizes based on results.
        pass


#####################################################################
# Main
#####################################################################


def main(argv):
    if not prepare_flags(argv):
        print 'Invalid flag settings. Exiting.'
        sys.exit(1)

    cookies = {'session': FLAGS.session_cookie}
    print 'Cookies:', cookies
    location_name, location_id = fetch_location(FLAGS.location)
    cityabbrev = ''.join([word[0] for word in location_name.split()]).lower()
    outfile = 'usernames.%s.%s.csv' % (
        cityabbrev, datetime.date.today().strftime('%Y%m%d'))
    print 'Saving to:', outfile
    f = open(outfile, 'w')
    print >>f, 'age,sex,username'  # Header row
    all_usernames = []

    slice_gen = SliceGenerator(location_id)
    for params, age, gender in slice_gen:
        pass
        while True:
            print 'Sleeping...',
            time.sleep(2)  # Avoid throttling by OKC servers
            print 'querying...',
            r = requests.get(MATCH_URL, params=params, cookies=cookies)
            print 'done.'#, r.url
            if r.status_code != 200:
                print 'Request did not succeed. Will retry.'
            else:
                usernames = extract_usernames(r.text)
                # Write incrementally in case the program crashes
                for u in usernames:
                    print >>f, ','.join([str(age), gender, u])
                f.flush()
                slice_gen.calibrate(len(usernames))
                all_usernames.extend(usernames)
                break

    f.close()
    print 'Found %d total users' % len(all_usernames)


if __name__ == '__main__':
    main(sys.argv)
