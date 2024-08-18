import pytest
from brownie import config, Contract, ZERO_ADDRESS, chain, interface, accounts
import requests


# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    pass


# set this for if we want to use tenderly or not; mostly helpful because with brownie.reverts fails in tenderly forks.
use_tenderly = False

# use this to set what chain we use. 1 for ETH, 250 for fantom, 10 optimism, 42161 arbitrum, 8453 base
chain_used = 8453


################################################## TENDERLY DEBUGGING ##################################################


# change autouse to True if we want to use this fork to help debug tests
# generally we don't need to use this anymore if we're using anvil for our RPC
@pytest.fixture(scope="session", autouse=use_tenderly)
def tenderly_fork(web3, chain):
    fork_base_url = "https://simulate.yearn.network/fork"
    payload = {"network_id": str(chain.id)}
    resp = requests.post(fork_base_url, headers={}, json=payload)
    fork_id = resp.json()["simulation_fork"]["id"]
    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    print(fork_rpc_url)
    tenderly_provider = web3.HTTPProvider(fork_rpc_url, {"timeout": 600})
    web3.provider = tenderly_provider
    print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")


################################################ UPDATE THINGS BELOW HERE ################################################

#################### FIXTURES BELOW NEED TO BE ADJUSTED FOR THIS REPO ####################


@pytest.fixture(scope="session")
def token():
    # this should be the address of the ERC-20 used by the strategy/vault
    token_address = "0x03FF264046b085450649A993Cdd65dCDD01A893e"  # pwBLT-pHAM
    yield interface.IVeloPoolV2(token_address)


# v2 aero/usdc pool: 0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d (liq here to swap fine)


@pytest.fixture(scope="function")
def whale(amount, token, gauge):
    # Totally in it for the tech
    # Update this with a large holder of your want token (the largest EOA holder of LP)
    whale = accounts.at(
        "0xa5d981BC0Bc57500ffEDb2674c597F14a3Cb68c1", force=True
    )  # 0xa5d981BC0Bc57500ffEDb2674c597F14a3Cb68c1, random EOA

    if token.balanceOf(whale) < 2 * amount:
        raise ValueError(
            "Our whale needs more funds. Find another whale or reduce your amount variable."
        )
    yield whale


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance
@pytest.fixture(scope="function")
def amount(token):
    amount = 60 * 10 ** token.decimals()  # 60 for pwBLT-pHAM
    yield amount


# since we do atomic swaps and not yswaps for velodrome V2, this is actually a VELO whale to make sure we have enough to swap
@pytest.fixture(scope="function")
def profit_whale(profit_amount, to_sweep, whale):
    # ideally not the same whale as the main whale, or else they will lose money
    profit_whale = accounts.at(
        "0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4", force=True
    )  # 0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4, AERO veNFT
    if to_sweep.balanceOf(profit_whale) < 5 * profit_amount:
        raise ValueError(
            "Our profit whale needs more funds. Find another whale or reduce your profit_amount variable."
        )
    yield profit_whale


@pytest.fixture(scope="function")
def profit_amount(token):
    profit_amount = 11 * 10**18
    yield profit_amount


# set address if already deployed, use ZERO_ADDRESS if not
@pytest.fixture(scope="session")
def vault_address():
    vault_address = ZERO_ADDRESS
    yield vault_address


# if our vault is pre-0.4.3, this will affect a few things
@pytest.fixture(scope="session")
def old_vault():
    old_vault = False
    yield old_vault


# this is the name we want to give our strategy
@pytest.fixture(scope="session")
def strategy_name():
    strategy_name = "StrategyVelodromeClonable"
    yield strategy_name


# this is the name of our strategy in the .sol file
@pytest.fixture(scope="session")
def contract_name(
    StrategyVelodromeFactoryClonable,
    which_strategy,
):
    contract_name = StrategyVelodromeFactoryClonable
    yield contract_name


# if our strategy is using ySwaps, then we need to donate profit to it from our profit whale
@pytest.fixture(scope="session")
def use_yswaps():
    use_yswaps = False
    yield use_yswaps


# whether or not a strategy is clonable. if true, don't forget to update what our cloning function is called in test_cloning.py
@pytest.fixture(scope="session")
def is_clonable():
    is_clonable = True
    yield is_clonable


# use this to test our strategy in case there are no profits
@pytest.fixture(scope="session")
def no_profit():
    no_profit = False
    yield no_profit


# use this when we might lose a few wei on conversions between want and another deposit token (like router strategies)
# generally this will always be true if no_profit is true, even for curve/convex since we can lose a wei converting
@pytest.fixture(scope="session")
def is_slippery(no_profit):
    is_slippery = False  # set this to true or false as needed
    if no_profit:
        is_slippery = True
    yield is_slippery


# use this to set the standard amount of time we sleep between harvests.
# generally 1 day, but can be less if dealing with smaller windows (oracles) or longer if we need to trigger weekly earnings.
@pytest.fixture(scope="session")
def sleep_time():
    hour = 3600

    # change this one right here
    hours_to_sleep = 12

    sleep_time = hour * hours_to_sleep
    yield sleep_time


#################### FIXTURES ABOVE NEED TO BE ADJUSTED FOR THIS REPO ####################

#################### FIXTURES BELOW SHOULDN'T NEED TO BE ADJUSTED FOR THIS REPO ####################


@pytest.fixture(scope="session")
def tests_using_tenderly():
    yes_or_no = use_tenderly
    yield yes_or_no


# by default, pytest uses decimals, but in solidity we use uints, so 10 actually equals 10 wei (1e-17 for most assets, or 1e-6 for USDC/USDT)
@pytest.fixture(scope="session")
def RELATIVE_APPROX(token):
    approx = 10
    print("Approx:", approx, "wei")
    yield approx


# use this to set various fixtures that differ by chain
if chain_used == 1:  # mainnet

    @pytest.fixture(scope="session")
    def gov():
        yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)

    @pytest.fixture(scope="session")
    def health_check():
        yield interface.IHealthCheck("0xddcea799ff1699e98edf118e0629a974df7df012")

    @pytest.fixture(scope="session")
    def base_fee_oracle():
        yield interface.IBaseFeeOracle("0xfeCA6895DcF50d6350ad0b5A8232CF657C316dA7")

    # set all of the following to SMS, just simpler
    @pytest.fixture(scope="session")
    def management():
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    @pytest.fixture(scope="session")
    def rewards(management):
        yield management

    @pytest.fixture(scope="session")
    def guardian(management):
        yield management

    @pytest.fixture(scope="session")
    def strategist(management):
        yield management

    @pytest.fixture(scope="session")
    def keeper(management):
        yield management

    @pytest.fixture(scope="session")
    def trade_factory():
        yield Contract("0xcADBA199F3AC26F67f660C89d43eB1820b7f7a3b")

    @pytest.fixture(scope="session")
    def keeper_wrapper():
        yield Contract("0x0D26E894C2371AB6D20d99A65E991775e3b5CAd7")

elif chain_used == 10:  # optimism

    @pytest.fixture(scope="session")
    def gov():
        yield accounts.at("0xF5d9D6133b698cE29567a90Ab35CfB874204B3A7", force=True)

    @pytest.fixture(scope="session")
    def health_check():
        yield interface.IHealthCheck("0x3d8F58774611676fd196D26149C71a9142C45296")

    @pytest.fixture(scope="session")
    def base_fee_oracle():
        yield interface.IBaseFeeOracle("0xbf4A735F123A9666574Ff32158ce2F7b7027De9A")

    # set all of the following to Scream Guardian MS
    @pytest.fixture(scope="session")
    def management():
        yield accounts.at("0xea3a15df68fCdBE44Fdb0DB675B2b3A14a148b26", force=True)

    @pytest.fixture(scope="session")
    def rewards(management):
        yield management

    @pytest.fixture(scope="session")
    def guardian(management):
        yield management

    @pytest.fixture(scope="session")
    def strategist(management):
        yield management

    @pytest.fixture(scope="session")
    def keeper(management):
        yield management

    @pytest.fixture(scope="session")
    def to_sweep():
        # token we can sweep out of strategy (use VELO v2)
        yield interface.IERC20("0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db")

    @pytest.fixture(scope="session")
    def keeper_wrapper(KeeperWrapper):
        yield KeeperWrapper.at("0x9Ce0115381f009E382acd52761127eFF61061482")

elif chain_used == 8453:  # base

    @pytest.fixture(scope="session")
    def gov():
        yield accounts.at("0xbfAABa9F56A39B814281D68d2Ad949e88D06b02E", force=True)

    @pytest.fixture(scope="session")
    def health_check():
        yield interface.IHealthCheck("0x8273217252254Ad7353f227aaEcd2b1C4A326Fa2")

    @pytest.fixture(scope="session")
    def base_fee_oracle():
        yield interface.IBaseFeeOracle("0x298Bd23E25C01440D68d4D2708bFf6A7E10a1db5")

    @pytest.fixture(scope="session")
    def management():
        yield accounts.at("0x01fE3347316b2223961B20689C65eaeA71348e93", force=True)

    @pytest.fixture(scope="session")
    def rewards(management):
        yield management

    @pytest.fixture(scope="session")
    def guardian(management):
        yield management

    @pytest.fixture(scope="session")
    def strategist(management):
        yield management

    @pytest.fixture(scope="session")
    def keeper(management):
        yield management

    @pytest.fixture(scope="session")
    def to_sweep():
        # token we can sweep out of strategy (use VELO v2)
        yield interface.IERC20("0x940181a94A35A4569E4529A3CDfB74e38FD98631")

    @pytest.fixture(scope="session")
    def to_sweep_whale():
        yield accounts.at("0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4", force=True)


#     @pytest.fixture(scope="session")
#     def keeper_wrapper(KeeperWrapper):
#         yield KeeperWrapper.at("0x9Ce0115381f009E382acd52761127eFF61061482")


@pytest.fixture(scope="function")
def vault(pm, gov, rewards, guardian, management, token, vault_address):
    if vault_address == ZERO_ADDRESS:
        Vault = pm(config["dependencies"][0]).Vault
        vault = guardian.deploy(Vault)
        vault.initialize(token, gov, rewards, "", "", guardian)
        vault.setDepositLimit(2**256 - 1, {"from": gov})
        vault.setManagement(management, {"from": gov})
    else:
        vault = interface.IVaultFactory045(vault_address)
    yield vault


#################### FIXTURES ABOVE SHOULDN'T NEED TO BE ADJUSTED FOR THIS REPO ####################

#################### FIXTURES BELOW LIKELY NEED TO BE ADJUSTED FOR THIS REPO ####################


# use this similarly to how we use use_yswaps
@pytest.fixture(scope="session")
def is_gmx():
    yield False


@pytest.fixture(scope="session")
def target():
    # whatever we want it to be—this is passed into our harvest function as a target
    yield 9


# this should be a strategy from a different vault to check during migration
@pytest.fixture(scope="session")
def other_strategy():
    yield Contract("0x321E9366a4Aaf40855713868710A306Ec665CA00")  # wBLT strategy


# replace the first value with the name of your strategy
@pytest.fixture(scope="function")
def strategy(
    strategist,
    keeper,
    vault,
    gov,
    management,
    health_check,
    contract_name,
    strategy_name,
    base_fee_oracle,
    vault_address,
    which_strategy,
    gauge,
    route0,
    route1,
):
    strategy = gov.deploy(
        contract_name,
        vault,
        gauge,
        route0,
        route1,
    )
    strategy.setKeeper(keeper, {"from": gov})

    # set our management fee to zero so it doesn't mess with our profit checking
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2**256 - 1, 0, {"from": gov})
    print("New Vault, Velo Strategy")
    chain.sleep(1)

    # this strategy needs to use the fee on transfer fxns
    strategy.setSwapRoutes(route0, route1, True, {"from": management})

    # turn our oracle into testing mode by setting the provider to 0x00, then forcing true
    strategy.setBaseFeeOracle(base_fee_oracle, {"from": management})
    base_fee_oracle.setBaseFeeProvider(
        ZERO_ADDRESS, {"from": base_fee_oracle.governance()}
    )
    base_fee_oracle.setManualBaseFeeBool(True, {"from": base_fee_oracle.governance()})
    assert strategy.isBaseFeeAcceptable() == True

    yield strategy


#################### FIXTURES ABOVE LIKELY NEED TO BE ADJUSTED FOR THIS REPO ####################

####################         PUT UNIQUE FIXTURES FOR THIS REPO BELOW         ####################


@pytest.fixture(scope="session")
def v1_pool_factory():
    yield "0x25CbdDb98b35ab1FF77413456B31EC81A6B6B746"  # not used by aero


@pytest.fixture(scope="session")
def v2_pool_factory():
    yield "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"  # aero factory


# route to swap from VELO v2 to USDC
@pytest.fixture(scope="session")
def route0(pham, usdc, pwblt, to_sweep, v2_pool_factory, v1_pool_factory):
    route0 = [
        (to_sweep.address, usdc, False, v2_pool_factory),
        (usdc, pwblt, False, v2_pool_factory),
        (pwblt, pham, False, v2_pool_factory),
    ]
    yield route0


# route to swap from VELO v2 to BLU (on v2)
@pytest.fixture(scope="session")
def route1(pham, usdc, pwblt, to_sweep, v2_pool_factory, v1_pool_factory):
    route1 = [
        (to_sweep.address, usdc, False, v2_pool_factory),
        (usdc, pwblt, False, v2_pool_factory),
    ]
    yield route1


@pytest.fixture(scope="session")
def usdbc():
    yield "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA"


@pytest.fixture(scope="session")
def usdc():
    yield "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


@pytest.fixture(scope="session")
def pwblt():
    yield "0x3Dd79d6BD927615787Cc95F2c7A77C9aC1AF26F4"


@pytest.fixture(scope="session")
def pham():
    yield "0x2C8D2FC58B80aCb3b307C165af8F3eE296e6A271"


@pytest.fixture(scope="session")
def dola():
    yield "0x4621b7A9c75199271F773Ebd9A499dbd165c3191"


# we don't use this, set it to 0 though since that's the index of our strategy
@pytest.fixture(scope="session")
def which_strategy():
    which_strategy = 1
    yield which_strategy


# gauge for the curve pool
@pytest.fixture(scope="session")
def gauge():
    gauge = "0x19b05F319aC12296CB073218E912D0816030548F"  # pHAM-pwBLT
    yield Contract(gauge)


# template vault just so we can create a template strategy for cloning
@pytest.fixture(scope="session")
def template_vault():
    template_vault = "0xc52229c6d30B1b2317F2838f7e0d9C65efeDc9aF"  # AERO-USDbC
    yield template_vault


# gauge for our template vault pool
@pytest.fixture(scope="session")
def template_gauge():
    template_gauge = "0x9a202c932453fB3d04003979B121E80e5A14eE7b"  # AERO-USDbC
    yield template_gauge


# route to swap from AERO to USDC
@pytest.fixture(scope="session")
def template_route0(usdbc, to_sweep, v2_pool_factory, v1_pool_factory):
    template_route0 = [
        (to_sweep.address, usdbc, False, v2_pool_factory),
    ]
    yield template_route0


# route to swap from VELO v2 to...itself
@pytest.fixture(scope="session")
def template_route1(usdc, to_sweep, v2_pool_factory, v1_pool_factory):
    template_route1 = []
    yield template_route1


@pytest.fixture(scope="session")
def random_route_1(usdbc, usdc, to_sweep, v2_pool_factory, v1_pool_factory):
    random_route_1 = [
        (to_sweep.address, usdc, False, v2_pool_factory),
        (usdc, usdbc, True, v1_pool_factory),
    ]
    yield random_route_1


@pytest.fixture(scope="session")
def random_route_2(usdbc, usdc, to_sweep, v2_pool_factory, v1_pool_factory):
    random_route_2 = [
        (usdbc, usdc, True, v1_pool_factory),
        (usdc, to_sweep.address, False, v2_pool_factory),
    ]
    yield random_route_2


@pytest.fixture(scope="function")
def velo_template(
    StrategyVelodromeFactoryClonable,
    template_vault,
    strategist,
    template_gauge,
    gov,
    template_route0,
    template_route1,
):
    # deploy our curve template
    velo_template = gov.deploy(
        StrategyVelodromeFactoryClonable,
        template_vault,
        template_gauge,
        template_route0,
        template_route1,
    )

    print("Velo Template deployed:", velo_template)

    yield velo_template


@pytest.fixture(scope="function")
def velo_global(
    VelodromeGlobal,
    new_registry,
    gov,
    velo_template,
):
    # deploy our factory
    velo_global = gov.deploy(
        VelodromeGlobal,
        new_registry,
        velo_template,
        gov,
    )

    print("Velodrome factory deployed:", velo_global)
    yield velo_global


@pytest.fixture(scope="session")
def new_registry():
    yield Contract("0xF3885eDe00171997BFadAa98E01E167B53a78Ec5")


################# USE THESE VARS FOR TESTING HOW OTHER LP TOKENS WOULD FUNCTION #################

################# STABLE POOL #################


# gauge for the curve pool
@pytest.fixture(scope="session")
def stable_gauge():
    stable_gauge = "0xCCff5627cd544b4cBb7d048139C1A6b6Bde67885"  # v2 USDC/DOLA
    yield interface.IVeloV2Gauge(stable_gauge)


@pytest.fixture(scope="session")
def stable_token():
    stable_token = "0xf213F2D02837012dC0236cC105061e121bB03e37"  # this should be the address of the ERC-20 used by the strategy/vault (USDC/DOLA LP)
    yield interface.IVeloPoolV2(stable_token)


# route to swap from AERO to DOLA
@pytest.fixture(scope="session")
def stable_route0(dola, usdc, to_sweep, v2_pool_factory, v1_pool_factory):
    stable_route0 = [
        (to_sweep.address, usdc, False, v2_pool_factory),
        (usdc, dola, True, v2_pool_factory),
    ]
    yield stable_route0


# route to swap from AERO to USDC
@pytest.fixture(scope="session")
def stable_route1(dola, usdc, to_sweep, v2_pool_factory, v1_pool_factory):
    # need to use v2 for USDC -> DOLA since we use v1 as our whale
    stable_route1 = [
        (to_sweep.address, usdc, False, v2_pool_factory),
    ]
    yield stable_route1


@pytest.fixture(scope="function")
def stable_whale(stable_amount, stable_token, stable_gauge):
    # Totally in it for the tech
    # Update this with a large holder of your want token (the largest EOA holder of LP)
    stable_whale = accounts.at(
        "0x33bcc72aa126a3258178822d2B8019AaCc966c93", force=True
    )  # 0x33bcc72aa126a3258178822d2B8019AaCc966c93, USDC/DOLA pool

    if stable_token.balanceOf(stable_whale) < 2 * stable_amount:
        raise ValueError(
            "Our whale needs more funds. Find another whale or reduce your amount variable."
        )
    yield stable_whale


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance
@pytest.fixture(scope="function")
def stable_amount(stable_token):
    stable_amount = (
        0.0001 * 10 ** stable_token.decimals()
    )  # 0.0001 for DOLA/USDC, total: 0.000501714971509605
    yield stable_amount


@pytest.fixture(scope="function")
def stable_profit_whale(stable_profit_amount, stable_token):
    # ideally not the same whale as the main whale, or else they will lose money
    profit_whale = accounts.at(
        "0x71AcF8CBf8C843a2dc88a6f3Ec6F93bbFeF3AD08", force=True
    )  # 0x71AcF8CBf8C843a2dc88a6f3Ec6F93bbFeF3AD08,
    if stable_token.balanceOf(profit_whale) < 5 * stable_profit_amount:
        raise ValueError(
            "Our profit whale needs more funds. Find another whale or reduce your profit_amount variable."
        )
    yield profit_whale


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance
@pytest.fixture(scope="function")
def stable_profit_amount(stable_token):
    stable_profit_amount = (
        0.0000005 * 10 ** stable_token.decimals()
    )  # for DOLA/USDC 0.000106393728851859 total
    yield stable_profit_amount


@pytest.fixture(scope="function")
def stable_vault(pm, gov, rewards, guardian, management, stable_token, vault_address):
    token = stable_token
    if vault_address == ZERO_ADDRESS:
        Vault = pm(config["dependencies"][0]).Vault
        stable_vault = guardian.deploy(Vault)
        stable_vault.initialize(token, gov, rewards, "", "", guardian)
        stable_vault.setDepositLimit(2**256 - 1, {"from": gov})
        stable_vault.setManagement(management, {"from": gov})
    else:
        stable_vault = interface.IVaultFactory045(vault_address)
    yield stable_vault


# replace the first value with the name of your strategy
@pytest.fixture(scope="function")
def stable_strategy(
    strategist,
    keeper,
    stable_vault,
    gov,
    management,
    health_check,
    contract_name,
    strategy_name,
    base_fee_oracle,
    vault_address,
    which_strategy,
    stable_gauge,
    stable_route0,
    stable_route1,
):
    vault = stable_vault
    strategy = gov.deploy(
        contract_name,
        vault,
        stable_gauge,
        stable_route0,
        stable_route1,
    )
    strategy.setKeeper(keeper, {"from": gov})

    # set our management fee to zero so it doesn't mess with our profit checking
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2**256 - 1, 0, {"from": gov})

    print("New Vault, Velo Strategy")
    chain.sleep(1)

    # turn our oracle into testing mode by setting the provider to 0x00, then forcing true
    strategy.setBaseFeeOracle(base_fee_oracle, {"from": management})
    base_fee_oracle.setBaseFeeProvider(
        ZERO_ADDRESS, {"from": base_fee_oracle.governance()}
    )
    base_fee_oracle.setManualBaseFeeBool(True, {"from": base_fee_oracle.governance()})
    assert strategy.isBaseFeeAcceptable() == True

    yield strategy


################# VELO POOL #################


# gauge for the curve pool
@pytest.fixture(scope="session")
def velo_gauge():
    velo_gauge = "0x4F09bAb2f0E15e2A078A227FE1537665F55b8360"  # USDC/AERO
    yield interface.IVeloV2Gauge(velo_gauge)


@pytest.fixture(scope="session")
def velo_token():
    velo_token = "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d"  # this should be the address of the ERC-20 used by the strategy/vault USDC/AERO
    yield interface.IVeloPoolV2(velo_token)


# route to swap from AERO v2 to USDC
@pytest.fixture(scope="session")
def velo_route0(dola, usdc, to_sweep, v2_pool_factory, v1_pool_factory):
    velo_route0 = [
        (to_sweep.address, usdc, False, v2_pool_factory),
    ]
    yield velo_route0


# route to swap from AERO
@pytest.fixture(scope="session")
def velo_route1(dola, usdc, to_sweep, v2_pool_factory, v1_pool_factory):
    # need to use v2 for USDC -> DOLA since we use v1 as our whale
    velo_route1 = []
    yield velo_route1


@pytest.fixture(scope="function")
def velo_whale(velo_amount, velo_token, velo_gauge):
    # Totally in it for the tech
    # Update this with a large holder of your want token (the largest EOA holder of LP)
    velo_whale = accounts.at(
        "0xc1342eE2B9d9E8f1B7A612131b69cf03261957E0", force=True
    )  # 0xc1342eE2B9d9E8f1B7A612131b69cf03261957E0, USDC/AERO

    if velo_token.balanceOf(velo_whale) < 2 * velo_amount:
        raise ValueError(
            "Our whale needs more funds. Find another whale or reduce your amount variable."
        )
    yield velo_whale


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance
@pytest.fixture(scope="function")
def velo_amount(velo_token):
    velo_amount = (
        0.00001 * 10 ** velo_token.decimals()
    )  # for AERO/USDC, total: 0.000122798730842673
    yield velo_amount


@pytest.fixture(scope="function")
def velo_profit_whale(velo_profit_amount, velo_token):
    # ideally not the same whale as the main whale, or else they will lose money
    profit_whale = accounts.at(
        "0x2ECd81E43C1F66185446F4af7DfEAa6AAE249f55", force=True
    )  # 0x2ECd81E43C1F66185446F4af7DfEAa6AAE249f55,
    if velo_token.balanceOf(profit_whale) < 5 * velo_profit_amount:
        raise ValueError(
            "Our profit whale needs more funds. Find another whale or reduce your profit_amount variable."
        )
    yield profit_whale


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance
@pytest.fixture(scope="function")
def velo_profit_amount(velo_token):
    velo_profit_amount = (
        0.00000005 * 10 ** velo_token.decimals()
    )  # for USDC/AERO, total: 0.000088530174954435
    yield velo_profit_amount


@pytest.fixture(scope="function")
def velo_vault(pm, gov, rewards, guardian, management, velo_token, vault_address):
    token = velo_token
    if vault_address == ZERO_ADDRESS:
        Vault = pm(config["dependencies"][0]).Vault
        velo_vault = guardian.deploy(Vault)
        velo_vault.initialize(token, gov, rewards, "", "", guardian)
        velo_vault.setDepositLimit(2**256 - 1, {"from": gov})
        velo_vault.setManagement(management, {"from": gov})
    else:
        velo_vault = interface.IVaultFactory045(vault_address)
    yield velo_vault


# replace the first value with the name of your strategy
@pytest.fixture(scope="function")
def velo_strategy(
    strategist,
    keeper,
    velo_vault,
    gov,
    management,
    health_check,
    contract_name,
    strategy_name,
    base_fee_oracle,
    vault_address,
    which_strategy,
    velo_gauge,
    velo_route0,
    velo_route1,
):
    vault = velo_vault
    strategy = gov.deploy(
        contract_name,
        vault,
        velo_gauge,
        velo_route0,
        velo_route1,
    )
    strategy.setKeeper(keeper, {"from": gov})

    # set our management fee to zero so it doesn't mess with our profit checking
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2**256 - 1, 0, {"from": gov})

    print("New Vault, Velo Strategy")
    chain.sleep(1)

    # turn our oracle into testing mode by setting the provider to 0x00, then forcing true
    strategy.setBaseFeeOracle(base_fee_oracle, {"from": management})
    base_fee_oracle.setBaseFeeProvider(
        ZERO_ADDRESS, {"from": base_fee_oracle.governance()}
    )
    base_fee_oracle.setManualBaseFeeBool(True, {"from": base_fee_oracle.governance()})
    assert strategy.isBaseFeeAcceptable() == True

    yield strategy
