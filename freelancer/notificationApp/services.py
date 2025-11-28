
class BaseNotificationSender:
    def __init__(self, notification):
        self.notification = notification

    def send(self):
        raise NotImplementedError("Subclasses must implement send()")
    
class EmailNotificationSender(BaseNotificationSender):
    def send(self):
        # Logic to send email notification
        pass