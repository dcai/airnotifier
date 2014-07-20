from pushservice import PushService

class MPNSClient(PushService):
    def __init__(self, masterdb, app, instanceid=0):
        self.app = app
