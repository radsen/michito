import socket
import uuid
import dns.resolver
import logging

from src.application.ports.mailbox_verifier_port import MailboxVerifierPort

logger = logging.getLogger(__name__)

class SocketSmtpVerifierAdapter(MailboxVerifierPort):
    def __init__(self, sender_email: str = "verify@example.com", timeout: int = 10):
        self.sender_email = sender_email
        self.timeout = timeout
        self.sender_domain = sender_email.split('@')[1] if '@' in sender_email else 'example.com'

    def _get_mx_record(self, domain: str) -> str:
        try:
            records = dns.resolver.resolve(domain, 'MX')
            mx_record = sorted(records, key=lambda rec: rec.preference)[0].exchange.to_text()
            return mx_record
        except Exception as e:
            logger.debug(f"Failed to get MX record for {domain}: {e}")
            return ""

    def _send_command(self, sock: socket.socket, cmd: str) -> tuple[int, str]:
        if cmd:
            sock.sendall((cmd + "\r\n").encode('utf-8'))
        response = sock.recv(1024).decode('utf-8')
        if not response:
            return 0, ""
        try:
            code = int(response[:3])
            return code, response
        except ValueError:
            return 0, response

    def _check_email(self, mx_host: str, email: str) -> tuple[bool, int]:
        """Returns (is_valid, smtp_code).
        
        TODO(contingency-03): Handle Greylisting / tarpitting by enterprise mail servers (Microsoft 365, Proofpoint).
        If the socket times out or drops without explicit 550 rejection, apply tier-adaptive fallback:
        accept confirmed MX host existence + RFC 5322 valid corporate domain format as deliverable.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((mx_host, 25))
            code, _ = self._send_command(sock, "")  # Initial banner
            if code >= 400:
                return False, code
                
            code, _ = self._send_command(sock, f"HELO {self.sender_domain}")
            if code >= 400:
                return False, code
                
            code, _ = self._send_command(sock, f"MAIL FROM:<{self.sender_email}>")
            if code >= 400:
                return False, code
                
            code, _ = self._send_command(sock, f"RCPT TO:<{email}>")
            
            # Send QUIT regardless of result
            self._send_command(sock, "QUIT")
            
            if code == 250:
                return True, code
            else:
                return False, code
                
        except Exception as e:
            logger.debug(f"Socket error when checking {email}: {e}")
            return False, 0
        finally:
            sock.close()

    def verify_email(self, email: str) -> str:
        if "@" not in email:
            return "invalid"
            
        domain = email.split("@")[1]
        mx_host = self._get_mx_record(domain)
        if not mx_host:
            return "invalid"
            
        # 1. Probe a random UUID email to test catch-all
        catch_all_probe = f"{uuid.uuid4().hex}@{domain}"
        ca_is_valid, ca_code = self._check_email(mx_host, catch_all_probe)
        
        # If greylisted or temp error on catch-all check, we might want to return 'temp-error' 
        # but the port says returning 'valid', 'catch-all', 'invalid'.
        if ca_code in (450, 421):
            # Treat as valid/catch-all or unknown? 
            # Instructions: "450/421: Greylisting/Temp error".
            pass

        # 2. Probe actual email
        actual_is_valid, actual_code = self._check_email(mx_host, email)
        
        if actual_is_valid:
            if ca_is_valid:
                return "catch-all"
            else:
                return "valid"
        else:
            return "invalid"
