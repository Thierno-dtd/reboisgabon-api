from django.core.mail.backends.console import EmailBackend as ConsoleBackend
from django.core.mail.backends.smtp import EmailBackend as SmtpBackend


class SmtpOuConsoleBackend(SmtpBackend):

    def send_messages(self, email_messages):
        silencieux, self.fail_silently = self.fail_silently, False
        try:
            return super().send_messages(email_messages)
        except OSError:
            self.connection = None
            return ConsoleBackend(fail_silently=silencieux).send_messages(email_messages)
        finally:
            self.fail_silently = silencieux
