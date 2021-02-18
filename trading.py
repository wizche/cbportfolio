import cbpro
import enum
import math
import sys
import json
import os
import random
from datetime import datetime, timedelta
import logging

from portfolio import Order, Portfolio, Product
from typing import Dict, List

class Strategy(enum.Enum):
    TopGainers = 1
    TopLosers = 2
    Mixed = 3


class PriceTrackerWsClient(cbpro.WebsocketClient):
    def start(self, url, products):
        self.url = url
        self.products = list(products)
        self.channels = ['ticker']
        self.prices = {}
        print(f"Subscribing to {len(self.products)} products tickers")
        super().start()

    def on_message(self, msg):
        if "price" in msg:
            self.prices[msg['product_id']] = 1/float(msg['price'])
            #print(f"{msg['product_id']}: {self.prices[msg['product_id']]:.5f}")

    def on_close(self):
        print("-- Goodbye! --")

    def get_price(self, product_id):
        if product_id in self.prices:
            return self.prices[product_id]
        else:
            return -1


class TradingEngine:
    def __init__(self, api_url, key, secret, passphrase, base_currency, max_buy_products,
                 buy_amount, strategy, limit_products):
        self.public_client = cbpro.PublicClient()
        self.auth_client = cbpro.AuthenticatedClient(key, secret, passphrase,
                                                     api_url=api_url)
        self.base_currency = base_currency
        self.max_buy_products = max_buy_products
        self.buy_amount = buy_amount
        self.strategy = strategy
        self.portfolio = Portfolio(base_currency)
        self.tickers_cache = {}
        self.last_strategy_flag = True
        self.limit_products = limit_products

    def get_account(self):
        coinbase_accounts = self.auth_client.get_coinbase_accounts()
        coinbase_account = None
        for acc in coinbase_accounts:
            if acc['currency'] == self.base_currency:
                coinbase_account = acc
                break
        return coinbase_account

    def get_tradable_products(self) -> Dict[str, Dict]:
        products = self.public_client.get_products()
        tradable_products = {}
        for product in products:
            if not product['trading_disabled'] and product['status'] == "online" and product['quote_currency'] == self.base_currency:
                tradable_products[Product.build(product['id'])] = product
        return tradable_products

    def get_last_market_trends(self, tradable_products, start, end):
        market_trend = {}
        for _, product in enumerate(tradable_products):
            pid = product.id
            sts = str(start.timestamp())
            ets = str(end.timestamp())

            if sts not in self.tickers_cache[pid] or ets not in self.tickers_cache[pid]:
                print(
                    f"Unable to compute trends for {pid}, missing ticker informations {sts}-{ets}")
                continue

            now = self.tickers_cache[pid][ets]
            old = self.tickers_cache[pid][sts]
            gain = (now["close"]-old["close"])/now["close"] * 100.0
            market_trend[product] = gain

        if self.strategy == Strategy.TopGainers:
            reverse = True
        elif self.strategy == Strategy.TopLosers:
            reverse = False
        else:
            strategy_file = "strategy.lock"
            if os.path.exists(strategy_file):
                reverse = True
                os.remove(strategy_file)
            else:
                reverse = False
                open(strategy_file, 'a').close()
            
        print(f"Strategy reverse flag {reverse}")
        # sort by gain
        sorted_list = sorted(market_trend.items(),
                             key=lambda item: item[1], reverse=reverse)
        if self.limit_products > 0 and len(market_trend) >= self.limit_products:
            sorted_list = sorted_list[:self.limit_products]
        sorted_market_trend = dict(sorted_list)
        return sorted_market_trend

    def get_buy_quotes(self, selected_prods, tradable_products):
        orders = {}
        ratio = sum(abs(v) for v in selected_prods.values())
        top = ()
        for p in selected_prods:
            val = abs(self.buy_amount *
                      (selected_prods[p]/ratio * 100.0) / 100.0)
            if len(top) == 0 or val > top[1]:
                top = (p, val)
            orders[p] = val
            #print(f"orders[{p}]: {orders[p]}")

        while True:
            untouched = True
            for p in orders.copy():
                min_value = float(tradable_products[p]['min_market_funds'])
                # if we dont reach the min amount we distribute the amount to the next currency
                if orders[p] < min_value:
                    keys = list(orders.keys())
                    idx = keys.index(p) + 1
                    if idx >= len(keys):
                        idx = 0
                    alternative = keys[idx]
                    orig_value = orders[p]
                    orders[alternative] += orders[p]
                    print(
                        f"{p} too small ({orig_value:.4f} < {min_value:.4f}), adding to next product {alternative} = {orders[alternative]:.4f} (min {float(tradable_products[alternative]['min_market_funds']):.4f})")
                    orders.pop(p)
                    untouched = False
            if untouched:
                break
        #print(orders)
        # lets truncate all orders to the right quote increment
        for p in orders:
            orders[p] = self.round_to_increment(orders[p], float(tradable_products[p]["quote_increment"]))

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

    def ticks_contains_date(self, tickers, expected_date):
        for t in tickers:
            if type(t[0]) is not int:
                print(f"Ticker contain string instead of int {t}")
                continue
            dt = datetime.fromtimestamp(int(t[0]))
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            if dt == expected_date:
                return True
        return False

    def prepare_data(self, products: List[Product], begin, end):
        cache_file = "cache.json"
        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
            print(f"Reading cache from file")
            with open(cache_file, "r") as f:
                self.tickers_cache = json.loads(f.read())

        for product in products:
            p = product.id
            print(
                f"Lookup {p} historical data {begin.isoformat()}-{end.isoformat()}")
            begin = begin.replace(hour=0, minute=0, second=0, microsecond=0)
            end = end.replace(hour=0, minute=0, second=0, microsecond=0)

            if p not in self.tickers_cache:
                #print(f"Product {p} not in self.tickers_cache!")
                self.tickers_cache[p] = {}
            else:
                begin_ts = str(begin.timestamp())
                end_ts = str(end.timestamp())
                if begin_ts in self.tickers_cache[p] and end_ts in self.tickers_cache[p]:
                    print(f"Product {p} already in cache!")
                    continue
                else:
                    pass
                    #print(f"Missing timestamps for {p} {begin_ts} - {end_ts}")
                    # print(cache[p])

            tickers = self.public_client.get_product_historic_rates(
                p, start=begin, end=end, granularity=86400)

            if not self.ticks_contains_date(tickers, begin) or not self.ticks_contains_date(tickers, end):
                print(f"Incomplete historical data for {p}")

            for t in tickers:
                try:
                    dt = datetime.fromtimestamp(int(t[0]))
                    dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                    timestamp = str(dt.timestamp())
                    self.tickers_cache[p][timestamp] = {
                        'low': t[1],
                        'high': t[2],
                        'open': t[3],
                        'close': t[4],
                        'volume': t[5],
                    }
                except:
                    print(t)

        with open(cache_file, "w") as f:
            f.write(json.dumps(self.tickers_cache))
        # print(cache)

    def round_to_increment(self, value, increment):
        s = '{:.16f}'.format(increment).split('.')[1]
        zeros = len(s) - len(s.lstrip('0'))
        zeros += 1
        factor = 10.0 ** zeros
        return math.trunc(value * factor) / factor

    def single_run(self, interval: int):
        print(f"**** Executing run {datetime.now()} - {self.buy_amount} {self.base_currency} / {interval} days interval")
        begin = datetime.today() - timedelta(days=interval)
        begin = begin.replace(hour=0, minute=0, second=0, microsecond=0)
        end = datetime.today()
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)

        tradable_products = self.get_tradable_products()
        print(f"Found {len(tradable_products)} tradable products")
        self.prepare_data(tradable_products, begin, end)
        trends = self.get_last_market_trends(tradable_products, begin, end)  
        ordering_products = self.get_buy_quotes(trends, tradable_products)

        print("Trends:")
        print("-------")
        for t in trends:
            print(f"{t.id}: {trends[t]:.2f}%")

        print("\nExecuting orders:")
        print("-------")
        #print(tradable_products)
        for p in ordering_products:
            print(f"Executing {p.id} order {ordering_products[p]} {p.quote}")
            order = self.auth_client.place_market_order(p.id, side="buy", funds=ordering_products[p])
            if "id" in order:
                print(f"Order {order['id']} confirmed!")
            else:
                print(f"Failed to execute order: {order}")

    def simulate_period(self, trading_interval_days: int, periods: int):
        begin = datetime.today() - timedelta(days=(periods*trading_interval_days))

        self.trading_interval_days = trading_interval_days

        tradable_products = self.get_tradable_products()
        print(f"Found {len(tradable_products)} tradable products")

        self.prepare_data(tradable_products, begin, datetime.today())

        for p in range(periods, 0, -1):
            start = datetime.now() - timedelta(days=p*trading_interval_days)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=trading_interval_days)
            end = end.replace(hour=0, minute=0, second=0, microsecond=0)
            print(f"Computing period {start.isoformat()} - {end.isoformat()}")

            trends = self.get_last_market_trends(tradable_products, start, end)

            ordering_products = self.get_buy_quotes(trends, tradable_products)
            # print(ordering_products)

            for product in ordering_products:
                pid = product.id
                order = Order(product)
                # ticker information contains value for a unit of cryptocurrency
                unit_value = 1.0 / \
                    self.tickers_cache[pid][str(end.timestamp())]["close"]
                order.buy(end, ordering_products[product], unit_value)
                self.portfolio.add(order)

        print(self.portfolio.summary(self.tickers_cache))
        print(
            f"Strategy used: {self.strategy.name} across last {periods} periods of {trading_interval_days} days each")

    def execute(self, order):
        pass
