/** One-click demo snippets per language. Real code — the engine genuinely analyzes them. */

export interface Sample {
  id: string;
  label: string;
  fileName: string;
  language: string;
  description: string;
  code: string;
}

export const SAMPLES: Sample[] = [
  {
    id: "vulnerable-api",
    label: "Vulnerable Flask API (Python)",
    fileName: "vulnerable_api.py",
    language: "python",
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
    label: "Complex Algorithm (Python)",
    fileName: "router.py",
    language: "python",
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
    label: "Clean Module (Python)",
    fileName: "inventory.py",
    language: "python",
    description: "Well-structured and documented — no findings expected",
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
  {
    id: "vulnerable-express",
    label: "Vulnerable Express API (JavaScript)",
    fileName: "server.js",
    language: "javascript",
    description: "eval, command & SQL injection, weak hash, insecure randomness",
    code: `const express = require("express");
const crypto = require("crypto");
const cp = require("child_process");
const fs = require("fs");
const lodash = require("lodash");

const app = express();

const DB_PASSWORD = "Pr0duction!Pass";
const STRIPE_API_KEY = "sk-live-9fj20fj20fj20fj20fj2";

function getUser(db, userId) {
  return db.query(\`SELECT * FROM users WHERE id = \${userId}\`);
}

function checkPassword(password) {
  if (password == "letmein2024") {
    return true;
  }
  return crypto.createHash("md5").update(password).digest("hex");
}

function makeSession() {
  var sessionToken = Math.random().toString(36);
  return sessionToken;
}

app.get("/calc", (req, res) => {
  res.send(String(eval(req.query.expr)));
});

app.get("/ping", (req, res) => {
  cp.exec("ping -c 1 " + req.query.host);
  res.send("ok");
});

app.get("/file", (req, res) => {
  const body = fs.readFileSync(\`/data/\${req.query.name}\`);
  res.send(body);
});

app.listen(3000, () => {
  console.log("listening");
});
`,
  },
  {
    id: "vulnerable-react",
    label: "Unsafe React Component (TypeScript)",
    fileName: "Profile.tsx",
    language: "typescript",
    description: "XSS sinks, any types, token in localStorage, suppressed errors",
    code: `import React from "react";

const AUTH_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r";

export function Profile({ user }: { user: any }) {
  // @ts-ignore
  localStorage.setItem("authToken", AUTH_TOKEN);

  function renderBio(el: HTMLElement, bio: any) {
    el.innerHTML = bio;
    el.insertAdjacentHTML("beforeend", bio);
  }

  const openPopup = () => {
    window.parent.postMessage({ user: user.id }, "*");
  };

  try {
    renderBio(document.body, user.bio);
  } catch (e) {}

  return (
    <div onClick={openPopup}>
      <div dangerouslySetInnerHTML={{ __html: user.bio }} />
    </div>
  );
}
`,
  },
  {
    id: "clean-typescript",
    label: "Clean Module (TypeScript)",
    fileName: "pricing.ts",
    language: "typescript",
    description: "Typed, documented, no findings expected",
    code: `/** Pricing helpers for the storefront. */

export interface LineItem {
  sku: string;
  quantity: number;
  unitPrice: number;
}

/** Return the combined value of every line item. */
export function subtotal(items: LineItem[]): number {
  return items.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0);
}

/** Apply a percentage discount, rounded to whole cents. */
export function applyDiscount(amount: number, percentage: number): number {
  if (percentage < 0 || percentage > 100) {
    throw new RangeError("percentage must be between 0 and 100");
  }
  return Math.round(amount * (1 - percentage / 100) * 100) / 100;
}
`,
  },
];

export const samplesForLanguage = (language: string): Sample[] =>
  SAMPLES.filter((sample) => sample.language === language);
