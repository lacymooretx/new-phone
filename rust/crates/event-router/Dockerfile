FROM rust:1.85-alpine AS builder
RUN apk add --no-cache musl-dev cmake make perl
WORKDIR /app

COPY Cargo.toml Cargo.lock ./
COPY shared/ shared/
COPY crates/event-router/ crates/event-router/

# Create dummy crates for other workspace members
RUN for crate in sip-proxy rtp-relay dpma-service parking-manager e911-handler sms-gateway; do \
      mkdir -p crates/$crate/src && \
      echo "fn main(){}" > crates/$crate/src/main.rs && \
      echo '[package]' > crates/$crate/Cargo.toml && \
      echo "name = \"$crate\"" >> crates/$crate/Cargo.toml && \
      echo 'version = "0.1.0"' >> crates/$crate/Cargo.toml && \
      echo 'edition = "2021"' >> crates/$crate/Cargo.toml; \
    done

RUN cargo build --release -p event-router

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=builder /app/target/release/event-router /usr/local/bin/
USER 65534
ENTRYPOINT ["event-router"]
