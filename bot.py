from web3 import Web3
import time

# Optimism RPC Endpoint
OPTIMISM_NODE_URL = "https://optimism-mainnet.infura.io/v3/9c7e70b4bf234955945ff87b8149926e"
web3 = Web3(Web3.HTTPProvider(OPTIMISM_NODE_URL))

# Check connection to Optimism node
if not web3.isConnected():
    raise ConnectionError("Unable to connect to Optimism node. Check your endpoint.")
print(f"Connected to Optimism node. Current block: {web3.eth.blockNumber}")

# Velodrome Router Address
VELODROME_ROUTER = web3.toChecksumAddress("0xa132DAB612dB5cB9fC9Ac426A0Cc215A3423F9c9")

# Router ABI (corrected with components)
ROUTER_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {
                "name": "routes",
                "type": "tuple[]",
                "components": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "stable", "type": "bool"}
                ]
            }
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI (minimal for decimals)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Initialize router contract
router_contract = web3.eth.contract(address=VELODROME_ROUTER, abi=ROUTER_ABI)
print("Router contract initialized successfully.")

# Token addresses (converted to checksum format)
VELO_TOKEN = web3.toChecksumAddress("0x3c8E4E3C171E230CD15396D48E3E6A272BA98C1E")  # VELO
USDC_TOKEN = web3.toChecksumAddress("0x7F5C764CBC14F9669B88837CA1490CCA17C31607")  # USDC
OP_TOKEN = web3.toChecksumAddress("0x4200000000000000000000000000000000000042")  # OP

# Define pairs with routes
TOKEN_PAIRS = {
    "VELO-OP": [{"from": VELO_TOKEN, "to": OP_TOKEN, "stable": False}],
    "USDC-OP": [{"from": USDC_TOKEN, "to": OP_TOKEN, "stable": False}],
    "VELO-USDC": [{"from": VELO_TOKEN, "to": USDC_TOKEN, "stable": False}]
}

# Cache decimals to avoid redundant calls
DECIMALS_CACHE = {}

# Function to fetch token decimals
def get_token_decimals(token_address):
    if token_address in DECIMALS_CACHE:
        return DECIMALS_CACHE[token_address]
    
    try:
        print(f"Fetching decimals for token: {token_address}")
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
        if not web3.eth.getCode(token_address):
            print(f"No contract code found at address: {token_address}")
            return 18  # Default to 18 if no contract code is found
        
        decimals = token_contract.functions.decimals().call()
        DECIMALS_CACHE[token_address] = decimals
        return decimals
    except Exception as e:
        print(f"Error fetching decimals for token {token_address}: {e}")
        return 18  # Default to 18 decimals if call fails

# Function to fetch rates using the router
def fetch_rate(pair_name, routes):
    try:
        # Get decimals for the input token
        input_token = routes[0]["from"]
        input_decimals = get_token_decimals(input_token)
        amount_in = 10**input_decimals  # 1 unit of input token
        
        # Convert routes to tuple format for Web3.py
        route_tuples = [(route["from"], route["to"], route["stable"]) for route in routes]

        # Debugging: Print parameters before calling
        print(f"Fetching rate for pair {pair_name} with amountIn: {amount_in}, routes: {route_tuples}")
        
        # Call getAmountsOut
        amounts_out = router_contract.functions.getAmountsOut(amount_in, route_tuples).call()
        print(f"Successfully fetched amountsOut: {amounts_out}")
        
        # Calculate rate (price)
        output_decimals = get_token_decimals(routes[-1]["to"])
        rate = (amounts_out[-1] / 10**output_decimals) / (amounts_out[0] / 10**input_decimals)
        
        return {
            "amountIn": amounts_out[0],
            "amountOut": amounts_out[-1],  # Final output amount in the path
            "rate": rate,
            "routes": route_tuples
        }
    except Exception as e:
        print(f"Error fetching rate for pair {pair_name}: {e}")
        return None

# Main loop to fetch rates every few seconds
def main():
    print("Starting real-time Velodrome price fetcher using getAmountsOut...")
    while True:
        print(f"Fetching rates at block {web3.eth.blockNumber}...")
        for pair_name, routes in TOKEN_PAIRS.items():
            data = fetch_rate(pair_name, routes)
            if data:
                print(f"Pair: {pair_name} | Rate: {data['rate']:.6f}")
            else:
                print(f"Failed to fetch rate for pair {pair_name}.")
        time.sleep(5)

if __name__ == "__main__":
    main()
