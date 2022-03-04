from flask import Flask,request     #request is a class in flask library to request data from end user
import json
import hashlib
import datetime

from urllib.parse import urlparse
import requests     #call an ip address of an node

class Blockchain:
    
    def __init__(self):
        self.chain = []

        self.transactions = []                  #array to hold pool of transactions
        self.create_block(proof=1,previous_hash='0')

        self.nodes = set()
        
    def create_block(self,proof,previous_hash):
        block = {'index':len(self.chain)+1,
                 'timestamp':str(datetime.datetime.now()),
                 'proof': proof,
                 'transactions':self.transactions,   #to take the trans request from array and add into block
                 'previous_hash':previous_hash}
        self.transactions = []             #to vacate the pool of transactions once mining done
        self.chain.append(block)
        return block

    def hash(self,block):
        encoded_block = json.dumps(block , sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self,previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof == False:
            hash_val = hashlib.sha256(str(new_proof**2-previous_proof**2).encode()).hexdigest()
            if hash_val[:4] == '0000':
                check_proof = True
            else:
                new_proof = new_proof + 1
        return new_proof

    def add_transaction(self,sender,receiver,amount):    #multiple job:-
        self.transactions.append({'sender':sender,
                                  'receiver':receiver,
                                  'amount':amount})         #adding trasaction into pool
        previous_block = self.get_previous_block()    
        return previous_block['index'] + 1              #returning possible index of next block
        

    def add_node(self,address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)


    #Validation of chain on any node
    def is_valid(self,chain):
        previous_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            current_block = chain[current_index]
            
            if current_block['previous_hash'] != self.hash(previous_block):
                return False
            
            previous_proof = previous_block['proof']
            current_proof = current_block['proof']
            hash_val = hashlib.sha256(str(current_proof**2-previous_proof**2).encode()).hexdigest()
            if hash_val[:4] != '0000':
                return False
            
            previous_block = current_block
            current_index += 1
        return True
        


    def update_chain(self):
        ntrk = self.nodes             #address of all nodes in the network
        max_length = len(self.chain)  #length of chain on current node
        longest_chain = None       #will remain null until any larger chain encountered

        for node in ntrk:            #to call each node address with the set of nodes
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                chain = response.json()['chain']
                length = len(chain)
                if length > max_length:     #max-length:-length on self node, length:-length on other node
                    if self.is_valid(chain):  #validating the chain on other nodes
                        longest_chain = chain
                        max_length = length
        if longest_chain:
            self.chain = longest_chain
            return True
        return False
        
        
app = Flask(__name__)

blk = Blockchain()


@app.route('/mine_block')
def mine_block():
    previous_block = blk.get_previous_block()

    previous_proof = previous_block['proof']
    proof = blk.proof_of_work(previous_proof)
    
    previous_hash = blk.hash(previous_block)
    block = blk.create_block(proof,previous_hash)
    response = {'Message':'Block is mined',
                'Block':block}
    return response

@app.route('/get_chain')
def get_chain():
    response = {'chain' : blk.chain}
    return response

@app.route('/add_transaction',methods=['POST'])
def add_transaction():
    json = request.get_json()                           #user entered value
    transaction_keys =['sender','receiver','amount']    #mandatory keys for transactions
    
    if not all(key in json for key in transaction_keys):   #validating the presence of required keys
        return 'Some Elements are missing',400
    
    index = blk.add_transaction(json['sender'] , json['receiver'] , json['amount'])  #adding transaction and accessing index of next block
    response = {'Message':f'Your Transactions are added into block index {index}'}   #Response for user
    return response


@app.route('/connect_nodes',methods=['POST'])
def connect_nodes():
    json = request.get_json()
    nodes = json.get('nodes')

    if nodes is None:
        return 'No Nodes',400
    for node in nodes:
        blk.add_node(node)

    response = {'Message':'All nodes are connected',
                'Total Nodes': list(blk.nodes)}
    return response

#Replace the chain
@app.route('/replace_chain')
def replace_chain():
    is_replaced = blk.update_chain()
    if is_replaced:
        response = {'Message' : 'You got the longest chain',
                    'New Chain' : blk.chain}
    else:
        response = {'Message' : 'No need to update',
                    'New Chain' : blk.chain}
    return response

@app.route('/is_valid')
def is_valid():
    status = blk.is_valid(blk.chain)
    if status:
        response = {'Message':'It is a valid chain'}
    else:
        response = {'Message':'It is not a valid chain'}
    return response
    
app.run(host='0.0.0.0',port=5002)
