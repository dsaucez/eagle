import socket
import time
import sys
import argparse

BUFSIZE=4096

def server(sock, port=8080):
  print ("Listening on UDP/{}".format(port))
  server_address = ('0.0.0.0', port)
  sock.bind(server_address)

  me = socket.gethostname().encode()
  while True:
    data, address = sock.recvfrom(BUFSIZE)
     
    if data:
      sent = sock.sendto(me, address)

def client(sock, server, port=8080):
  server_address = (server, port)
  sock.bind(('',0))

  me = socket.gethostname().encode()
  sock.settimeout(1)

  while True:
    sock.sendto(me, server_address)
    try:
      data, fromaddr = sock.recvfrom(BUFSIZE)
      print ('{} from {}'.format(data, fromaddr))
    except (socket.timeout):
        pass
    time.sleep(1)


def main():
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--port', dest='port', action='store', required=True, type=int)
  parser.add_argument('-a', '--address', dest='address', action='store')
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('-s', dest='server', action='store_true', help="Run in server mode")
  group.add_argument('-c', dest='client', action='store_true', help="Run  in client mode")
  args = parser.parse_args()

  if args.server:
    server(sock, args.port)

  if args.client:
    client(sock, server=args.address, port=args.port)

if __name__ == '__main__':
  main()
