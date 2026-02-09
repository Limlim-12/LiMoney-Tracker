from models import get_db_connection
import sqlite3

def update_loans_db():
    print("🛡️ Updating Loan Database...")
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 1. Add 'created_at' column to loan_payments
        try:
            c.execute("ALTER TABLE loan_payments ADD COLUMN created_at TEXT")
            print("   -> Added 'created_at' column.")
        except sqlite3.OperationalError:
            print("   -> Column 'created_at' already exists (skipping step).")

        # 2. Backfill existing payments with the current time
        # (Since we don't have historical time, we use NOW for old records to prevent errors)
        c.execute("UPDATE loan_payments SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        print("   -> Updated existing records.")

        # 3. Create Trigger for future payments
        trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS set_timestamp_loans
        AFTER INSERT ON loan_payments
        BEGIN
            UPDATE loan_payments 
            SET created_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END;
        """
        c.execute(trigger_sql)
        print("   -> Created automation trigger.")

        conn.commit()
        print("\n✅ Success! Loan history is ready.")
        
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_loans_db()