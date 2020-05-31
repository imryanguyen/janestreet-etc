#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json
from enum import Enum


# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="twentiethcenturyfox"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = False

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
    print(exchange_hostname)
    print(port)
    s.connect((exchange_hostname, port))
    return s.makefile('rw', 1)

def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")

def read_from_exchange(exchange):

    return json.loads(exchange.readline())

class Order:
    def __init__(self, size, order_id, symbol):
        self.size = size
        self.symbol = symbol
        self.order_id = order_id
        self.status = OrderStatus.NOTHING

class OrderStatus(Enum):
    NOTHING = 1
    BUY_PLACED = 2
    BUY_ACKED = 3
    CONVERT_PLACED = 4
    CONVERT_ACKED= 5
    SELL_PLACED = 6
    SELL_ACKED = 7
    REJECT = 8

# ~~~~~============== MAIN LOOP ==============~~~~~

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

def bond_exchange(exchange, order_id):
    print("bond done")
    write_to_exchange(exchange, create_add_order(order_id, symbol="BOND",
        dir="BUY", price=999, size=1))
    write_to_exchange(exchange, create_add_order(order_id+1, symbol="BOND",
        dir="SELL", price=1001, size=1))

def get_order(id, orders):
    for o in orders:
        if o.order_id == id:
            return o

def main():
    exchange = connect()

    # Hello from backend
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)
    inv = hello_from_exchange["symbols"]
    print(inv)

    book = {}
    orders = {}

    isVALBZLessThanVALE = False

    orders = []
    xlf_order_ids = []
    bond_order = Order(0, 1010000000, "BOND")
    val_order = Order(0, 1, "VALE")
    xlf_order = Order(0, 10000000000000, "XFL")
    orders.append(bond_order)
    orders.append(val_order)
    orders.append(xlf_order)

    loop = 0
    while 1:
        loop += 1
        incoming = read_from_exchange(exchange)
        if incoming["type"] == "close":
            print(incoming)
            print("CLOSE")
            break
        if incoming["type"] == "book":
            book[incoming["symbol"]] = incoming

        if incoming["type"] == "reject" or incoming["type"] == "ack" or incoming["type"] == "fill":
            print(incoming)

        if loop % 1000000 == 0:
            print("reset")
            for o in orders:
                if o.status == OrderStatus.REJECT:
                    o.status = OrderStatus.NOTHING

        if incoming["type"] == "reject":
            order = get_order(incoming["order_id"], orders)
            if order is not None:
                order.status = OrderStatus.REJECT
                print("reject!")

        if incoming["type"] == "ack":
            order = get_order(incoming["order_id"], orders)
            if order is not None:
                if order.status == OrderStatus.BUY_PLACED:
                    order.status = OrderStatus.BUY_ACKED
                elif order.status == OrderStatus.SELL_PLACED:
                    order.status = OrderStatus.SELL_ACKED
                elif order.status == OrderStatus.CONVERT_PLACED:
                    order.status == OrderStatus.CONVERT_ACKED
                    order. size = 0

        if incoming["type"] == "fill":
            order = get_order(incoming["order_id"], orders)
            if order is not None:
                order.size -= incoming["size"]

        if "XLF" in book and "GS" in book and "MS" in book and "WFC" in book and len(book["XLF"]["sell"]) > 0 and len(book["XLF"]["buy"]) > 0 and len(book["GS"]["sell"]) > 0 and len(book["MS"]["sell"]) > 0 and len(book["WFC"]["sell"]) > 0:
            xlf_sell_price = book["XLF"]["sell"][0][0]
            xlf_buy_price = book["XLF"]["buy"][0][0]
            gs_sell_price = book["GS"]["sell"][0][0]
            ms_sell_price = book["MS"]["sell"][0][0]
            wfc_sell_price = book["WFC"]["sell"][0][0]

            if (incoming["type"] == "fill" or incoming["type"] == "ack") and incoming["order_id"] == xlf_order.order_id and xlf_order.size == 0:
                if xlf_order.status == OrderStatus.BUY_ACKED:
                    xlf_order.order_id += 1
                    xlf_order.size = 10
                    write_to_exchange(exchange, create_convert_order(xlf_order.order_id, "XLF", "SELL", xlf_order.size))
                    xlf_order.status = OrderStatus.CONVERT_PLACED
                    print("XLF CONVERT PLACED!")
                elif xlf_order.status == OrderStatus.CONVERT_PLACED:
                    xlf_order.order_id += 1
                    xlf_order_ids.append(xlf_order.order_id)
                    write_to_exchange(exchange, create_add_order(xlf_order.order_id, "BOND", "SELL", 1000, 3))
                    xlf_order.order_id += 1
                    xlf_order_ids.append(xlf_order.order_id)
                    write_to_exchange(exchange, create_add_order(xlf_order.order_id, "GS", "SELL", gs_sell_price, 2))
                    xlf_order.order_id += 1
                    xlf_order_ids.append(xlf_order.order_id)
                    write_to_exchange(exchange, create_add_order(xlf_order.order_id, "MS", "SELL", ms_sell_price, 3))
                    xlf_order.order_id += 1
                    xlf_order_ids.append(xlf_order.order_id)
                    write_to_exchange(exchange, create_add_order(xlf_order.order_id, "WFC", "SELL", wfc_sell_price, 2))
                    xlf_order.status = OrderStatus.NOTHING
                    print("XLF SELL PLACED!")
                else:
                    xlf_order.status = OrderStatus.NOTHING
                    xlf_order.order_id += 1
                    print("XLF SELL confirmed!!")

            xfl_val = 3 * 1000 + 2 * gs_sell_price + 3 * ms_sell_price + 2 * wfc_sell_price
            #print("val of xlf: " + str(xfl_val))
            #print("sell price of " + str(xlf_buy_price))
            xlf_buy_price
            # if doing nothing, buy!
            if xlf_order.status == OrderStatus.NOTHING:
                xlf_order.order_id += 1
                xlf_order.size = 10
                write_to_exchange(exchange, create_add_order(xlf_order.order_id, "XLF", "BUY", xlf_buy_price, xlf_order.size))
                xlf_order.status = OrderStatus.BUY_PLACED
                print("XLF BUY!")
        
        # REACT TO VALE TRADING
        if "VALE" in book and "VALBZ" in book and len(book["VALE"]["sell"]) > 0 and len(book["VALBZ"]["buy"]) > 0:
            vale_sell_price = book["VALE"]["sell"][0][0]
            valbz_buy_price = book["VALBZ"]["buy"][0][0]

            if (incoming["type"] == "fill" or incoming["type"] == "ack") and incoming["order_id"] == val_order.order_id and val_order.size == 0:
                if val_order.status == OrderStatus.BUY_ACKED:
                    val_order.order_id += 1
                    val_order.size = 10
                    write_to_exchange(exchange, create_convert_order(val_order.order_id, "VALE", "BUY", val_order.size))
                    val_order.status = OrderStatus.CONVERT_PLACED
                    print("VAL CONVERT PLACED!")
                elif val_order.status == OrderStatus.CONVERT_PLACED:
                    val_order.order_id += 1
                    val_order.size = 10
                    write_to_exchange(exchange, create_add_order(val_order.order_id , "VALE", "SELL", vale_sell_price - 1, val_order.size))
                    val_order.status = OrderStatus.SELL_PLACED
                    print("VAL SELL PLACED!")
                else:
                    val_order.status = OrderStatus.NOTHING
                    val_order.order_id += 1
                    print("VAL SELL confirmed!!")


            isVALBZLessThanVALE = valbz_buy_price < vale_sell_price

            if isVALBZLessThanVALE and val_order.status == OrderStatus.NOTHING:
                val_order.size = 10
                val_order.order_id += 1
                print(val_order.order_id)
                write_to_exchange(exchange, create_add_order(val_order.order_id, "VALBZ", "BUY", valbz_buy_price + 1, val_order.size))
                val_order.status = OrderStatus.BUY_PLACED
                print("BUY PLACED! at" + str(valbz_buy_price + 1))

        # REACT TO BOND ORDER FILL
        if incoming["type"] == "fill" and incoming["order_id"] == bond_order.order_id and bond_order.size == 0:
            if bond_order.status == OrderStatus.BUY_ACKED:
                bond_order.order_id += 1
                print(bond_order.order_id)
                write_to_exchange(exchange, create_add_order(bond_order.order_id, "BOND", "SELL", 1001, 30))
                bond_order.status = OrderStatus.SELL_PLACED
                bond_order.size = 10
                print("SELL BOND")
            elif bond_order.status == OrderStatus.SELL_ACKED:
                bond_order.status = OrderStatus.NOTHING
                print("SELL Complete")
        # react to empty bond
        if bond_order.status == OrderStatus.NOTHING:
            bond_order.order_id += 1
            print(bond_order.order_id)
            write_to_exchange(exchange, create_add_order(bond_order.order_id, "BOND", "BUY", 999, 30))
            bond_order.status = OrderStatus.BUY_PLACED
            bond_order.size = 10
            print("BUY BOND")




    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)

if __name__ == "__main__":
    main()
