import json
from pathlib import Path
from collections import defaultdict
from part_a.models import Ticket


def load_and_validate(raw_path: str) -> list[Ticket]:
    """Load JSON and validate each row against the Pydantic schema."""
    data = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    tickets = []
    for row in data:
        tickets.append(Ticket(**row))
    return tickets


def flag_empty_issues(tickets: list[Ticket]) -> tuple[list[Ticket], list[str]]:
    """Flag tickets with empty issue fields without dropping them."""
    flags = []
    for t in tickets:
        if not t.issue.strip():
            flags.append(f"{t.ticket_id}: empty issue field")
    return tickets, flags


def deduplicate(tickets: list[Ticket]) -> tuple[list[Ticket], int]:
    """Remove duplicate tickets by ticket_id. Keep first occurrence."""
    seen = set()
    unique = []
    for t in tickets:
        if t.ticket_id not in seen:
            seen.add(t.ticket_id)
            unique.append(t)
    duplicates_removed = len(tickets) - len(unique)
    return unique, duplicates_removed


def compute_ticket_counts(tickets: list[Ticket]) -> dict:
    """Count open vs resolved tickets per product."""
    counts = defaultdict(lambda: {"open": 0, "resolved": 0})
    for t in tickets:
        counts[t.product][t.status] += 1
    return dict(counts)


def compute_avg_resolution_hours(tickets: list[Ticket]) -> float | None:
    """Average resolution time in hours for resolved tickets."""
    hours = []
    for t in tickets:
        if t.status == "resolved" and t.resolved_at is not None:
            delta = (t.resolved_at - t.created_at).total_seconds() / 3600
            if delta < 0:
                print(f"WARNING: {t.ticket_id} has negative resolution time, skipping")
                continue
            hours.append(delta)
    if not hours:
        return None
    return round(sum(hours) / len(hours), 2)


def run_pipeline(input_path: str, output_path: str) -> dict:
    """Full pipeline: load → flag → dedup → compute → save."""
    # Step 1: Load and validate
    tickets = load_and_validate(input_path)
    total_raw = len(tickets)

    # Step 2: Flag empty issues
    tickets, quality_flags = flag_empty_issues(tickets)

    # Step 3: Deduplicate
    tickets, duplicates_removed = deduplicate(tickets)
    total_clean = len(tickets)

    # Step 4: Compute metrics
    counts = compute_ticket_counts(tickets)
    avg_hours = compute_avg_resolution_hours(tickets)

    # Step 5: Build result
    result = {
        "data_quality": {
            "total_raw": total_raw,
            "duplicates_removed": duplicates_removed,
            "flagged_issues": quality_flags,
            "total_clean": total_clean,
        },
        "ticket_counts_by_product": counts,
        "avg_resolution_time_hours": avg_hours,
    }

    # Step 6: Save output
    Path(output_path).write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    result = run_pipeline(
        input_path="data/tickets_raw.json",
        output_path="part_a/output.json",
    )
    print(json.dumps(result, indent=2))