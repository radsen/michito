from abc import ABC, abstractmethod
from typing import Optional

class MailboxVerifierPort(ABC):
    @abstractmethod
    def verify_email(self, email: str, mx_host: Optional[str] = None) -> str:
        """
        Verifies email deliverability via DNS MX resolution and TCP socket handshake.
        Returns one of: 'valid', 'catch-all', 'invalid'.
        """
        pass
