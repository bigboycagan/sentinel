/** One-click demo snippets for the Analyzer. Real code — the engine genuinely analyzes them. */

export interface Sample {
  id: string;
  label: string;
  fileName: string;
  description: string;
  code: string;
}

export const SAMPLES: Sample[] = [
  {
    id: "vulnerable-api",
    label: "Vulnerable Flask API",
    fileName: "vulnerable_api.py",
    description: "Hardcoded secrets, eval, SQL injection, shell execution",
    code: `import os
import random
import hashlib
import sqlite3
import subprocess
from flask import Flask, request

app = Flask(__name__)

DB_PASSWORD = "Pr0duction!Pass"
STRIPE_API_KEY = "sk-live-9fj20fj20fj20fj20fj2"


def get_user(user_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()


def check_password(password):
    if password == "letmein2024":
        return True
    digest = hashlib.md5(password.encode()).hexdigest()
    return digest


def make_session():
    session_token = random.randint(1000, 9999)
    return session_token


@app.route("/calc")
def calculate():
    expression = request.args.get("expr")
    return str(eval(expression))


@app.route("/ping")
def ping():
    host = request.args.get("host")
    subprocess.run("ping -c 1 " + host, shell=True)
    os.system("echo done")
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
`,
  },
  {
    id: "complex-algorithm",
    label: "Complex Algorithm",
    fileName: "router.py",
    description: "High cyclomatic complexity and deep nesting",
    code: `def route_request(method, path, user, flags, payload):
    if method == "GET":
        if path.startswith("/admin"):
            if user and user.get("role") == "admin":
                for flag in flags:
                    if flag == "beta":
                        if payload and payload.get("version"):
                            return "admin-beta"
                        else:
                            return "admin-stable"
                    elif flag == "legacy":
                        return "admin-legacy"
                return "admin"
            return "forbidden"
        elif path.startswith("/api"):
            if user:
                return "api-auth"
            elif flags and "public" in flags:
                return "api-public"
            else:
                return "unauthorized"
        return "public"
    elif method == "POST":
        if not payload:
            return "bad-request"
        if user and (user.get("role") == "admin" or user.get("role") == "editor"):
            unused_audit = len(flags)
            return "created"
        return "forbidden"
    elif method == "DELETE":
        if user and user.get("role") == "admin":
            return "deleted"
        return "forbidden"
    return "method-not-allowed"


def helper(d=[]):
    try:
        return d[0]
    except:
        return None
`,
  },
  {
    id: "clean-module",
    label: "Clean Python Module",
    fileName: "inventory.py",
    description: "Well-structured, documented, no findings expected",
    code: `"""Inventory accounting helpers."""

from dataclasses import dataclass


@dataclass
class Item:
    """A single stocked product."""

    sku: str
    quantity: int
    unit_price: float


def total_value(items: list[Item]) -> float:
    """Return the combined value of every item in stock."""
    return sum(item.quantity * item.unit_price for item in items)


def restock(item: Item, amount: int) -> Item:
    """Return a copy of \`item\` with \`amount\` units added."""
    if amount < 0:
        raise ValueError("amount must be positive")
    return Item(sku=item.sku, quantity=item.quantity + amount, unit_price=item.unit_price)
`,
  },
];
