from decimal import Decimal, InvalidOperation

from config import (
    DEFAULT_USD_TO_INR,
    DATE_INPUT_FMT,
    RECORD_TAGS,
)

from core.calculations import (
    parse_date,
    matured_by,
    today,
)


# ==================================================
# DATA STRUCTURE
# ==================================================

def new_data():
    return {
        "rate": DEFAULT_USD_TO_INR,
        "earnings": {},
        "withdrawals": [],
        "locked": False,
        "issues": [],
    }


# ==================================================
# BASIC VALIDATION
# ==================================================

def check_date(text):
    try:
        parsed = parse_date(text)

        if parsed.strftime(DATE_INPUT_FMT) != text:
            raise ValueError

    except ValueError:
        raise ValueError(
            f"invalid date '{text}'"
        ) from None


def parse_stars(text):
    stars = int(text)

    if stars <= 0:
        raise ValueError("stars must be positive")

    return stars


def parse_rate(text):
    rate = Decimal(text)

    if not rate.is_finite() or rate <= 0:
        raise ValueError(
            "rate must be a positive number"
        )

    return rate


def parse_fee(text):
    try:
        fee = Decimal(text)
    except InvalidOperation:
        raise ValueError("fee must be a number")

    if not fee.is_finite() or fee < 0:
        raise ValueError(
            "fee must be a non-negative number"
        )

    return fee


# ==================================================
# RECORD PARSING
# ==================================================

def apply_record(data, tag, fields):
    """Apply one RATE, ENTRY or WITHDRAW record."""

    if tag == "RATE":

        if len(fields) != 1:
            raise ValueError(
                "RATE needs exactly 1 value"
            )

        data["rate"] = parse_rate(fields[0])

    elif tag == "ENTRY":

        if len(fields) != 2:
            raise ValueError(
                "ENTRY needs date|stars"
            )

        date, stars = fields

        check_date(date)

        if date in data["earnings"]:
            raise ValueError(
                f"duplicate ENTRY date '{date}'"
            )

        data["earnings"][date] = parse_stars(stars)

    elif tag == "WITHDRAW":

        if len(fields) not in (2, 3, 4):
            raise ValueError(
                "WITHDRAW needs date|stars|rate|fee"
            )

        date, stars, *extra = fields

        check_date(date)

        rate = (
            parse_rate(extra[0])
            if extra
            else data["rate"]
        )

        fee = (
            parse_fee(extra[1])
            if len(extra) == 2
            else Decimal("0")
        )

        data["withdrawals"].append({
            "date": date,
            "stars": parse_stars(stars),
            "rate": rate,
            "fee": fee,
        })


def parse_lines(lines):
    """
    Parse the record section.

    The first blank line marks the beginning
    of the generated report.
    """

    data = new_data()
    issues = []
    in_report = False

    for number, raw in enumerate(lines, start=1):

        line = raw.strip()

        if not line:
            in_report = True
            continue

        if in_report:
            continue

        tag, *fields = line.split("|")

        if tag not in RECORD_TAGS:

            issues.append(
                f"line {number}: "
                f"unknown record tag '{tag}'"
            )

            continue

        try:
            apply_record(data, tag, fields)

        except InvalidOperation:

            issues.append(
                f"line {number}: invalid number"
            )

        except (ValueError, OverflowError) as err:

            issues.append(
                f"line {number}: {err}"
            )

    return data, issues


# ==================================================
# ACCOUNTING VALIDATION
# ==================================================

def shortfalls(earnings, withdrawals):
    """
    Find dates where cumulative withdrawals
    exceed matured Stars.
    """

    days = {
        parse_date(w["date"])
        for w in withdrawals
    } | {today()}

    problems = {}

    for day in days:

        needed = sum(
            w["stars"]
            for w in withdrawals
            if parse_date(w["date"]) <= day
        )

        matured = matured_by(earnings, day)

        if needed > matured:
            problems[day] = (matured, needed)

    return problems


def describe_shortfall(day, matured, needed):
    return (
        f"by {day.strftime('%d %B %Y')}: "
        f"{needed:,} Stars withdrawn but only "
        f"{matured:,} matured"
    )


def accounting_problems(data):
    found = shortfalls(
        data["earnings"],
        data["withdrawals"],
    )

    return [
        describe_shortfall(
            day,
            matured,
            needed,
        )
        for day, (matured, needed)
        in sorted(found.items())
    ]


def new_shortfall(
    old_earnings,
    old_withdrawals,
    new_earnings,
    new_withdrawals,
):
    """
    Detect whether a modification makes an existing
    accounting shortfall worse.
    """

    before = shortfalls(
        old_earnings,
        old_withdrawals,
    )

    after = shortfalls(
        new_earnings,
        new_withdrawals,
    )

    worse = {}

    for day, (matured, needed) in after.items():

        old_gap = 0

        if day in before:
            old_gap = (
                before[day][1]
                - before[day][0]
            )

        new_gap = needed - matured

        if new_gap > old_gap:
            worse[day] = (matured, needed)

    if not worse:
        return None

    day = min(worse)
    matured, needed = worse[day]

    return day, matured, needed


def report_shortfall(problem):
    day, matured, needed = problem

    print(
        f"\nNot enough matured Stars by "
        f"{day.strftime('%d %B %Y')}!"
    )

    print(f"Matured by then : {matured:,} Stars")
    print(f"Needed          : {needed:,} Stars")