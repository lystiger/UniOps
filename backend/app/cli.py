from __future__ import annotations

import argparse
import getpass
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from app.config import get_settings
from app.database import SessionLocal
from app.integrations.easybooks.client import (
    EasyBooksClient,
    EasyBooksConfigurationError,
    HttpxReadOnlyTransport,
    business_today,
)
from app.integrations.easybooks.sync import FixtureBundle, fetch_live_bundle, sync_bundle
from app.services import auth
from app.services.db_transfer import TransferRefused, transfer
from app.services.export import export_workbook


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _export(args: argparse.Namespace) -> None:
    """Write the workbook from already-ingested data. No credential is needed."""
    with SessionLocal() as session:
        summary = export_workbook(
            session, args.out, from_date=args.from_date, to_date=args.to_date
        )
    print(
        json.dumps(
            {
                "path": str(summary.path),
                "sheets": summary.sheet_rows,
                "total_rows": summary.total_rows,
            }
        )
    )


def _read_password(prompt: str, from_stdin: bool) -> str:
    """Take a password from a pipe or a terminal, never from the command line.

    An argument would land in the shell history and in the process list, where
    anyone on the machine can read it.
    """
    if from_stdin:
        return sys.stdin.readline().rstrip("\n")
    first = getpass.getpass(prompt)
    if first != getpass.getpass("Repeat password: "):
        raise SystemExit("the two passwords do not match")
    return first


def _user(args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        try:
            if args.user_command == "list":
                for user in auth.list_users(session):
                    state = "active" if user.is_active else "disabled"
                    last = user.last_login_at.isoformat() if user.last_login_at else "never"
                    print(f"{user.username}\t{user.role.value}\t{state}\tlast login {last}")
                return
            if args.user_command == "create":
                password = _read_password("New password: ", args.password_stdin)
                user = auth.create_user(
                    session,
                    username=args.username,
                    password=password,
                    role=auth.ROLE_BY_CLI_NAME[args.role],
                    full_name=args.full_name,
                )
                print(f"created {user.username} with role {user.role.value}")
                return
            if args.user_command == "passwd":
                password = _read_password("New password: ", args.password_stdin)
                user = auth.set_password(session, args.username, password)
                print(f"password changed for {user.username}; every session was signed out")
                return
            user = auth.set_active(session, args.username, args.user_command == "enable")
            print(f"{user.username} is now {'active' if user.is_active else 'disabled'}")
        except (auth.UserExists, auth.UserNotFound, auth.WeakPassword) as exc:
            raise SystemExit(str(exc)) from exc


def _purge_sessions(_: argparse.Namespace) -> None:
    with SessionLocal() as session:
        removed = auth.purge_expired_sessions(session)
    print(json.dumps({"sessions_removed": removed}))


def _migrate_db(args: argparse.Namespace) -> None:
    try:
        summary = transfer(args.source, args.target, batch_size=args.batch_size)
    except TransferRefused as exc:
        print(f"transfer refused: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps({"tables": summary.rows_by_table, "total_rows": summary.total_rows}))


def _add_user_parsers(subparsers: argparse._SubParsersAction) -> None:
    user = subparsers.add_parser("user", help="manage UniOps accounts")
    commands = user.add_subparsers(dest="user_command", required=True)
    commands.add_parser("list", help="list accounts, roles, and last sign-in")

    create = commands.add_parser("create", help="create an account")
    create.add_argument("--username", required=True)
    create.add_argument("--role", required=True, choices=sorted(auth.ROLE_BY_CLI_NAME))
    create.add_argument("--full-name")
    create.add_argument(
        "--password-stdin", action="store_true", help="read the password from stdin"
    )

    passwd = commands.add_parser("passwd", help="set a new password and sign the account out")
    passwd.add_argument("--username", required=True)
    passwd.add_argument(
        "--password-stdin", action="store_true", help="read the password from stdin"
    )

    for name, help_text in [("disable", "disable"), ("enable", "re-enable")]:
        parser = commands.add_parser(name, help=f"{help_text} an account")
        parser.add_argument("--username", required=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="uniops")
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync = subparsers.add_parser("sync-easybooks", help="run read-only EasyBooks ingestion")
    mode = sync.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture", type=Path)
    mode.add_argument("--live", action="store_true")
    sync.add_argument("--from-date", type=_date)
    sync.add_argument("--to-date", type=_date)
    sync.add_argument(
        "--headers-only",
        action="store_true",
        help=(
            "live only: diagnostic read of sales headers, count, and purchases "
            "without the sales-detail route"
        ),
    )
    export = subparsers.add_parser(
        "export", help="write ingested data to a workbook; reads no EasyBooks API"
    )
    export.add_argument("--out", type=Path, required=True, help="destination .xlsx path")
    export.add_argument("--from-date", type=_date)
    export.add_argument("--to-date", type=_date)

    _add_user_parsers(subparsers)
    subparsers.add_parser("purge-sessions", help="delete expired and revoked sign-in sessions")

    migrate = subparsers.add_parser(
        "migrate-db", help="copy a whole UniOps database into an empty migrated one"
    )
    migrate.add_argument("--source", required=True, help="SQLAlchemy URL to read")
    migrate.add_argument("--target", required=True, help="SQLAlchemy URL to fill")
    migrate.add_argument("--batch-size", type=int, default=1000)

    args = parser.parse_args()
    if args.command == "user":
        _user(args)
        return
    if args.command == "purge-sessions":
        _purge_sessions(args)
        return
    if args.command == "migrate-db":
        _migrate_db(args)
        return
    # EasyBooks answers an inverted window with an empty result rather than an
    # error, which reads as "no documents" instead of "bad request".
    if args.from_date and args.to_date and args.from_date > args.to_date:
        parser.error(
            f"--from-date {args.from_date} is after --to-date {args.to_date}; "
            "EasyBooks would return an empty result for that window"
        )
    if args.command == "export":
        _export(args)
        return
    if args.headers_only and args.fixture:
        parser.error("--headers-only applies to --live reads")

    settings = get_settings()
    to_date = args.to_date or business_today()
    from_date = args.from_date or (to_date - timedelta(days=settings.easybooks_sync_overlap_days))
    if args.fixture:
        payload = json.loads(args.fixture.read_text())
        bundle = FixtureBundle.from_dict(payload)
        mode_name = "fixture"
    else:
        try:
            transport = HttpxReadOnlyTransport(settings)
            client = EasyBooksClient(transport, settings)
            bundle = fetch_live_bundle(
                client, from_date, to_date, include_lines=not args.headers_only
            )
        except EasyBooksConfigurationError as exc:
            # Expected operator-configuration refusal, not a crash.
            print(f"EasyBooks live read refused: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        mode_name = "live-headers" if args.headers_only else "live"

    with SessionLocal() as session:
        run = sync_bundle(session, bundle, mode=mode_name, from_date=from_date, to_date=to_date)
        print(
            json.dumps(
                {
                    "sync_run_id": run.id,
                    "status": run.status.value,
                    "documents_seen": run.documents_seen,
                    "created": run.documents_created,
                    "updated": run.documents_updated,
                    "unchanged": run.documents_unchanged,
                    "failed": run.documents_failed,
                    "reconciliation_warnings": run.reconciliation_warnings,
                }
            )
        )


if __name__ == "__main__":
    main()
