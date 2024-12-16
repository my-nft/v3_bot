MAX_TICK = 887272
FIXED_POINT_96_Q96 = 2**96
TICKS_UP = 3
TICKS_DOWN = 3

BITWISE_FACTORS = [
    0xfffcb933bd6fad37aa2d162d1a594001,
    0xfff97272373d413259a46990580e213a,
    0xfff2e50f5f656932ef12357cf3c7fdcc,
    0xffe5caca7e10e4e61c3624eaa0941cd0,
    0xffcb9843d60f6159c9db58835c926644,
    0xff973b41fa98c081472e6896dfb254c0,
    0xff2ea16466c96a3843ec78b326b52861,
    0xfe5dee046a99a2a811c461f1969c3053,
    0xfcbe86c7900a88aedcffc83b479aa3a4,
    0xf987a7253ac413176f2b074cf7815e54,
    0xf3392b0822b70005940c7a398e4b70f3,
    0xe7159475a2c29b7443b29c7fa6e889d9,
    0xd097f3bdfd2022b8845ad8f792aa5825,
    0xa9f746462d870fdf8a65dc1f90e061e5,
    0x70d869a156d2a1b890bb3df62baf32f7,
    0x31be135f97d08fd981231505542fcfa6,
    0x9aa508b5b7a84e1c677de54f3e99bc9,
    0x5d6af8dedb81196699c329225ee604,
    0x2216e584f5fa1ea926041bedfe98,
    0x48a170391f7dc42444e8fa2
]

def get_sqrt_price_x96(tick):
    """
    Calculate the sqrtPriceX96 at a specific tick.

    :param tick: The tick for which to calculate sqrtPriceX96.
    :return: sqrtPriceX96 as an integer.
    """
    if abs(tick) > MAX_TICK:
        raise ValueError(f"Tick {tick} exceeds MAX_TICK {MAX_TICK}")

    abs_tick = abs(tick)

    ratio = BITWISE_FACTORS[0] if (abs_tick & 0x1) != 0 else 0x100000000000000000000000000000000

    for i in range(1, len(BITWISE_FACTORS)):
        if (abs_tick & (1 << i)) != 0:
            ratio = (ratio * BITWISE_FACTORS[i]) >> 128

    if tick > 0:
        ratio = (1 << 256) // ratio

    # Adjust to Q96.96 format and round up
    sqrt_price_x96 = (ratio >> 32) + (1 if (ratio & ((1 << 32) - 1)) != 0 else 0)

    return sqrt_price_x96


def calculate_sqrt_ratios(lower_tick, upper_tick):
    """
    Calculate sqrt ratios for the given tick range.

    :param lower_tick: The lower tick of the range.
    :param upper_tick: The upper tick of the range.
    :return: (sqrt_ratio_a_x96, sqrt_ratio_b_x96)
    """
    sqrt_ratio_a_x96 = get_sqrt_price_x96(lower_tick)
    sqrt_ratio_b_x96 = get_sqrt_price_x96(upper_tick)

    return sqrt_ratio_a_x96, sqrt_ratio_b_x96

def get_liquidity_for_amount0(sqrt_ratio_a_x96, sqrt_ratio_b_x96, amount0):
    """
    Calculate liquidity based on token0 amount.
    
    :param sqrt_ratio_a_x96: sqrt price at tick A (lower or upper).
    :param sqrt_ratio_b_x96: sqrt price at tick B (lower or upper).
    :param amount0: Amount of token0.
    :return: Liquidity.
    """
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96
    intermediate = (sqrt_ratio_a_x96 * sqrt_ratio_b_x96) // (1 << 96)  # FullMath.mulDiv equivalent
    liquidity = (amount0 * intermediate) // (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
    return int(liquidity)


def get_liquidity_for_amount1(sqrt_ratio_a_x96, sqrt_ratio_b_x96, amount1):
    """
    Calculate liquidity based on token1 amount.
    
    :param sqrt_ratio_a_x96: sqrt price at tick A (lower or upper).
    :param sqrt_ratio_b_x96: sqrt price at tick B (lower or upper).
    :param amount1: Amount of token1.
    :return: Liquidity.
    """
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96
    liquidity = (amount1 * (1 << 96)) // (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
    return int(liquidity)

def get_token0_amount(sqrt_ratio_a_x96, sqrt_ratio_b_x96, liquidity):
    """
    Calculate the token0 amount required for the given liquidity and tick range.

    :param sqrt_ratio_a_x96: sqrtPriceX96 at the lower tick boundary.
    :param sqrt_ratio_b_x96: sqrtPriceX96 at the upper tick boundary.
    :param liquidity: Liquidity value.
    :return: Amount of token0.
    """
    try:
        print("args sqrt_ratio_a_x96: ", sqrt_ratio_a_x96)
        print("args sqrt_ratio_b_x96: ", sqrt_ratio_b_x96)
        print("args liquidity: ", liquidity)

        # Ensure sqrt_ratio_a_x96 is the smaller value
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        # Fixed-point resolution constant
        fixed_point_resolution = 2**96

        # Calculate numerator values
        numerator1 = liquidity * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
        numerator2 = sqrt_ratio_b_x96

        print("numerator1: ", numerator1)
        print("numerator2: ", numerator2)

        # Ensure sqrt_ratio_a_x96 is non-zero to avoid division by zero
        if sqrt_ratio_a_x96 == 0:
            raise ValueError("sqrt_ratio_a_x96 must be greater than 0 to avoid division by zero.")

        # Perform the calculation using Python's integer arithmetic
        amount0 = (numerator1 * fixed_point_resolution) // (numerator2 * sqrt_ratio_a_x96)

        print("amount0: ", amount0)
        return amount0
    except Exception as e:
        print(f"Error calculating token0 amount: {e}")
        return 0

def get_token1_amount(sqrt_ratio_a_x96, sqrt_ratio_b_x96, liquidity):
    """
    Calculate the token1 amount required for the given liquidity and tick range.

    :param sqrt_ratio_a_x96: sqrtPriceX96 at the lower tick boundary.
    :param sqrt_ratio_b_x96: sqrtPriceX96 at the upper tick boundary.
    :param liquidity: Liquidity value.
    :return: Amount of token1.
    """
    try:
        # Ensure sqrt_ratio_a_x96 is the smaller value
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        # Fixed-point resolution constant
        fixed_point_resolution = 2**96

        # Calculate the difference in sqrt ratios
        ratio_difference = sqrt_ratio_b_x96 - sqrt_ratio_a_x96

        # Perform the calculation for token1 amount
        amount1 = (liquidity * ratio_difference) // fixed_point_resolution

        return amount1
    except Exception as e:
        print(f"Error calculating token1 amount: {e}")
        return 0

def calculate_ticks(tick, tick_spacing, ticks_down, ticks_up):
    """
    Calculate the tick range for adding liquidity.

    :param tick: Current tick from the pool.
    :param tick_spacing: Tick spacing of the pool.
    :param ticks_down: Number of ticks below the floor tick for the lower boundary.
    :param ticks_up: Number of ticks above the ceiling tick for the upper boundary.
    :return: (tick_lower, tick_upper)
    """

    def floor_tick(tick, tick_spacing):
        """
        Calculate the floor tick.

        :param tick: Current tick.
        :param tick_spacing: Tick spacing of the pool.
        :return: Floor tick.
        """
        compressed = tick // tick_spacing
        if tick < 0 and tick % tick_spacing != 0:
            compressed -= 1
        return compressed * tick_spacing

    # Calculate the floor and ceiling ticks
    tick_floor = floor_tick(tick, tick_spacing)
    tick_ceil = tick_floor + tick_spacing

    # Calculate the lower and upper ticks
    tick_lower = tick_floor - ticks_down * tick_spacing
    tick_upper = tick_ceil + ticks_up * tick_spacing

    return tick_lower, tick_upper

def compute_amounts_and_liquidity(pool_contract, token0_balance, token1_balance, lower_tick, upper_tick, token0_decimals, token1_decimals):
    """
    Compute the token amounts and maximum liquidity that can be added for the given balances and tick range,
    considering token decimals.
    """
    
    try:
        
        # Fetch current slot0 data
        slot0 = pool_contract.functions.slot0().call()
        # sqrt_price_x96 = slot0[0]

        # Calculate sqrt price bounds for ticks
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = calculate_sqrt_ratios(lower_tick, upper_tick)

        # Ensure bounds are in ascending order
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        print("token0_amount: ", token0_balance)
        print("token1_amount: ", token1_balance)

        # Calculate liquidity based on token0
        liquidity_from_token0 = (
            (token0_balance * sqrt_ratio_a_x96 * sqrt_ratio_b_x96)
            // (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
        )

        # Calculate liquidity based on token1
        liquidity_from_token1 = (
            token1_balance * FIXED_POINT_96_Q96
        ) // (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)

        # Calculate possible liquidity for token0 and token1

        print("liquidity_from_token0: ", liquidity_from_token0)
        print("liquidity_from_token1: ", liquidity_from_token1)

        # Determine the maximum liquidity that can be added
        max_liquidity = min(liquidity_from_token0, liquidity_from_token1)
        
        # Compute adjusted token amounts based on max liquidity
        if max_liquidity > 0:
            # Adjusted token0 amount
            adjusted_token0_scaled = get_token0_amount(sqrt_ratio_a_x96, sqrt_ratio_b_x96, max_liquidity)

            # Adjusted token1 amount
            adjusted_token1_scaled = get_token1_amount(sqrt_ratio_a_x96, sqrt_ratio_b_x96, max_liquidity)
            print(f"adjusted_token0_scaled: {adjusted_token0_scaled} | adjusted_token1_scaled: {adjusted_token1_scaled}")
            # Scale adjusted amounts back to original token decimals
            adjusted_token0 = adjusted_token0_scaled # // (10 ** (18 - token0_decimals))
            adjusted_token1 = adjusted_token1_scaled # // (10 ** (18 - token1_decimals))

            # Ensure the adjusted amounts do not exceed the balances
            adjusted_token0 = min(adjusted_token0, token0_balance)
            adjusted_token1 = min(adjusted_token1, token1_balance)

            return adjusted_token0, adjusted_token1

        return 0, 0, 0
    except Exception as e:
        print(f"Error computing amounts and liquidity: {e}")
        return 0, 0, 0
