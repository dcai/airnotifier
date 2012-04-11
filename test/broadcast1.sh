#!/bin/sh

#Notifiction
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -X POST -d "alert=AlertFromcURL" http://localhost:8000/broadcast/
