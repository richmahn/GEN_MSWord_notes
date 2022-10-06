FROM nikolaik/python-nodejs:latest

COPY . /app
WORKDIR /app

RUN mkdir /repos
RUN cd /repos
RUN git clone https://git.door43.org/unfoldingWord/en_tn.git
