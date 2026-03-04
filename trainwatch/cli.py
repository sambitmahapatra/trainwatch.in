"""TrainWatch CLI."""

from __future__ import annotations

import argparse
import sys

from .cloud import add_email, delete_email, verify_email
from .help import help as show_help
from .exceptions import TrainWatchError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trainwatch", description="TrainWatch CLI")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add-email", help="Register an email for notifications")
    add_parser.add_argument("email", help="Email address to register")
    add_parser.add_argument("--base-url", help="TrainWatch Cloud base URL")
    add_parser.add_argument("--api-key-path", help="Path to store credentials JSON")

    verify_parser = subparsers.add_parser(
        "verify-email", help="Verify a code without prompting (advanced)"
    )
    verify_parser.add_argument("email", help="Email address to verify")
    verify_parser.add_argument("code", help="Verification code")
    verify_parser.add_argument("--base-url", help="TrainWatch Cloud base URL")
    verify_parser.add_argument("--api-key-path", help="Path to store credentials JSON")

    delete_parser = subparsers.add_parser("delete-email", help="Delete the registered email")
    delete_parser.add_argument("--base-url", help="TrainWatch Cloud base URL")
    delete_parser.add_argument("--api-key-path", help="Path to credentials JSON")

    subparsers.add_parser("help", help="Show TrainWatch quick help")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 2

    try:
        if args.command == "add-email":
            add_email(args.email, base_url=args.base_url, api_key_path=args.api_key_path)
            print("Email registered and API key stored.")
            return 0
        if args.command == "verify-email":
            verify_email(
                args.email,
                args.code,
                base_url=args.base_url,
                api_key_path=args.api_key_path,
            )
            print("Email verified and API key stored.")
            return 0
        if args.command == "delete-email":
            delete_email(base_url=args.base_url, api_key_path=args.api_key_path)
            print("Email deleted and credentials removed.")
            return 0
        if args.command == "help":
            show_help()
            return 0
    except TrainWatchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
