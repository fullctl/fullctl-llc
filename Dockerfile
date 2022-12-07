
ARG virtual_env=/venv
ARG install_to=/srv/service
ARG poetry_pin="==1.2.2"

ARG build_deps=" \
    build-base \
    postgresql-dev \
    g++ \
    git \
    libffi-dev \
    libjpeg-turbo-dev \
    linux-headers \
    make \
    openssl-dev \
    curl \
    rust \
    cargo \
    "
ARG run_deps=" \
    libgcc \
    postgresql-libs \
    "

FROM python:3.9-alpine as base

ARG virtual_env

# env to pass to sub images
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=$virtual_env
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# build container
FROM base as builder

ARG build_deps
ARG poetry_pin

RUN apk upgrade --no-cache --available \
    && apk --no-cache add $build_deps

# Use Pip to install Poetry
RUN python3 -m pip install --upgrade pip && pip install "poetry$poetry_pin"

# Create a VENV
RUN python3 -m venv "$VIRTUAL_ENV"

WORKDIR /build

# individual files here instead of COPY . . for caching
COPY pyproject.toml poetry.lock ./

# Need to upgrade pip and wheel within Poetry for all its installs
RUN poetry run pip install --upgrade pip wheel
RUN poetry install --no-root
