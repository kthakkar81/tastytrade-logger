"""Delete row 343"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

print("Deleting row 343...")
logger.sheet.delete_rows(343)
print("✓ Done")
