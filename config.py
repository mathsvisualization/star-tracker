from decimal import Decimal

# ==================================================
# SETTINGS
# ==================================================

STARS_PER_PACKAGE = 500

BUYER_PRICE_INR = Decimal("999")
PAYOUT_USD = Decimal("6.50")
DEFAULT_USD_TO_INR = Decimal("104")

PAYMENT_DELAY_DAYS = 21

FILE_NAME = "/storage/emulated/0/stars_payment_report.txt"
BACKUP_NAME = FILE_NAME + ".bak"

DATE_INPUT_FMT = "%Y-%m-%d"
DATE_DISPLAY_FMT = "%d %B %Y"
DATE_SHORT_FMT = "%d %b %Y"

WIDTH = 60

RECORD_TAGS = ("RATE", "ENTRY", "WITHDRAW")

LOCKED_MESSAGE = (
    "\nEditing is LOCKED because the file has invalid records.\n"
    "Fix the file in a text editor and use 'Reload File From Disk',\n"
    "or use 'Unlock Editing' to continue without those lines."
)


class SaveError(Exception):
    """Raised when the main report cannot be safely replaced."""