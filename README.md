# ICN-final-project
Final project for ICN Fall, 2021 at NTU

## Installation

Clone the repository with `https://github.com/Fiona1121/ICN-final-project.git`.

Having python>=3.6 installed, create a virtual environment by running `python -m venv venv` inside the cloned folder.

Activate the virtual environment (`source venv/bin/activate` on Linux, `.\venv\Scripts\activate` on Windows).

Install the requirements with `python -m pip install -r requirements.txt`.
## Usage
Server should be run first with 
```
python main_server.py
```
To specify server ip, port, or session ID
 ```
 $ python main_server.py -h
 usage: main_server.py [-h] [-i IPADDRESS] [-p PORT] [-s SESSIONID]

optional arguments:
  -h, --help            show this help message and exit
  -i IPADDRESS, --IPADDRESS IPADDRESS
                        The RTSP server IP address
  -p PORT, --PORT PORT  The port number
  -s SESSIONID, --SESSIONID SESSIONID
                        Session IDServer session ID
 ```