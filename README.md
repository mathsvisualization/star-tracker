# Telegram Stars Tracker

A Python-based application for tracking Telegram Stars earnings, withdrawals, payment maturity, and financial summaries.

## Features

- Track daily Telegram Stars earnings.
- Record and manage withdrawals.
- Separate available and pending Stars.
- Calculate 21-day payment maturity.
- Track scheduled withdrawals.
- Store exchange rates.
- Calculate INR and USD values.
- Generate financial reports.
- Monthly earnings summaries.
- Automatic backup and recovery.
- Safe file storage.

## Project Structure

```text
star_tracker/
├── core/
│   ├── calculations.py
│   └── validation.py
├── storage/
│   ├── backup.py
│   ├── file_manager.py
│   └── recovery.py
├── reports/
│   └── report_builder.py
├── ui/
│   ├── actions.py
│   └── menu.py
├── main.py
├── config.py
└── pyproject.toml
```

## Requirements

- Python 3.10 or later
- pip

## Installation

Clone the repository:

```bash
git@github.com:mathsvisualization/star-tracker.git
```

Navigate into the project:

```bash
cd telegram-stars-tracker
```

Install in editable mode:

```bash
python3 -m pip install -e .
```

## Usage

Run the application:

```bash
star-tracker
```

Alternatively:

```bash
python3 main.py
```

## Configuration

Application settings are available in `config.py`.

Important settings include:

- Stars package size
- Buyer price
- Payout value
- USD to INR exchange rate
- Payment maturity period
- Report storage location

## Data Storage

The application stores earnings and withdrawal records in a local text report.

A backup file is maintained to support recovery.

**Important:** Back up your report file regularly. Never upload personal financial records to a public repository.

## Contributing

Contributions are welcome!

1. Fork this repository.
2. Create a new branch.
3. Make your changes.
4. Test your changes.
5. Submit a Pull Request.

For bug reports and feature requests, use the GitHub Issues section.

## License

This project is licensed under the MIT License.
See the `LICENSE` file for details.
