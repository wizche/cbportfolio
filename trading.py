import cbpro
import enum
import sys
import json
import os
from datetime import datetime, timedelta
import logging
from rich import print
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("trading")

from portfolio import Order, Portfolio

class Strategy(enum.Enum):
   TopGainers = 1
   TopLosers = 2

class PriceTrackerWsClient(cbpro.WebsocketClient):
    def start(self, url, products):
        self.url = url
        self.products = list(products)
        self.channels = ['ticker']
        self.prices = {}
        log.info(f"Subscribing to {len(self.products)} products tickers")
        super().start()

    def on_message(self, msg):
        if "price" in msg:
            self.prices[msg['product_id']] = 1/float(msg['price'])
            #log.info(f"{msg['product_id']}: {self.prices[msg['product_id']]:.5f}")

    def on_close(self):
        log.info("-- Goodbye! --")

    def get_price(self, product_id):
        if product_id in self.prices:
            return self.prices[product_id]
        else: 
            return -1


class TradingEngine:
    def __init__(self, key, secret, passphrase, base_currency, max_buy_products, 
    buy_amount, strategy):
        self.public_client = cbpro.PublicClient()
        self.auth_client = cbpro.AuthenticatedClient(key, secret, passphrase,
                                                api_url="https://api-public.sandbox.pro.coinbase.com")
        self.base_currency = base_currency
        self.max_buy_products = max_buy_products
        self.buy_amount = buy_amount
        self.strategy = strategy

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
            sts = str(start.timestamp())
            ets = str(end.timestamp())
            
            if sts not in self.tickers_cache[pid] or ets not in self.tickers_cache[pid]:
                log.warn(f"Unable to compute trends for {pid}, missing ticker informations")
                continue

            now = self.tickers_cache[pid][ets]
            old = self.tickers_cache[pid][sts]
            gain = (now["close"]-old["close"])/now["close"] * 100.0
            market_trend[p['id']] = gain

        # sort by gain
        sorted_list = sorted(market_trend.items(), key=lambda item: item[1], reverse=self.strategy == Strategy.TopGainers)
        if limit_products > 0 and len(market_trend) >= limit_products:
            sorted_list = sorted_list[:limit_products]
        sorted_market_trend = dict(sorted_list)
        return sorted_market_trend
    
    def get_buy_quotes(self, selected_prods, tradable_products):
        orders = {}
        ratio = sum(abs(v) for v in selected_prods.values())
        top = ()
        for p in selected_prods:
            val = abs(self.buy_amount * (selected_prods[p]/ratio * 100.0) / 100.0)
            if len(top) == 0 or val > top[1]:
                top = (p, val)
            orders[p] = val
            #log.info(f"orders[{p}]: {orders[p]}")

        while True:
            untouched = True
            for p in orders.copy():
                min_value = float(tradable_products[p]['min_market_funds'])
                if orders[p] < min_value:
                    orders[top[0]] += orders[p]
                    log.info(f"{p} too small ({orders[p]:.2f} < {min_value:.2f}), adding to top product {top[0]} = {orders[top[0]]:.2f}")
                    orders.pop(p)
                    untouched = False
            if untouched: break
        return orders

    def execute_orders(self, orders):
        exec_orders = []
        for o in orders:
            log.info(f"Executing order for {o}: {orders[o]} {self.base_currency}")
            order = self.auth_client.place_market_order(
                product_id=o, side='buy', funds=orders[o])
            log.info(order)
            exec_orders.append(order)
        return exec_orders

    def prepare_data(self, products, begin, end):
        self.tickers_cache = {}
        cache_file = "cache.json"
        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
            log.info(f"Reading cache from file")
            with open(cache_file, "r") as f:
                self.tickers_cache = json.loads(f.read())

        for p in products:
            log.info(f"Lookup {p} historical data {begin.isoformat()}-{end.isoformat()}")
            begin = begin.replace(hour=0, minute=0, second=0, microsecond=0)
            end = end.replace(hour=0, minute=0, second=0, microsecond=0)

            if p not in self.tickers_cache:
                #log.info(f"Product {p} not in self.tickers_cache!")
                self.tickers_cache[p] = {}
            else:
                begin_ts = str(begin.timestamp()) 
                end_ts = str(end.timestamp())
                if begin_ts in self.tickers_cache[p] and end_ts in self.tickers_cache[p]:
                    log.info(f"Product {p} already in cache!")
                    continue
                else:
                    pass
                    #log.info(f"Missing timestamps for {p} {begin_ts} - {end_ts}")
                    #log.info(cache[p])
                
            
            tickers = self.public_client.get_product_historic_rates(
                    p, start=begin, end=end, granularity=86400)

            diff = end.date()-begin.date()
            if len(tickers) < diff.days:
                log.info(f"Missing ticks {len(tickers)} instead of {diff.days}")
                continue
            for t in tickers:
                #log.info(t)
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

        with open(cache_file, "w") as f:
            f.write(json.dumps(self.tickers_cache))
        #log.info(cache)

    def simulate_period(self, trading_interval_days: int, periods: int):
        portfolio = Portfolio(self.base_currency)
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

            trends = self.get_last_market_trends(tradable_products, start, end, limit_products=5)

            ordering_products = self.get_buy_quotes(trends, tradable_products)            
            #print(ordering_products)

            for pid in ordering_products:
                order = Order(pid)
                # ticker information contains value for a unit of cryptocurrency
                unit_value = 1.0/self.tickers_cache[pid][str(end.timestamp())]["close"]
                order.buy(end, ordering_products[pid], unit_value)
                portfolio.add(order)

        print(portfolio.summary(self.tickers_cache))
        print(f"Strategy used: {self.strategy.name} across last {periods} periods of {trading_interval_days} days each")

    def execute(self, order):
        pass