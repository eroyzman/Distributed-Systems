# Get the latest base image for python
FROM python:latest
# Put files at the image '/client/' folder.
#ADD secondary1/secondary1.py /secondary1/
ADD secondary1.py /secondary1/
# '/server/' is base directory
WORKDIR /secondary1/
# execute the command
CMD [ "python3", "/secondary1/secondary1.py" ]
#docker build -t secondary1 .
#docker run --network=my_network -it secondary1