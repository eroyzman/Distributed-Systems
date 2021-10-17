# Get the latest base image for python
FROM python:latest
# Put files at the image '/server/' folder.
#ADD client/client.py /client/
ADD client.py /client/
# '/server/' is base directory
WORKDIR /client/
# execute the command
CMD [ "python3", "/client/client.py" ]
#docker build -t client .
#docker run --network=my_network -it client