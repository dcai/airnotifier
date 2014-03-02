import urllib
import urllib2
import json
import time
import random
import requests
import logging

GCM_ENDPOINT = 'https://android.googleapis.com/gcm/send'

class GCMException(Exception): pass

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
    
    def send(self, regids, data=None, collapse_key=None,ttl=None, retries=5):
        if not regids:
            raise GCMException("Registration IDs cannot be empty")

        payload = self.build_request(regids, data, collapse_key, ttl)
        response = requests.post(self.endpoint, data=payload, headers={"content-type":"application/json", 'Authorization': 'key=%s' % self.apikey})
        if not response.status_code == 200:
            response.raise_for_status()
            
        return response

