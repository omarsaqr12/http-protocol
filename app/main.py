import socket
import threading
import os
import time
import sys
import gzip

def handle_client(client_socket):
    # time.sleep(10)
    with client_socket:
            request_data = client_socket.recv(1024).decode("utf-8")
            print(request_data)
            # Check if the request starts with 'GET '


            if request_data.startswith('POST'):
                    dir=sys.argv[2]
                    os.chdir(dir)

                    # print(f"Current Directory: {dir}")
                    fil=request_data.split('files/')[-1].split(' ')[0]
                    cont=request_data.split('\r\n')[-1]
                    # List all files and directories in the current directory
                    print(fil)

                    with open(fil, "w") as fil:
                         fil.write(cont)  # Read the content of the file
                    response =f"HTTP/1.1 201 Created\r\n\r\n"
                    client_socket.sendall(response.encode('utf-8'))
            elif request_data.startswith('GET '):
                # print(request_data)
                z=request_data.find('/')
                if ('files' in request_data):
                    current_directory = os.getcwd()
                    dir=sys.argv[2]
                    os.chdir(dir)

                    # print(f"Current Directory: {dir}")
                    fil=request_data.split('files/')[-1].split(' ')[0]
                    # List all files and directories in the current directory
                    files = os.listdir(dir)
                    print(fil)
                    if fil in files:
                        with open(fil, "r") as file:
                            s = file.read()  # Read the content of the file

                            response =f"HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Length: {len(s)}\r\n\r\n{s}\r\n"
                        client_socket.sendall(response.encode('utf-8'))
                    else:
                        response = 'HTTP/1.1 404 Not Found\r\n\r\n'
                        client_socket.sendall(response.encode('utf-8'))                 
                # print(request_data[z+1:z+6])
                elif('user-agent'in request_data):
                    s = request_data.split('User-Agent: ')
                    if len(s) > 1:
                        # If 'User-Agent: ' exists, split the first part on '\r\n'
                        s = s[-1].split("\r\n")[0]
                    else:
                        # Handle the case where 'User-Agent: ' is not found
                        s = None
                    print(request_data)
                    if s:
                        response=f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(s)}\r\n\r\n{s}\r\n"
                    else:
                        response="HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n\r\n"
                    client_socket.sendall(response.encode('utf-8'))


                elif request_data[z+1:z+6]==" HTTP":
                    print("ni")
                    response="HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n\r\n"
                    client_socket.sendall(response.encode('utf-8'))
                elif ("echo/" in request_data):
                    ree=""
                    m=""
                    if 'Accept-Encoding'in request_data:
                        fil=request_data.split('Accept-Encoding: ')[-1]
                        print("fie",fil)
                        if("gzip" in fil):
                            ree="Content-Encoding: gzip\r\n"
                            s=request_data.split("echo/")[-1].split(' ')[0]
                            m=gzip.compress(s.encode('utf-8'))


                        else:
                         ree="\r\n"
                    s=request_data.split("echo/")[-1].split(' ')[0]
                    if m!='':
                        response=f"HTTP/1.1 200 OK\r\n{ree}Content-Type: text/plain\r\nContent-Length:{len(m)}\r\n\r\n"
                        # print(response)
                        client_socket.sendall(response.encode('utf-8') + m+"\r\n".encode('utf-8') if m else response.encode('utf-8'))
                    elif s:
                        response=f"HTTP/1.1 200 OK\r\n{ree}Content-Type: text/plain\r\nContent-Length:{len(s)}\r\n\r\n{s}\r\n"
                        # print(response)
                        client_socket.sendall(response.encode('utf-8'))
                else:
                    response = 'HTTP/1.1 404 Not Found\r\n\r\n'
                    client_socket.sendall(response.encode('utf-8'))                  
def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    # print("Logs from your program will appear here!")

    # Create a server socket
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    server_socket.listen(1)  
    while True:
        connection_socket, client_address = server_socket.accept()
        # Use the connection_socket to receive data
        client_thread = threading.Thread(target=handle_client, args=(connection_socket,))
        client_thread.start()

        

if __name__ == "__main__":
    main()