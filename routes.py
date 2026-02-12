from flask import render_template, request, redirect, session, url_for, flash, send_from_directory
import models
from functools import wraps
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import requests
import json
import re
import os


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
# 🧠 AI HELPER FUNCTION (Global Scope)
# -------------------------------
def ask_llama_budget(salary, frequency, fixed_expenses, zero_items, remaining_budget):
    API_KEY = os.environ.get("GROQ_API_KEY")  #
    API_URL = "https://api.groq.com/openai/v1/chat/completions"  #
    MODEL = "llama-3.3-70b-versatile"  #

    total_fixed = sum(fixed_expenses.values())  #
    fixed_ratio = (total_fixed / salary) * 100 if salary > 0 else 0  #

    status = "STABLE"  #
    if fixed_ratio > 60:
        status = "CRITICAL (High Fixed Costs)"  #
    elif fixed_ratio < 40:
        status = "EXCELLENT (High Disposable Income)"  #

    # Updated prompt to include reasoning
    prompt = f"""
    You are a Financial API. Distribute the remaining budget of {remaining_budget} into the categories provided.
    
    CONTEXT:
    - Income: {salary} ({frequency})
    - Fixed Expenses: {total_fixed} ({fixed_ratio:.1f}%)
    - Status: {status}
    
    CATEGORIES TO FILL:
    {json.dumps(zero_items)}
    
    RULES:
    1. The sum of allocated amounts MUST equal exactly {remaining_budget}.
    2. Use the EXACT category names provided as keys in the "plan" object.
    3. Provide a concise, professional 2-3 sentence "reasoning" explaining your logic.
    4. Return ONLY a valid JSON object with keys: "plan" and "reasoning".
    """

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a JSON-only financial API that provides a budget 'plan' and its 'reasoning'.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,  # Slightly higher for natural reasoning text
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }  #

    try:
        response = requests.post(API_URL, json=payload, headers=headers)  #
        data = response.json()  #

        if "choices" in data:
            raw_content = data["choices"][0]["message"]["content"]  #
            print(f"\n🤖 AI RAW RESPONSE: {raw_content}\n")  #

            start = raw_content.find("{")  #
            end = raw_content.rfind("}") + 1  #
            if start != -1 and end != -1:
                return json.loads(raw_content[start:end])  #
            return None
        else:
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None


# -------------------------------
# Routes registration (Main Function)
# -------------------------------
def init_routes(app):
    app.secret_key = "supersecretkey"

    # --- Date Filter ---
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
                    return value
        return dt.strftime(format)

    # ---------------------------------------------------
    #  SMART BUDGET ROUTE (INDENTED INSIDE init_routes)
    # ---------------------------------------------------
    @app.route("/smart-budget", methods=["GET", "POST"])
    @login_required
    def smart_budget():
        user_id = session["user_id"]
        results = None
        salary_info = None
        ai_note = None
        ai_reasoning = None  # Added to track AI explanation

        if request.method == "POST":
            try:
                salary = float(request.form.get("salary_amount", 0))
                frequency = request.form.get("frequency", "Monthly")
                item_names = request.form.getlist("item_name[]")
                item_amounts = request.form.getlist("item_amount[]")

                # Retrieve hidden reasoning if saving, or empty if generating new
                current_reasoning = request.form.get("ai_reasoning_hidden", "")
                save_mode = request.form.get("save_budget") == "true"

                parsed_items = []
                total_fixed = 0
                zero_items_indices = []

                for i in range(len(item_names)):
                    name = item_names[i].strip()
                    if not name:
                        continue

                    try:
                        amt = float(item_amounts[i])
                    except:
                        amt = 0.0

                    parsed_items.append(
                        {"name": name, "user": amt, "ai": amt, "auto": False}
                    )

                    if amt > 0:
                        total_fixed += amt
                    else:
                        zero_items_indices.append(i)

                remaining = salary - total_fixed

                # --- DISTRIBUTION LOGIC ---
                if remaining > 0 and zero_items_indices and not save_mode:
                    # Prepare data for AI
                    fixed_dict = {
                        item["name"]: item["user"]
                        for item in parsed_items
                        if item["user"] > 0
                    }
                    zero_names = [parsed_items[i]["name"] for i in zero_items_indices]

                    # Call upgraded AI helper
                    print("🤖 Asking Llama...")
                    ai_response = ask_llama_budget(
                        salary, frequency, fixed_dict, zero_names, remaining
                    )

                    if ai_response and "plan" in ai_response:
                        ai_plan = ai_response["plan"]
                        ai_reasoning = ai_response.get(
                            "reasoning", "AI optimized your budget."
                        )
                        ai_note = "✨ AI (Llama 3) successfully distributed your remaining funds."

                        for idx in zero_items_indices:
                            original_name = parsed_items[idx]["name"]
                            allocated = 0

                            # Smart Match Logic
                            if original_name in ai_plan:
                                allocated = ai_plan[original_name]
                            else:
                                simple_name = (
                                    re.sub(r"[^\w\s]", "", original_name)
                                    .strip()
                                    .lower()
                                )
                                for key, val in ai_plan.items():
                                    simple_key = (
                                        re.sub(r"[^\w\s]", "", key).strip().lower()
                                    )
                                    if (
                                        simple_name == simple_key
                                        or simple_name in simple_key
                                    ):
                                        allocated = val
                                        break

                            parsed_items[idx]["ai"] = float(allocated)
                            parsed_items[idx]["auto"] = True
                    else:
                        ai_note = (
                            f"📡 (Offline Mode) Distributed ₱{remaining:,.2f} equally."
                        )
                        ai_reasoning = "I couldn't reach the AI brain, so I split the remaining budget equally."
                        share = remaining / len(zero_items_indices)
                        for idx in zero_items_indices:
                            parsed_items[idx]["ai"] = share
                            parsed_items[idx]["auto"] = True

                elif remaining < 0:
                    ai_note = "⚠️ Expenses exceed income!"
                    ai_reasoning = "Your fixed expenses are higher than your income. Please reduce expenses."
                elif remaining == 0:
                    ai_note = "✅ Perfect balance."

                # --- SAVE TO DB ---
                if save_mode:
                    # Passes the reasoning text to the model
                    budget_entry = models.create_salary_budget(
                        user_id, salary, frequency, current_reasoning
                    )
                    for item in parsed_items:
                        models.add_salary_item(
                            budget_entry.id,
                            item["name"],
                            item["user"],
                            item["ai"],
                            item["auto"],
                        )
                    flash("Budget Plan Saved Successfully!", "success")
                    return redirect(url_for("smart_budget"))

                results = parsed_items
                salary_info = {"amount": salary, "frequency": frequency}

            except Exception as e:
                flash(f"Error: {str(e)}", "error")
                print(e)

        history = models.get_user_budgets(user_id)
        return render_template(
            "smart_budget.html",
            results=results,
            salary_info=salary_info,
            ai_note=ai_note,
            ai_reasoning=ai_reasoning,  # Pass reasoning to template
            history=history,
            username=session.get("username", "User"),
        )

    @app.route("/smart-budget/view/<int:id>")
    @login_required
    def view_smart_budget(id):
        details = models.get_budget_details(id)
        if not details or details["info"]["user_id"] != session["user_id"]:
            flash("Budget not found", "error")
            return redirect(url_for("smart_budget"))
        return render_template("smart_budget_view.html", budget=details)

    import re  # <--- Make sure to import 're' at the top of your file

    # ---------------------------------------------------
    #  SMART BUDGET CHAT ROUTE (Add inside init_routes)
    # ---------------------------------------------------
    @app.route("/smart-budget/chat", methods=["POST"])
    @login_required
    def smart_budget_chat():
        import re

        data = request.json
        user_message = data.get("message")
        full_context = data.get("context", "No context.")

        API_KEY = os.environ.get("GROQ_API_KEY")
        API_URL = "https://api.groq.com/openai/v1/chat/completions"

        # --- SMART RE-BALANCING LOGIC ---
        system_instruction = """
        You are the LiMoney AI Architect. You are a STRICT BUDGET CALCULATOR.

        YOUR GOAL: 
        When the user changes one item, you must RE-CALCULATE the rest of the budget to fit the Total Income.

        ALGORITHM TO FOLLOW:
        1. Identify the user's new constraint (e.g., "Food = 8000").
        2. Identify the Total Income from the context.
        3. Keep "Fixed" bills (Rent, Internet, Utilities) UNCHANGED unless explicitly asked.
        4. Subtract (Fixed Costs + New User Item) from Total Income.
        5. Distribute the REMAINING result across the other flexible categories (Savings, Wants, Misc).
        6. CRITICAL: Do NOT set flexible items to 0 if there is money left. Reduce them proportionally.
        
        EXAMPLE:
        Income: 10,000. Rent: 3,000. Food: 2,000. Savings: 5,000.
        User: "Set Food to 6,000"
        Math: 10k - 3k (Rent) - 6k (New Food) = 1,000 remaining.
        Action: Set Savings to 1,000 (instead of 0).
        
        OUTPUT FORMAT:
        Return a JSON object with the FULL updated list of ALL categories.
        {
          "new_plan": { 
             "Rent": 3000, 
             "Food": 6000, 
             "Savings": 1000 
          },
          "reply": "I've increased Food to 6,000. To make this work, I adjusted Savings to 1,000."
        }
        """

        prompt = f"""
        CURRENT BLUEPRINT:
        {full_context}

        USER COMMAND:
        "{user_message}"
        """

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,  # Very low temperature for strict math
        }

        try:
            r = requests.post(
                API_URL, json=payload, headers={"Authorization": f"Bearer {API_KEY}"}
            )
            if r.status_code == 200:
                raw_content = r.json()["choices"][0]["message"]["content"]

                # --- CLEANER: Extract JSON if mixed with text ---
                try:
                    json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
                    if json_match:
                        clean_json = json_match.group(0)
                        return {"reply": clean_json}
                except:
                    pass

                return {"reply": raw_content}
            else:
                return {"reply": "I'm having trouble thinking right now."}, 500
        except Exception as e:
            print(e)
            return {"reply": "Connection error."}, 500

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
            session["user_id"], session["username"] = user["id"], user["username"]
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

    @app.route("/sw.js")
    def service_worker():
        response = send_from_directory(
            "static", "sw.js", mimetype="application/javascript"
        )
        # Force browser to NEVER cache the Service Worker
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # ------------------ DASHBOARD ------------------
    @app.route("/")
    @login_required
    def dashboard():
        user_id = session["user_id"]

        transactions = models.get_transactions(user_id) or []

        balance = sum(
            t["amount"] if t["type"] == "income" else -t["amount"] 
            for t in transactions
        )

        total_savings = models.get_total_savings(user_id) or 0

        try:
            cards = models.get_user_cards(user_id) or []
        except Exception:
            cards = []

        total_wallet = sum(card["balance"] for card in cards)

        loans = models.get_loans(user_id) or []

        # Prepare Chart Data
        loan_labels = []
        loan_totals = []
        loan_paids = []
        total_remaining_debt = 0

        nearest_due = 999  # Default to a high number (far away)
        today = date.today()

        for loan in loans:

            paid = models.get_total_loan_payments(loan["id"]) or 0
            remaining = loan["amount"] - paid

            # Only count positive debt
            if remaining > 0:
                total_remaining_debt += remaining

                # --- SMART REMINDER LOGIC START ---
                try:
                    # 1. Parse the start date to get the "Day of Month" (e.g., 15th)
                    start_dt = datetime.strptime(loan["start_date"], "%Y-%m-%d").date()

                    # 2. Create a due date for THIS current month
                    # (Handle error if today is Feb and due date is 30th)
                    try:
                        this_month_due = date(today.year, today.month, start_dt.day)
                    except ValueError:
                        # Fallback for short months (use 28th or 1st of next month)
                        this_month_due = date(today.year, today.month, 28)

                    # 3. If this month's due date has passed, the next one is next month
                    if this_month_due < today:
                        next_due = this_month_due + relativedelta(months=1)
                    else:
                        next_due = this_month_due

                    # 4. Calculate days remaining
                    days_diff = (next_due - today).days

                    # 5. Keep the smallest number (the most urgent loan)
                    if days_diff < nearest_due:
                        nearest_due = days_diff
                except Exception:
                    pass  # If date parsing fails, skip this loan

            # Prepare Chart Data
            loan_labels.append(loan["loan_name"])
            loan_totals.append(loan["amount"])
            loan_paids.append(paid)

        net_balance = (total_wallet + total_savings) - total_remaining_debt

        return render_template(
            "dashboard.html",
            transactions=transactions,
            balance=balance,
            total_wallet=total_wallet,
            total_savings=total_savings,
            total_debt=total_remaining_debt,
            days_until_due=nearest_due,
            net_balance=net_balance,
            username=session.get("username", "User"),  # Safe fallback name
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
