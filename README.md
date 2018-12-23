# CmpE 487 Final Project: Screen Sharing in LAN
By **[Enes Koşar](https://github.com/eneskosr)** and **[Onur Kalınağaç](https://github.com/Onurklngc)**.

Python 3.6 applications developed to share your screen with multi clients on LAN and provide clients to manage your screen with mouse clicks.

# Platform
**Python 3.6** on **Ubuntu 16.04** and **Windows 10**.

# Dependencies
Depending on your platform and client&server usage selection, you will need the following python modules:

### Server
* Pillow -> To resize screenshots.
* mss -> To get screenshots.
* PyUserInput -> To perform click actions.

### Client
* pygame -> To display server screen and to capture mouse events.

You may install them at once by executing,

`pip3 install -r requirements.txt`

# Usage
### Server
To share your screen, use the **Server** application,

`python3 server.py`

* You can select the screen resolution for sharing by adding **-r** or **--resolution** optional parameter with one of the **360,480,720,1080** values.

e.g. `python3 server.py -r 720`

### Client
To view a computer where the Server application runs on it, use the **Client** application,

`python3 client.py`

* Left and right mouse clicks on the shared screen views on the client side shall be sent to the server computer and click actions shall be executed at that specific location.

* _F5_ button refreshes screen and _F11_ button toogles the Fullscreen Mode.

* If UDP broadcast is not permitted on your LAN, server shall not be discovered by client. In that case you can give the local ip address of the server you wish to connect manually and skip discovery procedure. Add **-i** or **--server_ip** optional parameter with local ip address of the server.

e.g. `python3 client.py -i 192.168.1.41`
