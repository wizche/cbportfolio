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

import json
import sys
import itertools
import random
import datetime
from docopt import docopt

from trading import TradingEngine, Strategy
from portfolio import Order, Portfolio, Product
from typing import Dict, List

from rich import print
from rich.layout import Layout
from rich import box
from rich.align import Align
from rich.console import Console, RenderGroup
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.bar import Bar
from rich.color import Color

# base currency (where the funds are taken from)
base_currency = "EUR"
# buy_amount = 0.0012 # 50 EUR -> BTC


def make_layout() -> Layout:
    """Define the layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3),
    )
    layout["main"].split(
        Layout(name="side"),
        Layout(name="body", ratio=1.5, minimum_size=60),
        direction="horizontal",
    )
    layout["body"].split(Layout(
        name="summary", size=5), Layout(name="orders"), direction="vertical")
    layout["side"].split(Layout(name="portfoliolayout"),
                         Layout(name="gainlayout"))
    return layout


def make_order_grid(orders: List[Order]):
    table = Table(title="Orders", expand=True)

    table.add_column("Date", no_wrap=True)
    table.add_column("Amount", justify="right", style="magenta")
    table.add_column("Spent", justify="right", style="red")
    table.add_column("Unit Price", justify="right")

    for o in orders:
        table.add_row(
            f"{o.buy_time.strftime('%Y-%m-%d')}",
            f"{o.product.base} {o.buy_currency:.3f}",
            f"{o.product.quote} {o.buy_price_with_fee:.3f}",
            f"{o.product.base}/{o.product.quote} {o.unit_price:.3f}"
        )
    return table


def make_summary(portfolio: Portfolio, prices, base_currency):
    grid = Table.grid(expand=True)
    grid.add_column("", justify="left")
    grid.add_column("", justify="right")
    grid.add_column("", justify="left")
    nowts = str(datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0).timestamp())
    total = 0.0
    for p in portfolio.portfolio:
        product_value = portfolio.portfolio[p] * \
            prices[p.id][nowts]["close"]
        total += product_value

    total_spent = portfolio.get_total_spent()
    grid.add_row("[b]Total amount spent:[/b]", f"[red]{total_spent:.2f}[/red]", f"[red] {base_currency}[/red]")
    grid.add_row("[b]Current worth:[/b]", f"[green]{total:.2f}[/green]", f"[green] {base_currency}[/green]")
    grid.add_row("[b]Current gain:[/b]", f"[green]{total/total_spent*100.0:.2f}[/green]", f" [green]%[/green]")
    return Panel(grid, title="Earning/Loss Summary", border_style="green")


def make_portfolio(portfolio: Portfolio, prices):
    table = Table(title="Portfolio", expand=True)
    table.add_column("Curr", no_wrap=True)
    table.add_column("Amount", no_wrap=True)
    table.add_column("Value", justify="right")
    nowts = str(datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0).timestamp())
    for p in portfolio.portfolio:
        spent = 0.0
        for order in portfolio.orders:
            if order.product == p:
                spent += order.buy_price_with_fee

        product_value = portfolio.portfolio[p] * \
            prices[p.id][nowts]["close"]
        val = portfolio.portfolio[p]
        table.add_row(
            f"[magenta]{p.base}[/magenta]",
            f"[magenta]{val:.2f}[/magenta]",
            f"{p.quote} {product_value:.2f}")
    return table


def make_gain(portfolio: Portfolio, prices):
    table = Table(expand=True)
    table.add_column("Curr", no_wrap=True)
    table.add_column("Gain")
    nowts = str(datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0).timestamp())
    max = 0.0
    gains = {}
    for p in portfolio.portfolio:
        spent = 0.0
        for order in portfolio.orders:
            if order.product == p:
                spent += order.buy_price_with_fee
        product_value = portfolio.portfolio[p] * \
            prices[p.id][nowts]["close"]
        gain = product_value/spent*100.0
        if gain > max:
            max = gain

        gains[p]=product_value

    for p in gains:
        gain = gains[p]
        grid = Table.grid()
        grid.add_row(Bar(size=max, begin=0.0, end=gain, color=Color.from_ansi(
            random.randint(1, 254))), f"{gain:.0f}%")
        table.add_row(
            p.base,
            grid)
    return table


class Header:
    def __init__(self, periods, interval):
        self.periods = periods
        self.interval = interval

    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            f"[b]Simulation[/b] {self.periods} periods of {self.interval} days",
            datetime.datetime.now().ctime(),
        )
        return Panel(grid, style="white on blue")


def simulate(buy_amount, interval, periods, strategy, limit_products):
    trading = TradingEngine(None, None, None, None,
                            base_currency, buy_amount, strategy, limit_products)

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
    layout["footer"].update(Panel(
        f"[b]Strategy:[/b] {strategy} | [b]Buy Amount:[/b] {buy_amount} {base_currency} | [b]Max products:[/b] {limit_products}"))
    # print(layout)
    from rich.live import Live
    from time import sleep

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


if __name__ == "__main__":
    arguments = docopt(__doc__, version="1.0")

    if arguments["simulate"]:
        simulate(int(arguments["--amount"]), int(arguments["--interval"]), int(
            arguments["--periods"]), strategy_from_option(arguments["--strategy"]), int(arguments["--limit"]))

    elif arguments["run"]:
        with open(arguments["--config"]) as config_file:
            data = json.load(config_file)
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
