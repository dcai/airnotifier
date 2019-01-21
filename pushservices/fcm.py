#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Server Side FCM sample.

Firebase Cloud Messaging (FCM) can be used to send messages to clients on iOS,
Android and Web.

This sample uses FCM to send two types of messages to clients that are subscribed
to the `news` topic. One type of message is a simple notification message (display message).
The other is a notification message (display notification) with platform specific
customizations. For example, a badge is added to messages that are sent to iOS devices.
"""

import argparse
import json
import requests
from . import PushService
import json
import time
from util import strip_tags

from oauth2client.service_account import ServiceAccountCredentials

PROJECT_ID = 'foleo'
BASE_URL = 'https://fcm.googleapis.com'
FCM_ENDPOINT = 'v1/projects/' + PROJECT_ID + '/messages:send'
FCM_URL = BASE_URL + '/' + FCM_ENDPOINT
SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

def _get_access_token(json_string):
  """Retrieve a valid access token that can be used to authorize requests.
  :return: Access token.
  """
  data = json.loads(json_string)
  credentials = ServiceAccountCredentials.from_json_keyfile_dict(data, SCOPES)
  access_token_info = credentials.get_access_token()
  return access_token_info
  #  return access_token_info.access_token

def send():
  """Send HTTP request to FCM with given message.

  Args:
    fcm_message: JSON object that will make up the body of the request.
  """
  fcm_message = _build_common_message()
  # [START use_access_token]

  headers = {
    'Authorization': 'Bearer ' + _get_access_token(),
    'Content-Type': 'application/json; UTF-8',
  }
  # [END use_access_token]
  resp = requests.post(FCM_URL, data=json.dumps(fcm_message), headers=headers)

  if resp.status_code == 200:
      print "11111"
      print('1111Message sent to Firebase for delivery, response:')
      print(resp.text)
      print "11111"
  else:
      print('Unable to send message to Firebase')
      print(resp.text)

def _send_fcm_message(fcm_message):
  """Send HTTP request to FCM with given message.

  Args:
    fcm_message: JSON object that will make up the body of the request.
  """
  # [START use_access_token]
  headers = {
    'Authorization': 'Bearer ' + _get_access_token(),
    'Content-Type': 'application/json; UTF-8',
  }
  # [END use_access_token]
  resp = requests.post(FCM_URL, data=json.dumps(fcm_message), headers=headers)

  if resp.status_code == 200:
    print('Message sent to Firebase for delivery, response:')
    print(resp.text)
  else:
    print('Unable to send message to Firebase')
    print(resp.text)

def _build_common_message():
  """Construct common notifiation message.

  Construct a JSON object that will be used to define the
  common parts of a notification message that will be sent
  to any app instance subscribed to the news topic.
  """
  return {
    'message': {
      'topic': 'news',
      'notification': {
        'title': 'FCM Notification',
        'body': 'Notification from FCM'
      }
    }
  }

def _build_override_message():
  """Construct common notification message with overrides.

  Constructs a JSON object that will be used to customize
  the messages that are sent to iOS and Android devices.
  """
  fcm_message = _build_common_message()

  apns_override = {
    'payload': {
      'aps': {
        'badge': 1
      }
    },
    'headers': {
      'apns-priority': '10'
    }
  }

  android_override = {
    'notification': {
      'click_action': 'android.intent.action.MAIN'
    }
  }

  fcm_message['message']['android'] = android_override
  fcm_message['message']['apns'] = apns_override

  return fcm_message

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--message')
  args = parser.parse_args()
  if args.message and args.message == 'common-message':
    common_message = _build_common_message()
    print('FCM request body for message using common notification object:')
    print(json.dumps(common_message, indent=2))
    _send_fcm_message(common_message)
  elif args.message and args.message == 'override-message':
    override_message = _build_override_message()
    print('FCM request body for override message:')
    print(json.dumps(override_message, indent=2))
    _send_fcm_message(override_message)
  else:
    print('''Invalid command. Please use one of the following commands:
python messaging.py --message=common-message
python messaging.py --message=override-message''')

class FCMClient(PushService):
    def __init__(self, project_id, jsonkey, appname, instanceid=0, endpoint=FCM_ENDPOINT):
        self.project_id = project_id
        self.jsonkey = jsonkey
        self.appname = appname
        self.instanceid = instanceid
        self.endpoint = endpoint
        data = json.loads(jsonkey)
        self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(data, SCOPES)


    def build_request(self, regids, data, collapse_key, ttl):
        payload = {'registration_ids': regids}
        if data:
            payload['data'] = data

        if ttl >= 0:
            payload['time_to_live'] = ttl

        if collapse_key:
            payload['collapse_key'] = collapse_key

        return json.dumps(payload)

    def reverse_response_info(self, key, ids, results):
        zipped = zip(ids, results)
        # Get items having error key
        filtered = filter(lambda x: key in x[1], zipped)
        # Expose error value
        exposed = [(s[0], s[1][key]) for s in filtered]
        errors = {}
        for k, v in exposed:
            if v not in errors:
                errors[v] = []
            errors[v].append(k)
        return errors

    def process(self, **kwargs):
        self.access_token_info = self.credentials.get_access_token()

        print self.access_token_info

        fcm_message = _build_common_message()
        headers = {
            'Authorization': 'Bearer %s' % self.access_token_info.access_token,
            'Content-Type': 'application/json; UTF-8',
        }
        # [END use_access_token]
        #  gcmparam = kwargs.get('gcm', {})
        #  collapse_key = gcmparam.get('collapse_key', None)
        #  ttl = gcmparam.get('ttl', None)
        #  alert = kwargs.get('alert', None)
        #  data = gcmparam.get('data', {})
        #  if 'message' not in data:
            #  data['message'] = kwargs.get('alert', '')
        #  appdb = kwargs.get('appdb', None)
        #  return self.send(kwargs['token'], data=data, collapse_key=collapse_key, ttl=ttl, appdb=appdb)
        resp = requests.post(FCM_URL, data=json.dumps(fcm_message), headers=headers)

        if resp.status_code == 200:
            print('Message sent to Firebase for delivery, response:')
            print(resp.text)
        else:
            print('Unable to send message to Firebase')
            print(resp.text)

    def send(self, regids, data=None, collapse_key=None, ttl=None, retries=5, appdb=None):
        '''
        Send message to google gcm endpoint
        :param regids: list
        :param data: dict
        :param collapse_key: string
        :param ttl: int
        :param retries: int
        :param appdb: Database
        '''
        if not regids:
            raise GCMException("Registration IDs cannot be empty")

        payload = self.build_request(regids, data, collapse_key, ttl)
        headers = {"content-type":"application/json", 'Authorization': 'key=%s' % self.apikey}
        response = requests.post(self.endpoint, data=payload, headers=headers)

        if response.status_code == 400:
            raise GCMException('Request could not be parsed as JSON, or it contained invalid fields.')
        elif response.status_code == 401:
            raise GCMException('There was an error authenticating the sender account.')
        elif response.status_code >= 500:
            raise GCMException('GCMClient server is temporarily unavailable .')

        responsedata = response.json()
        if responsedata.get('canonical_ids', 0) != 0:
            # means we need to take a look at results, looking for registration_id key
            responsedata['canonical_ids'] = self.reverse_response_info('registration_id', regids, responsedata['results'])

        # Handling errors
        if responsedata.get('failure', 0) != 0:
            # means we need to take a look at results, looking for error key
            errors = self.reverse_response_info('error', regids, responsedata['results'])
            for errorkey, packed_rregisteration_ids in errors.items():
                # Check for errors and act accordingly
                if errorkey == 'NotRegistered':
                    # Should remove the registration ID from your server database
                    # because the application was uninstalled from the device or
                    # it does not have a broadcast receiver configured to receive
                    if appdb is not None:
                        appdb.tokens.delete_many({'token': {'$in': packed_rregisteration_ids}})
                        self.add_to_log(appdb, 'GCM', 'Cleaned unregistered tokens: ' + ', '.join(packed_rregisteration_ids))
                    else:
                        raise GCMNotRegisteredException(packed_rregisteration_ids)
                elif errorkey == 'InvalidRegistration':
                    # You should remove the registration ID from your server
                    # database because the application was uninstalled from the device or it does not have a broadcast receiver configured to receive
                    if appdb is not None:
                        appdb.tokens.delete_many({'token': {'$in': packed_rregisteration_ids}})
                        self.add_to_log(appdb, 'GCM', 'Cleaned invalid tokens: ' + ', '.join(packed_rregisteration_ids))
                    else:
                        raise GCMInvalidRegistrationException(packed_rregisteration_ids)
                elif errorkey == 'MismatchSenderId':
                    '''
                    A registration ID is tied to a certain group of senders. When an application registers for GCMClient usage,
                    it must specify which senders are allowed to send messages. Make sure you're using one of those when
                    trying to send messages to the device. If you switch to a different sender, the existing registration
                    IDs won't work.
                    '''
                    raise GCMException('Mismatch sender Id')
                elif errorkey == 'MissingRegistration':
                    '''
                    Check that the request contains a registration ID (either in the registration_id parameter in a
                    plain text message, or in the registration_ids field in JSON).
                    '''
                    raise GCMException('Missing registration')
                elif errorkey == 'MessageTooBig':
                    raise GCMException('Message too big')
                elif errorkey == 'InvalidDataKey':
                    raise GCMException('Invalid data key')
                elif errorkey == 'InvalidTtl':
                    raise GCMException('Invalid Ttl')
                elif errorkey == 'InvalidPackageName':
                    raise GCMException('Invalid package name')
                raise GCMException('Unknown error, contact admin')

        return response

    def add_to_log(self, appdb, action, info=None, level="info"):
        log = {}
        log['action'] = strip_tags(action)
        log['info'] = strip_tags(info)
        log['level'] = strip_tags(level)
        log['created'] = int(time.time())
        if appdb is not None:
            appdb.logs.insert(log, safe=True)
