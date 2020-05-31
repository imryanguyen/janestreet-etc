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
test_mode = True

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index=1
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
    def __init__(self, size):
        self.size = size

class OrderStatus(Enum):
    NOTHING = 1
    BUY_PLACED = 2
    CONVERT_PLACED = 3
    SELL_PLACED = 4

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

def main():
    exchange = connect()

    # Hello from backend
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)

    book = {}
    orders = []
    VALBZ_status = OrderStatus.NOTHING
    VALE_status = OrderStatus.NOTHING

    isVALBZLessThanVALE = False
    isVALELessThanVALBZ = False

    order_id = 1010



    while 1:
        incoming = read_from_exchange(exchange)
        if incoming["type"] == "book":
            book[incoming["symbol"]] = incoming
        if incoming["type"] == "reject" or incoming["type"] == "ack":
            print(incoming)

        # if ack for convert, it means fulfilled (no fill sent for convert)
        if incoming["type"] == "ack" and VALBZ_status == OrderStatus.CONVERT_PLACED:
            size = 0
        if incoming["type"] == "fill":
            print(incoming)
            size -= incoming["size"]

        if incoming["type"] == "ack" and VALE_status == OrderStatus.CONVERT_PLACED:
            size_vale = 0
        if incoming["type"] == "fill":
            print(incoming)
            size_vale -= incoming["size"]

        if "VALE" in book and "VALBZ" in book and len(book["VALE"]["sell"]) > 0 and len(book["VALBZ"]["buy"]) > 0:
            vale_sell_price = book["VALE"]["sell"][0][0]
            valbz_buy_price = book["VALBZ"]["buy"][0][0]

            if (incoming["type"] == "fill" or incoming["type"] == "ack") and incoming["order_id"] == order_id and size == 0:
                if VALBZ_status == OrderStatus.BUY_PLACED:
                    order_id += 1
                    size = 10
                    write_to_exchange(exchange, create_convert_order(order_id, "VALE", "BUY", size)) #valbz -> vale
                    VALBZ_status = OrderStatus.CONVERT_PLACED
                    print("CONVERT PLACED!")
                elif VALBZ_status == OrderStatus.CONVERT_PLACED:
                    order_id += 1
                    size = 10
                    write_to_exchange(exchange, create_add_order(order_id, "VALE", "SELL", vale_sell_price - 1, size))
                    VALBZ_status = OrderStatus.SELL_PLACED
                    print("SELL PLACED!")
                else:
                    VALBZ_status = OrderStatus.NOTHING
                    order_id += 1
                    print("SELL confirmed!!")

            isVALBZLessThanVALE = valbz_buy_price < vale_sell_price 
            if(isVALBZLessThanVALE):
                print("convert valbz -> vale")

            if isVALBZLessThanVALE and VALBZ_status == OrderStatus.NOTHING:
                size = 10
                write_to_exchange(exchange, create_add_order(order_id, "VALBZ", "BUY", valbz_buy_price + 1, size))
                VALBZ_status = OrderStatus.BUY_PLACED
                print("BUY PLACED! at" + str(valbz_buy_price + 1))

       
        if "VALBZ" in book and "VALE" in book and len(book["VALBZ"]["sell"]) > 0 and len(book["VALE"]["buy"]) > 0:
            VALBZ_sell_price = book["VALBZ"]["sell"][0][0]
            VALE_buy_price = book["VALE"]["buy"][0][0]

            if (incoming["type"] == "fill" or incoming["type"] == "ack") and incoming["order_id"] == order_id and size_vale == 0:
                if VALE_status == OrderStatus.BUY_PLACED:
                    order_id += 1
                    size_vale = 10
                    write_to_exchange(exchange, create_convert_order(order_id, "VALBZ", "BUY", size_vale)) #VALE -> VALBZ
                    VALE_status = OrderStatus.CONVERT_PLACED
                    print("CONVERT PLACED!")
                elif VALE_status == OrderStatus.CONVERT_PLACED:
                    order_id += 1
                    size_vale = 10
                    write_to_exchange(exchange, create_add_order(order_id, "VALBZ", "SELL", VALBZ_sell_price - 1, size_vale))
                    VALE_status = OrderStatus.SELL_PLACED
                    print("SELL PLACED!")
                else:
                    VALE_status = OrderStatus.NOTHING
                    order_id += 1
                    print("SELL confirmed!!")

            isVALELessThanVALBZ = VALE_buy_price < VALBZ_sell_price
            if(isVALELessThanVALBZ):   
                print("convert vale -> valbz")

            if isVALELessThanVALBZ and VALE_status == OrderStatus.NOTHING:
                size_vale = 10
                write_to_exchange(exchange, create_add_order(order_id, "VALE", "BUY", VALE_buy_price + 1, size_vale))
                VALE_status = OrderStatus.BUY_PLACED
                print("BUY PLACED! at" + str(VALE_buy_price + 1))



    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)

if __name__ == "__main__":
    main()
