#!/bin/sh

#Notifiction
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -X POST -d "alert=AlertFromcURL&token=9116fc350fbcb47a0ed078e214b7f13a9e9cb02105d16d76381c700e1da6c2be" http://push.tux.im/notification/

