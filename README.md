# pstream

pstream is a server implementation for Apple's PhotoStream that supports iOS 5.1.1 and OS X 10.7 and 10.8. It is built on [Twisted](https://twistedmatrix.com).

**Warning**: This is a proof of concept. Data is stored in memory except for uploaded pictures. The data is saved to disk using [pickle](http://docs.python.org/library/pickle.html), but this is far from being efficient. pstream currently does not provide an authentication mechanism.

## Requirements

Requirements can be installed using pip, I recommend using a virtualenv.

    pip install -r requirements.txt

## Setup

### Server Certificate
pstream impersonates iCloud servers, so you need to create a X.509 SSL server certificate and make the client devices trust it. Its common name should be `*.icloud.com`. Place private key and certificate in PEM encoding(as created by OpenSSL) in `certs/icloud.com.{key,crt}`.

You can make your devices trust the certificate e.g. by installing the certificate on the device.

### Push
If you want devices to automatically download photos once another device has uploaded them, you need to set up [pushproxy](https://github.com/meeee/pushproxy). pstream automatically tries to connect to a pushproxy instance running on 127.0.0.1:1234, where pushproxy listens by default.

## Running
pstream listens on port 443 by default, this requires root privileges. It tries to use sudo to acquire them. The root privileges are only used for listening on this port and dropped to your current user for the process serving requests.

    cd pstream
    ./runstreams.sh

See `settings/development.py` for changing the default configuration.
