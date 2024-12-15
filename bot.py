# from web3 import Web3
from datetime import datetime
import time
from config import *
from erc20_utils import *
from abis import *

from uni_math import *

liquidity_positions = []

# Function to manage liquidity
def manage_liquidity(pool_address):
    pool_contract = web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=UNISWAP_POOL_ABI)

    while True:
        try:
            # Fetch the current tick
            slot0 = pool_contract.functions.slot0().call()
            current_tick = slot0[1]

            tick_spacing = pool_contract.functions.tickSpacing().call()
            
            # Fetch token addresses
            token0_address = pool_contract.functions.token0().call()
            token1_address = pool_contract.functions.token1().call()
            
            # Fetch wallet balances
            token0_balance = get_token_balance(token0_address, WALLET_ADDRESS)
            token1_balance = get_token_balance(token1_address, WALLET_ADDRESS)

            token0_balance = token0_balance / BALANCE_PERC
            token1_balance = token1_balance / BALANCE_PERC

            print(f"Current Tick: {current_tick} | Token0 Balance to be used: {token0_balance} | Token1 Balance to be used: {token1_balance}")

            # Calculate ticks based on current tick and tick spacing
            lower_tick, upper_tick = calculate_ticks(current_tick, tick_spacing, TICKS_DOWN, TICKS_UP)

            print("Lower tick: ", lower_tick)
            print("Upper tick: ", upper_tick)

            # Track if all NFTs are out of range
            all_out_of_range = True

            # Get the position manager contract
            position_manager = web3.eth.contract(address=POSITION_MANAGER_ADDRESS, abi=POSITION_MANAGER_ABI)
            wallet_address = Web3.to_checksum_address(WALLET_ADDRESS)

            # Get the total number of NFTs held by the wallet
            nft_count = position_manager.functions.balanceOf(wallet_address).call()

            for i in range(nft_count):
                # Get the token ID of the NFT
                token_id = position_manager.functions.tokenOfOwnerByIndex(wallet_address, i).call()

                # Fetch position details
                position = position_manager.functions.positions(token_id).call()
                nft_lower_tick = position[5]  # tickLower
                nft_upper_tick = position[6]  # tickUpper

                # Check if the NFT's tick range is in range
                if lower_tick <= nft_lower_tick and upper_tick >= nft_upper_tick:
                    print(f"NFT {token_id} is in range. No action needed.")
                    all_out_of_range = False
                else:
                    remove_liquidity(token_id)

            # If all NFTs are out of range, add new liquidity
            if all_out_of_range:
                print("All positions are out of range. Adding new liquidity...")
                add_liquidity_call(pool_address, token0_address, token1_address, lower_tick, upper_tick, token0_balance, token1_balance)

            time.sleep(5)  # Adjust as necessary
        except Exception as e:
            print(f"Error in manage_liquidity loop: {e}")
            time.sleep(10)  # Add delay to prevent spamming in case of errors


# Placeholder for liquidity out-of-range check
def liquidity_out_of_range(lower_tick, upper_tick, pool_contract):
    """Check if the current tick is out of the specified range."""
    try:
        slot0 = pool_contract.functions.slot0().call()
        current_tick = slot0[1]  # Fetch the current tick
        print(f"Current Tick: {current_tick}, Range: [{lower_tick}, {upper_tick}]")
        return not (lower_tick <= current_tick <= upper_tick)
    except Exception as e:
        print(f"Error checking liquidity range: {e}")
        return True  # Default to rebalance if check fails

# Placeholder for removing liquidity
def remove_liquidity(token_id):
    """
    Remove all liquidity for a given token ID.

    :param token_id: NFT token ID representing the liquidity position.
    """
    try:
        position_manager = web3.eth.contract(address=POSITION_MANAGER_ADDRESS, abi=POSITION_MANAGER_ABI)

        # Fetch position details using the token ID
        position = position_manager.functions.positions(token_id).call()
        liquidity = position[7]  # Index 7 corresponds to liquidity in the `positions` output

        if liquidity == 0:
            return

        # Build transaction to decrease liquidity
        tx = position_manager.functions.decreaseLiquidity({
            "tokenId": token_id,
            "liquidity": liquidity,
            "amount0Min": 0,
            "amount1Min": 0,
            "deadline": int(time.time()) + deadline # 5-minute deadline
        }).build_transaction({
            "from": WALLET_ADDRESS,
            "gas": 300000,  # Adjust gas limit as needed
            "gasPrice":2*web3.eth.gas_price, # web3.toWei(5, "gwei"),  # Static gas price for predictable fees
            "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS),
        })

        # Sign and send the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Remove liquidity transaction sent. Hash: {tx_hash.hex()}")

        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        # Collect tokens
        collect_tokens(token_id)

    except Exception as e:
        print(f"Error removing liquidity for token ID {token_id}: {e}")

def get_pool_fee(pool_address):
    """Fetch the fee tier for a given pool."""
    try:
        pool_contract = web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=UNISWAP_POOL_ABI)
        return pool_contract.functions.fee().call()
    except Exception as e:
        print(f"Error fetching fee for pool {pool_address}: {e}")
        return None

# Function to add liquidity
def add_liquidity_call(pool_address, token0_address, token1_address, lower_tick, upper_tick, token0_balance, token1_balance):
    """
    Add liquidity for the specified range and store the resulting token ID.

    :param pool_address: Address of the liquidity pool.
    :param token0_address: Address of token0.
    :param token1_address: Address of token1.
    :param lower_tick: Lower tick of the range.
    :param upper_tick: Upper tick of the range.
    :param token0_amount: Amount of token0 to add.
    :param token1_amount: Amount of token1 to add.
    """
    try:
        position_manager = web3.eth.contract(address=POSITION_MANAGER_ADDRESS, 
                                             abi=POSITION_MANAGER_ABI)
        pool_contract = web3.eth.contract(address=Web3.to_checksum_address(pool_address), 
                                          abi=UNISWAP_POOL_ABI)
        # Fetch current sqrtPriceX96
        slot0 = pool_contract.functions.slot0().call()

        token0_decimals = get_token_decimals(token0_address)
        token1_decimals = get_token_decimals(token1_address)
        
        # Calculate optimal amounts
        token0_amount, token1_amount = compute_amounts_and_liquidity(pool_contract, 
                                                                     token0_balance, 
                                                                     token1_balance, 
                                                                     lower_tick, 
                                                                     upper_tick, 
                                                                     token0_decimals, 
                                                                     token1_decimals)
        
        print(f"Adjusted Token0 Amount: {token0_amount} | Adjusted Token1 Amount: {token1_amount}")

        # Approve tokens
        approve_tokens(POSITION_MANAGER_ADDRESS, 
                       token0_address, 
                       token1_address, 
                       int(token0_amount), 
                       int(token1_amount))

        pool_fee = get_pool_fee(pool_address)
        # Build transaction to add liquidity
        tx = position_manager.functions.mint({
            "token0": token0_address,
            "token1": token1_address,
            "fee": pool_fee,  # Replace with the pool fee tier
            "tickLower": lower_tick,
            "tickUpper": upper_tick,
            "amount0Desired": int(token0_amount),
            "amount1Desired": int(token1_amount),
            "amount0Min": 0,
            "amount1Min": 0,
            "recipient": WALLET_ADDRESS,
            "deadline": int(time.time()) + deadline  # Set a 5-minute deadline
        }).build_transaction({
            "from": WALLET_ADDRESS,
            "gas": 600000,
            "gasPrice": 2*web3.eth.gas_price, # Web3.to_wei(5, 'gwei'),
            "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS)+2,
        })

        # Sign and send the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Add liquidity transaction sent: {tx_hash.hex()}")

        # Wait for transaction receipt and extract token ID
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        logs = receipt['logs']

    except Exception as e:
        print(f"Error adding liquidity: {e}")

def extract_token_id_from_transfer_event(logs):
    """
    Extract the NFT token ID from the Transfer event logs.

    :param logs: List of logs from the transaction receipt.
    :return: Extracted token ID or None if not found.
    """
    # Transfer event signature
    TRANSFER_EVENT_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    for log in logs:
        # Check if the log has topics and matches the Transfer event signature
        if (
            "topics" in log
            and len(log["topics"]) >= 4  # Ensure there are enough topics
            and log["topics"][0].hex() == TRANSFER_EVENT_SIGNATURE
        ):
            try:
                # Extract token ID from the third topic
                token_id = int(log["topics"][3].hex(), 16)
                return token_id
            except Exception as e:
                print(f"Error extracting token ID: {e}")
                return None

    print("Transfer event not found in logs or topics are insufficient.")
    return None

def collect_tokens(token_id):
    """
    Collect fees (tokens owed) for a given liquidity position (token ID).

    :param token_id: The unique ID of the liquidity position NFT.
    """
    try:
        # Create a contract instance for the Position Manager
        position_manager = web3.eth.contract(address=POSITION_MANAGER_ADDRESS, abi=POSITION_MANAGER_ABI)

        print("token_id: ", token_id)
        print("recipient: ", Web3.to_checksum_address(WALLET_ADDRESS))
        print("amount0Max: ", MAX_INT)
        print("amount1Max: ", MAX_INT)

        temp_list = [
            int(token_id), 
            Web3.to_checksum_address(WALLET_ADDRESS), 
            MAX_INT, 
            MAX_INT,
        ]

        collect_params = tuple(temp_list)

        tx = position_manager.functions.collect(collect_params).build_transaction({
            "from": Web3.to_checksum_address(WALLET_ADDRESS),
            "gas": 200000,  # Adjust as needed
            "gasPrice": 2 * web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(Web3.to_checksum_address(WALLET_ADDRESS)),
        })

        # Sign and send the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f"Collect transaction sent: {tx_hash.hex()}")

        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Collect transaction confirmed in block: {receipt['blockNumber']}")

    except Exception as e:
        print(f"Error collecting tokens for token ID {token_id}: {e}")


def main():
    print("Starting liquidity management bot...")
    for pool_name, pool_address in UNISWAP_POOLS.items():
        print(f"Monitoring pool: {pool_name}")

        manage_liquidity(pool_address)

if __name__ == "__main__":
    main()
