import cbpro
import sys
from datetime import datetime, timedelta

class TradingEngine:
    def __init__(self, key, secret, passphrase, base_currency):
        self.public_client = cbpro.PublicClient()
        self.auth_client = cbpro.AuthenticatedClient(key, secret, passphrase,
                                                api_url="https://api-public.sandbox.pro.coinbase.com")
        self.base_currency = base_currency

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

    def get_market_trends(self, tradable_products, limit_products, trading_interval_days):
        market_trend = {}
        for idx, pid in enumerate(tradable_products):
            p = tradable_products[pid]
            if limit_products > 0 and idx >= limit_products:
                break

            start = (datetime.today() - timedelta(days=trading_interval_days)).isoformat()
            print(
                f"Asking {trading_interval_days} days historical data for {p['id']} from {start}")
            tickers = self.public_client.get_product_historic_rates(
                p['id'], start=start, end=datetime.today().isoformat(), granularity=86400)
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
            if len(tickers) < trading_interval_days:
                print("Not enough information for this product, skipping!")
                continue
            now = tickers[0]
            old = tickers[len(tickers)-1]
            gain = (now[2]-old[2])/now[2] * 100.0
            market_trend[p['id']] = gain

        # sort by gain
        sorted_market_trend = dict(
            sorted(market_trend.items(), key=lambda item: item[1], reverse=True))
        return sorted_market_trend
    
    def get_buy_quotes(self, buy_amount, selected_prods, tradable_products):
        orders = {}
        ratio = sum(selected_prods.values())
        top = ()

        for p in selected_prods:
            val = buy_amount * (abs(selected_prods[p])/ratio * 100.0) / 100.0
            if len(top) == 0 or val > top[1]:
                top = (p, val)
            orders[p] = val

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