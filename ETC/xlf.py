#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json
import time
from enum import Enum

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="twentiethcenturyfox"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = True

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index=0
prod_exchange_hostname="production"

port=25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

# ~~~~~============== NETWORKING CODE ==============~~~~~
def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((exchange_hostname, port))
    return s.makefile('rw', 1)

def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")

def read_from_exchange(exchange):
    return json.loads(exchange.readline())


# ~~~~~============== BUYING ORDERS ==============~~~~~
class Order:
    def __init__(self, xlf_size):
        self.xlf_size = xlf_size

class OrderStatus(Enum):
    NOTHING = 1
    BUY_PLACED = 2
    CONVERT_PLACED = 3
    SELL_PLACED = 4

# Return dictionary representing client message. Works for add and convert types.
def create_client_message(type, order_id, symbol, dir, price=0, size=0):
    client_message = {}
    client_message["type"] = type
    client_message["order_id"] = order_id
    client_message["symbol"] = symbol
    client_message["dir"] = dir
    client_message["price"] = price
    client_message["size"] = size
    return client_message

def create_add_order(order_id, symbol, dir, price, size):
    add_order = create_client_message(type="add", order_id=order_id, symbol=symbol,
        dir=dir, price=price, size=size)
    return add_order

def create_convert_order(order_id, symbol, dir, size):
    add_order = create_client_message(type="convert", order_id=order_id, symbol=symbol,
        dir=dir, size=size)
    return add_order

def bond(exchange, order, order_id):
    write_to_exchange(exchange, order)
    order_id += 1
    time.sleep(0.01)
    return order_id

def bond_exchange(exchange, order_id):
    write_to_exchange(exchange, create_add_order(order_id=order_id, symbol="BOND", 
        dir="BUY", price=999, size=1))
    write_to_exchange(exchange, create_add_order(order_id=order_id+1, symbol="BOND", 
        dir="SELL", price=1001, size=1))

def calculate_xlf_convert(XLF_convert):
    return (3*XLF_convert["BOND"] + 2*XLF_convert["GS"] + 3*XLF_convert["MS"] + 2*XLF_convert["WFC"])

def nonempty_sell_list(book, symbol):
    all_nonempty = True
    symbol_nonempty = len(book[symbol]["sell"]) > 0
    all_nonempty = all_nonempty and symbol_nonempty
    return all_nonempty

def nonempty_buy_list(book, symbols):
    all_nonempty = True
    for symbol in symbols:
        symbol_nonempty = len(book[symbol]["buy"]) > 0
        all_nonempty = all_nonempty and symbol_nonempty
    return all_nonempty


# ~~~~~============== MAIN LOOP ==============~~~~~

def main():
    order_id = 1012313
    book = {}
    print("hey")

    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)

    xlf_sell_price = 0
    XLF_convert = {
        "BOND":0,
        "GS":0,
        "MS":0,
        "WFC":0
    }
    canConvert = False
    XLF_status = OrderStatus.NOTHING
    xlf_size = 0

    bond_size = 0
    gs_size = 0
    ms_size = 0
    wfc_size = 0
    

    while(1):
        incoming = read_from_exchange(exchange)
        if incoming["type"] == "book":
            book[incoming["symbol"]] = incoming
        if incoming["type"] == "reject" or incoming["type"] == "ack":
            print(incoming)

        if incoming["type"] == "ack" and XLF_status == OrderStatus.CONVERT_PLACED:
            xlf_size = 0
        if incoming["type"] == "fill":
            print(incoming)
            xlf_size -= incoming["size"]


        stock_symbols = ["BOND", "GS", "MS", "WFC"]
        all_symbols = ["BOND", "GS", "MS", "WFC", "XLF"]
        
        if all(symbol in book for symbol in all_symbols) and len(book["XLF"]["sell"]) > 0 and len(book["XLF"]["buy"]) > 0 and nonempty_buy_list(book, stock_symbols):
            print(book)
            if "XLF" in book and len(book["XLF"]["sell"]) > 0 and len(book["XLF"]["buy"]) > 0:
                xlf_sell_price = book["XLF"]["sell"][0][0]
                xlf_buy_price = book["XLF"]["buy"][0][0]

            for key in XLF_convert:
                if key in book and len(book[key]["buy"]) > 0:
                    XLF_convert[key] = book[key]["buy"][0][0]

            convert_buy_price = calculate_xlf_convert(XLF_convert)-100
            stock_sold = (gs_size + bond_size + wfc_size + ms_size == 0)

            if (incoming["type"] == "fill" or incoming["type"] == "ack") and incoming["order_id"] == order_id and stock_sold == True:
                if XLF_status == OrderStatus.BUY_PLACED:
                    order_id += 1
                    xlf_size = 10
                    write_to_exchange(exchange, create_convert_order(order_id, "XLF", "SELL", xlf_size)) #xlf -> stocks
                    XLF_status = OrderStatus.CONVERT_PLACED
                
                elif XLF_status == OrderStatus.CONVERT_PLACED:
                    order_id += 1
                    xlf_size = 0
                    bond_size = 3
                    gs_size = 2
                    ms_size = 3
                    wfc_size = 2

                    write_to_exchange(exchange, create_add_order(order_id, "BOND", "SELL", XLF_convert["BOND"] - 1, bond_size))
                    write_to_exchange(exchange, create_add_order(order_id, "GS", "SELL", XLF_convert["GS"] - 1, gs_size))
                    write_to_exchange(exchange, create_add_order(order_id, "MS", "SELL", XLF_convert["MS"] - 1, ms_size))
                    write_to_exchange(exchange, create_add_order(order_id, "WFC", "SELL", XLF_convert["WFC"] - 1, wfc_size))
                    XLF_status = OrderStatus.SELL_PLACED

                else:
                    XLF_status = OrderStatus.NOTHING
                    order_id += 1
                    print("SELL confirmed.")
            


            print("10 XLF price: ", 10*xlf_sell_price)
            print("Convert: ", calculate_xlf_convert(XLF_convert)-100)

            if ((10*xlf_sell_price) < calculate_xlf_convert(XLF_convert)-100):
                canConvert = True
                print("Can convert.")
                print()

            if (XLF_status == OrderStatus.NOTHING and canConvert == True):
                xlf_size = 10
                write_to_exchange(exchange, create_add_order(order_id, "XLF", "BUY", xlf_buy_price + 1, xlf_size))

    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)

if __name__ == "__main__":
    main()
