"""
Writes cleared trades and penalties to the EnergyLedger contract.

Configuration (environment variables, all optional):
  GANACHE_URL      RPC endpoint, default http://127.0.0.1:7545   ("test" = in-memory test chain)
  ASTRA_PRIVATE_KEY  if set, transactions are signed locally with this key;
                     if not set, the first unlocked account (Ganache default) is used
  ASTRA_CONTRACT   contract address; otherwise read from ledger/deployment.json
"""
import json, os, threading
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
CONTRACT_ADDRESS = "0xYourDeployedContractAddressHere"

CONTRACT_ABI = json.loads('''[
    {
        "inputs": [
            {"internalType": "string", "name": "seller", "type": "string"},
            {"internalType": "string", "name": "buyer", "type": "string"},
            {"internalType": "uint256", "name": "volumeWh", "type": "uint256"},
            {"internalType": "uint256", "name": "pricePaise", "type": "uint256"},
            {"internalType": "uint256", "name": "slot", "type": "uint256"}
        ],
        "name": "recordTrade",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]''')

def log_trades_to_blockchain(cleared_trades, slot, sender_address, private_key):
    if not w3.is_connected():
        return []
    c = _state["contract"]
    out = []
    for t in cleared_trades:
        out.append(_send(c.functions.recordTrade(
            str(t["seller_id"]), str(t["buyer_id"]),
            int(round(t["volume_kwh"] * 1000)), int(round(t["price_inr"] * 100)), int(slot))))
    return out


    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    tx_hashes = []

    for trade in cleared_trades:
        vol_wh = int(trade["volume_kwh"] * 1000)
        price_paise = int(trade["price_inr"] * 100)
        nonce = w3.eth.get_transaction_count(sender_address)

        txn = contract.functions.recordTrade(
            str(trade["seller_id"]),
            str(trade["buyer_id"]),
            vol_wh,
            price_paise,
            int(slot)
        ).build_transaction({
            'chainId': 1337,
            'gas': 200000,
            'gasPrice': w3.to_wei('20', 'gwei'),
            'from': sender_address,
            'nonce': nonce,
        })

        signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_hashes.append(w3.to_hex(tx_hash))

    return tx_hashes
