#!/bin/python3
"""Trader.

Usage:
  trader.py simulate [--amount=<amount>] [--config=<configfile>] [--interval=<interval>] [--periods=<periods>] [--strategy=<strategy>] [--limit=<limit>]
  trader.py run [--amount=<amount>] [--config=<configfile>] [--interval=<interval>] [--strategy=<strategy>] [--limit=<limit>]
  trader.py (-h | --help)
  trader.py --version

Options:
  -h --help                 Show this screen.
  --version                 Show version
  --interval=<interval>     Interval between buy [default: 7]
  --periods=<periods>       How many periods (of interval) [default: 20]
  --strategy=<strategy>     Strategy (gainer|loser|mixed) [default: gainer]
  --config=<configfile>     JSON config file [default: config.sandbox.json]
  --amount=<amount>         Amount to buy [default: 50]
  --limit=<limit>           Max products to buy, -1 all of them [default: 10]
"""

import json
import sys
import itertools
from docopt import docopt

from trading import TradingEngine, Strategy

# base currency (where the funds are taken from)
base_currency = "EUR"
# buy_amount = 0.0012 # 50 EUR -> BTC


def strategy_from_option(strategy):
    if strategy == "gainer":
        return Strategy.TopGainers
    elif strategy == "loser":
        return Strategy.TopLosers
    elif strategy == "mixed":
        return Strategy.Mixed
    else:
        raise RuntimeError(f"Unknown strategy {strategy}")


def run(data, buy_amount, interval, strategy, limit_products):
    trading = TradingEngine(data['url'], data['key'], data['b64secret'], data['passphrase'],
                            base_currency, buy_amount, strategy, limit_products)
    coinbase_account = trading.get_account()

    if coinbase_account is None:
        print(
            f"Couldnt find a coinbase account with the desired currency {base_currency}")
        sys.exit(0)

    print(
        f"Coinbase account balance {coinbase_account['balance']} {coinbase_account['currency']}")

    trading.single_run(interval)


def simulate(data, buy_amount, interval, periods, strategy, limit_products):
    trading = TradingEngine(data['url'], data['key'], data['b64secret'], data['passphrase'],
                            base_currency, buy_amount, strategy, limit_products)

    trading.simulate_period(interval, periods)


if __name__ == "__main__":
    arguments = docopt(__doc__, version="1.0")

    with open(arguments["--config"]) as config_file:
        data = json.load(config_file)

    if arguments["simulate"]:
        simulate(data, int(arguments["--amount"]), int(arguments["--interval"]), int(
            arguments["--periods"]), strategy_from_option(arguments["--strategy"]), int(arguments["--limit"]))
    elif arguments["run"]:
        run(data, int(arguments["--amount"]), int(arguments["--interval"]),
            strategy_from_option(arguments["--strategy"]), int(arguments["--limit"]))
    else:
        raise RuntimeError("Unknown mode")

#    # FUCKED UP
#    sorted_market_trend = trading.get_last_market_trends(
#        tradable_products, limit_products, trading_interval_days,)#
#    print(f"Selecting {max_products} most gainable products")
#    ordering_products = dict(itertools.islice(
#        sorted_market_trend.items(), max_products))#
#    for pid in ordering_products:
#        print(f"{pid}: {ordering_products[pid]:.4f}%")#
#    orders = trading.get_buy_quotes(
#        buy_amount, ordering_products, tradable_products)
#    trading.execute_orders(orders)
