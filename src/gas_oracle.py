class GasFeeOracle:
    """
    Estimates the gas fee for a DEX transaction in USD.
    """
    # A swap on Uniswap V2 typically costs between 150k and 250k gas.
    # We'll use a conservative estimate.
    GAS_LIMIT_PER_SWAP = 250000

    def __init__(self, w3_instance, cex_for_pricing):
        self.w3 = w3_instance
        self.cex_for_pricing = cex_for_pricing
        self.native_asset = "ETH" # Assuming Ethereum

    async def estimate_swap_fee_in_usd(self):
        """
        Estimates the total cost of a DEX swap in USD.

        :return: The estimated fee in USD, or None if it cannot be determined.
        """
        try:
            # 1. Get current gas price in wei
            gas_price_wei = self.w3.eth.gas_price

            # 2. Calculate fee in native currency (ETH)
            fee_in_eth = self.w3.from_wei(gas_price_wei * self.GAS_LIMIT_PER_SWAP, 'ether')

            # 3. Get the current price of the native currency in USD
            native_price_ticker = await self.cex_for_pricing.get_ticker(f"{self.native_asset}/USD")
            native_price_usd = native_price_ticker['last']

            # 4. Calculate the final fee in USD
            fee_in_usd = float(fee_in_eth) * native_price_usd

            return fee_in_usd
        except Exception as e:
            print(f"Could not estimate gas fee: {e}")
            return None
