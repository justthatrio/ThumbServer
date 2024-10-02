# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

ARG NODE_VERSION=y

FROM node:${NODE_VERSION}-alpine

# Use production node environment by default.
ENV NODE_ENV production

WORKDIR /usr/src/app

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.npm to speed up subsequent builds.
# Leverage a bind mounts to package.json and package-lock.json to avoid having to copy them into
# into this layer.
RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    --mount=type=cache,target=/root/.npm \
    npm ci --omit=dev

# Run the application as a non-root user.
USER node

# Copy the rest of the source files into the image.
COPY . .


# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages
RUN apk add --no-cache wget

# Download Blender 3.3
RUN wget https://download.blender.org/release/Blender3.3/blender-3.3.0-linux-x64.tar.xz \
    && tar -xvf blender-3.3.0-linux-x64.tar.xz \
    && rm blender-3.3.0-linux-x64.tar.xz

# Expose the port that the application listens on.
EXPOSE 5000

# Run the application.
CMD node run ./
