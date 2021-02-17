#!/bin/python3
import json
import sys
import itertools
from datetime import datetime

from rich import box, print
from rich.align import Align
from rich.console import Console, RenderGroup
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from trading import TradingEngine, Strategy

# this account is the one using to transfer founds
trading_interval_days = 7
# how many products should considerate? (-1 for all of them)
limit_products = 10
# base currency (where the funds are taken from)
base_currency = "EUR"
# recurring buy amount
buy_amount = 50
# how many products should we buy at once?
max_buy_products = 5
simulation = True

class Header:
    """Display header with clock."""

    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            "[b]Trading[/b] Engine",
            datetime.now().ctime().replace(":", "[blink]:[/]"),
        )
        return Panel(grid, style="white on blue")

def make_layout() -> Layout:
    """Define the layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=7),
    )
    layout["main"].split(
        Layout(name="side"),
        Layout(name="body", ratio=2, minimum_size=60),
        direction="horizontal",
    )
    layout["side"].split(Layout(name="box1"), Layout(name="box2"))
    return layout

with open('config.json') as config_file:
    data = json.load(config_file)

trading = TradingEngine(data['key'], data['b64secret'], data['passphrase'], base_currency, max_buy_products, buy_amount, Strategy.TopGainers)

coinbase_account = trading.get_account()

if coinbase_account is None:
    print(
        f"Couldnt find a coinbase account with the desired currency {base_currency}")
    sys.exit(0)

print(
    f"Coinbase account balance {coinbase_account['balance']} {coinbase_account['currency']}")

#tradable_products = trading.get_tradable_products()
# print(tradable_products)

if simulation:
    trading.simulate_period(trading_interval_days, 30)
else:
    # FUCKED UP
    sorted_market_trend = trading.get_last_market_trends(
        tradable_products, limit_products, trading_interval_days,)

    print(f"Selecting {max_products} most gainable products")
    ordering_products = dict(itertools.islice(
        sorted_market_trend.items(), max_products))

    for pid in ordering_products:
        print(f"{pid}: {ordering_products[pid]:.2f}%")

    orders = trading.get_buy_quotes(buy_amount, ordering_products, tradable_products)
    trading.execute_orders(orders)
