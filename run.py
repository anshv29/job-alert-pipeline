"""Run the job alerts.

  python run.py              scan everything and email anything new
  python run.py --dry-run    scan and print what WOULD be emailed (sends nothing, remembers nothing)
  python run.py --test-email send a short test email to check your secrets
"""
import argparse
import sys

from jobalert.settings import ConfigError


def main():
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-email", action="store_true")
    parser.add_argument("--only", help="comma list: greenhouse,lever,ashby,workday,feeds,simplify")
    parser.add_argument("--limit-companies", type=int, help="only the first N companies per source (quick tests)")
    args = parser.parse_args()

    try:
        if args.test_email:
            from jobalert.emailer import EmailConfigError, send_email

            try:
                to = send_email("Job alerts: test email", "<p>It works. Your job alerts can reach this inbox.</p>")
            except EmailConfigError as e:
                sys.exit(str(e))
            print(f"Test email sent to {to}")
            return

        from jobalert.pipeline import run

        only = set(args.only.split(",")) if args.only else None
        run(dry_run=args.dry_run, only=only, limit_companies=args.limit_companies)
    except ConfigError as e:
        sys.exit(f"Config problem: {e}")


if __name__ == "__main__":
    main()
