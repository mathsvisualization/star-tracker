from decimal import Decimal
from calendar import month_name

from config import (
    WIDTH,
    DATE_DISPLAY_FMT,
    DATE_SHORT_FMT,
)

from core.calculations import (
    calculate,
    value_of,
    parse_date,
    sorted_withdrawals,
    done_withdrawals,
    scheduled_withdrawals,
    total_earned,
    total_withdrawn,
    scheduled_stars,
    available_stars,
    pending_stars,
    upcoming_payouts,
    payment_date_for,
)


def title_lines(title):
    return [
        "=" * WIDTH,
        title.center(WIDTH),
        "=" * WIDTH,
    ]


def format_entry(date_text, stars, rate):
    date = parse_date(date_text)

    payment_date = payment_date_for(date_text)[1]

    result = calculate(stars, rate)

    return [
        f"Date        : {date.strftime(DATE_DISPLAY_FMT)}",
        f"Stars       : {stars:,}",
        f"Buyer paid  : Rs. {result['buyer']:,.2f}",
        f"Buyer USD   : ${result['buyer_usd']:,.2f}",
        f"Payout      : ${result['usd']:,.2f}",
        f"Payout INR  : Rs. {result['inr']:,.2f}",
        f"Payment on  : {payment_date.strftime(DATE_DISPLAY_FMT)}",
    ]


def format_withdrawal(withdrawal):
    date = parse_date(withdrawal["date"])

    result = calculate(
        withdrawal["stars"],
        withdrawal["rate"],
    )

    fee = withdrawal.get("fee", Decimal("0"))
    net_usd = result["usd"] - fee
    net_inr = net_usd * withdrawal["rate"]

    if date <= parse_date(str(__import__("datetime").datetime.now().date())):
        status = "Completed"
    else:
        status = "Scheduled"

    return [
        f"Date        : {date.strftime(DATE_DISPLAY_FMT)}",
        f"Stars       : {withdrawal['stars']:,}",
        f"Status      : {status}",
        f"Rate        : Rs. {withdrawal['rate']}/USD",
        f"Gross USD   : ${result['usd']:,.2f}",
        f"Gross INR   : Rs. {result['inr']:,.2f}",
        f"Binance Fee : ${fee:,.2f}",
        f"Net USD     : ${net_usd:,.2f}",
        f"Net INR     : Rs. {net_inr:,.2f}",
    ]


def withdrawal_total_lines(withdrawals):
    usd, inr = value_of(withdrawals)

    total = sum(
        withdrawal["stars"]
        for withdrawal in withdrawals
    )

    fees = sum(
        (
            withdrawal.get("fee", Decimal("0"))
            for withdrawal in withdrawals
        ),
        Decimal("0"),
    )

    net_usd = usd - fees
    net_inr = sum(
        (
            calculate(
                withdrawal["stars"],
                withdrawal["rate"],
            )["usd"] - withdrawal.get("fee", Decimal("0"))
        ) * withdrawal["rate"]
        for withdrawal in withdrawals
    )

    return [
        f"Total withdrawn : {total:,} Stars",
        f"Gross payout    : ${usd:,.2f}",
        f"Gross payout INR: Rs. {inr:,.2f}",
        f"Total Binance fee: ${fees:,.2f}",
        f"Net received    : ${net_usd:,.2f}",
        f"Net received INR: Rs. {net_inr:,.2f}",
    ]


def balance_lines(data):
    earned = total_earned(data)
    withdrawn = total_withdrawn(data)
    scheduled = scheduled_stars(data)
    available = available_stars(data)
    pending = pending_stars(data)

    return [
        f"Total earned     : {earned:,} Stars",
        f"Total withdrawn  : {withdrawn:,} Stars",
        f"Scheduled        : {scheduled:,} Stars",
        f"Available        : {available:,} Stars",
        f"Pending maturity : {pending:,} Stars",
    ]


def upcoming_lines(data):
    payouts = upcoming_payouts(data)

    if not payouts:
        return ["No upcoming payouts."]

    lines = []

    for payout_date, stars in payouts:
        lines.append(
            f"{payout_date.strftime(DATE_SHORT_FMT)}"
            f" : {stars:,} Stars"
        )

    return lines


def monthly_lines(data):
    monthly = {}

    for date_text, stars in data["earnings"].items():
        date = parse_date(date_text)
        key = (date.year, date.month)

        if key not in monthly:
            monthly[key] = {
                "stars": 0,
                "buyer": Decimal("0"),
                "usd": Decimal("0"),
                "inr": Decimal("0"),
                "gap": Decimal("0"),
            }

        result = calculate(stars, data["rate"])

        monthly[key]["stars"] += stars
        monthly[key]["buyer"] += result["buyer"]
        monthly[key]["usd"] += result["usd"]
        monthly[key]["inr"] += result["inr"]
        monthly[key]["gap"] += result["gap"]

    if not monthly:
        return ["No earning records available."]

    lines = []

    for year, month in sorted(monthly):
        record = monthly[(year, month)]

        lines.extend([
            "",
            f"{month_name[month]} {year}",
            "-" * WIDTH,
            f"Stars earned : {record['stars']:,}",
            f"Buyer paid   : Rs. {record['buyer']:,.2f}",
            f"Payout USD   : ${record['usd']:,.2f}",
            f"Payout INR   : Rs. {record['inr']:,.2f}",
            f"Price gap    : Rs. {record['gap']:,.2f}",
        ])

    return lines


def build_report(data):
    lines = []

    lines.extend(title_lines("TELEGRAM STARS TRACKER"))
    lines.append("")

    # Earnings
    lines.extend(title_lines("EARNINGS"))

    earnings = data["earnings"]

    if earnings:
        for index, (date, stars) in enumerate(
            sorted(earnings.items()),
            1,
        ):
            lines.extend([
                "",
                f"ENTRY #{index}",
                "-" * WIDTH,
            ])

            lines.extend(
                format_entry(date, stars, data["rate"])
            )

    else:
        lines.append("No earnings recorded.")

    # Withdrawals
    lines.extend([
        "",
        *title_lines("WITHDRAWALS"),
    ])

    withdrawals = sorted_withdrawals(data)

    if withdrawals:
        for index, withdrawal in enumerate(withdrawals, 1):
            lines.extend([
                "",
                f"WITHDRAWAL #{index}",
                "-" * WIDTH,
            ])

            lines.extend(format_withdrawal(withdrawal))

        lines.extend(withdrawal_total_lines(withdrawals))

    else:
        lines.append("No withdrawals recorded.")

    # Balance
    lines.extend([
        "",
        *title_lines("CURRENT BALANCE"),
    ])

    lines.extend(balance_lines(data))

    # Upcoming payouts
    lines.extend([
        "",
        *title_lines("UPCOMING PAYOUTS"),
    ])

    lines.extend(upcoming_lines(data))

    # Monthly summary
    lines.extend([
        "",
        *title_lines("MONTHLY SUMMARY"),
    ])

    lines.extend(monthly_lines(data))

    lines.extend([
        "",
        "=" * WIDTH,
        "END OF REPORT".center(WIDTH),
        "=" * WIDTH,
    ])

    return "\n".join(lines) + "\n"