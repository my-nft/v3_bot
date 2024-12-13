# from web3 import Web3
from datetime import datetime
import time
from config import *
from erc20_utils import *
from abis import *

from uni_math import *

liquidity_positions = []

BALANCE_PERC = 100 # USE 1 to add full balance

# Global variable to track initial liquidity addition
initial_liquidity_added = False

# Function to manage liquidity
def manage_liquidity(pool_address):
    pool_contract = web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=UNISWAP_POOL_ABI)

    while True:
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

        token0_balance = token0_balance/BALANCE_PERC
        token1_balance = token1_balance/BALANCE_PERC

        print(f"Current Tick: {current_tick} | Token0 Balance to be used: {token0_balance} | Token1 Balance to be used: {token1_balance}")

        lower_tick, upper_tick= calculate_ticks(current_tick, tick_spacing, TICKS_DOWN, TICKS_UP)
        
        print("lower tick: ", lower_tick)
        print("upper tick: ", upper_tick)

        # Handle initial liquidity addition
        global initial_liquidity_added
        if not initial_liquidity_added:
            print("No initial liquidity found. Adding initial liquidity...")
            add_liquidity_call(pool_address, token0_address, token1_address, lower_tick, upper_tick, token0_balance, token1_balance)
            initial_liquidity_added = True
        else:
            # Check if liquidity needs to be removed and re-added
            if liquidity_out_of_range(lower_tick, upper_tick, pool_contract):
                print("Liquidity out of range. Rebalancing...")

                # Remove liquidity
                remove_liquidity(pool_address, lower_tick, upper_tick)
                
                # Re-add liquidity
                add_liquidity_call(pool_address, lower_tick, upper_tick, token0_balance/100, token1_balance/100)
        
        time.sleep(5)  # Adjust as necessary


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
def remove_liquidity(liquidity_amount):
    """
    Remove liquidity for the most recent position.

    :param liquidity_amount: Amount of liquidity to remove.
    """
    if not liquidity_positions:
        print("No liquidity positions found.")
        return

    token_id = liquidity_positions.pop()  # Use the most recent token ID

    try:
        position_manager = web3.eth.contract(address=POSITION_MANAGER_ADDRESS, abi=POSITION_MANAGER_ABI)

        # Build transaction to decrease liquidity
        tx = position_manager.functions.decreaseLiquidity({
            "tokenId": token_id,
            "liquidity": liquidity_amount,
            "amount0Min": 0,
            "amount1Min": 0,
            "deadline": int(time.time()) + 300  # Set a 5-minute deadline
        }).build_transaction({
            "from": WALLET_ADDRESS,
            "gas": 500000,
            "gasPrice": 2*web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS),
        })

        # Sign and send the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Remove liquidity transaction sent: {tx_hash.hex()}")

    except Exception as e:
        print(f"Error removing liquidity: {e}")

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
        sqrt_price_x96 = slot0[0]
        tick_spacing = pool_contract.functions.tickSpacing().call()  # Fetch tick spacing
        print(f"Current sqrtPriceX96: {sqrt_price_x96} | Tick Spacing: {tick_spacing}")
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
        print(f"Pool Fee: {pool_fee}")

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
            "deadline": int(time.time()) + 3000  # Set a 5-minute deadline
        }).build_transaction({
            "from": WALLET_ADDRESS,
            "gas": 600000,
            "gasPrice": 2*web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS)+2,
        })

        # Sign and send the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Add liquidity transaction sent: {tx_hash.hex()}")

        # Wait for transaction receipt and extract token ID
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print("receipt: ", receipt)
        logs = receipt['logs']
        print("logs: ", logs)
        for log in logs:
            if log['address'].lower() == POSITION_MANAGER_ADDRESS.lower():
                data = web3.codec.decode(['uint256', 'uint128', 'uint256', 'uint256'], log['data'])
                token_id = data[0]  # The first element should be the token ID
                liquidity_positions.append(token_id)
                print(f"Liquidity position added with token ID: {token_id}")
                break

    except Exception as e:
        print(f"Error adding liquidity: {e}")

def main():
    print("Starting liquidity management bot...")
    for pool_name, pool_address in UNISWAP_POOLS.items():
        print(f"Monitoring pool: {pool_name}")
        manage_liquidity(pool_address)

if __name__ == "__main__":
    main()
