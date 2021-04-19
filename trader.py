#!/usr/bin/env python3
"""Trader.

Usage:
  trader.py simulate [--tune] [--amount=<amount>] [--interval=<interval>] [--periods=<periods>] [--strategy=<strategy>] [--limit=<limit>] [--config=<configfile>]
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
  --tune                    Generate gains for many different parameters
  --limit=<limit>           Max products to buy, -1 all of them [default: 10]
"""

import datetime
import itertools
import json
import sys

from docopt import docopt

from gui import (Header, make_footer, make_gain, make_layout, make_order_grid,
                 make_portfolio, make_summary)
from portfolio import Portfolio, Product
from trading import Strategy, TradingEngine

# base currency (where the funds are taken from)
base_currency = "EUR"
# buy_amount = 0.0012 # ~ 50 EUR -> BTC


def simulate(data, buy_amount, interval, periods, strategy, limit_products, tune=False):

    if tune:
        limits = [2, 5, 8, 10, 15]
        intervals = [3, 5, 7, 10, 15, 20, 30, 40]
        strategies = [Strategy.TopGainers, Strategy.TopLosers, Strategy.Mixed]
        res = {}
        for strategy in strategies:
            res[strategy] = {}
            for limit in limits:
                res[strategy][limit] = {}
                for interval in intervals:
                    trading = TradingEngine(data, base_currency,
                                    buy_amount, strategy, limit)
                    gain = trading.simulate_period(interval, periods)
                    res[strategy][limit][interval] = gain

        for i in res:
            print(f"{i}: {res[i]}")

    else:
        trading = TradingEngine(data, base_currency,
                            buy_amount, strategy, limit_products)
        gain = trading.simulate_period(interval, periods)

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
    elif strategy == "topvolume":
        return Strategy.TopVolume
    elif strategy == "lessvolume":
        return Strategy.LessVolume
    elif strategy == "topmarketcap":
        return Strategy.TopMarketCap
    else:
        raise RuntimeError(f"Unknown strategy {strategy}")


def run(data, buy_amount, interval, strategy, limit_products):
    trading = TradingEngine(data,
                            base_currency, buy_amount, strategy, limit_products)
    trading.single_run(interval)

    print(f"\nStrategy {strategy}")
    print(f"Run finished at {datetime.datetime.now()}")


if __name__ == "__main__":
    arguments = docopt(__doc__, version="1.0")

    with open(arguments["--config"]) as config_file:
        data = json.load(config_file)

    if arguments["simulate"]:
        simulate(data, int(arguments["--amount"]), int(arguments["--interval"]), int(
            arguments["--periods"]), strategy_from_option(arguments["--strategy"]), int(arguments["--limit"]), bool(arguments["--tune"]))
    elif arguments["run"]:
        run(data, int(arguments["--amount"]), int(arguments["--interval"]),
            strategy_from_option(arguments["--strategy"]), int(arguments["--limit"]))
    else:
        raise RuntimeError("Unknown mode")
