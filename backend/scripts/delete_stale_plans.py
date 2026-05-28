import sys
import psycopg2 as psycopg

DB_URL = "postgresql://crece:crece_dev@localhost:5438/crece"

def main():
    plan_ids = (77, 74, 71, 70)
    print(f"Connecting to database to delete stale plans: {plan_ids}...")
    try:
        conn = psycopg.connect(DB_URL)
        with conn.cursor() as cur:
            # Let's count how many exist first
            cur.execute("SELECT id, tipo, created_at FROM planes_ia WHERE id IN %s", (plan_ids,))
            rows = cur.fetchall()
            print(f"Found {len(rows)} plans before deletion:")
            for r in rows:
                print(f"  ID: #{r[0]} | Tipo: {r[1]} | Creado: {r[2]}")
            
            if not rows:
                print("No plans to delete. They might have been deleted already.")
                return 0
                
            cur.execute("DELETE FROM planes_ia WHERE id IN %s", (plan_ids,))
            deleted = cur.rowcount
            print(f"Deleted {deleted} plans.")
            
        conn.commit()
        conn.close()
        print("Transaction committed successfully.")
        return 0
    except Exception as e:
        print(f"Error during deletion: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
