from web3 import Web3
import time

# Ethereum node endpoint (replace with your own endpoint)
ETH_NODE_URL = "https://sepolia.infura.io/v3/9c7e70b4bf234955945ff87b8149926e"
web3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# Check connection to Ethereum node
if not web3.isConnected():
    raise ConnectionError("Unable to connect to Ethereum node. Check your endpoint.")


# Sepolia position manager: 0x1238536071E1c677A632429e3655c799b22cDA52
# Sepolia factory contract: 0x0227628f3F023bb0B980b67D528571c95c6DaC1c

# Uniswap V3 pool addresses (replace with actual pool addresses)
UNISWAP_POOLS = {
    "UNI-WETH": "0x287B0e934ed0439E2a7b1d5F0FC25eA2c24b64f7", # UNI-WETH
    "USDC-WETH": "0xaB9C1409490dCf0B9177dF840D96Da5653F5c5cF", # USDC-WETH
    "MTK-WETH": "0x836860FB729EC534E8777C61F4c48655E9fD0541" # MTK-WETH
}

# ABI for Uniswap V3 pool (minimal required for fetching prices)
UNISWAP_POOL_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"name": "sqrtPriceX96", "type": "uint160"},
            {"name": "tick", "type": "int24"},
            {"name": "observationIndex", "type": "uint16"},
            {"name": "observationCardinality", "type": "uint16"},
            {"name": "observationCardinalityNext", "type": "uint16"},
            {"name": "feeProtocol", "type": "uint8"},
            {"name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Function to fetch the real-time price
def fetch_price(pool_address):
    try:
        pool_contract = web3.eth.contract(address=web3.toChecksumAddress(pool_address), abi=UNISWAP_POOL_ABI)
        slot0 = pool_contract.functions.slot0().call()
        sqrt_price_x96 = slot0[0]  # sqrtPriceX96 from slot0
        tick = slot0[1]  # Current tick
        price = (sqrt_price_x96 / (2 ** 96)) ** 2  # Convert sqrtPriceX96 to price
        return {"sqrtPriceX96": sqrt_price_x96, "tick": tick, "price": price}
    except Exception as e:
        print(f"Error fetching price for pool {pool_address}: {e}")
        return None

# Main loop to fetch prices every block
def main():
    print("Starting real-time Uniswap V3 price fetcher...")
    while True:
        print(f"Fetching prices at block {web3.eth.blockNumber}...")
        for pair, pool_address in UNISWAP_POOLS.items():
            data = fetch_price(pool_address)
            if data:
                print(f"Pair: {pair} | Price: {data['price']:.8f} | Tick: {data['tick']} | sqrtPriceX96: {data['sqrtPriceX96']}")
            else:
                print(f"Failed to fetch data for pair {pair}.")
        print("-" * 50)
        time.sleep(1)  # Adjust this if you want faster or slower updates

if __name__ == "__main__":
    main()
