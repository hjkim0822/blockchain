import Node
import threading
import genesis #p2p네트워크로 이동되는 모든 데이터는 genesis라고 가정
import time #Block에 기록되는 time_stamp는 time.time()으로부터 구해진다.
import hashlib
from fastecdsa import ecdsz, keys, curve, point



class BlockchainNode(Node.Node):
    class Transaction:
        def __init__(self, consumer: str, perconsumer: str, item_history: str, digital_signature, public_key):
            ...
            consumer: 구매자의 URL
            preconsumer: 구매 예정자의 URL
            data: 구매자가 구매를 했을때의 data들...
            digital_signature: 구매자가 구매를 할 때 쓰는 결제 방법
            public_key: 구매자의 공개키


            self.consumer=consumer
            self.preconsumer=preconsumer
            self.item_history=item_history
            self.digital_signature=digital_signature
            self.public_key=public_key

        def serialize(self):
            self.digital_signature=(str(self.digital_signature[0]),str(self.digital_signature[1]))
            self.public_key=(str(self.public_key.x),str(self.public_key.y))

        def deserialize(self):
            self.digital_signature=(int(self.digital_signature[0]),int(self.digital_signature[1]))
            self.public_key=point.Point(int(self.public_key[0]),int(self.public_key[1]))

    class Blockchain:

        class Block:

            def __init__(self, index: int, time_temp: float, prev_block_hash, transaction_list,nonce:int):

                index: 블록의 번호
                time_temp: 블록이 생성된 시간
                prev_block_hash: 이전 블록의 hash값
                transaction_list: 블록이 가지고 있는 거래들
                nonce: 채굴 과정에서 구한 정답

                self.index=index
                self.time_temp=time_temp
                self.prev_block_hash=prev_block_hash
                self.transaction_list=transaction_list
                self.nonce=nonce

           def get_hash_val(self):
                '''
                sha256을 이용해서 block의 hash값을 return
                '''
                merge_string = str(self.index) + str(self.time_stamp) + str(self.prev_block_hash) + str(self.transaction_list) + str(self.nonce)
                return hashlib.sha256(merge_string.encode()).hexdigest()
            
            def serialize(self):
                temp = ''
                for trans in self.transaction_list:
                    temp += trans +','
                temp = temp[0:-1]
                self.transaction_list = str(temp)
                
            def deserialize(self):
                temp=[]
                for trans in self.transaction_list.split(','):
                    temp.append(trans)

                self.transaction_list = temp
            def __init__(self):
                self.chain = []
                # Create the genesis block
                # 임의의 genesis block을 생성해서 추가해줘야 한다..!
                genesis_block = self.Block(0,0,0,[],0)
                self.append_block(genesis_block)
            def append_block(self,block: Block):
            
                self.chain.append(block)
            def __init__(self, host, port, callback=None):
                super(BlockchainNode, self).__init__(host, port, callback)
                self.blockchain = self.Blockchain()
                self.transaction_pool = []
                self.private_key = self.gen_private_key()
                self.public_key = self.gen_public_key(self.private_key)
                self.node_address = self.gen_node_address(self.public_key)
                self.miner = Mine(self)
                self.miner_count = 0

            def gen_keys(self):
                self.private_key = self.gen_private_key()
                self.public_key = self.gen_public_key(self.private_key)
                self.node_address = self.gen_node_address(self.public_key)
                return str(self.private_key)

            def gen_private_key(self):
                return keys.gen_private_key(curve.P256)

            def gen_public_key(self, private_key):
                return keys.get_public_key(private_key,curve.P256)

            def gen_node_address(self, public_key):
                
                string = str(public_key.x).encode() + str(public_key.y).encode()
                return hashlib.sha256(string).hexdigest()

          

            def gen_transaction(self, consumer: str, preconsumer: str, data: str):
                 
                ret_str = ""
                if self.get_unique_node_count() >= 5 and self.miner_count >= 2:
                    digital_signature = ecdsa.sign(sender + receiver + data, self.private_key)
                    new_transaction = self.Transaction(sender,receiver,data,digital_signature,self.public_key)
                    new_transaction.serialize()
                    jdata = json.dumps(new_transaction.__dict__)
                    jdata = json.loads(jdata)
                    jdata['Type'] = 'transaction'
                    new_transaction.deserialize()
                    self.transaction_pool.append(new_transaction.item_history)

                    self.sendAll(jdata)
                    return ret_str
                else:
                    ret_str = "Failed to generate transaction: "
                    if self.get_unique_node_count() < 5:
                        ret_str += "'Too few users in network' "
                    if self.miner_count < 2:
                        ret_str += "'Too few miners in network'"
                    print(ret_str)
                    return ret_str

            
            def is_valid_block(self, block: Blockchain.Block) -> bool:
                
                prev = self.blockchain.get_last_block
                if prev.get_hash_val() != block.prev_block_hash:
                print("prev.get_hash_val() != block.prev_block_hash")
                return (block.prev_block_hash == 0 or prev.get_hash_val() == block.prev_block_hash) and (block.get_hash_val() < LEVEL)
        
            def start_mining(self):
                if not self.miner.is_mining:
                    self.miner.start()
                    print("%s started mining" % self.node_address)
                    self.miner_count += 1
                    self.sendAll({'Type': 'new_miner'})

            def stop_mining(self):
                if self.miner.is_mining:
                    self.miner.stop_mining()
                    # self.miner.join()
                    print("%s stopped mining" % self.node_address)
                    self.miner_count -= 1
                    self.sendAll({'Type': 'retired_miner'})
        
            def get_unique_node_count(self):
                self.removeClosedConnections()
                allnodes = self.getAllNodes()
        
                unique_nodes = dict()
                uniq_count = 1
                for node in allnodes:
                    port = node.peerPort
                    host = node.peerHost
                    if port not in unique_nodes.keys():
                        unique_nodes[port] = [host]
                        uniq_count += 1
                    elif host not in unique_nodes[port]:
                        hosts = unique_nodes[port]
                        hosts.append(host)
                        unique_nodes[port] = hosts
                        uniq_count += 1
        
                return uniq_count
        
            def ask_for_mine_count(self):
                for node in self.nodesOut:
                    if not node.shouldTerminate:
                        self.sendToNode(node, {'Type': 'ask_mine_count', 'Address': (self.host, self.port)})
                        break
        
            def ask_for_transaction_pool(self):
                for node in self.nodesOut:
                    if not node.shouldTerminate:
                        self.sendToNode(node, {'Type': 'ask_transaction_pool', 'Address': (self.host, self.port)})
                        break
        
            def ask_for_blockchain(self):
                for node in self.nodesOut:
                    if not node.shouldTerminate:
                        self.sendToNode(node, {'Type': 'ask_chain', 'Address': (self.host, self.port)})
                        break
        
            def join_network(self, host, port):
                self.connectToNode(host, port)
                time.sleep(0.1)
                self.ask_for_mine_count()
                self.ask_for_transaction_pool()
                self.ask_for_blockchain()
                time.sleep(0.1)
        
       
