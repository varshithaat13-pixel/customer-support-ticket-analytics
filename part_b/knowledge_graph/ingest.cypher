// ============================================================================
// DATA INGESTION SCRIPT (Parameterized & Idempotent)
// ============================================================================
// Expects a parameter `$tickets` containing the cleaned JSON ticket array.
// Example parameter input:
// :param tickets => [
//   {"ticket_id": "T1", "customer": "Asha Rao", "product": "CloudSync", "issue": "Login fails after password reset", "status": "resolved", "created_at": "2026-09-01T09:00:00", "resolved_at": "2026-09-01T14:00:00"},
//   {"ticket_id": "T2", "customer": "Liam Chen", "product": "CloudSync", "issue": "Sync stuck at 90%", "status": "open", "created_at": "2026-09-02T10:00:00", "resolved_at": null},
//   {"ticket_id": "T3", "customer": "Asha Rao", "product": "InvoicePro", "issue": "PDF export missing line items", "status": "resolved", "created_at": "2026-09-03T11:00:00", "resolved_at": "2026-09-04T09:00:00"},
//   {"ticket_id": "T4", "customer": "Priya Nair", "product": "InvoicePro", "issue": "", "status": "open", "created_at": "2026-09-05T08:30:00", "resolved_at": null}
// ]

UNWIND $tickets AS row

// 1. Merge Customer Node
MERGE (c:Customer {customer_id: row.customer})

// 2. Merge Product Node
MERGE (p:Product {name: row.product})

// 3. Merge Ticket Node
MERGE (t:Ticket {ticket_id: row.ticket_id})
  ON CREATE SET 
    t.issue = row.issue,
    t.status = row.status,
    t.created_at = datetime(row.created_at),
    t.resolved_at = CASE WHEN row.resolved_at IS NOT NULL THEN datetime(row.resolved_at) ELSE null END

// 4. Create Relationships
MERGE (c)-[r1:RAISED]->(t)
  ON CREATE SET r1.at = datetime(row.created_at)

MERGE (t)-[r2:ABOUT]->(p);