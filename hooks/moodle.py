import requests
from api import API_PERMISSIONS

HUBURL = "https://moodle.net/local/sitecheck/check.php"


def process_pushnotification_payload(data):
    extra = data.get("extra", {})
    userfrom = extra.get("userfromfullname", None)
    site = extra.get("site", None)
    timecreated = extra.get("timecreated", None)
    message = extra.get("smallmessage", None)
    notif = extra.get("notification", None)
    title = extra.get("sitefullname", None)

    if not message:
        message = extra.get("fullmessage", None)

    if not title:
        title = "Notification"

    if "alert" not in data:
        data["alert"] = {"body": message, "title": title}

    data["fcm"] = {"data": extra}
    if not "wns" in extra:
        data["wns"] = {
            "type": "toast",
            "template": "ToastText01",
            "text": [data["alert"]],
        }

    return data


def process_accesskey_payload(data):
    mdlurl = data.get("url", "")
    mdlsiteid = data.get("siteid", "")
    params = {"siteid": mdlsiteid, "url": mdlurl}
    response = requests.get(HUBURL, params=params)
    result = int(response.text)
    if result == 0:
        raise Exception("Site not registered on moodle.net")
    else:
        # This is 1111 in binary means all permissions are granted
        data["permission"] = (
            API_PERMISSIONS["create_token"][0]
            | API_PERMISSIONS["delete_token"][0]
            | API_PERMISSIONS["send_notification"][0]
            | API_PERMISSIONS["send_broadcast"][0]
        )
        return data


def process_token_payload(data):
    return data
