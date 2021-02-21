#!/bin/python3
"""Trader.

Usage:
  trader.py simulate [--amount=<amount>] [--interval=<interval>] [--periods=<periods>] [--strategy=<strategy>] [--limit=<limit>]
  trader.py run [--amount=<amount>] [--config=<configfile>] [--interval=<interval>] [--strategy=<strategy>] [--limit=<limit>]
  trader.py (-h | --help)
  trader.py --version

Options:
  -h --help                 Show this screen.
  --version                 Show version
  --interval=<interval>     Interval between buy [default: 7]
  --periods=<periods>       How many periods (of interval) [default: 20]
  --strategy=<strategy>     Strategy (gainer|loser|mixed) [default: gainer]
  --config=<configfile>     JSON API config file [default: config.sandbox.json]
  --amount=<amount>         Amount to buy [default: 50]
  --limit=<limit>           Max products to buy, -1 all of them [default: 10]
"""

import datetime
import itertools
import json
import random
import sys

from docopt import docopt

from gui import (Header, make_footer, make_gain, make_layout, make_order_grid,
                 make_portfolio, make_summary)
from portfolio import Portfolio, Product
from trading import Strategy, TradingEngine

# base currency (where the funds are taken from)
base_currency = "EUR"
# buy_amount = 0.0012 # ~ 50 EUR -> BTC


def simulate(data, buy_amount, interval, periods, strategy, limit_products):
    trading = TradingEngine(data, base_currency,
                            buy_amount, strategy, limit_products)

    trading.simulate_period(interval, periods)

    layout = make_layout()

    layout["header"].update(Header(periods, interval))
    layout["orders"].update(make_order_grid(trading.portfolio.orders))
    layout["summary"].update(make_summary(
        trading.portfolio, trading.tickers_cache, base_currency))
    layout["portfoliolayout"].update(make_portfolio(
        trading.portfolio, trading.tickers_cache))
    layout["gainlayout"].update(
        make_gain(trading.portfolio, trading.tickers_cache))
    layout["footer"].update(make_footer(
        strategy, buy_amount, base_currency, limit_products))
    # print(layout)
    from time import sleep

    from rich.live import Live

    with Live(layout, refresh_per_second=10, screen=True):
        while True:
            sleep(0.5)


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
    trading = TradingEngine(data,
                            base_currency, buy_amount, strategy, limit_products)
    trading.single_run(interval)


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
