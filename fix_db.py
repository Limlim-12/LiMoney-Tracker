import sqlite3
import os


def update_database():
    print("🛡️ Starting Database Schema Update...")

    # Path to your SQLite database
    # Based on standard Flask setups, it's usually in 'instance/limoney.db'
    db_path = os.path.join("instance", "limoney.db")

    if not os.path.exists(db_path):
        # Fallback if not in instance folder
        db_path = "limoney.db"

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        print(f"📍 Connected to: {db_path}")

        # 1. Update 'loan_payments' table
        print("📝 Updating 'loan_payments'...")
        try:
            c.execute("ALTER TABLE loan_payments ADD COLUMN created_at DATETIME")
            print("   -> Added 'created_at' column.")
        except sqlite3.OperationalError:
            print("   -> Column 'created_at' already exists.")

        # Backfill existing payments with current timestamp
        c.execute(
            "UPDATE loan_payments SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )

        # 2. Update 'salary_budgets' table (CRITICAL for AI Reasoning)
        print("📝 Updating 'salary_budgets'...")
        try:
            c.execute("ALTER TABLE salary_budgets ADD COLUMN ai_reasoning TEXT")
            print("   -> Added 'ai_reasoning' column.")
        except sqlite3.OperationalError:
            print("   -> Column 'ai_reasoning' already exists.")

        # 3. Create Trigger for loan payments (Automation)
        # This ensures every new payment automatically gets a timestamp
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
        print("   -> Automation trigger verified.")

        conn.commit()
        print("\n✅ Success! Database schema is now up to date.")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    update_database()
