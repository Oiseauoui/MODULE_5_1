from http import server
import aiohttp
import asyncio
import logging
import websockets
from datetime import datetime, timedelta
import names
import httpx
import argparse
from prettytable import PrettyTable

from websockets import WebSocketServerProtocol, WebSocketProtocolError

logging.basicConfig(level=logging.INFO)


async def request(url: str) -> dict | str:
    timeout_seconds = 10

    async with aiohttp.ClientSession() as client:
        try:
            async with client.get(url, timeout=timeout_seconds) as response:
                response.raise_for_status()
                result = await response.json()
                return result
        except aiohttp.ClientError as e:
            return f"Failed to retrieve data. Error: {e}"


async def request_exchange_rate(date: str) -> dict:
    url = f'https://api.privatbank.ua/p24api/exchange_rates?date={date}'
    return await request(url)


async def get_exchange_rates_for_days(num_days: int, currencies: list):
    today = datetime.now()
    exchange_rates = []

    for i in range(min(num_days, 10)):
        date = (today - timedelta(days=i)).strftime('%d.%m.%Y')
        data = await request_exchange_rate(date)

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

    return exchange_rates


async def main(num_days: int, currencies: list):
    if num_days > 10:
        print("Максимальна кількість днів для відображення - 10 днів")
        return

    exchange_rates = await get_exchange_rates_for_days(num_days, currencies)

    # Display exchange rates as a table
    table = PrettyTable()
    table.field_names = ["Date", "Currency", "Purchase", "Sale"]

    for entry in exchange_rates:
        date, currencies_data = list(entry.items())[0]
        for currency, rates in currencies_data.items():
            table.add_row([date, currency, rates.get('purchase', ''), rates.get('sale', '')])

    print(table)


class Server:
    clients = set()

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

    async def ws_handler(self, ws: WebSocketServerProtocol, path: str):
        await self.register(ws)
        try:
            await self.distribute(ws)
        except WebSocketProtocolError as err:
            logging.error(err)
        finally:
            await self.unregister(ws)

    async def distribute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message.startswith("exchange"):
                command, *params = message.split(" ")
                if command == "exchange":
                    num_days = int(params[0]) if params else 1
                    currencies = ['EUR', 'USD'] + params[1:]
                    exchange = await get_exchange_rates_for_days(num_days, currencies)
                    await ws.send(str(exchange))
                    # Log the exchange command to a file
                    with open('exchange_logs.txt', 'a') as log_file:
                        log_file.write(f"Exchange command executed: {message}\n")
            else:
                # Broadcast regular messages to all clients
                await self.send_to_clients(f"{ws.name}: {message}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get exchange rates for EUR and USD from PrivatBank.')
    parser.add_argument('num_days', type=int, help='Number of days to retrieve exchange rates for')
    parser.add_argument('--currencies', nargs='+', default=['EUR', 'USD'], help='Additional currencies to include')
    args = parser.parse_args()

    try:
        asyncio.run(main(args.num_days, args.currencies))
    except KeyboardInterrupt:
        pass
