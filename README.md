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

## Installation

Please read [Installation guide](https://github.com/airnotifier/airnotifier/wiki/Installation)

## Configuration
`airnotifier.conf` is the config file, options:

- pemdir: The directory storing APNS certificate
- passwordsalt: passwordsalt
- masterdb: MongoDB database name
- dbprefix: MongoDB collection name prefix, this will be used to create object data collection

## Design
- [Product design](https://github.com/airnotifier/airnotifier/wiki/Specification)

## Web service documentation
- [Web service interfaces (In progress)](https://github.com/airnotifier/airnotifier/wiki/API)

## Requirements

- [Python 2.6+](http://www.python.org)
- [MongoDB 2.0+](http://www.mongodb.org/)
- [Tornado 3.0+](http://tornadoweb.org)

## Copyright
Copyright (c) Dongsheng Cai and individual contributors
