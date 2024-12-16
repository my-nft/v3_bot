
from web3 import Web3

ETH_NODE_URL = "https://sepolia.infura.io/v3/b6271a54103e430fbc6d2ec56ff98755"
web3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

POSITION_MANAGER_ADDRESS = "0x1238536071E1c677A632429e3655c799b22cDA52"  # Sepolia Position Manager

# Wallet private key (store securely, this is for testing only)
PRIVATE_KEY = ""  # Replace with your private key
WALLET_ADDRESS = web3.eth.account.from_key(PRIVATE_KEY).address

BALANCE_PERC = 100 # USE 1 to add full balance

MAX_INT = 1000000000000000000000000000000000

TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""  # Replace with your chat ID

deadline = 3000

# Uniswap V3 pool addresses
UNISWAP_POOLS = {
    "USDC-WETH": "0x3289680dD4d6C10bb19b899729cda5eEF58AEfF1"
}