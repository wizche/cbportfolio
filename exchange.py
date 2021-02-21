import krakenex
from pykrakenapi import KrakenAPI
import cbpro
from abc import ABC, abstractmethod

from typing import Dict, List

from portfolio import Product


class Exchange(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def get_historical(self, product_id, begin, end):
        pass

    @abstractmethod
    def get_account(self, base_currency):
        pass

    @abstractmethod
    def place_market_order(self, product_id, quote_amount) -> int:
        pass

    @abstractmethod
    def get_tradable_products(self, base_currency) -> Dict[str, Dict]:
        pass

    @staticmethod
    def build(data: Dict) -> 'Exchange':
        if data['type'] == "coinbase":
            return CoinbaseExchange(data)
        elif data['type'] == 'kraken':
            return KrakenExchange(data)
        else:
            raise RuntimeError(f"Unknown exchange type {data['type']}")


class CoinbaseExchange:
    def __init__(self, key_data):
        self.public_client = cbpro.PublicClient()
        key = key_data['key']
        if key is not None and key.strip() != "":
            self.auth_client = cbpro.AuthenticatedClient(
                key, key_data['b64secret'], key_data['passphrase'], api_url=key_data['url'])
        else:
            # this will break when executing orders/get account
            self.auth_client = None
        pass
    
    def get_account(self, base_currency):
        coinbase_accounts = self.auth_client.get_coinbase_accounts()
        coinbase_account = None
        for acc in coinbase_accounts:
            if acc['currency'] == base_currency:
                coinbase_account = acc
                break
        return coinbase_account

    def get_tradable_products(self, base_currency) -> Dict[str, Dict]:
        products = self.public_client.get_products()
        tradable_products = {}
        for product in products:
            if not product['trading_disabled'] and product['status'] == "online" and product['quote_currency'] == base_currency:
                tradable_products[Product.build(product['id'])] = product
        return tradable_products

    def get_historical(self, product_id, begin, end):
        tickers = self.public_client.get_product_historic_rates(
                    product_id, start=begin, end=end, granularity=86400)
        return tickers
            

    def place_market_order(self, product_id: str, quote_amount: float):
        order = self.auth_client.place_market_order(
                product_id, side="buy", funds=quote_amount)
        return order


class KrakenExchange:
    def __init__(self, key_data):

        key = key_data['key']
        if key is not None and key.strip() != "":
            api = krakenex.API(key_data['key'], key_data['b64secret'])
        else:
            api = krakenex.API()
        self.kraken = KrakenAPI(api)

    def get_historical(self, product_id, begin, end):
        pass

    def place_market_order(self, product_id, quote_amount):
        pass

    def get_account(self, base_currency):
        pass

    def get_tradable_products(self, base_currency) -> Dict[str, Dict]:
        products = self.kraken.get_tradable_asset_pairs()
        for index, row in products.iterrows():
            print(f"{index}: {row['ordermin']}")
            print(row)
        tradable_products = {}
        for product in products:
            if not product['trading_disabled'] and product['status'] == "online" and product['quote_currency'] == base_currency:
                tradable_products[Product.build(product['id'])] = product
        return tradable_products