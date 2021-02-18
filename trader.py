#!/bin/python3
"""Trader.

Usage:
  trader.py simulate [--interval=<interval>] [--periods=<periods>] [--strategy=<strategy>] [--config=<configfile>]
  trader.py run
  trader.py (-h | --help)
  trader.py --version

Options:
  -h --help                 Show this screen.
  --version                 Show version
  --interval=<interval>     Interval between buy [default: 7]
  --periods=<periods>       How many periods (of interval) [default: 20]
  --strategy=<strategy>     Strategy (gainer|loser|mixed) [default: gainer]
  --config=<configfile>     JSON config file [default: config.json]
"""

import json
import sys
import itertools
from docopt import docopt

from trading import TradingEngine, Strategy

# how many products should considerate? (-1 for all of them)
limit_products = 10
# base currency (where the funds are taken from)
base_currency = "EUR"
# recurring buy amount
buy_amount = 50
# how many products should we buy at once?
max_buy_products = 5

def strategy_from_option(strategy):
    if strategy == "gainer":
        return Strategy.TopGainers
    elif strategy == "loser":
        return Strategy.TopLosers
    elif strategy == "mixed":
        return Strategy.Mixed
    else:
        raise RuntimeError(f"Unknown strategy {strategy}")

def simulate(data, interval, periods, strategy):
    trading = TradingEngine(data['key'], data['b64secret'], data['passphrase'],
                            base_currency, max_buy_products, buy_amount, strategy, limit_products)

    coinbase_account = trading.get_account()

    if coinbase_account is None:
        print(
            f"Couldnt find a coinbase account with the desired currency {base_currency}")
        sys.exit(0)

    print(
        f"Coinbase account balance {coinbase_account['balance']} {coinbase_account['currency']}")

    trading.simulate_period(interval, periods)


if __name__ == "__main__":
    arguments = docopt(__doc__, version="1.0")

    with open(arguments["--config"]) as config_file:
        data = json.load(config_file)

    if arguments["simulate"]:
        simulate(data, int(arguments["--interval"]), int(arguments["--periods"]), strategy_from_option(arguments["--strategy"]))


#    # FUCKED UP
#    sorted_market_trend = trading.get_last_market_trends(
#        tradable_products, limit_products, trading_interval_days,)#
#    print(f"Selecting {max_products} most gainable products")
#    ordering_products = dict(itertools.islice(
#        sorted_market_trend.items(), max_products))#
#    for pid in ordering_products:
#        print(f"{pid}: {ordering_products[pid]:.2f}%")#
#    orders = trading.get_buy_quotes(
#        buy_amount, ordering_products, tradable_products)
#    trading.execute_orders(orders)
