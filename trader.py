#!/bin/python3
import json
import sys
import itertools

from trading import TradingEngine

# this account is the one using to transfer founds
trading_interval_days = 7
# how many products should considerate? (-1 for all of them)
limit_products = 10
# base currency (where the funds are taken from)
base_currency = "EUR"
# recurring buy amount
buy_amount = 50
# how many products should we buy at once?
max_products = 5

with open('config.json') as config_file:
    data = json.load(config_file)

trading = TradingEngine(data['key'], data['b64secret'], data['passphrase'], base_currency)

coinbase_account = trading.get_account()

if coinbase_account is None:
    print(
        f"Couldnt find a coinbase account with the desired currency {base_currency}")
    sys.exit(0)

print(
    f"Coinbase account balance {coinbase_account['balance']} {coinbase_account['currency']}")

tradable_products = trading.get_tradable_products()
# print(tradable_products)
print(f"Found {len(tradable_products)} tradable products")

sorted_market_trend = trading.get_market_trends(
    tradable_products, limit_products, trading_interval_days)

print(f"Selecting {max_products} most gainable products")
ordering_products = dict(itertools.islice(
    sorted_market_trend.items(), max_products))

for pid in ordering_products:
    print(f"{pid}: {ordering_products[pid]:.2f}%")

orders = trading.get_buy_quotes(buy_amount, ordering_products, tradable_products)
trading.execute_orders(orders)
