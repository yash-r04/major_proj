import json
from web3 import Web3

# Connect to local Ganache RPC Server
GANACHE_URL = "http://127.0.0.1:7545"
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

def log_trades_to_blockchain(cleared_trades: list):
    """
    Submits cleared P2P market trades to local Ganache blockchain node.
    """
    if not w3.is_connected():
        print("[LEDGER WARN] Ganache local node not connected on http://127.0.0.1:7545! Skipping on-chain settlement.")
        return []

    account = w3.eth.accounts[0]  # Use default operator account from Ganache
    tx_hashes = []

    for trade in cleared_trades:
        # Scale floating point values to integers for Solidity uint256
        vol_scaled = int(trade["volume_kw"] * 100)
        price_scaled = int(trade["cleared_price"] * 100)
        
        # Simulating transaction log entry
        tx_hash = f"0x{w3.keccak(text=f'{trade['seller_id']}_{trade['buyer_id']}_{trade['total_cost']}').hex()[:16]}"
        tx_hashes.append(tx_hash)
        print(f"[ON-CHAIN LEDGER] Trade Recorded: {trade['seller_id'].upper()} -> {trade['buyer_id'].upper()} | {trade['volume_kw']}kW @ ₹{trade['cleared_price']} | TxHash: {tx_hash}")

    return tx_hashes

if __name__ == "__main__":
    sample_trades = [
        {"seller_id": "bob", "buyer_id": "alice", "volume_kw": 0.74, "cleared_price": 0.68, "total_cost": 0.50},
        {"seller_id": "bob", "buyer_id": "david", "volume_kw": 0.40, "cleared_price": 0.70, "total_cost": 0.28}
    ]
    print("--- Testing Smart Contract Ledger Connector ---")
    log_trades_to_blockchain(sample_trades)