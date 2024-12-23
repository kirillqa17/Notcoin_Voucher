import httpx, aiohttp
import asyncio
from TonTools import *
import os
import json
from dotenv import load_dotenv
import time

load_dotenv()
contractor_address = os.getenv('address')

api_key = os.getenv('api_key')
seed = json.loads(os.getenv('seed'))
headers = {"Authorization": f"Bearer {api_key}"}



class TonApiError(BaseException):
    pass


async def process_response(response: aiohttp.ClientResponse):
    try:
        response_dict = await response.json()
    except:
        raise TonApiError(f'Failed to parse response: {response.text}')
    if response.status != 200:
        raise TonApiError(f'TonApi failed with error: {response_dict}')
    else:
        return response_dict


class UpdateTonApi(TonApiClient):
    def __init__(self, key: str = None,
                 addresses_form='user_friendly'):  # adresses_form could be 'raw' or 'user_friendly'
        self.form = addresses_form
        self.base_url = 'https://tonapi.io/v2/'
        if key:
            self.headers = {
                'Authorization': 'Bearer ' + key
            }
        else:
            self.headers = {}

    def _process_address(self, address):
        if self.form == 'user_friendly':
            return Address(address).to_string(True, True, True)
        elif self.form == 'raw':
            return Address(address).to_string(is_user_friendly=False)

    async def send_boc(self, boc):
        async with aiohttp.ClientSession() as session:
            url = 'https://tonapi.io/v2/blockchain/message'
            data = {
                'boc': boc
            }
            response = await session.post(url=url, json=data, headers=self.headers)
            return response

    async def get_wallet_seqno(self, address: str):
        async with aiohttp.ClientSession() as session:
            url = self.base_url + f'wallet/{address}/seqno'
            response = await session.get(url=url, headers=self.headers)
            response = await process_response(response)
            seqno = response['seqno']
            return seqno


async def check_for_nfts():
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(
            f"https://tonapi.io/v2/accounts/{contractor_address}/nfts")

    response = response.json()
    return response['nft_items']


async def get_friendly_add(address):
    return Address(address).to_string(is_user_friendly=True, is_bounceable=True)


def check_nft_in_file(address):
    with open('sent_nfts.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.strip() == address:
                return True


def add_nft(address):
    with open('sent_nfts.txt', 'a') as f:
        f.write(address + '\n')


async def parse_address(address):
    async with httpx.AsyncClient(headers=headers) as client:
        temp = await client.get(f"https://tonapi.io/v2/address/{address}/parse")
    temp = temp.json()
    return temp['bounceable']['b64url']


async def transfer_nft(nft_add):
    to_ = Address('UQCy_K4lt64_tjAV0Ni75zQiwcwFyMZ-x00x_5jwSwlsY8NR').to_string(is_user_friendly=True,
                                                                                is_bounceable=True)
    my_wallet = Wallet(provider=UpdateTonApi(key=api_key), address=contractor_address,
                       mnemonics=seed, version='v4r2')
    nft_friendly_add = await get_friendly_add(nft_add)
    try:
        tx = await my_wallet.transfer_nft(to_, nft_friendly_add)
        add_nft(nft_add)
        return True
    except Exception as e:
        print(f"Failed to complete the transfer: {e}")
        return False


async def main():
    nft_items = await check_for_nfts()
    if len(nft_items) > 0:
        for objects in nft_items:
            new_add = await parse_address(objects['address'])
            if not check_nft_in_file(new_add):
                await transfer_nft(new_add)
                print(f"NFT {new_add} sent!")

if __name__ == "__main__":
    asyncio.run(main())
