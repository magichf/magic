import argparse
import json
from .core import initialize, append_event, verify_store, export_verified


def main():
    parser = argparse.ArgumentParser(prog="iac")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "verify"):
        sub = commands.add_parser(name)
        sub.add_argument("path")
    sub = commands.add_parser("append")
    sub.add_argument("path")
    sub.add_argument("event_type")
    sub.add_argument("payload_json")
    sub = commands.add_parser("export")
    sub.add_argument("source")
    sub.add_argument("destination")
    args = parser.parse_args()

    if args.command == "init":
        initialize(args.path)
        print("initialized")
    elif args.command == "verify":
        print(json.dumps(verify_store(args.path), indent=2))
    elif args.command == "append":
        payload = json.loads(args.payload_json)
        print(json.dumps(append_event(args.path, args.event_type, payload), indent=2))
    else:
        print(json.dumps(export_verified(args.source, args.destination), indent=2))


if __name__ == "__main__":
    main()
