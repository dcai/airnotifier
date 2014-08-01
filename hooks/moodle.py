import logging

def process_pushnotification_payload(data):
    extra = data.get('extra', {})
    userfrom = extra.get('userfrom', None)
    timecreated = extra.get('timecreated', None)
    userto = extra.get('userto', None)
    subject = extra.get('subject', None)
    fullmessage = extra.get('fullmessage', None)

    if 'alert' not in data
        data['alert'] = fullmessage

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
