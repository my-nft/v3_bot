from web3 import Web3
import time

# Ethereum node endpoint
ETH_NODE_URL = "https://optimism-mainnet.infura.io/v3/b6271a54103e430fbc6d2ec56ff98755"
web3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# Check connection to Ethereum node
if not web3.isConnected():
    raise ConnectionError("Unable to connect to Ethereum node. Check your endpoint.")

# Uniswap V3 pool addresses
UNISWAP_POOLS = {
    "USDC-WETH": "0x478946BcD4a5a22b316470F5486fAfb928C0bA25"
}

# ABI for Uniswap V3 pool
UNISWAP_POOL_ABI = [
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI (minimal for decimals and symbol)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Cache decimals and symbols to avoid redundant calls
DECIMALS_CACHE = {}
SYMBOLS_CACHE = {}

def get_token_decimals(token_address):
    """Fetch the decimals for a given token."""
    if token_address in DECIMALS_CACHE:
        return DECIMALS_CACHE[token_address]
    try:
        token_contract = web3.eth.contract(address=web3.toChecksumAddress(token_address), abi=ERC20_ABI)
        decimals = token_contract.functions.decimals().call()
        DECIMALS_CACHE[token_address] = decimals
        return decimals
    except Exception as e:
        print(f"Error fetching decimals for token {token_address}: {e}")
        return 18  # Default to 18 decimals if call fails

def get_token_symbol(token_address):
    """Fetch the symbol for a given token."""
    if token_address in SYMBOLS_CACHE:
        return SYMBOLS_CACHE[token_address]
    try:
        token_contract = web3.eth.contract(address=web3.toChecksumAddress(token_address), abi=ERC20_ABI)
        symbol = token_contract.functions.symbol().call()
        SYMBOLS_CACHE[token_address] = symbol
        return symbol
    except Exception as e:
        print(f"Error fetching symbol for token {token_address}: {e}")
        return token_address  # Fallback to address if symbol fetch fails

def fetch_price(pool_address):
    """Fetch the real-time price adjusted for token decimals."""
    try:
        pool_contract = web3.eth.contract(address=web3.toChecksumAddress(pool_address), abi=UNISWAP_POOL_ABI)
        
        # Fetch token0 and token1 addresses
        token0_address = pool_contract.functions.token0().call()
        token1_address = pool_contract.functions.token1().call()
        
        # Fetch token decimals
        token0_decimals = get_token_decimals(token0_address)
        token1_decimals = get_token_decimals(token1_address)

        # Fetch slot0 data
        slot0 = pool_contract.functions.slot0().call()
        sqrt_price_x96 = slot0[0]
        tick = slot0[1]

        # Calculate raw price
        price = (sqrt_price_x96 / (2 ** 96)) ** 2

        # Adjust for token decimals
        adjusted_price = price * (10 ** token0_decimals) / (10 ** token1_decimals)

        adjusted_price = 1 / adjusted_price

        # Fetch token symbols
        token0_symbol = get_token_symbol(token0_address)
        token1_symbol = get_token_symbol(token1_address)

        return {
            "sqrtPriceX96": sqrt_price_x96,
            "tick": tick,
            "price": adjusted_price,
            "token0_symbol": token0_symbol,
            "token1_symbol": token1_symbol
        }
    except Exception as e:
        print(f"Error fetching price for pool {pool_address}: {e}")
        return None

def main():
    print("Starting real-time Uniswap V3 price fetcher...")
    while True:
        print(f"Fetching prices at block {web3.eth.blockNumber}...")
        for pair, pool_address in UNISWAP_POOLS.items():
            data = fetch_price(pool_address)
            if data:
                print(f"Pair: {pair} | 1 {data['token0_symbol']} = {data['price']:.6f} {data['token1_symbol']}")
                print(f"Tick: {data['tick']} | sqrtPriceX96: {data['sqrtPriceX96']}")
            else:
                print(f"Failed to fetch data for pair {pair}.")
        print("-" * 50)
        time.sleep(5)  # Adjust this for frequency of updates

if __name__ == "__main__":
    main()
