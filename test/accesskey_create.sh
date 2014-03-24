#!/bin/sh

#Token creation and deletion
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: 411b1577afcbad22202c2fae08e3af1e" -X POST -d 'contact=guy@test.name&description=need a key&permission=15&url=http://test.com&siteid=2222' http://localhost:8801/accesskeys/
