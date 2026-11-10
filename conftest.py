import pytest
from datetime import datetime
from part_a.models import Ticket


@pytest.fixture
def sample_tickets():
    """4 clean, unique tickets for testing."""
    return [
        Ticket(
            ticket_id="T1",
            customer="Asha Rao",
            product="CloudSync",
            issue="Login fails after password reset",
            status="resolved",
            created_at=datetime(2026, 9, 1, 9, 0),
            resolved_at=datetime(2026, 9, 1, 14, 0),
        ),
        Ticket(
            ticket_id="T2",
            customer="Liam Chen",
            product="CloudSync",
            issue="Sync stuck at 90%",
            status="open",
            created_at=datetime(2026, 9, 2, 10, 0),
            resolved_at=None,
        ),
        Ticket(
            ticket_id="T3",
            customer="Asha Rao",
            product="InvoicePro",
            issue="PDF export missing line items",
            status="resolved",
            created_at=datetime(2026, 9, 3, 11, 0),
            resolved_at=datetime(2026, 9, 4, 9, 0),
        ),
        Ticket(
            ticket_id="T4",
            customer="Priya Nair",
            product="InvoicePro",
            issue="",
            status="open",
            created_at=datetime(2026, 9, 5, 8, 30),
            resolved_at=None,
        ),
    ]