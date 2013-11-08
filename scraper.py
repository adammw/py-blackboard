#!/usr/bin/env python
# 
# Blackboard Mobile Scraper Demo
# 
# Developed by github.com/adammw, released under MIT License
#

from api import BlackboardMobileApi
from credentials import username, password

import os
import re
import json
import sys
import urllib

SWIN_BASEURL="http://ilearn.swin.edu.au/"
SWIN_B2URL="https://ilearn.swin.edu.au/webapps/Bb-mobile-bb_bb60/"
OUTPUT_DIR="./out"

bb = BlackboardMobileApi(SWIN_B2URL)
bb.login(username, password)
enrollments = bb.enrollments()

def folder_name(name):
  return re.sub("[^a-zA-Z0-9\-\.\(\)\,%\&_ ]","_", name.encode('utf-8'))

def file_name(name):
  return re.sub("[^a-zA-Z0-9\-\.\(\)\,%\&_ ]","_", name.encode('utf-8'))

def writeJsonIndex(items, parent_obj, output_location):
  jf = open(output_location, "w")
  parent_obj['children'] = items
  json.dump(parent_obj, jf)
  jf.close()

def writeHtmlIndex(items, parent_obj, output_location):
  hf = open(output_location, "w")
  hf.write("<!doctype html>\n<html><head><title>" + parent_obj['name'].encode('utf-8') + "</title></head><body><h1>" + parent_obj['name'].encode('utf-8') + "</h1><hr />")
  for item in items:
    if item['is_folder']:
      hf.write("<h2><a href=\"" + folder_name(item['name']) + "/index.html\">" + item['name'] + "</a></h2>")
    else:
      if item['view_url']:
        hf.write("<h2><a href=\"" + item['view_url'] + "\">" + item['name'].encode('utf-8') + "</a></h2>")
      else:
        hf.write("<h2>" + item['name'].encode('utf-8') + "</h2>")
      if item['body']:
        hf.write(item['body'].encode('utf-8'))
      if len(item['attachments']):
        hf.write("<h3>Attachments</h3><ul>")
        for attachment in item['attachments']:
          hf.write("<li><a href=\"" + file_name(attachment['name']) + "\">" + attachment['link_label'].encode('utf-8') + "</a></li>")
        hf.write("</ul>")
    hf.write('<hr />')
  hf.close()

download_tasks = []
def add_download_task(attachment, out):
  download_tasks.append((attachment, out))

for course in enrollments['courses']:
  print "Retrieving metadata for %s..." % (course.name)
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
      sys.stdout.write("\r%s (%d/%d)" % (output_directory, i+1, len(contents)))
      sys.stdout.flush()

      content = contents[i]
      # Download the body text for the content
      detail = content.detail()

      # Locate and start downloading attachments
      attachments = []
      for attachment in detail['attachments']:
        download_location = "%s/%s" % (output_directory, file_name(attachment.name))
        attachments.append({
          'type': 'attachment',
          'name': attachment.name,
          'uri': attachment.uri,
          'file_size': attachment.file_size,
          'link_label': attachment.link_label,
          'date_modified': attachment.date_modified,
          'download_location': download_location
        })
        add_download_task(attachment, "%s/%s" % (courseDir, download_location))
      
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
        
        print "" # new line
        #print "Traversing folder %s" % folder_output_directory
        try:
          os.makedirs("%s/%s" % (courseDir, folder_output_directory))
        except OSError:
          pass

        recurseContents(content.children, contentObj, folder_output_directory)

      #contentObj['children'] = children
      items.append(contentObj)
    print "" # new line
    #print "Finished folder %s, writing index..." % output_directory
    writeJsonIndex(items, parent_obj, "%s/%s/index.json" % (courseDir, output_directory))
    writeHtmlIndex(items, parent_obj, "%s/%s/index.html" % (courseDir, output_directory))
    return items
  recurseContents(contents, courseObj)
  break # only do one for testing

# Count download tasks
print "Starting downloading of ", len(download_tasks), "files"
for task_no in range(0, len(download_tasks)):
  def progress(blocks, blocksize, totalsize):
    downloaded = blocks*blocksize
    sys.stdout.write("\r%d / %d (%d%%)         " % (downloaded, totalsize, 100*downloaded/totalsize))
    sys.stdout.flush()
  task = download_tasks[task_no]
  print ""
  print "Downloading (%d/%d) - %s" % (task_no + 1, len(download_tasks), task[1])
  print "Connecting.."
  uri = task[0].uri
  if not uri.startswith("http"):
    uri = SWIN_BASEURL + uri
  urllib.urlretrieve(uri, task[1], progress)
print ""
print "All files downloaded."