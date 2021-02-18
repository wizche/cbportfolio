import datetime
from typing import List


class Product:
    def __init__(self, base_product, quote_product):
        self.base = base_product
        self.quote = quote_product
        self.id = f"{base_product}-{quote_product}"

    def __str__(self):
        return self.id

    def __eq__(self, other):
        if isinstance(other, Product):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    @staticmethod
    def build(product_id) -> 'Product':
        tokens = product_id.split('-')
        return Product(tokens[0].strip(), tokens[1].strip())

    @staticmethod
    def build_list(product_ids: List[str]) -> List['Product']:
        res = []
        for pid in product_ids:
            res.append(Product.build(pid))
        return res


class Order:
    def __init__(self, product, fee_tax=0.5):
        self.product = product
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
        res = f"[{df}] Order {self.buy_currency:.2f} {self.product.base} for {self.buy_price_with_fee:.2f} {self.product.quote} (fee {self.fee:.4f}) | price {self.unit_price:.4f} {self.product.base}/{self.product.quote}"
        return res


class Portfolio:
    def __init__(self, base_currency):
        self.orders = []
        self.portfolio = {}
        self.base_currency = base_currency

    def add(self, order: Order):
        self.orders.append(order)
        if order.product not in self.portfolio:
            self.portfolio[order.product] = 0.0
        self.portfolio[order.product] += order.buy_currency

    def get_total_spent(self):
        return sum(o.buy_price_with_fee for o in self.orders)

    def summary(self, prices):
        v = ""
        v += f"Portfolio contains {len(self.orders)} orders\n"
        for o in self.orders:
            v += str(o)
            v += "\n"
        v += "Total amounts in portfolio:\n"

        nowts = str(datetime.datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0).timestamp())
        total = 0.0
        for product in self.portfolio:
            product_value = self.portfolio[product] * \
                prices[product.id][nowts]["close"]
            spent = 0.0
            for order in self.orders:
                if order.product == product:
                    spent += o.buy_price_with_fee
            v += f"{self.portfolio[product]:.4f} {product.base:<3} \t| spent {spent:.2f} {self.base_currency} \t| current value: {product_value:.2f} {self.base_currency} ({product_value/spent*100.0:.2f}%)\n"
            total += product_value

        v += f"Total spent: {self.get_total_spent():.2f} {self.base_currency} across {len(self.orders)} orders\n"
        v += f"Total value: {total:.2f} {self.base_currency} | {total/self.get_total_spent()*100.0:.2f} % gain"
        return v
