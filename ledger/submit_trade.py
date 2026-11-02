import json
from web3 import Web3

# Connect to local Ganache RPC Server
GANACHE_URL = "http://127.0.0.1:7545"
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

def log_trades_to_blockchain(cleared_trades: list):
    """
    Submits real transactions to local Ganache node to populate TRANSACTIONS & BLOCKS tabs.
    """
    if not w3.is_connected():
        print("[LEDGER WARN] Ganache local node not connected on http://127.0.0.1:7545! Skipping on-chain settlement.")
        return []

    # Use primary accounts from Ganache
    sender_account = w3.eth.accounts[0]
    receiver_account = w3.eth.accounts[1]
    
    tx_hashes = []

    for trade in cleared_trades:
        # Construct real transaction payload
        tx_payload = {
            'from': sender_account,
            'to': receiver_account,
            'value': w3.to_wei(0.0001, 'ether'),
            'gas': 200000,
            'gasPrice': w3.to_wei('20', 'gwei'),
            'data': w3.to_hex(text=json.dumps({
                "seller": trade["seller_id"],
                "buyer": trade["buyer_id"],
                "vol_kw": trade["volume_kw"],
                "price": trade["cleared_price"]
            }))
        }
        
        # Send transaction directly to Ganache
        tx_hash = w3.eth.send_transaction(tx_payload)
        tx_hash_hex = tx_hash.hex()
        tx_hashes.append(tx_hash_hex)
        print(f"[ON-CHAIN LEDGER] Trade Recorded: {trade['seller_id'].upper()} -> {trade['buyer_id'].upper()} | {trade['volume_kw']}kW @ ₹{trade['cleared_price']} | TxHash: {tx_hash_hex}")

    return tx_hashes

if __name__ == "__main__":
    sample_trades = [
        {"seller_id": "bob", "buyer_id": "alice", "volume_kw": 0.74, "cleared_price": 0.68, "total_cost": 0.50},
        {"seller_id": "bob", "buyer_id": "david", "volume_kw": 0.40, "cleared_price": 0.70, "total_cost": 0.28}
    ]
    print("--- Testing Real Smart Contract Ledger Broadcast ---")
    log_trades_to_blockchain(sample_trades)