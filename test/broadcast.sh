#!/bin/sh

#Notifiction
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: 04005c30-9685-4924-ad6a-41bd15e8d294" -X POST -d "channel=default&alert=Testing broadcast" http://localhost:8801/broadcast/

