FROM safarov/freeswitch:latest

COPY entrypoint.sh /custom-entrypoint.sh
RUN chmod +x /custom-entrypoint.sh

EXPOSE 5061/tcp 5066/tcp 7443/tcp 8021/tcp

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD fs_cli -x "status" || exit 1

ENTRYPOINT ["/custom-entrypoint.sh"]
