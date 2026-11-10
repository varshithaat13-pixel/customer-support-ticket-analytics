import json
from datetime import datetime
from pathlib import Path
from part_a.models import Ticket
from part_a.pipeline import (
    deduplicate,
    flag_empty_issues,
    compute_ticket_counts,
    compute_avg_resolution_hours,
    run_pipeline,
)


# ── Deduplication Tests ──────────────────────────────

class TestDeduplicate:
    def test_removes_exact_duplicate(self, sample_tickets):
        """T1 appears twice in raw data. Should keep only one."""
        duplicate = sample_tickets[0]  # T1 again
        tickets_with_dupe = sample_tickets + [duplicate]

        unique, removed = deduplicate(tickets_with_dupe)

        assert removed == 1
        assert len(unique) == 4
        assert [t.ticket_id for t in unique] == ["T1", "T2", "T3", "T4"]

    def test_no_duplicates_returns_same(self, sample_tickets):
        """If data is already clean, nothing should be removed."""
        unique, removed = deduplicate(sample_tickets)

        assert removed == 0
        assert len(unique) == 4


# ── Empty Issue Flagging Tests ───────────────────────

class TestFlagEmptyIssues:
    def test_flags_empty_string(self, sample_tickets):
        """T4 has issue='' — should be flagged."""
        tickets, flags = flag_empty_issues(sample_tickets)

        assert len(flags) == 1
        assert "T4" in flags[0]

    def test_no_flags_when_all_filled(self, sample_tickets):
        """If all issues are filled, no flags."""
        for t in sample_tickets:
            t.issue = "some issue"

        _, flags = flag_empty_issues(sample_tickets)
        assert len(flags) == 0


# ── Ticket Count Tests ──────────────────────────────

class TestComputeTicketCounts:
    def test_counts_per_product(self, sample_tickets):
        """CloudSync: 1 open, 1 resolved. InvoicePro: 1 open, 1 resolved."""
        counts = compute_ticket_counts(sample_tickets)

        assert counts["CloudSync"]["open"] == 1
        assert counts["CloudSync"]["resolved"] == 1
        assert counts["InvoicePro"]["open"] == 1
        assert counts["InvoicePro"]["resolved"] == 1

    def test_all_open_tickets(self):
        """Edge case: no resolved tickets at all."""
        tickets = [
            Ticket(
                ticket_id="T10",
                customer="Test",
                product="App",
                issue="bug",
                status="open",
                created_at=datetime(2026, 1, 1),
            )
        ]
        counts = compute_ticket_counts(tickets)

        assert counts["App"]["open"] == 1
        assert counts["App"]["resolved"] == 0


# ── Average Resolution Time Tests ────────────────────

class TestComputeAvgResolutionHours:
    def test_correct_average(self, sample_tickets):
        """T1=5hrs, T3=22hrs. Average should be 13.5."""
        avg = compute_avg_resolution_hours(sample_tickets)

        assert avg == 13.5

    def test_returns_none_when_no_resolved(self):
        """If all tickets are open, return None — not zero."""
        tickets = [
            Ticket(
                ticket_id="T10",
                customer="Test",
                product="App",
                issue="bug",
                status="open",
                created_at=datetime(2026, 1, 1),
            )
        ]
        avg = compute_avg_resolution_hours(tickets)

        assert avg is None

    def test_skips_negative_resolution_time(self):
        """resolved_at before created_at is impossible — skip it."""
        tickets = [
            Ticket(
                ticket_id="T99",
                customer="Test",
                product="App",
                issue="bug",
                status="resolved",
                created_at=datetime(2026, 9, 2, 10, 0),
                resolved_at=datetime(2026, 9, 1, 10, 0),  # before created!
            )
        ]
        avg = compute_avg_resolution_hours(tickets)

        assert avg is None  # skipped the only ticket


# ── End-to-End Pipeline Test ─────────────────────────

class TestRunPipeline:
    def test_full_pipeline(self, tmp_path):
        """Run the full pipeline on raw data and verify output."""
        # Create a temp input file
        raw_data = [
            {
                "ticket_id": "T1",
                "customer": "Asha Rao",
                "product": "CloudSync",
                "issue": "Login fails",
                "status": "resolved",
                "created_at": "2026-09-01T09:00:00",
                "resolved_at": "2026-09-01T14:00:00",
            },
            {
                "ticket_id": "T1",
                "customer": "Asha Rao",
                "product": "CloudSync",
                "issue": "Login fails",
                "status": "resolved",
                "created_at": "2026-09-01T09:00:00",
                "resolved_at": "2026-09-01T14:00:00",
            },
        ]
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(raw_data))

        output_file = tmp_path / "output.json"

        result = run_pipeline(str(input_file), str(output_file))

        assert result["data_quality"]["duplicates_removed"] == 1
        assert result["data_quality"]["total_clean"] == 1
        assert result["avg_resolution_time_hours"] == 5.0
        assert output_file.exists()