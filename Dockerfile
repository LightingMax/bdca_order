FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV ENV_PATH=/opt/conda/envs/order
ENV CUPS_SERVER=/run/cups/cups.sock

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       libcups2 \
       cups-client \
       poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/order

COPY .docker/order-env.tar.gz /tmp/order-env.tar.gz
RUN mkdir -p "${ENV_PATH}" \
    && tar -xzf /tmp/order-env.tar.gz -C "${ENV_PATH}" \
    && rm /tmp/order-env.tar.gz \
    && if [ -x "${ENV_PATH}/bin/conda-unpack" ] && [ -x "${ENV_PATH}/bin/python" ]; then "${ENV_PATH}/bin/python" "${ENV_PATH}/bin/conda-unpack"; fi

ENV PATH="${ENV_PATH}/bin:${PATH}"

COPY . /workspace/order

ARG BUILD_VERSION=unknown
ARG BUILD_TIME=unknown
ARG REQ_SHA256=unknown
RUN mkdir -p /workspace/order/.build_meta \
    && echo "${REQ_SHA256}" > /workspace/order/.build_meta/requirements.sha256 \
    && echo "${BUILD_VERSION}" > /workspace/order/.build_meta/version \
    && echo "${BUILD_TIME}"    > /workspace/order/.build_meta/build_time \
    && echo "full"             > /workspace/order/.build_meta/build_mode

LABEL order.build.version="${BUILD_VERSION}" \
      order.build.time="${BUILD_TIME}" \
      order.build.mode="full" \
      order.req.sha256="${REQ_SHA256}"

EXPOSE 12345

CMD ["python", "run.py"]
