from abc import ABC, abstractmethod

class MailboxVerifierPort(ABC):
    @abstractmethod
    def verify_email(self, email: str) -> str:
        """
        Verifies email via TCP socket.
        Returns one of: 'valid', 'catch-all', 'invalid'.
        """
        pass
