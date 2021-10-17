# Get the latest base image for python
FROM python:latest
# Put files at the image '/server/' folder.
#ADD master/master.py /master/
ADD master.py /master/
# '/server/' is base directory
WORKDIR /master/
# Expose port 9090 in the container
EXPOSE 9090
# execute the command
CMD [ "python3", "/master/master.py" ]
#docker network create my_network
#docker build -t master .
#docker run --network=my_network --name master_dns -it master