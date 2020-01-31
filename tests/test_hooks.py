from hooks.moodle import process_pushnotification_payload
import unittest
import logging

extra = dict(
    {
        "courseid": "1",
        "modulename": "",
        "component": "mod_forum",
        "name": "posts",
        "convid": "",
        "subject": "LAW STUDY GROUP",
        "fullmessage": "VLE -> Forums -> UG Laws Discussion Forum -> study group \nhttps://url-to-moodle.com/mod/forum/discuss.php?d=11404#p51395\nRe: study group\nby Dongsheng Cai - Tuesday, 28 January 2020, 1:27 AM\n---------------------------------------------------------------------\nAdd me please +5926629923\n\n \n\n\n\n---------------------------------------------------------------------\nThis is a copy of a message posted in law study.\n\nTo reply click on this link: https://url-to-moodle.com/mod/forum/post.php?reply=51395\nUnsubscribe from this forum: https://url-to-moodle.com/mod/forum/subscribe.php?id=155\nUnsubscribe from this discussion: https://url-to-moodle.com/mod/forum/subscribe.php?id=155&d=11404\nChange your forum digest preferences: https://url-to-moodle.com/mod/forum/index.php?id=1",
        "fullmessageformat": "2",
        "fullmessagehtml": "\n    law study\n    »\n    Forums\n    »\n    UG Laws Discussion Forum\n    »\n    study group\n\n\n\n    \n        \n            \n        \n        \n            \n                Re: study group\n            \n            \n                by Dongsheng Cai - Tuesday, 28 January 2020, 1:27 AM\n            \n        \n    \n    \n        \n                 \n        \n        \n            Add me please +5926629923\r\n \n\n            \n                    \n                        Show parent\n                    \n                        |\n                    \n                        Reply\n                    \n            \n\n            \n                \n                    See this post in context\n                \n            \n        \n    \n\n\n\n\n    Unsubscribe from this forum \n    Unsubscribe from this discussion \n    Change your forum digest preferences\n",
        "smallmessage": "Dongsheng Cai posted in Forum: LAW STUDY GROUP",
        "notification": 1,
        "contexturl": "https://url-to-moodle.com/mod/forum/discuss.php?d=11404#p51395",
        "contexturlname": "LAW STUDY GROUP",
        "replyto": "",
        "replytoname": "",
        "savedmessageid": 2470742,
        "attachment": "",
        "attachname": "",
        "timecreated": "",
        "userfromid": "51122",
        "userfromfullname": "Dongsheng Cai",
        "usertoid": "50681",
        "processor": "moodle",
        "site": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxksdffj",
        "date": 1580176731,
        "sitefullname": "moodle website",
        "siteshortname": "moodle",
    },
)
moodle_push_request = {
    "device": "Android-fcm",
    "token": "fvHiFM9n-Ms",
    "extra": extra,
}

alert = dict(
    {
        "body": "Dongsheng Cai posted in Forum: LAW STUDY GROUP",
        "title": "moodle website",
    }
)

fixture = {
    "alert": alert,
    "fcm": {"data": extra},
    "wns": {"type": "toast", "template": "ToastText01", "text": [alert],},
    "device": "Android-fcm",
    "token": "fvHiFM9n-Ms",
    "extra": extra,
}


class TestHooks(unittest.TestCase):
    def test_moodle_hook(self):
        self.maxDiff = None
        processed_payload = process_pushnotification_payload(moodle_push_request)
        self.assertDictEqual(
            processed_payload["alert"], fixture["alert"], "should have alert"
        )
        self.assertDictEqual(
            processed_payload["fcm"], fixture["fcm"], "should have fcm"
        )
        self.assertDictEqual(
            processed_payload["wns"], fixture["wns"], "should have wns"
        )


if __name__ == "__main__":
    unittest.main()
