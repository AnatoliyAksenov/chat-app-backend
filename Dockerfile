FROM python:3.12-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

ARG ADDITIONAL_CORS
ENV ADDITIONAL_CORS=${ADDITIONAL_CORS}

ARG API_KEY
ARG BASE_URL
ARG MODEL_NAME
ARG FOLDER
ARG MCP_CONFIG
ARG LDAP_SERVER
ARG LDAP_PORT
ARG POSTGRESQL_URL

ENV API_KEY=${API_KEY}
ENV BASE_URL=${BASE_URL}
ENV MODEL_NAME=${MODEL_NAME}
ENV FOLDER=${FOLDER}
ENV MCP_CONFIG=${MCP_CONFIG}
ENV LDAP_SERVER=${LDAP_SERVER}
ENV LDAP_PORT=${LDAP_PORT}
ENV POSTGRESQL_URL=${POSTGRESQL_URL}

RUN mkdir /app

WORKDIR /app

COPY . .

RUN echo API_KEY=$API_KEY > .env && \
    echo BASE_URL=$BASE_URL >> .env && \
    echo MODEL_NAME=$MODEL_NAME >> .env && \
    echo FOLDER=$FOLDER >> .env && \
    echo MCP_CONFIG=$MCP_CONFIG >> .env && \
    echo LDAP_SERVER=$LDAP_SERVER >> .env && \
    echo LDAP_PORT=$LDAP_PORT >> .env && \
    echo POSTGRESQL_URL=$POSTGRESQL_URL >> .env


RUN if [ -n "$HTTP_PROXY" ]; then \
      pip install --proxy "$HTTP_PROXY" poetry==2.1.3; \
    else \
      pip install poetry==2.1.3; \
    fi && \
    poetry install --no-root

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--forwarded-allow-ips", "*"]