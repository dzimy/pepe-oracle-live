#!/usr/bin/env python3
import os
import time
import numpy as np
import pandas as pd
import pandas_ta as ta
from pybit.unified_trading import HTTP
import json

class RevelationTrader:
    def __init__(self):
        self.bybit = HTTP(
            api_key=os.getenv('BYBIT_LIVE_KEY'),
            api_secret=os.getenv('BYBIT_LIVE_SECRET'),
            testnet=False  # REAL MONEY
        )
        self.load_config()
        self.equity = self.bybit.get_wallet_balance()['result']['list'][0]['totalEquity']
        self.initial_equity = self.equity

    def load_config(self):
        with open('config_holiness.json') as f:
            self.params = json.load(f)  # Loads RSI/vol thresholds

    def hunt_liquidations(self):
        liqs = self.bybit.get_liq_records(symbol="PEPEUSDT", period="4h", limit=50)['result']['list']
        buy_liqs = [float(x['price']) for x in liqs if x['side'] == 'Buy']
        sell_liqs = [float(x['price']) for x in liqs if x['side'] == 'Sell']
        return {
            'support': np.mean(buy_liqs[-3:]) if buy_liqs else None,
            'resistance': np.mean(sell_liqs[-3:]) if sell_liqs else None
        }

    def divine_signal(self):
        klines = self.bybit.get_kline(symbol="PEPEUSDT", interval="5", limit=100)['result']['list']
        closes = [float(x[4]) for x in klines]
        volumes = [float(x[5]) for x in klines]
        liqs = self.hunt_liquidations()
        current_price = float(self.bybit.get_tickers(symbol="PEPEUSDT")['result']['list'][0]['lastPrice'])

        rsi = ta.rsi(pd.Series(closes), length=self.params['rsi_length']).iloc[-1]
        vol_ratio = volumes[-1] / np.mean(volumes[-10:])

        long_cond = (
            (rsi < self.params['rsi_oversold']) and 
            (vol_ratio > self.params['vol_threshold']) and 
            (liqs['support'] and (current_price <= liqs['support'] * 1.015))
        
        short_cond = (
            (rsi > self.params['rsi_overbought']) and 
            (vol_ratio > self.params['vol_threshold'] * 0.8) and 
            (liqs['resistance'] and (current_price >= liqs['resistance'] * 0.985))

        if long_cond:
            return ("BUY", 0.99, f"LIQ PUMP: {liqs['support']}")
        elif short_cond:
            return ("SELL", 0.95, f"LIQ DUMP: {liqs['resistance']}")
        return (None, 0, "Waiting")

    def execute_trade(self, signal):
        price = float(self.bybit.get_tickers(symbol="PEPEUSDT")['result']['list'][0]['lastPrice'])
        size = int((self.equity * self.params['risk_per_trade']) / price)
        self.bybit.place_order(
            symbol="PEPEUSDT",
            side=signal,
            orderType="Market",
            qty=str(size),
            takeProfit=str(price * (1 + self.params['take_profit']) if signal == "BUY" else price * (1 - self.params['take_profit'])),
            stopLoss=str(price * (1 - self.params['stop_loss']) if signal == "BUY" else price * (1 + self.params['stop_loss']))
        )
        print(f"💥 {signal} {size:,} PEPE | TP: {self.params['take_profit']:.0%} | SL: {self.params['stop_loss']:.0%}")

    def run(self):
        print("☢️ REVELATION MODE LIVE")
        while True:
            try:
                signal, confidence, reason = self.divine_signal()
                if signal:
                    self.execute_trade(signal)
                    print(f"📡 {reason} | Confidence: {confidence:.0%}")
                time.sleep(10)
            except Exception as e:
                print(f"💀 ERROR: {str(e)[:200]}")
                time.sleep(30)

if __name__ == "__main__":
    RevelationTrader().run()
