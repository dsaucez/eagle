# Inspired from https://docs.python.org/3/library/asyncio-protocol.html#examples
import argparse
import asyncio
import socket
import time
import uuid
import sys
import re

REGEX="(?=.*(seq=(\d*|\d+|\d+)))(?=.*(ts=(\d*\.\d+|\d+\.\d*|\d+)))(?=.*(id=(.*[0-9(a-f|A-F)]{8}-[0-9(a-f|A-F)]{4}-4[0-9(a-f|A-F)]{3}-[89ab][0-9(a-f|A-F)]{3}-[0-9(a-f|A-F)]{12})))"

def print_data(data, addr, now=None):
  tokens = re.split(REGEX, data.decode())
  _seq = tokens[2]
  _ts = float(tokens[4])
  _uuid = tokens[6]
  _ttl = 128

  if now is not None:
    delay = (now-_ts)*1000.0
  else:
    delay = -1

  print ("{size} bytes from {ip}: seq={seq} ttl={ttl} time={delay:.3f} ms".format(seq=_seq, size=len(data), ip=addr[0], ttl=_ttl, delay=delay))

# Server side
class EchoServerProtocol:
  def connection_made(self, transport):
    self.transport = transport

  def datagram_received(self, data, addr):
    message = data.decode()
    print_data(data, addr)
    self.transport.sendto(data, addr)


# Client side
class EchoClientProtocol:
  def __init__(self, loop, interval):
    self.message = "id={id} seq={seq} ts={ts:3f}"
    self.loop = loop
    self.interval = interval

    self.transport = None
    self.seq = 0
    self.uid = uuid.uuid4()

  async def send_request(self):
    data = self.message.format(id=self.uid, seq=self.seq, ts=time.perf_counter())
    self.transport.sendto(data.encode())
    self.seq = self.seq + 1

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
    print("Socket closed, stop the event loop")
    loop = asyncio.get_event_loop()
    loop.stop()

async def server(port, address="0.0.0.0"):
  print("Server listening on {address}:{port}".format(address=address, port=port))

  # Get a reference to the event loop as we plan to use
  # low-level APIs.
  loop = asyncio.get_running_loop()

  # One protocol instance will be created to serve all
  # client requests.
  transport, protocol = await loop.create_datagram_endpoint(
    lambda: EchoServerProtocol(),
    local_addr=(address, port))

  try:
    await loop.create_future()
  finally:
    transport.close()

def client(server, port, interval):
  loop = asyncio.get_event_loop()
  connect = loop.create_datagram_endpoint(
    lambda: EchoClientProtocol(loop, interval),
    remote_addr=(server, port))
  transport, protocol = loop.run_until_complete(connect)
  loop.run_forever()
  transport.close()
  loop.close()

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--port', dest='port', action='store', required=True, type=int)
  parser.add_argument('-a', '--address', dest='address', action='store')
  parser.add_argument('-i', '--interval', dest='interval', action='store', default=1, type=float)
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('-s', dest='server', action='store_true', help="Run in server mode")
  group.add_argument('-c', dest='client', action='store_true', help="Run  in client mode")
  args = parser.parse_args()

  if args.server:
    asyncio.run(server(port=args.port))

  if args.client:
    client(server=args.address, port=args.port, interval=args.interval)

if __name__ == '__main__':
  main()
