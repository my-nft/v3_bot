from web3 import Web3
import collections

# ETH_NODE_URL = "https://sepolia.infura.io/v3/b6271a54103e430fbc6d2ec56ff98755" # sepolia
ETH_NODE_URL = "https://optimism-mainnet.infura.io/v3/9c7e70b4bf234955945ff87b8149926e" # optimism mainnet
web3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# POSITION_MANAGER_ADDRESS = "0x1238536071E1c677A632429e3655c799b22cDA52"  # Sepolia Position Manager
POSITION_MANAGER_ADDRESS = "0x416b433906b1B72FA758e166e239c43d68dC6F29"  # optmism
# op mainnet: 0x416b433906b1B72FA758e166e239c43d68dC6F29
# op testnet: 0xdA75cEf1C93078e8b736FCA5D5a30adb97C8957d
# Wallet private key (store securely, this is for testing only)
# PRIVATE_KEY = ""  # Replace with your private key
PRIVATE_KEY = "0x5c4a56b92650d36377f244860dce8045980e5ec8b47ca90eb4dc25264541b616" # Client key, op loaded
WALLET_ADDRESS = web3.eth.account.from_key(PRIVATE_KEY).address

BALANCE_PERC = 100 # USE 1 to add full balance

MAX_INT = 1000000000000000000000000000000000

TELEGRAM_BOT_TOKEN = "7854276420:AAECy2HwzVW0-Xgi1evj5fc8lGnHjk_L-2c"
TELEGRAM_CHAT_ID = "498172456"  # Replace with your chat ID

X_PERCENT_THRESHOLD = 20 # Example threshold of 20% for EMA change detection
ALPHA = 0.1 # Smoothing factor for EMA calculation
EMA_WINDOW = collections.deque(maxlen=20) # Stores the last 20 liquidity values

deadline = 3000

# Uniswap V3 pool addresses
UNISWAP_POOLS = {
    # "USDC-WETH": "0x3289680dD4d6C10bb19b899729cda5eEF58AEfF1"
   "USDC-WETH":  "0x478946BcD4a5a22b316470F5486fAfb928C0bA25" # op mainnet usdc-weth
}

