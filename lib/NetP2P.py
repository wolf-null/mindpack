import socket
import threading
from lib.Null import Null

"""
Each socket  pair is opened to transmit a certain message.
Message is a bytes split into _n (unknown) parts of length _l
These parts are primed with _i bytes telling the number of parts
After the sending socket finished the transmission it closes the socket
Then the receiving socket gets b'' (a null byte string) which is for the transmission finish
The receiving socket, finally, sorts parts by the primers and reunites the message sent

The maximum number of parts is 2^i
Then the maximum message length is l * 2^i

Since this operations might be time-intensive 
   
"""

class NetReceiver(threading.Thread):
    def __init__(self, **kwargs):
        super(NetReceiver, self).__init__(**kwargs)

        self._address = kwargs['address']
        self._port = kwargs['port']
        self._socket = socket.socket()

        self._domain = kwargs['domain']  # type: Null

        self._inbound_connections = list()  # type: list[socket.socket]

    def run(self):
        print("[NetReceiver]: Bind")
        self._socket.bind((self._address, self._port))
        print("[NetReceiver]: Listen")
        self._socket.listen()
        self._socket.setblocking(False)




class NetP2P:
    """
    Each Proc. has
    - Single socket server for receiving signals
    - Multiple socket clients for transmitting signals to other Procs.

    TODO:
    - Just transmit something :)
    """

    def __init__(self, port=1664):
        self._server = socket.socket()
        self._server.bind(("127.0.0.1", 1664))
        self._server.listen(2)
        cn, ad = self._server.accept()
        # TODO:  Separate onto threads
        self._server.sendall(b'awooo')
        print(self._server.recv(1024))




p2p = NetP2P()
