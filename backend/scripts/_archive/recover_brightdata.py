"""
Script to recover lost social_comments data from Brightdata snapshots.
Context: social_comments was dropped and recreated empty due to alembic stamp error.
"""
from __future__ import annotations

import argparse
import sys

import requests

# Importing from brightdata_comments automatically loads .env.scraping-keys
from brightdata_comments import API_KEY, DATASETS, download_snapshot, insert_comments


def list_snapshots(dataset_id: str, limit: int = 5) -> list[dict]:
    """List recent snapshots for a given dataset."""
    url = f"https://api.brightdata.com/datasets/v3/snapshots?dataset_id={dataset_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    
    data = r.json()
    snapshots = []
    
    # Brightdata might return a list directly or a nested dictionary
    if isinstance(data, list):
        snapshots = data
    elif isinstance(data, dict):
        snapshots = data.get("snapshots", data.get("data", []))
        
    return snapshots[:limit]


def print_snapshot_list(limit: int = 5):
    print(f"=== Last {limit} Snapshots by Platform ===")
    for platform, dataset_id in DATASETS.items():
        print(f"\n[{platform}] - Dataset: {dataset_id}")
        try:
            snapshots = list_snapshots(dataset_id, limit)
            if not snapshots:
                print("  No snapshots found.")
                continue
            for snap in snapshots:
                snap_id = snap.get("snapshot_id", snap.get("id", "UNKNOWN"))
                status = snap.get("status", "UNKNOWN")
                date_created = snap.get("created_at", snap.get("date_created", "UNKNOWN"))
                rows = snap.get("rows_count", snap.get("rows", "?"))
                print(f"  - ID: {snap_id} | Status: {status} | Date: {date_created} | Rows: {rows}")
        except Exception as e:
            print(f"  Error fetching snapshots: {e}")


def recover_snapshot(snapshot_id: str, platform: str):
    print(f"\nRecovering snapshot {snapshot_id} for platform {platform}...")
    try:
        rows = download_snapshot(snapshot_id)
        print(f"Downloaded {len(rows)} rows.")
        inserted, skipped = insert_comments(rows, platform)
        print(f"Result: {inserted} inserted, {skipped} skipped.")
    except Exception as e:
        print(f"Error recovering snapshot: {e}")


def recover_all_interactive():
    print("=== Auto-Recover Recent Snapshots ===")
    for platform, dataset_id in DATASETS.items():
        print(f"\nFetching latest snapshot for {platform}...")
        try:
            snapshots = list_snapshots(dataset_id, limit=1)
            if not snapshots:
                print(f"No snapshots found for {platform}.")
                continue
            
            latest = snapshots[0]
            snap_id = latest.get("snapshot_id", latest.get("id"))
            if not snap_id:
                print("Could not determine snapshot ID.")
                continue
            
            status = latest.get("status", "UNKNOWN")
            date_created = latest.get("created_at", latest.get("date_created", "UNKNOWN"))
            print(f"Latest snapshot: {snap_id} (Status: {status}, Date: {date_created})")
            
            # Note: in a CI/headless environment, input() might fail or hang.
            # However, this script is designed to be used by the CEO.
            ans = input(f"Recover this snapshot for {platform}? (y/N): ")
            if ans.lower() == 'y':
                recover_snapshot(snap_id, platform)
            else:
                print("Skipped.")
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Recover Brightdata snapshots into social_comments")
    parser.add_argument("--list", action="store_true", help="List the latest snapshots for each platform")
    parser.add_argument("--limit", type=int, default=5, help="Number of snapshots to list per platform")
    parser.add_argument("--recover", nargs=2, metavar=("SNAPSHOT_ID", "PLATFORM"), help="Recover a specific snapshot")
    parser.add_argument("--recover-all", action="store_true", help="List recent snapshots and offer to recover them")

    args = parser.parse_args()

    if args.list:
        print_snapshot_list(args.limit)
    elif args.recover:
        snap_id, platform = args.recover
        if platform.upper() not in DATASETS:
            print(f"Error: Platform must be one of {list(DATASETS.keys())}")
            sys.exit(1)
        recover_snapshot(snap_id, platform.upper())
    elif args.recover_all:
        recover_all_interactive()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
