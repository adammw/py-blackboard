# 
# Blackboard Mobile API Library
# 
# Developed by github.com/adammw, released under MIT License
#

import sys
from urlparse import urlparse
import xml.etree.ElementTree as etree

try:
  import requests
except ImportError:
  sys.stderr.write("ERROR: requests module not available\nTo install requests:\n   pip install requests\n")
  sys.exit(1)

def log(msg, *args):
  #sys.stderr.write("%s\n" % (msg % args))
  pass

class BlackboardMobileApi:
  class BlackboardObject(object):
    def __init__(self, bb_id):
      self.bb_id = bb_id

  class Course(BlackboardObject):
    def __init__(self, bb_id, name = None, course_id = None, enrollment_date = None):
      super(BlackboardMobileApi.Course, self).__init__(bb_id)
      self.ContentItem = self.parent.ContentItem
      self.ContentItem.course = self
      self.name = name
      self.course_id = course_id
      self.enrollment_date = enrollment_date
    def __repr__(self):
      return '<Course bb_id="%s" course_id="%s">' % (self.bb_id, self.course_id)
    def content(self):
      def parse_item(map_item):
        item = None
        link_type = map_item.attrib['linktype']
        if link_type == 'announcements':
          log("TODO: parse annoncements")
          #TODO
        elif link_type == 'discussion_board':
          log("TODO: parse discussion_board")
          #TODO
        elif link_type == 'groups':
          log("TODO: parse groups")
          #TODO
        elif link_type == 'STAFF_INFO':
          log("TODO: parse STAFF_INFO")
          #TODO
        elif link_type == 'MODULE_PAGE':
          log("TODO: parse MODULE_PAGE")
          #TODO
        elif link_type == 'DIVIDER':
          log("TODO: parse DIVIDER")
          #TODO
        elif link_type == 'course_tools_area':
          log("TODO: parse course_tools_area")
          #TODO
        elif link_type == 'student_gradebook':
          log("TODO: parse student_gradebook")
          #TODO
        elif link_type == 'course_email':
          log("TODO: parse course_email")
          #TODO
        elif link_type == 'Bb-wiki':
          log("TODO: parse Bb-wiki")
          #TODO
        elif map_item.attrib.has_key('contentid'):
          item = self.ContentItem(bb_id = map_item.attrib['contentid'], name = map_item.attrib['name'], view_url = map_item.attrib['viewurl'], date_modified = map_item.attrib['datemodified'], is_folder = (map_item.attrib['isfolder'] == "true"))
          children = map_item.find('children')
          if children is not None:
            for child in children.findall('map-item'):
              child = parse_item(child)
              if child is not None:
                item.children.append(child)
        else:
          log("Warning: unhandled link_type %s" % link_type)
        return item

      resp = self.parent.request('/courseMap', params={'course_id': self.bb_id})
      content = []
      for map_item in resp.find('map').findall('map-item'):
        item = parse_item(map_item)
        if item is not None:
          content.append(item)
      return content

  class Organisation(BlackboardObject):
    def __init__(self, bb_id, name = None, course_id = None, enrollment_date = None):
      super(BlackboardMobileApi.Organisation, self).__init__(bb_id)
      self.name = name
      self.course_id = course_id
      self.enrollment_date = enrollment_date

  class ContentItem(BlackboardObject):
    def __init__(self, bb_id, name = None, view_url = None, date_modified = None, is_folder = False):
      super(BlackboardMobileApi.ContentItem, self).__init__(bb_id)
      self.Attachment = self.parent.Attachment
      self.Attachment.content = self
      self.name = name
      self.view_url = view_url
      self.date_modified = date_modified
      self.is_folder = is_folder
      self.children = []
    def __repr__(self):
      return '<ContentItem bb_id="%s" name="%s" is_folder="%s">' % (self.bb_id, self.name, self.is_folder)
    def detail(self, rich_content_level = 'RICH'):
      resp = self.parent.request('/contentDetail', params={'course_id': self.course.bb_id, 'content_id': self.bb_id, 'rich_content_level': rich_content_level})
      content = resp.find('content')
      attachments = []
      attachments_el = content.find('attachments')
      if attachments_el is not None:
        for attachment in attachments_el.findall('attachment'):
          attachments.append(self.Attachment(uri = attachment.attrib['uri'], name = attachment.attrib['name'], file_size = attachment.attrib['filesize'], link_label = attachment.attrib['linkLabel'], date_modified = attachment.attrib['modifiedDate']))
      body = content.find('body')
      return {'attachments': attachments, 'body': body.text}

  class Attachment(BlackboardObject):
    def __init__(self, uri, name = None, file_size = None, link_label = None, date_modified = None):
      self.uri = uri
      self.name = name
      self.file_size = file_size
      self.link_label = link_label
      self.date_modified = date_modified
    def __repr__(self):
      return '<Attachment label="%s" uri="%s">' % (self.link_label, self.uri)

  def __init__(self, b2_url):
    self.b2_url = b2_url
    self.cookies = dict()
    self.Course.parent = self
    self.Organisation.parent = self
    self.ContentItem.parent = self

    # Check that b2_url is valid
    if not b2_url:
      raise Exception("Required parameter b2_url not specified")

    parsed_url = urlparse(b2_url)
    if not parsed_url.netloc:
      raise Exception("Invalid b2_url specified")

    if parsed_url.scheme != 'https':
      log("Warning: Not using SSL, your password will be exposed in plaintext!")
    
    # We don't want a trailing slash, we do that ourselves
    if b2_url.endswith('/'):
      self.b2_url = self.b2_url[0:-1]

  def request(self, endpoint, **kwargs):
    log('bb#request(endpoint=\'%s\')', endpoint)
    kwargs['cookies'] = self.cookies
    kwargs['method'] = kwargs.get('method', 'get')
    r = requests.request(url = self.b2_url + endpoint, **kwargs)
    self.cookies.update(r.cookies)
    if r.status_code == 200:
      resp = etree.fromstring(r.text.encode('utf-8'))
      return resp
    else:
      return None

  def login(self, username, password):
    log('bb#login(username=%s, password=%s)', username, '*'*len(password))
    resp = self.request('/sslUserLogin', data={ 'username': username, 'password': password }, method='post')
    self.user_id = resp.attrib['userid']
    return self.user_id

  def enrollments(self, course_type='ALL'):
    log('bb#enrollments(course_type=%s)', course_type)
    resp = self.request('/enrollments', params={'course_type': course_type})
    courses = []
    organisations = []
    for course in resp.find('courses').findall('course'):
      courses.append(self.Course(bb_id = course.attrib['bbid'], name = course.attrib['name'], course_id = course.attrib['courseid'], enrollment_date = course.attrib['enrollmentdate']))
    for org in resp.find('orgs').findall('org'):
      organisations.append(self.Organisation(bb_id = course.attrib['bbid'], name = course.attrib['name'], course_id = course.attrib['courseid'], enrollment_date = course.attrib['enrollmentdate']))
    return {'courses': courses, 'organisations': organisations}
