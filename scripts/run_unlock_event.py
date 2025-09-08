import argparse

from sqlalchemy import text

from db import engine

"""
Run this to unlock an event using dbo.usp_UnlockEventDate and show the
final state.

Usage examples:
    python -m scripts.run_unlock_event --event-id 123
    python -m scripts.run_unlock_event --event-id 123 --user-id 42 \
        --reason "Admin override" --request-id "local-test"

Notes:
- Event is considered "locked" in the UI if IsDateLocked = 1 OR Published = 1.
- This script only clears IsDateLocked/DateLockedAt. It does NOT change Published.
"""


def main():
    parser = argparse.ArgumentParser(description="Unlock an event date via stored procedure")
    parser.add_argument("--event-id", type=int, required=True, help="EventID to unlock")
    parser.add_argument(
        "--user-id", type=int, default=None, help="Optional operator UserID (for audit context)"
    )
    parser.add_argument(
        "--reason", type=str, default=None, help="Optional reason (for audit context)"
    )
    parser.add_argument(
        "--request-id", type=str, default=None, help="Optional request id (for audit context)"
    )
    args = parser.parse_args()

    with engine.begin() as conn:
        # Execute the procedure
        sp = text(
            "EXEC dbo.usp_UnlockEventDate "
            "@EventID=:event_id, @PerformedByUserID=:uid, "
            "@Reason=:reason, @RequestID=:rqid"
        )
        conn.execute(
            sp,
            {
                "event_id": args.event_id,
                "uid": args.user_id,
                "reason": args.reason,
                "rqid": args.request_id,
            },
        )
        # Confirm final state
        row = (
            conn.execute(
                text(
                    "SELECT EventID, CAST(IsDateLocked AS bit) AS IsDateLocked, "
                    "DateLockedAt, CAST(Published AS bit) AS Published "
                    "FROM dbo.[Event] WHERE EventID=:event_id"
                ),
                {"event_id": args.event_id},
            )
            .mappings()
            .first()
        )
        if not row:
            print("Event not found")
            return
        print(
            "EventID="
            + str(row['EventID'])
            + " IsDateLocked="
            + str(row['IsDateLocked'])
            + " DateLockedAt="
            + str(row['DateLockedAt'])
            + " Published="
            + str(row['Published'])
        )
        if row["Published"]:
            print(
                "Note: UI still shows as locked because Published=1. "
                "Unlocking only clears IsDateLocked."
            )


if __name__ == "__main__":
    main()
