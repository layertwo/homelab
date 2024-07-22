FROM alpine:3.20.2 AS builder
ENV BIRD_VERSION=2.15.1
RUN apk update
RUN apk upgrade
RUN apk add curl
RUN curl -LOk https://bird.network.cz/download/bird-$BIRD_VERSION.tar.gz

RUN apk add curl build-base flex bison m4 linux-headers ncurses-dev readline-dev git libssh-dev

RUN tar xvf bird-$BIRD_VERSION.tar.gz
WORKDIR /bird-$BIRD_VERSION
RUN ./configure
RUN make install

FROM alpine:3.20.2
RUN apk update
RUN apk upgrade
RUN apk add bash libssh inotify-tools
RUN mkdir -p /usr/local/var/run
COPY --from=builder /usr/local/sbin/bird /usr/local/sbin/bird
COPY --from=builder /usr/local/sbin/birdc /usr/local/sbin/birdc
COPY birdvars.conf /usr/local/include/birdvars.conf
COPY wrapper.sh /wrapper.sh
COPY reconfig.sh /reconfig.sh
COPY docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
# CMD ["bird",  "-fR"]
CMD ./wrapper.sh
