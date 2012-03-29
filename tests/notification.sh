#!/bin/sh

#Notifiction
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: bargainmate" -H "X-AN-APP-KEY: XXX" -X POST -d "alert=AlertFromcURL&token=9116fc350fbcb47a0ed078e214b7f13a9e9cb02105d16d76381c700e1da6c2be" http://localhost:8000/notification/
