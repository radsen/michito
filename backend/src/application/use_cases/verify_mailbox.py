from src.application.ports.mailbox_verifier_port import MailboxVerifierPort

class VerifyContactMailboxUseCase:
    def __init__(self, verifier: MailboxVerifierPort):
        self.verifier = verifier

    def execute(self, email: str) -> str:
        """
        Executes the mailbox verification process.
        
        Args:
            email (str): The email address to verify.
            
        Returns:
            str: The verification status ('valid', 'invalid', 'catch-all').
        """
        if not email:
            return "invalid"
            
        return self.verifier.verify_email(email)
