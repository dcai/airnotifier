## Introduction
AirNotifier is an easy-to-use yet professional application server for sending real-time notifications to mobile and desktop applications. AirNotifier provides an unified web service interface to deliver messages to multi devices using multi protocols, it also features a friendly web based administrator UI to configure and manage services.

## Features
- Multi devices: iOS(APNs), Android(GCM), Windows Phone(WNS/MPNS), Windows 8.1(MPNS)
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

### Server stack
- [Python 2.6+](http://www.python.org)
- [MongoDB 2.0+](http://www.mongodb.org/)
- [Tornado 3.0+](http://tornadoweb.org)

## Copyright
Copyright (c) 2012, Dongsheng Cai

## License

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the Dongsheng Cai nor the names of its 
      contributors may be used to endorse or promote products derived
      from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL DONGSHENG CAI BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
