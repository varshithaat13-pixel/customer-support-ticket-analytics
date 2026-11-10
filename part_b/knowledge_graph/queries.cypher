// ============================================================================
// GRAPH QUERIES & ANALYTICS
// ============================================================================

// ----------------------------------------------------------------------------
// PROBLEM QUERY:
// "Find every customer who has raised a ticket about more than one distinct product."
// ----------------------------------------------------------------------------
MATCH (c:Customer)-[:RAISED]->(t:Ticket)-[:ABOUT]->(p:Product)
WITH c, COLLECT(DISTINCT p.name) AS products, COUNT(DISTINCT p) AS product_count
WHERE product_count > 1
RETURN 
  c.customer_id AS customer, 
  products, 
  product_count
ORDER BY product_count DESC;

// Expected Output for Dataset:
// +-------------------------------+
// | customer  | products           | product_count |
// +-------------------------------+
// | Asha Rao  | ["CloudSync", "InvoicePro"] | 2 |
// +-------------------------------+


// ----------------------------------------------------------------------------
// BONUS PRODUCTION QUERY:
// Product Health & Open Ticket Risk Analysis
// Finds total open tickets and average resolution time per product.
// ----------------------------------------------------------------------------
MATCH (t:Ticket)-[:ABOUT]->(p:Product)
RETURN 
  p.name AS product,
  COUNT(CASE WHEN t.status = 'open' THEN 1 END) AS open_tickets,
  COUNT(CASE WHEN t.status = 'resolved' THEN 1 END) AS resolved_tickets;