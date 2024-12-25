from web3 import Web3
from abis import *
from config import *

# Function to fetch balances
def get_token_balance(token_address, wallet_address):
    token_contract = web3.eth.contract(address=web3.to_checksum_address(token_address), abi=ERC20_ABI)
    balance = token_contract.functions.balanceOf(wallet_address).call()
    return balance 

# Cache to store token decimals
DECIMALS_CACHE = {}

def get_token_decimals(token_address):
    """
    Fetch the number of decimals for a given ERC-20 token.
    
    :param token_address: Address of the ERC-20 token.
    :return: Number of decimals for the token.
    """
    if token_address in DECIMALS_CACHE:
        return DECIMALS_CACHE[token_address]
    
    try:
        token_contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        decimals = token_contract.functions.decimals().call()
        DECIMALS_CACHE[token_address] = decimals
        return decimals
    except Exception as e:
        print(f"Error fetching decimals for token {token_address}: {e}")
        return 18  # Default to 18 decimals if the call fails
   
# Function to approve a single token
def approve_single_token(spender_address, token_address, amount, nonce_offset=0):
    """
    Approve the Nonfungible Position Manager to spend a single token.

    :param spender_address: Address of the Nonfungible Position Manager.
    :param token_address: Address of the token to approve.
    :param amount: Amount of the token to approve.
    :param nonce_offset: Offset for the transaction nonce.
    """
    try:
        token_contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        tx = token_contract.functions.approve(
            Web3.to_checksum_address(spender_address), amount
        ).build_transaction({
            "from": Web3.to_checksum_address(WALLET_ADDRESS),
            "gas": 100000,
            "gasPrice": 20*web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(Web3.to_checksum_address(WALLET_ADDRESS)) + nonce_offset
        })
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    except Exception as e:
        print(f"Error approving token {token_address}: {e}")

# Function to approve tokens
def approve_tokens(spender_address, token0_address, token1_address, token0_amount, token1_amount):
    """
    Approve the Nonfungible Position Manager to spend token0 and token1.

    :param spender_address: Address of the Nonfungible Position Manager.
    :param token0_address: Address of token0.
    :param token1_address: Address of token1.
    :param token0_amount: Amount of token0 to approve.
    :param token1_amount: Amount of token1 to approve.
    """
    # Approve token0
    approve_single_token(spender_address, token0_address, token0_amount, nonce_offset=0)

    # Approve token1
    approve_single_token(spender_address, token1_address, token1_amount, nonce_offset=1)
