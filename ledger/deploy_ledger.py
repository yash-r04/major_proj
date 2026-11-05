"""Deploy EnergyLedger to the chain in GANACHE_URL and save the address to ledger/deployment.json.

Usage:  python ledger/deploy_ledger.py          (Ganache running on http://127.0.0.1:7545)
"""
import json, os
from web3 import Web3

HERE = os.path.dirname(os.path.abspath(__file__))
url = os.environ.get("GANACHE_URL", "http://127.0.0.1:7545")

if url == "test":
    from web3 import EthereumTesterProvider
    w3 = Web3(EthereumTesterProvider())
else:
    w3 = Web3(Web3.HTTPProvider(url))
assert w3.is_connected(), f"No chain at {url}. Start Ganache first."

art = json.load(open(os.path.join(HERE, "EnergyLedger.json")))
key = os.environ.get("ASTRA_PRIVATE_KEY")
contract = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])

if key:
    acct = w3.eth.account.from_key(key).address
    tx = contract.constructor().build_transaction({"from": acct, "nonce": w3.eth.get_transaction_count(acct),
                                                    "gas": 1500000, "gasPrice": w3.eth.gas_price})
    signed = w3.eth.account.sign_transaction(tx, private_key=key)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)
else:
    acct = w3.eth.accounts[0]
    tx_hash = contract.constructor().transact({"from": acct})

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
json.dump({"address": receipt["contractAddress"], "deployer": acct, "chain_id": w3.eth.chain_id,
           "deploy_gas": receipt["gasUsed"]}, open(os.path.join(HERE, "deployment.json"), "w"), indent=1)
print("EnergyLedger deployed at", receipt["contractAddress"], "gas", receipt["gasUsed"])
