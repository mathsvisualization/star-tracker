from datetime import datetime, timedelta
from decimal import Decimal

from config import (
    STARS_PER_PACKAGE,
    BUYER_PRICE_INR,
    PAYOUT_USD,
    PAYMENT_DELAY_DAYS,
    DATE_INPUT_FMT,
)


# ==================================================
# DATES
# ==================================================

def today():
    return datetime.now().date()


def parse_date(text):
    return datetime.strptime(text, DATE_INPUT_FMT).date()


def payment_date_for(date):
    earned = parse_date(date)
    return earned, earned + timedelta(days=PAYMENT_DELAY_DAYS)


# ==================================================
# CALCULATIONS
# ==================================================

def buyer_price_usd(rate):
    return BUYER_PRICE_INR / rate


def payout_inr(rate):
    return PAYOUT_USD * rate


def calculate(stars, rate):
    """Calculate buyer spending, payout and price gap."""

    packages = Decimal(stars) / STARS_PER_PACKAGE

    buyer_inr = packages * BUYER_PRICE_INR
    earn_usd = packages * PAYOUT_USD
    earn_inr = earn_usd * rate
    gap_inr = buyer_inr - earn_inr

    return {
        "buyer": buyer_inr,
        "buyer_usd": buyer_inr / rate,
        "usd": earn_usd,
        "inr": earn_inr,
        "gap": gap_inr,
        "gap_usd": gap_inr / rate,
    }


def value_of(withdrawals):
    """Calculate withdrawals using their own saved exchange rates."""

    results = [
        calculate(w["stars"], w["rate"])
        for w in withdrawals
    ]

    return (
        sum((r["usd"] for r in results), Decimal("0")),
        sum((r["inr"] for r in results), Decimal("0")),
    )


# ==================================================
# WITHDRAWALS
# ==================================================

def sorted_withdrawals(data):
    return sorted(data["withdrawals"], key=lambda w: w["date"])


def done_withdrawals(data):
    return [
        w for w in data["withdrawals"]
        if parse_date(w["date"]) <= today()
    ]


def scheduled_withdrawals(data):
    return [
        w for w in data["withdrawals"]
        if parse_date(w["date"]) > today()
    ]


def withdrawn_so_far(data):
    return sum(w["stars"] for w in done_withdrawals(data))


def scheduled_stars(data):
    return sum(w["stars"] for w in scheduled_withdrawals(data))


def total_withdrawn(data):
    return sum(w["stars"] for w in data["withdrawals"])


# ==================================================
# BALANCE
# ==================================================

def total_earned(data):
    return sum(data["earnings"].values())


def matured_by(earnings, day):
    """Stars whose payment date is on or before the given day."""

    return sum(
        stars
        for date, stars in earnings.items()
        if payment_date_for(date)[1] <= day
    )


def balance_stars(data):
    return total_earned(data) - withdrawn_so_far(data)


def available_stars(data):
    """Maximum additional Stars withdrawable today."""

    today_day = today()
    check_days = {today_day}

    check_days.update(
        parse_date(w["date"])
        for w in data["withdrawals"]
        if parse_date(w["date"]) > today_day
    )

    capacities = []

    for day in check_days:
        matured = matured_by(data["earnings"], day)

        already_committed = sum(
            w["stars"]
            for w in data["withdrawals"]
            if parse_date(w["date"]) <= day
        )

        capacities.append(matured - already_committed)

    return max(0, min(capacities, default=0))


def pending_stars(data):
    return balance_stars(data) - available_stars(data)


def upcoming_payouts(data):
    items = []

    for date, stars in data["earnings"].items():
        pay = payment_date_for(date)[1]

        if pay > today():
            items.append((pay, stars))

    return sorted(items)