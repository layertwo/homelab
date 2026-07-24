# Media Management Stack

This document provides detailed information about the media management stack in the homelab.

## Overview

The media management stack is a collection of applications that work together to automate the downloading, organizing, and streaming of media content. The stack includes:

- **Sonarr**: TV show management
- **Radarr**: Movie management
- **Bazarr**: Subtitle management
- **Prowlarr**: Indexer management
- **qBittorrent**: Download client (routed through a Gluetun VPN sidecar)
- **Jellyfin**: Media server
- **Recyclarr**: Configuration management for *arr apps
- **FlareSolverr**: Helps Prowlarr solve Cloudflare/anti-bot challenges on indexers

## Architecture

The media stack follows the following workflow:

1. **Prowlarr** manages indexers and connects to Sonarr and Radarr
2. **Sonarr** and **Radarr** search for content using Prowlarr and send download requests to qBittorrent
3. **qBittorrent** downloads the content and places it in the appropriate directory
4. **Sonarr** and **Radarr** organize the downloaded content
5. **Bazarr** downloads subtitles for the content
6. **Jellyfin** scans the organized content and makes it available for streaming
7. **Recyclarr** keeps the *arr apps configured with best practices

## Components

### Sonarr

Sonarr is an application that manages TV shows. It can automatically search for and download new episodes as they become available.

#### Configuration

- **URL**: sonarr.layertwo.dev
- **Storage**: PVC for configuration; database is a dedicated CloudNativePG (CNPG) PostgreSQL cluster
- **Media Paths**:
  - /shows
  - /downloads

### Radarr

Radarr is an application that manages movies. It can automatically search for and download movies based on a watchlist.

#### Configuration

- **URL**: radarr.layertwo.dev
- **Storage**: PVC for configuration; database is a dedicated CloudNativePG (CNPG) PostgreSQL cluster
- **Media Paths**:
  - /movies
  - /downloads

### Bazarr

Bazarr is an application that manages subtitles. It can automatically search for and download subtitles for TV shows and movies.

#### Configuration

- **URL**: bazarr.layertwo.dev
- **Storage**: PVC for configuration; database is a dedicated CloudNativePG (CNPG) PostgreSQL cluster
- **Media Paths**:
  - /movies
  - /tv

### Prowlarr

Prowlarr is an application that manages indexers. It provides a unified interface for searching across multiple indexers and can sync indexers with Sonarr and Radarr.

#### Configuration

- **URL**: prowlarr.layertwo.dev
- **Storage**: PVC for configuration; database is a dedicated CloudNativePG (CNPG) PostgreSQL cluster

### FlareSolverr

FlareSolverr is a proxy server that solves Cloudflare and other anti-bot challenges. It is deployed alongside the rest of the stack and used by Prowlarr to work around indexers protected by these challenges.

### qBittorrent

qBittorrent is a download client that handles the actual downloading of content. All torrent traffic is routed through a **Gluetun** VPN sidecar container, paired with a **port-forward manager** sidecar that keeps qBittorrent's listening port in sync with the VPN provider's dynamically assigned forwarded port.

#### Configuration

- **URL**: qt.layertwo.dev
- **Storage**: PVC for configuration and downloads
- **Download Path**: /data/downloads

### Jellyfin

Jellyfin is a media server that provides a web interface for browsing and streaming media content.

#### Configuration

- **URL**: jellyfin.layertwo.dev
- **Storage**: PVC for configuration and metadata
- **Media Paths**:
  - /movies
  - /tv

### Recyclarr

Recyclarr is a tool that synchronizes recommended settings from the TRaSH guides to Sonarr and Radarr.

#### Configuration

- Runs as a CronJob
- Configures quality profiles, custom formats, and release profiles

## Storage

The media stack uses persistent storage for both configuration and media content:

- **Configuration**: Each application has its own PVC for storing configuration
- **Databases**: Sonarr, Radarr, Bazarr, and Prowlarr each use a dedicated CloudNativePG (CNPG) PostgreSQL cluster instead of an embedded database on the config PVC
- **Media**: Shared NFS storage is used for media content, with separate directories for TV shows, movies, and downloads

## Networking

The media stack is exposed through the external Traefik instance:

- Each application has its own subdomain (e.g., sonarr.layertwo.dev)
- Authentication is handled by Pocket ID via an OIDC Traefik Middleware (`mediabox-oidc`)

## Maintenance

### Updating

Chart versions and image tags are pinned exactly rather than tracking a floating tag. Updates are proposed by Renovate bot as pull requests; once a PR is merged, Flux CD picks up the new pinned version and applies it.

### Backup

- There is no VolSync (or other automated) backup configured for any mediabox application's configuration
- Media content backup depends on the underlying NFS storage, not any in-cluster process

## Troubleshooting

### Download Issues

If downloads are not working:

1. Check that qBittorrent is running and accessible
2. Verify that Sonarr and Radarr can connect to qBittorrent
3. Check that Prowlarr is configured correctly and can connect to indexers

### Streaming Issues

If streaming is not working:

1. Check that Jellyfin is running and accessible
2. Verify that Jellyfin can access the media directories
3. Check that the media files are in a format that Jellyfin can play

### Subtitle Issues

If subtitles are not being downloaded:

1. Check that Bazarr is running and accessible
2. Verify that Bazarr can connect to Sonarr and Radarr
3. Check that Bazarr is configured with subtitle providers
