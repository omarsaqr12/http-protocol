
# Python HTTP Server

## Overview

This project implements a simple multi-threaded HTTP server in Python that can handle basic GET and POST requests. The server is designed to serve files, handle echo requests, and support gzip compression for responses.

## Features

- **GET Requests**:
  - Serves files from a specified directory.
  - Returns user-agent information if requested.
  - Echoes back text provided in the URL.
  - Supports gzip compression for echo responses.
  
- **POST Requests**:
  - Receives data and stores it in a file within a specified directory.

## File Structure

- **main.py**: The main script that sets up the server and handles incoming client requests.
  
## Getting Started

### Prerequisites

- Python 3.x
- Basic understanding of HTTP methods and Python threading.

### Installation

1. Clone the repository (if applicable):

   \`\`\`sh
   git clone https://github.com/yourusername/yourrepo.git
   cd yourrepo
   \`\`\`

2. Run the server:

   \`\`\`sh
   python3 main.py /path/to/directory
   \`\`\`

   Replace `/path/to/directory` with the directory you want the server to use for serving and storing files.

### Usage

- **GET /files/filename**: Retrieve the contents of `filename` from the specified directory.
- **POST /files/filename**: Store the content sent in the body of the request into `filename` in the specified directory.
- **GET /echo/sometext**: Returns the `sometext` provided in the URL. Supports gzip compression if requested via `Accept-Encoding`.
- **GET /user-agent**: Returns the User-Agent string of the client.

### Example

1. **GET Request to Retrieve a File**:
   
   \`\`\`
   GET /files/example.txt HTTP/1.1
   Host: localhost:4221
   \`\`\`

2. **POST Request to Store a File**:
   
   \`\`\`
   POST /files/example.txt HTTP/1.1
   Host: localhost:4221
   Content-Length: 11

   Hello World
   \`\`\`

### Contributing

If you'd like to contribute to this project, please fork the repository and submit a pull request.

### License

This project is licensed under the MIT License - see the `LICENSE` file for details.

