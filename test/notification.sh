#!/bin/sh

#Notifiction
APPKEY=411b1577afcbad22202c2fae08e3af1e
ALERT=ThisIsAnNotificationMessage
DEVICE=android
TOKEN=APA91bFKS2u3gxuncfvP--rQfT3aIim5nb7pNu4vai-pL0bv96NLojUzXbG8mTjiYJU5rQX-9UnnoTTYhhJUOUhjv19dP_7i4YT89i1fjFNJcqrFjWps7a7jsQKTV6pZcTwkKkPIv6Wkqh8kvDsOP-EDdrr77ygu0RzSTe3BGC6VnbI7eMHEDIE
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: $APPKEY" -X POST -d "alert=$ALERT&device=$DEVICE&token=$TOKEN&score=198" http://localhost:8801/notification/
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: $APPKEY" -X POST -d "alert=$ALERT&device=$DEVICE&token=abc&score=198" http://localhost:8801/notification/
