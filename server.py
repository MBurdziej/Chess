import socket
import threading

def handle_client(client_socket, address, clients):
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                print(f"Connection from {address} has been closed.")
                clients.remove(client_socket)
                client_socket.close()
                break

            print(f"Received message from {address}: {message}")
            broadcast(message, clients, client_socket)
        except Exception as e:
            print(f"Error handling client {address}: {e}")
            clients.remove(client_socket)
            client_socket.close()
            break

def broadcast(message, clients, sender_socket):
    for client in clients:
        if client != sender_socket:
            client.send(message.encode('utf-8'))

host = 'localhost'
port = 5555

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, port))
server_socket.listen(5)

print(f"Server is listening on {host}:{port}")
clients = []

while True:
    client_socket, address = server_socket.accept()
    clients.append(client_socket)
    print(f"Connection established with {address}")
    client_handler = threading.Thread(target=handle_client, args=(client_socket, address, clients))
    client_handler.start()
