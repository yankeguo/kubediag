FROM ghcr.io/astral-sh/uv:python3.13-trixie

ENV LANG="zh_CN.UTF-8"
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y locales locales-all tzdata ca-certificates vim curl tini && \
    rm -rf /var/lib/apt/lists/* && \
    TZ=Asia/Shanghai && \
    echo $TZ >/etc/timezone && \
    ln -sf /usr/share/zoneinfo/$TZ /etc/localtime

WORKDIR /app

ADD . .

RUN uv sync --locked

ENTRYPOINT [ "/usr/bin/tini", "--" ]

CMD [ "./run.sh" ]