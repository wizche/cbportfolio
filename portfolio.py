import datetime

class Order:
    def __init__(self, id, fee_tax=0.5):
        self.id = id
        self.fee_tax = fee_tax
        self.buy_price_with_fee = 0.0
        self.buy_currency = 0.0
        self.fee = 0.0
        self.unit_price = 0.0

    def buy(self, order_date, fund_amount, unit_price):
        self.buy_price_with_fee = fund_amount
        self.fee = fund_amount * self.fee_tax / 100.0
        self.buy_currency = fund_amount * unit_price
        self.unit_price = unit_price
        self.buy_time = order_date

    def __str__(self):
        df = '{0:%d.%m.%Y %H:%M:%S}'.format(self.buy_time)
        res = f"[{df}] Order {self.buy_currency:.2f} {self.id} for {self.buy_price_with_fee:.2f} (fee {self.fee:.4f}) | unit price {self.unit_price:.4f}"
        return res

class Portfolio:
    def __init__(self, base_currency):
        self.orders = []
        self.portfolio = {}
        self.base_currency = base_currency
    
    def add(self, order: Order):
        self.orders.append(order)
        if order.id not in self.portfolio:
            self.portfolio[order.id] = 0.0
        self.portfolio[order.id] += order.buy_currency

    def get_total_spent(self):
        return sum(o.buy_price_with_fee for o in self.orders)

    def summary(self, prices):
        v = ""
        v += f"Portfolio contains {len(self.orders)} orders\n"
        for o in self.orders:
            v += str(o)
            v += "\n"
        v += "Total amounts in portfolio:\n"


        nowts = str(datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        total = 0.0
        for c in self.portfolio:
            ct = self.portfolio[c] * prices[c][nowts]["close"]
            spent = 0.0
            for o in self.orders:
                if o.id == c:
                    spent += o.buy_price_with_fee
            v += f"{self.portfolio[c]:.2f} {c:<10} \t| spent {spent:.2f} {self.base_currency} \t| current value: {ct:.2f} {self.base_currency} ({ct/spent*100.0:.2f}%)\n"
            total += ct

        v += f"Total spent: {self.get_total_spent():.2f} {self.base_currency} across {len(self.orders)} orders\n"
        v += f"Total value: {total:.2f} {self.base_currency} | {total/self.get_total_spent()*100.0:.2f} % gain"
        return v
        