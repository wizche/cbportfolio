import cbpro
import sys
from datetime import datetime, timedelta

from portfolio import Order, Portfolio

class TradingEngine:
    def __init__(self, key, secret, passphrase, base_currency, max_buy_products, 
    buy_amount, trading_interval_days):
        self.public_client = cbpro.PublicClient()
        self.auth_client = cbpro.AuthenticatedClient(key, secret, passphrase,
                                                api_url="https://api-public.sandbox.pro.coinbase.com")
        self.base_currency = base_currency
        self.max_buy_products = max_buy_products
        self.buy_amount = buy_amount
        self.trading_interval_days = trading_interval_days

    def get_account(self):
        coinbase_accounts = self.auth_client.get_coinbase_accounts()
        coinbase_account = None
        for acc in coinbase_accounts:
            if acc['currency'] == self.base_currency:
                coinbase_account = acc
                break
        return coinbase_account
        
    def get_tradable_products(self):
        products = self.public_client.get_products()
        tradable_products = {}
        for product in products:
            if not product['trading_disabled'] and product['status'] == "online" and product['quote_currency'] == self.base_currency:
                tradable_products[product['id']] = product
        return tradable_products

    def get_last_market_trends(self, tradable_products, start, end, limit_products = -1):
        market_trend = {}
        for _, pid in enumerate(tradable_products):
            p = tradable_products[pid]
            if limit_products > 0 and len(market_trend) >= limit_products:
                break

            tickers = self.public_client.get_product_historic_rates(
                p['id'], start=start, end=end, granularity=86400)
            '''
            Each bucket is an array of the following information:
                time bucket start time
                low lowest price during the bucket interval
                high highest price during the bucket interval
                open opening price (first trade) in the bucket interval
                close closing price (last trade) in the bucket interval
                volume volume of trading activity during the bucket interval
            '''
            # for tick in tickers:
            #    print(f"{datetime.fromtimestamp(tick[0]).isoformat()}: {tick[2]}")
            if len(tickers) < 2:
                #print(f"Not enough historical information ({len(tickers)}) for this product, skipping!")
                continue
            now = tickers[0]
            old = tickers[len(tickers)-1]
            gain = (now[2]-old[2])/now[2] * 100.0
            market_trend[p['id']] = gain

        # sort by gain
        sorted_market_trend = dict(
            sorted(market_trend.items(), key=lambda item: item[1], reverse=True))
        return sorted_market_trend
    
    def get_buy_quotes(self, selected_prods, tradable_products):
        orders = {}
        ratio = sum(abs(v) for v in selected_prods.values())
        top = ()
        print(f"Ratio: {ratio}")
        for p in selected_prods:
            val = abs(self.buy_amount * (selected_prods[p]/ratio * 100.0) / 100.0)
            if len(top) == 0 or val > top[1]:
                top = (p, val)
            orders[p] = val
            #print(f"orders[{p}]: {orders[p]}")

        while True:
            untouched = True
            for p in orders.copy():
                min_value = float(tradable_products[p]['min_market_funds'])
                if orders[p] < min_value:
                    orders[top[0]] += orders[p]
                    print(f"{p} too small ({orders[p]:.2f} < {min_value:.2f}), adding to top product {top[0]} = {orders[top[0]]}")
                    orders.pop(p)
                    untouched = False
            if untouched: break
        return orders

    def execute_orders(self, orders):
        exec_orders = []
        for o in orders:
            print(f"Executing order for {o}: {orders[o]} {self.base_currency}")
            order = self.auth_client.place_market_order(
                product_id=o, side='buy', funds=orders[o])
            print(order)
            exec_orders.append(order)
        return exec_orders

    def simulate_period(self, weeks: int):
        portfolio = Portfolio()
        periods = []
        old_now = datetime.today() - timedelta(days=weeks*7)
        tradable_products = self.get_tradable_products()

        for _ in range(0, weeks+1):
            start = old_now - timedelta(days=7)
            end = old_now
            period = (start.isoformat(), end.isoformat())
            periods.insert(0, period)
            old_now = end + timedelta(days=7)
            print(f"Computing period {period[0]} - {period[1]}")
            trends = self.get_last_market_trends(tradable_products, start, end, limit_products=5)
            ordering_products = self.get_buy_quotes(trends, tradable_products)
            for pid in ordering_products:
                curr_value = self.public_client.get_product_ticker(pid)
                if "size" not in curr_value or "price" not in curr_value:
                    print(f"Ticker doesnt contains needed information {curr_value}, skipping order!")
                    continue
                unit_value = float(curr_value['size'])/float(curr_value['price'])
                order = Order(pid)
                order.buy(ordering_products[pid], unit_value)
                portfolio.add(order)
        print(portfolio.summary())

            #break

    def execute(self, order):
        pass