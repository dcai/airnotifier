#!/bin/sh

#Notifiction
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: 71df6e86-2fdf-432f-bf80-7104143e9769" -X POST -d "alert=Testing broadcast" http://push.tux.im/broadcast/

