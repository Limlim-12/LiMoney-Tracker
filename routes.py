from flask import render_template, request, redirect, session, url_for, flash, send_from_directory
import models
from functools import wraps
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


# -------------------------------
# Login required decorator
# -------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


# -------------------------------
# Routes registration
# -------------------------------
def init_routes(app):
    app.secret_key = "supersecretkey"  # ⚠️ Move to env var in production

    # -------------------------------
    # Template filter for date formatting
    # -------------------------------
    @app.template_filter("datetimeformat")
    def datetimeformat(value, format="%b %d, %Y"):
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
        except (ValueError, TypeError):
            try:
                dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                try:
                    dt = datetime.strptime(value, "%Y-%m-%d")
                except (ValueError, TypeError):
                    return value  # Return original value if parsing fails
        return dt.strftime(format)

    # ------------------ AUTH ------------------
    @app.route("/account")
    def account():
        return render_template("account.html", page="login")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return render_template("account.html", page="register")
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("register"))
        success = models.create_user(username, email, password)
        if not success:
            flash("Username or Email already exists", "error")
            return redirect(url_for("register"))
        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("account.html", page="login")
        username = request.form["username"].strip()
        password = request.form["password"]
        user = models.verify_user(username, password)
        if user:
            session["user_id"], session["username"] = user[0], user[1]
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for("login"))

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out", "info")
        return redirect(url_for("login"))
    
    @app.route('/sw.js')
    def service_worker():
    # This serves the file from static/sw.js but makes it appear at localhost:5000/sw.js
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')

    # ------------------ DASHBOARD ------------------
    @app.route("/")
    @login_required
    def dashboard():
        user_id = session["user_id"]
    
    # --- 1. Fetch Basic Data ---
        transactions = models.get_transactions(user_id)
    
    # Calculate "Cash Flow" Balance (Income - Expenses from transactions)
    # We keep this variable 'balance' in case your charts use it.
        balance = sum(
        t["amount"] if t["type"] == "income" else -t["amount"] for t in transactions
    )

    # Get Total Savings
        total_savings = models.get_total_savings(user_id) or 0

    # --- 2. Digital Wallet (Assets) ---
        try:
            cards = models.get_user_cards(user_id)
        except:
            cards = []
    
    # Calculate Total Wallet Money (Sum of all cards)
        total_wallet = sum(card["balance"] for card in cards)

    # --- 3. Loans & Real Debt (Liabilities) ---
        loans = models.get_loans(user_id)
    
        loan_labels = []
        loan_totals = []
        loan_paids = []
    
        total_remaining_debt = 0

        for loan in loans:
        # Get payments for this specific loan
            paid = models.get_total_loan_payments(loan["id"]) or 0
        
        # Calculate remaining debt for this loan
            remaining = loan["amount"] - paid
            if remaining > 0:
                total_remaining_debt += remaining

        # Prepare Chart Data
            loan_labels.append(loan["loan_name"])
            loan_totals.append(loan["amount"])
            loan_paids.append(paid)

    # --- 4. The Net Balance Formula ---
    # (Wallet Assets + Savings Assets) - (Remaining Debt Liabilities)
        net_balance = (total_wallet + total_savings) - total_remaining_debt

        return render_template(
            "dashboard.html",
            transactions=transactions,
            balance=balance,
            total_wallet=total_wallet,        # Needed for Dashboard Summary
            total_savings=total_savings,
            total_debt=total_remaining_debt,  # Now shows actual debt, not just loan amount
            net_balance=net_balance,          # The new Hero Number
            username=session["username"],
            loan_labels=loan_labels,
            loan_totals=loan_totals,
            loan_paids=loan_paids,
            cards=cards,
    )
    @app.route("/add", methods=["POST"])
    @login_required
    def add():
        description = request.form["description"].strip()
        try:
            amount = float(request.form["amount"])
        except ValueError:
            flash("Amount must be a number", "error")
            return redirect(url_for("dashboard"))
        t_type = request.form["type"]
        models.add_transaction(session["user_id"], description, amount, t_type)
        flash("Transaction added successfully!", "success")
        return redirect(url_for("dashboard"))

    # ------------------ LOAN TRACKER ------------------
    @app.route("/loan-tracker")
    @login_required
    def loan_tracker():
        loans = models.get_loans(session["user_id"])
        active_loans = []
        finished_loans = []
        today = date.today()
        for loan in loans:
            total_paid = models.get_total_loan_payments(loan["id"])
            remaining_balance = loan["amount"] - total_paid
            if remaining_balance <= 0:
                loan["status"] = "Full Loan Paid"
                models.update_loan_status(loan["id"], "Full Loan Paid")
                finished_loans.append(loan)
            else:
                active_loans.append(loan)
                if total_paid > 0:
                    loan["status"] = "Partial Payment"
                else:
                    loan["status"] = "Outstanding"
                start = datetime.strptime(loan["start_date"], "%Y-%m-%d").date()
                end = datetime.strptime(loan["end_date"], "%Y-%m-%d").date()
                if today > end:
                    loan["duration_months"] = 0
                    loan["duration_days"] = 0
                else:
                    delta = relativedelta(end, today)
                    loan["duration_months"] = delta.years * 12 + delta.months
                    total_days = (end - today).days
                    full_months_date = today + relativedelta(
                        months=loan["duration_months"]
                    )
                    days_in_full_months = (full_months_date - today).days
                    loan["duration_days"] = max(total_days - days_in_full_months, 0)
            loan["notes"] = loan.get("notes") or ""
        return render_template(
            "loan_tracker.html",
            active_loans=active_loans,
            finished_loans=finished_loans,
            username=session["username"],
            get_loan_payments=models.get_loan_payments,
            get_total_loan_payments=models.get_total_loan_payments,
            current_date=date.today().isoformat(),
        )

    @app.route("/add-loan", methods=["POST"])
    @login_required
    def add_loan():
        try:
            loan_name = request.form["loan_name"].strip()
            start_date = request.form["start_date"]
            end_date = request.form["end_date"]
            notes = request.form.get("notes", "").strip()
            loan_amount = float(request.form["loan_amount"])
            monthly_payment = float(request.form["monthly_payment"])
            if not loan_name or loan_amount <= 0 or monthly_payment <= 0:
                flash("Please enter valid loan details", "error")
            elif start_date > end_date:
                flash("End Date must be after Start Date", "error")
            else:
                models.add_loan(
                    session["user_id"],
                    loan_name,
                    loan_amount,
                    start_date,
                    end_date,
                    monthly_payment,
                    notes,
                )
                # FIX: Removed '✅'
                flash("Loan added successfully!", "success")
        except ValueError:
            flash("Amount and Monthly Payment must be numbers", "error")
        except Exception as e:
            flash(f"Error adding loan: {str(e)}", "error")
        return redirect(url_for("loan_tracker"))

    @app.route("/pay-loan/<int:loan_id>", methods=["POST"])
    @login_required
    def pay_loan(loan_id):
        loan = models.get_loan_by_id(loan_id)
        if not loan or loan["user_id"] != session["user_id"]:
            flash("Loan not found or unauthorized access", "error")
        else:
            try:
                pay_amount = float(request.form["pay_amount"])
                pay_date = request.form["pay_date"]
                models.add_loan_payment(
                    loan_id, session["user_id"], pay_amount, pay_date
                )
                # You can keep 💸 if you want a second icon, or remove it.
                flash(f"Payment of ₱{pay_amount:.2f} recorded!", "success")
            except ValueError:
                flash("Amount must be a number", "error")
            except Exception as e:
                flash(f"Error recording payment: {str(e)}", "error")
        return redirect(url_for("loan_tracker"))

    @app.route("/delete-loan/<int:loan_id>", methods=["POST"])
    @login_required
    def delete_loan(loan_id):
        loan = models.get_loan_by_id(loan_id)
        if not loan or loan["user_id"] != session["user_id"]:
            flash("Loan not found or unauthorized access", "error")
        else:
            try:
                models.delete_loan(loan_id)
                flash("Loan deleted successfully!", "success")
            except Exception as e:
                flash(f"Error deleting loan: {str(e)}", "error")
        return redirect(url_for("loan_tracker"))

    # ------------------ SAVINGS TRACKER ------------------
    @app.route("/savings")
    @login_required
    def savings_tracker():
        user_id = session["user_id"]
        savings_data = models.get_savings(user_id)
    
        return render_template(
            "savings.html", 
            savings=savings_data, 
            username=session["username"],
            get_savings_transactions=models.get_savings_transactions 
    )

    

    @app.route("/add-savings", methods=["POST"])
    @login_required
    def add_savings():
        try:
            savings_name = request.form["savings_name"].strip()
            target_amount = float(request.form.get("target_amount", 0) or 0)
            models.add_savings(session["user_id"], savings_name, target_amount)
            # FIX: Removed '✅'
            flash("Savings goal created successfully!", "success")
        except Exception as e:
            flash(f"Error adding savings: {str(e)}", "error")
        return redirect(url_for("savings_tracker"))

    @app.route("/deposit-savings/<int:savings_id>", methods=["POST"])
    @login_required
    def deposit_savings(savings_id):
        try:
            amount = float(request.form["deposit_amount"])
            models.deposit_savings(savings_id, amount)
            flash("Deposit successful!", "success")
        except Exception as e:
            flash(f"Error depositing: {str(e)}", "error")
        return redirect(url_for("savings_tracker"))

    @app.route("/withdraw-savings/<int:savings_id>", methods=["POST"])
    @login_required
    def withdraw_savings(savings_id):
        try:
            amount = float(request.form["withdraw_amount"])
            models.withdraw_savings(savings_id, amount)
            flash("Withdrawal successful!", "success")
        except Exception as e:
            flash(f"Error withdrawing: {str(e)}", "error")
        return redirect(url_for("savings_tracker"))

    @app.route("/auto_savings/<int:savings_id>", methods=["POST"])
    @login_required
    def auto_savings(savings_id):
        try:
            payout_amount = float(request.form["payout_amount"])
            percentage = float(request.form["percentage"])
            auto_amount = (payout_amount * percentage) / 100
            models.deposit_savings(savings_id, auto_amount)
            flash(f"Auto-saved ₱{auto_amount:.2f} into your fund!", "success")
        except Exception as e:
            flash(f"Error with auto-save: {str(e)}", "error")
        return redirect(url_for("savings_tracker"))
    
    @app.route("/delete-savings/<int:id>", methods=["POST"])
    @login_required
    def delete_savings(id):
        try:
            # Check if it belongs to user (optional security step)
            # savings = models.get_savings_by_id(id)
            # if savings['user_id'] != session['user_id']: ...
            
            models.delete_savings(id)
            flash("Savings goal deleted successfully!", "success")
        except Exception as e:
            flash(f"Error deleting goal: {str(e)}", "error")
        
        # ⚠️ THIS LINE MUST BE INDENTED to match the 'try/except' block above
        return redirect(url_for('savings_tracker'))

    # ------------------ BUDGET TRACKER ------------------
    @app.route("/budget")
    @login_required
    def budget_tracker():
        user_id = session["user_id"]
        categories = models.get_budget_categories(user_id)
        transactions = models.get_budget_transactions(user_id)
        expense_totals = models.get_expense_totals_by_type(user_id)
        savings_accounts = models.get_active_savings(user_id)
        for c in categories:
            c["actual_spent"] = models.get_actual_spent(user_id, c["id"])
        return render_template(
            "budget.html",
            categories=categories,
            transactions=transactions,
            username=session["username"],
            expense_totals=expense_totals,
            savings=savings_accounts,
        )

    @app.route("/add-budget", methods=["POST"])
    @login_required
    def add_budget():
        try:
            category_id = int(request.form["category_id"])
            expense_name = request.form["expense_name"].strip()
            expense_amount = float(request.form["expense_amount"])
            expense_type = request.form.get("expense_type", "daily")
            savings_id = (
                int(request.form["savings_id"])
                if request.form.get("savings_id")
                else None
            )
            models.add_budget_transaction(
                session["user_id"],
                category_id,
                expense_name,
                expense_amount,
                expense_type,
                savings_id,
            )
            # FIX: Removed '✅'
            flash("Expense added successfully!", "success")
        except Exception as e:
            flash(f"Error adding expense: {str(e)}", "error")
        return redirect(url_for("budget_tracker"))

    @app.route("/delete-budget/<int:id>")
    @login_required
    def delete_budget(id):
        try:
            models.delete_budget_transaction(id, session["user_id"])
            flash("Expense deleted successfully!", "success")
        except Exception as e:
            flash(f"Error deleting expense: {str(e)}", "error")
        return redirect(url_for("budget_tracker"))

    @app.route("/add-category", methods=["POST"])
    @login_required
    def add_category():
        try:
            category_name = request.form["category_name"].strip()
            planned_budget = float(request.form.get("planned_budget", 0))
            models.add_category(session["user_id"], category_name, planned_budget)
            # FIX: Removed '📂' and '✅' to avoid duplicates
            flash("Category added successfully!", "success")
        except Exception as e:
            flash(f"Error adding category: {str(e)}", "error")
        return redirect(url_for("budget_tracker"))

    @app.route("/set-planned-budget", methods=["POST"])
    @login_required
    def set_planned_budget():
        try:
            category_id = int(request.form["category_id"])
            planned_budget = float(request.form["planned_budget"])
            models.update_budget_category(
                session["user_id"], category_id, planned_budget
            )
            # FIX: Removed '✅'
            flash("Planned budget updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating planned budget: {str(e)}", "error")
        return redirect(url_for("budget_tracker"))

    # ------------------ PROFILE & WALLET ------------------
    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        user_id = session["user_id"]
        
        # 1. Handle Profile Updates (Your requested code)
        if request.method == "POST":
            form_type = request.form.get("form_type")
            if form_type == "personal":
                surname = request.form["surname"].strip()
                firstname = request.form["firstname"].strip()
                middle_initial = request.form.get("middle_initial", "").strip()
                nickname = request.form.get("nickname", "").strip()
                models.save_personal_info(
                    user_id, surname, firstname, middle_initial, nickname
                )
                flash("Personal info updated successfully!", "success")
            elif form_type == "work":
                occupation = request.form.get("occupation", "").strip()
                company = request.form.get("company", "").strip()
                try:
                    salary = float(request.form.get("salary", 0) or 0)
                except ValueError:
                    salary = 0
                models.save_work_info(user_id, occupation, company, salary)
                flash("Work info updated successfully!", "success")
            return redirect(url_for("profile"))

        # 2. Load Data (Profile + Wallet Cards)
        profile_data = models.get_profile(user_id)
        if not profile_data:
            profile_data = {
                "surname": "", "firstname": "", "middle_initial": "",
                "nickname": "", "occupation": "", "company": "", "salary": 0,
            }

        # IMPORTANT: This fetches your cards so they appear in the wallet!
        try:
            cards = models.get_user_cards(user_id)
        except Exception:
            cards = [] 

        return render_template(
            "profile.html", 
            profile=profile_data, 
            username=session["username"],
            cards=cards  # <-- Passing cards to the HTML
        )

    # --- Wallet Routes (Keep these so the buttons work!) ---
    @app.route("/add-card", methods=["POST"])
    @login_required
    def add_card():
        try:
            bank_name = request.form["bank_name"]
            card_type = request.form["card_type"]
            last_four = request.form["last_four"][-4:] 
            balance = float(request.form["balance"])
            color_theme = request.form["color_theme"]
            usage_tag = request.form["usage_tag"]
            
            models.add_card(session["user_id"], bank_name, card_type, last_four, balance, color_theme, usage_tag)
            flash("Card added to wallet!", "success")
        except Exception as e:
            flash(f"Error adding card: {str(e)}", "error")
        return redirect(url_for('profile'))

    @app.route("/delete-card/<int:id>", methods=["POST"])
    @login_required
    def delete_card(id):
        try:
            models.delete_card(id)
            flash("Card removed from wallet.", "success")
        except Exception as e:
            flash(f"Error removing card: {str(e)}", "error")
        return redirect(url_for('profile'))