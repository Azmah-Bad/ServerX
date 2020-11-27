# Dockerfile
FROM ubuntu:bionic


COPY clients/client1 client


CMD ["./client", "10.25.34.51","8080","gros-fichier.mp4"]