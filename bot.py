import time
from config import *
from erc20_utils import *
from abis import *
import math


from uni_math import *


# from telegram import Bot
import logging

# from telegram import Update


# Initialize the Telegram bot
# bot = Bot(token=TELEGRAM_BOT_TOKEN)

liquidity_positions = []


import requests

def send_telegram_message_synchronously(message):
    """
    Send a message to the Telegram chat synchronously using the HTTP API.
    
    :param message: The message to send.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an error for HTTP errors
        print(f"Telegram notification sent: {message}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def notify_liquidity_action(action, details):
    """
    Notify about liquidity actions using Telegram.

    :param action: The type of action (e.g., "Added", "Removed").
    :param details: Details of the action.
    """
    message = f"Liquidity {action}:\n{details}"
    send_telegram_message_synchronously(message)

# Function to manage liquidity


def calculate_ema(window, alpha):
    """
    Function to calculate the Exponential Moving Average (EMA) over a window of values.
    
    :param window: A deque containing the last N liquidity values.
    :param alpha: The smoothing factor (0 < alpha < 1).
    :return: The updated EMA value.
    """
    # Start with the first value in the window as the initial EMA
    ema = window[0]
    
    # Apply the formula to all points in the window
    for i in range(1, len(window)):
        ema = alpha * window[i] + (1 - alpha) * ema
    return ema


def manage_liquidity(pool_address):
    pool_contract = web3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=UNISWAP_POOL_ABI)
    
    ema_window = EMA_WINDOW  
    prev_ema = None  # Previous EMA value, starts as None
    current_ema = None
    ema_removed = False  # Flag to track if liquidity was removed based on EMA condition
    alpha = ALPHA  
    x_percent_threshold = X_PERCENT_THRESHOLD # Example threshold of 5% for EMA change detection

    while True:
        try:
            # Fetch the current tick and liquidity data from the pool
            slot0 = pool_contract.functions.slot0().call()
            current_tick = slot0[1]
            tick_spacing = pool_contract.functions.tickSpacing().call()

            # Fetch current liquidity in the pool
            liquidity = pool_contract.functions.liquidity().call()

            # Add current liquidity to the EMA window
            ema_window.append(liquidity)
            current_ema = prev_ema
            # Calculate the EMA at the start of each iteration, using the entire window
            prev_ema = calculate_ema(ema_window, alpha)

            # Fetch token addresses
            token0_address = pool_contract.functions.token0().call()
            token1_address = pool_contract.functions.token1().call()

            # Fetch wallet balances
            token0_balance = get_token_balance(token0_address, WALLET_ADDRESS)
            token1_balance = get_token_balance(token1_address, WALLET_ADDRESS)

            token0_balance = token0_balance / BALANCE_PERC
            token1_balance = token1_balance / BALANCE_PERC

            decimals0 = get_token_decimals(token0_address)
            decimals1 = get_token_decimals(token1_address)

            # Adjust for decimals in price calculation
            decimal_adjustment = 10 ** (decimals1 - decimals0)

            # Calculate price with adjustment for decimals
            price_token1_in_token0 = math.pow(1.0001, current_tick) / decimal_adjustment
            price_token0_in_token1 = decimal_adjustment / math.pow(1.0001, current_tick)

            print(f"Current Tick: {current_tick} | Token0 Balance to be used: {token0_balance/(10**decimals0)} | Token1 Balance to be used: {token1_balance/(10**decimals1)}")
            print(f"Price (Token1 in Token0): {price_token1_in_token0:.6f} | Price (Token0 in Token1): {price_token0_in_token1:.6f}")

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
            existing_token_id = 0
            for i in range(nft_count):
                # Get the token ID of the NFT
                token_id = position_manager.functions.tokenOfOwnerByIndex(wallet_address, i).call()

                # Fetch position details
                position = position_manager.functions.positions(token_id).call()
                nft_lower_tick = position[5]  # tickLower
                nft_upper_tick = position[6]  # tickUpper

                # Check if the NFT's tick range is in range
                if lower_tick <= nft_lower_tick and upper_tick >= nft_upper_tick:
                    if ((int)(position[7]) > 0):
                        print(f"NFT {token_id} is in range. No action needed.")
                        all_out_of_range = False
                        existing_token_id = token_id
                else:
                    remove_liquidity(token_id)

            # If all NFTs are out of range, add new liquidity
            if all_out_of_range:
                print("All positions are out of range. Adding new liquidity...")
                add_liquidity_call(pool_address, token0_address, token1_address, lower_tick, upper_tick, token0_balance, token1_balance, tick_spacing)
                pass
            elif (current_ema and prev_ema):
                ema_change_percentage = ((current_ema - prev_ema) / prev_ema) * 100

                # Calculate the EMA with the existing points in the window
                # Log the current liquidity and EMA
                print(f"Current Liquidity : {liquidity} | Current EMA: {prev_ema:.6f}")
                # Calculate percentage EMA change if previous EMA exists
                if current_ema is not None:
                    ema_change_percentage = ((current_ema - prev_ema) / prev_ema) * 100
                    # Log the EMA Change Percentage
                    print(f"EMA Change Percentage: {ema_change_percentage:.2f}%")

                # Check for significant EMA change
                if ema_change_percentage < -x_percent_threshold and not ema_removed:
                    # If EMA decreases by more than the threshold and liquidity is available, remove liquidity
                    print("EMA has decreased significantly. Removing liquidity...")
                    # Remove liquidity using the previous method
                    remove_liquidity(existing_token_id)
                    ema_removed = True
                elif ema_change_percentage > x_percent_threshold and ema_removed:
                    # If EMA increases by more than the threshold and liquidity was removed earlier, add liquidity back
                    print("EMA has increased significantly. Adding liquidity back...")
                    # Add liquidity using the previous method
                    add_liquidity_call(pool_address, token0_address, token1_address, lower_tick, upper_tick, token0_balance, token1_balance, tick_spacing)
                    ema_removed = False

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
            "gasPrice":20*web3.eth.gas_price, # web3.toWei(5, "gwei"),  # Static gas price for predictable fees
            "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS),
        })

        # Sign and send the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Remove liquidity transaction sent. Hash: {tx_hash.hex()}")

        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        try:
            notify_liquidity_action("Removed", f"Token ID: {token_id}, liquidity: {liquidity}")
        except Exception as e:
            logging.error(f"Error adding liquidity: {e}")
            notify_liquidity_action("Failed to Remove", f"Error: {str(e)}")

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
def add_liquidity_call(pool_address, token0_address, token1_address, lower_tick, upper_tick, token0_balance, token1_balance, tick_spacing):
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

        print("amount0Desired: ", int(token0_amount)/(10**token0_decimals))
        print("amount1Desired: ", int(token1_amount)/(10**token1_decimals))

        pool_fee = get_pool_fee(pool_address)
        # Build transaction to add liquidity
        tx = position_manager.functions.mint({
            "token0": token0_address,
            "token1": token1_address,
            # "fee": pool_fee,  # Replace with the pool fee tier
            "tickSpacing": tick_spacing,
            "tickLower": lower_tick,
            "tickUpper": upper_tick,
            "amount0Desired": int(token0_amount),
            "amount1Desired": int(token1_amount),
            "amount0Min": 0,
            "amount1Min": 0,
            "recipient": WALLET_ADDRESS,
            "deadline": int(time.time()) + deadline,  # Set a 5-minute deadline
            "sqrtPriceX96": 0
        }).build_transaction({
            "from": WALLET_ADDRESS,
            "gas": 600000,
            "gasPrice": 20*web3.eth.gas_price, # Web3.to_wei(5, 'gwei'),
            "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS)+2,
        })

        # Sign and send the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Add liquidity transaction sent: {tx_hash.hex()}")

        # Wait for transaction receipt and extract token ID
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        logs = receipt['logs']

        token_id = extract_token_id_from_transfer_event(logs)
        try:
            notify_liquidity_action("Added", f"Token ID: {token_id}, Amount0: {token0_amount}, Amount1: {token1_amount}")
        except Exception as e:
            logging.error(f"Error adding liquidity: {e}")
            notify_liquidity_action("Failed to Add", f"Error: {str(e)}")
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
            "gasPrice": 20 * web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(Web3.to_checksum_address(WALLET_ADDRESS)),
        })

        # Sign and send the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f"Collect transaction sent: {tx_hash.hex()}")

        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        try:
            notify_liquidity_action("Collected", f"Token ID: {token_id}")
        except Exception as e:
            logging.error(f"Error adding liquidity: {e}")
            notify_liquidity_action("Failed to Remove", f"Error: {str(e)}")

    except Exception as e:
        print(f"Error collecting tokens for token ID {token_id}: {e}")

# async def start(update: Update, context):
#     chat_id = update.effective_chat.id
#     print(f"Chat ID: {chat_id}")
#     await context.bot.send_message(chat_id=chat_id, text=f"Your Chat ID is: {chat_id}")


def main():
    print("Starting liquidity management bot...")
    for pool_name, pool_address in UNISWAP_POOLS.items():
        print(f"Monitoring pool: {pool_name}")

        manage_liquidity(pool_address)

if __name__ == "__main__":
    main()



