#!/usr/bin/env python
# 
# Blackboard Mobile Scraper Demo
# 
# Developed by github.com/adammw, released under MIT License
#

from api import BlackboardMobileApi
from credentials import username, password

SWIN_B2URL="https://ilearn.swin.edu.au/webapps/Bb-mobile-bb_bb60/"

bb = BlackboardMobileApi(SWIN_B2URL)
bb.login(username, password)
enrollments = bb.enrollments()

def dumpContents(contents):
  for content in contents:
    print content
    print content.detail()
    if len(content.children):
      dumpContents(content.children)

for course in enrollments['courses']:
  print course
  contents = course.content()
  dumpContents(contents)