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

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="REPLACEME"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = True

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index=2
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

def bond(exchange, order_id, buy_order, sell_order):
    write_to_exchange(exchange, buy_order);
    time.sleep(0.01)
    write_to_exchange(exchange, sell_order)


# ~~~~~============== MAIN LOOP ==============~~~~~

def main():

    add_order_id = 0 # Increment every time order is created.
    add_order_999 = create_add_order(order_id=add_order_id,
        symbol="BOND", dir="BUY", price=999, size=10)
    add_order_id += 1
    add_order_998 = create_add_order(order_id=add_order_id,
        symbol="BOND", dir="BUY", price=998, size=10)
    add_order_id += 1
    add_order_998 = create_add_order(order_id=add_order_id,
        symbol="BOND", dir= "BUY", price=997, size=10)
    add_order_id += 1

    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)

    while(1):
        add_order_id += 1;
        buy_price = [999,998,997];

        add_buy_order = create_add_order(order_id=add_order_id,
            symbol="BOND", dir="BUY", price=, size=10)
        bond(exchange, add_order_id, add_buy_order)


        time.sleep(0.01)
        add_order_id += 1;
        init_sell_price = 1000;
        add_buy_order = create_add_order(order_id=add_order_id,
            symbol="BOND", dir="BUY", price=init_sell_price+1, size=10)
        

    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)

if __name__ == "__main__":
    main()
