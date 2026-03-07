FROM rust:1.85-alpine AS builder
RUN apk add --no-cache musl-dev cmake make perl
WORKDIR /app

# Copy workspace files
COPY Cargo.toml Cargo.lock ./
COPY shared/ shared/
COPY crates/sip-proxy/ crates/sip-proxy/

# Create dummy crates for other workspace members
RUN mkdir -p crates/rtp-relay/src && echo "fn main(){}" > crates/rtp-relay/src/main.rs && cp crates/sip-proxy/Cargo.toml crates/rtp-relay/Cargo.toml.bak
RUN mkdir -p crates/dpma-service/src && echo "fn main(){}" > crates/dpma-service/src/main.rs
RUN mkdir -p crates/event-router/src && echo "fn main(){}" > crates/event-router/src/main.rs
RUN mkdir -p crates/parking-manager/src && echo "fn main(){}" > crates/parking-manager/src/main.rs
RUN mkdir -p crates/e911-handler/src && echo "fn main(){}" > crates/e911-handler/src/main.rs
RUN mkdir -p crates/sms-gateway/src && echo "fn main(){}" > crates/sms-gateway/src/main.rs

# Create minimal Cargo.toml for dummy crates
RUN for crate in rtp-relay dpma-service event-router parking-manager e911-handler sms-gateway; do \
      echo '[package]' > crates/$crate/Cargo.toml && \
      echo "name = \"$crate\"" >> crates/$crate/Cargo.toml && \
      echo 'version = "0.1.0"' >> crates/$crate/Cargo.toml && \
      echo 'edition = "2021"' >> crates/$crate/Cargo.toml; \
    done

RUN cargo build --release -p sip-proxy

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=builder /app/target/release/sip-proxy /usr/local/bin/
USER 65534
ENTRYPOINT ["sip-proxy"]
