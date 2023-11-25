import argparse
import asyncio
import logging
from datetime import datetime, timedelta
import names
import httpx
import websockets
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK
from prettytable import PrettyTable

logging.basicConfig(level=logging.INFO)


class MaxDaysError(Exception):
    pass


async def request(date: str) -> dict | str:
    async with httpx.AsyncClient() as client:
        url = f'https://api.privatbank.ua/p24api/exchange_rates?date={date}'
        try:
            r = await client.get(url)
            r.raise_for_status()

            result = r.json()
            return result
        except httpx.HTTPStatusError as e:
            logging.error(f"Failed to fetch exchange rates. Status code: {e.response.status_code}")
            return "Failed to fetch exchange rates."


async def get_exchange_rates_for_days(num_days: int, currencies: list):
    today = datetime.now()
    exchange_rates = []

    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(0, num_days):
            if i >= 10:
                raise MaxDaysError("Максимальна кількість днів для відображення - 10 днів")

            date = (today - timedelta(days=i)).strftime('%d.%m.%Y')

            try:
                url = f'https://api.privatbank.ua/p24api/exchange_rates?date={date}'
                r = await client.get(url)
                r.raise_for_status()

                data = r.json()

                if 'exchangeRate' in data:
                    rates = data['exchangeRate']
                    currency_rates = {}

                    for currency in currencies:
                        rate = next((r for r in rates if r['currency'] == currency), None)
                        if rate:
                            currency_rates[currency] = {
                                'sale': float(rate['saleRateNB']),
                                'purchase': float(rate['purchaseRateNB'])
                            }

                    if currency_rates:
                        exchange_rates.append({
                            date: currency_rates
                        })
                        print(date)  # Print each date on a separate line

            except httpx.HTTPStatusError as e:
                logging.error(f"Failed to fetch exchange rates. Status code: {e.response.status_code}")
            except httpx.ReadTimeout:
                logging.error("HTTP request timed out.")
            except Exception as e:
                logging.error(f"An error occurred: {e}")

    return exchange_rates if num_days <= 10 else None  # Return None if num_days exceeds 10


def format_table(exchange_rates, currencies):
    table = PrettyTable()
    table.field_names = ["Date"] + currencies

    for entry in exchange_rates:
        date, currencies_data = list(entry.items())[0]
        row_data = [date] + [currencies_data.get(currency, {'sale': '', 'purchase': ''}) for currency in currencies]
        table.add_row(row_data)

        return str(table)


class Server:
    clients = set()
    currencies = ['EUR', 'USD']  # Add default currencies as a class variable

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distribute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distribute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message.startswith("exchange"):
                command, *params = message.split(" ")
                if command == "exchange":
                    num_days = min(int(params[0]) if params else 1, 10)
                    currencies = ['EUR', 'USD'] + params[1:]

                    try:
                        exchange = await get_exchange_rates_for_days(num_days, currencies)
                        if exchange is not None:
                            await ws.send(str(exchange))

                            # Log the exchange command and timestamp to a file
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            with open('exchange_logs.txt', 'a') as log_file:
                                log_file.write(f"{timestamp} - Exchange command executed: {message}\n")
                        else:
                            await ws.send("Максимальна кількість днів для відображення - 10 днів")
                    except MaxDaysError as e:
                        await ws.send(str(e))
            else:
                # Broadcast regular messages to all clients
                await self.send_to_clients(f"{ws.name}: {message}")


async def main(num_days: int, currencies: list):
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8082):
        await asyncio.Future()  # run forever

        # Get exchange rates
        exchange_rates = await get_exchange_rates_for_days(num_days, currencies)

        # Display exchange rates as a table
        if exchange_rates is not None:
            print(format_table(exchange_rates, currencies))
        else:
            print("Максимальна кількість днів для відображення - 10 днів")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Exchange Rate WebSocket Server')
    parser.add_argument('--num_days', type=int, default=1, help='Number of days for exchange rates')
    parser.add_argument('--currencies', nargs='+', default=['EUR', 'USD'], help='Currencies to track')
    args = parser.parse_args()

    try:
        asyncio.run(main(args.num_days, args.currencies))
    except KeyboardInterrupt:
        pass
