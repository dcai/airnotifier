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

    return data

