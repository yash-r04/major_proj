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

HERE = os.path.dirname(os.path.abspath(__file__))
_tx_lock = threading.Lock()     # one transaction at a time (keeps nonces and receipts consistent)
_state = {"w3": None, "contract": None, "sender": None, "key": None, "error": None}


def _connect():
    if _state["contract"] is not None:
        return True
    try:
        url = os.environ.get("GANACHE_URL", "http://127.0.0.1:7545")
        if url == "test":
            from web3 import EthereumTesterProvider
            w3 = Web3(EthereumTesterProvider())
        else:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 5}))
        if not w3.is_connected():
            _state["error"] = f"no chain at {url}"
            return False

        addr = os.environ.get("ASTRA_CONTRACT")
        dep = os.path.join(HERE, "deployment.json")
        if not addr and os.path.exists(dep):
            addr = json.load(open(dep))["address"]
        if not addr:
            _state["error"] = "contract not deployed (run ledger/deploy_ledger.py)"
            return False

        abi = json.load(open(os.path.join(HERE, "EnergyLedger.json")))["abi"]
        key = os.environ.get("ASTRA_PRIVATE_KEY")
        sender = w3.eth.account.from_key(key).address if key else w3.eth.accounts[0]
        _state.update(w3=w3, contract=w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi),
                      sender=sender, key=key, error=None)
        return True
    except Exception as exc:
        _state["error"] = str(exc)
        return False


def ledger_ready():
    return _connect()


def ledger_error():
    return _state["error"]


def _send(fn):
    """Send a contract call, signed locally if a key is configured, else via an unlocked account."""
    with _tx_lock:
        return _send_locked(fn)


def _send_locked(fn):
    w3, sender, key = _state["w3"], _state["sender"], _state["key"]
    if key:
        tx = fn.build_transaction({"from": sender, "nonce": w3.eth.get_transaction_count(sender),
                                   "gas": 300000, "gasPrice": w3.eth.gas_price})
        signed = w3.eth.account.sign_transaction(tx, private_key=key)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction   # name differs between versions
        tx_hash = w3.eth.send_raw_transaction(raw)
    else:
        tx_hash = fn.transact({"from": sender})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=20)
    return {"tx_hash": w3.to_hex(tx_hash), "block": receipt["blockNumber"], "gas_used": receipt["gasUsed"]}


def log_trades_to_blockchain(cleared_trades, slot):
    """cleared_trades: list of {seller_id, buyer_id, volume_kwh, price_inr}. Returns one dict per trade."""
    if not _connect():
        return []
    c = _state["contract"]
    out = []
    for t in cleared_trades:
        out.append(_send(c.functions.recordTrade(
            str(t["seller_id"]), str(t["buyer_id"]),
            int(round(t["volume_kwh"] * 1000)), int(round(t["price_inr"] * 100)), int(slot))))
    return out


def log_penalty(device_id, slot):
    if not _connect():
        return None
    return _send(_state["contract"].functions.recordPenalty(str(device_id), int(slot)))
