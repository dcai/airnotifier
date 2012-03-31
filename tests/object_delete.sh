#!/bin/sh

#Token creation and deletion
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: bargainmate" -H "X-AN-APP-KEY: XXX" -X DELETE http://localhost:8000/objects/cups/4f770fde1f5c7d6f9f000000
