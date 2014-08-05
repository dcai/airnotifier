## Introduction
AirNotifier is an easy-to-use yet professional application server for sending real-time notifications to mobile and desktop applications. AirNotifier provides an unified web service interface to deliver messages to multi devices using multi protocols, it also features a friendly web based administrator UI to configure and manage services.

## Features
- Multi devices: iOS(APNs), Android(GCM), Windows Phone(WNS/MPNS)
- Subscribe to multi channels
- Unlimited number of devices and channels
- API access control
- Web-based UI to configure
- Broadcase notifications
- Access key management
- Logging activities
- Apple Feedback API
- GCM broadcast API
- Non-blocking API design allows master provider to handle large loads of request smoothly

## Push notification examples


### Sending simple notification to iOS devices
```
POST /api/v2/push HTTP/1.1
X-AN-APP-NAME: moodlemobileapp
X-AN-APP-KEY: b2b56dbb
Content-Type: application/json
{
    "device": "ios",
    "token": "FE66489F304DC75B8D6E8200DFF8A456E8DAEACEC428B427E9518741C92C6660",
    "alert": "Hello from AirNotifier",
    "sound": "Submarine.aiff",
    "badge": 1
}
```

### Sending toast type notification to windows 8.1 devices
```
POST /api/v2/push HTTP/1.1
X-AN-APP-NAME: moodlemobileapp
X-AN-APP-KEY: b2b56dbb
Content-Type: application/json
{
    "device": "wns",
    "token": "https:\/\/sin.notify.windows.com\/?token=AgYAAACDWksZrGbln5sUbP6D3F%2b9ddjptarcZ%2f9vJsDwCt16EHiupJaRddEXJ8BEfx4SE5slxQlB6iknY7zdUEXFayFclNXCIYp6CWnMTYSHGVRySO7aglj6%2b09wTBYqBFxFuoA%3d",
    "alert": "alert contetnt",
    "wns": {
        "type": "toast",
        "template": "ToastImageAndText01",
        "image": ["image1"],
        "text": ["test1"]
    },
    "extra": {
        "processor":"moodle",
        "data":{"key1":"param1 value","key2":"param2 value"}
    }
}
```

## Installation

Please read [Installation guide](https://github.com/airnotifier/airnotifier/wiki/Installation)

## Configuration
`airnotifier.conf` is the config file, options:

- pemdir: The directory storing certificates
- passwordsalt: passwordsalt
- masterdb: MongoDB database name
- dbprefix: MongoDB collection name prefix, this will be used to create object data collection

## Web service documentation
- [Web service interfaces](https://github.com/airnotifier/airnotifier/wiki/API)

## Requirements

- [Python 2.6+](http://www.python.org)
- [MongoDB 2.0+](http://www.mongodb.org/)
- [Tornado 3.0+](http://tornadoweb.org)

## Copyright
Copyright (c) Dongsheng Cai and individual contributors
