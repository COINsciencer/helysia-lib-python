import os
from hexbytes import HexBytes
from web3 import Web3
from web3.middleware import geth_poa_middleware
import urllib
import json
from abis import abis

class Helysia:

    def __init__(self, speed=0):
        self.CHAIN = os.environ.get('CHAIN')
        if not self.CHAIN:
            raise NameError('CHAIN not found')
        self.INFURA = os.environ.get('INFURA')
        if not self.INFURA:
            raise NameError('INFURA not found')
        self.CONTRACT = os.environ.get('CONTRACT')
        if not self.CONTRACT:
            raise NameError('CONTRACT not found')
        self.DAI = os.environ.get('DAI')
        if not self.DAI:
            raise NameError('DAI not found')
        self.MARKET = os.environ.get('MARKET')
        if not self.MARKET:
            raise NameError('MARKET not found')
        self.AGENT = os.environ.get('AGENT')
        if not self.AGENT:
            raise NameError('AGENT not found')
        self.ACCOUNT = os.environ.get('ACCOUNT')
        if not self.ACCOUNT:
            raise NameError('ACCOUNT not found')
        self.PRIVATEKEY = os.environ.get('PRIVATEKEY')
        if not self.PRIVATEKEY:
            raise NameError('PRIVATEKEY not found')

        # init web3 provider (using Infura)
        self.web3 = Web3(Web3.HTTPProvider('https://{}.infura.io/v3/{}'.format(self.CHAIN, self.INFURA)))

        if self.CHAIN == 'rinkeby':
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        # init contracts
        abi = abis('erc20')
        self.tokenContract = self.web3.eth.contract(self.CONTRACT, abi=abi)
        self.daiContract = self.web3.eth.contract(self.DAI, abi=abi)
        abi = abis('marketmaker')
        self.marketMakerContract = self.web3.eth.contract(self.MARKET, abi=abi)
        # get token data
        self.tokenName = self.tokenContract.functions.name().call()
        self.tokenSymbol = self.tokenContract.functions.symbol().call()
        self.decimals = 10 ** self.tokenContract.functions.decimals().call()
        
        print('Token', self.tokenName)

    def balance(self, account='0x29532a9898cFBEF5DFa9F8f1D98a714D2d550b65'):
        # get token balance
        rawTokenBalance = self.tokenContract.functions.balanceOf(account).call()
        tokenBalance = rawTokenBalance // self.decimals
        # get ether balance
        ethBalance = self.web3.fromWei(self.web3.eth.getBalance(account), 'ether')
        return tokenBalance, ethBalance

    def tx(self, tx_hash='0x6569a94a84bcee90ee59472bd072ca463e57102fc3b9cf747f173086204e94b1'):    
        tx = self.web3.eth.waitForTransactionReceipt(tx_hash)
        if tx.logs:
            data = int(tx.logs[0].data, 16)
            _from = tx['from']
            _int = self.web3.toInt(tx.logs[0].topics[2])
            _hex = self.web3.toHex(_int)
            _to = self.web3.toChecksumAddress(_hex)
        else:
            tx = self.web3.eth.getTransaction(tx_hash)
            data = tx.value
            _from = tx['from']
            _to = tx['to']

        # get block timestamp
        block = self.web3.eth.getBlock(tx.blockNumber)
        timestamp = block.timestamp
        # get value
        value = self.web3.fromWei(data, 'ether')

        return tx, value, _from, _to, timestamp

    def sendEther(self, address='0xcfB35Ae84f6216EcdC75c5f56C6c4C4c9CA8D761', amount='0.01'):
        # get balance
        tokens, balance = self.balance(self.ACCOUNT)
        # check balance
        if float(balance) < float(amount):
            raise NameError('no-eth-funds')
        # get the amount in wei
        wei = self.web3.toWei(amount, 'ether')
        # get the nonce
        nonce = self.web3.eth.getTransactionCount(self.ACCOUNT)
        # create a raw transaction
        rawTransaction = {
            'gasPrice': hex(2000000000),
            'gas': hex(210000),
            'to': address,
            'value': hex(wei),
            'nonce': hex(nonce),
            'chainId': 4 if self.CHAIN == 'rinkeby' else 1
        }
        # sing the transaction
        signed_txn = self.web3.eth.account.signTransaction(
            rawTransaction,
            self.PRIVATEKEY,
        )
        # send the transaction
        tx_hash = HexBytes(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)).hex()
        return tx_hash

    def sendTokens(self, address='0xcfB35Ae84f6216EcdC75c5f56C6c4C4c9CA8D761', amount='1'):
        # get balance
        balance, eth = self.balance(self.ACCOUNT)
        # check balance
        if float(balance) < float(amount):
            raise NameError('no-token-funds')
        # get the amount in tokens
        tokens = float(amount) * self.decimals
        # get the nonce
        nonce = self.web3.eth.getTransactionCount(self.ACCOUNT)
        # create a raw transaction
        rawTransaction = {
            "from": self.ACCOUNT,
            'gasPrice': hex(2000000000),
            'gas': hex(210000),
            'to': self.CONTRACT,
            'value': '0x0',
            'nonce': hex(nonce),
            'data': self.tokenContract.encodeABI('transfer', [address, int(tokens)]),
            'chainId': 4 if self.CHAIN == 'rinkeby' else 1
        }
        # sing the transaction
        signed_txn = self.web3.eth.account.signTransaction(
            rawTransaction,
            self.PRIVATEKEY,
        )
        # send the transaction
        tx_hash = HexBytes(self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)).hex()
        return tx_hash

    def tokenPrice(self, amount=1):
        # get EURO/DOLAR rate
        response = urllib.request.urlopen('https://api.exchangeratesapi.io/latest')        
        data = response.read()
        encoding = response.info().get_content_charset('utf-8')
        rates = json.loads(data.decode(encoding))
        eurusd = rates['rates']['USD']

        # get PPM
        PPM = self.marketMakerContract.functions.PPM().call()
        # print(PPM)
        # overallBalance(reserve, collateral): balanceOf(reserve, collateral) + virtualBalance(collateral) + collateralsToBeClaimed(collateral)
        # balanceOf(reserve, collateral)
        reserveBalance = self.daiContract.functions.balanceOf(self.AGENT).call()
        # get the collateral token
        collateralToken = self.marketMakerContract.functions.getCollateralToken(self.DAI).call()
        # get the virtualBalance and the reserveRatio
        virtualSupply = collateralToken[1]
        # print(self.web3.fromWei(virtualSupply, 'ether'), "collateral.virtualSupply")
        virtualBalance = collateralToken[2]
        # print(self.web3.fromWei(virtualBalance, 'ether'), "collateral.virtualBalance")
        reserveRatio = collateralToken[3]
        # print(reserveRatio, "reserveRatio")
        collateral = self.web3.toWei(amount, 'ether')
        overallBalance = reserveBalance + virtualBalance + collateral
        # print(overallBalance, "overallBalance")
        
        # overallSupply(collateral): bondedToken.totalSupply + bondedToken.tokensToBeMinted + virtualSupply(collateral)
        totalSupply = self.tokenContract.functions.totalSupply().call()
        tokensToBeMinted = self.marketMakerContract.functions.tokensToBeMinted().call()
        # print(tokensToBeMinted, "tokensToBeMinted")
        overallSupply = totalSupply + tokensToBeMinted + virtualSupply
        # print(overallSupply, "overallSupply")
        
        n = PPM * overallBalance
        d = overallSupply * reserveRatio 
        
        tokenPrice = n / d

        # change to euros
        euros = tokenPrice / eurusd

        return euros, tokenPrice

    def price(self, amount=1):
        eur, usd = self.tokenPrice(1)
        tokens = float(amount) / eur
        
        return tokens


if __name__ == '__main__':
    try:
        helysia = Helysia()
    except NameError:
        raise
    while True:
        action = input('What should I do? [B]alance, [X]Transaction receipt, '
                       'token [P]rice, EU[R] price, send [E]ther, or send [T]okens? ').upper()
        if action not in 'BXPRET' or len(action) != 1:
            print('I don\'t know how to do that')
            continue
        if action == 'B':            
            account = input('What account? ')
            if account:
                token, eth = helysia.balance(account)
            else:
                token, eth = helysia.balance()
            print(token, 'tokens, ', eth, 'ETH')
        elif action == 'X':
            tx_hash = input('What tx hash? ')
            if tx_hash:
                tx, value, _from, _to, timestamp = helysia.tx(tx_hash)
            else:
                tx, value, _from, _to, timestamp = helysia.tx()
            # print('TX', tx)
            print('from', _from, 'to', _to, value, 'at', timestamp)
        elif action == 'E':
            account = input('To what account? ')
            amount = input('How much ETH? ')
            if account and amount:
                tx_hash = helysia.sendEther(account, amount)
            else:
                tx_hash = helysia.sendEther()
            print('https://{}.etherscan.io/tx/{}'.format(os.environ.get('CHAIN'), tx_hash))
        elif action == 'T':
            account = input('To what account? ')
            amount = input('How much Helysia? ')
            if account and amount:
                tx_hash = helysia.sendTokens(account, amount)
            else:
                tx_hash = helysia.sendTokens()
            print('https://{}.etherscan.io/tx/{}'.format(os.environ.get('CHAIN'), tx_hash))
        elif action == 'P':
            amount = input('How much Helysia (1)? ')
            if amount:
                euros, usd = helysia.tokenPrice(amount)
            else:
                euros, usd = helysia.tokenPrice()
            print(euros, 'EUR', usd, 'USD')
        elif action == 'R':
            amount = input('How much EUR (1)? ')
            if amount:
                tokens = helysia.price(amount)
            else:
                tokens = helysia.price()
            print(tokens)