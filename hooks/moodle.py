import logging

def process_pushnotification_payload(data):
    extra = {}
    if 'extra' in data:
        extra = data['extra']

    userfrom = None
    if 'userfrom' in extra:
        userfrom = extra['userfrom']
    userto = None
    if 'userto' in extra:
        userto = extra['userto']
    subject = None
    if 'subject' in extra:
        subject = extra['subject']

    fullmessage = None
    if 'fullmessage' in extra:
        fullmessage = extra['fullmessage']
        data['alert'] = fullmessage

    timecreated = None
    if 'timecreated' in extra:
        timecreated = extra['timecreated']

    if not 'wns' in extra:
        data['extra']['wns'] = {
                'type': 'toast',
                'template': 'ToastText01',
                'text': [data['alert']]
                }

    if not 'mpns' in extra:
        data['extra']['mpns'] = {
                'type': 'toast',
                'text1': [data['alert']]
                }

    if not 'gcm' in extra:
        pass

    return data
