import httpx, aiohttp
import asyncio
from TonTools import TonApiClient, Wallet, Address
import os
from dotenv import load_dotenv
import json

load_dotenv()
floor_gap = float(os.getenv('floor_gap'))
collection_id = os.getenv('collection_id')
api_key = os.getenv('api_key')
seed = json.loads(os.getenv('seed'))
contractor_address = os.getenv('address')


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

def get_list_of_nft():
    with open('nft_list.txt', 'r') as f:
        return f.read().splitlines()
    
def check_nft_in_file(address):
    with open('nft_list.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.strip() == address:
                return True
            
    return False

def add_nft(address):
    with open('nft_list.txt', 'a') as f:
        f.write(address + '\n')

class UpdateTonApi(TonApiClient):
    def __init__(self, key: str = None, addresses_form='user_friendly'):  # adresses_form could be 'raw' or 'user_friendly'
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

async def fetch_all_nfts_from_collection(collection: str, api_key: str, limit_per_request: int = 250):
    all_nfts = []
    offset = 0

    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(headers=headers) as client:
        while True:
            response = await client.get(f"https://tonapi.io/v2/nfts/collections/{collection}/items",
                                         params={"limit": limit_per_request, "offset": offset})
            data = response.json()
            nfts = data.get('nft_items', [])
            if not nfts:
                break
            all_nfts.extend(nfts)
            offset += limit_per_request
    return all_nfts

async def get_account(address: str, api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(f"https://tonapi.io/v2/accounts/{address}")
        return response.json()

async def get_events(address: str, api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(f"https://tonapi.io/v2/accounts/{address}/events?initiator=false&subject_only=false&limit=10")
        return response.json()

async def get_method(address: str, api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(f"https://tonapi.io/v2/blockchain/accounts/{address}/methods/get_sale_data")
        return response.json()

async def get_nft(nft_address: str, api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.post(f"https://tonapi.io/v2/nfts/_bulk",
                                     json = {
                                        "account_ids": [nft_address]
                                    })
        return response.json()


async def check_for_nfts():
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(
            f"https://tonapi.io/v2/accounts/{contractor_address}/nfts")

    response = response.json()
    if len(response['nft_items']) > 0:
        return True
    else:
        return False

async def buy_nft(contract_nft_address, api_key, ton_amount, seed):
    if check_nft_in_file(contract_nft_address):
        print(f"NFT {contract_nft_address} already bought.")
        return False

    try:
        account = await get_account(contract_nft_address, api_key)
    except Exception as e:
        print(f"Failed to get account information: {e}")
        return False
    
    if "interfaces" not in account or "nft_sale_v2" not in account["interfaces"]:
        print("Invalid NFT address or not a sale contract.")
        return False

    my_wallet = Wallet(provider=UpdateTonApi(key=api_key), address=contractor_address, mnemonics=seed, version='v4r2')
    friendly_address = Address(contract_nft_address).to_string(is_user_friendly=True, is_bounceable=True)
    try:
        tx = await my_wallet.transfer_ton(friendly_address, ton_amount)
        print(f"NFT {friendly_address} bought for {ton_amount} TON | Transaction: {tx}")
        add_nft(contract_nft_address)  # Record the NFT purchase
        return True
    except Exception as e:
        print(f"Failed to complete the purchase: {e}")
        return False



async def fetch_floor_price(address: str) -> float:
    query = """
    query ExampleQuery($address: String!) {
      me {
        id
      }
      myPermissions
      alphaNftCollectionStats(address: $address) {
        floorPrice
      }
    }
    """

    url = "https://api.getgems.io/graphql"
    json_data = {
        "query": query,
        "variables": {"address": address},
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=json_data)
        response.raise_for_status()
        data = response.json()
        
        floor_price = data["data"]["alphaNftCollectionStats"]["floorPrice"]
        return floor_price

async def main(collection_id, api_key, floor_gap, seed):
    while True:
        # floor_price = await fetch_floor_price(collection_id)
        # print(floor_price)
        floor_price = 0.6
        floor_price = (floor_price - floor_gap) * 10**9 * 10 # cuz 10 mil have price 10 much higher

        if floor_price < 0:
            return

        events = await get_events("EQAIFunALREOeQ99syMbO6sSzM_Fa1RsPD5TBoS0qVeKQ-AR", api_key)
        if "events" not in events:
            continue
        
        events = events["events"]
        
        for event in events:
            if "actions" not in event:
                continue
            
            for action in event["actions"]:
                if "type" not in action:
                    continue
                
                if action["type"] == "SmartContractExec":
                    contract_address = action["SmartContractExec"]["contract"]["address"]
                    operation = action["SmartContractExec"]["operation"]
                    
                    if operation == "0x00000001":
                        #print("Probably we can buy it")

                        sale_data = await get_method(contract_address, api_key)
                        if "error" in sale_data:
                            continue
                        
                        price = int(sale_data["decoded"]["full_price"])
                        nft_address = sale_data["decoded"]["nft"]
                        
                        if not price or price == 0 or price > floor_price or price < 0 * 10 ** 9:
                            continue

                        price_with_fee = (price + 1 * 10**9) / 10 ** 9
                        
                        nft = await get_nft(nft_address, api_key)
                        
                        if not nft or "nft_items" not in nft:
                            continue
                        nft_item = nft["nft_items"][0]
                        nft_collection = nft_item["collection"]["address"]
                        
                        if nft_collection.lower() != collection_id.lower():
                            continue

                        await buy_nft(contract_address, api_key, price_with_fee, seed)

        if await check_for_nfts():
            os.system('python transfer_nft.py')



if __name__ == "__main__":
    asyncio.run(main(
        collection_id=collection_id,
        api_key=api_key, 
        floor_gap=floor_gap,  
        seed=seed
        )
    )
