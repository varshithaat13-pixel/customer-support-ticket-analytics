import os
import json
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from part_a.pipeline import deduplicate, load_and_validate


class SupportKnowledgeGraph:
    def __init__(self, uri: str, auth: tuple[str, str]):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def setup_schema(self):
        """Apply uniqueness constraints."""
        constraints = [
            "CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE;",
            "CREATE CONSTRAINT ticket_id_unique IF NOT EXISTS FOR (t:Ticket) REQUIRE t.ticket_id IS UNIQUE;",
            "CREATE CONSTRAINT product_name_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.name IS UNIQUE;",
        ]
        with self.driver.session() as session:
            for query in constraints:
                session.run(query)

    def ingest_tickets(self, tickets: list[dict]):
        """Ingest clean tickets into the graph model."""
        cypher = """
        UNWIND $tickets AS row
        MERGE (c:Customer {customer_id: row.customer})
        MERGE (p:Product {name: row.product})
        MERGE (t:Ticket {ticket_id: row.ticket_id})
          ON CREATE SET 
            t.issue = row.issue,
            t.status = row.status,
            t.created_at = datetime(row.created_at),
            t.resolved_at = CASE WHEN row.resolved_at IS NOT NULL THEN datetime(row.resolved_at) ELSE null END
        MERGE (c)-[r1:RAISED]->(t)
          ON CREATE SET r1.at = datetime(row.created_at)
        MERGE (t)-[r2:ABOUT]->(p);
        """
        with self.driver.session() as session:
            session.run(cypher, tickets=tickets)

    def get_multi_product_customers(self) -> list[dict]:
        """Find every customer who raised tickets about >1 distinct product."""
        query = """
        MATCH (c:Customer)-[:RAISED]->(t:Ticket)-[:ABOUT]->(p:Product)
        WITH c, COLLECT(DISTINCT p.name) AS products, COUNT(DISTINCT p) AS product_count
        WHERE product_count > 1
        RETURN 
          c.customer_id AS customer, 
          products, 
          product_count
        ORDER BY product_count DESC;
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [
                {
                    "customer": record["customer"],
                    "products": record["products"],
                    "product_count": record["product_count"],
                }
                for record in result
            ]


def build_and_query_graph():
    project_dir = Path(__file__).resolve().parents[2]
    env_path = project_dir / ".env"
    load_dotenv(env_path)

    required_settings = ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD")
    missing_settings = [
        setting for setting in required_settings if not os.getenv(setting, "").strip()
    ]
    if missing_settings:
        raise ValueError(
            f"Missing required Neo4j settings in {env_path}: "
            + ", ".join(missing_settings)
        )

    raw_path = project_dir / "data" / "tickets_raw.json"
    tickets, _ = deduplicate(load_and_validate(str(raw_path)))
    clean_tickets = [ticket.model_dump(mode="json") for ticket in tickets]

    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USER"]
    password = os.environ["NEO4J_PASSWORD"]

    print(f"Connecting to Neo4j instance at {uri}...")

    kg = SupportKnowledgeGraph(uri=uri, auth=(user, password))
    try:
        print("1. Applying schema constraints...")
        kg.setup_schema()

        print("2. Ingesting tickets into Knowledge Graph...")
        kg.ingest_tickets(clean_tickets)

        print("3. Querying customers with >1 product...")
        results = kg.get_multi_product_customers()
        print("\n--- Query Results ---")
        print(json.dumps(results, indent=2))

        return results

    except Exception as e:
        print(f"\n[Neo4j Connection Error]: {e}")
        print("Verify the URI, instance status, credentials, and network access.")
        raise
    finally:
        kg.close()


if __name__ == "__main__":
    build_and_query_graph()