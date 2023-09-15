import json
import os
import random
import string
import time
import hashlib
import struct
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from uuid import UUID

import requests
from eth_account import Account
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt

from eth_sandbox import get_shared_secret

HTTP_PORT = os.getenv("HTTP_PORT", "10088")
PUBLIC_IP = os.getenv("PUBLIC_IP", "127.0.0.1")

CHALLENGE_ID = os.getenv("CHALLENGE_ID", "challenge")
ENV = os.getenv("ENV", "dev")
FLAG = os.getenv("FLAG", "PCTF{placeholder}")

Account.enable_unaudited_hdwallet_features()


@dataclass
class Ticket:
    challenge_id: string
    team_id: string


@dataclass
class Action:
    name: str
    handler: Callable[[], int]


def sendTransaction(web3: Web3, tx: Dict) -> Optional[TxReceipt]:
    if "gas" not in tx:
        tx["gas"] = 10_000_000

    if "gasPrice" not in tx:
        tx["gasPrice"] = 0

    # web3.provider.make_request("anvil_impersonateAccount", [tx["from"]])
    txhash = web3.eth.sendTransaction(tx)
    # web3.provider.make_request("anvil_stopImpersonatingAccount", [tx["from"]])

    while True:
        try:
            rcpt = web3.eth.getTransactionReceipt(txhash)
            break
        except TransactionNotFound:
            time.sleep(0.1)

    if rcpt.status != 1:
        raise Exception("failed to send transaction")

    return rcpt


def new_launch_instance_action(
    do_deploy: Callable[[Web3, str], str],
):
    def action() -> int:
        def proof_of_work_okay(chall, solution, hardness):
            h = hashlib.sha256(chall.encode('ASCII') + struct.pack('<Q', solution)).hexdigest()
            return int(h, 16) < 2**256 / hardness

        def random_string(length = 10):
            characters = string.ascii_letters + string.digits
            return ''.join(random.choice(characters) for _ in range(length))

        hardness = 2**25

        challenge = random_string()
        print()
        print(' ======================================')
        print(' Proof of work code & solver')
        print(' You may run the following to solve:')
        print()
        print(' python3 ./pow.py {}_{}'.format(hardness, challenge))
        print(' ======================================')
        print()

        print('Proof of work challenge: {}_{}'.format(hardness, challenge))
        sys.stdout.write('Your response? ')
        sys.stdout.flush()
        sol = int(input())
        if not proof_of_work_okay(challenge, sol, hardness):
            print('Wrong :(')
            exit(1)

        print("please wait..")




        data = requests.post(
            f"http://127.0.0.1:{HTTP_PORT}/new",
            headers={
                "Authorization": f"Bearer {get_shared_secret()}",
                "Content-Type": "application/json",
            },
        ).json()

        if data["ok"] == False:
            print(data["message"])
            return 1

        uuid = data["uuid"]
        mnemonic = data["mnemonic"]
        
        deployer_acct = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/0")
        player_acct = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/1")

        web3 = Web3(Web3.HTTPProvider(
            f"http://127.0.0.1:{HTTP_PORT}/{uuid}",
            request_kwargs={
                "headers": {
                    "Authorization": f"Bearer {get_shared_secret()}",
                    "Content-Type": "application/json",
                },
            },
        ))

        setup_addr = do_deploy(web3, deployer_acct.address, player_acct.address)

        with open(f"/tmp/{uuid}", "w") as f:
            f.write(
                json.dumps(
                    {
                        "uuid": uuid,
                        "mnemonic": mnemonic,
                        "address": setup_addr,
                    }
                )
            )

        print()
        print(f"your private blockchain has been deployed")
        print(f"it will automatically terminate in 30 minutes")
        print(f"here's some useful information")
        print(f"uuid:           {uuid}")
        print(f"rpc endpoint:   http://{PUBLIC_IP}:{HTTP_PORT}/{uuid}")
        print(f"private key:    {player_acct.privateKey.hex()}")
        print(f"your address:   {player_acct.address}")
        print(f"setup contract: {setup_addr}")
        return 0

    return Action(name="launch new instance", handler=action)


def new_kill_instance_action():
    def action() -> int:
        uuid = check_uuid(input("uuid please: "))
        if not uuid:
            print("invalid uuid!")
            return 1
        

        data = requests.post(
            f"http://127.0.0.1:{HTTP_PORT}/kill",
            headers={
                "Authorization": f"Bearer {get_shared_secret()}",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                {
                    "uuid": uuid,
                }
            ),
        ).json()

        print(data["message"])
        return 1

    return Action(name="kill instance", handler=action)

def is_solved_checker(web3: Web3, addr: str) -> bool:
    result = web3.eth.call(
        {
            "to": addr,
            "data": web3.sha3(text="isSolved()")[:4],
        }
    )
    return int(result.hex(), 16) == 1

def check_uuid(uuid) -> bool:
    try:
        UUID(uuid)
        return uuid
    except (TypeError, ValueError):
        return None

def new_get_flag_action(
    checker: Callable[[Web3, str], bool] = is_solved_checker,
):
    def action() -> int:
        uuid = check_uuid(input("uuid please: "))
        if not uuid:
            print("invalid uuid!")
            return 1

        try:
            with open(f"/tmp/{uuid}", "r") as f:
                data = json.loads(f.read())
        except:
            print("bad uuid")
            return 1

        web3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{HTTP_PORT}/{data['uuid']}"))

        if not checker(web3, data['address']):
            print("are you *really* sure you solved it?")
            return 1

        print(FLAG)
        print('')
        print('for your safety, you should delete your instance now that you are done')
        return 0

    return Action(name="get flag", handler=action)


def run_launcher(actions: List[Action]):
    for i, action in enumerate(actions):
        print(f"{i+1} - {action.name}")

    action = int(input("action? ")) - 1
    if action < 0 or action >= len(actions):
        print("can you not")
        exit(1)

    exit(actions[action].handler())
