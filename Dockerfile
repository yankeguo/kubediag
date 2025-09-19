FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y tzdata ca-certificates vim curl tini && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ADD . .

RUN uv sync --locked

ENTRYPOINT [ "/usr/bin/tini", "--" ]

CMD [ "./run.sh" ]
