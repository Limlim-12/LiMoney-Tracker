from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db  # Importing db from your app.py

# ==========================================
# 1. DATABASE TABLES (SQLAlchemy Models)
# ==========================================


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)


class Loan(db.Model):
    __tablename__ = "loans"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    loan_name = db.Column(db.String(100))
    amount = db.Column(db.Float)
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    monthly_payment = db.Column(db.Float)
    notes = db.Column(db.Text)
    paid_amount = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LoanPayment(db.Model):
    __tablename__ = "loan_payments"
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loans.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float)
    pay_date = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Savings(db.Model):
    __tablename__ = "savings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    savings_name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, default=0)
    current_balance = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SavingsTransaction(db.Model):
    __tablename__ = "savings_transactions"
    id = db.Column(db.Integer, primary_key=True)
    savings_id = db.Column(db.Integer, db.ForeignKey("savings.id"), nullable=False)
    type = db.Column(db.String(20))
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(200))


class BudgetCategory(db.Model):
    __tablename__ = "budget_categories"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    planned_budget = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BudgetTransaction(db.Model):
    __tablename__ = "budget_transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(
        db.Integer, db.ForeignKey("budget_categories.id"), nullable=False
    )
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)
    expense_type = db.Column(db.String(20), default="daily")
    savings_id = db.Column(db.Integer, db.ForeignKey("savings.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserProfile(db.Model):
    __tablename__ = "user_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    surname = db.Column(db.String(100), nullable=True)
    firstname = db.Column(db.String(100), nullable=True)
    middle_initial = db.Column(db.String(10))
    nickname = db.Column(db.String(50))
    occupation = db.Column(db.String(100))
    company = db.Column(db.String(100))
    salary = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Card(db.Model):
    __tablename__ = "cards"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    bank_name = db.Column(db.String(100))
    card_type = db.Column(db.String(50))
    last_four = db.Column(db.String(4))
    balance = db.Column(db.Float)
    color_theme = db.Column(db.String(20))
    usage_tag = db.Column(db.String(50))


# --- Helper: Convert Database Object to Dictionary ---
def to_dict(obj):
    if not obj:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# ==========================================
# 2. USER FUNCTIONS
# ==========================================


def create_user(username, email, password):
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)
    try:
        db.session.add(new_user)
        db.session.commit()
        return True
    except:
        db.session.rollback()
        return False


def get_user_by_username(username):
    user = User.query.filter_by(username=username).first()
    return to_dict(user)


def verify_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        return to_dict(user)
    return None


def init_db():
    # Handled automatically in app.py now
    pass


# ==========================================
# 3. TRANSACTION FUNCTIONS
# ==========================================


def get_transactions(user_id):
    txns = Transaction.query.filter_by(user_id=user_id).all()
    return [to_dict(t) for t in txns]


def add_transaction(user_id, description, amount, t_type):
    new_txn = Transaction(
        user_id=user_id, description=description, amount=amount, type=t_type
    )
    db.session.add(new_txn)
    db.session.commit()


# ==========================================
# 4. LOAN FUNCTIONS
# ==========================================


def add_loan(user_id, loan_name, amount, start_date, end_date, monthly_payment, notes):
    new_loan = Loan(
        user_id=user_id,
        loan_name=loan_name,
        amount=amount,
        start_date=start_date,
        end_date=end_date,
        monthly_payment=monthly_payment,
        notes=notes,
        status="active",
    )
    db.session.add(new_loan)
    db.session.commit()


def get_loans(user_id):
    loans = Loan.query.filter_by(user_id=user_id).all()
    return [to_dict(l) for l in loans]


def get_loan_by_id(loan_id):
    loan = Loan.query.get(loan_id)
    return to_dict(loan)


def pay_loan(loan_id, monthly_payment):
    loan = Loan.query.get(loan_id)
    if loan:
        loan.paid_amount += monthly_payment
        db.session.commit()


def delete_loan(loan_id):
    loan = Loan.query.get(loan_id)
    if loan:
        db.session.delete(loan)
        db.session.commit()


def update_loan_status(loan_id, status):
    loan = Loan.query.get(loan_id)
    if loan:
        loan.status = status
        db.session.commit()


def add_loan_payment(loan_id, user_id, amount, pay_date):
    payment = LoanPayment(
        loan_id=loan_id, user_id=user_id, amount=amount, pay_date=pay_date
    )
    db.session.add(payment)
    db.session.commit()


def get_loan_payments(loan_id):
    payments = (
        LoanPayment.query.filter_by(loan_id=loan_id)
        .order_by(LoanPayment.created_at.desc())
        .all()
    )
    return [to_dict(p) for p in payments]


def get_total_loan_payments(loan_id):
    result = (
        db.session.query(db.func.sum(LoanPayment.amount))
        .filter_by(loan_id=loan_id)
        .scalar()
    )
    return result or 0


def get_total_paid_this_month(loan_id, year, month):
    # This queries payments by string matching the date (YYYY-MM)
    # Assumes pay_date format is YYYY-MM-DD
    search_str = f"{year}-{month:02}"
    payments = LoanPayment.query.filter(
        LoanPayment.loan_id == loan_id, LoanPayment.pay_date.like(f"{search_str}%")
    ).all()
    return sum(p.amount for p in payments)


# ==========================================
# 5. SAVINGS FUNCTIONS
# ==========================================


def add_savings(user_id, savings_name, target_amount=0):
    new_savings = Savings(
        user_id=user_id,
        savings_name=savings_name,
        target_amount=target_amount,
        current_balance=0,
    )
    db.session.add(new_savings)
    db.session.commit()


def get_active_savings(user_id):
    savings = Savings.query.filter_by(user_id=user_id).all()
    return [to_dict(s) for s in savings]


def get_savings(user_id):
    return get_active_savings(user_id)


def deposit_savings(savings_id, amount, note=""):
    txn = SavingsTransaction(
        savings_id=savings_id, type="deposit", amount=amount, note=note
    )
    db.session.add(txn)
    savings = Savings.query.get(savings_id)
    if savings:
        savings.current_balance += amount
    db.session.commit()


def withdraw_savings(savings_id, amount, note=""):
    txn = SavingsTransaction(
        savings_id=savings_id, type="withdraw", amount=amount, note=note
    )
    db.session.add(txn)
    savings = Savings.query.get(savings_id)
    if savings:
        savings.current_balance -= amount
    db.session.commit()


def get_savings_transactions(savings_id):
    txns = (
        SavingsTransaction.query.filter_by(savings_id=savings_id)
        .order_by(SavingsTransaction.timestamp.desc())
        .all()
    )
    return [to_dict(t) for t in txns]


def get_total_savings(user_id):
    result = (
        db.session.query(db.func.sum(Savings.current_balance))
        .filter_by(user_id=user_id)
        .scalar()
    )
    return result or 0


def delete_savings(savings_id):
    SavingsTransaction.query.filter_by(savings_id=savings_id).delete()
    Savings.query.filter_by(id=savings_id).delete()
    db.session.commit()


# ==========================================
# 6. BUDGET FUNCTIONS
# ==========================================

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
    new_cat = BudgetCategory(user_id=user_id, name=name, planned_budget=planned_budget)
    db.session.add(new_cat)
    db.session.commit()


def seed_default_categories(user_id):
    count = BudgetCategory.query.filter_by(user_id=user_id).count()
    if count == 0:
        for cat_name in DEFAULT_CATEGORIES:
            add_category(user_id, cat_name, 0)


def get_categories(user_id):
    cats = BudgetCategory.query.filter_by(user_id=user_id).all()
    return [to_dict(c) for c in cats]


def get_budget_categories(user_id):
    seed_default_categories(user_id)
    return get_categories(user_id)


def update_category_budget(category_id, planned_budget):
    cat = BudgetCategory.query.get(category_id)
    if cat:
        cat.planned_budget = planned_budget
        db.session.commit()


def update_budget_category(user_id, category_id, planned_budget):
    cat = BudgetCategory.query.filter_by(id=category_id, user_id=user_id).first()
    if cat:
        cat.planned_budget = planned_budget
        db.session.commit()


def add_budget_transaction(
    user_id, category_id, description, amount, expense_type="daily", savings_id=None
):
    new_expense = BudgetTransaction(
        user_id=user_id,
        category_id=category_id,
        description=description,
        amount=amount,
        expense_type=expense_type,
        savings_id=savings_id,
    )
    db.session.add(new_expense)

    if savings_id:
        withdraw_savings(savings_id, amount, f"Budget expense: {description}")

    db.session.commit()


def get_budget_transactions(user_id):
    # Perform a Join to get Category Name and Savings Name
    results = (
        db.session.query(BudgetTransaction, BudgetCategory.name, Savings.savings_name)
        .join(BudgetCategory, BudgetTransaction.category_id == BudgetCategory.id)
        .outerjoin(Savings, BudgetTransaction.savings_id == Savings.id)
        .filter(BudgetTransaction.user_id == user_id)
        .order_by(BudgetTransaction.created_at.desc())
        .all()
    )

    txns = []
    for txn, cat_name, sav_name in results:
        t_dict = to_dict(txn)
        t_dict["category_name"] = cat_name
        t_dict["savings_name"] = sav_name
        txns.append(t_dict)
    return txns


def get_actual_spent(user_id, category_id):
    result = (
        db.session.query(db.func.sum(BudgetTransaction.amount))
        .filter_by(user_id=user_id, category_id=category_id)
        .scalar()
    )
    return result or 0


def delete_budget_transaction(txn_id, user_id):
    txn = BudgetTransaction.query.filter_by(id=txn_id, user_id=user_id).first()
    if txn:
        db.session.delete(txn)
        db.session.commit()


def get_category_summary(user_id):
    """Returns categories with their planned budget AND actual spent."""
    categories = (
        BudgetCategory.query.filter_by(user_id=user_id)
        .order_by(BudgetCategory.name)
        .all()
    )
    summary = []
    for cat in categories:
        spent = (
            db.session.query(db.func.sum(BudgetTransaction.amount))
            .filter_by(category_id=cat.id)
            .scalar()
            or 0
        )
        summary.append(
            {
                "id": cat.id,
                "name": cat.name,
                "planned_budget": cat.planned_budget,
                "actual_spent": spent,
            }
        )
    return summary


def get_expense_totals_by_type(user_id):
    """Returns totals for daily, monthly, yearly expenses."""
    results = (
        db.session.query(
            BudgetTransaction.expense_type, db.func.sum(BudgetTransaction.amount)
        )
        .filter_by(user_id=user_id)
        .group_by(BudgetTransaction.expense_type)
        .all()
    )

    totals = {"daily": 0, "monthly": 0, "yearly": 0}
    for type_, total in results:
        totals[type_] = total or 0
    return totals


# ==========================================
# 7. PROFILE & CARD FUNCTIONS
# ==========================================


def get_profile(user_id):
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    return to_dict(profile)


def save_personal_info(user_id, surname, firstname, middle_initial, nickname):
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if profile:
        profile.surname = surname
        profile.firstname = firstname
        profile.middle_initial = middle_initial
        profile.nickname = nickname
        profile.updated_at = datetime.utcnow()
    else:
        new_profile = UserProfile(
            user_id=user_id,
            surname=surname,
            firstname=firstname,
            middle_initial=middle_initial,
            nickname=nickname,
        )
        db.session.add(new_profile)
    db.session.commit()


def save_work_info(user_id, occupation, company, salary):
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if profile:
        profile.occupation = occupation
        profile.company = company
        profile.salary = salary
        profile.updated_at = datetime.utcnow()
    else:
        new_profile = UserProfile(
            user_id=user_id,
            surname="",
            firstname="",
            occupation=occupation,
            company=company,
            salary=salary,
        )
        db.session.add(new_profile)
    db.session.commit()


def get_total_debt(user_id):
    active_loans = Loan.query.filter(
        Loan.user_id == user_id, Loan.status != "Full Loan Paid"
    ).all()
    total_debt = sum(l.amount - l.paid_amount for l in active_loans)
    return total_debt


def add_card(user_id, bank_name, card_type, last_four, balance, color_theme, usage_tag):
    new_card = Card(
        user_id=user_id,
        bank_name=bank_name,
        card_type=card_type,
        last_four=last_four,
        balance=balance,
        color_theme=color_theme,
        usage_tag=usage_tag,
    )
    db.session.add(new_card)
    db.session.commit()


def get_user_cards(user_id):
    cards = Card.query.filter_by(user_id=user_id).all()
    return [to_dict(c) for c in cards]


def delete_card(card_id):
    card = Card.query.get(card_id)
    if card:
        db.session.delete(card)
        db.session.commit()


# ==========================================
# 8. SMART BUDGETTER MODELS (NEW)
# ==========================================


class SalaryBudget(db.Model):
    __tablename__ = "salary_budgets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    salary_amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(50), nullable=False)  # Semi-Monthly, Weekly, etc.
    total_allocated = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ai_reasoning = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to items
    items = db.relationship(
        "SalaryBudgetItem", backref="budget", lazy=True, cascade="all, delete-orphan"
    )


class SalaryBudgetItem(db.Model):
    __tablename__ = "salary_budget_items"
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(
        db.Integer, db.ForeignKey("salary_budgets.id"), nullable=False
    )
    item_name = db.Column(db.String(100), nullable=False)
    user_amount = db.Column(db.Float, default=0)  # What user manually typed
    ai_amount = db.Column(db.Float, default=0)  # What system suggested
    is_auto_filled = db.Column(db.Boolean, default=False)


# ... (Keep your helper functions like to_dict, create_user, etc.) ...

# --- ADD THESE NEW FUNCTIONS AT THE END OF models.py ---


def create_salary_budget(user_id, salary_amount, frequency, ai_reasoning=""):
    new_budget = SalaryBudget(
        user_id=user_id,
        salary_amount=salary_amount,
        frequency=frequency,
        ai_reasoning=ai_reasoning,  # <--- Pass it here
    )
    db.session.add(new_budget)
    db.session.commit()
    return new_budget


def add_salary_item(budget_id, item_name, user_amount, ai_amount, is_auto_filled):
    item = SalaryBudgetItem(
        budget_id=budget_id,
        item_name=item_name,
        user_amount=user_amount,
        ai_amount=ai_amount,
        is_auto_filled=is_auto_filled,
    )
    db.session.add(item)
    db.session.commit()


def get_user_budgets(user_id):
    # Get latest 5 budgets for history
    return (
        SalaryBudget.query.filter_by(user_id=user_id)
        .order_by(SalaryBudget.created_at.desc())
        .limit(5)
        .all()
    )


def get_budget_details(budget_id):
    budget = SalaryBudget.query.get(budget_id)
    if budget:
        return {"info": to_dict(budget), "items": [to_dict(i) for i in budget.items]}
    return None
