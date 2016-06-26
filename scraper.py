#!/usr/bin/env python3
#
# Blackboard Mobile Scraper Demo
#
# Developed by github.com/adammw, released under MIT License
#

from api import BlackboardMobileApi
from credentials import username, password

try:
  import requests
except ImportError:
  sys.stderr.write("ERROR: requests module not available\nTo install requests:\n   pip install requests\n")
  sys.exit(1)

import os
import re
import json
import sys
import urllib.request, urllib.parse, urllib.error

SWIN_BASEURL="http://ilearn.swin.edu.au/"
SWIN_B2URL="https://ilearn.swin.edu.au/webapps/Bb-mobile-bb_bb60/"
SWIN_AUTHREALM="ilearn.swin.edu.au"
OUTPUT_DIR="./out"
CHUNK_SIZE=1024

bb = BlackboardMobileApi(SWIN_B2URL)
bb.login(username, password)
enrollments = bb.enrollments()
download_counter = 0

def folder_name(name):
  return re.sub("[^a-zA-Z0-9\-\.\(\)\,%\&_ ]","_", name)

def file_name(name):
  return re.sub("[^a-zA-Z0-9\-\.\(\)\,%\&_ ]","_", name)

def fix_url(url):
  if not url.startswith("http"):
    url = SWIN_BASEURL + url
  return url

def ovr_line(line):
  ts = os.get_terminal_size()
  if len(line) > ts.columns:
    line = line[0..ts.columns]
  sys.stdout.write("\r%s%s" % (line, ' '*(ts.columns - len(line))))
  sys.stdout.flush()

def writeJsonIndex(items, parent_obj, output_location):
  jf = open(output_location, "w")
  parent_obj['children'] = items
  json.dump(parent_obj, jf)
  jf.close()

def writeHtmlIndex(items, parent_obj, output_location):
  hf = open(output_location, "w")
  hf.write("<!doctype html>\n<html><head><title>" + parent_obj['name'] + "</title></head><body><h1>" + parent_obj['name'] + "</h1><hr />")
  for item in items:
    if item['is_folder']:
      hf.write("<h2><a href=\"" + folder_name(item['name']) + "/index.html\">" + item['name'] + "</a></h2>")
    else:
      if item['view_url']:
        hf.write("<h2><a href=\"" + fix_url(item['view_url']) + "\">" + item['name'] + "</a></h2>")
      else:
        hf.write("<h2>" + item['name'] + "</h2>")
      if item['body']:
        hf.write(item['body'])
      if len(item['attachments']):
        hf.write("<h3>Attachments</h3><ul>")
        for attachment in item['attachments']:
          hf.write("<li><a href=\"" + file_name(attachment['name']) + "\">" + attachment['link_label'] + "</a></li>")
        hf.write("</ul>")
    hf.write('<hr />')
  hf.close()

def download_attachment(attachment, out):
  try:
    if str(os.path.getsize(out)) == attachment.file_size:
      print("Skipping download of %s" % attachment.name)
      return
  except OSError:
    pass

  sys.stdout.write("\nStarting download of %s" % attachment.name)
  sys.stdout.flush()

  global download_counter
  download_counter = download_counter + 1
  uri = fix_url(attachment.uri)
  r = requests.get(uri, stream=True, cookies=bb.cookies)
  try:
    r.raise_for_status()
  except requests.HTTPError as err:
    print("\nERROR: %s" % err)
  downloaded_bytes = 0
  with open(out, 'wb') as f:
    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
      downloaded_bytes += len(chunk)
      totalsize = int(attachment.file_size)
      ovr_line("%d / %d (%d%%) %s" % (downloaded_bytes, totalsize, 100*downloaded_bytes/totalsize, attachment.name))
      f.write(chunk)

  ovr_line("%d / %s (100%%) %s" % (os.path.getsize(out), attachment.file_size, attachment.name))

for course in enrollments['courses']:
  print("Retrieving metadata for %s..." % (course.name))
  courseDir = "%s/%s" % (OUTPUT_DIR, folder_name(course.name))
  try:
    os.makedirs(courseDir)
  except OSError:
    pass

  courseObj = {
    'type': 'course',
    'bb_id': course.bb_id,
    'name': course.name,
    'course_id': course.course_id,
    'enrollment_date': course.enrollment_date,
  }

  contents = course.content()

  def recurseContents(contents, parent_obj, output_directory='.'):
    items = []
    sys.stdout.write(output_directory)
    for i in range(0,len(contents)):
      print("Traversing %s/ (%d/%d)" % (output_directory, i+1, len(contents)))

      content = contents[i]
      # Download the body text for the content
      detail = content.detail()

      # Locate and download attachments (sequentially)
      attachments = []
      for attachment in detail['attachments']:
        download_location = "%s/%s" % (output_directory, file_name(attachment.name))

        # work around bug where urls are generated for the wrong course
        match = re.search('/courses/1/(.+?)/content', attachment.uri)
        if match and match.group(1) != course.course_id:
          attachment.uri = attachment.uri.replace(match.group(1), course.course_id)

        attachments.append({
          'type': 'attachment',
          'name': attachment.name,
          'uri': attachment.uri,
          'file_size': attachment.file_size,
          'link_label': attachment.link_label,
          'date_modified': attachment.date_modified,
          'download_location': download_location
        })
        download_attachment(attachment, "%s/%s" % (courseDir, download_location))

      contentObj = {
        'type': 'content',
        'bb_id': content.bb_id,
        'name': content.name,
        'view_url': content.view_url,
        'date_modified': content.date_modified,
        'is_folder': content.is_folder,
        'body': detail['body'],
        'attachments': attachments
      }

      # Recurse through the children
      if content.is_folder:
        folder_output_directory = "%s/%s" % (output_directory, folder_name(content.name))

        try:
          os.makedirs("%s/%s" % (courseDir, folder_output_directory))
        except OSError:
          pass

        recurseContents(content.children, contentObj, folder_output_directory)

      #contentObj['children'] = children
      items.append(contentObj)
    #print "Finished folder %s, writing index..." % output_directory
    writeJsonIndex(items, parent_obj, "%s/%s/index.json" % (courseDir, output_directory))
    writeHtmlIndex(items, parent_obj, "%s/%s/index.html" % (courseDir, output_directory))
    return items
  recurseContents(contents, courseObj)

print("All files downloaded.")
