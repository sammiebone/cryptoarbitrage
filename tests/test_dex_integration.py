import pytest
import os
from src.dex_exchange import DEXExchange
from src.wallet_manager import WalletManager

# --- Test Setup Notes ---
# Running these tests requires a specific setup that cannot be achieved in this environment.
# A developer running these locally would need to:
# 1. Run a local mainnet fork using Hardhat or Ganache.
#    e.g., `npx hardhat node --fork https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID`
# 2. Set the RPC_URL in the test to point to this local fork (e.g., "http://127.0.0.1:8545").
# 3. Set the PRIVATE_KEY environment variable to a private key that has ETH on the forked mainnet.
#    (Hardhat provides a list of funded accounts when you start a node).

@pytest.mark.skip(reason="Requires local forked mainnet and funded private key")
@pytest.mark.asyncio
async def test_dex_get_price_and_execute_swap():
    """
    End-to-end test for DEX interaction.
    - Fetches a price from a DEX.
    - Executes a swap.
    - Checks that the balance changes appropriately.
    """
    # 1. Setup
    # Ensure the required environment variables are set
    assert os.environ.get("PRIVATE_KEY"), "Set PRIVATE_KEY env var"

    # Use the local fork's RPC URL
    RPC_URL = "http://127.0.0.1:8545"

    # Use the official Uniswap V2 Router on Mainnet
    ROUTER_ADDRESS = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    ROUTER_ABI = '[...]' # The ABI from config.yaml

    # Initialize WalletManager and DEXExchange
    wallet = WalletManager()
    dex = DEXExchange(
        name="uniswap_v2_test",
        rpc_url=RPC_URL,
        chain_id=1, # This would be 31337 for a default Hardhat fork
        router_address=ROUTER_ADDRESS,
        router_abi=ROUTER_ABI
    )

    # Define the assets for the swap (e.g., WETH to DAI)
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    dai_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"

    # 2. Get Price
    # This is a simplified check; the real bot uses get_order_book
    amounts_out = dex.router.functions.getAmountsOut(1 * 10**18, [weth_address, dai_address]).call()
    price = amounts_out[1] / (10**18)
    print(f"On-chain price for 1 WETH is {price} DAI")
    assert price > 0

    # 3. Execute Swap
    # Get pre-trade balances
    initial_dai_balance = dex.w3.eth.contract(address=dai_address, abi='[...]').functions.balanceOf(wallet.get_address()).call()

    # Execute the trade (selling 0.01 WETH for DAI)
    # A real test would require approving the token first.
    await dex.execute_trade("WETH/DAI", "sell", 0.01, price)

    # 4. Assert Balance Change
    # Get post-trade balances
    final_dai_balance = dex.w3.eth.contract(address=dai_address, abi='[...]').functions.balanceOf(wallet.get_address()).call()

    print(f"DAI balance changed from {initial_dai_balance} to {final_dai_balance}")
    assert final_dai_balance > initial_dai_balance
