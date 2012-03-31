#!/bin/sh

#Token creation and deletion
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: bargainmate" -H "X-AN-APP-KEY: XXX" -X GET http://localhost:8000/objects/cups/4f770f6c1f5c7d6f9f000000
