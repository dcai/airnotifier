#!/bin/sh

#Notifiction
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: 31bde27540b03bb221f14a815a690582" -X POST -d "alert=AlertFromcURL&device=android&token=justtakethis" http://localhost:8801/notification/
