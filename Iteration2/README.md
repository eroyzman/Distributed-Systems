# Distributed Systems: Phase 1
1. Close repo with the `git clone https://github.com/Ferenecruma/Distributed-Sytems-Phase-1.git`
2. Write `docker-compose up --build`
3. Use some tool ([httpie](https://httpie.io/cli), curl, [httpx](https://www.python-httpx.org/)) to make http request to the master node
```
>> http POST localhost:8000 message=hello  
HTTP/1.0 200 OK
Content-Length: 49
Content-Type: application/json
Date: Sun, 17 Oct 2021 20:10:45 GMT
Server: Werkzeug/2.0.2 Python/3.9.7

{
    "message": "successful",
    "status": "OK"
}

>> http localhost:8000
HTTP/1.0 200 OK
Content-Length: 5
Content-Type: text/html; charset=utf-8
Date: Sun, 17 Oct 2021 20:10:56 GMT
Server: Werkzeug/2.0.2 Python/3.9.7

hello
```
