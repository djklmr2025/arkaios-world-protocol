"""Local economic simulator. Synthetic units only; no network or real money."""
import sqlite3


class Economy:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS accounts (
          id TEXT PRIMARY KEY,
          available INTEGER NOT NULL DEFAULT 0 CHECK(available>=0),
          held INTEGER NOT NULL DEFAULT 0 CHECK(held>=0));
        CREATE TABLE IF NOT EXISTS funding (
          receipt TEXT PRIMARY KEY, account TEXT NOT NULL REFERENCES accounts(id),
          amount INTEGER NOT NULL CHECK(amount>0));
        CREATE TABLE IF NOT EXISTS orders (
          id TEXT PRIMARY KEY, buyer TEXT NOT NULL REFERENCES accounts(id),
          seller TEXT NOT NULL REFERENCES accounts(id),
          amount INTEGER NOT NULL CHECK(amount>0), state TEXT NOT NULL,
          CHECK(buyer<>seller));
        CREATE TABLE IF NOT EXISTS journal (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL, reference TEXT NOT NULL,
          account TEXT NOT NULL REFERENCES accounts(id),
          available_delta INTEGER NOT NULL, held_delta INTEGER NOT NULL);
        """)

    @staticmethod
    def amount(value):
        # SQLite signed integers; bound simulator to prevent arithmetic overflow.
        if type(value) is not int or not 0 < value <= 10**12:
            raise ValueError("positive integer minor units required")

    def transaction(self, action):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = action()
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def account(self, identity):
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("identity required")
        self.db.execute("INSERT OR IGNORE INTO accounts(id) VALUES (?)", (identity,))

    def balance(self, identity):
        row = self.db.execute("SELECT available, held FROM accounts WHERE id=?", (identity,)).fetchone()
        if row is None:
            raise ValueError("unknown account")
        return row

    def entry(self, kind, reference, account, available, held):
        self.db.execute("INSERT INTO journal(kind,reference,account,available_delta,held_delta) VALUES (?,?,?,?,?)",
                        (kind, reference, account, available, held))

    def fund_test(self, receipt, account, amount):
        """Explicit test faucet. Never a claim of reserves or an AMR adapter."""
        self.amount(amount)
        def action():
            old = self.db.execute("SELECT account,amount FROM funding WHERE receipt=?", (receipt,)).fetchone()
            if old:
                if old != (account, amount):
                    raise ValueError("receipt payload mismatch")
                return
            current, _ = self.balance(account)
            if current + amount > 10**12:
                raise ValueError("simulator account limit")
            self.db.execute("INSERT INTO funding VALUES (?,?,?)", (receipt, account, amount))
            self.db.execute("UPDATE accounts SET available=available+? WHERE id=?", (amount, account))
            self.entry("test_funding", receipt, account, amount, 0)
        self.transaction(action)

    def reserve(self, order, buyer, seller, amount):
        self.amount(amount)
        def action():
            old = self.db.execute("SELECT buyer,seller,amount FROM orders WHERE id=?", (order,)).fetchone()
            if old:
                if old != (buyer, seller, amount):
                    raise ValueError("order payload mismatch")
                return
            if buyer == seller:
                raise ValueError("self purchase forbidden")
            self.balance(seller)
            changed = self.db.execute("UPDATE accounts SET available=available-?,held=held+? WHERE id=? AND available>=?",
                                      (amount, amount, buyer, amount)).rowcount
            if changed != 1:
                raise ValueError("insufficient funds or unknown buyer")
            self.db.execute("INSERT INTO orders VALUES (?,?,?,?, 'RESERVED')", (order, buyer, seller, amount))
            self.entry("reserve", order, buyer, -amount, amount)
        self.transaction(action)

    def finish(self, order, actor, accept):
        if type(accept) is not bool:
            raise ValueError("boolean decision required")
        target = "ACCEPTED" if accept else "REFUNDED"
        def action():
            row = self.db.execute("SELECT buyer,seller,amount,state FROM orders WHERE id=?", (order,)).fetchone()
            if not row:
                raise ValueError("unknown order")
            buyer, seller, amount, state = row
            if actor != buyer:
                raise ValueError("buyer authorization required")
            if state == target:
                return
            if state != "RESERVED":
                raise ValueError("order already finalized differently")
            recipient = seller if accept else buyer
            current, _ = self.balance(recipient)
            if current + amount > 10**12:
                raise ValueError("simulator account limit")
            self.db.execute("UPDATE accounts SET held=held-? WHERE id=?", (amount, buyer))
            self.db.execute("UPDATE accounts SET available=available+? WHERE id=?", (amount, recipient))
            self.db.execute("UPDATE orders SET state=? WHERE id=?", (target, order))
            self.entry(target, order, buyer, 0, -amount)
            self.entry(target, order, recipient, amount, 0)
        self.transaction(action)

    def operation_state(self, identity, next_cost):
        self.amount(next_cost)
        available, _ = self.balance(identity)
        return "READY" if available >= next_cost else "PAUSED_BUDGET"

    def audit(self):
        funded = self.db.execute("SELECT COALESCE(SUM(amount),0) FROM funding").fetchone()[0]
        total = self.db.execute("SELECT COALESCE(SUM(available+held),0) FROM accounts").fetchone()[0]
        if funded != total:
            raise AssertionError("supply mismatch")
        for identity, available, held in self.db.execute("SELECT id,available,held FROM accounts"):
            deltas = self.db.execute("SELECT COALESCE(SUM(available_delta),0),COALESCE(SUM(held_delta),0) FROM journal WHERE account=?", (identity,)).fetchone()
            reserved = self.db.execute("SELECT COALESCE(SUM(amount),0) FROM orders WHERE buyer=? AND state='RESERVED'", (identity,)).fetchone()[0]
            if deltas != (available, held) or held != reserved:
                raise AssertionError("account reconciliation mismatch")
        return {"test_units_issued": funded, "test_units_accounted": total}


if __name__ == "__main__":
    ledger = Economy()
    for name in ("client", "agent"):
        ledger.account(name)
    ledger.fund_test("test-receipt-1", "client", 1000)
    ledger.reserve("service-1", "client", "agent", 250)
    ledger.finish("service-1", "client", True)
    print({"client": ledger.balance("client"), "agent": ledger.balance("agent"), "audit": ledger.audit()})
