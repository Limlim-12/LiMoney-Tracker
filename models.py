import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DB_NAME = "money.db"


# ------------------ DB CONNECTION ------------------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # returns rows as dict-like objects
    return conn


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Users table
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT
        )"""
    )

    # Transactions table
    c.execute(
        """CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT,
            amount REAL,
            type TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"""
    )

    # Loans table
    c.execute(
        """CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            loan_name TEXT,
            amount REAL,
            start_date TEXT,
            end_date TEXT,
            monthly_payment REAL,
            notes TEXT,
            paid_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"""
    )

    # Loan payments
    c.execute(
        """CREATE TABLE IF NOT EXISTS loan_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            user_id INTEGER,
            amount REAL,
            pay_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"""
    )

    # Savings table
    c.execute(
        """CREATE TABLE IF NOT EXISTS savings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            savings_name TEXT NOT NULL,
            target_amount REAL DEFAULT 0,  -- <<< ADD THIS LINE
            current_balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"""
    )

    # Savings transactions
    c.execute(
        """CREATE TABLE IF NOT EXISTS savings_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            savings_id INTEGER NOT NULL,
            type TEXT CHECK(type IN ('deposit','withdraw')),
            amount REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note TEXT,
            FOREIGN KEY(savings_id) REFERENCES savings(id)
        )"""
    )

    # Budget Categories
    c.execute(
        """CREATE TABLE IF NOT EXISTS budget_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            planned_budget REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )"""
    )

    # Budget Transactions (expenses assigned to categories)
    c.execute(
        """CREATE TABLE IF NOT EXISTS budget_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            expense_type TEXT DEFAULT 'daily',
            savings_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(category_id) REFERENCES budget_categories(id),
            FOREIGN KEY(savings_id) REFERENCES savings(id)
        )"""
    )

    # User Profiles table
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            surname TEXT NOT NULL,
            firstname TEXT NOT NULL,
            middle_initial TEXT,
            nickname TEXT,
            occupation TEXT,
            company TEXT,
            salary REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )"""
    )

    # NEW: Wallet Cards Table
    c.execute(
        """CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bank_name TEXT,
            card_type TEXT, -- e.g., 'Debit', 'Credit'
            last_four TEXT,
            balance REAL,
            color_theme TEXT, -- 'blue', 'gold', 'black', 'platinum'
            usage_tag TEXT, -- e.g., 'Grocery', 'Gas', 'Online'
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"""
    )
    conn.commit()
    conn.close()


# ------------------ USER FUNCTIONS ------------------
def create_user(username, email, password):
    conn = get_db_connection()
    c = conn.cursor()
    hashed_password = generate_password_hash(password)
    try:
        c.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user


def verify_user(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user["password"], password):
        return user
    return None


# ------------------ TRANSACTION FUNCTIONS ------------------
def get_transactions(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE user_id=?", (user_id,))
    transactions = c.fetchall()
    conn.close()
    return [dict(t) for t in transactions]


def add_transaction(user_id, description, amount, t_type):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (user_id, description, amount, type) VALUES (?, ?, ?, ?)",
        (user_id, description, amount, t_type),
    )
    conn.commit()
    conn.close()


# ------------------ LOAN FUNCTIONS ------------------
def add_loan(user_id, loan_name, amount, start_date, end_date, monthly_payment, notes):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO loans 
           (user_id, loan_name, amount, start_date, end_date, monthly_payment, notes, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            loan_name,
            amount,
            start_date,
            end_date,
            monthly_payment,
            notes,
            "active",
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_loans(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM loans WHERE user_id=?", (user_id,))
    loans = c.fetchall()
    conn.close()
    return [dict(l) for l in loans]


def get_loan_by_id(loan_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM loans WHERE id=?", (loan_id,))
    loan = c.fetchone()
    conn.close()
    return dict(loan) if loan else None


def pay_loan(loan_id, monthly_payment):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE loans SET paid_amount = paid_amount + ? WHERE id=?",
        (monthly_payment, loan_id),
    )
    conn.commit()
    conn.close()


def delete_loan(loan_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM loans WHERE id=?", (loan_id,))
    conn.commit()
    conn.close()


def update_loan_status(loan_id, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE loans SET status=? WHERE id=?", (status, loan_id))
    conn.commit()
    conn.close()


def add_loan_payment(loan_id, user_id, amount, pay_date):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO loan_payments (loan_id, user_id, amount, pay_date)
           VALUES (?, ?, ?, ?)""",
        (loan_id, user_id, amount, pay_date),
    )
    conn.commit()
    conn.close()


def get_loan_payments(loan_id):
    conn = get_db_connection()
    c = conn.cursor()
    # Updated to sort by created_at DESC (Newest first)
    c.execute("SELECT * FROM loan_payments WHERE loan_id=? ORDER BY created_at DESC", (loan_id,))
    return c.fetchall()


def get_total_paid_this_month(loan_id, year, month):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """SELECT SUM(amount) as total
           FROM loan_payments
           WHERE loan_id=? AND strftime('%Y', pay_date)=? AND strftime('%m', pay_date)=?""",
        (loan_id, str(year), f"{month:02}"),
    )
    total = c.fetchone()[0]
    conn.close()
    return total or 0


def get_total_loan_payments(loan_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT SUM(amount) as total FROM loan_payments WHERE loan_id=?", (loan_id,)
    )
    total = c.fetchone()[0]
    conn.close()
    return total or 0


# ------------------ SAVINGS FUNCTIONS ------------------
def add_savings(user_id, savings_name, target_amount=0):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO savings (user_id, savings_name, target_amount, current_balance)
           VALUES (?, ?, ?, 0)""",
        (user_id, savings_name, target_amount),
    )
    conn.commit()
    conn.close()


def get_active_savings(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM savings WHERE user_id=?", (user_id,))
    savings = c.fetchall()
    conn.close()
    return [dict(s) for s in savings]


def deposit_savings(savings_id, amount, note=""):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO savings_transactions (savings_id, type, amount, note) 
           VALUES (?, 'deposit', ?, ?)""",
        (savings_id, amount, note),
    )
    c.execute(
        "UPDATE savings SET current_balance = current_balance + ? WHERE id=?",
        (amount, savings_id),
    )
    conn.commit()
    conn.close()


def withdraw_savings(savings_id, amount, note=""):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO savings_transactions (savings_id, type, amount, note) 
           VALUES (?, 'withdraw', ?, ?)""",
        (savings_id, amount, note),
    )
    c.execute(
        "UPDATE savings SET current_balance = current_balance - ? WHERE id=?",
        (amount, savings_id),
    )
    conn.commit()
    conn.close()


def get_savings_transactions(savings_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM savings_transactions WHERE savings_id=? ORDER BY timestamp DESC",
        (savings_id,),
    )
    txns = c.fetchall()
    conn.close()
    return [dict(t) for t in txns]

def get_savings(user_id):
    """Fetch all savings goals for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM savings WHERE user_id=?", (user_id,))
    return c.fetchall()


def get_savings_transactions(savings_id):
    """Fetch history for a specific savings goal."""
    conn = get_db_connection()
    c = conn.cursor()
    # FIX: Change 'created_at' to 'timestamp' to match your database table
    c.execute(
        "SELECT * FROM savings_transactions WHERE savings_id=? ORDER BY timestamp DESC",
        (savings_id,),
    )
    return c.fetchall()


# ------------------ BUDGET FUNCTIONS ------------------

DEFAULT_CATEGORIES = [
    "Food & Drinks",
    "Transportation",
    "Utilities",
    "Rent & Housing",
    "Health & Medicine",
    "Groceries",
    "Entertainment",
    "Savings & Investments",
    "Debt Payments",
    "Miscellaneous",
]


def add_category(user_id, name, planned_budget=0):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO budget_categories (user_id, name, planned_budget) VALUES (?, ?, ?)",
        (user_id, name, planned_budget),
    )
    conn.commit()
    conn.close()


def seed_default_categories(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM budget_categories WHERE user_id=?", (user_id,))
    count = c.fetchone()[0]

    if count == 0:
        for cat in DEFAULT_CATEGORIES:
            c.execute(
                "INSERT INTO budget_categories (user_id, name, planned_budget) VALUES (?, ?, ?)",
                (user_id, cat, 0),
            )
        conn.commit()
    conn.close()


def get_categories(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM budget_categories WHERE user_id=?", (user_id,))
    cats = c.fetchall()
    conn.close()
    return [dict(c) for c in cats]


def get_budget_categories(user_id):
    seed_default_categories(user_id)
    return get_categories(user_id)


def update_category_budget(category_id, planned_budget):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE budget_categories SET planned_budget=? WHERE id=?",
        (planned_budget, category_id),
    )
    conn.commit()
    conn.close()


def add_budget_transaction(
    user_id, category_id, description, amount, expense_type="daily", savings_id=None
):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO budget_transactions 
           (user_id, category_id, description, amount, expense_type, savings_id) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, category_id, description, amount, expense_type, savings_id),
    )

    if savings_id:
        c.execute(
            """INSERT INTO savings_transactions (savings_id, type, amount, note)
               VALUES (?, 'withdraw', ?, ?)""",
            (savings_id, amount, f"Budget expense: {description}"),
        )
        c.execute(
            "UPDATE savings SET current_balance = current_balance - ? WHERE id=?",
            (amount, savings_id),
        )

    conn.commit()
    conn.close()


def get_budget_transactions(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """SELECT bt.*, bc.name as category_name, s.savings_name
           FROM budget_transactions bt
           JOIN budget_categories bc ON bt.category_id = bc.id
           LEFT JOIN savings s ON bt.savings_id = s.id
           WHERE bt.user_id=?
           ORDER BY bt.created_at DESC""",
        (user_id,),
    )
    txns = c.fetchall()
    conn.close()
    return [dict(t) for t in txns]


def get_actual_spent(user_id, category_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """SELECT IFNULL(SUM(amount), 0) as actual_spent
           FROM budget_transactions
           WHERE user_id=? AND category_id=?""",
        (user_id, category_id),
    )
    result = c.fetchone()
    conn.close()
    return result["actual_spent"] if result else 0


def get_category_summary(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """SELECT bc.id, bc.name, bc.planned_budget,
                  IFNULL(SUM(bt.amount),0) as actual_spent
           FROM budget_categories bc
           LEFT JOIN budget_transactions bt ON bc.id = bt.category_id
           WHERE bc.user_id=?
           GROUP BY bc.id
           ORDER BY bc.name""",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expense_totals_by_type(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """SELECT expense_type, IFNULL(SUM(amount),0) as total
           FROM budget_transactions
           WHERE user_id=?
           GROUP BY expense_type""",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()

    totals = {"daily": 0, "monthly": 0, "yearly": 0}
    for r in rows:
        totals[r["expense_type"]] = r["total"]
    return totals


def delete_budget_transaction(txn_id, user_id):
    """Delete a budget transaction safely (only if it belongs to the user)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM budget_transactions
        WHERE id = ? AND user_id = ?
        """,
        (txn_id, user_id),
    )

    conn.commit()
    conn.close()


def update_budget_category(user_id, category_id, planned_budget):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE budget_categories SET planned_budget=? WHERE id=? AND user_id=?",
        (planned_budget, category_id, user_id),
    )
    conn.commit()
    conn.close()


# ------------------ PROFILE FUNCTIONS ------------------


def create_profile_table():
    """Ensure the user_profiles table exists (call inside init_db)."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            surname TEXT NOT NULL,
            firstname TEXT NOT NULL,
            middle_initial TEXT,
            nickname TEXT,
            occupation TEXT,
            company TEXT,
            salary REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )"""
    )
    conn.commit()
    conn.close()


def get_profile(user_id):
    """Fetch a user profile by user_id."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,))
    profile = c.fetchone()
    conn.close()
    return dict(profile) if profile else None


def save_personal_info(user_id, surname, firstname, middle_initial, nickname):
    """Insert or update personal info."""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM user_profiles WHERE user_id=?", (user_id,))
    exists = c.fetchone()

    if exists:
        c.execute(
            """UPDATE user_profiles 
               SET surname=?, firstname=?, middle_initial=?, nickname=?, updated_at=? 
               WHERE user_id=?""",
            (surname, firstname, middle_initial, nickname, datetime.utcnow(), user_id),
        )
    else:
        c.execute(
            """INSERT INTO user_profiles 
               (user_id, surname, firstname, middle_initial, nickname) 
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, surname, firstname, middle_initial, nickname),
        )

    conn.commit()
    conn.close()


def save_work_info(user_id, occupation, company, salary):
    """Insert or update work info (occupation, company, salary)."""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM user_profiles WHERE user_id=?", (user_id,))
    exists = c.fetchone()

    if exists:
        c.execute(
            """UPDATE user_profiles
               SET occupation=?, company=?, salary=?, updated_at=?
               WHERE user_id=?""",
            (occupation, company, salary, datetime.utcnow(), user_id),
        )
    else:
        c.execute(
            """INSERT INTO user_profiles 
               (user_id, surname, firstname, middle_initial, nickname, occupation, company, salary)
               VALUES (?, '', '', '', '', ?, ?, ?)""",
            (user_id, occupation, company, salary),
        )

    conn.commit()
    conn.close()


def get_total_savings(user_id):
    """Get the sum of all savings balances for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(current_balance) FROM savings WHERE user_id=?", (user_id,))
    total = c.fetchone()[0]
    conn.close()
    return total or 0


def get_total_debt(user_id):
    """Get the sum of all outstanding loan balances for a user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT SUM(amount - paid_amount) FROM loans WHERE user_id=? AND status != 'Full Loan Paid'",
        (user_id,),
    )
    total = c.fetchone()[0]
    conn.close()
    return total or 0

def delete_savings(savings_id):
    """Delete a savings goal and its history."""
    conn = get_db_connection()
    c = conn.cursor()
    # Optional: Delete transactions related to this savings first (clean up)
    # c.execute("DELETE FROM savings_transactions WHERE savings_id=?", (savings_id,))
    c.execute("DELETE FROM savings WHERE id=?", (savings_id,))
    conn.commit()
    conn.close()

    # --- PASTE THIS AT THE BOTTOM OF models.py ---

def add_card(user_id, bank_name, card_type, last_four, balance, color_theme, usage_tag):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO cards (user_id, bank_name, card_type, last_four, balance, color_theme, usage_tag) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, bank_name, card_type, last_four, balance, color_theme, usage_tag),
    )
    conn.commit()
    conn.close()

def get_user_cards(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE user_id=?", (user_id,))
    return c.fetchall()

def delete_card(card_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM cards WHERE id=?", (card_id,))
    conn.commit()
    conn.close()
