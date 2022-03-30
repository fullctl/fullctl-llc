import fullctl.django.mail as mail


def test_send_plain():
    mail.send_plain("subject", "message", "sender@localhost", ["receiver@localhost"])
