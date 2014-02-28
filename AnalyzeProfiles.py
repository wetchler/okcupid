#!/usr/bin/python2.7
'''
Created on Jun 30, 2012

@author: everettw
'''

import code
import sqlite3
import sys
import FetchProfiles
import ReadingLevel

class Profile(object):
  def __init__(self):
    pass

def ParseTableSchema(schema):
  params = schema.split("(")[1].split(")")[0].split(", ")
  return [tuple(p.split()[:2]) for p in params]

def ReadProfiles(db, max_to_read=-1):
  con = sqlite3.connect(db)
  profiles = []
  with con:
    cur = con.cursor()
    unused = cur.execute("select * from sqlite_master where name = 'Profiles';")
    schema_create = str(cur.fetchone()[-1])
    if not schema_create.startswith("CREATE TABLE"):
      print "ERROR: schema create statement did not start with 'CREATE TABLE'"
      return None
    params = ParseTableSchema(schema_create)
    unused = cur.execute("select * from Profiles")
    processed = 0
    while True:
      processed += 1
      if max_to_read > 0 and processed > max_to_read:
        print "Stopping after loading", max_to_read
        break
      if processed % 1000 == 0:
        print "Reading profile #%d" % processed
      row = cur.fetchone()
      if not row:
        print "No more profiles to parse"
        break
      p = Profile()
      p.fields = []
      for col,value in enumerate(row):
        field = params[col][0]
        if params[col][1] == "TEXT":
          value = str(value)
        p.__setattr__(field, value)
        p.fields.append(field)
        if field.startswith('essay'):
          p.__setattr__(field + '_scores', ReadingLevel.TextScores(value))
      profiles.append(p)
  return profiles

def main(argv):
  # Example usage. This can all be done from the command line ad hoc.
  profiles = ReadProfiles('profiles.db.sf.20120701',10)
  # for p in profiles:
  #   print p.username, p.sex, p.age, p.drugs, p.essay0_scores.level
  code.interact()


if __name__ == '__main__':
    main(sys.argv)


