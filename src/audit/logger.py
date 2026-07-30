import logging
import logging.handlers
from audit.events import AskAuditEvent
import platform

class NativeSysLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        import syslog
        self.syslog = syslog

    def emit(self, record):
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            pri = self.syslog.LOG_ERR
        elif record.levelno >= logging.WARNING:
            pri = self.syslog.LOG_WARNING
        elif record.levelno >= logging.INFO:
            pri = self.syslog.LOG_INFO
        else:
            pri = self.syslog.LOG_DEBUG
        self.syslog.syslog(pri, msg)

def get_audit_logger():
    logger = logging.getLogger("LocaLLM")
    logger.setLevel(logging.INFO)
    
    # Avoid adding multiple handlers if called multiple times
    if not logger.handlers:
        try:
            if platform.system() == "Darwin":
                handler = NativeSysLogHandler()
            else:
                handler = logging.handlers.SysLogHandler(address='/var/run/syslog')
                
            # Format: LocalSecAgent: {json_metadata}
            formatter = logging.Formatter('LocalSecAgent: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        except Exception:
            # Safe fallback if syslog isn't available
            fallback = logging.StreamHandler()
            logger.addHandler(fallback)
            
    return logger

from policy.secrets import redact_secrets

def log_audit_event(event):
    raw_json = event.model_dump_json()
    safe_json = redact_secrets(raw_json)
    logger = get_audit_logger()
    logger.info(safe_json)