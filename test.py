import Blockchain
import time
import random

port1 = random.randint(0000,9999)
port2 = random.randint(0000,9999)
port3 = random.randint(0000,9999)


print("person1", port1)
print("person2", port2)
print("person3", port3)



node1 = Blockchain.BlockchainNode('localhost', port1)
node2 = Blockchain.BlockchainNode('localhost', port2)
node3 = Blockchain.BlockchainNode('localhost', port3)


node1.start()
node2.start()
node3.start()


node1.join_network('localhost', port2)
node1.join_network('localhost', port3)


node2.start_mining()
node3.start_mining()



node2.stop_mining()
node3.stop_mining()

node1.stop()
node2.stop()
node3.stop()


node1.join()
node2.join()
node3.join()


print("All stopped")
