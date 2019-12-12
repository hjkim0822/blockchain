import socket
import random
import hashlib
import threading
import json
import time


class Node(threading.Thread):

    def __init__(self, host, port, callback=None):
        super(Node, self).__init__()

        # IP and Port used for connn
        self.host = host
        self.port = port

        # Used for communicating back events
        self.callback = callback

        # Creates a unique ID for the node
        self.id = self.createUniqueID()

        # List of Inbound nodes
        self.nodesIn = []
        # List of Outbound nodes
        self.nodesOut = []
        # List of all known addresses in the network
        self.knownAddresses = []
        self.knownAddresses.append([host, port])  # add self to known addresses

        # Initialise the server
        self.sock = self.serverInit()

        self.shouldTerminate = False

        self.debug = False

    def setDebug(self, bool):
        self.debug = bool

    # function to create Unique ID for the node
    def createUniqueID(self):
        id = hashlib.md5()
        temp = self.host + str(self.port) + str(random.uniform(-999, 999))
        id.update(temp.encode('ascii'))  # use host+port+randomVal to create a unique id using RSA hash function
        return id.hexdigest()

    def dprint(self, message):
        if self.debug:
            print("Node.dprint: " + str(message))

    def eventNodeMessage(self, node, data):
        if self.callback != None:
            self.callback("NODE_MESSAGE", self, node, data)

    def eventConnectToNode(self, node):
        if self.callback != None:
            self.callback("NEW_CONNECTION", self, node)

    def getAllAddresses(self):
        allnodes = self.getAllNodes()
        addresses = []
        for node in allnodes:
            address = node.address
            addresses.append(address)
        return addresses

    def getAllNodes(self):
        allnodes = list(set(self.nodesOut).union(self.nodesIn)) # all nodes = union of inbound + outbound nodes
        return allnodes

    # Creates the TCP/IP socket for connections
    def serverInit(self):
        sock = socket.socket()  # create socket, by default uses AF_INET
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.port))  # '' used as host to mean all available interfaces
        sock.settimeout(15.0)  # 15 seconds
        sock.listen(10)  # backlog = 10, meaning 10 nodes can be waiting while establishing connection
        return sock

    # NodeConnection is just a basic class to create a connection node
    # if more functionality is needed we should override this in our blockchain implementation
    # and probably inherit NodeConnection in that implementation
    def newConnection(self, conn, address, callback):
        return NodeConnection(self, conn, address, callback)

    def removeClosedConnections(self):
        for node in self.nodesOut:
            if node.shouldTerminate:
                if self.callback != None:
                    self.callback("OUTBOUND_NODE_CLOSED", self, node, {})

                node.join()
                self.nodesOut.pop(self.nodesOut.index(node))

        for node in self.nodesIn:
            if node.shouldTerminate:
                if self.callback != None:
                    self.callback("INBOUND_NODE_CLOSED", self, node, {})

                node.join()
                self.nodesIn.pop(self.nodesIn.index(node))

    # Uses sendToNode to send data to all the other nodes in the network
    def sendAll(self, data):
        # Remove closed connections before trying to send messages to nodes
        self.removeClosedConnections()
        allnodes = self.getAllNodes()

        sent = dict()
        for node in allnodes:
            port = node.peerPort
            host = node.peerHost
            if port not in sent.keys():
                self.sendToNode(node, data)
                sent[port] = [host]
            elif host not in sent[port]:
                self.sendToNode(node, data)
                hosts = sent[port]
                hosts.append(host)
                sent[port] = hosts
            time.sleep(0.1)  # TODO : this is only for debugging
            #print("sent:", sent)  # TODO : this is only for debugging

    def sendToNode(self, node, data):
        type = None
        try:
            if 'Type' in data.keys():
                type = data['Type']
            node.send(data, type)

        except Exception as e:
            self.dprint("Node.sendToNode: Error while sending data to node (%s) - (%s)" %(node.id, e))

    # this function should get a list of addresses to connect to
    # addresses -> [[host, port], ... , [host, port]]
    def connectToNodes(self, addresses):
        for address in addresses:
            host = address[0]
            port = address[1]
            self.connectToNode(host, int(port))

    def connectToNode(self, host, port):
        if host == self.host and port == self.port:
            self.dprint("Node.connectToNode: Can't connect to yourself")
            return

        for node in self.nodesOut:
            if host == node.host and port == node.port:
                self.dprint(self.getName() + " Node.connectToNode: Already connected to this node. (%s, %s)" %(host, port))
                return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            clientThread = self.newConnection(sock, (host, port), self.callback)
            clientThread.start()
            self.nodesOut.append(clientThread)
            self.eventConnectToNode(clientThread)
            clientThread.sendKnownAddresses()  # send the nodes we know about to the new node in our network
            clientThread.sendPeerAddress()

            if self.callback != None:
                self.callback("CONNECTED_TO_NODE", self, clientThread, {})

            # Check if address is already in known addresses
            self.addKnownAddress(host, port)

        except Exception as e:
            self.dprint("Node.connectToNode: Error while connecting to node (%s, %s) - (%s)" %(host, port, e))

    def addKnownAddress(self, host, port):
        for address in self.knownAddresses:
            if host == address[0] and port == address[1]:
                self.dprint(
                    self.getName() + " Node.connectToNode: Already know this address. (%s, %s)" % (host, port))
                return
        self.knownAddresses.append([host, port])

    def disconnectFromNode(self, node):
        if node in self.nodesOut:
            node.send({"type": "message", "message": "Disconnect"})
            node.stop()
            node.join()
            self.nodesOut.pop(self.nodesOut.index(node))

    def stop(self):
        self.shouldTerminate = True

    # The part that is run when calling Node.start(), part of the threading library
    # Main loop for accepting incoming connections
    def run(self):
        while not self.shouldTerminate:  # while thread should not terminate
            try:  # establish incoming connections
                conn, address = self.sock.accept()
                clientThread = self.newConnection(conn, address, self.callback)
                clientThread.start()
                self.nodesIn.append(clientThread)
                clientThread.sendKnownAddresses()  # send the nodes we know about to the new node in our network

                if self.callback != None:
                    self.callback("NODE_CONNECTED", self, clientThread, {})
            except socket.timeout:
                pass
            except Exception as e:
                self.dprint(
                    "Node.run: Error while trying to establish a connection with node - " + self.getName() + " " + str(e)
                )

        self.dprint(self.getName() + " Number of connected outbound nodes: " + str(len(self.nodesOut)))
        self.dprint(self.getName() + " Number of connected inbound nodes: " + str(len(self.nodesIn)))

        for node in self.nodesIn:
            node.stop()

        for node in self.nodesOut:
            node.stop()

        for node in self.nodesIn:
            node.join()

        for node in self.nodesOut:
            node.join()
        self.dprint("Server Node " + self.getName() + " closed connection")


class NodeConnection(threading.Thread):
    def __init__(self, server, sock, address, callback):
        super(NodeConnection, self).__init__()

        self.address = address
        self.host = address[0]
        self.port = address[1]
        self.server = server
        self.sock = sock
        self.callback = callback
        self.shouldTerminate = False

        self.peerHost = address[0]
        self.peerPort = address[1]

        self.buffer = ""  # Used for messages between nodes

        self.id = self.createUniqueID()  # create ID

    # function to create Unique ID for the node
    def createUniqueID(self):
        id = hashlib.md5()
        temp = self.host + str(self.port) + str(random.uniform(-999, 999))
        id.update(temp.encode('ascii'))  # use host+port+randomVal to create a unique id using RSA hash function
        return id.hexdigest()

    def send(self, data, type=None):
        try:
            data['Sender'] = self.server.getName()
            data['Type'] = type
            message = json.dumps(data, separators=(',', ':')) + "-SEP"
            self.sock.sendall(message.encode('utf-8'))  # encode message into byte object and send
        except Exception as e:
            self.server.dprint("NodeConnection.send: Unexpected Error while sending message:" + str(e))

    # When a new connection have been established, we should send all of our known nodes
    def sendKnownAddresses(self):
        addresses = self.server.knownAddresses
        data = {"Addresses": addresses}
        self.send(data, "node_propagation")

    def sendPeerAddress(self):
        address = [self.server.host, self.server.port]
        data = {"Address": address}
        self.send(data, "peer_address")

    def stop(self):
        self.shouldTerminate = True

    # Main loop, run() is required by threading.Thread
    def run(self):
        self.sock.settimeout(15.0)

        while not self.shouldTerminate:
            message = dict()

            try:
                # https://docs.python.org/3/library/socket.html
                # Note: For best match with hardware and network realities,
                # the value of bufsize should be a relatively small power of 2, for example, 4096.
                message = self.sock.recv(4096)  # return value is a bytes object
                message = message.decode("utf-8")

            except Exception as e:
                # terminate Node if there is an issue with the connection
                # self.shouldTerminate =
                pass

            if message != "":
                if message == {}:  # an empty dict is received when peer node is closed
                    # self.shouldTerminate = True
                    continue

                # Get messages one by one using seperator -SEP
                self.buffer += message
                idx = self.buffer.find("-SEP")
                while idx > 0:
                    data = self.buffer[0:idx]
                    self.buffer = self.buffer[idx+4:]

                    try:
                        data = json.loads(data)

                    except Exception as e:
                        self.server.dprint("NodeConnection.run: message could not be parsed. "+str(data)+" "+str(e))

                    if data['Type'] == "node_propagation":
                        addresses = data['Addresses']
                        self.server.dprint("NodeConnection.run: Node Propagation " + str(addresses))
                        self.server.connectToNodes(addresses)

                    elif data['Type'] == "peer_address":
                        address = data['Address']
                        self.server.dprint("NodeConnection.run: Peer Address " + str(address))
                        self.peerHost = address[0]
                        self.peerPort = address[1]

                    else:
                        #print(data)
                        self.server.eventNodeMessage(self, data)  # invoke event, message received


                    idx = self.buffer.find("-SEP")
            time.sleep(0.1)

        self.sock.settimeout(None)
        self.sock.close()
        self.server.dprint("NodeConnection: Stopped")
