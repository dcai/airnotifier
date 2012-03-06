#!/usr/bin/python


"""
Available options:
    - apns
    - certfile
    - keyfile
"""
airnotifier_config = {
        # dev or production
        'mode': 'dev',
        # Dev options
        'dev_certfile': 'cert.pem',
        'dev_keyfile' : 'key.pem',
        'dev_apns': ('gateway.sandbox.push.apple.com', 2195),
        # Production options
        'production_certfile': '',
        'production_keyfile' : '',
        'production_apns': ('gateway.push.apple.com', 2195),
}

def get_option(key):
    mode = airnotifier_config.get('mode')
    return airnotifier_config.get(airnotifier_config.get('mode') + '_' + key)

if __name__ == "__main__":
    dev_apns = get_option('apns')
