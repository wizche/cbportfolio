import datetime

class Order:
    def __init__(self, id, fee_tax=0.5):
        self.id = id
        self.fee_tax = fee_tax
        self.buy_price_with_fee = 0.0
        self.buy_currency = 0.0
        self.fee = 0.0
        self.unit_price = 0.0

    def buy(self, fund_amount, unit_price):
        self.buy_price_with_fee = fund_amount
        self.fee = fund_amount * self.fee_tax / 100.0
        self.buy_currency = fund_amount * unit_price
        self.unit_price = unit_price
        self.buy_time = datetime.datetime.now()

    def __str__(self):
        df = '{0:%d.%m.%Y %H:%M:%S}'.format(self.buy_time)
        res = f"[{df}] Order {self.buy_currency:.4f} {self.id} for {self.buy_price_with_fee:.4f} (fee {self.fee:.4f}) | unit price {self.unit_price}"
        return res

class Portfolio:
    def __init__(self):
        self.orders = []
        self.portfolio = {}
    
    def add(self, order: Order):
        self.orders.append(order)
        if order.id not in self.portfolio:
            self.portfolio[order.id] = 0.0
        self.portfolio[order.id] += order.buy_currency

    def summary(self):
        v = ""
        v += f"Portfolio contains {len(self.orders)} orders\n"
        for o in self.orders:
            v += str(o)
            v += "\n"
        v += "Total amounts in portfolio:\n"
        for c in self.portfolio:
            v += f"{self.portfolio[c]} {c}\n"
        return v