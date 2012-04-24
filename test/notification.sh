#!/bin/sh

#Notifiction
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: ca36ca26233a8178eb870a2e5229e803" -X POST -d "alert=AlertFromcURL&token=9116fc350fbcb47a0ed078e214b7f13a9e9cb02105d16d76381c700e1da6c2be" http://localhost:8801/notification/
