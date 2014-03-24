#!/bin/sh

#Notifiction
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: 411b1577afcbad22202c2fae08e3af1e" -X POST -d "channel=default&alert=Testing broadcast" http://localhost:8801/broadcast/

