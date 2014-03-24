#!/bin/sh

#Notifiction
APPKEY=411b1577afcbad22202c2fae08e3af1e
ALERT=ThisIsAnNotificationMessage2222
DEVICE=android
TOKEN=APA91bGDQA8sgHDZGtihbY5amXAITwhtGL3lIAnhexkkEMh3i44uaQ1JyFtNCfseEeB6gpxmAKPDUVT-Hvu1hgzqdUhZEhckVi5v7RuoEgvRGUhemR7TxfMGDJl_OJdcby6ICw9wrT2cktrpawGQSZtMfZZtJGEsfFCj6_qwRmpW8FGPeaKGov4
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: $APPKEY" -X POST -d "alert=$ALERT&device=$DEVICE&token=$TOKEN&score=198" http://localhost:8801/notification/
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: $APPKEY" -X POST -d "alert=$ALERT&device=$DEVICE&token=abc&score=198" http://localhost:8801/notification/
