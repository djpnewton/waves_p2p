import json
import base64
import time
import struct
import os
import random
import hashlib

import base58
import axolotl_curve25519 as curve
import sha3
import pyblake2

CHAIN_ID = None

TYPES = dict(issue=3, transfer=4, reissue=5, setscript=13, sponsor=14)

DEFAULT_TX_FEE = 100000
DEFAULT_ASSET_FEE = 100000000
DEFAULT_SPONSOR_FEE = 100000000
DEFAULT_SCRIPT_FEE = 1000000

def throw_error(msg):
    raise Exception(msg)

def str2bytes(s):
    # warning this method is flawed with some input
    return s.encode("latin-1")

def sign(privkey, message):
    random64 = os.urandom(64)
    return base58.b58encode(curve.calculateSignature(random64, base58.b58decode(privkey), message))

def sha256(data):
    return hashlib.sha256(data).digest()

def waves_hash(data):
    hash1 = pyblake2.blake2b(data, digest_size=32).digest()
    hash2 = sha3.keccak_256(hash1).digest()
    return hash2

def generate_address(pubkey, chain_id):
    # convert input to bytes
    chain_id = str2bytes(chain_id)
    # decode base58 pubkey
    pubkey = base58.b58decode(pubkey)
    # create address
    address_version = bytes([1])
    address = address_version + chain_id + waves_hash(pubkey)[:20]
    checksum = waves_hash(address)[:4]
    # base58 encode pubkey
    address = base58.b58encode(address + checksum)
    return address

def waves_timestamp():
    return int(time.time() * 1000)

def json_dumps(obj):
    return json.dumps(obj, indent=4)

def transfer_asset_non_witness_bytes(pubkey, recipient, assetid, amount, attachment='', feeAsset='', fee=DEFAULT_TX_FEE, timestamp=0):
    if amount <= 0:
        msg = 'Amount must be > 0'
        throw_error(msg)
    else:
        if timestamp == 0:
            timestamp = waves_timestamp()
        sdata = b'\4' + \
            b'\2' + \
            base58.b58decode(pubkey) + \
            (b'\1' + base58.b58decode(assetid) if assetid else b'\0') + \
            (b'\1' + base58.b58decode(feeAsset) if feeAsset else b'\0') + \
            struct.pack(">Q", timestamp) + \
            struct.pack(">Q", amount) + \
            struct.pack(">Q", fee) + \
            base58.b58decode(recipient) + \
            struct.pack(">H", len(attachment)) + \
            str2bytes(attachment)
        return sdata

def transfer_asset_payload(address, pubkey, privkey, recipient, assetid, amount, attachment='', feeAsset='', fee=DEFAULT_TX_FEE, timestamp=0):
    sdata = transfer_asset_non_witness_bytes(pubkey, recipient, assetid, amount, attachment, feeAsset, fee, timestamp)

    signature = ""
    if privkey:
        signature = sign(privkey, sdata)
    data = json_dumps({
        "type": 4,
        "version": 2,
        "senderPublicKey": pubkey,
        "recipient": recipient,
        "assetId": (assetid if assetid else ""),
        "feeAssetId": (feeAsset if feeAsset else ""),
        "amount": amount,
        "fee": fee,
        "timestamp": timestamp,
        "attachment": base58.b58encode(str2bytes(attachment)),
        "proofs": [
            signature
        ]
    })

    return data

def issue_asset_non_witness_bytes(pubkey, name, description, quantity, script=None, decimals=2, reissuable=True, fee=DEFAULT_ASSET_FEE, timestamp=0):
    if len(name) < 4 or len(name) > 16:
        msg = 'Asset name must be between 4 and 16 characters long'
        throw_error(msg)
    else:
        # it looks like script can always be 'None' (might be a bug)
        if script:
            rawScript = base64.b64decode(script)
            scriptLength = len(rawScript)
        if timestamp == 0:
            timestamp = waves_timestamp()
        sdata = b'\3' + \
            b'\2' + \
            str2bytes(str(CHAIN_ID)) + \
            base58.b58decode(pubkey) + \
            struct.pack(">H", len(name)) + \
            str2bytes(name) + \
            struct.pack(">H", len(description)) + \
            str2bytes(description) + \
            struct.pack(">Q", quantity) + \
            struct.pack(">B", decimals) + \
            (b'\1' if reissuable else b'\0') + \
            struct.pack(">Q", fee) + \
            struct.pack(">Q", timestamp) + \
            (b'\1' + struct.pack(">H", scriptLength) + rawScript if script else b'\0')
        return sdata


def issue_asset_payload(address, pubkey, privkey, name, description, quantity, script=None, decimals=2, reissuable=True, fee=DEFAULT_ASSET_FEE, timestamp=0):
    sdata = issue_asset_non_witness_bytes(pubkey, name, description, quantity, script, decimals, reissuable, fee, timestamp)

    signature = ""
    if privkey:
        signature = sign(privkey, sdata)
    data = json_dumps({
        "type": 3,
        "version": 2,
        "senderPublicKey": pubkey,
        "name": name,
        "description": description,
        "quantity": quantity,
        "decimals": decimals,
        "reissuable": reissuable,
        "fee": fee,
        "timestamp": timestamp,
        "proofs": [
            signature
        ]
    })

    return data

def reissue_asset_non_witness_bytes(pubkey, assetid, quantity, reissuable=False, fee=DEFAULT_TX_FEE, timestamp=0):
    if timestamp == 0:
        timestamp = waves_timestamp()
    sdata = b'\5' + \
        b'\2' + \
        str2bytes(str(CHAIN_ID)) + \
        base58.b58decode(pubkey) + \
        base58.b58decode(assetid) + \
        struct.pack(">Q", quantity) + \
        (b'\1' if reissuable else b'\0') + \
        struct.pack(">Q",fee) + \
        struct.pack(">Q", timestamp)
    return sdata

def reissue_asset_payload(address, pubkey, privkey, assetid, quantity, reissuable=False, fee=DEFAULT_TX_FEE, timestamp=0):
    sdata = reissue_asset_non_witness_bytes(pubkey, assetid, quantity, reissuable, fee, timestamp)

    signature = ""
    if privkey:
        signature = sign(privkey, sdata)
    data = json_dumps({
        "type": 5,
        "version": 2,
        "senderPublicKey": pubkey,
        "assetId": assetid,
        "quantity": quantity,
        "timestamp": timestamp,
        "reissuable": reissuable,
        "fee": fee,
        "proofs": [
            signature
        ]
    })

    return data

def sponsor_non_witness_bytes(pubkey, assetId, minimalFeeInAssets, fee=DEFAULT_SPONSOR_FEE, timestamp=0):
    if timestamp == 0:
        timestamp = int(time.time() * 1000)
    sdata = b'\x0e' + \
        b'\1' + \
        base58.b58decode(pubkey) + \
        base58.b58decode(assetId) + \
        struct.pack(">Q", minimalFeeInAssets) + \
        struct.pack(">Q", fee) + \
        struct.pack(">Q", timestamp)
    return sdata

def sponsor_payload(address, pubkey, privkey, assetId, minimalFeeInAssets, fee=DEFAULT_SPONSOR_FEE, timestamp=0):
    sdata = sponsor_non_witness_bytes(pubkey, assetId, minimalFeeInAssets, fee, timestamp)

    signature = ""
    if privkey:
        signature = sign(privkey, sdata)

    data = json_dumps({
        "type": 14,
        "version": 1,
        "senderPublicKey": pubkey,
        "assetId": assetId,
        "fee": fee,
        "timestamp": timestamp,
        "minSponsoredAssetFee": minimalFeeInAssets,
        "proofs": [
            signature
        ]
    })

    return data

def set_script_non_witness_bytes(pubkey, script, fee=DEFAULT_SCRIPT_FEE, timestamp=0):
    if script:
        rawScript = base64.b64decode(script)
        scriptLength = len(rawScript)
    if timestamp == 0:
        timestamp = waves_timestamp()
    sdata = b'\x0d' + \
        b'\1' + \
        str2bytes(str(CHAIN_ID)) + \
        base58.b58decode(pubkey) + \
        (b'\1' + struct.pack(">H", scriptLength) + rawScript if script else b'\0') + \
        struct.pack(">Q", fee) + \
        struct.pack(">Q", timestamp)
    return sdata

def set_script_payload(address, pubkey, privkey, script, fee=DEFAULT_SCRIPT_FEE, timestamp=0):
    sdata = set_script_non_witness_bytes(pubkey, script, fee, timestamp)

    signature = ""
    if privkey:
        signature = sign(privkey, sdata)

    data = json_dumps({
        "type": 13,
        "version": 1,
        "senderPublicKey": pubkey,
        "fee": fee,
        "timestamp": timestamp,
        "script": ('base64:' + script if script else None),
        "proofs": [
            signature
        ]
    })

    return data

def tx_serialize(testnet, tx):
    print("testnet: {}".format(testnet))
    print("tx: {}".format(tx))

    global CHAIN_ID
    if testnet:
        CHAIN_ID = 'T'
    else:
        CHAIN_ID = 'W'

    # serialize
    type = tx["type"]
    if type == 4:
        print(":: transfer tx")
        data = transfer_asset_non_witness_bytes(tx["senderPublicKey"], tx["recipient"], tx["assetId"], \
            tx["amount"], tx["attachment"], tx["feeAssetId"], tx["fee"], tx["timestamp"])
    elif type == 3:
        print(":: issue tx")
        data = issue_asset_non_witness_bytes(tx["senderPublicKey"], tx["name"], tx["description"], \
            tx["quantity"], None, tx["decimals"], tx["reissuable"], tx["fee"], tx["timestamp"])
    elif type == 5:
        print(":: reissue tx")
        data = reissue_asset_non_witness_bytes(tx["senderPublicKey"], tx["assetId"], tx["quantity"], \
            tx["reissuable"], tx["fee"], tx["timestamp"])
    elif type == 14:
        print(":: sponsor tx")
        data = sponsor_non_witness_bytes(tx["senderPublicKey"], tx["assetId"], \
            tx["minSponsoredAssetFee"], tx["fee"], tx["timestamp"])
    elif type == 13:
        print(":: set script tx")
        data = set_script_non_witness_bytes(tx["senderPublicKey"], tx["script"], tx["fee"], \
            tx["timestamp"])
    else:
        return None

    return data

def post(host, api, data):
    return requests.post('%s%s' % (host, api), data=data, headers={'content-type': 'application/json'}).json()

def get(host, api):
    return requests.get('%s%s' % (host, api)).json()

def broadcast_tx(host, data):
    return post(host, "/transactions/broadcast", data)

def get_fee(host, default_fee, address, user_provided_fee):
    fee = default_fee
    if user_provided_fee:
        fee = user_provided_fee
    else:
        try:
            data = get(host, f"/addresses/scriptInfo/{address}")
            if "error" in data:
                throw_error(f"unable to check script fees on address ({address})")
            else:
                fee += data["extraFee"]
        except:
            throw_error(f"unable to check script fees on address ({address})")

    return fee
