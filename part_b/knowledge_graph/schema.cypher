// ============================================================================
// SCHEMA & CONSTRAINTS DEFINITION
// ============================================================================

// 1. Ensure Customer ID uniqueness
CREATE CONSTRAINT customer_id_unique IF NOT EXISTS
FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE;

// 2. Ensure Ticket ID uniqueness
CREATE CONSTRAINT ticket_id_unique IF NOT EXISTS
FOR (t:Ticket) REQUIRE t.ticket_id IS UNIQUE;

// 3. Ensure Product Name uniqueness
CREATE CONSTRAINT product_name_unique IF NOT EXISTS
FOR (p:Product) REQUIRE p.name IS UNIQUE;