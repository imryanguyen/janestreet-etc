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
            print("convert vale -> valbz")

            if isVALELessThanVALBZ and VALE_status == OrderStatus.NOTHING:
                size_vale = 10
                write_to_exchange(exchange, create_add_order(order_id, "VALE", "BUY", VALE_buy_price + 1, size_vale))
                VALE_status = OrderStatus.BUY_PLACED
                print("BUY PLACED! at" + str(VALE_buy_price + 1))