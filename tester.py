# Inspired from https://docs.python.org/3/library/asyncio-protocol.html#examples
import argparse
import asyncio
import socket
import time
import uuid
import sys
import re

REGEX_CLIENT="(?=.*(seq=(\d*|\d+|\d+)))(?=.*(ts=(\d*\.\d+|\d+\.\d*|\d+)))(?=.*(id=(.*[0-9(a-f|A-F)]{8}-[0-9(a-f|A-F)]{4}-4[0-9(a-f|A-F)]{3}-[89ab][0-9(a-f|A-F)]{3}-[0-9(a-f|A-F)]{12})))"
REGEX_NEXT="next=((?:[0-9]{1,3}\.){3}[0-9]{1,3}):([0-9]{1,5})"
REGEX_RELAY="(?=.*({}))".format(REGEX_NEXT)

def print_data(data, now=None):
  tokens = re.split(REGEX_CLIENT, data.decode())
  _seq = tokens[2]
  _ts = float(tokens[4])
  _uuid = tokens[6]
  _ttl = 128

  if now is not None:
    delay = (now-_ts)*1000.0
  else:
    delay = -1

  print ("{size} bytes from {uuid}: seq={seq}".format(seq=_seq, size=len(data), uuid=_uuid))

# Server/Relay side
class ServerProtocol:
  def connection_made(self, transport):
    self.transport = transport

  def datagram_received(self, data, addr):
    message = data.decode()

    if "next=" in message:
      print("{} [relay]".format(message))
      tokens = re.split(REGEX_RELAY, message) 
      dst=tokens[2]
      port=int(tokens[3])
      message = re.sub(REGEX_NEXT,"", message)
      data=message.encode()
      self.transport.sendto(data, (dst,port))
    else:
      print (message)

  def connection_lost(self, exc):
    loop = asyncio.get_event_loop()
    loop.stop()

# Client side
class EchoClientProtocol:
  def __init__(self, loop, interval, packetsize, destination):
    self.message = "id={id} seq={seq} ts={ts:3f}" 
    if destination:
      self.message = self.message + " next={dst}"
    self.loop = loop
    self.interval = interval
    self.packetsize = packetsize
    self.destination = destination

    self.transport = None
    self.seq = 0
    self.uid = uuid.uuid4()

  async def send_request(self):
    message = self.message.format(id=self.uid, seq=self.seq, ts=time.perf_counter(), dst=self.destination)
    extra = self.packetsize - len(message) - 6
    message = "{} data={}".format(message, '0'*extra)
    data=message.encode()
    self.transport.sendto(data)
    self.seq = self.seq + 1
    print(message)

  async def send_requests(self):
    while True:
      self.loop.create_task(self.send_request())
      await asyncio.gather(
        asyncio.sleep(self.interval),
      )

  def connection_made(self, transport):
    self.transport = transport
    self.loop.create_task(self.send_requests())

  def datagram_received(self, data, addr):
    now = time.perf_counter()
    print_data(data, addr, now)

  def error_received(self, exc):
    print('Error received:', exc)

  def connection_lost(self, exc):
    loop = asyncio.get_event_loop()
    loop.stop()

async def server(port, address="0.0.0.0"):
  print("Server listening on {address}:{port}".format(address=address, port=port ))

  # Get a reference to the event loop as we plan to use
  # low-level APIs.
  loop = asyncio.get_running_loop()

  # One protocol instance will be created to serve all
  # client requests.
  transport, protocol = await loop.create_datagram_endpoint(
    lambda: ServerProtocol(),
    local_addr=(address, port))

  try:
    await loop.create_future()
  finally:
    transport.close()

def client(server, port, interval, packetsize, destination=None): 
  loop = asyncio.get_event_loop()
  try:
    connect = loop.create_datagram_endpoint(
      lambda: EchoClientProtocol(loop, interval, packetsize, destination),
      remote_addr=(server, port))
    transport, protocol = loop.run_until_complete(connect)
    loop.run_forever()
  except KeyboardInterrupt:
    pass
  finally:
    transport.close()
    loop.close()

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--port', dest='port', action='store', default=8080, type=int)
  parser.add_argument('-s', '--packetsize', dest='packetsize', action='store', type=int, default=64, choices=range(64,1500))
  parser.add_argument('-a', '--address', dest='address', default='0.0.0.0', action='store')
  parser.add_argument('-j', '--jump', dest='jump', action='store')
  parser.add_argument('-i', '--interval', dest='interval', action='store', default=1, type=float)
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('-l', dest='server', action='store_true', help="Run in server mode")
  group.add_argument('-c', dest='client', action='store_true', help="Run  in client mode")
  args = parser.parse_args()

  if args.server:
    try:
      asyncio.run(server(port=args.port, address=args.address))
    except KeyboardInterrupt:
      pass

  if args.client:
    srv = args.address
    port = args.port
    destination = None
    if args.jump:
       destination = "{}:{}".format(srv, port)
       srv, port=args.jump.split(":")
       port = int(port)

    client(server=srv, port=port, interval=args.interval, packetsize=args.packetsize, destination=destination)


if __name__ == '__main__':
  main()
