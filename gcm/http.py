import urllib
import urllib2
import json
import time
import random
import requests
import logging

GCM_ENDPOINT = 'https://android.googleapis.com/gcm/send'

class GCMException(Exception): pass

class GCMNotRegisteredException(GCMException):
    def __init__(self, regids):
        Exception.__init__(self, "Not Registered")
        self.regids = regids

class GCMInvalidRegistrationException(GCMException):
    def __init__(self, regids):
        Exception.__init__(self, "Invalid Registration")
        self.regids = regids

class GCM(object):
    def __init__(self, projectnumber, apikey, appname, instanceid=0, endpoint=GCM_ENDPOINT):
        self.projectnumber = projectnumber
        self.apikey = apikey
        self.appname = appname
        self.instanceid = instanceid
        self.endpoint = endpoint


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

    def send(self, regids, data=None, collapse_key=None, ttl=None, retries=5):
        if not regids:
            raise GCMException("Registration IDs cannot be empty")

        payload = self.build_request(regids, data, collapse_key, ttl)
        response = requests.post(self.endpoint, data=payload, headers={"content-type":"application/json", 'Authorization': 'key=%s' % self.apikey})
        if response.status_code == 400:
            raise GCMException('Request could not be parsed as JSON, or it contained invalid fields.')
        elif response.status_code == 401:
            raise GCMException('There was an error authenticating the sender account.')
        elif response.status_code >= 500:
            raise GCMException('GCM server is temporarily unavailable .')

        responsedata = response.json()

        # Handling errors
        if 'failure' in responsedata and responsedata['failure'] is not 0:
            errors = self.reverse_response_info('error', regids, responsedata['results'])
            for errorkey, packed_rregisteration_ids in errors.items():
                # Check for errors and act accordingly
                if errorkey == 'NotRegistered':
                    # Should remove the registration ID from your server database
                    # because the application was uninstalled from the device or
                    # it does not have a broadcast receiver configured to receive
                    raise GCMNotRegisteredException(packed_rregisteration_ids)
                elif errorkey == 'InvalidRegistration':
                    # You should remove the registration ID from your server
                    # database because the application was uninstalled from the device or it does not have a broadcast receiver configured to receive
                    raise GCMInvalidRegistrationException(packed_rregisteration_ids)
                elif errorkey == 'MismatchSenderId':
                    """
                    A registration ID is tied to a certain group of senders. When an application registers for GCM usage,
                    it must specify which senders are allowed to send messages. Make sure you're using one of those when
                    trying to send messages to the device. If you switch to a different sender, the existing registration
                    IDs won't work.
                    """
                    raise GCMException('Mismatch sender Id')
                elif errorkey == 'MissingRegistration':
                    """
                    Check that the request contains a registration ID (either in the registration_id parameter in a
                    plain text message, or in the registration_ids field in JSON).
                    """
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

